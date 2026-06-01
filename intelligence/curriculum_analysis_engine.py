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


def build_curriculum_analysis(program_id: int, *, db_name: str | None = None) -> dict[str, Any]:
    program = _program_base(program_id, db_name=db_name)
    program_name = str(program.get("nombre_especializacion") or "").strip()
    context = microcurriculum_context_repository.fetch_program_context(
        program_id,
        specialization_name=program_name,
        db_name=db_name,
    ) or {}
    intelligence = build_program_intelligence_for_program(program_id, db_name=db_name).to_dict()
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
