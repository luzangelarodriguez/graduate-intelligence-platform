from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.inference.domain_classifier import predict_domain, prediction_to_dict


def main() -> int:
    parser = argparse.ArgumentParser(description="Run disciplinary domain inference.")
    parser.add_argument("--title", default="")
    parser.add_argument("--description", default="")
    parser.add_argument("--skills", default="")
    args = parser.parse_args()
    skills = [item.strip() for item in args.skills.split(",") if item.strip()]
    result = predict_domain(title=args.title, description=args.description, skills=skills)
    print(json.dumps(prediction_to_dict(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
