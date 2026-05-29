from agents.agentic_job_extractor import (
    AgenticNavigationPolicy,
    EnterpriseAgenticJobExtractor,
    deduplicate_results,
    is_real_job_posting,
    job_content_hash,
    run_enterprise_extraction,
)


def test_navigation_policy_is_humanized_and_conservative() -> None:
    policy = AgenticNavigationPolicy()

    assert policy.min_delay_ms >= 800
    assert policy.max_delay_ms > policy.min_delay_ms
    assert policy.max_retries >= 1
    assert policy.max_jobs <= 30


def test_real_job_validator_requires_company_and_detail_signals() -> None:
    assert is_real_job_posting(
        {
            "title": "Analista BI",
            "company": "DataCo",
            "description": "Responsabilidades: construir dashboards. Requisitos: SQL y Power BI. Contrato indefinido.",
        },
        "https://example.com/jobs/1",
    )
    assert not is_real_job_posting(
        {
            "title": "Skills",
            "company": "",
            "description": "Power BI SQL Tableau filtros categorias ubicaciones",
        },
        "javascript:;",
    )


def test_enterprise_agent_extracts_only_job_evidence_from_detail() -> None:
    html = """
    <html><body><main>
      <h1>Analytics Engineer Power BI</h1>
      <span class="company">DataCo</span>
      <section class="description">
        Empresa requiere Analytics Engineer. Responsabilidades: construir pipelines,
        dashboards ejecutivos, reporting y KPIs. Requisitos: SQL, Power BI, Python,
        ETL y data warehouse. Modalidad remota, contrato indefinido.
      </section>
    </main></body></html>
    """

    result = EnterpriseAgenticJobExtractor().inspect_detail_html(
        html=html,
        source_name="Elempleo",
        source_url="https://example.com/jobs/analytics-engineer",
        fallback_title="Analytics Engineer Power BI",
    )

    assert result.silver.document_type == "job_posting"
    assert result.silver.job_evidence_skills
    assert result.silver.portal_taxonomy_skills == []
    assert result.silver.contextual["skill_confidence_score"] > 0.5


def test_taxonomy_detail_never_reaches_gold_in_enterprise_agent() -> None:
    html = """
    <html><body><main>
      <h1>Skills</h1>
      <nav>Power BI SQL Tableau Python BI KPIs dashboarding filtros categorias ubicaciones</nav>
    </main></body></html>
    """

    result = EnterpriseAgenticJobExtractor().inspect_detail_html(
        html=html,
        source_name="Ticjob",
        source_url="javascript:;",
        fallback_title="Skills",
    )

    assert result.silver.document_type == "portal_taxonomy"
    assert result.silver.job_evidence_skills == []
    assert result.gold is None


def test_deduplicate_results_uses_content_hash() -> None:
    html = """
    <html><body><main>
      <h1>Analista BI</h1><span class="company">DataCo</span>
      <section>Responsabilidades: dashboards. Requisitos: SQL Power BI. Contrato.</section>
    </main></body></html>
    """
    extractor = EnterpriseAgenticJobExtractor()
    result = extractor.inspect_detail_html(html=html, source_name="Elempleo", source_url="https://example.com/jobs/1", fallback_title="Analista BI")

    assert len(deduplicate_results([result, result])) == 1
    assert job_content_hash(title="A", company="B", normalized_description="C") == job_content_hash(title="A", company="B", normalized_description="C")


def test_enterprise_extraction_dry_run_is_safe() -> None:
    result = run_enterprise_extraction(sources=["ticjob"], execute_network=False)

    assert result["dry_run"] is True
    assert result["gold"] == 0
