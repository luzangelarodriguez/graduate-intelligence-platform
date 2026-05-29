from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from microcurriculum_engine.pipelines.process_microcurriculum import process_microcurriculum
from microcurriculum_engine.pipelines.run_latest_pdf_analysis import compact_analysis, pdf_page_diagnostics
from scrapers.normalization.classify_domains import is_domain_compatible
from scrapers.taxonomy.domain_taxonomy import SKILL_BY_CANONICAL, normalize_text


TARGET_DIR = Path("storage/test_microcurriculos")
FALLBACK_DIR = Path("storage/microcurriculos")
JSON_OUTPUT = Path("outputs/ml_validation_results.json")
REPORT_OUTPUT = Path("outputs/ml_validation_report.md")


EXPECTED_DOMAIN_HINTS = (
    ("software", "ti"),
    ("ing_software", "ti"),
    ("ingenieria de software", "ti"),
    ("visual analytics", "analitica"),
    ("datos", "analitica"),
    ("ambiental", "ambiental"),
    ("energet", "energia"),
    ("derecho", "legal-tech"),
    ("seguridad", "cybersecurity"),
    ("educacion", "educacion"),
    ("gerencia", "management"),
)

EMERGING_TERMS = {
    "java": "java",
    ".net": ".net",
    "android studio": "android studio",
    "eclipse": "eclipse",
    "netbeans": "netbeans",
    "google cloud": "google cloud",
    "mariadb": "mariadb",
    "php": "php",
    "kotlin": "kotlin",
    "kubernetes": "kubernetes",
    "github actions": "github actions",
    "microservicios": "microservicios",
}


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pdf_inputs(target_dir: Path = TARGET_DIR) -> tuple[list[Path], str]:
    if target_dir.exists():
        candidates = sorted(target_dir.glob("*.pdf"), key=lambda item: item.name.casefold())
        source_mode = str(target_dir)
    else:
        candidates = []
        source_mode = f"{target_dir} missing"
    if not candidates:
        candidates = sorted(FALLBACK_DIR.glob("*.pdf"), key=lambda item: item.stat().st_mtime)
        source_mode += f"; fallback={FALLBACK_DIR}"
    unique: dict[str, Path] = {}
    for path in candidates:
        digest = file_hash(path)
        unique.setdefault(digest, path)
    return list(unique.values()), source_mode


def expected_domain(path: Path, text: str) -> str | None:
    value = normalize_text(f"{path.name} {text[:2000]}")
    for needle, domain in EXPECTED_DOMAIN_HINTS:
        if normalize_text(needle) in value:
            return domain
    return None


def skill_domain(skill: str) -> str | None:
    definition = SKILL_BY_CANONICAL.get(skill)
    return definition.domain if definition else None


def detect_emerging_terms(text: str, detected_skills: set[str]) -> list[str]:
    normalized = normalize_text(text)
    missing: list[str] = []
    for term, canonical in EMERGING_TERMS.items():
        if normalize_text(term) in normalized and canonical not in detected_skills:
            missing.append(canonical)
    return sorted(set(missing))


def evaluate_analysis(path: Path, analysis: dict[str, Any]) -> dict[str, Any]:
    diagnostics = analysis.get("diagnostics") or {}
    domain = diagnostics.get("domain") or ""
    text = diagnostics.get("clean_text_preview") or ""
    full_text = analysis.get("_clean_text") or text
    expected = expected_domain(path, full_text)
    skills = analysis.get("skills") or []
    contamination = []
    ambiguous = []
    for skill in skills:
        s_domain = skill_domain(skill)
        if not s_domain:
            ambiguous.append(skill)
        elif domain and not is_domain_compatible(domain, s_domain):
            contamination.append({"skill": skill, "skill_domain": s_domain, "predicted_domain": domain})
    missing_terms = detect_emerging_terms(full_text, set(skills))
    false_positive_rate = len(contamination) / max(1, len(skills))
    domain_ok = expected is None or expected == domain or is_domain_compatible(expected, domain)
    recommendation_items = analysis.get("recommendations") or []
    incoherent_recommendations = [
        item for item in recommendation_items
        if expected and expected in {"ambiental", "energia", "legal-tech", "educacion"} and any(
            term in normalize_text(str(item))
            for term in ("backend", "fullstack", "react", "docker", "devops")
        )
    ]
    precision = round(max(0.0, 1.0 - false_positive_rate), 4)
    recall = round(len(skills) / max(1, len(skills) + len(missing_terms)), 4)
    coherence = round(1.0 - (len(incoherent_recommendations) / max(1, len(recommendation_items))), 4)
    return {
        "expected_domain": expected,
        "domain_ok": domain_ok,
        "precision_approx": precision,
        "recall_approx": recall,
        "domain_contamination_rate": round(false_positive_rate, 4),
        "recommendation_coherence": coherence,
        "contamination": contamination,
        "ambiguous_skills": ambiguous,
        "possible_false_positives": [item["skill"] for item in contamination],
        "underclassification_terms": missing_terms,
        "overclassification": bool(len(skills) > 12 and diagnostics.get("confidence", 0) < 0.7),
        "underclassification": bool(len(skills) < 4 or len(missing_terms) >= 4),
        "incoherent_recommendations": incoherent_recommendations,
    }


def validate_pdf(path: Path) -> dict[str, Any]:
    started = time.perf_counter()
    diagnostics = pdf_page_diagnostics(path)
    result = process_microcurriculum(path, persist=False, persist_original=False)
    elapsed = time.perf_counter() - started
    analysis = compact_analysis(result, diagnostics, elapsed)
    analysis["_clean_text"] = result.get("document", {}).get("clean_text", "")
    evaluation = evaluate_analysis(path, analysis)
    return {
        "file": str(path),
        "analysis": {key: value for key, value in analysis.items() if key != "_clean_text"},
        "evaluation": evaluation,
        "raw_metrics": {
            "pages": diagnostics.get("page_count"),
            "chars": analysis.get("diagnostics", {}).get("clean_text_chars"),
            "processing_seconds": analysis.get("diagnostics", {}).get("processing_seconds"),
        },
    }


def aggregate(results: list[dict[str, Any]], source_mode: str) -> dict[str, Any]:
    evaluations = [item["evaluation"] for item in results]
    count = len(results)
    avg = lambda key: round(sum(float(item.get(key, 0)) for item in evaluations) / max(1, count), 4)
    missing_taxonomy: set[str] = set()
    contamination: list[Any] = []
    for item in evaluations:
        missing_taxonomy.update(item.get("underclassification_terms") or [])
        contamination.extend(item.get("contamination") or [])
    readiness = "bajo"
    precision = avg("precision_approx")
    coherence = avg("recommendation_coherence")
    contamination_rate = avg("domain_contamination_rate")
    if count >= 3 and precision >= 0.78 and coherence >= 0.75 and contamination_rate <= 0.15:
        readiness = "medio"
    if count >= 5 and precision >= 0.85 and coherence >= 0.85 and contamination_rate <= 0.10:
        readiness = "alto"
    return {
        "source_mode": source_mode,
        "documents_processed": count,
        "precision_approx": precision,
        "recall_approx": avg("recall_approx"),
        "domain_contamination_rate": contamination_rate,
        "recommendation_coherence": coherence,
        "domain_accuracy_heuristic": round(sum(1 for item in evaluations if item.get("domain_ok")) / max(1, count), 4),
        "readiness_for_university_pilot": readiness,
        "missing_taxonomies": sorted(missing_taxonomy),
        "contamination_events": contamination,
    }


def write_outputs(payload: dict[str, Any]) -> None:
    JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    summary = payload["summary"]
    lines = [
        "# ML Validation Report - Microcurriculum Engine",
        "",
        "## Resumen Ejecutivo",
        "",
        f"- Fuente: `{summary['source_mode']}`",
        f"- Documentos procesados: `{summary['documents_processed']}`",
        f"- Precision aproximada: `{summary['precision_approx']}`",
        f"- Recall aproximado: `{summary['recall_approx']}`",
        f"- Domain contamination rate: `{summary['domain_contamination_rate']}`",
        f"- Recommendation coherence: `{summary['recommendation_coherence']}`",
        f"- Domain accuracy heuristica: `{summary['domain_accuracy_heuristic']}`",
        f"- Readiness piloto universitario: `{summary['readiness_for_university_pilot']}`",
        "",
        "## Resultados por PDF",
        "",
    ]
    for item in payload["results"]:
        analysis = item["analysis"]
        diagnostics = analysis["diagnostics"]
        evaluation = item["evaluation"]
        lines.extend([
            f"### {Path(item['file']).name}",
            "",
            f"- Dominio detectado: `{diagnostics.get('domain')}`",
            f"- Dominio esperado heuristico: `{evaluation.get('expected_domain')}`",
            f"- Confidence: `{diagnostics.get('confidence')}` ({diagnostics.get('confidence_level')})",
            f"- Paginas: `{diagnostics.get('page_count')}`",
            f"- Caracteres: `{diagnostics.get('clean_text_chars')}`",
            f"- Skills: {', '.join(analysis.get('skills') or []) or 'Sin skills'}",
            f"- Posibles falsos positivos: {', '.join(evaluation.get('possible_false_positives') or []) or 'No detectados'}",
            f"- Skills ambiguas: {', '.join(evaluation.get('ambiguous_skills') or []) or 'No detectadas'}",
            f"- Gaps: {', '.join(analysis.get('missing_market_skills') or []) or 'Sin gaps'}",
            f"- Recomendaciones: {len(analysis.get('recommendations') or [])}",
            "",
        ])
    lines.extend([
        "## Taxonomias y Aliases Faltantes",
        "",
        *[f"- {item}" for item in summary["missing_taxonomies"]],
        "",
        "## Mejoras Concretas",
        "",
        "- Ampliar taxonomia de software: Java, .NET, PHP, MariaDB, Android Studio, Eclipse, NetBeans, Google Cloud, Kubernetes y GitHub Actions.",
        "- Separar extracción curricular por tablas/filas PDF para no depender solo de texto corrido.",
        "- Calibrar confidence usando dataset anotado por programa/asignatura y no solo reglas + modelo semilla.",
        "- Incorporar embeddings por bloque curricular para distinguir contenidos, resultados de aprendizaje y actividades.",
        "- Penalizar recomendaciones sin evidencia Gold laboral y marcar recomendaciones de fallback como exploratorias.",
        "- Crear gold set manual con dominios esperados y skills esperadas por microcurriculo.",
    ])
    REPORT_OUTPUT.write_text("\n".join(lines), encoding="utf-8")


def run(target_dir: Path = TARGET_DIR) -> dict[str, Any]:
    pdfs, source_mode = pdf_inputs(target_dir)
    results = [validate_pdf(path) for path in pdfs]
    payload = {
        "summary": aggregate(results, source_mode),
        "results": results,
    }
    write_outputs(payload)
    print(json.dumps({
        "documents_processed": payload["summary"]["documents_processed"],
        "precision_approx": payload["summary"]["precision_approx"],
        "recall_approx": payload["summary"]["recall_approx"],
        "domain_contamination_rate": payload["summary"]["domain_contamination_rate"],
        "recommendation_coherence": payload["summary"]["recommendation_coherence"],
        "readiness": payload["summary"]["readiness_for_university_pilot"],
        "json_output": str(JSON_OUTPUT),
        "report_output": str(REPORT_OUTPUT),
    }, ensure_ascii=False))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate disciplinary classification and curricular extraction over microcurriculum PDFs.")
    parser.add_argument("--input-dir", default=str(TARGET_DIR))
    args = parser.parse_args()
    run(Path(args.input_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
