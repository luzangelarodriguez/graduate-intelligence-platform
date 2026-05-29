from crawlers.core.document_classifier import classify_crawled_document, is_strong_job_posting


def test_rejects_filter_or_taxonomy_page_as_job() -> None:
    result = classify_crawled_document(
        {
            "title": "Skills",
            "company": "",
            "description": "Power BI SQL Python Tableau filtros categorias ciudades roles tecnologias",
            "tags": ["Power BI", "SQL"],
        },
        source_url="javascript:;",
    )

    assert result["document_type"] == "portal_taxonomy"
    assert result["is_real_job_posting"] is False


def test_accepts_real_job_posting() -> None:
    payload = {
        "title": "Analista BI",
        "company": "DataCo",
        "description": "Responsabilidades: construir dashboards. Requisitos: experiencia en Power BI, SQL, KPIs y reporting corporativo.",
        "tags": [],
    }

    assert is_strong_job_posting(payload, source_url="https://jobs.example.com/1") is True
