from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support


@dataclass(frozen=True)
class EvaluationReport:
    model_name: str
    accuracy: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    labels: list[str]
    confusion_matrix: list[list[int]]


def evaluate_predictions(model_name: str, y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    labels = sorted(set(y_true) | set(y_pred))
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=labels,
        average="macro",
        zero_division=0,
    )
    report = EvaluationReport(
        model_name=model_name,
        accuracy=round(float(accuracy_score(y_true, y_pred)), 4),
        precision_macro=round(float(precision), 4),
        recall_macro=round(float(recall), 4),
        f1_macro=round(float(f1), 4),
        labels=labels,
        confusion_matrix=confusion_matrix(y_true, y_pred, labels=labels).tolist(),
    )
    return asdict(report)
