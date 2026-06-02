from __future__ import annotations

from typing import Any

from backend.repositories import microcurriculum_context_repository, programas_repository
from intelligence.domain_benchmark_layer import build_domain_benchmark
from intelligence.domain_taxonomy_layer import build_domain_taxonomy_from_program
from intelligence.forecast_expansion_engine import build_forecast_summary
from intelligence.predictive_intelligence_engine import build_curriculum_risk_index, build_university_market_alignment
from intelligence.program_intelligence_engine import build_program_intelligence_for_program


def _program_base(program_id: int, *, db_name: str | None = None) -> dict[str, Any]:
    row = programas_repository.fetch_program_base_row(program_id, db_name=db_name)
    if not row:
        raise KeyError(f"programa {program_id} not found")
    return dict(row)


def _has_curricular_evidence(context: dict[str, Any]) -> bool:
    evidence_fields = (
        "technical_skills",
        "transversal_skills",
        "methodologies",
        "tools",
        "platforms",
        "technologies",
        "keywords",
        "labor_roles",
        "occupational_profiles",
        "strengthening_areas",
        "real_market_gaps",
        "subjects",
    )
    for field in evidence_fields:
        value = context.get(field)
        if isinstance(value, (list, tuple, set)) and any(str(item).strip() for item in value):
            return True
        if isinstance(value, dict) and value:
            return True
    return False


def build_curriculum_analysis(program_id: int, *, db_name: str | None = None) -> dict[str, Any]:
    program = _program_base(program_id, db_name=db_name)
    program_name = str(program.get("nombre_especializacion") or "").strip()
    context = microcurriculum_context_repository.fetch_program_context(
        program_id,
        specialization_name=program_name,
        db_name=db_name,
    ) or {}
    intelligence = build_program_intelligence_for_program(program_id, db_name=db_name).to_dict()
    if not _has_curricular_evidence(context):
        empty_risk = {
            "program_id": program_id,
            "program_name": program_name,
            "risk_score": 0.0,
            "risk_level": "low",
            "risk_drivers": [],
            "recommended_actions": [],
            "supporting_evidence": {"reason": "no_curricular_evidence", "microcurriculum_context": context},
            "source_tables": ["especializaciones"],
            "confidence": 0.0,
        }
        empty_alignment = {
            "program_id": program_id,
            "program_name": program_name,
            "alignment_score": 0.0,
            "alignment_level": "low",
            "current_alignment": 0.0,
            "projected_alignment_if_added": 0.0,
            "missing_skills": [],
            "emerging_skills": [],
            "company_demand_score": 0.0,
            "labor_demand_score": 0.0,
            "forecasted_demand_score": 0.0,
            "emerging_technology_score": 0.0,
            "explanation": "No curricular evidence available. Upload or process a microcurriculum to generate academic intelligence.",
            "supporting_evidence": {"reason": "no_curricular_evidence", "microcurriculum_context": context},
            "source_tables": ["especializaciones"],
            "confidence": 0.0,
        }
        return {
            "program": program,
            "microcurriculum_context": context,
            "program_intelligence": intelligence,
            "domain_taxonomy": {},
            "domain_benchmark": {},
            "curriculum_risk": empty_risk,
            "alignment": empty_alignment,
            "forecast_summary": {"items": [], "count": 0, "total": 0, "limit": 0, "offset": 0, "filters": {"reason": "no_curricular_evidence"}},
        }
    taxonomy = build_domain_taxonomy_from_program(
        program_name=program_name,
        program_role=str(program.get("rol") or ""),
        microcurriculum_context=context,
        skills=list(context.get("technical_skills") or []) + list(context.get("transversal_skills") or []),
    )
    benchmark = build_domain_benchmark(taxonomy.domain_key)
    risk = build_curriculum_risk_index(program_id, persist=False, db_name=db_name).to_dict()
    alignment = build_university_market_alignment(program_id, persist=False, db_name=db_name).to_dict()
    forecast_summary = build_forecast_summary(db_name=db_name, persist=False, limit=20)
    return {
        "program": program,
        "microcurriculum_context": context,
        "program_intelligence": intelligence,
        "domain_taxonomy": taxonomy.to_dict(),
        "domain_benchmark": benchmark.to_dict(),
        "curriculum_risk": risk,
        "alignment": alignment,
        "forecast_summary": forecast_summary,
    }
