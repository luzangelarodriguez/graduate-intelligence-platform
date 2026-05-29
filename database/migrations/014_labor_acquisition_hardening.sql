-- Labor Acquisition Platform hardening tables.
-- Safe incremental migration: no DROP, no TRUNCATE, no destructive updates.

ALTER TABLE crawler_jobs_queue
    ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 100,
    ADD COLUMN IF NOT EXISTS locked_by TEXT,
    ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS correlation_id TEXT;

CREATE TABLE IF NOT EXISTS crawler_execution_logs (
    id BIGSERIAL PRIMARY KEY,
    correlation_id TEXT NOT NULL,
    source_name TEXT,
    event_name TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'info',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crawler_metrics (
    id BIGSERIAL PRIMARY KEY,
    correlation_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    requests INTEGER NOT NULL DEFAULT 0,
    successes INTEGER NOT NULL DEFAULT 0,
    failures INTEGER NOT NULL DEFAULT 0,
    blocked INTEGER NOT NULL DEFAULT 0,
    avg_latency_ms NUMERIC(12, 3) NOT NULL DEFAULT 0,
    network_health_score NUMERIC(6, 4) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crawler_dead_letter_queue (
    id BIGSERIAL PRIMARY KEY,
    correlation_id TEXT,
    source_name TEXT NOT NULL,
    search_url TEXT,
    detail_url TEXT,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crawler_jobs_queue_priority_status
    ON crawler_jobs_queue (status, priority, created_at);

CREATE INDEX IF NOT EXISTS idx_crawler_execution_logs_correlation
    ON crawler_execution_logs (correlation_id, created_at);

CREATE INDEX IF NOT EXISTS idx_crawler_metrics_correlation
    ON crawler_metrics (correlation_id, source_name);

CREATE INDEX IF NOT EXISTS idx_crawler_dead_letter_queue_source
    ON crawler_dead_letter_queue (source_name, created_at);
