from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from intelligence.common import normalize_key
from intelligence.domain_taxonomy_layer import DOMAIN_RULES, benchmark_terms_for_domain


@dataclass(frozen=True)
class DomainBenchmarkProfile:
    domain_key: str
    domain_label: str
    reference_program: str
    core_competencies: list[str] = field(default_factory=list)
    priority_skills: list[str] = field(default_factory=list)
    market_skills: list[str] = field(default_factory=list)
    market_signals: list[str] = field(default_factory=list)
    comparison_terms: list[str] = field(default_factory=list)
    analysis_weights: dict[str, float] = field(default_factory=dict)
    narrative_focus: str = ""
    benchmark_institutions: list[dict[str, Any]] = field(default_factory=list)
    curriculum_structure: list[str] = field(default_factory=list)
    graduate_profile: list[str] = field(default_factory=list)
    occupational_profile: list[str] = field(default_factory=list)
    labor_roles: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DOMAIN_BENCHMARKS: dict[str, dict[str, Any]] = {
    "data_analytics": {
        "reference_program": "Benchmark de analítica de datos",
        "core_competencies": [
            "modelado de datos",
            "visualización",
            "gobierno de datos",
            "analítica descriptiva",
            "analítica predictiva",
        ],
        "priority_skills": ["Power BI", "SQL", "dbt", "Python", "Data Governance", "Data Quality"],
        "market_signals": ["business intelligence", "analytics engineer", "data product", "dashboards", "reporting"],
        "analysis_weights": {"coverage": 0.38, "gap": 0.25, "forecast": 0.18, "emerging": 0.09, "role": 0.10},
    },
    "ai": {
        "reference_program": "Benchmark de inteligencia artificial",
        "core_competencies": [
            "modelado predictivo",
            "ingeniería de prompts",
            "despliegue de modelos",
            "evaluación de modelos",
            "gobernanza de IA",
        ],
        "priority_skills": ["Python", "Machine Learning", "LLMOps", "RAG", "Azure", "Databricks", "Model Monitoring"],
        "market_signals": ["ai engineer", "llmops", "agentic ai", "copilot", "machine learning"],
        "analysis_weights": {"coverage": 0.30, "gap": 0.22, "forecast": 0.24, "emerging": 0.16, "role": 0.08},
    },
    "criminology": {
        "reference_program": "Benchmark de criminología y seguridad",
        "core_competencies": [
            "análisis de evidencia",
            "métodos de investigación criminal",
            "victimología y atención a víctimas",
            "prevención del delito",
            "análisis criminal",
            "cadena de custodia",
            "criminal intelligence",
            "seguridad pública",
            "crimen organizado",
            "crimen financiero",
        ],
        "priority_skills": [
            "criminal investigation",
            "victimology",
            "criminal profiling",
            "criminal intelligence",
            "crime prevention",
            "public safety",
            "public security",
            "cybercrime",
            "forensic analysis",
            "chain of custody",
            "risk analysis",
            "compliance",
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
        "market_signals": ["forensic", "investigation", "public safety", "security analyst", "risk analyst", "cybercrime", "victim services"],
        "analysis_weights": {"coverage": 0.38, "gap": 0.26, "forecast": 0.10, "emerging": 0.10, "role": 0.16},
        "benchmark_institutions": [
            {"country": "Colombia", "institution": "Universidad Externado de Colombia", "program": "Especializacion en Criminologia", "source": "SNIES"},
            {"country": "Colombia", "institution": "Universidad Sergio Arboleda", "program": "Criminologia y Seguridad", "source": "SNIES"},
            {"country": "Colombia", "institution": "Universidad Libre", "program": "Criminalistica y Ciencias Forenses", "source": "SNIES"},
            {"country": "Colombia", "institution": "Universidad Militar Nueva Granada", "program": "Seguridad y Defensa", "source": "SNIES"},
            {"country": "Colombia", "institution": "UNAD", "program": "Criminologia", "source": "SNIES"},
            {"country": "International", "institution": "Universidad de Salamanca", "program": "Criminologia", "source": "Benchmark"},
            {"country": "International", "institution": "Universidad de Barcelona", "program": "Criminologia", "source": "Benchmark"},
            {"country": "International", "institution": "University of Leicester", "program": "Criminology", "source": "Benchmark"},
            {"country": "International", "institution": "University of Portsmouth", "program": "Criminology and Criminal Justice", "source": "Benchmark"},
        ],
        "curriculum_structure": [
            "fundamentos de criminologia",
            "investigacion criminal",
            "victimologia",
            "criminalistica y ciencias forenses",
            "seguridad publica y prevencion",
            "criminal intelligence y analisis de riesgo",
        ],
        "graduate_profile": [
            "analista en investigacion criminal",
            "especialista en prevencion del delito",
            "analista de inteligencia criminal",
            "asesor en seguridad publica",
            "analista de riesgo criminologico",
        ],
        "occupational_profile": [
            "Forensic Analyst",
            "Criminal Intelligence Analyst",
            "Cybercrime Investigator",
            "Victim Assistance Specialist",
            "Public Security Advisor",
            "Compliance Analyst",
        ],
        "labor_roles": [
            "Forensic Analyst",
            "Criminal Intelligence Analyst",
            "Cybercrime Investigator",
            "Victim Assistance Specialist",
            "Public Security Advisor",
            "Compliance Analyst",
        ],
    },
    "law": {
        "reference_program": "Benchmark de derecho y cumplimiento",
        "core_competencies": [
            "razonamiento jurídico",
            "cumplimiento normativo",
            "argumentación",
            "gestión documental",
            "análisis regulatorio",
        ],
        "priority_skills": ["Compliance", "Regulation", "Contract Management", "Legal Tech", "Data Protection"],
        "market_signals": ["legal", "compliance", "regulation", "privacy", "contracts"],
        "analysis_weights": {"coverage": 0.36, "gap": 0.30, "forecast": 0.10, "emerging": 0.04, "role": 0.20},
    },
    "psychology": {
        "reference_program": "Benchmark de psicología",
        "core_competencies": [
            "evaluación psicológica",
            "intervención",
            "psicometría",
            "acompañamiento",
            "investigación aplicada",
        ],
        "priority_skills": ["Psychometrics", "Research Methods", "Mental Health", "Counseling", "Organizational Development"],
        "market_signals": ["mental health", "clinical", "organizational", "wellbeing", "assessment"],
        "analysis_weights": {"coverage": 0.36, "gap": 0.28, "forecast": 0.10, "emerging": 0.04, "role": 0.22},
    },
}


def _ensure_terms(values: list[str], fallback_domain_key: str) -> list[str]:
    fallback = benchmark_terms_for_domain(fallback_domain_key)
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values + fallback:
        normalized = normalize_key(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(value)
    return ordered


def build_domain_benchmark(domain_key: str) -> DomainBenchmarkProfile:
    key = normalize_key(domain_key)
    if key not in DOMAIN_BENCHMARKS:
        key = "data_analytics"
    config = DOMAIN_BENCHMARKS[key]
    return DomainBenchmarkProfile(
        domain_key=key,
        domain_label=DOMAIN_RULES[key]["label"],
        reference_program=str(config["reference_program"]),
        core_competencies=_ensure_terms([str(item) for item in config.get("core_competencies", [])], key),
        priority_skills=_ensure_terms([str(item) for item in config.get("priority_skills", [])], key),
        market_skills=_ensure_terms([str(item) for item in config.get("market_skills") or config.get("priority_skills", [])], key),
        market_signals=_ensure_terms([str(item) for item in config.get("market_signals", [])], key),
        comparison_terms=_ensure_terms(
            [*config.get("core_competencies", []), *config.get("priority_skills", []), *config.get("market_skills", []), *config.get("market_signals", [])],
            key,
        ),
        analysis_weights={str(k): float(v) for k, v in config.get("analysis_weights", {}).items()},
        narrative_focus=str(DOMAIN_RULES[key].get("prompt_focus") or ""),
        benchmark_institutions=[dict(item) for item in config.get("benchmark_institutions", [])],
        curriculum_structure=[str(item) for item in config.get("curriculum_structure", [])],
        graduate_profile=[str(item) for item in config.get("graduate_profile", [])],
        occupational_profile=[str(item) for item in config.get("occupational_profile", [])],
        labor_roles=[str(item) for item in config.get("labor_roles", config.get("occupational_profile", []))],
    )


def benchmark_terms(domain_key: str) -> list[str]:
    return build_domain_benchmark(domain_key).comparison_terms
