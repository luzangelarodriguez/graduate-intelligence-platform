-- Graduate Intelligence Platform
-- Migration 007: compatibility columns for legacy dashboard views and
-- enterprise labor evidence tables.

ALTER TABLE IF EXISTS public.empleos ADD COLUMN IF NOT EXISTS titulo TEXT;
ALTER TABLE IF EXISTS public.empleos ADD COLUMN IF NOT EXISTS empresa TEXT;
ALTER TABLE IF EXISTS public.empleos ADD COLUMN IF NOT EXISTS ubicacion TEXT;
ALTER TABLE IF EXISTS public.empleos ADD COLUMN IF NOT EXISTS ciudad TEXT;
ALTER TABLE IF EXISTS public.empleos ADD COLUMN IF NOT EXISTS fuente TEXT;
ALTER TABLE IF EXISTS public.empleos ADD COLUMN IF NOT EXISTS portal TEXT;
ALTER TABLE IF EXISTS public.empleos ADD COLUMN IF NOT EXISTS url TEXT;
ALTER TABLE IF EXISTS public.empleos ADD COLUMN IF NOT EXISTS fecha DATE;
ALTER TABLE IF EXISTS public.empleos ADD COLUMN IF NOT EXISTS fecha_publicacion DATE;
ALTER TABLE IF EXISTS public.empleos ADD COLUMN IF NOT EXISTS descripcion TEXT;
ALTER TABLE IF EXISTS public.empleos ADD COLUMN IF NOT EXISTS modalidad TEXT;
ALTER TABLE IF EXISTS public.empleos ADD COLUMN IF NOT EXISTS dominio TEXT;

DO $$
BEGIN
    IF to_regclass('public.empleos') IS NOT NULL THEN
        UPDATE public.empleos
        SET
            ubicacion = COALESCE(NULLIF(ubicacion, ''), ciudad),
            fuente = COALESCE(NULLIF(fuente, ''), portal),
            fecha = COALESCE(fecha, fecha_publicacion);
    END IF;
END $$;

ALTER TABLE IF EXISTS public.empleo_skills ADD COLUMN IF NOT EXISTS skill_id INTEGER;

DO $$
BEGIN
    IF to_regclass('public.empleo_skills') IS NOT NULL
       AND to_regclass('public.skills') IS NOT NULL
       AND NOT EXISTS (
           SELECT 1
           FROM pg_constraint
           WHERE conname = 'fk_empleo_skills_skill_id'
       ) THEN
        ALTER TABLE public.empleo_skills
        ADD CONSTRAINT fk_empleo_skills_skill_id
        FOREIGN KEY (skill_id) REFERENCES public.skills(id)
        ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_empleo_skills_skill_id
ON public.empleo_skills(skill_id);

CREATE INDEX IF NOT EXISTS ix_empleos_titulo_trgm
ON public.empleos USING gin (lower(titulo) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_empleos_ubicacion
ON public.empleos(ubicacion);

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
