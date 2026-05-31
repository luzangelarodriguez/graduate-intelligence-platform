BEGIN;

DO $$
DECLARE
    relkind CHAR;
BEGIN
    SELECT c.relkind
    INTO relkind
    FROM pg_class c
    INNER JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relname = 'program_intelligence';

    IF relkind = 'm' THEN
        EXECUTE 'DROP MATERIALIZED VIEW IF EXISTS public.program_intelligence CASCADE';
    ELSIF relkind = 'v' THEN
        EXECUTE 'DROP VIEW IF EXISTS public.program_intelligence CASCADE';
    ELSIF relkind = 'r' THEN
        EXECUTE 'DROP TABLE IF EXISTS public.program_intelligence CASCADE';
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.program_intelligence (
    program_id BIGINT PRIMARY KEY,
    canonical_program_key TEXT NOT NULL,
    program_name TEXT NOT NULL,
    program_role TEXT NOT NULL DEFAULT '',
    alignment_score NUMERIC(8, 2) NOT NULL DEFAULT 0,
    risk_score NUMERIC(8, 2) NOT NULL DEFAULT 0,
    risk_level TEXT NOT NULL DEFAULT 'low',
    gap_count INTEGER NOT NULL DEFAULT 0,
    top_gaps JSONB NOT NULL DEFAULT '[]'::jsonb,
    top_recommendations JSONB NOT NULL DEFAULT '[]'::jsonb,
    forecast_signals JSONB NOT NULL DEFAULT '[]'::jsonb,
    role_signals JSONB NOT NULL DEFAULT '[]'::jsonb,
    emerging_technologies JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommended_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    business_justification TEXT NOT NULL DEFAULT '',
    supporting_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_tables JSONB NOT NULL DEFAULT '[]'::jsonb,
    confidence NUMERIC(6, 4) NOT NULL DEFAULT 0,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_program_intelligence_canonical_program_key
    ON public.program_intelligence (canonical_program_key);

CREATE INDEX IF NOT EXISTS idx_program_intelligence_risk_score
    ON public.program_intelligence(risk_score DESC, alignment_score DESC);

CREATE INDEX IF NOT EXISTS idx_program_intelligence_alignment_score
    ON public.program_intelligence(alignment_score DESC, risk_score DESC);

CREATE INDEX IF NOT EXISTS idx_program_intelligence_generated_at
    ON public.program_intelligence(generated_at DESC);

COMMIT;
