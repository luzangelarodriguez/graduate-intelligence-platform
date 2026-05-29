from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthChecks(BaseModel):
    database: bool = False
    labor_core: bool = False
    curriculum_core: bool = False
    ml_core: bool = False
    observatory: bool = False
    labor_core_tables: dict[str, bool] = Field(default_factory=dict)
    curriculum_core_tables: dict[str, bool] = Field(default_factory=dict)
    ml_core_tables: dict[str, bool] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: datetime
    layers: dict[str, bool] = Field(default_factory=dict)
    checks: HealthChecks = Field(default_factory=HealthChecks)
    observatory_status: dict[str, Any] = Field(default_factory=dict)
    observatory_freshness: dict[str, Any] = Field(default_factory=dict)


class PaginatedResponse(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0
    limit: int = 0
    offset: int = 0
    filters: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    entity_type: str
    count: int
    limit: int
    items: list[dict[str, Any]] = Field(default_factory=list)


class ProgramSkill(BaseModel):
    skill_id: int
    nombre: str
    conteo: int = 0


class Skill(ProgramSkill):
    pass


class Program(BaseModel):
    especializacion_id: int
    nombre_especializacion: str
    rol: str = ""
    total_skills_programa: int = 0
    total_herramientas: int = 0
    total_competencias: int = 0
    total_habilidades_blandas: int = 0
    promedio_match_mercado: float = 0.0
    porcentaje_match: float = 0.0
    max_match_mercado: float = 0.0
    total_empleos_relacionados: int = 0
    skills_cubiertas: int = 0
    skills: list[Skill] = Field(default_factory=list)


class Match(BaseModel):
    especializacion_id: int | None = None
    empleo_id: str
    titulo_empleo: str
    total_skills_empleo: int = 0
    total_skills_especializacion: int = 0
    skills_en_comun: int = 0
    porcentaje_match: float = 0.0


class RecommendationProgram(BaseModel):
    nombre: str
    match: float
    reason: str


class ProgramDashboardKpis(BaseModel):
    alignment_score: float = 0.0
    missing_critical_skills: int = 0
    high_demand_roles: int = 0
    employability_trend: float = 0.0
    digital_coverage: float = 0.0
    curricular_update_signal: str = ""


class ProgramDashboardStatus(BaseModel):
    curricular_status: str = ""
    curricular_status_detail: str = ""
    ai_signal: str = ""
    trend_label: str = ""


class ProgramDashboardInsights(BaseModel):
    detected: str = ""
    ai_recommends: list[str] = Field(default_factory=list)
    emerging_gap: str = ""
    critical_signal: str = ""


class ProgramDashboardResponse(BaseModel):
    program_id: int
    program: Program
    kpis: ProgramDashboardKpis
    status: ProgramDashboardStatus
    missing_skills: list[Skill] = Field(default_factory=list)
    matches: list[Match] = Field(default_factory=list)
    recommendations: list[RecommendationProgram] = Field(default_factory=list)
    insights: ProgramDashboardInsights
    source: str


class ProgramPageResponse(BaseModel):
    items: list[Program] = Field(default_factory=list)
    count: int = 0
    total: int = 0
    limit: int = 0
    offset: int = 0


class ObservatoryStatusResponse(BaseModel):
    observatory_tables: dict[str, bool] = Field(default_factory=dict)
    missing_tables: list[str] = Field(default_factory=list)
    completion_percentage: float = 0.0
    status: str = "partial_observatory"
