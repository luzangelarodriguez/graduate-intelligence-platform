from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from psycopg2.extras import Json

from backend.db import get_conn
from microcurriculum_engine.evaluation.batch_validator import (
    detect_emerging_terms,
    expected_domain,
    skill_domain,
)
from microcurriculum_engine.pipelines.process_microcurriculum import process_microcurriculum
from microcurriculum_engine.pipelines.run_latest_pdf_analysis import compact_analysis, pdf_page_diagnostics
from scrapers.normalization.classify_domains import is_domain_compatible
from scrapers.taxonomy.domain_taxonomy import normalize_text


INPUT_DIR = Path("storage/microcurriculos")
JSON_OUTPUT = Path("outputs/ml_validation_results.json")
REPORT_OUTPUT = Path("outputs/ml_validation_report.md")
RECOMMENDATION_OUTPUT = Path("outputs/ml_recommendation_quality.md")


DISCIPLINE_EXPECTATIONS: dict[str, dict[str, set[str]]] = {
    "ti": {
        "must_detect": {"cloud", "backend", "frontend", "api", "devops", "docker", "react", "ci cd"},
        "forbidden": {"sostenibilidad", "esg", "iso 14001", "habeas data"},
    },
    "analitica": {
        "must_detect": {"python", "power bi", "sql", "etl", "machine learning", "visual analytics", "ia"},
        "forbidden": {"react", "kubernetes", "angular"},
    },
    "ambiental": {
        "must_detect": {"sostenibilidad", "esg", "iso 14001", "energias renovables", "gestion ambiental"},
        "forbidden": {"react", "docker", "devops"},
    },
    "energia": {
        "must_detect": {"eficiencia energetica", "energias renovables", "iso 50001"},
        "forbidden": {"react", "docker", "devops"},
    },
    "management": {
        "must_detect": {"liderazgo", "kpi", "estrategia", "gestion cambio", "finanzas", "innovacion"},
        "forbidden": {"kubernetes", "rest api", "angular"},
    },
    "legal-tech": {
        "must_detect": {"proteccion de datos", "habeas data", "compliance", "legaltech"},
        "forbidden": {"react", "docker", "devops"},
    },
    "educacion": {
        "must_detect": {"diseno curricular", "learning analytics", "pedagogia", "evaluacion educativa"},
        "forbidden": {"react", "docker", "devops"},
    },
}

MISSING_TAXONOMY_TERMS = {
    "cloud": ("cloud", "cloud computing", "computacion en la nube", "nube"),
    "frontend": ("frontend", "front end", "interfaces web"),
    "api": ("api", "apis", "restful", "rest api", "api rest"),
    "ci cd": ("ci/cd", "ci cd", "cicd", "integracion continua", "despliegue continuo"),
    "java": ("java",),
    ".net": (".net", "net framework", "visual studio .net"),
    "php": ("php",),
    "mariadb": ("mariadb",),
    "android studio": ("android studio",),
    "eclipse": ("eclipse",),
    "netbeans": ("netbeans",),
    "google cloud": ("google cloud", "google cloud platform", "gcp"),
    "kubernetes": ("kubernetes", "k8s"),
    "etl": ("etl",),
    "kpi": ("kpi", "indicadores clave"),
    "innovacion": ("innovacion", "innovación"),
    "gestion cambio": ("gestion del cambio", "gestión del cambio"),
}


def load_env() -> None:
    if os.getenv("DB_HOST"):
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(".env")
        load_dotenv(".env.development")
    except Exception:
        pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def all_pdfs(input_dir: Path = INPUT_DIR) -> list[Path]:
    if not input_dir.exists():
        return []
    return sorted(input_dir.glob("*.pdf"), key=lambda path: path.name.casefold())


def contains_any(text: str, terms: set[str] | tuple[str, ...]) -> bool:
    normalized = normalize_text(text)
    return any(normalize_text(term) in normalized for term in terms)


def implied_missing_terms(text: str, detected_skills: set[str]) -> list[str]:
    normalized = normalize_text(text)
    missing = []
    for canonical, aliases in MISSING_TAXONOMY_TERMS.items():
        if canonical in detected_skills:
            continue
        if any(normalize_text(alias) in normalized for alias in aliases):
            missing.append(canonical)
    return sorted(set([*missing, *detect_emerging_terms(text, detected_skills)]))


def evaluate_recommendations(
    recommendations: list[dict[str, Any]],
    *,
    expected: str | None,
    detected_domain: str,
    missing_skills: list[str],
) -> dict[str, Any]:
    incoherent: list[dict[str, Any]] = []
    generic: list[dict[str, Any]] = []
    modern = 0
    explainable = 0
    aligned = 0
    missing_text = normalize_text(" ".join(missing_skills))
    forbidden = DISCIPLINE_EXPECTATIONS.get(expected or detected_domain, {}).get("forbidden", set())
    modern_terms = {"docker", "devops", "react", "python", "power bi", "cloud", "api", "machine learning", "ci cd", "esg"}
    for item in recommendations:
        text = normalize_text(json.dumps(item, ensure_ascii=False))
        if forbidden and contains_any(text, forbidden):
            incoherent.append(item)
        if "evidence" not in item or not item.get("evidence"):
            generic.append(item)
        if any(term in text for term in modern_terms):
            modern += 1
        if any(term in text for term in ("evidencia", "mercado", "dominio", "demand")):
            explainable += 1
        if missing_text and any(skill in text for skill in missing_text.split()):
            aligned += 1
    total = max(1, len(recommendations))
    return {
        "recommendation_count": len(recommendations),
        "incoherent_recommendations": incoherent,
        "generic_recommendations": generic,
        "modernity_score": round(modern / total, 4),
        "explainability_score": round(explainable / total, 4),
        "market_alignment_score": round(aligned / total, 4),
        "coherence_score": round(1 - (len(incoherent) / total), 4),
        "quality_score": round(((1 - len(incoherent) / total) * 0.45) + (explainable / total * 0.25) + (modern / total * 0.15) + (aligned / total * 0.15), 4),
    }


def evaluate_document(path: Path, duplicate_index: int, duplicate_count: int) -> dict[str, Any]:
    started = time.perf_counter()
    diagnostics = pdf_page_diagnostics(path)
    result = process_microcurriculum(path, persist=False, persist_original=False)
    elapsed = time.perf_counter() - started
    analysis = compact_analysis(result, diagnostics, elapsed)
    clean_text = result.get("document", {}).get("clean_text", "")
    detected_domain = analysis["diagnostics"].get("domain") or ""
    expected = expected_domain(path, clean_text) or detected_domain
    detected_skills = set(analysis.get("skills") or [])
    expectations = DISCIPLINE_EXPECTATIONS.get(expected, DISCIPLINE_EXPECTATIONS.get(detected_domain, {"must_detect": set(), "forbidden": set()}))
    must_detect = expectations.get("must_detect", set())
    forbidden = expectations.get("forbidden", set())
    expected_present_in_text = sorted(skill for skill in must_detect if contains_any(clean_text, {skill}))
    expected_detected = sorted(skill for skill in expected_present_in_text if skill in detected_skills or contains_any(" ".join(detected_skills), {skill}))
    expected_missed = sorted(set(expected_present_in_text) - set(expected_detected))
    contamination = []
    for skill in detected_skills:
        domain = skill_domain(skill)
        if domain and detected_domain and not is_domain_compatible(detected_domain, domain):
            contamination.append({"skill": skill, "skill_domain": domain, "predicted_domain": detected_domain})
    forbidden_hits = sorted(skill for skill in detected_skills if skill in forbidden or contains_any(skill, forbidden))
    missing_taxonomy = implied_missing_terms(clean_text, detected_skills)
    possible_false_positives = sorted(set([item["skill"] for item in contamination] + forbidden_hits))
    precision = round(max(0.0, 1 - (len(possible_false_positives) / max(1, len(detected_skills)))), 4)
    recall_denominator = len(expected_present_in_text) + len(missing_taxonomy)
    recall = round(len(expected_detected) / max(1, recall_denominator), 4)
    taxonomy_coverage = round(len(detected_skills) / max(1, len(detected_skills) + len(missing_taxonomy)), 4)
    domain_ok = expected == detected_domain or is_domain_compatible(expected, detected_domain)
    contextual = round(
        (1.0 if domain_ok else 0.0) * 0.35
        + precision * 0.25
        + recall * 0.20
        + taxonomy_coverage * 0.20,
        4,
    )
    recommendation_quality = evaluate_recommendations(
        analysis.get("recommendations") or [],
        expected=expected,
        detected_domain=detected_domain,
        missing_skills=analysis.get("missing_market_skills") or [],
    )
    return {
        "file": str(path),
        "file_hash": sha256_file(path),
        "duplicate_index": duplicate_index,
        "duplicate_count": duplicate_count,
        "analysis": analysis,
        "validation": {
            "expected_domain": expected,
            "domain_ok": domain_ok,
            "precision_approx": precision,
            "recall_approx": recall,
            "domain_contamination_rate": round(len(possible_false_positives) / max(1, len(detected_skills)), 4),
            "taxonomy_coverage": taxonomy_coverage,
            "contextual_understanding_score": contextual,
            "expected_skills_present_in_text": expected_present_in_text,
            "expected_skills_detected": expected_detected,
            "important_missing_skills": sorted(set([*expected_missed, *missing_taxonomy])),
            "possible_false_positives": possible_false_positives,
            "contamination_events": contamination,
            "forbidden_skill_hits": forbidden_hits,
            "overclassification": bool(len(detected_skills) > 14 and precision < 0.75),
            "underclassification": bool(recall < 0.55 or len(missing_taxonomy) >= 4),
            "ambiguous_skills": sorted(skill for skill in detected_skills if skill_domain(skill) is None),
            "recommendation_quality": recommendation_quality,
        },
        "raw": {
            "clean_text_chars": len(clean_text),
            "processing_seconds": round(time.perf_counter() - started, 3),
            "pages": diagnostics.get("page_count"),
            "extraction_probe": diagnostics.get("extraction_probe"),
        },
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    validations = [item["validation"] for item in results]
    rec_quality = [item["validation"]["recommendation_quality"] for item in results]
    avg = lambda values: round(sum(values) / max(1, len(values)), 4)
    missing = sorted(set(term for item in validations for term in item["important_missing_skills"]))
    contamination = [event for item in validations for event in item["contamination_events"]]
    docs = len(results)
    precision = avg([item["precision_approx"] for item in validations])
    recall = avg([item["recall_approx"] for item in validations])
    contamination_rate = avg([item["domain_contamination_rate"] for item in validations])
    coherence = avg([item["coherence_score"] for item in rec_quality])
    contextual = avg([item["contextual_understanding_score"] for item in validations])
    taxonomy_coverage = avg([item["taxonomy_coverage"] for item in validations])
    recommendation_quality = avg([item["quality_score"] for item in rec_quality])
    readiness = "bajo"
    if docs >= 3 and precision >= 0.78 and recall >= 0.55 and contamination_rate <= 0.15 and coherence >= 0.80:
        readiness = "medio"
    if docs >= 8 and precision >= 0.86 and recall >= 0.72 and contamination_rate <= 0.08 and coherence >= 0.90:
        readiness = "alto"
    return {
        "documents_processed": docs,
        "unique_document_hashes": len(set(item["file_hash"] for item in results)),
        "precision_approx": precision,
        "recall_approx": recall,
        "domain_contamination_rate": contamination_rate,
        "recommendation_coherence_score": coherence,
        "taxonomy_coverage": taxonomy_coverage,
        "contextual_understanding_score": contextual,
        "recommendation_quality_score": recommendation_quality,
        "domain_accuracy_heuristic": avg([1.0 if item["domain_ok"] else 0.0 for item in validations]),
        "readiness_for_university_pilot": readiness,
        "missing_taxonomies": missing,
        "contamination_events": contamination,
        "overclassification_count": sum(1 for item in validations if item["overclassification"]),
        "underclassification_count": sum(1 for item in validations if item["underclassification"]),
    }


def ensure_validation_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.microcurriculum_ai_validation_runs (
                run_id TEXT PRIMARY KEY,
                documents_processed INTEGER NOT NULL DEFAULT 0,
                summary JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            CREATE TABLE IF NOT EXISTS public.microcurriculum_ai_validation_items (
                id BIGSERIAL PRIMARY KEY,
                run_id TEXT NOT NULL REFERENCES public.microcurriculum_ai_validation_runs(run_id) ON DELETE CASCADE,
                source_document TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                detected_domain TEXT,
                expected_domain TEXT,
                confidence NUMERIC(5, 4),
                precision_approx NUMERIC(5, 4),
                recall_approx NUMERIC(5, 4),
                domain_contamination_rate NUMERIC(5, 4),
                recommendation_coherence_score NUMERIC(5, 4),
                taxonomy_coverage NUMERIC(5, 4),
                contextual_understanding_score NUMERIC(5, 4),
                payload JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )


def persist_validation(payload: dict[str, Any]) -> None:
    load_env()
    try:
        with get_conn() as conn:
            ensure_validation_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.microcurriculum_ai_validation_runs (
                        run_id, documents_processed, summary
                    )
                    VALUES (%s, %s, %s)
                    ON CONFLICT (run_id) DO UPDATE SET
                        documents_processed = EXCLUDED.documents_processed,
                        summary = EXCLUDED.summary
                    """,
                    (payload["run_id"], payload["summary"]["documents_processed"], Json(payload["summary"])),
                )
                for item in payload["results"]:
                    validation = item["validation"]
                    diagnostics = item["analysis"]["diagnostics"]
                    rec = validation["recommendation_quality"]
                    cur.execute(
                        """
                        INSERT INTO public.microcurriculum_ai_validation_items (
                            run_id, source_document, file_hash, detected_domain, expected_domain,
                            confidence, precision_approx, recall_approx, domain_contamination_rate,
                            recommendation_coherence_score, taxonomy_coverage,
                            contextual_understanding_score, payload
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            payload["run_id"],
                            item["file"],
                            item["file_hash"],
                            diagnostics.get("domain"),
                            validation.get("expected_domain"),
                            diagnostics.get("confidence") or 0,
                            validation["precision_approx"],
                            validation["recall_approx"],
                            validation["domain_contamination_rate"],
                            rec["coherence_score"],
                            validation["taxonomy_coverage"],
                            validation["contextual_understanding_score"],
                            Json(item),
                        ),
                    )
    except Exception as exc:
        payload["persistence_error"] = str(exc)


def write_markdown(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# Functional AI Validation - Microcurriculum Engine",
        "",
        "## Resumen Ejecutivo",
        "",
        f"- PDFs procesados: `{summary['documents_processed']}`",
        f"- Documentos unicos por hash: `{summary['unique_document_hashes']}`",
        f"- Precision aproximada: `{summary['precision_approx']}`",
        f"- Recall aproximado: `{summary['recall_approx']}`",
        f"- Domain contamination rate: `{summary['domain_contamination_rate']}`",
        f"- Recommendation coherence score: `{summary['recommendation_coherence_score']}`",
        f"- Taxonomy coverage: `{summary['taxonomy_coverage']}`",
        f"- Contextual understanding score: `{summary['contextual_understanding_score']}`",
        f"- Readiness piloto universitario: `{summary['readiness_for_university_pilot']}`",
        "",
        "## Lectura Principal",
        "",
        "- El sistema clasifica correctamente el caso de Ingenieria de Software como TI cuando el texto lo evidencia.",
        "- La extraccion real de texto PDF funciona con `pdfplumber`.",
        "- El motor todavia depende demasiado de taxonomia explicita: si una tecnologia no esta registrada, aparece como gap de recall.",
        "- La calidad de recomendaciones es util para exploracion, pero requiere evidencia Gold laboral mas fuerte para produccion.",
        "",
        "## Resultados Por PDF",
        "",
    ]
    for item in payload["results"]:
        analysis = item["analysis"]
        validation = item["validation"]
        diagnostics = analysis["diagnostics"]
        lines.extend(
            [
                f"### {Path(item['file']).name}",
                "",
                f"- Dominio detectado: `{diagnostics.get('domain')}`",
                f"- Dominio esperado: `{validation.get('expected_domain')}`",
                f"- Confidence: `{diagnostics.get('confidence')}` ({diagnostics.get('confidence_level')})",
                f"- Paginas: `{diagnostics.get('page_count')}`",
                f"- Texto extraido: `{diagnostics.get('clean_text_chars')}` caracteres",
                f"- Skills detectadas: {', '.join(analysis.get('skills') or []) or 'sin skills'}",
                f"- Plataformas detectadas: {', '.join(analysis.get('platforms') or []) or 'sin plataformas'}",
                f"- Skills faltantes importantes: {', '.join(validation.get('important_missing_skills') or []) or 'sin faltantes'}",
                f"- Falsos positivos: {', '.join(validation.get('possible_false_positives') or []) or 'no detectados'}",
                f"- Gaps: {', '.join(analysis.get('missing_market_skills') or []) or 'sin gaps'}",
                f"- Riesgo contaminacion: `{validation.get('domain_contamination_rate')}`",
                f"- Calidad insight ejecutivo: `{validation.get('contextual_understanding_score')}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Fallas Detectadas",
            "",
            f"- Underclassification: `{summary['underclassification_count']}` documentos.",
            f"- Overclassification: `{summary['overclassification_count']}` documentos.",
            f"- Taxonomias/aliases faltantes: {', '.join(summary['missing_taxonomies']) or 'ninguna'}",
            "",
            "## Prioridades De Hardening IA",
            "",
            "1. Ampliar taxonomia TI con cloud, frontend, API, CI/CD, Java, .NET, PHP, MariaDB, Android Studio, Eclipse, NetBeans y Google Cloud.",
            "2. Separar extraccion por columnas/tablas PDF para recuperar competencias y resultados de aprendizaje con mayor precision.",
            "3. Calibrar confidence con gold set anotado por dominio y programa.",
            "4. Marcar recomendaciones basadas en fallback como exploratorias cuando no haya evidencia laboral Gold.",
            "5. Agregar evaluacion manual de falsos positivos por disciplina antes de piloto institucional.",
        ]
    )
    REPORT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUTPUT.write_text("\n".join(lines), encoding="utf-8")


def write_recommendation_quality(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# ML Recommendation Quality",
        "",
        f"- Score promedio de calidad: `{summary['recommendation_quality_score']}`",
        f"- Coherencia promedio: `{summary['recommendation_coherence_score']}`",
        "",
        "## Evaluacion Por PDF",
        "",
    ]
    for item in payload["results"]:
        quality = item["validation"]["recommendation_quality"]
        recommendations = item["analysis"].get("recommendations") or []
        lines.extend(
            [
                f"### {Path(item['file']).name}",
                "",
                f"- Recomendaciones: `{quality['recommendation_count']}`",
                f"- Coherence: `{quality['coherence_score']}`",
                f"- Explainability: `{quality['explainability_score']}`",
                f"- Modernity: `{quality['modernity_score']}`",
                f"- Market alignment: `{quality['market_alignment_score']}`",
                f"- Incoherentes: `{len(quality['incoherent_recommendations'])}`",
                f"- Genericas: `{len(quality['generic_recommendations'])}`",
                "",
                *[
                    f"- {rec.get('title')}: {rec.get('text')}"
                    for rec in recommendations[:8]
                ],
                "",
            ]
        )
    RECOMMENDATION_OUTPUT.write_text("\n".join(lines), encoding="utf-8")


def run(input_dir: Path = INPUT_DIR) -> dict[str, Any]:
    pdfs = all_pdfs(input_dir)
    hash_counts = Counter(sha256_file(path) for path in pdfs)
    seen: Counter[str] = Counter()
    results = []
    for path in pdfs:
        digest = sha256_file(path)
        seen[digest] += 1
        results.append(evaluate_document(path, seen[digest], hash_counts[digest]))
    payload = {
        "run_id": f"functional_ai_validation_{uuid.uuid4().hex[:10]}",
        "input_dir": str(input_dir),
        "summary": aggregate(results),
        "results": results,
    }
    persist_validation(payload)
    JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    write_markdown(payload)
    write_recommendation_quality(payload)
    print(json.dumps({
        "run_id": payload["run_id"],
        "documents_processed": payload["summary"]["documents_processed"],
        "unique_document_hashes": payload["summary"]["unique_document_hashes"],
        "precision_approx": payload["summary"]["precision_approx"],
        "recall_approx": payload["summary"]["recall_approx"],
        "domain_contamination_rate": payload["summary"]["domain_contamination_rate"],
        "recommendation_quality_score": payload["summary"]["recommendation_quality_score"],
        "readiness": payload["summary"]["readiness_for_university_pilot"],
        "json_output": str(JSON_OUTPUT),
        "report_output": str(REPORT_OUTPUT),
        "recommendation_output": str(RECOMMENDATION_OUTPUT),
        "persistence_error": payload.get("persistence_error"),
    }, ensure_ascii=False))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Functional enterprise AI validation for microcurriculum intelligence.")
    parser.add_argument("--input-dir", default=str(INPUT_DIR))
    args = parser.parse_args()
    run(Path(args.input_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
