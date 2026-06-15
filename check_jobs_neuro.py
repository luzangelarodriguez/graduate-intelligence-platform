#!/usr/bin/env python3
"""Temporary diagnostic: check neuropsicología jobs in Railway DB."""
import os, sys
from pathlib import Path

# Load .env.local
env_path = Path(__file__).parent / ".env.local"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

url = os.getenv("RAILWAY_DATABASE_URL", "")
if not url:
    sys.exit("ERROR: RAILWAY_DATABASE_URL not set")

# Proxy workaround
url = url.replace("ballast.proxy.rlwy.net", "66.33.22.248")

import psycopg2, psycopg2.extras

conn = psycopg2.connect(url, sslmode="require", cursor_factory=psycopg2.extras.RealDictCursor)
cur = conn.cursor()

# ── 1. Columns of 'jobs' table ────────────────────────────────────────────────
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'jobs'
    ORDER BY ordinal_position
""")
cols = cur.fetchall()
print("=== jobs table columns ===")
for c in cols:
    print(f"  {c['column_name']:30s} {c['data_type']}")

# ── 2. Total jobs count ───────────────────────────────────────────────────────
cur.execute("SELECT COUNT(*) AS n FROM jobs")
print(f"\n=== Total jobs: {cur.fetchone()['n']} ===")

# ── 3. Jobs matching neuropsicología / psicología ────────────────────────────
cur.execute("""
    SELECT COUNT(*) AS n FROM jobs
    WHERE title ILIKE '%neuropsicolog%'
       OR title ILIKE '%psicolog%'
""")
print(f"\n=== Jobs matching *neuropsicolog* or *psicolog*: {cur.fetchone()['n']} ===")

# ── 4. Sample 3 matching jobs ─────────────────────────────────────────────────
cur.execute("""
    SELECT title, company, LENGTH(description) AS desc_len, LEFT(description, 200) AS desc_preview
    FROM jobs
    WHERE title ILIKE '%neuropsicolog%' OR title ILIKE '%psicolog%'
    LIMIT 3
""")
rows = cur.fetchall()
print("\n=== Sample matching jobs ===")
for r in rows:
    print(f"\n  title      : {r['title']}")
    print(f"  company    : {r['company']}")
    print(f"  desc_len   : {r['desc_len']}")
    print(f"  desc[:200] : {r['desc_preview']}")

# ── 5. Domain column check ────────────────────────────────────────────────────
has_domain = any(c["column_name"] == "domain" for c in cols)
if has_domain:
    cur.execute("""
        SELECT domain, COUNT(*) AS n FROM jobs
        GROUP BY domain ORDER BY n DESC LIMIT 10
    """)
    print("\n=== Jobs by domain ===")
    for r in cur.fetchall():
        print(f"  {r['domain'] or 'NULL':30s} {r['n']}")
else:
    print("\n(No 'domain' column in jobs table)")

# ── 6. Jobs with non-empty job_skills ─────────────────────────────────────────
cur.execute("""
    SELECT COUNT(DISTINCT j.id) AS n
    FROM jobs j
    JOIN job_skills js ON js.job_id = j.id
    WHERE (j.title ILIKE '%neuropsicolog%' OR j.title ILIKE '%psicolog%'
           OR j.title ILIKE '%docente%' OR j.title ILIKE '%educati%')
      AND js.canonical_skill IS NOT NULL AND js.canonical_skill <> ''
""")
print(f"\n=== Education-related jobs with non-empty job_skills: {cur.fetchone()['n']} ===")

# ── 7. What portals are jobs from? ────────────────────────────────────────────
portal_col = next((c["column_name"] for c in cols if c["column_name"] in ("portal", "source", "fuente")), None)
if portal_col:
    cur.execute(f"SELECT {portal_col}, COUNT(*) AS n FROM jobs GROUP BY {portal_col} ORDER BY n DESC LIMIT 10")
    print(f"\n=== Jobs by {portal_col} ===")
    for r in cur.fetchall():
        print(f"  {str(r[portal_col] or 'NULL'):30s} {r['n']}")

conn.close()
print("\nDone.")
