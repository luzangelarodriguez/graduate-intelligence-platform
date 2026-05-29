from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
from sklearn.model_selection import train_test_split

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.embeddings.embedding_service import semantic_similarity_matrix, sentence_transformers_available
from ml.evaluation.evaluate import evaluate_predictions
from ml.registry import register_evaluation
from ml.training.dataset_builder import build_initial_dataset, load_dataset
from scrapers.taxonomy.domain_taxonomy import DOMAIN_DEFINITIONS


def evaluate(*, dataset_path: Path, models_dir: Path) -> dict:
    rows = load_dataset(dataset_path)
    texts = [row["text"] for row in rows]
    labels = [row["domain"] for row in rows]
    _, x_test, _, y_test = train_test_split(texts, labels, test_size=0.30, random_state=42, stratify=labels)
    reports: dict[str, dict] = {}
    for artifact in models_dir.glob("domain_classifier_*.joblib"):
        model = joblib.load(artifact)
        reports[artifact.stem] = evaluate_predictions(artifact.stem, y_test, list(model.predict(x_test)))

    domain_texts = [f"{domain.name} {domain.description} {' '.join(domain.terms)}" for domain in DOMAIN_DEFINITIONS]
    matrix = semantic_similarity_matrix(x_test, domain_texts)
    predicted = [DOMAIN_DEFINITIONS[int(row.argmax())].code for row in matrix]
    reports["sentence_transformer_similarity" if sentence_transformers_available() else "tfidf_semantic_similarity"] = (
        evaluate_predictions("semantic_similarity", y_test, predicted)
    )
    output = {
        "dataset_path": str(dataset_path),
        "sentence_transformers_available": sentence_transformers_available(),
        "reports": reports,
        "winner": max(reports.items(), key=lambda item: item[1]["f1_macro"])[0] if reports else None,
    }
    (models_dir / "domain_classifier_evaluation_report.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    for name, metrics in reports.items():
        register_evaluation(model_name=name, model_version="phase1", dataset_path=str(dataset_path), metrics=metrics)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate disciplinary domain classifiers.")
    parser.add_argument("--dataset-path", default="ml/datasets/domain_training_seed.csv")
    parser.add_argument("--models-dir", default="ml/models")
    args = parser.parse_args()
    dataset_path = ROOT_DIR / args.dataset_path if not Path(args.dataset_path).is_absolute() else Path(args.dataset_path)
    models_dir = ROOT_DIR / args.models_dir if not Path(args.models_dir).is_absolute() else Path(args.models_dir)
    if not dataset_path.exists():
        build_initial_dataset(dataset_path)
    print(json.dumps(evaluate(dataset_path=dataset_path, models_dir=models_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
