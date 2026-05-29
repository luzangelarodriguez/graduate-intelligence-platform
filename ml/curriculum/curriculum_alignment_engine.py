from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from microcurriculum_engine.ingestion.document_loader import extract_text  # noqa: E402
from scrapers.normalization.visual_analytics_skill_taxonomy import (  # noqa: E402
    SKILL_DEFINITIONS,
    extract_visual_analytics_skills,
    normalize_text,
    normalize_visual_analytics_skill,
)

CURRICULUM_ROOT = ROOT_DIR / "storage" / "test_microcurriculos" / "especialización en visual analytics y big data"
GRAPH_PATH = ROOT_DIR / "ml" / "datasets" / "curriculum_skill_graph.json"
REPORT_PATH = ROOT_DIR / "outputs" / "curriculum_alignment_engine_report.md"

RELATED_SKILL_EXPANSION: dict[str, tuple[str, ...]] = {
    "Power BI": ("dashboarding", "reporting", "KPIs", "visualizacion analitica", "storytelling with data", "Microsoft Fabric"),
    "SQL": ("ETL", "data warehouse", "queries", "pipelines", "data quality", "data integration"),
    "Python": ("pandas", "analytics", "machine learning", "notebooks", "modelos predictivos", "MLOps"),
    "R": ("estadistica", "analytics", "visualizacion analitica", "modelos predictivos"),
    "BI": ("business intelligence", "reporting", "KPIs", "dashboarding", "analitica empresarial"),
    "dashboarding": ("reporting", "KPIs", "visualizacion analitica", "storytelling with data"),
    "visualizacion analitica": ("dashboarding", "Tableau", "Power BI", "storytelling with data"),
    "data warehouse": ("ETL", "SQL", "pipelines", "data lake", "lakehouse"),
    "data lake": ("lakehouse", "Spark", "Databricks", "cloud analytics"),
    "machine learning": ("Python", "notebooks", "scikit learn", "modelos predictivos", "MLOps"),
    "Azure Data": ("Azure Synapse", "Microsoft Fabric", "cloud analytics", "Databricks"),
    "AWS Analytics": ("Redshift", "AWS Glue", "cloud analytics", "data lake"),
    "Google Cloud Analytics": ("BigQuery", "Looker", "cloud analytics"),
    "data governance": ("data quality", "linaje", "seguridad del dato", "gobierno de datos"),
    "ETL": ("pipelines", "data warehouse", "data integration", "DataOps"),
}

MARKET_GAP_TERMS = {
    "Azure Synapse",
    "Microsoft Fabric",
    "DataOps",
    "data governance",
    "Databricks",
    "Snowflake",
    "GenAI analytics",
    "MLOps",
    "lakehouse",
    "BigQuery",
    "data quality",
}

HYBRID_CURRICULUM_ROLES = {
    "data platform engineer",
    "analytics engineer",
    "bi backend developer",
    "cloud analytics engineer",
    "reporting developer",
    "etl specialist",
    "azure data engineer",
    "data integration engineer",
    "insights analyst",
    "kpi analyst",
    "business reporting analyst",
}


@dataclass(frozen=True)
class CurriculumSkillNode:
    skill: str
    aliases: list[str]
    semantic_cluster: str
    frequency: int
    curricular_importance: float
    related_tools: list[str]
    related_concepts: list[str]


@dataclass(frozen=True)
class CurriculumSkillGraph:
    source_path: str
    documents_processed: int
    skills: list[CurriculumSkillNode]
    concept_frequency: dict[str, int]


@dataclass(frozen=True)
class CurriculumAlignmentResult:
    curriculum_alignment_score: float
    shared_skills: list[str]
    shared_tools: list[str]
    related_matches: dict[str, list[str]]
    semantic_overlap_score: float
    direct_overlap_score: float
    related_overlap_score: float
    market_gap_signal: list[str]
    role_curriculum_fit: float
    explanation: str


def supported_documents(root: Path = CURRICULUM_ROOT) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.suffix.lower() in {".pdf", ".docx", ".txt"})


def _skill_cluster(skill: str) -> str:
    skill_type = str(SKILL_DEFINITIONS.get(skill, {}).get("type", "technical_skill"))
    if skill in {"Power BI", "Tableau", "dashboarding", "visualizacion analitica", "storytelling with data"}:
        return "visualization"
    if skill in {"BI", "KPIs"}:
        return "business_intelligence"
    if skill in {"SQL", "ETL", "data warehouse", "data lake", "lakehouse", "Spark", "Hadoop", "Databricks", "Snowflake"}:
        return "data_engineering"
    if skill in {"Azure Data", "AWS Analytics", "Google Cloud Analytics"}:
        return "cloud_data"
    if skill in {"AI", "machine learning", "MLOps"}:
        return "ai_analytics"
    if skill in {"data governance", "data quality"}:
        return "governance"
    return skill_type


def _aliases_for(skill: str) -> list[str]:
    aliases = SKILL_DEFINITIONS.get(skill, {}).get("aliases", ())
    values = [str(alias) for alias in aliases]
    values.extend(RELATED_SKILL_EXPANSION.get(skill, ()))
    return sorted({value for value in values if value})


def _extract_concepts(text: str) -> Counter[str]:
    normalized = normalize_text(text)
    concepts = Counter()
    for concept in {
        "resultados de aprendizaje",
        "visualizacion",
        "business intelligence",
        "tableros",
        "indicadores",
        "toma de decisiones",
        "bases de datos",
        "mineria de datos",
        "modelos predictivos",
        "gobierno de datos",
        "calidad de datos",
        "procesamiento masivo",
        "proyectos bi",
        "analitica descriptiva",
        "analitica predictiva",
    }:
        count = normalized.count(normalize_text(concept))
        if count:
            concepts[concept] += count
    return concepts


def build_curriculum_skill_graph(root: Path = CURRICULUM_ROOT, *, write: bool = True) -> CurriculumSkillGraph:
    skill_counts: Counter[str] = Counter()
    concept_counts: Counter[str] = Counter()
    docs = supported_documents(root)
    for path in docs:
        raw_text, _method = extract_text(path)
        text = raw_text or ""
        concept_counts.update(_extract_concepts(text))
        for skill in extract_visual_analytics_skills(text):
            skill_counts[skill.normalized] += 1

    if not skill_counts:
        for fallback in ("Power BI", "SQL", "dashboarding", "BI", "KPIs", "visualizacion analitica"):
            skill_counts[fallback] += 1

    doc_count = max(len(docs), 1)
    nodes: list[CurriculumSkillNode] = []
    for skill, frequency in sorted(skill_counts.items(), key=lambda item: (-item[1], item[0])):
        related = list(RELATED_SKILL_EXPANSION.get(skill, ()))
        importance = min(0.35 + (frequency / doc_count) * 0.45 + (0.15 if skill in {"Power BI", "SQL", "BI", "dashboarding"} else 0.05), 1.0)
        nodes.append(
            CurriculumSkillNode(
                skill=skill,
                aliases=_aliases_for(skill),
                semantic_cluster=_skill_cluster(skill),
                frequency=frequency,
                curricular_importance=round(importance, 4),
                related_tools=sorted({item for item in related if item in SKILL_DEFINITIONS or item in {"Microsoft Fabric", "Azure Synapse", "BigQuery"}}),
                related_concepts=sorted(set(related)),
            )
        )
    graph = CurriculumSkillGraph(
        source_path=str(root),
        documents_processed=len(docs),
        skills=nodes,
        concept_frequency=dict(concept_counts.most_common(40)),
    )
    if write:
        GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
        GRAPH_PATH.write_text(json.dumps(asdict(graph), indent=2, ensure_ascii=False), encoding="utf-8")
    return graph


def load_or_build_curriculum_skill_graph(root: Path = CURRICULUM_ROOT) -> CurriculumSkillGraph:
    if GRAPH_PATH.exists():
        try:
            payload = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
            if payload.get("source_path") == str(root):
                return CurriculumSkillGraph(
                    source_path=str(payload.get("source_path", root)),
                    documents_processed=int(payload.get("documents_processed", 0)),
                    skills=[CurriculumSkillNode(**item) for item in payload.get("skills", [])],
                    concept_frequency={str(k): int(v) for k, v in payload.get("concept_frequency", {}).items()},
                )
        except Exception:
            pass
    return build_curriculum_skill_graph(root)


def _contains(text: str, term: str) -> bool:
    return f" {normalize_text(term)} " in f" {normalize_text(text)} "


def _semantic_overlap(job_text: str, curriculum_terms: Iterable[str]) -> float:
    target = " ".join(sorted({normalize_text(term) for term in curriculum_terms if term}))
    normalized_job = normalize_text(job_text)
    if not normalized_job or not target:
        return 0.0
    job_tokens = set(normalized_job.split())
    target_tokens = set(target.split())
    token_overlap = len(job_tokens & target_tokens) / max(len(target_tokens), 1)
    sequence = SequenceMatcher(None, normalized_job[:2400], target[:2400]).ratio() * 0.35
    return round(min(max(token_overlap, sequence), 1.0), 4)


def score_curriculum_alignment(
    *,
    title: str,
    description: str,
    skills: Iterable[str] = (),
    technologies: Iterable[str] = (),
    graph: CurriculumSkillGraph | None = None,
    document_type: str = "job_posting",
    evidence_source_type: str = "job_evidence",
    is_real_job_posting: bool = True,
) -> CurriculumAlignmentResult:
    if document_type != "job_posting" or evidence_source_type != "job_evidence" or not is_real_job_posting:
        return CurriculumAlignmentResult(
            curriculum_alignment_score=0.0,
            shared_skills=[],
            shared_tools=[],
            related_matches={},
            semantic_overlap_score=0.0,
            direct_overlap_score=0.0,
            related_overlap_score=0.0,
            market_gap_signal=[],
            role_curriculum_fit=0.0,
            explanation="No se usa para alineacion curricular porque el documento no es una vacante laboral real.",
        )
    graph = graph or load_or_build_curriculum_skill_graph()
    job_text = " ".join([title, description, " ".join(skills), " ".join(technologies)])
    job_skills = {skill.normalized for skill in extract_visual_analytics_skills(job_text)}
    job_skills.update(normalize_visual_analytics_skill(skill) for skill in skills if skill)

    curriculum_skills = {node.skill for node in graph.skills}
    curriculum_terms = set(curriculum_skills)
    for node in graph.skills:
        curriculum_terms.update(node.aliases)
        curriculum_terms.update(node.related_concepts)

    shared_skills = sorted(job_skills & curriculum_skills)
    shared_tools = sorted(skill for skill in shared_skills if SKILL_DEFINITIONS.get(skill, {}).get("type") in {"tool", "platform", "cloud", "language", "methodology"})

    related_matches: dict[str, list[str]] = defaultdict(list)
    for node in graph.skills:
        for related in RELATED_SKILL_EXPANSION.get(node.skill, ()):
            if _contains(job_text, related) or normalize_visual_analytics_skill(related) in job_skills:
                related_matches[node.skill].append(related)

    market_gap_signal = sorted(
        term
        for term in MARKET_GAP_TERMS
        if (_contains(job_text, term) or normalize_visual_analytics_skill(term) in job_skills)
        and normalize_visual_analytics_skill(term) not in curriculum_skills
    )

    weighted_direct = sum(node.curricular_importance for node in graph.skills if node.skill in shared_skills)
    max_weight = sum(node.curricular_importance for node in graph.skills) or 1.0
    direct_overlap_score = min(weighted_direct / max_weight * 1.9, 1.0)
    related_overlap_score = min(sum(len(values) for values in related_matches.values()) / 8, 1.0)
    semantic_overlap_score = _semantic_overlap(job_text, curriculum_terms)
    role_curriculum_fit = 0.78 if any(_contains(f"{title} {description}", role) for role in HYBRID_CURRICULUM_ROLES) else 0.42
    if shared_skills or related_matches:
        role_curriculum_fit = max(role_curriculum_fit, 0.72)

    score = (
        direct_overlap_score * 0.40
        + related_overlap_score * 0.24
        + semantic_overlap_score * 0.18
        + (len(shared_tools) / max(len(shared_skills), 1) if shared_skills else 0.0) * 0.10
        + role_curriculum_fit * 0.08
    )
    score = round(min(score, 1.0), 4)
    explanation_parts = []
    if shared_skills:
        explanation_parts.append("comparte " + ", ".join(shared_skills[:8]))
    if related_matches:
        expanded = [item for values in related_matches.values() for item in values]
        explanation_parts.append("extiende el curriculo hacia " + ", ".join(sorted(set(expanded))[:8]))
    if market_gap_signal:
        explanation_parts.append("senala gaps de mercado como " + ", ".join(market_gap_signal[:6]))
    explanation = "Alineada porque " + "; ".join(explanation_parts) + "." if explanation_parts else "No se encontro evidencia curricular suficiente para alinear la vacante."

    return CurriculumAlignmentResult(
        curriculum_alignment_score=score,
        shared_skills=shared_skills,
        shared_tools=shared_tools,
        related_matches={key: sorted(set(values)) for key, values in related_matches.items()},
        semantic_overlap_score=round(semantic_overlap_score, 4),
        direct_overlap_score=round(direct_overlap_score, 4),
        related_overlap_score=round(related_overlap_score, 4),
        market_gap_signal=market_gap_signal,
        role_curriculum_fit=round(role_curriculum_fit, 4),
        explanation=explanation,
    )


def compute_gold_score(
    *,
    semantic_market_relevance: float,
    curriculum_alignment_score: float,
    contextual_evidence_score: float,
    quality_score: float = 0.85,
) -> float:
    return round(
        min(
            semantic_market_relevance * 0.35
            + curriculum_alignment_score * 0.40
            + contextual_evidence_score * 0.15
            + quality_score * 0.10,
            1.0,
        ),
        4,
    )


def curriculum_gold_tier(gold_score: float, curriculum_alignment_score: float) -> str:
    if gold_score >= 0.80 and curriculum_alignment_score >= 0.70:
        return "Gold A"
    if gold_score >= 0.65 and curriculum_alignment_score >= 0.50:
        return "Gold B"
    if gold_score >= 0.50:
        return "Silver"
    return "Rejected"


def write_curriculum_alignment_report(graph: CurriculumSkillGraph | None = None, samples: list[CurriculumAlignmentResult] | None = None) -> Path:
    graph = graph or load_or_build_curriculum_skill_graph()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Curriculum Alignment Engine Report",
        "",
        f"- Fuente curricular: `{graph.source_path}`",
        f"- Documentos procesados: {graph.documents_processed}",
        f"- Skills/conceptos curriculares indexados: {len(graph.skills)}",
        "",
        "## Curriculum Skill Graph",
    ]
    for node in graph.skills[:30]:
        lines.append(f"- {node.skill} | cluster={node.semantic_cluster} | frecuencia={node.frequency} | importancia={node.curricular_importance}")
    lines.extend(["", "## Conceptos Pedagogicos Frecuentes"])
    lines.extend([f"- {concept}: {count}" for concept, count in graph.concept_frequency.items()] or ["- Sin conceptos detectados."])
    if samples:
        lines.extend(["", "## Validaciones de Alineacion"])
        for sample in samples:
            lines.extend(
                [
                    f"- Score curricular: {sample.curriculum_alignment_score}",
                    f"  - Skills compartidas: {', '.join(sample.shared_skills) or 'ninguna'}",
                    f"  - Gaps mercado: {', '.join(sample.market_gap_signal) or 'ninguno'}",
                    f"  - Explicacion: {sample.explanation}",
                ]
            )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REPORT_PATH


def result_to_dict(result: CurriculumAlignmentResult) -> dict[str, object]:
    return asdict(result)
