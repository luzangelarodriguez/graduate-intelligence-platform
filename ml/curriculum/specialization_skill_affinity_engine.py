from __future__ import annotations

import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.curriculum.specialization_curriculum_graph_engine import SpecializationCurriculumGraph
from ml.labor.occupational_skill_cluster_engine import classify_skill_cluster
from scrapers.normalization.visual_analytics_skill_taxonomy import normalize_text


@dataclass(frozen=True)
class SkillAffinityResult:
    skill: str
    specialization_id: str
    affinity_score: float
    coverage_status: str
    matched_curriculum_skill: str | None
    cluster_name: str
    reason: str


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()


def calculate_skill_affinity(skill: str, graph: SpecializationCurriculumGraph) -> SkillAffinityResult:
    cluster_name = classify_skill_cluster(skill)
    curriculum_skills = {node.skill: node for node in graph.skills}
    if skill in curriculum_skills:
        node = curriculum_skills[skill]
        return SkillAffinityResult(
            skill=skill,
            specialization_id=graph.specialization_id,
            affinity_score=round(max(0.82, node.curricular_weight), 4),
            coverage_status="covered",
            matched_curriculum_skill=skill,
            cluster_name=cluster_name,
            reason="Skill presente directamente en microcurriculos o perfil curricular.",
        )

    best_skill = None
    best_score = 0.0
    for current in curriculum_skills:
        score = _similarity(skill, current)
        if classify_skill_cluster(current) == cluster_name:
            score += 0.18
        if score > best_score:
            best_score = score
            best_skill = current

    if best_score >= 0.72:
        return SkillAffinityResult(
            skill=skill,
            specialization_id=graph.specialization_id,
            affinity_score=round(min(best_score, 0.81), 4),
            coverage_status="partial",
            matched_curriculum_skill=best_skill,
            cluster_name=cluster_name,
            reason="Skill relacionada semanticamente con competencias o herramientas curriculares.",
        )

    if cluster_name in {"BI & Visualization", "Data Engineering", "Cloud Analytics", "AI Analytics", "Data Governance", "Reporting & KPI", "DataOps", "GenAI Analytics"}:
        return SkillAffinityResult(
            skill=skill,
            specialization_id=graph.specialization_id,
            affinity_score=0.55 if cluster_name in {"Cloud Analytics", "DataOps", "GenAI Analytics"} else 0.48,
            coverage_status="missing",
            matched_curriculum_skill=best_skill,
            cluster_name=cluster_name,
            reason="Skill laboral relevante para el ecosistema de Visual Analytics y Big Data, pero sin cobertura curricular directa.",
        )

    return SkillAffinityResult(
        skill=skill,
        specialization_id=graph.specialization_id,
        affinity_score=0.08,
        coverage_status="irrelevant",
        matched_curriculum_skill=best_skill,
        cluster_name=cluster_name,
        reason="Skill con baja relacion semantica frente al grafo curricular de la especializacion.",
    )

