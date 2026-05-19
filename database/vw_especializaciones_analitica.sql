-- Canonical skill and title matching for PostgreSQL.
-- Full match remains skill-based; job titles are normalized too so you can diagnose
-- cases where the title suggests a relation that the skill pipeline misses.

CREATE OR REPLACE FUNCTION fn_normaliza_skill(p_text text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT regexp_replace(
        regexp_replace(
            lower(
                translate(
                    coalesce(p_text, ''),
                    'ÁÄÀÂÃáäàâãÉËÈÊéëèêÍÏÌÎíïìîÓÖÒÔÕóöòôõÚÜÙÛúüùûÑñÇç',
                    'AAAAAaaaaaEEEEeeeeIIIIiiiiOOOOOoooooUUUUuuuuNnCc'
                )
            ),
            '[^a-z0-9]+',
            ' ',
            'g'
        ),
        '\s+',
        ' ',
        'g'
    );
$$;

CREATE OR REPLACE FUNCTION fn_skill_canonica(p_text text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
    WITH n AS (
        SELECT fn_normaliza_skill(p_text) AS t
    )
    SELECT CASE
        WHEN t LIKE '%powerbi%'
          OR t LIKE '%power bi%'
          OR t LIKE '%ms power bi%'
          OR t LIKE '%microsoft power bi%'
        THEN 'power bi'

        WHEN t = 'bi'
          OR t LIKE '%business intelligence%'
          OR t LIKE '%inteligencia de negocios%'
          OR t LIKE '%analitica de negocio%'
          OR t LIKE '%business analytics%'
        THEN 'business intelligence'

        WHEN t LIKE '%visual analytics%'
          OR t LIKE '%visualizacion de datos%'
          OR t LIKE '%data visualization%'
          OR t LIKE '%tableau%'
          OR t LIKE '%looker studio%'
          OR t LIKE '%google data studio%'
        THEN 'visual analytics'

        WHEN t LIKE '%big data%'
          OR t LIKE '%analitica de datos a gran escala%'
        THEN 'big data'

        WHEN t LIKE '%analitica de datos%'
          OR t LIKE '%data analytics%'
          OR t LIKE '%data analysis%'
        THEN 'analitica de datos'

        ELSE t
    END
    FROM n;
$$;

CREATE OR REPLACE FUNCTION fn_normaliza_titulo_empleo(p_text text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT fn_normaliza_skill(p_text);
$$;

CREATE OR REPLACE FUNCTION fn_titulo_empleo_canonico(p_text text)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
    WITH n AS (
        SELECT fn_normaliza_titulo_empleo(p_text) AS t
    )
    SELECT CASE
        WHEN t LIKE '%powerbi%'
          OR t LIKE '%power bi%'
        THEN 'power bi'

        WHEN t = 'bi'
          OR t LIKE '%business intelligence%'
          OR t LIKE '%inteligencia de negocios%'
          OR t LIKE '%bi analyst%'
          OR t LIKE '%bi developer%'
          OR t LIKE '%analista bi%'
        THEN 'business intelligence'

        WHEN t LIKE '%visual analytics%'
          OR t LIKE '%visualizacion de datos%'
          OR t LIKE '%data visualization%'
          OR t LIKE '%tableau%'
          OR t LIKE '%visual data%'
        THEN 'visual analytics'

        WHEN t LIKE '%big data%'
        THEN 'big data'

        WHEN t LIKE '%data analyst%'
          OR t LIKE '%analista de datos%'
          OR t LIKE '%data analytics%'
          OR t LIKE '%analitica de datos%'
        THEN 'analitica de datos'

        ELSE t
    END
    FROM n;
$$;

CREATE OR REPLACE VIEW vw_skills_normalizadas AS
SELECT
    s.id AS skill_id,
    s.nombre AS skill_nombre,
    fn_normaliza_skill(s.nombre) AS skill_normalizada,
    fn_skill_canonica(s.nombre) AS skill_canonica,
    (fn_normaliza_skill(s.nombre) <> fn_skill_canonica(s.nombre)) AS es_alias
FROM skills s;

CREATE OR REPLACE VIEW vw_empleos_normalizados AS
SELECT
    e.id AS empleo_id,
    e.titulo AS titulo_empleo,
    fn_normaliza_titulo_empleo(e.titulo) AS titulo_normalizado,
    fn_titulo_empleo_canonico(e.titulo) AS titulo_canonico
FROM empleos e;

-- Full matching view: all empleo x especializacion pairs.
-- Matching is based on canonical skill concepts, not just exact skill_id.
CREATE OR REPLACE VIEW vw_match_empleo_especializacion AS
WITH empleo_skills_canonicas AS (
    SELECT DISTINCT
        es.empleo_id,
        sn.skill_canonica
    FROM empleo_skills es
    INNER JOIN vw_skills_normalizadas sn
        ON sn.skill_id = es.skill_id
),
especializacion_skills_canonicas AS (
    SELECT DISTINCT
        esp.especializacion_id,
        sn.skill_canonica
    FROM especializacion_skills esp
    INNER JOIN vw_skills_normalizadas sn
        ON sn.skill_id = esp.skill_id
),
total_skills_empleo AS (
    SELECT
        empleo_id,
        COUNT(*) AS total_skills_empleo
    FROM empleo_skills_canonicas
    GROUP BY empleo_id
),
total_skills_especializacion AS (
    SELECT
        especializacion_id,
        COUNT(*) AS total_skills_especializacion
    FROM especializacion_skills_canonicas
    GROUP BY especializacion_id
),
skills_en_comun AS (
    SELECT
        e.empleo_id,
        p.especializacion_id,
        COUNT(*) AS skills_en_comun
    FROM empleo_skills_canonicas e
    INNER JOIN especializacion_skills_canonicas p
        ON p.skill_canonica = e.skill_canonica
    GROUP BY
        e.empleo_id,
        p.especializacion_id
)
SELECT
    e.id AS empleo_id,
    e.titulo AS titulo_empleo,
    en.titulo_normalizado,
    en.titulo_canonico,
    s.id AS especializacion_id,
    s.nombre AS nombre_especializacion,
    COALESCE(te.total_skills_empleo, 0) AS total_skills_empleo,
    COALESCE(ts.total_skills_especializacion, 0) AS total_skills_especializacion,
    COALESCE(sec.skills_en_comun, 0) AS skills_en_comun,
    ROUND(
        CASE
            WHEN COALESCE(te.total_skills_empleo, 0) = 0 THEN 0
            ELSE (COALESCE(sec.skills_en_comun, 0)::numeric / te.total_skills_empleo) * 100
        END,
        2
    ) AS porcentaje_match
FROM empleos e
INNER JOIN vw_empleos_normalizados en
    ON en.empleo_id = e.id
CROSS JOIN especializaciones s
LEFT JOIN total_skills_empleo te
    ON te.empleo_id = e.id
LEFT JOIN total_skills_especializacion ts
    ON ts.especializacion_id = s.id
LEFT JOIN skills_en_comun sec
    ON sec.empleo_id = e.id
   AND sec.especializacion_id = s.id;

CREATE OR REPLACE VIEW vw_match_empleo_especializacion_positivo AS
SELECT *
FROM vw_match_empleo_especializacion
WHERE skills_en_comun > 0;

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

DROP MATERIALIZED VIEW IF EXISTS mv_dashboard_especializacion;
CREATE MATERIALIZED VIEW mv_dashboard_especializacion AS
SELECT *
FROM vw_dashboard_especializacion;

CREATE UNIQUE INDEX IF NOT EXISTS ux_mv_dashboard_especializacion
ON mv_dashboard_especializacion (especializacion_id);

-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dashboard_especializacion;

-- =========================================================
-- Validation and diagnosis queries
-- =========================================================

-- 1) Exact skills for the target specialization.
WITH target_especializacion AS (
    SELECT id, nombre
    FROM especializaciones
    WHERE fn_normaliza_skill(nombre) = fn_normaliza_skill('Especializacion en Visual Analytics y Big Data')
    LIMIT 1
)
SELECT
    e.id AS especializacion_id,
    e.nombre AS nombre_especializacion,
    s.id AS skill_id,
    s.nombre AS skill_nombre,
    sn.skill_normalizada,
    sn.skill_canonica,
    sn.es_alias
FROM target_especializacion e
INNER JOIN especializacion_skills esp
    ON esp.especializacion_id = e.id
INNER JOIN skills s
    ON s.id = esp.skill_id
INNER JOIN vw_skills_normalizadas sn
    ON sn.skill_id = s.id
ORDER BY sn.skill_canonica, s.nombre;

-- 2) Top 10 related jobs for that specialization using a stronger canonical match.
WITH target_especializacion AS (
    SELECT id, nombre
    FROM especializaciones
    WHERE fn_normaliza_skill(nombre) = fn_normaliza_skill('Especializacion en Visual Analytics y Big Data')
    LIMIT 1
)
SELECT
    m.empleo_id,
    m.titulo_empleo,
    m.titulo_canonico,
    m.especializacion_id,
    m.nombre_especializacion,
    m.skills_en_comun,
    m.porcentaje_match
FROM vw_match_empleo_especializacion_positivo m
INNER JOIN target_especializacion e
    ON e.id = m.especializacion_id
WHERE m.skills_en_comun >= 2
ORDER BY m.porcentaje_match DESC, m.skills_en_comun DESC, m.empleo_id
LIMIT 10;

-- 3) Skills from the related jobs, with canonical form and alias flag.
WITH target_especializacion AS (
    SELECT id, nombre
    FROM especializaciones
    WHERE fn_normaliza_skill(nombre) = fn_normaliza_skill('Especializacion en Visual Analytics y Big Data')
    LIMIT 1
),
related_jobs AS (
    SELECT empleo_id, titulo_empleo, titulo_canonico, porcentaje_match, skills_en_comun
    FROM vw_match_empleo_especializacion_positivo
    WHERE especializacion_id = (SELECT id FROM target_especializacion)
      AND skills_en_comun >= 2
    ORDER BY porcentaje_match DESC, skills_en_comun DESC, empleo_id
    LIMIT 10
)
SELECT
    r.empleo_id,
    r.titulo_empleo,
    r.titulo_canonico,
    s.id AS skill_id,
    s.nombre AS skill_nombre,
    sn.skill_normalizada,
    sn.skill_canonica,
    sn.es_alias
FROM related_jobs r
INNER JOIN empleo_skills es
    ON es.empleo_id = r.empleo_id
INNER JOIN skills s
    ON s.id = es.skill_id
INNER JOIN vw_skills_normalizadas sn
    ON sn.skill_id = s.id
ORDER BY r.porcentaje_match DESC, r.empleo_id, sn.skill_canonica, s.nombre;

-- 4) Exact overlaps by raw skill_id.
WITH target_especializacion AS (
    SELECT id, nombre
    FROM especializaciones
    WHERE fn_normaliza_skill(nombre) = fn_normaliza_skill('Especializacion en Visual Analytics y Big Data')
    LIMIT 1
)
SELECT DISTINCT
    s.nombre AS skill_nombre_exacta
FROM target_especializacion e
INNER JOIN especializacion_skills esp
    ON esp.especializacion_id = e.id
INNER JOIN empleo_skills es
    ON es.skill_id = esp.skill_id
INNER JOIN skills s
    ON s.id = esp.skill_id
ORDER BY s.nombre;

-- 5) Canonical overlaps that were missed by exact skill_id matching.
WITH target_especializacion AS (
    SELECT id, nombre
    FROM especializaciones
    WHERE fn_normaliza_skill(nombre) = fn_normaliza_skill('Especializacion en Visual Analytics y Big Data')
    LIMIT 1
),
programa AS (
    SELECT DISTINCT
        sn.skill_canonica,
        s.nombre AS skill_programa,
        s.id AS skill_programa_id
    FROM especializacion_skills esp
    INNER JOIN target_especializacion e
        ON e.id = esp.especializacion_id
    INNER JOIN vw_skills_normalizadas sn
        ON sn.skill_id = esp.skill_id
    INNER JOIN skills s
        ON s.id = esp.skill_id
),
empleo AS (
    SELECT DISTINCT
        sn.skill_canonica,
        s.nombre AS skill_empleo,
        s.id AS skill_empleo_id,
        es.empleo_id
    FROM empleo_skills es
    INNER JOIN vw_skills_normalizadas sn
        ON sn.skill_id = es.skill_id
    INNER JOIN skills s
        ON s.id = es.skill_id
)
SELECT DISTINCT
    p.skill_canonica,
    p.skill_programa,
    p.skill_programa_id,
    e.skill_empleo,
    e.skill_empleo_id,
    e.empleo_id
FROM programa p
INNER JOIN empleo e
    ON e.skill_canonica = p.skill_canonica
WHERE p.skill_programa_id <> e.skill_empleo_id
ORDER BY p.skill_canonica, p.skill_programa, e.skill_empleo, e.empleo_id;

-- 6) Jobs whose titles suggest a relation even if skills are sparse.
WITH target_especializacion AS (
    SELECT id, nombre
    FROM especializaciones
    WHERE fn_normaliza_skill(nombre) = fn_normaliza_skill('Especializacion en Visual Analytics y Big Data')
    LIMIT 1
),
programa_conceptos AS (
    SELECT DISTINCT
        sn.skill_canonica
    FROM especializacion_skills esp
    INNER JOIN target_especializacion e
        ON e.id = esp.especializacion_id
    INNER JOIN vw_skills_normalizadas sn
        ON sn.skill_id = esp.skill_id
),
possible_title_matches AS (
    SELECT
        en.empleo_id,
        en.titulo_empleo,
        en.titulo_canonico
    FROM vw_empleos_normalizados en
    INNER JOIN programa_conceptos pc
        ON pc.skill_canonica = en.titulo_canonico
)
SELECT
    p.empleo_id,
    p.titulo_empleo,
    p.titulo_canonico
FROM possible_title_matches p
ORDER BY p.titulo_canonico, p.titulo_empleo, p.empleo_id;

-- 7) Why a specialization can show missing skills but zero strong related jobs.
WITH target_especializacion AS (
    SELECT id, nombre
    FROM especializaciones
    WHERE fn_normaliza_skill(nombre) = fn_normaliza_skill('Especializacion en Visual Analytics y Big Data')
    LIMIT 1
),
exact_related_jobs AS (
    SELECT COUNT(*) AS total
    FROM (
        SELECT es.empleo_id
        FROM empleo_skills es
        INNER JOIN especializacion_skills esp
            ON esp.skill_id = es.skill_id
        INNER JOIN target_especializacion e
            ON e.id = esp.especializacion_id
        GROUP BY es.empleo_id
        HAVING COUNT(DISTINCT esp.skill_id) >= 2
    ) exact_jobs
),
canonical_related_jobs AS (
    SELECT COUNT(*) AS total
    FROM (
        SELECT m.empleo_id
        FROM vw_match_empleo_especializacion_positivo m
        INNER JOIN target_especializacion e
            ON e.id = m.especializacion_id
        WHERE m.skills_en_comun >= 2
        GROUP BY m.empleo_id
    ) canonical_jobs
),
program_total_skills AS (
    SELECT COUNT(*) AS total
    FROM especializacion_skills esp
    INNER JOIN target_especializacion e
        ON e.id = esp.especializacion_id
),
possible_title_matches AS (
    SELECT COUNT(DISTINCT en.empleo_id) AS total
    FROM vw_empleos_normalizados en
    INNER JOIN (
        SELECT DISTINCT sn.skill_canonica
        FROM especializacion_skills esp
        INNER JOIN target_especializacion e
            ON e.id = esp.especializacion_id
        INNER JOIN vw_skills_normalizadas sn
            ON sn.skill_id = esp.skill_id
    ) pc
        ON pc.skill_canonica = en.titulo_canonico
)
SELECT
    e.id AS especializacion_id,
    e.nombre AS nombre_especializacion,
    pts.total AS total_skills_programa,
    erj.total AS empleos_relacionados_exactos,
    crj.total AS empleos_relacionados_canonicos,
    ptm.total AS empleos_relacionados_por_titulo,
    CASE
        WHEN erj.total = 0 AND crj.total > 0 THEN 'Exact join was too strict; canonical aliases recover matches'
        WHEN erj.total = 0 AND crj.total = 0 AND ptm.total > 0 THEN 'Skills are sparse, but title analysis shows likely related jobs'
        WHEN erj.total = 0 AND crj.total = 0 AND ptm.total = 0 THEN 'No market overlap found even after canonicalization and title analysis'
        ELSE 'Exact and canonical matching both find related jobs'
    END AS diagnostico
FROM target_especializacion e
CROSS JOIN program_total_skills pts
CROSS JOIN exact_related_jobs erj
CROSS JOIN canonical_related_jobs crj
CROSS JOIN possible_title_matches ptm;

-- 8) Top 10 specializations by market match.
SELECT
    especializacion_id,
    nombre_especializacion,
    total_skills_programa,
    total_empleos_relacionados,
    promedio_match_mercado,
    max_match_mercado
FROM vw_dashboard_especializacion
ORDER BY promedio_match_mercado DESC, total_empleos_relacionados DESC, especializacion_id
LIMIT 10;
