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
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'curriculum_gap_observatory'
            ORDER BY ordinal_position
            """
        )
        print(json.dumps(cur.fetchall(), ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    main()
