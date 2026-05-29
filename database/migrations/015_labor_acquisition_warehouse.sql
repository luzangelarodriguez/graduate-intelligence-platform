-- Labor Acquisition Platform normalized warehouse.
-- Safe migration: no DROP, no TRUNCATE, no destructive changes.

CREATE TABLE IF NOT EXISTS public.sources (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL DEFAULT 'job_portal',
    confidence NUMERIC(6,4) NOT NULL DEFAULT 0.7000,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.companies (
    id BIGSERIAL PRIMARY KEY,
    company TEXT NOT NULL,
    normalized_company TEXT NOT NULL UNIQUE,
    original_company TEXT,
    company_confidence_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.industries (
    id BIGSERIAL PRIMARY KEY,
    industry TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.locations (
    id BIGSERIAL PRIMARY KEY,
    location TEXT NOT NULL,
    normalized_location TEXT NOT NULL UNIQUE,
    city TEXT,
    country TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.modalities (
    id BIGSERIAL PRIMARY KEY,
    modality TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.seniority_levels (
    id BIGSERIAL PRIMARY KEY,
    seniority TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.execution_runs (
    correlation_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'running',
    sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    execute_network BOOLEAN NOT NULL DEFAULT FALSE,
    persist_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    manifest_path TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS public.crawl_metrics (
    id BIGSERIAL PRIMARY KEY,
    correlation_id TEXT REFERENCES public.execution_runs(correlation_id) ON DELETE SET NULL,
    source TEXT NOT NULL,
    requests INTEGER NOT NULL DEFAULT 0,
    successes INTEGER NOT NULL DEFAULT 0,
    failures INTEGER NOT NULL DEFAULT 0,
    blocked INTEGER NOT NULL DEFAULT 0,
    avg_latency_ms NUMERIC(12,3) NOT NULL DEFAULT 0,
    health_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (correlation_id, source)
);

CREATE TABLE IF NOT EXISTS public.failed_jobs (
    id BIGSERIAL PRIMARY KEY,
    correlation_id TEXT REFERENCES public.execution_runs(correlation_id) ON DELETE SET NULL,
    source TEXT NOT NULL,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    source_url TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.canonical_skills (
    id BIGSERIAL PRIMARY KEY,
    canonical_skill TEXT NOT NULL UNIQUE,
    skill_category TEXT NOT NULL DEFAULT 'Unknown',
    skill_family TEXT NOT NULL DEFAULT 'Unknown',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.skill_aliases (
    id BIGSERIAL PRIMARY KEY,
    canonical_skill_id BIGINT NOT NULL REFERENCES public.canonical_skills(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.jobs (
    id BIGSERIAL PRIMARY KEY,
    source_id BIGINT REFERENCES public.sources(id) ON DELETE SET NULL,
    company_id BIGINT REFERENCES public.companies(id) ON DELETE SET NULL,
    location_id BIGINT REFERENCES public.locations(id) ON DELETE SET NULL,
    modality_id BIGINT REFERENCES public.modalities(id) ON DELETE SET NULL,
    seniority_id BIGINT REFERENCES public.seniority_levels(id) ON DELETE SET NULL,
    industry_id BIGINT REFERENCES public.industries(id) ON DELETE SET NULL,
    execution_id TEXT REFERENCES public.execution_runs(correlation_id) ON DELETE SET NULL,
    source TEXT NOT NULL,
    source_job_id TEXT,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    original_company TEXT,
    normalized_company TEXT,
    company_confidence_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    location TEXT,
    modality TEXT,
    seniority TEXT,
    industry TEXT,
    salary_min NUMERIC(14,2),
    salary_max NUMERIC(14,2),
    salary_currency TEXT,
    salary_period TEXT,
    contract_type TEXT,
    experience_level TEXT,
    description TEXT NOT NULL,
    responsibilities TEXT,
    requirements TEXT,
    source_url TEXT NOT NULL,
    application_url TEXT,
    fingerprint TEXT NOT NULL UNIQUE,
    content_hash TEXT NOT NULL UNIQUE,
    duplicate_group_id TEXT,
    duplicate_confidence NUMERIC(6,4) NOT NULL DEFAULT 0,
    canonical_job_id BIGINT,
    semantic_title_family TEXT,
    role_similarity NUMERIC(6,4) NOT NULL DEFAULT 0,
    occupational_role_inference TEXT,
    completeness_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    extraction_confidence NUMERIC(6,4) NOT NULL DEFAULT 0,
    source_confidence NUMERIC(6,4) NOT NULL DEFAULT 0,
    job_probability_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    curation_level TEXT NOT NULL DEFAULT 'rejected',
    rejection_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    semantic_evidence_count INTEGER NOT NULL DEFAULT 0,
    semantic_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    top_acceptance_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    unknown_skill_candidates JSONB NOT NULL DEFAULT '[]'::jsonb,
    document_type TEXT NOT NULL DEFAULT 'job_posting',
    is_real_job_posting BOOLEAN NOT NULL DEFAULT TRUE,
    raw_context JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.job_skills (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT NOT NULL REFERENCES public.jobs(id) ON DELETE CASCADE,
    canonical_skill_id BIGINT REFERENCES public.canonical_skills(id) ON DELETE SET NULL,
    canonical_skill TEXT NOT NULL,
    skill_category TEXT NOT NULL DEFAULT 'Unknown',
    skill_family TEXT NOT NULL DEFAULT 'Unknown',
    confidence NUMERIC(6,4) NOT NULL DEFAULT 0,
    evidence_type TEXT NOT NULL DEFAULT 'job_evidence',
    source_section TEXT NOT NULL DEFAULT 'description',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (job_id, canonical_skill)
);

ALTER TABLE public.industries ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE public.locations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE public.modalities ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE public.seniority_levels ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS job_probability_score NUMERIC(6,4) NOT NULL DEFAULT 0;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS curation_level TEXT NOT NULL DEFAULT 'rejected';
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS rejection_reasons JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS semantic_evidence_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS semantic_evidence JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS top_acceptance_reasons JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS unknown_skill_candidates JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.companies ADD COLUMN IF NOT EXISTS original_company TEXT;
ALTER TABLE public.companies ADD COLUMN IF NOT EXISTS company_confidence_score NUMERIC(6,4) NOT NULL DEFAULT 0;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS original_company TEXT;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS normalized_company TEXT;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS company_confidence_score NUMERIC(6,4) NOT NULL DEFAULT 0;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS duplicate_group_id TEXT;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS duplicate_confidence NUMERIC(6,4) NOT NULL DEFAULT 0;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS canonical_job_id BIGINT;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS semantic_title_family TEXT;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS role_similarity NUMERIC(6,4) NOT NULL DEFAULT 0;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS occupational_role_inference TEXT;

CREATE INDEX IF NOT EXISTS idx_jobs_source_created ON public.jobs(source, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON public.jobs(company_id);
CREATE INDEX IF NOT EXISTS idx_jobs_fingerprint ON public.jobs(fingerprint);
CREATE INDEX IF NOT EXISTS idx_jobs_execution ON public.jobs(execution_id);
CREATE INDEX IF NOT EXISTS idx_jobs_curation_probability ON public.jobs(curation_level, job_probability_score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_duplicate_group ON public.jobs(duplicate_group_id);
CREATE INDEX IF NOT EXISTS idx_job_skills_skill ON public.job_skills(canonical_skill, confidence DESC);
CREATE INDEX IF NOT EXISTS idx_job_skills_job ON public.job_skills(job_id);
CREATE INDEX IF NOT EXISTS idx_crawl_metrics_source ON public.crawl_metrics(source, created_at DESC);
