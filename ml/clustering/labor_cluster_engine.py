from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.curriculum.curriculum_alignment_engine import (  # noqa: E402
    CurriculumSkillGraph,
    load_or_build_curriculum_skill_graph,
    score_curriculum_alignment,
)
from scrapers.normalization.visual_analytics_skill_taxonomy import extract_visual_analytics_skills, normalize_text  # noqa: E402

RESULTS_PATH = ROOT_DIR / "outputs" / "agentic_labor_extraction_results.json"
CLUSTERS_JSON = ROOT_DIR / "outputs" / "labor_occupational_clusters.json"
CLUSTERS_REPORT = ROOT_DIR / "outputs" / "labor_occupational_clusters_report.md"
AFFINITY_REPORT = ROOT_DIR / "outputs" / "curriculum_affinity_report.md"
GAPS_REPORT = ROOT_DIR / "outputs" / "market_gap_intelligence_report.md"


@dataclass(frozen=True)
class LaborJobSignal:
    job_id: str
    title: str
    description: str
    company: str
    source_url: str
    skills: list[str]
    tools: list[str]
    technologies: list[str]
    contextual_evidence: str
    curriculum_alignment_score: float
    gold_score: float
    semantic_clusters: dict[str, list[str]]
    responsibilities: list[str]


@dataclass(frozen=True)
class OccupationalCluster:
    id: int
    cluster_name: str
    semantic_summary: str
    dominant_skills: list[str]
    dominant_tools: list[str]
    dominant_roles: list[str]
    market_frequency: int
    avg_salary_estimate: float | None
    growth_signal: str
    embedding_centroid: list[float]
    jobs: list[LaborJobSignal]
    specialization_affinity: dict[str, float]
    market_gaps: list[dict[str, Any]]
    trends: list[str]


CLUSTER_RULES: dict[str, tuple[str, ...]] = {
    "BI & Visualization": ("power bi", "tableau", "dashboard", "dashboards", "visualizacion", "visualization", "storytelling"),
    "Cloud Analytics": ("azure", "aws", "gcp", "cloud analytics", "synapse", "fabric", "bigquery", "redshift"),
    "Data Engineering": ("etl", "pipeline", "pipelines", "data warehouse", "spark", "hadoop", "databricks", "snowflake"),
    "AI Analytics": ("machine learning", "modelos predictivos", "ai", "ia", "predictive analytics"),
    "Reporting & KPI": ("reporting", "kpi", "kpis", "indicadores", "business reporting"),
    "Data Governance": ("data governance", "gobierno de datos", "data quality", "linaje"),
    "DataOps": ("dataops", "observability", "reliability", "ci cd", "pipelines"),
    "GenAI Analytics": ("genai", "generative ai", "copilot", "rag analytics", "llm"),
}

EMERGING_TERMS = {
    "fabric",
    "databricks",
    "genai analytics",
    "copilot bi",
    "data governance",
    "rag analytics",
    "snowflake",
    "synapse",
    "dataops",
}


def _job_text(job: LaborJobSignal) -> str:
    return " ".join(
        [
            job.title,
            job.description,
            " ".join(job.skills),
            " ".join(job.tools),
            " ".join(job.technologies),
            job.contextual_evidence,
        ]
    )


def load_valid_jobs_from_results(path: Path = RESULTS_PATH) -> list[LaborJobSignal]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    jobs: list[LaborJobSignal] = []
    for index, item in enumerate(data):
        silver = item.get("silver") or {}
        contextual = silver.get("contextual") or {}
        if silver.get("document_type") != "job_posting" or not silver.get("is_real_job_posting"):
            continue
        if not silver.get("job_evidence_skills"):
            continue
        if not item.get("gold") and not silver.get("accepted_for_gold"):
            continue
        jobs.append(
            LaborJobSignal(
                job_id=str(silver.get("content_hash") or index),
                title=str(silver.get("normalized_title") or ""),
                description=str(silver.get("normalized_description") or ""),
                company=str(silver.get("normalized_company") or ""),
                source_url=str(silver.get("source_url") or ""),
                skills=list(silver.get("job_evidence_skills") or silver.get("extracted_skills") or []),
                tools=list(silver.get("extracted_tools") or []),
                technologies=list((silver.get("extracted_cloud") or []) + (silver.get("extracted_frameworks") or [])),
                contextual_evidence=str(contextual.get("contextual_evidence") or ""),
                curriculum_alignment_score=float(contextual.get("curriculum_alignment_score") or 0),
                gold_score=float(contextual.get("gold_score") or 0),
                semantic_clusters=dict(contextual.get("cluster_signals") or {}),
                responsibilities=[],
            )
        )
    return jobs


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model.encode(texts, normalize_embeddings=True).tolist()
    except Exception:
        from sklearn.feature_extraction.text import TfidfVectorizer

        matrix = TfidfVectorizer(max_features=64, ngram_range=(1, 2)).fit_transform(texts)
        return matrix.toarray().tolist()


def _cosine_centroid(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    width = max(len(vector) for vector in vectors)
    padded = [vector + [0.0] * (width - len(vector)) for vector in vectors]
    return [round(sum(vector[i] for vector in padded) / len(padded), 6) for i in range(width)]


def _rule_cluster_name(job: LaborJobSignal) -> str:
    text = normalize_text(_job_text(job))
    scores = {
        name: sum(1 for term in terms if normalize_text(term) in text)
        for name, terms in CLUSTER_RULES.items()
    }
    best, score = max(scores.items(), key=lambda item: item[1])
    return best if score else "Enterprise Analytics"


def _cluster_labels(jobs: list[LaborJobSignal], embeddings: list[list[float]]) -> list[int]:
    if len(jobs) <= 4:
        by_rule: dict[str, int] = {}
        labels: list[int] = []
        for job in jobs:
            name = _rule_cluster_name(job)
            by_rule.setdefault(name, len(by_rule))
            labels.append(by_rule[name])
        return labels
    try:
        import hdbscan
        import umap

        reduced = umap.UMAP(n_components=min(5, len(jobs) - 1), random_state=42).fit_transform(embeddings)
        labels = hdbscan.HDBSCAN(min_cluster_size=2, min_samples=1).fit_predict(reduced)
        if any(label >= 0 for label in labels):
            return [int(label) if int(label) >= 0 else max(labels) + idx + 1 for idx, label in enumerate(labels)]
    except Exception:
        pass
    try:
        from sklearn.cluster import KMeans

        k = min(max(2, len(jobs) // 3), 8, len(jobs))
        return [int(label) for label in KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(embeddings)]
    except Exception:
        by_rule: dict[str, int] = {}
        labels: list[int] = []
        for job in jobs:
            name = _rule_cluster_name(job)
            by_rule.setdefault(name, len(by_rule))
            labels.append(by_rule[name])
        return labels


def _dominant(values: Iterable[str], limit: int = 8) -> list[str]:
    return [value for value, _count in Counter(value for value in values if value).most_common(limit)]


def _cluster_name_for_jobs(jobs: list[LaborJobSignal]) -> str:
    names = [_rule_cluster_name(job) for job in jobs]
    return Counter(names).most_common(1)[0][0] if names else "Enterprise Analytics"


def _affinity_scores(jobs: list[LaborJobSignal], graph: CurriculumSkillGraph) -> dict[str, float]:
    if not jobs:
        return {}
    visual_scores = [
        score_curriculum_alignment(
            title=job.title,
            description=job.description,
            skills=job.skills,
            technologies=job.technologies,
            graph=graph,
        ).curriculum_alignment_score
        for job in jobs
    ]
    visual = round(sum(visual_scores) / len(visual_scores), 4)
    cluster_text = normalize_text(" ".join(_job_text(job) for job in jobs))
    big_data_boost = 0.14 if any(term in cluster_text for term in ("spark", "hadoop", "databricks", "snowflake", "lakehouse", "warehouse")) else 0.04
    ai_boost = 0.12 if any(term in cluster_text for term in ("machine learning", "ai", "modelos predictivos", "genai")) else 0.03
    return {
        "Especializacion en Visual Analytics y Big Data": min(round(visual, 4), 1.0),
        "Especializacion en Big Data": min(round(visual + big_data_boost, 4), 1.0),
        "Especializacion en Inteligencia Artificial Aplicada": min(round(visual * 0.58 + ai_boost, 4), 1.0),
    }


def _market_gaps(jobs: list[LaborJobSignal], graph: CurriculumSkillGraph) -> list[dict[str, Any]]:
    curriculum_skills = {node.skill for node in graph.skills}
    skill_counts = Counter(skill for job in jobs for skill in job.skills + job.technologies)
    gaps: list[dict[str, Any]] = []
    for skill, count in skill_counts.most_common(20):
        coverage = 1.0 if skill in curriculum_skills else 0.35 if any(skill in node.related_concepts for node in graph.skills) else 0.0
        if coverage < 0.65:
            gaps.append(
                {
                    "emerging_skill": skill,
                    "gap_score": round((1 - coverage) * min(count / max(len(jobs), 1), 1.0), 4),
                    "curricular_coverage": coverage,
                    "labor_frequency": count,
                }
            )
    return sorted(gaps, key=lambda item: item["gap_score"], reverse=True)


def _trends(jobs: list[LaborJobSignal]) -> list[str]:
    text = normalize_text(" ".join(_job_text(job) for job in jobs))
    return sorted({term for term in EMERGING_TERMS if term in text})


def build_labor_occupational_clusters(jobs: list[LaborJobSignal] | None = None, *, write_outputs: bool = True) -> list[OccupationalCluster]:
    jobs = jobs if jobs is not None else load_valid_jobs_from_results()
    jobs = [job for job in jobs if job.title and job.source_url.startswith(("http://", "https://")) and job.skills]
    graph = load_or_build_curriculum_skill_graph()
    embeddings = embed_texts([_job_text(job) for job in jobs])
    labels = _cluster_labels(jobs, embeddings)
    grouped: dict[int, list[tuple[LaborJobSignal, list[float]]]] = defaultdict(list)
    for job, label, embedding in zip(jobs, labels, embeddings, strict=False):
        grouped[label].append((job, embedding))

    clusters: list[OccupationalCluster] = []
    for cluster_id, (_label, items) in enumerate(sorted(grouped.items(), key=lambda item: item[0]), start=1):
        cluster_jobs = [item[0] for item in items]
        cluster_embeddings = [item[1] for item in items]
        dominant_skills = _dominant(skill for job in cluster_jobs for skill in job.skills)
        dominant_tools = _dominant(tool for job in cluster_jobs for tool in job.tools + job.technologies)
        dominant_roles = _dominant((job.title for job in cluster_jobs), limit=5)
        name = _cluster_name_for_jobs(cluster_jobs)
        trends = _trends(cluster_jobs)
        clusters.append(
            OccupationalCluster(
                id=cluster_id,
                cluster_name=name,
                semantic_summary=f"Cluster {name} basado en {len(cluster_jobs)} vacante(s) verificadas y skills {', '.join(dominant_skills[:5])}.",
                dominant_skills=dominant_skills,
                dominant_tools=dominant_tools,
                dominant_roles=dominant_roles,
                market_frequency=len(cluster_jobs),
                avg_salary_estimate=None,
                growth_signal="emergente" if trends else "estable",
                embedding_centroid=_cosine_centroid(cluster_embeddings),
                jobs=cluster_jobs,
                specialization_affinity=_affinity_scores(cluster_jobs, graph),
                market_gaps=_market_gaps(cluster_jobs, graph),
                trends=trends,
            )
        )
    if write_outputs:
        write_cluster_outputs(clusters)
    return clusters


def write_cluster_outputs(clusters: list[OccupationalCluster]) -> None:
    CLUSTERS_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(cluster) for cluster in clusters]
    CLUSTERS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = ["# Labor Occupational Clusters Report", ""]
    if not clusters:
        lines.append("No hay vacantes `job_posting` validas para clusterizar. Las paginas de taxonomia/listado fueron excluidas.")
    for cluster in clusters:
        lines.extend(
            [
                f"## {cluster.cluster_name}",
                "",
                f"- Frecuencia: {cluster.market_frequency}",
                f"- Growth signal: {cluster.growth_signal}",
                f"- Skills dominantes: {', '.join(cluster.dominant_skills) or 'N/A'}",
                f"- Herramientas dominantes: {', '.join(cluster.dominant_tools) or 'N/A'}",
                f"- Roles dominantes: {', '.join(cluster.dominant_roles) or 'N/A'}",
                f"- Resumen: {cluster.semantic_summary}",
                "",
            ]
        )
    CLUSTERS_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    affinity_lines = ["# Curriculum Affinity Report", ""]
    for cluster in clusters:
        affinity_lines.append(f"## {cluster.cluster_name}")
        affinity_lines.extend([f"- {name}: {score}" for name, score in cluster.specialization_affinity.items()])
        affinity_lines.append("")
    if not clusters:
        affinity_lines.append("Sin clusters validos para calcular afinidad curricular.")
    AFFINITY_REPORT.write_text("\n".join(affinity_lines) + "\n", encoding="utf-8")

    gap_lines = ["# Market Gap Intelligence Report", ""]
    for cluster in clusters:
        gap_lines.append(f"## {cluster.cluster_name}")
        gap_lines.extend(
            [
                f"- {gap['emerging_skill']}: gap={gap['gap_score']} coverage={gap['curricular_coverage']} freq={gap['labor_frequency']}"
                for gap in cluster.market_gaps
            ]
            or ["- Sin gaps relevantes."]
        )
        gap_lines.extend([f"- Tendencia: {trend}" for trend in cluster.trends])
        gap_lines.append("")
    if not clusters:
        gap_lines.append("Sin evidencia Gold/job_posting para gaps de mercado.")
    GAPS_REPORT.write_text("\n".join(gap_lines) + "\n", encoding="utf-8")


def cluster_to_dict(cluster: OccupationalCluster) -> dict[str, Any]:
    return asdict(cluster)


if __name__ == "__main__":
    clusters = build_labor_occupational_clusters()
    print(json.dumps({"clusters": len(clusters), "output": str(CLUSTERS_JSON)}, indent=2, ensure_ascii=False))
