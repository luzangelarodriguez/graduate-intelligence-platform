from __future__ import annotations

from types import SimpleNamespace

from intelligence.career_path_engine import CareerTransition
from intelligence.company_observatory_engine import build_company_observatory
from intelligence.curriculum_gap_observatory import build_curriculum_gap_observatory
from intelligence.emerging_technology_engine import build_emerging_technology_observatory
from intelligence.observatory_metrics_engine import build_observatory_metrics
from intelligence.recommendation_api_engine import build_recommendation_api_payload
from intelligence.semantic_role_graph_engine import build_semantic_role_graph


def _gap_item(skill: str, cluster: str, status: str, evidence_weight: float, affinity_score: float, recommendation: str = "Reforzar") -> SimpleNamespace:
    return SimpleNamespace(
        skill=skill,
        cluster_name=cluster,
        coverage_status=status,
        evidence_weight=evidence_weight,
        evidence_sources={"silver_job_posting": 2},
        affinity_score=affinity_score,
        matched_curriculum_skill=None,
        roles=["Data Analyst", "Analytics Engineer"],
        recommendation=recommendation,
        reason="Evidencia semantica de mercado",
    )


def test_observatory_metrics_capture_core_kpis() -> None:
    market_intelligence = SimpleNamespace(
        emerging_skills=[_gap_item("Microsoft Fabric", "Cloud Analytics", "emerging", 1.3, 0.2)],
        occupational_clusters=[{"cluster_name": "Cloud Analytics", "total_weight": 4.2, "evidence_count": 8}],
    )
    company_profiles = [
        SimpleNamespace(
            company="Globant",
            hiring_velocity=0.72,
            cloud_maturity_score=0.81,
            bi_maturity_score=0.55,
            ai_adoption_score=0.63,
            dominant_skills=["AWS", "Spark", "Python"],
            dominant_clusters=["Cloud Analytics"],
            technology_maturity="advanced",
        )
    ]
    role_signals = [
        SimpleNamespace(role_title="Analytics Engineer", role_family="Analytics Engineering", semantic_role_cluster="Analytics Engineering", role_similarity_score=0.86, centrality_score=0.74, equivalent_roles=["Data Engineer"]),
    ]
    gap_map = SimpleNamespace(
        covered_skills=[_gap_item("SQL", "Reporting & KPI", "covered", 1.1, 0.92)],
        partial_skills=[_gap_item("dbt", "Data Engineering", "partial", 0.8, 0.55)],
        missing_skills=[_gap_item("Synapse", "Cloud Analytics", "missing", 1.4, 0.18)],
        emerging_skills=[_gap_item("Microsoft Fabric", "Cloud Analytics", "emerging", 1.3, 0.2)],
    )
    forecasts = [SimpleNamespace(growth_velocity=0.77)]

    metrics = build_observatory_metrics(
        market_intelligence=market_intelligence,
        company_profiles=company_profiles,
        role_signals=role_signals,
        gap_map=gap_map,
        forecasts=forecasts,
        metric_period="2026-05",
    )

    names = {metric.metric_name for metric in metrics}
    assert "curriculum_gap_severity" in names
    assert any(name.startswith("top_emerging_skill") for name in names)
    assert any(name.startswith("top_hiring_company") for name in names)


def test_curriculum_gap_observatory_prioritizes_emerging_skills() -> None:
    gap_map = SimpleNamespace(
        specialization_name="Especializacion en Visual Analytics y Big Data",
        specialization_id="visual-analytics-big-data",
        covered_skills=[_gap_item("SQL", "Reporting & KPI", "covered", 1.2, 0.93)],
        partial_skills=[_gap_item("dbt", "Data Engineering", "partial", 0.8, 0.52)],
        missing_skills=[_gap_item("Synapse", "Cloud Analytics", "missing", 1.5, 0.22)],
        emerging_skills=[_gap_item("Microsoft Fabric", "Cloud Analytics", "emerging", 1.7, 0.2)],
    )

    observations = build_curriculum_gap_observatory(gap_map=gap_map, metric_period="2026-05", write_output=False)

    assert observations
    assert observations[0].urgency_score >= observations[-1].urgency_score
    assert any(item.missing_skill == "Microsoft Fabric" for item in observations)


def test_recommendation_api_payload_has_four_types() -> None:
    company_profiles = [
        SimpleNamespace(
            company="Globant",
            hiring_velocity=0.82,
            cloud_maturity_score=0.81,
            bi_maturity_score=0.5,
            ai_adoption_score=0.66,
            dominant_skills=["AWS", "Spark", "Python"],
            dominant_clusters=["Cloud Analytics"],
            technology_maturity="advanced",
        )
    ]
    gap_map = SimpleNamespace(
        specialization_name="Especializacion en Visual Analytics y Big Data",
        specialization_id="visual-analytics-big-data",
        emerging_skills=[_gap_item("Microsoft Fabric", "Cloud Analytics", "emerging", 1.7, 0.2)],
        missing_skills=[_gap_item("Synapse", "Cloud Analytics", "missing", 1.5, 0.22)],
        partial_skills=[_gap_item("dbt", "Data Engineering", "partial", 0.8, 0.52)],
        recommended_curriculum_updates=[{"skill": "Microsoft Fabric", "cluster_name": "Cloud Analytics", "action": "Agregar modulo", "evidence_weight": 1.7}],
    )
    role_signals = [
        SimpleNamespace(role_title="Analytics Engineer", role_family="Analytics Engineering", semantic_role_cluster="Analytics Engineering", role_similarity_score=0.86, centrality_score=0.74, equivalent_roles=["Data Engineer"]),
    ]
    career_transitions = [CareerTransition("Data Analyst", "BI Analyst", 0.72, ["Power BI"], ["SQL", "Power BI"])]

    recommendations = build_recommendation_api_payload(
        market_intelligence=SimpleNamespace(),
        gap_map=gap_map,
        company_profiles=company_profiles,
        role_signals=role_signals,
        career_transitions=career_transitions,
        metric_period="2026-05",
        write_output=False,
    )

    assert {item.recommendation_type for item in recommendations} >= {"student", "curriculum", "career", "company_fit"}


def test_semantic_role_graph_joins_titles_by_shared_skills_and_transitions() -> None:
    jobs = [
        {"title": "Analytics Engineer", "skills": ["SQL", "dbt", "ETL", "Python"]},
        {"title": "Data Engineer", "skills": ["SQL", "ETL", "Spark", "Python"]},
    ]
    role_signals = [
        SimpleNamespace(role_title="Analytics Engineer", role_family="Analytics Engineering", semantic_role_cluster="Analytics Engineering", role_similarity_score=0.86, centrality_score=0.74, equivalent_roles=["Data Engineer"]),
        SimpleNamespace(role_title="Data Engineer", role_family="Analytics Engineering", semantic_role_cluster="Analytics Engineering", role_similarity_score=0.8, centrality_score=0.68, equivalent_roles=["Analytics Engineer"]),
    ]
    career_transitions = [CareerTransition("Data Analyst", "BI Analyst", 0.72, ["Power BI"], ["SQL", "Power BI"])]

    edges = build_semantic_role_graph(jobs=jobs, role_signals=role_signals, career_transitions=career_transitions, metric_period="2026-05", write_output=False)

    assert edges
    assert any(edge.shared_skills for edge in edges)
    assert any(edge.source_role == "Data Analyst" for edge in edges)


def test_company_observatory_formats_company_stack_and_maturity() -> None:
    company_profiles = [
        SimpleNamespace(
            company="Globant",
            hiring_velocity=0.82,
            cloud_maturity_score=0.81,
            bi_maturity_score=0.5,
            ai_adoption_score=0.66,
            dominant_skills=["AWS", "Spark", "Python", "SQL"],
            dominant_clusters=["Cloud Analytics", "AI Analytics"],
            technology_maturity="advanced",
        )
    ]
    items = build_company_observatory(company_profiles=company_profiles, metric_period="2026-05", write_output=False)

    assert items[0].company == "Globant"
    assert "AWS" in items[0].dominant_stack
    assert items[0].technology_maturity == "advanced"


def test_emerging_technology_observatory_detects_fabric_and_genai() -> None:
    forecasts = [
        SimpleNamespace(entity_name="Microsoft Fabric", growth_velocity=0.79, forecast_confidence=0.82),
        SimpleNamespace(entity_name="GenAI Analytics", growth_velocity=0.74, forecast_confidence=0.79),
    ]
    market_intelligence = SimpleNamespace(
        market_skills=[
            SimpleNamespace(skill="Microsoft Fabric", market_weight=1.2),
            SimpleNamespace(skill="GenAI Analytics", market_weight=1.1),
        ]
    )

    items = build_emerging_technology_observatory(
        forecasts=forecasts,
        market_intelligence=market_intelligence,
        metric_period="2026-05",
        write_output=False,
    )

    technologies = {item.technology for item in items}
    assert "Fabric" in technologies
    assert "GenAI" in technologies
