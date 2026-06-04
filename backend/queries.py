from __future__ import annotations

from typing import Any

from backend.db import get_conn, get_cursor
from backend.services.domain_taxonomy import (
    DOMAIN_LABELS,
    build_sql_domain_case,
    build_sql_job_domain_case,
    build_sql_domain_weight_case,
    JOB_DOMAIN_LABELS,
)


def _sql_domain_label_case(domain_expr: str, labels: dict[str, str] | None = None) -> str:
    label_map = labels or DOMAIN_LABELS
    clauses = [f"WHEN {domain_expr} = '{domain_key}' THEN '{label}'" for domain_key, label in label_map.items()]
    default_label = label_map.get("business_management", "Business Management")
    return "CASE\n" + "\n".join(clauses) + f"\nELSE '{default_label}'\nEND"


def _sql_literal(value: str) -> str:
    return value.replace("'", "''")


def _program_base_sql() -> str:
    return """
SELECT
    s.id AS program_id,
    s.nombre AS program_name,
    COALESCE(s.descripcion, '') AS program_description,
    COALESCE(s.facultad, '') AS faculty,
    COALESCE(s.rol, '') AS role,
    COALESCE(s.campo_laboral, '') AS field,
    lower(unaccent(COALESCE(s.nombre, ''))) AS normalized_program_name,
    COALESCE(ps.total_skills_programa, 0) AS total_skills_programa,
    COALESCE(ph.total_herramientas, 0) AS total_herramientas,
    COALESCE(pc.total_competencias, 0) AS total_competencias,
    COALESCE(pbl.total_habilidades_blandas, 0) AS total_habilidades_blandas,
    CASE
        WHEN COALESCE(s.source_url, '') <> '' OR COALESCE(s.plan_estudios, '') <> '' THEN 0
        ELSE 1
    END AS source_priority,
    CASE WHEN COALESCE(s.rol, '') <> '' THEN 0 ELSE 1 END AS role_priority,
    CASE WHEN s.nombre ~ '^[A-Z]' THEN 0 ELSE 1 END AS casing_priority
FROM public.especializaciones s
LEFT JOIN (
    SELECT especializacion_id, COUNT(DISTINCT skill_id)::int AS total_skills_programa
    FROM public.especializacion_skills
    GROUP BY especializacion_id
) ps ON ps.especializacion_id = s.id
LEFT JOIN (
    SELECT especializacion_id, COUNT(DISTINCT herramienta_id)::int AS total_herramientas
    FROM public.especializacion_herramientas
    GROUP BY especializacion_id
) ph ON ph.especializacion_id = s.id
LEFT JOIN (
    SELECT especializacion_id, COUNT(DISTINCT competencia_id)::int AS total_competencias
    FROM public.especializacion_competencias
    GROUP BY especializacion_id
) pc ON pc.especializacion_id = s.id
LEFT JOIN (
    SELECT especializacion_id, COUNT(DISTINCT habilidad_id)::int AS total_habilidades_blandas
    FROM public.especializacion_habilidades_blandas
    GROUP BY especializacion_id
) pbl ON pbl.especializacion_id = s.id
"""


PROGRAM_DOMAIN_MAPPING_SEED_ROWS = (
    (108, "criminology_security", "Criminology & Security"),
    (107, "health", "Health"),
    (82, "business_management", "Business Management"),
    (97, "legal_compliance", "Legal & Compliance"),
    (100, "legal_compliance", "Legal & Compliance"),
    (99, "legal_compliance", "Legal & Compliance"),
    (88, "marketing_commercial", "Marketing & Commercial"),
    (90, "project_management", "Project Management"),
    (96, "data_analytics", "Data & Analytics"),
    (105, "education", "Education"),
    (102, "education", "Education"),
    (104, "education", "Education"),
    (84, "finance_accounting", "Finance & Accounting"),
    (95, "logistics_operations", "Logistics & Operations"),
    (83, "health", "Health"),
    (86, "business_management", "Business Management"),
    (98, "legal_compliance", "Legal & Compliance"),
    (91, "data_analytics", "Data & Analytics"),
    (92, "artificial_intelligence", "Artificial Intelligence"),
    (85, "data_analytics", "Data & Analytics"),
    (87, "marketing_commercial", "Marketing & Commercial"),
    (101, "education", "Education"),
    (106, "education", "Education"),
    (89, "finance_accounting", "Finance & Accounting"),
    (93, "cybersecurity", "Cybersecurity"),
    (103, "education", "Education"),
    (94, "data_analytics", "Data & Analytics"),
)

PROGRAM_DOMAIN_MAPPING_SEED_VALUES_SQL = ",\n        ".join(
    f"({program_id}, '{_sql_literal(domain_key)}', '{_sql_literal(domain_label)}')"
    for program_id, domain_key, domain_label in PROGRAM_DOMAIN_MAPPING_SEED_ROWS
)


PROGRAM_DOMAIN_MAPPING_SQL = '''
CREATE TABLE IF NOT EXISTS public.program_domain_mapping (
    program_id integer PRIMARY KEY,
    program_name text NOT NULL,
    domain_key text NOT NULL,
    domain_label text NOT NULL,
    is_manual boolean NOT NULL DEFAULT TRUE,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO public.program_domain_mapping (program_id, program_name, domain_key, domain_label, is_manual, created_at, updated_at)
WITH canonical_programs AS (
    SELECT *
    FROM (
        SELECT
            base.*,
            ROW_NUMBER() OVER (
                PARTITION BY base.normalized_program_name
                ORDER BY
                    base.source_priority,
                    base.total_skills_programa DESC,
                    base.role_priority,
                    base.casing_priority,
                    base.program_id DESC
            ) AS program_rank
        FROM ({program_base_sql}) base
    ) ranked
    WHERE ranked.program_rank = 1
)
SELECT
    s.program_id,
    s.program_name,
    seed.domain_key,
    seed.domain_label,
    TRUE,
    now(),
    now()
FROM (
    VALUES
        {seed_values}
) AS seed(program_id, domain_key, domain_label)
INNER JOIN canonical_programs s
    ON s.program_id = seed.program_id
ON CONFLICT (program_id) DO UPDATE SET
    program_name = EXCLUDED.program_name,
    domain_key = EXCLUDED.domain_key,
    domain_label = EXCLUDED.domain_label,
    is_manual = TRUE,
    updated_at = now();
'''.format(
    seed_values=PROGRAM_DOMAIN_MAPPING_SEED_VALUES_SQL,
    program_base_sql=_program_base_sql(),
)


PROGRAM_BASE_SQL = """
SELECT
    s.id AS program_id,
    s.nombre AS program_name,
    COALESCE(s.descripcion, '') AS program_description,
    COALESCE(s.facultad, '') AS faculty,
    COALESCE(s.rol, '') AS role,
    COALESCE(s.campo_laboral, '') AS field,
    lower(unaccent(COALESCE(s.nombre, ''))) AS normalized_program_name,
    COALESCE(ps.total_skills_programa, 0) AS total_skills_programa,
    COALESCE(ph.total_herramientas, 0) AS total_herramientas,
    COALESCE(pc.total_competencias, 0) AS total_competencias,
    COALESCE(pbl.total_habilidades_blandas, 0) AS total_habilidades_blandas,
    CASE
        WHEN COALESCE(s.source_url, '') <> '' OR COALESCE(s.plan_estudios, '') <> '' THEN 0
        ELSE 1
    END AS source_priority,
    CASE WHEN COALESCE(s.rol, '') <> '' THEN 0 ELSE 1 END AS role_priority,
    CASE WHEN s.nombre ~ '^[A-Z]' THEN 0 ELSE 1 END AS casing_priority
FROM public.especializaciones s
LEFT JOIN (
    SELECT especializacion_id, COUNT(DISTINCT skill_id)::int AS total_skills_programa
    FROM public.especializacion_skills
    GROUP BY especializacion_id
) ps ON ps.especializacion_id = s.id
LEFT JOIN (
    SELECT especializacion_id, COUNT(DISTINCT herramienta_id)::int AS total_herramientas
    FROM public.especializacion_herramientas
    GROUP BY especializacion_id
) ph ON ph.especializacion_id = s.id
LEFT JOIN (
    SELECT especializacion_id, COUNT(DISTINCT competencia_id)::int AS total_competencias
    FROM public.especializacion_competencias
    GROUP BY especializacion_id
) pc ON pc.especializacion_id = s.id
LEFT JOIN (
    SELECT especializacion_id, COUNT(DISTINCT habilidad_id)::int AS total_habilidades_blandas
    FROM public.especializacion_habilidades_blandas
    GROUP BY especializacion_id
) pbl ON pbl.especializacion_id = s.id
"""


SKILL_DOMAIN_TAXONOMY_SQL = '''
CREATE OR REPLACE VIEW public.vw_skill_domain_taxonomy AS
SELECT
    canonical_skill_id,
    canonical_skill,
    skill_category,
    skill_family,
    aliases_text,
    alias_keys,
    {skill_domain_sql} AS domain_key,
    {skill_domain_label_sql} AS domain_label
FROM (
    SELECT
        s.id AS canonical_skill_id,
        s.nombre AS canonical_skill,
        'skill'::text AS skill_category,
        'skill'::text AS skill_family,
        ''::text AS aliases_text,
        ''::text AS alias_keys
    FROM public.skills s
) classified;
'''.format(
    skill_domain_sql=build_sql_domain_case("concat_ws(' ', canonical_skill, skill_category, skill_family, aliases_text, alias_keys)"),
    skill_domain_label_sql=_sql_domain_label_case(build_sql_domain_case("concat_ws(' ', canonical_skill, skill_category, skill_family, aliases_text, alias_keys)")),
)


SKILL_ALIAS_DOMAIN_TAXONOMY_SQL = '''
CREATE OR REPLACE VIEW public.vw_skill_alias_domain_taxonomy AS
SELECT
    alias_id,
    canonical_skill_id,
    canonical_skill,
    skill_category,
    skill_family,
    alias,
    normalized_alias,
    {skill_domain_sql} AS domain_key,
    {skill_domain_label_sql} AS domain_label
FROM (
    SELECT
        s.id AS alias_id,
        s.id AS canonical_skill_id,
        s.nombre AS canonical_skill,
        'skill'::text AS skill_category,
        'skill'::text AS skill_family,
        s.nombre AS alias,
        lower(unaccent(COALESCE(s.nombre, ''))) AS normalized_alias
    FROM public.skills s
) classified;
'''.format(
    skill_domain_sql=build_sql_domain_case("concat_ws(' ', canonical_skill, skill_category, skill_family, alias, normalized_alias)"),
    skill_domain_label_sql=_sql_domain_label_case(build_sql_domain_case("concat_ws(' ', canonical_skill, skill_category, skill_family, alias, normalized_alias)")),
)


PROGRAM_DOMAIN_TAXONOMY_SQL = '''
CREATE OR REPLACE VIEW public.vw_program_domain_taxonomy AS
WITH program_base AS (
    SELECT *
    FROM (
        SELECT
            base.*,
            ROW_NUMBER() OVER (
                PARTITION BY base.normalized_program_name
                ORDER BY
                    base.source_priority,
                    base.total_skills_programa DESC,
                    base.role_priority,
                    base.casing_priority,
                    base.program_id DESC
            ) AS program_rank
        FROM ({program_base_sql}) base
    ) ranked
    WHERE ranked.program_rank = 1
),
program_context AS (
    SELECT
        pb.program_id,
        pb.program_name,
        pb.faculty AS facultad,
        pb.role AS rol,
        pb.field AS campo_laboral,
        COALESCE(pb.program_description, '') AS general_text,
        COALESCE(string_agg(DISTINCT ps.skill, ' ' ORDER BY ps.skill), '') AS skill_text,
        COALESCE(string_agg(DISTINCT ps.skill_domain, ' ' ORDER BY ps.skill_domain), '') AS skill_domains,
        COALESCE(string_agg(DISTINCT ps.categoria, ' ' ORDER BY ps.categoria), '') AS skill_categories
    FROM program_base pb
    LEFT JOIN public.vw_programa_skills ps
        ON ps.especializacion_id = pb.program_id
    GROUP BY
        pb.program_id,
        pb.program_name,
        pb.faculty,
        pb.role,
        pb.field,
        pb.program_description
),
classified AS (
    SELECT
        pc.program_id,
        pc.program_name,
        pc.facultad,
        pc.rol,
        pc.campo_laboral,
        pc.general_text,
        pc.skill_text,
        pc.skill_domains,
        pc.skill_categories,
        COALESCE(pdm.domain_key, {program_domain_sql}) AS domain_key
    FROM program_context pc
    LEFT JOIN public.program_domain_mapping pdm
        ON pdm.program_id = pc.program_id
)
SELECT
    program_id,
    program_name,
    facultad,
    rol,
    campo_laboral,
    general_text,
    skill_text,
    skill_domains,
    skill_categories,
    domain_key,
    {program_domain_label_sql} AS domain_label
FROM classified;
'''.format(
    program_base_sql=PROGRAM_BASE_SQL,
    program_domain_sql=build_sql_domain_case("concat_ws(' ', pc.program_name, pc.general_text, pc.skill_text, pc.skill_domains, pc.skill_categories)"),
    program_domain_label_sql=_sql_domain_label_case("domain_key"),
)


JOB_DOMAIN_TAXONOMY_SQL = '''
CREATE OR REPLACE VIEW public.vw_job_domain_taxonomy AS
WITH job_context AS (
    SELECT
        j.id AS job_id,
        COALESCE(j.title, '') AS job_title,
        COALESCE(j.description, '') AS job_description,
        COALESCE(j.company, '') AS company,
        COALESCE(j.location, '') AS location,
        COALESCE(j.created_at::text, '') AS job_date,
        COALESCE(j.source, '') AS source,
        COALESCE(j.industry, '') AS declared_program,
        COALESCE(COALESCE(j.job_probability_score, 0)::text, '') AS best_score,
        COALESCE(string_agg(DISTINCT COALESCE(js.canonical_skill, js.skill_family, js.skill_category, ''), ' ' ORDER BY COALESCE(js.canonical_skill, js.skill_family, js.skill_category, '')), '') AS skill_text,
        COALESCE(string_agg(DISTINCT {job_skill_domain_sql}, ' ' ORDER BY {job_skill_domain_sql}), '') AS skill_domains
    FROM public.jobs j
    LEFT JOIN public.job_skills js
        ON js.job_id = j.id
    GROUP BY
        j.id,
        j.title,
        j.description,
        j.company,
        j.location,
        j.created_at::text,
        j.source,
        j.industry,
        j.job_probability_score
),
classified AS (
    SELECT
        job_id,
        job_title,
        job_description,
        company,
        location,
        job_date,
        source,
        declared_program,
        best_score,
        skill_text,
        skill_domains,
        {job_domain_sql} AS domain_key
    FROM job_context
)
SELECT
    job_id,
    job_title,
    job_description,
    company,
    location,
    job_date,
    source,
    declared_program,
    best_score,
    skill_text,
    skill_domains,
    domain_key,
    {job_domain_label_sql} AS domain_label
FROM classified;
'''.format(
    job_skill_domain_sql=build_sql_domain_case("concat_ws(' ', js.canonical_skill, js.skill_family, js.skill_category)"),
    job_domain_sql=build_sql_job_domain_case("concat_ws(' ', job_title, job_description, company, location, job_date, source, declared_program, skill_text, skill_domains)"),
    job_domain_label_sql=_sql_domain_label_case("domain_key", JOB_DOMAIN_LABELS),
)


JOB_SKILL_DOMAIN_TAXONOMY_SQL = '''
CREATE OR REPLACE VIEW public.vw_job_skill_domain_taxonomy AS
SELECT
    job_skill_id,
    job_id,
    job_title,
    skill_name,
    skill_domain,
    domain_key AS job_domain,
    {skill_domain_label_sql} AS skill_domain_label,
    {job_domain_label_sql} AS job_domain_label
FROM (
    SELECT
        ROW_NUMBER() OVER (ORDER BY js.job_id, js.id)::bigint AS job_skill_id,
        js.job_id AS job_id,
        j.title AS job_title,
        COALESCE(js.canonical_skill, js.skill_family, js.skill_category, '') AS skill_name,
        {skill_domain_sql} AS skill_domain,
        {job_domain_sql} AS domain_key
    FROM public.job_skills js
    LEFT JOIN public.jobs j
        ON j.id = js.job_id
) classified;
'''.format(
    skill_domain_sql=build_sql_domain_case("concat_ws(' ', js.canonical_skill, js.skill_family, js.skill_category)"),
    job_domain_sql=build_sql_job_domain_case("concat_ws(' ', j.title, j.description, j.company, COALESCE(j.location, ''), COALESCE(j.source, ''), COALESCE(j.industry, ''), COALESCE(js.canonical_skill, js.skill_family, js.skill_category, ''))"),
    skill_domain_label_sql=_sql_domain_label_case("skill_domain"),
    job_domain_label_sql=_sql_domain_label_case("domain_key", JOB_DOMAIN_LABELS),
)


MATCH_MATERIALIZED_VIEW_SQL = '''
CREATE TABLE IF NOT EXISTS public.mv_match_empleo_especializacion AS
SELECT *
FROM (
WITH empleo_skills_distinct AS (
    SELECT DISTINCT
        js.job_id AS empleo_id,
        lower(unaccent(COALESCE(js.canonical_skill, js.skill_family, js.skill_category, ''))) AS skill_key,
        COALESCE(js.canonical_skill, js.skill_family, js.skill_category, '') AS skill
    FROM public.job_skills js
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
        j.id AS empleo_id,
        j.title AS titulo_empleo,
        COALESCE(jd.job_domain, {job_domain_sql}) AS job_domain,
        COALESCE(jd.job_domain_label, '') AS job_domain_label,
        s.program_id AS especializacion_id,
        s.program_name AS nombre_especializacion,
        COALESCE(pd.program_domain, {program_domain_sql}) AS program_domain,
        COALESCE(pd.program_domain_label, '') AS program_domain_label,
        COALESCE(te.total_skills_empleo, 0) AS total_skills_empleo,
        COALESCE(ts.total_skills_especializacion, 0) AS total_skills_especializacion,
        COALESCE(sec.skills_en_comun, 0) AS skills_en_comun
    FROM public.jobs j
    CROSS JOIN program_domains s
    LEFT JOIN total_skills_empleo te
        ON te.empleo_id = j.id
    LEFT JOIN total_skills_especializacion ts
        ON ts.especializacion_id = s.program_id
    LEFT JOIN skills_en_comun sec
        ON sec.empleo_id = j.id
       AND sec.especializacion_id = s.program_id
    LEFT JOIN program_domains pd
        ON pd.program_id = s.program_id
    LEFT JOIN job_domains jd
        ON jd.job_id = j.id
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
),
weighted_matches AS (
    SELECT
        scored.*,
        ROUND((scored.jaccard_score + scored.cosine_score) / 2, 2) AS base_match_score,
        {domain_weight_sql} AS domain_score,
        {domain_weight_sql} AS domain_weight,
        ROUND((scored.jaccard_score + scored.cosine_score) / 2, 2) AS base_similarity_score,
        ROUND(
            (
                (ROUND((scored.jaccard_score + scored.cosine_score) / 2, 2) * 0.50)
                + (scored.coverage_score * 0.30)
                + ({domain_weight_sql} * 20)
            ),
            2
        ) AS adjusted_match_score,
        CASE
            WHEN {domain_weight_sql} = 0.1
                 AND COALESCE(scored.skills_en_comun, 0) < 3
            THEN FALSE
            WHEN {domain_weight_sql} = 1.0
                 AND COALESCE(scored.skills_en_comun, 0) >= 1
            THEN TRUE
            WHEN {domain_weight_sql} >= 0.5
                 AND COALESCE(scored.skills_en_comun, 0) >= 2
            THEN TRUE
            ELSE FALSE
        END AS passes_skill_threshold
    FROM scored_matches scored
)
SELECT
    weighted.empleo_id,
    weighted.especializacion_id,
    weighted.program_domain,
    weighted.job_domain,
    weighted.domain_score,
    weighted.domain_weight,
    weighted.jaccard_score,
    weighted.cosine_score,
    weighted.coverage_score,
    weighted.total_skills_empleo,
    weighted.total_skills_especializacion,
    weighted.skills_en_comun,
    weighted.passes_skill_threshold
   FROM weighted_matches weighted
) AS materialized_match
WHERE FALSE;
'''.format(
    job_domain_sql=build_sql_job_domain_case("concat_ws(' ', j.title, j.description, j.company, COALESCE(j.location, ''), COALESCE(j.source, ''), COALESCE(j.industry, ''))"),
    program_domain_sql=build_sql_domain_case("concat_ws(' ', s.program_name)"),
    domain_weight_sql=build_sql_domain_weight_case("scored.program_domain", "scored.job_domain"),
)

MATCH_MATERIALIZED_INDEX_SQLS = (
    'CREATE UNIQUE INDEX IF NOT EXISTS ux_mv_match_empleo_especializacion ON public.mv_match_empleo_especializacion (empleo_id, especializacion_id)',
    'CREATE INDEX IF NOT EXISTS ix_mv_match_empleo_especializacion_empleo_id ON public.mv_match_empleo_especializacion (empleo_id)',
    'CREATE INDEX IF NOT EXISTS ix_mv_match_empleo_especializacion_especializacion_id ON public.mv_match_empleo_especializacion (especializacion_id)',
    'CREATE INDEX IF NOT EXISTS ix_mv_match_empleo_especializacion_program_domain ON public.mv_match_empleo_especializacion (program_domain)',
    'CREATE INDEX IF NOT EXISTS ix_mv_match_empleo_especializacion_job_domain ON public.mv_match_empleo_especializacion (job_domain)',
    'CREATE INDEX IF NOT EXISTS ix_mv_match_empleo_especializacion_domain_score ON public.mv_match_empleo_especializacion (domain_score)',
    'CREATE INDEX IF NOT EXISTS ix_mv_match_empleo_especializacion_passes_skill_threshold ON public.mv_match_empleo_especializacion (passes_skill_threshold)',
)

MATCH_VIEW_SQL = '''
CREATE OR REPLACE VIEW public.vw_match_empleo_especializacion AS
SELECT
    m.empleo_id,
    m.especializacion_id,
    m.program_domain,
    COALESCE(pd.domain_label, '') AS program_domain_label,
    m.job_domain,
    COALESCE(jd.domain_label, '') AS job_domain_label,
    j.title AS titulo_empleo,
    COALESCE(pd.program_name, '') AS nombre_especializacion,
    m.domain_score,
    m.domain_weight,
    ROUND((m.jaccard_score + m.cosine_score) / 2, 2) AS base_match_score,
    ROUND((m.jaccard_score + m.cosine_score) / 2, 2) AS base_similarity_score,
    m.coverage_score,
    ROUND(100 - m.coverage_score, 2) AS gap_score,
    ROUND(
        (
            (ROUND((m.jaccard_score + m.cosine_score) / 2, 2) * 0.50)
            + (m.coverage_score * 0.30)
            + (m.domain_weight * 20)
        ),
        2
    ) AS match_score,
    ROUND(
        (
            (ROUND((m.jaccard_score + m.cosine_score) / 2, 2) * 0.50)
            + (m.coverage_score * 0.30)
            + (m.domain_weight * 20)
        ),
        2
    ) AS porcentaje_match,
    m.total_skills_empleo,
    m.total_skills_especializacion,
    m.skills_en_comun,
    m.skills_en_comun AS total_skills_comunes,
    m.passes_skill_threshold,
    m.jaccard_score,
    m.cosine_score
FROM public.mv_match_empleo_especializacion m
LEFT JOIN public.jobs j
    ON j.id = m.empleo_id
LEFT JOIN public.vw_program_domain_taxonomy pd
    ON pd.program_id = m.especializacion_id
LEFT JOIN public.vw_job_domain_taxonomy jd
    ON jd.job_id = m.empleo_id;
'''

MATCH_POSITIVE_SQL = '''
CREATE OR REPLACE VIEW vw_match_empleo_especializacion_positivo AS
SELECT *
FROM public.vw_match_empleo_especializacion
WHERE passes_skill_threshold = TRUE;
'''

DASHBOARD_VIEW_SQL = '''
CREATE OR REPLACE VIEW vw_dashboard_especializacion AS
WITH program_domains AS (
    SELECT
        program_id,
        program_name,
        domain_key AS program_domain,
        domain_label AS program_domain_label
    FROM public.vw_program_domain_taxonomy
),
programa_skills AS (
    SELECT
        especializacion_id,
        COUNT(DISTINCT skill_id) AS total_skills_programa
    FROM especializacion_skills
    GROUP BY especializacion_id
),
programa_herramientas AS (
    SELECT
        especializacion_id,
        COUNT(DISTINCT herramienta_id) AS total_herramientas
    FROM especializacion_herramientas
    GROUP BY especializacion_id
),
programa_competencias AS (
    SELECT
        especializacion_id,
        COUNT(DISTINCT competencia_id) AS total_competencias
    FROM especializacion_competencias
    GROUP BY especializacion_id
),
programa_habilidades_blandas AS (
    SELECT
        especializacion_id,
        COUNT(DISTINCT habilidad_id) AS total_habilidades_blandas
    FROM especializacion_habilidades_blandas
    GROUP BY especializacion_id
),
match_summary AS (
    SELECT
        especializacion_id,
        ROUND(AVG(porcentaje_match), 2) AS promedio_match_mercado,
        ROUND(MAX(porcentaje_match), 2) AS max_match_mercado,
        COUNT(DISTINCT empleo_id) AS total_empleos_relacionados
    FROM vw_match_empleo_especializacion_positivo
    GROUP BY especializacion_id
)
SELECT
    pd.program_id AS especializacion_id,
    pd.program_name AS nombre_especializacion,
    COALESCE(ps.total_skills_programa, 0) AS total_skills_programa,
    COALESCE(ph.total_herramientas, 0) AS total_herramientas,
    COALESCE(pc.total_competencias, 0) AS total_competencias,
    COALESCE(pbl.total_habilidades_blandas, 0) AS total_habilidades_blandas,
    COALESCE(ms.promedio_match_mercado, 0) AS promedio_match_mercado,
    COALESCE(ms.max_match_mercado, 0) AS max_match_mercado,
    COALESCE(ms.total_empleos_relacionados, 0) AS total_empleos_relacionados
FROM program_domains pd
LEFT JOIN programa_skills ps
    ON ps.especializacion_id = pd.program_id
LEFT JOIN programa_herramientas ph
    ON ph.especializacion_id = pd.program_id
LEFT JOIN programa_competencias pc
    ON pc.especializacion_id = pd.program_id
LEFT JOIN programa_habilidades_blandas pbl
    ON pbl.especializacion_id = pd.program_id
LEFT JOIN match_summary ms
    ON ms.especializacion_id = pd.program_id;
'''

DASHBOARD_MV_SQL = '''
DROP MATERIALIZED VIEW IF EXISTS mv_dashboard_especializacion;
CREATE MATERIALIZED VIEW mv_dashboard_especializacion AS
SELECT *
FROM vw_dashboard_especializacion;
'''

INDEX_SQL = '''
CREATE UNIQUE INDEX IF NOT EXISTS ux_mv_dashboard_especializacion
ON mv_dashboard_especializacion (especializacion_id);
'''

_PROGRAM_MARKET_OBJECTS_READY = False

PROGRAMA_SKILLS_SQL = '''
CREATE OR REPLACE VIEW public.vw_programa_skills AS
WITH program_base AS (
    SELECT *
    FROM (
        SELECT
            base.*,
            ROW_NUMBER() OVER (
                PARTITION BY base.normalized_program_name
                ORDER BY
                    base.source_priority,
                    base.total_skills_programa DESC,
                    base.role_priority,
                    base.casing_priority,
                    base.program_id DESC
            ) AS program_rank
        FROM ({program_base_sql}) base
    ) ranked
    WHERE ranked.program_rank = 1
),
unified_rows AS (
    SELECT
        pb.program_id AS especializacion_id,
        pb.program_name AS especializacion,
        COALESCE((SELECT pdm.domain_key FROM public.program_domain_mapping pdm WHERE pdm.program_id = pb.program_id LIMIT 1), {program_domain_sql}) AS program_domain,
        ROW_NUMBER() OVER (
            PARTITION BY pb.program_id
            ORDER BY lower(unaccent(COALESCE(s.nombre, ''))), s.id
        ) AS skill_id,
        s.nombre AS skill,
        s.nombre AS nombre,
        'skill' AS categoria,
        'skill' AS source_kind,
        'especializacion_skills' AS source_table,
        {skill_domain_sql_skill} AS skill_domain,
        lower(unaccent(COALESCE(s.nombre, ''))) AS skill_key
    FROM program_base pb
    INNER JOIN public.especializacion_skills es
        ON es.especializacion_id = pb.program_id
    INNER JOIN public.skills s
        ON s.id = es.skill_id
    UNION ALL
    SELECT
        pb.program_id AS especializacion_id,
        pb.program_name AS especializacion,
        COALESCE((SELECT pdm.domain_key FROM public.program_domain_mapping pdm WHERE pdm.program_id = pb.program_id LIMIT 1), {program_domain_sql}) AS program_domain,
        ROW_NUMBER() OVER (
            PARTITION BY pb.program_id
            ORDER BY lower(unaccent(COALESCE(c.nombre, ''))), c.id
        ) AS skill_id,
        c.nombre AS skill,
        c.nombre AS nombre,
        'competencia' AS categoria,
        'competency' AS source_kind,
        'especializacion_competencias' AS source_table,
        {skill_domain_sql_competency} AS skill_domain,
        lower(unaccent(COALESCE(c.nombre, ''))) AS skill_key
    FROM program_base pb
    INNER JOIN public.especializacion_competencias ec
        ON ec.especializacion_id = pb.program_id
    INNER JOIN public.competencias c
        ON c.id = ec.competencia_id
    UNION ALL
    SELECT
        pb.program_id AS especializacion_id,
        pb.program_name AS especializacion,
        COALESCE((SELECT pdm.domain_key FROM public.program_domain_mapping pdm WHERE pdm.program_id = pb.program_id LIMIT 1), {program_domain_sql}) AS program_domain,
        ROW_NUMBER() OVER (
            PARTITION BY pb.program_id
            ORDER BY lower(unaccent(COALESCE(h.nombre, ''))), h.id
        ) AS skill_id,
        h.nombre AS skill,
        h.nombre AS nombre,
        'herramienta' AS categoria,
        'tool' AS source_kind,
        'especializacion_herramientas' AS source_table,
        {skill_domain_sql_tool} AS skill_domain,
        lower(unaccent(COALESCE(h.nombre, ''))) AS skill_key
    FROM program_base pb
    INNER JOIN public.especializacion_herramientas eh
        ON eh.especializacion_id = pb.program_id
    INNER JOIN public.herramientas h
        ON h.id = eh.herramienta_id
    UNION ALL
    SELECT
        pb.program_id AS especializacion_id,
        pb.program_name AS especializacion,
        COALESCE((SELECT pdm.domain_key FROM public.program_domain_mapping pdm WHERE pdm.program_id = pb.program_id LIMIT 1), {program_domain_sql}) AS program_domain,
        ROW_NUMBER() OVER (
            PARTITION BY pb.program_id
            ORDER BY lower(unaccent(COALESCE(hb.nombre, ''))), hb.id
        ) AS skill_id,
        hb.nombre AS skill,
        hb.nombre AS nombre,
        'habilidad_blanda' AS categoria,
        'soft_skill' AS source_kind,
        'especializacion_habilidades_blandas' AS source_table,
        {skill_domain_sql_soft} AS skill_domain,
        lower(unaccent(COALESCE(hb.nombre, ''))) AS skill_key
    FROM program_base pb
    INNER JOIN public.especializacion_habilidades_blandas ehb
        ON ehb.especializacion_id = pb.program_id
    INNER JOIN public.habilidades_blandas hb
        ON hb.id = ehb.habilidad_id
)
SELECT DISTINCT ON (especializacion_id, skill_key)
    especializacion_id,
    especializacion,
    program_domain,
    skill_id,
    skill,
    nombre,
    categoria,
    source_kind,
    source_table,
    skill_domain,
    skill_key
FROM unified_rows
WHERE skill_key <> ''
ORDER BY especializacion_id, skill_key, source_kind, skill_id;
'''.format(
    program_base_sql=PROGRAM_BASE_SQL,
    program_domain_sql=build_sql_domain_case("concat_ws(' ', pb.program_name, COALESCE(pb.program_description, ''))"),
    skill_domain_sql_skill=build_sql_domain_case("concat_ws(' ', s.nombre)"),
    skill_domain_sql_competency=build_sql_domain_case("concat_ws(' ', c.nombre)"),
    skill_domain_sql_tool=build_sql_domain_case("concat_ws(' ', h.nombre, 'herramienta')"),
    skill_domain_sql_soft=build_sql_domain_case("concat_ws(' ', hb.nombre, 'habilidad blanda')"),
)

PROGRAM_RECOMMENDED_JOBS_SQL = '''
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
FROM public.vw_match_empleo_especializacion
WHERE passes_skill_threshold = TRUE;
'''

PROGRAM_SKILL_GAPS_SQL = '''
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
        COALESCE(js.canonical_skill, js.skill_family, js.skill_category, '') AS skill,
        COUNT(DISTINCT m.empleo_id)::int AS gap_frequency
    FROM public.vw_match_empleo_especializacion_positivo m
    INNER JOIN program_domains pd
        ON pd.program_id = m.especializacion_id
    INNER JOIN public.job_skills js
        ON js.job_id = m.empleo_id
    LEFT JOIN program_skill_keys psk
        ON psk.especializacion_id = m.especializacion_id
       AND psk.skill_key = lower(unaccent(COALESCE(js.canonical_skill, js.skill_family, js.skill_category, '')))
    WHERE psk.skill_key IS NULL
      AND COALESCE(m.program_domain, '') <> ''
      AND COALESCE(m.job_domain, '') <> ''
      AND m.program_domain = m.job_domain
    GROUP BY m.especializacion_id, COALESCE(js.canonical_skill, js.skill_family, js.skill_category, '')
)
SELECT
    msh.program_id,
    pd.program_domain,
    pd.program_domain_label,
    skill,
    gap_frequency
FROM market_skill_hits msh
LEFT JOIN program_domains pd
    ON pd.program_id = msh.program_id;
'''

PROGRAM_PROGRAM_SIMILARITY_SQL = '''
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
'''

PROGRAM_PROGRAM_SIMILARITY_SQL = '''
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
program_domains AS (
    SELECT
        program_id,
        program_name,
        domain_key AS program_domain,
        domain_label AS program_domain_label
    FROM public.vw_program_domain_taxonomy
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
),
scored_pairs AS (
    SELECT
        p1.program_id AS program_id,
        p1.program_name AS program_name,
        pd1.program_domain,
        pd1.program_domain_label,
        p2.program_id AS peer_program_id,
        p2.program_name AS peer_program_name,
        pd2.program_domain AS peer_program_domain,
        pd2.program_domain_label AS peer_program_domain_label,
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
        ROUND((
            CASE
                WHEN COALESCE(pc1.total_skills_programa, 0) + COALESCE(pc2.total_skills_programa, 0) - COALESCE(ss.shared_skills, 0) = 0 THEN 0
                ELSE (COALESCE(ss.shared_skills, 0)::numeric / NULLIF((COALESCE(pc1.total_skills_programa, 0) + COALESCE(pc2.total_skills_programa, 0) - COALESCE(ss.shared_skills, 0)), 0)) * 100
            END
            + CASE
                WHEN COALESCE(pc1.total_skills_programa, 0) = 0 OR COALESCE(pc2.total_skills_programa, 0) = 0 THEN 0
                ELSE (COALESCE(ss.shared_skills, 0)::numeric / NULLIF(SQRT((COALESCE(pc1.total_skills_programa, 0)::numeric) * (COALESCE(pc2.total_skills_programa, 0)::numeric)), 0)) * 100
            END
        ) / 2, 2) AS base_similarity_score,
        {domain_weight_sql} AS domain_weight
    FROM program_domains p1
    INNER JOIN program_domains p2
        ON p1.program_id <> p2.program_id
    LEFT JOIN shared_skills ss
        ON ss.program_id = p1.program_id
       AND ss.peer_program_id = p2.program_id
    LEFT JOIN program_skill_counts pc1
        ON pc1.especializacion_id = p1.program_id
    LEFT JOIN program_skill_counts pc2
        ON pc2.especializacion_id = p2.program_id
    LEFT JOIN program_domains pd1
        ON pd1.program_id = p1.program_id
    LEFT JOIN program_domains pd2
        ON pd2.program_id = p2.program_id
)
SELECT
    scored_pairs.*,
    ROUND(100 - scored_pairs.coverage_score, 2) AS gap_score,
    scored_pairs.base_similarity_score AS similarity_score,
    ROUND(scored_pairs.base_similarity_score * scored_pairs.domain_weight, 2) AS adjusted_similarity_score
FROM scored_pairs;
'''.format(
    domain_weight_sql=build_sql_domain_weight_case("COALESCE(pd1.program_domain, '')", "COALESCE(pd2.program_domain, '')"),
)

PROGRAM_MARKET_ALIGNMENT_SQL = '''
CREATE OR REPLACE VIEW public.vw_program_market_alignment AS
WITH program_domains AS (
    SELECT
        program_id,
        program_name,
        domain_key AS program_domain,
        domain_label AS program_domain_label
    FROM public.vw_program_domain_taxonomy
),
market_alignment AS (
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
    pd.program_id AS program_id,
    pd.program_name AS program_name,
    COALESCE(pd.program_domain, '') AS program_domain,
    COALESCE(pd.program_domain_label, '') AS program_domain_label,
    COALESCE(ma.market_alignment_score, 0) AS market_alignment_score,
    COALESCE(ma.coverage_score, 0) AS coverage_score,
    COALESCE(ma.gap_score, 0) AS gap_score,
    COALESCE(ma.matched_jobs, 0) AS matched_jobs,
    COALESCE(tms.missing_skills, '[]'::jsonb) AS missing_skills
FROM program_domains pd
LEFT JOIN market_alignment ma
    ON ma.program_id = pd.program_id
LEFT JOIN top_missing_skills tms
    ON tms.program_id = pd.program_id;
'''


def _fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with get_cursor() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def _fetch_one(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with get_cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def _fetch_name_list(sql: str, params: tuple[Any, ...] = ()) -> list[str]:
    return [row['nombre'] for row in _fetch_all(sql, params)]


def ensure_program_market_matching_objects() -> None:
    global _PROGRAM_MARKET_OBJECTS_READY
    if _PROGRAM_MARKET_OBJECTS_READY:
        return
    drop_statements: list[str] = [
        'DROP MATERIALIZED VIEW IF EXISTS public.mv_dashboard_especializacion CASCADE',
        'DROP TABLE IF EXISTS public.mv_match_empleo_especializacion CASCADE',
        'DROP VIEW IF EXISTS public.vw_program_market_alignment CASCADE',
        'DROP VIEW IF EXISTS public.vw_program_skill_gaps CASCADE',
        'DROP VIEW IF EXISTS public.vw_program_recommended_jobs CASCADE',
        'DROP VIEW IF EXISTS public.vw_program_program_similarity CASCADE',
        'DROP VIEW IF EXISTS public.vw_match_empleo_especializacion_positivo CASCADE',
        'DROP VIEW IF EXISTS public.vw_match_empleo_especializacion CASCADE',
        'DROP VIEW IF EXISTS public.vw_job_skill_domain_taxonomy CASCADE',
        'DROP VIEW IF EXISTS public.vw_job_domain_taxonomy CASCADE',
        'DROP VIEW IF EXISTS public.vw_program_domain_taxonomy CASCADE',
        'DROP VIEW IF EXISTS public.vw_skill_alias_domain_taxonomy CASCADE',
        'DROP VIEW IF EXISTS public.vw_skill_domain_taxonomy CASCADE',
        'DROP VIEW IF EXISTS public.vw_programa_skills CASCADE',
    ]
    statements: list[str] = [
        PROGRAM_DOMAIN_MAPPING_SQL,
        PROGRAMA_SKILLS_SQL,
        SKILL_DOMAIN_TAXONOMY_SQL,
        SKILL_ALIAS_DOMAIN_TAXONOMY_SQL,
        PROGRAM_DOMAIN_TAXONOMY_SQL,
        JOB_DOMAIN_TAXONOMY_SQL,
        JOB_SKILL_DOMAIN_TAXONOMY_SQL,
        MATCH_MATERIALIZED_VIEW_SQL,
        MATCH_VIEW_SQL,
        MATCH_POSITIVE_SQL,
        PROGRAM_RECOMMENDED_JOBS_SQL,
        PROGRAM_SKILL_GAPS_SQL,
        PROGRAM_MARKET_ALIGNMENT_SQL,
        PROGRAM_PROGRAM_SIMILARITY_SQL,
    ]

    conn = get_conn()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
            for statement in drop_statements:
                cur.execute(statement)
            for statement in statements:
                cur.execute(statement)
        _PROGRAM_MARKET_OBJECTS_READY = True
    finally:
        conn.close()


def fetch_specialization_options() -> list[dict[str, Any]]:
    return _fetch_all(
        '''
        SELECT
            id AS especializacion_id,
            nombre AS nombre_especializacion
        FROM especializaciones
        ORDER BY nombre
        '''
    )


def _ensure_dashboard_objects() -> None:
    ensure_program_market_matching_objects()
    checks = _fetch_one(
        'SELECT to_regclass(%s) IS NOT NULL AS mv_exists, to_regclass(%s) IS NOT NULL AS vw_exists, to_regclass(%s) IS NOT NULL AS match_exists',
        ('public.mv_dashboard_especializacion', 'public.vw_dashboard_especializacion', 'public.vw_match_empleo_especializacion'),
    ) or {}

    statements: list[str] = []
    if not checks.get('match_exists'):
        statements.extend([MATCH_VIEW_SQL, MATCH_POSITIVE_SQL])
    if not checks.get('vw_exists'):
        statements.append(DASHBOARD_VIEW_SQL)
    if not checks.get('mv_exists'):
        statements.extend([DASHBOARD_MV_SQL, INDEX_SQL])

    if not statements:
        return

    conn = get_conn()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)
    finally:
        conn.close()


def _dashboard_relation() -> str:
    _ensure_dashboard_objects()
    row = _fetch_one('SELECT to_regclass(%s) IS NOT NULL AS exists', ('public.mv_dashboard_especializacion',))
    if row and row.get('exists'):
        return 'mv_dashboard_especializacion'
    return 'vw_dashboard_especializacion'


def fetch_dashboard_summary() -> list[dict[str, Any]]:
    relation = _dashboard_relation()
    sql = f'''
        SELECT
            especializacion_id,
            nombre_especializacion,
            total_skills_programa,
            total_herramientas,
            total_competencias,
            total_habilidades_blandas,
            promedio_match_mercado,
            max_match_mercado,
            total_empleos_relacionados
        FROM {relation}
        ORDER BY promedio_match_mercado DESC, total_empleos_relacionados DESC, especializacion_id
    '''
    return _fetch_all(sql)


def fetch_global_kpis() -> dict[str, Any]:
    relation = _dashboard_relation()
    sql = f'''
        SELECT
            COUNT(*)::int AS total_programas,
            COALESCE(ROUND(AVG(promedio_match_mercado)::numeric, 2), 0) AS promedio_global_match,
            COALESCE(ROUND(MAX(max_match_mercado)::numeric, 2), 0) AS mejor_match_global,
            COALESCE((
                SELECT COUNT(DISTINCT empleo_id)
                FROM vw_match_empleo_especializacion_positivo
            ), 0)::int AS total_empleos_relacionados,
            COALESCE((
                SELECT COUNT(*)
                FROM vw_match_empleo_especializacion_positivo
            ), 0)::int AS total_relaciones_empleo_programa,
            COALESCE((
                SELECT COUNT(DISTINCT skill_id)
                FROM especializacion_skills
            ), 0)::int AS total_skills_programa_distintas,
            COALESCE((
                SELECT COUNT(DISTINCT skill_id)
                FROM empleo_skills
            ), 0)::int AS total_skills_mercado_distintas
        FROM {relation}
    '''
    row = _fetch_one(sql)
    return row or {
        'total_programas': 0,
        'promedio_global_match': 0,
        'mejor_match_global': 0,
        'total_empleos_relacionados': 0,
        'total_relaciones_empleo_programa': 0,
        'total_skills_programa_distintas': 0,
        'total_skills_mercado_distintas': 0,
    }


def fetch_program_dashboard(especializacion_id: int) -> dict[str, Any] | None:
    relation = _dashboard_relation()
    sql = f'''
        SELECT
            especializacion_id,
            nombre_especializacion,
            total_skills_programa,
            total_herramientas,
            total_competencias,
            total_habilidades_blandas,
            promedio_match_mercado,
            max_match_mercado,
            total_empleos_relacionados
        FROM {relation}
        WHERE especializacion_id = %s
    '''
    return _fetch_one(sql, (especializacion_id,))


def fetch_top_jobs_for_program(especializacion_id: int, limit: int = 10) -> list[dict[str, Any]]:
    _ensure_dashboard_objects()
    sql = '''
        SELECT
            v.empleo_id,
            v.titulo_empleo,
            v.especializacion_id,
            v.nombre_especializacion,
            v.total_skills_empleo,
            v.total_skills_especializacion,
            v.skills_en_comun,
            v.porcentaje_match,
            STRING_AGG(DISTINCT s.nombre, ', ' ORDER BY s.nombre) AS skills_comunes
        FROM vw_match_empleo_especializacion v
        INNER JOIN empleo_skills es
            ON es.empleo_id = v.empleo_id
        INNER JOIN especializacion_skills esp
            ON esp.especializacion_id = v.especializacion_id
           AND esp.skill_id = es.skill_id
        INNER JOIN skills s
            ON s.id = es.skill_id
        WHERE v.especializacion_id = %s
          AND v.skills_en_comun >= 2
        GROUP BY
            v.empleo_id,
            v.titulo_empleo,
            v.especializacion_id,
            v.nombre_especializacion,
            v.total_skills_empleo,
            v.total_skills_especializacion,
            v.skills_en_comun,
            v.porcentaje_match
        ORDER BY v.porcentaje_match DESC, v.skills_en_comun DESC, v.empleo_id
        LIMIT %s
    '''
    return _fetch_all(sql, (especializacion_id, limit))


def fetch_missing_skills_for_program(especializacion_id: int, limit: int = 20) -> list[dict[str, Any]]:
    sql = '''
        SELECT
            s.id AS skill_id,
            s.nombre AS nombre,
            COUNT(DISTINCT es.empleo_id)::int AS empleos_que_la_demandan
        FROM vw_match_empleo_especializacion_positivo v
        INNER JOIN empleo_skills es
            ON es.empleo_id = v.empleo_id
        INNER JOIN skills s
            ON s.id = es.skill_id
        WHERE v.especializacion_id = %s
          AND NOT EXISTS (
              SELECT 1
              FROM especializacion_skills esp
              WHERE esp.especializacion_id = %s
                AND esp.skill_id = es.skill_id
          )
        GROUP BY s.id, s.nombre
        HAVING COUNT(DISTINCT es.empleo_id) >= 2
        ORDER BY empleos_que_la_demandan DESC, s.nombre
        LIMIT %s
    '''
    return _fetch_all(sql, (especializacion_id, especializacion_id, limit))


def fetch_related_employment_skills_for_program(especializacion_id: int, limit: int = 20) -> list[dict[str, Any]]:
    sql = '''
        SELECT
            s.nombre AS nombre,
            COUNT(DISTINCT v.empleo_id)::int AS empleos_que_la_tienen
        FROM vw_match_empleo_especializacion_positivo v
        INNER JOIN empleo_skills es
            ON es.empleo_id = v.empleo_id
        INNER JOIN skills s
            ON s.id = es.skill_id
        WHERE v.especializacion_id = %s
        GROUP BY s.nombre
        ORDER BY empleos_que_la_tienen DESC, s.nombre
        LIMIT %s
    '''
    return _fetch_all(sql, (especializacion_id, limit))


def fetch_program_skills(especializacion_id: int) -> dict[str, list[str]]:
    return {
        'skills': _fetch_name_list(
            '''
            SELECT DISTINCT s.nombre AS nombre
            FROM especializacion_skills es
            INNER JOIN skills s ON s.id = es.skill_id
            WHERE es.especializacion_id = %s
            ORDER BY s.nombre
            ''',
            (especializacion_id,),
        ),
        'herramientas': _fetch_name_list(
            '''
            SELECT DISTINCT h.nombre AS nombre
            FROM especializacion_herramientas eh
            INNER JOIN herramientas h ON h.id = eh.herramienta_id
            WHERE eh.especializacion_id = %s
            ORDER BY h.nombre
            ''',
            (especializacion_id,),
        ),
        'competencias': _fetch_name_list(
            '''
            SELECT DISTINCT c.nombre AS nombre
            FROM especializacion_competencias ec
            INNER JOIN competencias c ON c.id = ec.competencia_id
            WHERE ec.especializacion_id = %s
            ORDER BY c.nombre
            ''',
            (especializacion_id,),
        ),
        'habilidades_blandas': _fetch_name_list(
            '''
            SELECT DISTINCT hb.nombre AS nombre
            FROM especializacion_habilidades_blandas ehb
            INNER JOIN habilidades_blandas hb ON hb.id = ehb.habilidad_id
            WHERE ehb.especializacion_id = %s
            ORDER BY hb.nombre
            ''',
            (especializacion_id,),
        ),
    }


def fetch_program_composition(especializacion_id: int) -> list[dict[str, Any]]:
    row = _fetch_one(
        '''
        SELECT
            COALESCE((
                SELECT COUNT(DISTINCT skill_id)
                FROM especializacion_skills
                WHERE especializacion_id = %s
            ), 0)::int AS skills,
            COALESCE((
                SELECT COUNT(DISTINCT herramienta_id)
                FROM especializacion_herramientas
                WHERE especializacion_id = %s
            ), 0)::int AS herramientas,
            COALESCE((
                SELECT COUNT(DISTINCT competencia_id)
                FROM especializacion_competencias
                WHERE especializacion_id = %s
            ), 0)::int AS competencias,
            COALESCE((
                SELECT COUNT(DISTINCT habilidad_id)
                FROM especializacion_habilidades_blandas
                WHERE especializacion_id = %s
            ), 0)::int AS habilidades_blandas
        ''',
        (especializacion_id, especializacion_id, especializacion_id, especializacion_id),
    ) or {}
    return [
        {'label': 'Skills', 'value': row.get('skills', 0)},
        {'label': 'Herramientas', 'value': row.get('herramientas', 0)},
        {'label': 'Competencias', 'value': row.get('competencias', 0)},
        {'label': 'Habilidades blandas', 'value': row.get('habilidades_blandas', 0)},
    ]



def fetch_program_market_skill_counts(especializacion_id: int) -> dict[str, Any]:
    row = _fetch_one(
        '''
        SELECT
            COALESCE((
                SELECT COUNT(DISTINCT esp.skill_id)
                FROM especializacion_skills esp
                WHERE esp.especializacion_id = %s
            ), 0)::int AS skills_programa,
            COALESCE((
                SELECT COUNT(DISTINCT es.skill_id)
                FROM vw_match_empleo_especializacion_positivo v
                INNER JOIN empleo_skills es
                    ON es.empleo_id = v.empleo_id
                WHERE v.especializacion_id = %s
            ), 0)::int AS skills_mercado
        ''',
        (especializacion_id, especializacion_id),
    )
    return row or {'skills_programa': 0, 'skills_mercado': 0}



def fetch_top_programs_by_match(limit: int = 10) -> list[dict[str, Any]]:
    relation = _dashboard_relation()
    sql = f'''
        SELECT
            especializacion_id,
            nombre_especializacion,
            promedio_match_mercado,
            max_match_mercado,
            total_empleos_relacionados
        FROM {relation}
        ORDER BY promedio_match_mercado DESC, total_empleos_relacionados DESC, nombre_especializacion
        LIMIT %s
    '''
    return _fetch_all(sql, (limit,))



def fetch_top_market_skills(limit: int = 10) -> list[dict[str, Any]]:
    return _fetch_all(
        '''
        SELECT
            s.nombre AS nombre,
            COUNT(DISTINCT es.empleo_id)::int AS conteo
        FROM empleo_skills es
        INNER JOIN skills s
            ON s.id = es.skill_id
        GROUP BY s.nombre
        ORDER BY conteo DESC, s.nombre
        LIMIT %s
        ''',
        (limit,),
    )



def fetch_top_missing_skills(especializacion_id: int, limit: int = 10) -> list[dict[str, Any]]:
    return fetch_missing_skills_for_program(especializacion_id, limit=limit)


def fetch_dashboard_analysis_terms(limit: int = 10) -> dict[str, list[dict[str, Any]]]:
    return {
        'skills_programa': _fetch_all(
            '''
            SELECT
                s.nombre AS nombre,
                COUNT(DISTINCT esp.especializacion_id)::int AS conteo
            FROM especializacion_skills esp
            INNER JOIN skills s
                ON s.id = esp.skill_id
            GROUP BY s.nombre
            ORDER BY conteo DESC, s.nombre
            LIMIT %s
            ''',
            (limit,),
        ),
        'skills_mercado': _fetch_all(
            '''
            SELECT
                s.nombre AS nombre,
                COUNT(DISTINCT es.empleo_id)::int AS conteo
            FROM empleo_skills es
            INNER JOIN skills s
                ON s.id = es.skill_id
            GROUP BY s.nombre
            ORDER BY conteo DESC, s.nombre
            LIMIT %s
            ''',
            (limit,),
        ),
        'herramientas': _fetch_all(
            '''
            SELECT
                h.nombre AS nombre,
                COUNT(DISTINCT eh.especializacion_id)::int AS conteo
            FROM especializacion_herramientas eh
            INNER JOIN herramientas h
                ON h.id = eh.herramienta_id
            GROUP BY h.nombre
            ORDER BY conteo DESC, h.nombre
            LIMIT %s
            ''',
            (limit,),
        ),
        'competencias': _fetch_all(
            '''
            SELECT
                c.nombre AS nombre,
                COUNT(DISTINCT ec.especializacion_id)::int AS conteo
            FROM especializacion_competencias ec
            INNER JOIN competencias c
                ON c.id = ec.competencia_id
            GROUP BY c.nombre
            ORDER BY conteo DESC, c.nombre
            LIMIT %s
            ''',
            (limit,),
        ),
        'habilidades_blandas': _fetch_all(
            '''
            SELECT
                hb.nombre AS nombre,
                COUNT(DISTINCT ehb.especializacion_id)::int AS conteo
            FROM especializacion_habilidades_blandas ehb
            INNER JOIN habilidades_blandas hb
                ON hb.id = ehb.habilidad_id
            GROUP BY hb.nombre
            ORDER BY conteo DESC, hb.nombre
            LIMIT %s
            ''',
            (limit,),
        ),
    }


def refresh_materialized_views() -> str:
    _ensure_dashboard_objects()
    refresh_match_views()
    relation = _dashboard_relation()
    if relation != 'mv_dashboard_especializacion':
        return 'view-only'

    statements = (
        'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dashboard_especializacion',
        'REFRESH MATERIALIZED VIEW mv_dashboard_especializacion',
    )
    last_error: Exception | None = None
    for statement in statements:
        conn = get_conn()
        try:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(statement)
            return statement
        except Exception as exc:
            last_error = exc
        finally:
            conn.close()
    if last_error is not None:
        raise last_error
    return statements[-1]


def _match_empleo_especializacion_body_sql(job_filter_sql: str = '') -> str:
    prefix = "\nCREATE TABLE IF NOT EXISTS public.mv_match_empleo_especializacion AS\nSELECT *\nFROM (\n"
    suffix = "\n) AS materialized_match\nWHERE FALSE;\n"
    sql = MATCH_MATERIALIZED_VIEW_SQL
    if not sql.startswith(prefix) or not sql.endswith(suffix):
        raise RuntimeError('unexpected match storage SQL wrapper')
    body = sql[len(prefix):-len(suffix)]
    if job_filter_sql:
        body = body.replace(
            "FROM public.jobs j\n    CROSS JOIN program_domains s",
            f"FROM (SELECT * FROM public.jobs {job_filter_sql}) j\n    CROSS JOIN program_domains s",
            1,
        )
    return body


def refresh_match_views() -> str:
    ensure_program_market_matching_objects()
    conn = get_conn()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM public.jobs ORDER BY id')
            job_ids = [row['id'] for row in cur.fetchall()]
            if not job_ids:
                cur.execute('DROP TABLE IF EXISTS public.mv_match_empleo_especializacion_new CASCADE')
                cur.execute('CREATE TABLE public.mv_match_empleo_especializacion_new (LIKE public.mv_match_empleo_especializacion INCLUDING ALL)')
                cur.execute('DROP TABLE IF EXISTS public.mv_match_empleo_especializacion CASCADE')
                cur.execute('ALTER TABLE public.mv_match_empleo_especializacion_new RENAME TO mv_match_empleo_especializacion')
                cur.execute(MATCH_VIEW_SQL)
                cur.execute(MATCH_POSITIVE_SQL)
                for statement in (
                    PROGRAM_RECOMMENDED_JOBS_SQL,
                    PROGRAM_SKILL_GAPS_SQL,
                    PROGRAM_MARKET_ALIGNMENT_SQL,
                    PROGRAM_PROGRAM_SIMILARITY_SQL,
                ):
                    cur.execute(statement)
                for statement in MATCH_MATERIALIZED_INDEX_SQLS:
                    cur.execute(statement)
                return 'rebuilt-empty'

            temp_tables: list[str] = []
            for job_idx, job_id in enumerate(job_ids, start=1):
                batch_sql = _match_empleo_especializacion_body_sql('')
                batch_sql = batch_sql.replace(
                    'FROM public.jobs j\n    CROSS JOIN program_domains s',
                    f"FROM (SELECT * FROM public.jobs WHERE id = '{job_id}') j\n    CROSS JOIN program_domains s",
                    1,
                )
                temp_table = f'tmp_match_empleo_especializacion_{job_idx}'
                cur.execute(f'DROP TABLE IF EXISTS {temp_table}')
                cur.execute(f'CREATE TEMP TABLE {temp_table} AS\n{batch_sql}')
                temp_tables.append(temp_table)

            cur.execute('DROP TABLE IF EXISTS public.mv_match_empleo_especializacion_new CASCADE')
            cur.execute(f'CREATE TABLE public.mv_match_empleo_especializacion_new (LIKE {temp_tables[0]} INCLUDING ALL)')
            for temp_table in temp_tables:
                cur.execute(f'INSERT INTO public.mv_match_empleo_especializacion_new SELECT * FROM {temp_table}')
            cur.execute('DROP TABLE IF EXISTS public.mv_match_empleo_especializacion CASCADE')
            cur.execute('ALTER TABLE public.mv_match_empleo_especializacion_new RENAME TO mv_match_empleo_especializacion')
            cur.execute(MATCH_VIEW_SQL)
            cur.execute(MATCH_POSITIVE_SQL)
            for statement in (
                PROGRAM_RECOMMENDED_JOBS_SQL,
                PROGRAM_SKILL_GAPS_SQL,
                PROGRAM_MARKET_ALIGNMENT_SQL,
                PROGRAM_PROGRAM_SIMILARITY_SQL,
            ):
                cur.execute(statement)
            for statement in MATCH_MATERIALIZED_INDEX_SQLS:
                cur.execute(statement)
            return f'rebuilt:{len(temp_tables)}'
    finally:
        conn.close()




