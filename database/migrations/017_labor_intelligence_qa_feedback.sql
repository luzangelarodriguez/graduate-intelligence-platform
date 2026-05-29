-- QA feedback and model guardrail layer for Labor Intelligence.
-- Idempotent by design: safe to run after 015/016 in local or Railway PostgreSQL.

CREATE TABLE IF NOT EXISTS public.human_validation_feedback (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT REFERENCES public.jobs(id) ON DELETE SET NULL,
    canonical_skill_id BIGINT REFERENCES public.canonical_skills(id) ON DELETE SET NULL,
    accepted BOOLEAN,
    rejected BOOLEAN,
    corrected_skill TEXT,
    corrected_company TEXT,
    corrected_role TEXT,
    reviewer TEXT,
    confidence_override NUMERIC(6,4),
    observation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.human_validation_feedback ADD COLUMN IF NOT EXISTS feedback_type TEXT NOT NULL DEFAULT 'job_quality';
ALTER TABLE public.human_validation_feedback ADD COLUMN IF NOT EXISTS original_value TEXT;
ALTER TABLE public.human_validation_feedback ADD COLUMN IF NOT EXISTS corrected_value TEXT;
ALTER TABLE public.human_validation_feedback ADD COLUMN IF NOT EXISTS review_status TEXT NOT NULL DEFAULT 'pending';
ALTER TABLE public.human_validation_feedback ADD COLUMN IF NOT EXISTS source_payload JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE public.human_validation_feedback ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS public.labor_qa_audit_runs (
    id BIGSERIAL PRIMARY KEY,
    correlation_id TEXT NOT NULL UNIQUE,
    sample_size INTEGER NOT NULL DEFAULT 0,
    sampled_jobs INTEGER NOT NULL DEFAULT 0,
    suspicious_companies INTEGER NOT NULL DEFAULT 0,
    duplicate_groups INTEGER NOT NULL DEFAULT 0,
    guardrail_status TEXT NOT NULL DEFAULT 'unknown',
    report_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.labor_qa_job_sample (
    id BIGSERIAL PRIMARY KEY,
    audit_run_id BIGINT REFERENCES public.labor_qa_audit_runs(id) ON DELETE CASCADE,
    job_id BIGINT REFERENCES public.jobs(id) ON DELETE CASCADE,
    source TEXT,
    title TEXT,
    company TEXT,
    curation_level TEXT,
    job_probability_score NUMERIC(6,4),
    completeness_score NUMERIC(6,4),
    duplicate_group_id TEXT,
    qa_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (audit_run_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_human_validation_feedback_job ON public.human_validation_feedback(job_id);
CREATE INDEX IF NOT EXISTS idx_human_validation_feedback_status ON public.human_validation_feedback(review_status, feedback_type);
CREATE INDEX IF NOT EXISTS idx_labor_qa_job_sample_run ON public.labor_qa_job_sample(audit_run_id);
CREATE INDEX IF NOT EXISTS idx_labor_qa_audit_created ON public.labor_qa_audit_runs(created_at DESC);
