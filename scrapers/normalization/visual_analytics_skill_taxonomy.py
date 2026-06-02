from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class VisualAnalyticsSkill:
    original: str
    normalized: str
    skill_type: str
    confidence: float


def normalize_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9+#.]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


SKILL_DEFINITIONS: dict[str, dict[str, object]] = {
    "BI": {
        "type": "technical_skill",
        "aliases": ("business intelligence", "inteligencia de negocios", "bi", "analitica empresarial"),
    },
    "visualizacion analitica": {
        "type": "technical_skill",
        "aliases": ("visual analytics", "visualizacion analitica", "visualizacion de datos", "data visualization"),
    },
    "dashboarding": {
        "type": "technical_skill",
        "aliases": ("dashboards", "dashboard", "dashboarding", "tableros de control", "cuadros de mando"),
    },
    "storytelling with data": {
        "type": "soft_skill",
        "aliases": ("data storytelling", "storytelling with data", "narrativa de datos", "comunicacion de datos"),
    },
    "data governance": {
        "type": "methodology",
        "aliases": ("gobierno de datos", "data governance", "gobernanza de datos"),
    },
    "data quality": {
        "type": "methodology",
        "aliases": ("calidad de datos", "data quality", "calidad del dato"),
    },
    "data warehouse": {
        "type": "platform",
        "aliases": ("almacen de datos", "data warehouse", "data warehousing", "bodega de datos"),
    },
    "data lake": {
        "type": "platform",
        "aliases": ("lago de datos", "data lake"),
    },
    "lakehouse": {
        "type": "platform",
        "aliases": ("arquitectura lakehouse", "lakehouse", "data lakehouse"),
    },
    "AI": {
        "type": "emerging_skill",
        "aliases": ("inteligencia artificial", "ai", "artificial intelligence", "ia"),
    },
    "machine learning": {
        "type": "emerging_skill",
        "aliases": ("aprendizaje automatico", "machine learning", "ml", "modelos predictivos"),
    },
    "big data processing": {
        "type": "technical_skill",
        "aliases": ("procesamiento masivo de datos", "big data processing", "procesamiento distribuido"),
    },
    "Power BI": {"type": "tool", "aliases": ("power bi", "powerbi", "microsoft power bi", "pbi")},
    "Tableau": {"type": "tool", "aliases": ("tableau",)},
    "SQL": {"type": "language", "aliases": ("sql", "structured query language")},
    "Python": {"type": "language", "aliases": ("python", "py")},
    "R": {"type": "language", "aliases": ("lenguaje r", "r programming", "programacion en r")},
    "ETL": {"type": "methodology", "aliases": ("etl", "extract transform load", "extraccion transformacion carga")},
    "Spark": {"type": "platform", "aliases": ("spark", "apache spark", "pyspark")},
    "Hadoop": {"type": "platform", "aliases": ("hadoop", "apache hadoop")},
    "Databricks": {"type": "platform", "aliases": ("databricks",)},
    "Snowflake": {"type": "platform", "aliases": ("snowflake",)},
    "MLOps": {"type": "emerging_skill", "aliases": ("mlops", "model operations", "operacionalizacion de modelos")},
    "DataOps": {"type": "emerging_skill", "aliases": ("dataops", "data operations")},
    "Azure Data": {"type": "cloud", "aliases": ("azure data", "azure synapse", "microsoft fabric", "azure analytics")},
    "AWS Analytics": {"type": "cloud", "aliases": ("aws analytics", "redshift", "aws glue", "amazon quicksight")},
    "Google Cloud Analytics": {"type": "cloud", "aliases": ("google cloud analytics", "bigquery", "looker", "gcp analytics")},
    "KPIs": {"type": "foundational_skill", "aliases": ("kpi", "kpis", "indicadores", "indicadores clave")},
    "estadistica": {"type": "foundational_skill", "aliases": ("estadistica", "statistics", "analisis estadistico")},
    # Criminology labor intelligence
    "criminal investigation": {
        "type": "technical_skill",
        "aliases": ("criminal investigation", "investigacion criminal", "investigacion judicial", "investigacion criminalistica"),
    },
    "victimology": {"type": "technical_skill", "aliases": ("victimology", "victimologia", "victim assistance", "atencion a victimas")},
    "forensic analysis": {
        "type": "technical_skill",
        "aliases": ("forensic analysis", "analisis forense", "criminalistica", "criminalistics", "forensics", "forensic science"),
    },
    "cybercrime": {"type": "technical_skill", "aliases": ("cybercrime", "ciberdelito", "delito informatico", "computer crime")},
    "criminal intelligence": {
        "type": "technical_skill",
        "aliases": ("criminal intelligence", "inteligencia criminal", "analisis de inteligencia criminal"),
    },
    "compliance": {"type": "methodology", "aliases": ("compliance", "cumplimiento", "cumplimiento normativo")},
    "risk analysis": {"type": "technical_skill", "aliases": ("risk analysis", "analisis de riesgo", "risk assessment", "risk management")},
    "chain of custody": {"type": "methodology", "aliases": ("chain of custody", "cadena de custodia", "custodia de evidencia")},
    "organized crime": {"type": "technical_skill", "aliases": ("organized crime", "crimen organizado", "delincuencia organizada")},
    "financial crime": {
        "type": "technical_skill",
        "aliases": ("financial crime", "delito financiero", "fraude financiero", "money laundering", "lavado de activos"),
    },
    "public safety": {"type": "technical_skill", "aliases": ("public safety", "public security", "seguridad publica", "seguridad ciudadana")},
    "criminal analysis": {"type": "technical_skill", "aliases": ("criminal analysis", "analisis criminal", "analisis criminologico")},
    "crime prevention": {"type": "technical_skill", "aliases": ("crime prevention", "prevencion del delito", "prevencion criminal")},
    "penitentiary systems": {"type": "technical_skill", "aliases": ("penitentiary systems", "sistemas penitenciarios", "sistema penitenciario")},
}

ALIAS_TO_CANONICAL: dict[str, str] = {
    normalize_text(alias): canonical
    for canonical, definition in SKILL_DEFINITIONS.items()
    for alias in definition["aliases"]  # type: ignore[index]
}


def normalize_visual_analytics_skill(value: str) -> str:
    key = normalize_text(value)
    return ALIAS_TO_CANONICAL.get(key, value.strip())


def classify_visual_analytics_skill(value: str) -> str:
    normalized = normalize_visual_analytics_skill(value)
    definition = SKILL_DEFINITIONS.get(normalized)
    if definition:
        return str(definition["type"])
    return "technical_skill"


def _contains_alias(text: str, alias: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", text) is not None


def extract_visual_analytics_skills(text: str) -> list[VisualAnalyticsSkill]:
    normalized_text = normalize_text(text)
    found: dict[str, VisualAnalyticsSkill] = {}
    for alias, canonical in ALIAS_TO_CANONICAL.items():
        if not _contains_alias(normalized_text, alias):
            continue
        definition = SKILL_DEFINITIONS[canonical]
        confidence = 0.95 if alias == normalize_text(canonical) else 0.84
        current = found.get(canonical)
        candidate = VisualAnalyticsSkill(alias, canonical, str(definition["type"]), confidence)
        if current is None or candidate.confidence > current.confidence:
            found[canonical] = candidate
    return sorted(found.values(), key=lambda item: (item.skill_type, item.normalized))


def skills_to_dicts(skills: Iterable[VisualAnalyticsSkill]) -> list[dict[str, object]]:
    return [asdict(skill) for skill in skills]
