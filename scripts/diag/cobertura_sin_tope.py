"""
Diagnóstico de cobertura de skills de mercado sin tope artificial.

Ejecuta 4 variantes del procesamiento por programa:
  A — parámetros actuales (frequency_threshold + HARD_CAP=60)
  B — umbral 5% (ceil(0.05·n)), sin tope
  C — min_freq=2, sin tope
  D — min_freq=1, sin tope

Programas analizados: 13, 146, 1, 9, 11, 20, 109, 108

Chequeo de coherencia (valores esperados documentados):
  Programa 13  → variante A: 36.4% cobertura, 4 brechas, 7 fortalezas, 3 skills sin asig.
  Programa 146 → variante A: 77.8% cobertura, 14 brechas, 4 fortalezas, 2 skills sin asig.

Uso:
    python scripts/diag/cobertura_sin_tope.py

La contraseña de BD se solicita por getpass (nunca se imprime).
"""
from __future__ import annotations

import getpass
import math
import sys
from pathlib import Path

# ── asegura que el root del proyecto esté en sys.path ─────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("psycopg2 no encontrado. Instala con: pip install psycopg2-binary")
    sys.exit(1)

from api.skills_analysis_logic import (
    HARD_CAP,
    frequency_threshold,
    process_job_skill_rows,
)

# ── Programas a analizar ───────────────────────────────────────────────────────
PROGRAM_IDS = [13, 146, 1, 9, 11, 20, 109, 108]

# ── SQL copiado literalmente de api/market_sample.py y api/main.py ───────────
_MARKET_SAMPLE_CTE = """
    latest_runs AS (
        SELECT especializacion_id, MAX(run_id) AS run_id
        FROM ml_program_job_matches
        GROUP BY especializacion_id
    ),
    ranked AS (
        SELECT m.id               AS match_id,
               m.especializacion_id,
               m.empleo_id,
               m.skills_empleo,
               m.relevance_label,
               RANK() OVER (
                   PARTITION BY m.empleo_id
                   ORDER BY m.role_alignment DESC
               ) AS rnk
        FROM ml_program_job_matches m
        JOIN latest_runs lr
          ON lr.especializacion_id = m.especializacion_id
         AND lr.run_id = m.run_id
        JOIN jobs j ON j.id::text = m.empleo_id
        WHERE m.role_alignment IS NOT NULL
          AND m.empleo_id IS NOT NULL
          AND COALESCE(j.activo, TRUE) = TRUE
    ),
    market_sample AS (
        SELECT * FROM ranked WHERE rnk = 1
    )
"""

SQL_MARKET_SKILLS = f"""
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

SQL_PROG_SKILLS = """
    SELECT COALESCE(ms.skill_normalized, ms.skill_original) AS skill_name,
           COUNT(*) AS cobertura,
           ARRAY_REMOVE(ARRAY_AGG(DISTINCT m.asignatura), NULL) AS asignaturas
    FROM microcurriculo_skills ms
    JOIN microcurriculos m ON m.id = ms.microcurriculo_id
    WHERE m.specialization_id = %s
      AND COALESCE(ms.skill_normalized, ms.skill_original) IS NOT NULL
      AND NOT (
            COALESCE(m.source_document, '') ~* '^[A-Za-z]:[/\\\\]'
         OR COALESCE(m.source_document, '') ILIKE '%test_microcurric%'
         OR COALESCE(m.asignatura,      '') ILIKE 'PROGRAMA ACAD%'
      )
    GROUP BY COALESCE(ms.skill_normalized, ms.skill_original)
    ORDER BY cobertura DESC
"""


# ── Helpers ────────────────────────────────────────────────────────────────────

def _connect() -> "psycopg2.extensions.connection":
    db_host = input("DB host [localhost]: ").strip() or "localhost"
    db_port = input("DB port [5432]: ").strip() or "5432"
    db_name = input("DB name: ").strip()
    db_user = input("DB user: ").strip()
    db_pass = getpass.getpass("DB password: ")
    return psycopg2.connect(
        host=db_host,
        port=int(db_port),
        dbname=db_name,
        user=db_user,
        password=db_pass,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def _fetch_all(cur, sql: str, params: tuple) -> list[dict]:
    cur.execute(sql, params)
    return cur.fetchall()


def _program_skills_set(cur, program_id: int) -> set[str]:
    """Canonical keys of skills present in the program's microcurrículos."""
    from api.skills_analysis_logic import canonical_key
    rows = _fetch_all(cur, SQL_PROG_SKILLS, (program_id,))
    return {canonical_key(r["skill_name"]) for r in rows if r["skill_name"]}


def _run_variant(
    rows: list[dict],
    prog_skills: set[str],
    min_freq: int | None,
    hard_cap: int | None,
) -> dict:
    skills, n_matches = process_job_skill_rows(rows, min_freq=min_freq, hard_cap=hard_cap)
    from api.skills_analysis_logic import canonical_key
    mkt_keys = {canonical_key(s["skill"]) for s in skills}
    matched = mkt_keys & prog_skills
    pct = round(100 * len(matched) / len(mkt_keys), 1) if mkt_keys else 0.0
    brechas = mkt_keys - prog_skills
    fortalezas = prog_skills & mkt_keys
    sin_asig = brechas  # skills en mercado sin cobertura en microcurrículos
    return {
        "n_matches": n_matches,
        "n_skills_mkt": len(skills),
        "pct_cobertura": pct,
        "n_brechas": len(brechas),
        "n_fortalezas": len(fortalezas),
        "n_sin_asig": len(sin_asig),
        "threshold_used": min_freq if min_freq is not None else frequency_threshold(n_matches),
    }


def _coherence_check(prog_id: int, variant_a: dict) -> None:
    """Print coherence warnings for the two documented reference programs."""
    expected = {
        13:  {"pct_cobertura": 36.4, "n_brechas": 4, "n_fortalezas": 7, "n_sin_asig": 3},
        146: {"pct_cobertura": 77.8, "n_brechas": 14, "n_fortalezas": 4, "n_sin_asig": 2},
    }
    if prog_id not in expected:
        return
    ref = expected[prog_id]
    mismatches = [
        f"{k}: esperado {ref[k]}, obtenido {variant_a[k]}"
        for k in ref
        if variant_a[k] != ref[k]
    ]
    if mismatches:
        print(f"  ⚠ COHERENCIA [{prog_id}]: {'; '.join(mismatches)}")
    else:
        print(f"  ✓ coherencia OK [{prog_id}]")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("Diagnóstico cobertura sin tope — graduate-intelligence-platform")
    print("=" * 70)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            header = (
                f"{'Prog':>5}  {'Var':>3}  {'n_mkt':>6}  {'n_matches':>9}  "
                f"{'umbral':>6}  {'cobertura%':>10}  {'brechas':>7}  "
                f"{'fortalez':>8}  {'sin_asig':>8}"
            )
            print()
            print(header)
            print("-" * len(header))

            for prog_id in PROGRAM_IDS:
                rows = _fetch_all(cur, SQL_MARKET_SKILLS, (prog_id,))
                prog_skills = _program_skills_set(cur, prog_id)
                n_raw = len(rows)

                n_matches_approx = len({str(r["match_id"]) for r in rows})
                thr_actual = frequency_threshold(n_matches_approx)

                variants = {
                    "A": _run_variant(rows, prog_skills, None, HARD_CAP),
                    "B": _run_variant(rows, prog_skills, math.ceil(0.05 * n_matches_approx) if n_matches_approx else 1, None),
                    "C": _run_variant(rows, prog_skills, 2, None),
                    "D": _run_variant(rows, prog_skills, 1, None),
                }

                for var_name, v in variants.items():
                    print(
                        f"{prog_id:>5}  {var_name:>3}  {v['n_skills_mkt']:>6}  "
                        f"{v['n_matches']:>9}  {v['threshold_used']:>6}  "
                        f"{v['pct_cobertura']:>10.1f}  {v['n_brechas']:>7}  "
                        f"{v['n_fortalezas']:>8}  {v['n_sin_asig']:>8}"
                    )

                _coherence_check(prog_id, variants["A"])
                print()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
