from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from extract_job_offers_and_skills import main as run_extractor


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the public job crawler using portal sources only.")
    parser.add_argument(
        "--config",
        default="scrapers/config/portal_sources.colombia_aggressive.json",
        help="JSON config with portal URLs and output paths.",
    )
    parser.add_argument("--output-dir", default=None, help="Optional override for output directory.")
    parser.add_argument("--db-path", default=None, help="Optional override for SQLite path.")
    parser.add_argument("--no-sqlite", action="store_true", help="Write CSV only.")
    parser.add_argument("--no-csv", action="store_true", help="Write SQLite only.")
    args, passthrough = parser.parse_known_args(argv)

    forwarded = ["--config", args.config]
    if args.output_dir:
        forwarded.extend(["--output-dir", args.output_dir])
    if args.db_path:
        forwarded.extend(["--db-path", args.db_path])
    if args.no_sqlite:
        forwarded.append("--no-sqlite")
    if args.no_csv:
        forwarded.append("--no-csv")
    forwarded.extend(passthrough)
    return run_extractor(forwarded)


if __name__ == "__main__":
    raise SystemExit(main())
