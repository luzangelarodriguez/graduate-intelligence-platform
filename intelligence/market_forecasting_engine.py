from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, asdict
from typing import Any

from intelligence.common import clamp


EMERGING_HINTS = {"Microsoft Fabric", "Databricks", "Synapse", "Copilot BI", "LLM", "RAG", "MLOps", "DataOps", "GenAI Analytics"}


@dataclass(frozen=True)
class MarketForecast:
    entity_type: str
    entity_name: str
    growth_velocity: float
    forecast_confidence: float
    market_phase: str
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def forecast_skills(jobs: list[dict[str, Any]]) -> list[MarketForecast]:
    counts = Counter(skill for job in jobs for skill in (job.get("skills") or []))
    total_jobs = max(len(jobs), 1)
    forecasts: list[MarketForecast] = []
    for skill, count in counts.items():
        frequency = count / total_jobs
        emerging_boost = 0.30 if skill in EMERGING_HINTS else 0.0
        growth_velocity = clamp(frequency + emerging_boost)
        phase = "emerging" if skill in EMERGING_HINTS or frequency < 0.10 else "expanding" if frequency < 0.35 else "established"
        forecasts.append(
            MarketForecast(
                entity_type="skill",
                entity_name=skill,
                growth_velocity=round(growth_velocity, 4),
                forecast_confidence=round(clamp(0.45 + min(count / 20, 0.45) + emerging_boost / 2), 4),
                market_phase=phase,
                evidence={"mentions": count, "total_jobs": total_jobs},
            )
        )
    return sorted(forecasts, key=lambda item: (item.growth_velocity, item.forecast_confidence), reverse=True)
