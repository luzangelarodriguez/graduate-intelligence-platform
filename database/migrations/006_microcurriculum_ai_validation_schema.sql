-- Graduate Intelligence Platform
-- Migration 006: functional AI validation persistence for curricular QA.

CREATE TABLE IF NOT EXISTS public.microcurriculum_ai_validation_runs (
    run_id TEXT PRIMARY KEY,
    documents_processed INTEGER NOT NULL DEFAULT 0,
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.microcurriculum_ai_validation_items (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES public.microcurriculum_ai_validation_runs(run_id) ON DELETE CASCADE,
    source_document TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    detected_domain TEXT,
    expected_domain TEXT,
    confidence NUMERIC(5, 4),
    precision_approx NUMERIC(5, 4),
    recall_approx NUMERIC(5, 4),
    domain_contamination_rate NUMERIC(5, 4),
    recommendation_coherence_score NUMERIC(5, 4),
    taxonomy_coverage NUMERIC(5, 4),
    contextual_understanding_score NUMERIC(5, 4),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_microcurriculum_ai_validation_items_run
ON public.microcurriculum_ai_validation_items(run_id);

CREATE INDEX IF NOT EXISTS ix_microcurriculum_ai_validation_items_domain
ON public.microcurriculum_ai_validation_items(detected_domain, confidence DESC);

