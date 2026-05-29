from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.semantic_matching.visual_analytics_matcher import VisualAnalyticsMatcher  # noqa: E402
from ml.relevance.hybrid_semantic_relevance_engine import score_hybrid_semantic_relevance  # noqa: E402
from scrapers.normalization.visual_analytics_skill_taxonomy import (  # noqa: E402
    extract_visual_analytics_skills,
    normalize_visual_analytics_skill,
)

DATASET_PATH = ROOT_DIR / "ml" / "datasets" / "visual_analytics_match_training.jsonl"
REPORT_PATH = ROOT_DIR / "outputs" / "visual_analytics_matching_model_report.md"


@dataclass(frozen=True)
class MatchTrainingRow:
    microcurriculum_skill: str
    job_skill: str
    job_title: str
    job_description: str
    role_class: str
    match_label: int
    similarity_score: float
    source: str
    confidence: float
    hybrid_role: str
    semantic_label: str
    gold_tier: str
    contextual_evidence: str
    cluster_signals: dict[str, list[str]]
    final_semantic_relevance_score: float
    accepted_by_hybrid: bool


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_microcurriculum_skills() -> list[str]:
    data = load_yaml(ROOT_DIR / "config" / "visual_analytics_professional_competencies.yaml")
    skills: set[str] = set()
    for item in data.get("competencies", []):
        for skill in item.get("normalized_skills", []):
            skills.add(normalize_visual_analytics_skill(str(skill)))
    return sorted(skills)


def load_labor_skills() -> list[str]:
    data = load_yaml(ROOT_DIR / "config" / "visual_analytics_job_queries.yaml")
    skills = data.get("skills", {}).get("technologies", [])
    return sorted({normalize_visual_analytics_skill(str(skill)) for skill in skills})


def build_dataset() -> list[MatchTrainingRow]:
    matcher = VisualAnalyticsMatcher()
    curriculum_skills = load_microcurriculum_skills()
    labor_skills = load_labor_skills()
    rows: list[MatchTrainingRow] = []
    for curriculum_skill in curriculum_skills:
        for labor_skill in labor_skills:
            title = f"Perfil Visual Analytics con {labor_skill}"
            description = f"Vacante de analitica, BI y visualizacion que requiere {labor_skill}, datos, dashboarding y toma de decisiones."
            result = matcher.score_match(
                microcurriculum_text=curriculum_skill,
                job_title=title,
                job_description=description,
                job_skills=[labor_skill],
            )
            hybrid = score_hybrid_semantic_relevance(
                title=title,
                description=description,
                skills=[labor_skill, curriculum_skill],
            )
            label = 1 if result.final_match_score >= 0.30 else 0
            rows.append(
                MatchTrainingRow(
                    microcurriculum_skill=curriculum_skill,
                    job_skill=labor_skill,
                    job_title=title,
                    job_description=description,
                    role_class=result.role_class,
                    match_label=label,
                    similarity_score=result.final_match_score,
                    source="controlled_visual_analytics_seed",
                    confidence=result.confidence,
                    hybrid_role=hybrid.career_family,
                    semantic_label=hybrid.tier,
                    gold_tier=hybrid.tier if hybrid.tier.startswith("Gold") else "",
                    contextual_evidence=hybrid.evidence_summary,
                    cluster_signals=hybrid.cluster_hits,
                    final_semantic_relevance_score=hybrid.final_semantic_relevance_score,
                    accepted_by_hybrid=hybrid.accepted,
                )
            )
    return rows


def write_dataset(rows: list[MatchTrainingRow], path: Path = DATASET_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")


def write_report(rows: list[MatchTrainingRow]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    positives = sum(row.match_label for row in rows)
    top = sorted(rows, key=lambda row: row.similarity_score, reverse=True)[:15]
    lines = [
        "# Visual Analytics Matching Model Report",
        "",
        "Dataset controlado inicial para entrenamiento del matching del piloto Visual Analytics y Big Data.",
        "",
        f"- Registros: {len(rows)}",
        f"- Positivos: {positives}",
        f"- Negativos: {len(rows) - positives}",
        f"- Aceptados por motor hibrido: {sum(row.accepted_by_hybrid for row in rows)}",
        "",
        "## Top Pares Semanticos",
    ]
    for row in top:
        lines.append(f"- {row.microcurriculum_skill} <-> {row.job_skill}: {row.similarity_score:.3f}")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Visual Analytics matching training dataset.")
    parser.add_argument("--output", default=str(DATASET_PATH))
    args = parser.parse_args()
    rows = build_dataset()
    write_dataset(rows, Path(args.output))
    write_report(rows)
    print(json.dumps({"rows": len(rows), "output": args.output}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
