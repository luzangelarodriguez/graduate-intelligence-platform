-- Enterprise labor intelligence schema.
-- Non-destructive migration: adds the canonical tables and missing columns only.

CREATE TABLE IF NOT EXISTS public.domains (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.skills_master (
    id SERIAL PRIMARY KEY,
    canonical_name TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    tipo TEXT NOT NULL,
    descripcion TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.skills_alias (
    alias TEXT PRIMARY KEY,
    canonical_skill TEXT NOT NULL REFERENCES public.skills_master(canonical_name) ON UPDATE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.empleos (
    id TEXT PRIMARY KEY,
    portal TEXT,
    titulo TEXT,
    titulo_normalizado TEXT,
    empresa TEXT,
    ciudad TEXT,
    modalidad TEXT,
    salario TEXT,
    descripcion TEXT,
    seniority TEXT,
    sector TEXT,
    dominio TEXT,
    fecha_publicacion DATE,
    url TEXT,
    hash_contenido TEXT,
    embedding JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.empleos ADD COLUMN IF NOT EXISTS portal TEXT;
ALTER TABLE public.empleos ADD COLUMN IF NOT EXISTS titulo_normalizado TEXT;
ALTER TABLE public.empleos ADD COLUMN IF NOT EXISTS empresa TEXT;
ALTER TABLE public.empleos ADD COLUMN IF NOT EXISTS ciudad TEXT;
ALTER TABLE public.empleos ADD COLUMN IF NOT EXISTS modalidad TEXT;
ALTER TABLE public.empleos ADD COLUMN IF NOT EXISTS salario TEXT;
ALTER TABLE public.empleos ADD COLUMN IF NOT EXISTS descripcion TEXT;
ALTER TABLE public.empleos ADD COLUMN IF NOT EXISTS seniority TEXT;
ALTER TABLE public.empleos ADD COLUMN IF NOT EXISTS sector TEXT;
ALTER TABLE public.empleos ADD COLUMN IF NOT EXISTS dominio TEXT;
ALTER TABLE public.empleos ADD COLUMN IF NOT EXISTS fecha_publicacion DATE;
ALTER TABLE public.empleos ADD COLUMN IF NOT EXISTS url TEXT;
ALTER TABLE public.empleos ADD COLUMN IF NOT EXISTS hash_contenido TEXT;
ALTER TABLE public.empleos ADD COLUMN IF NOT EXISTS embedding JSONB;
ALTER TABLE public.empleos ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(5, 4);
ALTER TABLE public.empleos ADD COLUMN IF NOT EXISTS confidence_factors JSONB;
ALTER TABLE public.empleos ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS public.empleo_skills (
    id BIGSERIAL PRIMARY KEY,
    empleo_id TEXT NOT NULL REFERENCES public.empleos(id) ON DELETE CASCADE,
    skill_original TEXT,
    skill_normalized TEXT,
    skill_domain TEXT,
    tipo_skill TEXT,
    confianza_extraccion NUMERIC(5, 4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.empleo_skills ADD COLUMN IF NOT EXISTS id BIGSERIAL;
ALTER TABLE public.empleo_skills ADD COLUMN IF NOT EXISTS skill_original TEXT;
ALTER TABLE public.empleo_skills ADD COLUMN IF NOT EXISTS skill_normalized TEXT;
ALTER TABLE public.empleo_skills ADD COLUMN IF NOT EXISTS skill_domain TEXT;
ALTER TABLE public.empleo_skills ADD COLUMN IF NOT EXISTS tipo_skill TEXT;
ALTER TABLE public.empleo_skills ADD COLUMN IF NOT EXISTS confianza_extraccion NUMERIC(5, 4);
ALTER TABLE public.empleo_skills ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE UNIQUE INDEX IF NOT EXISTS ux_empleos_hash_contenido
ON public.empleos(hash_contenido)
WHERE hash_contenido IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_empleos_portal ON public.empleos(portal);
CREATE INDEX IF NOT EXISTS ix_empleos_dominio ON public.empleos(dominio);
CREATE INDEX IF NOT EXISTS ix_empleos_fecha_publicacion ON public.empleos(fecha_publicacion);
CREATE INDEX IF NOT EXISTS ix_empleos_confidence_score ON public.empleos(confidence_score);
CREATE INDEX IF NOT EXISTS ix_empleo_skills_empleo_id ON public.empleo_skills(empleo_id);
CREATE INDEX IF NOT EXISTS ix_empleo_skills_normalized ON public.empleo_skills(skill_normalized);
CREATE INDEX IF NOT EXISTS ix_empleo_skills_domain ON public.empleo_skills(skill_domain);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ux_empleo_skills_job_skill_type'
    ) THEN
        ALTER TABLE public.empleo_skills
        ADD CONSTRAINT ux_empleo_skills_job_skill_type
        UNIQUE (empleo_id, skill_normalized, tipo_skill);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.source_quality_metrics (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    success_rate NUMERIC(6, 4) NOT NULL DEFAULT 0,
    relevance_rate NUMERIC(6, 4) NOT NULL DEFAULT 0,
    timeout_rate NUMERIC(6, 4) NOT NULL DEFAULT 0,
    duplication_rate NUMERIC(6, 4) NOT NULL DEFAULT 0,
    extraction_date DATE NOT NULL DEFAULT CURRENT_DATE,
    raw_jobs INTEGER NOT NULL DEFAULT 0,
    normalized_jobs INTEGER NOT NULL DEFAULT 0,
    relevant_jobs INTEGER NOT NULL DEFAULT 0,
    timeout_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, extraction_date)
);

CREATE TABLE IF NOT EXISTS public.validated_jobs_gold (
    id BIGSERIAL PRIMARY KEY,
    empleo_id TEXT NOT NULL,
    dominio TEXT NOT NULL,
    validado BOOLEAN NOT NULL DEFAULT false,
    reviewer TEXT NOT NULL DEFAULT 'pending',
    fecha TIMESTAMPTZ NOT NULL DEFAULT now(),
    observaciones TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empleo_id, dominio)
);

CREATE TABLE IF NOT EXISTS public.skill_drift_events (
    id BIGSERIAL PRIMARY KEY,
    skill_normalized TEXT NOT NULL,
    skill_domain TEXT,
    current_count INTEGER NOT NULL DEFAULT 0,
    baseline_count INTEGER NOT NULL DEFAULT 0,
    growth_rate NUMERIC(10, 4) NOT NULL DEFAULT 0,
    detection_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status TEXT NOT NULL DEFAULT 'candidate',
    evidence JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (skill_normalized, detection_date)
);

CREATE TABLE IF NOT EXISTS public.xhr_endpoint_discovery (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    method TEXT,
    resource_type TEXT,
    status INTEGER,
    content_type TEXT,
    sample JSONB,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, url)
);

CREATE INDEX IF NOT EXISTS ix_source_quality_metrics_source_date
ON public.source_quality_metrics(source, extraction_date DESC);

CREATE INDEX IF NOT EXISTS ix_validated_jobs_gold_empleo
ON public.validated_jobs_gold(empleo_id);

CREATE INDEX IF NOT EXISTS ix_skill_drift_events_skill
ON public.skill_drift_events(skill_normalized);

CREATE INDEX IF NOT EXISTS ix_xhr_endpoint_discovery_source
ON public.xhr_endpoint_discovery(source);

CREATE TABLE IF NOT EXISTS public.extraction_runs (
    run_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'api_first',
    query TEXT,
    status TEXT NOT NULL DEFAULT 'started',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    raw_count INTEGER NOT NULL DEFAULT 0,
    silver_count INTEGER NOT NULL DEFAULT 0,
    gold_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS public.bronze_job_payloads (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES public.extraction_runs(run_id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    request_params JSONB,
    status_code INTEGER,
    payload JSONB NOT NULL,
    payload_hash TEXT NOT NULL UNIQUE,
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.silver_normalized_jobs (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES public.extraction_runs(run_id) ON DELETE CASCADE,
    bronze_payload_id BIGINT REFERENCES public.bronze_job_payloads(id) ON DELETE SET NULL,
    source TEXT NOT NULL,
    titulo TEXT,
    titulo_normalizado TEXT,
    empresa TEXT,
    ciudad TEXT,
    modalidad TEXT,
    salario TEXT,
    descripcion TEXT,
    seniority TEXT,
    sector TEXT,
    dominio TEXT,
    fecha_publicacion DATE,
    url TEXT,
    skills JSONB,
    metadata JSONB,
    hash_contenido TEXT,
    confidence_score NUMERIC(5, 4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.gold_validated_jobs (
    id BIGSERIAL PRIMARY KEY,
    silver_job_id TEXT NOT NULL REFERENCES public.silver_normalized_jobs(id) ON DELETE CASCADE,
    dominio TEXT NOT NULL,
    validado BOOLEAN NOT NULL DEFAULT false,
    reviewer TEXT NOT NULL DEFAULT 'pending',
    fecha TIMESTAMPTZ NOT NULL DEFAULT now(),
    observaciones TEXT,
    evidence_grade TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (silver_job_id, dominio)
);

CREATE TABLE IF NOT EXISTS public.relevance_scores (
    id BIGSERIAL PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES public.silver_normalized_jobs(id) ON DELETE CASCADE,
    run_id TEXT NOT NULL REFERENCES public.extraction_runs(run_id) ON DELETE CASCADE,
    source_weight NUMERIC(5, 4) NOT NULL DEFAULT 0,
    evidence_weight NUMERIC(5, 4) NOT NULL DEFAULT 0,
    domain_confidence NUMERIC(5, 4) NOT NULL DEFAULT 0,
    semantic_density NUMERIC(5, 4) NOT NULL DEFAULT 0,
    overall_score NUMERIC(5, 4) NOT NULL DEFAULT 0,
    factors JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (job_id, run_id)
);

CREATE INDEX IF NOT EXISTS ix_extraction_runs_source_started
ON public.extraction_runs(source, started_at DESC);

CREATE INDEX IF NOT EXISTS ix_bronze_job_payloads_run_source
ON public.bronze_job_payloads(run_id, source);

CREATE INDEX IF NOT EXISTS ix_silver_normalized_jobs_run_source
ON public.silver_normalized_jobs(run_id, source);

CREATE INDEX IF NOT EXISTS ix_silver_normalized_jobs_domain
ON public.silver_normalized_jobs(dominio);

CREATE INDEX IF NOT EXISTS ix_relevance_scores_overall
ON public.relevance_scores(overall_score DESC);

CREATE TABLE IF NOT EXISTS public.api_sources_registry (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL DEFAULT 'GET',
    response_type TEXT,
    confidence NUMERIC(5, 4) NOT NULL DEFAULT 0,
    seo_noise BOOLEAN NOT NULL DEFAULT false,
    auth_required BOOLEAN NOT NULL DEFAULT false,
    pagination JSONB,
    rank_score NUMERIC(5, 4) NOT NULL DEFAULT 0,
    ranking_factors JSONB,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, endpoint, method)
);

CREATE TABLE IF NOT EXISTS public.api_discovery_runs (
    run_id TEXT PRIMARY KEY,
    source TEXT,
    mode TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'started',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    endpoints_found INTEGER NOT NULL DEFAULT 0,
    errors INTEGER NOT NULL DEFAULT 0,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS public.api_request_logs (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT REFERENCES public.api_discovery_runs(run_id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    method TEXT,
    request_headers JSONB,
    request_payload JSONB,
    status_code INTEGER,
    resource_type TEXT,
    duration_ms INTEGER,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.api_response_snapshots (
    id BIGSERIAL PRIMARY KEY,
    request_log_id BIGINT REFERENCES public.api_request_logs(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    content_type TEXT,
    response_sample JSONB,
    response_hash TEXT NOT NULL UNIQUE,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.api_extraction_metrics (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT REFERENCES public.api_discovery_runs(run_id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    richness NUMERIC(5, 4) NOT NULL DEFAULT 0,
    freshness NUMERIC(5, 4) NOT NULL DEFAULT 0,
    semantic_density NUMERIC(5, 4) NOT NULL DEFAULT 0,
    vacancy_quality NUMERIC(5, 4) NOT NULL DEFAULT 0,
    extraction_completeness NUMERIC(5, 4) NOT NULL DEFAULT 0,
    seo_noise NUMERIC(5, 4) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, source, endpoint)
);

CREATE INDEX IF NOT EXISTS ix_api_sources_registry_source_rank
ON public.api_sources_registry(source, rank_score DESC);

CREATE INDEX IF NOT EXISTS ix_api_request_logs_run_source
ON public.api_request_logs(run_id, source);

CREATE INDEX IF NOT EXISTS ix_api_response_snapshots_source
ON public.api_response_snapshots(source);

CREATE INDEX IF NOT EXISTS ix_api_extraction_metrics_source
ON public.api_extraction_metrics(source, created_at DESC);

CREATE TABLE IF NOT EXISTS public.canonical_jobs (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_job_id TEXT,
    run_id TEXT REFERENCES public.extraction_runs(run_id) ON DELETE SET NULL,
    silver_job_id TEXT REFERENCES public.silver_normalized_jobs(id) ON DELETE SET NULL,
    role_title TEXT,
    canonical_role TEXT,
    domain TEXT,
    seniority TEXT,
    modality TEXT,
    salary TEXT,
    location TEXT,
    company TEXT,
    skills JSONB,
    evidence_text TEXT,
    source_url TEXT,
    title_company_location_hash TEXT NOT NULL,
    semantic_hash TEXT,
    relevance_score NUMERIC(5, 4) NOT NULL DEFAULT 0,
    active BOOLEAN NOT NULL DEFAULT true,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS public.job_skill_trends (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    domain TEXT NOT NULL,
    skill_normalized TEXT NOT NULL,
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    job_count INTEGER NOT NULL DEFAULT 0,
    previous_job_count INTEGER NOT NULL DEFAULT 0,
    growth_rate NUMERIC(10, 4) NOT NULL DEFAULT 0,
    demand_acceleration NUMERIC(10, 4) NOT NULL DEFAULT 0,
    is_emerging BOOLEAN NOT NULL DEFAULT false,
    is_declining BOOLEAN NOT NULL DEFAULT false,
    evidence JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, domain, skill_normalized, snapshot_date)
);

CREATE TABLE IF NOT EXISTS public.source_lineage (
    id BIGSERIAL PRIMARY KEY,
    kpi_name TEXT,
    gold_job_id BIGINT REFERENCES public.gold_validated_jobs(id) ON DELETE SET NULL,
    canonical_job_id TEXT REFERENCES public.canonical_jobs(id) ON DELETE SET NULL,
    silver_job_id TEXT REFERENCES public.silver_normalized_jobs(id) ON DELETE SET NULL,
    bronze_payload_id BIGINT REFERENCES public.bronze_job_payloads(id) ON DELETE SET NULL,
    run_id TEXT REFERENCES public.extraction_runs(run_id) ON DELETE SET NULL,
    source TEXT NOT NULL,
    api_endpoint TEXT NOT NULL,
    lineage_path JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.temporal_market_signals (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    domain TEXT NOT NULL,
    skill_normalized TEXT,
    current_count INTEGER NOT NULL DEFAULT 0,
    previous_count INTEGER NOT NULL DEFAULT 0,
    growth_rate NUMERIC(10, 4) NOT NULL DEFAULT 0,
    demand_acceleration NUMERIC(10, 4) NOT NULL DEFAULT 0,
    confidence NUMERIC(5, 4) NOT NULL DEFAULT 0,
    period_start DATE NOT NULL DEFAULT CURRENT_DATE,
    period_end DATE NOT NULL DEFAULT CURRENT_DATE,
    evidence JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, signal_type, domain, skill_normalized, period_end)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_canonical_jobs_source_hash
ON public.canonical_jobs(source, title_company_location_hash);

CREATE INDEX IF NOT EXISTS ix_canonical_jobs_domain_score
ON public.canonical_jobs(domain, relevance_score DESC);

CREATE INDEX IF NOT EXISTS ix_canonical_jobs_snapshot
ON public.canonical_jobs(snapshot_date DESC, source);

CREATE INDEX IF NOT EXISTS ix_job_skill_trends_domain_skill
ON public.job_skill_trends(domain, skill_normalized, snapshot_date DESC);

CREATE INDEX IF NOT EXISTS ix_source_lineage_run_source
ON public.source_lineage(run_id, source);

CREATE INDEX IF NOT EXISTS ix_temporal_market_signals_domain
ON public.temporal_market_signals(domain, period_end DESC);

CREATE TABLE IF NOT EXISTS public.source_governance (
    source TEXT PRIMARY KEY,
    source_tier TEXT NOT NULL DEFAULT 'Experimental',
    reliability_score NUMERIC(5, 4) NOT NULL DEFAULT 0,
    freshness_score NUMERIC(5, 4) NOT NULL DEFAULT 0,
    contamination_rate NUMERIC(5, 4) NOT NULL DEFAULT 0,
    blocked_auth_rate NUMERIC(5, 4) NOT NULL DEFAULT 0,
    semantic_density NUMERIC(5, 4) NOT NULL DEFAULT 0,
    evidence_quality NUMERIC(5, 4) NOT NULL DEFAULT 0,
    extraction_completeness NUMERIC(5, 4) NOT NULL DEFAULT 0,
    source_stability NUMERIC(5, 4) NOT NULL DEFAULT 0,
    gold_readiness BOOLEAN NOT NULL DEFAULT false,
    access_strategy TEXT NOT NULL DEFAULT 'unknown',
    notes TEXT,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS public.source_quality_history (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    source_tier TEXT NOT NULL,
    reliability_score NUMERIC(5, 4) NOT NULL DEFAULT 0,
    freshness_score NUMERIC(5, 4) NOT NULL DEFAULT 0,
    contamination_rate NUMERIC(5, 4) NOT NULL DEFAULT 0,
    blocked_auth_rate NUMERIC(5, 4) NOT NULL DEFAULT 0,
    semantic_density NUMERIC(5, 4) NOT NULL DEFAULT 0,
    evidence_quality NUMERIC(5, 4) NOT NULL DEFAULT 0,
    extraction_completeness NUMERIC(5, 4) NOT NULL DEFAULT 0,
    source_stability NUMERIC(5, 4) NOT NULL DEFAULT 0,
    gold_readiness BOOLEAN NOT NULL DEFAULT false,
    access_strategy TEXT NOT NULL DEFAULT 'unknown',
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, snapshot_date)
);

CREATE TABLE IF NOT EXISTS public.source_access_strategy (
    source TEXT PRIMARY KEY,
    access_strategy TEXT NOT NULL,
    primary_endpoint TEXT,
    auth_required BOOLEAN NOT NULL DEFAULT false,
    partnership_required BOOLEAN NOT NULL DEFAULT false,
    licensed_required BOOLEAN NOT NULL DEFAULT false,
    recommended_action TEXT,
    risk_level TEXT NOT NULL DEFAULT 'medium',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS public.source_sla_metrics (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    uptime NUMERIC(5, 4) NOT NULL DEFAULT 0,
    response_stability NUMERIC(5, 4) NOT NULL DEFAULT 0,
    schema_stability NUMERIC(5, 4) NOT NULL DEFAULT 0,
    auth_volatility NUMERIC(5, 4) NOT NULL DEFAULT 0,
    measured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    window_days INTEGER NOT NULL DEFAULT 30,
    metadata JSONB,
    UNIQUE (source, measured_at)
);

CREATE INDEX IF NOT EXISTS ix_source_governance_tier_score
ON public.source_governance(source_tier, reliability_score DESC);

CREATE INDEX IF NOT EXISTS ix_source_quality_history_source_date
ON public.source_quality_history(source, snapshot_date DESC);

CREATE INDEX IF NOT EXISTS ix_source_access_strategy_access
ON public.source_access_strategy(access_strategy);

CREATE INDEX IF NOT EXISTS ix_source_sla_metrics_source_measured
ON public.source_sla_metrics(source, measured_at DESC);
