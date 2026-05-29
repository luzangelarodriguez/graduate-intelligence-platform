CREATE TABLE IF NOT EXISTS public.observatory_metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_name TEXT NOT NULL,
    metric_category TEXT NOT NULL,
    metric_value NUMERIC(18,4) NOT NULL DEFAULT 0,
    metric_period TEXT NOT NULL,
    confidence_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    source_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (metric_name, metric_period)
);

CREATE TABLE IF NOT EXISTS public.curriculum_gap_observatory (
    id BIGSERIAL PRIMARY KEY,
    specialization TEXT NOT NULL,
    missing_skill TEXT NOT NULL,
    market_demand_score NUMERIC(18,4) NOT NULL DEFAULT 0,
    curriculum_coverage_score NUMERIC(18,4) NOT NULL DEFAULT 0,
    urgency_score NUMERIC(18,4) NOT NULL DEFAULT 0,
    emergence_score NUMERIC(18,4) NOT NULL DEFAULT 0,
    recommendation TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (specialization, missing_skill)
);

CREATE TABLE IF NOT EXISTS public.recommendation_observatory (
    id BIGSERIAL PRIMARY KEY,
    recommendation_type TEXT NOT NULL,
    target_role TEXT NOT NULL,
    target_company TEXT NOT NULL,
    recommendation_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    recommendation_reasoning TEXT NOT NULL,
    recommendation_confidence NUMERIC(6,4) NOT NULL DEFAULT 0,
    recommendation_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    metric_period TEXT NOT NULL DEFAULT 'current',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (recommendation_type, target_role, target_company, metric_period)
);

CREATE TABLE IF NOT EXISTS public.semantic_role_graph (
    id BIGSERIAL PRIMARY KEY,
    source_role TEXT NOT NULL,
    target_role TEXT NOT NULL,
    similarity_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    transition_probability NUMERIC(6,4) NOT NULL DEFAULT 0,
    shared_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    cluster_affinity TEXT NOT NULL DEFAULT '',
    centrality_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    metric_period TEXT NOT NULL DEFAULT 'current',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_role, target_role, metric_period)
);

CREATE TABLE IF NOT EXISTS public.company_observatory (
    id BIGSERIAL PRIMARY KEY,
    company TEXT NOT NULL,
    dominant_stack TEXT NOT NULL DEFAULT '',
    dominant_cluster TEXT NOT NULL DEFAULT '',
    hiring_velocity NUMERIC(18,4) NOT NULL DEFAULT 0,
    ai_adoption_score NUMERIC(18,4) NOT NULL DEFAULT 0,
    cloud_maturity_score NUMERIC(18,4) NOT NULL DEFAULT 0,
    bi_maturity_score NUMERIC(18,4) NOT NULL DEFAULT 0,
    technology_maturity TEXT NOT NULL DEFAULT 'emerging',
    top_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    top_clusters JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    metric_period TEXT NOT NULL DEFAULT 'current',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company, metric_period)
);

CREATE TABLE IF NOT EXISTS public.emerging_technology_observatory (
    id BIGSERIAL PRIMARY KEY,
    technology TEXT NOT NULL,
    emergence_score NUMERIC(18,4) NOT NULL DEFAULT 0,
    growth_velocity NUMERIC(18,4) NOT NULL DEFAULT 0,
    adoption_trend TEXT NOT NULL DEFAULT 'stable',
    forecast_confidence NUMERIC(6,4) NOT NULL DEFAULT 0,
    source_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    metric_period TEXT NOT NULL DEFAULT 'current',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (technology, metric_period)
);

ALTER TABLE public.human_validation_feedback
    ADD COLUMN IF NOT EXISTS recommendation_acceptance BOOLEAN;

ALTER TABLE public.human_validation_feedback
    ADD COLUMN IF NOT EXISTS recommendation_rejection_reason TEXT;

ALTER TABLE public.human_validation_feedback
    ADD COLUMN IF NOT EXISTS curriculum_gap_override TEXT;

ALTER TABLE public.human_validation_feedback
    ADD COLUMN IF NOT EXISTS company_resolution_override TEXT;

ALTER TABLE public.human_validation_feedback
    ADD COLUMN IF NOT EXISTS semantic_role_override TEXT;

CREATE INDEX IF NOT EXISTS idx_observatory_metrics_category ON public.observatory_metrics(metric_category, metric_period);
CREATE INDEX IF NOT EXISTS idx_curriculum_gap_observatory_specialization ON public.curriculum_gap_observatory(specialization, urgency_score DESC);
CREATE INDEX IF NOT EXISTS idx_recommendation_observatory_type ON public.recommendation_observatory(recommendation_type, metric_period);
CREATE INDEX IF NOT EXISTS idx_semantic_role_graph_source ON public.semantic_role_graph(source_role, metric_period);
CREATE INDEX IF NOT EXISTS idx_company_observatory_company ON public.company_observatory(company, metric_period);
CREATE INDEX IF NOT EXISTS idx_emerging_technology_observatory_technology ON public.emerging_technology_observatory(technology, metric_period);
