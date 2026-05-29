from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.curriculum.specialization_curriculum_graph_engine import build_specialization_curriculum_graph
from ml.curriculum.specialization_skill_affinity_engine import SkillAffinityResult, calculate_skill_affinity
from ml.labor.labor_market_skill_extraction_engine import LaborMarketSkill, build_labor_market_skill_universe
from ml.labor.occupational_skill_cluster_engine import OccupationalSkillCluster, build_occupational_skill_clusters

REPORT_PATH = ROOT_DIR / "outputs" / "visual_analytics_curriculum_market_gap_map.md"
JSON_PATH = ROOT_DIR / "outputs" / "visual_analytics_curriculum_market_gap_map.json"
EMERGING_CLUSTERS = {"Cloud Analytics", "DataOps", "GenAI Analytics", "AI Analytics", "Data Governance"}


@dataclass(frozen=True)
class CurriculumMarketGapItem:
    skill: str
    cluster_name: str
    coverage_status: str
    evidence_weight: float
    evidence_sources: dict[str, int]
    affinity_score: float
    matched_curriculum_skill: str | None
    roles: list[str]
    recommendation: str
    reason: str


@dataclass(frozen=True)
class CurriculumMarketGapMap:
    specialization_id: str
    specialization_name: str
    covered_skills: list[CurriculumMarketGapItem]
    partial_skills: list[CurriculumMarketGapItem]
    missing_skills: list[CurriculumMarketGapItem]
    emerging_skills: list[CurriculumMarketGapItem]
    irrelevant_skills: list[CurriculumMarketGapItem]
    occupational_clusters: list[OccupationalSkillCluster]
    recommended_curriculum_updates: list[dict[str, Any]]


def _coverage_status(skill: LaborMarketSkill, affinity: SkillAffinityResult) -> str:
    if affinity.coverage_status == "covered":
        return "covered"
    if affinity.coverage_status == "partial":
        return "partial"
    if affinity.coverage_status == "irrelevant":
        return "irrelevant"
    has_strong_market = skill.total_weight >= 0.7 or any(
        source in skill.source_breakdown for source in ("gold_job_posting", "silver_job_posting", "legacy_empleo_skill")
    )
    if affinity.cluster_name in EMERGING_CLUSTERS and has_strong_market:
        return "emerging"
    return "missing" if has_strong_market else "irrelevant"


def _recommendation(skill: LaborMarketSkill, status: str, cluster_name: str) -> str:
    if status == "covered":
        return "Mantener la evidencia curricular y documentar productos evaluables asociados."
    if status == "partial":
        return f"Profundizar {skill.skill} mediante actividades aplicadas vinculadas a {cluster_name}."
    if status == "emerging":
        return f"Evaluar incorporacion gradual de {skill.skill} como competencia emergente del cluster {cluster_name}."
    if status == "missing":
        return f"Incorporar evidencia curricular de {skill.skill} si se confirma demanda laboral recurrente."
    return "Excluir de recomendaciones curriculares por baja afinidad con la especializacion."


def build_curriculum_market_gap_map(
    *,
    universe: list[LaborMarketSkill] | None = None,
    write_output: bool = True,
) -> CurriculumMarketGapMap:
    graph = build_specialization_curriculum_graph(write_output=True)
    universe = universe if universe is not None else build_labor_market_skill_universe(write_output=True)
    clusters = build_occupational_skill_clusters(universe, write_output=True)

    buckets: dict[str, list[CurriculumMarketGapItem]] = {
        "covered": [],
        "partial": [],
        "missing": [],
        "emerging": [],
        "irrelevant": [],
    }
    for skill in universe:
        affinity = calculate_skill_affinity(skill.skill, graph)
        status = _coverage_status(skill, affinity)
        item = CurriculumMarketGapItem(
            skill=skill.skill,
            cluster_name=affinity.cluster_name,
            coverage_status=status,
            evidence_weight=skill.total_weight,
            evidence_sources=skill.source_breakdown,
            affinity_score=affinity.affinity_score,
            matched_curriculum_skill=affinity.matched_curriculum_skill,
            roles=skill.roles,
            recommendation=_recommendation(skill, status, affinity.cluster_name),
            reason=affinity.reason,
        )
        buckets[status].append(item)

    for values in buckets.values():
        values.sort(key=lambda item: (item.evidence_weight, item.affinity_score), reverse=True)

    updates = [
        {
            "skill": item.skill,
            "cluster_name": item.cluster_name,
            "priority": "alta" if item.coverage_status == "emerging" and item.evidence_weight >= 1 else "media",
            "action": item.recommendation,
            "evidence_weight": item.evidence_weight,
            "roles": item.roles[:5],
        }
        for item in [*buckets["emerging"], *buckets["missing"], *buckets["partial"]]
        if item.coverage_status != "irrelevant"
    ][:15]

    gap_map = CurriculumMarketGapMap(
        specialization_id=graph.specialization_id,
        specialization_name=graph.specialization_name,
        covered_skills=buckets["covered"],
        partial_skills=buckets["partial"],
        missing_skills=buckets["missing"],
        emerging_skills=buckets["emerging"],
        irrelevant_skills=buckets["irrelevant"],
        occupational_clusters=clusters,
        recommended_curriculum_updates=updates,
    )
    if write_output:
        write_gap_map_outputs(gap_map)
    return gap_map


def gap_map_to_dict(gap_map: CurriculumMarketGapMap) -> dict[str, Any]:
    return asdict(gap_map)


def write_gap_map_outputs(gap_map: CurriculumMarketGapMap) -> None:
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = gap_map_to_dict(gap_map)
    JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Visual Analytics Curriculum Market Gap Map",
        "",
        f"- Especializacion: {gap_map.specialization_name}",
        f"- Covered: {len(gap_map.covered_skills)}",
        f"- Partial: {len(gap_map.partial_skills)}",
        f"- Missing: {len(gap_map.missing_skills)}",
        f"- Emerging: {len(gap_map.emerging_skills)}",
        f"- Irrelevant: {len(gap_map.irrelevant_skills)}",
        "",
        "## Skills laborales detectadas",
        "",
    ]
    for item in [*gap_map.covered_skills, *gap_map.partial_skills, *gap_map.missing_skills, *gap_map.emerging_skills][:40]:
        lines.extend(
            [
                f"### {item.skill}",
                f"- Cluster ocupacional: {item.cluster_name}",
                f"- Cobertura curricular: {item.coverage_status}",
                f"- Peso de evidencia: {item.evidence_weight}",
                f"- Fuente de evidencia: {json.dumps(item.evidence_sources, ensure_ascii=False)}",
                f"- Cargos asociados: {', '.join(item.roles[:5]) or 'sin cargo asociado'}",
                f"- Relacion con perfil/grafo: {item.reason}",
                f"- Recomendacion: {item.recommendation}",
                "",
            ]
        )
    lines.extend(["## Recomendaciones curriculares", ""])
    lines.extend([f"- {item['action']} (skill: {item['skill']}, cluster: {item['cluster_name']})" for item in gap_map.recommended_curriculum_updates] or ["- Sin recomendaciones con evidencia suficiente."])
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    result = build_curriculum_market_gap_map()
    print(json.dumps({"covered": len(result.covered_skills), "missing": len(result.missing_skills), "emerging": len(result.emerging_skills)}, indent=2))

