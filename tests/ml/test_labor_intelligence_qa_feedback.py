from __future__ import annotations

import json

from ml.feedback import ingest_human_feedback as qa


def test_qa_flags_detect_company_and_duplicate_risks() -> None:
    flags = qa._qa_flags(
        {
            "title": "Analytics Engineer",
            "company": "Rol: Analytics Engineer Requisitos: SQL Power BI dashboards responsabilidades principales",
            "job_probability_score": 0.72,
            "completeness_score": 0.82,
            "duplicate_group_id": "abc",
        }
    )

    assert "company_looks_like_description" in flags
    assert "duplicate_group_tracked" in flags


def test_write_ml_model_guardrail_report_warns_on_small_perfect_dataset(tmp_path, monkeypatch) -> None:
    metadata = {
        "metrics": {
            "rows": 67,
            "classes": ["highly_relevant", "weak_signal"],
            "accuracy": 1.0,
            "f1_macro": 1.0,
            "probability_outputs": True,
            "weighted_training": True,
        }
    }
    metadata_path = tmp_path / "metadata.json"
    report_path = tmp_path / "guardrail.md"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    monkeypatch.setattr(qa, "MODEL_METADATA_PATH", metadata_path)
    monkeypatch.setattr(qa, "GUARDRAIL_REPORT_MD", report_path)

    result = qa.write_ml_model_guardrail_report()

    assert result["status"] == "pass"
    assert "perfect_metrics_on_small_dataset_review_required" in result["warnings"]
    assert report_path.exists()
