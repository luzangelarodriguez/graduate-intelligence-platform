from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class CurriculumClusterRecommendation:
    cluster_name: str
    recommendation_type: str
    suggested_module: str
    curricular_action: str
    new_competencies: list[str]
    suggested_tools: list[str]
    learning_outcomes: list[str]
    rationale: str
    evidence: str
    priority: str


def recommendations_from_cluster(cluster: Any) -> list[CurriculumClusterRecommendation]:
    cluster_name = getattr(cluster, "cluster_name", "") or cluster.get("cluster_name", "")
    gaps = getattr(cluster, "market_gaps", None) or cluster.get("market_gaps", [])
    dominant = getattr(cluster, "dominant_skills", None) or cluster.get("dominant_skills", [])
    gap_skills = [str(item.get("emerging_skill")) for item in gaps[:5] if item.get("emerging_skill")]
    tools = sorted(set(gap_skills + [str(skill) for skill in dominant[:4]]))
    if not tools:
        tools = ["Power BI", "SQL", "KPIs"]
    module = {
        "Cloud Analytics": "Laboratorio de cloud analytics y plataformas modernas de datos",
        "Data Engineering": "Modulo aplicado de pipelines, data warehouse y lakehouse",
        "BI & Visualization": "Taller de visual analytics, dashboards y storytelling ejecutivo",
        "AI Analytics": "Modulo de modelos predictivos y analitica aumentada",
        "Data Governance": "Modulo de gobierno, calidad y linaje de datos",
    }.get(cluster_name, "Seminario de inteligencia laboral aplicada a analitica")
    return [
        CurriculumClusterRecommendation(
            cluster_name=cluster_name,
            recommendation_type="cluster_curriculum_evolution",
            suggested_module=module,
            curricular_action=(
                f"Actualizar el microcurriculo con una experiencia aplicada de {module.lower()} "
                "con productos evaluables, evidencia laboral y trazabilidad de competencias."
            ),
            new_competencies=[
                f"Aplicar {tool} en escenarios reales de analitica institucional." for tool in tools[:3]
            ],
            suggested_tools=tools,
            learning_outcomes=[
                "Diseñar soluciones analiticas trazables a partir de requerimientos de negocio.",
                "Evaluar brechas entre demanda laboral y cobertura curricular usando evidencia verificable.",
            ],
            rationale=f"El cluster {cluster_name} evidencia demanda relacionada con {', '.join(tools[:5])}.",
            evidence=f"Skills dominantes: {', '.join(dominant[:5])}. Gaps detectados: {', '.join(gap_skills[:5]) or 'sin gaps criticos'}.",
            priority="alta" if gaps else "media",
        )
    ]


def recommendations_to_dict(items: list[CurriculumClusterRecommendation]) -> list[dict[str, Any]]:
    return [asdict(item) for item in items]
