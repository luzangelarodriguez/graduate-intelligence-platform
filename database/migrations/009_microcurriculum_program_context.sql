-- Graduate Intelligence Platform
-- Migration 009: contextual microcurriculum intelligence by specialization.
-- Non-destructive.

ALTER TABLE IF EXISTS public.microcurriculos
ADD COLUMN IF NOT EXISTS specialization_id INTEGER REFERENCES public.especializaciones(id) ON DELETE SET NULL;

ALTER TABLE IF EXISTS public.microcurriculos
ADD COLUMN IF NOT EXISTS specialization_name TEXT;

CREATE INDEX IF NOT EXISTS ix_microcurriculos_specialization
ON public.microcurriculos(specialization_id, created_at DESC);

CREATE TABLE IF NOT EXISTS public.microcurriculo_keywords (
    id BIGSERIAL PRIMARY KEY,
    microcurriculo_id BIGINT NOT NULL REFERENCES public.microcurriculos(id) ON DELETE CASCADE,
    specialization_id INTEGER REFERENCES public.especializaciones(id) ON DELETE SET NULL,
    keyword TEXT NOT NULL,
    keyword_type TEXT NOT NULL DEFAULT 'keyword',
    frequency INTEGER NOT NULL DEFAULT 1,
    confidence_score NUMERIC(5, 4) NOT NULL DEFAULT 0.70,
    source_document TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (microcurriculo_id, keyword, keyword_type)
);

CREATE INDEX IF NOT EXISTS ix_microcurriculo_keywords_specialization
ON public.microcurriculo_keywords(specialization_id, keyword_type, frequency DESC);

CREATE TABLE IF NOT EXISTS public.microcurriculum_program_contexts (
    specialization_id INTEGER PRIMARY KEY REFERENCES public.especializaciones(id) ON DELETE CASCADE,
    specialization_name TEXT NOT NULL,
    source_directory TEXT NOT NULL,
    documents_processed INTEGER NOT NULL DEFAULT 0,
    detected_domain TEXT,
    detected_subdomain TEXT,
    confidence NUMERIC(5, 4) NOT NULL DEFAULT 0,
    subjects JSONB NOT NULL DEFAULT '[]'::jsonb,
    technical_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    transversal_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    methodologies JSONB NOT NULL DEFAULT '[]'::jsonb,
    tools JSONB NOT NULL DEFAULT '[]'::jsonb,
    platforms JSONB NOT NULL DEFAULT '[]'::jsonb,
    technologies JSONB NOT NULL DEFAULT '[]'::jsonb,
    bibliography JSONB NOT NULL DEFAULT '[]'::jsonb,
    keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    occupational_profiles JSONB NOT NULL DEFAULT '[]'::jsonb,
    real_market_gaps JSONB NOT NULL DEFAULT '[]'::jsonb,
    strengthening_areas JSONB NOT NULL DEFAULT '[]'::jsonb,
    redundancies JSONB NOT NULL DEFAULT '[]'::jsonb,
    labor_roles JSONB NOT NULL DEFAULT '[]'::jsonb,
    benchmarking JSONB NOT NULL DEFAULT '[]'::jsonb,
    scores JSONB NOT NULL DEFAULT '{}'::jsonb,
    executive_narrative TEXT NOT NULL DEFAULT '',
    raw_context JSONB NOT NULL DEFAULT '{}'::jsonb,
    indexed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

