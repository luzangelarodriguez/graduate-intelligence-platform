from __future__ import annotations

import re
from typing import Any


GRAPHQL_PATTERNS = (
    r"/graphql\b",
    r"\bquery\s+[A-Za-z0-9_]*\s*[{(]",
    r"\bmutation\s+[A-Za-z0-9_]*\s*[{(]",
    r"GraphQLClient",
    r"apollo",
    r"urql",
)


def is_graphql_endpoint(url: str, payload: Any | None = None) -> bool:
    blob = f"{url} {payload or ''}"
    return any(re.search(pattern, blob, flags=re.IGNORECASE) for pattern in GRAPHQL_PATTERNS)


def extract_graphql_operations(text: str) -> list[str]:
    operations: list[str] = []
    for pattern in (r"\bquery\s+([A-Za-z0-9_]+)", r"\bmutation\s+([A-Za-z0-9_]+)"):
        operations.extend(re.findall(pattern, text, flags=re.IGNORECASE))
    return sorted(set(operations))

