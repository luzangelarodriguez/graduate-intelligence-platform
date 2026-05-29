from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from api.main import app

CONTRACT_DIR = ROOT_DIR / "frontend_contracts"


def build_example_contracts() -> dict[str, Any]:
    return {
        "health": {
            "status": "ok",
            "database": "connected",
            "timestamp": "2026-05-28T00:00:00Z",
            "checks": {
                "database": True,
                "jobs_table": True,
                "observatory_metrics": True,
                "curriculum_gap_observatory": True,
                "recommendation_observatory": True,
                "semantic_role_graph": True,
                "company_observatory": True,
                "emerging_technology_observatory": True,
            },
            "observatory_freshness": {
                "observatory_metrics": {"rows": 24, "latest": "2026-05-28T00:00:00Z"},
            },
        },
        "recommendations": {
            "items": [
                {
                    "recommendation_type": "career",
                    "target_role": "Analytics Engineer",
                    "target_company": "market",
                    "recommended_skills": ["dbt", "Snowflake", "Airflow"],
                    "market_alignment_score": 0.84,
                    "top_companies": ["Globant", "Rappi"],
                }
            ],
            "count": 1,
            "limit": 20,
            "offset": 0,
            "filters": {},
        },
        "semantic_search": {
            "query": "roles similares a Analytics Engineer",
            "entity_type": "job",
            "count": 1,
            "limit": 10,
            "items": [
                {
                    "entity_type": "job",
                    "entity_id": "123",
                    "title": "Analytics Engineer",
                    "similarity_score": 0.92,
                    "evidence": {"matched_query": "roles similares a Analytics Engineer", "skills": ["SQL", "dbt", "Power BI"]},
                }
            ],
        },
        "metrics": {
            "items": [
                {
                    "metric_name": "top_emerging_skill_1",
                    "metric_category": "skills",
                    "metric_value": 0.82,
                    "metric_period": "2026-05",
                    "confidence_score": 0.91,
                    "generated_at": "2026-05-28T00:00:00Z",
                }
            ],
            "count": 1,
            "limit": 20,
            "offset": 0,
            "filters": {},
        },
    }


def export_contracts(output_dir: Path = CONTRACT_DIR) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    openapi_path = output_dir / "openapi.json"
    contracts_path = output_dir / "contracts.json"
    openapi_path.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False), encoding="utf-8")
    contracts_path.write_text(json.dumps(build_example_contracts(), indent=2, ensure_ascii=False), encoding="utf-8")
    return {"openapi": str(openapi_path), "contracts": str(contracts_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Export API contracts for frontend integration.")
    parser.add_argument("--output-dir", type=Path, default=CONTRACT_DIR)
    args = parser.parse_args()
    print(json.dumps(export_contracts(args.output_dir), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
