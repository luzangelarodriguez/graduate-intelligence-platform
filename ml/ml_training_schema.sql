-- ML training dataset schema for job-skill extraction.
-- PostgreSQL is the auditable source of truth; JSONL exports are the training artifacts.

ALTER TABLE IF EXISTS empleos
    ADD COLUMN IF NOT EXISTS ubicacion TEXT,
    ADD COLUMN IF NOT EXISTS fuente TEXT,
    ADD COLUMN IF NOT EXISTS url TEXT;

UPDATE empleos
SET
    ubicacion = COALESCE(NULLIF(ubicacion, ''), location),
    fuente = COALESCE(NULLIF(fuente, ''), source),
    url = COALESCE(NULLIF(url, ''), job_url)
WHERE
    (ubicacion IS NULL OR ubicacion = '')
    OR (fuente IS NULL OR fuente = '')
    OR (url IS NULL OR url = '');

ALTER TABLE IF EXISTS especializaciones
    ADD COLUMN IF NOT EXISTS campo_laboral TEXT,
    ADD COLUMN IF NOT EXISTS plan_estudios TEXT,
    ADD COLUMN IF NOT EXISTS general_text TEXT,
    ADD COLUMN IF NOT EXISTS source_url TEXT;

CREATE TABLE IF NOT EXISTS ml_training_runs (
    id BIGSERIAL PRIMARY KEY,
    run_name TEXT NOT NULL,
    task_name TEXT NOT NULL DEFAULT 'job_skill_extraction',
    dataset_version TEXT NOT NULL,
    source_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (task_name, dataset_version)
);

CREATE TABLE IF NOT EXISTS ml_job_documents (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES ml_training_runs(id) ON DELETE CASCADE,
    external_job_id TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    posted_or_seen_date DATE,
    source TEXT,
    source_url TEXT,
    raw_description TEXT NOT NULL DEFAULT '',
    normalized_text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, external_job_id),
    UNIQUE (run_id, content_hash)
);

CREATE TABLE IF NOT EXISTS ml_skill_labels (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES ml_job_documents(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    skill_category TEXT,
    label_type TEXT NOT NULL DEFAULT 'positive'
        CHECK (label_type IN ('positive', 'negative', 'uncertain')),
    label_source TEXT NOT NULL DEFAULT 'weak_supervision'
        CHECK (label_source IN ('human', 'weak_supervision', 'model', 'imported')),
    confidence NUMERIC(5, 4) NOT NULL DEFAULT 1.0
        CHECK (confidence >= 0 AND confidence <= 1),
    source_phrase TEXT,
    reviewer TEXT,
    reviewed_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, skill_name, label_type, label_source)
);

CREATE TABLE IF NOT EXISTS ml_training_examples (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES ml_training_runs(id) ON DELETE CASCADE,
    document_id BIGINT NOT NULL REFERENCES ml_job_documents(id) ON DELETE CASCADE,
    split TEXT NOT NULL DEFAULT 'train'
        CHECK (split IN ('train', 'validation', 'test')),
    format TEXT NOT NULL DEFAULT 'chat_jsonl'
        CHECK (format IN ('chat_jsonl', 'record_jsonl')),
    prompt JSONB NOT NULL,
    completion JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, document_id, format)
);

CREATE INDEX IF NOT EXISTS ix_ml_job_documents_run_id
    ON ml_job_documents (run_id);

CREATE INDEX IF NOT EXISTS ix_ml_job_documents_source
    ON ml_job_documents (source);

CREATE INDEX IF NOT EXISTS ix_ml_skill_labels_document_id
    ON ml_skill_labels (document_id);

CREATE INDEX IF NOT EXISTS ix_ml_skill_labels_skill_name
    ON ml_skill_labels (lower(skill_name));

CREATE INDEX IF NOT EXISTS ix_ml_training_examples_run_split
    ON ml_training_examples (run_id, split);

CREATE TABLE IF NOT EXISTS ml_program_documents (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES ml_training_runs(id) ON DELETE CASCADE,
    external_program_id TEXT NOT NULL,
    program_name TEXT NOT NULL,
    role_target TEXT,
    description TEXT NOT NULL DEFAULT '',
    campo_laboral TEXT NOT NULL DEFAULT '',
    plan_estudios TEXT NOT NULL DEFAULT '',
    perfil_egreso TEXT NOT NULL DEFAULT '',
    general_text TEXT NOT NULL DEFAULT '',
    source_url TEXT,
    normalized_text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, external_program_id),
    UNIQUE (run_id, content_hash)
);

CREATE TABLE IF NOT EXISTS ml_program_skill_labels (
    id BIGSERIAL PRIMARY KEY,
    program_document_id BIGINT NOT NULL REFERENCES ml_program_documents(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    skill_category TEXT,
    evidence_section TEXT NOT NULL DEFAULT 'unknown'
        CHECK (evidence_section IN ('plan_estudios', 'campo_laboral', 'perfil_egreso', 'description', 'general_text', 'curated', 'unknown')),
    label_type TEXT NOT NULL DEFAULT 'positive'
        CHECK (label_type IN ('positive', 'negative', 'uncertain')),
    label_source TEXT NOT NULL DEFAULT 'weak_supervision'
        CHECK (label_source IN ('human', 'weak_supervision', 'model', 'curated', 'imported')),
    confidence NUMERIC(5, 4) NOT NULL DEFAULT 1.0
        CHECK (confidence >= 0 AND confidence <= 1),
    source_phrase TEXT,
    reviewer TEXT,
    reviewed_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (program_document_id, skill_name, evidence_section, label_type, label_source)
);

CREATE INDEX IF NOT EXISTS ix_ml_program_documents_run_id
    ON ml_program_documents (run_id);

CREATE INDEX IF NOT EXISTS ix_ml_program_documents_program_name
    ON ml_program_documents (lower(program_name));

CREATE INDEX IF NOT EXISTS ix_ml_program_skill_labels_document_id
    ON ml_program_skill_labels (program_document_id);

CREATE INDEX IF NOT EXISTS ix_ml_program_skill_labels_skill_name
    ON ml_program_skill_labels (lower(skill_name));

CREATE OR REPLACE VIEW vw_ml_skill_training_records AS
SELECT
    r.id AS run_id,
    r.dataset_version,
    d.id AS document_id,
    d.external_job_id,
    d.title,
    d.company,
    d.location,
    d.source,
    d.raw_description,
    d.normalized_text,
    COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'skill_name', l.skill_name,
                'skill_category', l.skill_category,
                'label_type', l.label_type,
                'label_source', l.label_source,
                'confidence', l.confidence,
                'source_phrase', l.source_phrase
            )
            ORDER BY l.skill_name
        ) FILTER (WHERE l.id IS NOT NULL),
        '[]'::jsonb
    ) AS labels
FROM ml_training_runs r
JOIN ml_job_documents d
    ON d.run_id = r.id
LEFT JOIN ml_skill_labels l
    ON l.document_id = d.id
GROUP BY
    r.id,
    r.dataset_version,
    d.id,
    d.external_job_id,
    d.title,
    d.company,
    d.location,
    d.source,
    d.raw_description,
    d.normalized_text;

CREATE OR REPLACE VIEW vw_ml_program_training_records AS
SELECT
    r.id AS run_id,
    r.dataset_version,
    p.id AS program_document_id,
    p.external_program_id,
    p.program_name,
    p.role_target,
    p.description,
    p.campo_laboral,
    p.plan_estudios,
    p.perfil_egreso,
    p.general_text,
    p.source_url,
    p.normalized_text,
    COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'skill_name', l.skill_name,
                'skill_category', l.skill_category,
                'evidence_section', l.evidence_section,
                'label_type', l.label_type,
                'label_source', l.label_source,
                'confidence', l.confidence,
                'source_phrase', l.source_phrase
            )
            ORDER BY l.evidence_section, l.skill_name
        ) FILTER (WHERE l.id IS NOT NULL),
        '[]'::jsonb
    ) AS labels
FROM ml_training_runs r
JOIN ml_program_documents p
    ON p.run_id = r.id
LEFT JOIN ml_program_skill_labels l
    ON l.program_document_id = p.id
GROUP BY
    r.id,
    r.dataset_version,
    p.id,
    p.external_program_id,
    p.program_name,
    p.role_target,
    p.description,
    p.campo_laboral,
    p.plan_estudios,
    p.perfil_egreso,
    p.general_text,
    p.source_url,
    p.normalized_text;

CREATE TABLE IF NOT EXISTS ml_program_job_matches (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES ml_training_runs(id) ON DELETE CASCADE,
    program_document_id BIGINT NOT NULL REFERENCES ml_program_documents(id) ON DELETE CASCADE,
    job_document_id BIGINT NOT NULL REFERENCES ml_job_documents(id) ON DELETE CASCADE,
    especializacion_id INTEGER,
    empleo_id TEXT,
    program_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    company TEXT,
    match_method TEXT NOT NULL DEFAULT 'rules_v1',
    model_name TEXT NOT NULL DEFAULT 'local_rules_v1',
    score_match NUMERIC(5, 2) NOT NULL
        CHECK (score_match >= 0 AND score_match <= 100),
    relevance_label TEXT NOT NULL DEFAULT 'low'
        CHECK (relevance_label IN ('high', 'medium', 'low', 'no_match')),
    role_alignment NUMERIC(5, 2) NOT NULL DEFAULT 0
        CHECK (role_alignment >= 0 AND role_alignment <= 100),
    skill_overlap_score NUMERIC(5, 2) NOT NULL DEFAULT 0
        CHECK (skill_overlap_score >= 0 AND skill_overlap_score <= 100),
    job_skill_density NUMERIC(5, 2) NOT NULL DEFAULT 0
        CHECK (job_skill_density >= 0 AND job_skill_density <= 100),
    skills_en_comun JSONB NOT NULL DEFAULT '[]'::jsonb,
    skills_faltantes JSONB NOT NULL DEFAULT '[]'::jsonb,
    skills_programa JSONB NOT NULL DEFAULT '[]'::jsonb,
    skills_empleo JSONB NOT NULL DEFAULT '[]'::jsonb,
    explanation TEXT NOT NULL DEFAULT '',
    content_hash TEXT NOT NULL,
    raw_features JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, program_document_id, job_document_id, match_method)
);

CREATE INDEX IF NOT EXISTS ix_ml_program_job_matches_run_id
    ON ml_program_job_matches (run_id);

CREATE INDEX IF NOT EXISTS ix_ml_program_job_matches_program
    ON ml_program_job_matches (especializacion_id, score_match DESC);

CREATE INDEX IF NOT EXISTS ix_ml_program_job_matches_job
    ON ml_program_job_matches (empleo_id);

DROP VIEW IF EXISTS vw_latest_ml_program_job_matches;

CREATE VIEW vw_latest_ml_program_job_matches AS
WITH latest_run AS (
    SELECT id
    FROM ml_training_runs
    WHERE task_name = 'program_job_match'
    ORDER BY created_at DESC, id DESC
    LIMIT 1
)
SELECT
    m.empleo_id,
    COALESCE(NULLIF(m.job_title, ''), e.titulo, '') AS titulo_empleo,
    COALESCE(NULLIF(m.company, ''), e.empresa, '') AS empresa,
    jsonb_array_length(m.skills_empleo)::int AS total_skills_empleo,
    jsonb_array_length(m.skills_programa)::int AS total_skills_especializacion,
    jsonb_array_length(m.skills_en_comun)::int AS skills_en_comun,
    m.score_match AS porcentaje_match,
    m.especializacion_id,
    m.role_alignment AS afinidad_rol,
    m.skill_overlap_score AS match_base,
    m.explanation AS explicacion_match,
    m.skills_en_comun AS skills_comunes_json,
    m.skills_faltantes AS skills_faltantes_json,
    m.skills_empleo AS skills_empleo_json,
    m.relevance_label,
    m.match_method,
    m.model_name,
    m.created_at
FROM ml_program_job_matches m
JOIN latest_run lr
    ON lr.id = m.run_id
LEFT JOIN empleos e
    ON e.id = m.empleo_id
WHERE m.relevance_label <> 'no_match';
