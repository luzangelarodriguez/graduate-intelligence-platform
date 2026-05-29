from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path


TRACEABILITY_COLUMNS = (
    "document_name",
    "section",
    "original_text",
    "action",
    "rewritten_text",
    "reason",
    "market_signal",
    "confidence",
)


@dataclass(frozen=True)
class CurriculumChange:
    document_name: str
    section: str
    original_text: str
    action: str
    rewritten_text: str
    reason: str
    market_signal: str
    confidence: float

    def to_row(self) -> dict[str, str | float]:
        return asdict(self)


def write_traceability_csv(changes: list[CurriculumChange], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=TRACEABILITY_COLUMNS)
        writer.writeheader()
        for change in changes:
            writer.writerow(change.to_row())
