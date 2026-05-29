from __future__ import annotations

import types
from pathlib import Path

from scrapers.pipelines import jobs_pipeline


def test_playwright_job_source_no_longer_depends_on_networkidle() -> None:
    source = Path("scrapers/sources/base.py").read_text(encoding="utf-8")
    assert 'wait_for_load_state("networkidle"' not in source
    assert "safe_wait_for_results" in source


def test_jobs_pipeline_marks_failed_source_as_degraded_and_continues(monkeypatch) -> None:
    jobs_pipeline.SOURCE_STATUS.clear()
    monkeypatch.setitem(jobs_pipeline.SOURCES, "broken", "tests.fake_broken_source")
    monkeypatch.setitem(jobs_pipeline.SOURCES, "healthy", "tests.fake_healthy_source")

    def fake_import_module(module_path: str):
        if module_path.endswith("fake_broken_source"):
            def scrape_jobs(**kwargs):
                raise TimeoutError("simulated selector timeout")

            return types.SimpleNamespace(scrape_jobs=scrape_jobs)

        def scrape_jobs(**kwargs):
            return [{"titulo": "Analista de datos", "descripcion": "SQL Power BI Python", "portal": "healthy"}]

        return types.SimpleNamespace(scrape_jobs=scrape_jobs)

    monkeypatch.setattr(jobs_pipeline.importlib, "import_module", fake_import_module)

    jobs = jobs_pipeline.scrape_sources(["broken", "healthy"], "python data analyst", "Colombia", 20, True)

    assert len(jobs) == 1
    assert jobs_pipeline.SOURCE_STATUS["broken"]["source_status"] == "degraded"
    assert jobs_pipeline.SOURCE_STATUS["healthy"]["source_status"] == "ok"


def test_jobs_pipeline_marks_empty_source_as_degraded(monkeypatch) -> None:
    jobs_pipeline.SOURCE_STATUS.clear()
    monkeypatch.setitem(jobs_pipeline.SOURCES, "empty", "tests.fake_empty_source")

    def fake_import_module(module_path: str):
        return types.SimpleNamespace(scrape_jobs=lambda **kwargs: [])

    monkeypatch.setattr(jobs_pipeline.importlib, "import_module", fake_import_module)

    jobs = jobs_pipeline.scrape_sources(["empty"], "python data analyst", "Colombia", 10, True)

    assert jobs == []
    assert jobs_pipeline.SOURCE_STATUS["empty"]["source_status"] == "degraded"
    assert jobs_pipeline.SOURCE_STATUS["empty"]["reason"] == "no_jobs_extracted"
