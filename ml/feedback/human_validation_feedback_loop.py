from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

FEEDBACK_PATH = ROOT_DIR / "ml" / "feedback" / "curriculum_human_feedback.jsonl"
FEEDBACK_REPORT = ROOT_DIR / "outputs" / "human_validation_feedback_report.md"


@dataclass(frozen=True)
class HumanValidationFeedback:
    item_id: str
    item_type: str
    original_label: str
    corrected_label: str
    reviewer: str
    notes: str
    created_at: str


def append_feedback(
    *,
    item_id: str,
    item_type: str,
    original_label: str,
    corrected_label: str,
    reviewer: str = "human_validator",
    notes: str = "",
    path: Path = FEEDBACK_PATH,
) -> HumanValidationFeedback:
    path.parent.mkdir(parents=True, exist_ok=True)
    feedback = HumanValidationFeedback(
        item_id=item_id,
        item_type=item_type,
        original_label=original_label,
        corrected_label=corrected_label,
        reviewer=reviewer,
        notes=notes,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(feedback), ensure_ascii=False) + "\n")
    return feedback


def load_feedback(path: Path = FEEDBACK_PATH) -> list[HumanValidationFeedback]:
    if not path.exists():
        return []
    rows: list[HumanValidationFeedback] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        rows.append(HumanValidationFeedback(**data))
    return rows


def summarize_feedback(rows: list[HumanValidationFeedback] | None = None) -> dict[str, Any]:
    rows = load_feedback() if rows is None else rows
    by_type: dict[str, int] = {}
    corrections: dict[str, int] = {}
    for row in rows:
        by_type[row.item_type] = by_type.get(row.item_type, 0) + 1
        key = f"{row.original_label}->{row.corrected_label}"
        corrections[key] = corrections.get(key, 0) + 1
    return {"total": len(rows), "by_type": by_type, "corrections": corrections}


def write_feedback_report(path: Path = FEEDBACK_REPORT) -> dict[str, Any]:
    summary = summarize_feedback()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Human Validation Feedback Loop",
        "",
        f"- Validaciones acumuladas: {summary['total']}",
        f"- Por tipo: {json.dumps(summary['by_type'], ensure_ascii=False)}",
        f"- Correcciones: {json.dumps(summary['corrections'], ensure_ascii=False)}",
        "",
        "Este archivo alimenta active learning sin modificar las reglas productivas ni los datos originales.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Register human validation feedback for curriculum ML.")
    parser.add_argument("--item-id")
    parser.add_argument("--item-type")
    parser.add_argument("--original-label")
    parser.add_argument("--corrected-label")
    parser.add_argument("--reviewer", default="human_validator")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()
    if args.item_id and args.item_type and args.original_label and args.corrected_label:
        append_feedback(
            item_id=args.item_id,
            item_type=args.item_type,
            original_label=args.original_label,
            corrected_label=args.corrected_label,
            reviewer=args.reviewer,
            notes=args.notes,
        )
    print(json.dumps(write_feedback_report(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
