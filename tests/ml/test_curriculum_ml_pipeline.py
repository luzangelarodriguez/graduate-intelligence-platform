from __future__ import annotations

import csv
from pathlib import Path

from ml.labor.market_skill_intelligence_engine import MarketSkillIntelligenceMap, MarketSkillSignal
from ml.recommendations.curriculum_ml_recommendation_engine import generate_ml_curriculum_recommendations
from ml.training.build_curriculum_alignment_dataset import CurriculumAlignmentTrainingRow, build_dataset


def _signal(skill: str, coverage: str, confidence: str = "medium") -> MarketSkillSignal:
    return MarketSkillSignal(
        skill=skill,
        skill_type="tool",
        occupational_cluster="BI & Visualization",
        market_weight=1.4,
        evidence_count=2,
        evidence_sources={"silver_job_posting": 2},
        market_signal_confidence=confidence,
        coverage_status=coverage,
        affinity_score=0.42 if coverage == "partial" else 0.12,
        matched_curriculum_skill="dashboarding" if coverage == "partial" else None,
        roles=["BI Analyst"],
        companies=["DataCo"],
        source_urls=["https://jobs.example.com/bi"],
        recommendation="Fortalecer evidencia curricular.",
        reason="Detectado en requisitos laborales con evidencia de BI.",
    )


def _map() -> MarketSkillIntelligenceMap:
    signals = [
        _signal("Power BI", "covered", "high"),
        _signal("Microsoft Fabric", "emerging", "medium"),
        _signal("DataOps", "partial", "medium"),
    ]
    return MarketSkillIntelligenceMap(
        specialization_id="visual-analytics-big-data",
        specialization_name="Especializacion en Visual Analytics y Big Data",
        market_skills=signals,
        covered_skills=[signals[0]],
        partial_skills=[signals[2]],
        missing_skills=[],
        emerging_skills=[signals[1]],
        irrelevant_skills=[],
        occupational_clusters=[{"cluster_name": "BI & Visualization", "skills": ["Power BI"]}],
        curriculum_gaps=[signals[1], signals[2]],
        recommended_updates=[],
    )


def test_curriculum_alignment_dataset_contains_supervised_labels(monkeypatch) -> None:
    from ml.training import build_curriculum_alignment_dataset as builder

    monkeypatch.setattr(builder, "build_market_skill_intelligence_map", lambda include_database=True, write_output=True: _map())

    rows = build_dataset()

    assert {row.job_relevance_label for row in rows} >= {"highly_relevant", "relevant"}
    assert {row.skill_coverage_label for row in rows} >= {"covered", "partial", "emerging"}
    assert rows[0].source_confidence_score > 0


def test_training_pipeline_writes_supervised_model_metadata(tmp_path: Path, monkeypatch) -> None:
    from ml.training import train_curriculum_ml_models as trainer

    monkeypatch_target = getattr(trainer, "MODEL_DIR")
    dataset_path = tmp_path / "curriculum_alignment_dataset.csv"
    rows = [
        CurriculumAlignmentTrainingRow(
            specialization_id="1",
            specialization_name="Visual Analytics",
            text="Power BI SQL dashboards",
            skill="Power BI",
            occupational_cluster="BI",
            job_relevance_label="highly_relevant",
            skill_coverage_label="covered",
            occupational_affinity_label="BI",
            market_weight=1.0,
            evidence_count=2,
            affinity_score=0.9,
            gold_count=0,
            silver_count=2,
            bronze_count=0,
            taxonomy_count=0,
            source_confidence_score=0.8,
            curriculum_overlap_score=0.9,
            market_frequency_score=1.0,
            cluster_centrality_score=0.5,
            recommendation_candidate=0,
        ),
        CurriculumAlignmentTrainingRow(
            specialization_id="1",
            specialization_name="Visual Analytics",
            text="Helpdesk hardware printers",
            skill="printer support",
            occupational_cluster="irrelevant",
            job_relevance_label="irrelevant",
            skill_coverage_label="irrelevant",
            occupational_affinity_label="irrelevant",
            market_weight=0.1,
            evidence_count=1,
            affinity_score=0.0,
            gold_count=0,
            silver_count=0,
            bronze_count=1,
            taxonomy_count=0,
            source_confidence_score=0.1,
            curriculum_overlap_score=0.0,
            market_frequency_score=0.1,
            cluster_centrality_score=0.1,
            recommendation_candidate=0,
        ),
    ]
    with dataset_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].__dict__.keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)

    model_dir = tmp_path / "models"
    monkeypatch.setattr(trainer, "MODEL_DIR", model_dir)
    monkeypatch.setattr(trainer, "RELEVANCE_MODEL_PATH", model_dir / "curriculum_relevance_classifier.joblib")
    monkeypatch.setattr(trainer, "SKILL_IMPORTANCE_MODEL_PATH", model_dir / "skill_importance_ranker.joblib")
    monkeypatch.setattr(trainer, "METADATA_PATH", model_dir / "curriculum_ml_metadata.json")
    monkeypatch.setattr(trainer, "PERFORMANCE_REPORT", tmp_path / "ml_model_performance_report.md")
    monkeypatch.setattr(trainer, "SKILL_IMPORTANCE_REPORT", tmp_path / "ml_skill_importance_report.md")

    metadata = trainer.train_models(dataset_path)

    assert metadata["metrics"]["rows"] == 2
    assert "highly_relevant" in metadata["metrics"]["classes"]
    assert monkeypatch_target != trainer.MODEL_DIR


def test_ml_inference_generates_explainable_predictions(monkeypatch) -> None:
    from ml.inference import curriculum_market_inference_pipeline as inference

    monkeypatch.setattr(inference, "build_market_skill_intelligence_map", lambda include_database=True, write_output=True: _map())

    result = inference.run_program_market_inference(program_id=1, include_database=False, write_reports=False)

    assert result["skill_predictions"]
    assert result["gap_predictions"]
    assert "feature_importance" in result["skill_predictions"][0]
    assert "explanation" in result["skill_predictions"][0]


def test_ml_recommendation_engine_uses_gap_predictions() -> None:
    inference_result = {
        "program_id": 1,
        "specialization_name": "Especializacion en Visual Analytics y Big Data",
        "gap_predictions": [
            {
                "skill": "Microsoft Fabric",
                "coverage_status": "emerging",
                "occupational_affinity": "Cloud Analytics",
                "prediction_confidence": 0.82,
                "predicted_relevance": "relevant",
                "skill_importance_score": 0.77,
                "feature_importance": [{"feature": "market_weight", "value": 1.0}],
                "evidence_sources": {"silver_job_posting": 2},
                "explanation": "Brecha emergente con evidencia laboral.",
            }
        ],
        "skill_predictions": [],
    }

    payload = generate_ml_curriculum_recommendations(inference_result=inference_result, write_report=False)

    assert payload["recommendations"]
    assert payload["recommendations"][0]["skill"] == "Microsoft Fabric"
    assert payload["recommendations"][0]["curriculum_action"]
