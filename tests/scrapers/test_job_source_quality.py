from __future__ import annotations

from pipelines.run_visual_analytics_job_connectors import calculate_final_quality
from scrapers.connectors.base import build_job


def test_source_quality_blocks_empty_or_error_runs() -> None:
    quality = calculate_final_quality(
        [],
        [{"source": "Ticjob", "title": "", "reason": "missing_title", "score": "0.0"}],
        [{"source": "LinkedIn", "error_type": "restricted_manual", "error_message": "auth"}],
        6,
    )
    assert quality < 0.75


def test_source_quality_allows_dense_relevant_jobs() -> None:
    jobs = [
        build_job(
            source_name="Ticjob",
            base_url="https://ticjob.co",
            title="BI Analyst Power BI",
            company="DataCo",
            location="Bogota Colombia",
            description="Power BI SQL ETL dashboards data governance visualizacion analitica storytelling with data para toma de decisiones.",
            tags=["Power BI", "SQL", "ETL", "data governance"],
            source_url="https://ticjob.co/oferta/1",
        ),
        build_job(
            source_name="Elempleo",
            base_url="https://elempleo.com",
            title="Data Engineer Spark",
            company="CloudData",
            location="Colombia remoto",
            description="Data Engineer con Spark, lakehouse, data warehouse, Python, ETL y cloud analytics para plataformas de datos.",
            tags=["Spark", "Python", "lakehouse", "ETL"],
            source_url="https://elempleo.com/oferta/1",
        ),
    ]
    quality = calculate_final_quality(jobs, [], [], 2)
    assert quality >= 0.75
