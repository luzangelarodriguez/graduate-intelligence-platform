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
    ciudades = fetch_all(
        """
        SELECT DISTINCT ciudad
        FROM empleos
        WHERE ciudad IS NOT NULL AND TRIM(ciudad) != ''
        ORDER BY ciudad
        LIMIT 50
        """,
        db_name=db_name,
    )
    portales = fetch_all(
        """
        SELECT DISTINCT portal
        FROM empleos
        WHERE portal IS NOT NULL AND TRIM(portal) != ''
        ORDER BY portal
        """,
        db_name=db_name,
    )
    return {
        "periodos": [r["periodo"] for r in periodos],
        "dominios": [r["dominio"] for r in dominios],
        "seniorities": [r["seniority"] for r in seniorities],
        "ciudades": [r["ciudad"] for r in ciudades],
        "portales": [r["portal"] for r in portales],
    }


def fetch_occupational_profiles(
    *,
    periodo: str | None = None,
    dominio: str | None = None,
    ciudad: str | None = None,
    seniority: str | None = None,
    portal: str | None = None,
    db_name: str | None = None,
) -> list[dict[str, Any]]:
    """Return top occupational profiles grouped by titulo_normalizado with vacancy counts."""
    filters = ["titulo_normalizado IS NOT NULL", "TRIM(titulo_normalizado) != ''"]
    params: list[Any] = []

    if periodo:
        filters.append("TO_CHAR(fecha_publicacion, 'YYYY-MM') = %s")
        params.append(periodo)
    if dominio:
        filters.append("dominio = %s")
        params.append(dominio)
    if ciudad:
        filters.append("ciudad = %s")
        params.append(ciudad)
    if seniority:
        filters.append("seniority = %s")
        params.append(seniority)
    if portal:
        filters.append("portal = %s")
        params.append(portal)

    where = " AND ".join(filters)
    return fetch_all(
        f"""
        SELECT
            titulo_normalizado AS perfil,
            COUNT(DISTINCT id)::int AS vacantes
        FROM empleos
        WHERE {where}
        GROUP BY titulo_normalizado
        ORDER BY vacantes DESC
        LIMIT 10
        """,
        params or None,
        db_name=db_name,
    )


def fetch_profile_skills(
    titulo_normalizado: str,
    *,
    periodo: str | None = None,
    dominio: str | None = None,
    ciudad: str | None = None,
    seniority: str | None = None,
    portal: str | None = None,
    db_name: str | None = None,
) -> list[dict[str, Any]]:
    """Return skills (with tipo_skill) for all empleos matching a titulo_normalizado."""
    job_filters = [
        "e.titulo_normalizado = %s",
        "es.skill_normalized IS NOT NULL",
        "TRIM(es.skill_normalized) != ''",
    ]
    params: list[Any] = [titulo_normalizado]

    if periodo:
        job_filters.append("TO_CHAR(e.fecha_publicacion, 'YYYY-MM') = %s")
        params.append(periodo)
    if dominio:
        job_filters.append("e.dominio = %s")
        params.append(dominio)
    if ciudad:
        job_filters.append("e.ciudad = %s")
        params.append(ciudad)
    if seniority:
        job_filters.append("e.seniority = %s")
        params.append(seniority)
    if portal:
        job_filters.append("e.portal = %s")
        params.append(portal)

    where = " AND ".join(job_filters)
    return fetch_all(
        f"""
        SELECT
            es.skill_normalized AS nombre,
            COALESCE(NULLIF(TRIM(es.tipo_skill), ''), 'Otros') AS tipo_skill,
            COUNT(DISTINCT e.id)::int AS vacantes
        FROM empleos e
        JOIN empleo_skills es ON es.empleo_id = e.id
        WHERE {where}
        GROUP BY es.skill_normalized, es.tipo_skill
        ORDER BY vacantes DESC
        """,
        params,
        db_name=db_name,
    )


def fetch_profile_kpis(
    *,
    periodo: str | None = None,
    dominio: str | None = None,
    ciudad: str | None = None,
    seniority: str | None = None,
    portal: str | None = None,
    db_name: str | None = None,
) -> dict[str, Any]:
    """Return aggregate KPIs for the perfiles view."""
    filters = ["titulo_normalizado IS NOT NULL", "TRIM(titulo_normalizado) != ''"]
    params: list[Any] = []

    if periodo:
        filters.append("TO_CHAR(fecha_publicacion, 'YYYY-MM') = %s")
        params.append(periodo)
    if dominio:
        filters.append("dominio = %s")
        params.append(dominio)
    if ciudad:
        filters.append("ciudad = %s")
        params.append(ciudad)
    if seniority:
        filters.append("seniority = %s")
        params.append(seniority)
    if portal:
        filters.append("portal = %s")
        params.append(portal)

    where = " AND ".join(filters)
    row = fetch_all(
        f"""
        SELECT
            COUNT(DISTINCT e.id)::int AS total_ofertas,
            COUNT(DISTINCT e.titulo_normalizado)::int AS total_perfiles,
            COUNT(DISTINCT es.skill_normalized)::int AS total_skills
        FROM empleos e
        LEFT JOIN empleo_skills es ON es.empleo_id = e.id
        WHERE {where}
        """,
        params or None,
        db_name=db_name,
    )
    if row:
        return row[0]
    return {"total_ofertas": 0, "total_perfiles": 0, "total_skills": 0}
