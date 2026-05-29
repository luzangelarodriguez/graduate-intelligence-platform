from __future__ import annotations

from typing import Any

from microcurriculum_engine.matching.market_matching import MarketComparison


def score_microcurriculum(
    *,
    comparison: MarketComparison,
    skills_count: int,
    competencies_count: int,
    recommendations_count: int,
) -> dict[str, Any]:
    coverage = comparison.coverage
    modernization = min(1.0, (skills_count + len(comparison.shared_skills)) / max(1, len(comparison.market_skills) + 3))
    obsolescence_risk = min(1.0, len(comparison.obsolete_skills) / max(1, skills_count))
    labor_alignment = round((coverage * 0.65) + (modernization * 0.25) + ((1 - obsolescence_risk) * 0.10), 4)
    curricular_relevance = round((labor_alignment * 0.75) + (min(1.0, competencies_count / 4) * 0.25), 4)
    return {
        "pertinencia_curricular": curricular_relevance,
        "cobertura_skills_mercado": coverage,
        "modernizacion_tecnologica": round(modernization, 4),
        "alineacion_laboral": labor_alignment,
        "riesgo_obsolescencia": round(obsolescence_risk, 4),
        "recommendations_count": recommendations_count,
    }
