from __future__ import annotations

from agents.visual_analytics_labor_agent import VisualAnalyticsLaborAgent


def test_portal_taxonomy_skills_page_never_reaches_gold() -> None:
    html = """
    <html><head><title>Skills</title></head>
    <body>
      <main>
        <h1>Skills</h1>
        <section>
          Power BI SQL Python ETL Hadoop Spark BI Power BI Tableau Machine Learning
          filtros areas ubicaciones roles lugar de trabajo categorias buscar ofertas
        </section>
      </main>
    </body></html>
    """

    result = VisualAnalyticsLaborAgent().inspect_static_html(
        html=html,
        source_name="Ticjob",
        source_url="javascript:;",
        fallback_title="Skills",
    )

    assert result.silver.document_type == "portal_taxonomy"
    assert result.silver.is_real_job_posting is False
    assert result.silver.accepted_for_gold is False
    assert result.gold is None
    assert result.silver.job_evidence_skills == []
    assert "Power BI" in (result.silver.portal_taxonomy_skills or [])


def test_filter_page_with_analytics_terms_is_not_job_evidence() -> None:
    html = """
    <html><head><title>Filtros</title></head>
    <body>
      <main>
        <h1>Filtros</h1>
        <nav>
          Power BI SQL Tableau Python BI KPIs dashboarding filtros categorias ubicaciones
          lugar de trabajo buscar ofertas areas empresas cargos
        </nav>
      </main>
    </body></html>
    """

    result = VisualAnalyticsLaborAgent().inspect_static_html(
        html=html,
        source_name="Elempleo",
        source_url="https://www.elempleo.com/co/ofertas-empleo/",
        fallback_title="Filtros",
    )

    assert result.silver.document_type in {"portal_taxonomy", "filter_page"}
    assert result.silver.accepted_for_gold is False
    assert result.gold is None
    assert not result.silver.job_evidence_skills
    assert {"Power BI", "SQL", "Tableau"} & set(result.silver.portal_taxonomy_skills or [])


def test_real_job_extracts_job_evidence_skills_and_can_reach_gold() -> None:
    html = """
    <html><head><title>Analista BI Power BI</title></head>
    <body>
      <main>
        <h1>Analista BI Power BI</h1>
        <span class="company">DataCo</span>
        <span class="location">Bogota</span>
        <section class="description">
          Empresa requiere analista BI. Responsabilidades: crear dashboards ejecutivos,
          KPIs y reporting corporativo. Requisitos: experiencia en SQL, Power BI,
          Tableau, ETL y data warehouse. Modalidad hibrida, contrato indefinido y
          postulacion directa con la empresa.
        </section>
      </main>
    </body></html>
    """

    result = VisualAnalyticsLaborAgent().inspect_static_html(
        html=html,
        source_name="Elempleo",
        source_url="https://example.com/jobs/bi-power-bi",
        fallback_title="Analista BI Power BI",
    )

    assert result.silver.document_type == "job_posting"
    assert result.silver.is_real_job_posting is True
    assert {"Power BI", "SQL", "KPIs"} & set(result.silver.job_evidence_skills or [])
    assert result.silver.portal_taxonomy_skills == []
    assert result.gold is not None
