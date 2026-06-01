from __future__ import annotations

import json
from pathlib import Path
import sys
from urllib.request import urlopen

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def fetch(url: str) -> dict:
    with urlopen(url, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    urls = {
        "program_intelligence": "http://127.0.0.1:8010/program-intelligence/108",
        "program_summary": "http://127.0.0.1:8010/program-summary/108",
        "curriculum_simulator": "http://127.0.0.1:8010/curriculum-simulator?program_id=108",
    }
    results = {}
    for name, url in urls.items():
        print(f"FETCH {name}")
        results[name] = fetch(url)
        print(f"OK {name}")
    print(json.dumps(
        {
            "gap_count": results["program_intelligence"].get("gap_count"),
            "top_gaps": results["program_intelligence"].get("top_gaps", [])[:8],
            "recommendations": results["program_intelligence"].get("top_recommendations", [])[:5],
            "role_signals": results["program_intelligence"].get("role_signals", [])[:8],
            "emerging_technologies": results["program_intelligence"].get("emerging_technologies", [])[:8],
            "simulation": results["curriculum_simulator"],
            "summary": results["program_summary"],
        },
        ensure_ascii=False,
        indent=2,
        default=str,
    ))


if __name__ == "__main__":
    main()
