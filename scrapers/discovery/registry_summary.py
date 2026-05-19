from __future__ import annotations

import json
import os

import psycopg2


def main() -> int:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "cliente_a_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        sslmode=os.getenv("DB_SSLMODE", "prefer"),
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM public.api_sources_registry")
            total = cur.fetchone()[0]
            cur.execute(
                """
                SELECT source, endpoint, rank_score, seo_noise, auth_required, response_type
                FROM public.api_sources_registry
                ORDER BY rank_score DESC, source, endpoint
                LIMIT 12
                """
            )
            rows = [
                {
                    "source": row[0],
                    "endpoint": row[1][:180],
                    "rank_score": float(row[2] or 0),
                    "seo_noise": bool(row[3]),
                    "auth_required": bool(row[4]),
                    "response_type": row[5],
                }
                for row in cur.fetchall()
            ]
            print(json.dumps({"registry_total": total, "top": rows}, ensure_ascii=False, indent=2))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

