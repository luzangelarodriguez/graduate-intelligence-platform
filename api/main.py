from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from api.auth import auth_router
from api.contracts import (
    CareerIntelligenceResponse,
    CriticalProgramPageResponse,
    CurriculumSimulationResponse,
    CurriculumRiskResponse,
    ExecutiveNarrativeResponse,
    ExecutiveObservatoryResponse,
    ForecastSummaryResponse,
    HealthResponse,
    MarketForecastPageResponse,
    ObservatoryStatusResponse,
    PaginatedResponse,
    ProgramIntelligenceItem,
    ProgramIntelligencePageResponse,
    Program,
    ProgramDashboardResponse,
    ProgramSummaryResponse,
    ProgramPageResponse,
    RecommendationV2PageResponse,
    RecommendationExplanationResponse,
    AskObservatoryRequest,
    AskObservatoryResponse,
    SearchResponse,
    UniversityMarketAlignmentResponse,
)
from api.logging import RequestLoggingMiddleware, configure_logging
from api import services


configure_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("api.main")


def _fallback_program_response(program_id: int) -> dict[str, Any]:
    program_name = f"Programa {program_id}"
    try:
        program_name = services._safe_program_name(program_id)  # type: ignore[attr-defined]
    except Exception:
        pass
    return {
        "especializacion_id": program_id,
        "nombre_especializacion": program_name,
        "rol": "",
        "total_skills_programa": 0,
        "total_herramientas": 0,
        "total_competencias": 0,
        "total_habilidades_blandas": 0,
        "promedio_match_mercado": 0.0,
        "porcentaje_match": 0.0,
        "max_match_mercado": 0.0,
        "total_empleos_relacionados": 0,
        "skills_cubiertas": 0,
        "skills": [],
        "microcurriculum_context": None,
        "curricular_context_source": "fallback",
        "narrativa_ia": "Análisis curricular pendiente de datos suficientes.",
    }


def _fallback_dashboard_response(program_id: int) -> dict[str, Any]:
    program = _fallback_program_response(program_id)
    return {
        "program_id": program_id,
        "program": program,
        "kpis": {
            "alignment_score": 0.0,
            "missing_critical_skills": 0,
            "high_demand_roles": 0,
            "employability_trend": 0.0,
            "digital_coverage": 0.0,
            "curricular_update_signal": "Baja",
        },
        "status": {
            "curricular_status": "Fallback",
            "curricular_status_detail": "Vista de contingencia mientras se recupera la evidencia.",
            "ai_signal": "Análisis institucional recuperado en modo fallback.",
            "trend_label": "Sin señal suficiente",
        },
        "missing_skills": [],
        "matches": [],
        "recommendations": [],
        "insights": {
            "detected": "No se pudo construir el panel completo; se muestra el programa con evidencia base.",
            "ai_recommends": [],
            "emerging_gap": "Sin brecha prioritaria identificada en el modo fallback",
            "critical_signal": "Fallback institucional",
        },
        "source": "fallback",
    }


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS") or os.getenv("API_CORS_ORIGINS") or "*"
    if raw.strip() == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        snapshot = services.get_health_snapshot()
        logger.info(
            "startup_validation_complete",
            extra={
                "source": "api",
                "database": snapshot.get("database"),
                "status": snapshot.get("status"),
            },
        )
    except Exception:
        logger.exception("startup_validation_failed", extra={"source": "api"})
    yield


app = FastAPI(
    title="AI Labor & Curriculum Observatory API",
    version="1.0.0",
    description="Public API for observatory metrics, recommendations, semantic roles, company intelligence and market forecasts.",
    lifespan=lifespan,
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix="/auth")
app.include_router(auth_router, prefix="/api/auth", include_in_schema=False)


@app.get("/", tags=["system"])
def root() -> dict[str, Any]:
    return {
        "name": "AI Labor & Curriculum Observatory API",
        "status": "ready",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> dict[str, Any]:
    return services.get_health_snapshot()


@app.get("/api/health", response_model=HealthResponse, tags=["system"], include_in_schema=False)
def api_health() -> dict[str, Any]:
    return services.get_health_snapshot()


@app.get("/readiness", response_model=HealthResponse, tags=["system"])
def readiness() -> dict[str, Any]:
    return services.get_readiness_snapshot()


@app.get("/api/readiness", response_model=HealthResponse, tags=["system"], include_in_schema=False)
def api_readiness() -> dict[str, Any]:
    return services.get_readiness_snapshot()


@app.get("/observatory-status", response_model=ObservatoryStatusResponse, tags=["system"])
def observatory_status() -> dict[str, Any]:
    return services.get_observatory_status()


@app.get("/api/observatory-status", response_model=ObservatoryStatusResponse, tags=["system"], include_in_schema=False)
def api_observatory_status() -> dict[str, Any]:
    return services.get_observatory_status()


@app.get("/liveness", tags=["system"])
def liveness() -> dict[str, Any]:
    return {"status": "alive"}


@app.get("/metrics", response_model=PaginatedResponse, tags=["observatory"])
def metrics(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    metric_category: str | None = Query(default=None),
    metric_name: str | None = Query(default=None),
) -> dict[str, Any]:
    return services.list_observatory_metrics(limit=limit, offset=offset, metric_category=metric_category, metric_name=metric_name)


@app.get("/api/programas", response_model=ProgramPageResponse, tags=["programas"])
def programas(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    try:
        return services.list_programas_compatibility(limit=limit, offset=offset)
    except Exception as exc:
        logger.warning("programas_route_fallback: %s", exc, exc_info=True)
        return {"items": [], "count": 0, "total": 0, "limit": limit, "offset": offset}


@app.get("/api/programas/{program_id}", response_model=Program, tags=["programas"])
def programa(program_id: int) -> dict[str, Any]:
    try:
        return services.get_programa_compatibility(program_id)
    except KeyError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning("programa_route_fallback: %s", exc, exc_info=True)
        return _fallback_program_response(program_id)


@app.get("/api/dashboard/programa/{program_id}", response_model=ProgramDashboardResponse, tags=["dashboard"])
def dashboard_programa(program_id: int) -> dict[str, Any]:
    try:
        return services.get_program_dashboard_compatibility(program_id)
    except KeyError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning("dashboard_programa_route_fallback: %s", exc, exc_info=True)
        return _fallback_dashboard_response(program_id)


@app.get("/curriculum-gaps", response_model=PaginatedResponse, tags=["observatory"])
def curriculum_gaps(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    specialization: str | None = Query(default=None),
    program_id: int | None = Query(default=None, ge=1),
) -> dict[str, Any]:
    return services.list_curriculum_gaps(limit=limit, offset=offset, specialization=specialization, program_id=program_id)


@app.get("/recommendations", response_model=PaginatedResponse, tags=["observatory"])
def recommendations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    recommendation_type: str | None = Query(default=None),
    target_company: str | None = Query(default=None),
) -> dict[str, Any]:
    return services.list_recommendations(limit=limit, offset=offset, recommendation_type=recommendation_type, target_company=target_company)


@app.get("/recommendations-v2", response_model=RecommendationV2PageResponse, tags=["predictive"])
def recommendations_v2(
    program_id: int | None = Query(default=None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    return services.list_recommendations_v2(program_id=program_id, limit=limit, offset=offset)


@app.get("/emerging-skills", response_model=PaginatedResponse, tags=["observatory"])
def emerging_skills(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    return services.list_emerging_skills(limit=limit, offset=offset)


@app.get("/semantic-roles", response_model=PaginatedResponse, tags=["observatory"])
def semantic_roles(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    role_family: str | None = Query(default=None),
) -> dict[str, Any]:
    return services.list_semantic_roles(limit=limit, offset=offset, role_family=role_family)


@app.get("/company-intelligence", response_model=PaginatedResponse, tags=["observatory"])
def company_intelligence(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    return services.list_company_intelligence(limit=limit, offset=offset)


@app.get("/career-paths", response_model=PaginatedResponse, tags=["observatory"])
def career_paths(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    return services.list_career_paths(limit=limit, offset=offset)


@app.get("/market-forecast", response_model=MarketForecastPageResponse, tags=["observatory"])
def market_forecast(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    entity_type: str | None = Query(default=None),
    entity_name: str | None = Query(default=None),
    horizon_months: int | None = Query(default=None, ge=1, le=36),
) -> dict[str, Any]:
    return services.list_market_forecast(limit=limit, offset=offset, entity_type=entity_type, entity_name=entity_name, horizon_months=horizon_months)


@app.get("/programas/{program_id}/curriculum-risk", response_model=CurriculumRiskResponse, tags=["predictive"])
def curriculum_risk(program_id: int) -> dict[str, Any]:
    return services.get_curriculum_risk_index(program_id)


@app.get("/programas/{program_id}/alignment", response_model=UniversityMarketAlignmentResponse, tags=["predictive"])
def curriculum_alignment(program_id: int) -> dict[str, Any]:
    return services.get_university_market_alignment(program_id)


@app.get("/critical-programs", response_model=CriticalProgramPageResponse, tags=["predictive"])
def critical_programs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    horizon_months: int = Query(12, ge=1, le=24),
) -> dict[str, Any]:
    return services.get_critical_programs(limit=limit, offset=offset, horizon_months=horizon_months)


@app.get("/curriculum-simulator", response_model=CurriculumSimulationResponse, tags=["predictive"])
def curriculum_simulator(
    program_id: int = Query(..., ge=1),
    proposed_skills: str | None = Query(default=None),
    horizon_months: int = Query(12, ge=1, le=24),
) -> dict[str, Any]:
    return services.get_curriculum_simulator(program_id, proposed_skills=proposed_skills, horizon_months=horizon_months)


@app.get("/forecast-summary", response_model=ForecastSummaryResponse, tags=["predictive"])
def forecast_summary(limit: int = Query(25, ge=1, le=50)) -> dict[str, Any]:
    return services.get_forecast_summary(limit=limit)


@app.get("/career-intelligence", response_model=CareerIntelligenceResponse, tags=["predictive"])
def career_intelligence(source_role: str | None = Query(default=None), limit: int = Query(12, ge=1, le=25)) -> dict[str, Any]:
    return services.get_career_intelligence(source_role=source_role, limit=limit)


@app.get("/executive-observatory", response_model=ExecutiveObservatoryResponse, tags=["predictive"])
def executive_observatory() -> dict[str, Any]:
    return services.get_executive_observatory()


@app.get("/executive-narrative", response_model=ExecutiveNarrativeResponse, tags=["predictive"])
def executive_narrative(program_id: int | None = Query(default=None, ge=1)) -> dict[str, Any]:
    return services.get_executive_narrative(program_id=program_id)


@app.get("/program-summary/{program_id}", response_model=ProgramSummaryResponse, tags=["predictive"])
def program_summary(program_id: int) -> dict[str, Any]:
    return services.get_program_summary(program_id)


@app.get("/recommendation-explanation/{recommendation_id}", response_model=RecommendationExplanationResponse, tags=["predictive"])
def recommendation_explanation(recommendation_id: int) -> dict[str, Any]:
    return services.get_recommendation_explanation(recommendation_id)


@app.post("/ask-observatory", response_model=AskObservatoryResponse, tags=["predictive"])
def ask_observatory(payload: AskObservatoryRequest) -> dict[str, Any]:
    return services.ask_observatory(
        payload.question,
        program_id=payload.program_id,
        recommendation_id=payload.recommendation_id,
        context=payload.context,
    )


@app.get("/program-intelligence", response_model=ProgramIntelligencePageResponse, tags=["predictive"])
def program_intelligence(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    return services.list_program_intelligence(limit=limit, offset=offset)


@app.get("/program-intelligence/{program_id}", response_model=ProgramIntelligenceItem, tags=["predictive"])
def program_intelligence_detail(program_id: int) -> dict[str, Any]:
    try:
        return services.get_program_intelligence(program_id)
    except KeyError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/dashboard/summary", tags=["dashboard"])
def dashboard_summary() -> dict[str, Any]:
    """Return aggregated match data from the latest ml run for the frontend dashboard."""
    from api.database import fetch_all, fetch_one

    run_row = fetch_one(
        "SELECT id, created_at FROM ml_training_runs "
        "WHERE task_name = 'program_job_match' ORDER BY id DESC LIMIT 1"
    )
    if not run_row:
        return {
            "run_id": None, "fecha": None,
            "programas": [], "top_matches": [],
            "totales": {"matches": 0, "alta": 0, "media": 0, "baja": 0},
        }

    run_id: int = run_row["id"]
    fecha: str = run_row["created_at"].strftime("%Y-%m-%d") if run_row.get("created_at") else ""

    prog_rows = fetch_all(
        """
        SELECT
            m.especializacion_id                          AS id,
            COALESCE(e.nombre, m.program_name)            AS nombre,
            COUNT(*)                                      AS matches_total,
            ROUND(AVG(m.score_match)::numeric, 1)        AS score_promedio,
            ROUND(MAX(m.score_match)::numeric, 1)        AS score_maximo,
            COUNT(*) FILTER (WHERE m.relevance_label = 'high')   AS lbl_high,
            COUNT(*) FILTER (WHERE m.relevance_label = 'medium') AS lbl_medium,
            COUNT(*) FILTER (WHERE m.relevance_label = 'low')    AS lbl_low
        FROM ml_program_job_matches m
        LEFT JOIN especializaciones e ON e.id = m.especializacion_id
        WHERE m.run_id = %s
        GROUP BY m.especializacion_id, e.nombre, m.program_name
        ORDER BY score_maximo DESC
        """,
        (run_id,),
    )

    programas = [
        {
            "id":             int(r["id"]) if r["id"] else None,
            "nombre":         r["nombre"] or "",
            "matches_total":  int(r["matches_total"]),
            "score_promedio": float(r["score_promedio"] or 0),
            "score_maximo":   float(r["score_maximo"] or 0),
            "labels": {
                "high":   int(r["lbl_high"]),
                "medium": int(r["lbl_medium"]),
                "low":    int(r["lbl_low"]),
            },
        }
        for r in prog_rows
    ]

    top_rows = fetch_all(
        """
        SELECT
            COALESCE(e.nombre, m.program_name) AS programa,
            m.job_title                        AS empleo,
            COALESCE(m.company, '')            AS empresa,
            ROUND(m.score_match::numeric, 1)   AS score,
            m.relevance_label                  AS label,
            m.skills_en_comun                  AS skills_en_comun,
            m.skills_faltantes                 AS skills_faltantes
        FROM ml_program_job_matches m
        LEFT JOIN especializaciones e ON e.id = m.especializacion_id
        WHERE m.run_id = %s
        ORDER BY m.score_match DESC
        LIMIT 30
        """,
        (run_id,),
    )

    top_matches = [
        {
            "programa":        r["programa"] or "",
            "empleo":          r["empleo"] or "",
            "empresa":         r["empresa"],
            "score":           float(r["score"] or 0),
            "label":           r["label"],
            "skills_en_comun": r["skills_en_comun"] if r["skills_en_comun"] is not None else [],
            "skills_faltantes": r["skills_faltantes"] if r["skills_faltantes"] is not None else [],
        }
        for r in top_rows
    ]

    tot_rows = fetch_all(
        "SELECT relevance_label, COUNT(*) AS cnt "
        "FROM ml_program_job_matches WHERE run_id = %s GROUP BY relevance_label",
        (run_id,),
    )
    lbl = {r["relevance_label"]: int(r["cnt"]) for r in tot_rows}

    return {
        "run_id":      run_id,
        "fecha":       fecha,
        "programas":   programas,
        "top_matches": top_matches,
        "totales": {
            "matches": sum(lbl.values()),
            "alta":    lbl.get("high", 0),
            "media":   lbl.get("medium", 0),
            "baja":    lbl.get("low", 0),
        },
    }


@app.get("/api/programs/related-universities/{program_id}", tags=["programs"])
def related_universities(program_id: int) -> dict[str, Any]:
    """Return competitor programs from mineducacion_programas_virtuales matching the domain keywords."""
    from api.database import fetch_all

    QUERIES: dict[int, str] = {
        94: """
            SELECT nombre_ies, nombre_programa, municipio, departamento, modalidad,
                   nivel_academico, creditos, duracion, area_conocimiento, periodicidad_admision
            FROM mineducacion_programas_virtuales
            WHERE (
                nombre_programa ILIKE '%analytic%' OR
                nombre_programa ILIKE '%datos%' OR
                nombre_programa ILIKE '%data%' OR
                nombre_programa ILIKE '%inteligencia de negocio%' OR
                nombre_programa ILIKE '%business intelligence%' OR
                nombre_programa ILIKE '%big data%'
            )
            AND (nombre_ies IS NULL OR nombre_ies NOT ILIKE '%UNIR%')
            ORDER BY nombre_ies
            LIMIT 50
        """,
        92: """
            SELECT nombre_ies, nombre_programa, municipio, departamento, modalidad,
                   nivel_academico, creditos, duracion, area_conocimiento, periodicidad_admision
            FROM mineducacion_programas_virtuales
            WHERE (
                nombre_programa ILIKE '%inteligencia artificial%' OR
                nombre_programa ILIKE '%machine learning%' OR
                nombre_programa ILIKE '%ciencia de datos%' OR
                nombre_programa ILIKE '%data science%'
            )
            AND (nombre_ies IS NULL OR nombre_ies NOT ILIKE '%UNIR%')
            ORDER BY nombre_ies
            LIMIT 50
        """,
        108: """
            SELECT nombre_ies, nombre_programa, municipio, departamento, modalidad,
                   nivel_academico, creditos, duracion, area_conocimiento, periodicidad_admision
            FROM mineducacion_programas_virtuales
            WHERE (
                nombre_programa ILIKE '%criminolog%' OR
                nombre_programa ILIKE '%forense%' OR
                nombre_programa ILIKE '%criminalistica%' OR
                nombre_programa ILIKE '%seguridad ciudadana%' OR
                nombre_programa ILIKE '%investigacion criminal%'
            )
            AND (nombre_ies IS NULL OR nombre_ies NOT ILIKE '%UNIR%')
            ORDER BY nombre_ies
            LIMIT 50
        """,
    }

    sql = QUERIES.get(program_id)
    if not sql:
        return {"program_id": program_id, "competitors": [], "total": 0}

    try:
        rows = fetch_all(sql)
    except Exception as exc:
        logger.error("related_universities query failed for program_id=%s: %s", program_id, exc)
        return {"program_id": program_id, "competitors": [], "total": 0, "error": str(exc)}

    logger.info("related_universities program_id=%s rows_returned=%s", program_id, len(rows))

    competitors = []
    for r in rows:
        try:
            competitors.append({
                "nombre_ies":            r.get("nombre_ies") or "",
                "nombre_programa":       r.get("nombre_programa") or "",
                "ciudad":                r.get("municipio") or "",
                "municipio":             r.get("municipio") or "",
                "departamento":          r.get("departamento") or "",
                "modalidad":             r.get("modalidad") or "",
                "nivel_academico":       r.get("nivel_academico") or "",
                "creditos":              r.get("creditos"),
                "duracion":              r.get("duracion") or "",
                "area_conocimiento":     r.get("area_conocimiento") or "",
                "periodicidad_admision": r.get("periodicidad_admision") or "",
            })
        except Exception as row_exc:
            logger.warning("related_universities skipping row: %s — %s", r, row_exc)

    return {"program_id": program_id, "competitors": competitors, "total": len(competitors)}


@app.get("/api/dashboard/skills-analysis/{program_id}", tags=["dashboard"])
def dashboard_skills_analysis(program_id: int) -> dict[str, Any]:
    """Bidirectional skills analysis: market demand vs. program curriculum for a given program."""
    from api.database import fetch_all

    # 1. Skills from market (job matches for this program, latest run)
    market_rows = fetch_all(
        """
        SELECT skill, COUNT(*) AS frecuencia
        FROM ml_program_job_matches,
             jsonb_array_elements_text(skills_empleo) AS skill
        WHERE especializacion_id = %s
          AND run_id = (SELECT MAX(run_id) FROM ml_program_job_matches)
          AND jsonb_typeof(skills_empleo) = 'array'
        GROUP BY skill
        ORDER BY frecuencia DESC
        LIMIT 30
        """,
        (program_id,),
    )
    skills_mercado = [
        {"skill": r["skill"], "frecuencia": int(r["frecuencia"])}
        for r in market_rows
        if r["skill"]
    ]

    # 2. Skills from program curriculum (microcurriculo)
    prog_rows = fetch_all(
        """
        SELECT ms.skill_name, COUNT(*) AS cobertura
        FROM microcurriculo_skills ms
        JOIN microcurriculos m ON m.id = ms.microcurriculo_id
        WHERE m.specialization_id = %s
        GROUP BY ms.skill_name
        ORDER BY cobertura DESC
        """,
        (program_id,),
    )
    skills_programa = [
        {"skill": r["skill_name"], "cobertura": int(r["cobertura"])}
        for r in prog_rows
        if r["skill_name"]
    ]

    # 3. Cross analysis
    mercado_set = {s["skill"].lower(): s for s in skills_mercado}
    programa_set = {s["skill"].lower(): s for s in skills_programa}

    brechas = [
        {"skill": s["skill"], "frecuencia_mercado": s["frecuencia"]}
        for key, s in mercado_set.items()
        if key not in programa_set
    ]
    fortalezas = [
        {
            "skill": s["skill"],
            "frecuencia_mercado": s["frecuencia"],
            "cobertura_programa": programa_set[key]["cobertura"],
        }
        for key, s in mercado_set.items()
        if key in programa_set
    ]
    exclusivas_programa = [
        {"skill": s["skill"], "cobertura": s["cobertura"]}
        for key, s in programa_set.items()
        if key not in mercado_set
    ]

    total_mercado = len(mercado_set)
    cobertura_pct = round(len(fortalezas) / total_mercado * 100, 1) if total_mercado else 0.0

    return {
        "program_id":          program_id,
        "skills_mercado":      skills_mercado,
        "skills_programa":     skills_programa,
        "brechas":             brechas,
        "fortalezas":          fortalezas,
        "exclusivas_programa": exclusivas_programa,
        "cobertura_pct":       cobertura_pct,
    }


@app.get("/semantic-search", response_model=SearchResponse, tags=["search"])
def semantic_search(
    q: str = Query(..., min_length=2, max_length=256),
    entity_type: str = Query(default="job", pattern="^(job|company|skill|role)$"),
    limit: int = Query(10, ge=1, le=25),
) -> dict[str, Any]:
    return services.semantic_search_results(q, entity_type=entity_type, limit=limit)
