"""
Diagnóstico de origen de skills "basura" en microcurrículos y mercado.

Secciones:
  a) Skills "R" y "Clasificación" — asignaturas/microcurrículos origen; fragmentos
     ±60 chars del campo clean_text usando el MISMO regex del extractor; conteo de
     "r" minúscula vs "R" mayúscula/RStudio para confirmar si IGNORECASE es la causa.
  b) Top 40 términos de mercado que no son skills (RUIDO_SIEMPRE + verbos/adjetivos/
     fragmentos). Soft skills legítimas listadas aparte como "transversales".
  c) Prog 109 y 9 — títulos de las 15 vacantes más frecuentes + regla _MARKET_SAMPLE_CTE.
  d) Duplicados por normalización (singular/plural, ES/EN, espacios, mayúsculas).

Al inicio: validación de columnas en information_schema para detectar desvíos.
Cada sección envuelta en try/except; un fallo no aborta las demás.

Uso:
    DATABASE_URL=postgres://user:pass@host/db python scripts/diag/origen_skills_basura.py
"""
from __future__ import annotations

import getpass
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("psycopg2 no encontrado.  pip install psycopg2-binary")
    sys.exit(1)

# Import the SAME regex patterns from the extractor — do NOT copy them.
from load_microcurriculos import _TECH_KEYWORDS, _TRANSVERSAL_KEYWORDS
from api.market_sample import _MARKET_SAMPLE_CTE
from api.microcurriculo_filters import SQL_FILTRO_NO_PRUEBA, SQL_FILTRO_NO_PRUEBA_PARAMS
from api.skills_analysis_logic import (
    RUIDO_SIEMPRE,
    canonical_key,
    is_transversal,
    norm,
    process_job_skill_rows,
)

PROGRAM_IDS = [13, 9, 109, 1, 11]

# ── Columnas que el script usa; verificadas al inicio ─────────────────────────
# (tabla, columna)
_EXPECTED_COLUMNS: list[tuple[str, str]] = [
    ("microcurriculo_skills", "tipo_skill"),
    ("microcurriculo_skills", "skill_original"),
    ("microcurriculo_skills", "skill_normalized"),
    ("microcurriculo_skills", "skill_domain"),
    ("microcurriculos",       "clean_text"),
    ("microcurriculos",       "asignatura"),
    ("microcurriculos",       "specialization_id"),
    ("ml_program_job_matches", "especializacion_id"),
    ("ml_program_job_matches", "empleo_id"),
    ("ml_program_job_matches", "role_alignment"),
    ("ml_program_job_matches", "run_id"),
    ("jobs",                   "title"),
    ("jobs",                   "id"),
    ("jobs",                   "activo"),
]

# ── SQL de producción ─────────────────────────────────────────────────────────

_SQL_MARKET_SKILLS = f"""
    WITH {_MARKET_SAMPLE_CTE}
    SELECT ms.match_id,
           ms.empleo_id,
           jsonb_array_elements_text(ms.skills_empleo) AS skill
    FROM market_sample ms
    WHERE ms.especializacion_id = %s
      AND ms.skills_empleo IS NOT NULL
      AND jsonb_typeof(ms.skills_empleo) = 'array'
      AND ms.skills_empleo != '[]'::jsonb
"""

_SQL_PROG_SKILLS = f"""
    SELECT COALESCE(ms.skill_normalized, ms.skill_original) AS skill_name,
           COUNT(*) AS cobertura,
           ARRAY_REMOVE(ARRAY_AGG(DISTINCT m.asignatura), NULL) AS asignaturas
    FROM microcurriculo_skills ms
    JOIN microcurriculos m ON m.id = ms.microcurriculo_id
    WHERE m.specialization_id = %s
      AND COALESCE(ms.skill_normalized, ms.skill_original) IS NOT NULL
      {SQL_FILTRO_NO_PRUEBA}
    GROUP BY COALESCE(ms.skill_normalized, ms.skill_original)
    ORDER BY cobertura DESC
"""

# ── a) Origen de skills sospechosas ──────────────────────────────────────────

_SQL_SKILL_ORIGIN = f"""
    SELECT ms.skill_original,
           ms.skill_normalized,
           ms.tipo_skill,
           ms.skill_domain,
           m.asignatura,
           m.clean_text,
           m.id AS microcurriculo_id
    FROM microcurriculo_skills ms
    JOIN microcurriculos m ON m.id = ms.microcurriculo_id
    WHERE m.specialization_id = %s
      AND LOWER(COALESCE(ms.skill_normalized, ms.skill_original)) = LOWER(%s)
      {SQL_FILTRO_NO_PRUEBA}
    ORDER BY m.asignatura
"""

# ── c) Títulos de vacantes ────────────────────────────────────────────────────

_SQL_VACANTES_TITLES = f"""
    WITH {_MARKET_SAMPLE_CTE}
    SELECT j.title,
           COUNT(DISTINCT ms.empleo_id) AS n
    FROM market_sample ms
    JOIN jobs j ON j.id::text = ms.empleo_id
    WHERE ms.especializacion_id = %s
    GROUP BY j.title
    ORDER BY n DESC
    LIMIT 15
"""

_SQL_SAMPLE_RULE = """
    SELECT
        (SELECT MAX(run_id) FROM ml_program_job_matches WHERE especializacion_id = %s)
            AS latest_run_id,
        COUNT(DISTINCT m.empleo_id) AS total_matches_latest_run,
        COUNT(DISTINCT CASE WHEN m.role_alignment IS NOT NULL THEN m.empleo_id END)
            AS with_role_alignment,
        MIN(m.role_alignment) AS min_ra,
        MAX(m.role_alignment) AS max_ra,
        AVG(m.role_alignment)::numeric(5,3) AS avg_ra
    FROM ml_program_job_matches m
    WHERE m.especializacion_id = %s
      AND m.run_id = (SELECT MAX(run_id) FROM ml_program_job_matches WHERE especializacion_id = %s)
"""

# ── b) Raw market terms ───────────────────────────────────────────────────────

_SQL_RAW_MARKET_TERMS = f"""
    WITH {_MARKET_SAMPLE_CTE}
    SELECT jsonb_array_elements_text(ms.skills_empleo) AS raw_skill,
           COUNT(DISTINCT ms.empleo_id) AS n_jobs
    FROM market_sample ms
    WHERE ms.especializacion_id = %s
      AND ms.skills_empleo IS NOT NULL
      AND jsonb_typeof(ms.skills_empleo) = 'array'
    GROUP BY 1
    ORDER BY n_jobs DESC
    LIMIT 300
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _connect() -> "psycopg2.extensions.connection":
    db_url = os.environ.get("DATABASE_URL") or getpass.getpass(
        "DATABASE_URL (postgres://user:pass@host/db): "
    )
    conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.set_session(readonly=True, autocommit=True)
    return conn


def _fetch(cur, sql: str, params: tuple) -> list[dict]:
    cur.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def _shorten(s: str, n: int = 70) -> str:
    s = (s or "").replace("\n", " ").strip()
    return s[:n] + "…" if len(s) > n else s


def _extract_fragments(text: str, pattern: re.Pattern, window: int = 60) -> list[str]:
    """Return up to 3 ±window-char fragments around each regex match."""
    if not text:
        return []
    frags = []
    for m in pattern.finditer(text):
        start = max(0, m.start() - window)
        end   = min(len(text), m.end() + window)
        frags.append(f"…{text[start:end]}…")
        if len(frags) >= 3:
            break
    return frags


# Regex for standalone lowercase "r" only (no IGNORECASE, word boundary)
_LOWERCASE_R = re.compile(r"\br\b")
# Regex for uppercase "R" standalone or as part of RStudio, R Studio
_UPPERCASE_R = re.compile(r"\bR\b|\bRStudio\b|\bR\s+Studio\b")


def _classify_r_in_text(text: str) -> tuple[int, int]:
    """Return (n_lowercase_r, n_uppercase_r_or_rstudio) in text."""
    return (
        len(_LOWERCASE_R.findall(text or "")),
        len(_UPPERCASE_R.findall(text or "")),
    )


# ── Soft-skill / transversal detection ───────────────────────────────────────

# Terms that are genuinely soft skills / transversales — list separately, do NOT
# mark as "noise" in section B.
_SOFT_SKILLS_ES = {
    "liderazgo", "comunicacion", "trabajo en equipo", "innovacion",
    "creatividad", "adaptabilidad", "proactividad", "responsabilidad",
    "pensamiento critico", "resolucion de problemas", "toma de decisiones",
    "gestion", "planeacion", "emprendimiento", "etica", "negociacion",
    "presentacion", "orientacion a resultados", "orientacion al cliente",
}

# 3-letter tech acronyms that ARE real skills — do NOT filter out
_LEGIT_SHORT = {
    "sql", "bi", "ia", "aws", "gcp", "sap", "crm", "api", "etl", "elt",
    "erp", "pbi", "nlp", "pca", "git", "dbt", "r",
}

# Terms that are clearly NOT technical skills: managerial/generic nouns,
# verb phrases, adjective phrases, sentence fragments. Excludes soft skills
# (those go in transversales).
_NOISE_TERMS = {
    "financiero", "financiera", "gerencia", "presupuesto", "indicadores",
    "servicio", "servicio al cliente", "calidad", "mejora continua",
    "procesos", "resultados", "estrategia", "control", "seguimiento",
    "supervision", "ventas", "clientes", "mercado", "producto",
    "tecnologia", "sistemas", "soluciones", "herramientas",
    "informacion", "conocimiento", "experiencia", "habilidades",
    "competencias", "net",  # bare "net" without ".NET" / "dotnet" context
}


def _classify_market_term(raw: str) -> str | None:
    """
    Returns:
      "ruido_siempre"   — in RUIDO_SIEMPRE
      "transversal"     — a legitimate soft skill
      "no_skill"        — clearly not a technical skill
      None              — keep (looks like a real technical skill)
    """
    nk = norm(raw)
    if nk in RUIDO_SIEMPRE:
        return "ruido_siempre"
    if nk in _SOFT_SKILLS_ES or is_transversal(raw):
        return "transversal"
    # Very short non-acronym tokens
    tokens = nk.replace(" ", "")
    if len(tokens) <= 3 and nk not in _LEGIT_SHORT:
        return "no_skill"
    if nk in _NOISE_TERMS or canonical_key(raw) in _NOISE_TERMS:
        return "no_skill"
    return None


# ── Schema validation ─────────────────────────────────────────────────────────

_SQL_COLUMN_CHECK = """
    SELECT table_name, column_name
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND (table_name, column_name) = ANY(%s)
"""


def validate_schema(cur) -> set[tuple[str, str]]:
    """Return set of (table, column) pairs that DO NOT exist in the DB."""
    present_rows = _fetch(cur, _SQL_COLUMN_CHECK,
                          ([list(p) for p in _EXPECTED_COLUMNS],))
    present = {(r["table_name"], r["column_name"]) for r in present_rows}
    missing = set(_EXPECTED_COLUMNS) - present
    return missing


# ── Sección a) ────────────────────────────────────────────────────────────────

def seccion_a(cur) -> None:
    print("\n" + "=" * 72)
    print("SECCIÓN A — Origen de skills sospechosas en microcurrículos")
    print("=" * 72)
    print()
    print("Ruta de código:")
    print("  load_microcurriculos.py:_TECH_KEYWORDS  (re.IGNORECASE activo)")
    print("  Patrón R:              r'\\bR\\b'   → captura 'r' minúscula por IGNORECASE")
    print("  Patrón Clasificación:  r'Clasificaci[oó]n'")
    print()

    for prog_id in PROGRAM_IDS:
        print(f"\n--- Prog {prog_id} ---")
        for target in ("R", "Clasificación"):
            rows = _fetch(cur, _SQL_SKILL_ORIGIN,
                          (prog_id, target) + SQL_FILTRO_NO_PRUEBA_PARAMS)
            # Also try normalized lowercase form
            if not rows:
                rows = _fetch(cur, _SQL_SKILL_ORIGIN,
                              (prog_id, target.lower()) + SQL_FILTRO_NO_PRUEBA_PARAMS)

            print(f"\n  Skill: {target!r}  →  {len(rows)} filas en microcurriculo_skills")
            if not rows:
                continue

            seen_asig: dict[str, int] = {}
            for r in rows:
                a = r["asignatura"] or "(sin asignatura)"
                seen_asig[a] = seen_asig.get(a, 0) + 1
            print(f"  Asignaturas ({len(seen_asig)}): {list(seen_asig.items())[:8]}")

            tipos = {r["tipo_skill"] for r in rows}
            print(f"  tipo_skill: {tipos}")

            # Extract fragments from clean_text using the production regex
            all_frags: list[str] = []
            n_lower_r_total = 0
            n_upper_r_total = 0
            micros_checked = 0
            seen_micro: set[int] = set()

            for r in rows:
                mid = r["microcurriculo_id"]
                if mid in seen_micro:
                    continue
                seen_micro.add(mid)
                txt = r.get("clean_text") or ""
                if not txt:
                    continue
                micros_checked += 1

                # Fragments via SAME regex (_TECH_KEYWORDS from extractor)
                # For "R" we narrow the pattern to just R-related matches
                if target == "R":
                    pat = re.compile(r"\bR\b", re.IGNORECASE)
                    lo, up = _classify_r_in_text(txt)
                    n_lower_r_total += lo
                    n_upper_r_total += up
                else:
                    pat = re.compile(r"Clasificaci[oó]n", re.IGNORECASE)

                if len(all_frags) < 3:
                    frags = _extract_fragments(txt, pat, window=60)
                    all_frags.extend(frags)

            if all_frags:
                print(f"  Fragmentos en clean_text ({micros_checked} microcurrículos con texto):")
                for i, f in enumerate(all_frags[:3], 1):
                    print(f"    {i}. {_shorten(f, 130)!r}")
            else:
                print(f"  (clean_text vacío en los {micros_checked} microcurrículos con esta skill)")

            if target == "R":
                total_r = n_lower_r_total + n_upper_r_total
                print(f"  Conteo 'r' minúscula sola: {n_lower_r_total}  |  "
                      f"'R' mayúscula/RStudio: {n_upper_r_total}  |  "
                      f"total coincidencias IGNORECASE: {total_r}")
                if total_r > 0:
                    pct_lower = 100 * n_lower_r_total / total_r
                    print(f"  → {pct_lower:.1f}% son 'r' minúscula (probable falso positivo por IGNORECASE)")


# ── Sección b) ────────────────────────────────────────────────────────────────

def seccion_b(cur) -> None:
    print("\n" + "=" * 72)
    print("SECCIÓN B — Top términos de mercado que no son skills")
    print("=" * 72)

    # Aggregate across all programs
    all_items: dict[str, dict] = {}
    for prog_id in PROGRAM_IDS:
        try:
            rows = _fetch(cur, _SQL_RAW_MARKET_TERMS, (prog_id,))
        except Exception as e:
            print(f"  [Prog {prog_id} error] {e}")
            continue
        for r in rows:
            raw = r["raw_skill"] or ""
            label = _classify_market_term(raw)
            if label is None:
                continue
            ck = canonical_key(raw)
            key = (ck, label)
            if key not in all_items:
                all_items[key] = {"raw": raw, "canonical": ck,
                                  "label": label, "n_jobs": r["n_jobs"], "n_progs": 1}
            else:
                all_items[key]["n_jobs"] = max(all_items[key]["n_jobs"], r["n_jobs"])
                all_items[key]["n_progs"] += 1

    noise  = sorted([v for v in all_items.values() if v["label"] == "no_skill"],
                    key=lambda x: (-x["n_progs"], -x["n_jobs"]))
    ruido  = sorted([v for v in all_items.values() if v["label"] == "ruido_siempre"],
                    key=lambda x: (-x["n_progs"], -x["n_jobs"]))
    trans  = sorted([v for v in all_items.values() if v["label"] == "transversal"],
                    key=lambda x: (-x["n_progs"], -x["n_jobs"]))

    print(f"\n--- No-skills (verbos, adjetivos, fragmentos genéricos) [{len(noise)}] ---")
    print(f"{'Raw term':45s}  {'canonical':35s}  {'n_jobs':>7}  {'progs':>5}")
    print("-" * 100)
    for item in noise[:40]:
        print(f"{item['raw'][:44]:<45s}  {item['canonical'][:34]:<35s}  "
              f"{item['n_jobs']:>7}  {item['n_progs']:>5}")

    print(f"\n--- RUIDO_SIEMPRE [{len(ruido)}] ---")
    for item in ruido:
        print(f"  {item['raw']!r}  →  canonical={item['canonical']!r}  n_jobs={item['n_jobs']}")

    # Special: "net" vs ".NET"
    print("\n--- Variantes de 'net' por programa ---")
    for prog_id in PROGRAM_IDS:
        try:
            rows = _fetch(cur, _SQL_RAW_MARKET_TERMS, (prog_id,))
        except Exception as e:
            print(f"  [Prog {prog_id}] {e}")
            continue
        net_rows = [r for r in rows
                    if norm(r["raw_skill"]) in {"net", ".net", "dotnet",
                                                 "net framework", "asp net",
                                                 "asp.net", ".net framework"}]
        if net_rows:
            print(f"  Prog {prog_id}: {[(r['raw_skill'], r['n_jobs']) for r in net_rows]}")

    print(f"\n--- Transversales (soft skills legítimas, informativo) [{len(trans)}] ---")
    print(f"{'Raw term':45s}  {'n_jobs':>7}  {'progs':>5}")
    print("-" * 60)
    for item in trans[:30]:
        print(f"{item['raw'][:44]:<45s}  {item['n_jobs']:>7}  {item['n_progs']:>5}")


# ── Sección c) ────────────────────────────────────────────────────────────────

def seccion_c(cur) -> None:
    print("\n" + "=" * 72)
    print("SECCIÓN C — Vacantes de prog 109 y prog 9 (posible desalineamiento)")
    print("=" * 72)
    for prog_id in [109, 9]:
        try:
            rows_titles = _fetch(cur, _SQL_VACANTES_TITLES, (prog_id,))
            rows_rule   = _fetch(cur, _SQL_SAMPLE_RULE, (prog_id, prog_id, prog_id))
        except Exception as e:
            print(f"\n  [Prog {prog_id} error] {e}")
            continue
        rule = rows_rule[0] if rows_rule else {}
        print(f"\n  Prog {prog_id} — Regla de entrada _MARKET_SAMPLE_CTE:")
        print(f"    latest_run_id={rule.get('latest_run_id')}  "
              f"total_matches={rule.get('total_matches_latest_run')}  "
              f"con_role_alignment={rule.get('with_role_alignment')}")
        print(f"    role_alignment: min={rule.get('min_ra')}  "
              f"max={rule.get('max_ra')}  avg={rule.get('avg_ra')}")
        print(f"  Top 15 títulos de vacante:")
        for i, r in enumerate(rows_titles, 1):
            print(f"    {i:>2}. ({r['n']:>4}×) {_shorten(r['title'], 60)!r}")
        if rows_titles:
            top_n = sum(r["n"] for r in rows_titles)
            print(f"  → {len(rows_titles)} títulos únicos en top-15 acumulan {top_n} vacantes")


# ── Sección d) ────────────────────────────────────────────────────────────────

def _find_duplicates_prog(cur, prog_id: int) -> list[tuple[str, str, str]]:
    rows = _fetch(cur, _SQL_PROG_SKILLS, (prog_id,) + SQL_FILTRO_NO_PRUEBA_PARAMS)
    seen: dict[str, list[str]] = {}
    for r in rows:
        sk = r["skill_name"] or ""
        ck = canonical_key(sk)
        seen.setdefault(ck, []).append(sk)
    return [(ck, forms[0], forms[1])
            for ck, forms in seen.items() if len(forms) >= 2]


def _find_duplicates_market(cur, prog_id: int) -> list[tuple[str, str, str]]:
    rows = _fetch(cur, _SQL_RAW_MARKET_TERMS, (prog_id,))
    seen: dict[str, list[str]] = {}
    for r in rows:
        sk = r["raw_skill"] or ""
        ck = canonical_key(sk)
        seen.setdefault(ck, []).append(sk)
    return [(ck, forms[0], forms[1])
            for ck, forms in seen.items() if len(forms) >= 2]


def seccion_d(cur) -> None:
    print("\n" + "=" * 72)
    print("SECCIÓN D — Duplicados tras normalización")
    print("=" * 72)
    for prog_id in PROGRAM_IDS:
        try:
            dups_prog = _find_duplicates_prog(cur, prog_id)
            dups_mkt  = _find_duplicates_market(cur, prog_id)
        except Exception as e:
            print(f"\n  [Prog {prog_id} error] {e}")
            continue
        if dups_prog or dups_mkt:
            print(f"\n  Prog {prog_id}:")
        if dups_prog:
            print(f"  Programa ({len(dups_prog)} pares):")
            for ck, a, b in dups_prog[:15]:
                print(f"    canonical={ck!r}: {a!r} ↔ {b!r}")
        if dups_mkt:
            print(f"  Mercado ({len(dups_mkt)} pares):")
            for ck, a, b in dups_mkt[:15]:
                print(f"    canonical={ck!r}: {a!r} ↔ {b!r}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 72)
    print("Diagnóstico origen_skills_basura — graduate-intelligence-platform")
    print("=" * 72)
    conn = _connect()
    try:
        with conn.cursor() as cur:

            # ── Validación de esquema ─────────────────────────────────────────
            print("\n--- Validación de columnas en information_schema ---")
            try:
                missing = validate_schema(cur)
                if missing:
                    print("  ATENCIÓN: columnas no encontradas:")
                    for tbl, col in sorted(missing):
                        print(f"    {tbl}.{col}")
                else:
                    print("  OK — todas las columnas esperadas existen.")
            except Exception as e:
                print(f"  [validación error] {e}")

            # ── Secciones ─────────────────────────────────────────────────────
            try:
                seccion_a(cur)
            except Exception as e:
                print(f"\n[SECCIÓN A — ERROR]: {e}")

            try:
                seccion_b(cur)
            except Exception as e:
                print(f"\n[SECCIÓN B — ERROR]: {e}")

            try:
                seccion_c(cur)
            except Exception as e:
                print(f"\n[SECCIÓN C — ERROR]: {e}")

            try:
                seccion_d(cur)
            except Exception as e:
                print(f"\n[SECCIÓN D — ERROR]: {e}")

    finally:
        conn.close()

    print("\n" + "=" * 72)
    print("Fin del diagnóstico.")
    print("=" * 72)


if __name__ == "__main__":
    main()
