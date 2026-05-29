from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from intelligence.common import clamp
from intelligence.company_intelligence_engine import CompanyProfile


@dataclass(frozen=True)
class IntelligenceRecommendation:
    recommendation_type: str
    target_entity: str
    target_company: str
    recommendation_score: float
    recommendation_reasoning: str
    recommendation_evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_recommendations(
    *,
    company_profiles: list[CompanyProfile],
    missing_skills: list[str],
    emerging_skills: list[str],
) -> list[IntelligenceRecommendation]:
    recommendations: list[IntelligenceRecommendation] = []
    priority_skills = list(dict.fromkeys([*emerging_skills, *missing_skills]))[:10]
    for profile in company_profiles[:12]:
        target_skills = [skill for skill in priority_skills if skill not in profile.dominant_skills][:5]
        if profile.cloud_maturity_score >= 0.35:
            career_path = "Cloud Analytics Engineer"
        elif profile.bi_maturity_score >= 0.35:
            career_path = "BI & Visualization Specialist"
        else:
            career_path = "Analytics Engineer"
        recommendations.append(
            IntelligenceRecommendation(
                recommendation_type="company_fit_recommendation",
                target_entity=career_path,
                target_company=profile.company,
                recommendation_score=round(clamp((profile.hiring_velocity + profile.cloud_maturity_score + profile.bi_maturity_score + profile.ai_adoption_score) / 3), 4),
                recommendation_reasoning=(
                    f"Priorizar ruta {career_path} para {profile.company}; la empresa muestra señales en "
                    f"{', '.join(profile.dominant_clusters[:2]) or 'analytics'} y demanda habilidades complementarias."
                ),
                recommendation_evidence={
                    "recommended_skills": target_skills or profile.dominant_skills[:5],
                    "dominant_skills": profile.dominant_skills[:8],
                    "dominant_clusters": profile.dominant_clusters,
                    "technology_maturity": profile.technology_maturity,
                },
            )
        )
    if priority_skills:
        recommendations.append(
            IntelligenceRecommendation(
                recommendation_type="curriculum_recommendation",
                target_entity="Especializacion en Visual Analytics y Big Data",
                target_company="market",
                recommendation_score=0.82,
                recommendation_reasoning="Actualizar contenidos curriculares con skills emergentes y faltantes observadas en el mercado laboral.",
                recommendation_evidence={"recommended_skills": priority_skills, "source": "market_gap_signals"},
            )
        )
    return sorted(recommendations, key=lambda item: item.recommendation_score, reverse=True)
