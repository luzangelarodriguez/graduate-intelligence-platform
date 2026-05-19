from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def run_step(command: list[str]) -> dict[str, object]:
    result = subprocess.run(command, cwd=ROOT_DIR, capture_output=True, text=True, timeout=360)
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip()[-4000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run API discovery and observability phase.")
    parser.add_argument("--sources", nargs="+", default=["magneto", "computrabajo", "elempleo", "torre", "spe"])
    parser.add_argument("--max-bundles", type=int, default=12)
    parser.add_argument("--wait-ms", type=int, default=7000)
    parser.add_argument("--write-db", action="store_true")
    parser.add_argument("--output", default="outputs/api_discovery/discovery_run_summary.json")
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    write_db = ["--write-db"] if args.write_db else []
    steps = [
        [
            sys.executable,
            "scrapers/discovery/bundle_inspector.py",
            "--sources",
            *args.sources,
            "--max-bundles",
            str(args.max_bundles),
            "--output",
            f"outputs/api_discovery/bundle_findings_{stamp}.json",
            "--run-id",
            f"bundle_inspector_{stamp}",
            *write_db,
        ],
        [
            sys.executable,
            "scrapers/discovery/xhr_capture.py",
            "--sources",
            *args.sources,
            "--wait-ms",
            str(args.wait_ms),
            "--output",
            f"outputs/api_discovery/xhr_capture_{stamp}.json",
            "--run-id",
            f"xhr_capture_{stamp}",
            *write_db,
        ],
    ]
    results = [run_step(step) for step in steps]
    output = ROOT_DIR / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"stamp": stamp, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": args.output, "steps": len(results), "failures": sum(1 for item in results if item["returncode"] != 0)}, ensure_ascii=False))
    return 0 if all(item["returncode"] == 0 for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

