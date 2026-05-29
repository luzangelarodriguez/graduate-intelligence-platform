from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from psycopg2.extras import Json, execute_values

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.db import get_conn  # noqa: E402
from crawlers.storage.postgres_warehouse import load_environment  # noqa: E402

MIGRATIONS = [
    ROOT_DIR / "database" / "migrations" / "015_labor_acquisition_warehouse.sql",
    ROOT_DIR / "database" / "migrations" / "016_labor_intelligence_enrichment.sql",
    ROOT_DIR / "database" / "migrations" / "017_labor_intelligence_qa_feedback.sql",
    ROOT_DIR / "database" / "migrations" / "018_labor_curriculum_intelligence.sql",
    ROOT_DIR / "database" / "migrations" / "019_labor_observatory_layer.sql",
]
QA_DIR = ROOT_DIR / "outputs" / "qa"
ANALYTICS_DIR = ROOT_DIR / "outputs" / "analytics"
MODEL_METADATA_PATH = ROOT_DIR / "ml" / "models" / "curriculum_ml_metadata.json"
JOB_SAMPLE_CSV = QA_DIR / "job_quality_sample.csv"
JOB_SAMPLE_MD = QA_DIR / "job_quality_sample.md"
COMPANY_AUDIT_MD = ANALYTICS_DIR / "company_cleanup_audit.md"
DEDUP_QA_MD = ANALYTICS_DIR / "deduplication_qa_report.md"
GUARDRAIL_REPORT_MD = ROOT_DIR / "outputs" / "ml_model_guardrail_report.md"


def _apply_migrations(cur: Any) -> None:
    for migration in MIGRATIONS:
        if migration.exists():
            cur.execute(migration.read_text(encoding="utf-8"))


def _qa_flags(row: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    company = str(row.get("company") or "")
    title = str(row.get("title") or "")
    if not company or company.casefold() == "no especificada":
        flags.append("company_missing")
    if len(company) > 90 or any(token in company.casefold() for token in ("rol:", "requisitos:", "responsabilidades:")):
        flags.append("company_looks_like_description")
    if not title or len(title) < 4:
        flags.append("title_weak")
    if float(row.get("job_probability_score") or 0) < 0.30:
        flags.append("low_probability")
    if float(row.get("completeness_score") or 0) < 0.50:
        flags.append("low_completeness")
    if row.get("duplicate_group_id"):
        flags.append("duplicate_group_tracked")
    return flags


def _parse_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    text = str(value).strip().casefold()
    if not text:
        return None
    if text in {"1", "true", "yes", "y", "si", "sí", "accept", "accepted", "aceptar", "aceptado"}:
        return True
    if text in {"0", "false", "no", "n", "reject", "rejected", "rechazar", "rechazado"}:
        return False
    return None


def fetch_job_quality_sample(sample_size: int = 50) -> list[dict[str, Any]]:
    load_environment()
    with get_conn() as conn:
        with conn.cursor() as cur:
            _apply_migrations(cur)
            cur.execute(
                """
                SELECT
                    j.id,
                    j.source,
                    j.title,
                    j.company,
                    j.normalized_company,
                    j.location,
                    j.modality,
                    j.seniority,
                    j.curation_level,
                    j.job_probability_score,
                    j.completeness_score,
                    j.extraction_confidence,
                    j.duplicate_group_id,
                    j.canonical_job_id,
                    COALESCE(
                        array_agg(js.canonical_skill ORDER BY js.confidence DESC)
                            FILTER (WHERE js.canonical_skill IS NOT NULL),
                        ARRAY[]::TEXT[]
                    ) AS top_skills
                FROM jobs j
                LEFT JOIN job_skills js ON js.job_id = j.id
                GROUP BY j.id
                ORDER BY
                    CASE WHEN j.company = 'No especificada' THEN 0 ELSE 1 END ASC,
                    j.job_probability_score DESC NULLS LAST,
                    j.updated_at DESC NULLS LAST,
                    j.created_at DESC
                LIMIT %s
                """,
                (sample_size,),
            )
            rows = [dict(row) for row in cur.fetchall()]
            conn.commit()
    for row in rows:
        row["qa_flags"] = _qa_flags(row)
        row["top_skills"] = list(row.get("top_skills") or [])[:8]
    return rows


def write_job_quality_sample(rows: list[dict[str, Any]]) -> None:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    headers = [
        "job_id",
        "source",
        "title",
        "company",
        "location",
        "modality",
        "seniority",
        "curation_level",
        "job_probability_score",
        "completeness_score",
        "duplicate_group_id",
        "top_skills",
        "qa_flags",
        "human_decision",
        "corrected_company",
        "corrected_role",
        "notes",
        "recommendation_acceptance",
        "recommendation_rejection_reason",
        "curriculum_gap_override",
        "company_resolution_override",
        "semantic_role_override",
    ]
    with JOB_SAMPLE_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "job_id": row["id"],
                    "source": row.get("source", ""),
                    "title": row.get("title", ""),
                    "company": row.get("company", ""),
                    "location": row.get("location", ""),
                    "modality": row.get("modality", ""),
                    "seniority": row.get("seniority", ""),
                    "curation_level": row.get("curation_level", ""),
                    "job_probability_score": row.get("job_probability_score", ""),
                    "completeness_score": row.get("completeness_score", ""),
                    "duplicate_group_id": row.get("duplicate_group_id", ""),
                    "top_skills": "; ".join(row.get("top_skills") or []),
                    "qa_flags": "; ".join(row.get("qa_flags") or []),
                    "human_decision": "",
                    "corrected_company": "",
                    "corrected_role": "",
                    "notes": "",
                    "recommendation_acceptance": "",
                    "recommendation_rejection_reason": "",
                    "curriculum_gap_override": "",
                    "company_resolution_override": "",
                    "semantic_role_override": "",
                }
            )
    lines = [
        "# Job Quality Sample",
        "",
        f"- Registros muestreados: {len(rows)}",
        "- Uso: completar `human_decision`, `corrected_company`, `corrected_role` y `notes` en el CSV para retroalimentación humana.",
        "",
        "| Job | Empresa | Nivel | Prob. | Flags | Skills |",
        "|---|---|---:|---:|---|---|",
    ]
    for row in rows[:30]:
        lines.append(
            "| {job} | {company} | {level} | {score} | {flags} | {skills} |".format(
                job=str(row.get("title") or "")[:70],
                company=str(row.get("company") or "")[:45],
                level=row.get("curation_level") or "",
                score=row.get("job_probability_score") or "",
                flags=", ".join(row.get("qa_flags") or []),
                skills=", ".join((row.get("top_skills") or [])[:5]),
            )
        )
    JOB_SAMPLE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_company_cleanup_audit() -> dict[str, Any]:
    load_environment()
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        with conn.cursor() as cur:
            _apply_migrations(cur)
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_jobs,
                    COUNT(*) FILTER (WHERE company = 'No especificada' OR company IS NULL OR company = '') AS missing_company,
                    COUNT(*) FILTER (WHERE char_length(company) > 90 OR company ~* '(rol:|requisitos:|responsabilidades:)') AS suspicious_company
                FROM jobs
                """
            )
            summary = dict(cur.fetchone())
            cur.execute(
                """
                SELECT company, COUNT(*) AS count
                FROM jobs
                GROUP BY company
                ORDER BY count DESC, company
                LIMIT 25
                """
            )
            companies = [dict(row) for row in cur.fetchall()]
            conn.commit()
    lines = [
        "# Company Cleanup Audit",
        "",
        f"- Jobs totales: {summary.get('total_jobs', 0)}",
        f"- Empresa no especificada: {summary.get('missing_company', 0)}",
        f"- Empresas sospechosas por longitud/patrón: {summary.get('suspicious_company', 0)}",
        "",
        "## Distribución de empresas",
        "",
        *[f"- {row['company']}: {row['count']}" for row in companies],
    ]
    COMPANY_AUDIT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"summary": summary, "companies": companies}


def write_deduplication_qa_report() -> dict[str, Any]:
    load_environment()
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        with conn.cursor() as cur:
            _apply_migrations(cur)
            cur.execute(
                """
                SELECT
                    duplicate_group_id,
                    COUNT(*) AS jobs,
                    MIN(canonical_job_id) AS canonical_job_id,
                    array_agg(DISTINCT source) AS sources,
                    array_agg(DISTINCT company) AS companies
                FROM jobs
                WHERE duplicate_group_id IS NOT NULL
                GROUP BY duplicate_group_id
                HAVING COUNT(*) > 1
                ORDER BY jobs DESC
                LIMIT 30
                """
            )
            groups = [dict(row) for row in cur.fetchall()]
            conn.commit()
    lines = [
        "# Deduplication QA Report",
        "",
        f"- Grupos duplicados revisables: {len(groups)}",
        "- La deduplicación conserva evidencia multi-fuente y solo asigna canonical_job_id.",
        "",
    ]
    for row in groups:
        lines.extend(
            [
                f"## {row['duplicate_group_id']}",
                f"- Jobs en grupo: {row['jobs']}",
                f"- Canonical job id: {row['canonical_job_id']}",
                f"- Fuentes: {', '.join(row.get('sources') or [])}",
                f"- Empresas: {', '.join(row.get('companies') or [])}",
                "",
            ]
        )
    DEDUP_QA_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"groups": groups}


def write_ml_model_guardrail_report() -> dict[str, Any]:
    metadata = json.loads(MODEL_METADATA_PATH.read_text(encoding="utf-8")) if MODEL_METADATA_PATH.exists() else {}
    metrics = metadata.get("metrics", {})
    rows = int(metrics.get("rows") or 0)
    classes = metrics.get("classes") or []
    status = "pass"
    warnings: list[str] = []
    if rows < 50:
        status = "warning"
        warnings.append("dataset_below_50_rows")
    if len(classes) < 2:
        status = "warning"
        warnings.append("single_class_training")
    if metrics.get("accuracy") == 1.0 and rows < 500:
        warnings.append("perfect_metrics_on_small_dataset_review_required")
    if not metrics.get("weighted_training"):
        status = "warning"
        warnings.append("training_weights_disabled")
    lines = [
        "# ML Model Guardrail Report",
        "",
        f"- Estado: {status}",
        f"- Filas dataset: {rows}",
        f"- Clases: {', '.join(map(str, classes))}",
        f"- Accuracy: {metrics.get('accuracy', 'N/A')}",
        f"- F1 macro: {metrics.get('f1_macro', 'N/A')}",
        f"- Probability outputs: {metrics.get('probability_outputs', False)}",
        f"- Weighted training: {metrics.get('weighted_training', False)}",
        "",
        "## Alertas",
        "",
        *([f"- {warning}" for warning in warnings] or ["- Sin alertas críticas."]),
    ]
    GUARDRAIL_REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": status, "warnings": warnings, "metrics": metrics}


def persist_qa_run(rows: list[dict[str, Any]], guardrail: dict[str, Any]) -> str:
    correlation_id = "qa-" + datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    suspicious = sum(1 for row in rows if "company_looks_like_description" in row.get("qa_flags", []))
    duplicate_groups = len({row.get("duplicate_group_id") for row in rows if row.get("duplicate_group_id")})
    load_environment()
    with get_conn() as conn:
        with conn.cursor() as cur:
            _apply_migrations(cur)
            cur.execute(
                """
                INSERT INTO labor_qa_audit_runs
                    (correlation_id, sample_size, sampled_jobs, suspicious_companies, duplicate_groups, guardrail_status, report_payload)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (correlation_id) DO UPDATE SET report_payload = EXCLUDED.report_payload
                RETURNING id
                """,
                (
                    correlation_id,
                    len(rows),
                    len(rows),
                    suspicious,
                    duplicate_groups,
                    guardrail.get("status", "unknown"),
                    Json({"guardrail": guardrail}),
                ),
            )
            audit_run_id = int(cur.fetchone()["id"])
            sample_rows = [
                (
                    audit_run_id,
                    int(row["id"]),
                    row.get("source"),
                    row.get("title"),
                    row.get("company"),
                    row.get("curation_level"),
                    row.get("job_probability_score"),
                    row.get("completeness_score"),
                    row.get("duplicate_group_id"),
                    Json(row.get("qa_flags") or []),
                )
                for row in rows
            ]
            if sample_rows:
                execute_values(
                    cur,
                    """
                    INSERT INTO labor_qa_job_sample
                        (audit_run_id, job_id, source, title, company, curation_level,
                         job_probability_score, completeness_score, duplicate_group_id, qa_flags)
                    VALUES %s
                    ON CONFLICT (audit_run_id, job_id) DO NOTHING
                    """,
                    sample_rows,
                )
        conn.commit()
    return correlation_id


def ingest_feedback_csv(path: Path, reviewer: str = "qa_reviewer") -> int:
    if not path.exists():
        return 0
    rows: list[tuple[Any, ...]] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            decision = (row.get("human_decision") or "").strip().casefold()
            corrected_company = (row.get("corrected_company") or "").strip()
            corrected_role = (row.get("corrected_role") or "").strip()
            notes = (row.get("notes") or "").strip()
            if not any((decision, corrected_company, corrected_role, notes)):
                continue
            job_id = row.get("job_id") or None
            accepted = decision in {"accept", "accepted", "aceptar", "aceptado"}
            rejected = decision in {"reject", "rejected", "rechazar", "rechazado"}
            rows.append(
                (
                    int(job_id) if job_id else None,
                    accepted,
                    rejected,
                    corrected_company or None,
                    corrected_role or None,
                    reviewer,
                    notes,
                    "job_quality",
                    row.get("company") or None,
                    corrected_company or corrected_role or None,
                    "reviewed",
                    Json(row),
                    _parse_optional_bool(row.get("recommendation_acceptance")),
                    row.get("recommendation_rejection_reason") or None,
                    row.get("curriculum_gap_override") or None,
                    row.get("company_resolution_override") or None,
                    row.get("semantic_role_override") or None,
                )
            )
    if not rows:
        return 0
    load_environment()
    with get_conn() as conn:
        with conn.cursor() as cur:
            _apply_migrations(cur)
            execute_values(
                cur,
                """
                INSERT INTO human_validation_feedback
                    (job_id, accepted, rejected, corrected_company, corrected_role, reviewer, observation,
                     feedback_type, original_value, corrected_value, review_status, source_payload,
                     recommendation_acceptance, recommendation_rejection_reason, curriculum_gap_override,
                     company_resolution_override, semantic_role_override)
                VALUES %s
                """,
                rows,
            )
        conn.commit()
    return len(rows)


def run_qa(sample_size: int, feedback_csv: Path | None = None) -> dict[str, Any]:
    rows = fetch_job_quality_sample(sample_size=sample_size)
    write_job_quality_sample(rows)
    company = write_company_cleanup_audit()
    dedup = write_deduplication_qa_report()
    guardrail = write_ml_model_guardrail_report()
    correlation_id = persist_qa_run(rows, guardrail)
    ingested = ingest_feedback_csv(feedback_csv) if feedback_csv else 0
    return {
        "correlation_id": correlation_id,
        "sampled_jobs": len(rows),
        "feedback_ingested": ingested,
        "company_audit": company["summary"],
        "dedup_groups_reviewed": len(dedup["groups"]),
        "guardrail": guardrail,
        "outputs": {
            "job_quality_sample_csv": str(JOB_SAMPLE_CSV),
            "job_quality_sample_md": str(JOB_SAMPLE_MD),
            "company_cleanup_audit": str(COMPANY_AUDIT_MD),
            "deduplication_qa_report": str(DEDUP_QA_MD),
            "ml_model_guardrail_report": str(GUARDRAIL_REPORT_MD),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate labor intelligence QA samples and ingest human feedback.")
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--feedback-csv", type=Path)
    args = parser.parse_args()
    print(json.dumps(run_qa(sample_size=args.sample_size, feedback_csv=args.feedback_csv), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
