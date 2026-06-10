BEGIN;

CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE OR REPLACE VIEW public.vw_programa_skills AS
WITH unified_rows AS (
    SELECT
        e.id AS especializacion_id,
        e.nombre AS especializacion,
        ROW_NUMBER() OVER (
            PARTITION BY e.id
            ORDER BY lower(unaccent(COALESCE(s.nombre, ''))), s.id
        ) AS skill_id,
        s.nombre AS skill,
        s.nombre AS nombre,
        COALESCE(NULLIF(s.categoria, ''), 'skill') AS categoria,
        'skill' AS source_kind,
        'especializacion_skills' AS source_table,
        lower(unaccent(COALESCE(s.nombre, ''))) AS skill_key
    FROM public.especializaciones e
    INNER JOIN public.especializacion_skills es
        ON es.especializacion_id = e.id
    INNER JOIN public.skills s
        ON s.id = es.skill_id
    UNION ALL
    SELECT
        e.id AS especializacion_id,
        e.nombre AS especializacion,
        ROW_NUMBER() OVER (
            PARTITION BY e.id
            ORDER BY lower(unaccent(COALESCE(c.nombre, ''))), c.id
        ) AS skill_id,
        c.nombre AS skill,
        c.nombre AS nombre,
        'competencia' AS categoria,
        'competency' AS source_kind,
        'especializacion_competencias' AS source_table,
        lower(unaccent(COALESCE(c.nombre, ''))) AS skill_key
    FROM public.especializaciones e
    INNER JOIN public.especializacion_competencias ec
        ON ec.especializacion_id = e.id
    INNER JOIN public.competencias c
        ON c.id = ec.competencia_id
    UNION ALL
    SELECT
        e.id AS especializacion_id,
        e.nombre AS especializacion,
        ROW_NUMBER() OVER (
            PARTITION BY e.id
            ORDER BY lower(unaccent(COALESCE(h.nombre, ''))), h.id
        ) AS skill_id,
        h.nombre AS skill,
        h.nombre AS nombre,
        'herramienta' AS categoria,
        'tool' AS source_kind,
        'especializacion_herramientas' AS source_table,
        lower(unaccent(COALESCE(h.nombre, ''))) AS skill_key
    FROM public.especializaciones e
    INNER JOIN public.especializacion_herramientas eh
        ON eh.especializacion_id = e.id
    INNER JOIN public.herramientas h
        ON h.id = eh.herramienta_id
    UNION ALL
    SELECT
        e.id AS especializacion_id,
        e.nombre AS especializacion,
        ROW_NUMBER() OVER (
            PARTITION BY e.id
            ORDER BY lower(unaccent(COALESCE(hb.nombre, ''))), hb.id
        ) AS skill_id,
        hb.nombre AS skill,
        hb.nombre AS nombre,
        'habilidad_blanda' AS categoria,
        'soft_skill' AS source_kind,
        'especializacion_habilidades_blandas' AS source_table,
        lower(unaccent(COALESCE(hb.nombre, ''))) AS skill_key
    FROM public.especializaciones e
    INNER JOIN public.especializacion_habilidades_blandas ehb
        ON ehb.especializacion_id = e.id
    INNER JOIN public.habilidades_blandas hb
        ON hb.id = ehb.habilidad_id
)
SELECT DISTINCT ON (especializacion_id, skill_key)
    especializacion_id,
    especializacion,
    skill_id,
    skill,
    nombre,
    categoria,
    source_kind,
    source_table,
    skill_key
FROM unified_rows
WHERE skill_key <> ''
ORDER BY especializacion_id, skill_key, source_kind, skill_id;

CREATE OR REPLACE VIEW public.vw_match_empleo_especializacion AS
WITH empleo_skills_distinct AS (
    SELECT DISTINCT
        es.empleo_id,
        lower(unaccent(COALESCE(s.nombre, ''))) AS skill_key,
        s.nombre AS skill
    FROM empleo_skills es
    INNER JOIN skills s
        ON s.id = es.skill_id
),
especializacion_skills_distinct AS (
    SELECT DISTINCT
        esp.especializacion_id,
        esp.skill_key,
        esp.skill
    FROM vw_programa_skills esp
),
program_domains AS (
    SELECT
        program_id,
        program_name,
        domain_key AS program_domain,
        domain_label AS program_domain_label
    FROM public.vw_program_domain_taxonomy
),
job_domains AS (
    SELECT
        job_id,
        job_title,
        domain_key AS job_domain,
        domain_label AS job_domain_label
    FROM public.vw_job_domain_taxonomy
),
total_skills_empleo AS (
    SELECT
        empleo_id,
        COUNT(*) AS total_skills_empleo
    FROM empleo_skills_distinct
    GROUP BY empleo_id
),
total_skills_especializacion AS (
    SELECT
        especializacion_id,
        COUNT(*) AS total_skills_especializacion
    FROM especializacion_skills_distinct
    GROUP BY especializacion_id
),
skills_en_comun AS (
    SELECT
        es.empleo_id,
        esp.especializacion_id,
        COUNT(*) AS skills_en_comun
    FROM empleo_skills_distinct es
    INNER JOIN especializacion_skills_distinct esp
        ON esp.skill_key = es.skill_key
    GROUP BY
        es.empleo_id,
        esp.especializacion_id
),
base_matches AS (
    SELECT
        e.id AS empleo_id,
        e.titulo AS titulo_empleo,
        COALESCE(jd.job_domain, '') AS job_domain,
        COALESCE(jd.job_domain_label, '') AS job_domain_label,
        s.id AS especializacion_id,
        s.nombre AS nombre_especializacion,
        COALESCE(pd.program_domain, '') AS program_domain,
        COALESCE(pd.program_domain_label, '') AS program_domain_label,
        COALESCE(te.total_skills_empleo, 0) AS total_skills_empleo,
        COALESCE(ts.total_skills_especializacion, 0) AS total_skills_especializacion,
        COALESCE(sec.skills_en_comun, 0) AS skills_en_comun
    FROM empleos e
    CROSS JOIN especializaciones s
    LEFT JOIN total_skills_empleo te
        ON te.empleo_id = e.id
    LEFT JOIN total_skills_especializacion ts
        ON ts.especializacion_id = s.id
    LEFT JOIN skills_en_comun sec
        ON sec.empleo_id = e.id
       AND sec.especializacion_id = s.id
    LEFT JOIN program_domains pd
        ON pd.program_id = s.id
    LEFT JOIN job_domains jd
        ON jd.job_id = e.id
),
scored_matches AS (
    SELECT
        base.*,
        ROUND(
            CASE
                WHEN COALESCE(total_skills_especializacion, 0) = 0 THEN 0
                ELSE (COALESCE(skills_en_comun, 0)::numeric / NULLIF(total_skills_especializacion, 0)) * 100
            END,
            2
        ) AS coverage_score,
        ROUND(
            CASE
                WHEN COALESCE(total_skills_empleo, 0) + COALESCE(total_skills_especializacion, 0) - COALESCE(skills_en_comun, 0) = 0 THEN 0
                ELSE (COALESCE(skills_en_comun, 0)::numeric / NULLIF((COALESCE(total_skills_empleo, 0) + COALESCE(total_skills_especializacion, 0) - COALESCE(skills_en_comun, 0)), 0)) * 100
            END,
            2
        ) AS jaccard_score,
        ROUND(
            CASE
                WHEN COALESCE(total_skills_empleo, 0) = 0 OR COALESCE(total_skills_especializacion, 0) = 0 THEN 0
                ELSE (COALESCE(skills_en_comun, 0)::numeric / NULLIF(SQRT((COALESCE(total_skills_empleo, 0)::numeric) * (COALESCE(total_skills_especializacion, 0)::numeric)), 0)) * 100
            END,
            2
        ) AS cosine_score
    FROM base_matches base
)
SELECT
    scored.*,
    ROUND(100 - scored.coverage_score, 2) AS gap_score,
    ROUND(((scored.jaccard_score + scored.cosine_score) / 2) * CASE
        WHEN scored.program_domain = scored.job_domain THEN 1.0
        WHEN (scored.program_domain = 'data_analytics' AND scored.job_domain IN ('artificial_intelligence', 'cybersecurity', 'finance_accounting', 'project_management', 'business_management', 'marketing_commercial', 'logistics_operations', 'legal_compliance', 'education', 'health', 'criminology_security'))
          OR (scored.job_domain = 'data_analytics' AND scored.program_domain IN ('artificial_intelligence', 'cybersecurity', 'finance_accounting', 'project_management', 'business_management', 'marketing_commercial', 'logistics_operations', 'legal_compliance', 'education', 'health', 'criminology_security'))
          OR (scored.program_domain = 'artificial_intelligence' AND scored.job_domain IN ('data_analytics', 'cybersecurity'))
          OR (scored.job_domain = 'artificial_intelligence' AND scored.program_domain IN ('data_analytics', 'cybersecurity'))
          OR (scored.program_domain = 'cybersecurity' AND scored.job_domain IN ('data_analytics', 'artificial_intelligence', 'criminology_security', 'legal_compliance'))
          OR (scored.job_domain = 'cybersecurity' AND scored.program_domain IN ('data_analytics', 'artificial_intelligence', 'criminology_security', 'legal_compliance'))
          OR (scored.program_domain = 'criminology_security' AND scored.job_domain IN ('cybersecurity', 'legal_compliance', 'business_management'))
          OR (scored.job_domain = 'criminology_security' AND scored.program_domain IN ('cybersecurity', 'legal_compliance', 'business_management'))
        THEN 0.5
        ELSE 0.1
    END, 2) AS match_score,
    ROUND(((scored.jaccard_score + scored.cosine_score) / 2) * CASE
        WHEN scored.program_domain = scored.job_domain THEN 1.0
        WHEN (scored.program_domain = 'data_analytics' AND scored.job_domain IN ('artificial_intelligence', 'cybersecurity', 'finance_accounting', 'project_management', 'business_management', 'marketing_commercial', 'logistics_operations', 'legal_compliance', 'education', 'health', 'criminology_security'))
          OR (scored.job_domain = 'data_analytics' AND scored.program_domain IN ('artificial_intelligence', 'cybersecurity', 'finance_accounting', 'project_management', 'business_management', 'marketing_commercial', 'logistics_operations', 'legal_compliance', 'education', 'health', 'criminology_security'))
          OR (scored.program_domain = 'artificial_intelligence' AND scored.job_domain IN ('data_analytics', 'cybersecurity'))
          OR (scored.job_domain = 'artificial_intelligence' AND scored.program_domain IN ('data_analytics', 'cybersecurity'))
          OR (scored.program_domain = 'cybersecurity' AND scored.job_domain IN ('data_analytics', 'artificial_intelligence', 'criminology_security', 'legal_compliance'))
          OR (scored.job_domain = 'cybersecurity' AND scored.program_domain IN ('data_analytics', 'artificial_intelligence', 'criminology_security', 'legal_compliance'))
          OR (scored.program_domain = 'criminology_security' AND scored.job_domain IN ('cybersecurity', 'legal_compliance', 'business_management'))
          OR (scored.job_domain = 'criminology_security' AND scored.program_domain IN ('cybersecurity', 'legal_compliance', 'business_management'))
        THEN 0.5
        ELSE 0.1
    END, 2) AS porcentaje_match,
    ROUND((scored.jaccard_score + scored.cosine_score) / 2, 2) AS base_similarity_score,
    CASE
        WHEN scored.program_domain = scored.job_domain THEN 1.0
        WHEN (scored.program_domain = 'data_analytics' AND scored.job_domain IN ('artificial_intelligence', 'cybersecurity', 'finance_accounting', 'project_management', 'business_management', 'marketing_commercial', 'logistics_operations', 'legal_compliance', 'education', 'health', 'criminology_security'))
          OR (scored.job_domain = 'data_analytics' AND scored.program_domain IN ('artificial_intelligence', 'cybersecurity', 'finance_accounting', 'project_management', 'business_management', 'marketing_commercial', 'logistics_operations', 'legal_compliance', 'education', 'health', 'criminology_security'))
          OR (scored.program_domain = 'artificial_intelligence' AND scored.job_domain IN ('data_analytics', 'cybersecurity'))
          OR (scored.job_domain = 'artificial_intelligence' AND scored.program_domain IN ('data_analytics', 'cybersecurity'))
          OR (scored.program_domain = 'cybersecurity' AND scored.job_domain IN ('data_analytics', 'artificial_intelligence', 'criminology_security', 'legal_compliance'))
          OR (scored.job_domain = 'cybersecurity' AND scored.program_domain IN ('data_analytics', 'artificial_intelligence', 'criminology_security', 'legal_compliance'))
          OR (scored.program_domain = 'criminology_security' AND scored.job_domain IN ('cybersecurity', 'legal_compliance', 'business_management'))
          OR (scored.job_domain = 'criminology_security' AND scored.program_domain IN ('cybersecurity', 'legal_compliance', 'business_management'))
        THEN 0.5
        ELSE 0.1
    END AS domain_score,
    CASE
        WHEN scored.program_domain = scored.job_domain THEN 1.0
        WHEN (scored.program_domain = 'data_analytics' AND scored.job_domain IN ('artificial_intelligence', 'cybersecurity', 'finance_accounting', 'project_management', 'business_management', 'marketing_commercial', 'logistics_operations', 'legal_compliance', 'education', 'health', 'criminology_security'))
          OR (scored.job_domain = 'data_analytics' AND scored.program_domain IN ('artificial_intelligence', 'cybersecurity', 'finance_accounting', 'project_management', 'business_management', 'marketing_commercial', 'logistics_operations', 'legal_compliance', 'education', 'health', 'criminology_security'))
          OR (scored.program_domain = 'artificial_intelligence' AND scored.job_domain IN ('data_analytics', 'cybersecurity'))
          OR (scored.job_domain = 'artificial_intelligence' AND scored.program_domain IN ('data_analytics', 'cybersecurity'))
          OR (scored.program_domain = 'cybersecurity' AND scored.job_domain IN ('data_analytics', 'artificial_intelligence', 'criminology_security', 'legal_compliance'))
          OR (scored.job_domain = 'cybersecurity' AND scored.program_domain IN ('data_analytics', 'artificial_intelligence', 'criminology_security', 'legal_compliance'))
          OR (scored.program_domain = 'criminology_security' AND scored.job_domain IN ('cybersecurity', 'legal_compliance', 'business_management'))
          OR (scored.job_domain = 'criminology_security' AND scored.program_domain IN ('cybersecurity', 'legal_compliance', 'business_management'))
        THEN 0.5
        ELSE 0.1
    END AS domain_weight,
    scored.skills_en_comun AS total_skills_comunes,
    CASE
        WHEN COALESCE(scored.skills_en_comun, 0) < 3
         AND ROUND((scored.jaccard_score + scored.cosine_score) / 2, 2) <= 80
        THEN FALSE
        ELSE TRUE
    END AS passes_skill_threshold
FROM scored_matches scored;

CREATE OR REPLACE VIEW public.vw_match_empleo_especializacion_positivo AS
SELECT *
FROM public.vw_match_empleo_especializacion
WHERE passes_skill_threshold = TRUE;

CREATE OR REPLACE VIEW public.vw_program_recommended_jobs AS
SELECT
    especializacion_id AS program_id,
    program_domain,
    job_domain,
    domain_score,
    domain_weight,
    base_match_score,
    base_similarity_score,
    empleo_id AS job_id,
    titulo_empleo AS job_title,
    porcentaje_match AS similarity_score,
    coverage_score,
    gap_score,
    match_score,
    total_skills_empleo,
    total_skills_especializacion,
    skills_en_comun,
    total_skills_comunes
FROM public.vw_match_empleo_especializacion_positivo
WHERE passes_skill_threshold = TRUE;

CREATE OR REPLACE VIEW public.vw_program_skill_gaps AS
WITH program_skill_keys AS (
    SELECT DISTINCT
        especializacion_id,
        skill_key
    FROM public.vw_programa_skills
),
program_domains AS (
    SELECT
        program_id,
        program_name,
        domain_key AS program_domain,
        domain_label AS program_domain_label
    FROM public.vw_program_domain_taxonomy
),
market_skill_hits AS (
    SELECT
        m.especializacion_id AS program_id,
        s.nombre AS skill,
        COUNT(DISTINCT m.empleo_id)::int AS gap_frequency
    FROM public.vw_match_empleo_especializacion_positivo m
    INNER JOIN program_domains pd
        ON pd.program_id = m.especializacion_id
    INNER JOIN public.empleo_skills es
        ON es.empleo_id = m.empleo_id
    INNER JOIN public.skills s
        ON s.id = es.skill_id
    LEFT JOIN program_skill_keys psk
        ON psk.especializacion_id = m.especializacion_id
       AND psk.skill_key = lower(unaccent(COALESCE(s.nombre, '')))
    WHERE psk.skill_key IS NULL
      AND COALESCE(m.program_domain, '') <> ''
      AND COALESCE(m.job_domain, '') <> ''
      AND m.program_domain = m.job_domain
    GROUP BY m.especializacion_id, s.nombre
)
SELECT
    program_id,
    skill,
    gap_frequency
FROM market_skill_hits;

CREATE OR REPLACE VIEW public.vw_program_market_alignment AS
WITH market_alignment AS (
    SELECT
        especializacion_id AS program_id,
        ROUND(AVG(match_score)::numeric, 2) AS market_alignment_score,
        ROUND(AVG(coverage_score)::numeric, 2) AS coverage_score,
        ROUND(AVG(gap_score)::numeric, 2) AS gap_score,
        COUNT(DISTINCT empleo_id)::int AS matched_jobs
    FROM public.vw_match_empleo_especializacion_positivo
    GROUP BY especializacion_id
),
top_missing_skills AS (
    SELECT
        g.program_id,
        COALESCE(
            jsonb_agg(g.skill ORDER BY g.gap_frequency DESC, g.skill),
            '[]'::jsonb
        ) AS missing_skills
    FROM (
        SELECT
            program_id,
            skill,
            gap_frequency,
            ROW_NUMBER() OVER (PARTITION BY program_id ORDER BY gap_frequency DESC, skill) AS rn
        FROM public.vw_program_skill_gaps
    ) g
    WHERE g.rn <= 10
    GROUP BY g.program_id
)
SELECT
    e.id AS program_id,
    e.nombre AS program_name,
    COALESCE(ma.market_alignment_score, 0) AS market_alignment_score,
    COALESCE(ma.coverage_score, 0) AS coverage_score,
    COALESCE(ma.gap_score, 0) AS gap_score,
    COALESCE(ma.matched_jobs, 0) AS matched_jobs,
    COALESCE(tms.missing_skills, '[]'::jsonb) AS missing_skills
FROM especializaciones e
LEFT JOIN market_alignment ma
    ON ma.program_id = e.id
LEFT JOIN top_missing_skills tms
    ON tms.program_id = e.id;

CREATE OR REPLACE VIEW public.vw_program_program_similarity AS
WITH program_skill_distinct AS (
    SELECT DISTINCT
        especializacion_id,
        skill_key
    FROM public.vw_programa_skills
),
program_skill_counts AS (
    SELECT
        especializacion_id,
        COUNT(*) AS total_skills_programa
    FROM program_skill_distinct
    GROUP BY especializacion_id
),
shared_skills AS (
    SELECT
        left_program.especializacion_id AS program_id,
        right_program.especializacion_id AS peer_program_id,
        COUNT(*) AS shared_skills
    FROM program_skill_distinct left_program
    INNER JOIN program_skill_distinct right_program
        ON right_program.skill_key = left_program.skill_key
       AND right_program.especializacion_id <> left_program.especializacion_id
    GROUP BY
        left_program.especializacion_id,
        right_program.especializacion_id
)
SELECT
    p1.id AS program_id,
    p1.nombre AS program_name,
    p2.id AS peer_program_id,
    p2.nombre AS peer_program_name,
    COALESCE(ss.shared_skills, 0) AS shared_skills,
    COALESCE(pc1.total_skills_programa, 0) AS total_skills_programa,
    COALESCE(pc2.total_skills_programa, 0) AS peer_total_skills_programa,
    ROUND(
        CASE
            WHEN COALESCE(pc1.total_skills_programa, 0) = 0 THEN 0
            ELSE (COALESCE(ss.shared_skills, 0)::numeric / NULLIF(pc1.total_skills_programa, 0)) * 100
        END,
        2
    ) AS coverage_score,
    ROUND(
        CASE
            WHEN COALESCE(pc1.total_skills_programa, 0) + COALESCE(pc2.total_skills_programa, 0) - COALESCE(ss.shared_skills, 0) = 0 THEN 0
            ELSE (COALESCE(ss.shared_skills, 0)::numeric / NULLIF((COALESCE(pc1.total_skills_programa, 0) + COALESCE(pc2.total_skills_programa, 0) - COALESCE(ss.shared_skills, 0)), 0)) * 100
        END,
        2
    ) AS jaccard_score,
    ROUND(
        CASE
            WHEN COALESCE(pc1.total_skills_programa, 0) = 0 OR COALESCE(pc2.total_skills_programa, 0) = 0 THEN 0
            ELSE (COALESCE(ss.shared_skills, 0)::numeric / NULLIF(SQRT((COALESCE(pc1.total_skills_programa, 0)::numeric) * (COALESCE(pc2.total_skills_programa, 0)::numeric)), 0)) * 100
        END,
        2
    ) AS cosine_score,
    ROUND(100 - (
        CASE
            WHEN COALESCE(pc1.total_skills_programa, 0) = 0 THEN 0
            ELSE (COALESCE(ss.shared_skills, 0)::numeric / NULLIF(pc1.total_skills_programa, 0)) * 100
        END
    ), 2) AS gap_score,
    ROUND((
        CASE
            WHEN COALESCE(pc1.total_skills_programa, 0) + COALESCE(pc2.total_skills_programa, 0) - COALESCE(ss.shared_skills, 0) = 0 THEN 0
            ELSE (COALESCE(ss.shared_skills, 0)::numeric / NULLIF((COALESCE(pc1.total_skills_programa, 0) + COALESCE(pc2.total_skills_programa, 0) - COALESCE(ss.shared_skills, 0)), 0)) * 100
        END
    + CASE
            WHEN COALESCE(pc1.total_skills_programa, 0) = 0 OR COALESCE(pc2.total_skills_programa, 0) = 0 THEN 0
            ELSE (COALESCE(ss.shared_skills, 0)::numeric / NULLIF(SQRT((COALESCE(pc1.total_skills_programa, 0)::numeric) * (COALESCE(pc2.total_skills_programa, 0)::numeric)), 0)) * 100
        END) / 2, 2) AS similarity_score
FROM especializaciones p1
INNER JOIN especializaciones p2
    ON p1.id <> p2.id
LEFT JOIN shared_skills ss
    ON ss.program_id = p1.id
   AND ss.peer_program_id = p2.id
LEFT JOIN program_skill_counts pc1
    ON pc1.especializacion_id = p1.id
LEFT JOIN program_skill_counts pc2
    ON pc2.especializacion_id = p2.id;

COMMIT;
