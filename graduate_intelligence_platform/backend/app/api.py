from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder

from backend.repositories import empleos_repository, matches_repository, programas_repository, skills_repository
from backend.repositories.base import fetch_all, fetch_one
from backend.services import alumni_service, dashboard_service, recommendation_service
from backend.services.normalization_service import basic_text_key, normalize_program_row

from .schemas import AlumniRegistrationIn, AlumniRegistrationOut, DashboardKpisResponse, HealthResponse, Page
from .auth import require_current_user

router = APIRouter()

DB_NAME = os.getenv("DB_NAME", "cliente_a_db")
MAX_LIMIT = 100

AREA_KEYWORDS_BY_KEY = {
    "datos": ("datos", "data", "analytics", "analitica", "bi", "business intelligence"),
    "tecnologia": ("software", "tecnologia", "cloud", "devops", "arquitectura", "sistemas"),
    "negocios": ("negocio", "gerencia", "marketing", "ventas", "finanzas", "gestion"),
    "operaciones": ("operaciones", "proyectos", "procesos", "calidad", "riesgo", "cumplimiento"),
}


def bounded_limit(limit: int) -> int:
    return max(1, min(int(limit or 25), MAX_LIMIT))


def not_found(resource: str, identifier: Any) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource} {identifier} not found")


def page(items: list[dict[str, Any]], *, limit: int, offset: int) -> Page:
    return Page(items=jsonable_encoder(items), count=len(items), limit=limit, offset=max(0, offset))


def programs() -> list[dict[str, Any]]:
    return dashboard_service.list_programs_base(db_name=DB_NAME)


def program_by_id(program_id: int) -> dict[str, Any] | None:
    resolved_id = programas_repository.resolve_program_id(program_id, db_name=DB_NAME)
    row = programas_repository.fetch_program_base_row(resolved_id, db_name=DB_NAME)
    if not row:
        return None
    normalized = normalize_program_row(row)
    for item in programs():
        if int(item.get("especializacion_id") or 0) == resolved_id:
            normalized.update(item)
            break
    normalized["skills"] = dashboard_service.normalize_skill_rows(
        programas_repository.fetch_program_skill_rows(resolved_id, db_name=DB_NAME)
    )
    return normalized


def role_candidates(program: dict[str, Any], limit: int = 4) -> list[str]:
    values = [
        str(program.get("rol", "") or "").strip(),
        str(program.get("nombre_especializacion", "") or "").strip(),
    ]
    return [value for value in values if value][:limit]


def skill_identity_key(value: str) -> str:
    return basic_text_key(value)


@router.get("/")
def root() -> dict[str, str]:
    return {
        "name": "Graduate Intelligence Platform API",
        "status": "running",
        "docs": "/docs",
        "health": "/api/health",
    }


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        row = fetch_one("SELECT current_database() AS database", db_name=DB_NAME)
        return HealthResponse(
            status="ok",
            service="fastapi-postgresql",
            database="ok",
            db_name=str((row or {}).get("database") or DB_NAME),
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from exc


@router.get("/api/bootstrap")
def bootstrap(_current_user=Depends(require_current_user)) -> dict[str, Any]:
    current_programs = programs()
    return {
        "platform": "Graduate Intelligence Platform",
        "source": "postgresql",
        "summary": dashboard_service.global_kpis(current_programs, db_name=DB_NAME),
        "programas": current_programs[:20],
    }


@router.get("/api/programas", response_model=Page)
def list_programas(
    limit: int = Query(25, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    _current_user=Depends(require_current_user),
) -> Page:
    limit = bounded_limit(limit)
    rows = programs()
    return page(rows[offset : offset + limit], limit=limit, offset=offset)


@router.get("/api/programas/{program_id}")
def get_programa(program_id: int, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    program = program_by_id(program_id)
    if not program:
        raise not_found("programa", program_id)
    return jsonable_encoder(program)


@router.get("/api/programs/related-universities/{program_id}", response_model=Page)
def related_universities_for_program(
    program_id: int,
    limit: int = Query(10, ge=1, le=MAX_LIMIT),
    _current_user=Depends(require_current_user),
) -> Page:
    program = program_by_id(program_id)
    if not program:
        raise not_found("programa", program_id)
    program_name = str(program.get("nombre_especializacion") or "")
    rows = programas_repository.fetch_related_virtual_programs(
        program_name,
        limit=bounded_limit(limit),
        db_name=DB_NAME,
    )
    return page(rows, limit=bounded_limit(limit), offset=0)


@router.get("/api/empleos", response_model=Page)
def list_empleos(
    limit: int = Query(25, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    _current_user=Depends(require_current_user),
) -> Page:
    limit = bounded_limit(limit)
    rows = empleos_repository.fetch_jobs_basic(db_name=DB_NAME)
    return page(rows[offset : offset + limit], limit=limit, offset=offset)


@router.get("/api/empleos/{empleo_id}")
def get_empleo(empleo_id: str, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    empleo = empleos_repository.fetch_job_metadata(empleo_id, db_name=DB_NAME)
    if not empleo:
        raise not_found("empleo", empleo_id)
    empleo["skills"] = skills_repository.fetch_job_skill_names(empleo_id, db_name=DB_NAME)
    return jsonable_encoder(empleo)


@router.get("/api/matches", response_model=Page)
def list_matches(
    limit: int = Query(25, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    _current_user=Depends(require_current_user),
) -> Page:
    relation = matches_repository.match_relation_name(db_name=DB_NAME)
    if not relation:
        return page([], limit=bounded_limit(limit), offset=offset)
    limit = bounded_limit(limit)
    rows = fetch_all(
        f"""
        SELECT
            especializacion_id,
            empleo_id,
            titulo_empleo,
            total_skills_empleo,
            total_skills_especializacion,
            skills_en_comun,
            porcentaje_match
        FROM {relation}
        WHERE skills_en_comun >= 1
        ORDER BY porcentaje_match DESC, skills_en_comun DESC, titulo_empleo
        LIMIT %s OFFSET %s
        """,
        (limit, offset),
        db_name=DB_NAME,
    )
    return page(rows, limit=limit, offset=offset)


@router.get("/api/matches/programa/{program_id}", response_model=Page)
def list_matches_for_program(
    program_id: int,
    limit: int = Query(25, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    _current_user=Depends(require_current_user),
) -> Page:
    relation = matches_repository.match_relation_name(db_name=DB_NAME)
    if not relation:
        return page([], limit=bounded_limit(limit), offset=offset)
    resolved_id = programas_repository.resolve_program_id(program_id, db_name=DB_NAME)
    limit = bounded_limit(limit)
    rows = matches_repository.fetch_match_rows_for_program(
        relation,
        resolved_id,
        limit=None,
        db_name=DB_NAME,
    )
    return page(rows[offset : offset + limit], limit=limit, offset=offset)


@router.get("/api/dashboard/kpis", response_model=DashboardKpisResponse)
def dashboard_kpis(_current_user=Depends(require_current_user)) -> DashboardKpisResponse:
    current_programs = programs()
    return DashboardKpisResponse(
        kpis=dashboard_service.global_kpis(current_programs, db_name=DB_NAME),
        source=matches_repository.match_relation_name(db_name=DB_NAME) or "empleo_skills",
    )


@router.get("/api/dashboard/programa/{program_id}")
def dashboard_programa(program_id: int, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    selected = program_by_id(program_id)
    if not selected:
        raise not_found("programa", program_id)

    relation = matches_repository.match_relation_name(db_name=DB_NAME)
    resolved_id = int(selected.get("especializacion_id") or programas_repository.resolve_program_id(program_id, db_name=DB_NAME))
    matches = (
        matches_repository.fetch_match_rows_for_program(relation, resolved_id, limit=25, db_name=DB_NAME)
        if relation
        else []
    )
    missing_skills = (
        skills_repository.fetch_missing_market_skill_rows_for_program(relation, resolved_id, 22, db_name=DB_NAME)
        if relation
        else []
    )
    current_programs = programs()
    recommendations = recommendation_service.recommended_program_cards(
        current_programs,
        selected,
        "",
        [],
        [],
        [],
        "",
        area_keywords_by_key=AREA_KEYWORDS_BY_KEY,
        get_program_skill_rows=lambda current_id: programas_repository.fetch_program_skill_rows(current_id, db_name=DB_NAME),
        skill_identity_key=skill_identity_key,
        program_role_candidates=role_candidates,
        limit=5,
    )
    payload = dashboard_service.program_context_dashboard(
        selected,
        matches=matches,
        missing_skills=missing_skills,
        recommendations=recommendations,
    )
    payload["source"] = relation or "empleo_skills"
    return jsonable_encoder(payload)


@router.post("/api/alumni/register", response_model=AlumniRegistrationOut)
def register_alumni(payload: AlumniRegistrationIn, _current_user=Depends(require_current_user)) -> AlumniRegistrationOut:
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    record_id = alumni_service.save_mentor_registration(data, programs(), db_name=DB_NAME)
    return AlumniRegistrationOut(
        id=record_id,
        status="created",
        message="Alumni profile registered in PostgreSQL.",
    )


@router.get("/api/recommendations/programs", response_model=Page)
def recommendations_programs(
    program_id: int = Query(..., description="Current especializacion/program id"),
    area_actual: str = "",
    skills_actuales: str = "",
    roles_interes: str = "",
    areas_interes: str = "",
    objetivo_laboral: str = "",
    limit: int = Query(5, ge=1, le=MAX_LIMIT),
    _current_user=Depends(require_current_user),
) -> Page:
    selected = program_by_id(program_id)
    if not selected:
        raise not_found("programa", program_id)
    current_programs = programs()
    items = recommendation_service.recommended_program_cards(
        current_programs,
        selected,
        area_actual,
        alumni_service.csv_values(skills_actuales),
        alumni_service.csv_values(roles_interes),
        alumni_service.csv_values(areas_interes),
        objetivo_laboral,
        area_keywords_by_key=AREA_KEYWORDS_BY_KEY,
        get_program_skill_rows=lambda current_id: programas_repository.fetch_program_skill_rows(current_id, db_name=DB_NAME),
        skill_identity_key=skill_identity_key,
        program_role_candidates=role_candidates,
        limit=bounded_limit(limit),
    )
    return page(items, limit=bounded_limit(limit), offset=0)


@router.get("/api/recommendations/jobs", response_model=Page)
def recommendations_jobs(
    program_id: int = Query(..., description="Especializacion/program id used for job matching"),
    limit: int = Query(10, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    _current_user=Depends(require_current_user),
) -> Page:
    relation = matches_repository.match_relation_name(db_name=DB_NAME)
    if not relation:
        return page([], limit=bounded_limit(limit), offset=offset)
    resolved_id = programas_repository.resolve_program_id(program_id, db_name=DB_NAME)
    rows = matches_repository.fetch_match_rows_for_program(
        relation,
        resolved_id,
        limit=None,
        db_name=DB_NAME,
    )
    return page(rows[offset : offset + bounded_limit(limit)], limit=bounded_limit(limit), offset=offset)
