from agents.visual_analytics_labor_agent import AgentExtractionResult, BronzeEvidence, SilverEvidence
from crawlers.core.data_quality import build_quality_envelope, deduplicate_cross_source, normalize_salary


def _result(description: str = "Power BI SQL dashboards KPIs") -> AgentExtractionResult:
    bronze = BronzeEvidence(
        source_name="unit",
        source_url="https://jobs.example.com/1",
        raw_html="",
        raw_text=description,
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
        normalized_location="Bogota, Colombia",
        normalized_description=description,
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
        contextual={"salary": "$6000000 - $9000000 COP"},
        document_type="job_posting",
        evidence_source_type="job_evidence",
        is_real_job_posting=True,
        invalid_job_reason="",
        job_evidence_skills=["Power BI", "SQL"],
        portal_taxonomy_skills=[],
    )
    return AgentExtractionResult(bronze=bronze, silver=silver, gold=None)


def test_quality_envelope_scores_and_normalizes() -> None:
    envelope = build_quality_envelope(_result("Responsabilidades y requisitos con Power BI, SQL, dashboards, KPIs y reporting corporativo."))

    assert envelope.completeness_score > 0.8
    assert envelope.normalized_location["city"] == "Bogota"
    assert envelope.normalized_salary["currency"] == "COP"
    assert {"Power BI", "SQL"} & set(envelope.unified_skills)


def test_deduplicate_cross_source_uses_fingerprint() -> None:
    results = [_result("Power BI SQL dashboards KPIs reporting corporativo"), _result("Power BI SQL dashboards KPIs reporting corporativo")]

    assert len(deduplicate_cross_source(results)) == 1


def test_salary_normalization_extracts_range() -> None:
    salary = normalize_salary("$6.000.000 - $9.000.000 COP")

    assert salary["min"] == 6000000
    assert salary["max"] == 9000000
