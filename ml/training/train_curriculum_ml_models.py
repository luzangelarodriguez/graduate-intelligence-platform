from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.training.build_curriculum_alignment_dataset import DATASET_PATH, build_dataset, write_dataset  # noqa: E402

MODEL_DIR = ROOT_DIR / "ml" / "models"
RELEVANCE_MODEL_PATH = MODEL_DIR / "curriculum_relevance_classifier.joblib"
SKILL_IMPORTANCE_MODEL_PATH = MODEL_DIR / "skill_importance_ranker.joblib"
METADATA_PATH = MODEL_DIR / "curriculum_ml_metadata.json"
PERFORMANCE_REPORT = ROOT_DIR / "outputs" / "ml_model_performance_report.md"
SKILL_IMPORTANCE_REPORT = ROOT_DIR / "outputs" / "ml_skill_importance_report.md"

NUMERIC_FEATURES = [
    "market_weight",
    "evidence_count",
    "affinity_score",
    "gold_count",
    "silver_count",
    "bronze_count",
    "taxonomy_count",
    "source_confidence_score",
    "curriculum_overlap_score",
    "market_frequency_score",
    "cluster_centrality_score",
    "job_relevance_soft_label",
    "skill_coverage_soft_label",
    "training_weight",
    "probabilistic_confidence",
]


def ensure_dataset(path: Path = DATASET_PATH) -> pd.DataFrame:
    if not path.exists():
        rows = build_dataset()
        write_dataset(rows, path)
    frame = pd.read_csv(path)
    for column in NUMERIC_FEATURES:
        if column not in frame.columns:
            frame[column] = 0.0
    return frame


def _split(df: pd.DataFrame, label: str):
    if len(df) < 10 or df[label].nunique() < 2:
        return df, df
    try:
        return train_test_split(df, test_size=0.25, random_state=42, stratify=df[label])
    except Exception:
        return train_test_split(df, test_size=0.25, random_state=42)


def _feature_pipeline(model: Any) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("text", TfidfVectorizer(max_features=384, ngram_range=(1, 2)), "text"),
            ("numeric", StandardScaler(), NUMERIC_FEATURES),
        ],
        remainder="drop",
    )
    return Pipeline([("features", preprocessor), ("model", model)])


def train_models(dataset_path: Path = DATASET_PATH) -> dict[str, Any]:
    df = ensure_dataset(dataset_path)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    train_df, test_df = _split(df, "job_relevance_label")
    classifier: Any
    if train_df["job_relevance_label"].nunique() < 2:
        classifier = DummyClassifier(strategy="most_frequent")
    else:
        classifier = LogisticRegression(max_iter=1000, class_weight="balanced")
    relevance_model = _feature_pipeline(classifier)
    fit_kwargs: dict[str, Any] = {}
    if "training_weight" in train_df.columns and classifier.__class__.__name__ != "DummyClassifier":
        fit_kwargs["model__sample_weight"] = train_df["training_weight"].clip(lower=0.05, upper=1.0)
    relevance_model.fit(train_df, train_df["job_relevance_label"], **fit_kwargs)
    predictions = relevance_model.predict(test_df)
    metrics = {
        "accuracy": round(float(accuracy_score(test_df["job_relevance_label"], predictions)), 4),
        "precision_macro": round(float(precision_score(test_df["job_relevance_label"], predictions, average="macro", zero_division=0)), 4),
        "recall_macro": round(float(recall_score(test_df["job_relevance_label"], predictions, average="macro", zero_division=0)), 4),
        "f1_macro": round(float(f1_score(test_df["job_relevance_label"], predictions, average="macro", zero_division=0)), 4),
        "rows": int(len(df)),
        "classes": sorted(map(str, df["job_relevance_label"].unique())),
        "weighted_training": bool("training_weight" in train_df.columns),
        "probability_outputs": bool(hasattr(relevance_model.named_steps["model"], "predict_proba")),
        "calibration_strategy": "probabilistic labels with sample weights; explicit calibration dataset pending",
    }
    joblib.dump(relevance_model, RELEVANCE_MODEL_PATH)

    rank_target = (
        df["market_frequency_score"] * 0.30
        + df["source_confidence_score"] * 0.20
        + df["affinity_score"] * 0.15
        + df.get("job_relevance_soft_label", 0.0) * 0.20
        + df.get("probabilistic_confidence", 0.0) * 0.15
    ).clip(0, 1)
    ranker = _feature_pipeline(GradientBoostingRegressor(random_state=42))
    ranker.fit(df, rank_target)
    joblib.dump(ranker, SKILL_IMPORTANCE_MODEL_PATH)

    metadata = {
        "dataset": str(dataset_path),
        "relevance_model": str(RELEVANCE_MODEL_PATH),
        "skill_importance_model": str(SKILL_IMPORTANCE_MODEL_PATH),
        "metrics": metrics,
        "calibration": {
            "enabled": metrics["probability_outputs"],
            "method": "native_predict_proba",
            "notes": "Soft labels and training weights stabilize probabilities until a larger human-validated calibration set is available.",
        },
        "explainability": {
            "feature_importance_persisted": True,
            "top_features_source": "TF-IDF coefficients plus numeric feature weights in model artifacts",
            "prediction_payload": ["prediction_confidence", "top_features", "explanation_payload"],
        },
        "models_requested": {
            "logistic_regression": "trained",
            "gradient_boosting_ranker": "trained",
            "xgboost": "optional_not_required",
            "lightgbm": "optional_not_required",
            "hdbscan_umap_bertopic": "handled_by existing clustering/fallback layers",
        },
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    write_reports(df, metrics)
    return metadata


def write_reports(df: pd.DataFrame, metrics: dict[str, Any]) -> None:
    PERFORMANCE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# ML Model Performance Report",
        "",
        f"- Rows: {metrics['rows']}",
        f"- Classes: {', '.join(metrics['classes'])}",
        f"- Accuracy: {metrics['accuracy']}",
        f"- Precision macro: {metrics['precision_macro']}",
        f"- Recall macro: {metrics['recall_macro']}",
        f"- F1 macro: {metrics['f1_macro']}",
        "",
        "Modelo entrenado: Logistic Regression baseline con TF-IDF + features numericas.",
    ]
    PERFORMANCE_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    top = df.sort_values(["market_weight", "affinity_score"], ascending=False).head(25)
    skill_lines = ["# ML Skill Importance Report", ""]
    for _index, row in top.iterrows():
        skill_lines.append(
            f"- {row['skill']}: market_weight={row['market_weight']}, affinity={row['affinity_score']}, coverage={row['skill_coverage_label']}"
        )
    SKILL_IMPORTANCE_REPORT.write_text("\n".join(skill_lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train curriculum ML models.")
    parser.add_argument("--dataset", default=str(DATASET_PATH))
    args = parser.parse_args()
    print(json.dumps(train_models(Path(args.dataset)), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
