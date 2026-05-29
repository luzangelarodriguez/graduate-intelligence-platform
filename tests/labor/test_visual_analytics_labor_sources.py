from __future__ import annotations

from pathlib import Path

import yaml

from scrapers.normalization.visual_analytics_skill_taxonomy import (
    classify_visual_analytics_skill,
    extract_visual_analytics_skills,
    normalize_visual_analytics_skill,
)


ROOT = Path(__file__).resolve().parents[2]


def test_controlled_labor_sources_are_configured() -> None:
    data = yaml.safe_load((ROOT / "config" / "labor_sources_visual_analytics.yaml").read_text(encoding="utf-8"))
    sources = data["sources"]
    names = {source["name"] for source in sources}
    assert {
        "LinkedIn",
        "Computrabajo",
        "Elempleo",
        "Ticjob",
        "Hireline",
        "Servicio Publico de Empleo",
        "Agencia Publica de Empleo SENA",
        "Mi Futuro Empleo",
        "FindJobIT",
    }.issubset(names)
    for source in sources:
        assert source["enabled"] is True
        assert source["rate_limit_seconds"] >= 8
        assert source["max_pages"] >= 2
        assert source["max_jobs"] >= 50
        assert source["allowed_paths"]


def test_visual_analytics_queries_load_roles_and_skills() -> None:
    data = yaml.safe_load((ROOT / "config" / "visual_analytics_job_queries.yaml").read_text(encoding="utf-8"))
    roles = data["roles"]["primary"]
    skills = data["skills"]["technologies"]
    assert "Analista BI" in roles
    assert "Data Engineer" in roles
    assert "Power BI" in skills
    assert "Data Governance" in skills
    assert "Google Cloud Analytics" in skills


def test_professional_competencies_have_required_mapping_fields() -> None:
    data = yaml.safe_load((ROOT / "config" / "visual_analytics_professional_competencies.yaml").read_text(encoding="utf-8"))
    competencies = data["competencies"]
    dimensions = {item["dimension"] for item in competencies}
    assert "Bases de datos" in dimensions
    assert "Inteligencia artificial y aprendizaje automatico" in dimensions
    for item in competencies:
        assert item["competency_text"]
        assert item["extracted_skills"]
        assert item["normalized_skills"]
        assert 0 <= float(item["market_alignment_weight"]) <= 1


def test_visual_analytics_skill_taxonomy_normalizes_aliases() -> None:
    assert normalize_visual_analytics_skill("business intelligence") == "BI"
    assert normalize_visual_analytics_skill("gobierno de datos") == "data governance"
    assert normalize_visual_analytics_skill("arquitectura lakehouse") == "lakehouse"
    assert normalize_visual_analytics_skill("aprendizaje automático") == "machine learning"
    assert classify_visual_analytics_skill("Azure Data") == "cloud"
    extracted = extract_visual_analytics_skills("Power BI, SQL, gobierno de datos y storytelling with data")
    assert {skill.normalized for skill in extracted} >= {"Power BI", "SQL", "data governance", "storytelling with data"}
