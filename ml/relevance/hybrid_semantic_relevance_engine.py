from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.relevance.job_contextual_evidence_engine import JobContextualEvidence, build_contextual_evidence  # noqa: E402
from scrapers.normalization.visual_analytics_skill_taxonomy import (  # noqa: E402
    extract_visual_analytics_skills,
    normalize_text,
)


@dataclass(frozen=True)
class SkillCluster:
    name: str
    weight: float
    synonyms: tuple[str, ...]
    semantic_aliases: tuple[str, ...]
    contextual_importance: str


@dataclass(frozen=True)
class HybridRelevanceResult:
    accepted: bool
    tier: str
    final_semantic_relevance_score: float
    title_relevance: float
    description_relevance: float
    analytics_cluster_score: float
    bi_cluster_score: float
    tools_stack_score: float
    semantic_similarity: float
    contextual_evidence_score: float
    negative_moderation: float
    career_family: str
    role_alignment: float
    cluster_hits: dict[str, list[str]]
    evidence_summary: str
    rejection_reason: str
    explainability: list[str]


SKILL_CLUSTERS: tuple[SkillCluster, ...] = (
    SkillCluster("visualization", 0.12, ("power bi", "tableau", "dashboard", "dashboards", "looker"), ("visual analytics", "visualizacion", "storytelling"), "primary"),
    SkillCluster("analytics", 0.14, ("analytics", "analitica", "analítica", "data analysis", "sql", "python"), ("analisis de datos", "insights", "metricas"), "primary"),
    SkillCluster("business_intelligence", 0.13, ("bi", "business intelligence", "reporting", "kpi", "kpis"), ("inteligencia de negocios", "corporate reporting"), "primary"),
    SkillCluster("data_engineering", 0.13, ("etl", "pipeline", "pipelines", "data warehouse", "spark"), ("data integration", "data platform", "warehouse"), "primary"),
    SkillCluster("cloud_data", 0.08, ("azure", "aws", "gcp", "bigquery", "redshift"), ("cloud analytics", "azure data", "aws analytics"), "secondary"),
    SkillCluster("ai_analytics", 0.07, ("machine learning", "predictive analytics", "modelos predictivos", "ai"), ("ml", "analitica predictiva"), "secondary"),
    SkillCluster("reporting", 0.08, ("reporting", "dashboard", "kpi", "indicadores"), ("executive reporting", "management reporting"), "secondary"),
    SkillCluster("governance", 0.07, ("data governance", "data quality", "linaje", "lineage"), ("gobierno de datos", "calidad de datos"), "secondary"),
    SkillCluster("mlops", 0.04, ("mlops", "model monitoring", "model deployment"), ("operacionalizacion de modelos",), "secondary"),
    SkillCluster("dataops", 0.04, ("dataops", "data observability", "data reliability"), ("operaciones de datos",), "secondary"),
)

PRIMARY_FAMILIES = {"analytics", "bi", "visualization", "data_engineering"}
SECONDARY_FAMILIES = {"cloud_data", "ai_analytics", "governance", "reporting"}
TERTIARY_FAMILIES = {"backend_data_platform", "apis", "pipelines"}

HYBRID_ROLE_TERMS = {
    "backend_data_platform": ("backend data developer", "bi backend developer", "backend", "apis", "microservices", "microservicios"),
    "data_engineering": ("etl developer", "data integration engineer", "data engineer", "analytics platform engineer"),
    "cloud_data": ("azure analytics engineer", "cloud data engineer", "cloud bi engineer"),
    "reporting": ("reporting engineer", "reporting developer"),
    "analytics_bi_visualization": ("bi engineer", "bi analyst", "data analyst", "analytics engineer", "visualization specialist", "power bi developer"),
}

PURE_NEGATIVE = ("helpdesk", "mesa de ayuda", "soporte tecnico", "soporte técnico", "hardware", "impresoras", "cableado", "mantenimiento fisico", "mantenimiento físico")
INFRA_NEGATIVE = ("networking", "redes", "noc", "infraestructura")


def _contains(text: str, term: str) -> bool:
    normalized = f" {normalize_text(text)} "
    return f" {normalize_text(term)} " in normalized


def cluster_hits(text: str) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for cluster in SKILL_CLUSTERS:
        terms = (*cluster.synonyms, *cluster.semantic_aliases)
        matched = sorted({term for term in terms if _contains(text, term)})
        if matched:
            hits[cluster.name] = matched
    return hits


def weighted_cluster_score(hits: dict[str, list[str]], cluster_names: Iterable[str] | None = None) -> float:
    selected = set(cluster_names or [cluster.name for cluster in SKILL_CLUSTERS])
    numerator = 0.0
    denominator = 0.0
    for cluster in SKILL_CLUSTERS:
        if cluster.name not in selected:
            continue
        denominator += cluster.weight
        if cluster.name in hits:
            density = min(0.65 + len(hits[cluster.name]) * 0.12, 1.0)
            numerator += cluster.weight * density
    return round(numerator / denominator if denominator else 0.0, 4)


def cluster_coverage_score(hits: dict[str, list[str]]) -> float:
    primary_hits = len([name for name in ("visualization", "analytics", "business_intelligence", "data_engineering") if name in hits])
    secondary_hits = len([name for name in ("cloud_data", "ai_analytics", "reporting", "governance", "mlops", "dataops") if name in hits])
    return round(min(primary_hits / 4 * 0.72 + secondary_hits / 6 * 0.28, 1.0), 4)


def role_title_relevance(title: str) -> float:
    normalized = normalize_text(title)
    role_terms = {
        "bi engineer",
        "bi analyst",
        "business intelligence",
        "data analyst",
        "analytics engineer",
        "data engineer",
        "etl developer",
        "reporting engineer",
        "power bi developer",
        "tableau developer",
        "backend data",
        "dataops",
    }
    if any(term in normalized for term in role_terms):
        return 1.0
    if any(term in normalized for term in ("backend", "cloud", "azure", "reporting", "etl")):
        return 0.62
    return 0.0


def semantic_similarity(text: str) -> float:
    target = (
        "visual analytics business intelligence dashboards kpis power bi tableau sql python etl data warehouse "
        "data lake cloud analytics azure spark databricks snowflake governance reporting predictive analytics"
    )
    normalized = normalize_text(text)
    if not normalized:
        return 0.0
    try:
        matrix = TfidfVectorizer(ngram_range=(1, 2)).fit_transform([normalized, target])
        tfidf = float(cosine_similarity(matrix[0], matrix[1])[0][0])
    except ValueError:
        tfidf = 0.0
    sequence = SequenceMatcher(None, normalized, normalize_text(target)).ratio() * 0.45
    return round(max(tfidf, sequence), 4)


def classify_career_family(title: str, text: str, hits: dict[str, list[str]]) -> tuple[str, float]:
    full_text = f"{title} {text}"
    for family, terms in HYBRID_ROLE_TERMS.items():
        if any(_contains(full_text, term) for term in terms):
            if family == "analytics_bi_visualization":
                return family, 0.92
            if family in {"backend_data_platform", "cloud_data"} and weighted_cluster_score(hits, {"analytics", "business_intelligence", "data_engineering", "visualization"}) >= 0.35:
                return family, 0.78
            if family != "backend_data_platform":
                return family, 0.82
    if any(name in hits for name in ("visualization", "analytics", "business_intelligence")):
        return "analytics_bi_visualization", 0.90
    if "data_engineering" in hits:
        return "data_engineering", 0.84
    return "generic_technology", 0.40


def negative_moderation(text: str, hits: dict[str, list[str]]) -> float:
    pure_hits = [term for term in PURE_NEGATIVE if _contains(text, term)]
    infra_hits = [term for term in INFRA_NEGATIVE if _contains(text, term)]
    positive_cluster_count = len(hits)
    if not pure_hits and not infra_hits:
        return 0.0
    if pure_hits and positive_cluster_count < 3:
        return 0.45
    if infra_hits and positive_cluster_count < 3:
        return 0.30
    return 0.10


def tier_for(score: float, evidence: JobContextualEvidence) -> str:
    strong_evidence = evidence.evidence_strength >= 0.55 and bool(evidence.evidence_summary)
    if score >= 0.80:
        return "Gold A"
    if score >= 0.65 and strong_evidence:
        return "Gold B"
    if score >= 0.50:
        return "Silver"
    return "Rejected"


def score_hybrid_semantic_relevance(
    *,
    title: str,
    description: str,
    skills: Iterable[str] = (),
    technologies: Iterable[str] = (),
    document_type: str = "job_posting",
    evidence_source_type: str = "job_evidence",
    is_real_job_posting: bool = True,
) -> HybridRelevanceResult:
    if document_type != "job_posting" or evidence_source_type != "job_evidence" or not is_real_job_posting:
        return HybridRelevanceResult(
            accepted=False,
            tier="Rejected",
            final_semantic_relevance_score=0.0,
            title_relevance=0.0,
            description_relevance=0.0,
            analytics_cluster_score=0.0,
            bi_cluster_score=0.0,
            tools_stack_score=0.0,
            semantic_similarity=0.0,
            contextual_evidence_score=0.0,
            negative_moderation=0.0,
            career_family="non_job_document",
            role_alignment=0.0,
            cluster_hits={},
            evidence_summary="",
            rejection_reason="rejected_non_job_document",
            explainability=[f"Rejected because document_type={document_type} and evidence_source_type={evidence_source_type}"],
        )
    extracted = extract_visual_analytics_skills(f"{title} {description} {' '.join(skills)} {' '.join(technologies)}")
    all_skills = [item.normalized for item in extracted]
    text = " ".join([title, description, " ".join(skills), " ".join(technologies), " ".join(all_skills)])
    hits = cluster_hits(text)
    evidence = build_contextual_evidence(
        title=title,
        description=description,
        skills=[*skills, *all_skills],
        technologies=technologies,
        document_type=document_type,
        evidence_source_type=evidence_source_type,
        is_real_job_posting=is_real_job_posting,
    )

    coverage = cluster_coverage_score(hits)
    title_relevance = max(weighted_cluster_score(cluster_hits(title)), role_title_relevance(title))
    description_relevance = max(weighted_cluster_score(cluster_hits(description)), coverage)
    analytics_cluster_score = weighted_cluster_score(hits, {"analytics", "visualization", "data_engineering"})
    bi_cluster_score = weighted_cluster_score(hits, {"business_intelligence", "reporting", "governance"})
    tools_stack_score = weighted_cluster_score(hits, {"visualization", "data_engineering", "cloud_data", "ai_analytics", "mlops", "dataops"})
    semantic = semantic_similarity(text)
    contextual_score = max(evidence.evidence_strength, coverage)
    family, role_alignment = classify_career_family(title, text, hits)
    negative = negative_moderation(text, hits)

    raw_score = (
        title_relevance * 0.15
        + description_relevance * 0.25
        + analytics_cluster_score * 0.20
        + bi_cluster_score * 0.15
        + tools_stack_score * 0.10
        + semantic * 0.10
        + contextual_score * 0.05
    )
    if family in {"backend_data_platform", "cloud_data", "data_engineering", "analytics_bi_visualization"} and coverage >= 0.45:
        raw_score += 0.08 * role_alignment
    final_score = round(max(min(raw_score - negative, 1.0), 0.0), 4)
    tier = tier_for(final_score, evidence)
    accepted = tier != "Rejected"
    explainability = []
    if accepted:
        explainability.append(f"Accepted as {tier}")
    else:
        explainability.append("Rejected because semantic relevance is below Silver threshold")
    for cluster_name, terms in hits.items():
        explainability.append(f"Cluster {cluster_name}: {', '.join(terms[:5])}")
    if negative:
        explainability.append(f"Negative moderation applied: {negative:.2f}")
    if evidence.evidence_summary:
        explainability.append(evidence.evidence_summary)
    rejection_reason = "accepted" if accepted else "rejected_low_hybrid_semantic_relevance"
    if negative >= 0.30 and not accepted:
        rejection_reason = "rejected_pure_support_or_infrastructure"

    return HybridRelevanceResult(
        accepted=accepted,
        tier=tier,
        final_semantic_relevance_score=final_score,
        title_relevance=title_relevance,
        description_relevance=description_relevance,
        analytics_cluster_score=analytics_cluster_score,
        bi_cluster_score=bi_cluster_score,
        tools_stack_score=tools_stack_score,
        semantic_similarity=semantic,
        contextual_evidence_score=contextual_score,
        negative_moderation=round(negative, 4),
        career_family=family,
        role_alignment=round(role_alignment, 4),
        cluster_hits=hits,
        evidence_summary=evidence.evidence_summary,
        rejection_reason=rejection_reason,
        explainability=explainability,
    )


def result_to_dict(result: HybridRelevanceResult) -> dict[str, object]:
    return asdict(result)


def write_market_memory(results: Iterable[HybridRelevanceResult], path: Path | None = None) -> Path:
    path = path or ROOT_DIR / "ml" / "datasets" / "semantic_market_memory.json"
    skill_counts: dict[str, int] = {}
    cluster_counts: dict[str, int] = {}
    roles: dict[str, int] = {}
    for result in results:
        roles[result.career_family] = roles.get(result.career_family, 0) + 1
        for cluster, terms in result.cluster_hits.items():
            cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
            for term in terms:
                skill_counts[term] = skill_counts.get(term, 0) + 1
    payload = {
        "skills_frecuentes": sorted(skill_counts.items(), key=lambda item: item[1], reverse=True),
        "clusters_comunes": sorted(cluster_counts.items(), key=lambda item: item[1], reverse=True),
        "roles_hibridos_detectados": sorted(roles.items(), key=lambda item: item[1], reverse=True),
        "senales_emergentes": ["lakehouse", "databricks", "snowflake", "mlops", "dataops", "cloud analytics"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
