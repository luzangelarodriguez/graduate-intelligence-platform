from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

from intelligence.common import clamp
from intelligence.career_path_engine import CareerTransition
from intelligence.semantic_role_intelligence import RoleSignal, role_similarity


@dataclass(frozen=True)
class SemanticRoleGraphEdge:
    source_role: str
    target_role: str
    similarity_score: float
    transition_probability: float
    shared_skills: list[str]
    cluster_affinity: str
    centrality_score: float
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _skills_by_title(jobs: list[dict[str, Any]]) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = {}
    for job in jobs:
        title = str(job.get("title") or job.get("normalized_title") or "").strip()
        if not title:
            continue
        mapping.setdefault(title, set()).update(str(skill) for skill in (job.get("skills") or []) if str(skill).strip())
    return mapping


def _role_pair_similarity(left: RoleSignal, right: RoleSignal, jobs: list[dict[str, Any]]) -> tuple[float, list[str]]:
    lookup = _skills_by_title(jobs)
    shared_skills = sorted(lookup.get(left.role_title, set()) & lookup.get(right.role_title, set()))
    score = role_similarity(
        {"title": left.role_title, "skills": shared_skills or list(lookup.get(left.role_title, set()))},
        {"title": right.role_title, "skills": shared_skills or list(lookup.get(right.role_title, set()))},
    )
    if left.role_family == right.role_family:
        score = clamp(score + 0.18)
    if shared_skills:
        score = clamp(score + min(len(shared_skills) / 12.0, 0.22))
    return round(score, 4), shared_skills[:8]


def build_semantic_role_graph(
    *,
    jobs: list[dict[str, Any]],
    role_signals: list[RoleSignal],
    career_transitions: list[CareerTransition],
    metric_period: str,
    write_output: bool = True,
) -> list[SemanticRoleGraphEdge]:
    edges: list[SemanticRoleGraphEdge] = []
    centrality_lookup = {signal.role_title: float(signal.centrality_score) for signal in role_signals}
    pair_map: dict[tuple[str, str], SemanticRoleGraphEdge] = {}

    for left, right in combinations(role_signals, 2):
        similarity, shared_skills = _role_pair_similarity(left, right, jobs)
        if similarity < 0.35 and left.role_family != right.role_family:
            continue
        edge = SemanticRoleGraphEdge(
            source_role=left.role_title,
            target_role=right.role_title,
            similarity_score=similarity,
            transition_probability=round(clamp((similarity * 0.65) + (max(left.centrality_score, right.centrality_score) * 0.35)), 4),
            shared_skills=shared_skills,
            cluster_affinity=left.role_family if left.role_family == right.role_family else "Enterprise Analytics",
            centrality_score=round((centrality_lookup.get(left.role_title, 0.0) + centrality_lookup.get(right.role_title, 0.0)) / 2, 4),
            evidence={"metric_period": metric_period, "role_family": left.role_family, "roles": [left.role_title, right.role_title]},
        )
        pair_map[(edge.source_role, edge.target_role)] = edge

    for transition in career_transitions:
        edge = SemanticRoleGraphEdge(
            source_role=transition.source_role,
            target_role=transition.target_role,
            similarity_score=round(clamp(float(transition.role_progression_probability) * 0.92), 4),
            transition_probability=round(clamp(float(transition.role_progression_probability)), 4),
            shared_skills=list(transition.recommended_next_skills[:8]),
            cluster_affinity="career_transition",
            centrality_score=round(clamp(float(transition.role_progression_probability)), 4),
            evidence={
                "metric_period": metric_period,
                "transition_skill_gaps": list(transition.transition_skill_gaps),
                "recommended_next_skills": list(transition.recommended_next_skills),
            },
        )
        pair_map[(edge.source_role, edge.target_role)] = edge

    edges = sorted(pair_map.values(), key=lambda item: (item.similarity_score, item.transition_probability, item.centrality_score), reverse=True)
    if write_output:
        write_semantic_role_graph_report(edges, metric_period)
    return edges


def write_semantic_role_graph_report(
    edges: list[SemanticRoleGraphEdge],
    metric_period: str,
    path: Path | None = None,
) -> None:
    path = path or (Path(__file__).resolve().parents[1] / "outputs" / "analytics" / "semantic_role_graph_report.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Semantic Role Graph",
        "",
        f"- Periodo: {metric_period}",
        f"- Edges: {len(edges)}",
        "",
    ]
    for item in edges[:40]:
        lines.extend(
            [
                f"## {item.source_role} -> {item.target_role}",
                f"- Similarity: {round(item.similarity_score, 4)}",
                f"- Transition probability: {round(item.transition_probability, 4)}",
                f"- Shared skills: {', '.join(item.shared_skills) or 'sin skills compartidas'}",
                f"- Cluster affinity: {item.cluster_affinity}",
                f"- Centrality: {round(item.centrality_score, 4)}",
                f"- Evidence: {json.dumps(item.evidence, ensure_ascii=False)}",
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
