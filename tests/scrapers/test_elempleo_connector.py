from __future__ import annotations

from scrapers.connectors.base import is_visual_analytics_related
from scrapers.connectors.elempleo_connector import ElempleoConnector


def test_elempleo_connector_extracts_jobposting_json_ld() -> None:
    html = """
    <script type="application/ld+json">
    {
      "@type": "JobPosting",
      "title": "Data Analyst SQL Python",
      "datePosted": "2026-05-25",
      "description": "Rol de analitica de datos con SQL, Python, Power BI, ETL, dashboards y data quality para Colombia.",
      "hiringOrganization": {"name": "DataCo"},
      "jobLocation": {"address": {"addressLocality": "Bogota", "addressCountry": "CO"}},
      "url": "https://www.elempleo.com/co/ofertas/data-analyst"
    }
    </script>
    """
    connector = ElempleoConnector(max_pages=1, max_jobs=10)
    jobs = connector.extract_from_html(html, "https://www.elempleo.com/co/ofertas-empleo/")
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Data Analyst SQL Python"
    assert {"SQL", "Python", "Power BI"}.issubset(set(job.skills))
    keep, reason = is_visual_analytics_related(job)
    assert keep is True, reason
