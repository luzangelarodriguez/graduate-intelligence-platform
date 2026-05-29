from __future__ import annotations

from intelligence.career_path_engine import build_career_paths
from intelligence.company_intelligence_engine import build_company_profiles
from intelligence.company_resolution_engine import resolve_company
from intelligence.market_forecasting_engine import forecast_skills
from intelligence.recommendation_intelligence_engine import build_recommendations
from intelligence.semantic_role_intelligence import build_role_intelligence, infer_role_family, role_similarity
from intelligence.semantic_search_engine import semantic_search


def test_company_resolution_maps_aliases_and_rejects_noise() -> None:
    resolved = resolve_company("International Business Machines Colombia SAS")
    noisy = resolve_company("Rol: Analista BI Requisitos: SQL Power BI responsabilidades dashboards")

    assert resolved.canonical_company_name == "IBM"
    assert resolved.company_resolution_confidence >= 0.9
    assert noisy.canonical_company_name == "No especificada"


def test_company_intelligence_scores_cloud_and_bi_maturity() -> None:
    profiles = build_company_profiles(
        [
            {"company": "Globant Colombia", "title": "Cloud Analytics Engineer", "skills": ["AWS", "Python", "Spark", "Power BI"]},
            {"company": "Globant", "title": "BI Analyst", "skills": ["Power BI", "SQL", "dashboarding", "KPIs"]},
        ]
    )

    assert profiles
    assert profiles[0].dominant_skills
    assert profiles[0].bi_maturity_score > 0


def test_semantic_role_intelligence_understands_hybrid_roles() -> None:
    family, score = infer_role_family("Analytics Engineer", ["SQL", "ETL", "Power BI"])
    similarity = role_similarity(
        {"title": "Analytics Engineer", "skills": ["SQL", "ETL", "BI"]},
        {"title": "Data Engineer BI", "skills": ["SQL", "pipelines", "Power BI"]},
    )

    assert family == "Analytics Engineering"
    assert score >= 0.8
    assert similarity > 0.2


def test_recommendations_career_forecast_and_search_are_generated() -> None:
    jobs = [
        {"id": 1, "company": "SETI", "title": "Analytics Engineer", "skills": ["SQL", "Power BI", "Azure", "Databricks"]},
        {"id": 2, "company": "SETI", "title": "BI Analyst", "skills": ["Power BI", "dashboarding", "KPIs"]},
    ]
    profiles = build_company_profiles(jobs)
    role_signals = build_role_intelligence(jobs)
    recommendations = build_recommendations(company_profiles=profiles, missing_skills=["Azure"], emerging_skills=["Databricks"])
    transitions = build_career_paths(role_signals, ["SQL", "Power BI", "Azure", "Databricks"])
    forecasts = forecast_skills(jobs)
    search = semantic_search("roles similares a Analytics Engineer", jobs)

    assert recommendations
    assert transitions
    assert forecasts[0].entity_name in {"Power BI", "Databricks", "Azure", "SQL", "dashboarding", "KPIs"}
    assert search
