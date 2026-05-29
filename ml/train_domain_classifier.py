from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import joblib
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.evaluation.evaluate import evaluate_predictions
from ml.registry import register_model
from ml.training.dataset_builder import build_initial_dataset, load_dataset


def train(*, dataset_path: Path, output_dir: Path) -> dict[str, Any]:
    rows = load_dataset(dataset_path)
    if not rows:
        rows = build_initial_dataset(dataset_path)
    texts = [row["text"] for row in rows]
    labels = [row["domain"] for row in rows]
    stratify = labels if min(labels.count(label) for label in set(labels)) >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=0.30,
        random_state=42,
        stratify=stratify,
    )
    models: dict[str, Pipeline] = {
        "logistic_regression": Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
                ("model", LogisticRegression(max_iter=1200, class_weight="balanced")),
            ]
        ),
        "lightgbm_baseline_fallback": Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=2500)),
                ("model", GradientBoostingClassifier(random_state=42)),
            ]
        ),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {"dataset_path": str(dataset_path), "rows": len(rows), "models": {}}
    best_name = ""
    best_f1 = -1.0
    for name, model in models.items():
        model.fit(x_train, y_train)
        predictions = list(model.predict(x_test))
        metrics = evaluate_predictions(name, y_test, predictions)
        artifact = output_dir / f"domain_classifier_{name}.joblib"
        joblib.dump(model, artifact)
        metrics["artifact_path"] = str(artifact)
        results["models"][name] = metrics
        register_model(
            model_name=f"domain_classifier_{name}",
            model_type=name,
            version="phase1",
            artifact_path=str(artifact),
            training_dataset_path=str(dataset_path),
            metrics=metrics,
            status="candidate",
        )
        if metrics["f1_macro"] > best_f1:
            best_name = name
            best_f1 = metrics["f1_macro"]
    best_artifact = output_dir / f"domain_classifier_{best_name}.joblib"
    canonical = output_dir / "domain_classifier_logreg.joblib"
    if best_artifact.exists():
        canonical.write_bytes(best_artifact.read_bytes())
    results["winner"] = best_name
    results["winner_f1_macro"] = best_f1
    (output_dir / "domain_classifier_training_report.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Train disciplinary domain classifiers.")
    parser.add_argument("--dataset-path", default="ml/datasets/domain_training_seed.csv")
    parser.add_argument("--output-dir", default="ml/models")
    args = parser.parse_args()
    dataset_path = ROOT_DIR / args.dataset_path if not Path(args.dataset_path).is_absolute() else Path(args.dataset_path)
    output_dir = ROOT_DIR / args.output_dir if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    build_initial_dataset(dataset_path)
    print(json.dumps(train(dataset_path=dataset_path, output_dir=output_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
