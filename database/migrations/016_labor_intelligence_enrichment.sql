-- Labor intelligence enrichment: embeddings, dedupe, company intelligence,
-- emerging skills and feedback infrastructure. Safe incremental migration.

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

CREATE TABLE IF NOT EXISTS public.job_embeddings (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT NOT NULL REFERENCES public.jobs(id) ON DELETE CASCADE,
    embedding_scope TEXT NOT NULL DEFAULT 'job',
    embedding_vector JSONB NOT NULL DEFAULT '[]'::jsonb,
    model_version TEXT NOT NULL,
    embedding_created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (job_id, embedding_scope, model_version)
);

CREATE TABLE IF NOT EXISTS public.skill_embeddings (
    id BIGSERIAL PRIMARY KEY,
    canonical_skill_id BIGINT REFERENCES public.canonical_skills(id) ON DELETE CASCADE,
    canonical_skill TEXT NOT NULL,
    embedding_vector JSONB NOT NULL DEFAULT '[]'::jsonb,
    model_version TEXT NOT NULL,
    embedding_created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (canonical_skill, model_version)
);

CREATE TABLE IF NOT EXISTS public.company_embeddings (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    embedding_vector JSONB NOT NULL DEFAULT '[]'::jsonb,
    model_version TEXT NOT NULL,
    embedding_created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, model_version)
);

CREATE TABLE IF NOT EXISTS public.company_skill_profiles (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    canonical_skill TEXT NOT NULL,
    skill_category TEXT,
    job_count INTEGER NOT NULL DEFAULT 0,
    avg_confidence NUMERIC(6,4) NOT NULL DEFAULT 0,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, canonical_skill)
);

CREATE TABLE IF NOT EXISTS public.company_cluster_profiles (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    dominant_cluster TEXT NOT NULL,
    job_count INTEGER NOT NULL DEFAULT 0,
    market_maturity TEXT NOT NULL DEFAULT 'emerging',
    top_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, dominant_cluster)
);

CREATE TABLE IF NOT EXISTS public.emerging_skill_candidates (
    id BIGSERIAL PRIMARY KEY,
    candidate TEXT NOT NULL UNIQUE,
    normalized_candidate TEXT NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    evidence_count INTEGER NOT NULL DEFAULT 0,
    growth_velocity NUMERIC(8,4) NOT NULL DEFAULT 0,
    emergence_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    source_payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

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

CREATE TABLE IF NOT EXISTS public.ml_prediction_explanations (
    id BIGSERIAL PRIMARY KEY,
    job_id BIGINT REFERENCES public.jobs(id) ON DELETE CASCADE,
    prediction_confidence NUMERIC(6,4) NOT NULL DEFAULT 0,
    top_features JSONB NOT NULL DEFAULT '[]'::jsonb,
    explanation_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    model_version TEXT NOT NULL DEFAULT 'curriculum_ml_v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_job_embeddings_job ON public.job_embeddings(job_id);
CREATE INDEX IF NOT EXISTS idx_company_skill_profiles_skill ON public.company_skill_profiles(canonical_skill, job_count DESC);
CREATE INDEX IF NOT EXISTS idx_company_cluster_profiles_cluster ON public.company_cluster_profiles(dominant_cluster, job_count DESC);
CREATE INDEX IF NOT EXISTS idx_emerging_skill_score ON public.emerging_skill_candidates(emergence_score DESC);
CREATE INDEX IF NOT EXISTS idx_human_validation_feedback_job ON public.human_validation_feedback(job_id);
