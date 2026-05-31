BEGIN;

CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE TABLE IF NOT EXISTS public.skill_normalization_mappings (
    id BIGSERIAL PRIMARY KEY,
    raw_skill TEXT NOT NULL,
    raw_skill_normalized TEXT NOT NULL UNIQUE,
    canonical_skill_id BIGINT REFERENCES public.canonical_skills(id) ON DELETE SET NULL,
    canonical_skill TEXT NOT NULL,
    match_method TEXT NOT NULL DEFAULT 'exact',
    confidence_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    source_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.program_skill_gap (
    id BIGSERIAL PRIMARY KEY,
    program_id BIGINT NOT NULL REFERENCES public.especializaciones(id) ON DELETE CASCADE,
    gap_key TEXT NOT NULL,
    canonical_skill_id BIGINT REFERENCES public.canonical_skills(id) ON DELETE SET NULL,
    missing_skill TEXT NOT NULL,
    gap_type TEXT NOT NULL DEFAULT 'curricular',
    market_pressure NUMERIC(8,4) NOT NULL DEFAULT 0,
    employability_impact NUMERIC(8,4) NOT NULL DEFAULT 0,
    urgency_score NUMERIC(8,4) NOT NULL DEFAULT 0,
    confidence_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    source_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (program_id, gap_key)
);

CREATE TABLE IF NOT EXISTS public.program_market_pressure (
    id BIGSERIAL PRIMARY KEY,
    program_id BIGINT NOT NULL REFERENCES public.especializaciones(id) ON DELETE CASCADE,
    horizon_months INTEGER NOT NULL DEFAULT 12,
    pressure_score NUMERIC(8,4) NOT NULL DEFAULT 0,
    employer_count INTEGER NOT NULL DEFAULT 0,
    skill_count INTEGER NOT NULL DEFAULT 0,
    forecast_coverage_score NUMERIC(8,4) NOT NULL DEFAULT 0,
    confidence_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    source_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (program_id, horizon_months)
);

CREATE TABLE IF NOT EXISTS public.program_employability_index (
    program_id BIGINT PRIMARY KEY REFERENCES public.especializaciones(id) ON DELETE CASCADE,
    employability_score NUMERIC(8,4) NOT NULL DEFAULT 0,
    employability_gain NUMERIC(8,4) NOT NULL DEFAULT 0,
    employability_loss NUMERIC(8,4) NOT NULL DEFAULT 0,
    expected_alignment_improvement NUMERIC(8,4) NOT NULL DEFAULT 0,
    confidence_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    source_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.program_risk_index (
    id BIGSERIAL PRIMARY KEY,
    program_id BIGINT NOT NULL REFERENCES public.especializaciones(id) ON DELETE CASCADE,
    horizon_months INTEGER NOT NULL DEFAULT 12,
    risk_score NUMERIC(8,4) NOT NULL DEFAULT 0,
    risk_level TEXT NOT NULL DEFAULT 'low',
    risk_explanation TEXT NOT NULL DEFAULT '',
    confidence_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    source_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (program_id, horizon_months)
);

CREATE TABLE IF NOT EXISTS public.skill_trend_forecast (
    id BIGSERIAL PRIMARY KEY,
    canonical_skill_id BIGINT REFERENCES public.canonical_skills(id) ON DELETE SET NULL,
    skill_name TEXT NOT NULL,
    horizon_months INTEGER NOT NULL DEFAULT 12,
    growth_score NUMERIC(8,4) NOT NULL DEFAULT 0,
    decline_score NUMERIC(8,4) NOT NULL DEFAULT 0,
    confidence_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    source_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (skill_name, horizon_months)
);

CREATE TABLE IF NOT EXISTS public.technology_forecasts (
    id BIGSERIAL PRIMARY KEY,
    entity_name TEXT NOT NULL,
    horizon_months INTEGER NOT NULL DEFAULT 12,
    growth_velocity NUMERIC(8,4) NOT NULL DEFAULT 0,
    forecast_confidence NUMERIC(6,4) NOT NULL DEFAULT 0,
    market_phase TEXT NOT NULL DEFAULT 'stable',
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    source_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (entity_name, horizon_months)
);

CREATE TABLE IF NOT EXISTS public.company_forecasts (
    id BIGSERIAL PRIMARY KEY,
    entity_name TEXT NOT NULL,
    horizon_months INTEGER NOT NULL DEFAULT 12,
    growth_velocity NUMERIC(8,4) NOT NULL DEFAULT 0,
    forecast_confidence NUMERIC(6,4) NOT NULL DEFAULT 0,
    market_phase TEXT NOT NULL DEFAULT 'stable',
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    source_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (entity_name, horizon_months)
);

CREATE TABLE IF NOT EXISTS public.role_forecasts (
    id BIGSERIAL PRIMARY KEY,
    entity_name TEXT NOT NULL,
    horizon_months INTEGER NOT NULL DEFAULT 12,
    growth_velocity NUMERIC(8,4) NOT NULL DEFAULT 0,
    forecast_confidence NUMERIC(6,4) NOT NULL DEFAULT 0,
    market_phase TEXT NOT NULL DEFAULT 'stable',
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    source_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (entity_name, horizon_months)
);

CREATE TABLE IF NOT EXISTS public.curriculum_simulations (
    id BIGSERIAL PRIMARY KEY,
    simulation_key TEXT NOT NULL UNIQUE,
    program_id BIGINT NOT NULL REFERENCES public.especializaciones(id) ON DELETE CASCADE,
    proposed_skills JSONB NOT NULL DEFAULT '[]'::jsonb,
    projected_alignment_score NUMERIC(8,4) NOT NULL DEFAULT 0,
    projected_risk_score NUMERIC(8,4) NOT NULL DEFAULT 0,
    projected_employability_gain NUMERIC(8,4) NOT NULL DEFAULT 0,
    projected_gap_reduction NUMERIC(8,4) NOT NULL DEFAULT 0,
    confidence_score NUMERIC(6,4) NOT NULL DEFAULT 0,
    explanation TEXT NOT NULL DEFAULT '',
    source_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.recommendation_observatory
    ADD COLUMN IF NOT EXISTS estimated_alignment_increase NUMERIC(8,4) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS estimated_employability_gain NUMERIC(8,4) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS estimated_risk_reduction NUMERIC(8,4) NOT NULL DEFAULT 0;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_recommendation_observatory_signature'
          AND conrelid = 'public.recommendation_observatory'::regclass
    ) THEN
        ALTER TABLE public.recommendation_observatory
            ADD CONSTRAINT uq_recommendation_observatory_signature
            UNIQUE (recommendation_type, target_role, target_company, metric_period);
    END IF;
END $$;

UPDATE public.recommendation_observatory
SET
    estimated_alignment_increase = COALESCE(
        NULLIF(recommendation_payload->>'estimated_alignment_increase', '')::numeric,
        NULLIF(recommendation_payload->>'market_alignment_score', '')::numeric,
        recommendation_confidence * 10
    ),
    estimated_employability_gain = COALESCE(
        NULLIF(recommendation_payload->>'estimated_employability_gain', '')::numeric,
        recommendation_confidence * 8
    ),
    estimated_risk_reduction = COALESCE(
        NULLIF(recommendation_payload->>'estimated_risk_reduction', '')::numeric,
        CASE
            WHEN recommendation_confidence > 0 THEN LEAST(15, recommendation_confidence * 10)
            ELSE 0
        END
    )
WHERE estimated_alignment_increase = 0
   OR estimated_employability_gain = 0
   OR estimated_risk_reduction = 0;

CREATE INDEX IF NOT EXISTS idx_program_skill_gap_program ON public.program_skill_gap(program_id, urgency_score DESC);
CREATE INDEX IF NOT EXISTS idx_program_market_pressure_program ON public.program_market_pressure(program_id, horizon_months, pressure_score DESC);
CREATE INDEX IF NOT EXISTS idx_program_employability_index_score ON public.program_employability_index(employability_score DESC);
CREATE INDEX IF NOT EXISTS idx_program_risk_index_score ON public.program_risk_index(risk_score DESC, horizon_months);
CREATE INDEX IF NOT EXISTS idx_skill_trend_forecast_skill ON public.skill_trend_forecast(skill_name, horizon_months);
CREATE INDEX IF NOT EXISTS idx_technology_forecasts_entity ON public.technology_forecasts(entity_name, horizon_months);
CREATE INDEX IF NOT EXISTS idx_company_forecasts_entity ON public.company_forecasts(entity_name, horizon_months);
CREATE INDEX IF NOT EXISTS idx_role_forecasts_entity ON public.role_forecasts(entity_name, horizon_months);
CREATE INDEX IF NOT EXISTS idx_curriculum_simulations_program ON public.curriculum_simulations(program_id, generated_at DESC);

COMMIT;
