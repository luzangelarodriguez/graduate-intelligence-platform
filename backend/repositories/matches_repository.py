from __future__ import annotations

from typing import Any

from backend.repositories.base import fetch_all, fetch_one, pick_relation, relation_has_rows


def match_relation_name(*, db_name: str | None = None) -> str | None:
    for name in ("vw_labor_program_job_matches", "vw_latest_ml_program_job_matches", "vw_match_empleo_especializacion_positivo"):
        if relation_has_rows(name, db_name=db_name):
            return name
    return pick_relation(("vw_match_empleo_especializacion_positivo",), db_name=db_name)


def fetch_ml_program_metric_rows(relation: str, *, db_name: str | None = None) -> list[dict[str, Any]]:
    return fetch_all(
        f"""
        SELECT
            especializacion_id,
            ROUND(AVG(porcentaje_match)::numeric, 2) AS promedio_match_mercado,
            ROUND(MAX(porcentaje_match)::numeric, 2) AS max_match_mercado,
            COUNT(DISTINCT empleo_id)::int AS total_empleos_relacionados
        FROM {relation}
        WHERE porcentaje_match > 0
        GROUP BY especializacion_id
        """,
        db_name=db_name,
    )


def fetch_match_rows_for_program(
    relation: str,
    especializacion_id: int,
    *,
    limit: int | None = 10,
    db_name: str | None = None,
) -> list[dict[str, Any]]:
    limit_sql = "LIMIT %s" if limit is not None else ""
    params: tuple[Any, ...] = (especializacion_id, limit) if limit is not None else (especializacion_id,)
    return fetch_all(
        f"""
        SELECT
            empleo_id,
            titulo_empleo,
            total_skills_empleo,
            total_skills_especializacion,
            skills_en_comun,
            porcentaje_match
        FROM {relation}
        WHERE especializacion_id = %s
          AND skills_en_comun >= 1
        ORDER BY porcentaje_match DESC, skills_en_comun DESC, titulo_empleo
        {limit_sql}
        """,
        params,
        db_name=db_name,
    )


def count_related_jobs(relation: str | None, *, db_name: str | None = None) -> int:
    if relation:
        row = fetch_one(
            f"""
            SELECT COUNT(DISTINCT empleo_id)::int AS total
            FROM {relation}
            WHERE skills_en_comun >= 2
            """,
            db_name=db_name,
        )
    else:
        row = fetch_one(
            """
            SELECT COUNT(DISTINCT empleo_id)::int AS total
            FROM empleo_skills
            """,
            db_name=db_name,
        )
    return int((row or {}).get("total", 0) or 0)
