from __future__ import annotations

import re
from typing import Any

from backend.repositories.base import fetch_all, fetch_one

_SKILL_REPR_RE = re.compile(r"SkillMatch\([^)]*skill_normalized='([^']+)'[^)]*\)")

_ACRONYMS = {
    "sql", "bi", "kpi", "kpis", "pmbok", "pmi", "pmp", "erp", "crm", "etl",
    "api", "r", "sap", "aws", "gcp", "nlp", "ml", "ai", "hr", "rpa", "dax",
    "vba", "css", "html", "php", "c", "c++", "c#",
}

# Maps raw skill_category values from the DB to the 4 UI categories.
# Keys are lowercased for case-insensitive lookup.
_TIPO_MAP: dict[str, str] = {
    # Herramienta
    "bi & visualization":           "herramienta",
    "bi and visualization":         "herramienta",
    "databases":                    "herramienta",
    "cloud analytics":              "herramienta",
    "cloud":                        "herramienta",
    "cloud platforms":              "herramienta",
    "data visualization":           "herramienta",
    "visualization":                "herramienta",
    "tools":                        "herramienta",
    "herramienta":                  "herramienta",
    "herramientas":                 "herramienta",
    # Tecnica / Conocimiento
    "programming / analytics":      "tecnica",
    "programming/analytics":        "tecnica",
    "programming":                  "tecnica",
    "analytics":                    "tecnica",
    "data engineering":             "tecnica",
    "ai analytics":                 "tecnica",
    "ai & analytics":               "tecnica",
    "machine learning":             "tecnica",
    "statistics":                   "tecnica",
    "data science":                 "tecnica",
    "tecnica":                      "tecnica",
    "técnica":                      "tecnica",
    "conocimiento":                 "tecnica",
    # Habilidad
    "soft skills":                  "habilidad",
    "soft skill":                   "habilidad",
    "communication":                "habilidad",
    "leadership":                   "habilidad",
    "habilidad":                    "habilidad",
    "habilidades":                  "habilidad",
    # Competencia / Gestión
    "governance":                   "competencia",
    "methodologies":                "competencia",
    "methodology":                  "competencia",
    "risk & security":              "competencia",
    "risk and security":            "competencia",
    "security":                     "competencia",
    "project management":           "competencia",
    "management":                   "competencia",
    "business":                     "competencia",
    "strategy":                     "competencia",
    "competencia":                  "competencia",
    "competencias":                 "competencia",
    "gestión":                      "competencia",
    "gestion":                      "competencia",
}


def _clean_tipo_skill(_self: object, raw: str | None) -> str:
    """Normalize a raw skill_category DB value to one of: herramienta/tecnica/habilidad/competencia."""
    if not raw:
        return "competencia"
    key = raw.strip().lower()
    return _TIPO_MAP.get(key, "competencia")


def _clean_skill_name(raw: str | None) -> str:
    """Return a display-ready skill name from a potentially contaminated canonical_skill value."""
    if not raw:
        return ""
    s = raw.strip()
    m = _SKILL_REPR_RE.search(s)
    if m:
        s = m.group(1)
    lower = s.lower()
    if lower in _ACRONYMS:
        return s.upper()
    return s.capitalize()


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
        "COALESCE(j.activo, TRUE) = TRUE",
        "COALESCE(j.semantic_title_family, j.title) IS NOT NULL",
        "TRIM(COALESCE(j.semantic_title_family, j.title)) != ''",
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
            LOWER(TRIM(COALESCE(j.semantic_title_family, j.title))) AS perfil,
            COUNT(DISTINCT j.id)::int AS vacantes
        FROM jobs j
        JOIN ml_program_job_matches m ON m.empleo_id = j.id::text
        WHERE {where}
        GROUP BY LOWER(TRIM(COALESCE(j.semantic_title_family, j.title)))
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
        "COALESCE(j.activo, TRUE) = TRUE",
        "LOWER(TRIM(COALESCE(j.semantic_title_family, j.title))) = LOWER(TRIM(%s))",
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
    rows = fetch_all(
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
    cleaned: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        nombre = _clean_skill_name(row.get("nombre"))
        if not nombre or nombre in seen:
            continue
        seen.add(nombre)
        cleaned.append({**row, "nombre": nombre})
    return cleaned


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
        "COALESCE(j.activo, TRUE) = TRUE",
        "COALESCE(j.semantic_title_family, j.title) IS NOT NULL",
        "TRIM(COALESCE(j.semantic_title_family, j.title)) != ''",
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
