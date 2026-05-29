from __future__ import annotations

from scrapers.normalization.classify_domains import classify_program_domain
from scrapers.normalization.normalize_skills import extract_skills


def normalized_skill_names(text: str, domain: str) -> set[str]:
    return {skill.skill_normalized for skill in extract_skills(text, domain_hint=domain)}


def test_alta_gerencia_rejects_ti_and_cybersecurity_contamination() -> None:
    program = "Especializacion en Alta Gerencia"
    domain = classify_program_domain(program).primary_domain
    skills = normalized_skill_names(
        "liderazgo gestion de proyectos estrategia backend ciberseguridad sql visual analytics",
        domain,
    )
    assert domain == "management"
    assert "liderazgo" in skills
    assert "gestion de proyectos" in skills
    assert "backend" not in skills
    assert "iso 27001" not in skills
    assert "sql" not in skills
    assert "visual analytics" not in skills


def test_ambiental_rejects_software_devops_contamination() -> None:
    program = "Especializacion en Gestion Ambiental y Energetica"
    domain = classify_program_domain(program).primary_domain
    skills = normalized_skill_names(
        "sostenibilidad ESG ISO 14001 eficiencia energetica energias renovables backend fullstack devops",
        domain,
    )
    assert domain == "ambiental"
    assert {"sostenibilidad", "esg", "iso 14001"}.issubset(skills)
    assert "backend" not in skills
    assert "fullstack" not in skills
    assert "devops" not in skills


def test_visual_analytics_accepts_data_stack() -> None:
    program = "Especializacion en Visual Analytics y Big Data"
    domain = classify_program_domain(program).primary_domain
    skills = normalized_skill_names("SQL Power BI Python Big Data visual analytics business intelligence", domain)
    assert domain == "analitica"
    assert {"sql", "power bi", "python", "big data", "visual analytics"}.issubset(skills)


def test_derecho_digital_accepts_legal_tech_stack() -> None:
    program = "Especializacion en Derecho Digital"
    domain = classify_program_domain(program).primary_domain
    skills = normalized_skill_names(
        "proteccion de datos habeas data compliance legaltech contratos tecnologicos propiedad intelectual",
        domain,
    )
    assert domain == "legal-tech"
    assert "proteccion de datos" in skills
    assert "compliance" in skills
    assert "derecho digital" in skills
    assert "contratos tecnologicos" in skills
