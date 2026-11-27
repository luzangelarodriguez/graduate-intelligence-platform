"""
Diagnóstico de origen de skills "basura" en microcurrículos y mercado.

Secciones:
  a) Skills "R" y "Clasificación" — asignaturas/microcurrículos origen, fragmentos de texto
  b) Top 40 términos de mercado que no son una skill
  c) Prog 109 y 9 — títulos de las 15 vacantes más frecuentes y regla de entrada
  d) Duplicados por normalización (singular/plural, ES/EN, espacios, mayúsculas)

Uso:
    DATABASE_URL=postgres://user:pass@host/db python scripts/diag/origen_skills_basura.py
"""
from __future__ import annotations

import getpass
import os
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

from api.market_sample import _MARKET_SAMPLE_CTE
from api.microcurriculo_filters import SQL_FILTRO_NO_PRUEBA, SQL_FILTRO_NO_PRUEBA_PARAMS
from api.skills_analysis_logic import (
    RUIDO_SIEMPRE,
    canonical_key,
    cross_analyze,
    is_transversal,
    norm,
    norm_match,
    process_job_skill_rows,
)

PROGRAM_IDS = [13, 9, 109, 1, 11]

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

# ── a) Origen de skills sospechosas en microcurrículos ───────────────────────

_SQL_SKILL_ORIGIN = f"""
    SELECT ms.skill_original,
           ms.skill_normalized,
           ms.skill_type,
           ms.context_snippet,
           m.asignatura,
           m.source_document,
           m.id AS microcurriculo_id
    FROM microcurriculo_skills ms
    JOIN microcurriculos m ON m.id = ms.microcurriculo_id
    WHERE m.specialization_id = %s
      AND LOWER(COALESCE(ms.skill_normalized, ms.skill_original)) = LOWER(%s)
      {SQL_FILTRO_NO_PRUEBA}
    ORDER BY m.asignatura
"""

# ── c) Títulos de vacantes para un programa ───────────────────────────────────

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

# Regla de entrada de _MARKET_SAMPLE_CTE para diagnóstico
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

# ── b) Raw market terms before filtering ─────────────────────────────────────

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


def _is_non_skill(raw: str) -> bool:
    """
    Heuristic: a market token is probably NOT a skill if it:
    - Is a single common word (verb, adjective, noun fragment)
    - Or is a suffix/fragment without technical specificity
    """
    nk = norm(raw)
    ck = canonical_key(raw)
    # single very short token (1-3 chars) unless it's a known acronym
    if len(nk.replace(" ", "")) <= 3 and nk not in {"sql", "bi", "ia", "r"}:
        return True
    # common Spanish/generic fragments
    NON_SKILLS = {
        "atencion", "orientacion", "orientacion a resultados", "financiero",
        "financiera", "gerencia", "presupuesto", "indicadores", "net",
        "servicio", "servicio al cliente", "calidad", "mejora continua",
        "procesos", "resultados", "innovacion", "estrategia", "planeacion",
        "organizacion", "control", "seguimiento", "supervision",
        "ventas", "negociacion", "clientes", "mercado", "producto",
        "tecnologia", "sistemas", "soluciones", "herramientas",
        "informacion", "conocimiento", "experiencia", "habilidades",
        "competencias", "trabajo en equipo", "comunicacion", "liderazgo",
        "adaptabilidad", "proactividad", "responsabilidad", "creatividad",
    }
    return nk in NON_SKILLS or ck in NON_SKILLS


# ── Sección a) ────────────────────────────────────────────────────────────────

def seccion_a(cur, prog_id: int, target_skill: str) -> None:
    rows = _fetch(cur, _SQL_SKILL_ORIGIN,
                  (prog_id, target_skill) + SQL_FILTRO_NO_PRUEBA_PARAMS)
    print(f"\n  Skill: {target_skill!r}  →  {len(rows)} filas en microcurriculo_skills")
    if not rows:
        return
    seen_asig: dict[str, int] = {}
    for r in rows:
        a = r["asignatura"] or "(sin asignatura)"
        seen_asig[a] = seen_asig.get(a, 0) + 1
    print(f"  Asignaturas ({len(seen_asig)}): {list(seen_asig.items())[:10]}")
    # up to 3 context snippets
    snippets = [r for r in rows if r.get("context_snippet")][:3]
    for i, r in enumerate(snippets, 1):
        print(f"  Snippet {i} ({r['asignatura']!r}, {r['skill_type']!r}): "
              f"{_shorten(r['context_snippet'], 80)!r}")
    if not snippets:
        print("  (sin context_snippet registrado — skill extraída sin fragmento)")
    types = {r["skill_type"] for r in rows}
    print(f"  Tipos de skill: {types}")


# ── Sección b) ────────────────────────────────────────────────────────────────

def seccion_b(cur, prog_id: int) -> list[dict]:
    """Return raw market terms classified as non-skills for this program."""
    rows = _fetch(cur, _SQL_RAW_MARKET_TERMS, (prog_id,))
    non_skills = []
    for r in rows:
        raw = r["raw_skill"]
        nk = norm(raw)
        if nk in RUIDO_SIEMPRE:
            stage = "RUIDO_SIEMPRE"
        elif _is_non_skill(raw):
            stage = "no-skill-heuristica"
        else:
            continue
        non_skills.append({
            "raw": raw,
            "canonical": canonical_key(raw),
            "n_jobs": r["n_jobs"],
            "stage": stage,
        })
    return non_skills


# ── Sección c) ────────────────────────────────────────────────────────────────

def seccion_c(cur, prog_id: int) -> None:
    rows_titles = _fetch(cur, _SQL_VACANTES_TITLES, (prog_id,))
    rows_rule = _fetch(cur, _SQL_SAMPLE_RULE, (prog_id, prog_id, prog_id))
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


# ── Sección d) ────────────────────────────────────────────────────────────────

def seccion_d_prog(cur, prog_id: int) -> list[tuple[str, str, str]]:
    """Find duplicate pairs after normalization within program skills."""
    rows = _fetch(cur, _SQL_PROG_SKILLS, (prog_id,) + SQL_FILTRO_NO_PRUEBA_PARAMS)
    seen: dict[str, list[str]] = {}
    for r in rows:
        sk = r["skill_name"] or ""
        ck = canonical_key(sk)
        seen.setdefault(ck, []).append(sk)
    return [(ck, forms[0], forms[1])
            for ck, forms in seen.items() if len(forms) >= 2]


def seccion_d_market(cur, prog_id: int) -> list[tuple[str, str, str]]:
    """Find duplicate pairs after normalization in raw market terms."""
    rows = _fetch(cur, _SQL_RAW_MARKET_TERMS, (prog_id,))
    seen: dict[str, list[str]] = {}
    for r in rows:
        sk = r["raw_skill"] or ""
        ck = canonical_key(sk)
        seen.setdefault(ck, []).append(sk)
    return [(ck, forms[0], forms[1])
            for ck, forms in seen.items() if len(forms) >= 2]


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 72)
    print("Diagnóstico origen_skills_basura — graduate-intelligence-platform")
    print("=" * 72)
    conn = _connect()
    try:
        with conn.cursor() as cur:

            # ── Sección a) ────────────────────────────────────────────────────
            print("\n" + "=" * 72)
            print("SECCIÓN A — Origen de skills sospechosas en microcurrículos")
            print("=" * 72)
            print()
            print("Ruta de código:")
            print("  load_microcurriculos.py:_TECH_KEYWORDS  →  línea 28")
            print("  Patrón: r'\\bR\\b' captura la letra R como skill 'tecnologia'")
            print("  'Clasificación': r'Clasificaci[oó]n' en _TECH_KEYWORDS línea 36")
            print()
            for prog_id in PROGRAM_IDS:
                print(f"\n--- Prog {prog_id} ---")
                seccion_a(cur, prog_id, "R")
                seccion_a(cur, prog_id, "Clasificación")
                # Also check normalized form
                seccion_a(cur, prog_id, "clasificacion")

            # ── Sección b) ────────────────────────────────────────────────────
            print("\n" + "=" * 72)
            print("SECCIÓN B — Top términos de mercado que no son skills")
            print("=" * 72)

            # Aggregate across all programs
            all_non_skills: dict[str, dict] = {}
            for prog_id in PROGRAM_IDS:
                for item in seccion_b(cur, prog_id):
                    ck = item["canonical"]
                    if ck not in all_non_skills:
                        all_non_skills[ck] = item.copy()
                        all_non_skills[ck]["n_progs"] = 1
                    else:
                        all_non_skills[ck]["n_jobs"] = max(
                            all_non_skills[ck]["n_jobs"], item["n_jobs"]
                        )
                        all_non_skills[ck]["n_progs"] += 1

            sorted_ns = sorted(all_non_skills.values(),
                               key=lambda x: (-x["n_progs"], -x["n_jobs"]))
            print(f"\n{'Raw term':45s}  {'canonical':35s}  {'n_jobs':>7}  {'stage'}")
            print("-" * 110)
            for item in sorted_ns[:40]:
                print(f"{item['raw'][:44]:<45s}  {item['canonical'][:34]:<35s}  "
                      f"{item['n_jobs']:>7}  {item['stage']}")

            # Special: "net" vs ".NET"
            print("\n  Nota sobre 'net':")
            for prog_id in PROGRAM_IDS:
                rows = _fetch(cur, _SQL_RAW_MARKET_TERMS, (prog_id,))
                net_rows = [r for r in rows
                            if norm(r["raw_skill"]) in {"net", ".net", "dotnet",
                                                         "net framework", "asp net"}]
                if net_rows:
                    print(f"  Prog {prog_id}: {[(r['raw_skill'], r['n_jobs']) for r in net_rows]}")

            # ── Sección c) ────────────────────────────────────────────────────
            print("\n" + "=" * 72)
            print("SECCIÓN C — Vacantes de prog 109 y prog 9 (posible desalineamiento)")
            print("=" * 72)
            for prog_id in [109, 9]:
                seccion_c(cur, prog_id)

            # ── Sección d) ────────────────────────────────────────────────────
            print("\n" + "=" * 72)
            print("SECCIÓN D — Duplicados tras normalización")
            print("=" * 72)
            for prog_id in PROGRAM_IDS:
                dups_prog = seccion_d_prog(cur, prog_id)
                dups_mkt  = seccion_d_market(cur, prog_id)
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

    finally:
        conn.close()

    print("\n" + "=" * 72)
    print("Fin del diagnóstico.")
    print("=" * 72)


if __name__ == "__main__":
    main()
