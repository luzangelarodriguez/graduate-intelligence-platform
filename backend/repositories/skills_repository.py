from __future__ import annotations

from typing import Any

from backend.repositories.base import fetch_all, fetch_one


def fetch_job_skill_names(empleo_id: str | int, *, db_name: str | None = None) -> list[str]:
    rows = fetch_all(
        """
        SELECT DISTINCT s.nombre AS nombre
        FROM empleo_skills es
        INNER JOIN skills s
            ON s.id = es.skill_id
        WHERE es.empleo_id = %s
        ORDER BY 1
        """,
        (empleo_id,),
        db_name=db_name,
    )
    return [str(row.get("nombre", "") or "").strip() for row in rows if str(row.get("nombre", "") or "").strip()]


def count_market_skills(*, db_name: str | None = None) -> int:
    row = fetch_one(
        """
        SELECT COUNT(DISTINCT skill_id)::int AS total
        FROM empleo_skills
        """,
        db_name=db_name,
    )
    return int((row or {}).get("total", 0) or 0)


def fetch_top_market_skill_rows(relation: str, limit: int, *, db_name: str | None = None) -> list[dict[str, Any]]:
    return fetch_all(
        f"""
        SELECT
            ROW_NUMBER() OVER (ORDER BY COUNT(DISTINCT m.empleo_id) DESC, s.nombre) AS skill_id,
            s.nombre AS nombre,
            COUNT(DISTINCT m.empleo_id)::int AS conteo
        FROM {relation} m
        INNER JOIN empleo_skills es
            ON es.empleo_id = m.empleo_id
        INNER JOIN skills s
            ON s.id = es.skill_id
        WHERE m.skills_en_comun >= 2
        GROUP BY s.nombre
        ORDER BY conteo DESC, s.nombre
        LIMIT %s
        """,
        (limit,),
        db_name=db_name,
    )


def fetch_missing_market_skill_rows_for_program(
    relation: str,
    especializacion_id: int,
    limit: int,
    *,
    db_name: str | None = None,
) -> list[dict[str, Any]]:
    return fetch_all(
        f"""
        WITH program_skills AS (
            SELECT DISTINCT
                lower(COALESCE(skill_key, '')) AS nombre_key
            FROM vw_programa_skills
            WHERE especializacion_id = %s
        ),
        market_skills AS (
            SELECT
                s.nombre AS nombre,
                COUNT(DISTINCT m.empleo_id)::int AS conteo
            FROM {relation} m
            INNER JOIN empleo_skills es
                ON es.empleo_id = m.empleo_id
            INNER JOIN skills s
                ON s.id = es.skill_id
            WHERE m.especializacion_id = %s
              AND m.skills_en_comun >= 1
            GROUP BY s.nombre
        )
        SELECT
            ROW_NUMBER() OVER (ORDER BY ms.conteo DESC, ms.nombre) AS skill_id,
            ms.nombre,
            ms.conteo
        FROM market_skills ms
        WHERE lower(ms.nombre) NOT IN (SELECT nombre_key FROM program_skills)
        ORDER BY ms.conteo DESC, ms.nombre
        LIMIT %s
        """,
        (especializacion_id, especializacion_id, limit),
        db_name=db_name,
    )
