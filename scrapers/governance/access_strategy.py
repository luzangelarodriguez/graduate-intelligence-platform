from __future__ import annotations

import json
from typing import Any

from psycopg2.extras import Json

from scrapers.governance.source_reliability import get_connection


def json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def infer_access_strategy(source: str) -> dict[str, Any]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT endpoint, method, auth_required, rank_score
            FROM public.api_sources_registry
            WHERE source = %s
            ORDER BY rank_score DESC, last_seen_at DESC
            LIMIT 1
            """,
            (source,),
        )
        endpoint = cur.fetchone()
        cur.execute(
            """
            SELECT COUNT(*) FILTER (WHERE status = 'blocked_auth')::int AS blocked,
                   COUNT(*)::int AS total
            FROM public.extraction_runs
            WHERE source = %s
            """,
            (source,),
        )
        runs = cur.fetchone() or {}
    blocked = int(runs.get("blocked") or 0)
    total = int(runs.get("total") or 0)
    blocked_rate = blocked / total if total else 0.0
    if endpoint and endpoint["auth_required"]:
        strategy = "blocked_auth"
        action = "resolver token, sesion autenticada, convenio o acceso licenciado antes de promocionar a Gold"
        risk = "high"
    elif endpoint and float(endpoint["rank_score"] or 0) >= 0.55:
        strategy = "API"
        action = "priorizar extractor API-first con monitoreo de contrato"
        risk = "low"
    elif blocked_rate >= 0.4:
        strategy = "partnership"
        action = "buscar convenio o mecanismo autorizado; evitar dependencia DOM"
        risk = "high"
    else:
        strategy = "scraping"
        action = "mantener scraper controlado con discovery API recurrente"
        risk = "medium"
    return {
        "source": source,
        "access_strategy": strategy,
        "primary_endpoint": endpoint["endpoint"] if endpoint else None,
        "auth_required": bool(endpoint["auth_required"]) if endpoint else blocked_rate > 0,
        "partnership_required": strategy == "partnership",
        "licensed_required": strategy in {"blocked_auth", "partnership", "licensed"},
        "recommended_action": action,
        "risk_level": risk,
        "metadata": {"blocked_auth_rate": round(blocked_rate, 4), "best_endpoint": dict(endpoint) if endpoint else None},
    }


def upsert_access_strategy(strategy: dict[str, Any]) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.source_access_strategy (
                source, access_strategy, primary_endpoint, auth_required,
                partnership_required, licensed_required, recommended_action,
                risk_level, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source) DO UPDATE SET
                access_strategy = EXCLUDED.access_strategy,
                primary_endpoint = EXCLUDED.primary_endpoint,
                auth_required = EXCLUDED.auth_required,
                partnership_required = EXCLUDED.partnership_required,
                licensed_required = EXCLUDED.licensed_required,
                recommended_action = EXCLUDED.recommended_action,
                risk_level = EXCLUDED.risk_level,
                metadata = EXCLUDED.metadata,
                updated_at = now()
            """,
            (
                strategy["source"],
                strategy["access_strategy"],
                strategy["primary_endpoint"],
                strategy["auth_required"],
                strategy["partnership_required"],
                strategy["licensed_required"],
                strategy["recommended_action"],
                strategy["risk_level"],
                Json(json_safe(strategy["metadata"])),
            ),
        )
