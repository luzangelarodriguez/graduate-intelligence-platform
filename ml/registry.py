from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from psycopg2.extras import Json

from backend.db import get_cursor

ROOT_DIR = Path(__file__).resolve().parents[1]


def ml_db_enabled() -> bool:
    return os.getenv("ML_WRITE_DB", "true").strip().lower() in {"1", "true", "yes", "on"}


def try_apply_schema() -> None:
    schema = ROOT_DIR / "database" / "enterprise_labor_intelligence_schema.sql"
    with get_cursor() as cur:
        cur.execute(schema.read_text(encoding="utf-8"))


def register_model(
    *,
    model_name: str,
    model_type: str,
    version: str,
    artifact_path: str,
    training_dataset_path: str,
    metrics: dict[str, Any],
    status: str = "candidate",
) -> None:
    if not ml_db_enabled():
        return
    try:
        try_apply_schema()
        with get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.ml_model_registry (
                    model_name, model_type, version, artifact_path,
                    training_dataset_path, metrics, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (model_name, version) DO UPDATE SET
                    artifact_path = EXCLUDED.artifact_path,
                    training_dataset_path = EXCLUDED.training_dataset_path,
                    metrics = EXCLUDED.metrics,
                    status = EXCLUDED.status
                """,
                (model_name, model_type, version, artifact_path, training_dataset_path, Json(metrics), status),
            )
    except Exception:
        return


def register_evaluation(
    *,
    model_name: str,
    model_version: str,
    dataset_path: str,
    metrics: dict[str, Any],
) -> None:
    if not ml_db_enabled():
        return
    try:
        try_apply_schema()
        with get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.ml_evaluation_runs (
                    run_id, model_name, model_version, dataset_path, accuracy,
                    precision_macro, recall_macro, f1_macro, confusion_matrix, metrics
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id) DO NOTHING
                """,
                (
                    f"eval_{uuid.uuid4().hex[:12]}",
                    model_name,
                    model_version,
                    dataset_path,
                    metrics.get("accuracy", 0),
                    metrics.get("precision_macro", 0),
                    metrics.get("recall_macro", 0),
                    metrics.get("f1_macro", 0),
                    Json(metrics.get("confusion_matrix", [])),
                    Json(metrics),
                ),
            )
    except Exception:
        return


def register_prediction(
    *,
    model_name: str,
    model_version: str | None,
    input_hash: str,
    input_payload: dict[str, Any],
    predicted_domain: str,
    confidence: float,
    confidence_level: str,
    blocked: bool,
    scores: dict[str, float],
) -> None:
    if not ml_db_enabled():
        return
    try:
        try_apply_schema()
        with get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.ml_predictions (
                    model_name, model_version, input_hash, input_payload,
                    predicted_domain, confidence, confidence_level, blocked, scores
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    model_name,
                    model_version,
                    input_hash,
                    Json(json.loads(json.dumps(input_payload, ensure_ascii=False, default=str))),
                    predicted_domain,
                    confidence,
                    confidence_level,
                    blocked,
                    Json(scores),
                ),
            )
    except Exception:
        return
