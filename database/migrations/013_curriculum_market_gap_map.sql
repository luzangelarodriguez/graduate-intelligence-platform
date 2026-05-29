-- Curriculum-market skill intelligence map.
-- Safe incremental migration: no DROP, no TRUNCATE.

CREATE TABLE IF NOT EXISTS public.labor_market_skill_universe (
    id BIGSERIAL PRIMARY KEY,
    skill TEXT NOT NULL,
    skill_type TEXT,
    total_weight NUMERIC(8,4) NOT NULL DEFAULT 0,
    evidence_count INTEGER NOT NULL DEFAULT 0,
    source_breakdown JSONB NOT NULL DEFAULT '{}'::jsonb,
    roles JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(skill)
);

CREATE TABLE IF NOT EXISTS public.occupational_skill_clusters (
    id BIGSERIAL PRIMARY KEY,
    cluster_name TEXT NOT NULL,
    skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    total_weight NUMERIC(8,4) NOT NULL DEFAULT 0,
    evidence_count INTEGER NOT NULL DEFAULT 0,
    dominant_sources JSONB NOT NULL DEFAULT '{}'::jsonb,
    representative_roles JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_strong_market_signal BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(cluster_name)
);

CREATE TABLE IF NOT EXISTS public.specialization_curriculum_graph (
    id BIGSERIAL PRIMARY KEY,
    specialization_id TEXT NOT NULL,
    specialization_name TEXT NOT NULL,
    source_root TEXT,
    documents_processed INTEGER NOT NULL DEFAULT 0,
    skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    profile_concepts JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(specialization_id)
);

CREATE TABLE IF NOT EXISTS public.specialization_skill_affinity (
    id BIGSERIAL PRIMARY KEY,
    specialization_id TEXT NOT NULL,
    skill TEXT NOT NULL,
    cluster_name TEXT,
    affinity_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    coverage_status TEXT NOT NULL,
    matched_curriculum_skill TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(specialization_id, skill)
);

CREATE TABLE IF NOT EXISTS public.curriculum_market_gaps (
    id BIGSERIAL PRIMARY KEY,
    specialization_id TEXT NOT NULL,
    skill TEXT NOT NULL,
    cluster_name TEXT,
    coverage_status TEXT NOT NULL,
    evidence_weight NUMERIC(8,4) NOT NULL DEFAULT 0,
    evidence_sources JSONB NOT NULL DEFAULT '{}'::jsonb,
    affinity_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    roles JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommendation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(specialization_id, skill)
);

CREATE TABLE IF NOT EXISTS public.curriculum_recommendation_candidates (
    id BIGSERIAL PRIMARY KEY,
    specialization_id TEXT NOT NULL,
    skill TEXT NOT NULL,
    cluster_name TEXT,
    priority TEXT,
    action TEXT NOT NULL,
    evidence_weight NUMERIC(8,4) NOT NULL DEFAULT 0,
    roles JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_labor_market_skill_universe_weight
ON public.labor_market_skill_universe(total_weight DESC);

CREATE INDEX IF NOT EXISTS ix_curriculum_market_gaps_specialization_status
ON public.curriculum_market_gaps(specialization_id, coverage_status);

CREATE INDEX IF NOT EXISTS ix_specialization_skill_affinity_specialization
ON public.specialization_skill_affinity(specialization_id, affinity_score DESC);

