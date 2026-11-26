"""Diagnóstico de cobertura con/sin filas de prueba — SOLO LECTURA.

Uso:
    DATABASE_URL=postgres://... python scripts/diag/cobertura_sin_pruebas.py

    Si DATABASE_URL no está en el entorno, el script la pide por getpass
    (nunca se imprime en pantalla).

Calcula para los programas 13, 108 y 146 la cobertura DOS veces usando la
lógica EXACTA de producción (_market_analysis_for_program en api/main.py):

    (a) con TODAS las filas — debe reproducir los números en producción
    (b) excluyendo filas de prueba

Criterio "fila de prueba" (microcurriculos.id que se excluye):
    - source_document coincide con r'^[A-Za-z]:\\\\' (ruta Windows local)
    - source_document contiene "test_microcurric" (case-insensitive)
    - asignatura empieza por "PROGRAMA ACAD" (case-insensitive)

Para el programa 108 imprime además id, asignatura y source_document
de cada fila sospechosa.

Chequeo de coherencia (aborta (b) si (a) no coincide con producción):
    Programa  13: 45.5 % · 5 fort · 6 brechas · 2 críticas
    Programa 146: 77.8 % · 14 fort · 4 brechas · 2 críticas (control limpio)

No escribe nada en la base de datos (sesión de solo lectura).
"""
from __future__ import annotations

import getpass
import os
import re
import sys
from pathlib import Path

# ── Raíz del proyecto en PYTHONPATH ──────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psycopg2

# ── Importaciones de producción ───────────────────────────────────────────────
# api.market_sample sólo define la constante _MARKET_SAMPLE_CTE, importa limpio.
from api.market_sample import _MARKET_SAMPLE_CTE            # api/market_sample.py
from api.skills_analysis_logic import cross_analyze, process_job_skill_rows

# ── SQL copiado LITERALMENTE de producción ────────────────────────────────────
# Fuente: api/main.py L987-1016 (rama main, commit actual).
# NO modificar — cualquier cambio rompe la equivalencia con producción.

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
"""  # api/main.py:987-997

_SQL_MARKET_SIZE = f"""
    WITH {_MARKET_SAMPLE_CTE}
    SELECT COUNT(DISTINCT ms.empleo_id)::int AS n_vacantes_muestra
    FROM market_sample ms
    WHERE ms.especializacion_id = %s
"""  # api/main.py:999-1004

_SQL_PROG_SKILLS = """
    SELECT COALESCE(ms.skill_normalized, ms.skill_original) AS skill_name,
           COUNT(*) AS cobertura,
           ARRAY_REMOVE(ARRAY_AGG(DISTINCT m.asignatura), NULL) AS asignaturas
    FROM microcurriculo_skills ms
    JOIN microcurriculos m ON m.id = ms.microcurriculo_id
    WHERE m.specialization_id = %s
      AND COALESCE(ms.skill_normalized, ms.skill_original) IS NOT NULL
    GROUP BY COALESCE(ms.skill_normalized, ms.skill_original)
    ORDER BY cobertura DESC
"""  # api/main.py:1006-1016

# Variante para (b): _SQL_PROG_SKILLS + filtro de exclusión por id.
# Se usa sólo cuando excluir_ids es no vacío (NOT IN vacío es error SQL).
_SQL_PROG_SKILLS_SIN_PRUEBAS = """
    SELECT COALESCE(ms.skill_normalized, ms.skill_original) AS skill_name,
           COUNT(*) AS cobertura,
           ARRAY_REMOVE(ARRAY_AGG(DISTINCT m.asignatura), NULL) AS asignaturas
    FROM microcurriculo_skills ms
    JOIN microcurriculos m ON m.id = ms.microcurriculo_id
    WHERE m.specialization_id = %s
      AND COALESCE(ms.skill_normalized, ms.skill_original) IS NOT NULL
      AND m.id NOT IN %s
    GROUP BY COALESCE(ms.skill_normalized, ms.skill_original)
    ORDER BY cobertura DESC
"""

# ── Parámetros ────────────────────────────────────────────────────────────────
PROGRAMAS = [13, 108, 146]

# Valores esperados en producción para el chequeo de coherencia.
# Si (a) difiere, se imprime advertencia y NO se presenta (b) como válido.
_ESPERADOS: dict[int, dict] = {
    13:  {"cob": 45.5, "fort": 5,  "brech": 6, "crit": 2},
    146: {"cob": 77.8, "fort": 14, "brech": 4, "crit": 2},
}

# Criterios de test
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


# ── Helper de fetch ───────────────────────────────────────────────────────────

def _fetch(cur, sql: str, params: tuple) -> list[dict]:
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


# ── Réplica exacta de _market_analysis_for_program (api/main.py:1019-1059) ───

def _run_analysis(cur, prog_id: int, excluir_ids: set[int]) -> dict:
    """
    Replica _market_analysis_for_program con los mismos pasos y parámetros.
    Si excluir_ids es no vacío, usa _SQL_PROG_SKILLS_SIN_PRUEBAS para (b).
    La consulta de mercado no cambia (no depende de microcurriculos).
    """
    # Mercado — idéntico en (a) y (b)
    raw_rows   = _fetch(cur, _SQL_MARKET_SKILLS, (prog_id,))
    size_rows  = _fetch(cur, _SQL_MARKET_SIZE,   (prog_id,))
    n_vacantes_muestra = int(size_rows[0]["n_vacantes_muestra"]) if size_rows else 0

    skills_mercado_raw, n_matches = process_job_skill_rows(
        [{"match_id": r["match_id"], "skill": r["skill"]} for r in raw_rows]
    )

    # Prog skills — (a) usa SQL original; (b) añade NOT IN
    if excluir_ids:
        prog_rows = _fetch(cur, _SQL_PROG_SKILLS_SIN_PRUEBAS,
                           (prog_id, tuple(excluir_ids)))
    else:
        prog_rows = _fetch(cur, _SQL_PROG_SKILLS, (prog_id,))

    skills_programa = [
        {
            "skill":       r["skill_name"],
            "cobertura":   int(r["cobertura"]),
            "asignaturas": list(r["asignaturas"]) if r["asignaturas"] else [],
        }
        for r in prog_rows
        if r["skill_name"]
    ]

    skills_mercado = [{"skill": s["skill"], "frecuencia": s["frecuencia"]}
                      for s in skills_mercado_raw]
    analysis = cross_analyze(skills_mercado, skills_programa, n_matches)
    analysis["n_vacantes_muestra"] = n_vacantes_muestra
    return analysis


# ── Veredicto: réplica de UMBRALES_VEREDICTO (frontend, ObservatorioStorytelling.tsx) ──
# AC=50, AK=6, FC=75, FK=3 — mismo que _veredictoSinGuardia en el frontend.

def _veredicto(cobertura: float, n_criticas: int) -> str:
    if cobertura < 50 or n_criticas >= 6:
        return "Actualizar"
    if cobertura < 75 or n_criticas >= 3:
        return "Fortalecer"
    return "Mantener"


def _print_result(label: str, analysis: dict) -> None:
    cob  = analysis["cobertura_pct"]
    fort = len(analysis["fortalezas"])
    brch = len(analysis["brechas"])
    crit = len(analysis["brechas_criticas"])
    evid = analysis.get("evidencia_baja", False)
    verd = _veredicto(cob, crit)
    print(f"  {label}:")
    print(f"    cobertura_pct    : {cob:.1f} %")
    print(f"    fortalezas       : {fort}")
    print(f"    brechas          : {brch}")
    print(f"    brechas_criticas : {crit}")
    print(f"    evidencia_baja   : {evid}")
    print(f"    veredicto        : {verd}  [réplica UMBRALES_VEREDICTO frontend]")


def _skills_set(analysis: dict) -> set[str]:
    return (
        {s["skill"] for s in analysis["fortalezas"]}
        | {s["skill"] for s in analysis["brechas"]}
    )


def _coherencia_ok(prog_id: int, ana: dict) -> bool:
    """Devuelve True si (a) reproduce los valores esperados en producción."""
    if prog_id not in _ESPERADOS:
        return True
    exp = _ESPERADOS[prog_id]
    cob  = round(ana["cobertura_pct"], 1)
    fort = len(ana["fortalezas"])
    brch = len(ana["brechas"])
    crit = len(ana["brechas_criticas"])
    return cob == exp["cob"] and fort == exp["fort"] and brch == exp["brech"] and crit == exp["crit"]


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

            # Identificar filas de prueba
            micro_rows = _fetch(
                cur,
                "SELECT id, asignatura, source_document "
                "FROM microcurriculos WHERE specialization_id = %s",
                (prog_id,),
            )
            test_rows = [r for r in micro_rows if _es_prueba(r["source_document"], r["asignatura"])]
            test_ids  = {r["id"] for r in test_rows}

            print(f"\nTotal microcurriculos : {len(micro_rows)}")
            print(f"Filas de prueba       : {len(test_rows)}  ids={sorted(test_ids)}")

            if prog_id == 108 and test_rows:
                print("\n  Fila(s) sospechosa(s) programa 108:")
                for r in test_rows:
                    print(f"    id={r['id']} | asignatura={r['asignatura']!r} | "
                          f"source_document={r['source_document']!r}")

            # ── (a) Todas las filas ──────────────────────────────────────────
            ana_all = _run_analysis(cur, prog_id, excluir_ids=set())
            print()
            _print_result("(a) TODAS las filas", ana_all)

            # Chequeo de coherencia
            if prog_id in _ESPERADOS:
                if _coherencia_ok(prog_id, ana_all):
                    print(f"\n  ✓ Coherencia OK — (a) reproduce producción.")
                else:
                    exp = _ESPERADOS[prog_id]
                    print(
                        f"\n  ADVERTENCIA: (a) NO reproduce producción.\n"
                        f"    Esperado : {exp['cob']:.1f} % · {exp['fort']} fort · "
                        f"{exp['brech']} brechas · {exp['crit']} críticas\n"
                        f"    Obtenido : {ana_all['cobertura_pct']:.1f} % · "
                        f"{len(ana_all['fortalezas'])} fort · "
                        f"{len(ana_all['brechas'])} brechas · "
                        f"{len(ana_all['brechas_criticas'])} críticas\n"
                        f"  (b) no se presenta como válido hasta resolver la discrepancia."
                    )
                    continue

            # ── (b) Sin pruebas ──────────────────────────────────────────────
            if not test_ids:
                print(f"\n  (sin filas de prueba; (b) == (a))")
                if prog_id == 146:
                    print("  ✓ Control limpio verificado: (a) == (b).")
                continue

            ana_clean = _run_analysis(cur, prog_id, excluir_ids=test_ids)
            print()
            _print_result("(b) SIN filas de prueba", ana_clean)

            if prog_id == 146:
                # Control: debe ser idéntico
                if _skills_set(ana_all) == _skills_set(ana_clean):
                    print("  ✓ Control limpio verificado: (a) == (b).")
                else:
                    print("  ADVERTENCIA: programa 146 inesperadamente tiene skills distintos en (b).")

            # Skills que desaparecen / aparecen
            sk_all   = _skills_set(ana_all)
            sk_clean = _skills_set(ana_clean)
            desaparecen = sk_all   - sk_clean
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
