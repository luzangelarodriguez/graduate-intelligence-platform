from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


DEFAULT_INPUT = Path("outputs/human_validation_matrix.csv")
DEFAULT_OUTPUT = Path("ml/datasets/curriculum_gold_dataset.csv")

OUTPUT_COLUMNS = (
    "text_fragment",
    "entity",
    "entity_type",
    "normalized_skill",
    "domain",
    "confidence",
    "validated_human",
)

TRUE_VALUES = {"1", "true", "yes", "y", "si", "sí", "correcto", "ok"}


def is_validated(value: str | None) -> bool:
    return str(value or "").strip().casefold() in TRUE_VALUES


def build_gold_dataset(input_path: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT) -> dict[str, int | str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0
    rows_read = 0

    with output_path.open("w", encoding="utf-8", newline="") as out_fh:
        writer = csv.DictWriter(out_fh, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()

        if input_path.exists():
            with input_path.open("r", encoding="utf-8-sig", newline="") as in_fh:
                reader = csv.DictReader(in_fh)
                for row in reader:
                    rows_read += 1
                    if not is_validated(row.get("is_correct")):
                        continue
                    corrected = (row.get("correction") or "").strip()
                    normalized = corrected or (row.get("normalized_entity") or "").strip()
                    entity = corrected or (row.get("entity_detected") or "").strip()
                    if not entity and not normalized:
                        continue
                    writer.writerow(
                        {
                            "text_fragment": row.get("text_fragment") or "",
                            "entity": entity or normalized,
                            "entity_type": row.get("entity_type") or "",
                            "normalized_skill": normalized or entity,
                            "domain": row.get("detected_subdomain") or row.get("detected_domain") or "",
                            "confidence": "",
                            "validated_human": "true",
                        }
                    )
                    rows_written += 1

    return {
        "input": str(input_path),
        "output": str(output_path),
        "rows_read": rows_read,
        "rows_written": rows_written,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the curriculum Gold dataset from human validation matrices.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    summary = build_gold_dataset(Path(args.input), Path(args.output))
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
