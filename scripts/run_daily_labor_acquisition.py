from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from graduate_intelligence_platform.backend.app.academic_job_acquisition import get_academic_search_intelligence  # noqa: E402
from pipelines.run_labor_acquisition_platform import run_labor_acquisition  # noqa: E402

DEFAULT_SOURCES = [
    "linkedin",
    "elempleo",
    "ticjob",
    "indeed",
    "jooble",
    "hireline",
    "findjobit",
    "interpol",
    "europol",
    "un_careers",
    "unodc",
    "securitas",
    "g4s",
    "prosegur",
    "fiscalia_colombia",
    "policia_colombia",
    "inpec",
    "procuraduria",
    "defensoria",
]

OUTPUT_DIR = ROOT_DIR / "outputs"
LOG_DIR = ROOT_DIR / "logs"
SOURCE_PLAN_FILE = OUTPUT_DIR / "labor_acquisition_source_plans.json"
SUMMARY_FILE = OUTPUT_DIR / "daily_labor_acquisition_summary.json"


def _load_environment() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    for name in (".env.local", ".env", ".env.development"):
        path = ROOT_DIR / name
        if path.exists():
            load_dotenv(path, override=False)


def _build_logger(run_id: str) -> tuple[logging.Logger, Path]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"daily_labor_acquisition_{run_id}.log"
    logger = logging.getLogger(f"daily_labor_acquisition.{run_id}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False
    return logger, log_path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def run_daily_labor_acquisition(
    *,
    sources: list[str],
    crawl_mode: str,
    keyword_limit: int,
    role_limit: int,
    max_jobs: int,
    max_pages: int,
    retries: int,
    retry_delay_seconds: int,
    execute_network: bool,
    persist: bool,
    quality_review: bool,
) -> dict[str, Any]:
    run_id = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    logger, log_path = _build_logger(run_id)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("daily labor acquisition started run_id=%s", run_id)
    last_error: str | None = None
    attempts = max(1, retries + 1)
    for attempt in range(1, attempts + 1):
        try:
            logger.info("building academic source plans attempt=%s/%s mode=%s", attempt, attempts, crawl_mode)
            intelligence = get_academic_search_intelligence(
                mode=crawl_mode,
                keyword_limit=keyword_limit,
                role_limit=role_limit,
            )
            _write_json(
                SOURCE_PLAN_FILE,
                {
                    "generated_at": intelligence.get("generated_at"),
                    "mode": intelligence.get("mode"),
                    "programs_analyzed": intelligence.get("programs_analyzed"),
                    "microcurricula_analyzed": intelligence.get("microcurricula_analyzed"),
                    "keywords_generated": intelligence.get("keywords_generated", []),
                    "roles_generated": intelligence.get("roles_generated", []),
                    "crawler_plans": intelligence.get("crawler_plans", {}),
                },
            )
            logger.info(
                "source plans ready programs=%s keywords=%s roles=%s",
                intelligence.get("programs_analyzed"),
                len(intelligence.get("keywords_generated") or []),
                len(intelligence.get("roles_generated") or []),
            )
            result = run_labor_acquisition(
                sources=sources,
                execute_network=execute_network,
                max_jobs=max_jobs,
                max_pages=max_pages,
                persist=persist,
                quality_review=quality_review,
                search_intelligence=intelligence,
            )
            result = dict(result)
            result.update(
                {
                    "run_id": run_id,
                    "attempts": attempt,
                    "source_plan_file": str(SOURCE_PLAN_FILE),
                    "log_file": str(log_path),
                }
            )
            _write_json(SUMMARY_FILE, result)
            logger.info("daily labor acquisition finished results=%s errors=%s", result.get("results"), len(result.get("errors", [])))
            return result
        except Exception as exc:  # pragma: no cover - scheduler failure path
            last_error = f"{type(exc).__name__}: {exc}"
            logger.exception("daily labor acquisition attempt failed attempt=%s/%s", attempt, attempts)
            if attempt < attempts:
                sleep_for = max(1, retry_delay_seconds)
                logger.info("retrying in %s seconds", sleep_for)
                time.sleep(sleep_for)
    failure = {
        "run_id": run_id,
        "attempts": attempts,
        "status": "failed",
        "error": last_error or "unknown_error",
        "source_plan_file": str(SOURCE_PLAN_FILE),
        "log_file": str(log_path),
    }
    _write_json(SUMMARY_FILE, failure)
    logger.error("daily labor acquisition failed error=%s", last_error)
    return failure


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily labor acquisition scheduler.")
    parser.add_argument("--sources", nargs="+", default=DEFAULT_SOURCES)
    parser.add_argument("--crawl-mode", default="academic_alignment")
    parser.add_argument("--keyword-limit", type=int, default=120)
    parser.add_argument("--role-limit", type=int, default=40)
    parser.add_argument("--max-jobs", type=int, default=1000)
    parser.add_argument("--max-pages", type=int, default=50)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-delay-seconds", type=int, default=120)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--persist", action="store_true", default=True)
    parser.add_argument("--no-persist", action="store_false", dest="persist")
    parser.add_argument("--quality-review", action="store_true", default=True)
    parser.add_argument("--no-quality-review", action="store_false", dest="quality_review")
    args = parser.parse_args()
    _load_environment()
    result = run_daily_labor_acquisition(
        sources=args.sources,
        crawl_mode=args.crawl_mode,
        keyword_limit=args.keyword_limit,
        role_limit=args.role_limit,
        max_jobs=args.max_jobs,
        max_pages=args.max_pages,
        retries=args.retries,
        retry_delay_seconds=args.retry_delay_seconds,
        execute_network=not args.dry_run,
        persist=args.persist,
        quality_review=args.quality_review,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
