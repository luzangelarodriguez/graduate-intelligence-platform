from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.labor.labor_market_skill_extraction_engine import LaborMarketSkill, build_labor_market_skill_universe
from scrapers.normalization.visual_analytics_skill_taxonomy import normalize_text

CLUSTERS_JSON = ROOT_DIR / "outputs" / "occupational_skill_clusters.json"

CLUSTER_TERMS: dict[str, tuple[str, ...]] = {
    "BI & Visualization": ("power bi", "tableau", "looker", "qlik", "dashboard", "visualizacion", "visualization", "storytelling"),
    "Data Engineering": ("etl", "spark", "hadoop", "databricks", "snowflake", "warehouse", "lake", "pipeline"),
    "Cloud Analytics": ("azure", "aws", "gcp", "google cloud", "bigquery", "fabric", "synapse", "cloud"),
    "AI Analytics": ("machine learning", "ai", "ia", "mlops", "modelos predictivos"),
    "Data Governance": ("governance", "gobierno", "quality", "calidad", "linaje", "metadata", "catalog"),
    "Reporting & KPI": ("reporting", "executive reporting", "kpi", "indicadores", "bi", "scorecard"),
    "DataOps": ("dataops", "observability", "ci cd", "reliability"),
    "GenAI Analytics": ("genai", "generative ai", "copilot", "rag", "llm"),
    "Software/Data Platform": ("api", "backend", "platform", "microservices", "software"),
}


@dataclass(frozen=True)
class OccupationalSkillCluster:
    cluster_name: str
    skills: list[str]
    total_weight: float
    evidence_count: int
    dominant_sources: dict[str, int]
    representative_roles: list[str]
    is_strong_market_signal: bool


def classify_skill_cluster(skill: str) -> str:
    text = normalize_text(skill)
    scores = {
        name: sum(1 for term in terms if normalize_text(term) in text)
        for name, terms in CLUSTER_TERMS.items()
    }
    best, score = max(scores.items(), key=lambda item: item[1])
    if score:
        return best
    return "Software/Data Platform" if any(term in text for term in ("api", "backend", "software", "platform")) else "Enterprise Analytics"


def build_occupational_skill_clusters(
    universe: list[LaborMarketSkill] | None = None,
    *,
    write_output: bool = True,
) -> list[OccupationalSkillCluster]:
    universe = universe if universe is not None else build_labor_market_skill_universe()
    grouped: dict[str, list[LaborMarketSkill]] = defaultdict(list)
    for item in universe:
        grouped[classify_skill_cluster(item.skill)].append(item)

    clusters: list[OccupationalSkillCluster] = []
    for cluster_name, items in grouped.items():
        source_counts: dict[str, int] = defaultdict(int)
        roles: set[str] = set()
        for item in items:
            for source, count in item.source_breakdown.items():
                source_counts[source] += count
            roles.update(item.roles)
        total_weight = round(sum(item.total_weight for item in items), 4)
        clusters.append(
            OccupationalSkillCluster(
                cluster_name=cluster_name,
                skills=[item.skill for item in sorted(items, key=lambda row: row.total_weight, reverse=True)],
                total_weight=total_weight,
                evidence_count=sum(item.evidence_count for item in items),
                dominant_sources=dict(sorted(source_counts.items())),
                representative_roles=sorted(roles)[:12],
                is_strong_market_signal=total_weight >= 1.0 or any(source in source_counts for source in ("gold_job_posting", "silver_job_posting")),
            )
        )
    clusters = sorted(clusters, key=lambda item: (item.total_weight, item.evidence_count), reverse=True)
    if write_output:
        CLUSTERS_JSON.parent.mkdir(parents=True, exist_ok=True)
        CLUSTERS_JSON.write_text(json.dumps([asdict(item) for item in clusters], indent=2, ensure_ascii=False), encoding="utf-8")
    return clusters


def clusters_to_dict(clusters: list[OccupationalSkillCluster]) -> list[dict[str, Any]]:
    return [asdict(item) for item in clusters]
