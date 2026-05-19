from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

from db import get_conn


ROOT = Path(__file__).resolve().parent
JOBS_CSV = ROOT / 'job_extraction_output_real_final' / 'jobs.csv'
JOB_SKILLS_CSV = ROOT / 'job_extraction_output_real_final' / 'job_skills.csv'
MARKET_JOBS_CSV = ROOT / 'unir_market_jobs.csv'


ALIASES = {
    'machine learning': ['machine learning', 'ml', 'deep learning', 'predictive', 'model training'],
    'ciencia de datos': ['data science', 'data analysis', 'data analyst', 'data engineer', 'data engineering', 'data governance', 'product data engineer'],
    'big data': ['big data', 'etl', 'sql', 'analyst sql', 'data modeling', 'data model', 'business intelligence'],
    'visual analytics': ['visual analytics', 'power bi', 'dashboard', 'dashboarding', 'reporting', 'data storytelling', 'stakeholder reporting', 'bi analyst', 'bi analyst business intelligence', 'kpi design'],
    'programación': ['python', 'cloud', 'api', 'apis', 'testing', 'software', 'javascript', 'node', 'backend', 'devops', 'git', 'programming'],
    'ciberseguridad': ['cybersecurity', 'privacy', 'data protection', 'incident response', 'security'],
    'auditoría': ['compliance', 'due diligence', 'legal analysis', 'regulatory compliance', 'legal risk', 'aml', 'cft', 'sarlaft', 'corporate governance', 'corporate law', 'contract', 'contract drafting', 'public policy', 'risk lead', 'risk management'],
    'gestión de proyectos': ['agile', 'project management', 'leadership', 'planning', 'procurement', 'procurement manager', 'state contracting', 'negotiation', 'risk management', 'cronograma', 'alcance'],
    'gestión de la calidad': ['evaluation', 'curriculum', 'curriculum design', 'instructional design', 'lms', 'learning analytics', 'learning'],
    'sistema de gestión': ['management system', 'sistema de gestion', 'governance', 'govern'],
}


VIEW_SQL = '''
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
        '\\s+',
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
        WHEN t LIKE '%powerbi%' OR t LIKE '%power bi%' OR t LIKE '%ms power bi%' OR t LIKE '%microsoft power bi%'
        THEN 'power bi'
        WHEN t = 'bi' OR t LIKE '%business intelligence%' OR t LIKE '%inteligencia de negocios%' OR t LIKE '%analitica de negocio%' OR t LIKE '%business analytics%'
        THEN 'business intelligence'
        WHEN t LIKE '%visual analytics%' OR t LIKE '%visualizacion de datos%' OR t LIKE '%data visualization%' OR t LIKE '%tableau%' OR t LIKE '%looker studio%' OR t LIKE '%google data studio%'
        THEN 'visual analytics'
        WHEN t LIKE '%big data%' OR t LIKE '%analitica de datos a gran escala%'
        THEN 'big data'
        WHEN t LIKE '%analitica de datos%' OR t LIKE '%data analytics%' OR t LIKE '%data analysis%'
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
        WHEN t LIKE '%powerbi%' OR t LIKE '%power bi%' THEN 'power bi'
        WHEN t = 'bi' OR t LIKE '%business intelligence%' OR t LIKE '%inteligencia de negocios%' OR t LIKE '%bi analyst%' OR t LIKE '%bi developer%' OR t LIKE '%analista bi%'
        THEN 'business intelligence'
        WHEN t LIKE '%visual analytics%' OR t LIKE '%visualizacion de datos%' OR t LIKE '%data visualization%' OR t LIKE '%tableau%' OR t LIKE '%visual data%'
        THEN 'visual analytics'
        WHEN t LIKE '%big data%' THEN 'big data'
        WHEN t LIKE '%data analyst%' OR t LIKE '%analista de datos%' OR t LIKE '%data analytics%' OR t LIKE '%analitica de datos%'
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
    SELECT empleo_id, COUNT(*) AS total_skills_empleo
    FROM empleo_skills_canonicas
    GROUP BY empleo_id
),
total_skills_especializacion AS (
    SELECT especializacion_id, COUNT(*) AS total_skills_especializacion
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
    GROUP BY e.empleo_id, p.especializacion_id
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
    SELECT especializacion_id, COUNT(DISTINCT skill_id) AS total_skills_programa
    FROM especializacion_skills
    GROUP BY especializacion_id
),
programa_herramientas AS (
    SELECT especializacion_id, COUNT(DISTINCT herramienta_id) AS total_herramientas
    FROM especializacion_herramientas
    GROUP BY especializacion_id
),
programa_competencias AS (
    SELECT especializacion_id, COUNT(DISTINCT competencia_id) AS total_competencias
    FROM especializacion_competencias
    GROUP BY especializacion_id
),
programa_habilidades_blandas AS (
    SELECT especializacion_id, COUNT(DISTINCT habilidad_id) AS total_habilidades_blandas
    FROM especializacion_habilidades_blandas
    GROUP BY especializacion_id
),
match_stats AS (
    SELECT
        especializacion_id,
        ROUND(AVG(porcentaje_match)::numeric, 2) AS promedio_match_mercado,
        ROUND(MAX(porcentaje_match)::numeric, 2) AS max_match_mercado,
        COUNT(DISTINCT empleo_id)::int AS total_empleos_relacionados
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
LEFT JOIN programa_skills ps ON ps.especializacion_id = s.id
LEFT JOIN programa_herramientas ph ON ph.especializacion_id = s.id
LEFT JOIN programa_competencias pc ON pc.especializacion_id = s.id
LEFT JOIN programa_habilidades_blandas pbl ON pbl.especializacion_id = s.id
LEFT JOIN match_stats ms ON ms.especializacion_id = s.id;

DROP MATERIALIZED VIEW IF EXISTS mv_dashboard_especializacion CASCADE;
CREATE MATERIALIZED VIEW mv_dashboard_especializacion AS
SELECT *
FROM vw_dashboard_especializacion;

CREATE UNIQUE INDEX IF NOT EXISTS ux_mv_dashboard_especializacion
ON mv_dashboard_especializacion (especializacion_id);
'''


def normalize(value: str) -> str:
    text = unicodedata.normalize('NFKD', value or '')
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def split_tokens(value: str) -> list[str]:
    if not value:
        return []
    tokens = re.split(r'[;|,/\n]+', value)
    return [token.strip() for token in tokens if token and token.strip()]


def skill_id_for(name_map: dict[str, int], raw_skill: str) -> int | None:
    norm = normalize(raw_skill)
    if not norm:
        return None

    if norm in name_map:
        return name_map[norm]

    for canonical, patterns in ALIASES.items():
        canonical_norm = normalize(canonical)
        if canonical_norm in name_map and any(pattern in norm for pattern in patterns):
            return name_map[canonical_norm]

    return None


def program_id_for(program_map: dict[str, int], raw_program: str) -> int | None:
    norm = normalize(raw_program)
    return program_map.get(norm)


def load_csv(path: Path):
    with path.open('r', encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    missing = [str(path) for path in (JOBS_CSV, JOB_SKILLS_CSV, MARKET_JOBS_CSV) if not path.exists()]
    if missing:
        raise SystemExit(f'No se encontraron los CSV esperados: {", ".join(missing)}')

    conn = get_conn()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute('DROP MATERIALIZED VIEW IF EXISTS mv_dashboard_especializacion CASCADE')
            cur.execute('DROP VIEW IF EXISTS vw_dashboard_especializacion CASCADE')
            cur.execute('DROP VIEW IF EXISTS vw_match_empleo_especializacion_positivo CASCADE')
            cur.execute('DROP VIEW IF EXISTS vw_match_empleo_especializacion CASCADE')
            cur.execute('DROP TABLE IF EXISTS empleo_skills CASCADE')
            cur.execute('DROP TABLE IF EXISTS empleos CASCADE')
            cur.execute('''
                CREATE TABLE empleos (
                    id TEXT PRIMARY KEY,
                    titulo TEXT NOT NULL,
                    empresa TEXT,
                    descripcion TEXT,
                    location TEXT,
                    fecha TEXT,
                    source TEXT,
                    source_kind TEXT,
                    best_program_id INTEGER REFERENCES especializaciones(id) ON DELETE SET NULL,
                    best_program TEXT,
                    best_score NUMERIC,
                    matched_skills TEXT,
                    missing_skills TEXT,
                    skills_text TEXT,
                    matched_skill_count INTEGER,
                    job_url TEXT
                )
            ''')
            cur.execute('''
                CREATE TABLE empleo_skills (
                    empleo_id TEXT NOT NULL REFERENCES empleos(id) ON DELETE CASCADE,
                    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
                    confidence NUMERIC,
                    PRIMARY KEY (empleo_id, skill_id)
                )
            ''')
            cur.execute('SELECT id, nombre FROM skills')
            skill_name_map = {normalize(row['nombre']): row['id'] for row in cur.fetchall()}
            cur.execute('SELECT id, nombre FROM especializaciones')
            program_map = {normalize(row['nombre']): row['id'] for row in cur.fetchall()}

        jobs_rows = load_csv(JOBS_CSV)
        market_rows = load_csv(MARKET_JOBS_CSV)
        job_skills_rows = load_csv(JOB_SKILLS_CSV)

        with conn.cursor() as cur:
            for row in jobs_rows:
                cur.execute(
                    '''
                    INSERT INTO empleos (
                        id, titulo, empresa, descripcion, location, fecha, source, source_kind,
                        best_program_id, best_program, best_score, matched_skills, missing_skills,
                        skills_text, matched_skill_count, job_url
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE
                    SET titulo = EXCLUDED.titulo,
                        empresa = EXCLUDED.empresa,
                        descripcion = EXCLUDED.descripcion,
                        location = EXCLUDED.location,
                        fecha = EXCLUDED.fecha,
                        source = EXCLUDED.source,
                        source_kind = EXCLUDED.source_kind,
                        best_program_id = EXCLUDED.best_program_id,
                        best_program = EXCLUDED.best_program,
                        best_score = EXCLUDED.best_score,
                        matched_skills = EXCLUDED.matched_skills,
                        missing_skills = EXCLUDED.missing_skills,
                        skills_text = EXCLUDED.skills_text,
                        matched_skill_count = EXCLUDED.matched_skill_count,
                        job_url = EXCLUDED.job_url
                    ''',
                    (
                        row.get('job_id'),
                        row.get('job_title'),
                        row.get('company'),
                        row.get('description'),
                        row.get('location'),
                        row.get('date'),
                        row.get('source'),
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        row.get('job_url'),
                    ),
                )

            for row in market_rows:
                best_program = row.get('best_program')
                best_program_id = program_id_for(program_map, best_program) if best_program else None
                matched_skills = row.get('matched_skills') or ''
                missing_skills = row.get('missing_skills') or ''
                skills_text = row.get('skills') or ''
                matched_skill_count = len(split_tokens(matched_skills))

                cur.execute(
                    '''
                    INSERT INTO empleos (
                        id, titulo, empresa, descripcion, location, fecha, source, source_kind,
                        best_program_id, best_program, best_score, matched_skills, missing_skills,
                        skills_text, matched_skill_count, job_url
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE
                    SET titulo = EXCLUDED.titulo,
                        empresa = EXCLUDED.empresa,
                        descripcion = EXCLUDED.descripcion,
                        location = EXCLUDED.location,
                        fecha = EXCLUDED.fecha,
                        source = EXCLUDED.source,
                        source_kind = EXCLUDED.source_kind,
                        best_program_id = EXCLUDED.best_program_id,
                        best_program = EXCLUDED.best_program,
                        best_score = EXCLUDED.best_score,
                        matched_skills = EXCLUDED.matched_skills,
                        missing_skills = EXCLUDED.missing_skills,
                        skills_text = EXCLUDED.skills_text,
                        matched_skill_count = EXCLUDED.matched_skill_count,
                        job_url = EXCLUDED.job_url
                    ''',
                    (
                        row.get('job_id'),
                        row.get('job_title'),
                        row.get('company'),
                        None,
                        row.get('location'),
                        row.get('date'),
                        row.get('source'),
                        row.get('source_kind'),
                        best_program_id,
                        best_program,
                        row.get('best_score'),
                        matched_skills,
                        missing_skills,
                        skills_text,
                        matched_skill_count,
                        row.get('job_url'),
                    ),
                )

            for row in job_skills_rows:
                skill_id = skill_id_for(skill_name_map, row.get('skill_name', ''))
                if skill_id is None:
                    continue
                confidence = row.get('confidence')
                cur.execute(
                    '''
                    INSERT INTO empleo_skills (empleo_id, skill_id, confidence)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                    ''',
                    (row.get('job_id'), skill_id, confidence or None),
                )

            for row in market_rows:
                empleo_id = row.get('job_id')
                for token in split_tokens(row.get('matched_skills', '')) + split_tokens(row.get('skills', '')):
                    skill_id = skill_id_for(skill_name_map, token)
                    if skill_id is None:
                        continue
                    cur.execute(
                        '''
                        INSERT INTO empleo_skills (empleo_id, skill_id, confidence)
                        VALUES (%s, %s, %s)
                        ON CONFLICT DO NOTHING
                        ''',
                        (empleo_id, skill_id, 0.8),
                    )

            cur.execute(VIEW_SQL)

            cur.execute('REFRESH MATERIALIZED VIEW mv_dashboard_especializacion')

        conn.commit()
        print('Importación y actualización de vistas completadas.')
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    raise SystemExit(main())
