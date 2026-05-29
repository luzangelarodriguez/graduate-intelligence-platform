from __future__ import annotations

from scrapers.connectors.indeed_partner_connector import (
    IndeedPartnerConnector,
    indeed_job_to_agent_result,
    normalize_indeed_node,
    validate_indeed_job,
)
from scrapers.connectors.indeed_publisher_plugin_config import load_publisher_plugin_config, plugin_search_query, render_plugin_html


def _node(title: str = "Analista BI Power BI") -> dict:
    return {
        "id": "job-1",
        "jobData": {
            "title": title,
            "dateCreated": "2026-05-20T10:00:00Z",
            "description": (
                "Responsabilidades: construir dashboards ejecutivos, KPIs y reporting corporativo. "
                "Requisitos: Power BI, SQL, ETL, Python y analitica de datos para toma de decisiones."
            ),
            "company": "Data Company",
            "salary": {
                "period": "MONTH",
                "maximumMinor": 0,
                "minimumMinor": 0,
                "currency": "COP",
                "maximumMajor": 9000000,
                "minimumMajor": 6000000,
                "basePaySpecified": True,
            },
            "jobLocation": {
                "countryCode": "CO",
                "city": "Bogota",
                "postalCode": "110111",
                "fullAddress": "Bogota D.C., Colombia",
            },
            "externalJobPageUrl": "https://jobs.example.com/1",
            "externalPostingMetadata": {
                "jobPostingId": "external-1",
                "jobRequisitionId": "req-1",
                "campaignCategories": ["analytics"],
                "rawInputLocation": "Bogota",
                "isIntegratedJob": True,
            },
            "datePostedOnIndeed": "2026-05-21T10:00:00Z",
        },
        "managementUrls": {"viewJob": "https://employers.indeed.com/jobs/view/job-1"},
    }


def test_missing_credentials_returns_source_status(monkeypatch) -> None:
    monkeypatch.delenv("INDEED_API_URL", raising=False)
    monkeypatch.delenv("INDEED_ACCESS_TOKEN", raising=False)

    result = IndeedPartnerConnector(api_url="", access_token="").fetch_jobs(execute_network=True)

    assert result["source_status"] == "credentials_missing"
    assert result["jobs"] == []


def test_normalizes_indeed_payload_to_common_shape() -> None:
    job = normalize_indeed_node(_node())

    assert job.source_name == "indeed_partner"
    assert job.source_job_id == "job-1"
    assert job.title == "Analista BI Power BI"
    assert job.company == "Data Company"
    assert job.salary_currency == "COP"
    assert job.document_type == "job_posting"
    assert job.is_real_job_posting is True


def test_validates_real_job_posting_and_rejects_incomplete_payload() -> None:
    valid = validate_indeed_job(
        {
            "title": "BI Analyst",
            "company": "DataCo",
            "description": "Requisitos y responsabilidades con Power BI, SQL, dashboards, KPIs y reporting corporativo para analitica empresarial.",
            "external_url": "https://jobs.example.com/1",
            "indeed_view_url": "",
        }
    )
    invalid = validate_indeed_job({"title": "", "company": "", "description": "short", "external_url": "", "indeed_view_url": ""})

    assert valid == ("job_posting", True, "")
    assert invalid[0] == "unknown"
    assert invalid[1] is False
    assert "missing_title" in invalid[2]


def test_content_hash_is_stable() -> None:
    first = normalize_indeed_node(_node()).content_hash
    second = normalize_indeed_node(_node()).content_hash

    assert first == second
    assert len(first) == 64


def test_pagination_with_has_next_page(monkeypatch) -> None:
    pages = [
        {
            "data": {
                "findEmployerJobsPartner": {
                    "pageInfo": {"endCursor": "cursor-1", "hasNextPage": True},
                    "edges": [{"node": _node("Analista BI Power BI")}],
                }
            }
        },
        {
            "data": {
                "findEmployerJobsPartner": {
                    "pageInfo": {"endCursor": None, "hasNextPage": False},
                    "edges": [{"node": _node("Data Analyst SQL")}],
                }
            }
        },
    ]
    posts: list[dict] = []

    class Response:
        status_code = 200

        def __init__(self, payload: dict) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self.payload

    class Session:
        def post(self, url, headers, json, timeout):  # noqa: ANN001
            posts.append({"headers": headers, "json": json})
            return Response(pages.pop(0))

    connector = IndeedPartnerConnector(api_url="https://api.indeed.example/graphql", access_token="secret-token")
    connector.session = Session()

    result = connector.fetch_jobs(execute_network=True, max_jobs=5, page_size=1)

    assert len(result["jobs"]) == 2
    assert posts[1]["json"]["variables"]["input"]["after"] == "cursor-1"


def test_access_token_not_exposed_in_public_result_or_reports(tmp_path, monkeypatch) -> None:
    from scrapers.connectors import indeed_partner_connector as module

    monkeypatch.setattr(module, "REPORT_PATH", tmp_path / "indeed_partner_extraction_report.md")
    monkeypatch.setattr(module, "SKILL_REPORT_PATH", tmp_path / "indeed_partner_skill_report.md")
    secret = "super-secret-token"
    connector = IndeedPartnerConnector(api_url="https://api.indeed.example/graphql", access_token=secret)
    result = connector.fetch_jobs(execute_network=False)

    assert secret not in str(result)
    assert secret not in module.REPORT_PATH.read_text(encoding="utf-8")


def test_indeed_result_feeds_silver_not_gold_directly() -> None:
    result = indeed_job_to_agent_result(normalize_indeed_node(_node()))

    assert result.silver.document_type == "job_posting"
    assert result.silver.is_real_job_posting is True
    assert {"Power BI", "SQL"} & set(result.silver.job_evidence_skills or [])
    assert result.gold is None


def test_publisher_plugin_config_uses_official_attributes(monkeypatch) -> None:
    monkeypatch.setenv("INDEED_PUBLISHER_PARTNER_APP_ID", "partner-app")
    monkeypatch.setenv("INDEED_PUBLISHER_PLACEMENT_ID", "placement-1")
    monkeypatch.setenv("INDEED_PUBLISHER_SEARCH_LIMIT", "20")
    monkeypatch.setenv("INDEED_PUBLISHER_SEARCH_WHAT", "Power BI OR SQL")
    monkeypatch.setenv("INDEED_PUBLISHER_SEARCH_WHERE", "Colombia")

    config = load_publisher_plugin_config()
    html = render_plugin_html(config)

    assert config.is_ready
    assert plugin_search_query(config) == "Power BI OR SQL"
    assert 'data-indeed-plugin-type="job-search"' in html
    assert 'data-indeed-partner-app-id="partner-app"' in html
    assert 'data-indeed-placement-id="placement-1"' in html
    assert 'data-indeed-search-limit="20"' in html
    assert 'data-indeed-search-what="Power BI OR SQL"' in html
    assert 'data-indeed-search-where="Colombia"' in html
    assert "indeed-plugin-event" in html
