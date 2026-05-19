from __future__ import annotations

from datetime import datetime, timezone

from scrapers.governance.source_reliability import clamp, get_connection


def compute_freshness_score(source: str, *, max_age_days: int = 14) -> float:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT MAX(started_at) AS last_run
            FROM public.extraction_runs
            WHERE source = %s
            """,
            (source,),
        )
        row = cur.fetchone()
    last_run = row["last_run"] if row else None
    if not last_run:
        return 0.0
    if last_run.tzinfo is None:
        last_run = last_run.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (datetime.now(timezone.utc) - last_run).total_seconds() / 86400)
    return clamp(1.0 - min(1.0, age_days / max(1, max_age_days)))


def freshness_label(score: float) -> str:
    if score >= 0.85:
        return "fresh"
    if score >= 0.55:
        return "aging"
    if score > 0:
        return "stale"
    return "no_recent_runs"
