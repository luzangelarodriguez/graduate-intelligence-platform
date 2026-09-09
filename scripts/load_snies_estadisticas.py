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
  4. UPSERT into snies_estadisticas_programa (codigo_snies, anio, matriculados, graduados).

Excel structure (confirmed with 2025 file):
  - Data sheet: first sheet whose name starts with a digit (e.g. "1.")
  - Rows 1-6: metadata/headers; row 7+ = data
  - Col 13 (0-based): CÓDIGO SNIES DEL PROGRAMA
  - Col 38: AÑO
  - Col 40: MATRICULADOS (or GRADUADOS in the graduados file)
  Data is disaggregated by semester and sex — loader sums all rows per codigo_snies.
"""
from __future__ import annotations

import argparse
import io
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import openpyxl

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BASE_URL = "https://snies.mineducacion.gov.co"
BASES_PAGE = f"{BASE_URL}/portal/ESTADISTICAS/Bases-consolidadas/"

# Column indices in the data sheet (0-based, confirmed with 2025 matriculados file)
COL_CODIGO_SNIES = 13
COL_ANIO         = 38
COL_VALUE        = 40  # MATRICULADOS or GRADUADOS — both files use the last column


def _find_xlsx_url(soup: BeautifulSoup, keyword: str, anio: int) -> str | None:
    """Return the first href whose link text matches keyword and anio (case-insensitive)."""
    patterns = [
        re.compile(rf"{re.escape(keyword)}.*{anio}", re.I),
        re.compile(rf"{anio}.*{re.escape(keyword)}", re.I),
    ]
    for tag in soup.find_all("a", href=True):
        text = tag.get_text(strip=True)
        for pat in patterns:
            if pat.search(text):
                href = tag["href"]
                log.info("RAW href para '%s': %r", text, href)
                if not href.startswith("http"):
                    href = urljoin(BASES_PAGE, href)
                log.info("Found '%s' → %s", text, href)
                return href
    return None


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


def _parse_xlsx(data: bytes, anio: int) -> dict[int, int]:
    """Return {codigo_snies: total_value} summing all rows for the given anio."""
    log.info("Parseando Excel (%d bytes) …", len(data))
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)

    # Find the first sheet whose name starts with a digit
    sheet_name = next((n for n in wb.sheetnames if n[:1].isdigit()), wb.sheetnames[0])
    ws = wb[sheet_name]
    log.info("Hoja de datos: '%s'", sheet_name)

    totals: dict[int, int] = {}
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
            totals[codigo] = totals.get(codigo, 0) + value
            processed += 1
        except (TypeError, ValueError):
            skipped += 1

    log.info("Filas procesadas: %d | omitidas: %d | programas únicos: %d", processed, skipped, len(totals))
    wb.close()
    return totals


def _upsert(
    conn,
    anio: int,
    matriculados: dict[int, int],
    graduados: dict[int, int],
    mat_url: str,
    grad_url: str | None,
    dry_run: bool,
) -> int:
    """UPSERT into snies_estadisticas_programa. Returns number of rows written."""
    all_codigos = set(matriculados) | set(graduados)
    rows = [
        (
            codigo,
            anio,
            matriculados.get(codigo, 0),
            graduados.get(codigo, 0),
            mat_url,
        )
        for codigo in all_codigos
    ]

    if dry_run:
        log.info("DRY RUN — %d filas listas para UPSERT (no se escribió nada).", len(rows))
        if rows:
            sample = rows[:5]
            for r in sample:
                log.info("  sample: codigo=%s anio=%s matriculados=%s graduados=%s", r[0], r[1], r[2], r[3])
        return len(rows)

    sql = """
        INSERT INTO snies_estadisticas_programa
            (codigo_snies, anio, matriculados, graduados, fuente_url)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (codigo_snies, anio) DO UPDATE SET
            matriculados = EXCLUDED.matriculados,
            graduados    = EXCLUDED.graduados,
            fuente_url   = EXCLUDED.fuente_url,
            loaded_at    = now()
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

    mat_data  = _download_xlsx(mat_url)
    matriculados = _parse_xlsx(mat_data, anio)

    graduados: dict[int, int] = {}
    if grad_url:
        grad_data = _download_xlsx(grad_url)
        graduados = _parse_xlsx(grad_data, anio)
    else:
        log.warning("Graduados no disponibles para %d — se cargará matriculados=0 para graduados.", anio)

    with _get_connection() as conn:
        n = _upsert(conn, anio, matriculados, graduados, mat_url, grad_url, dry_run)
    log.info("Listo. %d programas cargados para anio=%d.", n, anio)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Carga estadísticas SNIES a PostgreSQL")
    ap.add_argument("--anio", type=int, default=2025, help="Año a procesar (default: 2025)")
    ap.add_argument("--dry-run", action="store_true", help="Parsea pero no escribe en DB")
    args = ap.parse_args()
    run(args.anio, args.dry_run)
