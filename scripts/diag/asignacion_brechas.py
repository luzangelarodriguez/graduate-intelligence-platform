"""Diagnóstico de asignación de brechas a asignaturas para un programa.

Lee de la base de datos (solo lectura) y muestra, por cada brecha crítica del
programa, las asignaturas asignadas con su puntaje, y la lista de brechas sin
asignatura natural.

NO llama a OpenAI. NO modifica datos.

Uso:
    DATABASE_URL=postgres://... python scripts/diag/asignacion_brechas.py --program 13
    python scripts/diag/asignacion_brechas.py --program 13   # pide DATABASE_URL por stdin
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psycopg2
import psycopg2.extras

from api.microcurriculo_filters import SQL_FILTRO_NO_PRUEBA
from api.redesign_assignment import assign_brechas


# ── SQL — copiado literalmente de api/main.py con alias 'fetch_all' ───────────

def _fetch(cur, sql: str, params: tuple = ()) -> list[dict]:
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _run(program_id: int, conn) -> None:
    with conn.cursor() as cur:
        # 1. Microcurrículos del programa (filtro filas de prueba)
        mc_rows = _fetch(
            cur,
            f"""
            SELECT m.id, m.asignatura, m.clean_text,
                   COALESCE(m.asignatura, m.source_document) AS nombre
            FROM microcurriculos m
            WHERE m.specialization_id = %s
              AND m.clean_text IS NOT NULL
              AND length(m.clean_text) > 50
              {SQL_FILTRO_NO_PRUEBA}
            ORDER BY m.asignatura NULLS LAST
            """,
            (program_id,),
        )
        print(f"\nPrograma {program_id}: {len(mc_rows)} asignaturas (filas de prueba excluidas)")

        if not mc_rows:
            print("  Sin microcurrículos — verifica que el programa existe y tiene datos.")
            return

        # 2. Análisis de mercado — replica _market_analysis_for_program de api/main.py
        from api.market_sample import _MARKET_SAMPLE_CTE

        # Copiado de api/main.py ~L1000-1025
        _SQL_MARKET_SKILLS = f"""
            {_MARKET_SAMPLE_CTE}
            SELECT
                jsonb_array_elements_text(ms.skills_empleo) AS skill_raw,
                ms.match_id
            FROM market_sample ms
        """
        _SQL_MARKET_SIZE = f"""
            {_MARKET_SAMPLE_CTE}
            SELECT COUNT(*) AS n_jobs
            FROM market_sample ms
            WHERE ms.especializacion_id = %s
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

        market_rows = _fetch(cur, _SQL_MARKET_SKILLS)
        prog_rows   = _fetch(cur, _SQL_PROG_SKILLS, (program_id,))
        size_row    = _fetch(cur, _SQL_MARKET_SIZE, (program_id,))
        n_jobs      = int((size_row[0]["n_jobs"] if size_row else 0) or 0)

        print(f"  Mercado: {n_jobs} vacantes · {len(market_rows)} skill-rows · "
              f"{len(prog_rows)} skills del programa")

        # Replicar process_job_skill_rows + cross_analyze
        from api.skills_analysis_logic import process_job_skill_rows, cross_analyze
        market_skills, n_matches = process_job_skill_rows(market_rows)
        analysis = cross_analyze(market_skills, prog_rows, n_matches)

        brechas_criticas = analysis.get("brechas_criticas", [])
        all_brechas      = analysis.get("brechas", [])

        print(f"  n_matches={n_matches}  brechas={len(all_brechas)}  "
              f"brechas_criticas={len(brechas_criticas)}")

        if not brechas_criticas:
            print("  Sin brechas críticas — el programa cubre bien las skills del mercado.")
            return

        # 3. Asignación
        mc_list = [
            {
                "id":         r["id"],
                "asignatura": r.get("nombre") or r.get("asignatura"),
                "nombre":     r.get("nombre") or r.get("asignatura"),
                "clean_text": (r.get("clean_text") or "").strip(),
            }
            for r in mc_rows
        ]
        result = assign_brechas(mc_list, brechas_criticas)
        per_asig  = result["per_asignatura"]
        sin_asig  = result["brechas_sin_asignatura"]

        # 4. Imprimir resultado
        print(f"\n{'─'*60}")
        print(f"  BRECHAS CRÍTICAS: {len(brechas_criticas)}")
        print(f"{'─'*60}")

        for brecha in brechas_criticas:
            skill = brecha["skill"]
            freq  = brecha.get("frecuencia_mercado", "?")
            print(f"\n  Brecha: '{skill}'  (frecuencia mercado: {freq})")

            asigs_con_esta_brecha = [
                (mid, item)
                for mid, item in per_asig.items()
                if any(b["skill"] == skill for b in item["brechas_asignadas"])
            ]
            if asigs_con_esta_brecha:
                for mid, item in asigs_con_esta_brecha:
                    score = next(
                        b["score"]
                        for b in item["brechas_asignadas"]
                        if b["skill"] == skill
                    )
                    print(f"    → [{mid}] {item['asignatura']}  score={score:.1f}")
            else:
                print("    → (sin asignatura asignada)")

        if sin_asig:
            print(f"\n{'─'*60}")
            print(f"  BRECHAS SIN ASIGNATURA NATURAL ({len(sin_asig)}):")
            for b in sin_asig:
                print(f"    · {b['skill']}  (frecuencia: {b.get('frecuencia_mercado', '?')})")
        else:
            print("\n  Todas las brechas críticas tienen asignatura asignada.")

        print(f"\n{'─'*60}")
        print(f"  Asignaturas con propuestas: {len(per_asig)}")
        for mid, item in sorted(per_asig.items()):
            bnames = [b["skill"] for b in item["brechas_asignadas"]]
            print(f"    [{mid}] {item['asignatura']}: {bnames}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--program", type=int, required=True, help="ID del programa (especialización)")
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL") or getpass.getpass("DATABASE_URL: ")
    conn = psycopg2.connect(db_url)
    conn.set_session(readonly=True, autocommit=True)

    try:
        _run(args.program, conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
