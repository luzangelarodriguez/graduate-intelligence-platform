from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.curriculum.specialization_curriculum_graph_engine import build_specialization_curriculum_graph
from ml.curriculum.specialization_skill_affinity_engine import calculate_skill_affinity
from ml.labor.labor_market_skill_extraction_engine import LaborSkillEvidence, build_labor_market_skill_universe
from ml.labor.occupational_skill_cluster_engine import build_occupational_skill_clusters, classify_skill_cluster
from scrapers.normalization.visual_analytics_skill_taxonomy import normalize_text
from scrapers.normalization.visual_analytics_skill_taxonomy import SKILL_DEFINITIONS as LEGACY_SKILL_DEFINITIONS

REPORT_PATH = ROOT_DIR / "outputs" / "visual_analytics_market_skill_intelligence.md"
JSON_PATH = ROOT_DIR / "outputs" / "visual_analytics_market_skill_intelligence.json"
RECALL_REPORT_PATH = ROOT_DIR / "outputs" / "market_skill_extraction_recall_report.md"

MARKET_EVIDENCE_WEIGHTS = {
    "gold_job_posting": 1.0,
    "silver_job_posting": 0.8,
    "bronze_job_posting": 0.5,
    "portal_taxonomy": 0.1,
    "legacy_empleo_skill": 0.6,
}

EMERGING_SKILLS = {
    "Microsoft Fabric",
    "Azure Synapse",
    "Databricks",
    "DataOps",
    "GenAI Analytics",
    "Copilot BI",
    "Cloud Analytics",
    "Snowflake",
    "BigQuery",
    "MLOps",
    "data governance",
}

SUPPORTING_SKILLS = {
    "communication",
    "comunicacion",
    "work in team",
    "trabajo en equipo",
    "problem solving",
    "resolucion de problemas",
    "leadership",
    "liderazgo",
    "english",
    "ingles",
    "agile",
    "scrum",
    "kanban",
    "stakeholder management",
    "gestion de stakeholders",
    "presentation",
    "executive reporting",
    "reporting",
    "kpis",
    "bi",
    "power bi",
    "tableau",
    "qlik",
    "aws",
    "azure",
    "gcp",
    "postgresql",
    "mysql",
    "nosql",
    "sql server",
    "oracle",
    "spark",
    "hadoop",
    "etl",
    "elt",
    "api",
    "llm",
    "rag",
    "copilot bi",
    "mlflow",
    "pandas",
    "scikit learn",
    "kafka",
    "ssis",
    "pl/sql",
}


@dataclass(frozen=True)
class MarketSkillSignal:
    skill: str
    skill_type: str
    occupational_cluster: str
    market_weight: float
    evidence_count: int
    evidence_sources: dict[str, int]
    market_signal_confidence: str
    coverage_status: str
    affinity_score: float
    matched_curriculum_skill: str | None
    roles: list[str]
    companies: list[str]
    source_urls: list[str]
    recommendation: str
    reason: str


@dataclass(frozen=True)
class MarketSkillIntelligenceMap:
    specialization_id: str
    specialization_name: str
    market_skills: list[MarketSkillSignal]
    covered_skills: list[MarketSkillSignal]
    partial_skills: list[MarketSkillSignal]
    missing_skills: list[MarketSkillSignal]
    emerging_skills: list[MarketSkillSignal]
    irrelevant_skills: list[MarketSkillSignal]
    occupational_clusters: list[dict[str, Any]]
    curriculum_gaps: list[MarketSkillSignal]
    recommended_updates: list[dict[str, Any]]


def _weighted_score(evidence: list[LaborSkillEvidence]) -> float:
    return round(sum(MARKET_EVIDENCE_WEIGHTS.get(item.evidence_source, item.evidence_weight) for item in evidence), 4)


def _confidence(score: float, sources: dict[str, int], skill: str) -> str:
    if sources.get("gold_job_posting"):
        return "high"
    if sources.get("silver_job_posting") and score >= 1.2:
        return "high"
    if sources.get("silver_job_posting") or sources.get("legacy_empleo_skill"):
        return "medium"
    if skill in EMERGING_SKILLS and score >= 0.5:
        return "emerging"
    return "weak"


def _coverage_status(skill: str, affinity_status: str, market_confidence: str, cluster_name: str) -> str:
    if affinity_status == "covered":
        return "covered"
    if affinity_status == "partial":
        return "partial"
    if affinity_status == "irrelevant":
        normalized_skill = normalize_text(skill).strip()
        if normalized_skill in SUPPORTING_SKILLS:
            return "partial"
        return "irrelevant"
    if (skill in EMERGING_SKILLS or cluster_name in {"Cloud Analytics", "DataOps", "GenAI Analytics"}) and market_confidence in {"high", "medium", "emerging"}:
        return "emerging"
    normalized_skill = normalize_text(skill).strip()
    if normalized_skill in SUPPORTING_SKILLS:
        return "partial"
    if market_confidence in {"high", "medium"}:
        return "missing"
    return "irrelevant"


def _recommendation(skill: str, status: str, cluster_name: str, confidence: str) -> str:
    if status == "covered":
        return "Mantener cobertura curricular y fortalecer evidencia evaluable si el mercado confirma frecuencia alta."
    if status == "partial":
        return f"Profundizar {skill} como capacidad aplicada dentro del cluster {cluster_name}."
    if status == "emerging":
        return f"Analizar incorporacion de {skill} como skill emergente con señal {confidence} en {cluster_name}."
    if status == "missing":
        return f"Evaluar incorporacion curricular de {skill} por demanda laboral no cubierta en {cluster_name}."
    return "No priorizar curricularmente por baja afinidad o evidencia debil."


def build_market_skill_intelligence_map(*, include_database: bool = True, write_output: bool = True) -> MarketSkillIntelligenceMap:
    graph = build_specialization_curriculum_graph(write_output=True)
    base_universe = build_labor_market_skill_universe(include_database=include_database, write_output=True)
    clusters = build_occupational_skill_clusters(base_universe, write_output=True)
    cluster_payload = [asdict(item) for item in clusters]

    signals: list[MarketSkillSignal] = []
    for item in base_universe:
        sources = Counter(evidence.evidence_source for evidence in item.evidence)
        weight = _weighted_score(item.evidence)
        cluster_name = classify_skill_cluster(item.skill)
        confidence = _confidence(weight, dict(sources), item.skill)
        affinity = calculate_skill_affinity(item.skill, graph)
        status = _coverage_status(item.skill, affinity.coverage_status, confidence, cluster_name)
        signals.append(
            MarketSkillSignal(
                skill=item.skill,
                skill_type=item.skill_type,
                occupational_cluster=cluster_name,
                market_weight=weight,
                evidence_count=item.evidence_count,
                evidence_sources=dict(sorted(sources.items())),
                market_signal_confidence=confidence,
                coverage_status=status,
                affinity_score=affinity.affinity_score,
                matched_curriculum_skill=affinity.matched_curriculum_skill,
                roles=item.roles,
                companies=item.companies,
                source_urls=item.source_urls,
                recommendation=_recommendation(item.skill, status, cluster_name, confidence),
                reason=affinity.reason,
            )
        )

    signals = sorted(signals, key=lambda row: (row.market_weight, row.affinity_score, row.evidence_count), reverse=True)
    buckets: dict[str, list[MarketSkillSignal]] = defaultdict(list)
    for signal in signals:
        buckets[signal.coverage_status].append(signal)

    gaps = [*buckets["missing"], *buckets["emerging"], *buckets["partial"]]
    updates = [
        {
            "skill": item.skill,
            "cluster_name": item.occupational_cluster,
            "priority": "alta" if item.market_signal_confidence in {"high", "emerging"} else "media",
            "market_signal_confidence": item.market_signal_confidence,
            "market_weight": item.market_weight,
            "action": item.recommendation,
            "roles": item.roles[:5],
        }
        for item in gaps
        if item.coverage_status in {"missing", "emerging", "partial"}
    ][:20]

    intelligence = MarketSkillIntelligenceMap(
        specialization_id=graph.specialization_id,
        specialization_name=graph.specialization_name,
        market_skills=signals,
        covered_skills=buckets["covered"],
        partial_skills=buckets["partial"],
        missing_skills=buckets["missing"],
        emerging_skills=buckets["emerging"],
        irrelevant_skills=buckets["irrelevant"],
        occupational_clusters=cluster_payload,
        curriculum_gaps=gaps,
        recommended_updates=updates,
    )
    if write_output:
        write_market_skill_intelligence_outputs(intelligence)
    return intelligence


def market_skill_intelligence_to_dict(intelligence: MarketSkillIntelligenceMap) -> dict[str, Any]:
    return asdict(intelligence)


def write_market_skill_intelligence_outputs(intelligence: MarketSkillIntelligenceMap) -> None:
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    previous_skills: set[str] = set()
    if JSON_PATH.exists():
        try:
            previous_payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
            previous_skills = {str(item.get("skill")) for item in previous_payload.get("market_skills", []) if item.get("skill")}
        except Exception:
            previous_skills = set()
    JSON_PATH.write_text(json.dumps(market_skill_intelligence_to_dict(intelligence), indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Visual Analytics Market Skill Intelligence",
        "",
        f"- Especializacion: {intelligence.specialization_name}",
        f"- Skills mercado: {len(intelligence.market_skills)}",
        f"- Covered: {len(intelligence.covered_skills)}",
        f"- Partial: {len(intelligence.partial_skills)}",
        f"- Missing: {len(intelligence.missing_skills)}",
        f"- Emerging: {len(intelligence.emerging_skills)}",
        f"- Irrelevant: {len(intelligence.irrelevant_skills)}",
        "",
        "## Top market skills",
        "",
    ]
    for item in intelligence.market_skills[:30]:
        lines.extend(
            [
                f"### {item.skill}",
                f"- Cluster: {item.occupational_cluster}",
                f"- Market weight: {item.market_weight}",
                f"- Market signal confidence: {item.market_signal_confidence}",
                f"- Coverage curricular: {item.coverage_status}",
                f"- Evidence sources: {json.dumps(item.evidence_sources, ensure_ascii=False)}",
                f"- Roles asociados: {', '.join(item.roles[:5]) or 'sin cargo asociado'}",
                f"- Afinidad: {item.affinity_score}",
                f"- Recomendacion: {item.recommendation}",
                "",
            ]
        )
    lines.extend(["## Missing skills", ""])
    lines.extend([f"- {item.skill} ({item.occupational_cluster}, weight={item.market_weight})" for item in intelligence.missing_skills] or ["- Sin missing skills con señal media/alta."])
    lines.extend(["", "## Emerging skills", ""])
    lines.extend([f"- {item.skill} ({item.occupational_cluster}, signal={item.market_signal_confidence})" for item in intelligence.emerging_skills] or ["- Sin emerging skills con evidencia suficiente."])
    lines.extend(["", "## Recommended updates", ""])
    lines.extend([f"- {item['action']}" for item in intelligence.recommended_updates] or ["- Sin recomendaciones nuevas con evidencia suficiente."])
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    current_skills = {item.skill for item in intelligence.market_skills}
    legacy_baseline = current_skills & set(LEGACY_SKILL_DEFINITIONS)
    baseline_skills = legacy_baseline or previous_skills
    new_skills = sorted(current_skills - baseline_skills)
    recall_lines = [
        "# Market Skill Extraction Recall Report",
        "",
        f"- Skills antes: {len(baseline_skills)}",
        f"- Skills despues: {len(current_skills)}",
        f"- Nuevas skills detectadas: {len(new_skills)}",
        f"- Referencia anterior: extractor base Visual Analytics ({len(legacy_baseline)} skills presentes en la taxonomia base).",
        "",
        "## Nuevas skills detectadas",
        "",
    ]
    by_skill = {item.skill: item for item in intelligence.market_skills}
    for skill in new_skills[:80]:
        item = by_skill[skill]
        recall_lines.extend(
            [
                f"### {skill}",
                f"- Cluster: {item.occupational_cluster}",
                f"- Fuente: {json.dumps(item.evidence_sources, ensure_ascii=False)}",
                f"- Confidence: {item.market_signal_confidence}",
                f"- Clasificacion curricular: {item.coverage_status}",
                f"- Roles: {', '.join(item.roles[:5]) or 'sin cargo asociado'}",
                "",
            ]
        )
    if not new_skills:
        recall_lines.append("- No se detectaron skills nuevas frente al reporte anterior.")
    RECALL_REPORT_PATH.write_text("\n".join(recall_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    result = build_market_skill_intelligence_map()
    print(
        json.dumps(
            {
                "market_skills": len(result.market_skills),
                "covered": len(result.covered_skills),
                "partial": len(result.partial_skills),
                "missing": len(result.missing_skills),
                "emerging": len(result.emerging_skills),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
