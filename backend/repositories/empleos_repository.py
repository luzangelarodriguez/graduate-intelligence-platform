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
    """Return distinct filter option values from the jobs table."""
    periodos = fetch_all(
        """
        SELECT DISTINCT TO_CHAR(created_at, 'YYYY-MM') AS periodo
        FROM jobs
        WHERE created_at IS NOT NULL
        ORDER BY periodo DESC
        LIMIT 36
        """,
        db_name=db_name,
    )
    dominios = fetch_all(
        """
        SELECT DISTINCT industry AS dominio
        FROM jobs
        WHERE industry IS NOT NULL AND TRIM(industry) != ''
        ORDER BY industry
        """,
        db_name=db_name,
    )
    seniorities = fetch_all(
        """
        SELECT DISTINCT seniority
        FROM jobs
        WHERE seniority IS NOT NULL AND TRIM(seniority) != ''
        ORDER BY seniority
        """,
        db_name=db_name,
    )
    ciudades = fetch_all(
        """
        SELECT DISTINCT location AS ciudad
        FROM jobs
        WHERE location IS NOT NULL AND TRIM(location) != ''
        ORDER BY location
        LIMIT 50
        """,
        db_name=db_name,
    )
    portales = fetch_all(
        """
        SELECT DISTINCT source AS portal
        FROM jobs
        WHERE source IS NOT NULL AND TRIM(source) != ''
        ORDER BY source
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
    especializacion_id: int,
    *,
    periodo: str | None = None,
    dominio: str | None = None,
    ciudad: str | None = None,
    seniority: str | None = None,
    portal: str | None = None,
    db_name: str | None = None,
) -> list[dict[str, Any]]:
    """Return top occupational profiles (semantic_title_family) for a program via ml_program_job_matches."""
    job_filters = [
        "m.especializacion_id = %s",
        "m.run_id = (SELECT MAX(id) FROM ml_training_runs WHERE task_name = 'program_job_match')",
        "m.relevance_label IN ('high', 'medium')",
        "j.semantic_title_family IS NOT NULL",
        "TRIM(j.semantic_title_family) != ''",
    ]
    params: list[Any] = [especializacion_id]

    if periodo:
        job_filters.append("TO_CHAR(j.created_at, 'YYYY-MM') = %s")
        params.append(periodo)
    if dominio:
        job_filters.append("j.industry = %s")
        params.append(dominio)
    if ciudad:
        job_filters.append("j.location = %s")
        params.append(ciudad)
    if seniority:
        job_filters.append("j.seniority = %s")
        params.append(seniority)
    if portal:
        job_filters.append("j.source = %s")
        params.append(portal)

    where = " AND ".join(job_filters)
    return fetch_all(
        f"""
        SELECT
            j.semantic_title_family AS perfil,
            COUNT(DISTINCT j.id)::int AS vacantes
        FROM jobs j
        JOIN ml_program_job_matches m ON m.empleo_id = j.id::text
        WHERE {where}
        GROUP BY j.semantic_title_family
        ORDER BY vacantes DESC
        LIMIT 10
        """,
        params,
        db_name=db_name,
    )


def fetch_profile_skills(
    titulo_normalizado: str,
    especializacion_id: int,
    *,
    periodo: str | None = None,
    dominio: str | None = None,
    ciudad: str | None = None,
    seniority: str | None = None,
    portal: str | None = None,
    db_name: str | None = None,
) -> list[dict[str, Any]]:
    """Return skills for jobs matching a semantic_title_family for a given program via ml_program_job_matches."""
    job_filters = [
        "m.especializacion_id = %s",
        "m.run_id = (SELECT MAX(id) FROM ml_training_runs WHERE task_name = 'program_job_match')",
        "m.relevance_label IN ('high', 'medium')",
        "j.semantic_title_family = %s",
        "COALESCE(js.canonical_skill, js.skill_family, js.skill_category, '') != ''",
    ]
    params: list[Any] = [especializacion_id, titulo_normalizado]

    if periodo:
        job_filters.append("TO_CHAR(j.created_at, 'YYYY-MM') = %s")
        params.append(periodo)
    if dominio:
        job_filters.append("j.industry = %s")
        params.append(dominio)
    if ciudad:
        job_filters.append("j.location = %s")
        params.append(ciudad)
    if seniority:
        job_filters.append("j.seniority = %s")
        params.append(seniority)
    if portal:
        job_filters.append("j.source = %s")
        params.append(portal)

    where = " AND ".join(job_filters)
    return fetch_all(
        f"""
        SELECT
            COALESCE(js.canonical_skill, js.skill_family, js.skill_category) AS nombre,
            COALESCE(NULLIF(TRIM(js.skill_category), ''), 'Otros') AS tipo_skill,
            COUNT(DISTINCT j.id)::int AS vacantes
        FROM jobs j
        JOIN ml_program_job_matches m ON m.empleo_id = j.id::text
        JOIN job_skills js ON js.job_id = j.id
        WHERE {where}
        GROUP BY js.canonical_skill, js.skill_family, js.skill_category
        ORDER BY vacantes DESC
        """,
        params,
        db_name=db_name,
    )


def fetch_profile_kpis(
    especializacion_id: int,
    *,
    periodo: str | None = None,
    dominio: str | None = None,
    ciudad: str | None = None,
    seniority: str | None = None,
    portal: str | None = None,
    db_name: str | None = None,
) -> dict[str, Any]:
    """Return aggregate KPIs for jobs matched to a program via ml_program_job_matches."""
    job_filters = [
        "m.especializacion_id = %s",
        "m.run_id = (SELECT MAX(id) FROM ml_training_runs WHERE task_name = 'program_job_match')",
        "m.relevance_label IN ('high', 'medium')",
        "j.semantic_title_family IS NOT NULL",
        "TRIM(j.semantic_title_family) != ''",
    ]
    params: list[Any] = [especializacion_id]

    if periodo:
        job_filters.append("TO_CHAR(j.created_at, 'YYYY-MM') = %s")
        params.append(periodo)
    if dominio:
        job_filters.append("j.industry = %s")
        params.append(dominio)
    if ciudad:
        job_filters.append("j.location = %s")
        params.append(ciudad)
    if seniority:
        job_filters.append("j.seniority = %s")
        params.append(seniority)
    if portal:
        job_filters.append("j.source = %s")
        params.append(portal)

    where = " AND ".join(job_filters)
    row = fetch_all(
        f"""
        SELECT
            COUNT(DISTINCT j.id)::int AS total_ofertas,
            COUNT(DISTINCT j.semantic_title_family)::int AS total_perfiles,
            COUNT(DISTINCT COALESCE(js.canonical_skill, js.skill_family, js.skill_category))::int AS total_skills
        FROM jobs j
        JOIN ml_program_job_matches m ON m.empleo_id = j.id::text
        LEFT JOIN job_skills js ON js.job_id = j.id
        WHERE {where}
        """,
        params,
        db_name=db_name,
    )
    if row:
        return row[0]
    return {"total_ofertas": 0, "total_perfiles": 0, "total_skills": 0}
