from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re
import unicodedata
from typing import Any, Iterable, Sequence

from backend.repositories.base import fetch_all


DOMAIN_ORDER: list[str] = [
    "criminology_security",
    "cybersecurity",
    "artificial_intelligence",
    "data_analytics",
    "finance_accounting",
    "project_management",
    "business_management",
    "marketing_commercial",
    "logistics_operations",
    "legal_compliance",
    "education",
    "health",
]

DOMAIN_LABELS: dict[str, str] = {
    "data_analytics": "Data & Analytics",
    "artificial_intelligence": "Artificial Intelligence",
    "cybersecurity": "Cybersecurity",
    "criminology_security": "Criminology & Security",
    "finance_accounting": "Finance & Accounting",
    "project_management": "Project Management",
    "business_management": "Business Management",
    "marketing_commercial": "Marketing & Commercial",
    "logistics_operations": "Logistics & Operations",
    "education": "Education",
    "health": "Health",
    "legal_compliance": "Legal & Compliance",
}

PROGRAM_DOMAIN_SEEDS: tuple[dict[str, str], ...] = (
    {"program_name": "Especialización en Criminología", "domain_key": "criminology_security", "domain_label": "Criminology & Security"},
    {"program_name": "Especialización en Administración y Gerencia de la Salud", "domain_key": "health", "domain_label": "Health"},
    {"program_name": "Especialización en Alta Gerencia", "domain_key": "business_management", "domain_label": "Business Management"},
    {"program_name": "Especialización en Derecho de la Empresa", "domain_key": "legal_compliance", "domain_label": "Legal & Compliance"},
    {"program_name": "Especialización en Derecho Digital", "domain_key": "legal_compliance", "domain_label": "Legal & Compliance"},
    {"program_name": "Especialización en Derechos Humanos", "domain_key": "legal_compliance", "domain_label": "Legal & Compliance"},
    {"program_name": "Especialización en Dirección Comercial y Ventas", "domain_key": "marketing_commercial", "domain_label": "Marketing & Commercial"},
    {"program_name": "Especialización en Dirección y Gestión de Proyectos", "domain_key": "project_management", "domain_label": "Project Management"},
    {"program_name": "Especialización en Dirección y Gestión de Tecnologías de la Información", "domain_key": "data_analytics", "domain_label": "Data & Analytics"},
    {"program_name": "Especialización en Educación Inclusiva", "domain_key": "education", "domain_label": "Education"},
    {"program_name": "Especialización en Educación y Orientación Familiar", "domain_key": "education", "domain_label": "Education"},
    {"program_name": "Especialización en Gerencia Educativa", "domain_key": "education", "domain_label": "Education"},
    {"program_name": "Especialización en Gerencia Financiera", "domain_key": "finance_accounting", "domain_label": "Finance & Accounting"},
    {"program_name": "Especialización en Gestión Ambiental y Energética", "domain_key": "logistics_operations", "domain_label": "Logistics & Operations"},
    {"program_name": "Especialización en Gestión de la Seguridad y Salud en el Trabajo", "domain_key": "health", "domain_label": "Health"},
    {"program_name": "Especialización en Gestión Humana", "domain_key": "business_management", "domain_label": "Business Management"},
    {"program_name": "Especialización en Gestión Pública", "domain_key": "legal_compliance", "domain_label": "Legal & Compliance"},
    {"program_name": "Especialización en Ingeniería de Software", "domain_key": "data_analytics", "domain_label": "Data & Analytics"},
    {"program_name": "Especialización en Inteligencia Artificial", "domain_key": "artificial_intelligence", "domain_label": "Artificial Intelligence"},
    {"program_name": "Especialización en Inteligencia de Negocio", "domain_key": "data_analytics", "domain_label": "Data & Analytics"},
    {"program_name": "Especialización en Marketing Digital", "domain_key": "marketing_commercial", "domain_label": "Marketing & Commercial"},
    {"program_name": "Especialización en Neuropsicología y Educación", "domain_key": "education", "domain_label": "Education"},
    {"program_name": "Especialización en Pedagogía y Docencia", "domain_key": "education", "domain_label": "Education"},
    {"program_name": "Especialización en Revisoría Fiscal y Auditoría de Cuentas", "domain_key": "finance_accounting", "domain_label": "Finance & Accounting"},
    {"program_name": "Especialización en Seguridad Informática", "domain_key": "cybersecurity", "domain_label": "Cybersecurity"},
    {"program_name": "Especialización en TIC para la Enseñanza", "domain_key": "education", "domain_label": "Education"},
    {"program_name": "Especialización en Visual Analytics y Big Data", "domain_key": "data_analytics", "domain_label": "Data & Analytics"},
)

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "criminology_security": [
        "criminology",
        "criminological",
        "criminal investigation",
        "criminal intelligence",
        "forensic analysis",
        "forensic science",
        "forensic",
        "crime prevention",
        "organized crime",
        "organised crime",
        "cybercrime",
        "financial crime",
        "public safety",
        "chain of custody",
        "trafficking",
        "traffick",
        "osint",
        "law enforcement",
        "policing",
        "security operations",
        "physical security",
        "loss prevention",
        "security guard",
        "surveillance",
        "protective services",
        "prosecutor",
        "prosecution",
        "public prosecutor",
        "europol",
        "interpol",
        "unodc",
        "fiscalia",
        "procuraduria",
        "defensoria",
        "crime",
        "investigation",
    ],
    "cybersecurity": [
        "cybersecurity",
        "ciberseguridad",
        "seguridad informatica",
        "seguridad de redes",
        "information security",
        "infosec",
        "security architecture",
        "security engineering",
        "security analyst",
        "security operations center",
        "soc",
        "siem",
        "devsecops",
        "pentest",
        "penetration testing",
        "vulnerability",
        "threat",
        "zero trust",
        "identity",
        "iam",
        "malware",
        "digital forensics",
        "respuesta a incidentes",
        "incident response",
        "criptografia",
        "cryptography",
        "security",
    ],
    "artificial_intelligence": [
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "mlops",
        "prompt engineering",
        "large language model",
        "llm",
        "generative ai",
        "genai",
        "computer vision",
        "natural language",
        "nlp",
        "tensorflow",
        "pytorch",
        "ai ",
        " ai",
    ],
    "data_analytics": [
        "data analytics",
        "data analysis",
        "analytics",
        "business intelligence",
        "visual analytics",
        "dashboard",
        "reporting",
        "power bi",
        "tableau",
        "qlik",
        "looker",
        "etl",
        "data warehouse",
        "data lake",
        "data modeling",
        "statistics",
        "sql",
        "dax",
        "big data",
        "data science",
        "data governance",
        "data storytelling",
        "software",
        "developer",
        "engineering",
        "cloud",
        "api",
        "systems",
        "technology",
        "information technology",
        "it ",
        " backend",
        " frontend",
        "full stack",
    ],
    "finance_accounting": [
        "finance",
        "accounting",
        "audit",
        "auditoria",
        "controller",
        "treasury",
        "fiscal",
        "tax",
        "ifrs",
        "gaap",
        "financial analysis",
        "aml",
        "cft",
        "fraud",
        "bookkeeping",
    ],
    "project_management": [
        "project management",
        "project manager",
        "program management",
        "pmo",
        "agile",
        "scrum",
        "kanban",
        "roadmap",
        "stakeholder",
        "delivery",
        "planning",
        "governance",
    ],
    "business_management": [
        "business",
        "management",
        "leadership",
        "strategy",
        "administration",
        "manager",
        "organizational",
        "operations management",
        "general management",
        "corporate",
    ],
    "marketing_commercial": [
        "marketing",
        "sales",
        "commercial",
        "crm",
        "branding",
        "growth",
        "customer success",
        "revenue",
        "ecommerce",
        "commerce",
        "trade",
        "market",
        "merchandising",
    ],
    "logistics_operations": [
        "logistics",
        "supply chain",
        "warehouse",
        "inventory",
        "procurement",
        "purchasing",
        "transport",
        "transportation",
        "operations",
        "manufacturing",
        "production",
        "lean",
        "six sigma",
        "process improvement",
        "distribution",
    ],
    "legal_compliance": [
        "legal",
        "law",
        "compliance",
        "regulatory",
        "privacy",
        "contract",
        "governance",
        "due diligence",
        "litigation",
        "arbitration",
        "abogado",
        "legal analysis",
        "corporate law",
        "contract drafting",
        "aml/cft",
        "sagrilaft",
        "sarlaft",
    ],
    "education": [
        "education",
        "pedagogy",
        "curriculum",
        "instructional",
        "teaching",
        "learning",
        "lms",
        "assessment",
        "didactic",
        "didactics",
        "school",
        "education management",
    ],
    "health": [
        "health",
        "public health",
        "clinical",
        "patient",
        "hospital",
        "nursing",
        "epidemiology",
        "occupational health",
        "medical",
        "care",
        "health management",
    ],
}

DOMAIN_RELATIONS: dict[str, set[str]] = {
    "data_analytics": {
        "artificial_intelligence",
        "cybersecurity",
        "finance_accounting",
        "project_management",
        "business_management",
        "marketing_commercial",
        "logistics_operations",
        "legal_compliance",
        "education",
        "health",
        "criminology_security",
    },
    "artificial_intelligence": {
        "data_analytics",
        "cybersecurity",
        "project_management",
        "business_management",
        "education",
        "health",
        "criminology_security",
    },
    "cybersecurity": {
        "data_analytics",
        "artificial_intelligence",
        "criminology_security",
        "legal_compliance",
        "finance_accounting",
        "business_management",
        "project_management",
    },
    "criminology_security": {
        "cybersecurity",
        "legal_compliance",
        "finance_accounting",
        "health",
        "project_management",
    },
    "finance_accounting": {
        "data_analytics",
        "project_management",
        "business_management",
        "marketing_commercial",
        "legal_compliance",
    },
    "project_management": {
        "data_analytics",
        "artificial_intelligence",
        "cybersecurity",
        "finance_accounting",
        "business_management",
        "marketing_commercial",
        "logistics_operations",
        "education",
        "health",
        "legal_compliance",
        "criminology_security",
    },
    "business_management": {
        "data_analytics",
        "finance_accounting",
        "project_management",
        "marketing_commercial",
        "logistics_operations",
        "legal_compliance",
    },
    "marketing_commercial": {
        "data_analytics",
        "business_management",
        "project_management",
        "logistics_operations",
    },
    "logistics_operations": {
        "data_analytics",
        "business_management",
        "project_management",
        "finance_accounting",
        "marketing_commercial",
    },
    "legal_compliance": {
        "data_analytics",
        "cybersecurity",
        "criminology_security",
        "finance_accounting",
        "business_management",
        "project_management",
        "health",
    },
    "education": {
        "data_analytics",
        "project_management",
        "business_management",
        "health",
        "legal_compliance",
    },
    "health": {
        "data_analytics",
        "project_management",
        "business_management",
        "legal_compliance",
        "criminology_security",
    },
    "data_engineering": {
        "data_analytics",
        "artificial_intelligence",
        "project_management",
    },
    "software_engineering": {
        "data_analytics",
        "artificial_intelligence",
        "project_management",
        "business_management",
        "cybersecurity",
    },
    "cloud_infrastructure": {
        "cybersecurity",
        "software_engineering",
        "devops_platform",
        "data_analytics",
    },
    "devops_platform": {
        "software_engineering",
        "cloud_infrastructure",
        "cybersecurity",
        "data_analytics",
    },
    "technical_support": {
        "software_engineering",
        "cloud_infrastructure",
        "business_management",
    },
    "marketing_sales": {
        "business_management",
        "project_management",
    },
    "public_administration": {
        "legal_compliance",
        "business_management",
    },
}

JOB_DOMAIN_ORDER: list[str] = [
    "criminology_security",
    "data_analytics",
    "legal_compliance",
    "education",
    "health",
    "public_administration",
    "marketing_sales",
    "artificial_intelligence",
    "data_engineering",
    "software_engineering",
    "cloud_infrastructure",
    "devops_platform",
    "technical_support",
    "project_management",
    "business_management",
    "finance_accounting",
    "cybersecurity",
]

JOB_DOMAIN_LABELS: dict[str, str] = {
    "criminology_security": "Criminology & Security",
    "artificial_intelligence": "Artificial Intelligence",
    "data_engineering": "Data Engineering",
    "software_engineering": "Software Engineering",
    "cloud_infrastructure": "Cloud Infrastructure",
    "devops_platform": "DevOps Platform",
    "technical_support": "Technical Support",
    "project_management": "Project Management",
    "business_management": "Business Management",
    "marketing_sales": "Marketing & Sales",
    "finance_accounting": "Finance & Accounting",
    "legal_compliance": "Legal & Compliance",
    "public_administration": "Public Administration",
    "education": "Education",
    "health": "Health",
    "cybersecurity": "Cybersecurity",
    "data_analytics": "Data & Analytics",
}

JOB_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "criminology_security": [
        "criminology",
        "criminological",
        "criminal psychology",
        "forensic psychology",
        "victimology",
        "victimization",
        "victim support",
        "criminal investigation",
        "criminal intelligence",
        "crime analyst",
        "intelligence analyst",
        "forensic analysis",
        "forensic science",
        "forensic examiner",
        "forensic support",
        "digital forensics",
        "criminalistics",
        "criminalist",
        "profiling",
        "criminal profiling",
        "risk assessment",
        "reincidence",
        "recidivism",
        "counter terrorism",
        "terrorism",
        "organized crime",
        "organised crime",
        "cybercrime",
        "law enforcement",
        "policing",
        "security operations",
        "physical security",
        "loss prevention",
        "security guard",
        "security officer",
        "surveillance",
        "protective services",
        "europol",
        "interpol",
        "unodc",
        "fiscalia",
        "procuraduria",
        "defensoria",
        "crime",
        "investigation",
    ],
    "artificial_intelligence": [
        "artificial intelligence",
        "ai specialist",
        "ai architect",
        "machine learning",
        "deep learning",
        "mlops",
        "large language model",
        "llm",
        "generative ai",
        "genai",
        "prompt engineer",
        "prompt engineering",
        "copilot",
        "github copilot",
        "computer vision",
        "natural language processing",
        "nlp",
        "tensorflow",
        "pytorch",
    ],
    "data_engineering": [
        "data engineering",
        "data engineer",
        "etl",
        "data warehouse",
        "data lake",
        "data integration",
        "data pipeline",
        "data architect",
        "data orchestration",
        "apache airflow",
        "dbt",
        "spark",
        "hadoop",
        "big data",
        "data model",
        "data modeling",
    ],
    "software_engineering": [
        "software engineering",
        "software engineer",
        "software developer",
        "software architect",
        "backend",
        "frontend",
        "full stack",
        "fullstack",
        "desarrollador",
        "developer",
        "programmer",
        "java",
        ".net",
        "dotnet",
        "spring",
        "node",
        "angular",
        "react",
        "api",
    ],
    "cloud_infrastructure": [
        "cloud infrastructure",
        "cloud engineer",
        "cloud architect",
        "cloud platform",
        "platform engineer",
        "infrastructure engineer",
        "administrator of platforms",
        "administrador de plataformas",
        "administrator of servers",
        "administrador de servidores",
        "server administrator",
        "administrador linux",
        "linux",
        "oracle",
        "weblogic",
        "middleware",
        "vmware",
        "virtualization",
        "virtualizacion",
        "aws",
        "azure infrastructure",
        "infrastructure",
        "servers",
        "server",
        "dba",
        "database administrator",
        "solution architect",
        "arquitecto de soluciones",
    ],
    "devops_platform": [
        "devops",
        "sre",
        "site reliability",
        "platform engineering",
        "platform engineer",
        "kubernetes",
        "docker",
        "ci/cd",
        "continuous integration",
        "continuous delivery",
        "automation",
        "release engineering",
    ],
    "technical_support": [
        "technical support",
        "tech support",
        "help desk",
        "service desk",
        "mesa de ayuda",
        "soporte tecnico",
        "soporte",
        "desktop support",
        "application support",
        "support engineer",
    ],
    "project_management": [
        "project management",
        "project manager",
        "program management",
        "pmo",
        "scrum master",
        "product owner",
        "analista de proyectos",
        "project coordinator",
        "project analyst",
        "delivery manager",
    ],
    "business_management": [
        "business management",
        "business",
        "management",
        "gerente",
        "director",
        "consultor negocio",
        "consultor de negocio",
        "business development",
        "account executive",
        "account manager",
        "executive",
        "lead",
        "manager",
    ],
    "marketing_sales": [
        "marketing",
        "marketing digital",
        "digital marketing",
        "sales",
        "commercial",
        "ejecutivo comercial",
        "ejecutiva comercial",
        "asesor comercial",
        "executivo de ventas",
        "sales executive",
        "sales representative",
        "sales manager",
        "vendedor",
        "ventas",
        "mercadeo",
        "crm",
        "branding",
        "growth",
        "customer success",
        "revenue",
        "ecommerce",
        "commerce",
        "trade marketing",
        "business development",
        "account executive",
        "account manager",
    ],
    "finance_accounting": [
        "finance",
        "financial",
        "accounting",
        "accountant",
        "contador",
        "contabilidad",
        "audit",
        "auditor",
        "auditoria",
        "controller",
        "financial controller",
        "tax",
        "tributary",
        "fiscal",
        "ifrs",
        "niif",
        "gaap",
        "aml",
        "cft",
        "fraud",
        "bookkeeping",
    ],
    "legal_compliance": [
        "legal",
        "law",
        "compliance",
        "compliance officer",
        "compliance analyst",
        "regulatory",
        "regulatory affairs",
        "privacy",
        "data protection",
        "data protection officer",
        "contract",
        "contract management",
        "due diligence",
        "litigation",
        "arbitration",
        "abogado",
        "lawyer",
        "attorney",
        "legal counsel",
        "legal advisor",
        "legal analysis",
        "corporate law",
        "contract drafting",
        "aml/cft",
        "sagrilaft",
        "sarlaft",
        "governance",
        "corporate governance",
        "ethics",
        "risk and compliance",
        "juridico",
        "juridica",
        "dpo",
    ],
    "public_administration": [
        "public administration",
        "public sector",
        "government",
        "public policy",
        "public affairs",
        "government affairs",
        "state",
        "municipal",
        "administracion publica",
        "gestion publica",
        "public management",
        "public service",
        "administration",
        "civil service",
        "institutional",
        "institucional",
        "policy",
    ],
    "education": [
        "education",
        "educacion",
        "pedagogy",
        "pedagogia",
        "curriculum",
        "curricular",
        "curriculo",
        "instructional",
        "instructional designer",
        "instructional design",
        "teaching",
        "teacher",
        "docente",
        "profesor",
        "maestro",
        "tutor",
        "learning",
        "lms",
        "assessment",
        "didactic",
        "didactics",
        "school",
        "educator",
        "academic coordinator",
        "coordinador academico",
        "coordinador curricular",
        "coordinador de programa",
        "education management",
        "educational technology",
        "educational technology specialist",
        "e learning",
        "elearning",
        "aula virtual",
    ],
    "health": [
        "health",
        "salud",
        "public health",
        "clinical",
        "clinico",
        "patient",
        "paciente",
        "hospital",
        "nursing",
        "nurse",
        "epidemiology",
        "occupational health",
        "medical",
        "medico",
        "care",
        "health management",
        "healthcare",
        "health care",
        "healthcare manager",
        "health services",
        "eps",
        "ips",
    ],
    "cybersecurity": [
        "cybersecurity",
        "ciberseguridad",
        "information security",
        "infosec",
        "security architecture",
        "security engineering",
        "security analyst",
        "security operations center",
        "soc",
        "siem",
        "devsecops",
        "pentest",
        "penetration testing",
        "vulnerability",
        "threat hunting",
        "threat intelligence",
        "zero trust",
        "identity and access management",
        "iam",
        "malware",
        "incident response",
        "cryptography",
        "security incident",
        "security compliance",
    ],
    "data_analytics": [
        "data analytics",
        "data analysis",
        "business intelligence",
        "inteligencia de negocios",
        "visual analytics",
        "power bi",
        "powerbi",
        "power bi developer",
        "tableau",
        "qlik",
        "looker",
        "analytics engineer",
        "business intelligence analyst",
        "analista de inteligencia de negocios",
        "bi analyst",
        "analista bi",
        "data analyst",
        "analista de datos",
        "reporting analyst",
        "dax",
        "data visualization",
        "visual analytics",
        "visualization",
        "visualizacion de datos",
        "kpi",
    ],
}


@dataclass(frozen=True)
class DomainMatch:
    domain: str
    label: str
    confidence: float
    signals: tuple[str, ...]


def normalize_domain_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def domain_label(domain: str) -> str:
    return DOMAIN_LABELS.get(domain, domain)


def related_domains(domain: str) -> set[str]:
    return set(DOMAIN_RELATIONS.get(domain, set()))


def domain_weight(left_domain: str, right_domain: str) -> float:
    if not left_domain or not right_domain:
        return 0.1
    if left_domain == right_domain:
        return 1.0
    if right_domain in DOMAIN_RELATIONS.get(left_domain, set()) or left_domain in DOMAIN_RELATIONS.get(right_domain, set()):
        return 0.5
    return 0.1


def _program_seed_lookup() -> dict[str, tuple[str, str]]:
    return {
        normalize_domain_text(item["program_name"]): (item["domain_key"], item["domain_label"])
        for item in PROGRAM_DOMAIN_SEEDS
        if normalize_domain_text(item["program_name"])
    }


def resolve_program_domain_override(program_name: Any = "", *, program_id: int | None = None, db_name: str | None = None) -> DomainMatch | None:
    if program_id is not None:
        try:
            rows = fetch_all(
                """
                SELECT domain_key, domain_label
                FROM public.program_domain_mapping
                WHERE program_id = %s
                LIMIT 1
                """,
                (int(program_id),),
                db_name=db_name,
            )
            if rows:
                row = rows[0]
                domain_key = str(row.get("domain_key") or "").strip()
                if domain_key:
                    domain_label_value = str(row.get("domain_label") or domain_label(domain_key))
                    return DomainMatch(domain=domain_key, label=domain_label_value, confidence=1.0, signals=("program_domain_mapping",))
        except Exception:
            pass

    normalized_name = normalize_domain_text(program_name)
    if not normalized_name:
        return None

    seed_lookup = _program_seed_lookup()
    seeded = seed_lookup.get(normalized_name)
    if seeded:
        domain_key, domain_label_value = seeded
        return DomainMatch(domain=domain_key, label=domain_label_value, confidence=1.0, signals=("program_domain_seed",))

    if not any(marker in normalized_name for marker in ("especializacion", "maestria", "pregrado", "licenciatura", "programa")):
        return None

    try:
        rows = fetch_all(
            """
            SELECT domain_key, domain_label
            FROM public.program_domain_mapping
            WHERE lower(unaccent(COALESCE(program_name, ''))) = %s
            LIMIT 1
            """,
            (normalized_name,),
            db_name=db_name,
        )
        if rows:
            row = rows[0]
            domain_key = str(row.get("domain_key") or "").strip()
            if domain_key:
                domain_label_value = str(row.get("domain_label") or domain_label(domain_key))
                return DomainMatch(domain=domain_key, label=domain_label_value, confidence=1.0, signals=("program_domain_mapping",))
    except Exception:
        pass
    return None


def _score_domain(text: str, domain: str, *, domain_keywords: dict[str, list[str]]) -> tuple[int, tuple[str, ...]]:
    if not text:
        return 0, ()
    hits = tuple(keyword for keyword in domain_keywords.get(domain, []) if keyword in text)
    return len(hits), hits


def infer_domain_from_texts(
    texts: Sequence[Any],
    *,
    default: str = "business_management",
    domain_order: Sequence[str] | None = None,
    domain_keywords: dict[str, list[str]] | None = None,
) -> DomainMatch:
    normalized_text = " ".join(normalize_domain_text(item) for item in texts if normalize_domain_text(item))
    ordered_domains = tuple(domain_order or DOMAIN_ORDER)
    keyword_catalog = domain_keywords or DOMAIN_KEYWORDS
    best_domain = default
    best_hits: tuple[str, ...] = ()
    best_score = -1
    for domain in ordered_domains:
        score, hits = _score_domain(normalized_text, domain, domain_keywords=keyword_catalog)
        if score > best_score:
            best_domain = domain
            best_hits = hits
            best_score = score
    if best_score <= 0:
        return DomainMatch(domain=default, label=domain_label(default), confidence=0.2, signals=())
    confidence = min(0.98, 0.35 + (best_score * 0.12) + (len(best_hits) * 0.03))
    return DomainMatch(domain=best_domain, label=domain_label(best_domain), confidence=round(confidence, 3), signals=best_hits)


def infer_skill_domain(skill: Any, *, category: str | None = None, family: str | None = None) -> DomainMatch:
    parts = [skill, category or "", family or ""]
    return infer_domain_from_texts(parts, default="data_analytics")


def infer_program_domain(
    name: Any,
    *,
    faculty: Any = "",
    role: Any = "",
    skills: Sequence[Any] | None = None,
) -> DomainMatch:
    override = resolve_program_domain_override(name)
    if override is not None:
        return override
    parts: list[Any] = [name, faculty, role]
    if skills:
        parts.extend(skills)
    return infer_domain_from_texts(parts, default="business_management")


def classify_skill_key(skill: Any, *, category: str | None = None, family: str | None = None) -> tuple[str, str, float, tuple[str, ...]]:
    result = infer_skill_domain(skill, category=category, family=family)
    return result.domain, result.label, result.confidence, result.signals


def classify_program_key(name: Any, *, faculty: Any = "", role: Any = "", skills: Sequence[Any] | None = None) -> tuple[str, str, float, tuple[str, ...]]:
    result = infer_program_domain(name, faculty=faculty, role=role, skills=skills)
    return result.domain, result.label, result.confidence, result.signals


def classify_job_key(
    title: Any,
    *,
    source: Any = "",
    industry: Any = "",
    description: Any = "",
    responsibilities: Any = "",
    requirements: Any = "",
    skills: Sequence[Any] | None = None,
) -> tuple[str, str, float, tuple[str, ...]]:
    result = infer_job_domain(
        title,
        source=source,
        industry=industry,
        description=description,
        responsibilities=responsibilities,
        requirements=requirements,
        skills=skills,
    )
    return result.domain, result.label, result.confidence, result.signals


def infer_job_domain(
    title: Any,
    *,
    source: Any = "",
    industry: Any = "",
    description: Any = "",
    responsibilities: Any = "",
    requirements: Any = "",
    skills: Sequence[Any] | None = None,
) -> DomainMatch:
    title_result = infer_domain_from_texts(
        [title, title, title],
        default="business_management",
        domain_order=JOB_DOMAIN_ORDER,
        domain_keywords=JOB_DOMAIN_KEYWORDS,
    )
    if title_result.signals:
        return title_result

    parts: list[Any] = [source, industry, description, responsibilities, requirements]
    if skills:
        parts.extend(skills)
        parts.extend(skills)
    return infer_domain_from_texts(parts, default="business_management", domain_order=JOB_DOMAIN_ORDER, domain_keywords=JOB_DOMAIN_KEYWORDS)


def _sql_like_clauses(expression_sql: str, keywords: Sequence[str]) -> str:
    clauses: list[str] = []
    for keyword in keywords:
        escaped = keyword.replace("'", "''")
        clauses.append(f"{expression_sql} LIKE '%{escaped}%'")
    return " OR ".join(clauses) if clauses else "FALSE"


def build_sql_domain_case(
    expression_sql: str,
    *,
    default_domain: str = "business_management",
    domain_order: Sequence[str] | None = None,
    domain_keywords: dict[str, list[str]] | None = None,
) -> str:
    normalized_expr = f"lower(unaccent(COALESCE({expression_sql}, '')))"
    clauses: list[str] = []
    ordered_domains = tuple(domain_order or DOMAIN_ORDER)
    keyword_catalog = domain_keywords or DOMAIN_KEYWORDS
    for domain in ordered_domains:
        keyword_clauses = _sql_like_clauses(normalized_expr, keyword_catalog.get(domain, []))
        if keyword_clauses:
            clauses.append(f"WHEN {keyword_clauses} THEN '{domain}'")
    case_sql = "\n".join(clauses)
    return f"CASE\n{case_sql}\nELSE '{default_domain}'\nEND"


def build_sql_job_domain_case(expression_sql: str, *, default_domain: str = "business_management") -> str:
    return build_sql_domain_case(
        expression_sql,
        default_domain=default_domain,
        domain_order=JOB_DOMAIN_ORDER,
        domain_keywords=JOB_DOMAIN_KEYWORDS,
    )


def build_sql_domain_weight_case(left_expr: str, right_expr: str) -> str:
    related_checks: list[str] = []
    for domain, related in DOMAIN_RELATIONS.items():
        if not related:
            continue
        related_list = ", ".join(f"'{item}'" for item in sorted(related))
        related_checks.append(
            f"(({left_expr} = '{domain}' AND {right_expr} IN ({related_list})) OR ({right_expr} = '{domain}' AND {left_expr} IN ({related_list})))"
        )
    related_sql = " OR ".join(related_checks) if related_checks else "FALSE"
    return f"CASE WHEN {left_expr} = {right_expr} THEN 1.0 WHEN {related_sql} THEN 0.5 ELSE 0.1 END"


@lru_cache(maxsize=1)
def canonical_domain_set() -> tuple[str, ...]:
    return tuple(DOMAIN_ORDER)
