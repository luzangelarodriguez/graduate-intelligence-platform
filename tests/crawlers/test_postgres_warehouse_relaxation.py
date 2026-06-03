from crawlers.storage.postgres_warehouse import _job_skills, _persistable_job, _persisted_description, _persisted_title, _processing_stage
from agents.visual_analytics_labor_agent import AgentExtractionResult, BronzeEvidence, SilverEvidence


def _result(*, document_type: str = "unknown", curation_level: str = "candidate_job", source_url: str = "https://jobs.example.com/1", title: str = "", description: str = "", portal_skills: list[str] | None = None) -> AgentExtractionResult:
    bronze = BronzeEvidence(
        source_name="unit",
        source_url=source_url,
        raw_html="",
        raw_text="raw fallback description",
        raw_json={},
        extraction_timestamp="2026-05-28T00:00:00Z",
        page_title="Fallback page title",
        http_status=200,
        extraction_method="unit",
        content_hash="hash",
        detected_language="es",
    )
    silver = SilverEvidence(
        source_name="unit",
        source_url=source_url,
        normalized_title=title,
        normalized_company="DataCo",
        normalized_location="Bogota",
        normalized_description=description,
        extracted_skills=[],
        extracted_tools=[],
        extracted_cloud=[],
        extracted_frameworks=[],
        analytics_density=0.2,
        contextual_relevance_score=0.2,
        semantic_score=0.2,
        rejection_reason="silver_only",
        accepted_for_gold=False,
        parser_version="unit",
        content_hash="hash",
        contextual={"portal_taxonomy_skills": portal_skills or []},
        document_type=document_type,
        evidence_source_type="portal_taxonomy",
        is_real_job_posting=False,
        invalid_job_reason="",
        job_evidence_skills=[],
        portal_taxonomy_skills=portal_skills or [],
        job_probability_score=0.21,
        curation_level=curation_level,
        semantic_evidence_count=0,
        top_acceptance_reasons=[],
        unknown_skill_candidates=[],
    )
    return AgentExtractionResult(bronze=bronze, silver=silver, gold=None)


def test_persistable_job_accepts_candidate_like_rows_without_company_or_salary_filters() -> None:
    result = _result(
        document_type="unknown",
        curation_level="probable_job",
        title="",
        description="",
        portal_skills=["SQL", "Power BI"],
    )

    assert _persistable_job(result) is True
    assert _processing_stage(result.silver) == "probable_job"
    assert _persisted_title(result) == "Fallback page title"
    assert _persisted_description(result) == "raw fallback description"
    assert {skill.name for skill, _, _ in _job_skills(result)} >= {"SQL", "Power BI"}


def test_persistable_job_blocks_only_hard_taxonomy_and_javascript_urls() -> None:
    blocked_taxonomy = _result(document_type="portal_taxonomy", source_url="https://jobs.example.com/2")
    blocked_js = _result(document_type="job_posting", source_url="javascript:;")

    assert _persistable_job(blocked_taxonomy) is False
    assert _persistable_job(blocked_js) is False
    assert _processing_stage(blocked_taxonomy.silver) == "candidate_job"
