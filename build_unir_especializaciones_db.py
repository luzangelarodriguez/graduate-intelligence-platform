from __future__ import annotations

from typing import Iterable

try:
    import psycopg2
    from psycopg2 import Error as Psycopg2Error
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "psycopg2 no está instalado. Instala `psycopg2-binary` o `psycopg2` y vuelve a ejecutar el script."
    ) from exc


DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5433,
    "database": "cliente_a_db",
    "user": "postgres",
    "password": "postgres",
}


PROGRAMS = [
    {
        "name": "Especialización en Dirección y Gestión de Proyectos",
        "skills": ["gestión de proyectos", "planificación", "alcance", "riesgos", "cronograma", "metodologías ágiles"],
    },
    {
        "name": "Especialización en Gestión de la Seguridad y Salud en el Trabajo",
        "skills": ["sst", "prevención de riesgos", "salud ocupacional", "normativa laboral", "inspección", "seguridad industrial"],
    },
    {
        "name": "Especialización en Neuropsicología y Educación",
        "skills": ["neuropsicología", "aprendizaje", "cognición", "evaluación psicológica", "pedagogía", "intervención educativa"],
    },
    {
        "name": "Especialización en Administración y Gerencia de la Salud",
        "skills": ["gestión en salud", "administración sanitaria", "calidad asistencial", "liderazgo", "políticas de salud", "planeación"],
    },
    {
        "name": "Especialización en Alta Gerencia",
        "skills": ["liderazgo", "dirección estratégica", "toma de decisiones", "gestión de equipos", "planeación", "innovación"],
    },
    {
        "name": "Especialización en Visual Analytics y Big Data",
        "skills": ["big data", "visualización de datos", "power bi", "tableau", "sql", "analítica de negocio"],
    },
    {
        "name": "Especialización en Gerencia Financiera",
        "skills": ["finanzas corporativas", "análisis financiero", "presupuestos", "inversión", "contabilidad", "gestión de riesgos"],
    },
    {
        "name": "Especialización en Gestión Humana",
        "skills": ["talento humano", "selección", "capacitación", "clima organizacional", "liderazgo", "compensación"],
    },
    {
        "name": "Especialización en Inteligencia Artificial",
        "skills": ["machine learning", "python", "deep learning", "ciencia de datos", "nlp", "modelado predictivo"],
    },
    {
        "name": "Especialización en Gestión Pública",
        "skills": ["administración pública", "políticas públicas", "gobierno", "planeación institucional", "transparencia", "liderazgo público"],
    },
    {
        "name": "Especialización en Seguridad Informática",
        "skills": ["ciberseguridad", "seguridad de redes", "gestión de vulnerabilidades", "respuesta a incidentes", "criptografía", "auditoría"],
    },
    {
        "name": "Especialización en Ingeniería de Software",
        "skills": ["programación", "arquitectura de software", "testing", "apis", "git", "metodologías ágiles"],
    },
    {
        "name": "Especialización en Educación y Orientación Familiar",
        "skills": ["orientación familiar", "acompañamiento educativo", "consejería", "comunicación", "intervención psicoeducativa", "convivencia"],
    },
    {
        "name": "Especialización en Marketing Digital",
        "skills": ["marketing digital", "seo", "sem", "analítica web", "redes sociales", "branding"],
    },
    {
        "name": "Especialización en Gerencia Educativa",
        "skills": ["gestión educativa", "liderazgo pedagógico", "planeación", "calidad educativa", "currículo", "evaluación"],
    },
    {
        "name": "Especialización en Derechos Humanos",
        "skills": ["derechos humanos", "derecho internacional", "justicia social", "advocacy", "análisis de conflicto", "protección de derechos"],
    },
    {
        "name": "Especialización en Inteligencia de Negocio",
        "skills": ["business intelligence", "sql", "dashboards", "kpis", "analítica de datos", "visualización"],
    },
    {
        "name": "Especialización en Derecho de la Empresa",
        "skills": ["derecho comercial", "contratos", "cumplimiento", "sociedades", "asesoría jurídica", "gobierno corporativo"],
    },
    {
        "name": "Especialización en Educación Inclusiva",
        "skills": ["inclusión", "diversidad", "necesidades educativas especiales", "diseño universal", "pedagogía", "accesibilidad"],
    },
    {
        "name": "Especialización en Gestión Ambiental y Energética",
        "skills": ["gestión ambiental", "sostenibilidad", "energía", "impacto ambiental", "normativa ambiental", "eficiencia energética"],
    },
    {
        "name": "Especialización en Dirección Comercial y Ventas",
        "skills": ["ventas", "negociación", "estrategia comercial", "crm", "gestión de clientes", "canales comerciales"],
    },
    {
        "name": "Especialización en Derecho Digital",
        "skills": ["derecho digital", "protección de datos", "ciberseguridad legal", "comercio electrónico", "compliance", "propiedad digital"],
    },
    {
        "name": "Especialización en Pedagogía y Docencia",
        "skills": ["didáctica", "currículo", "evaluación", "diseño instruccional", "planificación educativa", "docencia"],
    },
    {
        "name": "Especialización en Dirección y Gestión de Tecnologías de la Información",
        "skills": ["gestión de ti", "transformación digital", "gobierno de ti", "arquitectura tecnológica", "liderazgo", "proyectos tecnológicos"],
    },
    {
        "name": "Especialización en TIC para la Enseñanza",
        "skills": ["tic educativas", "lms", "e-learning", "herramientas digitales", "diseño instruccional", "evaluación en línea"],
    },
    {
        "name": "Especialización en Revisoría Fiscal y Auditoría de Cuentas",
        "skills": ["auditoría", "revisoría fiscal", "contabilidad", "control interno", "niif", "cumplimiento"],
    },
]

ROLE_OVERRIDES = {
    "Especialización en Dirección y Gestión de Proyectos": "director de proyectos",
    "Especialización en Gestión de la Seguridad y Salud en el Trabajo": "gestor sst",
    "Especialización en Neuropsicología y Educación": "neuropsicólogo educativo",
    "Especialización en Administración y Gerencia de la Salud": "gerente en salud",
    "Especialización en Alta Gerencia": "directivo estratégico",
    "Especialización en Visual Analytics y Big Data": "analista de inteligencia de negocios",
    "Especialización en Gerencia Financiera": "gerente financiero",
    "Especialización en Gestión Humana": "gestor de talento humano",
    "Especialización en Inteligencia Artificial": "especialista en inteligencia artificial",
    "Especialización en Gestión Pública": "gestor público",
    "Especialización en Seguridad Informática": "analista de ciberseguridad",
    "Especialización en Ingeniería de Software": "ingeniero de software",
    "Especialización en Educación y Orientación Familiar": "orientador familiar",
    "Especialización en Marketing Digital": "especialista en marketing digital",
    "Especialización en Gerencia Educativa": "directivo educativo",
    "Especialización en Derechos Humanos": "gestor de derechos humanos",
    "Especialización en Inteligencia de Negocio": "analista de inteligencia de negocios",
    "Especialización en Derecho de la Empresa": "asesor jurídico empresarial",
    "Especialización en Educación Inclusiva": "gestor de educación inclusiva",
    "Especialización en Gestión Ambiental y Energética": "gestor ambiental",
    "Especialización en Dirección Comercial y Ventas": "director comercial",
    "Especialización en Derecho Digital": "asesor jurídico digital",
    "Especialización en Pedagogía y Docencia": "docente",
    "Especialización en Dirección y Gestión de Tecnologías de la Información": "director de ti",
    "Especialización en TIC para la Enseñanza": "docente en tic",
    "Especialización en Revisoría Fiscal y Auditoría de Cuentas": "revisor fiscal",
}


def uniq(items: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def get_or_create_id(
    cur,
    insert_sql: str,
    select_sql: str,
    insert_params: tuple,
    select_params: tuple | None = None,
) -> int:
    cur.execute(insert_sql, insert_params)
    row = cur.fetchone()
    if row:
        return int(row[0])

    cur.execute(select_sql, select_params or insert_params)
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"No se pudo recuperar el id para: {insert_params}")
    return int(row[0])


def infer_role(program_name: str) -> str:
    return ROLE_OVERRIDES.get(program_name, "especialista")


def ensure_schema(cur) -> None:
    cur.execute(
        """
        ALTER TABLE especializaciones
        ADD COLUMN IF NOT EXISTS rol TEXT
        """
    )


def build_db() -> None:
    conn = None
    inserted_specializations = 0
    inserted_relations = 0

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False

        with conn:
            with conn.cursor() as cur:
                ensure_schema(cur)
                specialization_insert = """
                    INSERT INTO especializaciones (nombre, rol)
                    VALUES (%s, %s)
                    ON CONFLICT (nombre) DO UPDATE
                    SET rol = EXCLUDED.rol
                    RETURNING id
                """
                specialization_select = """
                    SELECT id
                    FROM especializaciones
                    WHERE nombre = %s
                """
                skill_insert = """
                    INSERT INTO skills (nombre)
                    VALUES (%s)
                    ON CONFLICT (nombre) DO NOTHING
                    RETURNING id
                """
                skill_select = """
                    SELECT id
                    FROM skills
                    WHERE nombre = %s
                """
                relation_insert = """
                    INSERT INTO especializacion_skills (especializacion_id, skill_id)
                    VALUES (%s, %s)
                    ON CONFLICT (especializacion_id, skill_id) DO NOTHING
                """

                for program in PROGRAMS:
                    inserted_specializations += 1
                    especializacion_id = get_or_create_id(
                        cur,
                        specialization_insert,
                        specialization_select,
                        (program["name"], infer_role(program["name"])),
                        (program["name"],),
                    )

                    for skill in uniq(program["skills"]):
                        skill_id = get_or_create_id(
                            cur,
                            skill_insert,
                            skill_select,
                            (skill,),
                        )
                        cur.execute(relation_insert, (especializacion_id, skill_id))
                        inserted_relations += 1

        print(
            f"OK: procesadas {inserted_specializations} especializaciones y {inserted_relations} relaciones en PostgreSQL ({DB_CONFIG['database']})."
        )
    except Psycopg2Error as exc:
        if conn is not None:
            conn.rollback()
        raise SystemExit(f"Error de PostgreSQL: {exc}") from exc
    except Exception as exc:
        if conn is not None:
            conn.rollback()
        raise SystemExit(f"Error inesperado: {exc}") from exc
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    build_db()
