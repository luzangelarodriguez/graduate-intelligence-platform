from __future__ import annotations

import json
from pathlib import Path
import sys

from psycopg2.extras import RealDictCursor

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.db import get_conn


def main() -> None:
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("select * from program_intelligence where program_id = 108")
        pi = cur.fetchone()
        cur.execute("select * from microcurriculum_program_contexts where specialization_id = 108")
        mc = cur.fetchone()
        cur.execute(
            """
            select *
            from curriculum_simulations
            where program_id = 108
            order by updated_at desc nulls last, generated_at desc nulls last
            limit 1
            """
        )
        sim = cur.fetchone()
    print(json.dumps({
        "program_intelligence": pi,
        "microcurriculum_context": mc,
        "simulation": sim,
    }, default=str, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
