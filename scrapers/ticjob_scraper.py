from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urljoin, urlparse, urlunparse

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover
    BeautifulSoup = None

try:
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None

try:
    from extract_job_offers_and_skills import build_aggressive_portal_seeds, scrape_portal_jobs
except Exception:  # pragma: no cover
    build_aggressive_portal_seeds = None
    scrape_portal_jobs = None

try:
    from extract_job_offers_and_skills import extract_job_skills as extract_portal_job_skills
except Exception:  # pragma: no cover
    extract_portal_job_skills = None

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


DEFAULT_URL = "https://ticjob.co/es/search"
DEFAULT_SOURCE = "ticjob.co"
DEFAULT_DB_HOST = "127.0.0.1"
DEFAULT_DB_PORT = 5433
DEFAULT_DB_NAME = "cliente_a_db"
DEFAULT_COMPUTRABAJO_URL = "https://co.computrabajo.com/trabajo-de-colombia"
MIN_JOB_DATE = date(2026, 4, 1)
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
OPENAI_BASE_URL = (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
OPENAI_MODEL = (os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()
OPENAI_TIMEOUT = 60
LLM_ENABLED = bool(OPENAI_API_KEY)
ROOT_DIR = Path(__file__).resolve().parent

COMPUTRABAJO_SEARCH_TERMS = [
    "analista de datos",
    "analistas de datos",
    "data analyst",
    "data analytics",
    "analista bi",
    "analista de bi",
    "business intelligence",
    "power bi",
    "analista de informacion",
    "analista de información",
    "analista de negocios",
    "analista de procesos",
    "ingeniero de datos",
    "ingenieros de datos",
    "data engineer",
    "data engineer senior",
    "etl",
    "big data",
    "python",
    "python developer",
    "sql",
    "sql server",
    "devops",
    "devops engineer",
    "qa",
    "qa tester",
    "analista qa",
    "desarrollador backend",
    "backend developer",
    "desarrollador frontend",
    "frontend developer",
    "desarrollador full stack",
    "full stack developer",
    "arquitecto de software",
    "arquitecto de soluciones",
    "analista de sistemas",
    "ingeniero de sistemas",
    "dba",
    "base de datos",
    "ingeniero base de datos",
    "cloud",
    "azure",
    "aws",
    "cloud engineer",
    "cloud architect",
    "tableau",
    "reporting",
    "dashboard",
    "project manager",
    "scrum master",
    "pmo",
    "product owner",
    "gestor de proyectos",
    "ingeniero de software",
    "desarrollador software",
    "software engineer",
    "consultor bi",
    "business analyst",
    "analista funcional",
    "soporte tecnico",
    "infraestructura",
    "ciberseguridad",
    "seguridad informatica",
    "finanzas",
    "contabilidad",
    "tesoreria",
    "recursos humanos",
    "marketing digital",
    "ventas",
    "legal",
    "sector publico",
    "docente",
    "pedagogia",
    "salud",
    "enfermeria",
]

ACADEMIC_PROGRAM_HINTS = {
    "alta gerencia": ["gerencia", "liderazgo", "direccion estrategica", "gerente"],
    "gestion de la seguridad y salud en el trabajo": ["sst", "hseq", "seguridad y salud", "seguridad laboral"],
    "gerencia financiera": ["finanzas", "analista financiero", "tesoreria", "controller"],
    "inteligencia de negocio": ["analista bi", "business intelligence", "power bi", "data analyst"],
    "gestion humana": ["recursos humanos", "talento humano", "rrhh", "nomina"],
    "marketing digital": ["seo", "sem", "social media", "performance marketing"],
    "direccion comercial y ventas": ["ventas", "comercial", "ejecutivo comercial", "account manager"],
    "revisoria fiscal y auditoria de cuentas": ["auditoria", "revisor fiscal", "contabilidad", "impuestos"],
    "direccion y gestion de proyectos": ["project manager", "pmo", "scrum master", "gestor de proyectos"],
    "ingenieria de software": ["desarrollador software", "backend", "frontend", "software engineer"],
    "inteligencia artificial": ["machine learning", "data scientist", "ia", "ml engineer"],
    "seguridad informatica": ["ciberseguridad", "soc", "analista de seguridad", "information security"],
    "visual analytics y big data": ["visual analytics", "big data", "analytics", "reporting"],
    "gestion ambiental y energetica": ["ambiental", "sostenibilidad", "hseq", "eficiencia energetica"],
    "direccion y gestion de tecnologias de la informacion": ["ti", "sistemas", "infraestructura", "soporte tecnico"],
    "derecho de la empresa": ["abogado", "legal", "compliance", "contratos"],
    "gestion publica": ["sector publico", "politica publica", "planeacion", "gestion publica"],
    "derechos humanos": ["derechos humanos", "social", "comunitario", "gestion social"],
    "derecho digital": ["legaltech", "proteccion de datos", "privacidad", "compliance digital"],
    "neuropsicologia y educacion": ["neuropsicologia", "psicopedagogia", "educacion", "orientacion"],
    "educacion y orientacion familiar": ["orientacion familiar", "psicologia educativa", "familia", "acompanamiento"],
    "tic para la enseñanza": ["e-learning", "lms", "aula virtual", "didactica digital"],
    "gerencia educativa": ["coordinador academico", "rector", "direccion academica", "gestion educativa"],
    "educacion inclusiva": ["inclusion educativa", "pedagogia inclusiva", "necesidades educativas", "educacion especial"],
    "pedagogia y docencia": ["docencia", "curriculo", "pedagogia", "planeacion pedagogica"],
    "administracion y gerencia de la salud": ["salud", "gestion hospitalaria", "calidad asistencial", "servicios de salud"],
}

COMPUTRABAJO_LOCATIONS = [
    "bogota-dc",
    "medellin",
    "cali",
    "barranquilla",
    "cartagena",
    "cundinamarca",
    "antioquia",
    "valle-del-cauca",
    "santander",
    "atlantico",
]

MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

TECH_SKILL_CATEGORIES = {
    "sql": "datos",
    "python": "tecnologia",
    "java": "tecnologia",
    "javascript": "tecnologia",
    "typescript": "tecnologia",
    "node.js": "tecnologia",
    "nodejs": "tecnologia",
    "angular": "tecnologia",
    "react": "tecnologia",
    ".net": "tecnologia",
    "net core": "tecnologia",
    "microservices": "tecnologia",
    "api": "tecnologia",
    "rest": "tecnologia",
    "power bi": "datos",
    "tableau": "datos",
    "etl": "datos",
    "big data": "datos",
    "modelado de datos": "datos",
    "integracion de datos": "datos",
    "gobierno de datos": "datos",
    "calidad de datos": "datos",
    "data warehouse": "datos",
    "data lake": "datos",
    "slowly changing dimensions": "datos",
    "itil": "operaciones",
    "itil v3": "operaciones",
    "itil v4": "operaciones",
    "itsm": "operaciones",
    "qa": "calidad",
    "testing": "calidad",
    "pruebas funcionales": "calidad",
    "pruebas no funcionales": "calidad",
    "gestion de bugs": "calidad",
    "selenium": "calidad",
    "cucumber": "calidad",
    "docker": "tecnologia",
    "kubernetes": "tecnologia",
    "git": "tecnologia",
    "jenkins": "tecnologia",
    "cloud": "tecnologia",
    "microsoft azure": "tecnologia",
    "azure devops": "tecnologia",
    "azure": "tecnologia",
    "aws": "tecnologia",
    "gcp": "tecnologia",
    "linux": "tecnologia",
    "oracle": "tecnologia",
    "mysql": "tecnologia",
    "postgresql": "tecnologia",
    "postgres": "tecnologia",
    "sql server": "datos",
    "sap": "negocios",
    "excel": "datos",
    "nosql": "datos",
    "fhir": "salud",
    "hl7": "salud",
    "ehr": "salud",
    "emr": "salud",
    "hipaa": "salud",
    "pedagogia": "educacion",
    "didactica": "educacion",
    "curriculo": "educacion",
    "evaluacion educativa": "educacion",
    "liderazgo": "negocios",
    "estrategia": "negocios",
    "gestión de proyectos": "negocios",
    "gestion de proyectos": "negocios",
    "planificacion": "negocios",
    "riesgos": "negocios",
    "alcance": "negocios",
    "cronograma": "negocios",
    "presupuesto": "negocios",
    "metodologias agiles": "negocios",
    "scrum": "negocios",
    "kanban": "negocios",
    "pmp": "negocios",
    "toma de decisiones": "negocios",
    "comunicacion": "negocios",
    "trabajo en equipo": "negocios",
    "gestion de procesos": "operaciones",
    "gestion operacional": "operaciones",
    "operaciones": "operaciones",
    "logistica": "operaciones",
    "supply chain": "operaciones",
    "servicio al cliente": "operaciones",
}

SKILL_ALIAS_MAP = {
    "sql server": "sql",
    "elt": "etl",
    "grandes volumenes de datos": "big data",
    "grandes volúmenes de datos": "big data",
    "big data": "big data",
    "historizacion": "slowly changing dimensions",
    "historizacion slowly changing dimensions scd": "slowly changing dimensions",
    "slowly changing dimensions scd": "slowly changing dimensions",
    "sql server management studio": "sql server",
    "powerbi": "power bi",
    "excel avanzado": "excel",
    "microsoft azure": "azure",
    "azure devops": "azure devops",
    "node.js": "node.js",
    "node js": "node.js",
    ".net core": ".net core",
    "business intelligence": "business intelligence",
    "bi": "business intelligence",
    "apis": "api",
    "apis rest": "api",
    "rest api": "api",
    "json": "json",
    "xml": "xml",
    "c#": "c#",
    "c sharp": "c#",
    "modelamiento de datos": "modelado de datos",
    "integracion de datos": "integracion de datos",
    "gobierno de datos": "gobierno de datos",
    "calidad de datos": "calidad de datos",
    "data warehouse": "data warehouse",
    "data lake": "data lake",
    "pruebas funcionales": "pruebas funcionales",
    "pruebas no funcionales": "pruebas no funcionales",
    "gestion de bugs": "gestion de bugs",
    "itil v3": "itil v3",
    "itil v4": "itil v4",
    "itsm": "itsm",
}

EXACT_NOISE = {
    "professional",
    "profesional",
    "tecnologo",
    "tecnóloga",
    "tecnologo en",
    "tecnico",
    "técnico",
    "cualquier rama",
    "cualquier area",
    "cualquier área",
    "alternativamente",
    "requisitos",
    "responsabilidades",
    "experiencia",
    "años",
    "anos",
    "mínimo",
    "minimo",
    "grado",
    "titulo",
    "título",
    "liderazgo",
    "comunicación",
    "comunicacion",
    "trabajo en equipo",
    "jornada",
    "horario",
    "beneficios",
    "vacantes",
}

ROLE_HINTS = (
    "analista",
    "ingeniero",
    "desarrollador",
    "arquitecto",
    "técnico",
    "tecnico",
    "lider",
    "líder",
    "coordinador",
    "consultor",
    "devops",
    "qa",
    "data",
    "bi",
    "backend",
    "frontend",
    "soporte",
    "programador",
    "administrador",
    "especialista",
    "gestor",
    "auxiliar",
    "cloud",
    "full stack",
    "fullstack",
)

PHRASE_NOISE = (
    "amplia experiencia",
    "experiencia acreditada",
    "mínimo de",
    "minimo de",
    "años de experiencia",
    "anos de experiencia",
    "documentar problemas de rendimiento",
    "pruebas para identificar",
    "cualquier rama",
)

TECH_SIGNAL_WORDS = {
    "sql",
    "python",
    "java",
    "javascript",
    "typescript",
    "power bi",
    "tableau",
    "etl",
    "big data",
    "data warehouse",
    "data lake",
    "modelado de datos",
    "integracion de datos",
    "gobierno de datos",
    "calidad de datos",
    "docker",
    "kubernetes",
    "git",
    "cloud",
    "azure",
    "aws",
    "gcp",
    "linux",
    "oracle",
    "mysql",
    "postgresql",
    "postgres",
    "sap",
    "itil",
    "itsm",
    "qa",
    "testing",
    "selenium",
    "cucumber",
    "api",
    "rest",
    "json",
    "xml",
    "spark",
    "pyspark",
    "airflow",
    "kafka",
    "hadoop",
    "ssis",
    "ssas",
    "ssrs",
    "dax",
    "excel",
    "node.js",
    "nodejs",
    "angular",
    "react",
    "net",
    "microservices",
    "microservicios",
    "api",
    "rest",
    "jenkins",
}


class VisibleTextParser(HTMLParser):
    BLOCK_TAGS = {
        "article",
        "aside",
        "div",
        "footer",
        "header",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "main",
        "ol",
        "p",
        "section",
        "table",
        "tbody",
        "td",
        "th",
        "thead",
        "tfoot",
        "tr",
        "ul",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: List[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "li":
            self._newline()
            self._chunks.append("* ")
        elif tag == "br":
            self._newline()
        elif tag in self.BLOCK_TAGS:
            self._newline()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag in self.BLOCK_TAGS:
            self._newline()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        self._chunks.append(data)

    def _newline(self) -> None:
        if not self._chunks or not self._chunks[-1].endswith("\n"):
            self._chunks.append("\n")

    def lines(self) -> List[str]:
        raw = unescape("".join(self._chunks))
        cleaned: List[str] = []
        for line in raw.splitlines():
            text = re.sub(r"\s+", " ", repair_text(line)).strip()
            if not text:
                continue
            if text.startswith("* "):
                text = text[2:].strip()
            cleaned.append(text)
        return cleaned


def repair_text(value: Any) -> str:
    return "" if value is None else str(value)


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", repair_text(value))
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_text(value: Any) -> str:
    text = strip_accents(repair_text(value)).lower()
    text = re.sub(r"[^\w\s+#.-]", " ", text)
    text = re.sub(r"[_/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", repair_text(value)).strip()


def canonicalize_skill_name(skill: str) -> str:
    text = normalize_text(skill)
    if not text:
        return ""

    text = text.strip(" .,:;|-")
    text = re.sub(
        r"^(?:analista|analistas|desarrollador|desarrolladora|ingeniero|ingeniera|especialista|consultor|consultora|arquitecto|arquitecta|coordinador|coordinadora|gestor|gestora|profesional|tecnico|tecnica|tecnologo|tecnologa|senior|jr|junior|sr|lead|lider|líder)\s+",
        "",
        text,
    )
    text = re.sub(
        r"^(?:a fines de|a fines|centrado en|centrada en|enfocado en|enfocada en|orientado a|orientada a|manejo de|conocimiento en|experiencia en|dominio de|desarrollo de|habilidades en)\s+",
        "",
        text,
    )
    text = text.strip(" .,:;|-")

    for alias, canonical in sorted(SKILL_ALIAS_MAP.items(), key=lambda item: len(item[0]), reverse=True):
        alias_norm = normalize_text(alias)
        if text == alias_norm:
            return canonical
        if re.search(rf"\b{re.escape(alias_norm)}\b", text):
            return canonical

    if any(sep in text for sep in (" / ", " & ", " + ", " - ")):
        parts = [part.strip(" .,:;|-") for part in re.split(r"\s*(?:/|&|\+|-)\s*", text) if part.strip(" .,:;|-")]
        part_matches: list[str] = []
        for part in parts:
            for alias, canonical in sorted(SKILL_ALIAS_MAP.items(), key=lambda item: len(item[0]), reverse=True):
                alias_norm = normalize_text(alias)
                if part == alias_norm or re.search(rf"\b{re.escape(alias_norm)}\b", part):
                    part_matches.append(canonical)
                    break
            else:
                if part and has_technical_signal(part):
                    part_matches.append(part)
        if part_matches:
            return max(part_matches, key=lambda value: (len(normalize_text(value).split()), len(value)))

    return text


LLM_ALLOWED_CATEGORIES = {
    "datos",
    "tecnologia",
    "negocios",
    "calidad",
    "educacion",
    "salud",
    "operaciones",
}

SKILL_CATEGORY_HINTS = {
    "datos": [
        "sql",
        "power bi",
        "tableau",
        "etl",
        "big data",
        "data warehouse",
        "data lake",
        "modelado de datos",
        "integracion de datos",
        "gobierno de datos",
        "calidad de datos",
        "analitica",
        "analisis de datos",
        "dashboard",
        "reporting",
        "excel",
        "bi",
        "machine learning",
        "data science",
        "visual analytics",
    ],
    "tecnologia": [
        "python",
        "java",
        "javascript",
        "typescript",
        "node.js",
        "react",
        "angular",
        ".net",
        "api",
        "rest",
        "docker",
        "kubernetes",
        "cloud",
        "aws",
        "azure",
        "gcp",
        "git",
        "jenkins",
        "microservices",
        "linux",
        "oracle",
        "mysql",
        "postgres",
    ],
    "negocios": [
        "liderazgo",
        "estrategia",
        "gestion de proyectos",
        "planificacion",
        "riesgos",
        "alcance",
        "cronograma",
        "presupuesto",
        "metodologias agiles",
        "scrum",
        "kanban",
        "pmp",
        "toma de decisiones",
        "comunicacion",
        "trabajo en equipo",
        "presales",
        "ventas",
        "marketing",
        "finanzas",
        "recursos humanos",
    ],
    "calidad": [
        "qa",
        "testing",
        "pruebas funcionales",
        "pruebas no funcionales",
        "gestion de bugs",
        "selenium",
        "cucumber",
        "automatizacion de pruebas",
    ],
    "educacion": [
        "pedagogia",
        "didactica",
        "curriculo",
        "evaluacion educativa",
        "formacion",
        "docencia",
        "ensenanza",
        "aprendizaje",
        "inclusion educativa",
    ],
    "salud": [
        "fhir",
        "hl7",
        "ehr",
        "emr",
        "hipaa",
        "historia clinica",
        "salud publica",
        "atencion clinica",
        "healthtech",
    ],
    "operaciones": [
        "itil",
        "itsm",
        "gestion de procesos",
        "gestion operacional",
        "operaciones",
        "logistica",
        "supply chain",
        "soporte",
        "helpdesk",
        "mesa de ayuda",
        "servicio al cliente",
        "monitoreo",
    ],
}


def normalize_skill_category(category: Any) -> str:
    text = normalize_text(str(category or ""))
    mapping = {
        "management": "negocios",
        "domain specific": "tecnologia",
        "domain_specific": "tecnologia",
        "data analysis": "datos",
        "data_analysis": "datos",
        "business intelligence": "datos",
        "business_intelligence": "datos",
        "soft skill": "negocios",
        "soft_skill": "negocios",
        "datos": "datos",
        "tecnologia": "tecnologia",
        "negocios": "negocios",
        "calidad": "calidad",
        "educacion": "educacion",
        "salud": "salud",
        "operaciones": "operaciones",
    }
    return mapping.get(text, "tecnologia")


def infer_skill_category(skill: str) -> str:
    normalized = normalize_text(skill)
    for category, hints in SKILL_CATEGORY_HINTS.items():
        if any(hint in normalized for hint in hints):
            return category
    return "tecnologia"


def normalize_skill_entry(item: Any) -> Optional[Dict[str, str]]:
    if isinstance(item, dict):
        skill_value = item.get("skill") or item.get("nombre") or item.get("name") or item.get("skill_name") or ""
        category_value = item.get("categoria") or item.get("category") or ""
    else:
        skill_value = item or ""
        category_value = ""

    sanitized = sanitize_skill_candidate(skill_value)
    if sanitized:
        skill = compact_skill_phrase(sanitized)
    else:
        skill = normalize_text(skill_value)
        if not skill or is_noise_skill_candidate(skill):
            return None
        if len(skill.split()) > 3 and skill not in TECH_SKILL_CATEGORIES:
            return None
        if not has_technical_signal(skill) and skill not in TECH_SKILL_CATEGORIES:
            return None
        skill = compact_skill_phrase(skill)

    if not skill:
        return None

    category = normalize_skill_category(category_value) if category_value else infer_skill_category(skill)
    if category not in LLM_ALLOWED_CATEGORIES:
        category = infer_skill_category(skill)

    return {"skill": skill, "categoria": category}


ROLE_ALIAS_MAP = {
    "data analyst": "analista de datos",
    "senior data analyst": "analista de datos",
    "analyst": "analista de datos",
    "analista de inteligencia de negocios": "analista bi",
    "analista intelligence business": "analista bi",
    "business intelligence analyst": "analista bi",
    "inteligencia de negocios": "analista bi",
    "analista bi": "analista bi",
    "software engineer": "ingeniero de software",
    "backend software engineer": "ingeniero de software",
    "backend engineer": "ingeniero de software",
    "full stack engineer": "desarrollador full stack",
    "data engineer": "ingeniero de datos",
    "ingeniero de datos": "ingeniero de datos",
    "data scientist": "cientifico de datos",
    "scientist": "cientifico de datos",
    "backend developer": "desarrollador backend",
    "frontend developer": "desarrollador frontend",
    "full stack developer": "desarrollador full stack",
    "fullstack developer": "desarrollador full stack",
    "full stack": "desarrollador full stack",
    "software architect": "arquitecto software",
    "arquitecto de software": "arquitecto software",
    "solution architect": "arquitecto soluciones",
    "arquitecto de soluciones": "arquitecto soluciones",
    "devops engineer": "ingeniero devops",
    "ingeniero devops": "ingeniero devops",
    "quality assurance": "qa tester",
    "quality assurance tester": "qa tester",
    "qa automation tester": "qa tester",
    "qa automation": "qa tester",
    "qa tester": "qa tester",
    "tester": "qa tester",
    "analista qa": "qa tester",
    "coordinador qa": "qa tester",
    "lider de pruebas": "qa tester",
    "líder de pruebas": "qa tester",
    "soporte helpdesk": "soporte helpdesk",
    "mesa de ayuda": "soporte helpdesk",
    "project manager": "director de proyectos",
    "gestor de proyectos": "director de proyectos",
    "director de proyectos": "director de proyectos",
    "technical lead": "líder técnico",
    "tech lead": "líder técnico",
    "líder técnico": "líder técnico",
}


def normalize_cargo_text(value: str) -> str:
    text = normalize_role_text(value)
    if not text:
        return ""

    text = re.sub(r"^(senior|sr|junior|jr|mid|lead|principal)\s+", "", text)
    text = re.sub(r"\b(back[\s-]?end)\b", "backend", text)
    text = re.sub(r"\b(front[\s-]?end)\b", "frontend", text)

    alias = ROLE_ALIAS_MAP.get(text)
    if alias:
        return alias

    if "full stack" in text or "fullstack" in text:
        return "desarrollador full stack"

    if len(text.split()) > 3:
        compact = " ".join(text.split()[:3]).strip()
        alias = ROLE_ALIAS_MAP.get(compact)
        if alias:
            return alias
        return compact

    return text


def normalize_cargo_entries(items: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for item in items:
        if isinstance(item, dict):
            raw_value = item.get("cargo") or item.get("role") or item.get("titulo") or item.get("name") or item.get("value") or ""
        else:
            raw_value = item if isinstance(item, str) else str(item or "")
        candidate = normalize_cargo_text(raw_value)
        if not candidate:
            continue
        key = normalize_text(candidate)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result


def compact_skill_phrase(skill: str) -> str:
    text = canonicalize_skill_name(skill)
    tokens = normalize_text(text).split()
    if not tokens:
        return ""

    for size in (3, 2, 1):
        prefix = " ".join(tokens[:size]).strip()
        if not prefix:
            continue
        canonical_prefix = canonicalize_skill_name(prefix)
        if not canonical_prefix:
            continue
        if canonical_prefix in TECH_SKILL_CATEGORIES or canonical_prefix in TECH_SIGNAL_WORDS:
            return canonical_prefix
        if canonical_prefix != text and has_technical_signal(canonical_prefix):
            return canonical_prefix

    return text


def normalize_skill_entries(items: Iterable[Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        entry = normalize_skill_entry(item)
        if not entry:
            continue
        key = entry["skill"]
        if key in seen:
            continue
        seen.add(key)
        out.append(entry)
    return out


def has_technical_signal(skill: str) -> bool:
    text = normalize_text(skill)
    if not text:
        return False
    if text in TECH_SIGNAL_WORDS:
        return True
    return any(re.search(rf"\b{re.escape(signal)}\b", text) for signal in TECH_SIGNAL_WORDS)


def is_noise_skill_candidate(skill: str) -> bool:
    text = normalize_text(skill)
    if not text:
        return True
    if text in EXACT_NOISE:
        return True
    if any(phrase in text for phrase in PHRASE_NOISE):
        return True
    if re.fullmatch(r"[\d\s,.-]+", text):
        return True
    if re.search(r"\b(experiencia|experience|años|anos|minimo|mínimo|profesional|tecnico|técnico|tecnologo|tecnóloga)\b", text):
        return True
    return False


def sanitize_skill_candidate(skill: str) -> Optional[str]:
    text = collapse_spaces(repair_text(skill))
    if not text:
        return None

    text = re.sub(r"^[\-\*\u2022]+\s*", "", text)
    text = text.strip(" .,:;|-")
    normalized = normalize_text(text)

    if not normalized or is_noise_skill_candidate(normalized):
        return None

    normalized = re.sub(r"^(conocimiento(?:s)? en|experiencia en|manejo de|dominio de|habilidad en)\s+", "", normalized)
    normalized = re.sub(r"^(buscamos|requerimos|necesitamos|se requiere|se requieren|se busca|se buscan)\s+", "", normalized)
    normalized = normalized.strip(" .,:;|-")

    if not normalized or is_noise_skill_candidate(normalized):
        return None

    canonical = canonicalize_skill_name(normalized)
    if not canonical:
        return None

    if is_noise_skill_candidate(canonical):
        return None

    word_count = len(canonical.split())
    if canonical in TECH_SKILL_CATEGORIES:
        return canonical

    if word_count > 3:
        return None

    if not has_technical_signal(canonical):
        return None

    return canonical


def unique_skill_dicts(skills: Iterable[Dict[str, str]]) -> List[Dict[str, str]]:
    seen: set[str] = set()
    result: List[Dict[str, str]] = []
    for item in skills:
        skill = collapse_spaces(item.get("skill", "")).strip()
        if not skill:
            continue
        key = normalize_text(skill)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def unique_skill_names(skills: Iterable[str]) -> List[str]:
    return [item["skill"] for item in unique_skill_dicts({"skill": skill, "categoria": classify_skill(skill)} for skill in skills)]


def classify_skill(skill: str) -> str:
    canonical = normalize_skill(skill)
    return TECH_SKILL_CATEGORIES.get(canonical, infer_skill_category(canonical))


def normalize_role_text(value: str) -> str:
    text = collapse_spaces(repair_text(value)).strip(" .,:;|-")
    text = normalize_text(text)
    if not text:
        return ""
    text = re.sub(r"^(rol|cargo|puesto|perfil)\s*[:\-]?\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def infer_role_from_job_text(title: str, company: str, body_text: str, location: str = "") -> str:
    text = normalize_text(" ".join([title, company, body_text, location]))
    if not text:
        return normalize_role_text(title)

    role_rules = [
        (("data engineer", "ingeniero de datos"), "ingeniero de datos"),
        (("analista bi", "business intelligence", "inteligencia de negocio", "inteligencia de negocios"), "analista de inteligencia de negocios"),
        (("analista qa", "qa", "quality assurance", "tester", "testing"), "analista qa"),
        (("devops",), "devops engineer"),
        (("ingeniero devops",), "ingeniero devops"),
        (("arquitecto de software", "software architect"), "arquitecto de software"),
        (("desarrollador backend", "backend developer"), "desarrollador backend"),
        (("desarrollador frontend", "frontend developer"), "desarrollador frontend"),
        (("desarrollador full stack", "full stack", "fullstack"), "desarrollador full stack"),
        (("lider tecnico", "líder tecnico", "lead tecnico", "tech lead"), "líder técnico"),
        (("analista de monitoreo",), "analista de monitoreo"),
        (("soporte helpdesk", "helpdesk", "mesa de ayuda"), "soporte helpdesk"),
        (("ingeniero de datos",), "ingeniero de datos"),
        (("arquitecto de soluciones",), "arquitecto de soluciones"),
        (("coordinador qa", "lider de pruebas", "líder de pruebas"), "líder de pruebas"),
    ]
    for hints, role in role_rules:
        if any(hint in text for hint in hints):
            return normalize_cargo_text(role)

    title_norm = normalize_role_text(title)
    if title_norm:
        return title_norm
    return "especialista"


def extract_job_profile_with_llm(
    title: str,
    company: str,
    location: str,
    body_text: str,
    source_url: str,
) -> Optional[dict[str, Any]]:
    if not LLM_ENABLED:
        return None

    prompt_context = "\n".join(
        [
            f"titulo_visible: {title}",
            f"empresa: {company}",
            f"ubicacion: {location}",
            f"fuente: {source_url}",
            f"texto: {body_text}",
        ]
    ).strip()

    system_prompt = (
        "Eres un extractor senior de ofertas laborales en tecnología. "
        "Debes devolver SOLO JSON valido. "
        "Tu tarea es identificar el rol principal del cargo y extraer unicamente skills tecnicas reales y pertinentes. "
        "El rol debe ser corto, profesional y en minusculas. "
        "Las skills deben ser 5 a 8, maximo 3 palabras cada una, sin frases largas, sin ruido, sin habilidades blandas salvo que sean claramente parte del cargo. "
        "Si una skill es equivalente a otra, unificala a la forma estandar de industria."
    )

    user_prompt = (
        "A partir del siguiente texto de una vacante, devuelve este esquema exacto:\n"
        '{\n'
        '  "role": "cargo corto en minusculas",\n'
        '  "skills": ["skill 1", "skill 2", "skill 3"]\n'
        "}\n"
        "Reglas: usa solo skills tecnicas reales, elimina ruido, evita duplicados, y no regreses texto explicativo.\n\n"
        f"{prompt_context}"
    )

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }

    try:
        response = requests.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=OPENAI_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        content = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        if not content:
            return None
        profile = json.loads(content)
        role = normalize_role_text(str(profile.get("role") or profile.get("rol") or ""))
        skills = normalize_skill_entries(profile.get("skills") or [])
        if not role:
            role = infer_role_from_job_text(title, company, body_text)
        if not skills:
            return None
        return {"role": role, "skills": skills}
    except Exception:
        return None


def extract_job_profile_with_llm_v2(
    title: str,
    company: str,
    location: str,
    body_text: str,
    source_url: str,
) -> Optional[dict[str, Any]]:
    if not LLM_ENABLED:
        return None

    prompt_context = "\n".join(
        [
            f"titulo_visible: {title}",
            f"empresa: {company}",
            f"ubicacion: {location}",
            f"fuente: {source_url}",
            f"texto: {body_text}",
        ]
    ).strip()

    system_prompt = (
        "Eres un extractor senior de ofertas laborales. "
        "Debes devolver SOLO JSON valido. "
        "Tu tarea es identificar los cargos laborales y extraer skills reales del mercado laboral. "
        "Cada cargo debe ser corto, profesional, en minusculas y con maximo 3 palabras. "
        "Cada skill debe tener maximo 3 palabras y una categoria obligatoria elegida solo de: datos, tecnologia, negocios, calidad, educacion, salud, operaciones. "
        "No inventes informacion, no uses frases largas, no repitas skills y no agregues texto explicativo."
    )

    user_prompt = (
        "A partir del siguiente texto de una vacante, devuelve este esquema exacto:\n"
        '{\n'
        '  "cargos": ["cargo 1", "cargo 2"],\n'
        '  "skills": [\n'
        '    {"skill": "skill 1", "categoria": "datos"},\n'
        '    {"skill": "skill 2", "categoria": "tecnologia"}\n'
        "  ]\n"
        "}\n"
        "Reglas: usa solo skills reales y pertinentes, elimina ruido, evita duplicados, prioriza precision sobre cantidad y no regreses texto explicativo.\n\n"
        f"{prompt_context}"
    )

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }

    try:
        response = requests.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=OPENAI_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        content = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        if not content:
            return None
        profile = json.loads(content)
        cargos = normalize_cargo_entries(profile.get("cargos") or profile.get("roles") or [])
        fallback_role = normalize_cargo_text(str(profile.get("role") or profile.get("rol") or ""))
        if fallback_role:
            cargos = normalize_cargo_entries([fallback_role] + cargos)
        if not cargos:
            cargos = normalize_cargo_entries([infer_role_from_job_text(title, company, body_text, location)])
        role = cargos[0] if cargos else normalize_cargo_text(infer_role_from_job_text(title, company, body_text, location))
        skills = normalize_skill_entries(profile.get("skills") or [])
        if not skills:
            return None
        return {"role": role, "cargos": cargos or [role], "skills": skills}
    except Exception:
        return None


def split_skill_phrase(phrase: str) -> List[str]:
    text = collapse_spaces(strip_accents(phrase))
    if not text:
        return []
    text = re.sub(r"^(?:metodologia|conocimiento en|experiencia en)\s+", "", text, flags=re.I)
    text = re.sub(r"\(([^)]+)\)", r" \1 ", text)
    parts = re.split(r"\s*(?:,|/|&|\+|\by\b|\bo\b)\s*", text, flags=re.I)
    candidates: List[str] = []
    for part in parts:
        candidate = collapse_spaces(part).strip(" .,:;|-")
        if candidate:
            candidates.append(candidate)
    return candidates


def extract_skill_candidates(text: str) -> List[Dict[str, str]]:
    normalized = normalize_text(text)
    candidates: List[Dict[str, str]] = []

    for alias, canonical in sorted(SKILL_ALIAS_MAP.items(), key=lambda item: len(item[0]), reverse=True):
        alias_norm = normalize_text(alias)
        if alias_norm and re.search(rf"\b{re.escape(alias_norm)}\b", normalized):
            candidates.append({"skill": canonical, "categoria": classify_skill(canonical)})

    for raw_line in re.split(r"[\n•\u2022]+", text):
        chunk = collapse_spaces(raw_line)
        if not chunk:
            continue
        chunk_norm = normalize_text(chunk)
        if not chunk_norm or is_noise_skill_candidate(chunk_norm):
            continue
        if len(chunk_norm.split()) <= 4 and ("," in chunk or "/" in chunk or "&" in chunk or "+" in chunk or " y " in f" {chunk_norm} " or " o " in f" {chunk_norm} "):
            for part in split_skill_phrase(chunk):
                cleaned = sanitize_skill_candidate(part)
                if cleaned:
                    candidates.append({"skill": cleaned, "categoria": classify_skill(cleaned)})
        elif len(chunk_norm.split()) <= 3:
            cleaned = sanitize_skill_candidate(chunk)
            if cleaned:
                candidates.append({"skill": cleaned, "categoria": classify_skill(cleaned)})

    return unique_skill_dicts(candidates)


def extract_skills(text: str) -> List[Dict[str, str]]:
    return extract_skill_candidates(text)


def parse_date(value: str) -> Optional[date]:
    text = collapse_spaces(value)
    if not text:
        return None

    match = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", text)
    if match:
        try:
            return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        except ValueError:
            return None

    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None

    normalized = normalize_text(text)
    if normalized in {"hoy", "today"}:
        return date.today()
    if normalized in {"ayer", "yesterday"}:
        return date.today() - timedelta(days=1)
    relative = re.search(
        r"\bhace\s+(?:(?P<count>\d+)|(?P<word>un|una|uno|unos|unas))\s+"
        r"(?P<unit>dia|dias|semana|semanas|mes|meses|ano|anos|hora|horas|minuto|minutos)\b",
        normalized,
    )
    if relative:
        count = int(relative.group("count") or {"un": 1, "una": 1, "uno": 1, "unos": 3, "unas": 3}.get(relative.group("word") or "", 1))
        unit = relative.group("unit")
        today = date.today()
        if unit.startswith("dia"):
            return today - timedelta(days=count)
        if unit.startswith("semana"):
            return today - timedelta(days=count * 7)
        if unit.startswith("mes"):
            month = today.month - count
            year = today.year
            while month <= 0:
                month += 12
                year -= 1
            return date(year, month, min(today.day, 28))
        if unit.startswith("ano"):
            try:
                return date(today.year - count, today.month, today.day)
            except ValueError:
                return date(today.year - count, today.month, 28)
        if unit.startswith("hora") or unit.startswith("minuto"):
            return today

    month_day_match = re.match(r"^(\d{1,2})\s+de\s+([a-záéíóúüñ]+)$", normalized)
    if month_day_match and month_day_match.group(2) in MONTHS:
        month = MONTHS[month_day_match.group(2)]
        day = int(month_day_match.group(1))
        year = date.today().year
        try:
            parsed = date(year, month, day)
        except ValueError:
            return None
        if parsed > date.today():
            try:
                parsed = date(year - 1, month, day)
            except ValueError:
                return None
        return parsed

    month_year_match = re.match(r"^(\d{1,2})\s+de\s+([a-záéíóúüñ]+)\s+de\s+(\d{4})$", normalized)
    if month_year_match and month_year_match.group(2) in MONTHS:
        try:
            return date(
                int(month_year_match.group(3)),
                MONTHS[month_year_match.group(2)],
                int(month_year_match.group(1)),
            )
        except ValueError:
            return None

    month_match = re.match(r"^(\d{1,2})\s+([a-z]+)\s+(\d{4})$", normalized)
    if month_match and month_match.group(2) in MONTHS:
        try:
            return date(int(month_match.group(3)), MONTHS[month_match.group(2)], int(month_match.group(1)))
        except ValueError:
            return None

    return None


def is_date_line(line: str) -> bool:
    return parse_date(line) is not None


def is_salary_line(line: str) -> bool:
    text = normalize_text(line)
    if not text:
        return False
    if "salario" in text or "salary" in text or "a convenir" in text:
        return True
    if re.search(r"\d[\d.,]*\s*-\s*\d[\d.,]*", text):
        return True
    if re.fullmatch(r"[\d.,\s]+", text):
        return True
    return False


def is_footer_line(line: str) -> bool:
    norm = normalize_text(line)
    return any(
        token in norm
        for token in (
            "vinculado a la red de prestadores",
            "quienes somos",
            "trabajos y proyectos it",
            "informacion legal",
            "condiciones de uso",
            "politica de privacidad",
            "recibe por correo electronico",
            "actualizar alerta de empleo",
            "esta vacante es divulgada a traves de ticjob",
        )
    )


def is_location_line(line: str) -> bool:
    text = collapse_spaces(line)
    norm = normalize_text(text)
    if not text or is_salary_line(text) or is_date_line(text) or is_footer_line(text):
        return False
    if len(text) > 45 or ":" in text:
        return False
    if any(token in norm for token in ("ltda", "sas", "s a s", "inc", "llc", "corp", "corporation")):
        return False
    if any(token in norm for token in ("remoto", "hibrido", "híbrido", "presencial", "bogota", "medellin", "cali", "colombia", "cundinamarca")):
        return True
    words = norm.split()
    return 1 <= len(words) <= 3 and any(char.isalpha() for char in text)


def is_company_line(line: str) -> bool:
    text = collapse_spaces(line)
    norm = normalize_text(text)
    if not text or is_salary_line(text) or is_date_line(text) or is_location_line(text) or is_footer_line(text):
        return False
    if len(text) > 80:
        return False
    if re.search(r"\b(vacante|buscamos|oferta|puesto|perfil|requisitos|responsabilidades)\b", norm):
        return False
    if any(token in norm for token in ("s a s", "sas", "ltda", "sa", "inc", "llc", "corp", "corporation", "group", "soluciones", "consulting", "technology")):
        return True
    return any(char.isupper() for char in text) or len(norm.split()) <= 4


def is_title_candidate(line: str) -> bool:
    text = collapse_spaces(line)
    norm = normalize_text(text)
    if not text or is_date_line(text) or is_salary_line(text) or is_footer_line(text):
        return False
    if len(text) > 120:
        return False
    if len(norm.split()) < 2:
        return False
    if re.search(r"\b(postulate ahora|salary:|esta vacante|esta oferta|vinculado a la red)\b", norm):
        return False
    if any(token in norm for token in ("beneficios", "jornada", "horario", "contrato", "salario", "ubicacion", "ubicación")):
        return False
    if any(token in norm for token in ROLE_HINTS):
        return True
    return any(char.isalpha() for char in text)


def first_date_index(lines: Sequence[str], start: int, stop: int) -> Optional[int]:
    for idx in range(start, min(stop, len(lines))):
        if is_date_line(lines[idx]):
            return idx
    return None


def is_job_start(lines: Sequence[str], index: int) -> bool:
    if not is_title_candidate(lines[index]):
        return False
    return first_date_index(lines, index + 1, index + 8) is not None


def parse_job_block(lines: Sequence[str], start_index: int, end_index: int, source_url: str) -> Optional[Dict[str, Any]]:
    date_idx = first_date_index(lines, start_index + 1, end_index)
    if date_idx is None:
        return None

    posting_date = parse_date(lines[date_idx])
    if posting_date is None or posting_date < MIN_JOB_DATE:
        return None

    title = ""
    for line in lines[start_index:date_idx]:
        if is_title_candidate(line) and not is_company_line(line):
            title = collapse_spaces(line)
            break
    if not title:
        title = collapse_spaces(lines[start_index])

    company = "Unknown"
    for line in lines[start_index + 1 : date_idx]:
        if is_company_line(line) and collapse_spaces(line) != title:
            company = collapse_spaces(line)
            break

    if company == title:
        company = "Unknown"

    location = ""
    for line in lines[date_idx + 1 : end_index]:
        if is_location_line(line):
            location = collapse_spaces(line)
            break

    body_start = date_idx + 1
    if location:
        for idx in range(date_idx + 1, end_index):
            if collapse_spaces(lines[idx]) == location:
                body_start = idx + 1
                break

    body_lines: List[str] = []
    for line in lines[body_start:end_index]:
        text = collapse_spaces(line)
        if not text or is_date_line(text) or is_footer_line(text):
            continue
        if text == title:
            continue
        body_lines.append(text)

    body_text = " ".join(body_lines)
    llm_profile = extract_job_profile_with_llm_v2(title, company, location, body_text, source_url)
    cargos = llm_profile.get("cargos") if llm_profile else []
    role = llm_profile["role"] if llm_profile else infer_role_from_job_text(title, company, body_text, location)
    skill_items = llm_profile["skills"] if llm_profile else extract_skills(" ".join([title, body_text]))

    return {
        "job_title": role,
        "raw_title": title,
        "role": role,
        "cargos": cargos or [role],
        "company": company,
        "location": location,
        "date": posting_date.isoformat(),
        "description": body_text,
        "skills": skill_items,
        "url": source_url,
        "fuente": DEFAULT_SOURCE,
    }


def dedupe_jobs(jobs: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    result: List[Dict[str, Any]] = []
    for job in jobs:
        signature = normalize_text(
            "|".join(
                [
                    job.get("raw_title", job.get("job_title", "")),
                    job.get("company", ""),
                    job.get("date", ""),
                    job.get("url", ""),
                ]
            )
        )
        if signature in seen:
            continue
        seen.add(signature)
        result.append(job)
    return result


class ScrapeResult:
    def __init__(self, jobs: List[Dict[str, Any]], metrics: Dict[str, int]) -> None:
        self.jobs = jobs
        self.metrics = metrics


def fetch_html(url: str, timeout: int = 30, headers: Optional[Dict[str, str]] = None) -> str:
    if requests is None:
        raise RuntimeError("The requests package is required for scraping.")
    response = requests.get(
        url,
        timeout=timeout,
        headers=headers
        or {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
        },
    )
    response.raise_for_status()
    return response.text


def portal_slug(value: str) -> str:
    slug = normalize_text(value)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def portal_slug_variants(value: str) -> List[str]:
    text = normalize_text(value)
    if not text:
        return []

    stopwords = {"de", "del", "la", "el", "y", "en", "para", "con", "al", "a", "los", "las"}
    compact = " ".join(word for word in text.split() if word not in stopwords)
    candidates = [portal_slug(text)]
    if compact and compact != text:
        candidates.append(portal_slug(compact))
    return unique_values(candidates)


def unique_values(items: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(item for item in items if item))


def build_computrabajo_seeds(base_url: str, aggressive: bool = True) -> List[str]:
    parsed_base = base_url.rstrip("/")
    seeds = [
        parsed_base,
        f"{parsed_base}/trabajo-de-colombia",
        f"{parsed_base}/trabajo-de-analista-datos",
        f"{parsed_base}/trabajo-de-analista-data",
        f"{parsed_base}/trabajo-de-data-analyst",
        f"{parsed_base}/trabajo-de-analista-de-datos",
        f"{parsed_base}/trabajo-de-analistas-de-datos",
        f"{parsed_base}/trabajo-de-ingeniero-de-datos",
        f"{parsed_base}/trabajo-de-ingenieros-de-datos",
        f"{parsed_base}/trabajo-de-ingeniero-base-de-datos",
        f"{parsed_base}/trabajo-de-power-bi",
        f"{parsed_base}/trabajo-de-business-intelligence",
        f"{parsed_base}/trabajo-de-analista-bi",
        f"{parsed_base}/trabajo-de-data-engineer",
        f"{parsed_base}/trabajo-de-data-analyst",
        f"{parsed_base}/trabajo-de-devops",
        f"{parsed_base}/trabajo-de-devops-engineer",
        f"{parsed_base}/trabajo-de-qa",
        f"{parsed_base}/trabajo-de-analista-qa",
        f"{parsed_base}/trabajo-de-sql",
        f"{parsed_base}/trabajo-de-python",
        f"{parsed_base}/trabajo-de-analista-de-informacion",
        f"{parsed_base}/trabajo-de-analista-de-negocios",
        f"{parsed_base}/trabajo-de-analista-funcional",
        f"{parsed_base}/trabajo-de-desarrollador-backend",
        f"{parsed_base}/trabajo-de-desarrollador-frontend",
        f"{parsed_base}/trabajo-de-desarrollador-full-stack",
        f"{parsed_base}/trabajo-de-arquitecto-de-software",
        f"{parsed_base}/trabajo-de-arquitecto-de-soluciones",
        f"{parsed_base}/trabajo-de-soporte-tecnico",
        f"{parsed_base}/trabajo-de-infraestructura",
    ]
    if not aggressive:
        return unique_values(seeds)

    for term in COMPUTRABAJO_SEARCH_TERMS:
        for slug in portal_slug_variants(term):
            if not slug:
                continue
            seeds.append(f"{parsed_base}/trabajo-de-{slug}")
            for location in COMPUTRABAJO_LOCATIONS:
                seeds.append(f"{parsed_base}/trabajo-de-{slug}-en-{location}")

    seeds.append(f"{parsed_base}/trabajo-remoto")
    return unique_values(seeds)


PROFILE_EXCLUDE_PREFIXES = (
    "a fin de",
    "al culminar",
    "al egresar",
    "al final",
    "al finalizar",
    "algunos de los cargos",
    "brindando oportunidades",
    "contarás con",
    "consultoria y formacion",
    "consultoria y formación",
    "de la especializacion",
    "de la especialización",
    "de la fundacion universitaria",
    "de la fundación universitaria",
    "dispondrás de",
    "en cargos como",
    "entre los cargos",
    "entre las principales competencias",
    "entre las principales salidas profesionales se destacan",
    "entre las salidas laborales",
    "entre otras funciones de",
    "podras desempenarte",
    "podrás desempeñarte",
    "seras capaz",
    "serás capaz",
)

PROFILE_ROLE_HINTS = {
    "analista",
    "arquitecto",
    "asesor",
    "auditor",
    "capacitador",
    "cfo",
    "ceo",
    "cmo",
    "cno",
    "coordinador",
    "consultor",
    "controller",
    "data scientist",
    "dba",
    "developer",
    "desarrollador",
    "director",
    "docente",
    "especialista",
    "gerente",
    "gestor",
    "ingeniero",
    "lider",
    "líder",
    "pmo",
    "profesional",
    "qa",
    "revisor",
    "soc",
    "supervisor",
    "tecnico",
    "técnico",
}

PROFILE_ACRONYM_ROLES = {"bi", "cfo", "ceo", "cmo", "cno", "cto", "dba", "pmo", "qa", "soc", "sst", "rpa"}


def normalize_profile_term(value: str) -> str:
    raw = collapse_spaces(value)
    if not raw:
        return ""

    normalized = normalize_text(raw)
    if not normalized or len(normalized) > 90:
        return ""

    if any(normalized.startswith(prefix) for prefix in PROFILE_EXCLUDE_PREFIXES):
        return ""

    if not any(hint in normalized for hint in PROFILE_ROLE_HINTS) and normalized not in PROFILE_ACRONYM_ROLES:
        return ""

    if len(normalized.split()) > 8 and normalized not in PROFILE_ACRONYM_ROLES:
        return ""

    return normalized


def load_academic_search_terms_from_db(conn) -> List[str]:
    cur = conn.cursor()
    terms: List[str] = []
    try:
        cur.execute("SELECT DISTINCT nombre FROM especializaciones ORDER BY nombre")
        for (nombre,) in cur.fetchall():
            raw = collapse_spaces(nombre)
            normalized = strip_accents(raw).lower()
            normalized = re.sub(r"^especializacion(?:es)? en\s+", "", normalized)
            normalized = re.sub(r"\s+", " ", normalized).strip()
            if normalized and len(normalized) >= 4:
                terms.append(normalized)
                terms.extend(ACADEMIC_PROGRAM_HINTS.get(normalized, []))

        try:
            cur.execute("SELECT DISTINCT skill FROM vw_programa_skills ORDER BY skill")
            for (skill,) in cur.fetchall():
                candidate = collapse_spaces(skill)
                normalized = strip_accents(candidate).lower()
                normalized = re.sub(r"\s+", " ", normalized).strip()
                if normalized and len(normalized) >= 3:
                    terms.append(normalized)
        except Exception:
            # Algunas bases no tienen la vista y no deben bloquear la carga principal.
            try:
                conn.rollback()
            except Exception:
                pass
            pass
    finally:
        cur.close()

    filtered: List[str] = []
    seen: set[str] = set()
    noise_terms = {
        "gestion",
        "analisis",
        "analitica",
        "general",
        "especializacion",
    }
    for term in terms:
        cleaned = collapse_spaces(term)
        normalized = normalize_text(cleaned)
        if not normalized or normalized in noise_terms:
            continue
        if len(normalized) < 3:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        filtered.append(cleaned)
    return filtered


def load_profile_terms_from_db(conn) -> List[str]:
    cur = conn.cursor()
    terms: List[str] = []
    try:
        cur.execute("SELECT DISTINCT perfil FROM perfiles_egreso ORDER BY perfil")
        for (perfil,) in cur.fetchall():
            candidate = normalize_profile_term(perfil)
            if candidate:
                terms.append(candidate)
    finally:
        cur.close()
    return unique_values(terms)


def job_matches_terms(job: Dict[str, Any], terms: Sequence[str]) -> bool:
    if not terms:
        return True

    haystack = normalize_text(
        " ".join(
            [
                job.get("role", ""),
                job.get("job_title", ""),
                job.get("raw_title", ""),
                job.get("description", ""),
                job.get("company", ""),
                job.get("location", ""),
            ]
        )
    )
    if not haystack:
        return False

    for term in terms:
        candidate = normalize_text(term)
        if not candidate:
            continue
        if candidate in haystack or haystack in candidate:
            return True
    return False


def load_profile_index_from_db(conn) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    index: List[Dict[str, Any]] = []
    seen: set[Tuple[str, int]] = set()
    try:
        cur.execute(
            """
            SELECT p.especializacion_id, e.nombre, p.perfil
            FROM perfiles_egreso p
            JOIN especializaciones e ON e.id = p.especializacion_id
            ORDER BY p.especializacion_id, p.id
            """
        )
        for especializacion_id, especializacion_nombre, perfil in cur.fetchall():
            term = normalize_profile_term(perfil)
            if not term:
                continue
            key = (term, int(especializacion_id))
            if key in seen:
                continue
            seen.add(key)
            index.append(
                {
                    "term": term,
                    "especializacion_id": int(especializacion_id),
                    "especializacion_nombre": collapse_spaces(especializacion_nombre),
                    "perfil": collapse_spaces(perfil),
                }
            )
    finally:
        cur.close()
    return index


def match_job_to_profile(job: Dict[str, Any], profile_index: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not profile_index:
        return None

    haystack = normalize_text(
        " ".join(
            [
                job.get("role", ""),
                job.get("job_title", ""),
                job.get("raw_title", ""),
                job.get("description", ""),
                job.get("company", ""),
                job.get("location", ""),
            ]
        )
    )
    if not haystack:
        return None

    best_entry: Optional[Dict[str, Any]] = None
    best_score = -1
    for entry in profile_index:
        term = normalize_text(entry.get("term", ""))
        if not term:
            continue
        if term in haystack or haystack in term:
            score = len(term.split())
        else:
            term_tokens = [token for token in term.split() if token not in {"de", "del", "la", "el", "y", "en", "para", "con", "a", "al"}]
            if term_tokens and all(token in haystack for token in term_tokens):
                score = len(term_tokens)
            else:
                continue
        if score > best_score:
            best_entry = entry
            best_score = score
    return best_entry


def extract_computrabajo_listing_links(html: str, base_url: str) -> List[str]:
    links: List[str] = []
    if BeautifulSoup is None:
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.I)
        for href in hrefs:
            absolute = urljoin(base_url, href)
            if "/ofertas-de-trabajo/oferta" in absolute:
                links.append(absolute.split("#", 1)[0])
        return unique_values(links)

    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a.get("href") or ""
        absolute = urljoin(base_url, href)
        if "/ofertas-de-trabajo/oferta" in absolute:
            links.append(absolute.split("#", 1)[0])
    return unique_values(links)


def extract_computrabajo_next_links(html: str, base_url: str) -> List[str]:
    links: List[str] = []
    if BeautifulSoup is None:
        for target in re.findall(r'(?:data-path|href)=["\']([^"\']+)["\']', html, flags=re.I):
            absolute = urljoin(base_url, target)
            if "computrabajo.com" in absolute and ("p=" in absolute or "page=" in absolute or "trabajo-de-" in absolute):
                links.append(absolute.split("#", 1)[0])
        return unique_values(links)

    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select("[title='Siguiente'], .buildLink"):
        target = node.get("data-path") or node.get("href")
        if not target:
            continue
        absolute = urljoin(base_url, target)
        if "computrabajo.com" in absolute:
            links.append(absolute.split("#", 1)[0])
    return unique_values(links)


def parse_computrabajo_detail_page(html: str, page_url: str) -> Optional[Dict[str, Any]]:
    lines = html_lines(html)
    if not lines:
        return None

    title = extract_heading_text(html)
    if not title:
        for line in lines:
            normalized = normalize_text(line)
            if normalized and "ofertas de trabajo" not in normalized and "buscar empleos" not in normalized:
                title = collapse_spaces(line)
                break

    if not title:
        return None

    company = "Unknown"
    location = ""
    description_lines: List[str] = []
    description_start = None
    description_end = None
    date_value = None

    for idx, line in enumerate(lines):
        normalized = normalize_text(line)
        if normalized.startswith("descripcion de la oferta"):
            description_start = idx + 1
        elif description_start is not None and description_end is None and normalized in {"requerimientos", "aplicar", "denunciar empleo"}:
            description_end = idx
        if date_value is None:
            parsed_date = parse_date(line)
            if parsed_date is not None and any(token in normalized for token in ("hace", "ayer", "hoy", "actualizada")):
                date_value = parsed_date

    title_idx = None
    normalized_title = normalize_text(title)
    for idx, line in enumerate(lines):
        if normalize_text(line) == normalized_title:
            title_idx = idx
            break

    if title_idx is not None and title_idx + 1 < len(lines):
        next_line = collapse_spaces(lines[title_idx + 1])
        if " - " in next_line:
            company_part, location_part = next_line.split(" - ", 1)
            company = collapse_spaces(company_part)
            location = collapse_spaces(location_part)
        else:
            company = next_line
            if title_idx + 2 < len(lines):
                location = collapse_spaces(lines[title_idx + 2])

    if description_start is None:
        for idx, line in enumerate(lines):
            if normalize_text(line) == "descripcion de la oferta":
                description_start = idx + 1
                break

    if description_start is None:
        description_start = max((title_idx or 0) + 1, 0)
    if description_end is None:
        for idx in range(description_start, len(lines)):
            if normalize_text(lines[idx]) in {"requerimientos", "aplicar", "avisame con ofertas similares"}:
                description_end = idx
                break
    if description_end is None:
        description_end = min(len(lines), description_start + 12)

    for line in lines[description_start:description_end]:
        cleaned = collapse_spaces(line)
        if not cleaned:
            continue
        if parse_date(cleaned) is not None:
            continue
        description_lines.append(cleaned)

    description = collapse_spaces(" ".join(description_lines))
    if not description:
        description = collapse_spaces(" ".join(lines))

    if date_value is None:
        for line in reversed(lines):
            parsed_date = parse_date(line)
            if parsed_date is not None:
                date_value = parsed_date
                break

    if date_value is None:
        return None

    return {
        "job_title": title,
        "company": company,
        "location": location,
        "description": description,
        "date": date_value.isoformat(),
        "url": page_url,
        "fuente": "computrabajo.com",
    }


def html_lines(html: str) -> List[str]:
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        for node in soup(["script", "style", "noscript"]):
            node.decompose()
        text = soup.get_text("\n")
        return [collapse_spaces(line) for line in text.splitlines() if collapse_spaces(line)]

    parser = VisibleTextParser()
    parser.feed(html)
    parser.close()
    return parser.lines()


def extract_heading_text(html: str) -> str:
    if BeautifulSoup is None:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for selector in ("h1", "h2", "h3", "title"):
        for node in soup.find_all(selector):
            text = collapse_spaces(node.get_text(" ", strip=True))
            if text and len(text) <= 120:
                return text
    return ""


def normalize_source_job(
    job: Dict[str, Any],
    source_url: str,
    source_label: str,
    source_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    title = collapse_spaces(
        job.get("role")
        or job.get("job_title")
        or job.get("title")
        or job.get("cargo")
        or job.get("cargo_requerido")
        or ""
    )
    company = collapse_spaces(job.get("company") or job.get("empresa") or "Unknown")
    location = collapse_spaces(job.get("location") or job.get("ubicacion") or "")
    description = collapse_spaces(job.get("description") or job.get("descripcion") or "")
    url = collapse_spaces(job.get("url") or job.get("source_url") or source_url) or source_url
    date_value = job.get("date") or job.get("fecha") or job.get("deadline") or job.get("fecha_publicacion")

    posting_date = parse_date(str(date_value)) if date_value else None
    if posting_date is None or posting_date < MIN_JOB_DATE:
        return None

    llm_profile = extract_job_profile_with_llm_v2(title, company, location, description, url)
    cargos = llm_profile.get("cargos") if llm_profile else []
    role = llm_profile["role"] if llm_profile else infer_role_from_job_text(title, company, description, location)
    if llm_profile:
        skill_items = llm_profile["skills"]
    elif extract_portal_job_skills is not None:
        raw_skill_items = extract_portal_job_skills(
            {
                "job_id": normalize_text("|".join([title, company, url]))[:24] or "job",
                "job_title": title,
                "description": description,
            }
        )
        skill_items = normalize_skill_entries(raw_skill_items)
    else:
        skill_items = extract_skills(" ".join([title, description]))
    normalized_skills = normalize_skill_entries(skill_items)
    if not normalized_skills:
        return None

    return {
        "job_title": role,
        "raw_title": title,
        "role": role,
        "cargos": cargos or [role],
        "company": company,
        "location": location,
        "date": posting_date.isoformat(),
        "description": description,
        "skills": normalized_skills,
        "url": url,
        "fuente": source_label,
        "source_name": source_name or source_label,
    }


def scrape_computrabajo(
    url: str = DEFAULT_COMPUTRABAJO_URL,
    timeout: int = 30,
    max_pages: int = 12,
    aggressive: bool = True,
    seed_terms: Optional[Sequence[str]] = None,
) -> ScrapeResult:
    if requests is None:
        raise RuntimeError("The requests package is required for Computrabajo scraping.")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    }

    parsed = urlparse(url)
    origin = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
    seeds = build_computrabajo_seeds(origin, aggressive=aggressive)
    if seed_terms:
        extra_terms: List[str] = []
        for term in seed_terms:
            cleaned = collapse_spaces(term)
            if not cleaned:
                continue
            extra_terms.append(cleaned)
            extra_terms.extend(ACADEMIC_PROGRAM_HINTS.get(normalize_text(cleaned), []))
        for term in extra_terms:
            for slug in portal_slug_variants(term):
                if not slug:
                    continue
                seeds.append(f"{origin}/trabajo-de-{slug}")
                for location in COMPUTRABAJO_LOCATIONS:
                    seeds.append(f"{origin}/trabajo-de-{slug}-en-{location}")
        seeds = unique_values(seeds)
    queue: List[str] = list(seeds)
    seen_pages: set[str] = set()
    seen_details: set[str] = set()
    jobs: List[Dict[str, Any]] = []
    metrics = {"total_found": 0, "filtered": 0, "discarded": 0}
    page_count = 0
    max_jobs = max_pages * 25 if max_pages > 0 else 500

    while queue and page_count < max_pages and len(seen_details) < max_jobs:
        page_url = queue.pop(0)
        if page_url in seen_pages:
            continue
        seen_pages.add(page_url)
        page_count += 1

        try:
            html = fetch_html(page_url, timeout=timeout, headers=headers)
        except Exception:
            continue

        detail_links = extract_computrabajo_listing_links(html, page_url)
        next_links = extract_computrabajo_next_links(html, page_url)
        for next_url in next_links:
            if next_url not in seen_pages:
                queue.append(next_url)

        if not detail_links and "/ofertas-de-trabajo/oferta" in page_url:
            detail_links = [page_url]

        for detail_url in detail_links:
            if detail_url in seen_details:
                continue
            seen_details.add(detail_url)
            metrics["total_found"] += 1
            try:
                detail_html = fetch_html(detail_url, timeout=timeout, headers=headers)
                raw_job = parse_computrabajo_detail_page(detail_html, detail_url)
                if raw_job is None:
                    metrics["discarded"] += 1
                    continue
                normalized = normalize_source_job(raw_job, detail_url, "computrabajo.com", "Computrabajo Colombia")
                if normalized is None:
                    metrics["discarded"] += 1
                    continue
                metrics["filtered"] += 1
                jobs.append(normalized)
            except Exception:
                metrics["discarded"] += 1

    return ScrapeResult(dedupe_jobs(jobs), metrics)


def parse_spe_detail_page(html: str, page_url: str) -> Optional[Dict[str, Any]]:
    lines = html_lines(html)
    if not lines:
        return None

    title = extract_heading_text(html)
    cargo_requerido = ""
    company = "Unknown"
    location = ""
    deadline = ""
    description_lines: List[str] = []
    capture_description = False

    for idx, line in enumerate(lines):
        normalized = normalize_text(line)
        raw_line = strip_accents(collapse_spaces(line)).lower()
        if not title and line and len(line) <= 120 and normalized not in {"servicio publico de empleo", "ofertas de empleo publicadas"}:
            if line.isupper() or len(line.split()) <= 8:
                title = line
        if "cargo requerido" in raw_line:
            cargo_requerido = collapse_spaces(line.split("|")[-1] if "|" in line else line)
        if raw_line.startswith("empresa:"):
            company = collapse_spaces(line.split("|")[-1] if "|" in line else line)
        if "fecha limite" in normalized or "fecha límite" in normalized:
            deadline = collapse_spaces(line.split("|")[-1] if "|" in line else line)
        if raw_line.startswith("departamento") and "municipio" in raw_line and idx + 1 < len(lines):
            location = collapse_spaces(lines[idx + 1])
        if "lugar de trabajo" in normalized and idx + 1 < len(lines) and not location:
            location = collapse_spaces(lines[idx + 1])

        if "descripcion de la vacante" in normalized:
            capture_description = True
            continue
        if capture_description and (
            "compartir esta vacante" in normalized
            or "mas oportunidades de empleo" in normalized
            or "más oportunidades de empleo" in normalized
            or normalized.startswith("sistema de informacion del servicio de empleo")
        ):
            capture_description = False
        if capture_description:
            description_lines.append(line)

    raw_title = collapse_spaces(cargo_requerido or title)
    if not raw_title:
        raw_title = collapse_spaces(title)
    if not raw_title:
        return None

    date_value = parse_date(deadline) if deadline else None
    if date_value is None:
        return None

    description = collapse_spaces(" ".join(description_lines))
    if not description:
        description = collapse_spaces(" ".join(lines))

    return {
        "job_title": raw_title,
        "company": company,
        "location": location,
        "description": description,
        "date": date_value.isoformat(),
        "url": page_url,
        "fuente": "serviciodeempleo.gov.co",
    }


def scrape_servicio_empleo(
    urls: Sequence[str],
    timeout: int = 30,
) -> ScrapeResult:
    jobs: List[Dict[str, Any]] = []
    metrics = {"total_found": 0, "filtered": 0, "discarded": 0}
    seen: set[str] = set()

    for url in urls:
        clean_url = collapse_spaces(url)
        if not clean_url or clean_url in seen:
            continue
        seen.add(clean_url)
        metrics["total_found"] += 1
        try:
            html = fetch_html(clean_url, timeout=timeout)
            raw_job = parse_spe_detail_page(html, clean_url)
            if raw_job is None:
                metrics["discarded"] += 1
                continue
            normalized = normalize_source_job(raw_job, clean_url, "serviciodeempleo.gov.co", "Servicio de Empleo")
            if normalized is None:
                metrics["discarded"] += 1
                continue
            metrics["filtered"] += 1
            jobs.append(normalized)
        except Exception:
            metrics["discarded"] += 1

    return ScrapeResult(dedupe_jobs(jobs), metrics)


def load_urls_from_file(path_value: Optional[str]) -> List[str]:
    if not path_value:
        return []
    path = Path(path_value)
    if not path.exists():
        return []
    urls: List[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        value = collapse_spaces(line)
        if not value or value.startswith("#"):
            continue
        urls.append(value)
    return urls


def scrape_ticjob(url: str, timeout: int = 30, html: Optional[str] = None) -> ScrapeResult:
    if html is None:
        if requests is None:
            raise RuntimeError("The requests package is required for ticjob scraping.")
        response = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
            },
        )
        response.raise_for_status()
        html = response.text

    parser = VisibleTextParser()
    parser.feed(html)
    parser.close()
    lines = parser.lines()

    start_marker = 0
    for idx, line in enumerate(lines):
        if "empleos encontrados" in normalize_text(line):
            start_marker = idx + 1
            break

    footer_start = len(lines)
    for idx in range(start_marker, len(lines)):
        if is_footer_line(lines[idx]):
            footer_start = idx
            break

    work_lines = lines[start_marker:footer_start]
    starts = [idx for idx in range(len(work_lines)) if is_job_start(work_lines, idx)]

    jobs: List[Dict[str, Any]] = []
    metrics = {"total_found": 0, "filtered": 0, "discarded": 0}

    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(work_lines)
        metrics["total_found"] += 1
        job = parse_job_block(work_lines, start, end, url)
        if job is None:
            metrics["discarded"] += 1
            continue
        metrics["filtered"] += 1
        jobs.append(job)

    return ScrapeResult(dedupe_jobs(jobs), metrics)


def get_job_links(url: str = DEFAULT_URL, timeout: int = 30, html: Optional[str] = None) -> List[Dict[str, Any]]:
    return scrape_ticjob(url, timeout=timeout, html=html).jobs


def scrape_job(url: str, timeout: int = 30, html: Optional[str] = None) -> Optional[Dict[str, Any]]:
    jobs = scrape_ticjob(url, timeout=timeout, html=html).jobs
    return jobs[0] if jobs else None


def normalize_skill(skill: str) -> str:
    cleaned = sanitize_skill_candidate(skill)
    if cleaned:
        return cleaned
    normalized = normalize_text(skill)
    for alias, canonical in sorted(SKILL_ALIAS_MAP.items(), key=lambda item: len(item[0]), reverse=True):
        if normalized == normalize_text(alias):
            return canonical
    return normalized.strip(" .,:;|-")


def connect_postgres(host: str, port: int, dbname: str, user: str, password: str):
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is required. Install psycopg2-binary and try again.")
    return psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)


def stable_job_id(job_data: Dict[str, Any]) -> str:
    source = collapse_spaces(job_data.get("source_name") or job_data.get("source") or job_data.get("fuente") or "")
    url = collapse_spaces(job_data.get("url") or job_data.get("job_url") or "")
    title = collapse_spaces(job_data.get("matched_profile") or job_data.get("role") or job_data.get("job_title") or "")
    seed = "|".join([source, url, title])
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:20]
    return f"jobs:{digest}"


def get_or_create_skill(cur, skill: Any) -> int:
    entry = normalize_skill_entry(skill)
    if not entry:
        raise ValueError("Empty skill name")
    nombre = normalize_skill(entry["skill"])
    if not nombre:
        raise ValueError("Empty skill name")
    categoria = entry["categoria"]
    cur.execute(
        """
        INSERT INTO skills (nombre, categoria)
        VALUES (%s, %s)
        ON CONFLICT (nombre) DO UPDATE
        SET categoria = EXCLUDED.categoria
        """,
        (nombre, categoria),
    )
    cur.execute(
        "SELECT id FROM skills WHERE nombre = %s",
        (nombre,),
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Could not resolve skill id for: {nombre}")
    return int(row[0])


def upsert_empleo(cur, job_data: Dict[str, Any]) -> int:
    empleo_id = stable_job_id(job_data)
    titulo = collapse_spaces(
        job_data.get("matched_profile")
        or job_data.get("role")
        or job_data.get("job_title")
        or job_data.get("title")
        or ""
    )
    descripcion = collapse_spaces(job_data.get("description", ""))
    empresa = collapse_spaces(job_data.get("company", ""))
    ubicacion = collapse_spaces(job_data.get("location", ""))
    fecha_publicacion = collapse_spaces(job_data.get("date", ""))
    fuente = collapse_spaces(job_data.get("fuente") or job_data.get("source") or job_data.get("source_name") or "")
    source_kind = collapse_spaces(job_data.get("source_kind") or job_data.get("source_name") or job_data.get("fuente") or fuente)
    job_url = collapse_spaces(job_data.get("url") or job_data.get("job_url") or "")
    best_program_id = job_data.get("best_program_id")
    best_program = collapse_spaces(job_data.get("best_program") or "")
    best_score = job_data.get("best_score")

    if not titulo:
        raise ValueError("Job title is required")
    if not fecha_publicacion:
        raise ValueError("Job date is required")

    cur.execute(
        """
        SELECT id
        FROM empleos
        WHERE id = %s
        """,
        (empleo_id,),
    )
    row = cur.fetchone()
    if row:
        cur.execute(
            """
            UPDATE empleos
            SET titulo = %s,
                descripcion = %s,
                empresa = %s,
                location = %s,
                fecha = %s,
                source = %s,
                source_kind = %s,
                best_program_id = %s,
                best_program = %s,
                best_score = %s,
                job_url = %s
            WHERE id = %s
            """,
            (
                titulo,
                descripcion,
                empresa,
                ubicacion,
                fecha_publicacion,
                fuente,
                source_kind,
                best_program_id,
                best_program,
                best_score,
                job_url,
                empleo_id,
            ),
        )
        return empleo_id

    cur.execute(
        """
        INSERT INTO empleos (
            id,
            titulo,
            descripcion,
            empresa,
            location,
            fecha,
            source,
            source_kind,
            best_program_id,
            best_program,
            best_score,
            job_url
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            empleo_id,
            titulo,
            descripcion,
            empresa,
            ubicacion,
            fecha_publicacion,
            fuente,
            source_kind,
            best_program_id,
            best_program,
            best_score,
            job_url,
        ),
    )
    return empleo_id


def save_job_to_db(job_data: Dict[str, Any], conn) -> int:
    cur = conn.cursor()
    try:
        empleo_id = upsert_empleo(cur, job_data)

        raw_skills = job_data.get("skills") or []
        unique_skills = normalize_skill_entries(raw_skills)
        cur.execute(
            "DELETE FROM empleo_skills WHERE empleo_id = %s",
            (empleo_id,),
        )
        for skill in unique_skills:
            cur.execute("SAVEPOINT skill_insert")
            try:
                skill_id = get_or_create_skill(cur, skill)
                cur.execute(
                    """
                    INSERT INTO empleo_skills (empleo_id, skill_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (empleo_id, skill_id),
                )
                cur.execute("RELEASE SAVEPOINT skill_insert")
            except Exception:
                cur.execute("ROLLBACK TO SAVEPOINT skill_insert")
                cur.execute("RELEASE SAVEPOINT skill_insert")

        skill_names = [entry["skill"] for entry in unique_skills]
        skills_text = ", ".join(skill_names)
        cur.execute(
            """
            UPDATE empleos
            SET matched_skills = %s,
                missing_skills = %s,
                skills_text = %s,
                matched_skill_count = %s
            WHERE id = %s
            """,
            (skills_text, None, skills_text, len(skill_names), empleo_id),
        )

        conn.commit()
        return empleo_id
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def read_input(path_value: Optional[str]) -> str:
    if not path_value:
        return ""
    return Path(path_value).read_text(encoding="utf-8", errors="replace")


def main(argv: Optional[Sequence[str]] = None) -> int:
    global MIN_JOB_DATE
    parser = argparse.ArgumentParser(description="Scrape job boards and save only technical skills into PostgreSQL.")
    parser.add_argument("--url", default=DEFAULT_URL, help="ticjob search URL.")
    parser.add_argument("--input", default=None, help="Optional local HTML file to parse instead of fetching the URL.")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds.")
    parser.add_argument("--min-date", default=MIN_JOB_DATE.isoformat(), help="Minimum allowed publication date (YYYY-MM-DD).")
    parser.add_argument(
        "--sources",
        default="ticjob,computrabajo,spe",
        help="Comma-separated sources to scrape: ticjob,computrabajo,spe.",
    )
    parser.add_argument(
        "--computrabajo-url",
        default=DEFAULT_COMPUTRABAJO_URL,
        help="Computrabajo seed URL used to expand the crawl.",
    )
    parser.add_argument("--computrabajo-max-pages", type=int, default=12, help="Maximum Computrabajo pages to crawl.")
    parser.add_argument(
        "--spe-url",
        action="append",
        default=[],
        help="Servicio de Empleo detail URL. Repeat for multiple vacancies.",
    )
    parser.add_argument(
        "--spe-urls-file",
        default=None,
        help="Optional text file with one Servicio de Empleo detail URL per line.",
    )
    parser.add_argument("--db-host", default=os.getenv("PGHOST", DEFAULT_DB_HOST))
    parser.add_argument("--db-port", type=int, default=int(os.getenv("PGPORT", str(DEFAULT_DB_PORT))))
    parser.add_argument("--db-name", default=os.getenv("PGDATABASE", DEFAULT_DB_NAME))
    parser.add_argument("--db-user", default=os.getenv("PGUSER", "postgres"))
    parser.add_argument("--db-password", default=os.getenv("PGPASSWORD", ""))
    parser.add_argument("--dry-run", action="store_true", help="Do not write to PostgreSQL, only print summary.")
    args = parser.parse_args(argv)

    try:
        MIN_JOB_DATE = date.fromisoformat(args.min_date)
    except ValueError as exc:
        raise SystemExit(f"Invalid --min-date value: {args.min_date}") from exc

    try:
        conn = connect_postgres(
            host=args.db_host,
            port=args.db_port,
            dbname=args.db_name,
            user=args.db_user,
            password=args.db_password,
        )
    except Exception as exc:
        raise SystemExit(f"Could not connect to PostgreSQL: {exc}") from exc

    academic_terms = load_academic_search_terms_from_db(conn)
    profile_index = load_profile_index_from_db(conn)
    profile_terms = [entry["term"] for entry in profile_index]
    search_terms = unique_values(academic_terms + profile_terms)

    selected_sources = [normalize_text(item) for item in args.sources.split(",") if normalize_text(item)]
    aggregate_jobs: List[Dict[str, Any]] = []
    aggregate_metrics = {"total_found": 0, "filtered": 0, "discarded": 0}
    source_metrics: Dict[str, Dict[str, int]] = {}

    if "ticjob" in selected_sources:
        html = read_input(args.input)
        ticjob_result = scrape_ticjob(args.url, timeout=args.timeout, html=html or None)
        aggregate_jobs.extend(ticjob_result.jobs)
        aggregate_metrics["total_found"] += ticjob_result.metrics["total_found"]
        aggregate_metrics["filtered"] += ticjob_result.metrics["filtered"]
        aggregate_metrics["discarded"] += ticjob_result.metrics["discarded"]
        source_metrics["ticjob"] = ticjob_result.metrics

    if "computrabajo" in selected_sources:
        computrabajo_result = scrape_computrabajo(
            url=args.computrabajo_url,
            timeout=args.timeout,
            max_pages=args.computrabajo_max_pages,
            aggressive=True,
            seed_terms=search_terms,
        )
        aggregate_jobs.extend(computrabajo_result.jobs)
        aggregate_metrics["total_found"] += computrabajo_result.metrics["total_found"]
        aggregate_metrics["filtered"] += computrabajo_result.metrics["filtered"]
        aggregate_metrics["discarded"] += computrabajo_result.metrics["discarded"]
        source_metrics["computrabajo"] = computrabajo_result.metrics

    spe_urls = load_urls_from_file(args.spe_urls_file)
    spe_urls.extend(args.spe_url or [])
    if "spe" in selected_sources:
        if not spe_urls:
            print("Skipping Servicio de Empleo because no --spe-url or --spe-urls-file was provided.", file=sys.stderr)
        spe_result = scrape_servicio_empleo(spe_urls, timeout=args.timeout) if spe_urls else ScrapeResult([], {"total_found": 0, "filtered": 0, "discarded": 0})
        aggregate_jobs.extend(spe_result.jobs)
        aggregate_metrics["total_found"] += spe_result.metrics["total_found"]
        aggregate_metrics["filtered"] += spe_result.metrics["filtered"]
        aggregate_metrics["discarded"] += spe_result.metrics["discarded"]
        source_metrics["spe"] = spe_result.metrics

    profile_discarded = 0
    if profile_index:
        filtered_jobs: List[Dict[str, Any]] = []
        for job in aggregate_jobs:
            match = match_job_to_profile(job, profile_index)
            if not match:
                continue
            job["matched_profile"] = match["term"]
            job["best_program_id"] = match["especializacion_id"]
            job["best_program"] = match["especializacion_nombre"]
            job["best_score"] = 1.0
            filtered_jobs.append(job)
        profile_discarded = len(aggregate_jobs) - len(filtered_jobs)
        aggregate_jobs = filtered_jobs

    saved = 0
    failed = 0
    errors: List[str] = []

    if not args.dry_run:
        try:
            for job in aggregate_jobs:
                try:
                    save_job_to_db(job, conn)
                    saved += 1
                except Exception as exc:
                    failed += 1
                    errors.append(f'{job.get("job_title", "unknown")}: {exc}')
        finally:
            conn.close()
    else:
        conn.close()

    summary = {
        "source_url": args.url,
        "source_urls": {
            "ticjob": args.url if "ticjob" in selected_sources else None,
            "computrabajo": args.computrabajo_url if "computrabajo" in selected_sources else None,
            "spe": spe_urls if "spe" in selected_sources else [],
        },
        "sources": selected_sources,
        "minimum_date": MIN_JOB_DATE.isoformat(),
        "metrics": aggregate_metrics,
        "profile_filter": {
            "matched": len(aggregate_jobs),
            "discarded": profile_discarded,
            "total_profile_terms": len(profile_terms),
        },
        "source_metrics": source_metrics,
        "database": {
            "saved": saved,
            "failed": failed,
            "db_name": args.db_name,
            "db_host": args.db_host,
            "db_port": args.db_port,
        },
        "jobs": dedupe_jobs(aggregate_jobs),
    }
    if errors:
        summary["errors"] = errors

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
