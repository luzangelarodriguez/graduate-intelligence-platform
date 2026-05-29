-- Graduate Intelligence Platform
-- Migration 002: curricular core schema and compatibility columns.
-- Purpose: make the academic/curricular observatory tables explicit and
-- idempotent instead of relying on scraper bootstrap code.

CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

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

ALTER TABLE public.especializaciones ADD COLUMN IF NOT EXISTS descripcion TEXT;
ALTER TABLE public.especializaciones ADD COLUMN IF NOT EXISTS rol TEXT;
ALTER TABLE public.especializaciones ADD COLUMN IF NOT EXISTS facultad TEXT;
ALTER TABLE public.especializaciones ADD COLUMN IF NOT EXISTS nivel TEXT NOT NULL DEFAULT 'Posgrado';
ALTER TABLE public.especializaciones ADD COLUMN IF NOT EXISTS estado TEXT NOT NULL DEFAULT 'Activo';
ALTER TABLE public.especializaciones ADD COLUMN IF NOT EXISTS modalidad TEXT NOT NULL DEFAULT 'Virtual';
ALTER TABLE public.especializaciones ADD COLUMN IF NOT EXISTS campo_laboral TEXT;
ALTER TABLE public.especializaciones ADD COLUMN IF NOT EXISTS plan_estudios TEXT;
ALTER TABLE public.especializaciones ADD COLUMN IF NOT EXISTS general_text TEXT;
ALTER TABLE public.especializaciones ADD COLUMN IF NOT EXISTS source_url TEXT;
ALTER TABLE public.especializaciones ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE public.especializaciones ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

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

ALTER TABLE public.skills ADD COLUMN IF NOT EXISTS categoria TEXT;
ALTER TABLE public.skills ADD COLUMN IF NOT EXISTS dominio TEXT;
ALTER TABLE public.skills ADD COLUMN IF NOT EXISTS tipo TEXT;
ALTER TABLE public.skills ADD COLUMN IF NOT EXISTS descripcion TEXT;
ALTER TABLE public.skills ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE public.skills ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS public.herramientas (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    categoria TEXT,
    dominio TEXT,
    descripcion TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.herramientas ADD COLUMN IF NOT EXISTS categoria TEXT;
ALTER TABLE public.herramientas ADD COLUMN IF NOT EXISTS dominio TEXT;
ALTER TABLE public.herramientas ADD COLUMN IF NOT EXISTS descripcion TEXT;
ALTER TABLE public.herramientas ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE public.herramientas ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS public.competencias (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    categoria TEXT,
    dominio TEXT,
    descripcion TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.competencias ADD COLUMN IF NOT EXISTS categoria TEXT;
ALTER TABLE public.competencias ADD COLUMN IF NOT EXISTS dominio TEXT;
ALTER TABLE public.competencias ADD COLUMN IF NOT EXISTS descripcion TEXT;
ALTER TABLE public.competencias ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE public.competencias ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS public.habilidades_blandas (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    categoria TEXT,
    dominio TEXT,
    descripcion TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.habilidades_blandas ADD COLUMN IF NOT EXISTS categoria TEXT;
ALTER TABLE public.habilidades_blandas ADD COLUMN IF NOT EXISTS dominio TEXT;
ALTER TABLE public.habilidades_blandas ADD COLUMN IF NOT EXISTS descripcion TEXT;
ALTER TABLE public.habilidades_blandas ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE public.habilidades_blandas ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

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

CREATE TABLE IF NOT EXISTS public.perfiles_egreso (
    id SERIAL PRIMARY KEY,
    especializacion_id INTEGER NOT NULL REFERENCES public.especializaciones(id) ON DELETE CASCADE,
    perfil TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (especializacion_id, perfil)
);

CREATE INDEX IF NOT EXISTS ix_especializaciones_nombre_trgm
ON public.especializaciones USING gin (lower(nombre) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_especializaciones_estado_modalidad
ON public.especializaciones(estado, modalidad);

CREATE INDEX IF NOT EXISTS ix_skills_nombre_trgm
ON public.skills USING gin (lower(nombre) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_skills_categoria
ON public.skills(categoria);

CREATE INDEX IF NOT EXISTS ix_especializacion_skills_skill
ON public.especializacion_skills(skill_id);

CREATE INDEX IF NOT EXISTS ix_especializacion_herramientas_herramienta
ON public.especializacion_herramientas(herramienta_id);

CREATE INDEX IF NOT EXISTS ix_especializacion_competencias_competencia
ON public.especializacion_competencias(competencia_id);

CREATE INDEX IF NOT EXISTS ix_especializacion_habilidades_habilidad
ON public.especializacion_habilidades_blandas(habilidad_id);
