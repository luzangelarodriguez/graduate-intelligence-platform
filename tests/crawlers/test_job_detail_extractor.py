from crawlers.core.job_detail_extractor import extract_job_detail_from_html


def test_extracts_job_detail_fields_from_html() -> None:
    html = """
    <main>
      <h1>Analista BI Power BI</h1>
      <div class="company">DataCo</div>
      <div class="location">Bogota</div>
      <article class="description">
        Responsabilidades: construir dashboards ejecutivos y KPIs.
        Requisitos: experiencia con Power BI, SQL y ETL.
        Modalidad remoto.
      </article>
    </main>
    """

    detail = extract_job_detail_from_html(html, source_url="https://jobs.example.com/1")

    assert detail.title == "Analista BI Power BI"
    assert detail.company == "DataCo"
    assert detail.location == "Bogota"
    assert detail.modality == "remote"
    assert detail.requirements
    assert detail.responsibilities
