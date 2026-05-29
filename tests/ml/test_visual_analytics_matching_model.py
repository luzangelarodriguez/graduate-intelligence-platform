from __future__ import annotations

from ml.semantic_matching.visual_analytics_matcher import VisualAnalyticsMatcher
from ml.training.build_visual_analytics_match_dataset import build_dataset


def test_visual_analytics_matcher_scores_relevant_jobs_above_irrelevant_jobs() -> None:
    matcher = VisualAnalyticsMatcher()
    relevant = matcher.score_match(
        microcurriculum_text="Power BI SQL visual analytics data governance storytelling with data",
        job_title="BI Analyst Power BI",
        job_description="Rol de analitica para dashboards, SQL, Power BI, gobierno de datos y visualizacion ejecutiva.",
        job_skills=["Power BI", "SQL", "data governance", "dashboarding"],
    )
    irrelevant = matcher.score_match(
        microcurriculum_text="Power BI SQL visual analytics data governance storytelling with data",
        job_title="Auxiliar contable",
        job_description="Registro contable, conciliaciones bancarias y facturacion.",
        job_skills=["contabilidad", "facturacion"],
    )
    assert relevant.final_match_score > irrelevant.final_match_score
    assert relevant.final_match_score >= 0.65


def test_visual_analytics_matcher_uses_emerging_skill_weight() -> None:
    matcher = VisualAnalyticsMatcher()
    result = matcher.score_match(
        microcurriculum_text="lakehouse Databricks MLOps DataOps",
        job_title="Analytics Engineer",
        job_description="DataOps, MLOps, lakehouse, Databricks y cloud analytics.",
        job_skills=["lakehouse", "Databricks", "MLOps", "DataOps"],
    )
    assert result.emerging_skill_weight >= 0.66
    assert result.role_class in {"data_engineer", "ai_analytics", "analytics_related"}


def test_visual_analytics_training_dataset_builds_controlled_rows() -> None:
    rows = build_dataset()
    assert rows
    assert any(row.match_label == 1 for row in rows)
    assert any(row.job_skill == "Power BI" for row in rows)
    assert all(0 <= row.similarity_score <= 1 for row in rows)
