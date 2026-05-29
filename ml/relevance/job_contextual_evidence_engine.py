from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scrapers.normalization.visual_analytics_skill_taxonomy import normalize_text  # noqa: E402


@dataclass(frozen=True)
class JobContextualEvidence:
    evidence_summary: str
    detected_analytics_signals: list[str]
    detected_visualization_signals: list[str]
    detected_data_engineering_signals: list[str]
    detected_cloud_signals: list[str]
    detected_bi_signals: list[str]
    detected_governance_signals: list[str]
    detected_negative_signals: list[str]
    evidence_strength: float
    document_type: str = "job_posting"
    evidence_source_type: str = "job_evidence"
    is_real_job_posting: bool = True


SIGNAL_GROUPS: dict[str, tuple[str, ...]] = {
    "analytics": ("analytics", "analitica", "analítica", "data analysis", "analisis de datos", "modelos predictivos", "predictive analytics"),
    "visualization": ("power bi", "tableau", "dashboard", "dashboards", "visualizacion", "visualización", "looker", "storytelling"),
    "data_engineering": ("etl", "pipeline", "pipelines", "data warehouse", "warehouse", "data lake", "lakehouse", "spark", "databricks", "snowflake"),
    "cloud": ("azure", "aws", "gcp", "bigquery", "redshift", "cloud analytics", "azure data"),
    "bi": ("bi", "business intelligence", "inteligencia de negocios", "reporting", "kpi", "kpis", "indicadores"),
    "governance": ("data governance", "gobierno de datos", "data quality", "calidad de datos", "linaje", "lineage"),
    "negative": ("helpdesk", "mesa de ayuda", "soporte tecnico", "soporte técnico", "hardware", "impresoras", "cableado", "networking puro", "mantenimiento fisico", "mantenimiento físico"),
}


def detect_group(text: str, group: str) -> list[str]:
    normalized = f" {normalize_text(text)} "
    hits = []
    for signal in SIGNAL_GROUPS[group]:
        if f" {normalize_text(signal)} " in normalized:
            hits.append(signal)
    return sorted(set(hits))


def build_contextual_evidence(
    *,
    title: str,
    description: str,
    skills: Iterable[str] = (),
    technologies: Iterable[str] = (),
    document_type: str = "job_posting",
    evidence_source_type: str = "job_evidence",
    is_real_job_posting: bool = True,
) -> JobContextualEvidence:
    if document_type != "job_posting" or evidence_source_type != "job_evidence" or not is_real_job_posting:
        return JobContextualEvidence(
            evidence_summary="",
            detected_analytics_signals=[],
            detected_visualization_signals=[],
            detected_data_engineering_signals=[],
            detected_cloud_signals=[],
            detected_bi_signals=[],
            detected_governance_signals=[],
            detected_negative_signals=[],
            evidence_strength=0.0,
            document_type=document_type,
            evidence_source_type=evidence_source_type,
            is_real_job_posting=False,
        )
    text = " ".join([title, description, " ".join(skills), " ".join(technologies)])
    analytics = detect_group(text, "analytics")
    visualization = detect_group(text, "visualization")
    data_engineering = detect_group(text, "data_engineering")
    cloud = detect_group(text, "cloud")
    bi = detect_group(text, "bi")
    governance = detect_group(text, "governance")
    negative = detect_group(text, "negative")
    positive_count = len(analytics) + len(visualization) + len(data_engineering) + len(cloud) + len(bi) + len(governance)
    cluster_count = sum(bool(group) for group in (analytics, visualization, data_engineering, cloud, bi, governance))
    evidence_strength = min((positive_count / 10) * 0.65 + (cluster_count / 6) * 0.35, 1.0)
    summary_parts = []
    if visualization:
        summary_parts.append("visualizacion/BI: " + ", ".join(visualization[:4]))
    if bi:
        summary_parts.append("reporting e indicadores: " + ", ".join(bi[:4]))
    if data_engineering:
        summary_parts.append("ingenieria de datos: " + ", ".join(data_engineering[:4]))
    if cloud:
        summary_parts.append("cloud data: " + ", ".join(cloud[:4]))
    if analytics:
        summary_parts.append("analitica: " + ", ".join(analytics[:4]))
    if governance:
        summary_parts.append("gobierno/calidad: " + ", ".join(governance[:4]))
    evidence_summary = "Accepted because it contains " + "; ".join(summary_parts) + "." if summary_parts else ""
    return JobContextualEvidence(
        evidence_summary=evidence_summary,
        detected_analytics_signals=analytics,
        detected_visualization_signals=visualization,
        detected_data_engineering_signals=data_engineering,
        detected_cloud_signals=cloud,
        detected_bi_signals=bi,
        detected_governance_signals=governance,
        detected_negative_signals=negative,
        evidence_strength=round(evidence_strength, 4),
        document_type=document_type,
        evidence_source_type=evidence_source_type,
        is_real_job_posting=is_real_job_posting,
    )
