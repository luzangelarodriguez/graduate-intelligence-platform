from __future__ import annotations

import importlib.util
import json
import os
import re
import unicodedata
from datetime import date
from contextlib import contextmanager
from html import escape
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, redirect, render_template, request, url_for

from backend.repositories import base as repository_base
from backend.repositories import matches_repository, programas_repository
from backend.routes.empleos import create_empleos_blueprint
from backend.routes.matches import create_matches_blueprint
from backend.routes.programas import create_programas_blueprint
from backend.routes.recommendations import create_recommendations_blueprint
from backend.services import alumni_service, dashboard_service, normalization_service, recommendation_service, scoring_service


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

PROGRAM_DB_NAME = os.getenv("DB_NAME", "cliente_a_db")
BASE_DIR = Path(__file__).resolve().parent


def _register_modular_api_routes() -> None:
    for blueprint in (
        create_programas_blueprint(PROGRAM_DB_NAME),
        create_empleos_blueprint(PROGRAM_DB_NAME),
        create_matches_blueprint(PROGRAM_DB_NAME),
        create_recommendations_blueprint(),
    ):
        app.register_blueprint(blueprint)


_register_modular_api_routes()


CANONICAL_PROGRAMS_SQL = """
SELECT DISTINCT ON (lower(nombre_especializacion))
    especializacion_id,
    nombre_especializacion,
    rol
FROM (
    SELECT
        v.especializacion_id,
        v.nombre_especializacion,
        COALESCE(e.rol, '') AS rol
    FROM vw_dashboard_especializacion v
    LEFT JOIN especializaciones e
        ON e.id = v.especializacion_id
) ranked
ORDER BY lower(nombre_especializacion), CASE WHEN nombre_especializacion ~ '^[A-Z]' THEN 0 ELSE 1 END, especializacion_id
"""

PROGRAM_DASHBOARD_SQL = """
SELECT
    v.especializacion_id,
    v.nombre_especializacion,
    COALESCE(e.rol, '') AS rol,
    v.total_skills_programa,
    v.total_herramientas,
    v.total_competencias,
    v.total_habilidades_blandas,
    v.promedio_match_mercado,
    v.max_match_mercado,
    v.total_empleos_relacionados
FROM vw_dashboard_especializacion v
LEFT JOIN especializaciones e
    ON e.id = v.especializacion_id
WHERE v.especializacion_id = %s
"""


def _basic_text_key(text: str) -> str:
    return normalization_service.basic_text_key(text)


def _load_module_from_path(module_name: str, file_path: Path):
    try:
        if not file_path.exists():
            return None
        spec = importlib.util.spec_from_file_location(module_name, str(file_path))
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


BACKEND_SKILL_ENGINE = _load_module_from_path(
    "dashboard_backend_skill_engine",
    BASE_DIR / "graduate_intelligence_platform" / "backend" / "app" / "engine.py",
)
CURATED_PROGRAM_SOURCE = _load_module_from_path(
    "dashboard_curated_program_source",
    BASE_DIR / "build_unir_especializaciones_db.py",
)

MANUAL_SKILL_ALIAS_TO_CANONICAL = {
    "analitica de datos": "Data Analysis",
    "analítica de datos": "Data Analysis",
    "analisis de datos": "Data Analysis",
    "análisis de datos": "Data Analysis",
    "data analyst": "Data Analysis",
    "analista de datos": "Data Analysis",
    "business intelligence": "Business Intelligence",
    "inteligencia de negocio": "Business Intelligence",
    "inteligencia de negocios": "Business Intelligence",
    "visualizacion": "Visualization",
    "visualización": "Visualization",
    "visualizacion de datos": "Visualization",
    "visualización de datos": "Visualization",
    "dashboards": "Dashboarding",
    "dashboard": "Dashboarding",
    "kpi": "KPI Design",
    "kpis": "KPI Design",
    "gestion de proyectos": "Project Management",
    "gestión de proyectos": "Project Management",
    "big data": "Big Data",
    "sql": "SQL",
    "sql server": "SQL",
    "excel": "Excel",
    "power bi": "Power BI",
    "tableau": "Tableau",
    "etl": "ETL",
    "elt": "ETL",
    "modelado de datos": "Data Modeling",
    "azure": "Cloud",
    "cloud": "Cloud",
    "qa": "Testing",
    "pruebas funcionales": "Testing",
    "aseguramiento de calidad": "Testing",
    "programacion": "Programming",
    "programación": "Programming",
    "desarrollo de software": "Programming",
    "arquitectura de software": "Software Architecture",
    "metodologias agiles": "Agile Methodologies",
    "metodologías ágiles": "Agile Methodologies",
    "agile": "Agile Methodologies",
    "ci cd": "CI/CD",
    "ci/cd": "CI/CD",
    "devops": "DevOps",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "gobierno de datos": "Data Governance",
    "calidad de datos": "Data Quality",
}


def _build_curated_program_maps() -> tuple[dict[str, list[str]], dict[str, str]]:
    skill_map: dict[str, list[str]] = {}
    role_map: dict[str, str] = {}
    if CURATED_PROGRAM_SOURCE is None:
        return skill_map, role_map

    for item in getattr(CURATED_PROGRAM_SOURCE, "PROGRAMS", []) or []:
        name = str(item.get("name", "") or "").strip()
        skills = [str(skill).strip() for skill in item.get("skills", []) or [] if str(skill).strip()]
        key = _basic_text_key(name)
        if key and skills:
            skill_map[key] = skills

    for name, role in (getattr(CURATED_PROGRAM_SOURCE, "ROLE_OVERRIDES", {}) or {}).items():
        key = _basic_text_key(name)
        value = str(role or "").strip()
        if key and value:
            role_map[key] = value

    return skill_map, role_map


def _build_catalog_skill_lookup() -> tuple[dict[str, str], dict[str, str]]:
    alias_lookup: dict[str, str] = {}
    canonical_lookup: dict[str, str] = {}

    if BACKEND_SKILL_ENGINE is not None:
        for item in getattr(BACKEND_SKILL_ENGINE, "SKILL_CATALOG", []) or []:
            canonical = str(item.get("name", "") or "").strip()
            if not canonical:
                continue
            canonical_lookup[_basic_text_key(canonical)] = canonical
            for alias in [canonical] + list(item.get("aliases", []) or []):
                alias_key = _basic_text_key(alias)
                if alias_key:
                    alias_lookup[alias_key] = canonical

    for alias, canonical in MANUAL_SKILL_ALIAS_TO_CANONICAL.items():
        alias_lookup[_basic_text_key(alias)] = canonical
        alias_lookup[_basic_text_key(canonical)] = canonical
        canonical_lookup[_basic_text_key(canonical)] = canonical

    return alias_lookup, canonical_lookup


CURATED_PROGRAM_SKILLS, CURATED_PROGRAM_ROLES = _build_curated_program_maps()
CATALOG_SKILL_ALIAS_LOOKUP, CATALOG_SKILL_CANONICALS = _build_catalog_skill_lookup()

JOB_TITLE_ROLE_HINTS = tuple(
    _basic_text_key(item)
    for item in (
        "analista",
        "ingeniero",
        "desarrollador",
        "developer",
        "devops",
        "cientifico",
        "científico",
        "arquitecto",
        "soporte",
        "helpdesk",
        "qa",
        "sap",
        "infraestructura",
        "data",
        "administrador",
        "coordinador",
        "lider",
        "líder",
        "consultor",
        "especialista",
        "gerente",
        "monitor",
        "ofimatico",
        "ofimático",
    )
)
JOB_TITLE_BAD_PREFIXES = tuple(
    _basic_text_key(item)
    for item in (
        "100% remoto",
        "100 remoto",
        "remoto",
        "híbrido",
        "hibrido",
        "horario",
        "jornada",
        "tipo de contrato",
        "disponibilidad",
        "programas de bienestar",
        "postúlate ahora",
        "postulate ahora",
        "organización y documentación",
        "organizacion y documentacion",
        "salary",
        "esta oferta",
        "esta vacante",
    )
)
GENERIC_COMPANY_VALUES = {
    _basic_text_key(item)
    for item in (
        "",
        "híbrido",
        "hibrido",
        "remoto",
        "remote",
        "confidential",
        "hybrid",
        "buscar empleos",
    )
}


def get_connection(db_name: str | None = None):
    return repository_base.get_conn(db_name=db_name or PROGRAM_DB_NAME)


@contextmanager
def get_cursor(db_name: str | None = None):
    with repository_base.cursor(db_name=db_name or PROGRAM_DB_NAME) as cur:
        yield cur


def _fetch_all(sql: str, params: tuple[Any, ...] = (), *, db_name: str | None = None) -> list[dict[str, Any]]:
    return repository_base.fetch_all(sql, params, db_name=db_name or PROGRAM_DB_NAME)


def _fetch_one(sql: str, params: tuple[Any, ...] = (), *, db_name: str | None = None) -> dict[str, Any] | None:
    return repository_base.fetch_one(sql, params, db_name=db_name or PROGRAM_DB_NAME)


def _relation_exists(name: str) -> bool:
    return repository_base.relation_exists(name, db_name=PROGRAM_DB_NAME)


def _pick_relation(names: tuple[str, ...]) -> str | None:
    return repository_base.pick_relation(names, db_name=PROGRAM_DB_NAME)


def _relation_has_rows(name: str) -> bool:
    return repository_base.relation_has_rows(name, db_name=PROGRAM_DB_NAME)


def _match_relation_name() -> str | None:
    return matches_repository.match_relation_name(db_name=PROGRAM_DB_NAME)


def _resolve_program_id(especializacion_id: int) -> int:
    return programas_repository.resolve_program_id(especializacion_id, db_name=PROGRAM_DB_NAME)


def _lookup_curated_program_skills(program_name: str) -> list[str]:
    program_key = _basic_text_key(program_name)
    if not program_key:
        return []
    direct = CURATED_PROGRAM_SKILLS.get(program_key)
    if direct:
        return list(direct)
    for key, skills in CURATED_PROGRAM_SKILLS.items():
        if key in program_key or program_key in key:
            return list(skills)
    if BACKEND_SKILL_ENGINE is not None and hasattr(BACKEND_SKILL_ENGINE, "clean_program_skill_profile"):
        try:
            generated = BACKEND_SKILL_ENGINE.clean_program_skill_profile(program_name, "")
            return [str(skill).strip() for skill in generated if str(skill).strip()]
        except Exception:
            return []
    return []


def _lookup_curated_program_role(program_name: str) -> str:
    program_key = _basic_text_key(program_name)
    if not program_key:
        return ""
    direct = CURATED_PROGRAM_ROLES.get(program_key)
    if direct:
        return direct
    for key, role in CURATED_PROGRAM_ROLES.items():
        if key in program_key or program_key in key:
            return role
    return ""


def _catalog_skill_matches(text: str) -> list[str]:
    normalized_text = _basic_text_key(text)
    if not normalized_text:
        return []
    matches: dict[str, str] = {}
    for alias_key, canonical in CATALOG_SKILL_ALIAS_LOOKUP.items():
        if alias_key and re.search(rf"\b{re.escape(alias_key)}\b", normalized_text):
            matches[_basic_text_key(canonical)] = canonical
    return sorted(matches.values(), key=str.casefold)


def _skill_identity_key(name: str) -> str:
    matches = _catalog_skill_matches(name)
    if matches:
        return f"catalog:{_basic_text_key(matches[0])}"
    return _basic_text_key(name)


def _display_market_skill_name(name: str) -> str:
    matches = _catalog_skill_matches(name)
    if matches:
        return matches[0]
    return str(name or "").strip()


def _is_market_skill_noise(name: str) -> bool:
    key = _basic_text_key(name)
    if not key:
        return True
    if key in {"gestion", "analisis", "comunicacion", "liderazgo", "strategy", "communication", "leadership"}:
        return True
    role_tokens = {
        "analista",
        "architect",
        "arquitecto",
        "coordinador",
        "developer",
        "desarrollador",
        "engineer",
        "ingeniero",
        "lider",
        "officer",
        "specialist",
        "tecnico",
        "technical",
    }
    return any(token in set(key.split()) for token in role_tokens)


PROGRAM_GAP_BLOCKLISTS = (
    (
        ("ingenieria de software", "ingeniero de software", "software"),
        {
            "catalog:big data",
            "catalog:business intelligence",
            "catalog:data analysis",
            "catalog:data modeling",
            "catalog:etl",
            "catalog:kpi design",
            "catalog:power bi",
            "catalog:reporting",
            "catalog:sql",
            "catalog:tableau",
            "catalog:visualization",
            "excel",
        },
    ),
    (
        ("inteligencia de negocio", "business intelligence", "visual analytics", "big data"),
        {
            "arquitectura de software",
            "catalog:apis",
            "catalog:cybersecurity",
            "catalog:git",
            "catalog:project management",
            "catalog:testing",
            "metodologias agiles",
            "programacion",
        },
    ),
)


def _program_gap_blocklist(especializacion_id: int) -> set[str]:
    program = _fetch_program_base_row(especializacion_id) or {}
    source = _basic_text_key(
        " ".join(
            [
                str(program.get("nombre_especializacion") or ""),
                str(program.get("rol") or ""),
            ]
        )
    )
    blocked: set[str] = set()
    for needles, skill_keys in PROGRAM_GAP_BLOCKLISTS:
        if any(needle in source for needle in needles):
            blocked.update(skill_keys)
    return blocked


def _is_supported_market_skill(name: str) -> bool:
    key = _skill_identity_key(name)
    if key.startswith("catalog:"):
        return True
    simple_allowed = {
        "ci cd",
        "devops",
        "docker",
        "kubernetes",
        "jira",
        "json",
        "net",
        "node js",
        "rest",
        "soa",
        "ux",
    }
    return _basic_text_key(name) in simple_allowed


def _job_title_score(text: str) -> int:
    normalized = _basic_text_key(text)
    if not normalized:
        return -99
    if normalized in {"bogota", "antioquia", "remoto", "hibrido", "formacion", "apis", "almacenamiento"}:
        return -8
    if any(normalized.startswith(prefix) for prefix in JOB_TITLE_BAD_PREFIXES):
        return -7

    score = 0
    words = normalized.split()
    if 2 <= len(words) <= 6:
        score += 2
    elif len(words) == 1:
        score -= 1
    elif len(words) > 10:
        score -= 2

    if ":" in str(text):
        score -= 2
    if str(text).strip().endswith("."):
        score -= 1
    if any(hint in normalized for hint in JOB_TITLE_ROLE_HINTS):
        score += 4
    return score


def _best_job_title(*candidates: str) -> str:
    best_text = ""
    best_score = -99
    for candidate in candidates:
        value = str(candidate or "").strip()
        score = _job_title_score(value)
        if score > best_score:
            best_text = value
            best_score = score
    return best_text or str(next((candidate for candidate in candidates if str(candidate or "").strip()), "")).strip()


def _clean_company_name(company: str) -> str:
    value = str(company or "").strip()
    if _basic_text_key(value) in GENERIC_COMPANY_VALUES:
        return ""
    if any(_basic_text_key(value).startswith(prefix) for prefix in JOB_TITLE_BAD_PREFIXES):
        return ""
    return value


def _platform_label(source: str, url: str = "") -> str:
    source_key = _basic_text_key(source)
    url_key = _basic_text_key(url)
    combined = f"{source_key} {url_key}"
    if "computrabajo" in combined:
        return "Computrabajo"
    if "linkedin" in combined:
        return "LinkedIn"
    if "ticjob" in combined:
        return "Ticjob"
    if "elempleo" in combined:
        return "Elempleo"
    return str(source or "").strip() or "Portal de empleo"


def _job_catalog_skills(empleo_id: str | int, *extra_texts: str) -> list[str]:
    rows = _fetch_all(
        """
        SELECT DISTINCT s.nombre AS nombre
        FROM empleo_skills es
        INNER JOIN skills s
            ON s.id = es.skill_id
        WHERE es.empleo_id = %s
        ORDER BY 1
        """,
        (empleo_id,),
        db_name=PROGRAM_DB_NAME,
    )
    matches: dict[str, str] = {}
    texts = [str(text).strip() for text in extra_texts if str(text).strip()]
    texts.extend(str(row.get("nombre", "") or "").strip() for row in rows if str(row.get("nombre", "") or "").strip())
    for text in texts:
        for canonical in _catalog_skill_matches(text):
            matches[_basic_text_key(canonical)] = canonical
    return sorted(matches.values(), key=str.casefold)


def _merge_program_skill_rows(base_rows: list[dict[str, Any]], curated_names: list[str]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()

    for row in base_rows:
        name = str(row.get("nombre", "") or "").strip()
        if not name:
            continue
        key = _skill_identity_key(name)
        if key in seen:
            continue
        seen.add(key)
        merged.append(_normalize_skill_row(row))

    synthetic_id = 900000
    for name in curated_names:
        label = str(name or "").strip()
        if not label:
            continue
        key = _skill_identity_key(label)
        if key in seen:
            continue
        seen.add(key)
        merged.append({"skill_id": synthetic_id, "nombre": label, "conteo": 0})
        synthetic_id += 1

    merged.sort(key=lambda item: str(item.get("nombre", "")).casefold())
    return merged


def _fallback_job_match_rows(especializacion_id: int, limit: int | None = None) -> list[dict[str, Any]]:
    especializacion_id = _resolve_program_id(especializacion_id)
    limit_sql = "LIMIT %s" if limit is not None else ""
    params: tuple[Any, ...] = (especializacion_id,)
    if limit is not None:
        params = (especializacion_id, limit)
    rows = _fetch_all(
        f"""
        WITH program_skills AS (
            SELECT DISTINCT skill_id
            FROM especializacion_skills
            WHERE especializacion_id = %s
        ),
        program_skill_total AS (
            SELECT COUNT(*)::int AS total_skills_especializacion
            FROM program_skills
        ),
        employment_skill_total AS (
            SELECT empleo_id, COUNT(DISTINCT skill_id)::int AS total_skills_empleo
            FROM empleo_skills
            GROUP BY empleo_id
        ),
        common_skills AS (
            SELECT
                es.empleo_id,
                COUNT(DISTINCT es.skill_id)::int AS skills_en_comun
            FROM empleo_skills es
            INNER JOIN program_skills ps
                ON ps.skill_id = es.skill_id
            GROUP BY es.empleo_id
        )
        SELECT
            e.id AS empleo_id,
            e.titulo AS titulo_empleo,
            COALESCE(e.empresa, '') AS empresa,
            COALESCE(est.total_skills_empleo, 0) AS total_skills_empleo,
            pst.total_skills_especializacion,
            cs.skills_en_comun,
            CASE
                WHEN pst.total_skills_especializacion > 0 THEN ROUND((cs.skills_en_comun::numeric / pst.total_skills_especializacion::numeric) * 100, 2)
                ELSE 0
            END AS porcentaje_match
        FROM common_skills cs
        INNER JOIN empleos e
            ON e.id = cs.empleo_id
        LEFT JOIN employment_skill_total est
            ON est.empleo_id = cs.empleo_id
        CROSS JOIN program_skill_total pst
        WHERE cs.skills_en_comun >= 1
        ORDER BY porcentaje_match DESC, cs.skills_en_comun DESC, e.titulo
        {limit_sql}
        """,
        params,
        db_name=PROGRAM_DB_NAME,
    )
    if rows:
        return rows

    program = _fetch_program_base_row(especializacion_id) or {}
    role_candidates: list[str] = []
    base_role = str(program.get("rol") or "").strip()
    if base_role:
        role_candidates.append(base_role)
    for item in _program_role_hints(program, limit=4):
        role_name = str(item.get("rol") or "").strip()
        if role_name and role_name not in role_candidates:
            role_candidates.append(role_name)
    if not role_candidates:
        return []

    total_skills_programa = int(program.get("total_skills_programa", 0) or 0)
    rows = _fetch_all(
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
        db_name=PROGRAM_DB_NAME,
    )
    scored_rows: list[dict[str, Any]] = []
    for row in rows:
        title = _best_job_title(row.get("titulo_empleo", ""), row.get("ubicacion", ""))
        if not title:
            continue
        best_score = max((_title_affinity_score(role_name, title) for role_name in role_candidates), default=0.0)
        if best_score <= 0:
            continue
        scored_rows.append(
            {
                "empleo_id": row.get("empleo_id"),
                "titulo_empleo": title,
                "empresa": _clean_company_name(str(row.get("empresa", "") or "")),
                "ubicacion": str(row.get("ubicacion", "") or ""),
                "total_skills_empleo": int(row.get("total_skills_empleo", 0) or 0),
                "total_skills_especializacion": total_skills_programa,
                "skills_en_comun": 0,
                "porcentaje_match": round(best_score, 2),
            }
        )
    scored_rows.sort(
        key=lambda item: (
            -_safe_float(item.get("porcentaje_match", 0)),
            -int(item.get("total_skills_empleo", 0) or 0),
            str(item.get("titulo_empleo", "")).casefold(),
        )
    )
    return scored_rows[:limit] if limit is not None else scored_rows


def _row_value(row: dict[str, Any], *names: str, default: Any = None) -> Any:
    return normalization_service.row_value(row, *names, default=default)


def _normalize_program_row(row: dict[str, Any]) -> dict[str, Any]:
    return normalization_service.normalize_program_row(row)


def _normalize_skill_row(row: dict[str, Any]) -> dict[str, Any]:
    return normalization_service.normalize_skill_row(row)


def _fallback_programs() -> list[dict[str, Any]]:
    return [
        _normalize_program_row(row)
        for row in _fetch_all(
        """
        SELECT
            id AS especializacion_id,
            nombre AS nombre_especializacion,
            COALESCE(rol, '') AS rol
        FROM especializaciones
        ORDER BY nombre
        """
        )
    ]


def _market_metrics_for_program(especializacion_id: int) -> dict[str, Any]:
    especializacion_id = _resolve_program_id(especializacion_id)
    related_jobs = get_related_jobs(especializacion_id, limit=None)
    if not related_jobs:
        return {
            "promedio_match_mercado": 0.0,
            "porcentaje_match": 0.0,
            "max_match_mercado": 0.0,
            "total_empleos_relacionados": 0,
            "skills_cubiertas": 0,
        }
    matches = [_safe_float(job.get("match_pertinencia", job.get("porcentaje_match", 0))) for job in related_jobs]
    promedio = round(sum(matches) / len(matches), 2) if matches else 0.0
    maximo = round(max(matches, default=0.0), 2)
    total = len(related_jobs)
    return {
        "promedio_match_mercado": promedio,
        "porcentaje_match": promedio,
        "max_match_mercado": maximo,
        "total_empleos_relacionados": total,
        "skills_cubiertas": 0,
    }


def _ml_program_metric_map() -> dict[int, dict[str, Any]]:
    relation = _match_relation_name()
    if relation != "vw_latest_ml_program_job_matches":
        return {}
    try:
        rows = _fetch_all(
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
            db_name=PROGRAM_DB_NAME,
        )
    except Exception:
        return {}
    return {
        int(row["especializacion_id"]): {
            "promedio_match_mercado": _safe_float(row.get("promedio_match_mercado", 0)),
            "porcentaje_match": _safe_float(row.get("promedio_match_mercado", 0)),
            "max_match_mercado": _safe_float(row.get("max_match_mercado", 0)),
            "total_empleos_relacionados": int(row.get("total_empleos_relacionados", 0) or 0),
        }
        for row in rows
        if row.get("especializacion_id") is not None
    }


def _fetch_program_base_row(especializacion_id: int) -> dict[str, Any] | None:
    especializacion_id = _resolve_program_id(especializacion_id)
    row = _fetch_one(
        """
        WITH programa_skills AS (
            SELECT especializacion_id, COUNT(DISTINCT skill_id)::int AS total_skills_programa
            FROM especializacion_skills
            GROUP BY especializacion_id
        ),
        programa_herramientas AS (
            SELECT especializacion_id, COUNT(DISTINCT herramienta_id)::int AS total_herramientas
            FROM especializacion_herramientas
            GROUP BY especializacion_id
        ),
        programa_competencias AS (
            SELECT especializacion_id, COUNT(DISTINCT competencia_id)::int AS total_competencias
            FROM especializacion_competencias
            GROUP BY especializacion_id
        ),
        programa_habilidades_blandas AS (
            SELECT especializacion_id, COUNT(DISTINCT habilidad_id)::int AS total_habilidades_blandas
            FROM especializacion_habilidades_blandas
            GROUP BY especializacion_id
        )
        SELECT
            s.id AS especializacion_id,
            s.nombre AS nombre_especializacion,
            COALESCE(s.rol, '') AS rol,
            COALESCE(ps.total_skills_programa, 0) AS total_skills_programa,
            COALESCE(ph.total_herramientas, 0) AS total_herramientas,
            COALESCE(pc.total_competencias, 0) AS total_competencias,
            COALESCE(pbl.total_habilidades_blandas, 0) AS total_habilidades_blandas
        FROM especializaciones s
        LEFT JOIN programa_skills ps ON ps.especializacion_id = s.id
        LEFT JOIN programa_herramientas ph ON ph.especializacion_id = s.id
        LEFT JOIN programa_competencias pc ON pc.especializacion_id = s.id
        LEFT JOIN programa_habilidades_blandas pbl ON pbl.especializacion_id = s.id
        WHERE s.id = %s
        """,
        (especializacion_id,),
        db_name=PROGRAM_DB_NAME,
    )
    if not row:
        return None
    normalized = _normalize_program_row(row)
    if not normalized["rol"]:
        normalized["rol"] = _lookup_curated_program_role(normalized["nombre_especializacion"])
    return normalized


def get_programas() -> list[dict[str, Any]]:
    rows = dashboard_service.list_programs_base(db_name=PROGRAM_DB_NAME)
    ml_metrics = _ml_program_metric_map()
    programs = []
    for row in rows:
        normalized = _normalize_program_row(row)
        if not normalized["rol"]:
            normalized["rol"] = _lookup_curated_program_role(normalized["nombre_especializacion"])
        normalized.update(ml_metrics.get(int(normalized["especializacion_id"]), {}))
        normalized["total_skills_programa"] = len(get_program_skill_rows(normalized["especializacion_id"]))
        normalized["roles_sugeridos"] = _program_role_hints(normalized, limit=4)
        if normalized["total_skills_programa"] > 0:
            normalized["skills_cubiertas"] = int(
                round(normalized["total_skills_programa"] * normalized["promedio_match_mercado"] / 100.0)
            )
        programs.append(normalized)
    return programs


def get_programa(especializacion_id: int) -> dict[str, Any] | None:
    especializacion_id = _resolve_program_id(especializacion_id)
    row = _fetch_program_base_row(especializacion_id)
    if not row:
        return None
    normalized = row
    visible_program_ids = {int(item.get("especializacion_id") or 0) for item in get_programas()}
    if especializacion_id not in visible_program_ids:
        return None
    normalized.update(_market_metrics_for_program(especializacion_id))
    normalized["roles_sugeridos"] = _program_role_suggestions(especializacion_id, limit=4)
    normalized["total_skills_programa"] = len(get_program_skill_rows(especializacion_id))
    if normalized["total_skills_programa"] > 0:
        normalized["skills_cubiertas"] = int(
            round(normalized["total_skills_programa"] * normalized["promedio_match_mercado"] / 100.0)
        )
    return normalized


def get_program_skill_rows(especializacion_id: int) -> list[dict[str, Any]]:
    especializacion_id = _resolve_program_id(especializacion_id)
    relation = _pick_relation(("vw_programa_skills",))
    if relation:
        rows = []
        for row in _fetch_all(f"SELECT * FROM {relation}"):
            if int(_row_value(row, "especializacion_id", "id", "programa_id", default=0) or 0) == especializacion_id:
                rows.append(_normalize_skill_row(row))
        if rows:
            base_program = _fetch_program_base_row(especializacion_id) or {}
            return _merge_program_skill_rows(rows, _lookup_curated_program_skills(str(base_program.get("nombre_especializacion", "") or "")))
    rows = _fetch_all(
        """
        SELECT DISTINCT
            s.id AS skill_id,
            s.nombre AS nombre
        FROM especializacion_skills es
        JOIN skills s
            ON s.id = es.skill_id
        WHERE es.especializacion_id = %s
        ORDER BY s.nombre
        """,
        (especializacion_id,),
    )
    base_program = _fetch_program_base_row(especializacion_id) or {}
    return _merge_program_skill_rows(rows, _lookup_curated_program_skills(str(base_program.get("nombre_especializacion", "") or "")))


def get_programas_skills_ids(especializacion_id: int) -> list[int]:
    rows = get_program_skill_rows(especializacion_id)
    return [int(row["skill_id"]) for row in rows]


def get_skills_programa(especializacion_id: int) -> list[dict[str, Any]]:
    return get_program_skill_rows(especializacion_id)


def get_related_market_skill_rows(especializacion_id: int, limit: int | None = None) -> list[dict[str, Any]]:
    especializacion_id = _resolve_program_id(especializacion_id)
    relation = _match_relation_name()
    if relation == "vw_latest_ml_program_job_matches":
        limit_sql = "LIMIT %s" if limit is not None else ""
        params: tuple[Any, ...] = (especializacion_id, limit) if limit is not None else (especializacion_id,)
        try:
            rows = _fetch_all(
                f"""
                WITH market_skills AS (
                    SELECT
                        trim(skill_name) AS nombre,
                        empleo_id,
                        porcentaje_match
                    FROM {relation},
                    LATERAL jsonb_array_elements_text(skills_empleo_json) AS skill_name
                    WHERE especializacion_id = %s
                      AND porcentaje_match >= 30
                ),
                filtered AS (
                    SELECT nombre, empleo_id, porcentaje_match
                    FROM market_skills
                    WHERE nombre <> ''
                )
                SELECT
                    ROW_NUMBER() OVER (ORDER BY COUNT(DISTINCT empleo_id) DESC, MAX(porcentaje_match) DESC, nombre) AS skill_id,
                    nombre,
                    COUNT(DISTINCT empleo_id)::int AS conteo
                FROM filtered
                GROUP BY nombre
                ORDER BY conteo DESC, MAX(porcentaje_match) DESC, nombre
                {limit_sql}
                """,
                params,
                db_name=PROGRAM_DB_NAME,
            )
            grouped: dict[str, dict[str, Any]] = {}
            for row in rows:
                raw_name = str(row.get("nombre", "") or "").strip()
                if _is_market_skill_noise(raw_name):
                    continue
                display_name = _display_market_skill_name(raw_name)
                if _is_market_skill_noise(display_name) or not _is_supported_market_skill(display_name):
                    continue
                key = _skill_identity_key(display_name)
                entry = grouped.setdefault(
                    key,
                    {"skill_id": len(grouped) + 1, "nombre": display_name, "conteo": 0},
                )
                entry["conteo"] = int(entry["conteo"]) + int(row.get("conteo", 0) or 0)
            clean_rows = sorted(grouped.values(), key=lambda item: (-int(item["conteo"]), str(item["nombre"]).casefold()))
            if limit is not None:
                clean_rows = clean_rows[:limit]
            if clean_rows:
                return clean_rows
        except Exception:
            pass

    related_jobs = get_related_jobs(especializacion_id, limit=20)
    if not related_jobs:
        return []

    skill_counts: dict[str, dict[str, Any]] = {}
    for job in related_jobs:
        empleo_id = str(job.get("empleo_id", "")).strip()
        if not empleo_id:
            continue
        pertinence = _safe_float(job.get("match_pertinencia", job.get("porcentaje_match", 0)))
        role_weight = _safe_float(job.get("afinidad_rol", 0))
        job_weight = 4 if pertinence >= 75 else 3 if pertinence >= 55 else 2 if role_weight >= 50 else 1
        for name in _job_catalog_skills(empleo_id, str(job.get("titulo_empleo", ""))):
            key = _skill_identity_key(name)
            entry = skill_counts.setdefault(key, {"skill_id": len(skill_counts) + 1, "nombre": name, "conteo": 0})
            generic_penalty = 0.75 if _skill_identity_key(name) in {"gestion", "analisis", "comunicacion", "liderazgo"} else 1.0
            entry["conteo"] = int(entry["conteo"]) + int(round(job_weight * generic_penalty))

    rows = list(skill_counts.values())
    rows.sort(key=lambda item: (-int(item["conteo"]), str(item["nombre"]).casefold()))
    if limit is not None:
        rows = rows[:limit]
    return rows


def get_skills_mercado(especializacion_id: int) -> list[dict[str, Any]]:
    return get_related_market_skill_rows(especializacion_id)


def get_brechas(especializacion_id: int) -> list[dict[str, Any]]:
    program_skills = {_skill_identity_key(str(row.get("nombre", "") or "")) for row in get_program_skill_rows(especializacion_id)}
    market_skills = get_related_market_skill_rows(especializacion_id)
    blocked_skills = _program_gap_blocklist(_resolve_program_id(especializacion_id))
    brechas = [
        row
        for row in market_skills
        if _skill_identity_key(str(row.get("nombre", "") or "")) not in program_skills
        and _skill_identity_key(str(row.get("nombre", "") or "")) not in blocked_skills
        and not _is_market_skill_noise(str(row.get("nombre", "") or ""))
    ]
    return brechas


def get_match(especializacion_id: int) -> float:
    row = get_programa(especializacion_id)
    if row:
        return round(_safe_float(row.get("promedio_match_mercado", 0)), 2)
    program_skills = get_program_skill_rows(especializacion_id)
    market_names = {_skill_identity_key(str(row.get("nombre", "") or "")) for row in get_related_market_skill_rows(especializacion_id)}
    if not program_skills:
        return 0.0
    common = sum(1 for row in program_skills if _skill_identity_key(str(row.get("nombre", "") or "")) in market_names)
    return round((common * 100.0) / len(program_skills), 2)


def get_related_jobs(especializacion_id: int, limit: int | None = 10) -> list[dict[str, Any]]:
    especializacion_id = _resolve_program_id(especializacion_id)
    program = _fetch_program_base_row(especializacion_id)
    role_text = str(program.get("rol") or "").strip() if program else ""
    program_roles = _program_role_candidates(program or {}, limit=6) if program else []
    program_skill_names = {
        _skill_identity_key(str(row.get("nombre", "") or "")): str(row.get("nombre", "")).strip()
        for row in get_program_skill_rows(especializacion_id)
        if str(row.get("nombre", "")).strip()
    }
    program_skill_total = len(program_skill_names)
    relation = _match_relation_name()
    if relation:
        rows = _fetch_all(
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
            LIMIT %s
            """,
            (especializacion_id, limit),
            db_name=PROGRAM_DB_NAME,
        )
    else:
        rows = _fallback_job_match_rows(especializacion_id, limit=limit)
    result: list[dict[str, Any]] = []
    for raw in rows:
        empleo_id = str(_row_value(raw, "empleo_id", default="") or "").strip()
        if not empleo_id:
            continue
        job_meta = _fetch_one(
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
            db_name=PROGRAM_DB_NAME,
        ) or {}
        titulo = _best_job_title(
            _row_value(raw, "titulo_empleo", default=""),
            job_meta.get("titulo", ""),
            job_meta.get("ubicacion", ""),
        )
        if not titulo:
            continue
        employment_skills = _job_catalog_skills(empleo_id, titulo, str(job_meta.get("ubicacion", "") or ""))
        common_count = int(_row_value(raw, "skills_en_comun", default=0) or 0)
        role_score, overlap_score, pertinence_score = _job_pertinence_score(
            program_roles,
            role_text,
            titulo,
            common_count,
            program_skill_total,
            int(_row_value(raw, "total_skills_empleo", default=0) or 0),
        )
        if pertinence_score < 30 and common_count < 2:
            continue
        role_label = _canonical_role_label(titulo) or _infer_role_from_title(titulo)
        skills_comunes = [
            program_skill_names[_skill_identity_key(skill_name)]
            for skill_name in employment_skills
            if _skill_identity_key(skill_name) in program_skill_names
        ]
        url = str(job_meta.get("url", "") or "").strip()
        source = str(job_meta.get("fuente", "") or "").strip()
        company = _clean_company_name(str(job_meta.get("empresa", "") or _row_value(raw, "empresa", default="") or ""))
        result.append(
            {
                "empleo_id": empleo_id,
                "titulo_empleo": titulo,
                "empresa": company or _platform_label(source, url),
                "plataforma": _platform_label(source, url),
                "ubicacion": str(job_meta.get("ubicacion", "") or ""),
                "url": url,
                "fecha": str(job_meta.get("fecha", "") or ""),
                "total_skills_empleo": int(_row_value(raw, "total_skills_empleo", default=0) or 0),
                "total_skills_especializacion": program_skill_total,
                "skills_en_comun": common_count,
                "porcentaje_match": round(pertinence_score, 2),
                "match_base": round(overlap_score, 2),
                "match_pertinencia": round(pertinence_score, 2),
                "afinidad_rol": role_score,
                "cargo_similar": role_label,
                "skills_comunes": ", ".join(sorted(skills_comunes)),
            }
        )
    if result:
        role_matched = [item for item in result if _safe_float(item.get("afinidad_rol", 0)) > 0]
        if role_matched:
            result = role_matched
    result.sort(
        key=lambda item: (
            -_safe_float(item.get("afinidad_rol", 0)),
            -_safe_float(item["porcentaje_match"]),
            -int(item["skills_en_comun"]),
            str(item["titulo_empleo"]).casefold(),
        )
    )
    return result[:limit] if limit is not None else result


def get_program_match_rows(limit: int | None = None) -> list[dict[str, Any]]:
    rows = get_programas()
    rows.sort(key=lambda item: (-item["promedio_match_mercado"], -item["total_empleos_relacionados"], item["nombre_especializacion"].casefold()))
    return rows[:limit] if limit is not None else rows


def get_top_programs_by_match(limit: int = 8) -> list[dict[str, Any]]:
    return get_program_match_rows(limit=limit)


def get_top_market_skills(limit: int = 10) -> list[dict[str, Any]]:
    relation = _match_relation_name()
    if not relation:
        jobs = _fetch_all(
            """
            SELECT
                id AS empleo_id,
                COALESCE(titulo, '') AS titulo,
                COALESCE(ubicacion, '') AS ubicacion
            FROM empleos
            ORDER BY id
            """,
            db_name=PROGRAM_DB_NAME,
        )
        counts: dict[str, dict[str, Any]] = {}
        for job in jobs:
            title = _best_job_title(job.get("titulo", ""), job.get("ubicacion", ""))
            for skill_name in _job_catalog_skills(job.get("empleo_id", ""), title, str(job.get("ubicacion", "") or "")):
                key = _skill_identity_key(skill_name)
                entry = counts.setdefault(key, {"skill_id": len(counts) + 1, "nombre": skill_name, "conteo": 0})
                entry["conteo"] = int(entry["conteo"]) + 1
        rows = list(counts.values())
        rows.sort(key=lambda item: (-int(item["conteo"]), str(item["nombre"]).casefold()))
        return rows[:limit]
    rows = _fetch_all(
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
        db_name=PROGRAM_DB_NAME,
    )
    return [_normalize_skill_row(row) for row in rows]


def get_top_roles_overall(programas: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    role_scores: dict[str, float] = {}
    for program in programas:
        suggestions = program.get("roles_sugeridos") or _program_role_hints(program, limit=3)
        for index, role in enumerate(suggestions[:3]):
            label = str(role.get("rol") or "").strip()
            if not label:
                continue
            share = _safe_float(role.get("share", 0))
            weight = share if share > 0 else max(1.0, 3.0 - (index * 0.75))
            role_scores[label] = role_scores.get(label, 0.0) + weight

    rows = [
        {"skill_id": idx + 1, "nombre": role, "conteo": round(weight, 2)}
        for idx, (role, weight) in enumerate(sorted(role_scores.items(), key=lambda item: (-item[1], item[0]))[:limit])
    ]
    return rows


def get_global_kpis() -> dict[str, Any]:
    return dashboard_service.global_kpis(get_programas(), db_name=PROGRAM_DB_NAME)


def _alignment_level(match: float) -> tuple[str, str]:
    return dashboard_service.alignment_level(match)


def _top_skill_names(rows: list[dict[str, Any]], limit: int = 5) -> list[str]:
    names: list[str] = []
    for row in rows:
        name = str(row.get("nombre", "")).strip()
        if name:
            names.append(name)
    return names[:limit]


def _normalize_tokens(text: str) -> set[str]:
    return scoring_service.normalize_tokens(text)


def _normalize_text_key(text: str) -> str:
    return normalization_service.basic_text_key(text)


def _title_affinity_score(program_role: str, title: str) -> float:
    return scoring_service.title_affinity_score(program_role, title)


def _role_affinity(program_role: str, related_jobs: list[dict[str, Any]]) -> tuple[float, list[str]]:
    if not program_role or not related_jobs:
        return 0.0, []

    matched_jobs: list[str] = []
    for job in related_jobs:
        title = str(job.get("titulo_empleo", "")).strip()
        if not title:
            continue
        if _title_affinity_score(program_role, title) > 0:
            matched_jobs.append(title)

    score = round((len(matched_jobs) * 100.0) / len(related_jobs), 2) if related_jobs else 0.0
    return score, matched_jobs[:5]


def _canonical_role_label(text: str) -> str:
    normalized = _normalize_text_key(text)
    if not normalized:
        return ""
    for role_name, keywords in ROLE_KEYWORDS:
        role_key = _normalize_text_key(role_name)
        if role_key and role_key in normalized:
            return role_name
        for keyword in keywords:
            keyword_key = _normalize_text_key(keyword)
            if keyword_key and keyword_key in normalized:
                return role_name
    return ""


def _program_role_candidates(program: dict[str, Any], limit: int = 4) -> list[str]:
    candidates: list[str] = []
    base_role = str(program.get("rol") or "").strip()
    if base_role:
        candidates.append(base_role)

    program_name = str(program.get("nombre_especializacion") or "").strip()
    source = " ".join([_normalize_text_key(program_name), _normalize_text_key(base_role)])
    for keyword, hinted_roles in PROGRAM_ROLE_HINTS:
        if keyword and keyword in source:
            candidates.extend(hinted_roles)

    for item in _program_role_hints(program, limit=limit):
        role_name = str(item.get("rol") or "").strip()
        if role_name:
            candidates.append(role_name)

    normalized: list[str] = []
    seen: set[str] = set()
    for role_name in candidates:
        canonical = _canonical_role_label(role_name) or role_name
        key = _normalize_text_key(canonical)
        if key and key not in seen:
            seen.add(key)
            normalized.append(canonical)
    return normalized


def _job_role_match_score(program_roles: list[str], title: str) -> float:
    if not program_roles or not title:
        return 0.0
    title_label = _canonical_role_label(title) or _infer_role_from_title(title)
    title_key = _normalize_text_key(title_label or title)
    best = 0.0
    for role_name in program_roles:
        role_label = _canonical_role_label(role_name) or role_name
        role_key = _normalize_text_key(role_label)
        if not role_key:
            continue
        if title_key and role_key == title_key:
            return 100.0
        best = max(best, _title_affinity_score(role_label, title))
        if title_label and role_key == _normalize_text_key(title_label):
            best = max(best, 100.0)
    return best


def _job_pertinence_score(
    program_roles: list[str],
    role_text: str,
    title: str,
    skills_en_comun: int,
    total_skills_programa: int,
    total_skills_empleo: int,
) -> tuple[float, float, float]:
    role_score = _job_role_match_score(program_roles, title)
    if role_score <= 0 and role_text:
        role_score = _title_affinity_score(role_text, title)
    return scoring_service.job_pertinence_score(
        role_score,
        skills_en_comun,
        total_skills_programa,
        total_skills_empleo,
    )


ROLE_KEYWORDS = [
    ("analista de datos", ["analista de datos", "data analyst", "visual analytics", "business intelligence", "bi analyst", "reporting"]),
    ("cientÃ­fico de datos", ["ciencia de datos", "data scientist", "machine learning", "modelado predictivo", "ia", "inteligencia artificial"]),
    ("ingeniero de datos", ["ingeniero de datos", "data engineer", "etl", "pipelines", "big data", "integraciÃ³n de datos"]),
    ("analista de negocio", ["analista de negocio", "business analyst", "analÃ­tica de negocio", "inteligencia de negocio"]),
    ("gestor de calidad", ["gestor de calidad", "calidad", "qa", "compliance", "auditor", "auditorÃ­a"]),
    ("gestor operativo", ["gestor operativo", "operativo", "coordinador", "logÃ­stica", "operaciones"]),
    ("gestor de proyectos", ["gestiÃ³n de proyectos", "project manager", "pm", "scrum", "project"]),
    ("analista comercial", ["ventas", "comercial", "crm", "cuentas", "customer success", "inside sales"]),
    ("docente y orientador", ["docente", "educaciÃ³n", "pedagog", "orientaciÃ³n", "orientador", "currÃ­culo"]),
    ("analista de soporte", ["soporte", "help desk", "aplicaciones", "mesa de ayuda", "it support"]),
    ("auditor", ["auditor", "fiscal", "tributario", "revisorÃ­a", "contable"]),
    ("desarrollador", ["desarrollador", "programador", "software", "full stack", "frontend", "backend"]),
    ("ingeniero", ["ingeniero", "arquitecto", "infraestructura", "ciberseguridad", "redes"]),
]

PROGRAM_ROLE_HINTS = [
    ("datos", ["analista de datos", "cientÃ­fico de datos", "ingeniero de datos"]),
    ("analytics", ["analista de datos", "analista de negocio", "cientÃ­fico de datos"]),
    ("big data", ["ingeniero de datos", "analista de datos", "cientÃ­fico de datos"]),
    ("inteligencia de negocio", ["analista de negocio", "analista de datos", "gestor operativo"]),
    ("visual analytics", ["analista de datos", "analista de negocio", "gestor de proyectos"]),
    ("ventas", ["analista comercial", "gestor comercial", "customer success"]),
    ("comercial", ["analista comercial", "gestor comercial", "customer success"]),
    ("gerencia", ["gestor operativo", "gestor de proyectos", "gestor de calidad"]),
    ("administracion", ["gestor operativo", "gestor de proyectos", "gestor de calidad"]),
    ("proyectos", ["gestor de proyectos", "gestor operativo", "gestor de calidad"]),
    ("educacion", ["docente y orientador", "coordinador acadÃ©mico", "gestor de proyectos"]),
    ("pedagog", ["docente y orientador", "coordinador acadÃ©mico", "gestor de proyectos"]),
    ("salud", ["gestor de calidad", "gestor operativo", "coordinador"]),
    ("seguridad", ["ingeniero", "analista de soporte", "gestor de calidad"]),
    ("ciber", ["ingeniero", "analista de soporte", "gestor de calidad"]),
    ("auditor", ["auditor", "gestor de calidad", "analista de cumplimiento"]),
    ("fiscal", ["auditor", "gestor de calidad", "analista de cumplimiento"]),
]


def _infer_role_from_title(title: str) -> str:
    normalized = _normalize_text_key(title or "")
    if not normalized:
        return ""
    for role_name, keywords in ROLE_KEYWORDS:
        for keyword in keywords:
            if _normalize_text_key(keyword) in normalized:
                return role_name
    return ""


def _program_role_suggestions(especializacion_id: int, related_jobs: list[dict[str, Any]] | None = None, limit: int = 4) -> list[dict[str, Any]]:
    program = _fetch_program_base_row(especializacion_id)
    if not program:
        return []

    jobs = list(related_jobs or [])
    relation = _match_relation_name()
    broader_jobs: list[dict[str, Any]] = []
    if relation:
        broader_jobs = _fetch_all(
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
            LIMIT 40
            """,
            (especializacion_id,),
            db_name=PROGRAM_DB_NAME,
        )
    else:
        broader_jobs = _fallback_job_match_rows(especializacion_id, limit=40)
    seen_titles = {_normalize_text_key(str(job.get("titulo_empleo", ""))) for job in jobs if str(job.get("titulo_empleo", "")).strip()}
    for job in broader_jobs:
        title_key = _normalize_text_key(str(job.get("titulo_empleo", "")))
        if title_key and title_key not in seen_titles:
            jobs.append(job)
            seen_titles.add(title_key)
    role_scores: dict[str, dict[str, Any]] = {}
    program_skill_names = [_normalize_text_key(row["nombre"]) for row in get_program_skill_rows(especializacion_id) if str(row.get("nombre", "")).strip()]

    for role_name, keywords in ROLE_KEYWORDS:
        normalized_keywords = [_normalize_text_key(keyword) for keyword in keywords]
        program_hits = sum(
            1
            for skill_name in program_skill_names
            if any(keyword and keyword in skill_name for keyword in normalized_keywords)
        )
        job_hits = 0
        best_match = 0.0
        for job in jobs or []:
            title = str(job.get("titulo_empleo", "")).strip()
            if not title:
                continue
            title_key = _normalize_text_key(title)
            if any(keyword and keyword in title_key for keyword in normalized_keywords):
                job_hits += 1
                best_match = max(best_match, _safe_float(job.get("porcentaje_match", 0)))
        if program_hits or job_hits:
            weight = (program_hits * 4.0) + (job_hits * 2.0) + (best_match / 10.0)
            role_scores[role_name] = {
                "rol": role_name,
                "peso": weight,
                "empleos": job_hits,
                "mejor_match": best_match,
            }

    for job in jobs or []:
        title = str(job.get("titulo_empleo", "")).strip()
        if not title:
            continue
        role_name = _infer_role_from_title(title)
        if not role_name:
            continue
        match_pct = _safe_float(job.get("porcentaje_match", 0))
        skills_common = int(job.get("skills_en_comun", 0) or 0)
        affinity = _safe_float(job.get("afinidad_rol", 0))
        weight = max(1.0, (skills_common * 2.0) + (match_pct / 12.0) + (affinity / 25.0))
        bucket = role_scores.setdefault(role_name, {"rol": role_name, "peso": 0.0, "empleos": 0, "mejor_match": 0.0})
        bucket["peso"] = float(bucket["peso"]) + weight
        bucket["empleos"] = int(bucket["empleos"]) + 1
        bucket["mejor_match"] = max(float(bucket["mejor_match"]), match_pct)

    base_role = str(program.get("rol") or "").strip()
    if base_role:
        base_key = _normalize_text_key(base_role)
        if base_key not in role_scores:
            support = 0.0
            support_jobs = 0
            for job in jobs or []:
                score = _title_affinity_score(base_role, str(job.get("titulo_empleo", "")))
                if score > 0:
                    support += score
                    support_jobs += 1
            role_scores[base_key] = {
                "rol": base_role,
                "peso": support or 0.1,
                "empleos": support_jobs,
                "mejor_match": 0.0,
            }
        else:
            role_scores[base_key]["rol"] = base_role

    program_name_key = _normalize_text_key(str(program.get("nombre_especializacion") or ""))
    hint_source = " ".join([program_name_key, _normalize_text_key(base_role), " ".join(program_skill_names)])
    for keyword, hinted_roles in PROGRAM_ROLE_HINTS:
        if keyword and keyword in hint_source:
            for index, role_name in enumerate(hinted_roles):
                bonus = max(0.75, 2.6 - (index * 0.45))
                bucket = role_scores.setdefault(role_name, {"rol": role_name, "peso": 0.0, "empleos": 0, "mejor_match": 0.0})
                bucket["peso"] = float(bucket["peso"]) + bonus
                bucket["mejor_match"] = max(float(bucket["mejor_match"]), bonus * 10)

    ranked = sorted(role_scores.values(), key=lambda item: (-float(item["peso"]), -int(item["empleos"]), str(item["rol"])))
    total_weight = sum(float(item["peso"]) for item in ranked) or 1.0
    suggestions: list[dict[str, Any]] = []
    for item in ranked[:limit]:
        weight = float(item["peso"])
        suggestions.append(
            {
                "rol": item["rol"],
                "empleos": int(item["empleos"]),
                "peso": round(weight, 2),
                "share": round((weight / total_weight) * 100.0, 1),
                "mejor_match": round(float(item["mejor_match"]), 2),
            }
        )
    return suggestions


def _program_role_hints(program: dict[str, Any], limit: int = 4) -> list[dict[str, Any]]:
    source = " ".join(
        [
            _normalize_text_key(str(program.get("nombre_especializacion") or "")),
            _normalize_text_key(str(program.get("rol") or "")),
        ]
    )
    score_map: dict[str, dict[str, Any]] = {}

    for keyword, hinted_roles in PROGRAM_ROLE_HINTS:
        if keyword and keyword in source:
            for index, role_name in enumerate(hinted_roles):
                bonus = max(0.75, 2.6 - (index * 0.45))
                bucket = score_map.setdefault(role_name, {"rol": role_name, "peso": 0.0})
                bucket["peso"] = float(bucket["peso"]) + bonus

    if not score_map:
        base_role = str(program.get("rol") or "").strip()
        if base_role:
            score_map[base_role] = {"rol": base_role, "peso": 2.5}

    ranked = sorted(score_map.values(), key=lambda item: (-float(item["peso"]), str(item["rol"])))
    total_weight = sum(float(item["peso"]) for item in ranked) or 1.0
    suggestions: list[dict[str, Any]] = []
    for item in ranked[:limit]:
        weight = float(item["peso"])
        suggestions.append(
            {
                "rol": item["rol"],
                "empleos": 0,
                "peso": round(weight, 2),
                "share": round((weight / total_weight) * 100.0, 1),
                "mejor_match": 0.0,
            }
        )
    return suggestions


def _render_role_chips(roles: list[dict[str, Any]] | list[str] | None) -> str:
    if not roles:
        return '<span class="muted">Sin roles sugeridos</span>'
    chips: list[str] = []
    for role in roles:
        if isinstance(role, dict):
            label = str(role.get("rol") or "").strip()
            empleos = int(role.get("empleos") or 0)
            share = role.get("share")
            if isinstance(share, (int, float)):
                extra = f"{float(share):.1f}%"
            elif empleos:
                extra = f"{empleos} empleos"
            else:
                extra = ""
        else:
            label = str(role).strip()
            extra = ""
        if not label:
            continue
        meta = f" - {extra}" if extra else ""
        chips.append(f'<span class="chip chip-role">{escape(label)}{escape(meta)}</span>')
    return "".join(chips) if chips else '<span class="muted">Sin roles sugeridos</span>'


def _match_band(match: float) -> tuple[str, str, str]:
    return dashboard_service.match_band(match)


def _bullet_items(items: list[str], empty_label: str) -> str:
    if not items:
        return f'<p class="muted">{escape(empty_label)}</p>'
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


def _group_related_jobs_by_role(related_jobs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for job in related_jobs or []:
        role = str(job.get("cargo_similar") or "").strip() or _infer_role_from_title(str(job.get("titulo_empleo", ""))) or "Otros roles"
        groups.setdefault(role, []).append(job)
    for role in groups:
        groups[role] = sorted(
            groups[role],
            key=lambda item: (-_safe_float(item.get("porcentaje_match", 0)), -int(item.get("skills_en_comun", 0) or 0), str(item.get("titulo_empleo", "")).casefold()),
        )
    return dict(sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])))


def _match_badge(match: float) -> str:
    label, tone, _ = _match_band(match)
    return f'<span class="match-badge {tone}">{escape(label)}</span>'


def _build_executive_analysis(
    program: dict[str, Any],
    program_skills: list[dict[str, Any]],
    market_skills: list[dict[str, Any]],
    brechas: list[dict[str, Any]],
    match: float,
    program_only_names: list[str],
    common_skill_keys: set[str],
    related_jobs: list[dict[str, Any]],
) -> str:
    level, level_text = _alignment_level(match)
    roles_sugeridos = program.get("roles_sugeridos") or _program_role_suggestions(
        int(program.get("especializacion_id", 0) or 0),
        related_jobs=related_jobs,
        limit=4,
    )
    role_labels = [str(item.get("rol") or "").strip() for item in roles_sugeridos if str(item.get("rol") or "").strip()]
    role_text = ", ".join(role_labels) if role_labels else str(program.get("rol") or "").strip()
    if roles_sugeridos:
        role_score = round(max(_safe_float(item.get("share", 0)) for item in roles_sugeridos), 2)
        role_matches = [f"{item['rol']} · {_fmt_pct(item.get('share', 0))}" for item in roles_sugeridos[:5]]
    else:
        role_score, role_matches = _role_affinity(role_text, related_jobs)
    aligned_names = sorted(
        {
            str(p.get("nombre", "")).strip()
            for p in program_skills
            if _normalize_text_key(p.get("nombre", "")) in common_skill_keys and str(p.get("nombre", "")).strip()
        },
        key=str.casefold,
    )
    market_top = _top_skill_names(market_skills, limit=5)
    brecha_top = _top_skill_names(brechas, limit=5)
    program_only_top = sorted(program_only_names, key=str.casefold)[:5]
    role_match_text = ", ".join(role_matches) if role_matches else "No se detectan cargos relacionados de forma clara con el rol."

    recommendations: list[str] = []
    if brecha_top:
        recommendations.append(f"Fortalecer de forma prioritaria habilidades como {', '.join(brecha_top[:3])}.")
    else:
        recommendations.append("Mantener la cobertura actual y revisar periódicamente las vacantes para detectar cambios en la demanda.")
    if program_only_top:
        recommendations.append(f"Revisar si contenidos como {', '.join(program_only_top[:3])} siguen siendo estratégicos o necesitan ajuste.")
    if market_top:
        recommendations.append(f"Tomar como referencia el mercado en {', '.join(market_top[:3])} para actualizar el plan de estudios.")

    aligned_text = ", ".join(aligned_names[:6]) if aligned_names else "No se detectan coincidencias fuertes entre el programa y el mercado."
    brecha_text = ", ".join(brecha_top) if brecha_top else "No se observan brechas relevantes dentro del conjunto de empleos relacionados."
    sobrantes_text = ", ".join(program_only_top) if program_only_top else "No hay habilidades claramente sobrantes en el programa."

    return f"""
    <section class="card analysis-panel">
      <div class="section-head">
        <div>
          <span class="eyebrow">Análisis ejecutivo</span>
          <h2>Lectura clara para toma de decisiones</h2>
          <p>Resumen estructurado para entender la alineación entre el programa, el mercado y las oportunidades de mejora.</p>
        </div>
        <span class="analysis-badge">{escape(level)}</span>
      </div>
      <div class="analysis-cards">
        <article class="analysis-card">
          <h3>Nivel de alineación</h3>
          <p>{escape(level_text)}</p>
          <div class="analysis-metric">{_fmt_pct(match)}</div>
        </article>
        <article class="analysis-card">
          <h3>Principales brechas</h3>
          <p>{escape(brecha_text)}</p>
        </article>
        <article class="analysis-card">
          <h3>Skills bien alineadas</h3>
          <p>{escape(aligned_text)}</p>
        </article>
        <article class="analysis-card">
          <h3>Skills poco conectadas</h3>
          <p>{escape(sobrantes_text)}</p>
        </article>
        <article class="analysis-card">
          <h3>Afinidad con los roles</h3>
          <p>{escape(role_text or 'No definido')}.</p>
          <p>{escape(role_match_text)}</p>
          <div class="analysis-metric">{_fmt_pct(role_score)}</div>
        </article>
      </div>
      <div class="analysis-reco">
        <h3>Recomendaciones concretas</h3>
        <ul>
          {''.join(f'<li>{escape(item)}</li>' for item in recommendations)}
        </ul>
      </div>
    </section>
    """


def _fmt_int(value: Any) -> str:
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def _fmt_pct(value: Any) -> str:
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return "0.00%"


def _safe_float(value: Any) -> float:
    return normalization_service.safe_float(value)


def _chip_cloud(items: list[Any], empty_label: str = "Sin datos", tone: str = "") -> str:
    if not items:
        return f'<span class="muted">{escape(empty_label)}</span>'
    tone_class = f" {tone}" if tone else ""
    return "".join(
        f'<span class="chip{tone_class}">{escape(str(item))}</span>'
        for item in items
    )


def _count_chip_cloud(rows: list[dict[str, Any]], empty_label: str = "Sin datos") -> str:
    if not rows:
        return f'<span class="muted">{escape(empty_label)}</span>'
    return "".join(
        f'<span class="chip">{escape(str(row["nombre"]))} Â· {_fmt_int(row["conteo"])} empleos</span>'
        for row in rows
    )


def _skill_chip_cloud(rows: list[dict[str, Any]], empty_label: str = "Sin datos") -> str:
    if not rows:
        return f'<span class="muted">{escape(empty_label)}</span>'
    return "".join(
        f'<span class="chip">{escape(str(row["nombre"]))} Â· {_fmt_int(row["conteo"])} empleos</span>'
        for row in rows
    )


def _kpi_card(label: str, value: str, note: str = "") -> str:
    note_html = f'<div class="muted" style="margin-top:8px">{escape(note)}</div>' if note else ""
    return f"""
        <article class="kpi">
          <span>{escape(label)}</span>
          <strong>{escape(value)}</strong>
          {note_html}
        </article>
    """


def _inline_icon(name: str, class_name: str = "") -> str:
    classes = " ".join(part for part in ("icon", class_name.strip()) if part)
    paths = {
        "summary": '<rect x="4" y="5" width="16" height="14" rx="2"></rect><path d="M8 9h8"></path><path d="M8 13h5"></path>',
        "alignment": '<path d="M12 3.5v8.5h8.5"></path><path d="M20.5 12A8.5 8.5 0 1 1 12 3.5"></path>',
        "market": '<path d="M7 8V6.5A1.5 1.5 0 0 1 8.5 5h7A1.5 1.5 0 0 1 17 6.5V8"></path><rect x="4" y="8" width="16" height="11" rx="2"></rect><path d="M4 12.5h16"></path>',
        "jobs": '<rect x="5" y="4.5" width="14" height="16" rx="2"></rect><path d="M9 4.5h6"></path><path d="M8 9.5h8"></path><path d="M8 13.5h8"></path>',
        "gap": '<path d="M12 4.5 19 18H5z"></path><path d="M12 9v4.2"></path><path d="M12 16h.01"></path>',
        "recommendations": '<path d="M12 4.5 14.1 8.7l4.6.7-3.3 3.2.8 4.5L12 14.9l-4.2 2.2.8-4.5-3.3-3.2 4.6-.7z"></path>',
        "program": '<path d="M3 9.5 12 5l9 4.5L12 14z"></path><path d="M7 11.3V15c0 .9 2.2 2 5 2s5-1.1 5-2v-3.7"></path><path d="M21 10v4"></path>',
        "check": '<circle cx="12" cy="12" r="7"></circle><path d="m9.2 12.1 1.9 1.9 3.7-4.1"></path>',
        "calendar": '<rect x="4" y="5.5" width="16" height="14" rx="2"></rect><path d="M8 3.8v3.4"></path><path d="M16 3.8v3.4"></path><path d="M4 9.5h16"></path>',
        "download": '<path d="M12 4.5v9"></path><path d="m8.8 10.7 3.2 3.3 3.2-3.3"></path><path d="M5 18.5h14"></path>',
        "arrow-right": '<path d="M5 12h14"></path><path d="m14 7 5 5-5 5"></path>',
        "role": '<circle cx="12" cy="8" r="3"></circle><path d="M6 18c1.3-2.5 3.4-4 6-4s4.7 1.5 6 4"></path>',
    }
    path_markup = paths.get(name)
    if not path_markup:
        return f'<span class="{classes} icon-text">{escape((name or "?")[:1].upper())}</span>'
    return (
        f'<svg class="{classes}" viewBox="0 0 24 24" aria-hidden="true" fill="none" '
        f'stroke="currentColor" stroke-width="1.9" stroke-linecap="round" '
        f'stroke-linejoin="round">{path_markup}</svg>'
    )


def _icon_markup(icon: str) -> str:
    icon_names = {
        "summary",
        "alignment",
        "market",
        "jobs",
        "gap",
        "recommendations",
        "program",
        "check",
        "calendar",
        "download",
        "arrow-right",
        "role",
    }
    if icon in icon_names:
        return _inline_icon(icon)
    return f'<span class="metric-card__glyph">{escape(icon)}</span>'


def _metric_tile(label: str, value: str, note: str, accent: str, progress: float, icon: str = "â€¢") -> str:
    width = max(0.0, min(100.0, _safe_float(progress)))
    return f"""
        <article class="metric-card">
          <div class="metric-card__header">
            <div class="metric-card__icon" style="background:{accent};">{_icon_markup(icon)}</div>
            <div>
              <strong>{escape(value)}</strong>
              <span>{escape(label)}</span>
            </div>
          </div>
          <p>{escape(note)}</p>
          <div class="metric-bar"><i style="width:{width}%; background:{accent};"></i></div>
        </article>
    """


def _chart_card(title: str, subtitle: str, canvas_id: str, wide: bool = False) -> str:
    width_class = " wide" if wide else ""
    return f"""
        <section class="card chart-card{width_class}">
          <div class="section-head">
            <div>
              <h2>{escape(title)}</h2>
              <p>{escape(subtitle)}</p>
            </div>
          </div>
          <div class="chart-wrap">
            <canvas id="{escape(canvas_id)}"></canvas>
          </div>
        </section>
    """


def _program_bar_rank_card(rows: list[dict[str, Any]]) -> str:
    if not rows:
        items = '<div class="empty">No hay programas para graficar.</div>'
    else:
        max_value = max([_safe_float(row.get("porcentaje_match", 0)) for row in rows] or [1.0]) or 1.0
        items = "".join(
            f"""
            <li class="rank-bar-item">
              <a class="rank-bar-item__label" href="{url_for('dashboard', especializacion_id=row['especializacion_id'])}">
                {escape(str(row['nombre_especializacion']))}
              </a>
              <div class="rank-bar-item__track">
                <i style="width:{max(4.0, min(100.0, (_safe_float(row.get('porcentaje_match', 0)) / max_value) * 100.0)):.2f}%;"></i>
              </div>
              <strong>{_fmt_pct(row.get('porcentaje_match', 0))}</strong>
            </li>
            """
            for row in rows
        )
    return f"""
        <section class="card chart-card rank-bar-card">
          <div class="section-head">
            <div>
              <h2>Programas mejor alineados</h2>
              <p>Ranking de especializaciones con mejor encaje frente al mercado.</p>
            </div>
          </div>
          <ul class="rank-bar-list">{items}</ul>
        </section>
    """


def _summary_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<div class="empty">No hay especializaciones para mostrar.</div>'

    table_rows = []
    for row in rows:
        gap_count = max(int(row["total_skills_programa"]) - int(row["skills_cubiertas"]), 0)
        link = url_for("dashboard", especializacion_id=row["especializacion_id"])
        roles_html = _render_role_chips(row.get("roles_sugeridos") or ([row["rol"]] if row.get("rol") else None))
        table_rows.append(
            f"""
            <tr>
              <td><a href="{link}"><strong>{escape(str(row["nombre_especializacion"]))}</strong></a></td>
              <td>{roles_html}</td>
              <td>{_fmt_int(row["total_skills_programa"])}</td>
              <td>{_fmt_int(row["skills_cubiertas"])}</td>
              <td>{_fmt_int(gap_count)}</td>
              <td>{_fmt_pct(row["porcentaje_match"])}</td>
            </tr>
            """
        )

    return f"""
    <section class="card">
      <div class="section-head">
        <div>
          <h2>Resumen por especializaciÃ³n</h2>
          <p>RelaciÃ³n entre habilidades del programa y habilidades presentes en el mercado laboral.</p>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Programa</th>
              <th>Roles sugeridos</th>
              <th>Skills programa</th>
              <th>Skills cubiertas</th>
              <th>Brechas</th>
              <th>Match</th>
            </tr>
          </thead>
          <tbody>
            {''.join(table_rows)}
          </tbody>
        </table>
      </div>
    </section>
    """


def _selector_card(programas: list[dict[str, Any]], selected_id: int | None) -> str:
    option_tags = ['<option value="">Seleccione una especialización</option>']
    for program in programas:
        option_id = int(program["especializacion_id"])
        selected_attr = " selected" if selected_id == option_id else ""
        option_tags.append(
            f'<option value="{option_id}"{selected_attr}>{escape(str(program["nombre_especializacion"]))}</option>'
        )

    mode_label = "Cambiar especializacion"
    clear_button = (
        ""
        if selected_id is None
        else f'<button type="button" class="button secondary" onclick="window.location.href=\'{url_for("dashboard")}\';">Ver general</button>'
    )

    return f"""
    <section class="selector-card" id="selector">
      <div class="selector-copy">
        <span class="eyebrow">{escape(mode_label)}</span>
        <p>Selecciona una especializacion para actualizar el informe y comparar su encaje con el mercado laboral.</p>
      </div>
      <form method="get" action="{url_for('dashboard')}" class="selector-form">
        <div>
          <label for="especializacion_id">Especialización</label>
          <select id="especializacion_id" name="especializacion_id" onchange="this.form.submit()">
            {''.join(option_tags)}
          </select>
        </div>
        <button type="submit">Actualizar vista</button>
        {clear_button}
      </form>
    </section>
    """


def _chart_payload_script(charts: list[dict[str, Any]]) -> str:
    payload = json.dumps(charts, ensure_ascii=False)
    return f"""
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <script>
      const executiveValueLabels = {{
        id: 'executiveValueLabels',
        afterDatasetsDraw(chart, args, pluginOptions) {{
          if (chart.config.type !== 'bar') return;
          const {{ ctx, chartArea }} = chart;
          const suffix = (pluginOptions && pluginOptions.suffix) || '';
          const prefix = (pluginOptions && pluginOptions.prefix) || '';
          const color = (pluginOptions && pluginOptions.color) || '#102033';
          ctx.save();
          ctx.fillStyle = color;
          ctx.font = '700 11px Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
          ctx.textBaseline = 'middle';
          ctx.textAlign = 'left';
          chart.data.datasets.forEach((dataset, datasetIndex) => {{
            const meta = chart.getDatasetMeta(datasetIndex);
            meta.data.forEach((element, index) => {{
              const rawValue = dataset.data[index];
              if (rawValue === null || rawValue === undefined || rawValue === '') return;
              const value = Number(rawValue);
              const label = `${{prefix}}${{Number.isFinite(value) ? value.toFixed(0) : rawValue}}${{suffix}}`;
              const position = element.tooltipPosition();
              const y = position.y;
              const x = chart.config.options.indexAxis === 'y'
                ? Math.min(position.x + 10, chartArea.right - 4)
                : position.x;
              if (chart.config.options.indexAxis === 'y') {{
                ctx.textAlign = 'left';
                ctx.fillText(label, x, y);
              }} else {{
                ctx.textAlign = 'center';
                ctx.fillText(label, x, Math.max(chartArea.top + 10, y - 10));
              }}
            }});
          }});
          ctx.restore();
        }}
      }};
      const charts = {payload};
      for (const item of charts) {{
        const canvas = document.getElementById(item.id);
        if (!canvas) continue;
        const config = item.config;
        config.plugins = config.plugins || [];
        config.plugins.push(executiveValueLabels);
        new Chart(canvas, config);
      }}
    </script>
    """


def _bar_chart_config(
    labels: list[str],
    values: list[float],
    label: str,
    *,
    horizontal: bool = False,
    color: str = "rgba(15, 76, 129, 0.82)",
    border_color: str = "rgba(15, 76, 129, 1)",
    suggested_max: float | None = None,
    value_suffix: str = "",
) -> dict[str, Any]:
    options: dict[str, Any] = {
        "responsive": True,
        "maintainAspectRatio": False,
        "plugins": {
            "legend": {"display": False},
            "tooltip": {"enabled": False},
            "executiveValueLabels": {"suffix": value_suffix},
        },
        "scales": {
            "x": {"beginAtZero": True, "grid": {"display": False}, "border": {"display": False}, "ticks": {"display": False}},
            "y": {"grid": {"display": False}, "border": {"display": False}, "ticks": {"color": "#506174", "font": {"size": 12, "weight": "600"}}},
        },
    }
    if horizontal:
        options["indexAxis"] = "y"
    if suggested_max is not None:
        options["scales"]["x"]["suggestedMax"] = suggested_max
    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": label,
                    "data": values,
                    "backgroundColor": color,
                    "borderColor": border_color,
                    "borderWidth": 1,
                    "borderRadius": 10,
                    "maxBarThickness": 28,
                }
            ],
        },
        "options": options,
    }


def _doughnut_chart_config(labels: list[str], values: list[float]) -> dict[str, Any]:
    colors = [
        "rgba(15, 76, 129, 0.9)",
        "rgba(29, 127, 211, 0.88)",
        "rgba(15, 157, 88, 0.88)",
        "rgba(245, 158, 11, 0.88)",
    ]
    return {
        "type": "doughnut",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "data": values,
                    "backgroundColor": colors[: len(values)],
                    "borderColor": "#ffffff",
                    "borderWidth": 2,
                    "hoverOffset": 6,
                }
            ],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "cutout": "64%",
            "plugins": {"legend": {"display": False}, "tooltip": {"enabled": False}},
        },
    }


BASE_TEMPLATE_NAME = "dashboard/base.html"

def render_page(title: str, subtitle: str, body: str, active: str = "dashboard", scripts: str = "", sidebar_extra: str = ""):
    return render_template(
        BASE_TEMPLATE_NAME,
        title=title,
        subtitle=subtitle,
        body=body,
        active=active,
        dashboard_url=url_for("dashboard"),
        scripts=scripts,
        sidebar_extra=sidebar_extra,
    )


def _general_dashboard_body(programas: list[dict[str, Any]], selected_id: int | None) -> tuple[str, str]:
    global_kpis = get_global_kpis()
    top_programs = get_top_programs_by_match(limit=8)
    top_market_skills = get_top_market_skills(limit=10)
    top_roles = get_top_roles_overall(programas, limit=8)
    today_label = date.today().strftime("%d/%m/%Y")
    count_scale = max(
        int(global_kpis.get("total_programas", 0) or 0),
        int(global_kpis.get("total_empleos_relacionados", 0) or 0),
        1,
    )

    charts = [
        {
            "id": "chart-top-market-skills",
            "config": _bar_chart_config(
                [row["nombre"] for row in top_market_skills],
                [_safe_float(row["conteo"]) for row in top_market_skills],
                "Empleos que la demandan",
                horizontal=True,
                color="rgba(29, 127, 211, 0.82)",
                border_color="rgba(29, 127, 211, 1)",
            ),
        },
        {
            "id": "chart-top-roles",
            "config": _bar_chart_config(
                [row["nombre"] for row in top_roles],
                [_safe_float(row["conteo"]) for row in top_roles],
                "Peso acumulado",
                horizontal=True,
                color="rgba(25, 160, 255, 0.82)",
                border_color="rgba(25, 160, 255, 1)",
            ),
        },
    ]

    top_program_badges = "".join(
        f'<span class="chip chip-role">{escape(str(row["nombre_especializacion"]))}</span>'
        for row in top_programs[:8]
    ) or '<span class="muted">Sin programas para mostrar</span>'

    body = f"""
    <div class="stack">
      <section class="report-header">
        <div class="report-header__copy">
          <div class="report-header__eyebrow">Cuadro de control</div>
          <h1 class="report-header__title">Observatorio de especializaciones</h1>
          <p class="report-header__subtitle">
            Resumen ejecutivo del portafolio académico frente al mercado laboral.
            Identifica dónde la oferta educativa tiene mejor encaje y qué habilidades concentran la demanda.
          </p>
        </div>
        <div class="report-header__actions">
          <div class="report-header__meta">Última actualización: {escape(today_label)}</div>
          <a class="button secondary report-download" href="#graficos">Explorar gráficos</a>
        </div>
      </section>
      <section class="metric-grid" id="kpis">
        {_metric_tile('Programas', _fmt_int(global_kpis['total_programas']), 'Especializaciones evaluadas en el observatorio', 'rgba(0, 84, 159, 0.14)', (int(global_kpis['total_programas']) / count_scale) * 100, 'program')}
        {_metric_tile('Promedio global de match', _fmt_pct(global_kpis['promedio_global_match']), 'Alineación media entre programas y mercado', 'rgba(0, 143, 189, 0.14)', _safe_float(global_kpis['promedio_global_match']), 'alignment')}
        {_metric_tile('Mejor match global', _fmt_pct(global_kpis['mejor_match_global']), 'Programa con mayor encaje observado', 'rgba(0, 163, 200, 0.14)', _safe_float(global_kpis['mejor_match_global']), 'check')}
        {_metric_tile('Empleos relacionados', _fmt_int(global_kpis['total_empleos_relacionados']), 'Vacantes que aportan lectura de mercado', 'rgba(0, 84, 159, 0.12)', (int(global_kpis['total_empleos_relacionados']) / count_scale) * 100, 'jobs')}
      </section>
      <section class="chart-grid" id="graficos">
        {_program_bar_rank_card(top_programs)}
        {_chart_card('Skills más demandadas', 'Habilidades que aparecen con mayor frecuencia en las vacantes.', 'chart-top-market-skills')}
        {_chart_card('Roles objetivo más frecuentes', 'Familias de cargos sugeridas para las especializaciones.', 'chart-top-roles', wide=True)}
      </section>
      <section class="card" id="roles">
        <div class="section-head">
          <div>
            <h2>Programas mejor posicionados</h2>
            <p>Especializaciones con mayor alineación global y mayor tracción con el mercado.</p>
          </div>
        </div>
        <div class="chip-cloud">{top_program_badges}</div>
      </section>
    </div>
    """

    scripts = _chart_payload_script(charts)
    return body, scripts


def _program_dashboard_body(
    programas: list[dict[str, Any]],
    selected_id: int,
) -> tuple[str, str] | tuple[str, str, int]:
    program = get_programa(selected_id)
    if not program:
        body = f"""
        <div class="stack">
          <section class="card">
            <h2>Programa no encontrado</h2>
            <p class="muted">No existe una especialización con ID {selected_id}.</p>
            <div class="hero-links" style="margin-top:14px">
              <a class="primary" href="{url_for('dashboard')}">Volver al dashboard general</a>
            </div>
          </section>
        </div>
        """
        return body, "", 404

    program_skills = get_skills_programa(selected_id)
    market_skills = get_skills_mercado(selected_id)
    brechas = get_brechas(selected_id)
    related_jobs = get_related_jobs(selected_id, limit=10)
    match = get_match(selected_id)
    today_label = date.today().strftime("%d/%m/%Y")

    program_skill_map = {_normalize_text_key(row["nombre"]): str(row["nombre"]).strip() for row in program_skills if str(row.get("nombre", "")).strip()}
    market_skill_map = {_normalize_text_key(row["nombre"]): str(row["nombre"]).strip() for row in market_skills if str(row.get("nombre", "")).strip()}
    program_skill_names = sorted(program_skill_map.values(), key=str.casefold)
    market_skill_names = sorted(market_skill_map.values(), key=str.casefold)
    common_skill_keys = set(program_skill_map) & set(market_skill_map)
    program_only_names = sorted(
        [original for key, original in program_skill_map.items() if key not in market_skill_map],
        key=str.casefold,
    )
    common_skill_names = sorted(
        [program_skill_map[key] for key in common_skill_keys],
        key=str.casefold,
    )
    role_suggestions = program.get("roles_sugeridos") or _program_role_suggestions(selected_id, related_jobs=related_jobs, limit=4)

    top_related_market_skills = sorted(
        market_skills,
        key=lambda row: (-int(row.get("conteo", 0)), str(row.get("nombre", "")).casefold()),
    )[:5]
    top_gap_rows = sorted(
        brechas,
        key=lambda row: (-int(row.get("conteo", 0)), str(row.get("nombre", "")).casefold()),
    )[:5]
    example_jobs = sorted(
        related_jobs,
        key=lambda row: (
            0 if str(row.get("url", "") or "").strip() else 1,
            -_safe_float(row.get("porcentaje_match", 0)),
            str(row.get("titulo_empleo", "")).casefold(),
        ),
    )[:5]
    level_label, level_tone, _level_key = _match_band(match)
    tone_class = {"good": "high", "warn": "medium", "bad": "low"}.get(level_tone, "medium")
    ring_color = {"good": "#25a55f", "warn": "#ffb41f", "bad": "#ef4444"}.get(level_tone, "#ffb41f")
    gap_focus = ", ".join(row["nombre"] for row in top_gap_rows[:3]) if top_gap_rows else "habilidades analiticas y herramientas de mercado"
    market_focus = ", ".join(row["nombre"] for row in top_related_market_skills[:3]) if top_related_market_skills else "las habilidades mas repetidas en las vacantes"
    summary_copy_html = (
        f'El programa presenta una alineacion <strong class="report-tone report-tone--{tone_class}">{escape(level_label.upper())}</strong> '
        f'con el mercado laboral. Existen oportunidades para fortalecer {escape(gap_focus)} y consolidar {escape(market_focus)}.'
    )

    insight_items: list[str] = []
    if top_related_market_skills:
        insight_items.append(f"Alta demanda de {', '.join([row['nombre'] for row in top_related_market_skills[:3]])}.")
    if top_gap_rows:
        insight_items.append(f"Las brechas mas visibles estan en {', '.join([row['nombre'] for row in top_gap_rows[:3]])}.")
    if role_suggestions:
        insight_items.append(f"El programa ya conversa con roles como {', '.join([item['rol'] for item in role_suggestions[:3]])}.")
    if not insight_items:
        insight_items.append("No se identificaron senales claras para priorizar en esta vista.")

    gap_max = max([int(row.get("conteo", 0) or 0) for row in top_gap_rows] or [1])
    market_max = max([int(row.get("conteo", 0) or 0) for row in top_related_market_skills] or [1])

    priority_rows_html = "".join(
        f"""
        <li class="report-bar-item">
          <div class="report-bar-item__meta">
            <span class="report-avatar report-avatar--danger">{escape(str(row['nombre'])[:2].upper())}</span>
            <span class="priority-list__label">{escape(str(row['nombre']))}</span>
          </div>
          <div class="priority-list__track report-bar-track report-bar-track--danger"><i style="width:{max(12, min(100, (int(row.get('conteo', 0) or 0) / gap_max) * 100))}%;"></i></div>
          <strong>{_fmt_int(row['conteo'])}</strong>
        </li>
        """
        for row in top_gap_rows
    ) or '<li class="report-bar-item"><div class="report-bar-item__meta"><span class="report-avatar report-avatar--danger">--</span><span class="priority-list__label">Sin brechas criticas</span></div><div class="priority-list__track report-bar-track report-bar-track--danger"><i style="width:0%;"></i></div><strong>0</strong></li>'

    market_skill_rows_html = "".join(
        f"""
        <li class="report-bar-item">
          <div class="report-bar-item__meta">
            <span class="report-avatar report-avatar--success">{escape(str(row['nombre'])[:2].upper())}</span>
            <span class="priority-list__label">{escape(str(row['nombre']))}</span>
          </div>
          <div class="priority-list__track report-bar-track report-bar-track--success"><i style="width:{max(12, min(100, (int(row.get('conteo', 0) or 0) / market_max) * 100))}%;"></i></div>
          <strong>{_fmt_int(row['conteo'])}</strong>
        </li>
        """
        for row in top_related_market_skills
    ) or '<li class="report-bar-item"><div class="report-bar-item__meta"><span class="report-avatar report-avatar--success">--</span><span class="priority-list__label">Sin habilidades de mercado</span></div><div class="priority-list__track report-bar-track report-bar-track--success"><i style="width:0%;"></i></div><strong>0</strong></li>'

    def _job_skill_badges(raw_skills: Any) -> str:
        items = [item.strip() for item in str(raw_skills or "").split(",") if item.strip()]
        if not items:
            return '<span class="muted">Sin skills clave visibles</span>'
        return "".join(f'<span class="chip">{escape(item)}</span>' for item in items[:3])

    program_skill_rows_html = "".join(
        f"""
        <li class="program-skill-list__item report-skill-row">
          <div class="program-skill-list__meta">
            <span class="program-skill-list__dot {'is-aligned' if _normalize_text_key(skill) in common_skill_keys else ''}">{_inline_icon('program')}</span>
            <div class="program-skill-list__copy">
              <strong>{escape(skill)}</strong>
              <small>{'Alineada con el mercado' if _normalize_text_key(skill) in common_skill_keys else 'Cobertura interna del programa'}</small>
            </div>
          </div>
          <div class="program-skill-list__line"><i style="width:{100 if _normalize_text_key(skill) in common_skill_keys else 72}%;"></i></div>
        </li>
        """
        for skill in program_skill_names[:5]
    ) or '<li class="empty">Sin skills del programa para mostrar.</li>'

    top_role_html = "".join(
        f"""
        <article class="role-list__item role-rank">
          <div class="role-rank__meta">
            <span class="role-rank__icon">{_inline_icon('role')}</span>
            <div>
              <strong>{escape(str(item.get('rol') or 'Rol sugerido'))}</strong>
              <span>Frecuencia relativa en vacantes relacionadas</span>
            </div>
          </div>
          <div class="role-list__score">{float(item.get('share', 0) or 0):.1f}%</div>
        </article>
        """
        for item in role_suggestions[:4]
    ) or '<div class="empty">No hay roles relacionados para mostrar.</div>'

    example_jobs_html = "".join(
        f"""
        <article class="vacancy-card">
          <div>
            <strong class="vacancy-card__title">{escape(str(row['titulo_empleo']))}</strong>
            <div class="vacancy-card__meta">
              <span>{escape(str(row.get('empresa') or row.get('plataforma') or 'Portal de empleo'))}</span>
              <span>{escape(str(row.get('ubicacion') or 'Colombia'))}</span>
              <span>{escape(str(row.get('plataforma') or 'Vacante activa'))}</span>
              <span>{_match_badge(_safe_float(row.get('porcentaje_match', 0)))}</span>
            </div>
            <div class="job-skills-inline vacancy-card__skills">{_job_skill_badges(row.get('skills_comunes'))}</div>
          </div>
          <a class="vacancy-card__apply {'is-disabled' if not str(row.get('url', '') or '').strip() else ''}" href="{escape(str(row.get('url', '') or '#'))}" target="_blank" rel="noopener noreferrer">Aplicar</a>
        </article>
        """
        for row in example_jobs
    ) or '<div class="empty">No hay vacantes activas relacionadas para mostrar.</div>'

    recommendations = {
        "Ajustes prioritarios": [
            f"Fortalecer {', '.join([row['nombre'] for row in top_gap_rows[:3]]) or 'las habilidades criticas'} en contenidos y talleres.",
            f"Revisar si {', '.join(program_only_names[:3]) or 'los contenidos menos conectados'} necesitan ajuste o reubicacion.",
        ],
        "Mejoras estrategicas": [
            f"Incorporar como referencia {', '.join([row['nombre'] for row in top_related_market_skills[:3]]) or 'las habilidades mas demandadas'} en el plan de estudios.",
            f"Alinear la narrativa del programa con roles como {', '.join([item['rol'] for item in role_suggestions[:3]]) or 'los cargos objetivo'}.",
        ],
        "Oportunidad de posicionamiento": [
            "Usar las vacantes y roles de referencia como evidencia de salida laboral y pertinencia academica.",
            "Comunicar con claridad los roles donde el programa ya muestra mejor encaje.",
        ],
    }

    recommendations_html = "".join(
        f"""
        <article class="recommendation">
          <h3>{escape(title)}</h3>
          <details>
            <summary>Ver más</summary>
            {_bullet_items(items, empty_label='Sin recomendaciones')}
          </details>
        </article>
        """
        for title, items in recommendations.items()
    )

    summary_pills = "".join(
        [
            f'<div class="executive-summary__pill">Rol base: {escape(str(program.get("rol") or "No definido"))}</div>',
            f'<div class="executive-summary__pill">Skills alineadas: {escape(_fmt_int(len(common_skill_names)))}</div>',
            f'<div class="executive-summary__pill">Vacantes relacionadas: {escape(_fmt_int(program.get("total_empleos_relacionados", len(related_jobs))))}</div>',
        ]
    )

    body = f"""
    <div class="program-report stack">
      <section class="program-report__header">
        <div class="program-report__copy">
          <div class="program-report__title-row">
            <h1 class="program-report__title">{escape(str(program['nombre_especializacion']))}</h1>
            <span class="program-report__badge">Especializacion</span>
          </div>
          <p class="program-report__subtitle">Análisis de alineación del programa con el mercado laboral.</p>
        </div>
        <div class="program-report__actions">
          <div class="program-report__meta">{_inline_icon('calendar')}<span>Última actualización: {escape(today_label)}</span></div>
          <a class="button secondary program-report__download" href="#recomendaciones">{_inline_icon('download')}<span>Descargar reporte</span></a>
        </div>
      </section>

      <section class="program-overview" id="resumen">
        <div class="program-overview__summary">
          <div class="program-overview__eyebrow">Resumen ejecutivo</div>
          <h2 class="program-overview__headline">Alineación del programa con el mercado</h2>
          <p class="program-overview__copy">{summary_copy_html}</p>
          <div class="executive-summary__meta">{summary_pills}</div>
        </div>
        <div class="program-overview__score">
          <div class="score-ring" style="--value:{max(0.0, min(100.0, _safe_float(match))):.2f}%; --ring-color:{ring_color};">
            <div class="score-ring__inner">
              <strong>{_fmt_pct(match)}</strong>
              <span>Alineación</span>
            </div>
          </div>
          <span class="report-badge report-badge--{tone_class}">{escape(level_label.upper())}</span>
        </div>
        <div class="program-overview__highlights" id="alineacion">
          <div class="program-overview__highlights-title">{_inline_icon('recommendations')}<span>Claves principales</span></div>
          <ul class="program-highlight-list">
            {''.join(f'<li>{_inline_icon("check")}<span>{escape(text)}</span></li>' for text in insight_items[:3])}
          </ul>
        </div>
      </section>

      <section class="metric-grid" id="kpis">
        {_metric_tile('% alineación', _fmt_pct(match), 'Alineación del programa', 'rgba(60, 132, 244, 0.12)', _safe_float(match), 'alignment')}
        {_metric_tile('Skills en el programa', _fmt_int(len(program_skill_names)), 'Habilidades activas en la especialización', 'rgba(59, 130, 246, 0.12)', min(100.0, float(len(program_skill_names)) * 18.0), 'program')}
        {_metric_tile('Skills en el mercado', _fmt_int(len(market_skill_names)), 'Habilidades visibles en vacantes relacionadas', 'rgba(34, 197, 94, 0.12)', min(100.0, float(len(market_skill_names)) * 12.0), 'market')}
        {_metric_tile('Brechas críticas', _fmt_int(len(brechas)), 'Habilidades que conviene priorizar', 'rgba(248, 113, 113, 0.12)', min(100.0, float(len(brechas)) * 18.0), 'gap')}
      </section>

      <section class="analysis-layout analysis-layout--figma">
        <article class="analysis-block report-panel" id="brechas">
          <h2>Brechas prioritarias</h2>
          <p class="lead">Habilidades que el mercado demanda y el programa no cubre o tiene baja presencia.</p>
          <ul class="priority-list">{priority_rows_html}</ul>
          <a class="report-panel__link" href="#recomendaciones"><span>Ver todas las brechas</span>{_inline_icon('arrow-right')}</a>
        </article>
        <article class="analysis-block report-panel" id="mercado-laboral">
          <h2>Skills mas demandadas en el mercado</h2>
          <p class="lead">Habilidades que aparecen con mas frecuencia en los empleos relacionados.</p>
          <ul class="priority-list">{market_skill_rows_html}</ul>
          <a class="report-panel__link" href="#empleos"><span>Ver habilidades y empleos</span>{_inline_icon('arrow-right')}</a>
        </article>
        <article class="analysis-block report-panel">
          <h2>Skills del programa</h2>
          <p class="lead">Habilidades actuales incluidas en la especializacion.</p>
          <ul class="program-skill-list">{program_skill_rows_html}</ul>
          <a class="report-panel__link" href="#recomendaciones"><span>Ver detalle del programa</span>{_inline_icon('arrow-right')}</a>
        </article>
      </section>

      <section class="employment-grid" id="empleos">
        <article class="job-group report-panel" id="roles">
          <h2>Top roles del mercado</h2>
          <p>Roles mas frecuentes asociados a esta especializacion.</p>
          <div class="role-list">{top_role_html}</div>
          <a class="report-panel__link" href="#recomendaciones"><span>Ver todos los roles</span>{_inline_icon('arrow-right')}</a>
        </article>
        <article class="job-group report-panel">
          <h2>Vacantes disponibles para aplicar</h2>
          <p>Ofertas activas relacionadas con esta especializacion y sus skills clave.</p>
          <div class="vacancy-list">{example_jobs_html}</div>
          <a class="report-panel__link" href="#recomendaciones"><span>Ver recomendaciones de preparacion</span>{_inline_icon('arrow-right')}</a>
        </article>
      </section>

      <section class="recommendation-grid" id="recomendaciones">
        {recommendations_html}
      </section>
    </div>
    """

    return body, ""


REGISTRATION_AREA_OPTIONS = ["Datos", "Tecnología", "Negocios", "Operaciones"]
REGISTRATION_ROLE_OPTIONS = [
    "Analista de datos",
    "Business Intelligence",
    "Científico de datos",
    "Ingeniero de datos",
    "Desarrollador de software",
    "Arquitecto de soluciones",
    "Product Manager",
    "Consultor de negocio",
    "Gestión estratégica",
    "Líder de operaciones",
]
REGISTRATION_GOAL_OPTIONS = [
    "Encontrar empleo",
    "Cambiar de rol",
    "Mejorar perfil profesional",
    "Estudiar un programa",
]
REGISTRATION_AVAILABILITY_OPTIONS = [
    "Activamente buscando empleo",
    "Abierto a oportunidades",
    "No buscando",
]
REGISTRATION_AREA_KEYWORDS = {
    "datos": ("datos", "data", "analytics", "analítica", "analitica", "bi", "business intelligence"),
    "tecnología": ("software", "tecnología", "tecnologia", "cloud", "devops", "arquitectura", "sistemas"),
    "negocios": ("negocio", "gerencia", "comercial", "ventas", "estratégica", "estrategica", "marketing"),
    "operaciones": ("operaciones", "calidad", "proyectos", "procesos", "productividad", "supply"),
}


def ensure_mentor_registration_schema() -> None:
    alumni_service.ensure_mentor_registration_schema(db_name=PROGRAM_DB_NAME)


def _registration_program_lookup(programas: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return alumni_service.program_lookup(programas)


def _registration_split_name(full_name: str) -> tuple[str, str]:
    return alumni_service.split_name(full_name)


def _registration_csv_values(raw: Any) -> list[str]:
    return alumni_service.csv_values(raw)


def _registration_csv_text(raw: Any) -> str:
    return alumni_service.csv_text(raw)


def _registration_skill_suggestions() -> list[str]:
    static_labels = [
        "SQL",
        "Excel",
        "Power BI",
        "Python",
        "Tableau",
        "ETL",
        "Big Data",
        "Cloud",
        "Gestión de proyectos",
        "Data Analysis",
        "Business Intelligence",
        "Visual Analytics",
    ]
    dynamic_labels = [str(row.get("nombre", "")).strip() for row in get_top_market_skills(limit=24)]
    labels: list[str] = []
    seen: set[str] = set()
    for label in static_labels + dynamic_labels:
        if not label:
            continue
        key = _normalize_text_key(label)
        if key in seen:
            continue
        seen.add(key)
        labels.append(label)
    return labels


def _registration_text_hits(haystack: str, labels: list[str]) -> list[str]:
    return recommendation_service.text_hits(haystack, labels)


def _recommended_program_cards(
    programas: list[dict[str, Any]],
    selected_program: dict[str, Any],
    area_actual: str,
    user_skills: list[str],
    role_interests: list[str],
    area_interests: list[str],
    goal: str,
    limit: int = 2,
) -> list[dict[str, Any]]:
    return recommendation_service.recommended_program_cards(
        programas,
        selected_program,
        area_actual,
        user_skills,
        role_interests,
        area_interests,
        goal,
        area_keywords_by_key=REGISTRATION_AREA_KEYWORDS,
        get_program_skill_rows=get_program_skill_rows,
        skill_identity_key=_skill_identity_key,
        program_role_candidates=_program_role_candidates,
        limit=limit,
    )


def _registration_skill_priority(count: int, top_count: int) -> tuple[str, str]:
    return alumni_service.skill_priority(count, top_count)


def _registration_diagnostic_copy(match: float, gap_count: int) -> str:
    return alumni_service.diagnostic_copy(match, gap_count)


def _registration_priority_step(
    goal: str,
    missing_skills: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
    programs: list[dict[str, Any]],
) -> dict[str, str]:
    return alumni_service.priority_step(goal, missing_skills, jobs, programs)


def _build_registration_preview(especializacion_id: int, programas: list[dict[str, Any]], form_data: dict[str, str]) -> dict[str, Any]:
    program = get_programa(especializacion_id) or {}
    match = get_match(especializacion_id)
    level_label, level_copy = _alignment_level(match)
    match_label, match_tone, _ = _match_band(match)
    user_skills = _registration_csv_values(form_data.get("skills_actuales"))
    role_interests = _registration_csv_values(form_data.get("roles_interes"))
    area_interests = _registration_csv_values(form_data.get("areas_interes"))
    area_actual = form_data.get("area_actual", "")
    goal = form_data.get("objetivo_laboral", "")
    missing_skills = sorted(
        get_brechas(especializacion_id),
        key=lambda row: (-int(row.get("conteo", 0) or 0), str(row.get("nombre", "")).casefold()),
    )[:3]
    jobs = sorted(
        get_related_jobs(especializacion_id, limit=6),
        key=lambda row: (
            0 if str(row.get("url", "") or "").strip() else 1,
            -_safe_float(row.get("porcentaje_match", 0)),
            str(row.get("titulo_empleo", "")).casefold(),
        ),
    )[:3]
    recommended_programs = _recommended_program_cards(
        programas,
        program or {"especializacion_id": especializacion_id},
        area_actual,
        user_skills,
        role_interests,
        area_interests,
        goal,
        limit=2,
    )
    top_gap_count = max([int(row.get("conteo", 0) or 0) for row in missing_skills] or [0])

    normalized_missing_skills = []
    for row in missing_skills:
        demand_label, demand_tone = _registration_skill_priority(int(row.get("conteo", 0) or 0), top_gap_count)
        normalized_missing_skills.append(
            {
                "nombre": str(row.get("nombre", "")).strip(),
                "conteo": int(row.get("conteo", 0) or 0),
                "priority_label": demand_label,
                "priority_tone": demand_tone,
            }
        )

    normalized_jobs = []
    for row in jobs:
        job_match = round(_safe_float(row.get("porcentaje_match", 0)), 2)
        band_label, band_tone, _ = _match_band(job_match)
        normalized_jobs.append(
            {
                "titulo": str(row.get("titulo_empleo", "")).strip(),
                "empresa": str(row.get("empresa", "")).strip() or "Empresa",
                "url": str(row.get("url", "")).strip(),
                "match": job_match,
                "match_label": band_label.upper(),
                "match_tone": band_tone,
            }
        )

    normalized_programs = []
    for row in recommended_programs:
        relevance_label, relevance_tone, _ = _match_band(_safe_float(row.get("match", 0)))
        normalized_programs.append(
            {
                "nombre": str(row.get("nombre", "")).strip(),
                "match": round(_safe_float(row.get("match", 0)), 2),
                "reason": str(row.get("reason", "")).strip(),
                "relevance_label": relevance_label.upper(),
                "relevance_tone": relevance_tone,
            }
        )

    priority_step = _registration_priority_step(goal, normalized_missing_skills, normalized_jobs, normalized_programs)

    return {
        "programa": program.get("nombre_especializacion", ""),
        "match": round(match, 2),
        "alignment_label": level_label,
        "alignment_copy": level_copy,
        "alignment_summary": f"Tu programa de egreso tiene alineación {level_label.lower()} con el mercado.",
        "diagnostic_copy": _registration_diagnostic_copy(match, len(normalized_missing_skills)),
        "match_tone": match_tone,
        "match_label_ui": match_label.upper(),
        "next_step": priority_step,
        "route_steps": [
            {
                "title": "Cierra brechas clave",
                "description": (
                    f"Empieza por {', '.join(item['nombre'] for item in normalized_missing_skills[:2])}."
                    if normalized_missing_skills
                    else "No vemos brechas críticas; conserva tus skills actuales actualizadas."
                ),
            },
            {
                "title": "Explora vacantes recomendadas",
                "description": (
                    f"Revisa {len(normalized_jobs)} oportunidades con mejor encaje inicial."
                    if normalized_jobs
                    else "Aún no hay vacantes activas fuertes para tu combinación actual."
                ),
            },
            {
                "title": "Evalúa programas complementarios",
                "description": (
                    "Solo si refuerzan el siguiente movimiento profesional que buscas."
                    if normalized_programs
                    else "Hoy no hay programas complementarios con cercanía suficiente."
                ),
            },
        ],
        "missing_skills": normalized_missing_skills,
        "jobs": normalized_jobs,
        "programs": normalized_programs,
        "actions": [
            {
                "label": "Ver vacantes recomendadas",
                "href": f"{url_for('dashboard', especializacion_id=especializacion_id)}#empleos",
                "tone": "primary",
            },
            {
                "label": "Ver cómo cerrar mis brechas",
                "href": f"{url_for('dashboard', especializacion_id=especializacion_id)}#brechas",
                "tone": "secondary",
            },
            {
                "label": "Explorar programas sugeridos",
                "href": "#programas-complementarios",
                "tone": "secondary",
            },
        ],
        "follow_up_actions": [
            {
                "label": "Recibir alertas de empleo",
                "href": "#seguimiento",
            },
            {
                "label": "Actualizar mi perfil",
                "href": url_for("registro"),
            },
            {
                "label": "Seguir mi alineación",
                "href": url_for("dashboard", especializacion_id=especializacion_id),
            },
        ],
    }


def _registration_initial_step(form_data: dict[str, str]) -> int:
    return alumni_service.initial_step(form_data)


def _save_mentor_registration(form: dict[str, str], programas: list[dict[str, Any]]) -> int:
    return alumni_service.save_mentor_registration(form, programas, db_name=PROGRAM_DB_NAME)


REGISTRATION_TEMPLATE_NAME = "dashboard/registration.html"

@app.route("/registro", methods=["GET", "POST"])
def registro():
    programas = get_programas()
    form_data: dict[str, str] = {}
    errors: list[str] = []
    success = ""
    preview: dict[str, Any] | None = None
    initial_step = 1

    if request.method == "POST":
        form_data = {key: (request.form.get(key) or "").strip() for key in request.form.keys()}
        required_fields = {
            "nombre_completo": "Ingresa tu nombre completo.",
            "email": "Ingresa un email válido.",
            "especializacion_id": "Selecciona tu programa de egreso.",
            "anio_graduacion": "Selecciona tu año de graduación.",
            "cargo_actual": "Cuéntanos tu cargo actual.",
            "nivel_experiencia": "Selecciona tu nivel.",
            "area_actual": "Selecciona tu área.",
            "anios_experiencia": "Selecciona tus años de experiencia.",
            "skills_actuales": "Selecciona al menos una habilidad.",
            "herramientas_dia_dia": "Escribe las herramientas que usas en tu día a día.",
            "roles_interes": "Selecciona al menos un rol de interés.",
            "areas_interes": "Selecciona al menos un área de interés.",
            "objetivo_laboral": "Selecciona tu objetivo principal.",
            "disponibilidad": "Indica tu disponibilidad.",
        }
        for field, message in required_fields.items():
            if not (form_data.get(field) or "").strip():
                errors.append(message)
        if "@" not in form_data.get("email", ""):
            errors.append("El email debe tener formato válido.")

        initial_step = _registration_initial_step(form_data)

        if not errors:
            record_id = _save_mentor_registration(form_data, programas)
            preview = _build_registration_preview(int(form_data["especializacion_id"]), programas, form_data)
            success = f"Perfil creado correctamente. Alia ya puede ayudarte con tu primera lectura de mercado. ID #{record_id}."
    else:
        form_data = {
            "nombre_completo": "",
            "email": "",
            "especializacion_id": "",
            "anio_graduacion": "",
            "cargo_actual": "",
            "nivel_experiencia": "",
            "area_actual": "",
            "anios_experiencia": "",
            "skills_actuales": "",
            "herramientas_dia_dia": "",
            "roles_interes": "",
            "areas_interes": "",
            "objetivo_laboral": "",
            "disponibilidad": "",
        }

    return render_template(
        REGISTRATION_TEMPLATE_NAME,
        programas=programas,
        area_options=REGISTRATION_AREA_OPTIONS,
        role_options=REGISTRATION_ROLE_OPTIONS,
        goal_options=REGISTRATION_GOAL_OPTIONS,
        availability_options=REGISTRATION_AVAILABILITY_OPTIONS,
        skill_suggestions=_registration_skill_suggestions(),
        experience_options=["0-1", "2-3", "4-5", "6-8", "9-12", "13+"],
        graduation_years=list(range(date.today().year, date.today().year - 45, -1)),
        form=form_data,
        errors=errors,
        success=success,
        preview=preview,
        initial_step=initial_step,
    )


@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    programas = get_programas()
    selected_raw = (request.args.get("especializacion_id") or "").strip()
    try:
        selected_id = int(selected_raw) if selected_raw else None
    except ValueError:
        selected_id = None

    if selected_id is not None:
        program_result = _program_dashboard_body(programas, selected_id)
        if len(program_result) == 3:
            body, scripts, status = program_result
            return render_page(
                "Programa no encontrado",
                "Seleccione una especialización válida para ver el detalle.",
                body,
                scripts=scripts,
                sidebar_extra=_selector_card(programas, selected_id),
            ), status
        body, scripts = program_result
        program = get_programa(selected_id)
        return render_page(
            f"Dashboard: {program['nombre_especializacion']}",
            f"Detalle analítico del programa {program['nombre_especializacion']}",
            body,
            active="program",
            scripts=scripts,
            sidebar_extra=_selector_card(programas, selected_id),
        )

    body, scripts = _general_dashboard_body(programas, selected_id)
    return render_page(
        "Dashboard general",
        "Visión ejecutiva de la alineación entre programas académicos y mercado laboral.",
        body,
        scripts=scripts,
        sidebar_extra=_selector_card(programas, selected_id),
    )


@app.route("/dashboard/programa/<int:especializacion_id>")
def program_dashboard(especializacion_id: int):
    return redirect(url_for("dashboard", especializacion_id=especializacion_id))


