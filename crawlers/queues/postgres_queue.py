from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.db import get_conn  # noqa: E402

QUEUE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS crawler_jobs_queue (
    id SERIAL PRIMARY KEY,
    source_name TEXT NOT NULL,
    search_url TEXT,
    detail_url TEXT,
    attempts INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    priority INTEGER DEFAULT 100,
    locked_by TEXT,
    locked_at TIMESTAMP,
    correlation_id TEXT,
    error TEXT,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS crawler_job_results (
    id SERIAL PRIMARY KEY,
    queue_id INTEGER REFERENCES crawler_jobs_queue(id),
    source_name TEXT NOT NULL,
    detail_url TEXT,
    content_hash TEXT,
    result_json JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS crawler_failures (
    id SERIAL PRIMARY KEY,
    queue_id INTEGER REFERENCES crawler_jobs_queue(id),
    source_name TEXT NOT NULL,
    detail_url TEXT,
    error TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS crawler_execution_logs (
    id SERIAL PRIMARY KEY,
    correlation_id TEXT,
    source_name TEXT,
    event_type TEXT NOT NULL,
    payload JSONB,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS crawler_metrics (
    id SERIAL PRIMARY KEY,
    correlation_id TEXT,
    source_name TEXT,
    requests INTEGER DEFAULT 0,
    successes INTEGER DEFAULT 0,
    failures INTEGER DEFAULT 0,
    blocked INTEGER DEFAULT 0,
    avg_latency_ms NUMERIC DEFAULT 0,
    health_score NUMERIC DEFAULT 0,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS crawler_dead_letter_queue (
    id SERIAL PRIMARY KEY,
    queue_id INTEGER,
    source_name TEXT NOT NULL,
    detail_url TEXT,
    error TEXT,
    payload JSONB,
    created_at TIMESTAMP DEFAULT now()
);
"""

VALID_STATUSES = {"pending", "running", "success", "failed", "skipped"}


@dataclass(frozen=True)
class QueueItem:
    source_name: str
    search_url: str = ""
    detail_url: str = ""
    status: str = "pending"
    priority: int = 100
    correlation_id: str = ""


class PostgresCrawlerQueue:
    def ensure_schema(self) -> None:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(QUEUE_SCHEMA_SQL)
            conn.commit()

    def enqueue(self, item: QueueItem) -> int:
        if item.status not in VALID_STATUSES:
            raise ValueError("invalid_queue_status")
        self.ensure_schema()
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO crawler_jobs_queue (source_name, search_url, detail_url, status, priority, correlation_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (item.source_name, item.search_url, item.detail_url, item.status, item.priority, item.correlation_id),
                )
                row = cur.fetchone()
            conn.commit()
        return int(row["id"] if isinstance(row, dict) else row[0])

    def update_status(self, queue_id: int, status: str, error: str = "") -> None:
        if status not in VALID_STATUSES:
            raise ValueError("invalid_queue_status")
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE crawler_jobs_queue
                    SET status = %s, error = %s, updated_at = now(), attempts = attempts + 1
                    WHERE id = %s
                    """,
                    (status, error, queue_id),
                )
            conn.commit()

    def lease_next(self, worker_id: str, source_name: str | None = None) -> dict[str, Any] | None:
        self.ensure_schema()
        with get_conn() as conn:
            with conn.cursor() as cur:
                if source_name:
                    cur.execute(
                        """
                        SELECT id FROM crawler_jobs_queue
                        WHERE status = 'pending' AND source_name = %s
                        ORDER BY priority ASC, created_at ASC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                        """,
                        (source_name,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id FROM crawler_jobs_queue
                        WHERE status = 'pending'
                        ORDER BY priority ASC, created_at ASC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                        """
                    )
                row = cur.fetchone()
                if not row:
                    conn.commit()
                    return None
                queue_id = int(row["id"] if isinstance(row, dict) else row[0])
                cur.execute(
                    """
                    UPDATE crawler_jobs_queue
                    SET status = 'running', locked_by = %s, locked_at = now(), attempts = attempts + 1, updated_at = now()
                    WHERE id = %s
                    RETURNING *
                    """,
                    (worker_id, queue_id),
                )
                leased = cur.fetchone()
            conn.commit()
        return dict(leased) if leased else None

    def record_result(self, queue_id: int, source_name: str, detail_url: str, content_hash: str, result_json: dict[str, Any]) -> None:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO crawler_job_results (queue_id, source_name, detail_url, content_hash, result_json)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (queue_id, source_name, detail_url, content_hash, result_json),
                )
            conn.commit()

    def record_failure(self, queue_id: int | None, source_name: str, detail_url: str, error: str, payload: dict[str, Any] | None = None) -> None:
        self.ensure_schema()
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO crawler_dead_letter_queue (queue_id, source_name, detail_url, error, payload)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (queue_id, source_name, detail_url, error, payload or {}),
                )
            conn.commit()
