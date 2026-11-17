#!/usr/bin/env python3
"""
scripts/ingest_program.py

AI-powered curriculum ingestion using GPT-4o-mini.

Usage:
    python scripts/ingest_program.py \
        --carpeta <ruta> \
        --programa "Nombre del Programa" \
        --nivel pregrado|especializacion \
        --domain <domain_key> \
        [--preview | --execute --yes]

Requirements:
    openai>=1.0, pdfplumber, python-docx, openpyxl, psycopg2

OPENAI_API_KEY must be set in environment or .env.local.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

# ── paths ─────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = REPO_ROOT / "outputs"
CACHE_FILE = OUTPUTS_DIR / "ingest_cache.json"
ENV_LOCAL = REPO_ROOT / ".env.local"

sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ── canonical skill map (superset; works without Marketing parser) ────────────

_CANONICAL_SKILLS: dict[str, str] = {
    "seo": "SEO", "sem": "SEM", "roi": "ROI", "kpi": "KPI", "ctr": "CTR",
    "crm": "CRM", "roas": "ROAS", "cpm": "CPM", "cpc": "CPC", "rtb": "RTB",
    "nlp": "NLP", "olap": "OLAP", "oltp": "OLTP", "etl": "ETL", "elt": "ELT",
    "pca": "PCA", "aws": "AWS", "gcp": "GCP", "ux": "UX", "cx": "CX",
    "power bi": "Power BI",
    "hubspot": "HubSpot", "mailchimp": "Mailchimp",
    "linkedin": "LinkedIn", "youtube": "YouTube", "tiktok": "TikTok",
    "wordpress": "WordPress", "shopify": "Shopify", "woocommerce": "WooCommerce",
    "prestashop": "PrestaShop", "magento": "Magento",
    "e-commerce": "E-Commerce", "ecommerce": "E-Commerce", "e commerce": "E-Commerce",
    "marketing de contenidos": "Marketing de Contenidos",
    "marketing de afiliados": "Marketing de Afiliados",
    "embudo de conversion": "Embudo de Conversión",
    "embudo de conversión": "Embudo de Conversión",
    "posicionamiento de marca": "Posicionamiento de Marca",
    "investigacion de mercados": "Investigación de Mercados",
    "investigación de mercados": "Investigación de Mercados",
    "comportamiento del consumidor": "Comportamiento del Consumidor",
    "segmentacion de mercados": "Segmentación de Mercados",
    "segmentación de mercados": "Segmentación de Mercados",
    "mezcla de mercadeo": "Mezcla de Mercadeo",
    "analitica web": "Analítica Web", "analítica web": "Analítica Web",
    "analitica digital": "Analítica Digital", "analítica digital": "Analítica Digital",
    "produccion audiovisual": "Producción Audiovisual",
    "producción audiovisual": "Producción Audiovisual",
    "diseno grafico": "Diseño Gráfico", "diseño gráfico": "Diseño Gráfico",
    "identidad visual": "Identidad Visual",
    "customer experience": "Customer Experience",
    "pasarelas de pago": "Pasarelas de Pago", "pasarela de pago": "Pasarelas de Pago",
    "medios de pago": "Medios de Pago", "medio de pago": "Medios de Pago",
    "logistica": "Logística", "logística": "Logística",
    "fulfillment": "Fulfillment", "omnicanalidad": "Omnicanalidad",
    "experiencia de usuario": "Experiencia de Usuario",
    "catalogo de productos": "Catálogo de Productos",
    "catálogo de productos": "Catálogo de Productos",
    "gestion de inventarios": "Gestión de Inventarios",
    "gestión de inventarios": "Gestión de Inventarios",
    "seguridad en e-commerce": "Seguridad en E-Commerce",
    "seguridad en ecommerce": "Seguridad en E-Commerce",
    "plataformas de e-commerce": "Plataformas de E-Commerce",
    "plataforma de e-commerce": "Plataformas de E-Commerce",
    "plataformas de ecommerce": "Plataformas de E-Commerce",
}

# ── text normalization ─────────────────────────────────────────────────────────

def _normalize_text(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c)).strip()


# ── OpenAI system prompt ───────────────────────────────────────────────────────

OPENAI_SYSTEM_PROMPT = """\
You are an academic curriculum parser for a Colombian university.
Extract structured information from the given course block.

Return ONLY a valid JSON object with exactly this schema:
{
  "asignatura": "exact course name as written in the block",
  "creditos": <integer or null>,
  "cuatrimestre": <integer or null>,
  "resultados_aprendizaje": ["complete RA sentence 1", ...],
  "contenidos": ["topic 1", "topic 2", ...],
  "skills": [
    {"nombre": "canonical skill name", "tipo": "<tipo>"}
  ]
}

Valid tipos: herramienta, tecnologia, metodologia, competencia_dominio, skill_transversal, marketing

Rules:
- Do NOT invent information not present in the text.
- Use canonical capitalization: SEO, LinkedIn, Power BI, E-Commerce, Python, SQL, etc.
- Do NOT repeat the same skill twice (deduplicate by lowercase name).
- Keep resultados_aprendizaje as full sentences, one per list item.
- Separate domain/technical skills from soft/transversal skills.
- If a section is absent or says "No aplica", return empty list [].
- Return ONLY the JSON object, no prose.\
"""

# ── page-header pattern (strip from all programs) ─────────────────────────────

_PAGE_HEADER_RE = re.compile(
    r"(MICROCURR[IÍ]CULOS?\s+DEL\s+PROGRAMA|"
    r"DEL\s+PROGRAMA\s+ACAD[EÉ]MICO|"
    r"P[aá]gina\s+\d+\s+de\s+\d+)",
    re.IGNORECASE,
)

# ── file extraction ────────────────────────────────────────────────────────────

def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return _extract_docx(path)
    elif suffix == ".pdf":
        return _extract_pdf(path)
    elif suffix in (".xlsx", ".xls"):
        return _extract_xlsx(path)
    else:
        log.warning("Unsupported file type: %s", path.suffix)
        return ""


def _extract_docx(path: Path) -> str:
    from docx import Document  # type: ignore
    doc = Document(str(path))
    parts: list[str] = []
    for p in doc.paragraphs:
        t = p.text.strip()
        if t:
            parts.append(t)
    for table in doc.tables:
        for row in table.rows:
            seen: set[str] = set()
            for cell in row.cells:
                txt = cell.text.strip()
                if txt and txt not in seen:
                    seen.add(txt)
                    parts.append(txt)
    return "\n".join(parts)


def _extract_pdf(path: Path) -> str:
    try:
        import pdfplumber  # type: ignore
        pages: list[str] = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    pages.append(txt)
        return "\n".join(pages)
    except Exception as exc:
        log.warning("pdfplumber failed for %s: %s — trying pdftotext", path.name, exc)
        import subprocess
        try:
            result = subprocess.run(
                ["pdftotext", "-layout", str(path), "-"],
                capture_output=True, text=True, timeout=30,
            )
            return result.stdout
        except Exception as exc2:
            log.warning("pdftotext also failed: %s", exc2)
            return ""


def _extract_xlsx(path: Path) -> str:
    from openpyxl import load_workbook  # type: ignore
    wb = load_workbook(str(path), read_only=True, data_only=True)
    parts: list[str] = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
            if cells:
                parts.append("\t".join(cells))
    wb.close()
    return "\n".join(parts)

# ── block splitting ────────────────────────────────────────────────────────────

_DENOM_RE = re.compile(
    r"(?:^|\n)(?=DENOMINACI[OÓ]N\s+DE\s+LA\s+ASIGNATURA)",
    re.IGNORECASE,
)


def split_into_blocks(text: str, programa: str) -> list[dict]:
    # Strip repeated page headers
    clean = _PAGE_HEADER_RE.sub("", text)
    # Strip program-name repeats (whole lines matching normalized program name)
    prog_norm = _normalize_text(programa)
    lines = clean.splitlines()
    filtered: list[str] = []
    for line in lines:
        if _normalize_text(line) == prog_norm:
            continue
        filtered.append(line)
    clean = "\n".join(filtered)

    parts = _DENOM_RE.split(clean)
    parts = [p.strip() for p in parts if p.strip()]

    if not parts:
        return [{"block_text": clean.strip(), "block_index": 0}]

    # First segment before any DENOMINACIÓN is preamble — drop if tiny
    result: list[dict] = []
    start_idx = 0
    if parts and not re.match(r"DENOMINACI[OÓ]N", parts[0], re.IGNORECASE):
        if len(parts[0]) < 200:
            start_idx = 1
        else:
            result.append({"block_text": parts[0], "block_index": 0})
            start_idx = 1

    for i, part in enumerate(parts[start_idx:], 1):
        result.append({"block_text": part, "block_index": i})

    return result if result else [{"block_text": clean.strip(), "block_index": 0}]

# ── SHA-256 cache ──────────────────────────────────────────────────────────────

def hash_block(block_text: str) -> str:
    return hashlib.sha256(block_text.encode("utf-8")).hexdigest()


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def get_cache(block_hash: str) -> dict | None:
    return _load_cache().get(block_hash)


def save_cache(block_hash: str, response: dict) -> None:
    OUTPUTS_DIR.mkdir(exist_ok=True)
    cache = _load_cache()
    cache[block_hash] = response
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

# ── OpenAI call ────────────────────────────────────────────────────────────────

_EMPTY_RECORD: dict = {
    "asignatura": "", "creditos": None, "cuatrimestre": None,
    "resultados_aprendizaje": [], "contenidos": [], "skills": [],
}


def call_openai(block_text: str, programa: str, model: str = "gpt-4o-mini") -> dict:
    block_hash = hash_block(block_text)
    cached = get_cache(block_hash)
    if cached is not None:
        log.debug("Cache hit: %s", block_hash[:12])
        return cached

    _load_env_local()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        log.warning("OPENAI_API_KEY not set — returning empty record")
        return dict(_EMPTY_RECORD)

    try:
        import openai  # type: ignore
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": OPENAI_SYSTEM_PROMPT},
                {"role": "user", "content": f"Programa: {programa}\n\nBloque:\n{block_text[:4000]}"},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=800,
        )
        raw = response.choices[0].message.content or "{}"
        result = json.loads(raw)
        save_cache(block_hash, result)
        return result
    except Exception as exc:
        log.warning("OpenAI call failed: %s — returning empty record", exc)
        return dict(_EMPTY_RECORD)

# ── skill normalization ────────────────────────────────────────────────────────

def normalize_skills(skills_from_openai: list[dict]) -> dict[str, list[str]]:
    seen: set[str] = set()
    buckets: dict[str, list[str]] = {}

    for item in skills_from_openai:
        raw = str(item.get("nombre", "")).strip()
        tipo = str(item.get("tipo", "herramienta")).strip()
        if not raw:
            continue
        norm_raw = _normalize_text(raw)
        canonical = _CANONICAL_SKILLS.get(norm_raw, raw)
        norm_canonical = _normalize_text(canonical)
        if norm_canonical in seen:
            continue
        seen.add(norm_canonical)
        buckets.setdefault(tipo, []).append(canonical)

    return buckets

# ── record builder ─────────────────────────────────────────────────────────────

def _first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def build_record(
    block_result: dict,
    ai_response: dict,
    programa: str,
    domain_key: str,
    source_doc: str,
    doc_hash: str,
) -> dict:
    block_text = block_result["block_text"]
    asignatura = ai_response.get("asignatura") or _first_non_empty_line(block_text)
    source_path_obj = Path(source_doc)
    try:
        rel = str(source_path_obj.relative_to(REPO_ROOT))
    except ValueError:
        rel = source_doc

    return {
        "programa": programa,
        "asignatura": asignatura,
        "descripcion": block_text[:2000],
        "resultados_aprendizaje": ai_response.get("resultados_aprendizaje", [])[:15],
        "resultados_text_raw": "\n".join(ai_response.get("resultados_aprendizaje", [])),
        "contenido_tematico": ai_response.get("contenidos", [])[:20],
        "herramientas_recursos": "",
        "skills": normalize_skills(ai_response.get("skills", [])),
        "semestre_num": str(ai_response.get("cuatrimestre") or ""),
        "creditos_num": str(ai_response.get("creditos") or ""),
        "source_document": source_doc,
        "source_path": rel,
        "document_hash": f"{doc_hash}:{block_result['block_index']}",
        "domain_key": domain_key,
    }

# ── preview ────────────────────────────────────────────────────────────────────

def print_preview(
    records: list[dict],
    esps: list[dict],
    programa: str,
    domain_key: str,
) -> None:
    total_skills = sum(sum(len(v) for v in r["skills"].values()) for r in records)
    esp_id = _resolve_esp_id(programa, esps)

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║           PREVIEW — ingest_program.py (AI pipeline)      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  Programa      : {programa}")
    print(f"  Domain        : {domain_key}")
    if esp_id is None:
        print(f"  esp_id        : None  ⚠️  NUEVO — no está en especializaciones aún")
    else:
        print(f"  esp_id        : {esp_id}")
    print(f"  Asignaturas   : {len(records)}")
    print(f"  Skills totales: {total_skills}")
    print()

    for i, r in enumerate(records, 1):
        n_ra = len(r["resultados_aprendizaje"])
        n_sk = sum(len(v) for v in r["skills"].values())
        cuat = r["semestre_num"] or "?"
        cred = r["creditos_num"] or "?"
        print(f"  [{i:02d}] {r['asignatura']}")
        print(f"       Cuatrimestre={cuat}  Créditos={cred}  RA={n_ra}  Skills={n_sk}")
        for ra in r["resultados_aprendizaje"][:2]:
            print(f"       RA: {ra[:80]}")
        for tipo, skills in r["skills"].items():
            print(f"       {tipo}: {', '.join(skills[:8])}")
        print()

    # Write markdown report
    safe = re.sub(r"[^a-z0-9]+", "_", programa.lower()).strip("_")
    OUTPUTS_DIR.mkdir(exist_ok=True)
    md_path = OUTPUTS_DIR / f"ingesta_{safe}.md"
    lines: list[str] = [
        f"# Ingesta AI: {programa}\n",
        f"**Domain:** {domain_key}  ",
        f"**esp_id:** {esp_id if esp_id else 'NUEVO ⚠️'}  ",
        f"**Asignaturas:** {len(records)}  ",
        f"**Skills totales:** {total_skills}  ",
        "",
        "---",
        "",
    ]
    for i, r in enumerate(records, 1):
        lines.append(f"## {i}. {r['asignatura']}")
        lines.append(f"- Cuatrimestre: {r['semestre_num'] or '?'}")
        lines.append(f"- Créditos: {r['creditos_num'] or '?'}")
        lines.append(f"- RA ({len(r['resultados_aprendizaje'])}):")
        for ra in r["resultados_aprendizaje"]:
            lines.append(f"  - {ra}")
        for tipo, skills in r["skills"].items():
            lines.append(f"- {tipo}: {', '.join(skills)}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  → Preview escrito en: {md_path.relative_to(REPO_ROOT)}")

# ── DB helpers (self-contained for use from main) ─────────────────────────────

def _load_env_local() -> None:
    if ENV_LOCAL.exists():
        try:
            from dotenv import load_dotenv  # type: ignore
            load_dotenv(ENV_LOCAL, override=True)
        except ImportError:
            for line in ENV_LOCAL.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _resolve_esp_id(programa: str, esps: list[dict]) -> int | None:
    try:
        from scripts.load_microcurriculos import match_esp_id
        return match_esp_id(programa, esps)
    except Exception:
        prog_n = _normalize_text(programa)
        candidates = [e["id"] for e in esps if _normalize_text(e["nombre"]) in prog_n or prog_n in _normalize_text(e["nombre"])]
        return max(candidates) if candidates else None


def upsert_especializacion(conn, programa: str, nivel: str) -> int:
    """Insert or return existing especializacion id."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM especializaciones WHERE nombre = %s", (programa,))
        row = cur.fetchone()
        if row:
            return row[0]
        nivel_map = {"pregrado": "Pregrado", "especializacion": "Especialización",
                     "maestria": "Maestría", "doctorado": "Doctorado"}
        nivel_display = nivel_map.get(nivel.lower(), "Especialización")
        cur.execute(
            """
            INSERT INTO especializaciones (nombre, nivel_formacion)
            VALUES (%s, %s)
            ON CONFLICT (nombre) DO UPDATE SET nombre = EXCLUDED.nombre
            RETURNING id
            """,
            (programa, nivel_display),
        )
        return cur.fetchone()[0]

# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    os.environ.setdefault("PYTHONUTF8", "1")

    parser = argparse.ArgumentParser(
        description="AI-powered microcurriculum ingestion via GPT-4o-mini"
    )
    parser.add_argument("--carpeta", required=True, help="Folder with .pdf/.docx/.xlsx files")
    parser.add_argument("--programa", required=True, help="Program full name")
    parser.add_argument("--nivel", required=True,
                        choices=["pregrado", "especializacion", "maestria", "doctorado"])
    parser.add_argument("--domain", required=True, help="Domain key (e.g. marketing, artificial_intelligence)")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Required with --execute")
    parser.add_argument("--model", default="gpt-4o-mini")
    args = parser.parse_args()

    if not args.preview and not args.execute:
        parser.print_help()
        sys.exit(0)
    if args.execute and not args.yes:
        print("ERROR: --execute requires --yes")
        sys.exit(1)

    carpeta = Path(args.carpeta)
    if not carpeta.exists():
        print(f"ERROR: carpeta not found: {carpeta}")
        sys.exit(1)

    # 1. Find files
    extensions = (".pdf", ".docx", ".xlsx", ".xls")
    files = [p for p in carpeta.rglob("*") if p.suffix.lower() in extensions]
    if not files:
        print(f"No .pdf/.docx/.xlsx files found in {carpeta}")
        sys.exit(1)
    print(f"[1/4] Found {len(files)} file(s): {', '.join(f.name for f in files)}")

    # 2. Extract and concatenate text
    all_text_parts: list[str] = []
    doc_hash_parts: list[str] = []
    for f in files:
        print(f"  Extracting: {f.name}")
        text = extract_text_from_file(f)
        all_text_parts.append(text)
        doc_hash_parts.append(hashlib.md5(f.read_bytes()).hexdigest())
    full_text = "\n".join(all_text_parts)
    doc_hash = hashlib.md5(full_text.encode()).hexdigest()
    source_doc = files[0].name if len(files) == 1 else f"{files[0].name}+{len(files)-1}more"

    # 3. Split into blocks
    blocks = split_into_blocks(full_text, args.programa)
    print(f"[2/4] Split into {len(blocks)} block(s)")

    # 4. Call OpenAI per block
    print(f"[3/4] Calling {args.model} for each block …")
    records: list[dict] = []
    for block in blocks:
        ai = call_openai(block["block_text"], args.programa, model=args.model)
        rec = build_record(block, ai, args.programa, args.domain, source_doc, doc_hash)
        if rec["asignatura"]:
            records.append(rec)
        else:
            log.debug("Skipping block %d — no asignatura extracted", block["block_index"])
    print(f"  {len(records)} asignaturas extracted")

    # 5. Connect to DB
    conn = None
    esps: list[dict] = []
    db_available = False
    _load_env_local()
    print("[4/4] Connecting to DB …")
    try:
        from scripts.load_microcurriculos import get_conn, fetch_especializaciones
        conn = get_conn()
        esps = fetch_especializaciones(conn)
        db_available = True
        print(f"  DB reachable — {len(esps)} especializaciones found")
    except Exception as exc:
        print(f"  WARNING: DB not reachable — {exc}")

    # 6. Preview or execute
    if args.preview:
        print_preview(records, esps, args.programa, args.domain)
        return

    if args.execute and args.yes:
        if not db_available:
            print("ERROR: DB not reachable. Cannot execute.")
            sys.exit(1)
        from scripts.load_microcurriculos import insert_record, insert_skills
        try:
            esp_id = upsert_especializacion(conn, args.programa, args.nivel)
            esp_nombre = args.programa
            conn.commit()
            print(f"  esp_id = {esp_id}  ({esp_nombre})")

            inserted = 0
            for rec in records:
                mid = insert_record(conn, rec, esp_id, esp_nombre)
                n_sk = insert_skills(conn, mid, rec)
                print(f"  ✓ id={mid}  {rec['asignatura']}  ({n_sk} skills)")
                inserted += 1
            conn.commit()
            print(f"\n  Committed. {inserted} microcurriculos inserted.")
        except Exception as exc:
            if conn:
                conn.rollback()
            print(f"\n  ERROR — rolled back: {exc}")
            sys.exit(1)
        finally:
            if conn:
                conn.close()


if __name__ == "__main__":
    main()
