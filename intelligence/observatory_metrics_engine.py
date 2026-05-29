from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any

from intelligence.common import clamp


@dataclass(frozen=True)
class ObservatoryMetric:
    metric_name: str
    metric_category: str
    metric_value: float
    metric_period: str
    confidence_score: float
    generated_at: str
    source_payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _smooth(metric_name: str, current_value: float, previous_values: dict[str, float] | None) -> float:
    if not previous_values or metric_name not in previous_values:
        return round(current_value, 4)
    previous = float(previous_values[metric_name])
    return round((current_value * 0.7) + (previous * 0.3), 4)


def build_observatory_metrics(
    *,
    market_intelligence: Any,
    company_profiles: list[Any],
    role_signals: list[Any],
    gap_map: Any,
    forecasts: list[Any],
    metric_period: str,
    previous_values: dict[str, float] | None = None,
) -> list[ObservatoryMetric]:
    metrics: list[ObservatoryMetric] = []
    generated_at = datetime.now(UTC).isoformat()

    emerging_skills = list(getattr(market_intelligence, "emerging_skills", []) or [])[:5]
    for index, item in enumerate(emerging_skills, start=1):
        market_weight = float(getattr(item, "market_weight", getattr(item, "evidence_weight", 0)) or 0)
        evidence_count = float(getattr(item, "evidence_count", 1) or 1)
        metrics.append(
            ObservatoryMetric(
                metric_name=f"top_emerging_skill_{index}",
                metric_category="skills",
                metric_value=_smooth(f"top_emerging_skill_{index}", market_weight, previous_values),
                metric_period=metric_period,
                confidence_score=clamp(0.78 + min(evidence_count / 20.0, 0.18)),
                generated_at=generated_at,
                source_payload={
                    "skill": getattr(item, "skill", ""),
                    "cluster": getattr(item, "occupational_cluster", getattr(item, "cluster_name", "")),
                    "coverage_status": getattr(item, "coverage_status", ""),
                    "market_signal_confidence": getattr(item, "market_signal_confidence", "medium"),
                    "evidence_sources": getattr(item, "evidence_sources", {}),
                },
            )
        )

    clusters = sorted(
        list(getattr(market_intelligence, "occupational_clusters", []) or []),
        key=lambda item: (float(item.get("total_weight", 0) or 0), int(item.get("evidence_count", 0) or 0)),
        reverse=True,
    )[:5]
    for index, item in enumerate(clusters, start=1):
        value = float(item.get("total_weight", 0) or 0)
        metrics.append(
            ObservatoryMetric(
                metric_name=f"fastest_growing_cluster_{index}",
                metric_category="clusters",
                metric_value=_smooth(f"fastest_growing_cluster_{index}", value, previous_values),
                metric_period=metric_period,
                confidence_score=clamp(0.7 + min(float(item.get("evidence_count", 0) or 0) / 40.0, 0.2)),
                generated_at=generated_at,
                source_payload=item,
            )
        )

    top_companies = sorted(
        company_profiles,
        key=lambda item: (float(getattr(item, "hiring_velocity", 0) or 0), float(getattr(item, "cloud_maturity_score", 0) or 0), float(getattr(item, "bi_maturity_score", 0) or 0)),
        reverse=True,
    )[:5]
    for index, item in enumerate(top_companies, start=1):
        metrics.append(
            ObservatoryMetric(
                metric_name=f"top_hiring_company_{index}",
                metric_category="companies",
                metric_value=_smooth(f"top_hiring_company_{index}", float(getattr(item, "hiring_velocity", 0) or 0), previous_values),
                metric_period=metric_period,
                confidence_score=clamp(0.72 + min(len(getattr(item, "dominant_skills", []) or []) / 20.0, 0.18)),
                generated_at=generated_at,
                source_payload={
                    "company": item.company,
                    "dominant_skills": item.dominant_skills,
                    "dominant_clusters": item.dominant_clusters,
                    "technology_maturity": item.technology_maturity,
                    "ai_adoption_score": item.ai_adoption_score,
                    "bi_maturity_score": item.bi_maturity_score,
                    "cloud_maturity_score": item.cloud_maturity_score,
                },
            )
        )

    top_roles = sorted(role_signals, key=lambda item: (float(getattr(item, "centrality_score", 0) or 0), float(getattr(item, "role_similarity_score", 0) or 0)), reverse=True)[:5]
    for index, item in enumerate(top_roles, start=1):
        metrics.append(
            ObservatoryMetric(
                metric_name=f"semantic_role_growth_{index}",
                metric_category="roles",
            metric_value=_smooth(f"semantic_role_growth_{index}", float(getattr(item, "centrality_score", 0) or 0), previous_values),
            metric_period=metric_period,
            confidence_score=clamp(0.75 + min(float(getattr(item, "role_similarity_score", 0) or 0) / 2.0, 0.2)),
            generated_at=generated_at,
            source_payload={
                    "role_title": item.role_title,
                    "role_family": item.role_family,
                    "cluster": item.semantic_role_cluster,
                    "equivalent_roles": item.equivalent_roles,
                },
            )
        )

    covered = len(getattr(gap_map, "covered_skills", []) or [])
    partial = len(getattr(gap_map, "partial_skills", []) or [])
    missing = len(getattr(gap_map, "missing_skills", []) or [])
    emerging = len(getattr(gap_map, "emerging_skills", []) or [])
    metrics.append(
        ObservatoryMetric(
            metric_name="curriculum_gap_severity",
            metric_category="curriculum",
            metric_value=_smooth("curriculum_gap_severity", float((missing * 1.0) + (emerging * 0.8) + (partial * 0.4)), previous_values),
            metric_period=metric_period,
            confidence_score=0.9,
            generated_at=generated_at,
            source_payload={
                "covered": covered,
                "partial": partial,
                "missing": missing,
                "emerging": emerging,
            },
        )
    )

    coverage_ratio = (covered + partial) / max((covered + partial + missing + emerging), 1)
    metrics.append(
        ObservatoryMetric(
            metric_name="recommendation_coverage",
            metric_category="recommendations",
            metric_value=_smooth("recommendation_coverage", float(coverage_ratio), previous_values),
            metric_period=metric_period,
            confidence_score=0.88,
            generated_at=generated_at,
            source_payload={
                "covered": covered,
                "partial": partial,
                "missing": missing,
                "emerging": emerging,
            },
        )
    )

    if company_profiles:
        ai_adoption = mean(float(getattr(item, "ai_adoption_score", 0) or 0) for item in company_profiles)
        bi_maturity = mean(float(getattr(item, "bi_maturity_score", 0) or 0) for item in company_profiles)
        cloud_maturity = mean(float(getattr(item, "cloud_maturity_score", 0) or 0) for item in company_profiles)
    else:
        ai_adoption = bi_maturity = cloud_maturity = 0.0

    metrics.append(
        ObservatoryMetric(
            metric_name="ai_adoption_trend",
            metric_category="company",
            metric_value=_smooth("ai_adoption_trend", float(ai_adoption), previous_values),
            metric_period=metric_period,
            confidence_score=0.84,
            generated_at=generated_at,
            source_payload={"average_ai_adoption_score": round(ai_adoption, 4)},
        )
    )
    metrics.append(
        ObservatoryMetric(
            metric_name="bi_maturity_trend",
            metric_category="company",
            metric_value=_smooth("bi_maturity_trend", float(bi_maturity), previous_values),
            metric_period=metric_period,
            confidence_score=0.84,
            generated_at=generated_at,
            source_payload={"average_bi_maturity_score": round(bi_maturity, 4)},
        )
    )
    metrics.append(
        ObservatoryMetric(
            metric_name="cloud_adoption_trend",
            metric_category="company",
            metric_value=_smooth("cloud_adoption_trend", float(cloud_maturity), previous_values),
            metric_period=metric_period,
            confidence_score=0.84,
            generated_at=generated_at,
            source_payload={"average_cloud_maturity_score": round(cloud_maturity, 4)},
        )
    )

    if forecasts:
        market_velocity = mean(float(getattr(item, "growth_velocity", 0) or 0) for item in forecasts)
    else:
        market_velocity = 0.0
    metrics.append(
        ObservatoryMetric(
            metric_name="labor_market_velocity",
            metric_category="market",
            metric_value=_smooth("labor_market_velocity", float(market_velocity), previous_values),
            metric_period=metric_period,
            confidence_score=0.8,
            generated_at=generated_at,
            source_payload={"forecast_count": len(forecasts)},
        )
    )
    return metrics


def write_observatory_metrics_report(metrics: list[ObservatoryMetric], path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Labor Observatory Metrics",
        "",
        f"- Metrics generados: {len(metrics)}",
        "",
    ]
    grouped: dict[str, list[ObservatoryMetric]] = {}
    for metric in metrics:
        grouped.setdefault(metric.metric_category, []).append(metric)
    for category, rows in grouped.items():
        lines.extend([f"## {category}", ""])
        for row in rows:
            lines.append(
                f"- {row.metric_name}: {round(float(row.metric_value), 4)} "
                f"(confidence={row.confidence_score}) -> {row.source_payload}"
            )
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
