from __future__ import annotations

import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scrapers.normalization.visual_analytics_skill_taxonomy import (  # noqa: E402
    extract_visual_analytics_skills,
    normalize_text,
)


HIGH_RELEVANCE_SIGNALS = {
    "power bi",
    "tableau",
    "sql",
    "python",
    "dashboard",
    "dashboards",
    "kpi",
    "kpis",
    "reporting",
    "analytics",
    "analitica",
    "analítica",
    "etl",
    "bi",
    "visualization",
    "visualizacion",
    "visualización",
    "business intelligence",
    "data warehouse",
    "data lake",
    "snowflake",
    "databricks",
    "spark",
    "looker",
    "bigquery",
    "storytelling",
    "governance",
    "data governance",
    "data quality",
    "machine learning",
    "predictive analytics",
    "data pipeline",
    "warehouse",
}

STACK_SIGNALS = {
    "power bi",
    "tableau",
    "looker",
    "bigquery",
    "sql",
    "python",
    "r",
    "spark",
    "databricks",
    "snowflake",
    "redshift",
    "azure",
    "aws",
    "gcp",
    "etl",
    "data lake",
    "lakehouse",
    "data warehouse",
}

DATA_ENGINEERING_ROLES = {
    "backend data developer",
    "data platform engineer",
    "reporting developer",
    "bi backend engineer",
    "etl developer",
    "cloud data engineer",
    "analytics platform engineer",
    "data integration engineer",
    "data engineer",
    "ingeniero de datos",
}

NEGATIVE_SIGNALS = {
    "soporte tecnico",
    "soporte técnico",
    "helpdesk",
    "mesa de ayuda",
    "soporte en sitio",
    "mantenimiento hardware",
    "cableado",
    "impresoras",
    "active directory",
    "networking",
    "redes",
    "noc",
    "service desk",
}

ANALYTICS_ROLE_TERMS = {
    "data analyst",
    "analista de datos",
    "bi analyst",
    "analista bi",
    "business intelligence analyst",
    "analytics engineer",
    "analytics consultant",
    "data visualization specialist",
    "power bi developer",
    "tableau developer",
}


@dataclass(frozen=True)
class ContextualRelevanceResult:
    accepted: bool
    contextual_relevance_score: float
    title_relevance: float
    description_relevance: float
    stack_relevance: float
    analytics_density: float
    bi_density: float
    data_engineering_density: float
    emerging_skill_weight: float
    semantic_similarity: float
    role_alignment: float
    negative_signal_score: float
    detected_signals: list[str]
    detected_negative_signals: list[str]
    detected_stack: list[str]
    role_class: str
    decision_reason: str
    hybrid_tier: str
    final_semantic_relevance_score: float
    contextual_evidence: str
    cluster_signals: dict[str, list[str]]
    accepted_by_hybrid: bool
    hybrid_career_family: str
    curriculum_alignment_score: float
    gold_score: float
    curriculum_gold_tier: str
    curriculum_shared_skills: list[str]
    curriculum_related_matches: dict[str, list[str]]
    market_gap_signal: list[str]
    curriculum_explanation: str
    document_type: str = "job_posting"
    evidence_source_type: str = "job_evidence"
    is_real_job_posting: bool = True


def _count_signals(text: str, signals: Iterable[str]) -> list[str]:
    normalized = normalize_text(text)
    hits: list[str] = []
    for signal in signals:
        if re.search(rf"(?<![a-z0-9]){re.escape(normalize_text(signal))}(?![a-z0-9])", normalized):
            hits.append(signal)
    return sorted(set(hits))


def _density(text: str, signals: Iterable[str], denominator: int = 8) -> float:
    return round(min(len(_count_signals(text, signals)) / denominator, 1.0), 4)


def _semantic_similarity(text: str) -> float:
    target = (
        "visual analytics business intelligence analitica de datos big data power bi tableau sql python "
        "etl dashboards data engineering data warehouse data governance cloud analytics"
    )
    left = normalize_text(text)
    right = normalize_text(target)
    if not left:
        return 0.0
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    overlap = len(left_tokens & right_tokens) / max(len(right_tokens), 1)
    sequence = SequenceMatcher(None, left, right).ratio()
    return round(max(overlap, sequence * 0.35), 4)


def classify_contextual_role(title: str, description: str) -> str:
    text = normalize_text(f"{title} {description}")
    if any(normalize_text(term) in text for term in DATA_ENGINEERING_ROLES):
        return "data_engineering"
    if any(normalize_text(term) in text for term in ANALYTICS_ROLE_TERMS):
        return "analytics_bi"
    if any(term in text for term in ("reporting", "dashboard", "power bi", "tableau")):
        return "reporting_visualization"
    if any(term in text for term in ("etl", "pipeline", "warehouse", "lakehouse")):
        return "data_integration"
    return "generic_technology"


def score_contextual_relevance(
    *,
    title: str,
    description: str,
    tags: Iterable[str] = (),
    skills: Iterable[str] = (),
    technologies: Iterable[str] = (),
    document_type: str = "job_posting",
    evidence_source_type: str = "job_evidence",
    is_real_job_posting: bool = True,
) -> ContextualRelevanceResult:
    from ml.relevance.hybrid_semantic_relevance_engine import score_hybrid_semantic_relevance
    from ml.curriculum.curriculum_alignment_engine import (
        compute_gold_score,
        curriculum_gold_tier,
        score_curriculum_alignment,
    )

    hybrid = score_hybrid_semantic_relevance(
        title=title,
        description=description,
        skills=skills,
        technologies=technologies,
        document_type=document_type,
        evidence_source_type=evidence_source_type,
        is_real_job_posting=is_real_job_posting,
    )
    full_text = " ".join([title, description, " ".join(tags), " ".join(skills), " ".join(technologies)])
    detected_signals = _count_signals(full_text, HIGH_RELEVANCE_SIGNALS)
    detected_stack = _count_signals(full_text, STACK_SIGNALS)
    negative_signals = _count_signals(full_text, NEGATIVE_SIGNALS)
    extracted_skills = extract_visual_analytics_skills(full_text)
    role_class = classify_contextual_role(title, description)

    title_relevance = _density(title, HIGH_RELEVANCE_SIGNALS, denominator=3)
    description_relevance = _density(description, HIGH_RELEVANCE_SIGNALS, denominator=8)
    stack_relevance = round(min((len(detected_stack) + len(list(technologies))) / 8, 1.0), 4)
    analytics_density = _density(full_text, {"analytics", "analitica", "analítica", "data", "datos", "visualization", "visualizacion"}, denominator=5)
    bi_density = _density(full_text, {"bi", "business intelligence", "power bi", "tableau", "dashboard", "reporting", "kpi", "kpis"}, denominator=5)
    data_engineering_density = _density(full_text, {"etl", "pipeline", "spark", "databricks", "snowflake", "data warehouse", "data lake", "lakehouse"}, denominator=5)
    emerging_skill_weight = _density(full_text, {"machine learning", "predictive analytics", "databricks", "snowflake", "lakehouse", "bigquery", "data governance"}, denominator=5)
    semantic_similarity = _semantic_similarity(full_text)
    role_alignment = 0.90 if role_class != "generic_technology" else 0.45
    negative_signal_score = min(len(negative_signals) / 4, 1.0)
    curriculum = score_curriculum_alignment(
        title=title,
        description=description,
        skills=skills,
        technologies=technologies,
        document_type=document_type,
        evidence_source_type=evidence_source_type,
        is_real_job_posting=is_real_job_posting,
    )

    raw_score = (
        title_relevance * 0.10
        + description_relevance * 0.20
        + stack_relevance * 0.22
        + analytics_density * 0.10
        + bi_density * 0.16
        + data_engineering_density * 0.10
        + emerging_skill_weight * 0.05
        + semantic_similarity * 0.02
        + role_alignment * 0.05
    )
    penalty = 0.35 * negative_signal_score
    if negative_signals and (len(detected_signals) + len(detected_stack)) >= 4:
        penalty *= 0.35
    legacy_score = round(max(min(raw_score - penalty, 1.0), 0.0), 4)
    score = round(max(legacy_score, hybrid.final_semantic_relevance_score), 4)
    gold_score = compute_gold_score(
        semantic_market_relevance=score,
        curriculum_alignment_score=curriculum.curriculum_alignment_score,
        contextual_evidence_score=hybrid.contextual_evidence_score,
        quality_score=0.85,
    )
    curriculum_tier = curriculum_gold_tier(gold_score, curriculum.curriculum_alignment_score)
    accepted = (
        (score >= 0.50 and (len(detected_signals) >= 2 or len(detected_stack) >= 2))
        or hybrid.accepted
        or curriculum_tier in {"Gold A", "Gold B", "Silver"}
    )
    if negative_signals and score < 0.72:
        accepted = False
    if document_type != "job_posting" or evidence_source_type != "job_evidence" or not is_real_job_posting:
        accepted = False
    reason = (
        f"accepted_{curriculum_tier.lower().replace(' ', '_')}"
        if curriculum_tier in {"Gold A", "Gold B"}
        else f"accepted_{hybrid.tier.lower().replace(' ', '_')}"
        if hybrid.accepted
        else "accepted_contextual_curriculum_signal"
        if accepted
        else "rejected_low_contextual_relevance"
    )
    if negative_signals and not accepted:
        reason = "rejected_negative_support_or_infrastructure_signal"
    if document_type != "job_posting" or evidence_source_type != "job_evidence" or not is_real_job_posting:
        reason = "rejected_non_job_document"
    return ContextualRelevanceResult(
        accepted=accepted,
        contextual_relevance_score=score,
        title_relevance=round(title_relevance, 4),
        description_relevance=round(description_relevance, 4),
        stack_relevance=round(stack_relevance, 4),
        analytics_density=round(analytics_density, 4),
        bi_density=round(bi_density, 4),
        data_engineering_density=round(data_engineering_density, 4),
        emerging_skill_weight=round(emerging_skill_weight, 4),
        semantic_similarity=round(semantic_similarity, 4),
        role_alignment=round(role_alignment, 4),
        negative_signal_score=round(negative_signal_score, 4),
        detected_signals=detected_signals,
        detected_negative_signals=negative_signals,
        detected_stack=detected_stack,
        role_class=role_class,
        decision_reason=reason,
        hybrid_tier=hybrid.tier,
        final_semantic_relevance_score=hybrid.final_semantic_relevance_score,
        contextual_evidence=hybrid.evidence_summary,
        cluster_signals=hybrid.cluster_hits,
        accepted_by_hybrid=hybrid.accepted,
        hybrid_career_family=hybrid.career_family,
        curriculum_alignment_score=curriculum.curriculum_alignment_score,
        gold_score=gold_score,
        curriculum_gold_tier=curriculum_tier,
        curriculum_shared_skills=curriculum.shared_skills,
        curriculum_related_matches=curriculum.related_matches,
        market_gap_signal=curriculum.market_gap_signal,
        curriculum_explanation=curriculum.explanation,
        document_type=document_type,
        evidence_source_type=evidence_source_type,
        is_real_job_posting=is_real_job_posting,
    )


def result_to_dict(result: ContextualRelevanceResult) -> dict[str, object]:
    return asdict(result)


def main() -> int:
    sample = score_contextual_relevance(
        title="Backend Data Developer",
        description="Desarrollo de data pipelines, SQL, dashboards, ETL, data warehouse y reporting para plataformas de analytics.",
    )
    print(json.dumps(result_to_dict(sample), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
