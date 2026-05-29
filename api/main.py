from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from api.contracts import HealthResponse, PaginatedResponse, SearchResponse
from api.logging import RequestLoggingMiddleware, configure_logging
from api import services


configure_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("api.main")


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


@app.get("/readiness", response_model=HealthResponse, tags=["system"])
def readiness() -> dict[str, Any]:
    snapshot = services.get_health_snapshot()
    snapshot["status"] = "ready" if snapshot["database"] == "connected" and snapshot["checks"].get("jobs_table") else "degraded"
    return snapshot


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


@app.get("/curriculum-gaps", response_model=PaginatedResponse, tags=["observatory"])
def curriculum_gaps(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    specialization: str | None = Query(default=None),
) -> dict[str, Any]:
    return services.list_curriculum_gaps(limit=limit, offset=offset, specialization=specialization)


@app.get("/recommendations", response_model=PaginatedResponse, tags=["observatory"])
def recommendations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    recommendation_type: str | None = Query(default=None),
    target_company: str | None = Query(default=None),
) -> dict[str, Any]:
    return services.list_recommendations(limit=limit, offset=offset, recommendation_type=recommendation_type, target_company=target_company)


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


@app.get("/market-forecast", response_model=PaginatedResponse, tags=["observatory"])
def market_forecast(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    entity_type: str | None = Query(default=None),
) -> dict[str, Any]:
    return services.list_market_forecast(limit=limit, offset=offset, entity_type=entity_type)


@app.get("/semantic-search", response_model=SearchResponse, tags=["search"])
def semantic_search(
    q: str = Query(..., min_length=2, max_length=256),
    entity_type: str = Query(default="job", pattern="^(job|company|skill|role)$"),
    limit: int = Query(10, ge=1, le=25),
) -> dict[str, Any]:
    return services.semantic_search_results(q, entity_type=entity_type, limit=limit)
