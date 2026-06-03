from __future__ import annotations

from typing import Any

from backend.db import get_conn, get_cursor


MATCH_VIEW_SQL = '''
CREATE OR REPLACE VIEW vw_match_empleo_especializacion AS
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
        s.id AS especializacion_id,
        s.nombre AS nombre_especializacion,
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
    ROUND((scored.jaccard_score + scored.cosine_score) / 2, 2) AS match_score,
    ROUND((scored.jaccard_score + scored.cosine_score) / 2, 2) AS porcentaje_match
FROM scored_matches scored;
'''

MATCH_POSITIVE_SQL = '''
CREATE OR REPLACE VIEW vw_match_empleo_especializacion_positivo AS
SELECT *
FROM vw_match_empleo_especializacion
WHERE skills_en_comun > 0;
'''

DASHBOARD_VIEW_SQL = '''
CREATE OR REPLACE VIEW vw_dashboard_especializacion AS
WITH programa_skills AS (
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
    s.id AS especializacion_id,
    s.nombre AS nombre_especializacion,
    COALESCE(ps.total_skills_programa, 0) AS total_skills_programa,
    COALESCE(ph.total_herramientas, 0) AS total_herramientas,
    COALESCE(pc.total_competencias, 0) AS total_competencias,
    COALESCE(pbl.total_habilidades_blandas, 0) AS total_habilidades_blandas,
    COALESCE(ms.promedio_match_mercado, 0) AS promedio_match_mercado,
    COALESCE(ms.max_match_mercado, 0) AS max_match_mercado,
    COALESCE(ms.total_empleos_relacionados, 0) AS total_empleos_relacionados
FROM especializaciones s
LEFT JOIN programa_skills ps
    ON ps.especializacion_id = s.id
LEFT JOIN programa_herramientas ph
    ON ph.especializacion_id = s.id
LEFT JOIN programa_competencias pc
    ON pc.especializacion_id = s.id
LEFT JOIN programa_habilidades_blandas pbl
    ON pbl.especializacion_id = s.id
LEFT JOIN match_summary ms
    ON ms.especializacion_id = s.id;
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
'''

PROGRAM_RECOMMENDED_JOBS_SQL = '''
CREATE OR REPLACE VIEW public.vw_program_recommended_jobs AS
SELECT
    especializacion_id AS program_id,
    empleo_id AS job_id,
    titulo_empleo AS job_title,
    porcentaje_match AS similarity_score,
    coverage_score,
    gap_score,
    match_score,
    total_skills_empleo,
    total_skills_especializacion,
    skills_en_comun
FROM public.vw_match_empleo_especializacion
WHERE skills_en_comun >= 1;
'''

PROGRAM_SKILL_GAPS_SQL = '''
CREATE OR REPLACE VIEW public.vw_program_skill_gaps AS
WITH program_skill_keys AS (
    SELECT DISTINCT
        especializacion_id,
        skill_key
    FROM public.vw_programa_skills
),
market_skill_hits AS (
    SELECT
        m.especializacion_id AS program_id,
        s.nombre AS skill,
        COUNT(DISTINCT m.empleo_id)::int AS gap_frequency
    FROM public.vw_match_empleo_especializacion_positivo m
    INNER JOIN public.empleo_skills es
        ON es.empleo_id = m.empleo_id
    INNER JOIN public.skills s
        ON s.id = es.skill_id
    LEFT JOIN program_skill_keys psk
        ON psk.especializacion_id = m.especializacion_id
       AND psk.skill_key = lower(unaccent(COALESCE(s.nombre, '')))
    WHERE psk.skill_key IS NULL
    GROUP BY m.especializacion_id, s.nombre
)
SELECT
    program_id,
    skill,
    gap_frequency
FROM market_skill_hits;
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

PROGRAM_MARKET_ALIGNMENT_SQL = '''
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
    checks = _fetch_one(
        '''
        SELECT
            to_regclass(%s) IS NOT NULL AS programa_skills_exists,
            to_regclass(%s) IS NOT NULL AS match_exists,
            to_regclass(%s) IS NOT NULL AS positive_match_exists,
            to_regclass(%s) IS NOT NULL AS recommended_jobs_exists,
            to_regclass(%s) IS NOT NULL AS gaps_exists,
            to_regclass(%s) IS NOT NULL AS alignment_exists,
            to_regclass(%s) IS NOT NULL AS program_similarity_exists
        ''',
        (
            'public.vw_programa_skills',
            'public.vw_match_empleo_especializacion',
            'public.vw_match_empleo_especializacion_positivo',
            'public.vw_program_recommended_jobs',
            'public.vw_program_skill_gaps',
            'public.vw_program_market_alignment',
            'public.vw_program_program_similarity',
        ),
    ) or {}

    statements: list[str] = []
    if not checks.get('programa_skills_exists'):
        statements.append(PROGRAMA_SKILLS_SQL)
    if not checks.get('match_exists'):
        statements.extend([MATCH_VIEW_SQL, MATCH_POSITIVE_SQL])
    if not checks.get('recommended_jobs_exists'):
        statements.append(PROGRAM_RECOMMENDED_JOBS_SQL)
    if not checks.get('gaps_exists'):
        statements.append(PROGRAM_SKILL_GAPS_SQL)
    if not checks.get('alignment_exists'):
        statements.append(PROGRAM_MARKET_ALIGNMENT_SQL)
    if not checks.get('program_similarity_exists'):
        statements.append(PROGRAM_PROGRAM_SIMILARITY_SQL)

    if not statements:
        _PROGRAM_MARKET_OBJECTS_READY = True
        return

    conn = get_conn()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
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




