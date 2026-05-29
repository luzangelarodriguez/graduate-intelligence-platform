from __future__ import annotations

from scrapers.lakehouse.relevance import calculate_relevance_scores
from scrapers.normalization.classify_domains import classify_program_domain, classify_text_domain, is_domain_compatible
from scrapers.normalization.deduplicate_jobs import deduplicate_jobs
from scrapers.normalization.normalize_skills import extract_skills_with_rejections, normalize_skill


def test_disciplinary_classification_examples_are_stable() -> None:
    cases = {
        "Especializacion en Gestion Ambiental y Energetica": "ambiental",
        "Especializacion en Derecho Digital": "legal-tech",
        "Especializacion en Seguridad Informatica": "cybersecurity",
        "Especializacion en Visual Analytics": "analitica",
        "Especializacion en Gerencia de Talento Humano": "gestion_humana",
    }
    for text, expected_domain in cases.items():
        assert classify_program_domain(text).primary_domain == expected_domain


def test_domain_filtering_rejects_incompatible_skills() -> None:
    accepted, rejected = extract_skills_with_rejections(
        "sostenibilidad ISO 14001 backend fullstack devops",
        domain_hint="ambiental",
    )
    accepted_names = {skill.skill_normalized for skill in accepted}
    rejected_names = {skill.skill_normalized for skill in rejected}
    assert {"sostenibilidad", "iso 14001"}.issubset(accepted_names)
    assert {"backend", "fullstack", "devops"}.issubset(rejected_names)
    assert not is_domain_compatible("ambiental", "ti")


def test_skill_alias_normalization() -> None:
    assert normalize_skill("PowerBI") == "power bi"
    assert normalize_skill("Microsoft Power BI") == "power bi"
    assert normalize_skill("habeas data") == "proteccion de datos"
    assert normalize_skill("legaltech") == "derecho digital"


def test_job_deduplication_suppresses_title_company_location_duplicates() -> None:
    jobs = [
        {
            "portal": "test",
            "titulo": "Analista de Datos",
            "empresa": "ACME",
            "ciudad": "Bogota",
            "descripcion": "SQL Power BI Python para analitica institucional",
            "skills": ["sql", "power bi"],
        },
        {
            "portal": "test",
            "titulo": "Analista de Datos",
            "empresa": "ACME",
            "ciudad": "Bogota",
            "descripcion": "SQL Power BI Python para analitica institucional",
            "skills": ["sql", "power bi"],
        },
    ]
    assert len(deduplicate_jobs(jobs)) == 1


def test_relevance_score_minimum_for_complete_domain_consistent_job() -> None:
    job = {
        "source": "elempleo",
        "titulo": "Especialista en sostenibilidad ESG",
        "empresa": "Empresa Energia",
        "ciudad": "Bogota",
        "modalidad": "Hibrido",
        "url": "https://example.test/jobs/1",
        "fecha_publicacion": "2026-05-20",
        "descripcion": (
            "Gestion ambiental corporativa con sostenibilidad, ESG, ISO 14001, huella de carbono, "
            "eficiencia energetica, transicion energetica y energias renovables para proyectos institucionales."
        ),
        "skills": ["sostenibilidad", "esg", "iso 14001", "huella de carbono", "eficiencia energetica"],
    }
    scores = calculate_relevance_scores(job)
    assert classify_text_domain(f"{job['titulo']} {job['descripcion']}").primary_domain in {"ambiental", "energia"}
    assert scores["overall_score"] >= 0.58
