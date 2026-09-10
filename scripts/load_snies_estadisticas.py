#!/usr/bin/env python3
"""
Loader for SNIES estadístico — Matriculados and Graduados by programa.

Usage:
    python scripts/load_snies_estadisticas.py [--anio 2025] [--dry-run]

Workflow:
  1. Fetch https://snies.mineducacion.gov.co/portal/ESTADISTICAS/Bases-consolidadas/
     and parse the HTML to find the download URLs for "Estudiantes Matriculados {anio}"
     and "Estudiantes Graduados {anio}".
  2. Download each .xlsx (stream, ~19 MB each).
  3. Parse: skip 6 header rows, aggregate SUM(value) GROUP BY codigo_snies_programa.
  4. UPSERT into snies_estadisticas_programa.

Excel structure (confirmed with 2025 matriculados file):
  - Data sheet: first sheet whose name starts with a digit (e.g. "1.")
  - Rows 1-6: metadata/headers; row 7+ = data
  - Col  1 (0-based): INSTITUCIÓN DE EDUCACIÓN SUPERIOR
  - Col 13: CÓDIGO SNIES DEL PROGRAMA
  - Col 14: PROGRAMA ACADÉMICO
  - Col 16: METODOLOGÍA (presencial / virtual / a distancia)
  - Col 26: NIVEL DE FORMACIÓN
  - Col 38: AÑO
  - Col 40: MATRICULADOS (or GRADUADOS in the graduados file)
  Data is disaggregated by semester and sex — loader sums value per codigo_snies
  and takes the first non-null text fields (IES, programa, modalidad, nivel).

Target table schema (snies_estadisticas_programa):
  codigo_snies, nombre_ies, nombre_programa, modalidad, nivel_formacion,
  anio, matriculados, graduados, inscritos, admitidos, created_at
  (inscritos and admitidos default to 0 — loaded from separate SNIES files not yet integrated)
"""
from __future__ import annotations

import argparse
import io
import logging
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import openpyxl

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://snies.mineducacion.gov.co"
BASES_PAGE = f"{BASE_URL}/portal/ESTADISTICAS/Bases-consolidadas/"
# All downloadable files on this CMS are served under /1778/ regardless of the
# page they are linked from (e.g. hrefs are bare filenames like
# "articles-430149_recurso.xlsx" without any path prefix).
CMS_FILE_BASE = f"{BASE_URL}/1778/"

# Column indices in the data sheet (0-based, confirmed with 2025 matriculados file)
COL_IES          =  1   # INSTITUCIÓN DE EDUCACIÓN SUPERIOR
COL_CODIGO_SNIES = 13   # CÓDIGO SNIES DEL PROGRAMA
COL_PROGRAMA     = 14   # PROGRAMA ACADÉMICO
COL_MODALIDAD    = 16   # METODOLOGÍA
COL_NIVEL        = 26   # NIVEL DE FORMACIÓN
COL_ANIO         = 38   # AÑO
COL_VALUE        = 40   # MATRICULADOS or GRADUADOS — both files use the same last column


def _find_xlsx_url(soup: BeautifulSoup, keyword: str, anio: int) -> str | None:
    """Return the href for the exact 'Estudiantes {keyword} {anio}' dataset.

    The SNIES portal lists multiple variants per keyword, e.g.:
      - "Estudiantes Matriculados 2025"           ← the total dataset we want
      - "Estudiantes Matriculados en primer curso 2025"  ← a subset, do NOT use

    We require the keyword to appear as a full word sequence WITHOUT the
    "en primer curso" qualifier.  The pattern anchors to word boundaries and
    explicitly excludes the "en primer curso" variant.
    """
    # Matches "Matriculados {anio}" (with optional "Estudiantes " prefix) but
    # NOT "Matriculados en primer curso {anio}".
    exact_pat = re.compile(
        rf"\b{re.escape(keyword)}\b(?!\s+en\s+primer\s+curso).*\b{anio}\b",
        re.I,
    )
    candidates = []
    for tag in soup.find_all("a", href=True):
        text = tag.get_text(strip=True)
        if exact_pat.search(text):
            href = tag["href"]
            log.info("RAW href para '%s': %r", text, href)
            if not href.startswith("http"):
                href = CMS_FILE_BASE + href
            candidates.append((text, href))

    if not candidates:
        return None

    # Prefer the shortest text match (fewest qualifiers = most general dataset)
    candidates.sort(key=lambda x: len(x[0]))
    text, href = candidates[0]
    log.info("Selected '%s' → %s", text, href)
    return href


def _fetch_urls(anio: int) -> dict[str, str]:
    """Scrape Bases-consolidadas page and return {matriculados: url, graduados: url}."""
    log.info("Fetching %s …", BASES_PAGE)
    resp = requests.get(BASES_PAGE, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    mat_url = _find_xlsx_url(soup, "Matriculados", anio)
    grad_url = _find_xlsx_url(soup, "Graduados", anio)

    if not mat_url:
        raise RuntimeError(f"No se encontró el link de Matriculados {anio} en {BASES_PAGE}")
    if not grad_url:
        log.warning("No se encontró el link de Graduados %d — se cargará solo matriculados.", anio)

    return {"matriculados": mat_url, "graduados": grad_url}


def _download_xlsx(url: str) -> bytes:
    log.info("Descargando %s …", url)
    with requests.get(url, stream=True, timeout=120, headers={"User-Agent": "Mozilla/5.0"}) as r:
        r.raise_for_status()
        chunks = []
        total = 0
        for chunk in r.iter_content(chunk_size=1 << 20):  # 1 MB chunks
            chunks.append(chunk)
            total += len(chunk)
            log.info("  %.1f MB descargados…", total / 1e6)
        return b"".join(chunks)


def _parse_xlsx(data: bytes, anio: int) -> dict[int, dict]:
    """Return {codigo_snies: {value, nombre_ies, nombre_programa, modalidad, nivel_formacion}}
    summing value across all rows (disaggregated by semester+sex) per codigo_snies.
    Text fields (IES, programa, modalidad, nivel) are taken from the first non-null row.
    """
    log.info("Parseando Excel (%d bytes) …", len(data))
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)

    # Find the first sheet whose name starts with a digit
    sheet_name = next((n for n in wb.sheetnames if n[:1].isdigit()), wb.sheetnames[0])
    ws = wb[sheet_name]
    log.info("Hoja de datos: '%s'", sheet_name)

    programs: dict[int, dict] = {}
    skipped = 0
    processed = 0

    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i < 6:  # rows 0-5 are metadata/headers
            continue
        try:
            codigo_raw = row[COL_CODIGO_SNIES]
            value_raw  = row[COL_VALUE]
            if codigo_raw is None or value_raw is None:
                skipped += 1
                continue
            codigo = int(codigo_raw)
            value  = int(value_raw)

            if codigo not in programs:
                programs[codigo] = {
                    "value":          0,
                    "nombre_ies":     str(row[COL_IES] or "").strip(),
                    "nombre_programa": str(row[COL_PROGRAMA] or "").strip(),
                    "modalidad":      str(row[COL_MODALIDAD] or "").strip(),
                    "nivel_formacion": str(row[COL_NIVEL] or "").strip(),
                }
            programs[codigo]["value"] += value
            processed += 1
        except (TypeError, ValueError, IndexError):
            skipped += 1

    log.info(
        "Filas procesadas: %d | omitidas: %d | programas únicos: %d",
        processed, skipped, len(programs),
    )
    wb.close()
    return programs


def _upsert(
    conn,           # None when dry_run=True
    anio: int,
    matriculados: dict[int, dict],
    graduados: dict[int, dict],
    dry_run: bool,
) -> int:
    """UPSERT into snies_estadisticas_programa. Returns number of rows written."""
    all_codigos = set(matriculados) | set(graduados)

    rows = []
    for codigo in all_codigos:
        mat = matriculados.get(codigo, {})
        grad = graduados.get(codigo, {})
        # Prefer metadata from matriculados file; fall back to graduados if absent
        meta = mat if mat else grad
        rows.append((
            codigo,
            meta.get("nombre_ies", ""),
            meta.get("nombre_programa", ""),
            meta.get("modalidad", ""),
            meta.get("nivel_formacion", ""),
            anio,
            mat.get("value", 0),
            grad.get("value", 0),
            0,   # inscritos — loaded from a separate SNIES file, not yet integrated
            0,   # admitidos — same
        ))

    if dry_run:
        log.info("DRY RUN — %d filas listas para UPSERT (no se escribió nada).", len(rows))
        if rows:
            for r in rows[:5]:
                log.info(
                    "  sample: codigo=%s ies=%r programa=%r anio=%s mat=%s grad=%s",
                    r[0], r[1], r[2], r[5], r[6], r[7],
                )
        return len(rows)

    sql = """
        INSERT INTO snies_estadisticas_programa
            (codigo_snies, nombre_ies, nombre_programa, modalidad, nivel_formacion,
             anio, matriculados, graduados, inscritos, admitidos)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (codigo_snies, anio) DO UPDATE SET
            nombre_ies      = EXCLUDED.nombre_ies,
            nombre_programa = EXCLUDED.nombre_programa,
            modalidad       = EXCLUDED.modalidad,
            nivel_formacion = EXCLUDED.nivel_formacion,
            matriculados    = EXCLUDED.matriculados,
            graduados       = EXCLUDED.graduados
    """
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()
    log.info("UPSERT completado: %d filas en snies_estadisticas_programa.", len(rows))
    return len(rows)


def _get_connection():
    try:
        from api.database import connection as _conn_cm
        return _conn_cm()
    except Exception:
        import psycopg2
        url = os.environ.get("RAILWAY_DATABASE_URL") or os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError("Set RAILWAY_DATABASE_URL or DATABASE_URL")
        return psycopg2.connect(url)


def run(anio: int, dry_run: bool) -> None:
    urls = _fetch_urls(anio)
    mat_url  = urls["matriculados"]
    grad_url = urls.get("graduados")

    log.info("Descargando Matriculados …")
    mat_data = _download_xlsx(mat_url)
    log.info("Parseando Matriculados …")
    matriculados = _parse_xlsx(mat_data, anio)

    graduados: dict[int, dict] = {}
    if grad_url:
        log.info("Descargando Graduados …")
        grad_data = _download_xlsx(grad_url)
        log.info("Parseando Graduados …")
        graduados = _parse_xlsx(grad_data, anio)
    else:
        log.warning("Graduados no disponibles para %d — se cargará graduados=0.", anio)

    if dry_run:
        n = _upsert(None, anio, matriculados, graduados, dry_run=True)
        log.info("Listo (dry-run). %d programas listos para anio=%d.", n, anio)
        return

    log.info("Conectando a DB …")
    with _get_connection() as conn:
        n = _upsert(conn, anio, matriculados, graduados, dry_run=False)
    log.info("Listo. %d programas cargados para anio=%d.", n, anio)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Carga estadísticas SNIES a PostgreSQL")
    ap.add_argument("--anio", type=int, default=2025, help="Año a procesar (default: 2025)")
    ap.add_argument("--dry-run", action="store_true", help="Parsea pero no escribe en DB")
    args = ap.parse_args()
    run(args.anio, args.dry_run)
