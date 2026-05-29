-- Labor & Curriculum Intelligence semantic layer.
-- Safe incremental migration after acquisition, enrichment and QA layers.

ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS canonical_company_name TEXT;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS company_resolution_confidence NUMERIC(6,4) NOT NULL DEFAULT 0;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS inferred_company TEXT;
ALTER TABLE public.jobs ADD COLUMN IF NOT EXISTS resolution_method TEXT;

ALTER TABLE public.human_validation_feedback ADD COLUMN IF NOT EXISTS recommendation_feedback TEXT;
ALTER TABLE public.human_validation_feedback ADD COLUMN IF NOT EXISTS role_correction TEXT;
ALTER TABLE public.human_validation_feedback ADD COLUMN IF NOT EXISTS company_resolution_override TEXT;
ALTER TABLE public.human_validation_feedback ADD COLUMN IF NOT EXISTS semantic_similarity_override NUMERIC(6,4);

CREATE TABLE IF NOT EXISTS public.company_aliases (
    id BIGSERIAL PRIMARY KEY,
    canonical_company_name TEXT NOT NULL,
    alias TEXT NOT NULL UNIQUE,
    alias_normalized TEXT NOT NULL UNIQUE,
    confidence NUMERIC(6,4) NOT NULL DEFAULT 0.85,
    source TEXT NOT NULL DEFAULT 'system',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.company_profiles (
    id BIGSERIAL PRIMARY KEY,
    canonical_company_name TEXT NOT NULL UNIQUE,
    dominant_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    dominant_clusters JSONB NOT NULL DEFAULT '[]'::jsonb,
    hiring_velocity NUMERIC(8,4) NOT NULL DEFAULT 0,
    technology_maturity TEXT NOT NULL DEFAULT 'emerging',
    ai_adoption_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    bi_maturity_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    cloud_maturity_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.company_skill_affinity (
    id BIGSERIAL PRIMARY KEY,
    canonical_company_name TEXT NOT NULL,
    canonical_skill TEXT NOT NULL,
    affinity_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    evidence_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (canonical_company_name, canonical_skill)
);

CREATE TABLE IF NOT EXISTS public.company_cluster_affinity (
    id BIGSERIAL PRIMARY KEY,
    canonical_company_name TEXT NOT NULL,
    cluster_name TEXT NOT NULL,
    affinity_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    evidence_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (canonical_company_name, cluster_name)
);

CREATE TABLE IF NOT EXISTS public.company_trend_metrics (
    id BIGSERIAL PRIMARY KEY,
    canonical_company_name TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value NUMERIC(10,4) NOT NULL DEFAULT 0,
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (canonical_company_name, metric_name)
);

CREATE TABLE IF NOT EXISTS public.recommendation_intelligence (
    id BIGSERIAL PRIMARY KEY,
    recommendation_type TEXT NOT NULL,
    target_entity TEXT,
    target_company TEXT,
    recommendation_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    recommendation_reasoning TEXT NOT NULL,
    recommendation_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.semantic_role_clusters (
    id BIGSERIAL PRIMARY KEY,
    role_title TEXT NOT NULL,
    role_family TEXT NOT NULL,
    semantic_role_cluster TEXT NOT NULL,
    role_similarity_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    centrality_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (role_title, semantic_role_cluster)
);

CREATE TABLE IF NOT EXISTS public.occupational_graph_edges (
    id BIGSERIAL PRIMARY KEY,
    source_role TEXT NOT NULL,
    target_role TEXT NOT NULL,
    edge_type TEXT NOT NULL DEFAULT 'semantic_similarity',
    weight NUMERIC(6,4) NOT NULL DEFAULT 0,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_role, target_role, edge_type)
);

CREATE TABLE IF NOT EXISTS public.career_transitions (
    id BIGSERIAL PRIMARY KEY,
    source_role TEXT NOT NULL,
    target_role TEXT NOT NULL,
    role_progression_probability NUMERIC(6,4) NOT NULL DEFAULT 0,
    transition_skill_gaps JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommended_next_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_role, target_role)
);

CREATE TABLE IF NOT EXISTS public.market_forecasts (
    id BIGSERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    growth_velocity NUMERIC(8,4) NOT NULL DEFAULT 0,
    forecast_confidence NUMERIC(6,4) NOT NULL DEFAULT 0,
    market_phase TEXT NOT NULL DEFAULT 'emerging',
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (entity_type, entity_name)
);

CREATE INDEX IF NOT EXISTS idx_jobs_canonical_company ON public.jobs(canonical_company_name);
CREATE INDEX IF NOT EXISTS idx_company_profiles_maturity ON public.company_profiles(technology_maturity);
CREATE INDEX IF NOT EXISTS idx_company_skill_affinity_skill ON public.company_skill_affinity(canonical_skill, affinity_score DESC);
CREATE INDEX IF NOT EXISTS idx_semantic_role_clusters_family ON public.semantic_role_clusters(role_family);
CREATE INDEX IF NOT EXISTS idx_market_forecasts_phase ON public.market_forecasts(entity_type, market_phase, growth_velocity DESC);
