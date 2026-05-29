-- Occupational labor clustering layer for Academic Labor Intelligence Graph.
-- Safe incremental migration: no DROP, no TRUNCATE.

CREATE TABLE IF NOT EXISTS public.labor_occupational_clusters (
    id BIGSERIAL PRIMARY KEY,
    cluster_name TEXT NOT NULL,
    semantic_summary TEXT,
    dominant_skills JSONB DEFAULT '[]'::jsonb,
    dominant_tools JSONB DEFAULT '[]'::jsonb,
    dominant_roles JSONB DEFAULT '[]'::jsonb,
    market_frequency INTEGER NOT NULL DEFAULT 0,
    avg_salary_estimate NUMERIC(14,2),
    growth_signal TEXT,
    embedding_centroid JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.labor_cluster_job_relationships (
    id BIGSERIAL PRIMARY KEY,
    cluster_id BIGINT REFERENCES public.labor_occupational_clusters(id) ON DELETE CASCADE,
    job_source TEXT,
    job_source_url TEXT,
    job_title TEXT,
    relationship_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    evidence JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.labor_cluster_specialization_affinity (
    id BIGSERIAL PRIMARY KEY,
    cluster_id BIGINT REFERENCES public.labor_occupational_clusters(id) ON DELETE CASCADE,
    specialization_id TEXT,
    specialization_name TEXT NOT NULL,
    affinity_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    affinity_evidence JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.labor_cluster_skill_signals (
    id BIGSERIAL PRIMARY KEY,
    cluster_id BIGINT REFERENCES public.labor_occupational_clusters(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    skill_type TEXT,
    labor_frequency INTEGER NOT NULL DEFAULT 0,
    signal_strength NUMERIC(6,4) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.labor_cluster_market_trends (
    id BIGSERIAL PRIMARY KEY,
    cluster_id BIGINT REFERENCES public.labor_occupational_clusters(id) ON DELETE CASCADE,
    emerging_skill TEXT NOT NULL,
    gap_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    curricular_coverage NUMERIC(6,4) NOT NULL DEFAULT 0,
    labor_frequency INTEGER NOT NULL DEFAULT 0,
    trend_signal TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_labor_occupational_clusters_name
ON public.labor_occupational_clusters(cluster_name);

CREATE INDEX IF NOT EXISTS ix_labor_cluster_affinity_specialization
ON public.labor_cluster_specialization_affinity(specialization_name, affinity_score DESC);

CREATE INDEX IF NOT EXISTS ix_labor_cluster_market_trends_skill
ON public.labor_cluster_market_trends(emerging_skill, gap_score DESC);
