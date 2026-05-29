from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.embeddings.embedding_service import DEFAULT_EMBEDDING_MODEL, sentence_transformers_available  # noqa: E402
from ml.labor.market_skill_intelligence_engine import MarketSkillSignal, build_market_skill_intelligence_map  # noqa: E402
from ml.training.build_curriculum_alignment_dataset import (  # noqa: E402
    CurriculumAlignmentTrainingRow,
    job_relevance_label,
    soft_coverage_label,
    soft_relevance_label,
    source_confidence_score,
    training_weight,
)
from ml.training.train_curriculum_ml_models import (  # noqa: E402
    METADATA_PATH,
    NUMERIC_FEATURES,
    RELEVANCE_MODEL_PATH,
    SKILL_IMPORTANCE_MODEL_PATH,
    train_models,
)

GAP_PREDICTIONS_REPORT = ROOT_DIR / "outputs" / "ml_curriculum_gap_predictions.md"


def _ensure_models() -> dict[str, Any]:
    if not RELEVANCE_MODEL_PATH.exists() or not SKILL_IMPORTANCE_MODEL_PATH.exists() or not METADATA_PATH.exists():
        return train_models()
    try:
        return json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return train_models()


def _signal_to_feature_row(signal: MarketSkillSignal, specialization_id: str, specialization_name: str, max_weight: float) -> dict[str, Any]:
    sources = signal.evidence_sources
    text = " ".join(
        [
            signal.skill,
            signal.occupational_cluster,
            signal.market_signal_confidence,
            " ".join(signal.roles[:8]),
            signal.reason,
            signal.recommendation,
        ]
    )
    soft_relevance = soft_relevance_label(signal)
    soft_coverage = soft_coverage_label(signal)
    weight = training_weight(signal)
    row = CurriculumAlignmentTrainingRow(
        specialization_id=specialization_id,
        specialization_name=specialization_name,
        text=text,
        skill=signal.skill,
        occupational_cluster=signal.occupational_cluster,
        job_relevance_label=job_relevance_label(signal),
        skill_coverage_label=signal.coverage_status,
        occupational_affinity_label=signal.occupational_cluster,
        market_weight=signal.market_weight,
        evidence_count=signal.evidence_count,
        affinity_score=signal.affinity_score,
        gold_count=sources.get("gold_job_posting", 0),
        silver_count=sources.get("silver_job_posting", 0),
        bronze_count=sources.get("bronze_job_posting", 0),
        taxonomy_count=sources.get("portal_taxonomy", 0),
        source_confidence_score=source_confidence_score(signal),
        curriculum_overlap_score=signal.affinity_score,
        market_frequency_score=round(signal.market_weight / max(max_weight, 1.0), 4),
        cluster_centrality_score=round(min(signal.evidence_count / max(max_weight, 1.0), 1.0), 4),
        job_relevance_soft_label=soft_relevance,
        skill_coverage_soft_label=soft_coverage,
        training_weight=weight,
        probabilistic_confidence=round((soft_relevance + weight) / 2, 4),
        recommendation_candidate=1 if signal.coverage_status in {"missing", "emerging", "partial"} else 0,
    )
    return row.__dict__.copy()


def _prediction_confidence(model: Any, frame: pd.DataFrame, predicted_label: str) -> float:
    if not hasattr(model, "predict_proba"):
        return 0.65
    try:
        probabilities = model.predict_proba(frame)[0]
        classes = list(model.classes_) if hasattr(model, "classes_") else []
        if predicted_label in classes:
            return round(float(probabilities[classes.index(predicted_label)]), 4)
        return round(float(max(probabilities)), 4)
    except Exception:
        return 0.65


def _feature_importance(row: dict[str, Any]) -> list[dict[str, Any]]:
    numeric = [
        {"feature": name, "value": round(float(row.get(name, 0) or 0), 4)}
        for name in NUMERIC_FEATURES
    ]
    numeric.sort(key=lambda item: item["value"], reverse=True)
    return numeric[:5]


def _explain_prediction(signal: MarketSkillSignal, row: dict[str, Any], relevance_label: str, importance: float) -> str:
    if signal.coverage_status in {"missing", "emerging"}:
        action = "brecha curricular prioritaria"
    elif signal.coverage_status == "partial":
        action = "fortalecimiento curricular"
    elif signal.coverage_status == "covered":
        action = "capacidad cubierta"
    else:
        action = "senal laboral secundaria"
    return (
        f"{signal.skill} se clasifica como {action} porque combina cobertura {signal.coverage_status}, "
        f"cluster {signal.occupational_cluster}, peso de mercado {row['market_weight']} e importancia ML {round(importance, 4)}. "
        f"Prediccion de relevancia: {relevance_label}."
    )


def _has_real_market_evidence(item: dict[str, Any]) -> bool:
    sources = item.get("evidence_sources", {})
    return bool(
        sources.get("gold_job_posting", 0)
        or sources.get("silver_job_posting", 0)
        or sources.get("bronze_job_posting", 0)
        or sources.get("legacy_empleo_skill", 0)
    )


def run_program_market_inference(
    *,
    program_id: int | str = 0,
    include_database: bool = True,
    write_reports: bool = True,
) -> dict[str, Any]:
    metadata = _ensure_models()
    relevance_model = joblib.load(RELEVANCE_MODEL_PATH)
    ranker = joblib.load(SKILL_IMPORTANCE_MODEL_PATH)
    intelligence = build_market_skill_intelligence_map(include_database=include_database, write_output=True)
    max_weight = max((item.market_weight for item in intelligence.market_skills), default=1.0)

    skill_predictions: list[dict[str, Any]] = []
    for signal in intelligence.market_skills:
        row = _signal_to_feature_row(signal, intelligence.specialization_id, intelligence.specialization_name, max_weight)
        frame = pd.DataFrame([row])
        relevance_label = str(relevance_model.predict(frame)[0])
        importance = round(float(ranker.predict(frame)[0]), 4)
        confidence = _prediction_confidence(relevance_model, frame, relevance_label)
        skill_predictions.append(
            {
                "skill": signal.skill,
                "coverage_status": signal.coverage_status,
                "predicted_relevance": relevance_label,
                "prediction_confidence": confidence,
                "skill_importance_score": importance,
                "occupational_affinity": signal.occupational_cluster,
                "market_signal_confidence": signal.market_signal_confidence,
                "evidence_count": signal.evidence_count,
                "evidence_sources": signal.evidence_sources,
                "roles": signal.roles[:8],
                "feature_importance": _feature_importance(row),
                "explanation": _explain_prediction(signal, row, relevance_label, importance),
                "recommendation_candidate": signal.coverage_status in {"missing", "emerging", "partial"},
            }
        )

    gap_predictions = [
        item
        for item in skill_predictions
        if item["coverage_status"] in {"missing", "emerging", "partial"}
        and item["predicted_relevance"] != "irrelevant"
        and _has_real_market_evidence(item)
    ]
    gap_predictions.sort(key=lambda item: (item["coverage_status"] != "emerging", -item["skill_importance_score"]))
    skill_predictions.sort(key=lambda item: item["skill_importance_score"], reverse=True)
    result = {
        "program_id": program_id,
        "specialization_id": intelligence.specialization_id,
        "specialization_name": intelligence.specialization_name,
        "embedding_backend": "sentence-transformers" if sentence_transformers_available() else "tfidf_fallback",
        "embedding_model": DEFAULT_EMBEDDING_MODEL,
        "model_metadata": metadata,
        "skill_predictions": skill_predictions,
        "gap_predictions": gap_predictions,
        "occupational_clusters": intelligence.occupational_clusters,
        "recommended_updates": intelligence.recommended_updates,
    }
    if write_reports:
        write_gap_prediction_report(result)
    return result


def write_gap_prediction_report(result: dict[str, Any], path: Path = GAP_PREDICTIONS_REPORT) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# ML Curriculum Gap Predictions",
        "",
        f"- Programa: {result['specialization_name']}",
        f"- Backend semantico: {result['embedding_backend']} ({result['embedding_model']})",
        f"- Skills evaluadas: {len(result['skill_predictions'])}",
        f"- Gaps candidatos: {len(result['gap_predictions'])}",
        "",
        "## Predicciones Prioritarias",
    ]
    for item in result["gap_predictions"][:20]:
        lines.append(
            f"- {item['skill']} ({item['coverage_status']}): relevancia={item['predicted_relevance']}, "
            f"importancia={item['skill_importance_score']}, confianza={item['prediction_confidence']}. {item['explanation']}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ML curriculum-market inference.")
    parser.add_argument("--program-id", default="visual-analytics-big-data")
    parser.add_argument("--no-db", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run_program_market_inference(program_id=args.program_id, include_database=not args.no_db), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
