from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agents.visual_analytics_labor_agent import classify_document_type  # noqa: E402


def classify_crawled_document(payload: dict[str, Any], *, source_url: str) -> dict[str, Any]:
    return classify_document_type(payload, source_url=source_url)


def is_strong_job_posting(payload: dict[str, Any], *, source_url: str) -> bool:
    classification = classify_crawled_document(payload, source_url=source_url)
    return bool(classification["document_type"] == "job_posting" and classification["is_real_job_posting"])
