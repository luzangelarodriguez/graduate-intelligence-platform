from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from intelligence.common import clamp, normalize_key


TECHNOLOGY_ALIASES: dict[str, tuple[str, ...]] = {
    "GenAI": ("genai", "gen ai", "generative ai", "agentic ai"),
    "Fabric": ("fabric", "microsoft fabric"),
    "dbt": ("dbt",),
    "LLMOps": ("llmops", "llm ops"),
    "RAG": ("rag",),
    "Vector DB": ("vector db", "vector database"),
    "AI Analytics": ("ai analytics",),
    "Databricks": ("databricks",),
    "Synapse": ("synapse", "azure synapse"),
}


@dataclass(frozen=True)
class EmergingTechnologyItem:
    technology: str
    emergence_score: float
    growth_velocity: float
    adoption_trend: str
    forecast_confidence: float
    source_payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _matches(technology: str, forecast_name: str) -> bool:
    key = normalize_key(forecast_name)
    alias_terms = TECHNOLOGY_ALIASES.get(technology, (technology.lower(),))
    return any(normalize_key(term) in key or key in normalize_key(term) for term in alias_terms)


def build_emerging_technology_observatory(
    *,
    forecasts: list[Any],
    market_intelligence: Any,
    metric_period: str,
    write_output: bool = True,
) -> list[EmergingTechnologyItem]:
    skills = list(getattr(market_intelligence, "market_skills", []) or [])
    items: list[EmergingTechnologyItem] = []
    for technology, aliases in TECHNOLOGY_ALIASES.items():
        matching_forecasts = [forecast for forecast in forecasts if _matches(technology, str(getattr(forecast, "entity_name", "")))]
        matching_skills = [skill for skill in skills if _matches(technology, str(getattr(skill, "skill", "")))]
        if not matching_forecasts and not matching_skills:
            continue
        growth_velocity = max([float(getattr(forecast, "growth_velocity", 0) or 0) for forecast in matching_forecasts] + [float(getattr(skill, "market_weight", 0) or 0) / 10.0 for skill in matching_skills] + [0.0])
        confidence = max([float(getattr(forecast, "forecast_confidence", 0) or 0) for forecast in matching_forecasts] + [0.5])
        emergence_score = clamp((growth_velocity * 0.65) + (confidence * 0.35))
        trend = "accelerating" if growth_velocity >= 0.7 else "emerging" if growth_velocity >= 0.45 else "stable"
        items.append(
            EmergingTechnologyItem(
                technology=technology,
                emergence_score=round(emergence_score, 4),
                growth_velocity=round(growth_velocity, 4),
                adoption_trend=trend,
                forecast_confidence=round(clamp(confidence), 4),
                source_payload={
                    "aliases": list(aliases),
                    "matched_forecasts": [getattr(item, "entity_name", "") for item in matching_forecasts],
                    "matched_skills": [getattr(item, "skill", "") for item in matching_skills],
                    "metric_period": metric_period,
                },
            )
        )
    items = sorted(items, key=lambda item: (item.emergence_score, item.growth_velocity, item.forecast_confidence), reverse=True)
    if write_output:
        write_emerging_technology_report(items, metric_period)
        write_labor_market_forecast_report(items, metric_period)
    return items


def write_emerging_technology_report(
    items: list[EmergingTechnologyItem],
    metric_period: str,
    path: Path | None = None,
) -> None:
    path = path or (Path(__file__).resolve().parents[1] / "outputs" / "analytics" / "emerging_technology_report.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Emerging Technology Observatory",
        "",
        f"- Periodo: {metric_period}",
        f"- Tecnologias observadas: {len(items)}",
        "",
    ]
    for item in items[:40]:
        lines.extend(
            [
                f"## {item.technology}",
                f"- Emergence score: {round(item.emergence_score, 4)}",
                f"- Growth velocity: {round(item.growth_velocity, 4)}",
                f"- Adoption trend: {item.adoption_trend}",
                f"- Forecast confidence: {round(item.forecast_confidence, 4)}",
                f"- Evidence: {json.dumps(item.source_payload, ensure_ascii=False)}",
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_labor_market_forecast_report(
    items: list[EmergingTechnologyItem],
    metric_period: str,
    path: Path | None = None,
) -> None:
    path = path or (Path(__file__).resolve().parents[1] / "outputs" / "analytics" / "labor_market_forecast_report.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Labor Market Forecast Report",
        "",
        f"- Periodo: {metric_period}",
        "",
    ]
    for item in items[:20]:
        lines.append(
            f"- {item.technology}: phase={item.adoption_trend}, growth={round(item.growth_velocity, 4)}, confidence={round(item.forecast_confidence, 4)}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
