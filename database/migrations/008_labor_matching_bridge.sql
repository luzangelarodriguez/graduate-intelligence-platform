-- Graduate Intelligence Platform
-- Migration 008: labor-program matching bridge.
-- Non destructive. No data is deleted.

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

ALTER TABLE IF EXISTS public.empleo_skills ADD COLUMN IF NOT EXISTS skill_id INTEGER;

DO $$
BEGIN
    IF to_regclass('public.empleo_skills') IS NOT NULL
       AND to_regclass('public.skills') IS NOT NULL
       AND NOT EXISTS (
           SELECT 1 FROM pg_constraint WHERE conname = 'fk_empleo_skills_skill_id'
       ) THEN
        ALTER TABLE public.empleo_skills
        ADD CONSTRAINT fk_empleo_skills_skill_id
        FOREIGN KEY (skill_id) REFERENCES public.skills(id)
        ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_labor_program_skill_matches_program_score
ON public.labor_program_skill_matches(especializacion_id, match_score DESC);

CREATE INDEX IF NOT EXISTS ix_labor_program_skill_matches_job
ON public.labor_program_skill_matches(job_id);

CREATE INDEX IF NOT EXISTS ix_labor_program_skill_matches_skill
ON public.labor_program_skill_matches(skill_id);

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
    jm.job_id AS empleo_id,
    COALESCE(e.titulo, cj.role_title, sj.titulo, '') AS titulo_empleo,
    COALESCE(e.empresa, cj.company, sj.empresa, '') AS empresa,
    COALESCE(jst.total_skills_empleo, jm.skills_en_comun, 0) AS total_skills_empleo,
    COALESCE(pst.total_skills_especializacion, 0) AS total_skills_especializacion,
    jm.skills_en_comun,
    jm.porcentaje_match,
    jm.especializacion_id,
    jm.confidence,
    'labor_program_skill_matches'::text AS match_method,
    jm.created_at
FROM job_matches jm
LEFT JOIN public.empleos e
    ON e.id::text = jm.job_id
LEFT JOIN public.canonical_jobs cj
    ON cj.id::text = jm.job_id
LEFT JOIN public.silver_normalized_jobs sj
    ON sj.id::text = jm.job_id
LEFT JOIN job_skill_totals jst
    ON jst.job_id = jm.job_id
LEFT JOIN program_skill_totals pst
    ON pst.especializacion_id = jm.especializacion_id
WHERE jm.skills_en_comun > 0;

CREATE OR REPLACE VIEW public.vw_labor_program_metrics AS
SELECT
    especializacion_id,
    ROUND(AVG(porcentaje_match)::numeric, 2) AS promedio_match_mercado,
    ROUND(MAX(porcentaje_match)::numeric, 2) AS max_match_mercado,
    COUNT(DISTINCT empleo_id)::int AS total_empleos_relacionados
FROM public.vw_labor_program_job_matches
WHERE porcentaje_match > 0
GROUP BY especializacion_id;
