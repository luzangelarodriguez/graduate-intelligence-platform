from __future__ import annotations

from agents.visual_analytics_labor_agent import classify_document_type


def test_skills_page_is_portal_taxonomy() -> None:
    payload = {
        "title": "Skills",
        "company": "",
        "description": "Power BI SQL Python ETL Hadoop Spark BI Tableau machine learning filtros ubicaciones roles",
        "tags": [],
    }

    result = classify_document_type(payload, source_url="javascript:;")

    assert result["document_type"] == "portal_taxonomy"
    assert result["is_real_job_posting"] is False
    assert "invalid_catalog_title" in result["invalid_job_reason"]


def test_javascript_source_url_is_not_real_job() -> None:
    payload = {
        "title": "Analista BI",
        "company": "DataCo",
        "description": "Responsabilidades de reporting, requisitos de SQL y Power BI, experiencia y contrato.",
        "tags": [],
    }

    result = classify_document_type(payload, source_url="javascript:;")

    assert result["document_type"] == "portal_taxonomy"
    assert result["is_real_job_posting"] is False
    assert "javascript_source_url" in result["invalid_job_reason"]


def test_empty_company_with_labor_evidence_is_probabilistic_job() -> None:
    payload = {
        "title": "Analista BI",
        "company": "",
        "description": "Responsabilidades de dashboards, requisitos de SQL, experiencia, contrato y modalidad.",
        "tags": [],
    }

    result = classify_document_type(payload, source_url="https://example.com/job/1")

    assert result["document_type"] == "job_posting"
    assert result["job_probability_score"] >= 0.30
    assert result["curation_level"] in {"probable_job", "curated_job", "gold_job"}


def test_real_job_posting_is_detected() -> None:
    payload = {
        "title": "Analista BI Power BI",
        "company": "DataCo",
        "description": (
            "Empresa requiere analista BI. Responsabilidades: construir dashboards y KPIs. "
            "Requisitos: experiencia en SQL y Power BI. Modalidad hibrida, contrato indefinido."
        ),
        "tags": ["Power BI", "SQL"],
    }

    result = classify_document_type(payload, source_url="https://example.com/jobs/bi-1")

    assert result["document_type"] == "job_posting"
    assert result["is_real_job_posting"] is True
    assert result["invalid_job_reason"] == ""
