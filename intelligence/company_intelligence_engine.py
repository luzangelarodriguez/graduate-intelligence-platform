from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from typing import Any

from intelligence.common import clamp
from intelligence.company_resolution_engine import resolve_company
from intelligence.semantic_role_intelligence import infer_role_family


AI_SKILLS = {"AI", "machine learning", "MLflow", "MLOps", "LLM", "RAG", "Copilot BI", "pandas", "scikit-learn"}
BI_SKILLS = {"BI", "Power BI", "Tableau", "dashboarding", "KPIs", "reporting", "executive reporting"}
CLOUD_SKILLS = {"AWS", "Azure", "GCP", "Databricks", "Snowflake", "BigQuery", "Microsoft Fabric", "Synapse"}


@dataclass(frozen=True)
class CompanyProfile:
    company: str
    dominant_skills: list[str]
    dominant_clusters: list[str]
    hiring_velocity: float
    technology_maturity: str
    ai_adoption_score: float
    bi_maturity_score: float
    cloud_maturity_score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _maturity(total_jobs: int, skills_count: int, cloud_score: float, ai_score: float) -> str:
    if total_jobs >= 15 and skills_count >= 12 and (cloud_score >= 0.35 or ai_score >= 0.25):
        return "advanced"
    if total_jobs >= 5 or skills_count >= 6:
        return "growing"
    return "emerging"


def build_company_profiles(jobs: list[dict[str, Any]]) -> list[CompanyProfile]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for job in jobs:
        resolution = resolve_company(job.get("company"), context_text=" ".join([str(job.get("title") or ""), str(job.get("description") or "")]))
        grouped[resolution.canonical_company_name].append(job)
    profiles: list[CompanyProfile] = []
    for company, rows in grouped.items():
        if company == "No especificada":
            continue
        skill_counts = Counter(skill for row in rows for skill in (row.get("skills") or []))
        clusters = Counter(infer_role_family(str(row.get("title") or ""), row.get("skills") or [])[0] for row in rows)
        total_skill_mentions = max(sum(skill_counts.values()), 1)
        ai_score = sum(skill_counts.get(skill, 0) for skill in AI_SKILLS) / total_skill_mentions
        bi_score = sum(skill_counts.get(skill, 0) for skill in BI_SKILLS) / total_skill_mentions
        cloud_score = sum(skill_counts.get(skill, 0) for skill in CLOUD_SKILLS) / total_skill_mentions
        profiles.append(
            CompanyProfile(
                company=company,
                dominant_skills=[skill for skill, _ in skill_counts.most_common(10)],
                dominant_clusters=[cluster for cluster, _ in clusters.most_common(5)],
                hiring_velocity=round(clamp(len(rows) / 20), 4),
                technology_maturity=_maturity(len(rows), len(skill_counts), cloud_score, ai_score),
                ai_adoption_score=round(clamp(ai_score * 2.5), 4),
                bi_maturity_score=round(clamp(bi_score * 2.0), 4),
                cloud_maturity_score=round(clamp(cloud_score * 2.0), 4),
            )
        )
    return sorted(profiles, key=lambda item: (item.hiring_velocity, item.cloud_maturity_score, item.bi_maturity_score), reverse=True)
