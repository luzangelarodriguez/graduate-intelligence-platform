-- SNIES estadístico: matrícula y graduados por programa y año.
-- Safe migration: no DROP, no TRUNCATE.

CREATE TABLE IF NOT EXISTS public.snies_estadisticas_programa (
    id           BIGSERIAL PRIMARY KEY,
    codigo_snies INTEGER NOT NULL,
    anio         SMALLINT NOT NULL,
    matriculados INTEGER NOT NULL DEFAULT 0,
    graduados    INTEGER NOT NULL DEFAULT 0,
    inscritos    INTEGER NOT NULL DEFAULT 0,
    fuente_url   TEXT,
    loaded_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (codigo_snies, anio)
);

CREATE INDEX IF NOT EXISTS idx_snies_stats_codigo ON public.snies_estadisticas_programa(codigo_snies);
CREATE INDEX IF NOT EXISTS idx_snies_stats_anio   ON public.snies_estadisticas_programa(anio DESC);

-- Add fuente_url if the table was created before this column was defined.
ALTER TABLE public.snies_estadisticas_programa
    ADD COLUMN IF NOT EXISTS fuente_url TEXT;
