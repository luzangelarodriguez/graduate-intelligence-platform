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
            "big data",
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
    DomainDefinition(
        "transversal",
        "Competencias transversales",
        "Competencias humanas, comunicativas y de colaboracion que no deben contaminar dominios tecnicos.",
        (
            "liderazgo",
            "pensamiento critico",
            "trabajo en equipo",
            "comunicacion",
            "resolucion de problemas",
            "colaboracion",
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
    SkillDefinition("sql", "analitica", "database", aliases=("sql server", "bases de datos sql")),
    SkillDefinition("big data", "analitica", "tecnica", aliases=("bigdata", "datos masivos", "procesamiento masivo de datos")),
    SkillDefinition("machine learning", "analitica", "technical_skill", aliases=("aprendizaje automatico", "aprendizaje automático", "aprendizaje supervisado", "aprendizaje no supervisado", "random forest", "naive bayes", "redes neuronales")),
    SkillDefinition("ia", "analitica", "technical_skill", aliases=("inteligencia artificial", "ai", "artificial intelligence")),
    SkillDefinition("scikit-learn", "analitica", "tool", aliases=("sklearn", "scikit learn")),
    SkillDefinition("notebooks", "analitica", "tool", aliases=("jupyter", "jupyter notebook", "cuadernos")),
    SkillDefinition("mlops", "analitica", "methodology", aliases=("machine learning operations", "operaciones ml")),
    SkillDefinition("python", "ti", "programming_language", aliases=("python programming",)),
    SkillDefinition("java", "ti", "programming_language", aliases=("java se", "java ee")),
    SkillDefinition("c#", "ti", "programming_language", aliases=("c sharp", "csharp")),
    SkillDefinition("php", "ti", "programming_language", aliases=("php programming",)),
    SkillDefinition("kotlin", "ti", "programming_language", aliases=("kotlin android",)),
    SkillDefinition("swift", "ti", "programming_language", aliases=("swift ios",)),
    SkillDefinition("javascript", "ti", "programming_language", aliases=("js", "ecmascript")),
    SkillDefinition("backend", "ti", "technical_skill", aliases=("back end", "server side", "desarrollo backend")),
    SkillDefinition("frontend", "ti", "technical_skill", aliases=("front end", "interfaces web", "desarrollo frontend")),
    SkillDefinition("fullstack", "ti", "tecnica", aliases=("full stack", "full-stack")),
    SkillDefinition("api", "ti", "technical_skill", aliases=("apis", "rest api", "api rest", "restful", "servicios web")),
    SkillDefinition("cloud", "ti", "technical_skill", aliases=("cloud computing", "computacion en la nube", "nube")),
    SkillDefinition("devops", "ti", "methodology", aliases=("dev ops",)),
    SkillDefinition("ci cd", "ti", "methodology", aliases=("ci/cd", "cicd", "integracion continua", "despliegue continuo")),
    SkillDefinition("spring boot", "ti", "framework", aliases=("springboot", "spring framework")),
    SkillDefinition(".net", "ti", "framework", aliases=("net framework", "dotnet", "asp.net", "visual studio .net")),
    SkillDefinition("android", "ti", "technical_skill", aliases=("android development", "desarrollo android", "desarrollo movil android")),
    SkillDefinition("react", "ti", "framework", aliases=("reactjs", "react.js")),
    SkillDefinition("angular", "ti", "framework", aliases=("angularjs",)),
    SkillDefinition("vue", "ti", "framework", aliases=("vue.js", "vuejs")),
    SkillDefinition("node.js", "ti", "framework", aliases=("nodejs", "node js")),
    SkillDefinition("express", "ti", "framework", aliases=("express.js", "expressjs")),
    SkillDefinition("django", "ti", "framework", aliases=("django framework",)),
    SkillDefinition("flask", "ti", "framework", aliases=("flask python",)),
    SkillDefinition("postgresql", "ti", "database", aliases=("postgres", "postgres sql")),
    SkillDefinition("mysql", "ti", "database", aliases=("my sql",)),
    SkillDefinition("mariadb", "ti", "database", aliases=("maria db",)),
    SkillDefinition("mongodb", "ti", "database", aliases=("mongo db", "mongo")),
    SkillDefinition("firebase", "ti", "platform", aliases=("google firebase",)),
    SkillDefinition("docker", "ti", "tool", aliases=("containers", "contenedores docker")),
    SkillDefinition("kubernetes", "ti", "tool", aliases=("k8s",)),
    SkillDefinition("jenkins", "ti", "tool", aliases=("jenkins pipeline",)),
    SkillDefinition("github actions", "ti", "tool", aliases=("github action", "gh actions")),
    SkillDefinition("terraform", "ti", "tool", aliases=("iac terraform",)),
    SkillDefinition("aws", "ti", "cloud_provider", aliases=("amazon web services",)),
    SkillDefinition("azure", "ti", "cloud_provider", aliases=("microsoft azure",)),
    SkillDefinition("google cloud", "ti", "cloud_provider", aliases=("google cloud platform", "gcp")),
    SkillDefinition("kafka", "ti", "tool", aliases=("apache kafka",)),
    SkillDefinition("redis", "ti", "database", aliases=("redis cache",)),
    SkillDefinition("rabbitmq", "ti", "tool", aliases=("rabbit mq",)),
    SkillDefinition("eclipse", "ti", "tool", aliases=("eclipse ide",)),
    SkillDefinition("netbeans", "ti", "tool", aliases=("netbeans ide",)),
    SkillDefinition("android studio", "ti", "tool", aliases=("android ide",)),
    SkillDefinition("tableau", "analitica", "tool", aliases=("tableau desktop",)),
    SkillDefinition("etl", "analitica", "technical_skill", aliases=("extract transform load", "procesos etl")),
    SkillDefinition("iso 27001", "cybersecurity", "certificacion", aliases=("seguridad informacion", "isms")),
    SkillDefinition("siem", "cybersecurity", "herramienta", aliases=("security information event management",)),
    SkillDefinition("excel avanzado", "finanzas", "tool", aliases=("microsoft excel", "excel", "analisis financiero con microsoft excel")),
    SkillDefinition("power bi financiero", "finanzas", "tool", aliases=("power bi finanzas", "power bi financiero")),
    SkillDefinition("modelacion financiera", "finanzas", "technical_skill", aliases=("modelizacion financiera", "valoracion de inversiones", "van", "tir", "wacc", "capm")),
    SkillDefinition("analisis de escenarios", "finanzas", "technical_skill", aliases=("analisis de sensibilidad", "análisis de sensibilidad", "escenarios financieros")),
    SkillDefinition("indicadores financieros", "finanzas", "technical_skill", aliases=("kpi financieros", "rentabilidad", "riesgo financiero", "flujos de caja")),
    SkillDefinition("innovacion", "management", "technical_skill", aliases=("innovación", "i+d+i", "gestion de la innovacion", "gestión de la innovación")),
    SkillDefinition("design thinking", "management", "methodology", aliases=("pensamiento de diseño", "diseno centrado en usuario", "diseño centrado en usuario")),
    SkillDefinition("vigilancia tecnologica", "management", "technical_skill", aliases=("vigilancia tecnológica", "prospectiva tecnologica", "prospectiva tecnológica")),
    SkillDefinition("inteligencia competitiva", "management", "technical_skill", aliases=("competitive intelligence",)),
    SkillDefinition("gestion de proyectos", "management", "tecnica", aliases=("project management", "pmbok")),
    SkillDefinition("liderazgo", "transversal", "transversal_skill", aliases=("leadership",)),
    SkillDefinition("pensamiento critico", "transversal", "transversal_skill", aliases=("pensamiento crítico", "critical thinking")),
    SkillDefinition("trabajo en equipo", "transversal", "transversal_skill", aliases=("teamwork", "colaboracion")),
)


DOMAIN_BY_CODE = {domain.code: domain for domain in DOMAIN_DEFINITIONS}
SKILL_BY_CANONICAL = {skill.canonical_name: skill for skill in SKILL_DEFINITIONS}


def iter_alias_rows() -> Iterable[tuple[str, str]]:
    for skill in SKILL_DEFINITIONS:
        yield skill.canonical_name, skill.canonical_name
        for alias in skill.aliases:
            yield alias, skill.canonical_name
