from __future__ import annotations

from ml.curriculum.curriculum_alignment_engine import (
    build_curriculum_skill_graph,
    compute_gold_score,
    curriculum_gold_tier,
    score_curriculum_alignment,
)
from ml.relevance.contextual_job_relevance_engine import score_contextual_relevance


def test_curriculum_skill_graph_uses_real_visual_analytics_documents() -> None:
    graph = build_curriculum_skill_graph()

    assert graph.documents_processed >= 1
    assert {node.skill for node in graph.skills} & {"SQL", "Power BI", "BI", "visualizacion analitica", "dashboarding"}


def test_partially_related_cloud_analytics_vacancy_is_curriculum_aligned() -> None:
    graph = build_curriculum_skill_graph()
    result = score_curriculum_alignment(
        title="Azure Data Engineer",
        description="Azure Synapse, pipelines, KPIs, reporting, SQL, dashboards y cloud analytics.",
        graph=graph,
    )

    assert result.curriculum_alignment_score >= 0.45
    assert {"SQL", "KPIs", "dashboarding"} & set(result.shared_skills)
    assert "Azure Synapse" in result.market_gap_signal


def test_hybrid_backend_analytics_role_is_gold_b_when_curriculum_matches() -> None:
    result = score_contextual_relevance(
        title="BI Backend Developer",
        description="APIs para dashboards Power BI, SQL, ETL, reporting, KPIs y data warehouse.",
    )

    assert result.accepted
    assert result.curriculum_alignment_score >= 0.50
    assert result.gold_score >= 0.65
    assert result.curriculum_gold_tier == "Gold B"
    assert "Power BI" in result.curriculum_shared_skills


def test_unrelated_support_role_is_rejected_by_curriculum_alignment() -> None:
    result = score_contextual_relevance(
        title="Tecnico helpdesk",
        description="Soporte a impresoras, hardware, cableado, mesa de ayuda y mantenimiento en sitio.",
    )

    assert not result.accepted
    assert result.curriculum_alignment_score < 0.20
    assert result.curriculum_gold_tier == "Rejected"


def test_emerging_market_skills_are_detected_as_gaps() -> None:
    alignment = score_curriculum_alignment(
        title="Analytics Engineer",
        description="SQL, dashboards, Microsoft Fabric, DataOps, Databricks, GenAI analytics y data governance.",
    )

    assert {"Microsoft Fabric", "DataOps", "Databricks", "GenAI analytics"} & set(alignment.market_gap_signal)
    assert alignment.curriculum_alignment_score >= 0.40


def test_gold_formula_requires_curriculum_alignment_for_gold() -> None:
    score = compute_gold_score(
        semantic_market_relevance=0.90,
        curriculum_alignment_score=0.30,
        contextual_evidence_score=0.90,
        quality_score=0.90,
    )

    assert score >= 0.50
    assert curriculum_gold_tier(score, 0.30) == "Silver"
