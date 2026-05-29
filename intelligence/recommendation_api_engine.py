from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from intelligence.common import clamp


@dataclass(frozen=True)
class RecommendationAPIItem:
    recommendation_type: str
    target_role: str
    target_company: str
    recommended_skills: list[str]
    market_alignment_score: float
    top_companies: list[str]
    recommendation_payload: dict[str, Any]
    recommendation_reasoning: str
    recommendation_confidence: float
    recommendation_evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _top_companies(company_profiles: list[Any], limit: int = 5) -> list[str]:
    companies = sorted(
        company_profiles,
        key=lambda item: (float(getattr(item, "hiring_velocity", 0) or 0), float(getattr(item, "cloud_maturity_score", 0) or 0), float(getattr(item, "bi_maturity_score", 0) or 0)),
        reverse=True,
    )
    return [item.company for item in companies[:limit]]


def _recommendation_payload(
    *,
    recommendation_type: str,
    target_role: str,
    target_company: str,
    recommended_skills: list[str],
    market_alignment_score: float,
    top_companies: list[str],
    reasoning: str,
    evidence: dict[str, Any],
) -> RecommendationAPIItem:
    confidence = clamp(0.55 + (market_alignment_score * 0.35) + min(len(recommended_skills) / 20.0, 0.1))
    return RecommendationAPIItem(
        recommendation_type=recommendation_type,
        target_role=target_role,
        target_company=target_company,
        recommended_skills=recommended_skills[:8],
        market_alignment_score=round(clamp(market_alignment_score), 4),
        top_companies=top_companies[:5],
        recommendation_payload={
            "recommendation_type": recommendation_type,
            "target_role": target_role,
            "target_company": target_company,
            "recommended_skills": recommended_skills[:8],
            "market_alignment_score": round(clamp(market_alignment_score), 4),
            "top_companies": top_companies[:5],
            "why_recommended": evidence.get("why_recommended", []),
            "why_missing": evidence.get("why_missing", []),
            "top_evidence": evidence.get("top_evidence", {}),
        },
        recommendation_reasoning=reasoning,
        recommendation_confidence=round(confidence, 4),
        recommendation_evidence=evidence,
    )


def build_recommendation_api_payload(
    *,
    market_intelligence: Any,
    gap_map: Any,
    company_profiles: list[Any],
    role_signals: list[Any],
    career_transitions: list[Any],
    metric_period: str,
    write_output: bool = True,
) -> list[RecommendationAPIItem]:
    top_companies = _top_companies(company_profiles)
    items: list[RecommendationAPIItem] = []

    priority_gaps = list(getattr(gap_map, "emerging_skills", []) or [])
    priority_gaps.extend(list(getattr(gap_map, "missing_skills", []) or []))
    priority_gaps.extend(list(getattr(gap_map, "partial_skills", []) or []))
    for gap in priority_gaps[:6]:
        skills = [gap.skill, gap.cluster_name]
        items.append(
            _recommendation_payload(
                recommendation_type="student",
                target_role="Visual Analytics y Big Data",
                target_company="market",
                recommended_skills=skills,
                market_alignment_score=gap.affinity_score,
                top_companies=top_companies,
                reasoning=f"Fortalecer {gap.skill} porque aparece como {gap.coverage_status} y demanda mercado {round(gap.evidence_weight, 4)}.",
                evidence={
                    "gap_skill": gap.skill,
                    "cluster_name": gap.cluster_name,
                    "coverage_status": gap.coverage_status,
                    "evidence_sources": gap.evidence_sources,
                    "roles": gap.roles[:5],
                    "why_recommended": [gap.recommendation],
                    "why_missing": [gap.reason] if gap.coverage_status != "covered" else [],
                    "top_evidence": gap.evidence_sources,
                    "metric_period": metric_period,
                },
            )
        )

    curriculum_updates = list(getattr(gap_map, "recommended_curriculum_updates", []) or [])
    for update in curriculum_updates[:6]:
        items.append(
            _recommendation_payload(
                recommendation_type="curriculum",
                target_role="Especializacion en Visual Analytics y Big Data",
                target_company="curriculum",
                recommended_skills=[str(update.get("skill") or "")],
                market_alignment_score=float(update.get("evidence_weight") or 0),
                top_companies=top_companies,
                reasoning=str(update.get("action") or ""),
                evidence={
                    "update": update,
                    "why_recommended": [str(update.get("action") or "")],
                    "why_missing": [str(update.get("skill") or "")],
                    "top_evidence": update,
                    "metric_period": metric_period,
                },
            )
        )

    sorted_transitions = sorted(career_transitions, key=lambda item: float(getattr(item, "role_progression_probability", 0) or 0), reverse=True)
    for item in sorted_transitions[:5]:
        items.append(
            _recommendation_payload(
                recommendation_type="career",
                target_role=str(getattr(item, "target_role", "") or ""),
                target_company="market",
                recommended_skills=list(getattr(item, "recommended_next_skills", []) or []),
                market_alignment_score=float(getattr(item, "role_progression_probability", 0) or 0),
                top_companies=top_companies,
                reasoning=f"Ruta profesional {item.source_role} -> {item.target_role} con brechas {', '.join(getattr(item, 'transition_skill_gaps', []) or [])}.",
                evidence={
                    "source_role": item.source_role,
                    "target_role": item.target_role,
                    "transition_skill_gaps": list(getattr(item, "transition_skill_gaps", []) or []),
                    "recommended_next_skills": list(getattr(item, "recommended_next_skills", []) or []),
                    "metric_period": metric_period,
                },
            )
        )

    top_profiles = sorted(
        company_profiles,
        key=lambda item: (float(getattr(item, "hiring_velocity", 0) or 0), float(getattr(item, "cloud_maturity_score", 0) or 0), float(getattr(item, "bi_maturity_score", 0) or 0)),
        reverse=True,
    )
    for profile in top_profiles[:5]:
        target_role = "Cloud Analytics Engineer" if float(getattr(profile, "cloud_maturity_score", 0) or 0) >= 0.35 else "BI & Visualization Specialist"
        recommended_skills = list(dict.fromkeys([*(getattr(profile, "dominant_skills", []) or [])[:4], "SQL", "Python"]))[:6]
        items.append(
            _recommendation_payload(
                recommendation_type="company_fit",
                target_role=target_role,
                target_company=profile.company,
                recommended_skills=recommended_skills,
                market_alignment_score=clamp((float(getattr(profile, "hiring_velocity", 0) or 0) + float(getattr(profile, "ai_adoption_score", 0) or 0) + float(getattr(profile, "cloud_maturity_score", 0) or 0)) / 3),
                top_companies=top_companies,
                reasoning=(
                    f"Perfil de empresa {profile.company} con cluster dominado por {', '.join((getattr(profile, 'dominant_clusters', []) or [])[:2]) or 'analytics'} "
                    f"y madurez {profile.technology_maturity}."
                ),
                evidence={
                    "dominant_skills": list(getattr(profile, "dominant_skills", []) or [])[:8],
                    "dominant_clusters": list(getattr(profile, "dominant_clusters", []) or [])[:5],
                    "technology_maturity": getattr(profile, "technology_maturity", "emerging"),
                    "ai_adoption_score": getattr(profile, "ai_adoption_score", 0),
                    "bi_maturity_score": getattr(profile, "bi_maturity_score", 0),
                    "cloud_maturity_score": getattr(profile, "cloud_maturity_score", 0),
                    "metric_period": metric_period,
                },
            )
        )

    items = sorted(items, key=lambda item: (item.recommendation_type, item.recommendation_confidence, item.market_alignment_score), reverse=True)
    if write_output:
        write_recommendation_api_report(items, metric_period)
    return items


def write_recommendation_api_report(
    items: list[RecommendationAPIItem],
    metric_period: str,
    path: Path | None = None,
) -> None:
    path = path or (Path(__file__).resolve().parents[1] / "outputs" / "analytics" / "recommendation_observatory_report.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Recommendation Observatory",
        "",
        f"- Periodo: {metric_period}",
        f"- Recomendaciones: {len(items)}",
        "",
    ]
    for item in items[:40]:
        lines.extend(
            [
                f"## {item.recommendation_type}: {item.target_role}",
                f"- Empresa: {item.target_company}",
                f"- Skills recomendadas: {', '.join(item.recommended_skills) or 'sin skills'}",
                f"- Market alignment score: {round(item.market_alignment_score, 4)}",
                f"- Confidence: {round(item.recommendation_confidence, 4)}",
                f"- Justificacion: {item.recommendation_reasoning}",
                f"- Evidencia: {json.dumps(item.recommendation_evidence, ensure_ascii=False)}",
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
