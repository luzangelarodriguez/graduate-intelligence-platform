from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class SkillDefinition:
    canonical_name: str
    domain: str
    tipo: str
    descripcion: str = ""
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class DomainDefinition:
    code: str
    name: str
    description: str
    terms: tuple[str, ...]
    excluded_domains: tuple[str, ...] = ()


def normalize_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9+#.]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


DOMAIN_DEFINITIONS: tuple[DomainDefinition, ...] = (
    DomainDefinition(
        "ambiental",
        "Ambiental",
        "Gestion ambiental, sostenibilidad, biodiversidad y cumplimiento ambiental.",
        (
            "gestion ambiental",
            "ambiental",
            "sostenibilidad",
            "esg",
            "iso 14001",
            "huella de carbono",
            "cambio climatico",
            "biodiversidad",
            "licenciamiento ambiental",
            "economia circular",
            "residuos",
        ),
        ("ti", "cybersecurity", "software"),
    ),
    DomainDefinition(
        "energia",
        "Energia",
        "Gestion energetica, eficiencia, transicion y energias renovables.",
        (
            "gestion energetica",
            "energia",
            "energetica",
            "eficiencia energetica",
            "transicion energetica",
            "energias renovables",
            "iso 50001",
            "solar",
            "fotovoltaica",
            "carbono",
        ),
        ("ti", "cybersecurity", "software"),
    ),
    DomainDefinition(
        "legal-tech",
        "Legal tech",
        "Derecho digital, datos, tecnologia, propiedad intelectual y cumplimiento digital.",
        (
            "derecho digital",
            "legal tech",
            "derecho informatico",
            "proteccion de datos",
            "habeas data",
            "propiedad intelectual",
            "compliance digital",
            "contratos tecnologicos",
        ),
        ("software",),
    ),
    DomainDefinition(
        "legal",
        "Legal",
        "Derecho, cumplimiento, contratacion, riesgos juridicos y regulacion.",
        (
            "derecho",
            "juridico",
            "legal",
            "contratacion",
            "compliance",
            "sarlaft",
            "regulatorio",
            "auditoria legal",
            "riesgo legal",
        ),
        ("software",),
    ),
    DomainDefinition(
        "salud",
        "Salud",
        "Gestion sanitaria, salud publica, clinica, epidemiologia y calidad en salud.",
        (
            "salud",
            "clinico",
            "hospital",
            "epidemiologia",
            "ips",
            "eps",
            "seguridad del paciente",
            "calidad en salud",
        ),
    ),
    DomainDefinition(
        "educacion",
        "Educacion",
        "Pedagogia, diseno curricular, aprendizaje, evaluacion y tecnologia educativa.",
        (
            "educacion",
            "pedagogia",
            "curriculo",
            "diseno curricular",
            "docencia",
            "lms",
            "learning analytics",
            "evaluacion educativa",
        ),
    ),
    DomainDefinition(
        "marketing",
        "Marketing",
        "Mercadeo, experiencia cliente, marca, performance y estrategia comercial.",
        (
            "marketing",
            "mercadeo",
            "seo",
            "sem",
            "crm",
            "growth",
            "marca",
            "customer experience",
            "ventas",
        ),
    ),
    DomainDefinition(
        "ti",
        "TI",
        "Tecnologia, software, datos, cloud, arquitectura e infraestructura.",
        (
            "tecnologia",
            "software",
            "desarrollo",
            "backend",
            "frontend",
            "fullstack",
            "api",
            "cloud",
            "devops",
            "python",
            "javascript",
        ),
        ("ambiental", "energia"),
    ),
    DomainDefinition(
        "cybersecurity",
        "Ciberseguridad",
        "Seguridad informatica, riesgo tecnologico, respuesta a incidentes y privacidad.",
        (
            "ciberseguridad",
            "seguridad informatica",
            "ethical hacking",
            "pentesting",
            "soc",
            "siem",
            "iso 27001",
            "incidentes",
        ),
        ("ambiental", "energia"),
    ),
    DomainDefinition(
        "analitica",
        "Analitica",
        "Analitica de datos, BI, visual analytics, gobierno y ciencia de datos.",
        (
            "analitica",
            "data analytics",
            "business intelligence",
            "visual analytics",
            "power bi",
            "tableau",
            "sql",
            "datos",
            "machine learning",
        ),
    ),
    DomainDefinition(
        "finanzas",
        "Finanzas",
        "Finanzas corporativas, riesgos, contabilidad, auditoria y planeacion financiera.",
        (
            "finanzas",
            "financiero",
            "contabilidad",
            "auditoria",
            "tributario",
            "riesgo financiero",
            "presupuesto",
        ),
    ),
    DomainDefinition(
        "logistica",
        "Logistica",
        "Cadena de suministro, operaciones, compras, transporte e inventarios.",
        (
            "logistica",
            "supply chain",
            "abastecimiento",
            "compras",
            "inventarios",
            "transporte",
            "operaciones",
        ),
    ),
    DomainDefinition(
        "gestion_humana",
        "Gestion humana",
        "Talento humano, cultura, seleccion, bienestar, compensacion y desarrollo.",
        (
            "gestion humana",
            "recursos humanos",
            "talento humano",
            "seleccion",
            "compensacion",
            "bienestar",
            "cultura organizacional",
        ),
    ),
    DomainDefinition(
        "management",
        "Management",
        "Direccion, estrategia, gerencia, proyectos, liderazgo y transformacion.",
        (
            "alta gerencia",
            "gerencia",
            "management",
            "direccion",
            "estrategia",
            "liderazgo",
            "gestion de proyectos",
            "transformacion",
        ),
    ),
)


SKILL_DEFINITIONS: tuple[SkillDefinition, ...] = (
    SkillDefinition("sostenibilidad", "ambiental", "tecnica", aliases=("sustentabilidad", "desarrollo sostenible")),
    SkillDefinition("esg", "ambiental", "tecnica", aliases=("criterios esg", "environmental social governance")),
    SkillDefinition("iso 14001", "ambiental", "certificacion", aliases=("sistema de gestion ambiental", "gestion ambiental iso 14001")),
    SkillDefinition("huella de carbono", "ambiental", "tecnica", aliases=("carbon footprint", "inventario gei", "gases efecto invernadero")),
    SkillDefinition("licenciamiento ambiental", "ambiental", "tecnica", aliases=("permisos ambientales", "evaluacion impacto ambiental")),
    SkillDefinition("economia circular", "ambiental", "tecnica", aliases=("circular economy",)),
    SkillDefinition("gestion de residuos", "ambiental", "tecnica", aliases=("residuos solidos", "manejo de residuos")),
    SkillDefinition("eficiencia energetica", "energia", "tecnica", aliases=("uso eficiente energia", "ahorro energetico")),
    SkillDefinition("transicion energetica", "energia", "tecnica", aliases=("energy transition",)),
    SkillDefinition("energias renovables", "energia", "tecnica", aliases=("energia renovable", "solar", "eolica", "fotovoltaica")),
    SkillDefinition("iso 50001", "energia", "certificacion", aliases=("sistema de gestion energetica",)),
    SkillDefinition("auditoria energetica", "energia", "tecnica", aliases=("diagnostico energetico",)),
    SkillDefinition("proteccion de datos", "legal-tech", "tecnica", aliases=("habeas data", "privacy", "privacidad")),
    SkillDefinition("derecho digital", "legal-tech", "tecnica", aliases=("derecho informatico", "legaltech")),
    SkillDefinition("contratos tecnologicos", "legal-tech", "tecnica", aliases=("contratacion tecnologica",)),
    SkillDefinition("propiedad intelectual", "legal-tech", "tecnica", aliases=("derechos de autor", "marcas")),
    SkillDefinition("compliance", "legal", "tecnica", aliases=("cumplimiento normativo", "regulatory compliance")),
    SkillDefinition("sarlaft", "legal", "tecnica", aliases=("aml", "cft", "lavado de activos")),
    SkillDefinition("seguridad del paciente", "salud", "tecnica", aliases=("patient safety",)),
    SkillDefinition("epidemiologia", "salud", "tecnica", aliases=("vigilancia epidemiologica",)),
    SkillDefinition("diseno curricular", "educacion", "tecnica", aliases=("curriculum design", "curriculo")),
    SkillDefinition("learning analytics", "educacion", "tecnica", aliases=("analitica de aprendizaje",)),
    SkillDefinition("seo", "marketing", "herramienta", aliases=("search engine optimization",)),
    SkillDefinition("crm", "marketing", "herramienta", aliases=("customer relationship management",)),
    SkillDefinition("power bi", "analitica", "herramienta", aliases=("powerbi", "microsoft power bi", "pbi")),
    SkillDefinition("business intelligence", "analitica", "tecnica", aliases=("bi", "inteligencia de negocios")),
    SkillDefinition("visual analytics", "analitica", "tecnica", aliases=("visualizacion de datos", "data visualization")),
    SkillDefinition("sql", "analitica", "herramienta", aliases=("postgresql", "sql server", "bases de datos sql")),
    SkillDefinition("python", "ti", "herramienta", aliases=("python programming",)),
    SkillDefinition("backend", "ti", "tecnica", aliases=("back end", "server side")),
    SkillDefinition("fullstack", "ti", "tecnica", aliases=("full stack", "full-stack")),
    SkillDefinition("devops", "ti", "tecnica", aliases=("ci cd", "cicd")),
    SkillDefinition("iso 27001", "cybersecurity", "certificacion", aliases=("seguridad informacion", "isms")),
    SkillDefinition("siem", "cybersecurity", "herramienta", aliases=("security information event management",)),
    SkillDefinition("gestion de proyectos", "management", "tecnica", aliases=("project management", "pmbok")),
    SkillDefinition("liderazgo", "management", "blanda", aliases=("leadership",)),
)


DOMAIN_BY_CODE = {domain.code: domain for domain in DOMAIN_DEFINITIONS}
SKILL_BY_CANONICAL = {skill.canonical_name: skill for skill in SKILL_DEFINITIONS}


def iter_alias_rows() -> Iterable[tuple[str, str]]:
    for skill in SKILL_DEFINITIONS:
        yield skill.canonical_name, skill.canonical_name
        for alias in skill.aliases:
            yield alias, skill.canonical_name

