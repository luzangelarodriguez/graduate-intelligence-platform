-- Migration 026: Job TTL, soft-delete, and trend analysis support
-- Adds activo, fecha_expiracion, fecha_desactivacion to jobs and empleos
-- NO DELETE policy — full historical record is preserved for trend analysis
--
-- TTL by source (days from fecha_publicacion or created_at as fallback):
--   Computrabajo: 60 days (confirmed official policy)
--   All other sources: 60 days (conservative default, revise per source as verified)

-- ─── empleos ────────────────────────────────────────────────────────────────
-- fecha_publicacion already exists; add the three new lifecycle columns

ALTER TABLE public.empleos
    ADD COLUMN IF NOT EXISTS fecha_expiracion     DATE,
    ADD COLUMN IF NOT EXISTS activo               BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS fecha_desactivacion  TIMESTAMPTZ;

-- Back-fill fecha_expiracion for existing rows:
--   Use fecha_publicacion when available, else created_at as fallback.
--   TTL = 60 days for all sources until individually verified.
UPDATE public.empleos
SET fecha_expiracion = COALESCE(fecha_publicacion, created_at::date) + INTERVAL '60 days'
WHERE fecha_expiracion IS NULL;

-- Soft-deactivate rows whose expiration has already passed
UPDATE public.empleos
SET activo              = FALSE,
    fecha_desactivacion = NOW()
WHERE activo = TRUE
  AND fecha_expiracion < CURRENT_DATE;

-- Index for fast deactivation sweep and active-only filtering
CREATE INDEX IF NOT EXISTS ix_empleos_activo_expiracion
    ON public.empleos (activo, fecha_expiracion);

-- ─── jobs ───────────────────────────────────────────────────────────────────
-- jobs has no fecha_publicacion; use created_at as the anchor

ALTER TABLE public.jobs
    ADD COLUMN IF NOT EXISTS fecha_publicacion    DATE,
    ADD COLUMN IF NOT EXISTS fecha_expiracion     DATE,
    ADD COLUMN IF NOT EXISTS activo               BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS fecha_desactivacion  TIMESTAMPTZ;

-- Back-fill fecha_publicacion from created_at (best available proxy)
UPDATE public.jobs
SET fecha_publicacion = created_at::date
WHERE fecha_publicacion IS NULL;

-- Back-fill fecha_expiracion = fecha_publicacion + 60 days
UPDATE public.jobs
SET fecha_expiracion = fecha_publicacion + INTERVAL '60 days'
WHERE fecha_expiracion IS NULL;

-- Soft-deactivate rows whose expiration has already passed
UPDATE public.jobs
SET activo              = FALSE,
    fecha_desactivacion = NOW()
WHERE activo = TRUE
  AND fecha_expiracion < CURRENT_DATE;

-- Index for fast deactivation sweep and active-only filtering
CREATE INDEX IF NOT EXISTS ix_jobs_activo_expiracion
    ON public.jobs (activo, fecha_expiracion);

-- ─── Trend analysis helper function ─────────────────────────────────────────
-- skills_trend(skill, fecha_inicio, fecha_fin):
--   Counts how many ACTIVE-DURING-PERIOD vacantes from both tables mention a skill.
--   A vacancy is "active during period" if:
--     - Its fecha_publicacion <= fecha_fin  (it existed before the period ended)
--     - AND (fecha_expiracion >= fecha_inicio OR activo = TRUE)  (still live at some point in the period)
--   Returns the total count across empleos + jobs for trend comparison over time.

CREATE OR REPLACE FUNCTION public.skills_trend(
    p_skill       TEXT,
    p_fecha_inicio DATE,
    p_fecha_fin    DATE
) RETURNS BIGINT
LANGUAGE sql
STABLE
AS $$
    SELECT COUNT(DISTINCT job_key) FROM (
        -- empleos side: skill is stored in empleo_skills.skill_normalized / skill_original
        SELECT e.id::text AS job_key
        FROM public.empleos e
        JOIN public.empleo_skills es ON es.empleo_id = e.id
        WHERE (
            LOWER(COALESCE(es.skill_normalized, es.skill_original)) = LOWER(p_skill)
        )
          AND COALESCE(e.fecha_publicacion, e.created_at::date) <= p_fecha_fin
          AND (e.fecha_expiracion >= p_fecha_inicio OR e.activo = TRUE)

        UNION ALL

        -- jobs side: skill is stored in job_skills.canonical_skill
        SELECT j.id::text AS job_key
        FROM public.jobs j
        JOIN public.job_skills js ON js.job_id = j.id
        WHERE LOWER(js.canonical_skill) = LOWER(p_skill)
          AND j.fecha_publicacion <= p_fecha_fin
          AND (j.fecha_expiracion >= p_fecha_inicio OR j.activo = TRUE)
    ) combined;
$$;

COMMENT ON FUNCTION public.skills_trend(TEXT, DATE, DATE) IS
'Returns count of vacantes (empleos + jobs) that were active during [fecha_inicio, fecha_fin]
and mention the given skill. Use for month-over-month demand trend analysis once
2-3 months of historical data have accumulated. REST endpoint and UI not implemented yet.';
