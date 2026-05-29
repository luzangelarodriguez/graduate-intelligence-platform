from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CompanyObservatoryItem:
    company: str
    dominant_stack: str
    dominant_cluster: str
    hiring_velocity: float
    ai_adoption_score: float
    cloud_maturity_score: float
    bi_maturity_score: float
    technology_maturity: str
    top_skills: list[str]
    top_clusters: list[str]
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_company_observatory(
    *,
    company_profiles: list[Any],
    metric_period: str,
    write_output: bool = True,
) -> list[CompanyObservatoryItem]:
    items: list[CompanyObservatoryItem] = []
    for profile in sorted(
        company_profiles,
        key=lambda item: (float(getattr(item, "hiring_velocity", 0) or 0), float(getattr(item, "cloud_maturity_score", 0) or 0), float(getattr(item, "bi_maturity_score", 0) or 0)),
        reverse=True,
    ):
        dominant_skills = list(getattr(profile, "dominant_skills", []) or [])
        dominant_clusters = list(getattr(profile, "dominant_clusters", []) or [])
        items.append(
            CompanyObservatoryItem(
                company=profile.company,
                dominant_stack=", ".join(dominant_skills[:5]),
                dominant_cluster=dominant_clusters[0] if dominant_clusters else "Enterprise Analytics",
                hiring_velocity=round(float(getattr(profile, "hiring_velocity", 0) or 0), 4),
                ai_adoption_score=round(float(getattr(profile, "ai_adoption_score", 0) or 0), 4),
                cloud_maturity_score=round(float(getattr(profile, "cloud_maturity_score", 0) or 0), 4),
                bi_maturity_score=round(float(getattr(profile, "bi_maturity_score", 0) or 0), 4),
                technology_maturity=str(getattr(profile, "technology_maturity", "emerging") or "emerging"),
                top_skills=dominant_skills[:8],
                top_clusters=dominant_clusters[:5],
                evidence={
                    "metric_period": metric_period,
                    "dominant_skills": dominant_skills[:8],
                    "dominant_clusters": dominant_clusters[:5],
                },
            )
        )
    if write_output:
        write_company_observatory_report(items, metric_period)
    return items


def write_company_observatory_report(
    items: list[CompanyObservatoryItem],
    metric_period: str,
    path: Path | None = None,
) -> None:
    path = path or (Path(__file__).resolve().parents[1] / "outputs" / "analytics" / "company_observatory_report.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Company Observatory",
        "",
        f"- Periodo: {metric_period}",
        f"- Empresas analizadas: {len(items)}",
        "",
    ]
    for item in items[:40]:
        lines.extend(
            [
                f"## {item.company}",
                f"- Dominant stack: {item.dominant_stack}",
                f"- Dominant cluster: {item.dominant_cluster}",
                f"- Hiring velocity: {round(item.hiring_velocity, 4)}",
                f"- AI adoption score: {round(item.ai_adoption_score, 4)}",
                f"- Cloud maturity score: {round(item.cloud_maturity_score, 4)}",
                f"- BI maturity score: {round(item.bi_maturity_score, 4)}",
                f"- Technology maturity: {item.technology_maturity}",
                f"- Top skills: {', '.join(item.top_skills) or 'sin skills'}",
                f"- Evidence: {json.dumps(item.evidence, ensure_ascii=False)}",
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
