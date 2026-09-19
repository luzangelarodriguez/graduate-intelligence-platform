-- Migration 032: occupational profiles catalog + job normalization columns
--
-- Introduces three objects:
--   1. occupational_profiles  — master catalog of normalized job profiles
--   2. job_profile_mappings   — rule-based mapping patterns → profile
--   3. New columns on jobs    — normalized attributes + homologation state
--
-- Design notes
-- ------------
-- * occupational_profiles holds the canonical names used in the dashboard.
--   familia groups profiles into broader families (e.g. "Gestión de Proyectos").
--   codigo_cuoc is optional; populated in a later phase.
--
-- * job_profile_mappings stores string patterns (ILIKE-style) that the Phase B
--   rule engine applies to job.title.  A job may match multiple patterns; the
--   engine picks the one with the highest confianza.
--
-- * The new jobs columns are all nullable so the migration is non-blocking:
--   existing rows stay valid; the Phase B engine backfills them.
--
-- * homologacion_estado domain:
--     pending  — not yet processed
--     auto     — assigned by the rule engine (confianza >= threshold)
--     manual   — assigned/overridden by a human reviewer
--     rejected — reviewed and intentionally left unmapped
--
-- Idempotency
-- -----------
-- All CREATE TABLE / ADD COLUMN statements use IF NOT EXISTS / IF NOT EXISTS
-- guards so the migration is safe to run more than once.

-- ── 1. occupational_profiles ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.occupational_profiles (
    id              SERIAL PRIMARY KEY,
    nombre          TEXT    NOT NULL,
    familia         TEXT    NOT NULL,
    descripcion     TEXT,
    codigo_cuoc     TEXT,
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_occupational_profiles_nombre UNIQUE (nombre)
);

CREATE INDEX IF NOT EXISTS ix_occupational_profiles_familia
    ON public.occupational_profiles (familia);

-- ── 2. job_profile_mappings ──────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.job_profile_mappings (
    id              SERIAL PRIMARY KEY,
    perfil_id       INTEGER NOT NULL REFERENCES public.occupational_profiles(id) ON DELETE CASCADE,
    patron          TEXT    NOT NULL,           -- ILIKE pattern, e.g. '%analista%proyecto%'
    metodo          TEXT    NOT NULL DEFAULT 'ilike',  -- ilike | regex | exact
    confianza       NUMERIC(4,3) NOT NULL DEFAULT 1.000 CHECK (confianza BETWEEN 0 AND 1),
    activo          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_job_profile_mappings_patron UNIQUE (patron)
);

CREATE INDEX IF NOT EXISTS ix_job_profile_mappings_perfil
    ON public.job_profile_mappings (perfil_id);

-- ── 3. New columns on jobs ───────────────────────────────────────────────────

ALTER TABLE public.jobs
    ADD COLUMN IF NOT EXISTS ciudad_normalizada    TEXT,
    ADD COLUMN IF NOT EXISTS sector_normalizado    TEXT,
    ADD COLUMN IF NOT EXISTS seniority_normalizado TEXT,
    ADD COLUMN IF NOT EXISTS perfil_id             INTEGER REFERENCES public.occupational_profiles(id),
    ADD COLUMN IF NOT EXISTS homologacion_estado   TEXT NOT NULL DEFAULT 'pending'
                                                   CHECK (homologacion_estado IN ('pending','auto','manual','rejected')),
    ADD COLUMN IF NOT EXISTS homologacion_confianza NUMERIC(4,3) CHECK (homologacion_confianza BETWEEN 0 AND 1);

CREATE INDEX IF NOT EXISTS ix_jobs_perfil_id
    ON public.jobs (perfil_id)
    WHERE perfil_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_jobs_homologacion_estado
    ON public.jobs (homologacion_estado);

-- ── 4. Seed data — 8 initial profiles + mapping patterns ────────────────────
--
-- Profiles are inserted with ON CONFLICT DO NOTHING so re-runs are safe.
-- Patterns use PostgreSQL ILIKE semantics (case-insensitive, % wildcards).

INSERT INTO public.occupational_profiles (nombre, familia, descripcion) VALUES
    ('Analista de Proyectos',
     'Gestión de Proyectos',
     'Apoya la planificación, seguimiento y control de proyectos en organizaciones'),
    ('Coordinador de Proyectos de Tecnología',
     'Gestión de Proyectos',
     'Coordina proyectos de transformación digital y TI'),
    ('Analista de Datos',
     'Analítica y Ciencia de Datos',
     'Extrae, transforma y analiza datos para generar información de negocio'),
    ('Científico de Datos',
     'Analítica y Ciencia de Datos',
     'Construye modelos estadísticos y de ML para resolver problemas de negocio'),
    ('Analista de Business Intelligence',
     'Analítica y Ciencia de Datos',
     'Diseña y mantiene reportes, dashboards y cubos de datos para la toma de decisiones'),
    ('Ingeniero de Datos',
     'Analítica y Ciencia de Datos',
     'Diseña pipelines y arquitecturas de datos (ETL/ELT, data lakes, warehouses)'),
    ('Gerente de Proyectos',
     'Gestión de Proyectos',
     'Dirige proyectos estratégicos asegurando alcance, tiempo, costo y calidad'),
    ('Analista de Inteligencia de Negocios',
     'Analítica y Ciencia de Datos',
     'Investiga tendencias de mercado y genera inteligencia competitiva con datos')
ON CONFLICT (nombre) DO NOTHING;

-- Mapping patterns — inserted after profiles to resolve perfil_id via subquery.
-- Each pattern is intentionally broad; the engine filters by confianza if needed.

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%analista%proyecto%', 0.900
FROM public.occupational_profiles WHERE nombre = 'Analista de Proyectos'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%coordinador%proyecto%tecnolog%', 0.920
FROM public.occupational_profiles WHERE nombre = 'Coordinador de Proyectos de Tecnología'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%coordinador%proyecto%', 0.780
FROM public.occupational_profiles WHERE nombre = 'Coordinador de Proyectos de Tecnología'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%analista de datos%', 0.950
FROM public.occupational_profiles WHERE nombre = 'Analista de Datos'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%data analyst%', 0.950
FROM public.occupational_profiles WHERE nombre = 'Analista de Datos'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%científico de datos%', 0.960
FROM public.occupational_profiles WHERE nombre = 'Científico de Datos'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%data scientist%', 0.960
FROM public.occupational_profiles WHERE nombre = 'Científico de Datos'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%business intelligence%', 0.930
FROM public.occupational_profiles WHERE nombre = 'Analista de Business Intelligence'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%analista bi%', 0.910
FROM public.occupational_profiles WHERE nombre = 'Analista de Business Intelligence'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%ingeniero de datos%', 0.950
FROM public.occupational_profiles WHERE nombre = 'Ingeniero de Datos'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%data engineer%', 0.950
FROM public.occupational_profiles WHERE nombre = 'Ingeniero de Datos'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%gerente de proyecto%', 0.940
FROM public.occupational_profiles WHERE nombre = 'Gerente de Proyectos'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%project manager%', 0.940
FROM public.occupational_profiles WHERE nombre = 'Gerente de Proyectos'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%inteligencia de negocios%', 0.880
FROM public.occupational_profiles WHERE nombre = 'Analista de Inteligencia de Negocios'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%market intelligence%', 0.860
FROM public.occupational_profiles WHERE nombre = 'Analista de Inteligencia de Negocios'
ON CONFLICT (patron) DO NOTHING;

-- ── Additional profiles: IA y Automatización + Liderazgo de Datos ────────────
-- Validated against real job titles (B.0.3 queries, 2026-09-18).
-- Coverage contribution: ~11 additional jobs → total ~39.9% of high/medium matches.

INSERT INTO public.occupational_profiles (nombre, familia, descripcion) VALUES
    ('Especialista en Inteligencia Artificial',
     'IA y Automatización',
     'Diseña, desarrolla e implementa soluciones basadas en IA, ML y automatización'),
    ('Director de Datos',
     'Liderazgo de Datos',
     'Dirige estrategias de datos, analítica e inteligencia artificial a nivel organizacional')
ON CONFLICT (nombre) DO NOTHING;

-- Encoding-fix patterns for "científico de datos" (DB stores titles without accent marks)
INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%cientifico%datos%', 0.940
FROM public.occupational_profiles WHERE nombre = 'Científico de Datos'
ON CONFLICT (patron) DO NOTHING;

-- "data science" covers "data science analyst" and similar English variants
INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%data science%', 0.930
FROM public.occupational_profiles WHERE nombre = 'Científico de Datos'
ON CONFLICT (patron) DO NOTHING;

-- IA patterns — space before "ia" ensures word boundary (excludes "industrial", etc.)
INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%inteligencia artificial%', 0.950
FROM public.occupational_profiles WHERE nombre = 'Especialista en Inteligencia Artificial'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%ingeniero% ia%', 0.920
FROM public.occupational_profiles WHERE nombre = 'Especialista en Inteligencia Artificial'
ON CONFLICT (patron) DO NOTHING;

-- Liderazgo de Datos patterns
INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%director%datos%', 0.930
FROM public.occupational_profiles WHERE nombre = 'Director de Datos'
ON CONFLICT (patron) DO NOTHING;

INSERT INTO public.job_profile_mappings (perfil_id, patron, confianza)
SELECT id, '%transformaci%n digital%', 0.820
FROM public.occupational_profiles WHERE nombre = 'Director de Datos'
ON CONFLICT (patron) DO NOTHING;
