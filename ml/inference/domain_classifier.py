from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = ROOT_DIR / "ml" / "models" / "domain_classifier_logreg.joblib"
MIN_PUBLISH_CONFIDENCE = 0.65

from ml.embeddings.embedding_service import semantic_similarity_matrix
from ml.training.dataset_builder import build_initial_dataset
from scrapers.normalization.classify_domains import classify_text_domain
from scrapers.taxonomy.domain_taxonomy import DOMAIN_DEFINITIONS


@dataclass(frozen=True)
class DomainPrediction:
    domain: str
    confidence: float
    confidence_level: str
    blocked: bool
    model_name: str
    scores: dict[str, float]


def confidence_level(confidence: float) -> str:
    if confidence >= 0.80:
        return "high"
    if confidence >= MIN_PUBLISH_CONFIDENCE:
        return "medium"
    return "low"


def compose_input(title: str = "", description: str = "", skills: list[str] | str | None = None) -> str:
    if isinstance(skills, str):
        skills_text = skills
    else:
        skills_text = " ".join(skills or [])
    return " ".join(part for part in (title, description, skills_text) if part).strip()


def input_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_model(path: Path = DEFAULT_MODEL_PATH) -> Any | None:
    if not path.exists():
        return None
    return joblib.load(path)


def taxonomy_similarity_predict(text: str) -> DomainPrediction:
    domain_texts = [
        f"{domain.name} {domain.description} {' '.join(domain.terms)}"
        for domain in DOMAIN_DEFINITIONS
    ]
    matrix = semantic_similarity_matrix([text], domain_texts)
    values = matrix[0]
    best_index = int(np.argmax(values))
    raw_scores = {DOMAIN_DEFINITIONS[index].code: float(values[index]) for index in range(len(DOMAIN_DEFINITIONS))}
    sorted_scores = sorted(raw_scores.items(), key=lambda item: item[1], reverse=True)
    top = sorted_scores[0][1]
    second = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0
    confidence = round(min(0.95, max(0.20, top + max(0.0, top - second))), 4)
    domain = DOMAIN_DEFINITIONS[best_index].code
    return DomainPrediction(
        domain=domain,
        confidence=confidence,
        confidence_level=confidence_level(confidence),
        blocked=confidence < MIN_PUBLISH_CONFIDENCE,
        model_name="sentence_similarity_tfidf_fallback",
        scores={key: round(value, 4) for key, value in raw_scores.items()},
    )


def rule_adjusted_prediction(text: str, prediction: DomainPrediction) -> DomainPrediction:
    rule = classify_text_domain(text)
    if rule.confidence >= 0.65 and rule.primary_domain == prediction.domain:
        confidence = round(max(prediction.confidence, min(0.92, rule.confidence)), 4)
        scores = dict(prediction.scores)
        scores[rule.primary_domain] = max(scores.get(rule.primary_domain, 0), confidence)
        return DomainPrediction(
            domain=prediction.domain,
            confidence=confidence,
            confidence_level=confidence_level(confidence),
            blocked=confidence < MIN_PUBLISH_CONFIDENCE,
            model_name=f"hybrid_rules_{prediction.model_name}",
            scores=scores,
        )
    if rule.confidence >= 0.65 and rule.primary_domain != prediction.domain:
        confidence = round(max(prediction.confidence, min(0.92, rule.confidence)), 4)
        scores = dict(prediction.scores)
        scores[rule.primary_domain] = max(scores.get(rule.primary_domain, 0), confidence)
        return DomainPrediction(
            domain=rule.primary_domain,
            confidence=confidence,
            confidence_level=confidence_level(confidence),
            blocked=confidence < MIN_PUBLISH_CONFIDENCE,
            model_name=f"hybrid_rules_{prediction.model_name}",
            scores=scores,
        )
    return prediction


def predict_domain(
    *,
    title: str = "",
    description: str = "",
    skills: list[str] | str | None = None,
    model_path: Path = DEFAULT_MODEL_PATH,
) -> DomainPrediction:
    text = compose_input(title, description, skills)
    model = _load_model(model_path)
    if model is None:
        return rule_adjusted_prediction(text, taxonomy_similarity_predict(text))
    probabilities = model.predict_proba([text])[0]
    classes = list(model.classes_)
    best_index = int(np.argmax(probabilities))
    scores = {str(label): round(float(probabilities[index]), 4) for index, label in enumerate(classes)}
    confidence = round(float(probabilities[best_index]), 4)
    prediction = DomainPrediction(
        domain=str(classes[best_index]),
        confidence=confidence,
        confidence_level=confidence_level(confidence),
        blocked=confidence < MIN_PUBLISH_CONFIDENCE,
        model_name="logistic_regression_domain_classifier",
        scores=scores,
    )
    return rule_adjusted_prediction(text, prediction)


def prediction_to_dict(prediction: DomainPrediction) -> dict[str, Any]:
    return asdict(prediction)


def ensure_baseline_model() -> None:
    if DEFAULT_MODEL_PATH.exists():
        return
    from ml.train_domain_classifier import train

    dataset_path = ROOT_DIR / "ml" / "datasets" / "domain_training_seed.csv"
    build_initial_dataset(dataset_path)
    train(dataset_path=dataset_path, output_dir=ROOT_DIR / "ml" / "models")
