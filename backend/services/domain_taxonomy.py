from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re
import unicodedata
from typing import Any, Iterable, Sequence


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

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "criminology_security": [
        "criminal investigation",
        "criminal intelligence",
        "forensic analysis",
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
        "crime",
        "investigation",
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
        "threat",
        "zero trust",
        "identity",
        "iam",
        "malware",
        "digital forensics",
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


def _score_domain(text: str, domain: str) -> tuple[int, tuple[str, ...]]:
    if not text:
        return 0, ()
    hits = tuple(keyword for keyword in DOMAIN_KEYWORDS.get(domain, []) if keyword in text)
    return len(hits), hits


def infer_domain_from_texts(texts: Sequence[Any], *, default: str = "business_management") -> DomainMatch:
    normalized_text = " ".join(normalize_domain_text(item) for item in texts if normalize_domain_text(item))
    best_domain = default
    best_hits: tuple[str, ...] = ()
    best_score = -1
    for domain in DOMAIN_ORDER:
        score, hits = _score_domain(normalized_text, domain)
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
    parts: list[Any] = [name, faculty, role]
    if skills:
        parts.extend(skills)
    return infer_domain_from_texts(parts, default="business_management")


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
    parts: list[Any] = [title, source, industry, description, responsibilities, requirements]
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


def _sql_like_clauses(expression_sql: str, keywords: Sequence[str]) -> str:
    clauses: list[str] = []
    for keyword in keywords:
        escaped = keyword.replace("'", "''")
        clauses.append(f"{expression_sql} LIKE '%{escaped}%'")
    return " OR ".join(clauses) if clauses else "FALSE"


def build_sql_domain_case(expression_sql: str, *, default_domain: str = "business_management") -> str:
    normalized_expr = f"lower(unaccent(COALESCE({expression_sql}, '')))"
    clauses: list[str] = []
    for domain in DOMAIN_ORDER:
        keyword_clauses = _sql_like_clauses(normalized_expr, DOMAIN_KEYWORDS.get(domain, []))
        if keyword_clauses:
            clauses.append(f"WHEN {keyword_clauses} THEN '{domain}'")
    case_sql = "\n".join(clauses)
    return f"CASE\n{case_sql}\nELSE '{default_domain}'\nEND"


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
