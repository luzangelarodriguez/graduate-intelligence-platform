from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agents.visual_analytics_labor_agent import AgentExtractionResult, evidence_to_dict  # noqa: E402
from crawlers.connectors.api_wrappers import make_connector  # noqa: E402
from crawlers.connectors.linkedin_jobs_crawler import LinkedInCrawlerConfig, LinkedInJobsCrawler  # noqa: E402
from crawlers.core.data_quality import build_quality_envelope, deduplicate_cross_source  # noqa: E402
from crawlers.core.execution_manifest import ExecutionManifest  # noqa: E402
from crawlers.core.observability import JsonLogger, SourceMetrics, new_correlation_id  # noqa: E402
from crawlers.core.resilience import CircuitBreakerRegistry, detect_blocking_signal, fail_safe_shutdown  # noqa: E402
from crawlers.core.security import sanitize_value  # noqa: E402
from crawlers.storage.postgres_warehouse import persist_warehouse, verify_warehouse_counts, write_analytics_reports  # noqa: E402
from ml.curriculum.curriculum_market_gap_engine import build_curriculum_market_gap_map  # noqa: E402
from ml.labor.labor_market_skill_extraction_engine import build_labor_market_skill_universe  # noqa: E402
from ml.labor.market_skill_intelligence_engine import build_market_skill_intelligence_map  # noqa: E402
from ml.labor.occupational_skill_cluster_engine import build_occupational_skill_clusters  # noqa: E402
from pipelines.run_agentic_labor_intelligence import persist_layers  # noqa: E402

OUTPUT_DIR = ROOT_DIR / "outputs"
RESULTS_JSON = OUTPUT_DIR / "labor_acquisition_results.json"
HEALTH_REPORT = OUTPUT_DIR / "labor_acquisition_health_report.json"


def _run_source(source: str, *, execute_network: bool, max_jobs: int, max_pages: int) -> tuple[list[AgentExtractionResult], list[dict[str, str]]]:
    if source == "linkedin":
        crawler = LinkedInJobsCrawler(LinkedInCrawlerConfig(max_jobs=max_jobs, max_pages=max_pages, headless=True))
        return crawler.run(execute_network=execute_network)
    connector = make_connector(source, max_jobs=max_jobs, max_pages=max_pages)
    if hasattr(connector, "fetch_agent_results"):
        results, meta = connector.fetch_agent_results(execute_network=execute_network, max_jobs=max_jobs)
        errors = [
            {"source": source, "error_type": str(item.get("error_type", "error")), "error_message": str(item)[:500]}
            for item in meta.get("errors", [])
        ]
        if meta.get("source_status") == "credentials_missing":
            errors.append({"source": source, "error_type": "credentials_missing", "error_message": "credentials_missing"})
        return results, errors
    return connector.run(execute_network=execute_network)


def _write_reports(
    results: list[AgentExtractionResult],
    errors: list[dict[str, str]],
    persisted: dict[str, Any],
    market: dict[str, Any],
    *,
    source_metrics: dict[str, Any] | None = None,
    correlation_id: str = "",
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON.write_text(json.dumps([evidence_to_dict(item) for item in results], indent=2, ensure_ascii=False), encoding="utf-8")
    real_jobs = [item for item in results if item.silver.document_type == "job_posting"]
    probable_jobs = [item for item in results if float(getattr(item.silver, "job_probability_score", 0.0) or 0.0) >= 0.30]
    curated_jobs = [item for item in results if getattr(item.silver, "curation_level", "") in {"curated_job", "gold_job"}]
    gold_jobs = [item for item in results if getattr(item.silver, "curation_level", "") == "gold_job"]
    blocked = [item for item in results if item.silver.document_type != "job_posting"]
    skill_counts: dict[str, int] = {}
    for item in real_jobs:
        for skill in item.silver.job_evidence_skills or []:
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
    quality_envelopes = [build_quality_envelope(item).to_dict() for item in results]
    avg_completeness = round(sum(item["completeness_score"] for item in quality_envelopes) / max(len(quality_envelopes), 1), 4)
    lines = [
        "# Labor Acquisition Run Report",
        "",
        f"- Correlation ID: {correlation_id}",
        f"- Resultados inspeccionados: {len(results)}",
        f"- Vacantes reales detectadas: {len(real_jobs)}",
        f"- Probable jobs: {len(probable_jobs)}",
        f"- Curated jobs: {len(curated_jobs)}",
        f"- Gold jobs: {len(gold_jobs)}",
        f"- Documentos descartados/bloqueados: {len(blocked)}",
        f"- Errores: {len(errors)}",
        f"- Completeness promedio: {avg_completeness}",
        f"- Persistencia: {json.dumps(persisted, ensure_ascii=False)}",
        "",
        "## Skills extraidas",
        *[f"- {skill}: {count}" for skill, count in sorted(skill_counts.items(), key=lambda item: item[1], reverse=True)[:40]],
        "",
        "## Errores por portal",
        *[f"- {item['source']}: {item['error_type']} - {item['error_message']}" for item in errors],
    ]
    (OUTPUT_DIR / "labor_acquisition_run_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    quality = {
        "results": len(results),
        "real_job_postings": len(real_jobs),
        "probable_jobs": len(probable_jobs),
        "curated_jobs": len(curated_jobs),
        "gold_jobs": len(gold_jobs),
        "blocked_documents": len(blocked),
        "document_types": {},
        "quality_envelopes": quality_envelopes,
        "avg_completeness": avg_completeness,
        "persisted": persisted,
        "market": market,
        "errors": sanitize_value(errors),
    }
    for item in results:
        dtype = item.silver.document_type
        quality["document_types"][dtype] = quality["document_types"].get(dtype, 0) + 1
    (OUTPUT_DIR / "labor_acquisition_quality_report.json").write_text(json.dumps(quality, indent=2, ensure_ascii=False), encoding="utf-8")
    health_report = OUTPUT_DIR / "labor_acquisition_health_report.json"
    health_report.write_text(
        json.dumps(
            {
                "correlation_id": correlation_id,
                "source_metrics": source_metrics or {},
                "errors": sanitize_value(errors),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    failed_lines = ["# Labor Acquisition Failed URLs", ""]
    failed_lines.extend([f"- {item['source']}: {item['error_type']} - {item['error_message']}" for item in errors] or ["- Sin errores."])
    (OUTPUT_DIR / "labor_acquisition_failed_urls.md").write_text("\n".join(failed_lines) + "\n", encoding="utf-8")
    market_lines = [
        "# Labor Market Skill After Acquisition",
        "",
        f"- Skill universe: {market.get('skill_universe')}",
        f"- Occupational clusters: {market.get('occupational_clusters')}",
        f"- Covered skills: {market.get('covered_skills')}",
        f"- Missing skills: {market.get('missing_skills')}",
        f"- Emerging skills: {market.get('emerging_skills')}",
    ]
    (OUTPUT_DIR / "labor_market_skill_after_acquisition.md").write_text("\n".join(market_lines) + "\n", encoding="utf-8")


def run_labor_acquisition(
    *,
    sources: list[str],
    execute_network: bool,
    max_jobs: int,
    max_pages: int,
    persist: bool,
    quality_review: bool,
    correlation_id: str | None = None,
    workers: int = 1,
    resume_from: str = "",
) -> dict[str, Any]:
    correlation_id = correlation_id or new_correlation_id()
    logger = JsonLogger(correlation_id)
    manifest = ExecutionManifest(
        correlation_id=correlation_id,
        sources=sources,
        execute_network=execute_network,
        max_jobs=max_jobs,
        max_pages=max_pages,
        persist=persist,
        quality_review=quality_review,
    )
    manifest.save()
    logger.log("labor_acquisition_started", sources=sources, execute_network=execute_network, workers=workers, resume_from=resume_from)
    results: list[AgentExtractionResult] = []
    errors: list[dict[str, str]] = []
    metrics: dict[str, SourceMetrics] = {}
    circuit_breakers = CircuitBreakerRegistry()
    for source in sources:
        breaker = circuit_breakers.for_source(source)
        metrics[source] = SourceMetrics(source_name=source)
        if not breaker.allow_request():
            error = {"source": source, "error_type": "circuit_open", "error_message": "source circuit breaker is open"}
            errors.append(error)
            logger.log("source_skipped_circuit_open", **error)
            continue
        started = time.perf_counter()
        try:
            logger.log("source_started", source=source)
            source_results, source_errors = _run_source(source, execute_network=execute_network, max_jobs=max_jobs, max_pages=max_pages)
            results.extend(source_results)
            errors.extend(source_errors)
            metrics[source].requests += 1
            metrics[source].successes += 1 if source_results or not source_errors else 0
            metrics[source].failures += 1 if source_errors else 0
            if source_errors:
                breaker.record_failure()
            else:
                breaker.record_success()
            for error in source_errors:
                blocked, reason = detect_blocking_signal(text=json.dumps(error, ensure_ascii=False))
                if blocked:
                    metrics[source].blocked += 1
                    fail_safe_shutdown(errors, source_name=source, reason=reason)
                    breaker.record_failure()
                    break
            logger.log("source_finished", source=source, results=len(source_results), errors=source_errors)
        except Exception as exc:
            breaker.record_failure()
            metrics[source].requests += 1
            metrics[source].failures += 1
            error = {"source": source, "error_type": type(exc).__name__, "error_message": str(exc)[:500]}
            errors.append(error)
            logger.log("source_failed", **error)
        finally:
            metrics[source].record_latency((time.perf_counter() - started) * 1000)
            metrics[source].finish()
            manifest.checkpoint(f"source:{source}", {"results": len(results), "errors": len(errors), "circuit": breaker.snapshot()})

    before_dedupe = len(results)
    results = deduplicate_cross_source(results)
    logger.log("deduplication_completed", before=before_dedupe, after=len(results))
    persisted: dict[str, Any] = {"enabled": False}
    warehouse_verification: dict[str, Any] = {}
    analytics_reports: dict[str, str] = {}
    if persist and execute_network and results:
        persisted = {"enabled": True, **persist_layers(results, persist_gold=False)}
        warehouse = persist_warehouse(
            results,
            correlation_id=correlation_id,
            sources=sources,
            source_metrics={source: metric.to_dict() for source, metric in metrics.items()},
            errors=errors,
            manifest_path=str(manifest.path),
        )
        persisted.update(warehouse)
        warehouse_verification = verify_warehouse_counts()
        analytics_reports = write_analytics_reports(warehouse_verification)

    universe = build_labor_market_skill_universe(include_database=persisted.get("enabled", False), write_output=True)
    clusters = build_occupational_skill_clusters(universe, write_output=True)
    gap_map = build_curriculum_market_gap_map(universe=universe, write_output=True)
    intelligence = build_market_skill_intelligence_map(include_database=persisted.get("enabled", False), write_output=True)
    market = {
        "skill_universe": len(universe),
        "occupational_clusters": len(clusters),
        "covered_skills": len(gap_map.covered_skills),
        "missing_skills": len(gap_map.missing_skills),
        "emerging_skills": len(gap_map.emerging_skills),
        "market_skills": len(intelligence.market_skills),
        "warehouse_verification": warehouse_verification,
        "analytics_reports": analytics_reports,
    }
    source_metrics = {source: metric.to_dict() for source, metric in metrics.items()}
    _write_reports(results, errors, persisted, market, source_metrics=source_metrics, correlation_id=correlation_id)
    manifest.checkpoint("market", market)
    manifest.finish()
    logger.log("labor_acquisition_finished", results=len(results), errors=len(errors), market=market)
    return {
        "correlation_id": correlation_id,
        "sources": sources,
        "dry_run": not execute_network,
        "quality_review": quality_review,
        "results": len(results),
        "real_job_postings": sum(1 for item in results if item.silver.document_type == "job_posting"),
        "probable_jobs": sum(1 for item in results if float(getattr(item.silver, "job_probability_score", 0.0) or 0.0) >= 0.30),
        "curated_jobs": sum(1 for item in results if getattr(item.silver, "curation_level", "") in {"curated_job", "gold_job"}),
        "gold_jobs": sum(1 for item in results if getattr(item.silver, "curation_level", "") == "gold_job"),
        "errors": errors,
        "persisted": persisted,
        "market": market,
        "source_metrics": source_metrics,
        "reports": {
            "run": str(OUTPUT_DIR / "labor_acquisition_run_report.md"),
            "quality": str(OUTPUT_DIR / "labor_acquisition_quality_report.json"),
            "failed": str(OUTPUT_DIR / "labor_acquisition_failed_urls.md"),
            "market": str(OUTPUT_DIR / "labor_market_skill_after_acquisition.md"),
            "health": str(OUTPUT_DIR / "labor_acquisition_health_report.json"),
            "manifest": str(manifest.path),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Labor Acquisition Platform.")
    parser.add_argument("--sources", nargs="+", default=["ticjob", "elempleo"])
    parser.add_argument("--max-jobs", type=int, default=20)
    parser.add_argument("--max-pages", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute-network", action="store_true")
    parser.add_argument("--quality-review", action="store_true")
    parser.add_argument("--persist", action="store_true")
    parser.add_argument("--workers", type=int, default=1, help="Controlled worker count. Current implementation keeps source isolation sequential.")
    parser.add_argument("--resume-from", default="", help="Correlation ID of a previous manifest to resume in a future run.")
    args = parser.parse_args()
    execute_network = bool(args.execute_network and not args.dry_run)
    result = run_labor_acquisition(
        sources=args.sources,
        execute_network=execute_network,
        max_jobs=args.max_jobs,
        max_pages=args.max_pages,
        persist=args.persist,
        quality_review=args.quality_review,
        workers=max(1, min(args.workers, 4)),
        resume_from=args.resume_from,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
