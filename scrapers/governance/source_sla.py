from __future__ import annotations

import json
from typing import Any

from psycopg2.extras import Json

from scrapers.governance.source_reliability import clamp, get_connection


def json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def compute_sla_metrics(source: str, *, window_days: int = 30) -> dict[str, Any]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*)::int AS total,
                COUNT(*) FILTER (WHERE status IN ('completed', 'success'))::int AS completed,
                COUNT(*) FILTER (WHERE status = 'blocked_auth')::int AS blocked_auth,
                COALESCE(SUM(error_count), 0)::int AS errors
            FROM public.extraction_runs
            WHERE source = %s AND started_at >= now() - (%s || ' days')::interval
            """,
            (source, window_days),
        )
        runs = cur.fetchone() or {}
        cur.execute(
            """
            SELECT COUNT(DISTINCT response_type)::int AS response_types,
                   COUNT(*) FILTER (WHERE auth_required = true)::int AS auth_endpoints,
                   COUNT(*)::int AS endpoints
            FROM public.api_sources_registry
            WHERE source = %s AND last_seen_at >= now() - (%s || ' days')::interval
            """,
            (source, window_days),
        )
        registry = cur.fetchone() or {}
    total = int(runs.get("total") or 0)
    completed = int(runs.get("completed") or 0)
    blocked_auth = int(runs.get("blocked_auth") or 0)
    errors = int(runs.get("errors") or 0)
    endpoints = int(registry.get("endpoints") or 0)
    response_types = int(registry.get("response_types") or 0)
    auth_endpoints = int(registry.get("auth_endpoints") or 0)
    uptime = completed / total if total else 0.0
    response_stability = 1.0 - (errors / max(1, total + errors))
    schema_stability = 1.0 if endpoints and response_types <= 1 else max(0.0, 1.0 - response_types / max(2, endpoints))
    auth_volatility = (blocked_auth + auth_endpoints) / max(1, total + endpoints)
    return {
        "source": source,
        "uptime": clamp(uptime),
        "response_stability": clamp(response_stability),
        "schema_stability": clamp(schema_stability),
        "auth_volatility": clamp(auth_volatility),
        "window_days": window_days,
        "metadata": {"runs": dict(runs), "registry": dict(registry)},
    }


def upsert_sla_metrics(metrics: dict[str, Any]) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.source_sla_metrics (
                source, uptime, response_stability, schema_stability,
                auth_volatility, window_days, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                metrics["source"],
                metrics["uptime"],
                metrics["response_stability"],
                metrics["schema_stability"],
                metrics["auth_volatility"],
                metrics["window_days"],
                Json(json_safe(metrics["metadata"])),
            ),
        )
