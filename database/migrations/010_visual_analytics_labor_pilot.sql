-- Visual Analytics and Big Data labor pilot support.
-- Safe incremental migration: no DROP, no TRUNCATE.

CREATE TABLE IF NOT EXISTS labor_market_sources (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    country TEXT,
    priority TEXT,
    source_type TEXT,
    access_mode TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    rate_limit_seconds INTEGER DEFAULT 10,
    max_pages INTEGER DEFAULT 1,
    max_jobs INTEGER DEFAULT 50,
    allowed_paths JSONB DEFAULT '[]'::jsonb,
    blocked_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS labor_extraction_runs (
    id SERIAL PRIMARY KEY,
    run_id TEXT NOT NULL UNIQUE,
    pilot TEXT NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT DEFAULT 'running',
    sources_requested INTEGER DEFAULT 0,
    jobs_extracted INTEGER DEFAULT 0,
    jobs_discarded INTEGER DEFAULT 0,
    gold_jobs INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS labor_extraction_errors (
    id SERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    source TEXT NOT NULL,
    error_type TEXT NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE empleos
    ADD COLUMN IF NOT EXISTS job_relevance_score NUMERIC(5,4),
    ADD COLUMN IF NOT EXISTS role_class TEXT,
    ADD COLUMN IF NOT EXISTS extraction_run_id TEXT,
    ADD COLUMN IF NOT EXISTS gold_publishable BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_empleos_visual_analytics_relevance
    ON empleos (job_relevance_score DESC)
    WHERE job_relevance_score IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_empleos_extraction_run_id
    ON empleos (extraction_run_id);
