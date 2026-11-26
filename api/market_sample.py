"""Shared SQL fragment: rank-1 market sample per program (latest run, activo jobs only)."""
from __future__ import annotations

# Body of the market-sample CTE chain.  Usage:
#   f"WITH {_MARKET_SAMPLE_CTE} SELECT ..."
#   f"WITH {_MARKET_SAMPLE_CTE}, my_cte AS (...) SELECT ..."
_MARKET_SAMPLE_CTE = """
    latest_runs AS (
        SELECT especializacion_id, MAX(run_id) AS run_id
        FROM ml_program_job_matches
        GROUP BY especializacion_id
    ),
    ranked AS (
        SELECT m.id               AS match_id,
               m.especializacion_id,
               m.empleo_id,
               m.skills_empleo,
               m.relevance_label,
               RANK() OVER (
                   PARTITION BY m.empleo_id
                   ORDER BY m.role_alignment DESC
               ) AS rnk
        FROM ml_program_job_matches m
        JOIN latest_runs lr
          ON lr.especializacion_id = m.especializacion_id
         AND lr.run_id = m.run_id
        JOIN jobs j ON j.id::text = m.empleo_id
        WHERE m.role_alignment IS NOT NULL
          AND m.empleo_id IS NOT NULL
          AND COALESCE(j.activo, TRUE) = TRUE
    ),
    market_sample AS (
        SELECT * FROM ranked WHERE rnk = 1
    )
"""
