from __future__ import annotations

from pipelines.extract_visual_analytics_jobs import (
    LaborSource,
    calculate_job_relevance_score,
    normalize_job,
    should_discard_job,
)


SOURCE = LaborSource(
    name="Elempleo",
    url="https://www.elempleo.com/co/ofertas-empleo/sistemas-tecnologia",
    country="Colombia",
    priority="alta",
    source_type="portal_colombiano_tecnologia_informatica",
    access_mode="api_first_or_scraping_controlado",
    enabled=True,
    rate_limit_seconds=8,
    max_pages=2,
    max_jobs=50,
    allowed_paths=["/co/ofertas-empleo/sistemas-tecnologia"],
)


def test_irrelevant_or_seo_jobs_are_discarded() -> None:
    job = {
        "titulo": "Trabajos en Bogota",
        "descripcion": "Listado SEO de categorias laborales sin cargo real ni descripcion laboral suficiente " * 3,
        "ciudad": "Bogota",
        "url": "https://example.com/trabajos-en-bogota",
    }
    discard, reason = should_discard_job(job)
    assert discard is True
    assert reason in {"seo_course_or_advertising", "outside_visual_analytics_scope"}


def test_visual_analytics_jobs_are_kept_and_scored() -> None:
    job = {
        "titulo": "Analista BI Power BI",
        "empresa": "Empresa Data",
        "ciudad": "Bogota Colombia",
        "descripcion": (
            "Buscamos analista BI con experiencia en Power BI, SQL, ETL, dashboards, "
            "data governance, visualizacion de datos y storytelling with data para equipos de analitica."
        ),
        "url": "https://example.com/jobs/analista-bi",
    }
    discard, reason = should_discard_job(job)
    assert discard is False, reason
    score = calculate_job_relevance_score(job, SOURCE)
    assert score >= 0.65
    normalized = normalize_job(job, SOURCE)
    assert normalized.role_class in {"bi_analyst", "bi_developer", "analytics_related"}
    assert {"Power BI", "SQL", "ETL"}.issubset(set(normalized.skills))


def test_jobs_outside_colombia_are_discarded_unless_remote_latam() -> None:
    job = {
        "titulo": "Data Analyst SQL Python",
        "ciudad": "Madrid España",
        "descripcion": "Data Analyst con SQL Python Power BI y dashboards para analitica empresarial." * 3,
        "url": "https://example.com/jobs/data-analyst",
    }
    discard, reason = should_discard_job(job)
    assert discard is True
    assert reason == "outside_colombia_or_remote_latam"
