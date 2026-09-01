from __future__ import annotations

from typing import Any

from backend.repositories.base import fetch_all, fetch_one


def fetch_job_metadata(empleo_id: str | int, *, db_name: str | None = None) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT
            COALESCE(titulo, '') AS titulo,
            COALESCE(empresa, '') AS empresa,
            COALESCE(ubicacion, '') AS ubicacion,
            COALESCE(fuente, '') AS fuente,
            COALESCE(url, '') AS url,
            COALESCE(fecha::text, '') AS fecha
        FROM empleos
        WHERE id = %s
        """,
        (empleo_id,),
        db_name=db_name,
    )


def fetch_jobs_for_scoring(*, db_name: str | None = None) -> list[dict[str, Any]]:
    return fetch_all(
        """
        WITH employment_skill_total AS (
            SELECT empleo_id, COUNT(DISTINCT skill_id)::int AS total_skills_empleo
            FROM empleo_skills
            GROUP BY empleo_id
        )
        SELECT
            e.id AS empleo_id,
            e.titulo AS titulo_empleo,
            COALESCE(e.empresa, '') AS empresa,
            COALESCE(e.ubicacion, '') AS ubicacion,
            COALESCE(est.total_skills_empleo, 0) AS total_skills_empleo
        FROM empleos e
        LEFT JOIN employment_skill_total est
            ON est.empleo_id = e.id
        ORDER BY e.titulo
        """,
        db_name=db_name,
    )


def fetch_jobs_basic(*, db_name: str | None = None) -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT
            id AS empleo_id,
            COALESCE(titulo, '') AS titulo,
            COALESCE(ubicacion, '') AS ubicacion
        FROM empleos
        ORDER BY id
        """,
        db_name=db_name,
    )


def fetch_market_filter_options(*, db_name: str | None = None) -> dict[str, list[str]]:
    """Return distinct filter option values available in the empleos table."""
    periodos = fetch_all(
        """
        SELECT DISTINCT TO_CHAR(fecha_publicacion, 'YYYY-MM') AS periodo
        FROM empleos
        WHERE fecha_publicacion IS NOT NULL
        ORDER BY periodo DESC
        LIMIT 36
        """,
        db_name=db_name,
    )
    dominios = fetch_all(
        """
        SELECT DISTINCT dominio
        FROM empleos
        WHERE dominio IS NOT NULL AND TRIM(dominio) != ''
        ORDER BY dominio
        """,
        db_name=db_name,
    )
    seniorities = fetch_all(
        """
        SELECT DISTINCT seniority
        FROM empleos
        WHERE seniority IS NOT NULL AND TRIM(seniority) != ''
        ORDER BY seniority
        """,
        db_name=db_name,
    )
    return {
        "periodos": [r["periodo"] for r in periodos],
        "dominios": [r["dominio"] for r in dominios],
        "seniorities": [r["seniority"] for r in seniorities],
    }
