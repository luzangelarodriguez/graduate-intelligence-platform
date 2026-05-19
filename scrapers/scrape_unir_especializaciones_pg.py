from __future__ import annotations

import json
import argparse
import hashlib
import os
import re
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests import Response, Session

import psycopg2

from build_unir_especializaciones_db import PROGRAMS as CURATED_PROGRAMS
from psycopg2 import Error as Psycopg2Error


BASE_URL = 'https://unir.edu.co/especializaciones/'
REQUEST_TIMEOUT = 30
REQUEST_DELAY_SECONDS = 1.0

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}

DB_CONFIG = {
    'host': os.getenv('DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('DB_PORT', '5433')),
    'database': os.getenv('DB_NAME', 'cliente_a_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres'),
}

OPENAI_API_KEY = (os.getenv('OPENAI_API_KEY') or '').strip()
OPENAI_BASE_URL = (os.getenv('OPENAI_BASE_URL') or 'https://api.openai.com/v1').rstrip('/')
OPENAI_MODEL = (os.getenv('OPENAI_MODEL') or 'gpt-4.1-mini').strip()
OPENAI_TIMEOUT = 60
LLM_ENABLED = bool(OPENAI_API_KEY)

TECHNICAL_SKILLS = [
    ('machine learning', ['machine learning', 'aprendizaje automatico', 'aprendizaje automático']),
    ('deep learning', ['deep learning', 'redes neuronales profundas']),
    ('big data', ['big data']),
    ('ciencia de datos', ['ciencia de datos', 'data science']),
    ('programación', ['programacion', 'programación', 'coding', 'development']),
    ('ciberseguridad', ['ciberseguridad', 'seguridad informática', 'seguridad informatica']),
    ('auditoría', ['auditoria', 'auditoría']),
    ('gestión de proyectos', ['gestion de proyectos', 'gestión de proyectos', 'project management']),
    ('analítica de datos', ['analitica de datos', 'analítica de datos', 'data analytics']),
    ('gestión de la calidad', ['gestion de la calidad', 'gestión de la calidad']),
    ('gestión del riesgo', ['gestion del riesgo', 'gestión del riesgo', 'risk management']),
    ('visual analytics', ['visual analytics', 'analitica visual', 'analítica visual']),
    ('sistema de gestión', ['sistema de gestion', 'sistema de gestión']),
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
    ('análisis', ['analisis', 'análisis']),
    ('gestión', ['gestion', 'gestión']),
    ('planificación', ['planificacion', 'planificación']),
    ('estrategia', ['estrategia', 'estratégica', 'estrategico', 'estratégico']),
    ('evaluación', ['evaluacion', 'evaluación']),
    ('diagnóstico', ['diagnostico', 'diagnóstico']),
    ('implementación', ['implementacion', 'implementación']),
    ('diseño', ['diseno', 'diseño']),
    ('interpretación', ['interpretacion', 'interpretación']),
    ('toma de decisiones', ['toma de decisiones']),
    ('seguimiento', ['seguimiento']),
    ('control', ['control']),
    ('formulación', ['formulacion', 'formulación']),
    ('investigación', ['investigacion', 'investigación']),
    ('innovación', ['innovacion', 'innovación']),
]

SOFT_SKILLS = [
    ('liderazgo', ['liderazgo', 'leadership']),
    ('comunicación', ['comunicacion', 'comunicación']),
    ('trabajo en equipo', ['trabajo en equipo']),
    ('negociación', ['negociacion', 'negociación']),
    ('resolución de problemas', ['resolucion de problemas', 'resolución de problemas']),
    ('pensamiento crítico', ['pensamiento critico', 'pensamiento crítico']),
    ('adaptabilidad', ['adaptabilidad', 'adaptacion al cambio', 'adaptación al cambio']),
    ('creatividad', ['creatividad']),
    ('proactividad', ['proactividad']),
    ('colaboración', ['colaboracion', 'colaboración']),
    ('empatía', ['empatia', 'empatía']),
    ('organización', ['organizacion', 'organización']),
]

PROGRAM_SKILL_OVERRIDES = {
    program['name']: program['skills']
    for program in CURATED_PROGRAMS
    if program.get('name') and program.get('skills')
}

PROGRAM_TOOL_OVERRIDES: dict[str, list[str]] = {}

ROLE_OVERRIDES = {
    'Especialización en Dirección y Gestión de Proyectos': 'director de proyectos',
    'Especialización en Gestión de la Seguridad y Salud en el Trabajo': 'gestor sst',
    'Especialización en Neuropsicología y Educación': 'neuropsicólogo educativo',
    'Especialización en Administración y Gerencia de la Salud': 'gerente en salud',
    'Especialización en Alta Gerencia': 'directivo estratégico',
    'Especialización en Visual Analytics y Big Data': 'analista de inteligencia de negocios',
    'Especialización en Gerencia Financiera': 'gerente financiero',
    'Especialización en Gestión Humana': 'gestor de talento humano',
    'Especialización en Inteligencia Artificial': 'especialista en inteligencia artificial',
    'Especialización en Gestión Pública': 'gestor público',
    'Especialización en Seguridad Informática': 'analista de ciberseguridad',
    'Especialización en Ingeniería de Software': 'ingeniero de software',
    'Especialización en Educación y Orientación Familiar': 'orientador familiar',
    'Especialización en Marketing Digital': 'especialista en marketing digital',
    'Especialización en Gerencia Educativa': 'directivo educativo',
    'Especialización en Derechos Humanos': 'gestor de derechos humanos',
    'Especialización en Inteligencia de Negocio': 'analista de inteligencia de negocios',
    'Especialización en Derecho de la Empresa': 'asesor jurídico empresarial',
    'Especialización en Educación Inclusiva': 'gestor de educación inclusiva',
    'Especialización en Gestión Ambiental y Energética': 'gestor ambiental',
    'Especialización en Dirección Comercial y Ventas': 'director comercial',
    'Especialización en Derecho Digital': 'asesor jurídico digital',
    'Especialización en Pedagogía y Docencia': 'docente',
    'Especialización en Dirección y Gestión de Tecnologías de la Información': 'director de ti',
    'Especialización en TIC para la Enseñanza': 'docente en tic',
    'Especialización en Revisoría Fiscal y Auditoría de Cuentas': 'revisor fiscal',
}

STOP_HEADINGS_FOR_DESCRIPTION = [
    'plan de estudios',
    'campo laboral',
    'perfil recomendado',
    'requisitos de acceso',
    'metodologia',
    'metodología',
    'admision',
    'admisión',
]


@dataclass
class ProgramData:
    name: str
    role: str
    description: str
    campo_laboral: str
    plan_estudios: str
    general_text: str
    technical_skills: list[dict[str, str]]
    tools: list[str]
    competencies: list[str]
    soft_skills: list[str]
    source_url: str


def normalize_text(text: str) -> str:
    text = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode('ascii').lower()
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def clean_text(text: str) -> str:
    return normalize_text(text)


def compact_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip()


def uniq(items: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


LLM_ALLOWED_CATEGORIES = {
    'datos',
    'tecnologia',
    'negocios',
    'calidad',
    'educacion',
    'salud',
    'operaciones',
}

SKILL_CATEGORY_HINTS = {
    'datos': [
        'analitica',
        'analisis de datos',
        'estadistica',
        'sql',
        'python',
        'etl',
        'big data',
        'modelado de datos',
        'power bi',
        'tableau',
        'dashboards',
        'kpi',
        'kpis',
        'visual analytics',
        'data science',
    ],
    'tecnologia': [
        'programacion',
        'desarrollo',
        'software',
        'api',
        'cloud',
        'microservicios',
        'docker',
        'kubernetes',
        'java',
        'javascript',
        'typescript',
        'node.js',
        'react',
        'angular',
        'azure',
        'aws',
    ],
    'negocios': [
        'gestion de proyectos',
        'planificacion',
        'riesgos',
        'alcance',
        'cronograma',
        'presupuesto',
        'liderazgo',
        'estrategia',
        'toma de decisiones',
        'marketing',
        'ventas',
        'finanzas',
        'recursos humanos',
    ],
    'calidad': [
        'gestion de la calidad',
        'calidad',
        'auditoria',
        'pruebas funcionales',
        'pruebas no funcionales',
        'testing',
        'qa',
        'selenium',
        'cucumber',
        'gestion de bugs',
    ],
    'educacion': [
        'docencia',
        'pedagogia',
        'didactica',
        'curriculo',
        'aprendizaje',
        'enseñanza',
        'inclusion educativa',
        'evaluacion educativa',
        'orientacion educativa',
        'tic para la enseñanza',
    ],
    'salud': [
        'salud',
        'seguridad y salud en el trabajo',
        'sst',
        'fhir',
        'hl7',
        'ehr',
        'emr',
        'hipaa',
        'historia clinica',
        'salud publica',
    ],
    'operaciones': [
        'gestion',
        'procesos',
        'operaciones',
        'logistica',
        'supply chain',
        'itil',
        'itsm',
        'mesa de ayuda',
        'soporte',
        'monitoreo',
        'gestion ambiental',
        'sostenibilidad',
        'eficiencia energetica',
        'energias renovables',
        'cambio climatico',
        'economia circular',
        'desarrollo sostenible',
        'responsabilidad ambiental',
        'transicion energetica',
    ],
}


def normalize_skill_text(value: str) -> str:
    return normalize_text(value).strip()


def normalize_skill_category(category: Any) -> str:
    text = normalize_skill_text(str(category or ''))
    mapping = {
        'management': 'negocios',
        'domain specific': 'tecnologia',
        'domain_specific': 'tecnologia',
        'data analysis': 'datos',
        'data_analysis': 'datos',
        'business intelligence': 'datos',
        'business_intelligence': 'datos',
        'soft skill': 'negocios',
        'soft_skill': 'negocios',
        'datos': 'datos',
        'tecnologia': 'tecnologia',
        'negocios': 'negocios',
        'calidad': 'calidad',
        'educacion': 'educacion',
        'salud': 'salud',
        'operaciones': 'operaciones',
    }
    return mapping.get(text, 'tecnologia')


def infer_skill_category(skill: str) -> str:
    normalized = normalize_skill_text(skill)
    for category, hints in SKILL_CATEGORY_HINTS.items():
        if any(hint in normalized for hint in hints):
            return category
    if any(term in normalized for term in ('ambiental', 'sostenibilidad', 'energético', 'energetico', 'renovables', 'cambio climatico', 'economia circular')):
        return 'operaciones'
    return 'tecnologia'


def normalize_skill_entry(item: Any) -> Optional[dict[str, str]]:
    if isinstance(item, dict):
        skill_value = item.get('skill') or item.get('nombre') or item.get('name') or ''
        category_value = item.get('categoria') or item.get('category') or ''
    else:
        skill_value = item or ''
        category_value = ''

    skill = normalize_skill_text(str(skill_value))
    if not skill:
        return None

    category = normalize_skill_category(category_value) if category_value else infer_skill_category(skill)
    if any(term in skill for term in ('ambiental', 'sostenibilidad', 'energétic', 'energetic', 'renovables', 'cambio clim', 'economia circular', 'desarrollo sostenible', 'responsabilidad ambiental', 'transicion energetica')):
        category = 'operaciones'
    if category not in LLM_ALLOWED_CATEGORIES:
        category = infer_skill_category(skill)

    return {'skill': skill, 'categoria': category}


def normalize_skill_entries(items: Iterable[Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        entry = normalize_skill_entry(item)
        if not entry:
            continue
        key = entry['skill']
        if key in seen:
            continue
        seen.add(key)
        out.append(entry)
    return out


def first_sentence(text: str) -> str:
    cleaned = re.sub(r'\s+', ' ', (text or '')).strip()
    if not cleaned:
        return ''
    parts = re.split(r'[.\n•\u2022;]+', cleaned)
    for part in parts:
        candidate = part.strip()
        if candidate:
            return candidate
    return cleaned


def extract_role_from_campo_laboral(text: str) -> str:
    cleaned = (text or '').strip()
    if not cleaned:
        return ''

    normalized = normalize_text(cleaned)
    patterns = [
        r'roles?\s+como[:\s]*(.*)',
        r'asumir\s+roles?\s+como[:\s]*(.*)',
        r'podra\s+desempenarse\s+como[:\s]*(.*)',
        r'podras\s+desempenarte\s+como[:\s]*(.*)',
        r'capaz\s+de\s+desempenarse\s+como[:\s]*(.*)',
        r'puestos?\s+como[:\s]*(.*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if not match:
            continue
        fragment = match.group(1).strip()
        fragment = first_sentence(fragment)
        fragment = re.sub(r'\s*\(.*?\)\s*', ' ', fragment)
        fragment = re.split(r'\b(?:y|e)\b|,', fragment, maxsplit=1)[0]
        fragment = re.sub(r'\s+', ' ', fragment).strip(' -:,.')
        if fragment:
            return fragment

    return ''


def infer_role(name: str, description: str, campo_laboral: str, general_text: str) -> str:
    if name in ROLE_OVERRIDES:
        return ROLE_OVERRIDES[name]

    role_from_field = extract_role_from_campo_laboral(campo_laboral)
    if role_from_field:
        normalized = normalize_text(role_from_field)
        if normalized:
            return normalized

    combined = normalize_text(' '.join([name, description, campo_laboral, general_text]))
    inferred_rules = [
        (['direccion y gestion de proyectos', 'gerencia de proyectos'], 'director de proyectos'),
        (['alta gerencia'], 'directivo estrategico'),
        (['visual analytics', 'inteligencia de negocio', 'business intelligence'], 'analista de inteligencia de negocios'),
        (['gerencia financiera'], 'gerente financiero'),
        (['gestion humana'], 'gestor de talento humano'),
        (['inteligencia artificial'], 'especialista en inteligencia artificial'),
        (['gestion publica'], 'gestor publico'),
        (['seguridad informatica'], 'analista de ciberseguridad'),
        (['ingenieria de software'], 'ingeniero de software'),
        (['marketing digital'], 'especialista en marketing digital'),
        (['gerencia educativa'], 'directivo educativo'),
        (['derechos humanos'], 'gestor de derechos humanos'),
        (['derecho de la empresa'], 'asesor juridico empresarial'),
        (['educacion inclusiva'], 'gestor de educacion inclusiva'),
        (['gestion ambiental y energetica'], 'gestor ambiental'),
        (['direccion comercial y ventas'], 'director comercial'),
        (['derecho digital'], 'asesor juridico digital'),
        (['pedagogia y docencia'], 'docente'),
        (['tic para la ense~anza', 'tic para la ensenanza'], 'docente en tic'),
        (['revision fiscal', 'revisoria fiscal'], 'revisor fiscal'),
        (['sst', 'seguridad y salud en el trabajo'], 'gestor sst'),
    ]
    for keywords, role in inferred_rules:
        if any(keyword in combined for keyword in keywords):
            return role

    fallback = first_sentence(name)
    return normalize_text(fallback or name)


def extract_program_profile_with_llm(name: str, description: str, campo_laboral: str, plan_estudios: str, general_text: str) -> Optional[dict[str, Any]]:
    if not LLM_ENABLED:
        return None

    context = '\n'.join(
        [
            f'Nombre del programa: {name}',
            f'Campo laboral: {campo_laboral or ""}',
            f'Plan de estudios: {plan_estudios or ""}',
            f'Descripcion: {description or ""}',
            f'Texto general: {general_text or ""}',
        ]
    ).strip()

    system_prompt = (
        'Eres un experto en analisis curricular y perfiles de egreso. '
        'Debes leer los bloques "Plan de estudios" y "Campo laboral" de un programa academico y devolver SOLO JSON valido. '
        'El campo "rol" debe ser un cargo profesional corto, claro y especifico. '
        'El campo "skills" debe contener entre 5 y 8 habilidades realmente pertinentes al programa. '
        'No incluyas frases largas, requisitos academicos, habilidades blandas irrelevantes, ni tecnologias que no sean nucleo del programa. '
        'Cada skill debe ir con una categoria exacta en: datos, tecnologia, negocios, calidad, educacion, salud u operaciones.'
    )

    user_prompt = (
        'Extrae el rol y las habilidades del programa usando "Campo laboral" para el rol objetivo y "Plan de estudios" para habilidades curriculares. '
        'Devuelve este esquema exacto:\n'
        '{\n'
        '  "rol": "cargo corto en minusculas",\n'
        '  "skills": [\n'
        '    {"skill": "habilidad corta", "categoria": "datos"},\n'
        '    {"skill": "otra habilidad", "categoria": "tecnologia"}\n'
        '  ]\n'
        '}\n'
        'Reglas: usa maximo 8 skills, maximo 3 palabras por skill, todo en minusculas, sin duplicados, sin frases largas.'
        f'\n\n{context}'
    )

    payload = {
        'model': OPENAI_MODEL,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'temperature': 0,
        'response_format': {'type': 'json_object'},
    }

    try:
        response = requests.post(
            f'{OPENAI_BASE_URL}/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=OPENAI_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        content = (((data.get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()
        if not content:
            return None
        profile = json.loads(content)
        role = normalize_skill_text(str(profile.get('rol') or profile.get('role') or ''))
        skills = normalize_skill_entries(profile.get('skills') or [])
        if not role or not skills:
            return None
        return {'role': role, 'skills': skills}
    except Exception:
        return None


def contains_term(normalized_text: str, term: str) -> bool:
    normalized_term = normalize_text(term)
    if not normalized_term:
        return False
    if ' ' in normalized_term:
        return normalized_term in normalized_text
    return re.search(rf'\b{re.escape(normalized_term)}\b', normalized_text) is not None


def match_keywords(text: str, keyword_groups: list[tuple[str, list[str]]]) -> list[str]:
    normalized_text = normalize_text(text)
    matches: list[str] = []
    for canonical, aliases in keyword_groups:
        variants = [canonical] + aliases
        if any(contains_term(normalized_text, variant) for variant in variants):
            matches.append(canonical)
    return uniq(matches)


def get_session() -> Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def fetch_url(session: Session, url: str) -> Response:
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response


def get_program_links() -> list[str]:
    session = get_session()
    response = fetch_url(session, BASE_URL)
    soup = BeautifulSoup(response.text, 'html.parser')

    links: list[str] = []
    seen: set[str] = set()
    base_netloc = urlparse(BASE_URL).netloc

    for anchor in soup.find_all('a', href=True):
        href = urljoin(BASE_URL, anchor['href'])
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
        raise RuntimeError('No se encontraron enlaces de especializaciones en la página principal.')

    return links


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


def heading_matches(heading, terms: list[str]) -> bool:
    normalized_heading = normalize_text(heading.get_text(' ', strip=True))
    return any(term in normalized_heading for term in terms)


def find_section_by_heading(headings, terms: list[str]):
    for heading in headings:
        if heading_matches(heading, terms):
            return heading
    return None


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
    plan_estudios = ''
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

    campo_heading = find_section_by_heading(headings, ['campo laboral', 'salidas profesionales', 'salida profesional'])
    plan_heading = find_section_by_heading(
        headings,
        [
            'plan de estudios',
            'plan estudios',
            'malla curricular',
            'programa academico',
            'programa académico',
            'asignaturas',
            'materias',
            'contenidos',
        ],
    )

    if campo_heading is not None:
        campo_laboral = collect_section_text(campo_heading, stop_level=int(campo_heading.name[1]))
    if plan_heading is not None:
        plan_estudios = collect_section_text(plan_heading, stop_level=int(plan_heading.name[1]))

    return {
        'name': title,
        'description': ' '.join(description_parts).strip(),
        'campo_laboral': campo_laboral,
        'plan_estudios': plan_estudios,
        'general_text': general_text,
    }


def classify_text(text: str) -> dict[str, list[str]]:
    return {
        'skills': match_keywords(text, TECHNICAL_SKILLS),
        'tools': match_keywords(text, TOOLS),
        'competencies': match_keywords(text, COMPETENCIES),
        'soft_skills': match_keywords(text, SOFT_SKILLS),
    }


def merge_classifications(*items: dict[str, list[str]]) -> dict[str, list[str]]:
    merged = {
        'skills': [],
        'tools': [],
        'competencies': [],
        'soft_skills': [],
    }
    for item in items:
        for key in merged:
            merged[key].extend(item.get(key, []) or [])
    return {key: uniq(values) for key, values in merged.items()}


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

        curriculum_text = ' '.join(
            part for part in [sections.get('plan_estudios', ''), sections['description'], name] if part
        )
        labor_text = ' '.join(
            part for part in [sections['campo_laboral'], name] if part
        )
        combined_text = ' '.join(
            part
            for part in [
                sections.get('plan_estudios', ''),
                sections['campo_laboral'],
                sections['description'],
                sections['general_text'],
                name,
            ]
            if part
        )
        classification = merge_classifications(
            classify_text(curriculum_text),
            classify_text(labor_text),
            classify_text(combined_text),
        )
        llm_profile = extract_program_profile_with_llm(
            name.strip(),
            sections['description'],
            sections['campo_laboral'],
            sections.get('plan_estudios', ''),
            sections['general_text'],
        )
        role = llm_profile['role'] if llm_profile else infer_role(name.strip(), sections['description'], sections['campo_laboral'], sections['general_text'])
        curated_skills = PROGRAM_SKILL_OVERRIDES.get(name.strip())
        if curated_skills:
            classification['skills'] = curated_skills
        curated_tools = PROGRAM_TOOL_OVERRIDES.get(name.strip())
        if curated_tools:
            classification['tools'] = curated_tools

        technical_skills = llm_profile['skills'] if llm_profile else normalize_skill_entries(classification['skills'])

        description = sections['description'] or sections.get('plan_estudios', '') or sections['campo_laboral'] or ''

        return ProgramData(
            name=name.strip(),
            role=role,
            description=compact_text(description),
            campo_laboral=compact_text(sections['campo_laboral']),
            plan_estudios=compact_text(sections.get('plan_estudios', '')),
            general_text=compact_text(sections['general_text']),
            technical_skills=technical_skills,
            tools=classification['tools'],
            competencies=classification['competencies'],
            soft_skills=classification['soft_skills'],
            source_url=url,
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


def upsert_get_id(cur, insert_sql: str, select_sql: str, insert_params: tuple, select_params: tuple | None = None) -> int:
    cur.execute(insert_sql, insert_params)
    row = cur.fetchone()
    if row:
        return int(row[0])

    cur.execute(select_sql, select_params or insert_params)
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f'No se pudo recuperar el ID para {insert_params}')
    return int(row[0])


PROGRAM_TRAINING_SYSTEM_PROMPT = (
    'Extrae el perfil curricular de un programa academico. '
    'Usa plan de estudios para habilidades curriculares y campo laboral para rol/salidas. '
    'Devuelve solo JSON valido con: role_target, curriculum_skills, labor_outcomes, quality_flags.'
)


def program_content_hash(program: ProgramData) -> str:
    payload = '|'.join(
        [
            normalize_text(program.name),
            normalize_text(program.description),
            normalize_text(program.campo_laboral),
            normalize_text(program.plan_estudios),
            normalize_text(program.source_url),
        ]
    )
    return hashlib.sha1(payload.encode('utf-8')).hexdigest()


def extract_graduation_profiles(text: str, fallback_role: str = '') -> list[str]:
    cleaned = compact_text(text)
    normalized = normalize_text(cleaned)
    candidates: list[str] = []
    patterns = [
        r'(?:podras|podrá|podra|puedes|puede)\s+(?:desempenarte|desempeñarte|trabajar|laborar)\s+(?:como|en)\s+([^.;:]+)',
        r'(?:roles?|cargos?|salidas?)\s+(?:como|en|profesionales?)[:\s]+([^.;:]+)',
        r'(?:campo laboral|salidas profesionales?)[:\s]+([^.;:]+)',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, cleaned, flags=re.IGNORECASE):
            fragment = match.group(1)
            for part in re.split(r',|;|\sy\s|\so\s|/', fragment):
                value = compact_text(part).strip(' .:-')
                if value and 3 <= len(value) <= 80:
                    candidates.append(value.lower())
    if not candidates and fallback_role:
        candidates.append(fallback_role)
    if not candidates and normalized:
        for role in ROLE_OVERRIDES.values():
            role_key = normalize_text(role)
            if role_key and role_key in normalized:
                candidates.append(role)
    return uniq(candidates)[:8]


def program_training_payload(program: ProgramData) -> dict[str, Any]:
    skill_entries = normalize_skill_entries(program.technical_skills)
    input_text = '\n'.join(
        [
            f'Programa: {program.name}',
            f'Descripcion: {program.description}',
            f'Plan de estudios: {program.plan_estudios}',
            f'Campo laboral: {program.campo_laboral}',
        ]
    ).strip()
    quality_flags: list[str] = []
    if not program.plan_estudios:
        quality_flags.append('missing_plan_estudios')
    if not program.campo_laboral:
        quality_flags.append('missing_campo_laboral')
    if not skill_entries:
        quality_flags.append('no_curriculum_skill_labels')
    return {
        'input_text': input_text,
        'output': {
            'role_target': program.role,
            'curriculum_skills': skill_entries,
            'labor_outcomes': extract_graduation_profiles(program.campo_laboral, program.role),
            'quality_flags': quality_flags,
        },
        'metadata': {
            'program_name': program.name,
            'source_url': program.source_url,
            'content_hash': program_content_hash(program),
            'task': 'program_profile_extraction',
            'label_source': 'weak_supervision',
        },
    }


def program_payload_to_chat_jsonl(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        'messages': [
            {'role': 'system', 'content': PROGRAM_TRAINING_SYSTEM_PROMPT},
            {'role': 'user', 'content': payload['input_text']},
            {'role': 'assistant', 'content': json.dumps(payload['output'], ensure_ascii=False, separators=(',', ':'))},
        ],
        'metadata': payload['metadata'],
    }


def program_payload_to_record_jsonl(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        'input': payload['input_text'],
        'output': payload['output'],
        'metadata': payload['metadata'],
    }


def write_program_jsonl(path: Path, programs: list[ProgramData], jsonl_format: str = 'chat') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as handle:
        for program in programs:
            payload = program_training_payload(program)
            row = program_payload_to_record_jsonl(payload) if jsonl_format == 'record' else program_payload_to_chat_jsonl(payload)
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')


def ensure_ml_schema(cur) -> None:
    script_dir = Path(__file__).resolve().parent
    schema_candidates = [
        script_dir / 'ml_training_schema.sql',
        script_dir.parent / 'ml' / 'ml_training_schema.sql',
    ]
    for schema_path in schema_candidates:
        if schema_path.exists():
            cur.execute(schema_path.read_text(encoding='utf-8'))
            return


def upsert_ml_program_records(cur, data: list[ProgramData]) -> None:
    ensure_ml_schema(cur)
    dataset_version = time.strftime('unir_programs_%Y%m%d')
    cur.execute(
        """
        INSERT INTO ml_training_runs (run_name, task_name, dataset_version, source_config, notes)
        VALUES (%s, %s, %s, %s::jsonb, %s)
        ON CONFLICT (task_name, dataset_version) DO UPDATE
        SET source_config = EXCLUDED.source_config,
            notes = EXCLUDED.notes
        RETURNING id
        """,
        (
            'UNIR programas',
            'program_profile_extraction',
            dataset_version,
            json.dumps({'source': BASE_URL, 'script': Path(__file__).name}, ensure_ascii=False),
            'Programas con plan de estudios, campo laboral y skills curriculares.',
        ),
    )
    run_id = int(cur.fetchone()[0])

    for program in data:
        payload = program_training_payload(program)
        normalized_text = normalize_text(payload['input_text'])
        external_program_id = program.source_url or normalize_text(program.name)
        cur.execute(
            """
            INSERT INTO ml_program_documents (
                run_id,
                external_program_id,
                program_name,
                role_target,
                description,
                campo_laboral,
                plan_estudios,
                general_text,
                source_url,
                normalized_text,
                content_hash,
                raw_payload
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (run_id, external_program_id) DO UPDATE
            SET program_name = EXCLUDED.program_name,
                role_target = EXCLUDED.role_target,
                description = EXCLUDED.description,
                campo_laboral = EXCLUDED.campo_laboral,
                plan_estudios = EXCLUDED.plan_estudios,
                general_text = EXCLUDED.general_text,
                source_url = EXCLUDED.source_url,
                normalized_text = EXCLUDED.normalized_text,
                content_hash = EXCLUDED.content_hash,
                raw_payload = EXCLUDED.raw_payload
            RETURNING id
            """,
            (
                run_id,
                external_program_id,
                program.name,
                program.role,
                program.description,
                program.campo_laboral,
                program.plan_estudios,
                program.general_text,
                program.source_url,
                normalized_text,
                payload['metadata']['content_hash'],
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        document_id = int(cur.fetchone()[0])
        cur.execute('DELETE FROM ml_program_skill_labels WHERE program_document_id = %s', (document_id,))
        for skill in payload['output']['curriculum_skills']:
            cur.execute(
                """
                INSERT INTO ml_program_skill_labels (
                    program_document_id,
                    skill_name,
                    skill_category,
                    evidence_section,
                    label_source,
                    confidence,
                    metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT DO NOTHING
                """,
                (
                    document_id,
                    skill.get('skill', ''),
                    skill.get('categoria', ''),
                    'plan_estudios' if program.plan_estudios else 'description',
                    'weak_supervision',
                    0.85,
                    json.dumps({'program_name': program.name, 'source_url': program.source_url}, ensure_ascii=False),
                ),
            )


def ensure_schema(cur) -> None:
    cur.execute(
        """
        ALTER TABLE especializaciones
        ADD COLUMN IF NOT EXISTS rol TEXT
        """
    )
    cur.execute(
        """
        ALTER TABLE especializaciones
        ADD COLUMN IF NOT EXISTS campo_laboral TEXT
        """
    )
    cur.execute(
        """
        ALTER TABLE especializaciones
        ADD COLUMN IF NOT EXISTS plan_estudios TEXT
        """
    )
    cur.execute(
        """
        ALTER TABLE especializaciones
        ADD COLUMN IF NOT EXISTS general_text TEXT
        """
    )
    cur.execute(
        """
        ALTER TABLE especializaciones
        ADD COLUMN IF NOT EXISTS source_url TEXT
        """
    )


def save_to_postgresql(data: list[ProgramData]) -> None:
    if not data:
        raise ValueError('No hay datos para guardar en PostgreSQL.')

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False

        with conn:
            with conn.cursor() as cur:
                ensure_schema(cur)
                insert_especializacion = '''
                    INSERT INTO especializaciones (nombre, rol, descripcion, campo_laboral, plan_estudios, general_text, source_url)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (nombre) DO UPDATE
                    SET rol = EXCLUDED.rol,
                        descripcion = EXCLUDED.descripcion,
                        campo_laboral = EXCLUDED.campo_laboral,
                        plan_estudios = EXCLUDED.plan_estudios,
                        general_text = EXCLUDED.general_text,
                        source_url = EXCLUDED.source_url
                    RETURNING id
                '''

                category_config = [
                    {
                        'table': 'skills',
                        'relation_table': 'especializacion_skills',
                        'relation_id_col': 'skill_id',
                        'values_key': 'technical_skills',
                    },
                    {
                        'table': 'herramientas',
                        'relation_table': 'especializacion_herramientas',
                        'relation_id_col': 'herramienta_id',
                        'values_key': 'tools',
                    },
                    {
                        'table': 'competencias',
                        'relation_table': 'especializacion_competencias',
                        'relation_id_col': 'competencia_id',
                        'values_key': 'competencies',
                    },
                    {
                        'table': 'habilidades_blandas',
                        'relation_table': 'especializacion_habilidades_blandas',
                        'relation_id_col': 'habilidad_id',
                        'values_key': 'soft_skills',
                    },
                ]

                for program in data:
                    cur.execute(
                        insert_especializacion,
                        (
                            program.name,
                            program.role,
                            program.description,
                            program.campo_laboral,
                            program.plan_estudios,
                            program.general_text,
                            program.source_url,
                        ),
                    )
                    especializacion_id = int(cur.fetchone()[0])

                    for config in category_config:
                        if config['table'] == 'skills':
                            item_insert = '''
                                INSERT INTO skills (nombre, categoria)
                                VALUES (%s, %s)
                                ON CONFLICT (nombre) DO NOTHING
                                RETURNING id
                            '''
                            item_select = '''
                                SELECT id
                                FROM skills
                                WHERE nombre = %s
                            '''
                        else:
                            item_insert = f'''
                                INSERT INTO {config['table']} (nombre)
                                VALUES (%s)
                                ON CONFLICT DO NOTHING
                                RETURNING id
                            '''
                            item_select = f'''
                                SELECT id
                                FROM {config['table']}
                                WHERE nombre = %s
                            '''
                        relation_insert = f'''
                            INSERT INTO {config['relation_table']} (especializacion_id, {config['relation_id_col']})
                            VALUES (%s, %s)
                            ON CONFLICT DO NOTHING
                        '''

                        if config['table'] == 'skills':
                            skill_entries = normalize_skill_entries(getattr(program, config['values_key']))
                            for skill_entry in skill_entries:
                                item_id = upsert_get_id(
                                    cur,
                                    item_insert,
                                    item_select,
                                    (skill_entry['skill'], skill_entry['categoria']),
                                    (skill_entry['skill'],),
                                )
                                cur.execute(relation_insert, (especializacion_id, item_id))
                        else:
                            for value in uniq(getattr(program, config['values_key'])):
                                item_id = upsert_get_id(cur, item_insert, item_select, (value,))
                                cur.execute(relation_insert, (especializacion_id, item_id))

                upsert_ml_program_records(cur, data)

        print(f"OK: guardadas {len(data)} especializaciones en PostgreSQL ({DB_CONFIG['database']}).")
    except Psycopg2Error as exc:
        if conn is not None:
            conn.rollback()
        raise SystemExit(f'Error de PostgreSQL: {exc}') from exc
    except Exception as exc:
        if conn is not None:
            conn.rollback()
        raise SystemExit(f'Error inesperado: {exc}') from exc
    finally:
        if conn is not None:
            conn.close()


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description='Scrapea especializaciones UNIR y prepara datos de programas para PostgreSQL/ML.')
    parser.add_argument('--no-postgres', action='store_true', help='No guarda en PostgreSQL.')
    parser.add_argument('--jsonl-path', type=str, default='program_training_profiles.chat.jsonl', help='Ruta de salida JSONL para entrenamiento de perfiles de programa.')
    parser.add_argument('--jsonl-format', choices=('chat', 'record'), default='chat', help='Formato JSONL para ML.')
    parser.add_argument('--no-jsonl', action='store_true', help='No exporta JSONL de programas.')
    args = parser.parse_args(argv)

    session = get_session()
    scraped: list[ProgramData] = []

    try:
        links = get_program_links()
        print(f'Encontrados {len(links)} programas.')

        for index, url in enumerate(links, start=1):
            print(f'[{index}/{len(links)}] Scrapeando {url}')
            try:
                program = scrape_program(url, session=session)
                scraped.append(program)
                print(
                    f'  -> {program.name} | '
                    f'rol={program.role} '
                    f'skills={len(program.technical_skills)} '
                    f'tools={len(program.tools)} '
                    f'competencias={len(program.competencies)} '
                    f'blandas={len(program.soft_skills)}'
                )
            except Exception as exc:
                print(f'  !! Error: {exc}')
            time.sleep(REQUEST_DELAY_SECONDS)

        if not args.no_postgres:
            save_to_postgresql(scraped)
        if not args.no_jsonl:
            jsonl_path = Path(args.jsonl_path).expanduser().resolve()
            write_program_jsonl(jsonl_path, scraped, jsonl_format=args.jsonl_format)
            print(f'OK: JSONL de programas generado en {jsonl_path}')
    finally:
        session.close()


if __name__ == '__main__':
    main()
