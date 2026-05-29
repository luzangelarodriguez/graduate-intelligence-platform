-- Bronze/Silver/Gold labor evidence layers for Visual Analytics pilot.
-- Safe incremental migration: no DROP, no TRUNCATE.

CREATE TABLE IF NOT EXISTS public.bronze_empleos_raw (
    id BIGSERIAL PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_url TEXT,
    raw_html TEXT,
    raw_text TEXT,
    raw_json JSONB DEFAULT '{}'::jsonb,
    extraction_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    page_title TEXT,
    http_status INTEGER,
    extraction_method TEXT NOT NULL DEFAULT 'agentic_browser',
    content_hash TEXT NOT NULL UNIQUE,
    detected_language TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_bronze_empleos_raw_source_name
ON public.bronze_empleos_raw(source_name);

CREATE INDEX IF NOT EXISTS ix_bronze_empleos_raw_extraction_timestamp
ON public.bronze_empleos_raw(extraction_timestamp DESC);

CREATE TABLE IF NOT EXISTS public.silver_empleos_normalized (
    id BIGSERIAL PRIMARY KEY,
    bronze_id BIGINT REFERENCES public.bronze_empleos_raw(id) ON DELETE SET NULL,
    source_name TEXT NOT NULL,
    source_url TEXT,
    normalized_title TEXT,
    normalized_company TEXT,
    normalized_location TEXT,
    normalized_description TEXT,
    extracted_skills JSONB DEFAULT '[]'::jsonb,
    extracted_tools JSONB DEFAULT '[]'::jsonb,
    extracted_cloud JSONB DEFAULT '[]'::jsonb,
    extracted_frameworks JSONB DEFAULT '[]'::jsonb,
    analytics_density NUMERIC(6,4) NOT NULL DEFAULT 0,
    contextual_relevance_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    semantic_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    rejection_reason TEXT,
    accepted_for_gold BOOLEAN NOT NULL DEFAULT FALSE,
    parser_version TEXT NOT NULL DEFAULT 'agentic_visual_analytics_v1',
    content_hash TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_silver_empleos_normalized_gold
ON public.silver_empleos_normalized(accepted_for_gold, contextual_relevance_score DESC);

CREATE INDEX IF NOT EXISTS ix_silver_empleos_normalized_source_name
ON public.silver_empleos_normalized(source_name);

ALTER TABLE public.silver_empleos_normalized
ADD COLUMN IF NOT EXISTS document_type TEXT NOT NULL DEFAULT 'unknown',
ADD COLUMN IF NOT EXISTS evidence_source_type TEXT NOT NULL DEFAULT 'unknown',
ADD COLUMN IF NOT EXISTS is_real_job_posting BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS invalid_job_reason TEXT,
ADD COLUMN IF NOT EXISTS job_evidence_skills JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS portal_taxonomy_skills JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS job_probability_score NUMERIC(6,4) NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS curation_level TEXT NOT NULL DEFAULT 'rejected',
ADD COLUMN IF NOT EXISTS semantic_evidence_count INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS top_acceptance_reasons JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS unknown_skill_candidates JSONB DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS ix_silver_empleos_normalized_document_type
ON public.silver_empleos_normalized(document_type, is_real_job_posting);

CREATE TABLE IF NOT EXISTS public.gold_empleos_analytics (
    id BIGSERIAL PRIMARY KEY,
    silver_id BIGINT REFERENCES public.silver_empleos_normalized(id) ON DELETE SET NULL,
    curated_title TEXT NOT NULL,
    curated_description TEXT,
    evidence_summary TEXT NOT NULL,
    normalized_skills JSONB DEFAULT '[]'::jsonb,
    market_role TEXT,
    analytics_relevance NUMERIC(6,4) NOT NULL,
    ai_confidence NUMERIC(6,4) NOT NULL,
    approved_by_agent BOOLEAN NOT NULL DEFAULT TRUE,
    approved_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_name TEXT,
    source_url TEXT,
    content_hash TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_gold_empleos_analytics_relevance
ON public.gold_empleos_analytics(analytics_relevance DESC, ai_confidence DESC);
