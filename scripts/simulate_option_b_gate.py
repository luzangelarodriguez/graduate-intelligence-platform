#!/usr/bin/env python3
"""
Simula el impacto de la Opción B (gate de skills de dominio) sobre
ml_program_job_matches ANTES de aplicar el UPDATE masivo.

Ejecutar:
    python scripts/simulate_option_b_gate.py

Salida:
  - Totales del sistema: cuántas filas medium/high cambiarían a low/no_match
  - Desglose por programa
  - Lista detallada de los casos que cambiarían (para revisión)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env.local")
except ImportError:
    pass

_GENERIC_SKILLS: frozenset = frozenset({
    "comunicacion",
    "gestion",
    "liderazgo",
    "trabajo en equipo",
    "toma de decisiones",
    "orientacion a resultados",
    "pensamiento critico",
    "resolucion de problemas",
    "pensamiento analitico",
    "calidad",
    "servicio",
    "atencion",
    "experiencia",
    "manejo",
    "office",
})
_DOMAIN_SKILL_GATE = 2


def domain_skills_count(common: list[str]) -> int:
    return sum(1 for s in common if s.lower() not in _GENERIC_SKILLS)


def simulated_label(score: float, n_common: int, common: list[str],
                    current_label: str) -> str:
    n_domain = domain_skills_count(common)
    gate_ok = n_domain >= _DOMAIN_SKILL_GATE
    # Thresholds from academic_relevance_engine constants
    SCORE_HIGH   = 48.0
    SCORE_MEDIUM = 40.0
    SCORE_LOW    = 30.0
    if score >= SCORE_HIGH and n_common >= 2 and gate_ok:
        return "high"
    if score >= SCORE_MEDIUM and n_common >= 1 and gate_ok:
        return "medium"
    if score >= SCORE_LOW and n_common >= 1:
        return "low"
    return "no_match"


def main() -> None:
    conn = psycopg2.connect(
        os.environ["RAILWAY_DATABASE_URL"],
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    cur = conn.cursor()

    # Only look at active matches that are currently medium or high
    cur.execute("""
        SELECT
            m.id,
            m.especializacion_id,
            m.empleo_id,
            m.job_title,
            m.score_match,
            m.relevance_label,
            m.skills_en_comun,
            COALESCE(e.nombre, '(sin nombre)') AS programa
        FROM ml_program_job_matches m
        LEFT JOIN especializaciones e ON e.id = m.especializacion_id
        WHERE m.relevance_label IN ('high', 'medium')
        ORDER BY m.especializacion_id, m.score_match DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    total_checked = len(rows)
    degraded: list[dict] = []

    for row in rows:
        common = row["skills_en_comun"]
        if isinstance(common, str):
            common = json.loads(common or "[]")
        common = common or []
        new_label = simulated_label(
            float(row["score_match"]),
            len(common),
            common,
            row["relevance_label"],
        )
        if new_label != row["relevance_label"]:
            degraded.append({
                "id": row["id"],
                "especializacion_id": row["especializacion_id"],
                "programa": row["programa"],
                "empleo_id": row["empleo_id"],
                "job_title": row["job_title"],
                "score": float(row["score_match"]),
                "label_before": row["relevance_label"],
                "label_after": new_label,
                "n_common": len(common),
                "n_domain": domain_skills_count(common),
                "common": common,
            })

    # ── Resumen global ────────────────────────────────────────────────────────
    print("=" * 72)
    print("SIMULACIÓN OPCIÓN B — impacto en todo el sistema")
    print("=" * 72)
    print(f"  Filas medium/high revisadas:   {total_checked:>6}")
    print(f"  Filas que cambiarían de label: {len(degraded):>6}"
          f"  ({len(degraded)/max(total_checked,1)*100:.1f}%)")
    by_transition: dict[str, int] = {}
    for d in degraded:
        key = f"{d['label_before']} → {d['label_after']}"
        by_transition[key] = by_transition.get(key, 0) + 1
    for k, v in sorted(by_transition.items()):
        print(f"    {k}: {v}")

    # ── Por programa ──────────────────────────────────────────────────────────
    print()
    print("Por programa (solo programas con cambios):")
    print(f"  {'esp_id':>6}  {'programa':45}  {'cambian':>7}  {'de_total':>8}")
    by_prog: dict[int, dict] = {}
    for d in degraded:
        pid = d["especializacion_id"]
        if pid not in by_prog:
            by_prog[pid] = {"nombre": d["programa"], "n": 0}
        by_prog[pid]["n"] += 1
    # total per program (from all rows)
    total_per_prog: dict[int, int] = {}
    for row in rows:
        pid = row["especializacion_id"]
        total_per_prog[pid] = total_per_prog.get(pid, 0) + 1
    for pid, info in sorted(by_prog.items(), key=lambda x: -x[1]["n"]):
        print(f"  {pid:>6}  {info['nombre'][:45]:45}  {info['n']:>7}  "
              f"{total_per_prog.get(pid, 0):>8}")

    # ── Detalle de los primeros 30 casos que cambian ──────────────────────────
    print()
    print("Detalle — primeros 30 casos que cambiarían (ordenados por programa, score desc):")
    print(f"  {'esp_id':>6}  {'emp_id':>7}  {'score':>6}  "
          f"{'antes':>8}  {'después':>8}  {'n_dom':>6}  "
          f"{'skills_comunes / no-genéricas'}")
    for d in sorted(degraded, key=lambda x: (-x["especializacion_id"], -x["score"]))[:30]:
        non_gen = [s for s in d["common"] if s.lower() not in _GENERIC_SKILLS]
        print(f"  {d['especializacion_id']:>6}  {d['empleo_id']:>7}  "
              f"{d['score']:>6.2f}  {d['label_before']:>8}  {d['label_after']:>8}  "
              f"{d['n_domain']:>6}  {d['common'][:5]}  non-gen={non_gen[:3]}")

    # ── UPDATE SQL para aplicar si se aprueba ────────────────────────────────
    print()
    print("=" * 72)
    print("UPDATE a aplicar si se aprueba (copiar y ejecutar con psycopg2):")
    print("=" * 72)
    print("""
GENERIC_SKILLS = {
    'comunicacion', 'gestion', 'liderazgo', 'trabajo en equipo',
    'toma de decisiones', 'orientacion a resultados', 'pensamiento critico',
    'resolucion de problemas', 'pensamiento analitico', 'calidad',
    'servicio', 'atencion', 'experiencia', 'manejo', 'office',
}

# Downgrade medium→low for matches with < 2 domain skills
cur.execute(\"\"\"
    UPDATE ml_program_job_matches
    SET relevance_label = 'low',
        updated_at      = now()
    WHERE relevance_label = 'medium'
      AND (
          SELECT COUNT(*)
          FROM jsonb_array_elements_text(skills_en_comun) AS s
          WHERE lower(s) NOT IN (
              'comunicacion','gestion','liderazgo','trabajo en equipo',
              'toma de decisiones','orientacion a resultados','pensamiento critico',
              'resolucion de problemas','pensamiento analitico','calidad',
              'servicio','atencion','experiencia','manejo','office'
          )
      ) < 2
\"\"\")
print("medium→low rows:", cur.rowcount)

# Downgrade high→low for matches with < 2 domain skills
cur.execute(\"\"\"
    UPDATE ml_program_job_matches
    SET relevance_label = 'low',
        updated_at      = now()
    WHERE relevance_label = 'high'
      AND (
          SELECT COUNT(*)
          FROM jsonb_array_elements_text(skills_en_comun) AS s
          WHERE lower(s) NOT IN (
              'comunicacion','gestion','liderazgo','trabajo en equipo',
              'toma de decisiones','orientacion a resultados','pensamiento critico',
              'resolucion de problemas','pensamiento analitico','calidad',
              'servicio','atencion','experiencia','manejo','office'
          )
      ) < 2
\"\"\")
print("high→low rows:", cur.rowcount)
conn.commit()
""")


if __name__ == "__main__":
    main()
