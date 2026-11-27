from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
from api.market_sample import _MARKET_SAMPLE_CTE
from api.microcurriculo_filters import SQL_FILTRO_NO_PRUEBA as _SQL_FILTRO_NO_PRUEBA
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


class _UnicodeJSONResponse(JSONResponse):
    """Emit Spanish characters as-is instead of \\uXXXX escapes."""
    def render(self, content: Any) -> bytes:
        import json
        return json.dumps(content, ensure_ascii=False, allow_nan=False).encode("utf-8")


app = FastAPI(
    title="AI Labor & Curriculum Observatory API",
    version="1.0.0",
    description="Public API for observatory metrics, recommendations, semantic roles, company intelligence and market forecasts.",
    lifespan=lifespan,
    default_response_class=_UnicodeJSONResponse,
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
def dashboard_summary(program_id: int | None = Query(default=None)) -> dict[str, Any]:
    """Return aggregated match data from the latest ml run for the frontend dashboard.
    If program_id is provided, results are filtered to that specialization only.
    """
    try:
        from api.database import fetch_all, fetch_one

        run_row = fetch_one(
            "SELECT id, created_at FROM ml_training_runs "
            "WHERE task_name = 'program_job_match' ORDER BY id DESC LIMIT 1"
        )
        # Fallback: if ml_training_runs has no matching row, derive run_id from
        # the matches table directly so existing data is still served.
        if not run_row:
            fallback_row = fetch_one(
                "SELECT MAX(run_id) AS id FROM ml_program_job_matches"
            )
            if not fallback_row or not fallback_row.get("id"):
                return {
                    "run_id": None, "fecha": None,
                    "programas": [], "top_matches": [], "skill_matches": [],
                    "totales": {"matches": 0, "alta": 0, "media": 0, "baja": 0, "empleos_compatibles": 0},
                }
            run_row = {"id": fallback_row["id"], "created_at": None}

        run_id: int = int(run_row["id"])

        # Use MAX(updated_at) from the matches for this run as the "Corte" date.
        # updated_at is set to now() on every ON CONFLICT DO UPDATE (migration 029),
        # reflecting when scores were last recalculated — unlike ml_training_runs.created_at
        # which is fixed at the run's original creation date.
        try:
            corte_row = fetch_one(
                "SELECT MAX(updated_at) AS corte "
                "FROM ml_program_job_matches WHERE run_id = %s",
                (run_id,),
            )
        except Exception:
            corte_row = None  # column doesn't exist yet (pre-migration 029)
        if corte_row and corte_row.get("corte"):
            fecha: str = corte_row["corte"].strftime("%Y-%m-%d")
        elif run_row.get("created_at"):
            fecha = run_row["created_at"].strftime("%Y-%m-%d")
        else:
            fecha = ""

        # Use literal interpolation for the optional filter to avoid param-count mismatches
        pid_filter = f"AND m.especializacion_id = {int(program_id)}" if program_id else ""
        pid_filter_bare = f"AND especializacion_id = {int(program_id)}" if program_id else ""

        prog_rows = fetch_all(
            f"""
            SELECT
                m.especializacion_id                                    AS id,
                COALESCE(e.nombre, MAX(m.program_name))                 AS nombre,
                COUNT(*)                                                AS matches_total,
                ROUND(AVG(m.score_match)::numeric, 1)                  AS score_promedio,
                ROUND(MAX(m.score_match)::numeric, 1)                  AS score_maximo,
                COUNT(*) FILTER (WHERE m.relevance_label = 'high')     AS lbl_high,
                COUNT(*) FILTER (WHERE m.relevance_label = 'medium')   AS lbl_medium,
                COUNT(*) FILTER (WHERE m.relevance_label = 'low')      AS lbl_low
            FROM ml_program_job_matches m
            LEFT JOIN especializaciones e ON e.id = m.especializacion_id
            WHERE m.run_id = {run_id} {pid_filter}
            GROUP BY m.especializacion_id, e.nombre
            ORDER BY score_maximo DESC
            """,
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
            f"""
            SELECT
                COALESCE(e.nombre, m.program_name)  AS programa,
                m.job_title                         AS empleo,
                COALESCE(m.company, '')             AS empresa,
                COALESCE(j.source, '')              AS fuente,
                COALESCE(j.semantic_title_family, '') AS familia,
                ROUND(m.score_match::numeric, 1)    AS score,
                m.relevance_label                   AS label,
                m.skills_en_comun                   AS skills_en_comun,
                m.skills_faltantes                  AS skills_faltantes
            FROM ml_program_job_matches m
            LEFT JOIN especializaciones e ON e.id = m.especializacion_id
            LEFT JOIN jobs j ON j.id::text = m.empleo_id
            WHERE m.run_id = {run_id} {pid_filter}
              AND m.relevance_label IN ('high', 'medium')
            ORDER BY m.score_match DESC
            LIMIT 30
            """,
        )

        top_matches = [
            {
                "programa":        r["programa"] or "",
                "empleo":          r["empleo"] or "",
                "empresa":         r["empresa"],
                "fuente":          r["fuente"],
                "familia":         r["familia"],
                "score":           float(r["score"] or 0),
                "label":           r["label"],
                "skills_en_comun": r["skills_en_comun"] if r["skills_en_comun"] is not None else [],
                "skills_faltantes": r["skills_faltantes"] if r["skills_faltantes"] is not None else [],
            }
            for r in top_rows
        ]

        tot_rows = fetch_all(
            f"SELECT relevance_label, COUNT(*) AS cnt "
            f"FROM ml_program_job_matches "
            f"WHERE run_id = {run_id} {pid_filter_bare} "
            f"GROUP BY relevance_label",
        )
        lbl = {r["relevance_label"]: int(r["cnt"]) for r in tot_rows}

        # Count matches with real skill overlap across ALL rows, not just the top-30 sample.
        # Replicates the same predicate used in /api/dashboard/compare-programs.
        emp_row = fetch_one(
            f"SELECT COUNT(*) AS cnt "
            f"FROM ml_program_job_matches "
            f"WHERE run_id = {run_id} {pid_filter_bare} "
            f"  AND skills_en_comun IS NOT NULL "
            f"  AND skills_en_comun != '[]'::jsonb "
            f"  AND jsonb_array_length(skills_en_comun) > 0 "
            f"  AND relevance_label IN ('high', 'medium')",
        )
        empleos_compatibles: int = int(emp_row["cnt"]) if emp_row else 0

        # Fetch the actual list of matches with real skill overlap (not limited by top-30 score ranking).
        skill_match_rows = fetch_all(
            f"""
            SELECT
                COALESCE(e.nombre, m.program_name)  AS programa,
                m.job_title                         AS empleo,
                COALESCE(m.company, '')              AS empresa,
                COALESCE(j.source, '')              AS fuente,
                COALESCE(j.semantic_title_family, '') AS familia,
                m.score_match                       AS score,
                m.relevance_label                   AS label,
                m.skills_en_comun                   AS skills_en_comun,
                m.skills_faltantes                  AS skills_faltantes
            FROM ml_program_job_matches m
            LEFT JOIN especializaciones e ON e.id = m.especializacion_id
            LEFT JOIN jobs j ON j.id::text = m.empleo_id
            WHERE m.run_id = {run_id} {pid_filter}
              AND m.skills_en_comun IS NOT NULL
              AND m.skills_en_comun != '[]'::jsonb
              AND jsonb_array_length(m.skills_en_comun) > 0
            ORDER BY m.score_match DESC
            LIMIT 30
            """,
        )
        skill_matches = [
            {
                "programa":         r["programa"] or "",
                "empleo":           r["empleo"] or "",
                "empresa":          r["empresa"],
                "fuente":           r["fuente"],
                "familia":          r["familia"],
                "score":            float(r["score"] or 0),
                "label":            r["label"],
                "skills_en_comun":  r["skills_en_comun"] if r["skills_en_comun"] is not None else [],
                "skills_faltantes": r["skills_faltantes"] if r["skills_faltantes"] is not None else [],
            }
            for r in skill_match_rows
        ]

        return {
            "run_id":       run_id,
            "fecha":        fecha,
            "programas":    programas,
            "top_matches":  top_matches,
            "skill_matches": skill_matches,
            "totales": {
                "matches":             sum(lbl.values()),
                "alta":                lbl.get("high", 0) + lbl.get("high_semantic", 0),
                "media":               lbl.get("medium", 0) + lbl.get("medium_semantic", 0),
                "baja":                lbl.get("low", 0) + lbl.get("low_semantic", 0),
                "empleos_compatibles": empleos_compatibles,
            },
        }
    except Exception as exc:
        logger.error("dashboard_summary error program_id=%s: %s", program_id, exc, exc_info=True)
        return {
            "run_id": None, "fecha": None,
            "programas": [], "top_matches": [], "skill_matches": [],
            "totales": {"matches": 0, "alta": 0, "media": 0, "baja": 0, "empleos_compatibles": 0},
            "error": str(exc),
        }


@app.get("/api/programs/related-universities/{program_id}")
def related_universities(program_id: int) -> dict[str, Any]:
    try:
        JOIN_TEMPLATE = """
            LEFT JOIN snies_estadisticas_programa s
              ON s.codigo_snies = m.codigo_snies_programa::INTEGER
             AND s.anio = (SELECT MAX(anio) FROM snies_estadisticas_programa)
        """
        BASE_SELECT = """SELECT m.nombre_ies, m.nombre_programa, m.municipio, m.modalidad,
                                m.nivel_academico, m.creditos, m.duracion, m.periodicidad_admision,
                                COALESCE(s.matriculados, 0) AS matriculados,
                                COALESCE(s.graduados, 0)    AS graduados,
                                COALESCE(s.inscritos, 0)    AS inscritos
                         FROM mineducacion_programas_virtuales m"""
        # Fetch the real nivel for this program to avoid hardcoding 'Posgrado'
        from api.database import fetch_one
        prog_meta = fetch_one(
            "SELECT nivel FROM especializaciones WHERE id = %s", (program_id,)
        )
        prog_nivel = (prog_meta or {}).get("nivel") or "Posgrado"
        # Map internal nivel values to SNIES/mineducacion vocabulary
        nivel_filter = "Pregrado" if "pregrado" in prog_nivel.lower() else "Posgrado"
        # For pregrado, drop the '%especializ%' constraint (only meaningful for posgrado names)
        nombre_filter = "" if nivel_filter == "Pregrado" else "AND m.nombre_programa ILIKE '%especializ%'"

        FILTERS = f"""AND m.estado_programa ILIKE '%activo%'
                     AND m.modalidad ILIKE '%virtual%'
                     AND m.nivel_academico = '{nivel_filter}'
                     {nombre_filter}
                     ORDER BY COALESCE(s.matriculados, 0) DESC LIMIT 50"""

        PROGRAM_WHERE = {
            13: """WHERE (m.nombre_programa ILIKE '%analytic%'
                      OR m.nombre_programa ILIKE '%datos%'
                      OR m.nombre_programa ILIKE '%big data%'
                      OR m.nombre_programa ILIKE '%inteligencia de negocio%'
                      OR m.nombre_programa ILIKE '%business intelligence%')""",
            11: """WHERE (m.nombre_programa ILIKE '%inteligencia artificial%'
                      OR m.nombre_programa ILIKE '%machine learning%'
                      OR m.nombre_programa ILIKE '%ciencia de datos%'
                      OR m.nombre_programa ILIKE '%data science%')""",
            108: """WHERE (m.nombre_programa ILIKE '%criminolog%'
                       OR m.nombre_programa ILIKE '%forense%'
                       OR m.nombre_programa ILIKE '%criminalistica%'
                       OR m.nombre_programa ILIKE '%seguridad ciudadana%')""",
            9: """WHERE (
                    m.nombre_programa ILIKE '%gerencia de proyecto%'
                 OR m.nombre_programa ILIKE '%gesti_n de proyecto%'
                 OR m.nombre_programa ILIKE '%direcci_n de proyecto%'
                 OR m.nombre_programa ILIKE '%direcci_n y gesti_n de proyecto%'
                 OR m.nombre_programa ILIKE '%formulaci_n y evaluaci_n de proyecto%'
                 OR m.nombre_programa ILIKE '%evaluaci_n y gerencia de proyecto%'
                 OR m.nombre_programa ILIKE '%project management%'
                 OR m.nombre_programa ILIKE '%pmo%'
                 OR m.nombre_programa ILIKE '%scrum%'
               )
               AND m.nombre_programa NOT ILIKE '%construcci_n%'
               AND m.nombre_programa NOT ILIKE '%agropecuari%'
               AND m.nombre_programa NOT ILIKE '%telecomunicaciones%'
               AND m.nombre_programa NOT ILIKE '%ambiental%'
               AND m.nombre_programa NOT ILIKE '%socio%'
               AND m.nombre_programa NOT ILIKE '%multimedial%'
               AND m.nombre_programa NOT ILIKE '%audiovisual%'
               AND m.nombre_programa NOT ILIKE '%bim%'
               AND m.nombre_programa NOT ILIKE '%tur_stic%'
               AND m.nombre_programa NOT ILIKE '%creativ%'
               AND m.nombre_programa NOT ILIKE '%ingenier_a%'
               AND m.nombre_programa NOT ILIKE '%cooperaci_n internacional%'
               AND m.nombre_programa NOT ILIKE '%estatal%'
               AND m.nombre_programa NOT ILIKE '%inform_tica%'
               AND m.nombre_programa NOT ILIKE '%inteligencia de negocio%'
               AND m.nombre_programa NOT ILIKE '%desarrollo%'""",
            109: """WHERE (m.nombre_programa ILIKE '%ingenier_a inform_tica%'
                       OR m.nombre_programa ILIKE '%ingenier_a de sistemas%'
                       OR m.nombre_programa ILIKE '%tecnolog_a en sistemas%'
                       OR m.nombre_programa ILIKE '%ingenier_a en computaci_n%'
                       OR m.nombre_programa ILIKE '%tecnolog_a inform_tica%'
                       OR m.nombre_programa ILIKE '%ciencias de la computaci_n%'
                    )""",
            146: """WHERE (m.nombre_programa ILIKE '%marketing%'
                       OR m.nombre_programa ILIKE '%publicidad%'
                       OR m.nombre_programa ILIKE '%mercadeo%')""",
        }
        where = PROGRAM_WHERE.get(program_id)
        if not where:
            return {"program_id": program_id, "competitors": [], "total": 0}

        sql = f"{BASE_SELECT} {JOIN_TEMPLATE} {where} {FILTERS}"

        from api.database import connection
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()

        competitors = []
        for r in rows:
            competitors.append({
                "nombre_ies":            str(r[0] or ""),
                "nombre_programa":       str(r[1] or ""),
                "ciudad":                str(r[2] or ""),
                "modalidad":             str(r[3] or ""),
                "nivel_academico":       str(r[4] or ""),
                "creditos":              r[5],
                "duracion":              str(r[6] or ""),
                "periodicidad_admision": str(r[7] or ""),
                "matriculados":          int(r[8] or 0),
                "graduados":             int(r[9] or 0),
                "inscritos":             int(r[10] or 0),
            })
        return {"program_id": program_id, "competitors": competitors, "total": len(competitors)}
    except Exception as e:
        logger.error("related_universities error program_id=%s: %s", program_id, e)
        return {"program_id": program_id, "competitors": [], "total": 0, "error": str(e)}


@app.get("/api/programs/oferta-demanda/{program_id}", tags=["programs"])
def oferta_demanda(program_id: int) -> dict[str, Any]:
    """Oferta y Demanda Académica: datos SNIES del programa propio + universo comparable."""
    _EMPTY = {
        "program_id": program_id,
        "snies_vinculado": False,
        "anios_disponibles": [],
        "serie_matriculados": [],
        "serie_graduados": [],
        "nota_cobertura": None,
        "mercado": None,
        "benchmark": [],
        "oferta_geografica": [],
    }
    try:
        from api.database import connection, fetch_all, fetch_one

        PROGRAM_WHERE: dict[int, str] = {
            13: """WHERE (m.nombre_programa ILIKE '%analytic%'
                      OR m.nombre_programa ILIKE '%datos%'
                      OR m.nombre_programa ILIKE '%big data%'
                      OR m.nombre_programa ILIKE '%inteligencia de negocio%'
                      OR m.nombre_programa ILIKE '%business intelligence%')""",
            11: """WHERE (m.nombre_programa ILIKE '%inteligencia artificial%'
                      OR m.nombre_programa ILIKE '%machine learning%'
                      OR m.nombre_programa ILIKE '%ciencia de datos%'
                      OR m.nombre_programa ILIKE '%data science%')""",
            108: """WHERE (m.nombre_programa ILIKE '%criminolog%'
                       OR m.nombre_programa ILIKE '%forense%'
                       OR m.nombre_programa ILIKE '%criminalistica%'
                       OR m.nombre_programa ILIKE '%seguridad ciudadana%')""",
            9: """WHERE (
                    m.nombre_programa ILIKE '%gerencia de proyecto%'
                 OR m.nombre_programa ILIKE '%gesti_n de proyecto%'
                 OR m.nombre_programa ILIKE '%direcci_n de proyecto%'
                 OR m.nombre_programa ILIKE '%direcci_n y gesti_n de proyecto%'
                 OR m.nombre_programa ILIKE '%formulaci_n y evaluaci_n de proyecto%'
                 OR m.nombre_programa ILIKE '%evaluaci_n y gerencia de proyecto%'
                 OR m.nombre_programa ILIKE '%project management%'
                 OR m.nombre_programa ILIKE '%pmo%'
                 OR m.nombre_programa ILIKE '%scrum%'
               )
               AND m.nombre_programa NOT ILIKE '%construcci_n%'
               AND m.nombre_programa NOT ILIKE '%agropecuari%'
               AND m.nombre_programa NOT ILIKE '%telecomunicaciones%'
               AND m.nombre_programa NOT ILIKE '%ambiental%'
               AND m.nombre_programa NOT ILIKE '%socio%'
               AND m.nombre_programa NOT ILIKE '%multimedial%'
               AND m.nombre_programa NOT ILIKE '%audiovisual%'
               AND m.nombre_programa NOT ILIKE '%bim%'
               AND m.nombre_programa NOT ILIKE '%tur_stic%'
               AND m.nombre_programa NOT ILIKE '%creativ%'
               AND m.nombre_programa NOT ILIKE '%ingenier_a%'
               AND m.nombre_programa NOT ILIKE '%cooperaci_n internacional%'
               AND m.nombre_programa NOT ILIKE '%estatal%'
               AND m.nombre_programa NOT ILIKE '%inform_tica%'
               AND m.nombre_programa NOT ILIKE '%inteligencia de negocio%'
               AND m.nombre_programa NOT ILIKE '%desarrollo%'""",
            109: """WHERE (m.nombre_programa ILIKE '%ingenier_a inform_tica%'
                       OR m.nombre_programa ILIKE '%ingenier_a de sistemas%'
                       OR m.nombre_programa ILIKE '%tecnolog_a en sistemas%'
                       OR m.nombre_programa ILIKE '%ingenier_a en computaci_n%'
                       OR m.nombre_programa ILIKE '%tecnolog_a inform_tica%'
                       OR m.nombre_programa ILIKE '%ciencias de la computaci_n%'
                    )""",
            146: """WHERE (m.nombre_programa ILIKE '%marketing%'
                       OR m.nombre_programa ILIKE '%publicidad%'
                       OR m.nombre_programa ILIKE '%mercadeo%')""",
        }

        where = PROGRAM_WHERE.get(program_id)
        if not where:
            return _EMPTY

        # ── 1. Serie histórica del programa propio (via snies_estadisticas_programa) ──
        snies_row = fetch_one(
            "SELECT codigo_snies FROM snies_estadisticas_programa WHERE specialization_id = %s LIMIT 1",
            (program_id,),
        )
        snies_vinculado = snies_row is not None
        serie_matriculados: list[dict] = []
        serie_graduados: list[dict] = []
        anios_disponibles: list[int] = []
        if snies_vinculado:
            codigo_snies = snies_row["codigo_snies"]
            rows_serie = fetch_all(
                """SELECT anio, COALESCE(matriculados, 0) AS matriculados,
                          COALESCE(graduados, 0) AS graduados
                   FROM snies_estadisticas_programa
                   WHERE codigo_snies = %s
                   ORDER BY anio""",
                (codigo_snies,),
            )
            for r in rows_serie:
                anio = int(r["anio"])
                anios_disponibles.append(anio)
                serie_matriculados.append({"anio": anio, "valor": int(r["matriculados"])})
                serie_graduados.append({"anio": anio, "valor": int(r["graduados"])})

        nota_cobertura: str | None = None
        if len(anios_disponibles) == 1:
            nota_cobertura = f"Solo {anios_disponibles[0]} disponible"
        elif len(anios_disponibles) >= 2:
            nota_cobertura = f"{len(anios_disponibles)} años disponibles ({anios_disponibles[0]}–{anios_disponibles[-1]})"

        # ── 2. Mercado comparable: COUNT, sumas, benchmark desde mineducacion + snies ──
        latest_anio_row = fetch_one("SELECT MAX(anio) AS anio FROM snies_estadisticas_programa")
        latest_anio = int(latest_anio_row["anio"]) if latest_anio_row and latest_anio_row["anio"] else None

        JOIN_SNIES = ""
        if latest_anio:
            JOIN_SNIES = f"""LEFT JOIN snies_estadisticas_programa s
                               ON s.codigo_snies = m.codigo_snies_programa::INTEGER
                              AND s.anio = {latest_anio}"""

        base_query = f"""
            FROM mineducacion_programas_virtuales m
            {JOIN_SNIES}
            {where}
            AND m.estado_programa ILIKE '%activo%'
            AND m.modalidad ILIKE '%virtual%'
        """

        mercado_row = fetch_one(
            f"""SELECT COUNT(*) AS programas_similares,
                       COUNT(DISTINCT m.nombre_ies) AS instituciones,
                       COALESCE(SUM(s.matriculados), 0) AS matriculados_total,
                       COALESCE(SUM(s.graduados), 0)    AS graduados_total
                {base_query}"""
        )
        mercado: dict | None = None
        if mercado_row:
            mercado = {
                "programas_similares": int(mercado_row["programas_similares"] or 0),
                "instituciones":       int(mercado_row["instituciones"] or 0),
                "matriculados_total":  int(mercado_row["matriculados_total"] or 0),
                "graduados_total":     int(mercado_row["graduados_total"] or 0),
            }

        benchmark_rows = fetch_all(
            f"""SELECT m.nombre_ies,
                       COALESCE(s.matriculados, 0) AS matriculados,
                       COALESCE(s.graduados, 0)    AS graduados
                {base_query}
                ORDER BY COALESCE(s.matriculados, 0) DESC
                LIMIT 20"""
        )
        benchmark = [
            {
                "institucion": str(r["nombre_ies"] or ""),
                "matriculados": int(r["matriculados"]),
                "graduados":    int(r["graduados"]),
                "es_unir":      "unir" in str(r["nombre_ies"] or "").lower(),
            }
            for r in (benchmark_rows or [])
        ]

        # ── 3. Distribución geográfica desde mineducacion ──
        geo_rows = fetch_all(
            f"""SELECT m.departamento, m.municipio, COUNT(*) AS universidades
                FROM mineducacion_programas_virtuales m
                {where}
                AND m.estado_programa ILIKE '%activo%'
                AND m.modalidad ILIKE '%virtual%'
                GROUP BY m.departamento, m.municipio
                ORDER BY universidades DESC
                LIMIT 30"""
        )
        oferta_geografica = [
            {
                "departamento": str(r["departamento"] or ""),
                "municipio":    str(r["municipio"] or ""),
                "universidades": int(r["universidades"]),
            }
            for r in (geo_rows or [])
        ]

        return {
            "program_id":        program_id,
            "snies_vinculado":   snies_vinculado,
            "anios_disponibles": anios_disponibles,
            "serie_matriculados": serie_matriculados,
            "serie_graduados":    serie_graduados,
            "nota_cobertura":     nota_cobertura,
            "mercado":            mercado,
            "benchmark":          benchmark,
            "oferta_geografica":  oferta_geografica,
        }
    except Exception as e:
        logger.error("oferta_demanda error program_id=%s: %s", program_id, e)
        return {**_EMPTY, "error": str(e)}


@app.get("/api/dashboard/compare-programs", tags=["dashboard"])
def compare_programs(ids: str = Query(default="13,11,108,20")) -> list[dict]:
    """Compare key metrics across multiple programs for the dashboard Comparativa view."""
    try:
        from api.database import fetch_all

        id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        if not id_list:
            return []

        rows = fetch_all(
            """
            SELECT
                m.especializacion_id AS id,
                COALESCE(e.nombre, m.program_name) AS nombre,
                ROUND(AVG(m.score_match)::numeric, 1) AS pertinencia,
                COUNT(*) FILTER (
                    WHERE m.skills_en_comun IS NOT NULL
                    AND m.skills_en_comun != '[]'::jsonb
                    AND jsonb_array_length(m.skills_en_comun) > 0
                ) AS empleos_compatibles
            FROM ml_program_job_matches m
            LEFT JOIN especializaciones e ON e.id = m.especializacion_id
            WHERE m.run_id = (
                SELECT MAX(id) FROM ml_training_runs WHERE task_name = 'program_job_match'
            )
              AND m.especializacion_id = ANY(%s)
            GROUP BY m.especializacion_id, e.nombre, m.program_name
            """,
            (id_list,),
        )

        by_id = {int(r["id"]): r for r in rows}
        result = []
        for pid in id_list:
            sa = dashboard_skills_analysis(pid)
            r = by_id.get(pid)
            result.append({
                "id":                  pid,
                "nombre":              (r["nombre"] if r else None) or f"Programa {pid}",
                "pertinencia":         float(r["pertinencia"] or 0) if r else 0.0,
                "cobertura_pct":       sa.get("cobertura_pct", 0.0),
                "empleos_compatibles": int(r["empleos_compatibles"] or 0) if r else 0,
                "brechas_count":       len(sa.get("brechas", [])),
            })

        return sorted(result, key=lambda x: x["pertinencia"], reverse=True)
    except Exception as exc:
        logger.error("compare_programs error: %s", exc, exc_info=True)
        return []


# ── SQL shared by /skills-analysis endpoint and _run_redesign ─────────────────

# NOTE: The ranking assumes role_alignment is comparable across programs, i.e. all
# active runs were produced by the same engine/version.  If a program's latest run
# was generated by a different engine, its role_alignment scale may differ and the
# ranking could mis-assign vacancies.  Verify engine homogeneity before each run.
_SQL_MARKET_SKILLS = f"""
    WITH {_MARKET_SAMPLE_CTE}
    SELECT ms.match_id,
           ms.empleo_id,
           jsonb_array_elements_text(ms.skills_empleo) AS skill
    FROM market_sample ms
    WHERE ms.especializacion_id = %s
      AND ms.skills_empleo IS NOT NULL
      AND jsonb_typeof(ms.skills_empleo) = 'array'
      AND ms.skills_empleo != '[]'::jsonb
"""

_SQL_MARKET_SIZE = f"""
    WITH {_MARKET_SAMPLE_CTE}
    SELECT COUNT(DISTINCT ms.empleo_id)::int AS n_vacantes_muestra
    FROM market_sample ms
    WHERE ms.especializacion_id = %s
"""

_SQL_PROG_SKILLS = f"""
    SELECT COALESCE(ms.skill_normalized, ms.skill_original) AS skill_name,
           COUNT(*) AS cobertura,
           ARRAY_REMOVE(ARRAY_AGG(DISTINCT m.asignatura), NULL) AS asignaturas
    FROM microcurriculo_skills ms
    JOIN microcurriculos m ON m.id = ms.microcurriculo_id
    WHERE m.specialization_id = %s
      AND COALESCE(ms.skill_normalized, ms.skill_original) IS NOT NULL
      {_SQL_FILTRO_NO_PRUEBA}
    GROUP BY COALESCE(ms.skill_normalized, ms.skill_original)
    ORDER BY cobertura DESC
"""


def _market_analysis_for_program(program_id: int, fetch_all_fn: Any) -> dict:
    """
    Shared core: query high/medium job matches + microcurriculo skills, run cross_analyze.

    Accepts fetch_all_fn so the function can be called with a mock in unit tests.
    Returns the cross_analyze dict plus:
        skills_mercado_raw : list[{skill, frecuencia}] before tipo enrichment
        skills_mercado     : same, without tipo_skill (endpoint adds it)
        skills_programa    : list[{skill, cobertura, asignaturas}]
        n_matches          : number of job matches in market sample
    """
    from api.skills_analysis_logic import cross_analyze, process_job_skill_rows

    raw_rows = fetch_all_fn(_SQL_MARKET_SKILLS, (program_id,))
    size_rows = fetch_all_fn(_SQL_MARKET_SIZE, (program_id,))
    n_vacantes_muestra = int(size_rows[0]["n_vacantes_muestra"]) if size_rows else 0
    skills_mercado_raw, n_matches = process_job_skill_rows(
        [{"match_id": r["match_id"], "skill": r["skill"]} for r in raw_rows]
    )

    prog_rows = fetch_all_fn(_SQL_PROG_SKILLS, (program_id,))
    skills_programa = [
        {
            "skill":       r["skill_name"],
            "asignaturas": list(r["asignaturas"]) if r["asignaturas"] else [],
            "cobertura":   (
                len(list(r["asignaturas"])) if r["asignaturas"]
                else (1 if int(r["cobertura"]) > 0 else 0)
            ),
        }
        for r in prog_rows
        if r["skill_name"]
    ]

    skills_mercado = [{"skill": s["skill"], "frecuencia": s["frecuencia"]} for s in skills_mercado_raw]
    analysis = cross_analyze(skills_mercado, skills_programa, n_matches)
    return {
        **analysis,
        "skills_mercado_raw":    skills_mercado_raw,
        "skills_mercado":        skills_mercado,
        "skills_programa":       skills_programa,
        "n_matches":             n_matches,
        "n_vacantes_muestra":    n_vacantes_muestra,
    }


@app.get("/api/dashboard/skills-analysis/{program_id}", tags=["dashboard"])
def dashboard_skills_analysis(program_id: int) -> dict[str, Any]:
    """
    Bidirectional skills analysis: market demand vs. program curriculum.

    New fields added in this version (all existing fields preserved):
        transversales   : generic/management skills excluded from cobertura_pct
        brechas_criticas: brechas with frecuencia >= p66 of brecha frequencies
        n_matches       : number of high/medium job matches used
        evidencia_baja  : true when n_matches < 15 (low-confidence signal)
        fortalezas[*].prog_skill_match : which program skill covered this market skill
        fortalezas[*].regla : "exacta" | "frase"
        matriz_completa[*].tipo : fortaleza | brecha | transversal | solo_programa
    """
    from api.skills_analysis_logic import (
        build_matriz_completa,
        norm as _sal_norm,
    )

    _EMPTY = {
        "program_id":          program_id,
        "skills_mercado":      [],
        "skills_programa":     [],
        "brechas":             [],
        "fortalezas":          [],
        "exclusivas_programa": [],
        "cobertura_pct":       0.0,
        "transversales":       [],
        "brechas_criticas":    [],
        "n_matches":             0,
        "n_vacantes_muestra":    0,
        "evidencia_baja":        True,
    }
    try:
        from api.database import fetch_all

        # 1. Core market + curriculum analysis (shared with _run_redesign)
        core = _market_analysis_for_program(program_id, fetch_all)
        skills_mercado_raw   = core["skills_mercado_raw"]
        n_matches          = core["n_matches"]
        n_vacantes_muestra = core["n_vacantes_muestra"]
        fortalezas          = core["fortalezas"]
        brechas             = core["brechas"]
        transversales       = core["transversales"]
        cobertura_pct       = core["cobertura_pct"]
        exclusivas_programa = core["exclusivas_programa"]
        brechas_criticas    = core["brechas_criticas"]
        skills_programa     = core["skills_programa"]

        # 1b. Tipo-skill lookup (endpoint-specific — not needed by redesign)
        from api.tipo_skill import tipo_para_skill as _tipo_para_skill
        from backend.repositories.empleos_repository import _clean_tipo_skill
        from crawlers.storage.postgres_warehouse import canonicalize_skill

        tipo_rows = fetch_all(
            """
            SELECT
                LOWER(TRIM(COALESCE(js.canonical_skill, js.skill_family, js.skill_category, ''))) AS skill_key,
                MODE() WITHIN GROUP (ORDER BY COALESCE(NULLIF(TRIM(js.skill_category), ''), 'Unknown')) AS tipo_skill_raw
            FROM job_skills js
            JOIN ml_program_job_matches m ON m.empleo_id = js.job_id::text
            WHERE m.especializacion_id = %s
              AND m.run_id = (SELECT MAX(run_id) FROM ml_program_job_matches WHERE especializacion_id = %s)
              AND COALESCE(js.canonical_skill, js.skill_family, js.skill_category, '') != ''
            GROUP BY 1
            """,
            (program_id, program_id),
        )
        _UNCLASSIFIED = {"unknown", "unclassified", ""}

        tipo_lookup: dict[str, str] = {}
        for row in tipo_rows:
            key = (row["skill_key"] or "").strip()
            if not key:
                continue
            raw_cat = (row["tipo_skill_raw"] or "").strip().lower()
            if raw_cat in _UNCLASSIFIED:
                taxonomy_cat = canonicalize_skill(key).category
                tipo_lookup[key] = _clean_tipo_skill(None, taxonomy_cat)
            else:
                tipo_lookup[key] = _clean_tipo_skill(None, row["tipo_skill_raw"])

        skills_mercado = [
            {"skill": s["skill"], "frecuencia": s["frecuencia"], "tipo_skill": _tipo_para_skill(s["skill"], tipo_lookup)}
            for s in skills_mercado_raw
        ]

        # Enrich brechas, fortalezas, transversales, brechas_criticas with tipo_skill
        brechas = [{**b, "tipo_skill": _tipo_para_skill(b["skill"], tipo_lookup)} for b in brechas]
        brechas_criticas = [{**b, "tipo_skill": _tipo_para_skill(b["skill"], tipo_lookup)} for b in brechas_criticas]
        fortalezas = [{**f, "tipo_skill": _tipo_para_skill(f["skill"], tipo_lookup)} for f in fortalezas]
        transversales = [{**t, "tipo_skill": _tipo_para_skill(t["skill"], tipo_lookup)} for t in transversales]

        # 2 & 3. Cross-analysis handled in _market_analysis_for_program above.
        # fortalezas, brechas, transversales, cobertura_pct, exclusivas_programa,
        # brechas_criticas, skills_programa are already set from core.

        # 4. Build matriz_completa with tipo tags
        fortaleza_norms  = {_sal_norm(f["skill"]) for f in fortalezas}
        transversal_norms = {_sal_norm(t["skill"]) for t in transversales}
        matriz_completa = build_matriz_completa(
            skills_mercado, skills_programa, fortaleza_norms, transversal_norms
        )

        logger.info(
            "skills-analysis/%s: n_matches=%d, market=%d, prog=%d, "
            "fortalezas=%d, brechas=%d, transversales=%d, brechas_criticas=%d, matriz=%d",
            program_id, n_matches, len(skills_mercado), len(skills_programa),
            len(fortalezas), len(brechas), len(transversales), len(brechas_criticas),
            len(matriz_completa),
        )

        return {
            "program_id":          program_id,
            "skills_mercado":      skills_mercado,
            "skills_programa":     skills_programa,
            "brechas":             brechas,
            "fortalezas":          fortalezas,
            "exclusivas_programa": exclusivas_programa,
            "cobertura_pct":       cobertura_pct,
            "matriz_completa":     matriz_completa,
            # ── new fields (additive) ──────────────────────────────────────
            "transversales":       transversales,
            "brechas_criticas":    brechas_criticas,
            "n_matches":             n_matches,
            "n_vacantes_muestra":    n_vacantes_muestra,
            "evidencia_baja":        n_matches < 15,
        }
    except Exception as exc:
        logger.error("skills_analysis error program_id=%s: %s", program_id, exc, exc_info=True)
        return {**_EMPTY, "error": str(exc)}


@app.get("/semantic-search", response_model=SearchResponse, tags=["search"])
def semantic_search(
    q: str = Query(..., min_length=2, max_length=256),
    entity_type: str = Query(default="job", pattern="^(job|company|skill|role)$"),
    limit: int = Query(10, ge=1, le=25),
) -> dict[str, Any]:
    return services.semantic_search_results(q, entity_type=entity_type, limit=limit)


# ─── Pipeline endpoints ───────────────────────────────────────────────────────

# In-memory job store (Railway restarts clear it — sufficient for UX feedback)
_PIPELINE_JOBS: dict[str, dict[str, Any]] = {}

_SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
_PYTHON = sys.executable

ACQUISITION_STEPS = [
    ["run_acquisition.py", "--domain", "data_analytics",        "--source", "elempleo", "--limit", "20"],
    ["run_acquisition.py", "--domain", "data_analytics",        "--source", "magneto",  "--limit", "20"],
    ["run_acquisition.py", "--domain", "artificial_intelligence","--source", "elempleo", "--limit", "20"],
    ["run_acquisition.py", "--domain", "criminology",            "--source", "elempleo", "--limit", "20"],
]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_step(job: dict, label: str, cmd: list[str]) -> bool:
    job["current_step"] = label
    job["log"].append(f"[{_ts()}] START {label}")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        out = (result.stdout + result.stderr).strip()
        for line in out.splitlines()[-30:]:     # keep last 30 lines per step
            job["log"].append(line)
        if result.returncode != 0:
            job["log"].append(f"[{_ts()}] ERROR {label} (exit {result.returncode})")
            return False
        job["log"].append(f"[{_ts()}] DONE {label}")
        return True
    except subprocess.TimeoutExpired:
        job["log"].append(f"[{_ts()}] TIMEOUT {label}")
        return False
    except Exception as exc:
        job["log"].append(f"[{_ts()}] EXCEPTION {label}: {exc}")
        return False


def _run_pipeline(job_id: str, steps: list[str], program_id: int | None) -> None:
    job = _PIPELINE_JOBS[job_id]
    job["status"] = "running"
    job["started_at"] = _ts()
    errors: list[str] = []

    try:
        # Step 1 — load microcurrículos from Excel
        if "microcurriculos" in steps:
            ok = _run_step(
                job,
                "microcurriculos",
                [_PYTHON, os.path.join(_SCRIPTS_DIR, "load_microcurriculo_excel.py"), "--execute", "--yes"],
            )
            if not ok:
                errors.append("microcurriculos")

        # Step 2 — acquisition
        if "acquisition" in steps:
            for args in ACQUISITION_STEPS:
                script = args[0]
                label = f"acquisition:{args[2]}:{args[4]}"
                ok = _run_step(
                    job, label,
                    [_PYTHON, os.path.join(_SCRIPTS_DIR, script)] + args[1:],
                )
                if not ok:
                    errors.append(label)

        # Step 3 — matching
        if "matching" in steps:
            match_cmd = [
                _PYTHON,
                os.path.join(_SCRIPTS_DIR, "run_semantic_matching.py"),
                "--persist", "--min-score", "40",
            ]
            if program_id:
                match_cmd += ["--program-id", str(program_id)]
            ok = _run_step(job, "matching", match_cmd)
            if not ok:
                errors.append("matching")

    except Exception as exc:
        job["log"].append(f"[{_ts()}] FATAL: {exc}")
        errors.append("fatal")

    job["status"] = "error" if errors else "done"
    job["finished_at"] = _ts()
    job["errors"] = errors
    job["current_step"] = None


@app.post("/api/pipeline/run", tags=["pipeline"])
def pipeline_run(
    background_tasks: BackgroundTasks,
    body: dict[str, Any] = {},
) -> _UnicodeJSONResponse:
    steps_raw = body.get("steps") or ["microcurriculos"]
    program_id = body.get("program_id") or None
    if program_id is not None:
        try:
            program_id = int(program_id)
        except (TypeError, ValueError):
            program_id = None

    job_id = str(uuid.uuid4())[:8]
    _PIPELINE_JOBS[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "steps": steps_raw,
        "program_id": program_id,
        "created_at": _ts(),
        "started_at": None,
        "finished_at": None,
        "current_step": None,
        "errors": [],
        "log": [],
    }
    background_tasks.add_task(_run_pipeline, job_id, steps_raw, program_id)
    return _UnicodeJSONResponse({
        "job_id": job_id,
        "status": "queued",
        "message": "El matching semántico corre localmente o via GitHub Actions (cada noche). El botón solo recarga microcurrículos desde Excel.",
    })


# ─── Market Context ───────────────────────────────────────────────────────────

_MARKET_STUDIES = [
    {
        "title": "World Economic Forum — Future of Jobs Report 2025",
        "summary": (
            "Cifras clave verificadas: "
            "(1) La IA y la gestión de macrodatos (big data) encabezan la lista de habilidades de más rápido "
            "crecimiento global, seguidas de redes/ciberseguridad y alfabetización tecnológica. "
            "(2) El pensamiento analítico es la habilidad básica más buscada: 7 de cada 10 empresas la "
            "consideran esencial. "
            "(3) Se proyecta una creación neta de 170 millones de empleos para 2030, siendo especialistas "
            "en big data, ingenieros fintech y especialistas en IA/ML los roles de mayor crecimiento "
            "porcentual. "
            "(4) El 39% de las habilidades actuales de los trabajadores se transformará o quedará obsoleta "
            "para 2030. "
            "(5) El 59% de la fuerza laboral mundial necesitará upskilling o reskilling en los próximos años. "
            "(6) El 63% de los empleadores identifica la brecha de habilidades como su principal barrera "
            "de transformación."
        ),
        "url": "https://www.weforum.org/publications/the-future-of-jobs-report-2025",
    },
    {
        "title": "OLE Colombia — Observatorio Laboral para la Educación, Ministerio de Educación Nacional",
        "summary": (
            "Cifras verificadas del sistema oficial de seguimiento a egresados de educación superior en Colombia: "
            "(1) En 2023, los graduados de posgrado registraron una tasa de vinculación laboral (cotizantes) "
            "del 91,3%, frente a 73,4% en pregrado — la formación de posgrado mejora significativamente "
            "la inserción laboral. "
            "(2) La tasa nacional de cotizantes fue de 77,9% en 2022, con tendencia ascendente sostenida "
            "desde 2010."
        ),
        "url": "https://ole.mineducacion.gov.co",
    },
    {
        "title": "Tendencias del Mercado Laboral Colombia 2026 — Adecco / ManpowerGroup",
        "summary": (
            "Cifras verificadas sobre el mercado laboral colombiano en 2026: "
            "(1) Según Adecco Colombia, las cinco áreas con mayor proyección de empleabilidad son: "
            "analítica de datos / business intelligence / ciencia de datos, ciberseguridad, "
            "automatización e integración de IA, ventas consultivas con enfoque analítico, y "
            "sostenibilidad/transición energética. "
            "(2) La selección de talento prioriza evidencia de competencias medibles sobre volumen de "
            "contratación. "
            "(3) Según Experis/ManpowerGroup (Expectativas sobre Talento Tecnológico Q1 2026), el 68% "
            "de las empresas en Colombia reporta dificultad para encontrar talento en los ámbitos de "
            "TI y datos, frente a un país que proyecta necesitar 85.000 talentos digitales adicionales "
            "para fin de la década."
        ),
        "url": "https://www.adecco.com.co",
    },
]

# In-memory cache: program_id → {analisis, generado_en}
_MARKET_CONTEXT_CACHE: dict[int, dict[str, Any]] = {}


@app.post("/api/dashboard/market-context/{program_id}", tags=["dashboard"])
def market_context(program_id: int, refresh: bool = False) -> dict[str, Any]:
    """Generate AI-personalized market context analysis for a program, cached per program_id.
    Pass ?refresh=true to force regeneration (bypasses in-memory cache).
    """
    import datetime

    # Return cached result if available (unless refresh requested)
    if not refresh and program_id in _MARKET_CONTEXT_CACHE:
        return _MARKET_CONTEXT_CACHE[program_id]

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "analisis": "Análisis no disponible: OPENAI_API_KEY no configurada.",
            "generado_en": datetime.datetime.utcnow().isoformat(),
            "error": True,
        }

    try:
        # Get program skills data
        sa = dashboard_skills_analysis(program_id)
        brechas    = [b["skill"] for b in sa.get("brechas", [])[:8]]
        fortalezas = [f["skill"] for f in sa.get("fortalezas", [])[:6]]

        # Get program name
        from api.database import fetch_one
        row = fetch_one(
            "SELECT nombre FROM especializaciones WHERE id = %s",
            (program_id,),
        )
        nombre_programa = row["nombre"] if row else f"Programa {program_id}"

        # Get pertinencia score from latest run
        score_row = fetch_one(
            """
            SELECT ROUND(AVG(score_match)::numeric, 1) AS score
            FROM ml_program_job_matches
            WHERE especializacion_id = %s
              AND run_id = (SELECT MAX(id) FROM ml_training_runs WHERE task_name = 'program_job_match')
            """,
            (program_id,),
        )
        score = float(score_row["score"] or 0) if score_row else 0.0

        # Derive domain label from program name for domain-specific framing
        nombre_lower = nombre_programa.lower()
        if any(w in nombre_lower for w in ("dato", "analítica", "analytics", "inteligencia artificial", " ia ", "machine", "big data")):
            dominio = "tecnología de datos e inteligencia artificial"
        elif any(w in nombre_lower for w in ("ciberseguridad", "seguridad inform", "redes", "devops", "sistemas")):
            dominio = "ciberseguridad y tecnología"
        elif any(w in nombre_lower for w in ("crimin", "victimol", "derecho", "juridic", "penal")):
            dominio = "ciencias jurídicas y sociales"
        elif any(w in nombre_lower for w in ("neuropsicol", "psicol", "educaci", "pedagog", "clíni")):
            dominio = "salud mental y educación"
        elif any(w in nombre_lower for w in ("gestion", "gestión", "administr", "negocio", "finanz", "contabl")):
            dominio = "gestión y negocios"
        else:
            dominio = "su área disciplinar"

        # Top skills demanded by market for this program (with frequency)
        skills_mercado_top = sa.get("skills_mercado", [])[:10]
        mercado_str = ", ".join(
            f"{s['skill']} ({s['frecuencia']} vacantes)" for s in skills_mercado_top
        ) if skills_mercado_top else "sin datos disponibles"

        # Top 2-3 skill gaps as "oportunidades de fortalecimiento" (soft framing, not deficit list)
        oportunidades_str = ", ".join(brechas[:3]) if brechas else "ninguna identificada"

        # Fortalezas = market skills already covered by curriculum
        fortalezas_str = ", ".join(fortalezas[:5]) if fortalezas else "ninguna identificada"

        studies_text = "\n\n".join(
            f"[{s['title']}]\n{s['summary']}" for s in _MARKET_STUDIES
        )

        prompt = (
            f"Eres un analista de tendencias del mercado laboral especializado en {dominio}.\n\n"
            f"DATOS DE MERCADO VERIFICADOS (usa las cifras tal como aparecen — no las parafrasees "
            f"vagamente ni las atribuyas a la fuente incorrecta):\n\n"
            f"{studies_text}\n\n"
            f"CONTEXTO DEL PROGRAMA '{nombre_programa}':\n"
            f"- Dominio de formación: {dominio}\n"
            f"- Skills que el mercado más demanda para este tipo de perfil: {mercado_str}\n"
            f"- Fortalezas ya presentes en el currículo: {fortalezas_str}\n"
            f"- Áreas con oportunidad de fortalecimiento: {oportunidades_str}\n\n"
            f"INSTRUCCIÓN: Escribe un párrafo de 3-4 oraciones en español, dirigido a un comité "
            f"curricular, que presente el panorama de hacia dónde se dirige el campo de "
            f"'{nombre_programa}' según estos tres estudios.\n\n"
            f"El eje del párrafo son las TENDENCIAS del área — qué habilidades están creciendo, "
            f"qué está demandando el mercado, cómo está evolucionando la empleabilidad en este campo — "
            f"NO una lista de lo que le falta al currículo.\n\n"
            f"Puedes mencionar las áreas con oportunidad de fortalecimiento de forma natural y breve "
            f"(una sola frase, al pasar), como contexto adicional que el comité puede considerar, "
            f"pero esto no debe ser el tema central ni sonar a auditoría de déficits.\n\n"
            f"Cita el estudio que respalda cada tendencia (WEF, OLE Colombia o Adecco/Experis), "
            f"con cifras exactas. Tono informativo y prospectivo. "
            f"Sin introducción, título ni conclusión — solo el párrafo."
        )

        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=400,
        )
        analisis = response.choices[0].message.content.strip()

        result = {
            "analisis": analisis,
            "generado_en": datetime.datetime.utcnow().isoformat(),
            "error": False,
        }
        _MARKET_CONTEXT_CACHE[program_id] = result
        return result

    except Exception as exc:
        logger.error("market_context error program_id=%s: %s", program_id, exc, exc_info=True)
        return {
            "analisis": f"Error al generar el análisis: {exc}",
            "generado_en": datetime.datetime.utcnow().isoformat(),
            "error": True,
        }


# ─── Curriculum Redesign ──────────────────────────────────────────────────────

# In-memory cache: program_id → redesign result (cleared on new POST)
_REDESIGN_CACHE: dict[int, dict[str, Any]] = {}
# Job tracker for async redesign
_REDESIGN_JOBS: dict[str, dict[str, Any]] = {}


def _compute_tfidf_relevance(text: str, skills: list[str]) -> tuple[float, list[tuple[str, float]]]:
    """
    Return (max_similarity, [(skill, score), ...]) sorted by per-skill relevance to text DESC.

    Uses token overlap against the subject text: each skill token that appears in the text
    contributes to the score. This ensures each subject gets a different ranking because
    the scores depend on the subject's actual vocabulary.
    """
    import unicodedata as _udn
    import math

    def _n(s: str) -> str:
        return "".join(c for c in _udn.normalize("NFD", s.lower()) if _udn.category(c) != "Mn")

    text_norm = _n(text)
    text_tokens = set(text_norm.split())

    ranked: list[tuple[str, float]] = []
    for skill in skills:
        skill_norm = _n(skill)
        skill_tokens = skill_norm.split()
        if not skill_tokens:
            ranked.append((skill, 0.0))
            continue
        # Exact phrase match gets a big bonus
        phrase_bonus = 2.0 if skill_norm in text_norm else 0.0
        # Token overlap: fraction of skill tokens present in text
        hits = sum(1 for t in skill_tokens if t in text_tokens and len(t) >= 4)
        token_score = hits / len(skill_tokens)
        score = phrase_bonus + token_score
        ranked.append((skill, round(score, 4)))

    ranked.sort(key=lambda x: x[1], reverse=True)
    max_score = ranked[0][1] if ranked else 0.0
    return max_score, ranked


def _call_openai_for_ras(asignatura: str, clean_text: str, brechas_relevantes: list[str]) -> dict[str, Any]:
    """Call gpt-4o-mini to propose updated learning outcomes (RAs)."""
    import json as _json

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "ras_propuestos": [],
            "justificacion": "OPENAI_API_KEY no configurada en el entorno.",
        }

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        texto_resumido = clean_text[:900] if clean_text else "(sin texto disponible)"
        brechas_str = ", ".join(brechas_relevantes[:8])

        prompt = (
            f"Eres un diseñador curricular universitario colombiano experto en pertinencia académica. "
            f"Aquí están los contenidos/resultados de aprendizaje (RA) actuales "
            f"de la asignatura '{asignatura}':\n\n{texto_resumido}\n\n"
            f"El mercado laboral demanda estas competencias, asignadas a esta asignatura "
            f"por encaje temático con sus contenidos actuales: {brechas_str}\n\n"
            f"INSTRUCCIONES IMPORTANTES:\n"
            f"1. Verifica que la brecha sea académicamente coherente con el campo real de '{asignatura}'. "
            f"Si la asignación fue incorrecta (p. ej. se pide Excel a neuropsicología clínica), "
            f"DEBES responder con ras_propuestos: [] y explicar en justificacion por qué no aplica. "
            f"PROHIBIDO forzar propuestas cuando el contenido no encaja.\n"
            f"2. Solo propón RAs para brechas coherentes con el contenido de esta asignatura.\n"
            f"3. Para cada brecha coherente, propón 1 o 2 RAs NUEVOS o MODIFICADOS en formato académico "
            f"universitario (código RA-XXX, verbo de Bloom, contenido medible y específico).\n\n"
            f"Responde ÚNICAMENTE en JSON con esta estructura exacta:\n"
            f'{{"ras_propuestos": [{{"codigo": "RA-001", "texto": "...", '
            f'"skills_incorporadas": ["..."], "tipo": "nuevo", "ra_original_codigo": null}}], '
            f'"justificacion": "..."}}'
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=800,
        )
        result = _json.loads(response.choices[0].message.content)
        # Ensure expected keys exist
        result.setdefault("ras_propuestos", [])
        result.setdefault("justificacion", "")
        return result
    except Exception as exc:
        logger.error("openai_call_error asignatura=%s: %s", asignatura, exc)
        return {
            "ras_propuestos": [],
            "justificacion": f"Error al llamar a OpenAI: {exc}",
        }


MAX_BRECHAS_PER_OPENAI_CALL: int = 4


def _merge_ra_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge multiple OpenAI RA call results into one."""
    merged_ras: list[dict[str, Any]] = []
    justificaciones: list[str] = []
    for r in results:
        merged_ras.extend(r.get("ras_propuestos", []))
        j = r.get("justificacion", "")
        if j:
            justificaciones.append(j)
    return {
        "ras_propuestos": merged_ras,
        "justificacion":  " | ".join(justificaciones) if justificaciones else "",
    }


def _run_redesign(job_id: str, program_id: int) -> None:
    """Background task: analyze curriculum vs brechas and call OpenAI for each relevant subject."""
    job = _REDESIGN_JOBS[job_id]

    def _update(status: str, **kw: Any) -> None:
        job.update({"status": status, **kw})

    try:
        from api.database import fetch_all

        _update("running", current_step="Cargando microcurrículos")

        # 1. Fetch microcurriculos for this program (excludes test/sandbox rows)
        mc_rows = fetch_all(
            f"""
            SELECT m.id, m.asignatura, m.clean_text,
                   COALESCE(m.asignatura, m.source_document) AS nombre
            FROM microcurriculos m
            WHERE m.specialization_id = %s
              AND m.clean_text IS NOT NULL
              AND length(m.clean_text) > 50
              {_SQL_FILTRO_NO_PRUEBA}
            ORDER BY m.asignatura NULLS LAST
            """,
            (program_id,),
        )

        logger.info("[REDESIGN-DEBUG] program_id=%s mc_rows_count=%d asignaturas=%s",
                    program_id, len(mc_rows),
                    [r.get("nombre") or r.get("asignatura") or str(r.get("id")) for r in mc_rows])

        if not mc_rows:
            _update("error", error="No se encontraron microcurrículos para este programa. Ejecuta primero el pipeline de carga.")
            return

        # 2. Compute brechas using unified market analysis (same SQL as /skills-analysis)
        _update("running", current_step="Calculando brechas curriculares")

        analysis = _market_analysis_for_program(program_id, fetch_all)
        # Use ALL brechas ordered by frecuencia_mercado; criticas tracked for labeling
        all_brechas_data = sorted(
            analysis["brechas"], key=lambda x: -x.get("frecuencia_mercado", 0)
        )
        brechas_criticas_set = {b["skill"] for b in analysis["brechas_criticas"]}
        n_matches = analysis["n_matches"]

        logger.info(
            "[REDESIGN-DEBUG] program_id=%s n_matches=%d market_skills=%d prog_skills=%d "
            "brechas=%d brechas_criticas=%d",
            program_id, n_matches,
            len(analysis["fortalezas"]) + len(analysis["brechas"]),
            len(analysis["skills_programa"]),
            len(analysis["brechas"]),
            len(analysis["brechas_criticas"]),
        )

        if analysis["evidencia_baja"]:
            result = {
                "program_id":             program_id,
                "asignaturas_analizadas": len(mc_rows),
                "advertencia": (
                    f"Evidencia insuficiente: solo {n_matches} vacantes en la muestra de mercado. "
                    "Se necesitan al menos 15 para un rediseño confiable."
                ),
                "propuestas": [],
                "evidencia_baja": True,
            }
            _REDESIGN_CACHE[program_id] = result
            _update("done", result=result)
            return

        if not all_brechas_data:
            _update("done", result={
                "program_id":             program_id,
                "asignaturas_analizadas": len(mc_rows),
                "brechas_totales":        0,
                "brechas_criticas_count": 0,
                "n_matches":              n_matches,
                "advertencia": "No se encontraron brechas curriculares — el programa ya cubre las skills del mercado.",
                "propuestas":             [],
                "brechas_sin_asignatura": [],
            })
            _REDESIGN_CACHE[program_id] = _REDESIGN_JOBS[job_id].get("result", {})
            return

        # 3. Assign each brecha to the best-fit asignaturas
        from api.redesign_assignment import assign_brechas as _assign_brechas, compute_confianza as _compute_confianza

        _update("running", current_step="Asignando brechas a asignaturas")

        mc_list = [
            {
                "id":         row["id"],
                "asignatura": row.get("nombre") or row.get("asignatura"),
                "nombre":     row.get("nombre") or row.get("asignatura"),
                "clean_text": (row.get("clean_text") or "").strip(),
            }
            for row in mc_rows
        ]
        assignment = _assign_brechas(mc_list, all_brechas_data)
        per_asignatura   = assignment["per_asignatura"]
        brechas_sin_asig = assignment["brechas_sin_asignatura"]

        # Mark is_critica on each assigned brecha
        for item in per_asignatura.values():
            for b in item["brechas_asignadas"]:
                b["is_critica"] = b["skill"] in brechas_criticas_set

        logger.info(
            "[REDESIGN-DEBUG] program_id=%s brechas_criticas=%d asignaturas_con_brechas=%d "
            "brechas_sin_asignatura=%d",
            program_id, len(brechas_criticas_data),
            len(per_asignatura), len(brechas_sin_asig),
        )

        debug_info = {
            "fix_version":            "v7-all-brechas",
            "n_matches":              n_matches,
            "brechas_totales":        len(all_brechas_data),
            "brechas_criticas_count": len(analysis["brechas_criticas"]),
            "brechas_sin_asignatura": [b["skill"] for b in brechas_sin_asig],
            "asignaturas_con_brechas": list(per_asignatura.keys()),
        }

        if not per_asignatura:
            result = {
                "program_id":             program_id,
                "asignaturas_analizadas": len(mc_rows),
                "brechas_totales":        len(all_brechas_data),
                "brechas_criticas_count": len(analysis["brechas_criticas"]),
                "n_matches":              n_matches,
                "advertencia": "Ninguna brecha pudo asignarse a una asignatura con encaje suficiente.",
                "propuestas":             [],
                "brechas_sin_asignatura": brechas_sin_asig,
                "debug":                  debug_info,
            }
            _REDESIGN_CACHE[program_id] = result
            _update("done", result=result)
            return

        # 4. Call OpenAI only for asignaturas that have assigned brechas.
        #    If >MAX_BRECHAS_PER_OPENAI_CALL brechas assigned, split into chunks
        #    and merge results (no brecha is discarded).
        propuestas: list[dict[str, Any]] = []
        items_sorted = sorted(
            per_asignatura.values(),
            key=lambda x: (-max(b["score"] for b in x["brechas_asignadas"]), x["mc_id"]),
        )
        for i, item in enumerate(items_sorted):
            _update("running", current_step=f"Generando RAs con IA ({i+1}/{len(items_sorted)}): {item['asignatura'][:40]}")
            brechas_asig = [b["skill"] for b in item["brechas_asignadas"]]

            if len(brechas_asig) > MAX_BRECHAS_PER_OPENAI_CALL:
                chunks = [
                    brechas_asig[j:j + MAX_BRECHAS_PER_OPENAI_CALL]
                    for j in range(0, len(brechas_asig), MAX_BRECHAS_PER_OPENAI_CALL)
                ]
                chunk_results = [
                    _call_openai_for_ras(
                        asignatura=item["asignatura"],
                        clean_text=item["clean_text"],
                        brechas_relevantes=chunk,
                    )
                    for chunk in chunks
                ]
                ai_result = _merge_ra_results(chunk_results)
            else:
                ai_result = _call_openai_for_ras(
                    asignatura=item["asignatura"],
                    clean_text=item["clean_text"],
                    brechas_relevantes=brechas_asig,
                )

            all_skills: list[str] = []
            for ra in ai_result.get("ras_propuestos", []):
                all_skills.extend(ra.get("skills_incorporadas", []))

            # Annotate brechas_relevantes with ⚠ for critical brechas
            brechas_relevantes_labeled = [
                f"⚠ {b}" if b in brechas_criticas_set else b
                for b in brechas_asig
            ]

            propuestas.append({
                "asignatura":          item["asignatura"],
                "brechas_asignadas":   item["brechas_asignadas"],
                "relevancia_score":    max(b["score"] for b in item["brechas_asignadas"]),
                "confianza":           _compute_confianza(item["brechas_asignadas"]),
                "brechas_relevantes":  brechas_asig,
                "brechas_relevantes_labeled": brechas_relevantes_labeled,
                "ras_actuales_texto":  item["clean_text"][:600],
                "ras_propuestos":      ai_result.get("ras_propuestos", []),
                "skills_incorporadas": list(set(all_skills)),
                "justificacion":       ai_result.get("justificacion", ""),
            })

        result = {
            "program_id":             program_id,
            "asignaturas_analizadas": len(mc_rows),
            "brechas_totales":        len(all_brechas_data),
            "brechas_criticas_count": len(analysis["brechas_criticas"]),
            "n_matches":              n_matches,
            "propuestas":             propuestas,
            "brechas_sin_asignatura": brechas_sin_asig,
            "debug":                  debug_info,
        }
        _REDESIGN_CACHE[program_id] = result
        _update("done", result=result)
        logger.info("redesign/%s done: %d proposals", program_id, len(propuestas))

    except Exception as exc:
        logger.error("redesign_error program_id=%s: %s", program_id, exc, exc_info=True)
        _update("error", error=str(exc))


@app.post("/api/curriculum/redesign/{program_id}", tags=["curriculum"])
def curriculum_redesign_start(
    program_id: int,
    background_tasks: BackgroundTasks,
) -> _UnicodeJSONResponse:
    """Start async curriculum redesign analysis. Poll /status/{job_id} for progress."""
    job_id = str(uuid.uuid4())[:8]
    _REDESIGN_JOBS[job_id] = {
        "job_id":       job_id,
        "program_id":   program_id,
        "status":       "queued",
        "current_step": None,
        "error":        None,
        "result":       None,
    }
    background_tasks.add_task(_run_redesign, job_id, program_id)
    return _UnicodeJSONResponse({"job_id": job_id, "status": "queued"})


@app.get("/api/curriculum/redesign/status/{job_id}", tags=["curriculum"])
def curriculum_redesign_status(job_id: str) -> _UnicodeJSONResponse:
    """Poll redesign job status."""
    job = _REDESIGN_JOBS.get(job_id)
    if not job:
        return _UnicodeJSONResponse({"error": "job not found"}, status_code=404)  # type: ignore[name-defined]
    return _UnicodeJSONResponse(job)


@app.get("/api/curriculum/redesign/{program_id}/download", tags=["curriculum"])
def curriculum_redesign_download(program_id: int):
    """Generate and download a .docx report with the redesign proposals."""
    from fastapi.responses import StreamingResponse
    import io

    result = _REDESIGN_CACHE.get(program_id)
    if not result:
        return _UnicodeJSONResponse(
            {"error": "No hay análisis disponible. Ejecuta primero POST /api/curriculum/redesign/{program_id}"},
            status_code=404,  # type: ignore[name-defined]
        )

    propuestas = result.get("propuestas", [])
    if not propuestas:
        return _UnicodeJSONResponse(
            {"error": "El análisis no generó propuestas para este programa.", "advertencia": result.get("advertencia", "")},
            status_code=422,  # type: ignore[name-defined]
        )

    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()

        # Title
        from api.database import fetch_one
        prog_row = fetch_one("SELECT nombre FROM especializaciones WHERE id = %s", (program_id,))
        prog_nombre = prog_row["nombre"] if prog_row else f"Programa {program_id}"

        title = doc.add_heading(f"Propuesta de Actualización Curricular", level=1)
        title.runs[0].font.color.rgb = RGBColor(0x0D, 0x21, 0x58)

        subtitle = doc.add_paragraph(prog_nombre)
        subtitle.runs[0].bold = True
        subtitle.runs[0].font.size = Pt(13)

        from datetime import date
        doc.add_paragraph(f"Generado: {date.today().isoformat()} · Observatorio UNIR Colombia")
        n_sin_asig = len(result.get("brechas_sin_asignatura", []))
        doc.add_paragraph(
            f"Resumen: {len(propuestas)} asignaturas con propuestas · "
            f"{result.get('brechas_criticas_count', 0)} brechas críticas "
            f"(de {result.get('brechas_totales', 0)} brechas) · "
            f"{n_sin_asig} sin asignatura natural."
        )
        doc.add_paragraph("")

        # Per-subject section
        for prop in propuestas:
            doc.add_heading(prop["asignatura"], level=2)
            p = doc.add_paragraph()
            confianza_label = prop.get("confianza") or "—"
            p.add_run("Confianza: ").bold = True
            labeled = prop.get("brechas_relevantes_labeled") or prop.get("brechas_relevantes", [])
            p.add_run(f"{confianza_label} · Brechas: {', '.join(labeled[:5])}")

            # Comparison table
            table = doc.add_table(rows=1, cols=2)
            table.style = "Table Grid"
            hdr = table.rows[0].cells
            hdr[0].text = "RAs / Contenido Actual"
            hdr[1].text = "RAs Propuestos (IA)"
            for cell in hdr:
                for para in cell.paragraphs:
                    for run in para.runs:
                        run.bold = True
                        run.font.color.rgb = RGBColor(0x0D, 0x21, 0x58)

            row_cells = table.add_row().cells
            row_cells[0].text = (prop.get("ras_actuales_texto") or "Sin texto disponible")[:500]

            right = row_cells[1]
            for ra in prop.get("ras_propuestos", []):
                p_ra = right.add_paragraph()
                run_code = p_ra.add_run(f"[{ra.get('codigo','RA')}] ")
                run_code.bold = True
                if ra.get("tipo") == "nuevo":
                    run_code.font.color.rgb = RGBColor(0x05, 0x96, 0x69)  # green
                else:
                    run_code.font.color.rgb = RGBColor(0xD9, 0x77, 0x06)  # amber
                p_ra.add_run(ra.get("texto", ""))

            if prop.get("justificacion"):
                jus = doc.add_paragraph()
                jus.add_run("Justificación: ").italic = True
                jus.add_run(prop["justificacion"])

            doc.add_paragraph("")

        # Brechas sin asignatura natural
        brechas_sin_docx = result.get("brechas_sin_asignatura", [])
        if brechas_sin_docx:
            doc.add_heading("Brechas sin asignatura natural", level=2)
            doc.add_paragraph(
                "Las siguientes brechas del mercado no encontraron encaje suficiente "
                "en ninguna asignatura existente. Se recomienda considerar una nueva "
                "electiva o módulo transversal."
            )
            for b in brechas_sin_docx:
                doc.add_paragraph(
                    f"{b['skill']}  (demanda: {b.get('frecuencia_mercado', 0)} vacantes)"
                )

        # Footer
        n_matches_footer = result.get("n_matches", 0)
        doc.add_paragraph(
            f"Motor de Pertinencia Académica v2 · UNIR Colombia · "
            f"Datos: muestra de mercado laboral Colombia, n={n_matches_footer} vacantes"
        ).runs[0].font.color.rgb = RGBColor(0x9C, 0xA3, 0xAF)

        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)

        filename = f"redesign_curricular_programa_{program_id}.docx"
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        logger.error("redesign_download_error program_id=%s: %s", program_id, exc, exc_info=True)
        return _UnicodeJSONResponse({"error": f"Error generando documento: {exc}"}, status_code=500)  # type: ignore[name-defined]


@app.get("/api/pipeline/status/{job_id}", tags=["pipeline"])
def pipeline_status(job_id: str) -> _UnicodeJSONResponse:
    job = _PIPELINE_JOBS.get(job_id)
    if not job:
        return _UnicodeJSONResponse({"error": "job not found"}, status_code=404)  # type: ignore[name-defined]
    # Return last 50 log lines to keep response light
    payload = {**job, "log": job["log"][-50:]}
    return _UnicodeJSONResponse(payload)  # type: ignore[name-defined]


# ── Deep Curriculum Analysis ──────────────────────────────────────────────────

@app.get("/api/programs/{program_id}/deep-analysis", tags=["curriculum"])
def get_deep_analysis(program_id: int) -> _UnicodeJSONResponse:
    """Return the most recent persisted deep curriculum analysis, or 404."""
    try:
        from intelligence.curriculum_deep_analysis_engine import get_latest_deep_analysis
        result = get_latest_deep_analysis(program_id)
        if result is None:
            return _UnicodeJSONResponse(  # type: ignore[name-defined]
                {"error": f"No deep analysis found for program {program_id}. "
                          "POST to /api/programs/{id}/deep-analysis/generate to create one."},
                status_code=404,
            )
        return _UnicodeJSONResponse(result)  # type: ignore[name-defined]
    except Exception as exc:
        logger.exception("get_deep_analysis failed for program_id=%s", program_id)
        return _UnicodeJSONResponse({"error": str(exc)}, status_code=500)  # type: ignore[name-defined]


@app.post("/api/programs/{program_id}/deep-analysis/generate", tags=["curriculum"])
def generate_deep_analysis(program_id: int) -> _UnicodeJSONResponse:
    """Trigger a new LLM-based deep curriculum analysis and persist it."""
    try:
        from intelligence.curriculum_deep_analysis_engine import build_deep_analysis
        from api.database import fetch_all as _fa

        # Compute market context best-effort; analysis still runs without it
        market_ctx = None
        try:
            analysis_data = _market_analysis_for_program(program_id, _fa)
            all_mkt = (
                [{"skill": s["skill"], "frecuencia": s.get("frecuencia_mercado", 0)}
                 for s in analysis_data.get("fortalezas", [])]
                + [{"skill": b["skill"], "frecuencia": b.get("frecuencia_mercado", 0)}
                   for b in analysis_data.get("brechas", [])]
            )
            all_mkt.sort(key=lambda x: x["frecuencia"], reverse=True)
            market_ctx = {
                "top_skills":      all_mkt[:25],   # LLM context only (top 25)
                "all_skills":      all_mkt,         # full list for evidencia_mercado cross-ref
                "brechas_criticas": analysis_data.get("brechas_criticas", []),
                "n_matches":       analysis_data.get("n_matches", 0),
            }
        except Exception:
            logger.warning("market context unavailable for deep-analysis program_id=%s", program_id)

        result = build_deep_analysis(program_id, market_context=market_ctx, persist=True)
        return _UnicodeJSONResponse(result)  # type: ignore[name-defined]
    except ValueError as exc:
        return _UnicodeJSONResponse({"error": str(exc)}, status_code=404)  # type: ignore[name-defined]
    except RuntimeError as exc:
        return _UnicodeJSONResponse({"error": str(exc)}, status_code=503)  # type: ignore[name-defined]
    except Exception as exc:
        logger.exception("generate_deep_analysis failed for program_id=%s", program_id)
        return _UnicodeJSONResponse({"error": str(exc)}, status_code=500)  # type: ignore[name-defined]


@app.get("/api/programas/{program_id}/market-filters", tags=["market"])
def market_filter_options(program_id: int) -> dict:
    """Return distinct filter option values for the market dashboards."""
    try:
        from backend.repositories.empleos_repository import fetch_market_filter_options
        return fetch_market_filter_options()
    except Exception as exc:
        logger.warning("market_filter_options failed: %s", exc)
        return {"periodos": [], "dominios": [], "seniorities": [], "ciudades": [], "portales": []}


@app.get("/api/programas/{program_id}/perfiles-ocupacionales", tags=["market"])
def get_occupational_profiles(
    program_id: int,
    periodo: str | None = None,
    dominio: str | None = None,
    ciudad: str | None = None,
    seniority: str | None = None,
    portal: str | None = None,
) -> list:
    """Return top occupational profiles (by semantic_title_family) for a program."""
    try:
        from backend.repositories.empleos_repository import fetch_occupational_profiles
        return fetch_occupational_profiles(
            program_id, periodo=periodo, dominio=dominio, ciudad=ciudad, seniority=seniority, portal=portal
        )
    except Exception as exc:
        logger.warning("get_occupational_profiles failed: %s", exc)
        return []


@app.get("/api/programas/{program_id}/perfil-skills", tags=["market"])
def get_profile_skills(
    program_id: int,
    perfil: str,
    periodo: str | None = None,
    dominio: str | None = None,
    ciudad: str | None = None,
    seniority: str | None = None,
    portal: str | None = None,
) -> list:
    """Return skills for jobs matching a semantic_title_family for a given program."""
    try:
        from backend.repositories.empleos_repository import fetch_profile_skills
        return fetch_profile_skills(
            perfil, program_id, periodo=periodo, dominio=dominio, ciudad=ciudad, seniority=seniority, portal=portal
        )
    except Exception as exc:
        logger.warning("get_profile_skills failed: %s", exc)
        return []


@app.get("/api/programas/{program_id}/perfiles-kpis", tags=["market"])
def get_profile_kpis(
    program_id: int,
    periodo: str | None = None,
    dominio: str | None = None,
    ciudad: str | None = None,
    seniority: str | None = None,
    portal: str | None = None,
) -> dict:
    """Return aggregate KPIs for the perfiles ocupacionales view scoped to a program."""
    try:
        from backend.repositories.empleos_repository import fetch_profile_kpis
        return fetch_profile_kpis(
            program_id, periodo=periodo, dominio=dominio, ciudad=ciudad, seniority=seniority, portal=portal
        )
    except Exception as exc:
        logger.warning("get_profile_kpis failed: %s", exc)
        return {"total_ofertas": 0, "total_perfiles": 0, "total_skills": 0}


@app.get("/api/programas/{program_id}/sectores", tags=["market"])
def get_sectores(program_id: int) -> list:
    """Return sector distribution for jobs matched to a program."""
    try:
        from backend.repositories.empleos_repository import fetch_sectores
        return fetch_sectores(program_id)
    except Exception as exc:
        logger.warning("get_sectores failed: %s", exc)
        return []


@app.get("/api/programas/{program_id}/ciudades", tags=["market"])
def get_ciudades(program_id: int) -> list:
    """Return city distribution for jobs matched to a program."""
    try:
        from backend.repositories.empleos_repository import fetch_ciudades
        return fetch_ciudades(program_id)
    except Exception as exc:
        logger.warning("get_ciudades failed: %s", exc)
        return []


@app.get("/api/programas/{program_id}/tendencia-mensual", tags=["market"])
def get_tendencia_mensual(program_id: int) -> list:
    """Return monthly job counts for jobs matched to a program."""
    try:
        from backend.repositories.empleos_repository import fetch_tendencia_mensual
        return fetch_tendencia_mensual(program_id)
    except Exception as exc:
        logger.warning("get_tendencia_mensual failed: %s", exc)
        return []


@app.get("/api/programas/{program_id}/vacantes-filtros", tags=["market"])
def get_vacantes_filtros(program_id: int) -> dict:
    """Return distinct filter values (familia, cargo, empresa) for the Empleos view."""
    try:
        from backend.repositories.empleos_repository import fetch_vacantes_filtros
        return fetch_vacantes_filtros(program_id)
    except Exception as exc:
        logger.warning("get_vacantes_filtros failed: %s", exc)
        return {"familias": [], "cargos": [], "empresas": []}


@app.get("/api/programas/{program_id}/perfiles-homologados", tags=["market"])
def get_perfiles_homologados(program_id: int) -> dict:
    """Return occupational profile hierarchy (familia → perfiles → vacantes) for a program.

    Uses jobs.perfil_id populated by the homologation engine (Fase B).
    Jobs without a perfil_id are grouped under familia=null / perfil=null ('Sin clasificar').
    Sample definition: rank-1 per empleo_id from the latest run, activo jobs only
    (shared _MARKET_SAMPLE_CTE — no relevance_label filter on the sample).
    """
    SQL_FAMILIAS = f"""
        WITH {_MARKET_SAMPLE_CTE},
        vacantes AS (
            SELECT DISTINCT
                ms.empleo_id::bigint         AS job_id,
                j.title                      AS titulo_original,
                j.perfil_id,
                j.homologacion_estado,
                j.homologacion_confianza,
                op.nombre                    AS perfil_nombre,
                op.familia
            FROM market_sample ms
            JOIN jobs j ON j.id::text = ms.empleo_id
            LEFT JOIN occupational_profiles op ON op.id = j.perfil_id
            WHERE ms.especializacion_id = %(pid)s
              AND ms.empleo_id ~ '^[0-9]+$'
        ),
        total_cte AS (
            SELECT COUNT(DISTINCT job_id) AS total FROM vacantes
        ),
        por_familia AS (
            SELECT
                familia,
                perfil_id,
                perfil_nombre,
                COUNT(DISTINCT job_id)               AS vacantes,
                COUNT(DISTINCT titulo_original)       AS titulos_distintos,
                ARRAY_AGG(DISTINCT titulo_original
                          ORDER BY titulo_original)   AS titulos
            FROM vacantes
            GROUP BY familia, perfil_id, perfil_nombre
        )
        SELECT
            pf.*,
            t.total AS total_vacantes
        FROM por_familia pf, total_cte t
        ORDER BY pf.familia NULLS LAST, pf.vacantes DESC
    """
    SQL_KPIS = f"""
        WITH {_MARKET_SAMPLE_CTE},
        vacantes AS (
            SELECT DISTINCT
                ms.empleo_id::bigint         AS job_id,
                j.title                      AS titulo_original,
                j.perfil_id,
                j.homologacion_estado,
                op.familia
            FROM market_sample ms
            JOIN jobs j ON j.id::text = ms.empleo_id
            LEFT JOIN occupational_profiles op ON op.id = j.perfil_id
            WHERE ms.especializacion_id = %(pid)s
              AND ms.empleo_id ~ '^[0-9]+$'
        )
        SELECT
            COUNT(DISTINCT job_id)                                               AS total_vacantes,
            COUNT(DISTINCT familia)  FILTER (WHERE familia IS NOT NULL)          AS familias_identificadas,
            COUNT(DISTINCT perfil_id) FILTER (WHERE perfil_id IS NOT NULL)       AS perfiles_homologados,
            COUNT(DISTINCT titulo_original)                                       AS titulos_distintos,
            COUNT(DISTINCT job_id)   FILTER (WHERE homologacion_estado = 'auto') AS vacantes_homologadas,
            COUNT(DISTINCT job_id)   FILTER (WHERE homologacion_estado != 'auto'
                                                OR homologacion_estado IS NULL)  AS vacantes_sin_homologar,
            ROUND(
                100.0 * COUNT(DISTINCT job_id) FILTER (WHERE homologacion_estado = 'auto')
                / NULLIF(COUNT(DISTINCT job_id), 0), 1
            )                                                                    AS pct_homologadas,
            (
                SELECT familia
                FROM (
                    SELECT familia, COUNT(DISTINCT job_id) AS cnt
                    FROM vacantes
                    WHERE familia IS NOT NULL
                    GROUP BY familia
                    ORDER BY cnt DESC
                    LIMIT 1
                ) sub
            )                                                                    AS familia_top
        FROM vacantes
    """
    try:
        from api.database import fetch_all, fetch_one
        rows = fetch_all(SQL_FAMILIAS, {"pid": program_id})
        kpi_row = fetch_one(SQL_KPIS, {"pid": program_id})

        total = int(kpi_row["total_vacantes"]) if kpi_row else 0

        # Build familia → perfiles hierarchy
        familias: dict = {}
        for r in rows:
            fam_key = r["familia"] or "__sin_clasificar__"
            fam_label = r["familia"] or "Sin clasificar"
            if fam_key not in familias:
                familias[fam_key] = {"familia": fam_label, "vacantes": 0, "perfiles": []}
            familias[fam_key]["vacantes"] += int(r["vacantes"])
            familias[fam_key]["perfiles"].append({
                "perfil_id":        r["perfil_id"],
                "perfil":           r["perfil_nombre"] or "Sin clasificar",
                "vacantes":         int(r["vacantes"]),
                "titulos_distintos": int(r["titulos_distintos"]),
                "titulos":          list(r["titulos"] or [])[:20],
                "pct_total":        round(int(r["vacantes"]) / total * 100, 1) if total else 0,
            })

        familias_list = sorted(
            familias.values(),
            key=lambda f: (f["familia"] == "Sin clasificar", -f["vacantes"])
        )

        kpis = {
            "total_vacantes":        int(kpi_row["total_vacantes"])        if kpi_row else 0,
            "familias_identificadas": int(kpi_row["familias_identificadas"]) if kpi_row else 0,
            "perfiles_homologados":  int(kpi_row["perfiles_homologados"])  if kpi_row else 0,
            "titulos_distintos":     int(kpi_row["titulos_distintos"])     if kpi_row else 0,
            "vacantes_homologadas":  int(kpi_row["vacantes_homologadas"])  if kpi_row else 0,
            "vacantes_sin_homologar": int(kpi_row["vacantes_sin_homologar"]) if kpi_row else 0,
            "pct_homologadas":       float(kpi_row["pct_homologadas"] or 0) if kpi_row else 0.0,
            "familia_top":           kpi_row["familia_top"]                if kpi_row else None,
        }

        return {"kpis": kpis, "familias": familias_list}

    except Exception as exc:
        logger.warning("get_perfiles_homologados failed: %s", exc)
        return {"kpis": {
            "total_vacantes": 0, "familias_identificadas": 0, "perfiles_homologados": 0,
            "titulos_distintos": 0, "vacantes_homologadas": 0, "vacantes_sin_homologar": 0,
            "pct_homologadas": 0.0, "familia_top": None,
        }, "familias": []}


@app.get("/api/programas/{program_id}/top-vacantes", tags=["market"])
def get_top_vacantes(
    program_id: int,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=50),
    familia: str | None = None,
    cargo: str | None = None,
    empresa: str | None = None,
    nivel: str | None = None,
) -> dict:
    """Return a paginated list of top job matches for a program with optional filters."""
    try:
        from backend.repositories.empleos_repository import fetch_top_vacantes
        return fetch_top_vacantes(
            program_id,
            page=page,
            per_page=per_page,
            familia=familia,
            cargo=cargo,
            empresa=empresa,
            nivel=nivel,
        )
    except Exception as exc:
        logger.warning("get_top_vacantes failed: %s", exc)
        return {"total": 0, "page": page, "per_page": per_page, "items": []}


# ─── Market Studies ───────────────────────────────────────────────────────────

@app.get("/api/dashboard/market-studies/{program_id}", tags=["dashboard"])
def get_market_studies(program_id: int) -> dict[str, Any]:
    """Return structured market studies for a program, or empty hallazgos if none."""
    from api.market_studies import PROGRAM_STUDIES
    return PROGRAM_STUDIES.get(program_id, {"hallazgos": []})

