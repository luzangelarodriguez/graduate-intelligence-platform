from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, asdict
from itertools import combinations
from typing import Any

from intelligence.common import clamp, jaccard, normalize_key, token_set


ROLE_FAMILIES = {
    "BI & Visualization": {"bi", "business intelligence", "power bi", "tableau", "dashboard", "reporting", "visualization", "analyst"},
    "Analytics Engineering": {"analytics engineer", "etl", "elt", "pipeline", "sql", "dbt", "data warehouse", "data engineer"},
    "Cloud Analytics": {"aws", "azure", "gcp", "cloud", "synapse", "databricks", "bigquery", "snowflake"},
    "AI Analytics": {"machine learning", "ai", "mlops", "predictive", "nlp", "llm", "rag"},
    "Governance & Quality": {"governance", "quality", "lineage", "metadata", "privacy", "compliance"},
    "Software/Data Platform": {"backend", "api", "microservices", "java", ".net", "platform", "developer"},
    "Criminal Justice & Forensics": {"criminology", "criminal", "criminalistic", "forensic", "victim", "cybercrime", "evidence", "custody", "intelligence", "security", "prevention", "penitentiary", "compliance"},
    "Public Security & Prevention": {"public security", "public safety", "crime prevention", "risk analysis", "organized crime", "security advisor"},
}


@dataclass(frozen=True)
class RoleSignal:
    role_title: str
    role_family: str
    semantic_role_cluster: str
    role_similarity_score: float
    centrality_score: float
    equivalent_roles: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def infer_role_family(title: str, skills: list[str] | None = None) -> tuple[str, float]:
    text_tokens = token_set(" ".join([title or "", " ".join(skills or [])]))
    best_family = "Enterprise Analytics"
    best_score = 0.0
    title_key = normalize_key(title)
    if any(term in title_key for term in ("criminolog", "criminalistic", "forensic", "victim", "cibercrime", "cybercrime", "seguridad publica", "public security")):
        return "Criminal Justice & Forensics", 0.94
    for family, terms in ROLE_FAMILIES.items():
        score = jaccard(text_tokens, token_set(terms))
        if score > best_score:
            best_family = family
            best_score = score
    if "analytics engineer" in normalize_key(title):
        return "Analytics Engineering", 0.92
    if "bi analyst" in normalize_key(title) or "power bi" in normalize_key(title):
        return "BI & Visualization", max(best_score, 0.88)
    if "security advisor" in title_key or "public security" in title_key:
        return "Public Security & Prevention", max(best_score, 0.9)
    return best_family, clamp(best_score * 2.8)


def role_similarity(left: dict[str, Any], right: dict[str, Any]) -> float:
    left_tokens = token_set([left.get("title", ""), *(left.get("skills") or [])])
    right_tokens = token_set([right.get("title", ""), *(right.get("skills") or [])])
    return clamp(jaccard(left_tokens, right_tokens) * 1.8)


def build_role_intelligence(jobs: list[dict[str, Any]]) -> list[RoleSignal]:
    by_title: dict[str, list[dict[str, Any]]] = {}
    for job in jobs:
        title = str(job.get("title") or "").strip()
        if title:
            by_title.setdefault(title, []).append(job)
    counts = Counter(str(job.get("title") or "") for job in jobs)
    signals: list[RoleSignal] = []
    for title, rows in by_title.items():
        skills = sorted({skill for row in rows for skill in (row.get("skills") or [])})
        family, score = infer_role_family(title, skills)
        equivalents: list[str] = []
        current = {"title": title, "skills": skills}
        for other_title, other_rows in by_title.items():
            if other_title == title:
                continue
            other_skills = sorted({skill for row in other_rows for skill in (row.get("skills") or [])})
            if role_similarity(current, {"title": other_title, "skills": other_skills}) >= 0.45:
                equivalents.append(other_title)
        centrality = clamp((counts[title] / max(len(jobs), 1)) + min(len(equivalents) / 10, 0.5))
        signals.append(RoleSignal(title, family, family, round(score, 4), round(centrality, 4), equivalents[:8]))
    return sorted(signals, key=lambda item: (item.centrality_score, item.role_similarity_score), reverse=True)


def occupational_edges(signals: list[RoleSignal]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for left, right in combinations(signals, 2):
        if left.role_family != right.role_family:
            continue
        weight = clamp((left.role_similarity_score + right.role_similarity_score) / 2)
        if weight >= 0.35:
            edges.append(
                {
                    "source_role": left.role_title,
                    "target_role": right.role_title,
                    "edge_type": "same_role_family",
                    "weight": round(weight, 4),
                    "evidence": {"role_family": left.role_family},
                }
            )
    return edges
