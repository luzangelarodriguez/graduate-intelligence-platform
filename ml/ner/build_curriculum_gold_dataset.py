from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from microcurriculum_engine.ingestion.document_loader import load_document
from ml.ner import extract_curriculum_entities


DEFAULT_INPUT_DIRS = (Path("storage/microcurriculos"), Path("storage/test_microcurriculos"))
DEFAULT_OUTPUT = Path("ml/datasets/curriculum_gold_dataset.csv")
REQUIRED_COLUMNS = (
    "text_fragment",
    "entity",
    "entity_type",
    "normalized_skill",
    "domain",
    "confidence",
    "validated_human",
)


def _documents(input_dirs: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for directory in input_dirs:
        if not directory.exists():
            continue
        paths.extend(sorted(directory.glob("*.pdf")))
        paths.extend(sorted(directory.glob("*.txt")))
    return sorted(set(paths), key=lambda path: str(path).casefold())


def _load_text(path: Path) -> str:
    if path.suffix.casefold() == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    return load_document(path, persist_original=False).clean_text


def build_gold_dataset(input_dirs: list[Path], output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    rows: list[dict[str, str | float | bool]] = []
    seen: set[tuple[str, str, str]] = set()
    documents = _documents(input_dirs)
    for path in documents:
        text = _load_text(path)
        for entity in extract_curriculum_entities(text):
            key = (
                str(entity["text_fragment"]),
                str(entity["normalized_skill"]),
                str(entity["entity_type"]),
            )
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "text_fragment": entity["text_fragment"],
                    "entity": entity["entity"],
                    "entity_type": entity["entity_type"],
                    "normalized_skill": entity["normalized_skill"],
                    "domain": entity["domain"],
                    "confidence": entity["confidence"],
                    "validated_human": False,
                }
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return {
        "documents_scanned": len(documents),
        "rows_generated": len(rows),
        "output": str(output),
        "entity_types": sorted(set(str(row["entity_type"]) for row in rows)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build seed human-review Gold dataset for curriculum NER.")
    parser.add_argument("--input-dir", action="append", default=None)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    input_dirs = [Path(item) for item in args.input_dir] if args.input_dir else list(DEFAULT_INPUT_DIRS)
    summary = build_gold_dataset(input_dirs, Path(args.output))
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
