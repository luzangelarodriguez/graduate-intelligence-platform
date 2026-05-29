from __future__ import annotations

from ml.relevance.hybrid_semantic_relevance_engine import score_hybrid_semantic_relevance


def test_backend_with_powerbi_sql_is_accepted() -> None:
    result = score_hybrid_semantic_relevance(
        title="Backend Developer",
        description=(
            "Construye APIs y servicios backend con SQL, Power BI, dashboards ejecutivos, "
            "pipelines ETL, reporting y KPIs para plataformas de analytics."
        ),
    )

    assert result.accepted
    assert result.final_semantic_relevance_score >= 0.65
    assert "business_intelligence" in result.cluster_hits
    assert result.evidence_summary


def test_etl_dashboards_is_accepted() -> None:
    result = score_hybrid_semantic_relevance(
        title="ETL Developer",
        description="Procesos ETL, dashboards, SQL, data warehouse y reporting corporativo para equipos de datos.",
    )

    assert result.accepted
    assert result.tier in {"Gold A", "Gold B", "Silver"}
    assert "data_engineering" in result.cluster_hits


def test_azure_kpis_reporting_is_accepted() -> None:
    result = score_hybrid_semantic_relevance(
        title="Azure Analytics Engineer",
        description="Azure Data, KPIs, reporting, Power BI, SQL, cloud analytics y tableros para negocio.",
    )

    assert result.accepted
    assert result.final_semantic_relevance_score >= 0.50
    assert "cloud_data" in result.cluster_hits


def test_pure_helpdesk_is_rejected() -> None:
    result = score_hybrid_semantic_relevance(
        title="Tecnico helpdesk",
        description="Soporte tecnico a usuarios, impresoras, hardware, mesa de ayuda, cableado y mantenimiento fisico.",
    )

    assert not result.accepted
    assert result.tier == "Rejected"
    assert result.rejection_reason == "rejected_pure_support_or_infrastructure"


def test_pure_networking_is_rejected() -> None:
    result = score_hybrid_semantic_relevance(
        title="Administrador de redes",
        description="Networking puro, redes LAN y WAN, switches, cableado, soporte en sitio e infraestructura fisica.",
    )

    assert not result.accepted
    assert result.tier == "Rejected"


def test_bi_engineer_is_gold() -> None:
    result = score_hybrid_semantic_relevance(
        title="BI Engineer",
        description="Power BI, Tableau, SQL, dashboards, ETL, business intelligence, reporting y KPIs.",
    )

    assert result.accepted
    assert result.tier.startswith("Gold")
    assert result.career_family == "analytics_bi_visualization"


def test_dataops_analytics_is_accepted() -> None:
    result = score_hybrid_semantic_relevance(
        title="DataOps Engineer",
        description="DataOps, analytics, pipelines, data quality, SQL, cloud analytics y observability.",
    )

    assert result.accepted
    assert result.final_semantic_relevance_score >= 0.50
    assert "dataops" in result.cluster_hits
