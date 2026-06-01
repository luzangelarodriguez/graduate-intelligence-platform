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
        "label": "Data Analytics",
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
        ],
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
        "prompt_focus": "enfoque ejecutivo en analítica, negocio, reporting, inteligencia de datos y empleabilidad digital",
    },
    "ai": {
        "label": "AI",
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
        ],
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
        "prompt_focus": "enfoque ejecutivo en inteligencia artificial aplicada, adopción responsable, trazabilidad y productividad académica",
    },
    "criminology": {
        "label": "Criminology",
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
            "security",
            "investigation",
            "public safety",
            "public security",
            "victimology",
            "cybercrime",
            "chain of custody",
            "organized crime",
            "financial crime",
        ],
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
    "law": {
        "label": "Law",
        "aliases": [
            "law",
            "derecho",
            "derecho digital",
            "legal",
            "juridical",
            "judicial",
            "compliance",
            "regulation",
            "litigation",
            "contract",
            "rights",
            "due process",
        ],
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
        "prompt_focus": "enfoque ejecutivo en cumplimiento normativo, ética, regulación y pertinencia profesional jurídica",
    },
    "psychology": {
        "label": "Psychology",
        "aliases": [
            "psychology",
            "psicologia",
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
        "prompt_focus": "enfoque ejecutivo en salud mental, bienestar, intervención, medición y pertinencia humana y organizacional",
    },
}


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


def _domain_score(domain_key: str, texts: list[str]) -> tuple[int, list[str], str]:
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

    ranked_subdomain = ""
    if subdomain_hits:
        ranked_subdomain = max(subdomain_hits.items(), key=lambda item: (item[1], item[0]))[0]

    return score, matched_terms, ranked_subdomain


def build_domain_taxonomy(
    *,
    program_name: str = "",
    program_role: str = "",
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
    texts = _collect_texts(
        program_name,
        program_role,
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
        score, matched_terms, subdomain = _domain_score(domain_key, texts)
        if detected_domain and normalize_key(detected_domain) == domain_key:
            score += 3
        if detected_subdomain and normalize_key(detected_subdomain) == subdomain:
            score += 1
        scores.append((score, domain_key, matched_terms, subdomain))

    scores.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best_score, best_domain_key, matched_terms, subdomain = scores[0] if scores else (0, "data_analytics", [], "")
    config = DOMAIN_RULES.get(best_domain_key, DOMAIN_RULES["data_analytics"])
    confidence = min(0.98, 0.35 + (best_score * 0.12))
    if not subdomain:
        subdomain = next(iter(config["subdomains"].keys()), "")
    return DomainTaxonomyResult(
        domain_key=best_domain_key,
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
    microcurriculum_context: dict[str, Any] | None = None,
    skills: list[str] | None = None,
) -> DomainTaxonomyResult:
    context = microcurriculum_context or {}
    return build_domain_taxonomy(
        program_name=program_name,
        program_role=program_role,
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
