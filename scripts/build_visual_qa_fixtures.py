from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.services import (
    get_curriculum_risk_index,
    get_executive_observatory,
    get_program_intelligence,
    get_programa_compatibility,
    get_university_market_alignment,
    list_company_intelligence,
    list_emerging_skills,
    list_market_forecast,
    list_program_intelligence,
    list_programas_compatibility,
    list_recommendations_v2,
)


def _extract_skills(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        skills: list[str] = []
        for item in value:
            skills.extend(_extract_skills(item))
        return skills
    if isinstance(value, dict):
        candidates = [
            value.get("skill"),
            value.get("missing_skill"),
            value.get("canonical_skill"),
            value.get("canonical_skill_name"),
            value.get("title"),
            value.get("name"),
        ]
        nested = value.get("recommended_skills")
        if isinstance(nested, list):
            candidates.extend(nested)
        skills: list[str] = []
        for candidate in candidates:
            skills.extend(_extract_skills(candidate))
        return skills
    return []


def _first_text(value: object, fallback: str = "Sin información suficiente") -> str:
    items = _extract_skills(value)
    return items[0] if items else fallback


def _build_executive_narrative(program_count: int, critical_count: int, alignment: float) -> dict[str, object]:
    if alignment >= 70:
        state = "alta"
        tone = "solidez"
    elif alignment >= 50:
        state = "moderada"
        tone = "presión de intervención"
    else:
        state = "baja"
        tone = "riesgo crítico"
    narrative = (
        f"La institución presenta una alineación {state} con el mercado laboral. "
        f"Se identifican {critical_count} programas que requieren atención prioritaria de un total de {program_count} analizados. "
        f"El portafolio muestra {tone} en la actualización curricular y evidencia suficiente para decisiones académicas."
    )
    return {
        "program_id": None,
        "program_name": "Observatorio institucional",
        "narrative": narrative,
        "why_at_risk": f"{critical_count} programas concentran riesgo curricular relevante.",
        "evidence_sources": ["program_intelligence", "executive_observatory", "recommendation_observatory", "market_forecasts"],
        "source_tables": ["program_intelligence", "executive_observatory", "recommendation_observatory", "market_forecasts"],
        "supporting_evidence": {
            "programs_analyzed": program_count,
            "critical_programs": critical_count,
            "alignment_average": alignment,
        },
        "confidence": 0.86,
        "model": "deterministic-summary",
        "generated_at": "2026-05-31T00:00:00-05:00",
    }


def _build_program_summary(program: dict[str, object], intelligence: dict[str, object]) -> dict[str, object]:
    alignment = float(intelligence.get("alignment_score") or 0)
    risk = float(intelligence.get("risk_score") or max(0.0, 100.0 - alignment))
    gaps = _extract_skills(intelligence.get("top_gaps"))
    recommendations = _extract_skills(intelligence.get("top_recommendations"))
    top_gap = gaps[0] if gaps else "Sin brecha priorizada"
    top_rec = recommendations[0] if recommendations else "Sin recomendación priorizada"
    program_name = str(program.get("nombre_especializacion") or intelligence.get("program_name") or "Programa")
    return {
        "program_id": int(program.get("especializacion_id") or intelligence.get("program_id") or 0),
        "program_name": program_name,
        "summary": (
            f"{program_name} registra una alineación de {alignment:.1f}% y un riesgo curricular de {risk:.1f}%. "
            f"La principal brecha observada es {top_gap}. La acción prioritaria sugerida es {top_rec}."
        ),
        "why_at_risk": f"El programa concentra {len(gaps)} brechas priorizadas y señales de mercado asociadas.",
        "microcurriculum_traceability": {
            "program": program_name,
            "top_gap": top_gap,
            "top_recommendation": top_rec,
            "skills_covered": program.get("total_skills_programa", 0),
        },
        "evidence_sources": ["program_intelligence", "curriculum_gap_observatory", "recommendation_observatory", "market_forecasts"],
        "source_tables": ["program_intelligence", "curriculum_gap_observatory", "recommendation_observatory", "market_forecasts"],
        "supporting_evidence": {
            "alignment_score": alignment,
            "risk_score": risk,
            "gap_count": intelligence.get("gap_count", len(gaps)),
        },
        "confidence": float(intelligence.get("confidence") or 0.84),
        "model": "deterministic-summary",
        "generated_at": "2026-05-31T00:00:00-05:00",
    }


def main() -> int:
    root = ROOT
    output_dir = root / "outputs" / "qa" / "visual"
    output_dir.mkdir(parents=True, exist_ok=True)

    programs_page = list_programas_compatibility(limit=100, offset=0)
    programs = programs_page.get("items", [])
    first_program = programs[0]
    program_id = int(first_program["especializacion_id"])

    program_intelligence_page = list_program_intelligence(limit=100, offset=0)
    program_intelligence_items = program_intelligence_page.get("items", [])
    selected_program_intelligence = get_program_intelligence(program_id)
    curriculum_risk = get_curriculum_risk_index(program_id)
    alignment = get_university_market_alignment(program_id)
    executive_observatory = get_executive_observatory()
    recommendations = list_recommendations_v2(limit=12, offset=0)
    emerging_skills = list_emerging_skills(limit=12, offset=0)
    companies = list_company_intelligence(limit=12, offset=0)
    forecasts = list_market_forecast(limit=12, offset=0)

    suggested_skills = []
    suggested_skills.extend(_extract_skills(first_program.get("skills", [])))
    suggested_skills.extend(_extract_skills(selected_program_intelligence.get("top_gaps", [])))
    suggested_skills.extend(_extract_skills(selected_program_intelligence.get("top_recommendations", [])))
    suggested_skills.extend(alignment.get("missing_skills", []))
    suggested_skills = list(dict.fromkeys([skill.strip() for skill in suggested_skills if isinstance(skill, str) and skill.strip()]))[:6]
    if not suggested_skills:
        suggested_skills = ["Azure", "Databricks", "Power BI"]

    simulations = {}
    for horizon in (6, 12, 24):
        base_alignment = float(alignment.get("current_alignment") or alignment.get("alignment_score") or first_program.get("promedio_match_mercado") or 0)
        projected_alignment = min(100.0, base_alignment + (4.0 if horizon == 6 else 11.0 if horizon == 12 else 19.0))
        projected_risk = max(0.0, float(curriculum_risk.get("risk_score") or 100.0 - base_alignment) - (5.0 if horizon == 6 else 12.0 if horizon == 12 else 20.0))
        simulations[str(horizon)] = {
            "program_id": program_id,
            "program_name": first_program.get("nombre_especializacion") or selected_program_intelligence.get("program_name"),
            "program_role": first_program.get("rol") or selected_program_intelligence.get("program_role"),
            "horizon_months": horizon,
            "current_alignment_score": base_alignment,
            "current_risk_score": float(curriculum_risk.get("risk_score") or max(0.0, 100.0 - base_alignment)),
            "projected_alignment_score": projected_alignment,
            "projected_risk_score": projected_risk,
            "projected_employability_gain": max(0.0, projected_alignment - base_alignment),
            "projected_gap_reduction": max(0.0, projected_alignment - base_alignment) * 1.2,
            "confidence_score": 0.79 if horizon == 6 else 0.84 if horizon == 12 else 0.88,
            "proposed_skills": suggested_skills,
            "normalized_skills": [{"skill": skill, "canonical_skill": skill, "confidence": 0.9} for skill in suggested_skills],
            "risk_drivers": curriculum_risk.get("risk_drivers", []),
            "supporting_evidence": {
                "horizon_months": horizon,
                "selected_skills": suggested_skills,
                "alignment_basis": base_alignment,
            },
            "source_tables": ["program_intelligence", "curriculum_gap_observatory", "recommendation_observatory", "market_forecasts"],
            "generated_at": "2026-05-31T00:00:00-05:00",
        }

    critical_programs = {
        "items": [
            {
                "program_id": item["program_id"],
                "program_name": item["program_name"],
                "program_role": item["program_role"],
                "alignment_score": item["alignment_score"],
                "risk_score": item["risk_score"],
                "risk_level": item["risk_level"],
                "gap_count": item["gap_count"],
                "main_gap_driver": _first_text(item.get("top_gaps"), "Sin brecha principal"),
                "recommended_action": _first_text(item.get("top_recommendations"), "Sin recomendación priorizada"),
                "source_tables": item.get("source_tables", []),
                "confidence": item.get("confidence", 0.85),
                "generated_at": item.get("generated_at"),
            }
            for item in sorted(program_intelligence_items, key=lambda row: float(row.get("risk_score") or 0), reverse=True)
            if float(item.get("risk_score") or 0) >= 70
        ][:20],
        "total": len([item for item in program_intelligence_items if float(item.get("risk_score") or 0) >= 70]),
        "limit": 20,
        "offset": 0,
        "filters": {"horizon_months": 12},
        "source_tables": ["program_intelligence", "curriculum_gap_observatory", "recommendation_observatory", "market_forecasts"],
        "confidence": 0.88,
    }

    forecast_summary = {
        "items": forecasts.get("items", [])[:25],
        "total": forecasts.get("total", len(forecasts.get("items", []))),
        "limit": 25,
        "offset": 0,
        "source_tables": ["market_forecasts"],
        "filters": {},
        "confidence": 0.84,
    }

    recommendation_items = recommendations.get("items", [])
    first_recommendation_id = int(recommendation_items[0]["recommendation_id"]) if recommendation_items else 0

    fixtures = {
        "programId": program_id,
        "routes": {
            "GET /api/programas?limit=100": programs_page,
            "GET /api/program-intelligence?limit=100": program_intelligence_page,
            f"GET /api/program-intelligence/{program_id}": selected_program_intelligence,
            f"GET /program-intelligence/{program_id}": selected_program_intelligence,
            f"GET /api/programas/{program_id}": get_programa_compatibility(program_id),
            f"GET /api/programas/{program_id}/curriculum-risk": curriculum_risk,
            f"GET /programas/{program_id}/curriculum-risk": curriculum_risk,
            f"GET /api/programas/{program_id}/alignment": alignment,
            f"GET /programas/{program_id}/alignment": alignment,
            f"GET /program-summary/{program_id}": _build_program_summary(first_program, selected_program_intelligence),
            f"GET /executive-narrative?program_id={program_id}": _build_program_summary(first_program, selected_program_intelligence),
            "GET /executive-narrative": _build_executive_narrative(len(programs), len([item for item in program_intelligence_items if float(item.get("risk_score") or 0) >= 70]), float(executive_observatory.get("alignment_average") or 0)),
            "GET /executive-observatory": executive_observatory,
            "GET /recommendations-v2?limit=12&offset=0": recommendations,
            "GET /emerging-skills?limit=12&offset=0": emerging_skills,
            "GET /company-intelligence?limit=12&offset=0": companies,
            "GET /market-forecast?limit=12&offset=0": forecasts,
            "GET /critical-programs?limit=20&offset=0&horizon_months=12": critical_programs,
            "GET /forecast-summary?limit=25": forecast_summary,
        },
        "simulations": simulations,
        "suggestedSkills": suggested_skills,
    }

    (output_dir / "visual-qa-fixtures.json").write_text(json.dumps(fixtures, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
