from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipelines.extract_visual_analytics_jobs import ExtractedJob, LaborSource, upsert_sources_and_jobs  # noqa: E402
from ml.relevance.contextual_job_relevance_engine import result_to_dict, score_contextual_relevance  # noqa: E402
from scrapers.connectors.base import (  # noqa: E402
    BaseJobConnector,
    ConnectorJob,
    deduplicate_jobs,
    is_visual_analytics_related,
    job_relevance_score,
    normalize_text,
)
from scrapers.connectors.elempleo_connector import ElempleoConnector  # noqa: E402
from scrapers.connectors.findjobit_connector import FindJobITConnector  # noqa: E402
from scrapers.connectors.hireline_connector import HirelineConnector  # noqa: E402
from scrapers.connectors.mi_futuro_empleo_connector import MiFuturoEmpleoConnector  # noqa: E402
from scrapers.connectors.servicio_publico_empleo_connector import ServicioPublicoEmpleoConnector  # noqa: E402
from scrapers.connectors.ticjob_connector import TicjobConnector  # noqa: E402

OUTPUT_DIR = ROOT_DIR / "outputs"
QUALITY_THRESHOLD = 0.75
JOB_THRESHOLD = 0.65
CONTEXTUAL_JOB_THRESHOLD = 0.50

CONNECTOR_CLASSES: tuple[type[BaseJobConnector], ...] = (
    TicjobConnector,
    ElempleoConnector,
    HirelineConnector,
    ServicioPublicoEmpleoConnector,
    MiFuturoEmpleoConnector,
    FindJobITConnector,
)


def load_environment() -> None:
    for name in (".env.local", ".env", ".env.development"):
        path = ROOT_DIR / name
        if path.exists():
            load_dotenv(path, override=False)


def build_connectors(max_pages: int, max_jobs: int) -> list[BaseJobConnector]:
    return [cls(max_pages=max_pages, max_jobs=max_jobs) for cls in CONNECTOR_CLASSES]


def classify_and_filter(jobs: list[ConnectorJob], connector: BaseJobConnector) -> tuple[list[ConnectorJob], list[dict[str, str]]]:
    accepted: list[ConnectorJob] = []
    discarded: list[dict[str, str]] = []
    for job in jobs:
        contextual = score_contextual_relevance(
            title=job.title,
            description=job.description,
            tags=job.tags,
            skills=job.skills,
            technologies=job.technologies,
        )
        job.raw["contextual_relevance"] = result_to_dict(contextual)
        keep, reason = is_visual_analytics_related(job)
        score = job_relevance_score(job, source_priority=connector.priority)
        combined_score = max(score, contextual.contextual_relevance_score)
        contextual_recovered = (not keep or score < JOB_THRESHOLD) and contextual.accepted and combined_score >= CONTEXTUAL_JOB_THRESHOLD
        if not keep and not contextual_recovered:
            discarded.append({"source": job.source_name, "title": job.title, "reason": reason, "score": f"{score:.4f}", "contextual_score": f"{contextual.contextual_relevance_score:.4f}"})
            continue
        if score < JOB_THRESHOLD and not contextual_recovered:
            discarded.append({"source": job.source_name, "title": job.title, "reason": "below_job_relevance_threshold", "score": f"{score:.4f}", "contextual_score": f"{contextual.contextual_relevance_score:.4f}"})
            continue
        job.raw["contextual_recovered"] = contextual_recovered
        job.raw["final_acceptance_score"] = combined_score
        accepted.append(job)
    return accepted, discarded


def connector_to_source(connector: BaseJobConnector) -> LaborSource:
    return LaborSource(
        name=connector.source_name,
        url=connector.base_url,
        country="Colombia",
        priority=connector.priority,
        source_type="source_specific_connector",
        access_mode="connector_api_or_structured_html",
        enabled=True,
        rate_limit_seconds=connector.config.rate_limit_seconds,
        max_pages=connector.config.max_pages,
        max_jobs=connector.config.max_jobs,
        allowed_paths=["/"],
        blocked_reason=None,
    )


def to_extracted_job(job: ConnectorJob, score: float) -> ExtractedJob:
    contextual = job.raw.get("contextual_relevance", {})
    final_score = max(score, float(contextual.get("contextual_relevance_score", 0) or 0))
    return ExtractedJob(
        portal=job.source_name,
        titulo=job.title,
        empresa=job.company,
        ciudad=job.location,
        modalidad=job.modality,
        salario=job.salary,
        descripcion=job.description,
        seniority=job.seniority,
        sector="tecnologia_datos_analitica",
        dominio="analitica_visual_big_data",
        fecha_publicacion=job.publication_date or None,
        url=job.source_url,
        role_class=classify_role(job),
        job_relevance_score=round(final_score, 4),
        skills=job.skills,
        raw=job.to_dict(),
    )


def classify_role(job: ConnectorJob) -> str:
    text = normalize_text(f"{job.title} {job.description} {' '.join(job.skills)}")
    if any(term in text for term in ("data engineer", "ingeniero de datos", "etl", "spark", "lakehouse")):
        return "data_engineer"
    if any(term in text for term in ("power bi", "tableau", "dashboard", "visualizacion", "visualization")):
        return "bi_visualization"
    if any(term in text for term in ("analista bi", "bi analyst", "business intelligence")):
        return "bi_analyst"
    if any(term in text for term in ("analista de datos", "data analyst")):
        return "data_analyst"
    return "analytics_related"


def calculate_final_quality(jobs: list[ConnectorJob], discarded: list[dict[str, str]], errors: list[dict[str, str]], connector_count: int) -> float:
    accepted = len(jobs)
    reviewed = accepted + len(discarded)
    relevance_rate = accepted / reviewed if reviewed else 0.0
    avg_score = sum(float(job.raw.get("final_acceptance_score") or job_relevance_score(job)) for job in jobs) / accepted if accepted else 0.0
    skill_density = sum(len(job.skills) for job in jobs) / max(accepted * 5, 1) if accepted else 0.0
    successful_sources = len({job.source_name for job in jobs})
    source_coverage = successful_sources / max(connector_count, 1)
    hard_errors = [error for error in errors if error["error_type"] not in {"dry_run"}]
    stability = 1 - min(len(hard_errors) / max(connector_count, 1), 1)
    return round(relevance_rate * 0.25 + avg_score * 0.30 + min(skill_density, 1.0) * 0.20 + source_coverage * 0.15 + stability * 0.10, 4)


def run_connectors(*, execute_network: bool, max_pages: int, max_jobs: int, persist: bool) -> dict[str, Any]:
    run_id = f"va-connectors-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    connectors = build_connectors(max_pages=max_pages, max_jobs=max_jobs)
    all_jobs: list[ConnectorJob] = []
    discarded: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    source_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"raw": 0, "accepted": 0, "discarded": 0, "errors": 0})

    for connector in connectors:
        raw_jobs, connector_errors = connector.fetch_jobs(execute_network=execute_network)
        source_stats[connector.source_name]["raw"] += len(raw_jobs)
        source_stats[connector.source_name]["errors"] += len(connector_errors)
        errors.extend(connector_errors)
        accepted, rejected = classify_and_filter(raw_jobs, connector)
        source_stats[connector.source_name]["accepted"] += len(accepted)
        source_stats[connector.source_name]["discarded"] += len(rejected)
        all_jobs.extend(accepted)
        discarded.extend(rejected)

    before = len(all_jobs)
    unique_jobs = deduplicate_jobs(all_jobs)
    duplicates = before - len(unique_jobs)
    final_quality = calculate_final_quality(unique_jobs, discarded, errors, len(connectors))
    publishable = final_quality >= QUALITY_THRESHOLD

    extracted_jobs = [to_extracted_job(job, job_relevance_score(job)) for job in unique_jobs]
    if persist and not publishable:
        errors.append(
            {
                "source": "quality_gate",
                "error_type": "persist_blocked",
                "error_message": f"final_quality_score {final_quality:.4f} below {QUALITY_THRESHOLD:.2f}",
            }
        )
    elif persist and publishable:
        load_environment()
        upsert_sources_and_jobs(run_id, [connector_to_source(connector) for connector in connectors], extracted_jobs, errors)

    result = {
        "run_id": run_id,
        "execute_network": execute_network,
        "persist_requested": persist,
        "persisted": bool(persist and publishable),
        "final_quality_score": final_quality,
        "quality_threshold": QUALITY_THRESHOLD,
        "publishable": publishable,
        "jobs_extracted": len(unique_jobs),
        "jobs_discarded": len(discarded),
        "duplicates": duplicates,
        "source_stats": dict(source_stats),
        "discard_reasons": discarded,
        "errors": errors,
        "jobs": [job.to_dict() for job in unique_jobs],
    }
    write_reports(result)
    return result


def write_reports(result: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    quality_path = OUTPUT_DIR / "visual_analytics_sources_quality_report.json"
    quality_path.write_text(json.dumps({k: v for k, v in result.items() if k != "jobs"}, indent=2, ensure_ascii=False), encoding="utf-8")

    skill_counts = Counter(skill for job in result["jobs"] for skill in job.get("skills", []))
    role_counts = Counter(classify_role_from_dict(job) for job in result["jobs"])
    recovered = [job for job in result["jobs"] if job.get("raw", {}).get("contextual_recovered")]
    lines = [
        "# Visual Analytics Sources Extraction Report",
        "",
        f"- Run ID: `{result['run_id']}`",
        f"- Extraccion con red: {result['execute_network']}",
        f"- Empleos aceptados: {result['jobs_extracted']}",
        f"- Empleos descartados: {result['jobs_discarded']}",
        f"- Duplicados: {result['duplicates']}",
        f"- Final quality score: {result['final_quality_score']:.4f}",
        f"- Umbral Gold: {result['quality_threshold']:.2f}",
        f"- Persistido: {result['persisted']}",
        f"- Vacantes recuperadas por parsing contextual: {len(recovered)}",
        "",
        "## Fuentes",
    ]
    for source, stats in result["source_stats"].items():
        lines.append(f"- {source}: raw={stats['raw']}, accepted={stats['accepted']}, discarded={stats['discarded']}, errors={stats['errors']}")
    lines.extend(["", "## Razones De Descarte"])
    reason_counts = Counter(item["reason"] for item in result["discard_reasons"])
    lines.extend([f"- {reason}: {count}" for reason, count in reason_counts.items()] or ["- Sin descartes."])
    lines.extend(["", "## Skills Extraidas"])
    lines.extend([f"- {skill}: {count}" for skill, count in skill_counts.most_common(20)] or ["- Sin skills aceptadas."])
    lines.extend(["", "## Roles Detectados"])
    lines.extend([f"- {role}: {count}" for role, count in role_counts.most_common(20)] or ["- Sin roles aceptados."])
    lines.extend(["", "## Errores"])
    lines.extend([f"- {error['source']}: {error['error_type']} - {error['error_message']}" for error in result["errors"]] or ["- Sin errores."])
    (OUTPUT_DIR / "visual_analytics_sources_extraction_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    deep_lines = [
        "# Deep Vacancy Parsing Report",
        "",
        f"- Run ID: `{result['run_id']}`",
        f"- Vacantes aceptadas: {result['jobs_extracted']}",
        f"- Recuperadas por contexto: {len(recovered)}",
        f"- Final quality score: {result['final_quality_score']:.4f}",
        "",
        "## Vacantes Aceptadas Y Senales",
    ]
    for job in result["jobs"]:
        contextual = job.get("raw", {}).get("contextual_relevance", {})
        deep_lines.extend(
            [
                f"### {job.get('title', '')}",
                f"- Fuente: {job.get('source_name', '')}",
                f"- Score contextual: {contextual.get('contextual_relevance_score', 0)}",
                f"- Rol reclasificado: {contextual.get('role_class', '')}",
                f"- Analytics density: {contextual.get('analytics_density', 0)}",
                f"- BI density: {contextual.get('bi_density', 0)}",
                f"- Data engineering density: {contextual.get('data_engineering_density', 0)}",
                f"- Stack: {', '.join(contextual.get('detected_stack', [])) or 'No detectado'}",
                f"- Senales: {', '.join(contextual.get('detected_signals', [])) or 'No detectadas'}",
            ]
        )
    if not result["jobs"]:
        deep_lines.append("- No hubo vacantes aceptadas.")
    deep_lines.extend(["", "## Rechazos Principales"])
    for item in result["discard_reasons"][:40]:
        deep_lines.append(f"- {item['source']} | {item['title']} | {item['reason']} | score={item.get('score')} | contextual={item.get('contextual_score')}")
    (OUTPUT_DIR / "deep_vacancy_parsing_report.md").write_text("\n".join(deep_lines) + "\n", encoding="utf-8")


def classify_role_from_dict(job: dict[str, Any]) -> str:
    fake = ConnectorJob(
        title=job.get("title", ""),
        company=job.get("company", ""),
        location=job.get("location", ""),
        publication_date=job.get("publication_date", ""),
        description=job.get("description", ""),
        tags=job.get("tags", []),
        skills=job.get("skills", []),
        technologies=job.get("technologies", []),
        seniority=job.get("seniority", ""),
        modality=job.get("modality", ""),
        salary=job.get("salary", ""),
        source_url=job.get("source_url", ""),
        source_name=job.get("source_name", ""),
        raw=job.get("raw", {}),
    )
    return classify_role(fake)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run source-specific Visual Analytics job connectors.")
    parser.add_argument("--dry-run", action="store_true", help="Validate connectors without network or persistence.")
    parser.add_argument("--execute-network", action="store_true", help="Execute live network extraction.")
    parser.add_argument("--max-pages", type=int, default=2)
    parser.add_argument("--max-jobs", type=int, default=50)
    parser.add_argument("--quality-review", action="store_true", help="Generate quality report. Always enabled.")
    parser.add_argument("--persist", action="store_true", help="Persist only if final quality gate passes.")
    args = parser.parse_args()
    result = run_connectors(
        execute_network=args.execute_network and not args.dry_run,
        max_pages=args.max_pages,
        max_jobs=args.max_jobs,
        persist=args.persist and not args.dry_run,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "jobs"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
