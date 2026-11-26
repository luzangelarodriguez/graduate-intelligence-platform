"""Diagnóstico de cobertura con/sin filas de prueba — SOLO LECTURA.

Uso:
    DATABASE_URL=postgres://... python scripts/diag/cobertura_sin_pruebas.py

    Si DATABASE_URL no está en el entorno, el script la pide por getpass
    (nunca se imprime en pantalla).

Calcula para los programas 13 y 108 la cobertura DOS veces usando la
misma lógica de producción (cross_analyze / find_prog_match importados
desde api.skills_analysis_logic):

    (a) con TODAS las filas de microcurriculo_skills
    (b) excluyendo filas de prueba

Criterio "fila de prueba" (microcurriculos.id que se excluye):
    - source_document coincide con r'^[A-Za-z]:\\\\' (ruta Windows local)
    - source_document contiene "test_microcurric" (case-insensitive)
    - asignatura empieza por "PROGRAMA ACAD" (case-insensitive)

Para el programa 108 imprime además id, asignatura y source_document
de la fila sospechosa.

No escribe nada en la base de datos (sesión de solo lectura).
"""
from __future__ import annotations

import getpass
import os
import re
import sys
import textwrap
from pathlib import Path

# ── Añade la raíz del proyecto al PYTHONPATH para importar api.*  ────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psycopg2
import psycopg2.extras

from api.skills_analysis_logic import cross_analyze, process_job_skill_rows

# ── Parámetros ────────────────────────────────────────────────────────────────
PROGRAMAS = [13, 108]

# Criterios de test (aplicados sobre microcurriculos)
_RE_RUTA_LOCAL = re.compile(r"^[A-Za-z]:\\", re.IGNORECASE)
_RE_TEST_DOC   = re.compile(r"test_microcurric", re.IGNORECASE)
_RE_PROG_ACAD  = re.compile(r"^PROGRAMA\s+ACAD", re.IGNORECASE)


def _es_prueba(source_document: str | None, asignatura: str | None) -> bool:
    sd = source_document or ""
    ag = asignatura or ""
    return (
        bool(_RE_RUTA_LOCAL.match(sd))
        or bool(_RE_TEST_DOC.search(sd))
        or bool(_RE_PROG_ACAD.match(ag))
    )


# ── SQL ───────────────────────────────────────────────────────────────────────
_SQL_MICRO = """
    SELECT m.id,
           m.asignatura,
           m.source_document,
           COALESCE(ms.skill_normalized, ms.skill_original) AS skill_name,
           COUNT(*)  OVER (PARTITION BY
               COALESCE(ms.skill_normalized, ms.skill_original)
           )::int AS cobertura,
           ARRAY_REMOVE(
               ARRAY_AGG(DISTINCT m.asignatura)
               OVER (PARTITION BY COALESCE(ms.skill_normalized, ms.skill_original)),
               NULL
           ) AS asignaturas
    FROM microcurriculo_skills ms
    JOIN microcurriculos m ON m.id = ms.microcurriculo_id
    WHERE m.specialization_id = %s
      AND COALESCE(ms.skill_normalized, ms.skill_original) IS NOT NULL
"""

# Para el mercado usamos la misma CTE de producción (simplificada aquí:
# skills de matches de alta/media afinidad, igual que _SQL_MARKET_SKILLS)
_SQL_MARKET = """
    SELECT sm.empleo_id AS match_id,
           s.skill
    FROM skill_matches sm
    JOIN skills s ON s.id = sm.skill_id
    JOIN matches m ON m.id = sm.match_id
    WHERE m.especializacion_id = %s
      AND m.relevance_label IN ('high', 'medium')
      AND s.skill IS NOT NULL
"""

# n_matches para evidencia_baja
_SQL_N_MATCHES = """
    SELECT COUNT(DISTINCT m.id) AS n_matches
    FROM matches m
    WHERE m.especializacion_id = %s
      AND m.relevance_label IN ('high', 'medium')
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch(cur: psycopg2.extensions.cursor, sql: str, params: tuple) -> list[dict]:
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _build_prog_skills(rows: list[dict]) -> list[dict]:
    """Deduplica prog_skills como hace _SQL_PROG_SKILLS en producción."""
    seen: dict[str, dict] = {}
    for r in rows:
        sk = r["skill_name"]
        if sk not in seen:
            seen[sk] = {"skill": sk, "cobertura": r["cobertura"], "asignaturas": list(r["asignaturas"] or [])}
    return list(seen.values())


def _run_analysis(cur, prog_id: int, excluir_ids: set[int]) -> dict:
    """Calcula cobertura excluyendo los microcurriculo.id en excluir_ids."""
    raw_rows = _fetch(cur, _SQL_MICRO, (prog_id,))

    if excluir_ids:
        raw_rows = [r for r in raw_rows if r["id"] not in excluir_ids]

    prog_skills = _build_prog_skills(raw_rows)

    mkt_rows = _fetch(cur, _SQL_MARKET, (prog_id,))
    market_input = [{"match_id": r["match_id"], "skill": r["skill"]} for r in mkt_rows]
    skills_mercado_raw, n_matches = process_job_skill_rows(market_input)
    skills_mercado = [{"skill": s["skill"], "frecuencia": s["frecuencia"]} for s in skills_mercado_raw]

    n_matches_row = _fetch(cur, _SQL_N_MATCHES, (prog_id,))
    n_matches_total = int((n_matches_row[0]["n_matches"]) if n_matches_row else 0)

    analysis = cross_analyze(skills_mercado, prog_skills, n_matches_total)
    return analysis


def _veredicto(cobertura: float, n_criticas: int) -> str:
    if cobertura < 50 or n_criticas >= 6:
        return "Actualizar"
    if cobertura < 75 or n_criticas >= 3:
        return "Fortalecer"
    return "Mantener"


def _print_result(label: str, analysis: dict) -> None:
    cob   = analysis["cobertura_pct"]
    fort  = len(analysis["fortalezas"])
    brech = len(analysis["brechas"])
    crit  = len(analysis["brechas_criticas"])
    evid  = analysis.get("evidencia_baja", False)
    verd  = _veredicto(cob, crit)
    print(f"  {label}:")
    print(f"    cobertura_pct    : {cob:.1f} %")
    print(f"    fortalezas       : {fort}")
    print(f"    brechas          : {brech}")
    print(f"    brechas_criticas : {crit}")
    print(f"    evidencia_baja   : {evid}")
    print(f"    veredicto        : {verd}")


def _skills_set(analysis: dict) -> set[str]:
    return {s["skill"] for s in analysis["fortalezas"]} | {s["skill"] for s in analysis["brechas"]}


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    db_url = os.environ.get("DATABASE_URL") or getpass.getpass("DATABASE_URL: ")

    conn = psycopg2.connect(db_url)
    conn.set_session(readonly=True, autocommit=True)

    with conn.cursor() as cur:
        for prog_id in PROGRAMAS:
            print(f"\n{'='*60}")
            print(f"PROGRAMA {prog_id}")
            print("="*60)

            # Identificar filas de prueba en microcurriculos
            micro_rows = _fetch(
                cur,
                "SELECT id, asignatura, source_document FROM microcurriculos WHERE specialization_id = %s",
                (prog_id,),
            )
            test_rows = [r for r in micro_rows if _es_prueba(r["source_document"], r["asignatura"])]
            test_ids  = {r["id"] for r in test_rows}

            print(f"\nTotal microcurriculos : {len(micro_rows)}")
            print(f"Filas de prueba       : {len(test_rows)}  ids={sorted(test_ids)}")

            if prog_id == 108 and test_rows:
                print("\n  Fila(s) sospechosa(s) programa 108:")
                for r in test_rows:
                    print(f"    id={r['id']} | asignatura={r['asignatura']!r} | source_document={r['source_document']!r}")

            # Análisis (a) — todas las filas
            ana_all = _run_analysis(cur, prog_id, excluir_ids=set())

            # Análisis (b) — sin pruebas
            if test_ids:
                ana_clean = _run_analysis(cur, prog_id, excluir_ids=test_ids)
            else:
                ana_clean = ana_all
                print("  (sin filas de prueba; (b) == (a))")

            print()
            _print_result("(a) TODAS las filas", ana_all)
            print()
            _print_result("(b) SIN filas de prueba", ana_clean)

            # Skills que desaparecen en (b)
            if test_ids:
                sk_all   = _skills_set(ana_all)
                sk_clean = _skills_set(ana_clean)
                desaparecen = sk_all - sk_clean
                aparecen    = sk_clean - sk_all
                print()
                if desaparecen:
                    print(f"  Skills que DESAPARECEN en (b) [{len(desaparecen)}]:")
                    for sk in sorted(desaparecen):
                        print(f"    - {sk}")
                else:
                    print("  Sin skills que desaparezcan en (b).")
                if aparecen:
                    print(f"  Skills NUEVAS en (b) [{len(aparecen)}]:")
                    for sk in sorted(aparecen):
                        print(f"    + {sk}")

    conn.close()
    print("\nDiagnóstico completado (solo lectura).")


if __name__ == "__main__":
    main()
