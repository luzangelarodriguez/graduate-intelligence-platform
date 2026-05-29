from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Any, Iterable


def normalize_key(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text.casefold())
    return re.sub(r"\s+", " ", text).strip()


def token_set(value: str | Iterable[str]) -> set[str]:
    if isinstance(value, str):
        value = [value]
    tokens: set[str] = set()
    for item in value:
        tokens.update(normalize_key(str(item)).split())
    return {token for token in tokens if len(token) > 1}


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def cosine_from_counters(left: Counter[str], right: Counter[str]) -> float:
    keys = set(left) | set(right)
    if not keys:
        return 0.0
    dot = sum(left[key] * right[key] for key in keys)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def top_counts(rows: Iterable[Any], key: str, limit: int = 10) -> list[str]:
    counts = Counter(str(row.get(key) or "") for row in rows if row.get(key))
    return [item for item, _count in counts.most_common(limit)]
