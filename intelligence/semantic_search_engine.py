from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from intelligence.common import clamp, jaccard, token_set


@dataclass(frozen=True)
class SemanticSearchResult:
    entity_type: str
    entity_id: str
    title: str
    similarity_score: float
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def semantic_search(query: str, corpus: list[dict[str, Any]], *, entity_type: str = "job", limit: int = 10) -> list[SemanticSearchResult]:
    query_tokens = token_set(query)
    results: list[SemanticSearchResult] = []
    for row in corpus:
        text = " ".join(
            [
                str(row.get("title") or row.get("company") or row.get("skill") or ""),
                str(row.get("description") or ""),
                " ".join(row.get("skills") or []),
                str(row.get("role_family") or ""),
            ]
        )
        score = clamp(jaccard(query_tokens, token_set(text)) * 2.2)
        if score <= 0:
            continue
        results.append(
            SemanticSearchResult(
                entity_type=entity_type,
                entity_id=str(row.get("id") or row.get("title") or row.get("company") or ""),
                title=str(row.get("title") or row.get("company") or row.get("skill") or ""),
                similarity_score=round(score, 4),
                evidence={"matched_query": query, "skills": (row.get("skills") or [])[:8]},
            )
        )
    return sorted(results, key=lambda item: item.similarity_score, reverse=True)[:limit]
