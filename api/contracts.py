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
    skill_id: int | None = None
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
    microcurriculum_context: dict[str, Any] | None = None


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


class ExecutiveNarrativeResponse(BaseModel):
    program_id: int | None = None
    program_name: str = ""
    narrative: str = ""
    why_at_risk: str = ""
    evidence_sources: list[str] = Field(default_factory=list)
    source_tables: list[str] = Field(default_factory=list)
    supporting_evidence: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    model: str = ""
    generated_at: str = ""


class ProgramSummaryResponse(BaseModel):
    program_id: int
    program_name: str = ""
    summary: str = ""
    why_at_risk: str = ""
    microcurriculum_traceability: dict[str, Any] = Field(default_factory=dict)
    evidence_sources: list[str] = Field(default_factory=list)
    source_tables: list[str] = Field(default_factory=list)
    supporting_evidence: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    model: str = ""
    generated_at: str = ""


class RecommendationExplanationResponse(BaseModel):
    recommendation_id: int
    recommendation_title: str = ""
    explanation: str = ""
    why_this_recommendation: str = ""
    evidence_sources: list[str] = Field(default_factory=list)
    source_tables: list[str] = Field(default_factory=list)
    supporting_evidence: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    model: str = ""
    generated_at: str = ""


class AskObservatoryRequest(BaseModel):
    question: str
    program_id: int | None = None
    recommendation_id: int | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class AskObservatoryResponse(BaseModel):
    question: str
    answer: str = ""
    evidence_sources: list[str] = Field(default_factory=list)
    source_tables: list[str] = Field(default_factory=list)
    supporting_evidence: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    model: str = ""
    generated_at: str = ""


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


class RiskDriver(BaseModel):
    driver: str
    value: float = 0.0
    impact: float = 0.0
    evidence: list[str] = Field(default_factory=list)


class CurriculumRiskResponse(BaseModel):
    program_id: int
    program_name: str
    risk_score: float = 0.0
    risk_level: str = ""
    risk_drivers: list[RiskDriver] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    supporting_evidence: dict[str, Any] = Field(default_factory=dict)
    source_tables: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class UniversityMarketAlignmentResponse(BaseModel):
    program_id: int
    program_name: str
    alignment_score: float = 0.0
    alignment_level: str = ""
    current_alignment: float = 0.0
    projected_alignment_if_added: float = 0.0
    missing_skills: list[str] = Field(default_factory=list)
    emerging_skills: list[str] = Field(default_factory=list)
    company_demand_score: float = 0.0
    labor_demand_score: float = 0.0
    forecasted_demand_score: float = 0.0
    emerging_technology_score: float = 0.0
    explanation: str = ""
    supporting_evidence: dict[str, Any] = Field(default_factory=dict)
    source_tables: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class MarketForecastItem(BaseModel):
    entity_type: str
    entity_name: str
    horizon_months: int = 12
    growth_velocity: float = 0.0
    forecast_confidence: float = 0.0
    market_phase: str = ""
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class MarketForecastPageResponse(BaseModel):
    items: list[MarketForecastItem] = Field(default_factory=list)
    count: int = 0
    limit: int = 0
    offset: int = 0
    filters: dict[str, Any] = Field(default_factory=dict)


class EmergingSkillSignal(BaseModel):
    skill_name: str
    growth_rate: float = 0.0
    confidence_score: float = 0.0
    first_seen_date: str | None = None
    last_seen_date: str | None = None
    supporting_companies: list[str] = Field(default_factory=list)
    supporting_roles: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)


class CareerTransitionInsight(BaseModel):
    source_role: str
    target_role: str
    required_skills: list[str] = Field(default_factory=list)
    difficulty_score: float = 0.0
    estimated_salary_progression: float = 0.0
    transition_probability: float = 0.0
    source_family: str = ""
    target_family: str = ""
    supporting_evidence: dict[str, Any] = Field(default_factory=dict)


class CareerIntelligenceResponse(BaseModel):
    source_role: str = ""
    transitions: list[CareerTransitionInsight] = Field(default_factory=list)
    role_network: list[dict[str, Any]] = Field(default_factory=list)
    source_tables: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class RecommendationV2(BaseModel):
    recommendation_type: str
    target_entity: str
    target_company: str
    recommendation_score: float = 0.0
    priority: str = ""
    business_justification: str = ""
    expected_impact: str = ""
    confidence: float = 0.0
    estimated_alignment_increase: float = 0.0
    recommendation_evidence: dict[str, Any] = Field(default_factory=dict)
    recommendation_reasoning: str = ""


class RecommendationV2PageResponse(BaseModel):
    items: list[RecommendationV2] = Field(default_factory=list)
    count: int = 0
    limit: int = 0
    offset: int = 0
    filters: dict[str, Any] = Field(default_factory=dict)


class CriticalProgramItem(BaseModel):
    program_id: int
    program_name: str = ""
    program_role: str = ""
    alignment_score: float = 0.0
    risk_score: float = 0.0
    risk_level: str = ""
    gap_count: int = 0
    main_gap_driver: str = ""
    recommended_action: str = ""
    projected_employability_gain: float = 0.0
    horizon_months: int = 12
    supporting_evidence: dict[str, Any] = Field(default_factory=dict)
    source_tables: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    generated_at: str = ""


class CriticalProgramPageResponse(BaseModel):
    items: list[CriticalProgramItem] = Field(default_factory=list)
    count: int = 0
    limit: int = 0
    offset: int = 0
    filters: dict[str, Any] = Field(default_factory=dict)


class CurriculumSimulationResponse(BaseModel):
    program_id: int
    program_name: str = ""
    program_role: str = ""
    horizon_months: int = 12
    current_alignment_score: float = 0.0
    current_risk_score: float = 0.0
    projected_alignment_score: float = 0.0
    projected_risk_score: float = 0.0
    projected_employability_gain: float = 0.0
    projected_gap_reduction: float = 0.0
    confidence_score: float = 0.0
    proposed_skills: list[str] = Field(default_factory=list)
    normalized_skills: list[dict[str, Any]] = Field(default_factory=list)
    risk_drivers: list[dict[str, Any]] = Field(default_factory=list)
    supporting_evidence: dict[str, Any] = Field(default_factory=dict)
    source_tables: list[str] = Field(default_factory=list)
    explanation: str = ""
    simulation_key: str = ""
    generated_at: str = ""


class ForecastSummaryResponse(BaseModel):
    generated_at: str = ""
    source_tables: list[str] = Field(default_factory=list)
    total_records: int = 0
    counts: dict[str, int] = Field(default_factory=dict)
    coverage: dict[str, float] = Field(default_factory=dict)
    top_skills: list[MarketForecastItem] = Field(default_factory=list)
    top_technologies: list[MarketForecastItem] = Field(default_factory=list)
    top_companies: list[MarketForecastItem] = Field(default_factory=list)
    top_roles: list[MarketForecastItem] = Field(default_factory=list)


class ExecutiveMetric(BaseModel):
    metric_name: str
    metric_category: str
    metric_value: float = 0.0
    metric_period: str = ""
    confidence_score: float = 0.0
    source_tables: list[str] = Field(default_factory=list)
    supporting_evidence: dict[str, Any] = Field(default_factory=dict)


class ExecutiveObservatoryResponse(BaseModel):
    metrics: list[ExecutiveMetric] = Field(default_factory=list)
    alignment_average: float = 0.0
    high_risk_programs: list[dict[str, Any]] = Field(default_factory=list)
    medium_risk_programs: list[dict[str, Any]] = Field(default_factory=list)
    low_risk_programs: list[dict[str, Any]] = Field(default_factory=list)
    programs_analyzed: int = 0
    critical_gaps: list[dict[str, Any]] = Field(default_factory=list)
    top_emerging_skills: list[dict[str, Any]] = Field(default_factory=list)
    top_recommendations: list[dict[str, Any]] = Field(default_factory=list)
    top_programs: list[dict[str, Any]] = Field(default_factory=list)
    at_risk_programs: list[dict[str, Any]] = Field(default_factory=list)
    executive_narrative: str = ""
    source_tables: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class ProgramIntelligenceItem(BaseModel):
    program_id: int
    program_name: str = ""
    program_role: str = ""
    alignment_score: float = 0.0
    risk_score: float = 0.0
    risk_level: str = ""
    gap_count: int = 0
    top_gaps: list[dict[str, Any]] = Field(default_factory=list)
    top_recommendations: list[dict[str, Any]] = Field(default_factory=list)
    forecast_signals: list[dict[str, Any]] = Field(default_factory=list)
    role_signals: list[dict[str, Any]] = Field(default_factory=list)
    emerging_technologies: list[dict[str, Any]] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    business_justification: str = ""
    supporting_evidence: dict[str, Any] = Field(default_factory=dict)
    source_tables: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    generated_at: str = ""


class ProgramIntelligencePageResponse(BaseModel):
    items: list[ProgramIntelligenceItem] = Field(default_factory=list)
    count: int = 0
    total: int = 0
    limit: int = 0
    offset: int = 0
    filters: dict[str, Any] = Field(default_factory=dict)
    source_tables: list[str] = Field(default_factory=list)
    confidence: float = 0.0
