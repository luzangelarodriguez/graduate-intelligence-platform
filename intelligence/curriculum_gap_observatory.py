from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from intelligence.common import clamp

EMERGING_CLUSTERS = {"Cloud Analytics", "DataOps", "GenAI Analytics", "AI Analytics", "Data Governance"}


@dataclass(frozen=True)
class CurriculumGapObservation:
    specialization: str
    missing_skill: str
    market_demand_score: float
    curriculum_coverage_score: float
    urgency_score: float
    emergence_score: float
    recommendation: str
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _demand_score(item: Any, max_weight: float) -> float:
    return round(clamp(float(getattr(item, "evidence_weight", 0) or 0) / max(max_weight, 1.0)), 4)


def _emergence_score(item: Any) -> float:
    status = str(getattr(item, "coverage_status", "") or "")
    cluster = str(getattr(item, "cluster_name", "") or "")
    if status == "emerging":
        return 1.0
    if status == "missing" and cluster in EMERGING_CLUSTERS:
        return 0.85
    if status == "partial" and cluster in EMERGING_CLUSTERS:
        return 0.58
    if status == "missing":
        return 0.42
    return 0.12


def build_curriculum_gap_observatory(
    *,
    gap_map: Any,
    metric_period: str,
    write_output: bool = True,
) -> list[CurriculumGapObservation]:
    items = list(getattr(gap_map, "emerging_skills", []) or [])
    items.extend(list(getattr(gap_map, "missing_skills", []) or []))
    items.extend(list(getattr(gap_map, "partial_skills", []) or []))
    max_weight = max((float(getattr(item, "evidence_weight", 0) or 0) for item in items), default=1.0)
    observations: list[CurriculumGapObservation] = []
    for item in items:
        demand = _demand_score(item, max_weight)
        coverage = round(clamp(float(getattr(item, "affinity_score", 0) or 0)), 4)
        emergence = _emergence_score(item)
        urgency = round(clamp((demand * (1 - coverage)) + (emergence * 0.25)), 4)
        observations.append(
            CurriculumGapObservation(
                specialization=str(getattr(gap_map, "specialization_name", "") or getattr(gap_map, "specialization_id", "")),
                missing_skill=str(getattr(item, "skill", "") or ""),
                market_demand_score=demand,
                curriculum_coverage_score=coverage,
                urgency_score=urgency,
                emergence_score=emergence,
                recommendation=str(getattr(item, "recommendation", "") or ""),
                evidence={
                    "cluster_name": getattr(item, "cluster_name", ""),
                    "coverage_status": getattr(item, "coverage_status", ""),
                    "evidence_weight": getattr(item, "evidence_weight", 0),
                    "evidence_sources": getattr(item, "evidence_sources", {}),
                    "roles": getattr(item, "roles", []),
                    "reason": getattr(item, "reason", ""),
                    "metric_period": metric_period,
                },
            )
        )
    observations.sort(key=lambda row: (row.urgency_score, row.market_demand_score), reverse=True)
    if write_output:
        write_curriculum_gap_report(observations, metric_period)
    return observations


def write_curriculum_gap_report(
    observations: list[CurriculumGapObservation],
    metric_period: str,
    path: Path | None = None,
) -> None:
    path = path or (Path(__file__).resolve().parents[1] / "outputs" / "analytics" / "curriculum_gap_report.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Curriculum Gap Observatory",
        "",
        f"- Periodo: {metric_period}",
        f"- Gaps observados: {len(observations)}",
        "",
        "## Prioridades",
        "",
    ]
    for row in observations[:40]:
        lines.extend(
            [
                f"### {row.missing_skill}",
                f"- Especializacion: {row.specialization}",
                f"- Demanda de mercado: {round(row.market_demand_score, 4)}",
                f"- Cobertura curricular: {round(row.curriculum_coverage_score, 4)}",
                f"- Urgencia: {round(row.urgency_score, 4)}",
                f"- Emergencia: {round(row.emergence_score, 4)}",
                f"- Recomendacion: {row.recommendation}",
                f"- Evidencia: {json.dumps(row.evidence, ensure_ascii=False)}",
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
