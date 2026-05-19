from __future__ import annotations







import argparse



import logging



import os



import re



import sys



import time



import unicodedata



from dataclasses import dataclass



from typing import Iterable



from urllib.parse import urljoin, urlparse







import psycopg2



import requests



from bs4 import BeautifulSoup



from psycopg2 import Error as Psycopg2Error



from psycopg2 import sql



from requests import Response, Session











REQUEST_TIMEOUT = 30



REQUEST_DELAY_SECONDS = float(os.getenv('REQUEST_DELAY_SECONDS', '1'))



DB_CONNECT_RETRIES = int(os.getenv('DB_CONNECT_RETRIES', '10'))



DB_RETRY_DELAY_SECONDS = float(os.getenv('DB_RETRY_DELAY_SECONDS', '5'))



LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()



DEBUG_SQL_PARAMS = os.getenv('DEBUG_SQL_PARAMS', '').strip().lower() in {'1', 'true', 'yes', 'on'}



DB_HOST = os.getenv('DB_HOST', 'localhost')



DB_USER = os.getenv('DB_USER', 'postgres')



DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')



DB_PORT = int(os.getenv('DB_PORT', '5432'))







HEADERS = {



    'User-Agent': (



        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '



        'AppleWebKit/537.36 (KHTML, like Gecko) '



        'Chrome/124.0.0.0 Safari/537.36'



    ),



    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',



}







TENANTS = {



    'cliente_a': {



        'db_name': 'cliente_a_db',



        'url': 'https://unir.edu.co/especializaciones/',



    },



    'cliente_b': {



        'db_name': 'cliente_b_db',



        'url': 'https://unir.edu.co/especializaciones/',



    },



}







TECHNICAL_SKILLS = [



    ('machine learning', ['machine learning', 'aprendizaje automatico', 'aprendizaje autom�tico']),



    ('deep learning', ['deep learning', 'redes neuronales profundas']),



    ('big data', ['big data']),



    ('ciencia de datos', ['ciencia de datos', 'data science']),



    ('programaci�n', ['programacion', 'programaci�n', 'coding', 'development']),



    ('ciberseguridad', ['ciberseguridad', 'seguridad inform�tica', 'seguridad informatica']),



    ('auditor�a', ['auditoria', 'auditor�a']),



    ('gesti�n de proyectos', ['gestion de proyectos', 'gesti�n de proyectos', 'project management']),



    ('anal�tica de datos', ['analitica de datos', 'anal�tica de datos', 'data analytics']),



    ('gesti�n de la calidad', ['gestion de la calidad', 'gesti�n de la calidad']),



    ('gesti�n del riesgo', ['gestion del riesgo', 'gesti�n del riesgo', 'risk management']),



    ('visual analytics', ['visual analytics', 'analitica visual', 'anal�tica visual']),



    ('sistema de gesti�n', ['sistema de gestion', 'sistema de gesti�n']),



]







TOOLS = [



    ('python', ['python']),



    ('sql', ['sql']),



    ('power bi', ['power bi', 'powerbi']),



    ('tableau', ['tableau']),



    ('excel', ['excel', 'microsoft excel']),



    ('bim', ['bim', 'building information modeling']),



    ('scrum', ['scrum']),



    ('kanban', ['kanban']),



    ('pmp', ['pmp', 'project management professional']),



    ('jira', ['jira']),



    ('trello', ['trello']),



    ('git', ['git', 'github']),



    ('moodle', ['moodle']),



    ('google analytics', ['google analytics']),



]







COMPETENCIES = [



    ('an�lisis', ['analisis', 'an�lisis']),



    ('gesti�n', ['gestion', 'gesti�n']),



    ('planificaci�n', ['planificacion', 'planificaci�n']),



    ('estrategia', ['estrategia', 'estrat�gica', 'estrategico', 'estrat�gico']),



    ('evaluaci�n', ['evaluacion', 'evaluaci�n']),



    ('diagn�stico', ['diagnostico', 'diagn�stico']),



    ('implementaci�n', ['implementacion', 'implementaci�n']),



    ('dise�o', ['diseno', 'dise�o']),



    ('interpretaci�n', ['interpretacion', 'interpretaci�n']),



    ('toma de decisiones', ['toma de decisiones']),



    ('seguimiento', ['seguimiento']),



    ('control', ['control']),



    ('formulaci�n', ['formulacion', 'formulaci�n']),



    ('investigaci�n', ['investigacion', 'investigaci�n']),



    ('innovaci�n', ['innovacion', 'innovaci�n']),



]







SOFT_SKILLS = [



    ('liderazgo', ['liderazgo', 'leadership']),



    ('comunicaci�n', ['comunicacion', 'comunicaci�n']),



    ('trabajo en equipo', ['trabajo en equipo']),



    ('negociaci�n', ['negociacion', 'negociaci�n']),



    ('resoluci�n de problemas', ['resolucion de problemas', 'resoluci�n de problemas']),



    ('pensamiento cr�tico', ['pensamiento critico', 'pensamiento cr�tico']),



    ('adaptabilidad', ['adaptabilidad', 'adaptacion al cambio', 'adaptaci�n al cambio']),



    ('creatividad', ['creatividad']),



    ('proactividad', ['proactividad']),



    ('colaboraci�n', ['colaboracion', 'colaboraci�n']),



    ('empat�a', ['empatia', 'empat�a']),



    ('organizaci�n', ['organizacion', 'organizaci�n']),



]



SKILL_CANONICAL_MAP = {

    'sql server': 'sql',

    'microsoft sql server': 'sql',

    'postgresql': 'sql',

    'mysql': 'sql',

    'power bi desktop': 'power bi',

    'microsoft power bi': 'power bi',

    'aprendizaje automatico': 'machine learning',

    'aprendizaje automatico supervisado': 'machine learning',

    'big data analytics': 'big data',

    'inteligencia negocio': 'inteligencia de negocios',

}

ACADEMIC_SKILL_TAXONOMY = {

    'data_engineering': [

        ('sql', ['sql server', 'microsoft sql server', 'postgresql', 'mysql']),

        ('etl', ['etl', 'extraccion transformacion y carga', 'integracion de datos']),

        ('data warehouse', ['data warehouse', 'almacen de datos', 'bodega de datos']),

        ('modelado de datos', ['modelado de datos', 'data modeling']),

        ('pipelines de datos', ['pipeline de datos', 'pipelines de datos']),

    ],

    'data_analysis': [

        ('analitica de datos', ['analitica de datos', 'data analytics', 'analitica avanzada']),

        ('estadistica', ['estadistica', 'statistics']),

        ('mineria de datos', ['mineria de datos', 'data mining']),

        ('visualizacion de datos', ['visualizacion de datos', 'data visualization']),

        ('interpretacion de datos', ['interpretacion de datos']),

    ],

    'business_intelligence': [

        ('power bi', ['power bi desktop', 'microsoft power bi']),

        ('tableau', ['tableau']),

        ('dashboards', ['dashboard', 'dashboards', 'cuadros de mando']),

        ('reporting', ['reporting', 'reportes', 'informes gerenciales']),

        ('kpi', ['kpi', 'kpis', 'indicadores']),

    ],

    'data_science': [

        ('python', ['python']),

        ('machine learning', ['machine learning', 'aprendizaje automatico', 'aprendizaje automatico supervisado']),

        ('inteligencia artificial', ['inteligencia artificial', 'artificial intelligence']),

        ('big data', ['big data', 'big data analytics']),

        ('ciencia de datos', ['ciencia de datos', 'data science']),

        ('modelado predictivo', ['modelado predictivo', 'predictive modeling']),

    ],

    'management': [

        ('gestion de proyectos', ['gestion de proyectos', 'project management', 'pmp']),

        ('planificacion', ['planificacion', 'planeacion']),

        ('direccion estrategica', ['direccion estrategica', 'estrategia empresarial']),

        ('toma de decisiones', ['toma de decisiones']),

        ('gestion del riesgo', ['gestion del riesgo', 'risk management']),

    ],

    'soft_skill': [

        ('liderazgo', ['liderazgo']),

        ('comunicacion', ['comunicacion', 'communication']),

        ('trabajo en equipo', ['trabajo en equipo', 'colaboracion']),

        ('pensamiento critico', ['pensamiento critico']),

        ('negociacion', ['negociacion']),

        ('creatividad', ['creatividad']),

        ('empatia', ['empatia']),

        ('adaptabilidad', ['adaptabilidad']),

        ('proactividad', ['proactividad']),

        ('resolucion de problemas', ['resolucion de problemas']),

    ],

}

ACADEMIC_CATEGORY_PRIORITY = [

    'data_engineering',

    'data_science',

    'business_intelligence',

    'data_analysis',

    'management',

    'soft_skill',

]

TECHNICAL_CATEGORIES = {

    'data_engineering',

    'data_analysis',

    'business_intelligence',

    'data_science',

}

TOOL_LIKE_TERMS = {

    'python',

    'sql',

    'power bi',

    'tableau',

    'excel',

    'docker',

    'tensorflow',

    'jira',

    'scrum',

    'kanban',

    'google analytics',

    'moodle',

    'bim',

    'pmp',

}

TARGET_SKILL_CATEGORIES = {

    'datos',

    'tecnologia',

    'negocios',

    'calidad',

    'educacion',

    'salud',

    'operaciones',

}

TARGET_SKILL_TAXONOMY = [

    ('sql', 'tecnologia', ['sql', 'sql server', 'postgresql', 'mysql']),

    ('python', 'tecnologia', ['python']),

    ('power bi', 'datos', ['power bi', 'power bi desktop']),

    ('tableau', 'datos', ['tableau']),

    ('analitica de datos', 'datos', ['analitica de datos', 'analisis de datos', 'data analytics']),

    ('big data', 'datos', ['big data']),

    ('machine learning', 'datos', ['machine learning', 'aprendizaje automatico']),

    ('visual analytics', 'datos', ['visual analytics']),

    ('inteligencia artificial', 'tecnologia', ['inteligencia artificial']),

    ('moodle', 'tecnologia', ['moodle', 'lms']),

    ('canva', 'tecnologia', ['canva']),

    ('didactica', 'educacion', ['didactica']),

    ('pedagogia', 'educacion', ['pedagogia']),

    ('docencia', 'educacion', ['docencia']),

    ('diseno curricular', 'educacion', ['diseno curricular']),

    ('evaluacion formativa', 'educacion', ['evaluacion formativa']),

    ('inclusion educativa', 'educacion', ['inclusion educativa', 'educacion inclusiva']),

    ('gestion educativa', 'educacion', ['gestion educativa', 'gerencia educativa']),

    ('salud ocupacional', 'salud', ['salud ocupacional']),

    ('gestion en salud', 'salud', ['administracion en salud', 'gerencia de la salud', 'gestion en salud']),

    ('seguridad y salud', 'salud', ['seguridad y salud en el trabajo']),

    ('auditoria', 'calidad', ['auditoria', 'control interno']),

    ('gestion de calidad', 'calidad', ['gestion de la calidad', 'calidad']),

    ('mejoramiento continuo', 'calidad', ['mejoramiento continuo']),

    ('gestion de proyectos', 'operaciones', ['gestion de proyectos', 'project management', 'pmp']),

    ('gestion de procesos', 'operaciones', ['gestion de procesos']),

    ('logistica', 'operaciones', ['logistica']),

    ('marketing digital', 'negocios', ['marketing digital']),

    ('inteligencia de negocios', 'negocios', ['inteligencia de negocios', 'business intelligence']),

    ('gestion comercial', 'negocios', ['direccion comercial', 'ventas']),

    ('gestion financiera', 'negocios', ['gerencia financiera', 'finanzas']),

    ('gestion publica', 'negocios', ['gestion publica']),

    ('direccion estrategica', 'negocios', ['direccion estrategica', 'estrategia empresarial']),

]

ROLE_BY_CATEGORY = {

    'datos': 'analista de datos',

    'tecnologia': 'especialista digital',

    'negocios': 'gestor organizacional',

    'calidad': 'gestor de calidad',

    'educacion': 'docente innovador',

    'salud': 'gestor en salud',

    'operaciones': 'gestor operativo',

}

TARGET_SKILL_TAXONOMY += [

    ('ciberseguridad', 'tecnologia', ['ciberseguridad', 'seguridad informatica', 'seguridad de la informacion']),

    ('ingenieria software', 'tecnologia', ['ingenieria de software', 'arquitectura de software', 'desarrollo de software']),

    ('transformacion digital', 'tecnologia', ['transformacion digital']),

    ('tic educativas', 'tecnologia', ['tic para la ensenanza', 'tecnologias educativas']),

    ('canvas', 'tecnologia', ['canvas']),

    ('blackboard', 'tecnologia', ['blackboard']),

    ('classroom', 'tecnologia', ['classroom', 'google classroom']),

    ('genially', 'tecnologia', ['genially']),

    ('powtoon', 'tecnologia', ['powtoon']),

    ('mendeley', 'tecnologia', ['mendeley']),

    ('zotero', 'tecnologia', ['zotero']),

    ('google scholar', 'tecnologia', ['google scholar']),

    ('rubistar', 'tecnologia', ['rubistar']),

    ('educaplay', 'tecnologia', ['educaplay']),

    ('analitica visual', 'datos', ['analitica visual', 'visual analytics']),

    ('mineria de datos', 'datos', ['mineria de datos', 'data mining']),

    ('ciencia de datos', 'datos', ['ciencia de datos', 'data science']),

    ('modelado predictivo', 'datos', ['modelado predictivo']),

    ('inteligencia negocio', 'datos', ['inteligencia de negocio', 'inteligencia de negocios']),

    ('marketing digital', 'negocios', ['marketing digital']),

    ('gestion comercial', 'negocios', ['direccion comercial', 'gestion comercial', 'ventas']),

    ('talento humano', 'negocios', ['gestion humana', 'talento humano']),

    ('gerencia financiera', 'negocios', ['gerencia financiera', 'gestion financiera']),

    ('revisoria fiscal', 'calidad', ['revisoria fiscal']),

    ('auditoria cuentas', 'calidad', ['auditoria de cuentas']),

    ('control interno', 'calidad', ['control interno']),

    ('normatividad educativa', 'educacion', ['normativas del sistema educativo', 'normatividad educativa']),

    ('orientacion familiar', 'educacion', ['orientacion familiar']),

    ('neuropsicologia', 'salud', ['neuropsicologia']),

    ('salud ocupacional', 'salud', ['salud ocupacional']),

    ('seguridad laboral', 'salud', ['seguridad y salud en el trabajo']),

    ('gerencia salud', 'salud', ['gerencia de la salud', 'administracion en salud']),

    ('gestion ambiental', 'operaciones', ['gestion ambiental']),

    ('gestion energetica', 'operaciones', ['gestion energetica']),

    ('eficiencia energetica', 'operaciones', ['eficiencia energetica']),

    ('energias renovables', 'operaciones', ['energias renovables']),

    ('sostenibilidad', 'operaciones', ['sostenibilidad', 'economia circular']),

    ('gestion publica', 'negocios', ['gestion publica']),

    ('derecho digital', 'negocios', ['derecho digital']),

    ('derecho empresarial', 'negocios', ['derecho de la empresa', 'derecho empresarial']),

    ('derechos humanos', 'negocios', ['derechos humanos']),

]

TECHNICAL_SKILLS += [


    ('analisis de datos', ['analisis de datos', 'an?lisis de datos', 'data analysis']),



    ('visualizacion de datos', ['visualizacion de datos', 'visualizaci?n de datos']),



    ('mineria de datos', ['mineria de datos', 'miner?a de datos', 'data mining']),



    ('sistemas de informacion', ['sistemas de informacion', 'sistemas de informaci?n']),



    ('seguridad de la informacion', ['seguridad de la informacion', 'seguridad de la informaci?n']),



    ('gestion documental', ['gestion documental', 'gesti?n documental']),



    ('control interno', ['control interno']),



    ('planeacion estrategica', ['planeacion estrategica', 'planeaci?n estrategica', 'planeaci?n estrat?gica', 'planificacion estrategica']),



    ('transformacion digital', ['transformacion digital', 'transformaci?n digital']),



    ('arquitectura de software', ['arquitectura de software']),



    ('desarrollo de software', ['desarrollo de software']),



    ('inteligencia de negocios', ['inteligencia de negocios', 'business intelligence']),



    ('modelado de procesos', ['modelado de procesos']),



    ('gestion de procesos', ['gestion de procesos', 'gesti?n de procesos']),



    ('gestion de la calidad', ['gestion de la calidad', 'gesti?n de la calidad']),



]







TOOLS += [



    ('microsoft office', ['microsoft office', 'office 365', 'office']),



    ('microsoft word', ['microsoft word', 'word']),



    ('microsoft powerpoint', ['microsoft powerpoint', 'powerpoint']),



    ('microsoft teams', ['microsoft teams', 'teams']),



    ('sharepoint', ['sharepoint']),



    ('looker studio', ['looker studio', 'google data studio']),



    ('sap', ['sap']),



    ('oracle', ['oracle']),



    ('autocad', ['autocad']),



    ('revit', ['revit']),



    ('r studio', ['r studio', 'rstudio']),



    ('spss', ['spss']),



    ('stata', ['stata']),



    ('postgresql', ['postgresql', 'postgres']),



    ('mysql', ['mysql']),



    ('mongodb', ['mongodb']),



    ('jupyter', ['jupyter', 'jupyter notebook']),



    ('asana', ['asana']),



    ('microsoft project', ['microsoft project', 'ms project']),



    ('kubernetes', ['kubernetes']),



]







COMPETENCIES += [



    ('pensamiento analitico', ['pensamiento analitico', 'pensamiento anal?tico']),



    ('pensamiento estrategico', ['pensamiento estrategico', 'pensamiento estrat?gico']),



    ('orientacion a resultados', ['orientacion a resultados', 'orientaci?n a resultados']),



    ('aprendizaje continuo', ['aprendizaje continuo']),



    ('gestion del cambio', ['gestion del cambio', 'gesti?n del cambio']),



    ('gestion del tiempo', ['gestion del tiempo', 'gesti?n del tiempo']),



    ('comunicacion efectiva', ['comunicacion efectiva', 'comunicaci?n efectiva']),



    ('resolucion de conflictos', ['resolucion de conflictos', 'resoluci?n de conflictos']),



    ('autonomia', ['autonomia', 'autonom?a']),



    ('responsabilidad', ['responsabilidad']),



    ('etica profesional', ['etica profesional', '?tica profesional']),



    ('capacidad de analisis', ['capacidad de analisis', 'capacidad de an?lisis']),



    ('capacidad de sintesis', ['capacidad de sintesis', 'capacidad de s?ntesis']),



    ('toma de decisiones', ['toma de decisiones']),



]















SKILL_GENERIC_EXCLUSIONS = {

    'gestion',

    'analisis',

    'investigacion',

    'seguimiento',

    'evaluacion',

    'implementacion',

    'dise?o',

    'diseno',

    'interpretacion',

    'formulacion',

    'control',

    'diagnostico',

    'estrategia',

    'innovacion',

    'sistema de gestion',

    'planeacion',

    'proceso',

    'procesos',

    'desarrollo',

    'formacion',

    'conocimiento',
}



TECHNICAL_SKILLS += [

    ('gesti?n ambiental', ['gestion ambiental', 'gesti?n ambiental']),

    ('gesti?n energ?tica', ['gestion energ?tica', 'gesti?n energ?tica', 'gestion energetica', 'gesti?n energetica']),

    ('sostenibilidad', ['sostenibilidad']),

    ('eficiencia energ?tica', ['eficiencia energetica', 'eficiencia energ?tica']),

    ('energ?as renovables', ['energias renovables', 'energ?as renovables']),

    ('impacto ambiental', ['impacto ambiental']),

    ('cambio clim?tico', ['cambio climatico', 'cambio clim?tico']),

    ('econom?a circular', ['economia circular', 'econom?a circular']),

    ('seguridad y salud en el trabajo', ['seguridad y salud en el trabajo']),

    ('salud ocupacional', ['salud ocupacional']),

    ('derecho digital', ['derecho digital']),

    ('educaci?n inclusiva', ['educacion inclusiva', 'educaci?n inclusiva']),

    ('gesti?n p?blica', ['gestion publica', 'gesti?n p?blica']),

    ('gerencia educativa', ['gerencia educativa']),

    ('marketing digital', ['marketing digital']),

    ('inteligencia artificial', ['inteligencia artificial']),

]



STOP_HEADINGS_FOR_DESCRIPTION = [



    'plan de estudios',



    'campo laboral',



    'perfil recomendado',



    'requisitos de acceso',



    'metodologia',



    'metodolog?a',



    'admision',



    'admisi?n',



]







CATEGORY_SQL = {



    'skills': {



        'insert': '''



            INSERT INTO skills (nombre)



            VALUES (%s)



            ON CONFLICT (nombre) DO NOTHING



            RETURNING id



        ''',



        'select': '''



            SELECT id



            FROM skills



            WHERE nombre = %s



        ''',



        'relation': '''



            INSERT INTO especializacion_skills (especializacion_id, skill_id)



            VALUES (%s, %s)



            ON CONFLICT DO NOTHING



        ''',



    },



    'herramientas': {



        'insert': '''



            INSERT INTO herramientas (nombre)



            VALUES (%s)



            ON CONFLICT (nombre) DO NOTHING



            RETURNING id



        ''',



        'select': '''



            SELECT id



            FROM herramientas



            WHERE nombre = %s



        ''',



        'relation': '''



            INSERT INTO especializacion_herramientas (especializacion_id, herramienta_id)



            VALUES (%s, %s)



            ON CONFLICT DO NOTHING



        ''',



    },



    'competencias': {



        'insert': '''



            INSERT INTO competencias (nombre)



            VALUES (%s)



            ON CONFLICT (nombre) DO NOTHING



            RETURNING id



        ''',



        'select': '''



            SELECT id



            FROM competencias



            WHERE nombre = %s



        ''',



        'relation': '''



            INSERT INTO especializacion_competencias (especializacion_id, competencia_id)



            VALUES (%s, %s)



            ON CONFLICT DO NOTHING



        ''',



    },



    'habilidades_blandas': {



        'insert': '''



            INSERT INTO habilidades_blandas (nombre)



            VALUES (%s)



            ON CONFLICT (nombre) DO NOTHING



            RETURNING id



        ''',



        'select': '''



            SELECT id



            FROM habilidades_blandas



            WHERE nombre = %s



        ''',



        'relation': '''



            INSERT INTO especializacion_habilidades_blandas (especializacion_id, habilidad_id)



            VALUES (%s, %s)



            ON CONFLICT DO NOTHING



        ''',



    },



}











@dataclass



class ProgramData:



    name: str


    role: str





    description: str



    campo_laboral: str



    general_text: str



    technical_skills: list[str]



    tools: list[str]



    competencies: list[str]



    soft_skills: list[str]


    categorized_skills: list[tuple[str, str]]


    graduation_profiles: list[str]















def setup_logging() -> None:



    logging.basicConfig(



        level=getattr(logging, LOG_LEVEL, logging.INFO),



        format='%(asctime)s %(levelname)s %(message)s',



    )















def parse_args() -> argparse.Namespace:



    parser = argparse.ArgumentParser(description='Scraper multi-tenant de especializaciones UNIR')



    parser.add_argument(



        '--tenant',



        required=True,



        help='Nombre del tenant, lista separada por comas o all para ejecutar todos los tenants',



    )



    return parser.parse_args()















def get_config(tenant: str) -> dict[str, str]:



    if tenant not in TENANTS:



        raise KeyError(f'Tenant desconocido: {tenant}')



    return TENANTS[tenant]















def resolve_tenants(raw_value: str) -> list[str]:



    value = (raw_value or '').strip()



    if not value:



        return []



    if value.lower() == 'all':



        return list(TENANTS.keys())



    return [tenant.strip() for tenant in value.split(',') if tenant.strip()]















def normalize_text(text: str) -> str:



    text = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode('ascii').lower()



    text = re.sub(r'[^a-z0-9]+', ' ', text)



    return re.sub(r'\s+', ' ', text).strip()















def clean_text(text: str) -> str:



    return normalize_text(text)











def storage_label(text: str) -> str:



    return re.sub(r'\s+', ' ', (text or '').strip().lower())











SKILL_GENERIC_EXCLUSIONS_NORMALIZED = {normalize_text(term) for term in SKILL_GENERIC_EXCLUSIONS}

TOOL_LIKE_TERMS_NORMALIZED = {normalize_text(term) for term in TOOL_LIKE_TERMS}



def canonicalize_skill_name(skill: str) -> str:



    normalized = normalize_text(skill)



    if not normalized:



        return ''



    return SKILL_CANONICAL_MAP.get(normalized, normalized)



def extract_categorized_skills(program_text: str) -> list[dict[str, str]]:



    normalized_program_text = normalize_text(program_text)



    if not normalized_program_text:



        return []



    matched: dict[str, str] = {}



    for category in ACADEMIC_CATEGORY_PRIORITY:



        for canonical, aliases in ACADEMIC_SKILL_TAXONOMY.get(category, []):



            variants = [canonical] + aliases



            if not any(contains_term(normalized_program_text, variant) for variant in variants):



                continue



            normalized_skill = canonicalize_skill_name(canonical)



            if not normalized_skill or normalized_skill in SKILL_GENERIC_EXCLUSIONS_NORMALIZED:



                continue



            if normalized_skill not in matched:



                matched[normalized_skill] = category



    return [{'skill': skill, 'categoria': matched[skill]} for skill in sorted(matched)]




def extract_target_skills(program_text: str, limit: int = 8) -> list[tuple[str, str]]:

    normalized_program_text = normalize_text(program_text)

    if not normalized_program_text:

        return []

    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    for canonical, category, aliases in TARGET_SKILL_TAXONOMY:

        normalized_skill = storage_label(canonicalize_skill_name(canonical))
        if not normalized_skill or normalized_skill in seen:
            continue

        if category not in TARGET_SKILL_CATEGORIES:
            continue

        if len(normalized_skill.split()) > 3:
            continue

        variants = [canonical] + aliases
        if not any(contains_term(normalized_program_text, variant) for variant in variants):
            continue

        if normalized_skill in SKILL_GENERIC_EXCLUSIONS_NORMALIZED:
            continue

        seen.add(normalized_skill)
        out.append((normalized_skill, category))
        if len(out) >= limit:
            break

    return out


def infer_role(program_name: str, program_text: str, categorized_skills: list[tuple[str, str]]) -> str:

    normalized_title = normalize_text(program_name)
    normalized_text = normalize_text(program_text)

    if any(token in normalized_title for token in ['docencia', 'pedagogia', 'educacion']):
        return 'docente innovador'

    if any(token in normalized_title for token in ['salud', 'neuropsicologia']):
        return 'gestor en salud'

    if categorized_skills:
        counts: dict[str, int] = {}
        for _, category in categorized_skills:
            counts[category] = counts.get(category, 0) + 1
        dominant = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[0][0]
        return ROLE_BY_CATEGORY.get(dominant, 'gestor organizacional')

    if any(token in normalized_text for token in ['sql', 'analitica', 'datos']):
        return 'analista de datos'

    if any(token in normalized_text for token in ['software', 'tecnologia', 'digital']):
        return 'especialista digital'

    return 'gestor organizacional'


def extract_graduation_profiles(profile_text: str, role: str, limit: int = 8) -> list[str]:

    normalized_profile = (profile_text or '').strip()
    if not normalized_profile:
        return [storage_label(role)]

    # Prefer explicit role/area labels like "Analista de datos:" when present.
    label_pattern = re.compile(r'([A-Za-zÁÉÍÓÚáéíóúÑñ0-9()/\s-]{3,80}):')
    excluded_labels = {
        'campo laboral',
        'perfil de egreso',
        'perfil profesional',
        'plan de estudios',
        'metodologia',
        'requisitos de acceso',
        'entre tus principales competencias estaran',
        'en areas como',
    }
    labels: list[str] = []
    seen_labels: set[str] = set()
    for match in label_pattern.finditer(normalized_profile):
        raw_label = re.sub(r'\s+', ' ', match.group(1)).strip(' -\n\r\t')
        if not raw_label:
            continue
        normalized_label = normalize_text(raw_label)
        if not normalized_label or normalized_label in excluded_labels:
            continue
        if normalized_label.startswith('entre tus principales competencias'):
            continue
        if normalized_label.startswith('en areas como'):
            continue
        if normalized_label in seen_labels:
            continue
        seen_labels.add(normalized_label)
        labels.append(raw_label)
        if len(labels) >= limit:
            break
    if labels:
        return labels

    raw_parts = re.split(r'[\n.;]+', normalized_profile)
    out: list[str] = []
    for part in raw_parts:
        sentence = storage_label(part)
        if not sentence:
            continue

        sentence = re.sub(r'^(el|la)\s+egresad[oa]\s+', '', sentence)
        sentence = re.sub(r'^(sera|podra|estara)\s+(capaz de\s+)?', '', sentence)
        sentence = sentence.strip()

        words = sentence.split()
        if len(words) < 3:
            continue
        if len(words) > 20:
            continue
        if sentence in out:
            continue

        out.append(sentence)
        if len(out) >= limit:
            break

    if not out:
        return [storage_label(role)]
    return out

def uniq(items: Iterable[str]) -> list[str]:


    out: list[str] = []



    seen: set[str] = set()



    for item in items:



        if item and item not in seen:



            seen.add(item)



            out.append(item)



    return out















def contains_term(normalized_text: str, term: str) -> bool:



    normalized_term = normalize_text(term)



    if not normalized_term:



        return False



    if ' ' in normalized_term:



        return normalized_term in normalized_text



    return re.search(rf'\b{re.escape(normalized_term)}\b', normalized_text) is not None















def match_keywords(text: str, keyword_groups: list[tuple[str, list[str]]], exclude_terms: Iterable[str] | None = None) -> list[str]:



    normalized_text = normalize_text(text)



    excluded = {normalize_text(term) for term in (exclude_terms or [])}



    matches: list[str] = []



    for canonical, aliases in keyword_groups:



        variants = [canonical] + aliases



        if any(contains_term(normalized_text, variant) for variant in variants):



            label = storage_label(canonical)



            if normalize_text(label) not in excluded:



                matches.append(label)



    return uniq(matches)















def get_session() -> Session:



    session = requests.Session()



    session.headers.update(HEADERS)



    return session















def fetch_url(session: Session, url: str) -> Response:



    response = session.get(url, timeout=REQUEST_TIMEOUT)



    response.raise_for_status()



    return response















def get_program_links(url: str, session: Session | None = None) -> list[str]:



    owns_session = session is None



    session = session or get_session()







    try:



        response = fetch_url(session, url)



        soup = BeautifulSoup(response.text, 'html.parser')







        links: list[str] = []



        seen: set[str] = set()



        base_netloc = urlparse(url).netloc







        for anchor in soup.find_all('a', href=True):



            href = urljoin(url, anchor['href'])



            parsed = urlparse(href)







            if parsed.netloc != base_netloc:



                continue



            if not parsed.path.startswith('/especializaciones/'):



                continue



            if parsed.path.rstrip('/') == '/especializaciones':



                continue







            path_parts = [part for part in parsed.path.split('/') if part]



            if len(path_parts) != 2:



                continue







            normalized = parsed.scheme + '://' + parsed.netloc + parsed.path



            if normalized in seen:



                continue







            seen.add(normalized)



            links.append(normalized)







        if not links:



            raise RuntimeError('No se encontraron enlaces de especializaciones en la p�gina principal.')







        return links



    finally:



        if owns_session:



            session.close()















def collect_section_text(start_heading, stop_level: int | None = None) -> str:



    parts: list[str] = []



    for sibling in start_heading.next_siblings:



        if getattr(sibling, 'name', None) and re.fullmatch(r'h[1-6]', sibling.name or ''):



            sibling_level = int(sibling.name[1])



            if stop_level is None or sibling_level <= stop_level:



                break



        if hasattr(sibling, 'get_text'):



            text = sibling.get_text(' ', strip=True)



        else:



            text = str(sibling).strip()



        if text:



            parts.append(text)



    return ' '.join(parts).strip()















def extract_text_sections(soup: BeautifulSoup) -> dict[str, str]:



    main = soup.find('main') or soup.body or soup



    headings = main.find_all(re.compile(r'^h[1-6]$'))







    title = ''



    for heading in headings:



        if heading.name == 'h1':



            title = heading.get_text(' ', strip=True)



            break







    general_text = main.get_text(' ', strip=True)



    campo_laboral = ''

    perfil_egreso = ''



    description_parts: list[str] = []







    if headings:



        first_heading = headings[0]



        for sibling in first_heading.next_siblings:



            if getattr(sibling, 'name', None) and re.fullmatch(r'h[1-6]', sibling.name or ''):



                normalized_heading = normalize_text(sibling.get_text(' ', strip=True))



                if any(stop in normalized_heading for stop in STOP_HEADINGS_FOR_DESCRIPTION):



                    break



            if hasattr(sibling, 'get_text'):



                text = sibling.get_text(' ', strip=True)



            else:



                text = str(sibling).strip()



            if text:



                description_parts.append(text)







    campo_heading = None

    perfil_heading = None

    campo_section = main.select_one("section[aria-labelledby='campo-laboral']") or soup.select_one("section[aria-labelledby='campo-laboral']")



    for heading in headings:



        normalized_heading = normalize_text(heading.get_text(' ', strip=True))



        if 'campo laboral' in normalized_heading and campo_heading is None:



            campo_heading = heading

        if any(token in normalized_heading for token in ['perfil de egreso', 'perfil egreso', 'perfil profesional']) and perfil_heading is None:

            perfil_heading = heading

        if campo_heading is not None and perfil_heading is not None:
            break







    if campo_section is not None:

        campo_laboral = campo_section.get_text(' ', strip=True)

    elif campo_heading is not None:



        campo_laboral = collect_section_text(campo_heading, stop_level=int(campo_heading.name[1]))

    if perfil_heading is not None:

        perfil_egreso = collect_section_text(perfil_heading, stop_level=int(perfil_heading.name[1]))







    return {



        'name': title,



        'description': ' '.join(description_parts).strip(),



        'campo_laboral': campo_laboral,

        'perfil_egreso': perfil_egreso,



        'general_text': general_text,



    }















def _classify_text_legacy(text: str, skill_text: str | None = None) -> dict[str, list[str]]:


    skill_source = skill_text or text



    return {



        'skills': match_keywords(skill_source, TECHNICAL_SKILLS, exclude_terms=SKILL_GENERIC_EXCLUSIONS),



        'tools': match_keywords(text, TOOLS),



        'competencies': match_keywords(text, COMPETENCIES),



        'soft_skills': match_keywords(text, SOFT_SKILLS),



    }















def classify_text(text: str, skill_text: str | None = None) -> dict[str, list[str]]:

    skill_source = skill_text or text

    categorized = extract_categorized_skills(skill_source)
    normalized_skill_source = normalize_text(skill_source)

    tools = match_keywords(text, TOOLS)

    skills: list[str] = []

    competencies: list[str] = []

    soft_skills: list[str] = []

    normalized_tools = TOOL_LIKE_TERMS_NORMALIZED | {normalize_text(value) for value in tools}

    for item in categorized:
        value = storage_label(item['skill'])
        category = item['categoria']
        normalized_value = normalize_text(value)

        if not value or normalized_value in SKILL_GENERIC_EXCLUSIONS_NORMALIZED:
            continue

        if category == 'soft_skill':
            soft_skills.append(value)
            continue

        if category == 'management':
            competencies.append(value)
            continue

        if category in TECHNICAL_CATEGORIES:
            if normalized_value in normalized_tools:
                tools.append(value)
            else:
                skills.append(value)

    skills.extend(match_keywords(skill_source, TECHNICAL_SKILLS, exclude_terms=SKILL_GENERIC_EXCLUSIONS))
    competencies.extend(match_keywords(text, COMPETENCIES, exclude_terms=SKILL_GENERIC_EXCLUSIONS))
    soft_skills.extend(match_keywords(text, SOFT_SKILLS))

    tools = uniq(
        [
            storage_label(canonicalize_skill_name(value))
            for value in tools
            if canonicalize_skill_name(value)
        ]
    )
    normalized_tool_values = {normalize_text(value) for value in tools}

    skills = uniq(
        [
            storage_label(canonicalize_skill_name(value))
            for value in skills
            if canonicalize_skill_name(value)
            and normalize_text(canonicalize_skill_name(value)) not in SKILL_GENERIC_EXCLUSIONS_NORMALIZED
            and normalize_text(canonicalize_skill_name(value)) not in normalized_tool_values
        ]
    )
    skills = [
        value
        for value in skills
        if normalize_text(value) != 'big data' or contains_term(normalized_skill_source, 'big data')
    ]

    competencies = uniq(
        [
            storage_label(canonicalize_skill_name(value))
            for value in competencies
            if canonicalize_skill_name(value)
            and normalize_text(canonicalize_skill_name(value)) not in SKILL_GENERIC_EXCLUSIONS_NORMALIZED
        ]
    )

    soft_skills = uniq(
        [
            storage_label(canonicalize_skill_name(value))
            for value in soft_skills
            if canonicalize_skill_name(value)
        ]
    )

    return {
        'skills': skills,
        'tools': tools,
        'competencies': competencies,
        'soft_skills': soft_skills,
    }


def scrape_program(url: str, session: Session | None = None) -> ProgramData:


    owns_session = session is None



    session = session or get_session()







    try:



        response = fetch_url(session, url)



        soup = BeautifulSoup(response.text, 'html.parser')



        sections = extract_text_sections(soup)







        name = sections['name']



        if not name:



            fallback_h1 = soup.find('h1')



            name = fallback_h1.get_text(' ', strip=True) if fallback_h1 else ''



        if not name:



            raise ValueError(f'No se pudo extraer el nombre del programa: {url}')







        skill_text = ' '.join(



            part for part in [sections['description'], sections['campo_laboral'], sections.get('perfil_egreso', ''), name] if part



        )



        combined_text = ' '.join(



            part for part in [sections['description'], sections['campo_laboral'], sections['general_text'], name] if part



        )



        classification = classify_text(combined_text, skill_text=skill_text)







        description = ' '.join(



            part for part in [sections['description'], sections['campo_laboral']] if part



        ).strip()



        if not description:



            description = sections['general_text']








        target_skills = extract_target_skills(skill_text)

        role = infer_role(name, skill_text, target_skills)
        graduation_source = sections.get('campo_laboral', '') or sections.get('perfil_egreso', '')
        graduation_profiles = extract_graduation_profiles(graduation_source, role)

        return ProgramData(



            name=storage_label(name),

            role=role,




            description=clean_text(description),



            campo_laboral=clean_text(sections['campo_laboral']),



            general_text=clean_text(sections['general_text']),



            technical_skills=classification['skills'],



            tools=classification['tools'],



            competencies=classification['competencies'],



            soft_skills=classification['soft_skills'],

            categorized_skills=target_skills,

            graduation_profiles=graduation_profiles,




        )



    except requests.HTTPError as exc:



        raise RuntimeError(f'Error HTTP al acceder a {url}: {exc}') from exc



    except requests.RequestException as exc:



        raise RuntimeError(f'Error de red al acceder a {url}: {exc}') from exc



    except Exception as exc:



        raise RuntimeError(f'Error procesando {url}: {exc}') from exc



    finally:



        if owns_session:



            session.close()















def normalize_lookup_tables(conn) -> None:



    mappings = [



        ('skills', 'especializacion_skills', 'skill_id'),



        ('herramientas', 'especializacion_herramientas', 'herramienta_id'),



        ('competencias', 'especializacion_competencias', 'competencia_id'),



        ('habilidades_blandas', 'especializacion_habilidades_blandas', 'habilidad_id'),



        ('especializaciones', None, None),



    ]







    with conn.cursor() as cur:



        for table_name, relation_table, relation_column in mappings:



            cur.execute(



                sql.SQL(



                    '''



                    SELECT lower(nombre) AS normalized_name, array_agg(id ORDER BY id) AS ids



                    FROM {}



                    GROUP BY lower(nombre)



                    HAVING COUNT(*) > 1



                    '''



                ).format(sql.Identifier(table_name))



            )



            duplicates = cur.fetchall()







            for _, ids in duplicates:



                keep_id = ids[0]



                duplicate_ids = ids[1:]



                if relation_table is not None and duplicate_ids:



                    cur.execute(



                        sql.SQL(



                            '''



                            INSERT INTO {} (especializacion_id, {})



                            SELECT especializacion_id, %s



                            FROM {}



                            WHERE {} = ANY(%s)



                            ON CONFLICT DO NOTHING



                            '''



                        ).format(



                            sql.Identifier(relation_table),



                            sql.Identifier(relation_column),



                            sql.Identifier(relation_table),



                            sql.Identifier(relation_column),



                        ),



                        (keep_id, duplicate_ids),



                    )



                    cur.execute(



                        sql.SQL('DELETE FROM {} WHERE {} = ANY(%s)').format(



                            sql.Identifier(relation_table), sql.Identifier(relation_column)



                        ),



                        (duplicate_ids,),



                    )



                if duplicate_ids:



                    cur.execute(



                        sql.SQL('DELETE FROM {} WHERE id = ANY(%s)').format(sql.Identifier(table_name)),



                        (duplicate_ids,),



                    )







            cur.execute(



                sql.SQL('UPDATE {} SET nombre = lower(nombre)').format(sql.Identifier(table_name))



            )








    conn.commit()







def cleanup_generic_skills(conn) -> None:

    excluded = {normalize_text(term) for term in SKILL_GENERIC_EXCLUSIONS}

    with conn.cursor() as cur:

        cur.execute('SELECT id, nombre FROM skills')

        skill_rows = cur.fetchall()

        ids_to_remove = [skill_id for skill_id, nombre in skill_rows if normalize_text(nombre) in excluded]

        if ids_to_remove:

            cur.execute('DELETE FROM especializacion_skills WHERE skill_id = ANY(%s)', (ids_to_remove,))

            cur.execute('DELETE FROM skills WHERE id = ANY(%s)', (ids_to_remove,))

    conn.commit()





def ensure_database_exists(config: dict[str, str]) -> None:



    admin_conn = None



    try:



        admin_conn = psycopg2.connect(



            host=DB_HOST,



            database='postgres',



            user=DB_USER,



            password=DB_PASSWORD,



            port=DB_PORT,



        )



        admin_conn.autocommit = True



        with admin_conn.cursor() as cur:



            cur.execute('SELECT 1 FROM pg_database WHERE datname = %s', (config['db_name'],))



            if cur.fetchone() is None:



                cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(config['db_name'])))



                logging.info('Creada base de datos %s', config['db_name'])



    finally:



        if admin_conn is not None:



            admin_conn.close()















def ensure_schema(conn) -> None:



    with conn.cursor() as cur:



        cur.execute(



            '''



            CREATE TABLE IF NOT EXISTS especializaciones (



                id SERIAL PRIMARY KEY,



                nombre TEXT NOT NULL UNIQUE,



                descripcion TEXT



            )



            '''



        )



        cur.execute(



            '''



            CREATE TABLE IF NOT EXISTS skills (



                id SERIAL PRIMARY KEY,



                nombre TEXT NOT NULL UNIQUE



            )



            '''



        )


        cur.execute("ALTER TABLE especializaciones ADD COLUMN IF NOT EXISTS rol TEXT")

        cur.execute("ALTER TABLE skills ADD COLUMN IF NOT EXISTS categoria TEXT")




        cur.execute(



            '''



            CREATE TABLE IF NOT EXISTS herramientas (



                id SERIAL PRIMARY KEY,



                nombre TEXT NOT NULL UNIQUE



            )



            '''



        )



        cur.execute(



            '''



            CREATE TABLE IF NOT EXISTS competencias (



                id SERIAL PRIMARY KEY,



                nombre TEXT NOT NULL UNIQUE



            )



            '''



        )



        cur.execute(



            '''



            CREATE TABLE IF NOT EXISTS habilidades_blandas (



                id SERIAL PRIMARY KEY,



                nombre TEXT NOT NULL UNIQUE



            )



            '''



        )



        cur.execute(



            '''



            CREATE TABLE IF NOT EXISTS especializacion_skills (



                especializacion_id INTEGER NOT NULL REFERENCES especializaciones(id) ON DELETE CASCADE,



                skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,



                PRIMARY KEY (especializacion_id, skill_id)



            )



            '''



        )



        cur.execute(



            '''



            CREATE TABLE IF NOT EXISTS especializacion_herramientas (



                especializacion_id INTEGER NOT NULL REFERENCES especializaciones(id) ON DELETE CASCADE,



                herramienta_id INTEGER NOT NULL REFERENCES herramientas(id) ON DELETE CASCADE,



                PRIMARY KEY (especializacion_id, herramienta_id)



            )



            '''



        )



        cur.execute(



            '''



            CREATE TABLE IF NOT EXISTS especializacion_competencias (



                especializacion_id INTEGER NOT NULL REFERENCES especializaciones(id) ON DELETE CASCADE,



                competencia_id INTEGER NOT NULL REFERENCES competencias(id) ON DELETE CASCADE,



                PRIMARY KEY (especializacion_id, competencia_id)



            )



            '''



        )



        cur.execute(



            '''



            CREATE TABLE IF NOT EXISTS especializacion_habilidades_blandas (



                especializacion_id INTEGER NOT NULL REFERENCES especializaciones(id) ON DELETE CASCADE,



                habilidad_id INTEGER NOT NULL REFERENCES habilidades_blandas(id) ON DELETE CASCADE,



                PRIMARY KEY (especializacion_id, habilidad_id)



            )



            '''



        )

        cur.execute(

            '''

            CREATE TABLE IF NOT EXISTS perfiles_egreso (

                id SERIAL PRIMARY KEY,

                especializacion_id INTEGER NOT NULL REFERENCES especializaciones(id) ON DELETE CASCADE,

                perfil TEXT NOT NULL,

                UNIQUE (especializacion_id, perfil)

            )

            '''

        )

    conn.commit()















def connect_db(config: dict[str, str]):



    last_error: Exception | None = None



    for attempt in range(1, DB_CONNECT_RETRIES + 1):



        try:



            logging.info('[%s] Conectando a PostgreSQL db=%s intento=%s/%s', config['tenant'], config['db_name'], attempt, DB_CONNECT_RETRIES)



            ensure_database_exists(config)



            conn = psycopg2.connect(



                host=DB_HOST,



                database=config['db_name'],



                user=DB_USER,



                password=DB_PASSWORD,



                port=DB_PORT,



            )



            conn.autocommit = False



            ensure_schema(conn)



            normalize_lookup_tables(conn)



            cleanup_generic_skills(conn)



            return conn



        except Psycopg2Error as exc:



            last_error = exc



            logging.warning('[%s] No se pudo conectar a la base %s: %s', config['tenant'], config['db_name'], exc)



            if attempt < DB_CONNECT_RETRIES:



                time.sleep(DB_RETRY_DELAY_SECONDS)







    raise ConnectionError(f'No fue posible conectar a {config["db_name"]} tras {DB_CONNECT_RETRIES} intentos: {last_error}')















def normalize_params(params) -> tuple:



    if params is None:



        return ()



    if isinstance(params, tuple):



        return params



    if isinstance(params, list):



        return tuple(params)



    if isinstance(params, (str, bytes)):



        return (params,)



    return (params,)











def count_sql_placeholders(sql_text: str) -> int:



    return len(re.findall(r'(?<!%)%s', sql_text))











def validate_sql_params(sql_text: str, params: tuple, label: str) -> None:



    expected = count_sql_placeholders(sql_text)



    actual = len(params)



    if expected != actual:



        raise ValueError(



            f'[{label}] SQL placeholder mismatch: expected {expected} params, got {actual}. '



            f'SQL={sql_text!r} params={params!r}'



        )











def upsert_get_id(cur, insert_sql: str, select_sql: str, insert_params, select_params=None) -> int:



    safe_insert_params = normalize_params(insert_params)



    if select_params is None:



        if len(safe_insert_params) != 1:



            raise ValueError(



                'select_params is required when insert_params has more than one value; '



                f'insert_params={safe_insert_params!r}'



            )



        safe_select_params = safe_insert_params



    else:



        safe_select_params = normalize_params(select_params)







    validate_sql_params(insert_sql, safe_insert_params, 'insert')



    validate_sql_params(select_sql, safe_select_params, 'select')







    if DEBUG_SQL_PARAMS:



        logging.debug(



            'SQL params debug | insert=%s | select=%s | insert_params=%s | select_params=%s',



            count_sql_placeholders(insert_sql),



            count_sql_placeholders(select_sql),



            type(safe_insert_params).__name__ + ':' + repr(safe_insert_params),



            type(safe_select_params).__name__ + ':' + repr(safe_select_params),



        )







    cur.execute(insert_sql, safe_insert_params)



    row = cur.fetchone()



    if row:



        return int(row[0])







    cur.execute(select_sql, safe_select_params)



    row = cur.fetchone()



    if not row:



        raise RuntimeError(f'No se pudo recuperar el ID para {safe_select_params}')



    return int(row[0])











def save_to_db(data: list[ProgramData], conn) -> None:

    if not data:
        raise ValueError('No hay datos para guardar en PostgreSQL.')

    with conn:
        with conn.cursor() as cur:
            cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_especializaciones_nombre ON especializaciones (nombre)')
            cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_skills_nombre ON skills (nombre)')
            cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_especializacion_skills_rel ON especializacion_skills (especializacion_id, skill_id)')
            cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS ux_perfiles_egreso_rel ON perfiles_egreso (especializacion_id, perfil)')

            insert_especializacion = '''
                INSERT INTO especializaciones (nombre, rol, descripcion)
                VALUES (%s, %s, %s)
                ON CONFLICT (nombre) DO UPDATE
                SET rol = EXCLUDED.rol,
                    descripcion = EXCLUDED.descripcion
                RETURNING id
            '''
            select_especializacion = '''
                SELECT id
                FROM especializaciones
                WHERE nombre = %s
            '''

            insert_skill = '''
                INSERT INTO skills (nombre, categoria)
                VALUES (%s, %s)
                ON CONFLICT (nombre) DO UPDATE
                SET categoria = EXCLUDED.categoria
                RETURNING id
            '''
            select_skill = '''
                SELECT id
                FROM skills
                WHERE nombre = %s
            '''

            relation_sql = '''
                INSERT INTO especializacion_skills (especializacion_id, skill_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            '''

            profile_sql = '''
                INSERT INTO perfiles_egreso (especializacion_id, perfil)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            '''

            for program in data:
                especializacion_id = upsert_get_id(
                    cur,
                    insert_especializacion,
                    select_especializacion,
                    (program.name, program.role, program.description),
                    (program.name,),
                )

                cur.execute('DELETE FROM especializacion_skills WHERE especializacion_id = %s', (especializacion_id,))
                cur.execute('DELETE FROM perfiles_egreso WHERE especializacion_id = %s', (especializacion_id,))

                for skill_name, skill_category in uniq(program.categorized_skills):
                    item_id = upsert_get_id(
                        cur,
                        insert_skill,
                        select_skill,
                        (skill_name, skill_category),
                        (skill_name,),
                    )
                    cur.execute(relation_sql, (especializacion_id, item_id))

                for profile in uniq(program.graduation_profiles):
                    cur.execute(profile_sql, (especializacion_id, profile))


def scrape_tenant(tenant: str) -> None:



    config = get_config(tenant).copy()



    config['tenant'] = tenant







    logging.info('[%s] Iniciando scraping', tenant)



    session = get_session()



    scraped: list[ProgramData] = []







    try:



        links = get_program_links(config['url'], session=session)



        logging.info('[%s] Encontrados %s programas.', tenant, len(links))







        for index, link in enumerate(links, start=1):



            logging.info('[%s] [%s/%s] Scrapeando %s', tenant, index, len(links), link)



            try:



                program = scrape_program(link, session=session)



                scraped.append(program)



                logging.info(



                    '[%s]   -> %s | skills=%s herramientas=%s competencias=%s blandas=%s',



                    tenant,



                    program.name,



                    len(program.technical_skills),



                    len(program.tools),



                    len(program.competencies),



                    len(program.soft_skills),



                )



            except Exception:



                logging.exception('[%s] Error procesando %s', tenant, link)



            time.sleep(REQUEST_DELAY_SECONDS)







        if not scraped:



            raise RuntimeError(f'[{tenant}] No se obtuvo contenido v�lido para insertar.')







        conn = connect_db(config)



        try:



            save_to_db(scraped, conn)



            logging.info('[%s] Guardado completado en %s', tenant, config['db_name'])



        finally:



            conn.close()



    finally:



        session.close()















def main() -> int:



    setup_logging()



    args = parse_args()



    tenants = resolve_tenants(args.tenant)







    if not tenants:



        logging.error('No se indic� ning�n tenant v�lido.')



        return 1







    unknown = [tenant for tenant in tenants if tenant not in TENANTS]



    if unknown:



        logging.error('Tenants desconocidos: %s', ', '.join(unknown))



        tenants = [tenant for tenant in tenants if tenant in TENANTS]







    if not tenants:



        logging.error('No hay tenants v�lidos para procesar.')



        return 1







    failures = 0



    for tenant in tenants:



        try:



            scrape_tenant(tenant)



        except Exception:



            failures += 1



            logging.exception('[%s] Fall� la ejecuci�n del tenant', tenant)







    return 1 if failures else 0











if __name__ == '__main__':



    raise SystemExit(main())







