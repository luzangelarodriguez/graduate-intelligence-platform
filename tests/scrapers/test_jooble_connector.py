from __future__ import annotations

from scrapers.connectors.jooble_connector import JoobleConnector, jooble_job_to_agent_result, normalize_jooble_job, validate_jooble_job


def _job(title: str = "Analista BI Power BI") -> dict:
    return {
        "title": title,
        "location": "Bogota",
        "snippet": (
            "Empresa requiere analista de datos para construir dashboards, KPIs, reporting corporativo, "
            "Power BI, SQL, Python y procesos ETL para inteligencia de negocios."
        ),
        "salary": "6000000 - 9000000 COP",
        "source": "jooble",
        "type": "Full-time",
        "link": "https://co.jooble.org/jdp/12345",
        "company": "Data Company",
        "updated": "2026-05-22T10:00:00",
        "id": 12345,
    }


def test_missing_credentials_returns_source_status(monkeypatch) -> None:
    monkeypatch.delenv("JOOBLE_API_KEY", raising=False)

    result = JoobleConnector(api_key="").fetch_jobs(execute_network=True)

    assert result["source_status"] == "credentials_missing"
    assert result["jobs"] == []


def test_normalizes_jooble_payload_to_common_shape() -> None:
    job = normalize_jooble_job(_job())

    assert job.source_name == "jooble"
    assert job.source_job_id == "12345"
    assert job.title == "Analista BI Power BI"
    assert job.company == "Data Company"
    assert job.document_type == "job_posting"
    assert job.is_real_job_posting is True


def test_validates_real_job_and_rejects_incomplete_payload() -> None:
    valid = validate_jooble_job(
        {
            "title": "Data Analyst",
            "company": "DataCo",
            "description": "Requisitos con SQL, Power BI, dashboards, KPIs y reporting corporativo para analitica empresarial.",
            "external_url": "https://co.jooble.org/jdp/1",
        }
    )
    invalid = validate_jooble_job({"title": "", "company": "", "description": "short", "external_url": ""})

    assert valid == ("job_posting", True, "")
    assert invalid[0] == "unknown"
    assert "missing_title" in invalid[2]


def test_content_hash_is_stable() -> None:
    first = normalize_jooble_job(_job()).content_hash
    second = normalize_jooble_job(_job()).content_hash

    assert first == second
    assert len(first) == 64


def test_pagination_and_token_not_exposed(monkeypatch, tmp_path) -> None:
    from scrapers.connectors import jooble_connector as module

    monkeypatch.setattr(module, "REPORT_PATH", tmp_path / "jooble_extraction_report.md")
    monkeypatch.setattr(module, "SKILL_REPORT_PATH", tmp_path / "jooble_skill_report.md")
    pages = [
        {"totalCount": 2, "jobs": [_job("Analista BI Power BI")]},
        {"totalCount": 2, "jobs": [_job("Data Analyst SQL")]},
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
        def post(self, url, json, timeout):  # noqa: ANN001
            posts.append({"url": url, "json": json})
            return Response(pages.pop(0))

    secret = "secret-key"
    connector = JoobleConnector(api_url="https://jooble.org/api", api_key=secret)
    connector.session = Session()

    result = connector.fetch_jobs(execute_network=True, max_jobs=2, result_on_page=1)

    assert len(result["jobs"]) == 2
    assert posts[0]["json"]["page"] == "1"
    assert posts[1]["json"]["page"] == "2"
    assert secret not in str(result)
    assert secret not in module.REPORT_PATH.read_text(encoding="utf-8")


def test_jooble_result_feeds_silver_not_gold_directly() -> None:
    result = jooble_job_to_agent_result(normalize_jooble_job(_job()))

    assert result.silver.document_type == "job_posting"
    assert result.silver.is_real_job_posting is True
    assert {"Power BI", "SQL"} & set(result.silver.job_evidence_skills or [])
    assert result.gold is None
