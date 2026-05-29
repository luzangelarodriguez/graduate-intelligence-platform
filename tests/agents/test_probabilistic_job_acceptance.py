from agents.visual_analytics_labor_agent import classify_document_type, normalize_to_silver, parse_detail_html


def test_incomplete_analytics_job_becomes_probable_without_company() -> None:
    payload = {
        "title": "Analista BI Power BI",
        "company": "",
        "location": "Colombia",
        "description": (
            "Responsabilidades: construir dashboards, reportes ejecutivos y KPIs. "
            "Requisitos: SQL, Power BI, ETL y analitica de datos."
        ),
        "tags": [],
    }

    result = classify_document_type(payload, source_url="https://jobs.example.com/bi")

    assert result["document_type"] == "job_posting"
    assert result["job_probability_score"] >= 0.30
    assert result["curation_level"] in {"probable_job", "curated_job", "gold_job"}


def test_probable_job_preserves_job_evidence_skills_for_warehouse() -> None:
    html = """
    <html><body>
      <h1>Reporting Developer</h1>
      <main>
        Responsabilidades: crear dashboards, reporting corporativo y KPIs.
        Requisitos: SQL, Power BI, Python y ETL.
      </main>
    </body></html>
    """
    bronze, payload = parse_detail_html(
        html,
        source_name="Ticjob",
        source_url="https://jobs.example.com/reporting-developer",
        fallback_title="Reporting Developer",
    )

    silver = normalize_to_silver(bronze, payload)

    assert silver.job_probability_score >= 0.30
    assert silver.curation_level in {"probable_job", "curated_job", "gold_job"}
    assert {"SQL", "Power BI"} & set(silver.job_evidence_skills or [])
    assert silver.evidence_source_type == "job_evidence"
