from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ExpandedLaborSkill:
    original: str
    normalized: str
    category: str
    entity_type: str
    confidence: float
    section: str


SECTION_CONFIDENCE = {
    "requirements": 1.0,
    "responsibilities": 0.9,
    "description": 0.7,
    "title": 0.5,
    "tags": 0.35,
    "portal_taxonomy": 0.1,
}


def normalize_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9+#.]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


EXPANDED_SKILLS: dict[str, dict[str, object]] = {
    # BI & Visualizacion
    "Power BI": {"category": "BI & Visualization", "entity_type": "tool", "aliases": ("power bi", "powerbi", "microsoft power bi", "pbi")},
    "Tableau": {"category": "BI & Visualization", "entity_type": "tool", "aliases": ("tableau",)},
    "Looker": {"category": "BI & Visualization", "entity_type": "tool", "aliases": ("looker", "looker studio", "google looker")},
    "Qlik": {"category": "BI & Visualization", "entity_type": "tool", "aliases": ("qlik", "qlik sense", "qlikview")},
    "dashboarding": {"category": "BI & Visualization", "entity_type": "explicit_skill", "aliases": ("dashboard", "dashboards", "dashboarding", "tableros", "tableros de control")},
    "reporting": {"category": "BI & Visualization", "entity_type": "explicit_skill", "aliases": ("reporting", "reportes", "informes", "reporteria")},
    "KPIs": {"category": "BI & Visualization", "entity_type": "explicit_skill", "aliases": ("kpi", "kpis", "indicadores", "indicadores clave")},
    "scorecards": {"category": "BI & Visualization", "entity_type": "explicit_skill", "aliases": ("scorecards", "balanced scorecard", "cuadro de mando integral")},
    "storytelling with data": {"category": "BI & Visualization", "entity_type": "responsibility_skill", "aliases": ("storytelling", "data storytelling", "storytelling with data", "narrativa de datos")},
    "executive reporting": {"category": "BI & Visualization", "entity_type": "responsibility_skill", "aliases": ("executive reporting", "reporting ejecutivo", "informes ejecutivos")},
    "visualizacion analitica": {"category": "BI & Visualization", "entity_type": "explicit_skill", "aliases": ("visual analytics", "visualizacion", "visualizacion de datos", "data visualization")},
    # Bases de datos
    "SQL": {"category": "Databases", "entity_type": "technology", "aliases": ("sql", "structured query language")},
    "PostgreSQL": {"category": "Databases", "entity_type": "technology", "aliases": ("postgresql", "postgres")},
    "MySQL": {"category": "Databases", "entity_type": "technology", "aliases": ("mysql",)},
    "SQL Server": {"category": "Databases", "entity_type": "technology", "aliases": ("sql server", "microsoft sql server", "t sql", "tsql")},
    "Oracle": {"category": "Databases", "entity_type": "technology", "aliases": ("oracle", "oracle database")},
    "PL/SQL": {"category": "Databases", "entity_type": "technology", "aliases": ("pl/sql", "pl sql", "plsql")},
    "NoSQL": {"category": "Databases", "entity_type": "technology", "aliases": ("nosql", "no sql")},
    "MongoDB": {"category": "Databases", "entity_type": "technology", "aliases": ("mongodb", "mongo db")},
    "Redis": {"category": "Databases", "entity_type": "technology", "aliases": ("redis",)},
    # Data Engineering
    "ETL": {"category": "Data Engineering", "entity_type": "methodology", "aliases": ("etl", "extract transform load", "extraccion transformacion carga")},
    "ELT": {"category": "Data Engineering", "entity_type": "methodology", "aliases": ("elt",)},
    "pipelines": {"category": "Data Engineering", "entity_type": "technology", "aliases": ("pipeline", "pipelines", "data pipeline", "data pipelines")},
    "data warehouse": {"category": "Data Engineering", "entity_type": "technology", "aliases": ("data warehouse", "data warehousing", "almacen de datos", "bodega de datos")},
    "data lake": {"category": "Data Engineering", "entity_type": "technology", "aliases": ("data lake", "lago de datos")},
    "lakehouse": {"category": "Data Engineering", "entity_type": "technology", "aliases": ("lakehouse", "data lakehouse", "arquitectura lakehouse")},
    "Spark": {"category": "Data Engineering", "entity_type": "technology", "aliases": ("spark", "apache spark", "pyspark")},
    "Hadoop": {"category": "Data Engineering", "entity_type": "technology", "aliases": ("hadoop", "apache hadoop")},
    "Kafka": {"category": "Data Engineering", "entity_type": "technology", "aliases": ("kafka", "apache kafka")},
    "Airflow": {"category": "Data Engineering", "entity_type": "tool", "aliases": ("airflow", "apache airflow")},
    "dbt": {"category": "Data Engineering", "entity_type": "tool", "aliases": ("dbt", "data build tool")},
    "SSIS": {"category": "Data Engineering", "entity_type": "tool", "aliases": ("ssis", "sql server integration services")},
    # Cloud Analytics
    "Azure": {"category": "Cloud Analytics", "entity_type": "technology", "aliases": ("azure", "microsoft azure")},
    "AWS": {"category": "Cloud Analytics", "entity_type": "technology", "aliases": ("aws", "amazon web services")},
    "GCP": {"category": "Cloud Analytics", "entity_type": "technology", "aliases": ("gcp", "google cloud", "google cloud platform")},
    "Azure Synapse": {"category": "Cloud Analytics", "entity_type": "technology", "aliases": ("synapse", "azure synapse", "azure synapse analytics")},
    "BigQuery": {"category": "Cloud Analytics", "entity_type": "technology", "aliases": ("bigquery", "google bigquery")},
    "Redshift": {"category": "Cloud Analytics", "entity_type": "technology", "aliases": ("redshift", "amazon redshift")},
    "Snowflake": {"category": "Cloud Analytics", "entity_type": "technology", "aliases": ("snowflake",)},
    "Databricks": {"category": "Cloud Analytics", "entity_type": "technology", "aliases": ("databricks",)},
    "Microsoft Fabric": {"category": "Cloud Analytics", "entity_type": "technology", "aliases": ("microsoft fabric", "fabric")},
    # IA / ML / GenAI
    "AI": {"category": "AI Analytics", "entity_type": "technology", "aliases": ("ai", "ia", "inteligencia artificial", "artificial intelligence")},
    "machine learning": {"category": "AI Analytics", "entity_type": "explicit_skill", "aliases": ("machine learning", "aprendizaje automatico", "ml", "modelos predictivos")},
    "deep learning": {"category": "AI Analytics", "entity_type": "explicit_skill", "aliases": ("deep learning", "aprendizaje profundo")},
    "predictive analytics": {"category": "AI Analytics", "entity_type": "explicit_skill", "aliases": ("predictive analytics", "analitica predictiva", "modelos predictivos")},
    "NLP": {"category": "AI Analytics", "entity_type": "technology", "aliases": ("nlp", "procesamiento de lenguaje natural", "natural language processing")},
    "LLM": {"category": "GenAI Analytics", "entity_type": "technology", "aliases": ("llm", "large language models", "modelos de lenguaje")},
    "OpenAI": {"category": "GenAI Analytics", "entity_type": "tool", "aliases": ("openai", "chatgpt", "gpt")},
    "Copilot BI": {"category": "GenAI Analytics", "entity_type": "technology", "aliases": ("copilot", "copilot bi", "microsoft copilot")},
    "RAG": {"category": "GenAI Analytics", "entity_type": "technology", "aliases": ("rag", "retrieval augmented generation")},
    "GenAI analytics": {"category": "GenAI Analytics", "entity_type": "inferred_skill", "aliases": ("genai analytics", "generative ai analytics", "analitica generativa")},
    "MLflow": {"category": "AI Analytics", "entity_type": "tool", "aliases": ("mlflow",)},
    "MLOps": {"category": "AI Analytics", "entity_type": "methodology", "aliases": ("mlops", "model operations")},
    # Governance / Quality
    "data governance": {"category": "Governance", "entity_type": "methodology", "aliases": ("data governance", "gobierno de datos", "gobernanza de datos")},
    "data quality": {"category": "Governance", "entity_type": "methodology", "aliases": ("data quality", "calidad de datos", "calidad del dato")},
    "data catalog": {"category": "Governance", "entity_type": "tool", "aliases": ("data catalog", "catalogo de datos")},
    "lineage": {"category": "Governance", "entity_type": "methodology", "aliases": ("lineage", "linaje", "linaje de datos")},
    "metadata": {"category": "Governance", "entity_type": "methodology", "aliases": ("metadata", "metadatos")},
    "privacy": {"category": "Governance", "entity_type": "methodology", "aliases": ("privacy", "privacidad", "proteccion de datos")},
    "compliance": {"category": "Governance", "entity_type": "methodology", "aliases": ("compliance", "cumplimiento")},
    "security": {"category": "Governance", "entity_type": "methodology", "aliases": ("security", "seguridad", "seguridad de datos")},
    # Programacion / Analytics
    "Python": {"category": "Programming / Analytics", "entity_type": "technology", "aliases": ("python", "py")},
    "R": {"category": "Programming / Analytics", "entity_type": "technology", "aliases": ("lenguaje r", "r programming", "programacion en r")},
    "pandas": {"category": "Programming / Analytics", "entity_type": "tool", "aliases": ("pandas",)},
    "numpy": {"category": "Programming / Analytics", "entity_type": "tool", "aliases": ("numpy",)},
    "scikit-learn": {"category": "Programming / Analytics", "entity_type": "tool", "aliases": ("scikit-learn", "sklearn", "scikit learn")},
    "notebooks": {"category": "Programming / Analytics", "entity_type": "tool", "aliases": ("notebooks", "jupyter notebooks")},
    "Jupyter": {"category": "Programming / Analytics", "entity_type": "tool", "aliases": ("jupyter", "jupyterlab")},
    "APIs": {"category": "Programming / Analytics", "entity_type": "technology", "aliases": ("api", "apis", "rest api", "servicios rest")},
    # Metodologias
    "Agile": {"category": "Methodologies", "entity_type": "methodology", "aliases": ("agile", "agil", "metodologias agiles")},
    "Scrum": {"category": "Methodologies", "entity_type": "methodology", "aliases": ("scrum",)},
    "Kanban": {"category": "Methodologies", "entity_type": "methodology", "aliases": ("kanban",)},
    "ITIL": {"category": "Methodologies", "entity_type": "methodology", "aliases": ("itil",)},
    "Design Thinking": {"category": "Methodologies", "entity_type": "methodology", "aliases": ("design thinking",)},
    "CRISP-DM": {"category": "Methodologies", "entity_type": "methodology", "aliases": ("crisp-dm", "crisp dm")},
    "data storytelling": {"category": "Methodologies", "entity_type": "methodology", "aliases": ("data storytelling", "storytelling de datos")},
    # Soft skills
    "comunicacion": {"category": "Soft Skills", "entity_type": "soft_skill", "aliases": ("comunicacion", "communication", "comunicacion efectiva")},
    "liderazgo": {"category": "Soft Skills", "entity_type": "soft_skill", "aliases": ("liderazgo", "leadership")},
    "pensamiento analitico": {"category": "Soft Skills", "entity_type": "soft_skill", "aliases": ("pensamiento analitico", "analytical thinking")},
    "resolucion de problemas": {"category": "Soft Skills", "entity_type": "soft_skill", "aliases": ("resolucion de problemas", "problem solving")},
    "trabajo en equipo": {"category": "Soft Skills", "entity_type": "soft_skill", "aliases": ("trabajo en equipo", "teamwork")},
    "gestion de stakeholders": {"category": "Soft Skills", "entity_type": "soft_skill", "aliases": ("stakeholders", "gestion de stakeholders", "partes interesadas")},
    "ingles": {"category": "Soft Skills", "entity_type": "soft_skill", "aliases": ("ingles", "english", "b2", "c1")},
}

ALIAS_TO_SKILL = {
    normalize_text(alias): canonical
    for canonical, definition in EXPANDED_SKILLS.items()
    for alias in definition["aliases"]  # type: ignore[index]
}

LEGAL_OR_PORTAL_CONTEXT_TERMS = {
    "politica de privacidad",
    "privacy policy",
    "politica de cookies",
    "cookies",
    "condiciones de uso",
    "terminos y condiciones",
    "proteccion de datos personales",
    "tratamiento de datos personales",
}

LEGAL_CONTEXT_SKILLS = {"privacy", "compliance", "security", "metadata", "data catalog", "lineage"}


def _contains_alias(text: str, alias: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", text) is not None


def extract_expanded_labor_skills(text: str, *, section: str = "description") -> list[ExpandedLaborSkill]:
    normalized_text = normalize_text(text)
    legal_or_portal_context = section in {"description", "portal_taxonomy"} and any(term in normalized_text for term in LEGAL_OR_PORTAL_CONTEXT_TERMS)
    section_confidence = SECTION_CONFIDENCE.get(section, 0.7)
    found: dict[str, ExpandedLaborSkill] = {}
    for alias, canonical in ALIAS_TO_SKILL.items():
        if not _contains_alias(normalized_text, alias):
            continue
        if legal_or_portal_context and canonical in LEGAL_CONTEXT_SKILLS:
            continue
        definition = EXPANDED_SKILLS[canonical]
        confidence = section_confidence if alias == normalize_text(canonical) else section_confidence * 0.92
        item = ExpandedLaborSkill(
            original=alias,
            normalized=canonical,
            category=str(definition["category"]),
            entity_type=str(definition["entity_type"]),
            confidence=round(min(confidence, 1.0), 4),
            section=section,
        )
        current = found.get(canonical)
        if current is None or item.confidence > current.confidence:
            found[canonical] = item
    return sorted(found.values(), key=lambda item: (item.category, item.normalized))


def merge_expanded_skills(items: Iterable[ExpandedLaborSkill]) -> list[ExpandedLaborSkill]:
    best: dict[str, ExpandedLaborSkill] = {}
    for item in items:
        current = best.get(item.normalized)
        if current is None or item.confidence > current.confidence:
            best[item.normalized] = item
    return sorted(best.values(), key=lambda item: item.confidence, reverse=True)
