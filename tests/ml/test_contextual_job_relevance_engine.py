from __future__ import annotations

from ml.relevance.contextual_job_relevance_engine import score_contextual_relevance


def test_generic_backend_with_analytics_stack_is_accepted() -> None:
    result = score_contextual_relevance(
        title="Backend Developer",
        description=(
            "Desarrollo de data pipelines para analytics, SQL, Python, ETL, dashboards, "
            "Power BI, reporting, data warehouse y gobierno de datos."
        ),
    )
    assert result.accepted is True
    assert result.contextual_relevance_score >= 0.50
    assert "sql" in result.detected_stack


def test_pure_helpdesk_is_rejected() -> None:
    result = score_contextual_relevance(
        title="Tecnico de soporte helpdesk",
        description="Mesa de ayuda, soporte en sitio, mantenimiento hardware, impresoras y active directory.",
    )
    assert result.accepted is False
    assert result.decision_reason == "rejected_negative_support_or_infrastructure_signal"


def test_bi_analytics_is_accepted() -> None:
    result = score_contextual_relevance(
        title="BI Analyst",
        description="Power BI, Tableau, SQL, dashboards, KPIs, business intelligence y storytelling with data.",
    )
    assert result.accepted is True
    assert result.role_class in {"analytics_bi", "reporting_visualization"}


def test_etl_data_engineering_is_accepted() -> None:
    result = score_contextual_relevance(
        title="ETL Developer",
        description="Data pipelines, Spark, Databricks, Snowflake, data lake, data warehouse, Python y SQL.",
    )
    assert result.accepted is True
    assert result.data_engineering_density > 0


def test_pure_infrastructure_is_rejected() -> None:
    result = score_contextual_relevance(
        title="Ingeniero NOC",
        description="Networking, cableado, monitoreo de red, infraestructura, soporte en sitio y routers.",
    )
    assert result.accepted is False
    assert result.contextual_relevance_score < 0.45
