from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.labor.market_skill_intelligence_engine import MarketSkillSignal, build_market_skill_intelligence_map  # noqa: E402

DATASET_PATH = ROOT_DIR / "ml" / "datasets" / "curriculum_alignment_dataset.csv"
REPORT_PATH = ROOT_DIR / "outputs" / "ml_training_report.md"


@dataclass(frozen=True)
class CurriculumAlignmentTrainingRow:
    specialization_id: str
    specialization_name: str
    text: str
    skill: str
    occupational_cluster: str
    job_relevance_label: str
    skill_coverage_label: str
    occupational_affinity_label: str
    market_weight: float
    evidence_count: int
    affinity_score: float
    gold_count: int
    silver_count: int
    bronze_count: int
    taxonomy_count: int
    source_confidence_score: float
    curriculum_overlap_score: float
    market_frequency_score: float
    cluster_centrality_score: float
    recommendation_candidate: int = 0
    job_relevance_soft_label: float = 0.0
    skill_coverage_soft_label: float = 0.0
    training_weight: float = 1.0
    probabilistic_confidence: float = 0.0


def job_relevance_label(signal: MarketSkillSignal) -> str:
    if signal.market_signal_confidence == "high" and signal.coverage_status in {"covered", "partial", "emerging"}:
        return "highly_relevant"
    if signal.market_signal_confidence in {"high", "medium"}:
        return "relevant"
    if signal.coverage_status in {"partial", "emerging"}:
        return "partially_relevant"
    if signal.market_signal_confidence == "weak":
        return "weak_signal"
    return "irrelevant"


def source_confidence_score(signal: MarketSkillSignal) -> float:
    sources = signal.evidence_sources
    return round(
        min(
            1.0,
            sources.get("gold_job_posting", 0) * 1.0
            + sources.get("silver_job_posting", 0) * 0.22
            + sources.get("bronze_job_posting", 0) * 0.08
            + sources.get("legacy_empleo_skill", 0) * 0.12
            + sources.get("portal_taxonomy", 0) * 0.01,
        ),
        4,
    )


def soft_relevance_label(signal: MarketSkillSignal) -> float:
    confidence_base = {
        "high": 0.90,
        "medium": 0.68,
        "emerging": 0.62,
        "weak": 0.35,
    }.get(signal.market_signal_confidence, 0.20)
    coverage_bonus = {
        "covered": 0.08,
        "partial": 0.12,
        "missing": 0.02,
        "emerging": 0.15,
        "irrelevant": -0.20,
    }.get(signal.coverage_status, 0.0)
    return round(min(1.0, max(0.0, confidence_base + coverage_bonus + signal.affinity_score * 0.10)), 4)


def soft_coverage_label(signal: MarketSkillSignal) -> float:
    return {
        "covered": 1.0,
        "partial": 0.62,
        "emerging": 0.48,
        "missing": 0.20,
        "irrelevant": 0.0,
    }.get(signal.coverage_status, 0.15)


def training_weight(signal: MarketSkillSignal) -> float:
    source_score = source_confidence_score(signal)
    semantic_density = min(signal.evidence_count / 8, 1.0)
    probability = soft_relevance_label(signal)
    return round(max(0.05, source_score * 0.45 + probability * 0.40 + semantic_density * 0.15), 4)


def build_dataset() -> list[CurriculumAlignmentTrainingRow]:
    intelligence = build_market_skill_intelligence_map(include_database=True, write_output=True)
    max_weight = max((item.market_weight for item in intelligence.market_skills), default=1.0)
    rows: list[CurriculumAlignmentTrainingRow] = []
    for signal in intelligence.market_skills:
        sources = signal.evidence_sources
        text = " ".join(
            [
                signal.skill,
                signal.occupational_cluster,
                signal.market_signal_confidence,
                " ".join(signal.roles[:8]),
                signal.reason,
                signal.recommendation,
            ]
        )
        soft_relevance = soft_relevance_label(signal)
        soft_coverage = soft_coverage_label(signal)
        weight = training_weight(signal)
        rows.append(
            CurriculumAlignmentTrainingRow(
                specialization_id=intelligence.specialization_id,
                specialization_name=intelligence.specialization_name,
                text=text,
                skill=signal.skill,
                occupational_cluster=signal.occupational_cluster,
                job_relevance_label=job_relevance_label(signal),
                skill_coverage_label=signal.coverage_status,
                occupational_affinity_label=signal.occupational_cluster,
                market_weight=signal.market_weight,
                evidence_count=signal.evidence_count,
                affinity_score=signal.affinity_score,
                gold_count=sources.get("gold_job_posting", 0),
                silver_count=sources.get("silver_job_posting", 0),
                bronze_count=sources.get("bronze_job_posting", 0),
                taxonomy_count=sources.get("portal_taxonomy", 0),
                source_confidence_score=source_confidence_score(signal),
                curriculum_overlap_score=signal.affinity_score,
                market_frequency_score=round(signal.market_weight / max_weight, 4),
                cluster_centrality_score=round(min(signal.evidence_count / max(len(intelligence.market_skills), 1), 1.0), 4),
                job_relevance_soft_label=soft_relevance,
                skill_coverage_soft_label=soft_coverage,
                training_weight=weight,
                probabilistic_confidence=round((soft_relevance + weight) / 2, 4),
                recommendation_candidate=1 if signal.coverage_status in {"missing", "emerging", "partial"} else 0,
            )
        )
    return rows


def write_dataset(rows: list[CurriculumAlignmentTrainingRow], path: Path = DATASET_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(asdict(rows[0]).keys()) if rows else [field.name for field in CurriculumAlignmentTrainingRow.__dataclass_fields__.values()])
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_report(rows: list[CurriculumAlignmentTrainingRow]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    relevance_counts: dict[str, int] = {}
    coverage_counts: dict[str, int] = {}
    cluster_counts: dict[str, int] = {}
    for row in rows:
        relevance_counts[row.job_relevance_label] = relevance_counts.get(row.job_relevance_label, 0) + 1
        coverage_counts[row.skill_coverage_label] = coverage_counts.get(row.skill_coverage_label, 0) + 1
        cluster_counts[row.occupational_cluster] = cluster_counts.get(row.occupational_cluster, 0) + 1
    lines = [
        "# ML Training Dataset Report",
        "",
        f"- Rows: {len(rows)}",
        f"- Relevance labels: {json.dumps(relevance_counts, ensure_ascii=False)}",
        f"- Coverage labels: {json.dumps(coverage_counts, ensure_ascii=False)}",
        f"- Occupational clusters: {json.dumps(cluster_counts, ensure_ascii=False)}",
        "",
        "Heuristicas, aliases y taxonomias se conservan como features supervisadas, no como regla final.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build supervised curriculum alignment dataset.")
    parser.add_argument("--output", default=str(DATASET_PATH))
    args = parser.parse_args()
    rows = build_dataset()
    write_dataset(rows, Path(args.output))
    write_report(rows)
    print(json.dumps({"rows": len(rows), "output": args.output}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
