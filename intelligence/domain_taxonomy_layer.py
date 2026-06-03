from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from intelligence.common import normalize_key


@dataclass(frozen=True)
class DomainTaxonomyResult:
    domain_key: str
    domain_label: str
    subdomain: str
    confidence: float
    matched_terms: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DOMAIN_RULES: dict[str, dict[str, Any]] = {
    "data_analytics": {
        "label": "Data & Analytics",
        "aliases": [
            "data analytics",
            "analitica de datos",
            "analitica",
            "visual analytics",
            "big data",
            "business intelligence",
            "bi",
            "analytics engineering",
            "data science",
            "data engineering",
            "reporting",
            "dashboard",
            "power bi",
            "tableau",
            "sql",
            "etl",
        ],
        "name_hints": ("visual analytics", "big data", "business intelligence", "data analytics", "analytics"),
        "role_hints": ("analyst", "bi analyst", "analytics engineer", "data analyst"),
        "faculty_hints": ("engineering", "technology", "business", "economics"),
        "subdomains": {
            "visual_analytics": ["visual analytics", "power bi", "tableau", "dashboard", "reporting", "bi"],
            "data_engineering": ["data engineering", "etl", "elt", "dbt", "pipeline", "warehouse", "lakehouse"],
            "analytics_strategy": ["analytics strategy", "business intelligence", "performance", "kpi", "insight"],
        },
        "benchmark_terms": [
            "Power BI",
            "SQL",
            "dbt",
            "Data Governance",
            "Data Quality",
            "Data Warehousing",
            "Analytics Engineering",
        ],
        "prompt_focus": "enfoque ejecutivo en analitica, negocio, reporting, inteligencia de datos y empleabilidad digital",
    },
    "artificial_intelligence": {
        "label": "Artificial Intelligence",
        "aliases": [
            "ai",
            "ia",
            "artificial intelligence",
            "inteligencia artificial",
            "machine learning",
            "ml",
            "genai",
            "generative ai",
            "llm",
            "rag",
            "llmops",
            "mlops",
            "agentic ai",
            "predictive analytics",
        ],
        "name_hints": ("inteligencia artificial", "machine learning", "generative ai", "genai", "llm", "rag"),
        "role_hints": ("ai engineer", "machine learning engineer", "ml engineer", "llmops", "mlops"),
        "faculty_hints": ("engineering", "technology", "computer", "informatics"),
        "subdomains": {
            "applied_ai": ["machine learning", "ai", "generative ai", "copilot", "rag"],
            "ai_engineering": ["llmops", "mlops", "agentic ai", "model deployment", "model monitoring"],
            "data_ai": ["data science", "analytics", "predictive", "forecast", "nlp"],
        },
        "benchmark_terms": [
            "Generative AI",
            "Machine Learning",
            "LLMOps",
            "RAG",
            "Azure",
            "Databricks",
            "Python",
            "Model Monitoring",
        ],
        "prompt_focus": "enfoque ejecutivo en inteligencia artificial aplicada, adopcion responsable, trazabilidad y productividad academica",
    },
    "cybersecurity": {
        "label": "Cybersecurity",
        "aliases": [
            "cybersecurity",
            "ciberseguridad",
            "seguridad informatica",
            "information security",
            "iso 27001",
            "siem",
            "soc",
            "pentest",
            "privacy",
            "data protection",
            "incident response",
        ],
        "name_hints": ("seguridad informatica", "ciberseguridad", "cybersecurity", "information security"),
        "role_hints": ("security analyst", "soc analyst", "security engineer", "privacy officer"),
        "faculty_hints": ("engineering", "technology", "computer", "informatics"),
        "subdomains": {
            "security_operations": ["soc", "siem", "incident response", "threat", "monitoring"],
            "privacy_risk": ["privacy", "data protection", "iso 27001", "risk"],
            "cyber_defense": ["pentest", "vulnerability", "hardening", "security"],
        },
        "benchmark_terms": [
            "Cybersecurity",
            "Information Security",
            "ISO 27001",
            "SIEM",
            "Privacy",
            "Incident Response",
        ],
        "prompt_focus": "enfoque ejecutivo en ciberseguridad, riesgo tecnologico, privacidad y continuidad operativa",
    },
    "criminology_security": {
        "label": "Criminology & Security",
        "aliases": [
            "criminology",
            "criminologia",
            "criminalistics",
            "criminalistica",
            "forensic",
            "forense",
            "forensics",
            "crime",
            "criminal",
            "criminal justice",
            "investigation",
            "public safety",
            "public security",
            "victimology",
            "cybercrime",
            "chain of custody",
            "organized crime",
            "financial crime",
            "security",
        ],
        "name_hints": ("criminologia", "criminalistica", "forense", "seguridad publica", "seguridad ciudadana"),
        "role_hints": ("forensic analyst", "criminal intelligence analyst", "cybercrime investigator", "public security advisor"),
        "faculty_hints": ("social", "law", "public", "security"),
        "subdomains": {
            "forensic_analysis": ["forensic", "criminalistics", "evidence", "chain of custody", "forensic analysis"],
            "public_safety": ["public safety", "public security", "security", "risk", "prevention", "community"],
            "investigative_methods": ["investigation", "research methods", "analysis", "data interpretation", "criminal intelligence"],
            "cybercrime": ["cybercrime", "digital forensics", "incident response", "computer crime"],
        },
        "benchmark_terms": [
            "Criminal Investigation",
            "Victimology",
            "Criminal Profiling",
            "Criminal Intelligence",
            "Criminal Policy",
            "Crime Prevention",
            "Public Safety",
            "Public Security",
            "Cybercrime",
            "Forensic Analysis",
            "Chain of Custody",
            "Risk Analysis",
            "Compliance",
        ],
        "market_skills": [
            "criminal investigation",
            "victimology",
            "criminal profiling",
            "criminal intelligence",
            "criminal policy",
            "crime prevention",
            "public safety",
            "public security",
            "cybercrime",
            "criminal analysis",
            "forensic analysis",
            "chain of custody",
            "risk analysis",
            "compliance",
            "penitentiary systems",
            "organized crime",
            "financial crime",
        ],
        "prompt_focus": "enfoque ejecutivo en criminologia aplicada, evidencia, investigacion criminal, seguridad publica y prevencion del delito",
    },
    "finance_accounting": {
        "label": "Finance & Accounting",
        "aliases": [
            "finance",
            "financial",
            "accounting",
            "contabilidad",
            "auditoria",
            "auditoria financiera",
            "revisoria fiscal",
            "revisor fiscal",
            "tax",
            "tributaria",
            "tributario",
            "internal control",
            "control interno",
            "ifrs",
            "risk financial",
            "financial reporting",
        ],
        "name_hints": ("revisoria fiscal", "auditoria", "contaduria", "gerencia financiera", "finance", "accounting"),
        "role_hints": ("auditor", "revisor fiscal", "financial analyst", "controller", "accountant"),
        "faculty_hints": ("economics", "business", "administration", "accounting"),
        "subdomains": {
            "audit_and_assurance": ["auditoria", "auditing", "assurance", "revisoria fiscal", "control interno"],
            "tax_and_compliance": ["tax", "tributaria", "compliance", "regulation", "reporting"],
            "corporate_finance": ["finance", "financial", "budget", "valuation", "risk"],
        },
        "benchmark_terms": [
            "Auditoria",
            "Contabilidad",
            "IFRS",
            "Control Interno",
            "Financial Reporting",
            "Tax Compliance",
            "Risk Management",
        ],
        "market_skills": [
            "audit",
            "financial reporting",
            "internal control",
            "risk management",
            "compliance",
            "ifrs",
            "tax compliance",
        ],
        "prompt_focus": "enfoque ejecutivo en auditoria, contabilidad, control interno, tributacion y gestion financiera",
    },
    "project_management": {
        "label": "Project Management",
        "aliases": [
            "project management",
            "gestion de proyectos",
            "pmo",
            "pmbok",
            "agile",
            "scrum",
            "kanban",
            "portfolio",
            "program management",
            "delivery",
        ],
        "name_hints": ("gestion de proyectos", "project management", "pmo", "gestionar proyectos"),
        "role_hints": ("project manager", "pmo analyst", "scrum master", "delivery manager"),
        "faculty_hints": ("engineering", "business", "management", "administration"),
        "subdomains": {
            "pmo_governance": ["pmo", "governance", "portfolio", "program management"],
            "agile_delivery": ["agile", "scrum", "kanban", "delivery"],
            "portfolio_management": ["project management", "roadmap", "scope", "schedule"],
        },
        "benchmark_terms": [
            "Project Management",
            "PMO",
            "Agile Delivery",
            "Portfolio Management",
            "Governance",
        ],
        "market_skills": [
            "project management",
            "pmo",
            "agile",
            "scrum",
            "portfolio management",
            "stakeholder management",
        ],
        "prompt_focus": "enfoque ejecutivo en direccion de proyectos, gobierno, plazos, alcance y seguimiento",
    },
    "business_management": {
        "label": "Business Management",
        "aliases": [
            "management",
            "gerencia",
            "administration",
            "business administration",
            "alta gerencia",
            "strategy",
            "leadership",
            "transformacion",
            "operations management",
            "business",
        ],
        "name_hints": ("alta gerencia", "gerencia", "business administration", "business management", "administracion"),
        "role_hints": ("manager", "director", "head of", "lead", "chief"),
        "faculty_hints": ("business", "economics", "administration", "management"),
        "subdomains": {
            "strategy": ["strategy", "business", "growth", "planning"],
            "leadership": ["leadership", "management", "manager", "director"],
            "organizational_transformation": ["transformation", "change", "innovation", "governance"],
        },
        "benchmark_terms": [
            "Business Management",
            "Strategy",
            "Leadership",
            "Organizational Transformation",
            "Operations",
        ],
        "prompt_focus": "enfoque ejecutivo en gestion empresarial, estrategia, liderazgo y transformacion organizacional",
    },
    "logistics_operations": {
        "label": "Logistics & Operations",
        "aliases": [
            "logistics",
            "logistica",
            "supply chain",
            "operations",
            "operations management",
            "inventory",
            "procurement",
            "transportation",
            "warehousing",
            "distribution",
        ],
        "name_hints": ("logistica", "supply chain", "operaciones", "cadena de suministro"),
        "role_hints": ("operations analyst", "supply chain analyst", "logistics manager"),
        "faculty_hints": ("engineering", "business", "operations", "logistics"),
        "subdomains": {
            "supply_chain": ["supply chain", "distribution", "inventory", "warehouse"],
            "procurement": ["procurement", "purchasing", "sourcing"],
            "operations_excellence": ["operations", "process", "efficiency", "lean"],
        },
        "benchmark_terms": [
            "Supply Chain",
            "Operations",
            "Procurement",
            "Inventory Management",
            "Distribution",
        ],
        "market_skills": [
            "supply chain",
            "operations",
            "procurement",
            "inventory management",
            "distribution",
        ],
        "prompt_focus": "enfoque ejecutivo en cadena de suministro, operaciones, compras e inventarios",
    },
    "marketing_commercial": {
        "label": "Marketing & Commercial",
        "aliases": [
            "marketing",
            "mercadeo",
            "seo",
            "sem",
            "crm",
            "growth",
            "marca",
            "customer experience",
            "ventas",
            "comercial",
            "digital marketing",
        ],
        "name_hints": ("marketing", "mercadeo", "ventas", "comercial", "digital marketing"),
        "role_hints": ("marketing analyst", "sales manager", "commercial manager", "crm analyst"),
        "faculty_hints": ("business", "marketing", "commerce", "administration"),
        "subdomains": {
            "digital_marketing": ["seo", "sem", "digital marketing", "growth"],
            "commercial_management": ["sales", "ventas", "commercial", "business development"],
            "crm_growth": ["crm", "customer experience", "brand", "funnel"],
        },
        "benchmark_terms": [
            "Digital Marketing",
            "CRM",
            "Sales",
            "Brand Management",
            "Growth",
        ],
        "market_skills": [
            "digital marketing",
            "crm",
            "seo",
            "sem",
            "sales",
            "commercial strategy",
        ],
        "prompt_focus": "enfoque ejecutivo en mercadeo, ventas, marca, crm y crecimiento comercial",
    },
    "education": {
        "label": "Education",
        "aliases": [
            "education",
            "educacion",
            "pedagogy",
            "pedagogia",
            "curriculum",
            "curriculo",
            "teaching",
            "docencia",
            "lms",
            "instructional design",
            "learning analytics",
            "assessment",
        ],
        "name_hints": ("educacion", "pedagogia", "docencia", "curriculo", "learning"),
        "role_hints": ("teacher", "instructional designer", "curriculum designer", "academic coordinator"),
        "faculty_hints": ("education", "pedagogy", "teaching", "school"),
        "subdomains": {
            "curriculum_design": ["curriculum", "curriculo", "instructional design", "learning"],
            "educational_tech": ["lms", "moodle", "canvas", "blackboard", "learning analytics"],
            "evaluation": ["assessment", "evaluation", "measurement"],
        },
        "benchmark_terms": [
            "Curriculum Design",
            "Instructional Design",
            "Learning Analytics",
            "LMS",
            "Assessment",
        ],
        "market_skills": [
            "curriculum design",
            "instructional design",
            "learning analytics",
            "lms",
            "evaluation",
        ],
        "prompt_focus": "enfoque ejecutivo en diseno curricular, docencia, evaluacion y tecnologia educativa",
    },
    "health": {
        "label": "Health",
        "aliases": [
            "health",
            "salud",
            "public health",
            "health management",
            "occupational health",
            "patient safety",
            "hospital",
            "clinical",
            "epidemiology",
            "epidemiologia",
        ],
        "name_hints": ("salud", "health", "public health", "occupational health"),
        "role_hints": ("health manager", "patient safety", "quality analyst", "risk manager"),
        "faculty_hints": ("health", "medicine", "clinical", "hospital"),
        "subdomains": {
            "health_management": ["health management", "hospital", "operations"],
            "patient_safety": ["patient safety", "quality", "risk", "care"],
            "public_health": ["public health", "epidemiology", "public", "community"],
        },
        "benchmark_terms": [
            "Health Management",
            "Public Health",
            "Patient Safety",
            "Occupational Health",
            "Clinical Quality",
        ],
        "market_skills": [
            "health management",
            "public health",
            "patient safety",
            "occupational health",
            "quality management",
        ],
        "prompt_focus": "enfoque ejecutivo en gestion en salud, seguridad del paciente, calidad y salud publica",
    },
    "psychology": {
        "label": "Psychology",
        "aliases": [
            "psychology",
            "psicologia",
            "psicologia organizacional",
            "organizational psychology",
            "organizacional",
            "psychological",
            "psicologica",
            "mental health",
            "clinical",
            "counseling",
            "cognitive",
            "behavioral",
            "wellbeing",
            "well-being",
        ],
        "name_hints": ("psicologia", "psychology", "psychologia organizacional", "organizational psychology", "mental health"),
        "role_hints": ("psychologist", "counselor", "wellbeing", "org psych"),
        "faculty_hints": ("psychology", "mental", "behavioral"),
        "subdomains": {
            "clinical_psychology": ["clinical", "mental health", "assessment", "intervention"],
            "organizational_psychology": ["organizational", "workplace", "talent", "leadership", "culture"],
            "cognitive_behavioral": ["cognitive", "behavioral", "research methods", "psychometrics"],
        },
        "benchmark_terms": [
            "Psychometrics",
            "Research Methods",
            "Ethics",
            "Mental Health",
            "Counseling",
            "Organizational Development",
        ],
        "prompt_focus": "enfoque ejecutivo en salud mental, bienestar, intervencion y pertinencia humana y organizacional",
    },
    "legal_compliance": {
        "label": "Legal & Compliance",
        "aliases": [
            "law",
            "derecho",
            "legal",
            "juridical",
            "judicial",
            "compliance",
            "regulation",
            "litigation",
            "contract",
            "rights",
            "due process",
            "privacy",
            "governance",
        ],
        "name_hints": ("derecho", "legal", "compliance", "regulatory", "contracts"),
        "role_hints": ("legal analyst", "compliance officer", "privacy officer", "legal risk analyst"),
        "faculty_hints": ("law", "legal", "juridical", "rights"),
        "subdomains": {
            "legal_compliance": ["compliance", "regulation", "law", "rights", "ethics"],
            "corporate_law": ["contract", "corporate", "governance", "regulation", "compliance"],
            "judicial_procedure": ["judicial", "litigation", "due process", "procedure", "evidence"],
        },
        "benchmark_terms": [
            "Compliance",
            "Regulation",
            "Legal Tech",
            "Data Protection",
            "Ethics",
            "Contract Management",
        ],
        "prompt_focus": "enfoque ejecutivo en cumplimiento normativo, etica, regulacion y pertinencia profesional juridica",
    },
}

CANONICAL_DOMAIN_KEYS: dict[str, str] = {}


def _collect_texts(*values: Any) -> list[str]:
    texts: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            if value.strip():
                texts.append(value)
            continue
        if isinstance(value, dict):
            texts.extend(_collect_texts(*value.values()))
            continue
        if isinstance(value, (list, tuple, set)):
            texts.extend(_collect_texts(*list(value)))
            continue
        texts.append(str(value))
    return texts


def _domain_score(domain_key: str, texts: list[str], *, name_text: str = "", role_text: str = "", faculty_text: str = "") -> tuple[int, list[str], str]:
    config = DOMAIN_RULES[domain_key]
    aliases = [normalize_key(item) for item in config["aliases"]]
    subdomain_hits: dict[str, int] = {}
    matched_terms: list[str] = []
    joined = " ".join(normalize_key(text) for text in texts if normalize_key(text))
    score = 0

    for alias in aliases:
        if alias and alias in joined:
            score += 2
            matched_terms.append(alias)

    for subdomain, keywords in config["subdomains"].items():
        for keyword in keywords:
            normalized = normalize_key(keyword)
            if normalized and normalized in joined:
                score += 1
                subdomain_hits[subdomain] = subdomain_hits.get(subdomain, 0) + 1
                matched_terms.append(normalized)

    for hint in config.get("name_hints", ()):
        normalized = normalize_key(str(hint))
        if normalized and normalized in name_text:
            score += 4
            matched_terms.append(normalized)

    for hint in config.get("role_hints", ()):
        normalized = normalize_key(str(hint))
        if normalized and normalized in role_text:
            score += 3
            matched_terms.append(normalized)

    for hint in config.get("faculty_hints", ()):
        normalized = normalize_key(str(hint))
        if normalized and normalized in faculty_text:
            score += 2
            matched_terms.append(normalized)

    ranked_subdomain = ""
    if subdomain_hits:
        ranked_subdomain = max(subdomain_hits.items(), key=lambda item: (item[1], item[0]))[0]

    return score, matched_terms, ranked_subdomain


def build_domain_taxonomy(
    *,
    program_name: str = "",
    program_role: str = "",
    faculty: str = "",
    detected_domain: str | None = None,
    detected_subdomain: str | None = None,
    skills: list[str] | None = None,
    tools: list[str] | None = None,
    technologies: list[str] | None = None,
    subjects: list[str] | None = None,
    real_market_gaps: list[str] | None = None,
    strengthening_areas: list[str] | None = None,
    labor_roles: list[str] | None = None,
    keywords: list[str] | None = None,
) -> DomainTaxonomyResult:
    name_text = normalize_key(program_name)
    role_text = normalize_key(program_role)
    faculty_text = normalize_key(faculty)
    texts = _collect_texts(
        program_name,
        program_role,
        faculty,
        detected_domain,
        detected_subdomain,
        skills or [],
        tools or [],
        technologies or [],
        subjects or [],
        real_market_gaps or [],
        strengthening_areas or [],
        labor_roles or [],
        keywords or [],
    )
    scores: list[tuple[int, str, list[str], str]] = []
    for domain_key in DOMAIN_RULES:
        score, matched_terms, subdomain = _domain_score(
            domain_key,
            texts,
            name_text=name_text,
            role_text=role_text,
            faculty_text=faculty_text,
        )
        if detected_domain and normalize_key(detected_domain) == domain_key:
            score += 1
        if detected_subdomain and normalize_key(detected_subdomain) == subdomain:
            score += 1
        scores.append((score, domain_key, matched_terms, subdomain))

    scores.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best_score, best_domain_key, matched_terms, subdomain = scores[0] if scores else (0, "data_analytics", [], "")
    canonical_domain_key = CANONICAL_DOMAIN_KEYS.get(best_domain_key, best_domain_key)
    config = DOMAIN_RULES.get(canonical_domain_key, DOMAIN_RULES["data_analytics"])
    confidence = min(0.98, 0.35 + (best_score * 0.12))
    if not subdomain:
        subdomain = next(iter(config["subdomains"].keys()), "")
    return DomainTaxonomyResult(
        domain_key=canonical_domain_key,
        domain_label=config["label"],
        subdomain=subdomain,
        confidence=round(confidence, 4),
        matched_terms=matched_terms[:20],
        evidence={
            "source": "heuristic_taxonomy",
            "detected_domain": detected_domain,
            "detected_subdomain": detected_subdomain,
            "text_sources": texts[:20],
        },
    )


def build_domain_taxonomy_from_program(
    *,
    program_name: str = "",
    program_role: str = "",
    faculty: str = "",
    microcurriculum_context: dict[str, Any] | None = None,
    skills: list[str] | None = None,
) -> DomainTaxonomyResult:
    context = microcurriculum_context or {}
    return build_domain_taxonomy(
        program_name=program_name,
        program_role=program_role,
        faculty=faculty,
        detected_domain=str(context.get("detected_domain") or "").strip() or None,
        detected_subdomain=str(context.get("detected_subdomain") or "").strip() or None,
        skills=skills or list(context.get("technical_skills") or []),
        tools=list(context.get("tools") or []),
        technologies=list(context.get("technologies") or []),
        subjects=list(context.get("subjects") or []),
        real_market_gaps=list(context.get("real_market_gaps") or []),
        strengthening_areas=list(context.get("strengthening_areas") or []),
        labor_roles=list(context.get("labor_roles") or []),
        keywords=list(context.get("keywords") or []),
    )


def domain_prompt_focus(domain_key: str) -> str:
    config = DOMAIN_RULES.get(domain_key, DOMAIN_RULES["data_analytics"])
    return str(config.get("prompt_focus") or "")


def benchmark_terms_for_domain(domain_key: str) -> list[str]:
    config = DOMAIN_RULES.get(domain_key, DOMAIN_RULES["data_analytics"])
    return [str(item).strip() for item in config.get("benchmark_terms") or [] if str(item).strip()]


def market_skills_for_domain(domain_key: str) -> list[str]:
    config = DOMAIN_RULES.get(domain_key, DOMAIN_RULES["data_analytics"])
    explicit = [str(item).strip() for item in config.get("market_skills") or [] if str(item).strip()]
    return explicit or benchmark_terms_for_domain(domain_key)
