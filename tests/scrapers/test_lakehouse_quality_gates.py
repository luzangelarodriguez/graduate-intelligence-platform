from __future__ import annotations

import json

from scrapers.lakehouse.magneto_api_extractor import is_real_job_evidence
from scrapers.lakehouse.release_gates import ReleaseGateResult
from scrapers.pipelines.elempleo_gold_pipeline import gold_publishable_jobs, has_real_evidence, write_layer_file


def test_bronze_layer_captures_raw_payload(tmp_path, monkeypatch) -> None:
    import scrapers.pipelines.elempleo_gold_pipeline as pipeline

    def fake_dated_layer_path(layer: str, source: str, run_id: str):
        path = tmp_path / layer / source / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    monkeypatch.setattr(pipeline, "dated_layer_path", fake_dated_layer_path)
    payload = {"endpoint": "https://www.elempleo.com/co/api/joboffers/findbyfilter", "items": [{"title": "Analista"}]}
    target = write_layer_file("bronze", "run-test", "payload.json", payload)
    assert target.exists()
    assert json.loads(target.read_text(encoding="utf-8")) == payload


def test_silver_rejects_seo_category_pages_as_jobs() -> None:
    seo_job = {
        "titulo": "Trabajos en Bogota",
        "empresa": "",
        "descripcion": "Listado SEO de categorias laborales",
        "url": "https://www.magneto365.com/co/trabajos/trabajos-bogota",
        "skills": [],
    }
    assert is_real_job_evidence(seo_job) is False


def test_silver_accepts_real_job_evidence() -> None:
    job = {
        "titulo": "Analista de datos",
        "empresa": "ACME",
        "descripcion": " ".join(["SQL Power BI Python analitica de datos"] * 8),
        "salario": "5000000",
        "url": "https://www.magneto365.com/co/trabajos/analista-datos-123",
        "skills": ["sql", "power bi", "python"],
    }
    assert is_real_job_evidence(job) is True
    assert has_real_evidence(job) is True


def test_gold_publication_requires_minimum_confidence() -> None:
    jobs = [
        {"id": "low", "relevance_scores": {"overall_score": 0.40}},
        {"id": "high", "relevance_scores": {"overall_score": 0.76}},
    ]
    publishable = gold_publishable_jobs(jobs, min_relevance=0.64)
    assert [job["id"] for job in publishable] == ["high"]


def test_release_gate_result_blocks_contaminated_or_unvalidated_data() -> None:
    result = ReleaseGateResult(
        allowed=False,
        precision_rate=0.30,
        confidence_avg=0.42,
        gold_validation=2,
        threshold_precision=0.70,
        threshold_confidence=0.68,
        threshold_gold=30,
        reason="blocked_until_precision_confidence_and_gold_thresholds_pass",
    )
    assert result.allowed is False
    assert result.precision_rate < result.threshold_precision
    assert result.confidence_avg < result.threshold_confidence
    assert result.gold_validation < result.threshold_gold
