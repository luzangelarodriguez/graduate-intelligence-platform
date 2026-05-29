from __future__ import annotations

import json
import os
import re
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from sync_to_railway import connect, get_local_config, get_railway_config, load_dotenv_files


ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"

LABOR_TABLE_CANDIDATES = [
    "empleos",
    "empleo_skills",
    "job_offers",
    "labor_jobs",
    "labor_market_gold",
    "canonical_jobs",
    "silver_normalized_jobs",
    "gold_validated_jobs",
    "ml_program_job_matches",
    "labor_program_skill_matches",
    "vw_match_empleo_especializacion_positivo",
    "vw_latest_ml_program_job_matches",
    "vw_labor_program_job_matches",
]


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text.lower())
    return " ".join(text.split())


def fetch_all(conn, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def fetch_one(conn, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    rows = fetch_all(conn, query, params)
    return rows[0] if rows else {}


def relation_exists(conn, name: str) -> bool:
    return bool(fetch_one(conn, "SELECT to_regclass(%s) IS NOT NULL AS exists", (f"public.{name}",)).get("exists"))


def count_relation(conn, name: str) -> int | None:
    if not relation_exists(conn, name):
        return None
    return int(fetch_one(conn, f'SELECT COUNT(*) AS total FROM public."{name}"').get("total", 0) or 0)


def safe_query(conn, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    try:
        return fetch_all(conn, query, params)
    except Exception:
        conn.rollback()
        return []


def diagnose(conn) -> dict[str, Any]:
    table_counts = {name: count_relation(conn, name) for name in LABOR_TABLE_CANDIDATES}
    core_counts = {
        "especializaciones": count_relation(conn, "especializaciones"),
        "skills": count_relation(conn, "skills"),
        "especializacion_skills": count_relation(conn, "especializacion_skills"),
    }

    labor_skill_summary = {}
    if relation_exists(conn, "empleo_skills"):
        labor_skill_summary = fetch_one(
            conn,
            """
            SELECT
                COUNT(*)::int AS total_rows,
                COUNT(DISTINCT empleo_id)::int AS jobs_with_skills,
                COUNT(DISTINCT skill_id)::int AS distinct_skill_ids,
                COUNT(*) FILTER (WHERE skill_id IS NULL)::int AS rows_without_skill_id,
                COUNT(DISTINCT lower(COALESCE(skill_normalized, skill_original, '')))::int AS distinct_normalized_names
            FROM public.empleo_skills
            """,
        )

    view_match_counts = {}
    for relation in ("vw_labor_program_job_matches", "vw_latest_ml_program_job_matches", "vw_match_empleo_especializacion_positivo"):
        if relation_exists(conn, relation):
            view_match_counts[relation] = fetch_one(
                conn,
                f"""
                SELECT
                    COUNT(*)::int AS rows,
                    COUNT(DISTINCT especializacion_id)::int AS programs_with_matches,
                    COUNT(DISTINCT empleo_id)::int AS related_jobs,
                    ROUND(AVG(porcentaje_match)::numeric, 2) AS avg_match
                FROM public.{relation}
                WHERE skills_en_comun >= 1
                """,
            )
        else:
            view_match_counts[relation] = None

    programs_zero = safe_query(
        conn,
        """
        WITH metrics AS (
            SELECT especializacion_id, COUNT(DISTINCT empleo_id)::int AS total
            FROM public.vw_labor_program_job_matches
            GROUP BY especializacion_id
        )
        SELECT e.id, e.nombre, COALESCE(m.total, 0)::int AS total_empleos_relacionados
        FROM public.especializaciones e
        LEFT JOIN metrics m ON m.especializacion_id = e.id
        WHERE COALESCE(m.total, 0) = 0
        ORDER BY e.nombre
        LIMIT 50
        """,
    )

    curricular_skills = safe_query(
        conn,
        """
        SELECT s.id, s.nombre, COUNT(DISTINCT es.especializacion_id)::int AS programas
        FROM public.skills s
        JOIN public.especializacion_skills es ON es.skill_id = s.id
        GROUP BY s.id, s.nombre
        ORDER BY programas DESC, s.nombre
        """,
    )
    labor_skills = safe_query(
        conn,
        """
        SELECT
            COALESCE(s.id, es.skill_id) AS skill_id,
            COALESCE(s.nombre, es.skill_normalized, es.skill_original) AS nombre,
            COUNT(DISTINCT es.empleo_id)::int AS empleos
        FROM public.empleo_skills es
        LEFT JOIN public.skills s ON s.id = es.skill_id
        GROUP BY COALESCE(s.id, es.skill_id), COALESCE(s.nombre, es.skill_normalized, es.skill_original)
        ORDER BY empleos DESC, nombre
        """,
    )
    labor_keys = {normalize_text(row.get("nombre", "")) for row in labor_skills if row.get("nombre")}
    skills_without_labor_match = [
        row for row in curricular_skills if normalize_text(row.get("nombre", "")) not in labor_keys
    ][:10]

    sample_programs = {}
    for expected in (
        "Visual Analytics y Big Data",
        "Inteligencia Artificial Aplicada",
        "Dirección y Gestión de Tecnologías de la Información",
    ):
        rows = safe_query(
            conn,
            """
            SELECT e.id, e.nombre, COALESCE(m.total, 0)::int AS total_empleos_relacionados,
                   COALESCE(m.avg_match, 0)::numeric AS promedio_match_mercado
            FROM public.especializaciones e
            LEFT JOIN (
                SELECT especializacion_id,
                       COUNT(DISTINCT empleo_id)::int AS total,
                       ROUND(AVG(porcentaje_match)::numeric, 2) AS avg_match
                FROM public.vw_labor_program_job_matches
                GROUP BY especializacion_id
            ) m ON m.especializacion_id = e.id
            WHERE lower(unaccent(e.nombre)) LIKE lower(unaccent(%s))
            ORDER BY e.nombre
            LIMIT 5
            """,
            (f"%{expected}%",),
        )
        sample_programs[expected] = rows

    likely_causes = []
    if not table_counts.get("empleos") and not table_counts.get("canonical_jobs") and not table_counts.get("silver_normalized_jobs"):
        likely_causes.append("No hay tabla laboral con vacantes cargadas.")
    if relation_exists(conn, "empleo_skills") and labor_skill_summary.get("total_rows", 0) == 0:
        likely_causes.append("empleo_skills existe pero está vacía.")
    if labor_skill_summary.get("rows_without_skill_id", 0) and labor_skill_summary.get("distinct_skill_ids", 0) == 0:
        likely_causes.append("Las skills laborales no tienen skill_id; los joins exactos contra skills.id devuelven cero.")
    if not relation_exists(conn, "vw_labor_program_job_matches"):
        likely_causes.append("No existe la vista puente vw_labor_program_job_matches.")
    if view_match_counts.get("vw_labor_program_job_matches") and view_match_counts["vw_labor_program_job_matches"].get("rows", 0) == 0:
        likely_causes.append("La tabla puente existe pero no tiene matches calculados.")

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "core_counts": core_counts,
        "labor_table_counts": table_counts,
        "labor_skill_summary": labor_skill_summary,
        "view_match_counts": view_match_counts,
        "programs_with_zero_jobs": programs_zero,
        "top_10_curricular_skills_without_labor_match": skills_without_labor_match,
        "sample_programs": sample_programs,
        "likely_causes": likely_causes,
    }


def write_outputs(payload: dict[str, Any]) -> None:
    OUTPUTS.mkdir(exist_ok=True)
    (OUTPUTS / "labor_matching_diagnosis.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    lines = [
        "# Labor Matching Diagnosis",
        "",
        f"Generated at: {payload['generated_at']}",
        "",
        "## Core counts",
        "",
    ]
    for key, value in payload["core_counts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Labor table counts", ""])
    for key, value in payload["labor_table_counts"].items():
        label = "missing" if value is None else value
        lines.append(f"- {key}: {label}")
    lines.extend(["", "## Match views", ""])
    for key, value in payload["view_match_counts"].items():
        lines.append(f"- {key}: {value if value is not None else 'missing'}")
    lines.extend(["", "## Likely causes", ""])
    if payload["likely_causes"]:
        lines.extend(f"- {item}" for item in payload["likely_causes"])
    else:
        lines.append("- No blocking cause detected in aggregate counts.")
    lines.extend(["", "## Programs with 0 related jobs", ""])
    for row in payload["programs_with_zero_jobs"][:25]:
        lines.append(f"- {row.get('id')} | {row.get('nombre')} | {row.get('total_empleos_relacionados')}")
    lines.extend(["", "## Top curricular skills without labor match", ""])
    for row in payload["top_10_curricular_skills_without_labor_match"]:
        lines.append(f"- {row.get('nombre')} ({row.get('programas')} programas)")

    (OUTPUTS / "labor_matching_diagnosis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    load_dotenv_files()
    target = os.getenv("DIAGNOSE_DB_TARGET", "railway").lower()
    config = get_local_config() if target == "local" else get_railway_config()
    with connect(config) as conn:
        conn.autocommit = False
        payload = diagnose(conn)
    write_outputs(payload)
    print(json.dumps({
        "target": target,
        "outputs": [
            str(OUTPUTS / "labor_matching_diagnosis.md"),
            str(OUTPUTS / "labor_matching_diagnosis.json"),
        ],
        "likely_causes": payload["likely_causes"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

