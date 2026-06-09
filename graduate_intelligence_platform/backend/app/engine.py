from __future__ import annotations

import csv
import copy
import hashlib
import os
import re
import unicodedata
from collections import Counter
from datetime import datetime, timedelta
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional, Sequence

from backend.services.domain_taxonomy import (
    DOMAIN_KEYWORDS,
    DOMAIN_LABELS,
    classify_job_key,
    classify_program_key,
    classify_skill_key,
    domain_label,
    domain_weight,
    infer_job_domain,
    infer_program_domain,
    infer_skill_domain,
    normalize_domain_text,
    related_domains,
)


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def months_ago(months: int) -> str:
    delta_days = int(months) * 30
    return (datetime.utcnow() - timedelta(days=delta_days)).replace(microsecond=0).isoformat() + "Z"


def months_from_now(months: int) -> str:
    delta_days = int(months) * 30
    return (datetime.utcnow() + timedelta(days=delta_days)).replace(microsecond=0).isoformat() + "Z"


def repair_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if not any(marker in text for marker in ("Ãƒ", "Ã‚", "Ã¯Â¿Â½", "ï¿½")):
        return text
    attempts = [text]
    for encoding in ("latin1", "cp1252"):
        try:
            attempts.append(text.encode(encoding).decode("utf-8"))
        except UnicodeError:
            continue
    for candidate in attempts[1:]:
        if candidate and not any(marker in candidate for marker in ("Ãƒ", "Ã‚", "Ã¯Â¿Â½", "ï¿½")):
            return candidate
    for candidate in attempts[1:]:
        if candidate:
            return candidate
    return text


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", repair_text(value)).encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_human_text(value: Any) -> str:
    return repair_text(value)


def repair_structure(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: repair_structure(item) for key, item in value.items()}
    if isinstance(value, list):
        return [repair_structure(item) for item in value]
    if isinstance(value, str):
        return repair_text(value)
    return value


def clean_human_text(value: Any) -> str:
    return repair_text(value)


SKILL_CATALOG: List[Dict[str, Any]] = [
    {"name": "SQL", "category": "technical", "aliases": ["sql", "query language", "consultas sql"]},
    {"name": "Python", "category": "technical", "aliases": ["python", "py"]},
    {"name": "Statistics", "category": "technical", "aliases": ["statistics", "estadistica", "estadistica aplicada"]},
    {"name": "Machine Learning", "category": "technical", "aliases": ["machine learning", "ml", "aprendizaje automatico"]},
    {"name": "Data Modeling", "category": "technical", "aliases": ["data modeling", "modelado de datos"]},
    {"name": "Data Analysis", "category": "technical", "aliases": ["data analysis", "analisis de datos", "analytics"]},
    {"name": "Reporting", "category": "tools", "aliases": ["reporting", "reportes", "informes"]},
    {"name": "Visualization", "category": "tools", "aliases": ["visualization", "visualizacion", "data visualization"]},
    {"name": "KPI Design", "category": "technical", "aliases": ["kpi", "kpis", "indicadores", "metric design"]},
    {"name": "ETL", "category": "tools", "aliases": ["etl", "data pipelines", "pipelines"]},
    {"name": "Power BI", "category": "tools", "aliases": ["power bi", "powerbi"]},
    {"name": "Tableau", "category": "tools", "aliases": ["tableau"]},
    {"name": "Dashboarding", "category": "tools", "aliases": ["dashboards", "dashboarding", "tableros"]},
    {"name": "Data Storytelling", "category": "soft", "aliases": ["data storytelling", "storytelling"]},
    {"name": "Communication", "category": "soft", "aliases": ["communication", "comunicacion"]},
    {"name": "Leadership", "category": "soft", "aliases": ["leadership", "liderazgo"]},
    {"name": "Project Management", "category": "soft", "aliases": ["project management", "gestion de proyectos"]},
    {"name": "Strategy", "category": "soft", "aliases": ["strategy", "estrategia"]},
    {"name": "Finance", "category": "technical", "aliases": ["finance", "finanzas", "gerencia financiera"]},
    {"name": "Business Intelligence", "category": "technical", "aliases": ["business intelligence", "inteligencia de negocio", "bi"]},
    {"name": "Legal Analysis", "category": "technical", "aliases": ["legal analysis", "analisis juridico", "analisis legal"]},
    {"name": "Compliance", "category": "technical", "aliases": ["compliance", "cumplimiento", "control interno"]},
    {"name": "Risk Management", "category": "technical", "aliases": ["risk management", "gestion del riesgo", "gestiÃ³n del riesgo"]},
    {"name": "Cybersecurity", "category": "technical", "aliases": ["cybersecurity", "ciberseguridad", "seguridad informatica"]},
    {"name": "Privacy", "category": "technical", "aliases": ["privacy", "privacidad", "proteccion de datos"]},
    {"name": "Public Policy", "category": "technical", "aliases": ["public policy", "politica publica", "polÃ­tica publica"]},
    {"name": "Human Rights", "category": "technical", "aliases": ["human rights", "derechos humanos"]},
    {"name": "Occupational Health", "category": "technical", "aliases": ["occupational health", "salud ocupacional", "sst"]},
    {"name": "Public Health", "category": "technical", "aliases": ["public health", "salud publica", "salud pÃºblica"]},
    {"name": "Health Management", "category": "technical", "aliases": ["health management", "gestion en salud", "gestiÃ³n en salud"]},
    {"name": "Research Methods", "category": "technical", "aliases": ["research methods", "metodologia de investigacion", "metodologia de investigaciÃ³n"]},
    {"name": "Agile", "category": "tools", "aliases": ["agile", "scrum", "kanban"]},
    {"name": "APIs", "category": "technical", "aliases": ["api", "apis", "integracion de sistemas"]},
    {"name": "Git", "category": "tools", "aliases": ["git", "version control", "control de versiones"]},
    {"name": "Testing", "category": "technical", "aliases": ["testing", "qa", "pruebas de software"]},
    {"name": "Cloud", "category": "technical", "aliases": ["cloud", "aws", "azure", "gcp"]},
    {"name": "Big Data", "category": "technical", "aliases": ["big data", "data lake", "data warehouse"]},
    {"name": "Web Analytics", "category": "tools", "aliases": ["web analytics", "analitica web"]},
    {"name": "SEO", "category": "tools", "aliases": ["seo"]},
    {"name": "SEM", "category": "tools", "aliases": ["sem"]},
    {"name": "CRM", "category": "tools", "aliases": ["crm", "customer relationship management"]},
    {"name": "Curriculum Design", "category": "technical", "aliases": ["curriculum design", "diseno curricular", "diseÃ±o curricular"]},
    {"name": "Instructional Design", "category": "technical", "aliases": ["instructional design", "diseno instruccional", "diseÃ±o instruccional"]},
    {"name": "LMS", "category": "tools", "aliases": ["lms", "moodle", "canvas", "blackboard"]},
    {"name": "Evaluation", "category": "technical", "aliases": ["evaluation", "evaluacion", "evaluacion educativa"]},
    {"name": "Learning Analytics", "category": "technical", "aliases": ["learning analytics", "analitica educativa"]},
    {"name": "Digital Marketing", "category": "technical", "aliases": ["digital marketing", "marketing digital"]},
    {"name": "Prompt Engineering", "category": "technical", "aliases": ["prompt engineering", "prompt"]},
    {"name": "Contract Drafting", "category": "technical", "aliases": ["contract drafting", "drafting contracts", "redaccion contractual", "redaccion de contratos"]},
    {"name": "Corporate Governance", "category": "technical", "aliases": ["corporate governance", "gobierno corporativo", "gobernanza corporativa"]},
    {"name": "Regulatory Compliance", "category": "technical", "aliases": ["regulatory compliance", "cumplimiento regulatorio", "cumplimiento normativo"]},
    {"name": "Legal Risk", "category": "technical", "aliases": ["legal risk", "riesgo legal", "riesgo regulatorio"]},
    {"name": "Corporate Law", "category": "technical", "aliases": ["corporate law", "derecho corporativo", "derecho societario"]},
    {"name": "Litigation", "category": "technical", "aliases": ["litigation", "litigio", "pleitos"]},
    {"name": "Negotiation", "category": "soft", "aliases": ["negotiation", "negociacion", "negociacion juridica"]},
    {"name": "Due Diligence", "category": "technical", "aliases": ["due diligence", "debida diligencia"]},
    {"name": "Procurement", "category": "technical", "aliases": ["procurement", "contratacion estatal", "contratacion publica"]},
    {"name": "AML/CFT", "category": "technical", "aliases": ["aml", "cft", "sagrilaft", "sarlaft", "prevencion de lavado"]},
]


SKILL_LOOKUP: Dict[str, Dict[str, str]] = {}
for skill in SKILL_CATALOG:
    for alias in [skill["name"]] + skill["aliases"]:
        SKILL_LOOKUP[normalize_text(alias)] = {"name": skill["name"], "category": skill["category"]}


# Job search terms by domain — used by academic_job_acquisition.py and skill
# filtering logic.  Keyed by domain string matching DOMAIN_KEYWORDS.
DOMAIN_JOB_TERMS: Dict[str, List[str]] = {
    "technology": [
        "software engineer", "data engineer", "data analyst", "data scientist",
        "machine learning engineer", "backend developer", "frontend developer",
        "full stack developer", "devops engineer", "cloud architect",
        "business intelligence analyst", "ETL developer", "AI engineer",
    ],
    "data_analytics": [
        "data analyst", "business intelligence", "analytics engineer",
        "reporting analyst", "power bi developer", "tableau developer",
        "data visualization", "BI consultant",
    ],
    "artificial_intelligence": [
        "machine learning engineer", "AI researcher", "NLP engineer",
        "deep learning engineer", "computer vision engineer",
        "MLOps engineer", "data scientist",
    ],
    "business": [
        "project manager", "product manager", "business analyst",
        "operations manager", "strategy consultant", "financial analyst",
        "management consultant", "gerente de proyectos",
    ],
    "law": [
        "legal analyst", "compliance officer", "corporate lawyer",
        "legal counsel", "regulatory affairs", "abogado corporativo",
    ],
    "education": [
        "instructional designer", "e-learning developer", "academic coordinator",
        "curriculum designer", "educational technologist",
    ],
    "health": [
        "health manager", "clinical coordinator", "quality assurance",
        "hospital administrator", "health data analyst",
    ],
    "criminology": [
        "criminal analyst", "intelligence analyst", "forensic investigator",
        "security analyst", "crime analyst", "investigador criminal",
    ],
}

# Skill priority lists by domain — used to rank and filter skills in
# pertinence scoring.  Keyed by domain string.
DOMAIN_SKILL_PRIORITY: Dict[str, List[str]] = {
    "technology": [
        "Python", "SQL", "Java", "JavaScript", "TypeScript", "Go", "Rust",
        "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Git", "REST API",
        "Microservices", "CI/CD", "Linux", "PostgreSQL", "MongoDB",
    ],
    "data_analytics": [
        "SQL", "Python", "R", "Power BI", "Tableau", "Excel", "ETL",
        "Data Warehouse", "OLAP", "Business Intelligence", "DAX",
        "Data Modeling", "Statistics", "Looker", "Databricks",
    ],
    "artificial_intelligence": [
        "Python", "TensorFlow", "PyTorch", "Scikit-learn", "Keras",
        "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
        "MLflow", "Airflow", "Spark", "SQL", "Statistics",
    ],
    "business": [
        "Project Management", "Scrum", "Agile", "Power BI", "Excel",
        "Leadership", "Strategy", "Finance", "Communication",
        "Data Analysis", "ERP", "CRM", "PMBOK",
    ],
    "law": [
        "Legal Research", "Compliance", "Contract Law", "Regulatory Affairs",
        "Legal Writing", "Litigation", "Corporate Law", "Data Privacy",
    ],
    "education": [
        "Instructional Design", "LMS", "Curriculum Design", "Moodle",
        "E-learning", "Assessment", "Learning Analytics", "SCORM",
    ],
    "health": [
        "Health Management", "Risk Management", "Quality Assurance",
        "Project Management", "Data Analysis", "Compliance", "EHR",
    ],
    "criminology": [
        "Criminal Analysis", "Intelligence Analysis", "Forensics",
        "Risk Assessment", "Data Analysis", "Legal Framework",
        "Investigation Techniques", "GIS",
    ],
}

PROGRAM_BLUEPRINTS: List[Dict[str, str]] = [
    {"name": "EspecializaciÃ³n en Alta Gerencia", "faculty": "Ciencias EconÃ³micas y Administrativas", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en GestiÃ³n de la Seguridad y Salud en el Trabajo", "faculty": "Ciencias de la Salud", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en Gerencia Financiera", "faculty": "Ciencias EconÃ³micas y Administrativas", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en Inteligencia de Negocio", "faculty": "Ciencias EconÃ³micas y Administrativas", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en GestiÃ³n Humana", "faculty": "Ciencias EconÃ³micas y Administrativas", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en Marketing Digital", "faculty": "Ciencias EconÃ³micas y Administrativas", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en DirecciÃ³n Comercial y Ventas", "faculty": "Ciencias EconÃ³micas y Administrativas", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en RevisorÃ­a Fiscal y AuditorÃ­a de Cuentas", "faculty": "Ciencias EconÃ³micas y Administrativas", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en DirecciÃ³n y GestiÃ³n de Proyectos", "faculty": "IngenierÃ­a y TecnologÃ­a", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en IngenierÃ­a de Software", "faculty": "IngenierÃ­a y TecnologÃ­a", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en Inteligencia Artificial", "faculty": "IngenierÃ­a y TecnologÃ­a", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en Seguridad InformÃ¡tica", "faculty": "IngenierÃ­a y TecnologÃ­a", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en Visual Analytics y Big Data", "faculty": "IngenierÃ­a y TecnologÃ­a", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en GestiÃ³n Ambiental y EnergÃ©tica", "faculty": "IngenierÃ­a y TecnologÃ­a", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en DirecciÃ³n y GestiÃ³n de TecnologÃ­as de la InformaciÃ³n", "faculty": "IngenierÃ­a y TecnologÃ­a", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en Derecho de la Empresa", "faculty": "Derecho", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en GestiÃ³n PÃºblica", "faculty": "Derecho", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en Derechos Humanos", "faculty": "Derecho", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en Derecho Digital", "faculty": "Derecho", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en NeuropsicologÃ­a y EducaciÃ³n", "faculty": "EducaciÃ³n", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en EducaciÃ³n y OrientaciÃ³n Familiar", "faculty": "EducaciÃ³n", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en TIC para la EnseÃ±anza", "faculty": "EducaciÃ³n", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en Gerencia Educativa", "faculty": "EducaciÃ³n", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en EducaciÃ³n Inclusiva", "faculty": "EducaciÃ³n", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en PedagogÃ­a y Docencia", "faculty": "EducaciÃ³n", "level": "EspecializaciÃ³n"},
    {"name": "EspecializaciÃ³n en AdministraciÃ³n y Gerencia de la Salud", "faculty": "Ciencias de la Salud", "level": "EspecializaciÃ³n"},
    {"name": "Pregrado en ContadurÃ­a PÃºblica", "faculty": "Ciencias EconÃ³micas y Administrativas", "level": "Pregrado"},
    {"name": "Pregrado en AdministraciÃ³n de Empresas", "faculty": "Ciencias EconÃ³micas y Administrativas", "level": "Pregrado"},
    {"name": "Pregrado en Marketing y Publicidad", "faculty": "Ciencias EconÃ³micas y Administrativas", "level": "Pregrado"},
    {"name": "Pregrado en Negocios Internacionales", "faculty": "Ciencias EconÃ³micas y Administrativas", "level": "Pregrado"},
    {"name": "Pregrado en AdministraciÃ³n de la Seguridad y Salud en el Trabajo", "faculty": "Ciencias de la Salud", "level": "Pregrado"},
    {"name": "Pregrado en IngenierÃ­a InformÃ¡tica", "faculty": "IngenierÃ­a y TecnologÃ­a", "level": "Pregrado"},
    {"name": "Pregrado en Derecho", "faculty": "Derecho", "level": "Pregrado"},
    {"name": "Licenciatura en EducaciÃ³n BÃ¡sica Primaria", "faculty": "EducaciÃ³n", "level": "Pregrado"},
    {"name": "Licenciatura en EducaciÃ³n Infantil", "faculty": "EducaciÃ³n", "level": "Pregrado"},
    {"name": "Pregrado en AdministraciÃ³n en Salud", "faculty": "Ciencias de la Salud", "level": "Pregrado"},
]


def extend_unique(items: List[str], additions: Sequence[str]) -> List[str]:
    seen = {normalize_text(item) for item in items if item}
    for addition in additions:
        canonical = clean_human_text(addition).strip()
        normalized = normalize_text(canonical)
        if canonical and normalized and normalized not in seen:
            items.append(canonical)
            seen.add(normalized)
    return items


def unique(values: Iterable[Any]) -> List[Any]:
    result: List[Any] = []
    seen = set()
    for value in values:
        marker = normalize_text(value) if isinstance(value, str) else value
        if marker in seen:
            continue
        seen.add(marker)
        result.append(value)
    return result


def program_skill_profile(name: str, faculty: str) -> List[str]:
    title = normalize_text(name)
    skills: List[str] = []

    faculty_defaults = {
        "Ciencias EconÃ³micas y Administrativas": ["Leadership", "Project Management", "Communication", "Strategy", "Data Storytelling"],
        "IngenierÃ­a y TecnologÃ­a": ["APIs", "Cloud", "Agile", "Testing", "Project Management"],
        "Derecho": ["Legal Analysis", "Compliance", "Communication", "Evaluation", "Public Policy"],
        "EducaciÃ³n": ["Curriculum Design", "Instructional Design", "LMS", "Evaluation", "Learning Analytics"],
        "Ciencias de la Salud": ["Health Management", "Project Management", "Evaluation", "Communication", "Risk Management"],
    }
    extend_unique(skills, faculty_defaults.get(faculty, []))

    if "alta gerencia" in title:
        extend_unique(skills, ["Strategy", "Leadership", "Project Management", "Data Storytelling"])
    elif "gestion de la seguridad y salud en el trabajo" in title:
        extend_unique(skills, ["Occupational Health", "Risk Management", "Compliance", "Evaluation"])
    elif "gerencia financiera" in title or "contaduria" in title:
        extend_unique(skills, ["Finance", "Data Modeling", "Statistics", "Compliance"])
    elif "inteligencia de negocio" in title or "visual analytics" in title or "big data" in title:
        extend_unique(skills, ["Business Intelligence", "SQL", "Power BI", "Dashboarding", "ETL", "Tableau"])
    elif "gestion humana" in title:
        extend_unique(skills, ["Leadership", "Communication", "Evaluation", "Project Management"])
    elif "marketing digital" in title or "marketing y publicidad" in title:
        extend_unique(skills, ["Digital Marketing", "Web Analytics", "SEO", "SEM", "CRM"])
    elif "direccion comercial y ventas" in title or "negocios internacionales" in title:
        extend_unique(skills, ["CRM", "Communication", "Leadership", "Strategy", "Project Management"])
    elif "revisoria fiscal" in title:
        extend_unique(skills, ["Finance", "Compliance", "Evaluation", "Data Modeling"])
    elif "direccion y gestion de proyectos" in title:
        extend_unique(skills, ["Project Management", "Agile", "Leadership", "Communication"])
    elif "ingenieria de software" in title or "ingenieria informatica" in title:
        extend_unique(skills, ["Python", "APIs", "Git", "Testing", "Cloud", "Agile"])
    elif "inteligencia artificial" in title:
        extend_unique(skills, ["Python", "Machine Learning", "Statistics", "Big Data", "Prompt Engineering"])
    elif "seguridad informatica" in title:
        extend_unique(skills, ["Cybersecurity", "Privacy", "Cloud", "APIs", "Testing"])
    elif "gestion ambiental" in title:
        extend_unique(skills, ["Risk Management", "Compliance", "Project Management", "Evaluation"])
    elif "direccion y gestion de tecnologias" in title:
        extend_unique(skills, ["Cloud", "APIs", "Project Management", "Leadership", "Agile"])
    elif "derecho de la empresa" in title or title == "pregrado en derecho" or "derecho digital" in title:
        extend_unique(skills, ["Legal Analysis", "Compliance", "Privacy", "Public Policy"])
    elif "gestion publica" in title or "derechos humanos" in title:
        extend_unique(skills, ["Public Policy", "Communication", "Evaluation", "Human Rights"])
    elif "neuropsicologia" in title or "orientacion familiar" in title:
        extend_unique(skills, ["Evaluation", "Communication", "Learning Analytics", "Curriculum Design"])
    elif "tic para la ense" in title or "gerencia educativa" in title or "educacion inclusiva" in title or "pedagogia y docencia" in title:
        extend_unique(skills, ["LMS", "Curriculum Design", "Instructional Design", "Learning Analytics", "Evaluation"])
    elif "administracion y gerencia de la salud" in title or "administracion en salud" in title:
        extend_unique(skills, ["Health Management", "Project Management", "Evaluation", "Leadership"])
    elif "administracion de empresas" in title:
        extend_unique(skills, ["Leadership", "Project Management", "Strategy", "Communication"])
    elif "administracion de la seguridad y salud en el trabajo" in title:
        extend_unique(skills, ["Occupational Health", "Risk Management", "Compliance", "Evaluation"])
    elif "licenciatura en educacion basica primaria" in title or "licenciatura en educacion infantil" in title:
        extend_unique(skills, ["Curriculum Design", "Instructional Design", "LMS", "Evaluation"])

    return skills


def program_topic_profile(name: str, faculty: str) -> List[str]:
    title = normalize_text(name)
    topics: List[str] = []
    faculty_topics = {
        "Ciencias EconÃ³micas y Administrativas": ["DirecciÃ³n estratÃ©gica", "GestiÃ³n de negocio", "AnalÃ­tica aplicada", "Liderazgo organizacional"],
        "IngenierÃ­a y TecnologÃ­a": ["Arquitectura digital", "AutomatizaciÃ³n", "Ciclo de vida de productos", "TransformaciÃ³n tecnolÃ³gica"],
        "Derecho": ["Normativa y cumplimiento", "GestiÃ³n pÃºblica y privada", "Derecho digital", "Ã‰tica y regulaciÃ³n"],
        "EducaciÃ³n": ["DidÃ¡ctica", "CurrÃ­culo", "InnovaciÃ³n pedagÃ³gica", "EvaluaciÃ³n del aprendizaje"],
        "Ciencias de la Salud": ["GestiÃ³n en salud", "Calidad y seguridad", "PrevenciÃ³n de riesgos", "Toma de decisiones"],
    }
    topics.extend(faculty_topics.get(faculty, []))
    if "inteligencia artificial" in title:
        extend_unique(topics, ["Modelos de IA", "Procesamiento de lenguaje natural", "VisiÃ³n por computador", "Ciencia de datos"])
    elif "visual analytics" in title or "inteligencia de negocio" in title or "big data" in title:
        extend_unique(topics, ["Modelado de datos", "Dashboards ejecutivos", "Gobierno de datos", "KPIs"])
    elif "marketing" in title:
        extend_unique(topics, ["Customer journey", "Crecimiento digital", "ConversiÃ³n", "ExperimentaciÃ³n"])
    elif "software" in title or "informatica" in title:
        extend_unique(topics, ["Arquitectura de software", "Calidad", "APIs", "Entrega continua"])
    elif "derecho" in title:
        extend_unique(topics, ["Cumplimiento", "RegulaciÃ³n", "Derecho digital", "GestiÃ³n de riesgos legales"])
    elif "educacion" in title:
        extend_unique(topics, ["Aprendizaje", "InclusiÃ³n", "AcompaÃ±amiento docente", "EvaluaciÃ³n"])
    elif "salud" in title:
        extend_unique(topics, ["Calidad asistencial", "GestiÃ³n de servicios", "PrevenciÃ³n", "Bienestar"])
    return topics


def program_description(name: str, faculty: str) -> str:
    title = normalize_text(name)
    if "inteligencia artificial" in title:
        focus = "formaciÃ³n en aprendizaje automÃ¡tico, procesamiento del lenguaje natural y visiÃ³n por computador"
    elif "inteligencia de negocio" in title or "visual analytics" in title or "big data" in title:
        focus = "modelado, visualizaciÃ³n y analÃ­tica avanzada para la toma de decisiones"
    elif "marketing" in title or "publicidad" in title:
        focus = "estrategia comercial, crecimiento digital y mediciÃ³n de desempeÃ±o"
    elif "software" in title or "informatica" in title:
        focus = "desarrollo de soluciones tecnolÃ³gicas, calidad de software y arquitectura digital"
    elif "derecho" in title:
        focus = "anÃ¡lisis jurÃ­dico, cumplimiento normativo y transformaciÃ³n digital"
    elif "educacion" in title:
        focus = "innovaciÃ³n pedagÃ³gica, currÃ­culo y mejora de los procesos de aprendizaje"
    elif "salud" in title:
        focus = "gestiÃ³n de servicios, calidad, seguridad y toma de decisiones en salud"
    else:
        focus = "liderazgo, gestiÃ³n y transformaciÃ³n profesional"
    return f"Programa de {faculty.lower()} de la FundaciÃ³n UNIR Colombia orientado a {focus}."


def _fetch_db_programs() -> List[Dict[str, Any]] | None:
    """Query especializaciones + microcurriculo_skills from the configured DB.

    Returns None on any error so build_programs() can fall back to PROGRAM_BLUEPRINTS.
    Uses RAILWAY_DATABASE_URL / local DB via backend.db (same path as all other repositories).
    """
    try:
        from backend.repositories.base import fetch_all  # local import to avoid circular deps at module load
    except Exception:
        return None
    try:
        # id >= 80: low ids are mojibake duplicates from initial import.
        # detected_domain lives in microcurriculos, not especializaciones —
        # use DISTINCT ON to get one row per especialización.
        rows = fetch_all(
            """
            SELECT
                e.id                          AS especializacion_id,
                e.nombre                      AS nombre_especializacion,
                COALESCE(e.facultad, '')       AS facultad,
                COALESCE(e.nivel, '')          AS nivel,
                COALESCE(e.rol, '')            AS rol,
                COALESCE(e.plan_estudios, '')  AS plan_estudios,
                COALESCE(e.campo_laboral, '')  AS campo_laboral
            FROM especializaciones e
            LEFT JOIN microcurriculos m ON m.specialization_id = e.id
            WHERE e.id >= 80
            ORDER BY e.id
            """
        )
    except Exception:
        return None
    if not rows:
        return None

    # Fetch all microcurriculo skills in one query, keyed by programa name
    try:
        count_rows = fetch_all("SELECT COUNT(*) AS total FROM microcurriculo_skills")
        _skill_total = int((count_rows[0].get("total") or 0) if count_rows else 0)
    except Exception:
        _skill_total = -1

    try:
        # Navigate especializaciones → microcurriculos → microcurriculo_skills
        # so the JOIN is anchored to e.id >= 80 and uses the canonical e.nombre
        # as the program key (same as the rows query above).
        skill_rows = fetch_all(
            """
            SELECT
                e.nombre                                        AS programa,
                COALESCE(NULLIF(ms.skill_normalized, ''),
                         NULLIF(ms.skill_original,   ''))      AS skill_value,
                ms.tipo_skill,
                ms.confidence_score
            FROM especializaciones e
            JOIN microcurriculos m  ON m.specialization_id  = e.id
            JOIN microcurriculo_skills ms ON ms.microcurriculo_id = m.id
            WHERE e.id >= 80
              AND COALESCE(NULLIF(ms.skill_normalized, ''),
                           NULLIF(ms.skill_original,   '')) IS NOT NULL
            ORDER BY ms.confidence_score DESC
            """
        )
    except Exception:
        skill_rows = []

    # Build programa → skills index
    from collections import defaultdict
    micro_index: dict[str, dict[str, list[str]]] = defaultdict(lambda: {
        "technologies": [], "technical_skills": [], "tools": [],
        "platforms": [], "transversal_skills": [], "methodologies": [],
    })
    _tipo_map = {
        "tecnologia": "technologies",
        "skill_tecnica": "technical_skills",
        "herramienta": "tools",
        "plataforma": "platforms",
        "skill_transversal": "transversal_skills",
        "metodologia": "methodologies",
    }
    for sr in skill_rows:
        prog = str(sr.get("programa") or "").strip()
        skill = str(sr.get("skill_normalized") or "").strip()
        tipo = str(sr.get("tipo_skill") or "").strip()
        if not prog or not skill:
            continue
        bucket = _tipo_map.get(tipo, "technical_skills")
        bucket_list = micro_index[normalize_text(prog)][bucket]
        if skill not in bucket_list:
            bucket_list.append(skill)

    programs: List[Dict[str, Any]] = []
    for row in rows:
        name = str(row.get("nombre_especializacion") or "").strip()
        faculty = str(row.get("facultad") or "").strip()
        level = str(row.get("nivel") or "Especialización").strip()
        prog_dict: Dict[str, Any] = {
            "name": name,
            "faculty": faculty,
            "area": faculty,
            "level": level,
        }
        micro_ctx = micro_index.get(normalize_text(name), {})
        prog_dict["microcurriculum_context"] = {
            "technologies": list(micro_ctx.get("technologies", [])),
            "technical_skills": list(micro_ctx.get("technical_skills", [])),
            "tools": list(micro_ctx.get("tools", [])),
            "platforms": list(micro_ctx.get("platforms", [])),
            "transversal_skills": list(micro_ctx.get("transversal_skills", [])),
            "methodologies": list(micro_ctx.get("methodologies", [])),
        }
        prog_dict["curriculum_skills"] = program_skill_profile(name, faculty)
        prog_dict["curriculum_topics"] = program_topic_profile(name, faculty)
        domain_key = program_domain(prog_dict)
        prog_dict["domain_key"] = domain_key
        prog_dict["id"] = int(row.get("especializacion_id") or 0)
        prog_dict["nombre"] = name
        prog_dict["nombre_especializacion"] = name
        programs.append(prog_dict)
    return programs if programs else None


def build_programs() -> List[Dict[str, Any]]:
    db_programs = _fetch_db_programs()
    if db_programs is not None:
        return db_programs
    # Fallback: static PROGRAM_BLUEPRINTS (no DB available)
    programs: List[Dict[str, Any]] = []
    for index, blueprint in enumerate(PROGRAM_BLUEPRINTS, start=1):
        level = blueprint["level"]
        name = blueprint["name"]
        faculty = blueprint["faculty"]
        prog: Dict[str, Any] = {
            "id": index,
            "name": name,
            "nombre": name,
            "nombre_especializacion": name,
            "faculty": faculty,
            "area": faculty,
            "level": level,
            "credits": 24 if level in ("Especialización", "EspecializaciÃ³n") else 160,
            "delivery_mode": "Virtual",
            "description": program_description(name, faculty),
            "curriculum_skills": program_skill_profile(name, faculty),
            "curriculum_topics": program_topic_profile(name, faculty),
            "microcurriculum_context": {
                "technologies": [], "technical_skills": [], "tools": [],
                "platforms": [], "transversal_skills": [], "methodologies": [],
            },
        }
        prog["domain_key"] = program_domain(prog)
        programs.append(prog)
    return programs


def clean_program_description(name: str, faculty: str) -> str:
    name = clean_human_text(name)
    faculty = clean_human_text(faculty)
    title = normalize_text(name)
    if "inteligencia artificial" in title:
        focus = "formaciÃ³n en aprendizaje automÃ¡tico, procesamiento del lenguaje natural y visiÃ³n por computador"
    elif "inteligencia de negocio" in title or "visual analytics" in title or "big data" in title:
        focus = "modelado, visualizaciÃ³n y analÃ­tica avanzada para la toma de decisiones"
    elif "marketing" in title or "publicidad" in title:
        focus = "estrategia comercial, crecimiento digital y mediciÃ³n de desempeÃ±o"
    elif "software" in title or "informatica" in title:
        focus = "desarrollo de soluciones tecnolÃ³gicas, calidad de software y arquitectura digital"
    elif "derecho" in title:
        focus = "anÃ¡lisis jurÃ­dico, cumplimiento normativo y transformaciÃ³n digital"
    elif "educacion" in title:
        focus = "innovaciÃ³n pedagÃ³gica, currÃ­culo y mejora de los procesos de aprendizaje"
    elif "salud" in title:
        focus = "gestiÃ³n de servicios, calidad, seguridad y toma de decisiones en salud"
    else:
        focus = "liderazgo, gestiÃ³n y transformaciÃ³n profesional"
    return clean_human_text(f"Programa de {faculty.lower()} de la FundaciÃ³n UNIR Colombia orientado a {focus}.")


def clean_program_skill_profile(name: str, faculty: str) -> List[str]:
    name = clean_human_text(name)
    faculty = clean_human_text(faculty)
    title = normalize_text(name)
    skills: List[str] = []
    faculty_defaults = {
        "ciencias economicas y administrativas": ["Leadership", "Project Management", "Communication", "Strategy", "Data Storytelling"],
        "ingenieria y tecnologia": ["APIs", "Cloud", "Agile", "Testing", "Project Management"],
        "derecho": ["Legal Analysis", "Compliance", "Communication", "Evaluation", "Public Policy"],
        "educacion": ["Curriculum Design", "Instructional Design", "LMS", "Evaluation", "Learning Analytics"],
        "ciencias de la salud": ["Health Management", "Project Management", "Evaluation", "Communication", "Risk Management"],
    }
    extend_unique(skills, faculty_defaults.get(normalize_text(faculty), []))
    if "alta gerencia" in title:
        extend_unique(skills, ["Strategy", "Leadership", "Project Management", "Data Storytelling"])
    elif "gestion de la seguridad y salud en el trabajo" in title:
        extend_unique(skills, ["Occupational Health", "Risk Management", "Compliance", "Evaluation"])
    elif "gerencia financiera" in title or "contaduria" in title:
        extend_unique(skills, ["Finance", "Data Modeling", "Statistics", "Compliance"])
    elif "inteligencia de negocio" in title or "visual analytics" in title or "big data" in title:
        extend_unique(skills, ["Business Intelligence", "SQL", "Power BI", "Dashboarding", "ETL", "Tableau"])
    elif "gestion humana" in title:
        extend_unique(skills, ["Leadership", "Communication", "Evaluation", "Project Management"])
    elif "marketing digital" in title or "marketing y publicidad" in title:
        extend_unique(skills, ["Digital Marketing", "Web Analytics", "SEO", "SEM", "CRM"])
    elif "direccion comercial y ventas" in title or "negocios internacionales" in title:
        extend_unique(skills, ["CRM", "Communication", "Leadership", "Strategy", "Project Management"])
    elif "revisoria fiscal" in title:
        extend_unique(skills, ["Finance", "Compliance", "Evaluation", "Data Modeling"])
    elif "direccion y gestion de proyectos" in title:
        extend_unique(skills, ["Project Management", "Agile", "Leadership", "Communication"])
    elif "ingenieria de software" in title or "ingenieria informatica" in title:
        extend_unique(skills, ["Python", "APIs", "Git", "Testing", "Cloud", "Agile"])
    elif "inteligencia artificial" in title:
        extend_unique(skills, ["Python", "Machine Learning", "Statistics", "Big Data", "Prompt Engineering"])
    elif "seguridad informatica" in title:
        extend_unique(skills, ["Cybersecurity", "Privacy", "Cloud", "APIs", "Testing"])
    elif "gestion ambiental" in title:
        extend_unique(skills, ["Risk Management", "Compliance", "Project Management", "Evaluation"])
    elif "direccion y gestion de tecnologias" in title:
        extend_unique(skills, ["Cloud", "APIs", "Project Management", "Leadership", "Agile"])
    elif "derecho de la empresa" in title or "derecho digital" in title or normalize_text(name) == "pregrado en derecho":
        extend_unique(
            skills,
            [
                "Legal Analysis",
                "Compliance",
                "Regulatory Compliance",
                "Corporate Governance",
                "Contract Drafting",
                "Legal Risk",
                "Privacy",
                "Public Policy",
                "Corporate Law",
                "Due Diligence",
                "Procurement",
                "AML/CFT",
                "Negotiation",
                "Litigation",
            ],
        )
    elif "gestion publica" in title or "derechos humanos" in title:
        extend_unique(skills, ["Public Policy", "Communication", "Evaluation", "Human Rights"])
    elif "neuropsicologia" in title or "orientacion familiar" in title:
        extend_unique(skills, ["Evaluation", "Communication", "Learning Analytics", "Curriculum Design"])
    elif "tic para la ensenanza" in title or "gerencia educativa" in title or "educacion inclusiva" in title or "pedagogia y docencia" in title:
        extend_unique(skills, ["LMS", "Curriculum Design", "Instructional Design", "Learning Analytics", "Evaluation"])
    elif "administracion y gerencia de la salud" in title or "administracion en salud" in title:
        extend_unique(skills, ["Health Management", "Project Management", "Evaluation", "Leadership"])
    elif "administracion de empresas" in title:
        extend_unique(skills, ["Leadership", "Project Management", "Strategy", "Communication"])
    elif "administracion de la seguridad y salud en el trabajo" in title:
        extend_unique(skills, ["Occupational Health", "Risk Management", "Compliance", "Evaluation"])
    elif "licenciatura en educacion basica primaria" in title or "licenciatura en educacion infantil" in title:
        extend_unique(skills, ["Curriculum Design", "Instructional Design", "LMS", "Evaluation"])
    return skills


def clean_program_topic_profile(name: str, faculty: str) -> List[str]:
    name = clean_human_text(name)
    faculty = clean_human_text(faculty)
    title = normalize_text(name)
    topics: List[str] = []
    faculty_topics = {
        "ciencias economicas y administrativas": ["DirecciÃ³n estratÃ©gica", "GestiÃ³n de negocio", "AnalÃ­tica aplicada", "Liderazgo organizacional"],
        "ingenieria y tecnologia": ["Arquitectura digital", "AutomatizaciÃ³n", "Ciclo de vida de productos", "TransformaciÃ³n tecnolÃ³gica"],
        "derecho": ["Normativa y cumplimiento", "GestiÃ³n pÃºblica y privada", "Derecho digital", "Ã‰tica y regulaciÃ³n"],
        "educacion": ["DidÃ¡ctica", "CurrÃ­culo", "InnovaciÃ³n pedagÃ³gica", "EvaluaciÃ³n del aprendizaje"],
        "ciencias de la salud": ["GestiÃ³n en salud", "Calidad y seguridad", "PrevenciÃ³n de riesgos", "Toma de decisiones"],
    }
    extend_unique(topics, faculty_topics.get(normalize_text(faculty), []))
    if "inteligencia artificial" in title:
        extend_unique(topics, ["Modelos de IA", "Procesamiento de lenguaje natural", "VisiÃ³n por computador", "Ciencia de datos"])
    elif "visual analytics" in title or "inteligencia de negocio" in title or "big data" in title:
        extend_unique(topics, ["Modelado de datos", "Dashboards ejecutivos", "Gobierno de datos", "KPIs"])
    elif "marketing" in title:
        extend_unique(topics, ["Customer journey", "Crecimiento digital", "ConversiÃ³n", "ExperimentaciÃ³n"])
    elif "software" in title or "informatica" in title:
        extend_unique(topics, ["Arquitectura de software", "Calidad", "APIs", "Entrega continua"])
    elif "derecho" in title:
        extend_unique(topics, ["Cumplimiento", "RegulaciÃ³n", "Derecho digital", "GestiÃ³n de riesgos legales", "Habeas data", "SAGRILAFT", "SARLAFT"])
    elif "educacion" in title:
        extend_unique(topics, ["Aprendizaje", "InclusiÃ³n", "AcompaÃ±amiento docente", "EvaluaciÃ³n"])
    elif "salud" in title:
        extend_unique(topics, ["Calidad asistencial", "GestiÃ³n de servicios", "PrevenciÃ³n", "Bienestar"])
    return topics


def build_programs_clean() -> List[Dict[str, Any]]:
    programs: List[Dict[str, Any]] = []
    for index, blueprint in enumerate(PROGRAM_BLUEPRINTS, start=1):
        name = clean_human_text(blueprint["name"])
        faculty = clean_human_text(blueprint["faculty"])
        level = clean_human_text(blueprint["level"])
        programs.append(
            {
                "id": index,
                "name": name,
                "faculty": faculty,
                "area": faculty,
                "level": level,
                "credits": 24 if normalize_text(level) == "especializacion" else 160,
                "delivery_mode": "Virtual",
                "description": clean_program_description(name, faculty),
                "curriculum_skills": clean_program_skill_profile(name, faculty),
                "curriculum_topics": clean_program_topic_profile(name, faculty),
            }
        )
    return programs


PROGRAMS: List[Dict[str, Any]] = build_programs_clean()


def load_real_jobs(file_path: str) -> List[Dict[str, Any]]:
    path = os.path.abspath(file_path)
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"Input file not found: {path}")
    if not path.lower().endswith(".csv"):
        raise ValueError("Real job loading currently expects a CSV file.")

    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV file does not contain headers.")

        normalized_headers = {re.sub(r"[^a-z0-9]+", "", repair_text(name).lower()): name for name in reader.fieldnames}
        required = {"jobtitle", "company", "description", "location"}
        missing = [name for name in required if name not in normalized_headers]
        if missing:
            raise ValueError("CSV file is missing required columns: " + ", ".join(sorted(missing)))

        jobs: List[Dict[str, Any]] = []
        for index, row in enumerate(reader, start=1):
            job_title = repair_text(row.get(normalized_headers["jobtitle"], "")).strip()
            company = repair_text(row.get(normalized_headers["company"], "")).strip()
            description = repair_text(row.get(normalized_headers["description"], "")).strip()
            location = repair_text(row.get(normalized_headers["location"], "")).strip()
            if not job_title or not description:
                continue
            source_field = normalized_headers.get("source")
            date_field = normalized_headers.get("date") or normalized_headers.get("posted_at")
            industry_field = normalized_headers.get("industry")
            external_id_field = normalized_headers.get("job_id")
            source_value = repair_text(row.get(source_field, "")).strip() if source_field else ""
            date_value = repair_text(row.get(date_field, "")).strip() if date_field else ""
            industry_value = repair_text(row.get(industry_field, "")).strip() if industry_field else ""
            external_id = repair_text(row.get(external_id_field, "")).strip() if external_id_field else ""
            job_key = external_id or hashlib.sha1(
                "|".join(
                    [
                        normalize_text(job_title),
                        normalize_text(company),
                        normalize_text(location),
                        normalize_text(description[:500]),
                        str(index),
                    ]
                ).encode("utf-8")
            ).hexdigest()[:20]
            jobs.append(
                {
                    "id": job_key,
                    "job_id": job_key,
                    "title": job_title,
                    "job_title": job_title,
                    "company": company or "Unknown",
                    "industry": industry_value,
                    "location": location,
                    "source": source_value or "real",
                    "posted_at": date_value,
                    "description": description,
                }
            )

    if not jobs:
        raise ValueError("CSV file did not yield any valid job rows.")
    return jobs


GRADUATES: List[Dict[str, Any]] = [
    {
        "id": 1,
        "full_name": "Alex Ruiz",
        "program_id": 1,
        "current_role": "Data Analyst",
        "company": "Nova Retail",
        "sector": "Retail",
        "skills": ["SQL", "Power BI", "Python", "Statistics", "Dashboarding"],
        "employment_status": "employed",
        "salary_band": "4-6M COP",
        "linkedin_url": "https://linkedin.com/in/alex-ruiz",
        "linkedin_connected": True,
        "consent_given": True,
        "hire_date": months_ago(18),
        "last_promotion_at": months_ago(6),
        "updated_at": now_iso(),
        "next_survey_at": months_from_now(6),
    },
    {
        "id": 2,
        "full_name": "Paula Gomez",
        "program_id": 2,
        "current_role": "Software Engineer",
        "company": "EdTech Labs",
        "sector": "Technology",
        "skills": ["Python", "APIs", "Git", "Testing", "Agile", "Cloud"],
        "employment_status": "promoted",
        "salary_band": "6-8M COP",
        "linkedin_url": "https://linkedin.com/in/paula-gomez",
        "linkedin_connected": False,
        "consent_given": True,
        "hire_date": months_ago(22),
        "last_promotion_at": months_ago(4),
        "updated_at": now_iso(),
        "next_survey_at": months_from_now(6),
    },
    {
        "id": 3,
        "full_name": "Maria Torres",
        "program_id": 3,
        "current_role": "Academic Coordinator",
        "company": "Universidad Horizonte",
        "sector": "Higher Education",
        "skills": ["Curriculum Design", "Instructional Design", "LMS", "Evaluation", "Leadership"],
        "employment_status": "employed",
        "salary_band": "5-7M COP",
        "linkedin_url": "",
        "linkedin_connected": False,
        "consent_given": True,
        "hire_date": months_ago(30),
        "last_promotion_at": months_ago(12),
        "updated_at": now_iso(),
        "next_survey_at": months_from_now(6),
    },
    {
        "id": 4,
        "full_name": "Luis Herrera",
        "program_id": 1,
        "current_role": "BI Manager",
        "company": "Comercio Global",
        "sector": "Retail",
        "skills": ["SQL", "Power BI", "Dashboarding", "Data Storytelling", "Leadership", "Project Management"],
        "employment_status": "promoted",
        "salary_band": "8-12M COP",
        "linkedin_url": "https://linkedin.com/in/luis-herrera",
        "linkedin_connected": True,
        "consent_given": True,
        "hire_date": months_ago(40),
        "last_promotion_at": months_ago(9),
        "updated_at": now_iso(),
        "next_survey_at": months_from_now(6),
    },
    {
        "id": 5,
        "full_name": "Camila Rios",
        "program_id": 4,
        "current_role": "Marketing Analyst",
        "company": "Growth Hub",
        "sector": "Marketing",
        "skills": ["Digital Marketing", "Web Analytics", "SEO", "SEM", "CRM", "SQL"],
        "employment_status": "seeking",
        "salary_band": "4-6M COP",
        "linkedin_url": "",
        "linkedin_connected": False,
        "consent_given": True,
        "hire_date": months_ago(14),
        "last_promotion_at": None,
        "updated_at": now_iso(),
        "next_survey_at": months_from_now(6),
    },
]


INITIAL_EVENTS: List[Dict[str, Any]] = [
    {"id": 1, "graduate_id": 1, "type": "promotion", "title": "Promotion detected", "detail": "Promoted from Junior Analyst to Data Analyst", "created_at": months_ago(6)},
    {"id": 2, "graduate_id": 2, "type": "skill_adoption", "title": "New skill adoption", "detail": "Adopted Cloud and API delivery practices", "created_at": months_ago(4)},
    {"id": 3, "graduate_id": 4, "type": "promotion", "title": "Promotion detected", "detail": "Promoted to BI Manager", "created_at": months_ago(9)},
]


def skill_lookup(value: Any) -> Optional[Dict[str, str]]:
    normalized = normalize_text(value)
    if not normalized:
        return None
    return SKILL_LOOKUP.get(normalized)


def canonical_skill(value: Any) -> Optional[str]:
    match = skill_lookup(value)
    return match["name"] if match else None


def skill_category(value: Any) -> str:
    match = skill_lookup(value)
    return match["category"] if match else "technical"


def skill_type_from_category(category: str) -> str:
    normalized = normalize_text(category)
    if normalized == "soft":
        return "blanda"
    if normalized in {"technical", "tools"}:
        return "técnica"
    return "dominio"


def skill_confidence_score(skill_name: str, text: str, base: float = 0.72) -> float:
    normalized_skill = normalize_text(skill_name)
    normalized_text = normalize_text(text)
    if not normalized_skill:
        return round(base, 2)
    occurrences = len(re.findall(rf"\b{re.escape(normalized_skill)}\b", normalized_text))
    title_text = normalized_text.split(".")[0]
    confidence = base + min(0.18, occurrences * 0.06)
    if normalized_skill in title_text:
        confidence += 0.05
    return round(min(confidence, 0.98), 2)


def extract_skill_chunks(text: str) -> List[str]:
    cleaned = clean_human_text(text)
    if not cleaned:
        return []
    chunks = re.split(r"(?:,|;|/|\n|\band\b|\by\b|\bor\b|\bo\b)", cleaned, flags=re.IGNORECASE)
    candidates: List[str] = []
    seen = set()
    for chunk in chunks:
        phrase = clean_human_text(chunk)
        if not phrase:
            continue
        words = [word for word in re.findall(r"[^\W_]+", phrase, flags=re.UNICODE) if word]
        if not words:
            continue
        if len(words) > 6:
            continue
        if len(words) == 1 and len(normalize_text(words[0])) < 4:
            continue
        key = normalize_text(phrase)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(phrase)
    return candidates


def infer_skill_category(name: str) -> str:
    normalized = normalize_text(name)
    if not normalized:
        return "technical"
    if skill_lookup(name):
        return skill_category(name)
    technical_hints = {
        "python",
        "sql",
        "cloud",
        "etl",
        "power bi",
        "tableau",
        "dashboard",
        "analytics",
        "machine learning",
        "prompt engineering",
        "jira",
        "excel",
    }
    soft_hints = {
        "communication",
        "leadership",
        "negotiation",
        "teamwork",
        "comunication",
        "liderazgo",
        "trabajo en equipo",
    }
    law_hints = {
        "legal",
        "compliance",
        "regulatory",
        "contract",
        "governance",
        "privacy",
        "protection",
        "habeas data",
        "sagrilaft",
        "sarlaft",
        "litigation",
        "arbitration",
        "procurement",
        "due diligence",
        "risk",
    }
    if any(term in normalized for term in technical_hints):
        return "technical"
    if any(term in normalized for term in soft_hints):
        return "soft"
    if any(term in normalized for term in law_hints):
        return "domain"
    if len(normalized.split()) >= 2:
        return "domain"
    return "technical"


def extract_skills_from_text(text: str) -> List[Dict[str, Any]]:
    normalized = normalize_text(text)
    found: List[Dict[str, Any]] = []
    seen = set()

    def add_skill(name: str, category: str, confidence: float, source_phrase: str) -> None:
        canonical = canonical_skill(name)
        skill_name = canonical or clean_human_text(name)
        key = normalize_text(skill_name)
        if not key or key in seen:
            return
        seen.add(key)
        found.append(
            {
                "name": skill_name,
                "category": category,
                "confidence_score": round(confidence, 2),
                "source_phrase": clean_human_text(source_phrase) or skill_name,
            }
        )

    for skill in SKILL_CATALOG:
        for alias in [skill["name"]] + skill["aliases"]:
            alias_norm = normalize_text(alias)
            if not alias_norm:
                continue
            if re.search(rf"\b{re.escape(alias_norm)}\b", normalized):
                add_skill(skill["name"], skill["category"], skill_confidence_score(skill["name"], text, 0.9), alias)
                break

    for chunk in extract_skill_chunks(text):
        canonical = canonical_skill(chunk)
        if canonical:
            add_skill(canonical, skill_category(canonical), skill_confidence_score(canonical, text, 0.88), chunk)
            continue
        category = infer_skill_category(chunk)
        if category == "technical" and len(normalize_text(chunk).split()) < 2:
            continue
        confidence = 0.74 if len(chunk.split()) >= 2 else 0.62
        add_skill(chunk, category, skill_confidence_score(chunk, text, confidence), chunk)

    return [item for item in found]


def job_skill_relations(job: Dict[str, Any]) -> List[Dict[str, Any]]:
    text = f"{job.get('title', '')} {job.get('description', '')}"
    relations: List[Dict[str, Any]] = []
    for skill in extract_skills_from_text(text):
        relations.append(
            {
                "job_id": job.get("id"),
                "job_title": repair_text(job.get("title")),
                "skill_name": skill.get("name"),
                "skill_type": skill_type_from_category(str(skill.get("category") or "technical")),
                "confidence_score": skill.get("confidence_score", 0.75),
                "industry": repair_text(job.get("industry")),
                "location": repair_text(job.get("location")),
                "source": repair_text(job.get("source")),
                "date": job.get("posted_at"),
            }
        )
    return relations


def job_offer_payload(job: Dict[str, Any]) -> Dict[str, Any]:
    payload = repair_structure(copy.deepcopy(job))
    relations = job_skill_relations(job)
    payload["job_id"] = job.get("id")
    payload["job_title"] = repair_text(job.get("title"))
    payload["date"] = job.get("posted_at")
    payload["skills_detected"] = relations
    payload["skill_names"] = [item["skill_name"] for item in relations]
    return payload


def skill_offer_index(job_offers: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    index: Dict[str, Dict[str, Any]] = {}
    for offer in job_offers:
        for skill in offer.get("skills_detected") or []:
            name = str(skill.get("skill_name") or "").strip()
            if not name:
                continue
            entry = index.setdefault(
                name,
                {
                    "skill_name": name,
                    "frequency": 0,
                    "industry": [],
                    "job_titles": [],
                    "offers": [],
                },
            )
            entry["frequency"] += 1
            if offer.get("industry") and offer["industry"] not in entry["industry"]:
                entry["industry"].append(offer["industry"])
            if offer.get("job_title") and offer["job_title"] not in entry["job_titles"]:
                entry["job_titles"].append(offer["job_title"])
            entry["offers"].append(
                {
                    "job_id": offer.get("job_id"),
                    "job_title": offer.get("job_title"),
                    "company": offer.get("company"),
                    "industry": offer.get("industry"),
                    "location": offer.get("location"),
                    "source": offer.get("source"),
                    "date": offer.get("date"),
                    "confidence_score": skill.get("confidence_score"),
                    "skill_type": skill.get("skill_type"),
                }
            )
    return dict(sorted(index.items(), key=lambda item: (-item[1]["frequency"], item[0])))


def as_skill_names(values: Iterable[Any]) -> List[str]:
    names: List[str] = []
    for value in values:
        canonical = canonical_skill(value)
        names.append(canonical or str(value).strip())
    return [name for name in names if name]


def jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    sa = {normalize_text(item) for item in a if item}
    sb = {normalize_text(item) for item in b if item}
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def weighted_overlap(source: Sequence[str], target: Sequence[str]) -> Dict[str, Any]:
    source_norm = [canonical_skill(item) or item for item in source]
    target_norm = [canonical_skill(item) or item for item in target]
    source_set = {normalize_text(item) for item in source_norm}
    target_set = {normalize_text(item) for item in target_norm}
    matched = [item for item in target_norm if normalize_text(item) in source_set]
    missing = [item for item in target_norm if normalize_text(item) not in source_set]
    score = jaccard(source_norm, target_norm)
    return {
        "matched": matched,
        "missing": missing,
        "score": round(score * 100, 1),
        "coverage": len(matched) / max(len(target_norm), 1),
        "source_size": len(source_set),
        "target_size": len(target_set),
    }


def average(values: Iterable[float]) -> float:
    items = [float(value) for value in values if value is not None]
    return sum(items) / len(items) if items else 0.0


def months_between(start_iso: Optional[str], end_iso: Optional[str] = None) -> Optional[float]:
    if not start_iso:
        return None
    start = datetime.fromisoformat(start_iso.replace("Z", ""))
    end = datetime.fromisoformat((end_iso or now_iso()).replace("Z", ""))
    return round((end - start).days / 30.0, 1)


def program_skill_counts(program: Dict[str, Any]) -> Counter:
    return Counter(as_skill_names(program.get("curriculum_skills") or []))


def market_skill_counts(jobs: Sequence[Dict[str, Any]]) -> Counter:
    counts = Counter()
    for job in jobs:
        skills = extract_skills_from_text(f"{job.get('title', '')} {job.get('description', '')}")
        for skill in skills:
            counts[skill["name"]] += 1
    return counts


def graduate_skill_counts(graduates: Sequence[Dict[str, Any]]) -> Counter:
    counts = Counter()
    for graduate in graduates:
        for skill in as_skill_names(graduate.get("skills") or []):
            counts[skill] += 1
    return counts


def job_age_months(job: Dict[str, Any]) -> Optional[float]:
    return months_between(job.get("posted_at"))


def market_skill_trends(jobs: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    skill_stats: Dict[str, Dict[str, Any]] = {}
    for job in jobs:
        skills = extract_skills_from_text(f"{job.get('title', '')} {job.get('description', '')}")
        age = job_age_months(job)
        recent_weight = 1.0
        if age is not None:
            recent_weight = max(0.15, 1.25 - min(age / 12.0, 1.1))
        for skill in skills:
            entry = skill_stats.setdefault(
                skill["name"],
                {
                    "skill": skill["name"],
                    "category": skill["category"],
                    "count": 0,
                    "recent_count": 0.0,
                    "sources": set(),
                    "industries": set(),
                    "last_seen": None,
                },
            )
            entry["count"] += 1
            entry["recent_count"] += recent_weight
            entry["sources"].add(repair_text(job.get("source", "Unknown")))
            entry["industries"].add(repair_text(job.get("industry", "Unknown")))
            posted_at = job.get("posted_at")
            if posted_at and (entry["last_seen"] is None or str(posted_at) > str(entry["last_seen"])):
                entry["last_seen"] = posted_at

    trends: List[Dict[str, Any]] = []
    for entry in skill_stats.values():
        recent_count = round(float(entry["recent_count"]), 2)
        trend_score = round((recent_count - entry["count"]) * 100, 1)
        sources = sorted(entry["sources"])
        industries = sorted(entry["industries"])
        trends.append(
            {
                "skill": entry["skill"],
                "category": entry["category"],
                "count": entry["count"],
                "recent_count": recent_count,
                "trend": trend_score,
                "source_count": len(sources),
                "sources": sources,
                "industries": industries,
                "last_seen": entry["last_seen"],
            }
        )

    trends.sort(
        key=lambda item: (
            -(item["recent_count"] + (item["source_count"] * 0.5)),
            -item["count"],
            -item["trend"],
            item["skill"],
        )
    )
    return trends


def data_quality_metrics(jobs: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not jobs:
        return {
            "duplicate_rate": 0.0,
            "skill_diversity": 0.0,
            "source_diversity": 0.0,
            "recency_coverage": 0.0,
            "avg_age_months": None,
            "job_count": 0,
            "source_counts": {},
        }

    fingerprints = []
    for job in jobs:
        title = normalize_text(job.get("title"))
        company = normalize_text(job.get("company"))
        industry = normalize_text(job.get("industry"))
        fingerprint = f"{title}|{company}|{industry}"
        fingerprints.append(fingerprint)

    duplicate_rate = round((1 - (len(set(fingerprints)) / len(fingerprints))) * 100, 1)
    source_counts = Counter(repair_text(job.get("source") or "Unknown") for job in jobs)
    skill_counts = market_skill_counts(jobs)
    recency_months = [job_age_months(job) for job in jobs if job_age_months(job) is not None]
    recent_jobs = [job for job in jobs if (job_age_months(job) or 99) <= 6]

    return {
        "duplicate_rate": duplicate_rate,
        "skill_diversity": round((len(skill_counts) / max(len(jobs), 1)) * 100, 1),
        "source_diversity": round((len(source_counts) / len(jobs)) * 100, 1),
        "recency_coverage": round((len(recent_jobs) / len(jobs)) * 100, 1),
        "avg_age_months": round(average(recency_months), 1) if recency_months else None,
        "job_count": len(jobs),
        "source_counts": dict(source_counts),
    }


def program_domain(program: Dict[str, Any]) -> str:
    result = infer_program_domain(
        program.get("name"),
        faculty=program.get("faculty"),
        role=program.get("rol") or program.get("role"),
        skills=program.get("curriculum_skills") or program.get("skills") or [],
    )
    return result.domain


def job_text_blob(job: Dict[str, Any]) -> str:
    return normalize_text(
        " ".join(
            [
                str(job.get("title", "")),
                str(job.get("company", "")),
                str(job.get("industry", "")),
                str(job.get("location", "")),
                str(job.get("source", "")),
                str(job.get("description", "")),
            ]
        )
    )


def domain_skill_weight(skill: str, domain: str) -> float:
    skill_domain = infer_skill_domain(skill).domain
    return domain_weight(skill_domain, domain)


def job_relevance_score(program: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
    domain = program_domain(program)
    extracted = extract_skills_from_text(f"{job.get('title', '')} {job.get('description', '')}")
    job_domain = infer_job_domain(
        job.get("title"),
        source=job.get("source"),
        industry=job.get("industry"),
        description=job.get("description"),
        responsibilities=job.get("responsibilities"),
        requirements=job.get("requirements"),
        skills=[skill["name"] for skill in extracted],
    ).domain
    blob = job_text_blob(job)
    terms = DOMAIN_KEYWORDS.get(domain, [])
    curriculum = as_skill_names(program.get("curriculum_skills") or [])
    curriculum_keys = {normalize_text(item) for item in curriculum}
    domain_skills = {normalize_text(item) for item in DOMAIN_KEYWORDS.get(domain, [])}
    term_hits = [term for term in terms if normalize_text(term) in blob]
    excluded_hits: list[str] = []
    skill_hits = [skill["name"] for skill in extracted if normalize_text(skill["name"]) in curriculum_keys or infer_skill_domain(skill["name"]).domain == domain]
    context_hits = [token for token in normalize_text(clean_human_text(program.get("name", ""))).split() if len(token) > 3 and token in blob]
    industry_hits = 1 if normalize_text(job.get("industry")) in {normalize_text(domain_label(domain)), normalize_text(program.get("faculty"))} else 0
    score = (len(term_hits) * 2.0) + (len(skill_hits) * 1.6) + (len(context_hits) * 0.8) + (industry_hits * 1.0) - (len(excluded_hits) * 1.8)
    score *= domain_weight(domain, job_domain)
    return {
        "program_domain": domain,
        "job_domain": job_domain,
        "domain_weight": domain_weight(domain, job_domain),
        "score": round(max(score, 0.0), 2),
        "term_hits": term_hits,
        "excluded_hits": excluded_hits,
        "skill_hits": skill_hits,
        "extracted_skills": [skill["name"] for skill in extracted],
        "extracted_skill_details": extracted,
    }


def relevant_jobs_for_program(program: Dict[str, Any], jobs: Sequence[Dict[str, Any]], min_score: float = 3.2) -> List[Dict[str, Any]]:
    scored_jobs: List[Dict[str, Any]] = []
    for job in jobs:
        relevance = job_relevance_score(program, job)
        if relevance["score"] >= min_score:
            payload = repair_structure(copy.deepcopy(job))
            payload["relevance_score"] = relevance["score"]
            payload["relevance_reason"] = ", ".join(
                unique(
                    relevance["term_hits"][:4]
                    + relevance["skill_hits"][:4]
                    + ([f"-{item}" for item in relevance["excluded_hits"][:2]] if relevance["excluded_hits"] else [])
                )
            )
            payload["extracted_skills"] = relevance["extracted_skills"]
            payload["program_domain"] = relevance["program_domain"]
            scored_jobs.append(payload)
    scored_jobs.sort(key=lambda item: (-float(item.get("relevance_score", 0.0)), str(item.get("posted_at") or ""), str(item.get("title") or "")))
    return scored_jobs


def skill_evidence_from_jobs(jobs: Sequence[Dict[str, Any]], domain: str) -> Dict[str, Dict[str, Any]]:
    evidence: Dict[str, Dict[str, Any]] = {}
    allowed = {normalize_text(item) for item in DOMAIN_SKILL_PRIORITY.get(domain, [])}
    for job in jobs:
        age = job_age_months(job)
        recency = 1.0
        if age is not None:
            recency = max(0.2, 1.25 - min(age / 12.0, 1.1))
        skills = extract_skills_from_text(f"{job.get('title', '')} {job.get('description', '')}")
        for skill in skills:
            skill_name = skill["name"]
            if allowed and normalize_text(skill_name) not in allowed and domain == "law":
                if normalize_text(skill_name) in {normalize_text(item) for item in DOMAIN_SKILL_PRIORITY["technology"]}:
                    continue
            weight = domain_skill_weight(skill_name, domain)
            if weight <= 0:
                continue
            entry = evidence.setdefault(
                skill_name,
                {
                    "skill": skill_name,
                    "category": skill["category"],
                    "count": 0,
                    "weighted_count": 0.0,
                    "jobs": [],
                    "titles": [],
                    "companies": [],
                    "sectors": [],
                    "sources": [],
                    "last_seen": None,
                },
            )
            entry["count"] += 1
            entry["weighted_count"] += weight * recency
            entry["jobs"].append(job.get("id"))
            entry["titles"].append(repair_text(job.get("title")))
            entry["companies"].append(repair_text(job.get("company")))
            entry["sectors"].append(repair_text(job.get("industry")))
            entry["sources"].append(repair_text(job.get("source")))
            posted_at = job.get("posted_at")
            if posted_at and (entry["last_seen"] is None or str(posted_at) > str(entry["last_seen"])):
                entry["last_seen"] = posted_at
    return evidence


def program_market_report(program: Dict[str, Any], jobs: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    domain = program_domain(program)
    relevant_jobs = relevant_jobs_for_program(program, jobs)
    source_counts = Counter(repair_text(job.get("source") or "Unknown") for job in jobs)
    relevant_source_counts = Counter(str(job.get("source") or "Unknown") for job in relevant_jobs)
    curriculum = as_skill_names(program.get("curriculum_skills") or [])
    curriculum_keys = {normalize_text(item) for item in curriculum}
    extracted_count = len(relevant_jobs)
    if extracted_count < 3:
        return {
            "program_id": program["id"],
            "program_name": repair_text(program["name"]),
            "faculty": repair_text(program["faculty"]),
            "domain": domain,
            "generated_at": now_iso(),
            "processed_job_count": len(jobs),
            "relevant_job_count": extracted_count,
            "relevant_job_ratio": round((extracted_count / max(len(jobs), 1)) * 100, 1),
            "source_counts": dict(source_counts),
            "relevant_source_counts": dict(relevant_source_counts),
            "top_skills": [],
            "matched_skills": [],
            "missing_skills": [],
            "relevant_jobs": relevant_jobs[:10],
            "insufficient_data": True,
            "fallback_used": False,
            "message": "No hay suficientes vacantes relevantes para estimar skills de mercado.",
            "last_updated_at": now_iso(),
            "discarded_job_count": len(jobs) - extracted_count,
            "discarded_job_reasons": {"irrelevantes": len(jobs) - extracted_count},
        }

    evidence = skill_evidence_from_jobs(relevant_jobs, domain)
    if not evidence:
        return {
            "program_id": program["id"],
            "program_name": repair_text(program["name"]),
            "faculty": repair_text(program["faculty"]),
            "domain": domain,
            "generated_at": now_iso(),
            "processed_job_count": len(jobs),
            "relevant_job_count": extracted_count,
            "relevant_job_ratio": round((extracted_count / max(len(jobs), 1)) * 100, 1),
            "source_counts": dict(source_counts),
            "relevant_source_counts": dict(relevant_source_counts),
            "top_skills": [],
            "matched_skills": [],
            "missing_skills": [],
            "relevant_jobs": relevant_jobs[:10],
            "insufficient_data": True,
            "fallback_used": False,
            "message": "No hay suficientes vacantes relevantes para estimar skills de mercado.",
            "last_updated_at": now_iso(),
            "discarded_job_count": len(jobs) - extracted_count,
            "discarded_job_reasons": {"sin skills detectadas": extracted_count},
        }

    max_count = max((entry["count"] for entry in evidence.values()), default=1)
    max_weight = max((entry["weighted_count"] for entry in evidence.values()), default=1.0)
    ranked: List[Dict[str, Any]] = []
    for skill, entry in evidence.items():
        normalized = normalize_text(skill)
        share = round((entry["count"] / max(extracted_count, 1)) * 100, 1)
        recency_bonus = round(min(entry["weighted_count"] / max_weight, 1.0) * 100, 1)
        domain_weight = domain_skill_weight(skill, domain)
        if domain == "law" and normalized in {normalize_text(item) for item in DOMAIN_JOB_TERMS["technology"]}:
            domain_weight *= 0.2
        priority_score = round((share * 0.45) + (recency_bonus * 0.25) + ((entry["count"] / max_count) * 100 * 0.2) + (domain_weight * 10), 1)
        ranked.append(
            {
                "skill": skill,
                "category": entry["category"],
                "count": entry["count"],
                "share": share,
                "weighted_count": round(entry["weighted_count"], 2),
                "trend": recency_bonus,
                "priority_score": priority_score,
                "jobs": unique([str(item) for item in entry["titles"] if item]),
                "companies": unique([str(item) for item in entry["companies"] if item]),
                "sectors": unique([str(item) for item in entry["sectors"] if item]),
                "sources": unique([str(item) for item in entry["sources"] if item]),
                "last_seen": entry["last_seen"],
            }
        )

    ranked.sort(key=lambda item: (-item["priority_score"], -item["count"], item["skill"]))
    matched_skills = [skill for skill in curriculum if skill in evidence]
    missing_skills = [item["skill"] for item in ranked if normalize_text(item["skill"]) not in curriculum_keys]
    top_skills = []
    for item in ranked[:12]:
        top_skills.append(
            {
                **item,
                "priority": "alta" if item["priority_score"] >= 55 else "media" if item["priority_score"] >= 35 else "baja",
                "justification": f"Aparece en {item['share']}% de las vacantes relevantes del programa y en cargos como {', '.join(item['jobs'][:3])}.",
            }
        )
    report = {
        "program_id": program["id"],
        "program_name": repair_text(program["name"]),
        "faculty": repair_text(program["faculty"]),
        "domain": domain,
        "generated_at": now_iso(),
        "processed_job_count": len(jobs),
        "relevant_job_count": extracted_count,
        "relevant_job_ratio": round((extracted_count / max(len(jobs), 1)) * 100, 1),
        "source_counts": dict(source_counts),
        "relevant_source_counts": dict(relevant_source_counts),
        "top_skills": top_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills[:12],
        "relevant_jobs": relevant_jobs[:12],
        "insufficient_data": False,
        "fallback_used": False,
        "message": f"Se analizaron {extracted_count} vacantes relevantes sobre {len(jobs)} vacantes disponibles.",
        "last_updated_at": now_iso(),
        "discarded_job_count": len(jobs) - extracted_count,
        "discarded_job_reasons": {
            "fuera de contexto": len(jobs) - extracted_count,
        },
    }
    return report


def program_market_coverage(program: Dict[str, Any], jobs: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    report = program_market_report(program, jobs)
    program_skills = as_skill_names(program.get("curriculum_skills") or [])
    program_skill_keys = {normalize_text(item) for item in program_skills}
    if report.get("insufficient_data"):
        return {
            "coverage": 0.0,
            "gap_index": 100.0,
            "emerging": [],
            "missing": [],
            "insufficient_data": True,
            "relevant_job_count": report.get("relevant_job_count", 0),
            "last_updated_at": report.get("last_updated_at"),
            "source_counts": report.get("source_counts", {}),
            "relevant_source_counts": report.get("relevant_source_counts", {}),
        }

    top_skills = report.get("top_skills", [])
    covered = sum(1 for item in top_skills if normalize_text(item["skill"]) in program_skill_keys)
    total = len(top_skills)
    coverage = covered / max(total, 1)
    missing = [item["skill"] for item in top_skills if normalize_text(item["skill"]) not in program_skill_keys]
    emerging = missing[:5]
    return {
        "coverage": round(coverage * 100, 1),
        "gap_index": round((1.0 - coverage) * 100, 1),
        "emerging": emerging,
        "missing": missing,
        "insufficient_data": False,
        "relevant_job_count": report.get("relevant_job_count", 0),
        "last_updated_at": report.get("last_updated_at"),
        "source_counts": report.get("source_counts", {}),
        "relevant_source_counts": report.get("relevant_source_counts", {}),
    }


def graduate_success_rate(graduates: Sequence[Dict[str, Any]]) -> float:
    if not graduates:
        return 0.0
    status_weights = {
        "promoted": 1.0,
        "employed": 0.95,
        "self employed": 0.9,
        "freelance": 0.9,
        "studying": 0.65,
        "seeking": 0.25,
        "unemployed": 0.1,
        "inactive": 0.05,
    }
    scores = [status_weights.get(normalize_text(graduate.get("employment_status")), 0.4) for graduate in graduates]
    return round(average(scores) * 100, 1)


def time_to_promotion(graduates: Sequence[Dict[str, Any]], events: Sequence[Dict[str, Any]]) -> Optional[float]:
    months: List[float] = []
    for graduate in graduates:
        promotion_events = [event for event in events if event.get("graduate_id") == graduate.get("id") and normalize_text(event.get("type")) == "promotion"]
        if promotion_events:
            first_event = sorted(promotion_events, key=lambda item: item.get("created_at") or "")[0]
            months_value = months_between(graduate.get("hire_date"), first_event.get("created_at"))
            if months_value is not None:
                months.append(months_value)
    return round(average(months), 1) if months else None


def program_employability_alignment(program: Dict[str, Any], jobs: Sequence[Dict[str, Any]], graduates: Sequence[Dict[str, Any]], events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    market = program_market_coverage(program, jobs)
    linked_graduates = [graduate for graduate in graduates if graduate.get("program_id") == program.get("id")]
    success = graduate_success_rate(linked_graduates)
    promotion_months = time_to_promotion(linked_graduates, events)
    promotion_score = 0.5 if promotion_months is None else max(0.0, 1.0 - min(promotion_months / 36.0, 1.0))
    curriculum_coverage = market["coverage"] / 100.0
    if market.get("insufficient_data"):
        eas = round((0.35 * (success / 100.0) + 0.15 * promotion_score) * 100)
    else:
        eas = round((0.5 * curriculum_coverage + 0.3 * (success / 100.0) + 0.2 * promotion_score) * 100)
    return {
        "program_id": program["id"],
        "program_name": repair_text(program["name"]),
        "faculty": repair_text(program["faculty"]),
        "eas": max(0, min(100, eas)),
        "skill_gap_index": market["gap_index"],
        "market_coverage": market["coverage"],
        "graduate_success_rate": success,
        "time_to_promotion": promotion_months,
        "emerging_skills": market["emerging"],
        "curriculum_skills": as_skill_names(program.get("curriculum_skills") or []),
        "relevant_job_count": market.get("relevant_job_count", 0),
        "market_updated_at": market.get("last_updated_at"),
        "insufficient_data": market.get("insufficient_data", False),
    }


def graduate_program_matches(graduate: Dict[str, Any], programs: Sequence[Dict[str, Any]], jobs: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    graduate_skills = as_skill_names(graduate.get("skills") or [])
    ranked: List[Dict[str, Any]] = []
    for program in programs:
        program_skills = as_skill_names(program.get("curriculum_skills") or [])
        overlap = weighted_overlap(graduate_skills, program_skills)
        market_report = program_market_report(program, jobs)
        market_fit = weighted_overlap(program_skills, [item["skill"] for item in market_report.get("top_skills", [])])
        ranked.append(
            {
                "program_id": program["id"],
                "program_name": repair_text(program["name"]),
                "faculty": repair_text(program["faculty"]),
                "score": round(overlap["score"] * 0.65 + market_fit["score"] * 0.35, 1),
                "matched": overlap["matched"],
                "missing": overlap["missing"][:8],
                "market_fit": market_fit["score"],
                "relevant_job_count": market_report.get("relevant_job_count", 0),
            }
        )
    ranked.sort(key=lambda item: (-item["score"], item["program_name"]))
    return ranked


def graduate_job_matches(graduate: Dict[str, Any], jobs: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    graduate_skills = as_skill_names(graduate.get("skills") or [])
    ranked: List[Dict[str, Any]] = []
    for job in jobs:
        job_skills = as_skill_names(extract_skills_from_text(f"{job.get('title', '')} {job.get('description', '')}"))
        overlap = weighted_overlap(graduate_skills, job_skills)
        ranked.append(
            {
                "job_id": job["id"],
                "title": repair_text(job["title"]),
                "company": repair_text(job["company"]),
                "industry": repair_text(job["industry"]),
                "source": repair_text(job["source"]),
                "score": overlap["score"],
                "matched": overlap["matched"],
                "missing": overlap["missing"][:8],
            }
        )
    ranked.sort(key=lambda item: (-item["score"], item["title"]))
    return ranked


def detect_graduate_events(before: Dict[str, Any], after: Dict[str, Any], graduate_id: int) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    before_role = normalize_text(before.get("current_role"))
    after_role = normalize_text(after.get("current_role"))
    before_company = normalize_text(before.get("company"))
    after_company = normalize_text(after.get("company"))
    before_skills = {normalize_text(skill) for skill in as_skill_names(before.get("skills") or [])}
    after_skills = {normalize_text(skill) for skill in as_skill_names(after.get("skills") or [])}

    if before_role and after_role and before_role != after_role and before_company == after_company:
        events.append(
            {
                "id": None,
                "graduate_id": graduate_id,
                "type": "promotion",
                "title": "Promotion detected",
                "detail": f"Role changed from {before.get('current_role')} to {after.get('current_role')}",
                "created_at": now_iso(),
            }
        )
    if before_company and after_company and before_company != after_company:
        events.append(
            {
                "id": None,
                "graduate_id": graduate_id,
                "type": "company_change",
                "title": "Company change detected",
                "detail": f"Moved from {before.get('company')} to {after.get('company')}",
                "created_at": now_iso(),
            }
        )
    new_skills = sorted(after_skills - before_skills)
    if new_skills:
        events.append(
            {
                "id": None,
                "graduate_id": graduate_id,
                "type": "skill_adoption",
                "title": "New skill adoption",
                "detail": ", ".join(new_skills[:6]),
                "created_at": now_iso(),
            }
        )
    return events


def micro_survey_questions(graduate: Dict[str, Any]) -> List[str]:
    role = graduate.get("current_role") or "your current role"
    return [
        f"How aligned is {role} with the skills you learned in the program?",
        "What skill do you use most often in your day-to-day work?",
        "Which new tool or competence should the university teach better?",
    ]


def platform_summary(programs: Sequence[Dict[str, Any]], graduates: Sequence[Dict[str, Any]], jobs: Sequence[Dict[str, Any]], events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    program_scores = [program_employability_alignment(program, jobs, graduates, events) for program in programs]
    program_scores.sort(key=lambda item: (-item["eas"], item["program_name"]))
    market_counts = market_skill_counts(jobs)
    skill_trends = market_skill_trends(jobs)
    quality = data_quality_metrics(jobs)
    curriculum_counts = Counter()
    for program in programs:
        curriculum_counts.update(as_skill_names(program.get("curriculum_skills") or []))

    curriculum_keys = {normalize_text(item) for item in curriculum_counts.keys()}
    top_emerging = [item["skill"] for item in skill_trends if normalize_text(item["skill"]) not in curriculum_keys][:8]
    success_rate = graduate_success_rate(graduates)
    ttp = time_to_promotion(graduates, events)
    eas = round(average([item["eas"] for item in program_scores]) if program_scores else 0)

    return {
        "employability_alignment_score": eas,
        "skill_gap_index": round((1.0 - (average([item["market_coverage"] for item in program_scores]) / 100.0 if program_scores else 0.0)) * 100, 1),
        "graduate_success_rate": success_rate,
        "time_to_promotion": ttp,
        "top_emerging_skills": top_emerging,
        "top_trending_skills": skill_trends[:8],
        "top_programs": program_scores[:4],
        "graduate_count": len(graduates),
        "market_job_count": len(jobs),
        "event_count": len(events),
        "data_quality": quality,
    }


def simulate_curriculum(program: Dict[str, Any], add_skills: Sequence[str], remove_skills: Sequence[str], jobs: Sequence[Dict[str, Any]], graduates: Sequence[Dict[str, Any]], events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    original = as_skill_names(program.get("curriculum_skills") or [])
    remove_keys = {normalize_text(item) for item in remove_skills}
    updated = [skill for skill in original if normalize_text(skill) not in remove_keys]
    existing_keys = {normalize_text(item) for item in updated}
    for skill in add_skills:
        canonical = canonical_skill(skill) or str(skill).strip()
        if canonical and normalize_text(canonical) not in existing_keys:
            updated.append(canonical)
            existing_keys.add(normalize_text(canonical))

    before = program_employability_alignment(program, jobs, graduates, events)
    simulated = copy.deepcopy(program)
    simulated["curriculum_skills"] = updated
    after = program_employability_alignment(simulated, jobs, graduates, events)
    return {
        "program_id": program["id"],
        "program_name": repair_text(program["name"]),
        "before": before,
        "after": after,
        "delta_eas": after["eas"] - before["eas"],
        "delta_gap_index": after["skill_gap_index"] - before["skill_gap_index"],
        "updated_curriculum_skills": updated,
    }


def recommendation_urgency(impact_eas: float, market_demand: int, graduate_signal: int) -> str:
    if impact_eas >= 6 or market_demand >= 4 or (market_demand >= 3 and graduate_signal >= 2):
        return "alta"
    if impact_eas >= 3 or market_demand >= 2 or graduate_signal >= 2:
        return "media"
    return "baja"


def automatic_recommendations(
    program: Dict[str, Any],
    jobs: Sequence[Dict[str, Any]],
    graduates: Sequence[Dict[str, Any]],
    events: Sequence[Dict[str, Any]],
    limit: int = 6,
) -> Dict[str, Any]:
    curriculum = as_skill_names(program.get("curriculum_skills") or [])
    curriculum_keys = {normalize_text(item) for item in curriculum}
    market_report = program_market_report(program, jobs)
    if market_report.get("insufficient_data"):
        return {
            "program_id": program["id"],
            "program_name": repair_text(program["name"]),
            "faculty": repair_text(program["faculty"]),
            "curriculum_skills": curriculum,
            "items": [],
            "high_urgency_count": 0,
            "message": "No hay suficientes vacantes relevantes para estimar skills de mercado.",
            "market_report": market_report,
        }
    market_skills = market_report.get("top_skills", [])
    market_max = max((item.get("count", 0) for item in market_skills), default=1)

    linked_graduates = [graduate for graduate in graduates if graduate.get("program_id") == program.get("id")]
    successful_linked = [
        graduate
        for graduate in linked_graduates
        if normalize_text(graduate.get("employment_status")) in {"promoted", "employed", "self employed", "freelance"}
    ]
    graduate_counts = graduate_skill_counts(linked_graduates)
    successful_counts = graduate_skill_counts(successful_linked)
    graduate_max = max(graduate_counts.values(), default=1)

    candidates: List[str] = []
    seen = set()
    for source in ([ (item["skill"], item["count"]) for item in market_skills ], graduate_counts.most_common()):
        for skill, _count in source:
            if normalize_text(skill) in curriculum_keys:
                continue
            key = normalize_text(skill)
            if key in seen:
                continue
            seen.add(key)
            candidates.append(skill)

        if not candidates:
            return {
                "program_id": program["id"],
                "program_name": repair_text(program["name"]),
                "faculty": repair_text(program["faculty"]),
                "curriculum_skills": curriculum,
                "items": [],
            "high_urgency_count": 0,
            "message": "El programa ya cubre las skills principales del mercado y de los egresados analizados.",
        }

    base_alignment = program_employability_alignment(program, jobs, graduates, events)
    scored: List[Dict[str, Any]] = []

    for skill in candidates:
        simulated = simulate_curriculum(program, [skill], [], jobs, graduates, events)
        skill_market = next((item for item in market_skills if normalize_text(item["skill"]) == normalize_text(skill)), None)
        market_demand = int(skill_market["count"]) if skill_market else 0
        graduate_signal = int(successful_counts.get(skill, graduate_counts.get(skill, 0)))
        demand_score = market_demand / max(market_max, 1)
        graduate_score = graduate_signal / max(graduate_max, 1)
        impact_eas = round(max(0.0, float(simulated["delta_eas"])), 1)
        impact_score = min(max(impact_eas / 10.0, 0.0), 1.0)
        priority_score = round((impact_score * 0.5 + demand_score * 0.3 + graduate_score * 0.2) * 100, 1)
        urgency = recommendation_urgency(impact_eas, market_demand, graduate_signal)

        evidence_bits = []
        if market_demand:
            evidence_bits.append(f"aparece en {market_demand} vacantes")
        if graduate_signal:
            evidence_bits.append(f"la usan {graduate_signal} egresados del programa")
        if not evidence_bits:
            evidence_bits.append("tiene señales de adopción en la base analizada")

        justification = (
            f"{', '.join(evidence_bits)}. "
            f"Al incorporarla, el EAS sube {impact_eas:.1f} puntos "
            f"y la brecha baja de {base_alignment['skill_gap_index']}% a {simulated['after']['skill_gap_index']}%."
        )

        scored.append(
            {
                "skill": skill,
                "priority_score": priority_score,
                "impact_eas": impact_eas,
                "urgency": urgency,
                "justification": justification,
                "market_demand": market_demand,
                "graduate_signal": graduate_signal,
                "before_eas": base_alignment["eas"],
                "after_eas": simulated["after"]["eas"],
                "before_gap": base_alignment["skill_gap_index"],
                "after_gap": simulated["after"]["skill_gap_index"],
                "updated_curriculum_skills": simulated["updated_curriculum_skills"],
            }
        )

    scored.sort(
        key=lambda item: (
            -item["priority_score"],
            -item["impact_eas"],
            -item["market_demand"],
            item["skill"],
        )
    )

    high_urgency_count = sum(1 for item in scored if item["urgency"] == "alta")
    return {
        "program_id": program["id"],
        "program_name": repair_text(program["name"]),
        "faculty": repair_text(program["faculty"]),
        "curriculum_skills": curriculum,
        "items": scored[:limit],
        "high_urgency_count": high_urgency_count,
        "message": f"Se evaluaron {len(scored)} skills faltantes y se priorizaron las {min(limit, len(scored))} de mayor impacto.",
        "market_report": market_report,
    }


class InMemoryStore:
    def __init__(self, jobs_path: Optional[str] = None) -> None:
        self._lock = RLock()
        self.programs = copy.deepcopy(PROGRAMS)
        self.graduates = copy.deepcopy(GRADUATES)
        self.jobs = load_real_jobs(jobs_path or os.getenv("JOBS_INPUT_FILE") or "")
        self.events = copy.deepcopy(INITIAL_EVENTS)
        self.analysis_runs: List[Dict[str, Any]] = []
        self.surveys_sent: List[Dict[str, Any]] = []
        self.job_sources_sync_log: List[Dict[str, Any]] = []
        self.program_market_cache: Dict[int, Dict[str, Any]] = {}

    def _next_id(self, collection: Sequence[Dict[str, Any]]) -> int:
        return max((int(item.get("id") or 0) for item in collection), default=0) + 1

    def list_programs(self) -> List[Dict[str, Any]]:
        return repair_structure(copy.deepcopy(self.programs))

    def list_graduates(self) -> List[Dict[str, Any]]:
        return repair_structure(copy.deepcopy(self.graduates))

    def list_jobs(self) -> List[Dict[str, Any]]:
        return repair_structure(copy.deepcopy(self.jobs))

    def list_job_offers(self) -> List[Dict[str, Any]]:
        return [job_offer_payload(job) for job in self.list_jobs()]

    def list_skill_offer_index(self) -> Dict[str, Any]:
        return skill_offer_index(self.list_job_offers())

    def list_skill_offers(self, skill_name: str) -> List[Dict[str, Any]]:
        index = self.list_skill_offer_index()
        normalized = normalize_text(skill_name)
        for key, value in index.items():
            if normalize_text(key) == normalized:
                return copy.deepcopy(value.get("offers", []))
        return []

    def list_events(self) -> List[Dict[str, Any]]:
        items = sorted(self.events, key=lambda item: item.get("created_at") or "", reverse=True)
        return repair_structure(copy.deepcopy(items))

    def _log_job_sync(self, report: Dict[str, Any]) -> None:
        self.job_sources_sync_log.append(
            {
                "id": len(self.job_sources_sync_log) + 1,
                "program_id": report.get("program_id"),
                "program_name": report.get("program_name"),
                "domain": report.get("domain"),
                "queried_job_count": report.get("processed_job_count", 0),
                "relevant_job_count": report.get("relevant_job_count", 0),
                "relevant_job_ratio": report.get("relevant_job_ratio", 0),
                "source_counts": copy.deepcopy(report.get("source_counts", {})),
                "relevant_source_counts": copy.deepcopy(report.get("relevant_source_counts", {})),
                "discarded_job_count": report.get("discarded_job_count", 0),
                "generated_at": report.get("generated_at") or now_iso(),
            }
        )

    def get_program_market_report(self, program_id: int, refresh: bool = False) -> Dict[str, Any]:
        with self._lock:
            if not refresh and program_id in self.program_market_cache:
                return copy.deepcopy(self.program_market_cache[program_id])
            program = self.get_program(program_id)
            report = program_market_report(program, self.jobs)
            self.program_market_cache[program_id] = copy.deepcopy(report)
            self._log_job_sync(report)
            return copy.deepcopy(report)

    def list_program_market_reports(self) -> Dict[str, Any]:
        reports: Dict[str, Any] = {}
        for program in self.programs:
            report = self.get_program_market_report(int(program["id"]))
            reports[str(program["id"])] = report
        return reports

    def list_program_market_jobs(self, program_id: int) -> List[Dict[str, Any]]:
        report = self.get_program_market_report(program_id)
        return copy.deepcopy(report.get("relevant_jobs", []))

    def recompute_program_market(self, program_id: int) -> Dict[str, Any]:
        with self._lock:
            self.program_market_cache.pop(int(program_id), None)
            return self.get_program_market_report(program_id, refresh=True)

    def get_program(self, program_id: int) -> Dict[str, Any]:
        for program in self.programs:
            if int(program["id"]) == int(program_id):
                return repair_structure(copy.deepcopy(program))
        raise KeyError(f"Program {program_id} not found")

    def get_graduate(self, graduate_id: int) -> Dict[str, Any]:
        for graduate in self.graduates:
            if int(graduate["id"]) == int(graduate_id):
                return repair_structure(copy.deepcopy(graduate))
        raise KeyError(f"Graduate {graduate_id} not found")

    def create_graduate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            new_item = {
                "id": self._next_id(self.graduates),
                "full_name": payload.get("full_name", "").strip() or "Unnamed Graduate",
                "program_id": int(payload.get("program_id") or 1),
                "current_role": payload.get("current_role", "").strip(),
                "company": payload.get("company", "").strip(),
                "sector": payload.get("sector", "").strip(),
                "skills": as_skill_names(payload.get("skills") or []),
                "employment_status": payload.get("employment_status", "employed"),
                "salary_band": payload.get("salary_band", ""),
                "linkedin_url": payload.get("linkedin_url", ""),
                "linkedin_connected": bool(payload.get("linkedin_connected", False)),
                "consent_given": bool(payload.get("consent_given", False)),
                "hire_date": payload.get("hire_date") or now_iso(),
                "last_promotion_at": payload.get("last_promotion_at"),
                "updated_at": now_iso(),
                "next_survey_at": payload.get("next_survey_at") or months_from_now(6),
            }
            self.graduates.append(new_item)
            return copy.deepcopy(new_item)

    def update_graduate(self, graduate_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            for index, graduate in enumerate(self.graduates):
                if int(graduate["id"]) == int(graduate_id):
                    before = copy.deepcopy(graduate)
                    updated = copy.deepcopy(graduate)
                    for field in [
                        "full_name",
                        "program_id",
                        "current_role",
                        "company",
                        "sector",
                        "employment_status",
                        "salary_band",
                        "linkedin_url",
                        "linkedin_connected",
                        "consent_given",
                        "hire_date",
                        "last_promotion_at",
                        "next_survey_at",
                    ]:
                        if field in payload and payload[field] is not None:
                            updated[field] = payload[field]
                    if "skills" in payload and payload["skills"] is not None:
                        updated["skills"] = as_skill_names(payload["skills"])
                    updated["updated_at"] = now_iso()
                    self.graduates[index] = updated
                    for event in detect_graduate_events(before, updated, int(graduate_id)):
                        event["id"] = self._next_id(self.events)
                        self.events.append(event)
                    return copy.deepcopy(updated)
        raise KeyError(f"Graduate {graduate_id} not found")

    def scan_graduate(self, graduate_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        current = self.get_graduate(graduate_id)
        merged = copy.deepcopy(current)
        if payload:
            for key, value in payload.items():
                if value is not None:
                    merged[key] = value
        updated = self.update_graduate(graduate_id, merged)
        events = [event for event in self.list_events() if int(event.get("graduate_id") or 0) == int(graduate_id)]
        return {"graduate": updated, "events": events}

    def list_events_for_graduate(self, graduate_id: int) -> List[Dict[str, Any]]:
        return [event for event in self.list_events() if int(event.get("graduate_id") or 0) == int(graduate_id)]

    def log_analysis(self, query: str, mode: str, payload: Dict[str, Any]) -> None:
        self.analysis_runs.append({"id": len(self.analysis_runs) + 1, "query": query, "mode": mode, "payload": copy.deepcopy(payload), "created_at": now_iso()})

    def log_survey(self, graduate_id: int, questions: List[str]) -> None:
        self.surveys_sent.append({"id": len(self.surveys_sent) + 1, "graduate_id": graduate_id, "questions": list(questions), "created_at": now_iso()})

    def bootstrap(self) -> Dict[str, Any]:
        summary = platform_summary(self.programs, self.graduates, self.jobs, self.events)
        skill_counts = market_skill_counts(self.jobs)
        graduate_counts = graduate_skill_counts(self.graduates)
        market_skills = [{"skill": skill, "count": count} for skill, count in skill_counts.most_common(20)]
        graduate_skill_tallies = [{"skill": skill, "count": count} for skill, count in graduate_counts.most_common(16)]
        program_market_reports = self.list_program_market_reports()
        job_offers = self.list_job_offers()
        skill_index = skill_offer_index(job_offers)
        return {
            "platform": "Graduate Intelligence & Employability Platform",
            "generated_at": now_iso(),
            "summary": summary,
            "programs": [self._program_payload(program) for program in self.programs],
            "graduates": self.list_graduates(),
            "jobs": self.list_jobs(),
            "job_offers": job_offers,
            "extracted_skills": [relation for offer in job_offers for relation in offer.get("skills_detected", [])],
            "skill_offer_index": skill_index,
            "events": self.list_events()[:20],
            "market_skills": market_skills,
            "graduate_skills": graduate_skill_tallies,
            "skill_trends": market_skill_trends(self.jobs)[:20],
            "data_quality": data_quality_metrics(self.jobs),
            "program_market_reports": program_market_reports,
            "job_sources_sync_log": repair_structure(copy.deepcopy(self.job_sources_sync_log[-30:])),
            "skill_catalog": repair_structure(copy.deepcopy(SKILL_CATALOG)),
            "history": repair_structure(copy.deepcopy(self.analysis_runs[-12:])),
        }

    def _program_payload(self, program: Dict[str, Any]) -> Dict[str, Any]:
        data = repair_structure(copy.deepcopy(program))
        data["curriculum_skills"] = as_skill_names(program.get("curriculum_skills") or [])
        return data

    def dashboard(self) -> Dict[str, Any]:
        summary = platform_summary(self.programs, self.graduates, self.jobs, self.events)
        program_cards = [program_employability_alignment(program, self.jobs, self.graduates, self.events) for program in self.programs]
        program_cards.sort(key=lambda item: (-item["eas"], item["program_name"]))
        active_graduates = [graduate for graduate in self.graduates if normalize_text(graduate.get("employment_status")) in {"employed", "promoted", "self employed", "freelance"}]
        return {
            "summary": summary,
            "program_cards": program_cards,
            "graduate_count": len(self.graduates),
            "active_graduate_count": len(active_graduates),
            "promotion_rate": graduate_success_rate(self.graduates),
            "time_to_promotion": time_to_promotion(self.graduates, self.events),
            "top_events": self.list_events()[:8],
            "top_emerging_skills": summary["top_emerging_skills"],
            "top_trending_skills": summary["top_trending_skills"],
            "data_quality": summary["data_quality"],
            "job_sources_sync_log": copy.deepcopy(self.job_sources_sync_log[-12:]),
        }

    def analyze_graduate(self, graduate_id: int) -> Dict[str, Any]:
        graduate = self.get_graduate(graduate_id)
        program_matches = graduate_program_matches(graduate, self.programs, self.jobs)
        job_matches = graduate_job_matches(graduate, self.jobs)
        inferred_skills = extract_skills_from_text(" ".join([graduate.get("full_name", ""), graduate.get("current_role", ""), graduate.get("company", ""), " ".join(graduate.get("skills") or [])]))
        payload = {"graduate": graduate, "inferred_skills": inferred_skills, "program_matches": program_matches[:4], "job_matches": job_matches[:4]}
        self.log_analysis(graduate.get("full_name", ""), "graduate", payload)
        return payload

    def analyze_job_text(self, text: str) -> Dict[str, Any]:
        inferred = extract_skills_from_text(text)
        temp_job = {"id": 0, "title": "Ingested job", "company": "Unknown", "industry": "Unknown", "source": "Manual", "description": text}
        job_matches = []
        for program in self.programs:
            overlap = weighted_overlap([skill["name"] for skill in inferred], as_skill_names(program.get("curriculum_skills") or []))
            job_matches.append({"program_id": program["id"], "program_name": repair_text(program["name"]), "faculty": repair_text(program["faculty"]), "score": overlap["score"], "matched": overlap["matched"], "missing": overlap["missing"]})
        job_matches.sort(key=lambda item: (-item["score"], item["program_name"]))
        payload = {
            "job": temp_job,
            "inferred_skills": inferred,
            "inferred_skill_names": [skill["name"] for skill in inferred],
            "program_matches": job_matches[:4],
        }
        self.log_analysis(text[:120], "job_text", payload)
        return payload

    def simulate(self, program_id: int, add_skills: Sequence[str], remove_skills: Sequence[str]) -> Dict[str, Any]:
        program = self.get_program(program_id)
        result = simulate_curriculum(program, add_skills, remove_skills, self.jobs, self.graduates, self.events)
        self.log_analysis(program.get("name", ""), "simulation", result)
        return result

    def recommend(self, program_id: int) -> Dict[str, Any]:
        program = self.get_program(program_id)
        result = automatic_recommendations(program, self.jobs, self.graduates, self.events)
        self.log_analysis(program.get("name", ""), "recommendation", result)
        return result

    def micro_survey_for_graduate(self, graduate_id: int) -> Dict[str, Any]:
        graduate = self.get_graduate(graduate_id)
        questions = micro_survey_questions(graduate)
        self.log_survey(graduate_id, questions)
        return {"graduate_id": graduate_id, "graduate_name": graduate["full_name"], "trigger": "scheduled_or_event_based", "questions": questions, "recommended_channel": "email_or_portal"}





