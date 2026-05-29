from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from math import ceil
from dataclasses import asdict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from psycopg2.extras import execute_values

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agents.visual_analytics_labor_agent import (  # noqa: E402
    AgentExtractionResult,
    BronzeEvidence,
    GoldEvidence,
    SilverEvidence,
    VisualAnalyticsLaborAgent,
    evidence_to_dict,
)
from backend.db import get_conn  # noqa: E402

OUTPUT_DIR = ROOT_DIR / "outputs"
MIGRATION = ROOT_DIR / "database" / "migrations" / "011_bronze_silver_labor_layers.sql"

SOURCE_URLS = {
    "ticjob": ("Ticjob", "https://ticjob.co/es/search"),
    "elempleo": ("Elempleo", "https://www.elempleo.com/co/ofertas-empleo/"),
}


def load_environment() -> None:
    for name in (".env.local", ".env", ".env.development"):
        path = ROOT_DIR / name
        if path.exists():
            load_dotenv(path, override=False)


def persist_layers(results: list[AgentExtractionResult], *, persist_gold: bool) -> dict[str, int]:
    results = deduplicate_results(results)
    load_environment()
    with get_conn() as conn:
        with conn.cursor() as cur:
            if MIGRATION.exists():
                cur.execute(MIGRATION.read_text(encoding="utf-8"))
            bronze_rows = [
                (
                    r.bronze.source_name,
                    r.bronze.source_url,
                    r.bronze.raw_html,
                    r.bronze.raw_text,
                    json.dumps(r.bronze.raw_json, ensure_ascii=False),
                    r.bronze.extraction_timestamp,
                    r.bronze.page_title,
                    r.bronze.http_status,
                    r.bronze.extraction_method,
                    r.bronze.content_hash,
                    r.bronze.detected_language,
                )
                for r in results
            ]
            if bronze_rows:
                execute_values(
                    cur,
                    """
                    INSERT INTO bronze_empleos_raw
                        (source_name, source_url, raw_html, raw_text, raw_json, extraction_timestamp, page_title,
                         http_status, extraction_method, content_hash, detected_language)
                    VALUES %s
                    ON CONFLICT (content_hash) DO UPDATE SET
                        raw_text = EXCLUDED.raw_text,
                        raw_json = EXCLUDED.raw_json,
                        extraction_timestamp = EXCLUDED.extraction_timestamp
                    RETURNING id, content_hash
                    """,
                    bronze_rows,
                )
            cur.execute("SELECT id, content_hash FROM bronze_empleos_raw WHERE content_hash = ANY(%s)", ([r.bronze.content_hash for r in results],))
            bronze_ids = {row["content_hash"]: row["id"] for row in cur.fetchall()}
            silver_rows = [
                (
                    bronze_ids.get(r.bronze.content_hash),
                    r.silver.source_name,
                    r.silver.source_url,
                    r.silver.normalized_title,
                    r.silver.normalized_company,
                    r.silver.normalized_location,
                    r.silver.normalized_description,
                    json.dumps(r.silver.extracted_skills, ensure_ascii=False),
                    json.dumps(r.silver.extracted_tools, ensure_ascii=False),
                    json.dumps(r.silver.extracted_cloud, ensure_ascii=False),
                    json.dumps(r.silver.extracted_frameworks, ensure_ascii=False),
                    r.silver.analytics_density,
                    r.silver.contextual_relevance_score,
                    r.silver.semantic_score,
                    r.silver.rejection_reason,
                    r.silver.accepted_for_gold,
                    r.silver.parser_version,
                    r.silver.content_hash,
                    r.silver.document_type,
                    r.silver.evidence_source_type,
                    r.silver.is_real_job_posting,
                    r.silver.invalid_job_reason,
                    json.dumps(r.silver.job_evidence_skills or [], ensure_ascii=False),
                    json.dumps(r.silver.portal_taxonomy_skills or [], ensure_ascii=False),
                    r.silver.job_probability_score,
                    r.silver.curation_level,
                    r.silver.semantic_evidence_count,
                    json.dumps(r.silver.top_acceptance_reasons or [], ensure_ascii=False),
                    json.dumps(r.silver.unknown_skill_candidates or [], ensure_ascii=False),
                )
                for r in results
            ]
            if silver_rows:
                execute_values(
                    cur,
                    """
                    INSERT INTO silver_empleos_normalized
                        (bronze_id, source_name, source_url, normalized_title, normalized_company, normalized_location,
                         normalized_description, extracted_skills, extracted_tools, extracted_cloud, extracted_frameworks,
                         analytics_density, contextual_relevance_score, semantic_score, rejection_reason, accepted_for_gold,
                         parser_version, content_hash, document_type, evidence_source_type, is_real_job_posting,
                         invalid_job_reason, job_evidence_skills, portal_taxonomy_skills, job_probability_score,
                         curation_level, semantic_evidence_count, top_acceptance_reasons, unknown_skill_candidates)
                    VALUES %s
                    ON CONFLICT (content_hash) DO UPDATE SET
                        normalized_description = EXCLUDED.normalized_description,
                        extracted_skills = EXCLUDED.extracted_skills,
                        analytics_density = EXCLUDED.analytics_density,
                        contextual_relevance_score = EXCLUDED.contextual_relevance_score,
                        semantic_score = EXCLUDED.semantic_score,
                        rejection_reason = EXCLUDED.rejection_reason,
                        accepted_for_gold = EXCLUDED.accepted_for_gold,
                        document_type = EXCLUDED.document_type,
                        evidence_source_type = EXCLUDED.evidence_source_type,
                        is_real_job_posting = EXCLUDED.is_real_job_posting,
                        invalid_job_reason = EXCLUDED.invalid_job_reason,
                        job_evidence_skills = EXCLUDED.job_evidence_skills,
                        portal_taxonomy_skills = EXCLUDED.portal_taxonomy_skills,
                        job_probability_score = EXCLUDED.job_probability_score,
                        curation_level = EXCLUDED.curation_level,
                        semantic_evidence_count = EXCLUDED.semantic_evidence_count,
                        top_acceptance_reasons = EXCLUDED.top_acceptance_reasons,
                        unknown_skill_candidates = EXCLUDED.unknown_skill_candidates
                    RETURNING id, content_hash
                    """,
                    silver_rows,
                )
            gold_results = [r for r in results if r.gold]
            gold_inserted = 0
            if persist_gold and gold_results:
                cur.execute("SELECT id, content_hash FROM silver_empleos_normalized WHERE content_hash = ANY(%s)", ([r.silver.content_hash for r in gold_results],))
                silver_ids = {row["content_hash"]: row["id"] for row in cur.fetchall()}
                execute_values(
                    cur,
                    """
                    INSERT INTO gold_empleos_analytics
                        (silver_id, curated_title, curated_description, evidence_summary, normalized_skills, market_role,
                         analytics_relevance, ai_confidence, approved_by_agent, approved_timestamp, source_name, source_url, content_hash)
                    VALUES %s
                    ON CONFLICT (content_hash) DO UPDATE SET
                        evidence_summary = EXCLUDED.evidence_summary,
                        analytics_relevance = EXCLUDED.analytics_relevance,
                        ai_confidence = EXCLUDED.ai_confidence,
                        approved_timestamp = EXCLUDED.approved_timestamp
                    """,
                    [
                        (
                            silver_ids.get(r.silver.content_hash),
                            r.gold.curated_title,
                            r.gold.curated_description,
                            r.gold.evidence_summary,
                            json.dumps(r.gold.normalized_skills, ensure_ascii=False),
                            r.gold.market_role,
                            r.gold.analytics_relevance,
                            r.gold.ai_confidence,
                            r.gold.approved_by_agent,
                            r.gold.approved_timestamp,
                            r.gold.source_name,
                            r.gold.source_url,
                            r.gold.content_hash,
                        )
                        for r in gold_results
                        if r.gold
                    ],
                )
                gold_inserted = len(gold_results)
        conn.commit()
    return {"bronze": len(results), "silver": len(results), "gold": gold_inserted}


def deduplicate_results(results: list[AgentExtractionResult]) -> list[AgentExtractionResult]:
    seen: set[str] = set()
    unique: list[AgentExtractionResult] = []
    for result in results:
        if result.bronze.content_hash in seen:
            continue
        seen.add(result.bronze.content_hash)
        unique.append(result)
    return unique


def load_results_from_json(path: Path) -> list[AgentExtractionResult]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    results: list[AgentExtractionResult] = []
    for item in payload:
        results.append(
            AgentExtractionResult(
                bronze=BronzeEvidence(**item["bronze"]),
                silver=SilverEvidence(**item["silver"]),
                gold=GoldEvidence(**item["gold"]) if item.get("gold") else None,
            )
        )
    return results


def run_pipeline(*, execute_browser: bool, sources: list[str], max_jobs: int, persist_bronze_silver: bool, persist_gold: bool) -> dict[str, Any]:
    valid_sources = [source for source in sources if source in SOURCE_URLS]
    jobs_per_source = max(1, ceil(max_jobs / max(len(valid_sources), 1)))
    agent = VisualAnalyticsLaborAgent(headless=True, max_jobs=jobs_per_source)
    results: list[AgentExtractionResult] = []
    errors: list[dict[str, str]] = []
    for source_key in sources:
        if source_key not in SOURCE_URLS:
            errors.append({"source": source_key, "error_type": "unknown_source", "error_message": "source_not_configured"})
            continue
        source_name, source_url = SOURCE_URLS[source_key]
        if not execute_browser:
            continue
        try:
            results.extend(agent.run_source(source_name=source_name, source_url=source_url))
        except Exception as exc:  # pragma: no cover - live browser depends on environment
            errors.append({"source": source_name, "error_type": type(exc).__name__, "error_message": str(exc)[:500]})

    results = deduplicate_results(results)
    persisted = {"bronze": 0, "silver": 0, "gold": 0}
    if persist_bronze_silver and results:
        persisted = persist_layers(results, persist_gold=persist_gold)
    report = build_report(results, errors, persisted)
    write_outputs(results, report)
    return report


def build_report(results: list[AgentExtractionResult], errors: list[dict[str, str]], persisted: dict[str, int]) -> dict[str, Any]:
    gold = [result for result in results if result.gold]
    gold_a = [result for result in results if result.silver.contextual.get("hybrid_tier") == "Gold A"]
    gold_b = [result for result in results if result.silver.contextual.get("hybrid_tier") == "Gold B"]
    recovered = [result for result in results if result.silver.contextual_relevance_score >= 0.50]
    signal_counts = Counter(signal for result in results for signal in result.silver.contextual.get("detected_signals", []))
    skill_counts = Counter(skill for result in results for skill in result.silver.extracted_skills)
    role_counts = Counter(str(result.silver.contextual.get("hybrid_career_family") or result.silver.contextual.get("role_class", "")) for result in results)
    hybrid_role_counts = Counter(str(result.silver.contextual.get("hybrid_tier", "")) for result in results)
    document_type_counts = Counter(result.silver.document_type for result in results)
    blocked_taxonomy_skills = Counter(skill for result in results for skill in (result.silver.portal_taxonomy_skills or []))
    job_evidence_skill_counts = Counter(skill for result in results for skill in (result.silver.job_evidence_skills or []))
    return {
        "results": len(results),
        "bronze_records": len(results),
        "silver_records": len(results),
        "gold_candidates": len(gold),
        "gold_a": len(gold_a),
        "gold_b": len(gold_b),
        "rejected": len([result for result in results if not result.silver.accepted_for_gold]),
        "contextual_recovered": len(recovered),
        "hybrid_roles_accepted": role_counts.most_common(20),
        "hybrid_tiers": hybrid_role_counts.most_common(10),
        "top_skills": skill_counts.most_common(20),
        "job_evidence_skills": job_evidence_skill_counts.most_common(20),
        "blocked_taxonomy_skills": blocked_taxonomy_skills.most_common(20),
        "document_types": document_type_counts.most_common(10),
        "persisted": persisted,
        "top_signals": signal_counts.most_common(20),
        "errors": errors,
    }


def write_outputs(results: list[AgentExtractionResult], report: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "agentic_labor_extraction_results.json").write_text(
        json.dumps([evidence_to_dict(result) for result in results], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    lines = [
        "# Agentic Labor Extraction Report",
        "",
        f"- Bronze records: {report['bronze_records']}",
        f"- Silver records: {report['silver_records']}",
        f"- Gold candidates: {report['gold_candidates']}",
        f"- Gold A: {report['gold_a']}",
        f"- Gold B: {report['gold_b']}",
        f"- Rejected: {report['rejected']}",
        f"- Contextual recovered: {report['contextual_recovered']}",
        f"- Persisted: {report['persisted']}",
        "",
        "## Top Analytics Signals",
    ]
    lines.extend([f"- {signal}: {count}" for signal, count in report["top_signals"]] or ["- Sin senales detectadas."])
    lines.extend(["", "## Top Skills"])
    lines.extend([f"- {skill}: {count}" for skill, count in report["top_skills"]] or ["- Sin skills detectadas."])
    lines.extend(["", "## Document Types"])
    lines.extend([f"- {doctype}: {count}" for doctype, count in report["document_types"]] or ["- Sin documentos clasificados."])
    lines.extend(["", "## Job Evidence Skills"])
    lines.extend([f"- {skill}: {count}" for skill, count in report["job_evidence_skills"]] or ["- Sin skills de vacante real."])
    lines.extend(["", "## Portal Taxonomy Skills Blocked"])
    lines.extend([f"- {skill}: {count}" for skill, count in report["blocked_taxonomy_skills"]] or ["- Sin skills bloqueadas por taxonomia."])
    lines.extend(["", "## Tiers Hibridos"])
    lines.extend([f"- {tier or 'unknown'}: {count}" for tier, count in report["hybrid_tiers"]] or ["- Sin tiers detectados."])
    lines.extend(["", "## Vacantes Evaluadas"])
    for result in results:
        lines.extend(
            [
                f"### {result.silver.normalized_title or result.bronze.page_title}",
                f"- Fuente: {result.silver.source_name}",
                f"- Contextual relevance: {result.silver.contextual_relevance_score}",
                f"- Analytics density: {result.silver.analytics_density}",
                f"- Semantic score: {result.silver.semantic_score}",
                f"- Final semantic relevance: {result.silver.contextual.get('final_semantic_relevance_score')}",
                f"- Curriculum alignment: {result.silver.contextual.get('curriculum_alignment_score')}",
                f"- Gold score: {result.silver.contextual.get('gold_score')}",
                f"- Curriculum tier: {result.silver.contextual.get('curriculum_gold_tier')}",
                f"- Gold tier: {result.silver.contextual.get('hybrid_tier')}",
                f"- Accepted by hybrid: {result.silver.contextual.get('accepted_by_hybrid')}",
                f"- Market gaps: {json.dumps(result.silver.contextual.get('market_gap_signal', []), ensure_ascii=False)}",
                f"- Cluster signals: {json.dumps(result.silver.contextual.get('cluster_signals', {}), ensure_ascii=False)}",
                f"- Gold approved: {bool(result.gold)}",
                f"- Document type: {result.silver.document_type}",
                f"- Real job posting: {result.silver.is_real_job_posting}",
                f"- Invalid reason: {result.silver.invalid_job_reason}",
                f"- Job evidence skills: {json.dumps(result.silver.job_evidence_skills or [], ensure_ascii=False)}",
                f"- Portal taxonomy skills blocked: {json.dumps(result.silver.portal_taxonomy_skills or [], ensure_ascii=False)}",
                f"- Reason: {result.silver.rejection_reason}",
            ]
        )
        if result.gold:
            lines.append(f"- Evidence: {result.gold.evidence_summary}")
        elif result.silver.contextual.get("contextual_evidence"):
            lines.append(f"- Evidence: {result.silver.contextual.get('contextual_evidence')}")
    lines.extend(["", "## Errors"])
    lines.extend([f"- {item['source']}: {item['error_type']} - {item['error_message']}" for item in report["errors"]] or ["- Sin errores."])
    (OUTPUT_DIR / "agentic_labor_extraction_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "agentic_labor_hybrid_engine_validation.md").write_text(
        "\n".join(
            [
                "# Agentic Labor Hybrid Engine Validation",
                "",
                "## Comparacion Modelo Anterior vs Hibrido",
                "",
                "- Antes reportado: Bronze 6, Silver 6, Gold 0, Contextual recovered 4.",
                f"- Despues: Bronze {report['bronze_records']}, Silver {report['silver_records']}, Gold A {report['gold_a']}, Gold B {report['gold_b']}, Rejected {report['rejected']}, Contextual recovered {report['contextual_recovered']}.",
                "",
                "## Skills Frecuentes",
                *([f"- {skill}: {count}" for skill, count in report["top_skills"]] or ["- Sin skills detectadas."]),
                "",
                "## Tipos de Documento",
                *([f"- {doctype}: {count}" for doctype, count in report["document_types"]] or ["- Sin documentos clasificados."]),
                "",
                "## Skills validas de vacantes reales",
                *([f"- {skill}: {count}" for skill, count in report["job_evidence_skills"]] or ["- Sin skills de vacante real."]),
                "",
                "## Skills descartadas por venir de taxonomia/filtros",
                *([f"- {skill}: {count}" for skill, count in report["blocked_taxonomy_skills"]] or ["- Sin skills bloqueadas por taxonomia."]),
                "",
                "## Tiers Hibridos",
                *([f"- {tier or 'unknown'}: {count}" for tier, count in report["hybrid_tiers"]] or ["- Sin tiers detectados."]),
                "",
                "## Vacantes Recuperadas y Evidencia",
                *[
                    "\n".join(
                        [
                            f"### {result.silver.normalized_title or result.bronze.page_title}",
                            f"- Fuente: {result.silver.source_name}",
                            f"- Score final: {result.silver.contextual.get('final_semantic_relevance_score')}",
                            f"- Curriculum alignment: {result.silver.contextual.get('curriculum_alignment_score')}",
                            f"- Gold score: {result.silver.contextual.get('gold_score')}",
                            f"- Curriculum tier: {result.silver.contextual.get('curriculum_gold_tier')}",
                            f"- Gold tier: {result.silver.contextual.get('hybrid_tier')}",
                            f"- Aprobada Gold: {bool(result.gold)}",
                            f"- Document type: {result.silver.document_type}",
                            f"- Real job posting: {result.silver.is_real_job_posting}",
                            f"- Invalid reason: {result.silver.invalid_job_reason}",
                            f"- Job evidence skills: {json.dumps(result.silver.job_evidence_skills or [], ensure_ascii=False)}",
                            f"- Portal taxonomy skills blocked: {json.dumps(result.silver.portal_taxonomy_skills or [], ensure_ascii=False)}",
                            f"- Clusters: {json.dumps(result.silver.contextual.get('cluster_signals', {}), ensure_ascii=False)}",
                            f"- Gaps mercado: {json.dumps(result.silver.contextual.get('market_gap_signal', []), ensure_ascii=False)}",
                            f"- Alineacion curricular: {result.silver.contextual.get('curriculum_explanation')}",
                            f"- Evidencia: {result.silver.contextual.get('contextual_evidence') or (result.gold.evidence_summary if result.gold else '')}",
                            f"- Motivo: {result.silver.rejection_reason}",
                        ]
                    )
                    for result in results
                ],
                "",
                "## Recomendaciones de Calibracion",
                "- Mantener Helpdesk/Networking puro bloqueado por senales negativas.",
                "- Revisar manualmente Gold B antes de alimentar KPIs institucionales.",
                "- Priorizar detail pages con descripcion completa para mejorar evidencia contextual.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run agentic labor intelligence pipeline.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute-browser", action="store_true")
    parser.add_argument("--execute-network", action="store_true", help="Alias for --execute-browser.")
    parser.add_argument("--sources", nargs="+", default=["ticjob", "elempleo"])
    parser.add_argument("--max-pages", type=int, default=2, help="Accepted for compatibility; browser agent uses source discovery limits.")
    parser.add_argument("--max-jobs", type=int, default=8)
    parser.add_argument("--quality-review", action="store_true", help="Run extraction and reports without persistence.")
    parser.add_argument("--persist", action="store_true", help="Persist Bronze/Silver and approved Gold rows.")
    parser.add_argument("--persist-approved-gold-from-results", action="store_true", help="Persist only previously reviewed Gold rows from outputs JSON.")
    parser.add_argument("--persist-bronze-silver", action="store_true")
    parser.add_argument("--persist-gold", action="store_true")
    args = parser.parse_args()
    if args.persist_approved_gold_from_results:
        reviewed = [result for result in load_results_from_json(OUTPUT_DIR / "agentic_labor_extraction_results.json") if result.gold]
        persisted = persist_layers(reviewed, persist_gold=True) if reviewed else {"bronze": 0, "silver": 0, "gold": 0}
        report = build_report(reviewed, [], persisted)
        write_outputs(reviewed, report)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    report = run_pipeline(
        execute_browser=(args.execute_browser or args.execute_network) and not args.dry_run,
        sources=args.sources,
        max_jobs=args.max_jobs,
        persist_bronze_silver=(args.persist or args.persist_bronze_silver) and not args.dry_run and not args.quality_review,
        persist_gold=(args.persist or args.persist_gold) and not args.dry_run and not args.quality_review,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
