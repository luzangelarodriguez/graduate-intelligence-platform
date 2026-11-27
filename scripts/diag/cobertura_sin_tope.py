"""
Diagnóstico de cobertura de skills de mercado sin tope artificial.

Ejecuta 4 variantes del procesamiento por programa usando la misma lógica
de producción (process_job_skill_rows + cross_analyze):
  A — parámetros actuales (frequency_threshold + hard_cap=HARD_CAP=60)
  B — umbral 5% (ceil(0.05·n)), sin tope
  C — min_freq=2, sin tope
  D — min_freq=1, sin tope

Programas analizados: 13, 146, 1, 9, 11, 20, 109, 108

Coherencia esperada (variante A):
  Programa 13  → 36.4% cobertura / 4 fortalezas / 7 brechas / 3 críticas
  Programa 146 → 77.8% cobertura / 14 fortalezas / 4 brechas / 2 críticas
Si la variante A no coincide, se imprime ADVERTENCIA y las otras variantes
de ese programa se marcan como no comparables.

Métricas reportadas:
  n_skills_mkt  — skills de mercado tras el corte
  n_matches     — vacantes únicas en la muestra
  umbral        — frecuencia mínima aplicada
  cob_simple    — cobertura_pct de cross_analyze (fortalezas / no-transversales)
  cob_pond      — cobertura ponderada por demanda (ver cobertura_ponderada())
  fortalezas    — len(cross["fortalezas"])
  brechas       — len(cross["brechas"])
  criticas      — len(cross["brechas_criticas"])
  pct_menc_fuera — % menciones totales que el corte A deja fuera vs variante D

Uso:
    DATABASE_URL=postgres://user:pass@host/db python scripts/diag/cobertura_sin_tope.py
    # o sin variable → pide la URL completa por getpass
"""
from __future__ import annotations

import getpass
import math
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
    print("psycopg2 no encontrado.  Instala con:  pip install psycopg2-binary")
    sys.exit(1)

from api.market_sample import _MARKET_SAMPLE_CTE
from api.microcurriculo_filters import SQL_FILTRO_NO_PRUEBA, SQL_FILTRO_NO_PRUEBA_PARAMS
from api.skills_analysis_logic import (
    HARD_CAP,
    cross_analyze,
    frequency_threshold,
    process_job_skill_rows,
)

# ── Programas ──────────────────────────────────────────────────────────────────
PROGRAM_IDS = [13, 146, 1, 9, 11, 20, 109, 108]

# ── SQL copiado literalmente de api/main.py (mismos f-strings de producción) ──
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


# ── Función pura: cobertura ponderada por demanda ──────────────────────────────

def cobertura_ponderada(fortalezas: list[dict], brechas: list[dict]) -> float:
    """
    Cobertura ponderada por demanda de mercado.

    = suma(frecuencia_mercado de fortalezas) /
      suma(frecuencia_mercado de fortalezas + brechas)  × 100

    Refleja qué fracción de las MENCIONES totales del mercado el programa cubre,
    no solo el recuento de skills distintas.
    Returns 0.0 when both lists are empty.
    """
    total_fortalezas = sum(f.get("frecuencia_mercado", 0) for f in fortalezas)
    total_brechas = sum(b.get("frecuencia_mercado", 0) for b in brechas)
    total = total_fortalezas + total_brechas
    if total == 0:
        return 0.0
    return round(total_fortalezas / total * 100, 1)


def pct_menciones_fuera_del_corte(
    skills_a: list[dict], skills_d: list[dict]
) -> float:
    """
    Porcentaje de menciones totales (sum de frecuencias) que el corte A
    deja fuera comparado con D (sin tope, min_freq=1).

    = 1 − (sum frecuencias en A) / (sum frecuencias en D)  × 100

    Cuando D está vacío devuelve 0.0.
    """
    sum_a = sum(s["frecuencia"] for s in skills_a)
    sum_d = sum(s["frecuencia"] for s in skills_d)
    if sum_d == 0:
        return 0.0
    return round((1 - sum_a / sum_d) * 100, 1)


# ── Conexión ──────────────────────────────────────────────────────────────────

def _connect() -> "psycopg2.extensions.connection":
    db_url = os.environ.get("DATABASE_URL") or getpass.getpass(
        "DATABASE_URL (postgres://user:pass@host/db): "
    )
    conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
    conn.set_session(readonly=True, autocommit=True)
    return conn


def _fetch_all(cur, sql: str, params: tuple) -> list[dict]:
    cur.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


# ── Construcción de skills_programa igual que producción ─────────────────────

def _build_prog_skills(cur, program_id: int) -> list[dict]:
    rows = _fetch_all(cur, _SQL_PROG_SKILLS, (program_id,) + SQL_FILTRO_NO_PRUEBA_PARAMS)
    result = []
    for r in rows:
        if not r["skill_name"]:
            continue
        asigs = list(r["asignaturas"]) if r["asignaturas"] else []
        raw_count = int(r["cobertura"])
        cobertura = len(asigs) if asigs else (1 if raw_count > 0 else 0)
        result.append({
            "skill":       r["skill_name"],
            "asignaturas": asigs,
            "cobertura":   cobertura,
        })
    return result


# ── Variante única ────────────────────────────────────────────────────────────

def _run_variant(
    rows: list[dict],
    prog_skills: list[dict],
    min_freq: int | None,
    hard_cap: int | None,
) -> dict:
    skills_mkt, n_matches = process_job_skill_rows(rows, min_freq=min_freq, hard_cap=hard_cap)
    cross = cross_analyze(skills_mkt, prog_skills, n_matches)
    return {
        "skills_mkt":  skills_mkt,
        "n_skills_mkt": len(skills_mkt),
        "n_matches":   n_matches,
        "threshold":   min_freq if min_freq is not None else frequency_threshold(n_matches),
        "cob_simple":  cross["cobertura_pct"],
        "cob_pond":    cobertura_ponderada(cross["fortalezas"], cross["brechas"]),
        "fortalezas":  len(cross["fortalezas"]),
        "brechas":     len(cross["brechas"]),
        "criticas":    len(cross["brechas_criticas"]),
    }


# ── Coherencia ────────────────────────────────────────────────────────────────

COHERENCIA_ESPERADA: dict[int, dict] = {
    13:  {"cob_simple": 36.4, "fortalezas": 4, "brechas": 7, "criticas": 3},
    146: {"cob_simple": 77.8, "fortalezas": 14, "brechas": 4, "criticas": 2},
}


def _coherence_ok(prog_id: int, va: dict) -> bool:
    if prog_id not in COHERENCIA_ESPERADA:
        return True
    ref = COHERENCIA_ESPERADA[prog_id]
    mismatches = [
        f"  {k}: esperado {ref[k]}, obtenido {va[k]}"
        for k in ref
        if va[k] != ref[k]
    ]
    if mismatches:
        print(f"  ⚠ ADVERTENCIA coherencia [{prog_id}] — variante A no coincide:")
        for m in mismatches:
            print(m)
        print(f"  Las demás variantes de prog {prog_id} NO son comparables con producción.")
        return False
    print(f"  ✓ coherencia OK [{prog_id}]")
    return True


# ── Cabecera de tabla ──────────────────────────────────────────────────────────

_HDR = (
    f"{'Prog':>5}  {'Var':>3}  {'n_mkt':>5}  {'n_vac':>5}  "
    f"{'umbral':>6}  {'cob%':>6}  {'pond%':>6}  "
    f"{'ftal':>4}  {'brec':>4}  {'crit':>4}  {'fuera%':>7}"
)
_SEP = "-" * len(_HDR)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("Diagnóstico cobertura sin tope — graduate-intelligence-platform")
    print("=" * 70)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            print()
            print(_HDR)
            print(_SEP)

            for prog_id in PROGRAM_IDS:
                rows = _fetch_all(cur, _SQL_MARKET_SKILLS, (prog_id,))
                prog_skills = _build_prog_skills(cur, prog_id)

                n_approx = len({str(r["match_id"]) for r in rows})
                thr_b = math.ceil(0.05 * n_approx) if n_approx else 1

                va = _run_variant(rows, prog_skills, None, HARD_CAP)
                vb = _run_variant(rows, prog_skills, thr_b, None)
                vc = _run_variant(rows, prog_skills, 2, None)
                vd = _run_variant(rows, prog_skills, 1, None)

                fuera_a = pct_menciones_fuera_del_corte(va["skills_mkt"], vd["skills_mkt"])
                fuera_b = pct_menciones_fuera_del_corte(vb["skills_mkt"], vd["skills_mkt"])
                fuera_c = pct_menciones_fuera_del_corte(vc["skills_mkt"], vd["skills_mkt"])

                for var_name, v, fuera in [
                    ("A", va, fuera_a),
                    ("B", vb, fuera_b),
                    ("C", vc, fuera_c),
                    ("D", vd, 0.0),
                ]:
                    print(
                        f"{prog_id:>5}  {var_name:>3}  {v['n_skills_mkt']:>5}  "
                        f"{v['n_matches']:>5}  {v['threshold']:>6}  "
                        f"{v['cob_simple']:>6.1f}  {v['cob_pond']:>6.1f}  "
                        f"{v['fortalezas']:>4}  {v['brechas']:>4}  "
                        f"{v['criticas']:>4}  {fuera:>7.1f}"
                    )

                _coherence_ok(prog_id, va)
                print()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
