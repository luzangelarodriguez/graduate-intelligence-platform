from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.db import get_cursor


def main() -> None:
    with get_cursor(db_name=None) as cur:
        cur.execute(
            """
            SELECT gap_type, skill_normalized, severity, demand_count, confidence_score, evidence, source_document
            FROM public.microcurriculo_market_gaps
            WHERE microcurriculo_id = %s
            ORDER BY confidence_score DESC NULLS LAST, demand_count DESC NULLS LAST, skill_normalized ASC
            """,
            (21,),
        )
        print(json.dumps(cur.fetchall(), ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    main()
