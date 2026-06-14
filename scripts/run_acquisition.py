"""
scripts/run_acquisition.py
--------------------------
Run Playwright scrapers and persist results to PostgreSQL.

Usage:
    python scripts/run_acquisition.py --dry-run
    python scripts/run_acquisition.py --domain data_analytics --limit 5
    python scripts/run_acquisition.py --source elempleo --limit 10
"""
from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path bootstrap — allow imports from repo root
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

# ---------------------------------------------------------------------------
# Load .env.local before any backend imports that read env vars
# ---------------------------------------------------------------------------
_env_file = ROOT_DIR / ".env.local"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hardcoded fallback queries (used when get_academic_search_intelligence() fails)
# ---------------------------------------------------------------------------
FALLBACK_QUERIES: dict[str, list[str]] = {
    "data_analytics": ["analista de datos", "business intelligence", "power bi"],
    "artificial_intelligence": ["inteligencia artificial", "machine learning", "data scientist"],
    "criminology": [
        "perito judicial",
        "analista forense",
        "psicólogo forense",
        "investigador judicial",
        "oficial cumplimiento",
        "analista inteligencia criminal",
    ],
    "cybersecurity": [
        "analista ciberseguridad",
        "investigador digital",
        "analista riesgo",
    ],
    "technology": ["desarrollador software", "ingeniero de sistemas", "programador"],
    "business": ["analista financiero", "gerente de proyectos", "consultor empresarial"],
    "education": [
        "neuropsicólogo",
        "neuropsicología",
        "psicólogo educativo",
        "docente neuropsicología",
    ],
}

DEFAULT_DOMAINS = ["data_analytics", "artificial_intelligence", "criminology", "cybersecurity", "education"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def content_hash(job: dict[str, Any]) -> str:
    title = str(job.get("titulo") or job.get("title") or "")
    company = str(job.get("empresa") or job.get("company") or "")
    desc = str(job.get("descripcion") or job.get("description") or "")[:100]
    return hashlib.md5(f"{title}|{company}|{desc}".encode()).hexdigest()


def _get_search_terms_for_domain(domain: str, crawler_plans: dict[str, Any] | None) -> list[str]:
    """Extract Spanish search terms from the intelligence plans, falling back to hardcoded list."""
    if crawler_plans:
        # Try elempleo plan first (Colombian portal with search_terms)
        for source_key in ("elempleo", "computrabajo", "magneto", "occ", "ticjob", "indeed_co", "google_jobs"):
            plan = crawler_plans.get(source_key, {})
            if plan:
                terms = plan.get("search_terms") or plan.get("keywords") or []
                if terms:
                    return [str(t) for t in terms if t]
    return FALLBACK_QUERIES.get(domain, ["analista de datos", "business intelligence", "data analyst"])


def _introspect_columns(conn) -> tuple[set[str], bool]:
    """Return (jobs_columns, job_skills_exists)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'jobs' AND table_schema = 'public'"
        )
        rows = cur.fetchall()
        jobs_cols: set[str] = set()
        for row in rows:
            if isinstance(row, dict):
                jobs_cols.add(row["column_name"])
            else:
                jobs_cols.add(row[0])

        cur.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'job_skills' AND table_schema = 'public'"
        )
        row = cur.fetchone()
        count = row["count"] if isinstance(row, dict) else row[0]
        job_skills_exists = int(count) > 0

    return jobs_cols, job_skills_exists


def _existing_hashes(conn) -> set[str]:
    """Load all content_hash values already in the jobs table."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT content_hash FROM public.jobs WHERE content_hash IS NOT NULL")
            rows = cur.fetchall()
        result: set[str] = set()
        for row in rows:
            h = row["content_hash"] if isinstance(row, dict) else row[0]
            if h:
                result.add(str(h))
        return result
    except Exception as exc:
        logger.warning("Could not load existing hashes: %s", exc)
        return set()


def _build_insert_payload(
    job: dict[str, Any],
    *,
    domain: str,
    query: str,
    cols: set[str],
    job_hash: str,
) -> dict[str, Any]:
    """Build a dict of column→value for inserting into public.jobs."""
    # Field mapping: scraper field → DB column (checks which exists)
    def pick(db_col: str, *scraper_keys: str) -> Any:
        if db_col not in cols:
            return None
        for k in scraper_keys:
            v = job.get(k)
            if v is not None and str(v).strip():
                return str(v).strip()
        return None

    payload: dict[str, Any] = {}

    # Required NOT NULL fields
    title_val = pick("title", "titulo", "title") or pick("titulo", "titulo", "title") or "(sin título)"
    company_val = pick("company", "empresa", "company") or pick("empresa", "empresa", "company") or "(sin empresa)"
    description_val = (
        pick("description", "descripcion", "description")
        or pick("descripcion", "descripcion", "description")
        or ""
    )
    source_val = (
        pick("source", "source", "portal")
        or pick("portal", "portal", "source")
        or "elempleo"
    )
    url_val = pick("source_url", "url", "source_url") or pick("url", "url") or ""

    # Ensure required NOT NULL columns are always set if they exist
    if "title" in cols:
        payload["title"] = title_val
    if "titulo" in cols:
        payload["titulo"] = title_val
    if "company" in cols:
        payload["company"] = company_val
    if "empresa" in cols:
        payload["empresa"] = company_val
    if "description" in cols:
        payload["description"] = description_val
    if "descripcion" in cols:
        payload["descripcion"] = description_val
    if "source" in cols:
        payload["source"] = source_val
    if "portal" in cols:
        payload["portal"] = source_val
    if "source_url" in cols:
        payload["source_url"] = url_val
    if "url" in cols:
        payload["url"] = url_val

    # Optional columns
    location_val = pick("location", "ciudad", "city", "location")
    if "location" in cols and location_val:
        payload["location"] = location_val
    if "ciudad" in cols and location_val:
        payload["ciudad"] = location_val
    if "city" in cols and location_val:
        payload["city"] = location_val

    if "dominio" in cols:
        payload["dominio"] = domain
    if "domain" in cols:
        payload["domain"] = domain

    if "content_hash" in cols:
        payload["content_hash"] = job_hash

    if "fingerprint" in cols:
        # fingerprint = same as content_hash for our purposes
        payload["fingerprint"] = job_hash

    return payload


def _insert_job(conn, payload: dict[str, Any]) -> int | None:
    """Insert one job row, return the new id or None on conflict."""
    cols = list(payload.keys())
    placeholders = ["%s"] * len(cols)
    sql = (
        f"INSERT INTO public.jobs ({', '.join(cols)}) "
        f"VALUES ({', '.join(placeholders)}) "
        f"ON CONFLICT DO NOTHING "
        f"RETURNING id"
    )
    with conn.cursor() as cur:
        cur.execute(sql, [payload[c] for c in cols])
        row = cur.fetchone()
    if row is None:
        return None
    return int(row["id"] if isinstance(row, dict) else row[0])


def _insert_job_skills(conn, job_id: int, skills: list[str]) -> None:
    """Insert rows into public.job_skills for each skill."""
    if not skills or not job_id:
        return
    sql = (
        "INSERT INTO public.job_skills (job_id, canonical_skill, skill_category, skill_family, confidence, evidence_type, source_section) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (job_id, canonical_skill) DO NOTHING"
    )
    with conn.cursor() as cur:
        for skill in skills:
            if skill and str(skill).strip():
                cur.execute(sql, [job_id, str(skill).strip(), "Unknown", "Unknown", 0.5, "job_evidence", "description"])


# ---------------------------------------------------------------------------
# Main acquisition logic
# ---------------------------------------------------------------------------

def run_acquisition(
    domains: list[str],
    source_name: str,
    limit: int,
    dry_run: bool,
) -> dict[str, Any]:
    """Run the full acquisition pipeline."""
    # ------------------------------------------------------------------
    # 1. Get crawler plans from academic intelligence
    # ------------------------------------------------------------------
    crawler_plans_by_domain: dict[str, dict[str, Any]] = {}
    try:
        from graduate_intelligence_platform.backend.app.academic_job_acquisition import (
            get_academic_search_intelligence,
            source_plan_for,
        )
        logger.info("Loading academic search intelligence...")
        intelligence = get_academic_search_intelligence()
        # intelligence has .programs[] each with .source_plans
        for prog in intelligence.get("programs", []):
            dom = prog.get("domain", "")
            if dom and dom not in crawler_plans_by_domain:
                crawler_plans_by_domain[dom] = prog.get("source_plans", {})
        logger.info("Academic intelligence loaded for domains: %s", list(crawler_plans_by_domain.keys()))
    except Exception as exc:
        logger.warning("get_academic_search_intelligence() failed (%s) — using fallback queries", exc)

    # ------------------------------------------------------------------
    # 2. Connect to DB (unless dry-run)
    # ------------------------------------------------------------------
    conn = None
    db_available = False
    jobs_cols: set[str] = set()
    job_skills_exists = False
    existing_hashes: set[str] = set()

    if not dry_run:
        try:
            from backend.db import get_conn
            conn = get_conn()
            conn.autocommit = False
            jobs_cols, job_skills_exists = _introspect_columns(conn)
            existing_hashes = _existing_hashes(conn)
            db_available = True
            logger.info("DB connected. jobs table has %d columns. job_skills exists: %s", len(jobs_cols), job_skills_exists)
        except Exception as exc:
            logger.warning("DB connection failed (%s) — switching to dry-run mode", exc)
            dry_run = True

    # ------------------------------------------------------------------
    # 3. Load scraper
    # ------------------------------------------------------------------
    scrape_fn = None
    try:
        if source_name == "elempleo":
            from scrapers.sources.elempleo_scraper import scrape_jobs
            scrape_fn = scrape_jobs
        elif source_name == "google_jobs":
            from scrapers.sources.google_jobs_scraper import scrape_jobs
            scrape_fn = scrape_jobs
        else:
            # Generic lazy import
            import importlib
            mod = importlib.import_module(f"scrapers.sources.{source_name}_scraper")
            scrape_fn = getattr(mod, "scrape_jobs")
    except Exception as exc:
        logger.error("Could not load scraper '%s': %s", source_name, exc)
        scrape_fn = None

    # ------------------------------------------------------------------
    # 4. Run per domain
    # ------------------------------------------------------------------
    report_domains: dict[str, Any] = {}
    total_scraped = 0
    total_inserted = 0
    total_duplicates = 0
    total_errors = 0

    for domain in domains:
        domain_plans = crawler_plans_by_domain.get(domain)
        search_terms = _get_search_terms_for_domain(domain, domain_plans)
        selected_terms = search_terms[:3]

        domain_scraped = 0
        domain_inserted = 0
        domain_errors = 0
        domain_queries: list[str] = []

        for term in selected_terms:
            domain_queries.append(term)
            if scrape_fn is None:
                logger.error("No scraper available — skipping query '%s'", term)
                total_errors += 1
                domain_errors += 1
                continue

            jobs: list[dict[str, Any]] = []
            try:
                logger.info("Scraping domain=%s query='%s' limit=%d ...", domain, term, limit)
                jobs = scrape_fn(query=term, limit=limit)
                logger.info("  → %d jobs returned", len(jobs))
            except Exception as exc:
                logger.error("Scraper error for query '%s': %s", term, exc)
                total_errors += 1
                domain_errors += 1
                continue

            domain_scraped += len(jobs)
            total_scraped += len(jobs)

            # Deduplicate within this batch
            seen_in_batch: set[str] = set()
            new_jobs: list[dict[str, Any]] = []
            for job in jobs:
                h = content_hash(job)
                if h in seen_in_batch or h in existing_hashes:
                    total_duplicates += 1
                    continue
                seen_in_batch.add(h)
                new_jobs.append((job, h))

            if dry_run:
                for job, h in new_jobs:
                    title = job.get("titulo") or job.get("title") or "(no title)"
                    company = job.get("empresa") or job.get("company") or "(no company)"
                    print(f"  [DRY-RUN] Would insert: {title!r} @ {company!r} (hash={h[:8]})")
                domain_inserted += len(new_jobs)
                total_inserted += len(new_jobs)
                print(f"domain {domain} | query '{term}' | {len(new_jobs)} new jobs (dry-run)")
            else:
                inserted_count = 0
                for job, h in new_jobs:
                    payload = _build_insert_payload(
                        job,
                        domain=domain,
                        query=term,
                        cols=jobs_cols,
                        job_hash=h,
                    )
                    try:
                        job_id = _insert_job(conn, payload)
                        if job_id is not None:
                            existing_hashes.add(h)
                            inserted_count += 1
                            # Insert skills
                            if job_skills_exists:
                                skills = job.get("skills") or []
                                if skills:
                                    _insert_job_skills(conn, job_id, skills)
                    except Exception as exc:
                        logger.error("DB insert error for job '%s': %s", job.get("titulo") or job.get("title"), exc)
                        total_errors += 1
                        domain_errors += 1

                try:
                    conn.commit()
                except Exception as exc:
                    logger.error("Commit failed: %s", exc)
                    conn.rollback()

                domain_inserted += inserted_count
                total_inserted += inserted_count
                logger.info("domain %s | query '%s' | %d new jobs inserted", domain, term, inserted_count)
                print(f"domain {domain} | query '{term}' | {inserted_count} new jobs inserted")

        report_domains[domain] = {
            "queries_run": domain_queries,
            "jobs_scraped": domain_scraped,
            "jobs_inserted": domain_inserted,
            "errors": domain_errors,
        }

    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass

    return {
        "dry_run": dry_run,
        "total_scraped": total_scraped,
        "total_inserted": total_inserted,
        "total_duplicates": total_duplicates,
        "total_errors": total_errors,
        "domains": report_domains,
    }


def write_report(stats: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    mode = "dry-run" if stats["dry_run"] else "live"
    lines = [
        "# Acquisition Run Report",
        f"Date: {now}",
        f"Mode: {mode}",
        "",
        "## Summary",
        f"- Total jobs scraped: {stats['total_scraped']}",
        f"- Total jobs inserted: {stats['total_inserted']}",
        f"- Total duplicates skipped: {stats['total_duplicates']}",
        f"- Errors: {stats['total_errors']}",
        "",
        "## By Domain",
    ]
    for domain, info in stats["domains"].items():
        lines.append(f"### {domain}")
        queries_str = ", ".join(f"'{q}'" for q in info["queries_run"])
        lines.append(f"- Queries run: [{queries_str}]")
        lines.append(f"- Jobs scraped: {info['jobs_scraped']}")
        lines.append(f"- Jobs inserted: {info['jobs_inserted']}")
        lines.append(f"- Errors: {info['errors']}")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Report written to %s", output_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Playwright scrapers and persist results to PostgreSQL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't insert to DB, just print what would be inserted",
    )
    parser.add_argument(
        "--domain",
        metavar="DOMAIN",
        default=None,
        help="Only run for this domain (e.g. data_analytics). Default: all three main domains.",
    )
    parser.add_argument(
        "--source",
        metavar="SOURCE",
        default="elempleo",
        help=(
            "Scraper to use (default: elempleo). "
            "Available: elempleo, magneto, magneto_api, computrabajo, indeed_co, "
            "occ, torre, ticjob, hirelatam, getonbrd, tecnoempleo, spe, remoterocketship, google_jobs"
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="Max jobs per query (default: 10)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    domains = [args.domain] if args.domain else DEFAULT_DOMAINS
    logger.info(
        "Starting acquisition: domains=%s source=%s limit=%d dry_run=%s",
        domains, args.source, args.limit, args.dry_run,
    )

    stats = run_acquisition(
        domains=domains,
        source_name=args.source,
        limit=args.limit,
        dry_run=args.dry_run,
    )

    output_path = ROOT_DIR / "outputs" / "acquisition_run_report.md"
    write_report(stats, output_path)

    print("\n=== Acquisition complete ===")
    print(f"Mode       : {'dry-run' if stats['dry_run'] else 'live'}")
    print(f"Scraped    : {stats['total_scraped']}")
    print(f"Inserted   : {stats['total_inserted']}")
    print(f"Duplicates : {stats['total_duplicates']}")
    print(f"Errors     : {stats['total_errors']}")
    print(f"Report     : {output_path}")


if __name__ == "__main__":
    main()
