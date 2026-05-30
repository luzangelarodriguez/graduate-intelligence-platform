-- Production migration script for Railway compatibility.
-- Assumption: source data is exposed as schema `source_snapshot`
-- (via postgres_fdw, a staged dump, or a temporary import schema).
--
-- This script is intentionally idempotent:
-- - CREATE TABLE IF NOT EXISTS for missing production observatory tables
-- - INSERT ... ON CONFLICT DO UPDATE for data copy
-- - No DELETE statements
--
-- If the source is being executed directly inside the source database,
-- replace `source_snapshot.` with `public.`.

BEGIN;

-- -------------------------------------------------------------------
-- Supporting relations used by production dashboard and program views
-- -------------------------------------------------------------------

CREATE OR REPLACE VIEW public.vw_programa_skills AS
SELECT
    e.id AS especializacion_id,
    e.nombre AS especializacion,
    s.id AS skill_id,
    s.nombre AS skill,
    s.nombre AS nombre,
    s.categoria
FROM public.especializaciones e
JOIN public.especializacion_skills es
    ON es.especializacion_id = e.id
JOIN public.skills s
    ON s.id = es.skill_id;

CREATE OR REPLACE VIEW public.vw_dashboard_especializacion AS
WITH programa_skills AS (
    SELECT especializacion_id, COUNT(DISTINCT skill_id)::int AS total_skills_programa
    FROM public.especializacion_skills
    GROUP BY especializacion_id
),
programa_herramientas AS (
    SELECT especializacion_id, COUNT(DISTINCT herramienta_id)::int AS total_herramientas
    FROM public.especializacion_herramientas
    GROUP BY especializacion_id
),
programa_competencias AS (
    SELECT especializacion_id, COUNT(DISTINCT competencia_id)::int AS total_competencias
    FROM public.especializacion_competencias
    GROUP BY especializacion_id
),
programa_habilidades_blandas AS (
    SELECT especializacion_id, COUNT(DISTINCT habilidad_id)::int AS total_habilidades_blandas
    FROM public.especializacion_habilidades_blandas
    GROUP BY especializacion_id
),
match_summary AS (
    SELECT
        especializacion_id,
        ROUND(AVG(porcentaje_match)::numeric, 2) AS promedio_match_mercado,
        ROUND(MAX(porcentaje_match)::numeric, 2) AS max_match_mercado,
        COUNT(*)::int AS total_empleos_relacionados
    FROM public.vw_labor_program_job_matches
    GROUP BY especializacion_id
)
SELECT
    s.id AS especializacion_id,
    s.nombre AS nombre_especializacion,
    COALESCE(ps.total_skills_programa, 0) AS total_skills_programa,
    COALESCE(ph.total_herramientas, 0) AS total_herramientas,
    COALESCE(pc.total_competencias, 0) AS total_competencias,
    COALESCE(pbl.total_habilidades_blandas, 0) AS total_habilidades_blandas,
    COALESCE(ms.promedio_match_mercado, 0) AS promedio_match_mercado,
    COALESCE(ms.max_match_mercado, 0) AS max_match_mercado,
    COALESCE(ms.total_empleos_relacionados, 0) AS total_empleos_relacionados
FROM public.especializaciones s
LEFT JOIN programa_skills ps ON ps.especializacion_id = s.id
LEFT JOIN programa_herramientas ph ON ph.especializacion_id = s.id
LEFT JOIN programa_competencias pc ON pc.especializacion_id = s.id
LEFT JOIN programa_habilidades_blandas pbl ON pbl.especializacion_id = s.id
LEFT JOIN match_summary ms ON ms.especializacion_id = s.id;

CREATE MATERIALIZED VIEW IF NOT EXISTS public.mv_dashboard_especializacion AS
SELECT * FROM public.vw_dashboard_especializacion;

CREATE UNIQUE INDEX IF NOT EXISTS ux_mv_dashboard_especializacion
ON public.mv_dashboard_especializacion (especializacion_id);

CREATE OR REPLACE VIEW public.vw_labor_program_job_matches AS
WITH job_skill_totals AS (
    SELECT
        COALESCE(es.empleo_id::text, '') AS job_id,
        COUNT(DISTINCT COALESCE(es.skill_id::text, lower(es.skill_normalized), lower(es.skill_original)))::int AS total_skills_empleo
    FROM public.empleo_skills es
    GROUP BY COALESCE(es.empleo_id::text, '')
),
program_skill_totals AS (
    SELECT
        especializacion_id,
        COUNT(DISTINCT skill_id)::int AS total_skills_especializacion
    FROM public.especializacion_skills
    GROUP BY especializacion_id
),
job_matches AS (
    SELECT
        m.especializacion_id,
        m.job_id,
        COUNT(DISTINCT m.skill_id)::int AS skills_en_comun,
        ROUND(MAX(m.match_score)::numeric, 2) AS porcentaje_match,
        ROUND(AVG(m.confidence)::numeric, 4) AS confidence,
        MAX(m.created_at) AS created_at
    FROM public.labor_program_skill_matches m
    GROUP BY m.especializacion_id, m.job_id
)
SELECT
    jm.especializacion_id,
    jm.job_id,
    jm.skills_en_comun,
    jm.porcentaje_match,
    jm.confidence,
    jm.created_at,
    j.titulo AS job_title,
    j.empresa AS company,
    j.ciudad AS city,
    j.modalidad,
    j.url AS job_url,
    COALESCE(jst.total_skills_empleo, 0) AS total_skills_empleo,
    COALESCE(pst.total_skills_especializacion, 0) AS total_skills_especializacion,
    'labor_program_skill_matches'::text AS match_method
FROM job_matches jm
LEFT JOIN public.empleos j ON j.id::text = jm.job_id
LEFT JOIN job_skill_totals jst ON jst.job_id = jm.job_id
LEFT JOIN program_skill_totals pst ON pst.especializacion_id = jm.especializacion_id;

CREATE OR REPLACE VIEW public.vw_latest_ml_program_job_matches AS
SELECT DISTINCT ON (especializacion_id, job_id)
    especializacion_id,
    job_id,
    skills_en_comun,
    porcentaje_match,
    confidence,
    created_at,
    job_title,
    company,
    city,
    modalidad,
    job_url,
    total_skills_empleo,
    total_skills_especializacion,
    match_method
FROM public.vw_labor_program_job_matches
ORDER BY especializacion_id, job_id, porcentaje_match DESC, confidence DESC, created_at DESC;

-- -------------------------------------------------------------------
-- Core curricular tables
-- -------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.especializaciones (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    descripcion TEXT,
    rol TEXT,
    facultad TEXT,
    nivel TEXT NOT NULL DEFAULT 'Posgrado',
    estado TEXT NOT NULL DEFAULT 'Activo',
    modalidad TEXT NOT NULL DEFAULT 'Virtual',
    campo_laboral TEXT,
    plan_estudios TEXT,
    general_text TEXT,
    source_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.skills (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    categoria TEXT,
    dominio TEXT,
    tipo TEXT,
    descripcion TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.competencias (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    categoria TEXT,
    dominio TEXT,
    descripcion TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.herramientas (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    categoria TEXT,
    dominio TEXT,
    descripcion TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.habilidades_blandas (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    categoria TEXT,
    dominio TEXT,
    descripcion TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.especializacion_skills (
    especializacion_id INTEGER NOT NULL REFERENCES public.especializaciones(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES public.skills(id) ON DELETE CASCADE,
    confidence_score NUMERIC(5, 4) NOT NULL DEFAULT 1,
    source_document TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (especializacion_id, skill_id)
);

CREATE TABLE IF NOT EXISTS public.especializacion_herramientas (
    especializacion_id INTEGER NOT NULL REFERENCES public.especializaciones(id) ON DELETE CASCADE,
    herramienta_id INTEGER NOT NULL REFERENCES public.herramientas(id) ON DELETE CASCADE,
    confidence_score NUMERIC(5, 4) NOT NULL DEFAULT 1,
    source_document TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (especializacion_id, herramienta_id)
);

CREATE TABLE IF NOT EXISTS public.especializacion_competencias (
    especializacion_id INTEGER NOT NULL REFERENCES public.especializaciones(id) ON DELETE CASCADE,
    competencia_id INTEGER NOT NULL REFERENCES public.competencias(id) ON DELETE CASCADE,
    confidence_score NUMERIC(5, 4) NOT NULL DEFAULT 1,
    source_document TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (especializacion_id, competencia_id)
);

CREATE TABLE IF NOT EXISTS public.especializacion_habilidades_blandas (
    especializacion_id INTEGER NOT NULL REFERENCES public.especializaciones(id) ON DELETE CASCADE,
    habilidad_id INTEGER NOT NULL REFERENCES public.habilidades_blandas(id) ON DELETE CASCADE,
    confidence_score NUMERIC(5, 4) NOT NULL DEFAULT 1,
    source_document TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (especializacion_id, habilidad_id)
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
    confidence_score NUMERIC(5, 4),
    confidence_factors JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

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

ALTER TABLE IF EXISTS public.empleo_skills ADD COLUMN IF NOT EXISTS skill_id INTEGER;

CREATE TABLE IF NOT EXISTS public.labor_program_skill_matches (
    id BIGSERIAL PRIMARY KEY,
    especializacion_id INTEGER NOT NULL REFERENCES public.especializaciones(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL,
    skill_id INTEGER REFERENCES public.skills(id) ON DELETE SET NULL,
    match_score NUMERIC(5, 2) NOT NULL DEFAULT 0 CHECK (match_score >= 0 AND match_score <= 100),
    source TEXT NOT NULL DEFAULT 'labor_program_matching_v1',
    confidence NUMERIC(5, 4) NOT NULL DEFAULT 0 CHECK (confidence >= 0 AND confidence <= 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (especializacion_id, job_id, skill_id, source)
);

INSERT INTO public.especializaciones (
    id, nombre, descripcion, rol, facultad, nivel, estado, modalidad, campo_laboral, plan_estudios,
    general_text, source_url, created_at, updated_at
)
SELECT
    id, nombre, descripcion, rol, facultad, nivel, estado, modalidad, campo_laboral, plan_estudios,
    general_text, source_url, created_at, updated_at
FROM source_snapshot.especializaciones
ON CONFLICT (id) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion,
    rol = EXCLUDED.rol,
    facultad = EXCLUDED.facultad,
    nivel = EXCLUDED.nivel,
    estado = EXCLUDED.estado,
    modalidad = EXCLUDED.modalidad,
    campo_laboral = EXCLUDED.campo_laboral,
    plan_estudios = EXCLUDED.plan_estudios,
    general_text = EXCLUDED.general_text,
    source_url = EXCLUDED.source_url,
    updated_at = EXCLUDED.updated_at;

INSERT INTO public.skills (
    id, nombre, categoria, dominio, tipo, descripcion, created_at, updated_at
)
SELECT
    id, nombre, categoria, dominio, tipo, descripcion, created_at, updated_at
FROM source_snapshot.skills
ON CONFLICT (id) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    categoria = EXCLUDED.categoria,
    dominio = EXCLUDED.dominio,
    tipo = EXCLUDED.tipo,
    descripcion = EXCLUDED.descripcion,
    updated_at = EXCLUDED.updated_at;

INSERT INTO public.competencias (
    id, nombre, categoria, dominio, descripcion, created_at, updated_at
)
SELECT
    id, nombre, categoria, dominio, descripcion, created_at, updated_at
FROM source_snapshot.competencias
ON CONFLICT (id) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    categoria = EXCLUDED.categoria,
    dominio = EXCLUDED.dominio,
    descripcion = EXCLUDED.descripcion,
    updated_at = EXCLUDED.updated_at;

INSERT INTO public.herramientas (
    id, nombre, categoria, dominio, descripcion, created_at, updated_at
)
SELECT
    id, nombre, categoria, dominio, descripcion, created_at, updated_at
FROM source_snapshot.herramientas
ON CONFLICT (id) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    categoria = EXCLUDED.categoria,
    dominio = EXCLUDED.dominio,
    descripcion = EXCLUDED.descripcion,
    updated_at = EXCLUDED.updated_at;

INSERT INTO public.habilidades_blandas (
    id, nombre, categoria, dominio, descripcion, created_at, updated_at
)
SELECT
    id, nombre, categoria, dominio, descripcion, created_at, updated_at
FROM source_snapshot.habilidades_blandas
ON CONFLICT (id) DO UPDATE SET
    nombre = EXCLUDED.nombre,
    categoria = EXCLUDED.categoria,
    dominio = EXCLUDED.dominio,
    descripcion = EXCLUDED.descripcion,
    updated_at = EXCLUDED.updated_at;

INSERT INTO public.especializacion_skills (
    especializacion_id, skill_id, confidence_score, source_document, created_at
)
SELECT
    especializacion_id, skill_id, confidence_score, source_document, created_at
FROM source_snapshot.especializacion_skills
ON CONFLICT (especializacion_id, skill_id) DO UPDATE SET
    confidence_score = EXCLUDED.confidence_score,
    source_document = EXCLUDED.source_document,
    created_at = EXCLUDED.created_at;

INSERT INTO public.especializacion_herramientas (
    especializacion_id, herramienta_id, confidence_score, source_document, created_at
)
SELECT
    especializacion_id, herramienta_id, confidence_score, source_document, created_at
FROM source_snapshot.especializacion_herramientas
ON CONFLICT (especializacion_id, herramienta_id) DO UPDATE SET
    confidence_score = EXCLUDED.confidence_score,
    source_document = EXCLUDED.source_document,
    created_at = EXCLUDED.created_at;

INSERT INTO public.especializacion_competencias (
    especializacion_id, competencia_id, confidence_score, source_document, created_at
)
SELECT
    especializacion_id, competencia_id, confidence_score, source_document, created_at
FROM source_snapshot.especializacion_competencias
ON CONFLICT (especializacion_id, competencia_id) DO UPDATE SET
    confidence_score = EXCLUDED.confidence_score,
    source_document = EXCLUDED.source_document,
    created_at = EXCLUDED.created_at;

INSERT INTO public.especializacion_habilidades_blandas (
    especializacion_id, habilidad_id, confidence_score, source_document, created_at
)
SELECT
    especializacion_id, habilidad_id, confidence_score, source_document, created_at
FROM source_snapshot.especializacion_habilidades_blandas
ON CONFLICT (especializacion_id, habilidad_id) DO UPDATE SET
    confidence_score = EXCLUDED.confidence_score,
    source_document = EXCLUDED.source_document,
    created_at = EXCLUDED.created_at;

-- -------------------------------------------------------------------
-- Production job / match evidence used by dashboard relation
-- -------------------------------------------------------------------

INSERT INTO public.empleos (
    id, portal, titulo, titulo_normalizado, empresa, ciudad, modalidad, salario, descripcion,
    seniority, sector, dominio, fecha_publicacion, url, hash_contenido, embedding, created_at
)
SELECT
    id, portal, titulo, titulo_normalizado, empresa, ciudad, modalidad, salario, descripcion,
    seniority, sector, dominio, fecha_publicacion, url, hash_contenido, embedding, created_at
FROM source_snapshot.empleos
ON CONFLICT (id) DO UPDATE SET
    portal = EXCLUDED.portal,
    titulo = EXCLUDED.titulo,
    titulo_normalizado = EXCLUDED.titulo_normalizado,
    empresa = EXCLUDED.empresa,
    ciudad = EXCLUDED.ciudad,
    modalidad = EXCLUDED.modalidad,
    salario = EXCLUDED.salario,
    descripcion = EXCLUDED.descripcion,
    seniority = EXCLUDED.seniority,
    sector = EXCLUDED.sector,
    dominio = EXCLUDED.dominio,
    fecha_publicacion = EXCLUDED.fecha_publicacion,
    url = EXCLUDED.url,
    hash_contenido = EXCLUDED.hash_contenido,
    embedding = EXCLUDED.embedding;

INSERT INTO public.empleo_skills (
    id, empleo_id, skill_original, skill_normalized, skill_domain, tipo_skill, confianza_extraccion, created_at, skill_id
)
SELECT
    id, empleo_id, skill_original, skill_normalized, skill_domain, tipo_skill, confianza_extraccion, created_at, skill_id
FROM source_snapshot.empleo_skills
ON CONFLICT (id) DO UPDATE SET
    empleo_id = EXCLUDED.empleo_id,
    skill_original = EXCLUDED.skill_original,
    skill_normalized = EXCLUDED.skill_normalized,
    skill_domain = EXCLUDED.skill_domain,
    tipo_skill = EXCLUDED.tipo_skill,
    confianza_extraccion = EXCLUDED.confianza_extraccion,
    skill_id = EXCLUDED.skill_id;

INSERT INTO public.canonical_jobs (
    id, canonical_title, normalized_title, canonical_company, normalized_company, canonical_location,
    canonical_modality, canonical_seniority, canonical_salary, canonical_description, job_content_hash,
    source_name, source_url, created_at, updated_at
)
SELECT
    id, canonical_title, normalized_title, canonical_company, normalized_company, canonical_location,
    canonical_modality, canonical_seniority, canonical_salary, canonical_description, job_content_hash,
    source_name, source_url, created_at, updated_at
FROM source_snapshot.canonical_jobs
ON CONFLICT (id) DO UPDATE SET
    canonical_title = EXCLUDED.canonical_title,
    normalized_title = EXCLUDED.normalized_title,
    canonical_company = EXCLUDED.canonical_company,
    normalized_company = EXCLUDED.normalized_company,
    canonical_location = EXCLUDED.canonical_location,
    canonical_modality = EXCLUDED.canonical_modality,
    canonical_seniority = EXCLUDED.canonical_seniority,
    canonical_salary = EXCLUDED.canonical_salary,
    canonical_description = EXCLUDED.canonical_description,
    job_content_hash = EXCLUDED.job_content_hash,
    source_name = EXCLUDED.source_name,
    source_url = EXCLUDED.source_url,
    updated_at = EXCLUDED.updated_at;

INSERT INTO public.silver_normalized_jobs (
    id, source_name, source_url, content_hash, document_type, is_real_job_posting,
    normalized_title, normalized_company, normalized_location, description, requirements,
    responsibilities, technologies, tools, skills, job_evidence_skills, portal_taxonomy_skills,
    job_probability_score, curation_level, rejection_reason, created_at, updated_at
)
SELECT
    id, source_name, source_url, content_hash, document_type, is_real_job_posting,
    normalized_title, normalized_company, normalized_location, description, requirements,
    responsibilities, technologies, tools, skills, job_evidence_skills, portal_taxonomy_skills,
    job_probability_score, curation_level, rejection_reason, created_at, updated_at
FROM source_snapshot.silver_normalized_jobs
ON CONFLICT (id) DO UPDATE SET
    source_name = EXCLUDED.source_name,
    source_url = EXCLUDED.source_url,
    content_hash = EXCLUDED.content_hash,
    document_type = EXCLUDED.document_type,
    is_real_job_posting = EXCLUDED.is_real_job_posting,
    normalized_title = EXCLUDED.normalized_title,
    normalized_company = EXCLUDED.normalized_company,
    normalized_location = EXCLUDED.normalized_location,
    description = EXCLUDED.description,
    requirements = EXCLUDED.requirements,
    responsibilities = EXCLUDED.responsibilities,
    technologies = EXCLUDED.technologies,
    tools = EXCLUDED.tools,
    skills = EXCLUDED.skills,
    job_evidence_skills = EXCLUDED.job_evidence_skills,
    portal_taxonomy_skills = EXCLUDED.portal_taxonomy_skills,
    job_probability_score = EXCLUDED.job_probability_score,
    curation_level = EXCLUDED.curation_level,
    rejection_reason = EXCLUDED.rejection_reason,
    updated_at = EXCLUDED.updated_at;

INSERT INTO public.gold_validated_jobs (
    id, source_name, source_url, content_hash, curated_title, curated_description,
    evidence_summary, normalized_skills, market_role, analytics_relevance,
    ai_confidence, approved_by_agent, approved_timestamp, created_at, updated_at
)
SELECT
    id, source_name, source_url, content_hash, curated_title, curated_description,
    evidence_summary, normalized_skills, market_role, analytics_relevance,
    ai_confidence, approved_by_agent, approved_timestamp, created_at, updated_at
FROM source_snapshot.gold_validated_jobs
ON CONFLICT (id) DO UPDATE SET
    source_name = EXCLUDED.source_name,
    source_url = EXCLUDED.source_url,
    content_hash = EXCLUDED.content_hash,
    curated_title = EXCLUDED.curated_title,
    curated_description = EXCLUDED.curated_description,
    evidence_summary = EXCLUDED.evidence_summary,
    normalized_skills = EXCLUDED.normalized_skills,
    market_role = EXCLUDED.market_role,
    analytics_relevance = EXCLUDED.analytics_relevance,
    ai_confidence = EXCLUDED.ai_confidence,
    approved_by_agent = EXCLUDED.approved_by_agent,
    approved_timestamp = EXCLUDED.approved_timestamp,
    updated_at = EXCLUDED.updated_at;

INSERT INTO public.labor_program_skill_matches (
    id, especializacion_id, job_id, skill_id, match_score, source, confidence, created_at, updated_at
)
SELECT
    id, especializacion_id, job_id, skill_id, match_score, source, confidence, created_at, updated_at
FROM source_snapshot.labor_program_skill_matches
ON CONFLICT (especializacion_id, job_id, skill_id, source) DO UPDATE SET
    match_score = EXCLUDED.match_score,
    confidence = EXCLUDED.confidence,
    updated_at = EXCLUDED.updated_at;

-- -------------------------------------------------------------------
-- Microcurriculum program context
-- -------------------------------------------------------------------

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

INSERT INTO public.microcurriculum_program_contexts (
    specialization_id, specialization_name, source_directory, documents_processed,
    detected_domain, detected_subdomain, confidence, subjects, technical_skills,
    transversal_skills, methodologies, tools, platforms, technologies, bibliography,
    keywords, occupational_profiles, real_market_gaps, strengthening_areas, redundancies,
    labor_roles, benchmarking, scores, executive_narrative, raw_context, indexed_at, updated_at
)
SELECT
    specialization_id, specialization_name, source_directory, documents_processed,
    detected_domain, detected_subdomain, confidence, subjects, technical_skills,
    transversal_skills, methodologies, tools, platforms, technologies, bibliography,
    keywords, occupational_profiles, real_market_gaps, strengthening_areas, redundancies,
    labor_roles, benchmarking, scores, executive_narrative, raw_context, indexed_at, updated_at
FROM source_snapshot.microcurriculum_program_contexts
ON CONFLICT (specialization_id) DO UPDATE SET
    specialization_name = EXCLUDED.specialization_name,
    source_directory = EXCLUDED.source_directory,
    documents_processed = EXCLUDED.documents_processed,
    detected_domain = EXCLUDED.detected_domain,
    detected_subdomain = EXCLUDED.detected_subdomain,
    confidence = EXCLUDED.confidence,
    subjects = EXCLUDED.subjects,
    technical_skills = EXCLUDED.technical_skills,
    transversal_skills = EXCLUDED.transversal_skills,
    methodologies = EXCLUDED.methodologies,
    tools = EXCLUDED.tools,
    platforms = EXCLUDED.platforms,
    technologies = EXCLUDED.technologies,
    bibliography = EXCLUDED.bibliography,
    keywords = EXCLUDED.keywords,
    occupational_profiles = EXCLUDED.occupational_profiles,
    real_market_gaps = EXCLUDED.real_market_gaps,
    strengthening_areas = EXCLUDED.strengthening_areas,
    redundancies = EXCLUDED.redundancies,
    labor_roles = EXCLUDED.labor_roles,
    benchmarking = EXCLUDED.benchmarking,
    scores = EXCLUDED.scores,
    executive_narrative = EXCLUDED.executive_narrative,
    raw_context = EXCLUDED.raw_context,
    updated_at = EXCLUDED.updated_at;

-- -------------------------------------------------------------------
-- Observatory layer
-- -------------------------------------------------------------------

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

INSERT INTO public.observatory_metrics (
    id, metric_name, metric_category, metric_value, metric_period, confidence_score,
    source_payload, generated_at, updated_at
)
SELECT
    id, metric_name, metric_category, metric_value, metric_period, confidence_score,
    source_payload, generated_at, updated_at
FROM source_snapshot.observatory_metrics
ON CONFLICT (metric_name, metric_period) DO UPDATE SET
    metric_category = EXCLUDED.metric_category,
    metric_value = EXCLUDED.metric_value,
    confidence_score = EXCLUDED.confidence_score,
    source_payload = EXCLUDED.source_payload,
    generated_at = EXCLUDED.generated_at,
    updated_at = EXCLUDED.updated_at;

INSERT INTO public.curriculum_gap_observatory (
    id, specialization, missing_skill, market_demand_score, curriculum_coverage_score,
    urgency_score, emergence_score, recommendation, evidence, generated_at, updated_at
)
SELECT
    id, specialization, missing_skill, market_demand_score, curriculum_coverage_score,
    urgency_score, emergence_score, recommendation, evidence, generated_at, updated_at
FROM source_snapshot.curriculum_gap_observatory
ON CONFLICT (specialization, missing_skill) DO UPDATE SET
    market_demand_score = EXCLUDED.market_demand_score,
    curriculum_coverage_score = EXCLUDED.curriculum_coverage_score,
    urgency_score = EXCLUDED.urgency_score,
    emergence_score = EXCLUDED.emergence_score,
    recommendation = EXCLUDED.recommendation,
    evidence = EXCLUDED.evidence,
    generated_at = EXCLUDED.generated_at,
    updated_at = EXCLUDED.updated_at;

INSERT INTO public.recommendation_observatory (
    id, recommendation_type, target_role, target_company, recommendation_payload,
    recommendation_reasoning, recommendation_confidence, recommendation_evidence,
    metric_period, generated_at, updated_at
)
SELECT
    id, recommendation_type, target_role, target_company, recommendation_payload,
    recommendation_reasoning, recommendation_confidence, recommendation_evidence,
    metric_period, generated_at, updated_at
FROM source_snapshot.recommendation_observatory
ON CONFLICT (recommendation_type, target_role, target_company, metric_period) DO UPDATE SET
    recommendation_payload = EXCLUDED.recommendation_payload,
    recommendation_reasoning = EXCLUDED.recommendation_reasoning,
    recommendation_confidence = EXCLUDED.recommendation_confidence,
    recommendation_evidence = EXCLUDED.recommendation_evidence,
    generated_at = EXCLUDED.generated_at,
    updated_at = EXCLUDED.updated_at;

INSERT INTO public.semantic_role_graph (
    id, source_role, target_role, similarity_score, transition_probability,
    shared_skills, cluster_affinity, centrality_score, evidence, metric_period,
    generated_at, updated_at
)
SELECT
    id, source_role, target_role, similarity_score, transition_probability,
    shared_skills, cluster_affinity, centrality_score, evidence, metric_period,
    generated_at, updated_at
FROM source_snapshot.semantic_role_graph
ON CONFLICT (source_role, target_role, metric_period) DO UPDATE SET
    similarity_score = EXCLUDED.similarity_score,
    transition_probability = EXCLUDED.transition_probability,
    shared_skills = EXCLUDED.shared_skills,
    cluster_affinity = EXCLUDED.cluster_affinity,
    centrality_score = EXCLUDED.centrality_score,
    evidence = EXCLUDED.evidence,
    generated_at = EXCLUDED.generated_at,
    updated_at = EXCLUDED.updated_at;

INSERT INTO public.company_observatory (
    id, company, dominant_stack, dominant_cluster, hiring_velocity,
    ai_adoption_score, cloud_maturity_score, bi_maturity_score, technology_maturity,
    top_skills, top_clusters, evidence, metric_period, generated_at, updated_at
)
SELECT
    id, company, dominant_stack, dominant_cluster, hiring_velocity,
    ai_adoption_score, cloud_maturity_score, bi_maturity_score, technology_maturity,
    top_skills, top_clusters, evidence, metric_period, generated_at, updated_at
FROM source_snapshot.company_observatory
ON CONFLICT (company, metric_period) DO UPDATE SET
    dominant_stack = EXCLUDED.dominant_stack,
    dominant_cluster = EXCLUDED.dominant_cluster,
    hiring_velocity = EXCLUDED.hiring_velocity,
    ai_adoption_score = EXCLUDED.ai_adoption_score,
    cloud_maturity_score = EXCLUDED.cloud_maturity_score,
    bi_maturity_score = EXCLUDED.bi_maturity_score,
    technology_maturity = EXCLUDED.technology_maturity,
    top_skills = EXCLUDED.top_skills,
    top_clusters = EXCLUDED.top_clusters,
    evidence = EXCLUDED.evidence,
    generated_at = EXCLUDED.generated_at,
    updated_at = EXCLUDED.updated_at;

INSERT INTO public.emerging_technology_observatory (
    id, technology, emergence_score, growth_velocity, adoption_trend,
    forecast_confidence, source_payload, metric_period, generated_at, updated_at
)
SELECT
    id, technology, emergence_score, growth_velocity, adoption_trend,
    forecast_confidence, source_payload, metric_period, generated_at, updated_at
FROM source_snapshot.emerging_technology_observatory
ON CONFLICT (technology, metric_period) DO UPDATE SET
    emergence_score = EXCLUDED.emergence_score,
    growth_velocity = EXCLUDED.growth_velocity,
    adoption_trend = EXCLUDED.adoption_trend,
    forecast_confidence = EXCLUDED.forecast_confidence,
    source_payload = EXCLUDED.source_payload,
    generated_at = EXCLUDED.generated_at,
    updated_at = EXCLUDED.updated_at;

INSERT INTO public.career_transitions (
    id, source_role, target_role, role_progression_probability,
    transition_skill_gaps, recommended_next_skills, created_at
)
SELECT
    id, source_role, target_role, role_progression_probability,
    transition_skill_gaps, recommended_next_skills, created_at
FROM source_snapshot.career_transitions
ON CONFLICT (source_role, target_role) DO UPDATE SET
    role_progression_probability = EXCLUDED.role_progression_probability,
    transition_skill_gaps = EXCLUDED.transition_skill_gaps,
    recommended_next_skills = EXCLUDED.recommended_next_skills;

INSERT INTO public.market_forecasts (
    id, entity_type, entity_name, first_seen_at, last_seen_at, growth_velocity,
    forecast_confidence, market_phase, evidence, updated_at
)
SELECT
    id, entity_type, entity_name, first_seen_at, last_seen_at, growth_velocity,
    forecast_confidence, market_phase, evidence, updated_at
FROM source_snapshot.market_forecasts
ON CONFLICT (entity_type, entity_name) DO UPDATE SET
    first_seen_at = EXCLUDED.first_seen_at,
    last_seen_at = EXCLUDED.last_seen_at,
    growth_velocity = EXCLUDED.growth_velocity,
    forecast_confidence = EXCLUDED.forecast_confidence,
    market_phase = EXCLUDED.market_phase,
    evidence = EXCLUDED.evidence,
    updated_at = EXCLUDED.updated_at;

-- -------------------------------------------------------------------
-- Validate dashboard materialization after refresh
-- -------------------------------------------------------------------

REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_dashboard_especializacion;

COMMIT;
