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
        pi = cur.fetchone() or {}
        cur.execute("select * from microcurriculum_program_contexts where specialization_id = 108")
        mc = cur.fetchone() or {}
        cur.execute(
            """
            select *
            from curriculum_simulations
            where program_id = 108
            order by updated_at desc nulls last, generated_at desc nulls last
            limit 1
            """
        )
        sim = cur.fetchone() or {}

    def slim_program(row: dict[str, object]) -> dict[str, object]:
        return {
            "risk_score": row.get("risk_score"),
            "risk_level": row.get("risk_level"),
            "gap_count": row.get("gap_count"),
            "alignment_score": row.get("alignment_score"),
            "top_gaps": row.get("top_gaps"),
            "top_recommendations": row.get("top_recommendations"),
            "forecast_signals": row.get("forecast_signals"),
            "role_signals": row.get("role_signals"),
            "emerging_technologies": row.get("emerging_technologies"),
            "business_justification": row.get("business_justification"),
            "domain_key": (row.get("supporting_evidence") or {}).get("domain_taxonomy", {}).get("domain_key"),
            "domain_label": (row.get("supporting_evidence") or {}).get("domain_taxonomy", {}).get("domain_label"),
        }

    def slim_context(row: dict[str, object]) -> dict[str, object]:
        return {
            "detected_domain": row.get("detected_domain"),
            "detected_subdomain": row.get("detected_subdomain"),
            "confidence": row.get("confidence"),
            "technical_skills": row.get("technical_skills"),
            "real_market_gaps": row.get("real_market_gaps"),
            "benchmarking": row.get("benchmarking"),
            "executive_narrative": row.get("executive_narrative"),
        }

    def slim_sim(row: dict[str, object]) -> dict[str, object]:
        return {
            "projected_alignment_score": row.get("projected_alignment_score"),
            "projected_risk_score": row.get("projected_risk_score"),
            "projected_employability_gain": row.get("projected_employability_gain"),
            "projected_gap_reduction": row.get("projected_gap_reduction"),
            "confidence_score": row.get("confidence_score"),
            "proposed_skills": row.get("proposed_skills"),
            "explanation": row.get("explanation"),
        }

    print(json.dumps({
        "program_intelligence": slim_program(pi),
        "microcurriculum_context": slim_context(mc),
        "simulation": slim_sim(sim),
    }, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
