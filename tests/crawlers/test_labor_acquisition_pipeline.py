from agents.visual_analytics_labor_agent import AgentExtractionResult, BronzeEvidence, SilverEvidence
from pipelines.run_labor_acquisition_platform import run_labor_acquisition


def _result() -> AgentExtractionResult:
    bronze = BronzeEvidence(
        source_name="unit",
        source_url="https://jobs.example.com/1",
        raw_html="",
        raw_text="Analista BI Power BI SQL dashboards",
        raw_json={},
        extraction_timestamp="2026-05-28T00:00:00Z",
        page_title="Analista BI",
        http_status=200,
        extraction_method="unit",
        content_hash="hash",
        detected_language="es",
    )
    silver = SilverEvidence(
        source_name="unit",
        source_url="https://jobs.example.com/1",
        normalized_title="Analista BI",
        normalized_company="DataCo",
        normalized_location="Bogota",
        normalized_description="Responsabilidades y requisitos con Power BI, SQL, dashboards y KPIs.",
        extracted_skills=["Power BI", "SQL"],
        extracted_tools=["Power BI"],
        extracted_cloud=[],
        extracted_frameworks=[],
        analytics_density=0.7,
        contextual_relevance_score=0.8,
        semantic_score=0.7,
        rejection_reason="silver_only",
        accepted_for_gold=False,
        parser_version="unit",
        content_hash="hash",
        contextual={},
        document_type="job_posting",
        evidence_source_type="job_evidence",
        is_real_job_posting=True,
        invalid_job_reason="",
        job_evidence_skills=["Power BI", "SQL"],
        portal_taxonomy_skills=[],
    )
    return AgentExtractionResult(bronze=bronze, silver=silver, gold=None)


def test_labor_acquisition_pipeline_dry_run_recalculates_market(monkeypatch, tmp_path) -> None:
    from pipelines import run_labor_acquisition_platform as pipeline

    monkeypatch.setattr(pipeline, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(pipeline, "RESULTS_JSON", tmp_path / "labor_acquisition_results.json")
    monkeypatch.setattr(pipeline, "_run_source", lambda source, execute_network, max_jobs, max_pages: ([_result()], []))
    monkeypatch.setattr(pipeline, "persist_layers", lambda results, persist_gold=False: {"bronze": len(results), "silver": len(results), "gold": 0})

    result = run_labor_acquisition(
        sources=["unit"],
        execute_network=False,
        max_jobs=1,
        max_pages=1,
        persist=False,
        quality_review=True,
    )

    assert result["correlation_id"]
    assert result["results"] == 1
    assert result["real_job_postings"] == 1
    assert result["source_metrics"]["unit"]["health_score"] > 0
    assert (tmp_path / "labor_acquisition_run_report.md").exists()
    assert (tmp_path / "labor_acquisition_health_report.json").exists()
