from __future__ import annotations

from agents.visual_analytics_labor_agent import VisualAnalyticsLaborAgent, promote_to_gold


def test_agent_promotes_high_confidence_analytics_vacancy_to_gold() -> None:
    html = """
    <html><head><title>BI Analyst Power BI</title></head>
    <body>
      <main>
        <h1>BI Analyst Power BI</h1>
        <span class="company">DataCo</span>
        <span class="location">Bogota Colombia</span>
        <section class="description">
          Responsable de dashboards ejecutivos, KPIs, reporting corporativo, SQL, Power BI,
          Tableau, ETL, data warehouse, data governance, data quality, Python y analytics.
          Debe construir visualizaciones, storytelling with data y modelos predictivos para decisiones.
        </section>
      </main>
    </body></html>
    """
    result = VisualAnalyticsLaborAgent().inspect_static_html(
        html=html,
        source_name="Elempleo",
        source_url="https://example.com/job/1",
        fallback_title="BI Analyst Power BI",
    )
    assert result.silver.accepted_for_gold is True
    assert result.gold is not None
    assert "Power BI" in result.silver.extracted_skills
    assert result.gold.evidence_summary


def test_agent_keeps_support_noise_in_bronze_silver_but_not_gold() -> None:
    html = """
    <html><head><title>Tecnico de soporte</title></head>
    <body>
      <main>
        <h1>Tecnico de soporte helpdesk</h1>
        <section class="description">
          Mesa de ayuda, soporte en sitio, mantenimiento hardware, impresoras,
          cableado, active directory, networking y atencion de tickets.
        </section>
      </main>
    </body></html>
    """
    result = VisualAnalyticsLaborAgent().inspect_static_html(
        html=html,
        source_name="Ticjob",
        source_url="https://example.com/job/2",
        fallback_title="Tecnico de soporte",
    )
    assert result.bronze.raw_text
    assert result.silver.accepted_for_gold is False
    assert result.gold is None
    assert "negative" in result.silver.rejection_reason or "support" in result.silver.rejection_reason


def test_gold_gate_requires_evidence_summary() -> None:
    html = "<html><body><h1>Backend Developer</h1><p>Desarrollo general de servicios.</p></body></html>"
    result = VisualAnalyticsLaborAgent().inspect_static_html(
        html=html,
        source_name="Ticjob",
        source_url="https://example.com/job/3",
        fallback_title="Backend Developer",
    )
    assert promote_to_gold(result.silver) is None
