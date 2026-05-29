from __future__ import annotations

from scrapers.connectors.base import is_visual_analytics_related, job_relevance_score
from scrapers.connectors.ticjob_connector import TicjobConnector


def test_ticjob_connector_extracts_structured_cards() -> None:
    html = """
    <article class="job-card">
      <a href="/oferta/123"><h2>Analista BI Power BI</h2></a>
      <span class="company">Empresa Data</span>
      <span class="location">Bogota, Colombia</span>
      <time>Publicado hoy</time>
      <span class="tag">Power BI</span><span class="tag">SQL</span><span class="tag">ETL</span>
      <p>Vacante para analista BI con dashboards, SQL, Power BI, data governance y visualizacion ejecutiva para equipos de analitica.</p>
    </article>
    """
    connector = TicjobConnector(max_pages=1, max_jobs=10)
    jobs = connector.extract_from_html(html, "https://ticjob.co/")
    assert jobs
    job = jobs[0]
    assert job.title == "Analista BI Power BI"
    assert "Power BI" in job.skills
    assert "SQL" in job.skills
    keep, reason = is_visual_analytics_related(job)
    assert keep is True, reason
    assert job_relevance_score(job, source_priority="alta") >= 0.65


def test_ticjob_connector_discards_helpdesk_without_data_signal() -> None:
    html = """
    <article class="job-card">
      <a href="/oferta/456"><h2>Soporte tecnico helpdesk</h2></a>
      <span class="company">Empresa Soporte</span>
      <span class="location">Bogota, Colombia</span>
      <p>Mesa de ayuda, soporte tecnico, atencion de tickets, call center y service desk para usuarios internos.</p>
    </article>
    """
    connector = TicjobConnector(max_pages=1, max_jobs=10)
    job = connector.extract_from_html(html, "https://ticjob.co/")[0]
    keep, reason = is_visual_analytics_related(job)
    assert keep is False
    assert reason == "irrelevant_support_helpdesk"


def test_ticjob_connector_uses_parent_card_when_link_text_is_company() -> None:
    html = """
    <div class="job-result-card">
      <a href="/es/it-job-openings/analytics-engineer-bogota">SETI S.A.S.</a>
      <h3 class="job-title">Analytics Engineer</h3>
      <span class="location">Bogota</span>
      <p>Responsabilidades: construir pipelines, reporting, SQL, dashboards y Power BI para equipos de datos.</p>
    </div>
    """
    connector = TicjobConnector(max_pages=1, max_jobs=10)
    jobs = connector.extract_from_html(html, "https://ticjob.co/es/search")

    assert jobs
    assert jobs[0].title == "Analytics Engineer"
    assert jobs[0].company == "SETI S.A.S."
