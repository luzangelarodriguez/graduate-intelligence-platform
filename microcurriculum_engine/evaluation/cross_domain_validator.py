from __future__ import annotations

import argparse
import csv
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from microcurriculum_engine.ingestion.document_loader import load_document
from microcurriculum_engine.pipelines.process_microcurriculum import process_microcurriculum
from microcurriculum_engine.pipelines.run_latest_pdf_analysis import compact_analysis, pdf_page_diagnostics
from ml.ner import extract_curriculum_entities
from scrapers.normalization.classify_domains import is_domain_compatible
from scrapers.taxonomy.domain_taxonomy import SKILL_BY_CANONICAL, normalize_text


INPUT_ROOT = Path("storage/test_microcurriculos")
JSON_OUTPUT = Path("outputs/cross_domain_validation_results.json")
REPORT_OUTPUT = Path("outputs/cross_domain_validation_report.md")
HUMAN_MATRIX_OUTPUT = Path("outputs/human_validation_matrix.csv")
RECOMMENDATION_MATRIX_OUTPUT = Path("outputs/recommendation_validation_matrix.csv")
RECOMMENDATION_HARDENING_REPORT = Path("outputs/recommendation_engine_hardening_report.md")

DOMAIN_FOLDERS = {
    "ti": "ti",
    "analitica": "analitica",
    "ambiental": "ambiental",
    "gerencia": "management",
    "educacion": "educacion",
    "derecho": "legal-tech",
}

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
EXTRA_DEMO_DOCUMENTS = (
    (Path("storage/microcurriculos/Anexo 3.1 Microcurriculos - Esp_ing_Software.pdf"), "ti", "ingenieria_software"),
)

EXPECTED_DOCUMENT_OVERRIDES = {
    "aprendizaje automatico.docx": ("analitica", "inteligencia_artificial"),
    "diseño de proyectos orientados a la innovación.docx": ("management", "innovacion"),
    "diseno de proyectos orientados a la innovacion.docx": ("management", "innovacion"),
    "ade _s.5 _b. 1 _gerencia financiera.docx": ("management", "finanzas"),
}

EXPECTED_TERMS = {
    "ti": {"cloud", "devops", "api", "docker", "react", "backend", "frontend"},
    "analitica": {"python", "sql", "power bi", "machine learning", "etl", "visual analytics", "ia", "scikit-learn", "notebooks"},
    "ambiental": {"sostenibilidad", "esg", "iso 14001", "energias renovables", "gestion ambiental"},
    "management": {"liderazgo", "kpi", "estrategia", "gestion cambio", "finanzas", "innovacion", "excel avanzado", "modelacion financiera", "indicadores financieros"},
    "educacion": {"diseno curricular", "pedagogia", "learning analytics", "evaluacion educativa"},
    "legal-tech": {"proteccion de datos", "habeas data", "compliance", "legaltech", "derecho digital"},
}

EXPECTED_TERMS_BY_SUBDOMAIN = {
    "inteligencia_artificial": {"machine learning", "ia", "python", "scikit-learn", "notebooks", "visual analytics", "mlops"},
    "innovacion": {"innovacion", "vigilancia tecnologica", "inteligencia competitiva", "gestion de proyectos", "design thinking"},
    "finanzas": {"excel avanzado", "power bi financiero", "modelacion financiera", "analisis de escenarios", "indicadores financieros"},
}

FORBIDDEN_BY_DOMAIN = {
    "ambiental": {"react", "docker", "kubernetes", "devops", "backend", "frontend"},
    "management": {"kubernetes", "api", "react", "angular", "backend", "frontend", "devops", "cloud"},
    "educacion": {"react", "docker", "kubernetes", "devops", "backend"},
    "legal-tech": {"react", "docker", "kubernetes", "devops", "backend"},
    "analitica": {"react", "kubernetes", "angular"},
}

ALLOWED_BY_SUBDOMAIN = {
    "inteligencia_artificial": {"python", "machine learning", "mlops", "scikit-learn", "notebooks", "visual analytics", "datos", "power bi", "sql"},
    "innovacion": {"innovacion", "design thinking", "gestion de proyectos", "estrategia", "liderazgo", "kpi"},
    "finanzas": {"excel avanzado", "power bi", "modelacion financiera", "analisis de escenarios", "indicadores financieros", "finanzas", "kpi"},
}

TRANSVERSAL_SKILLS = {"liderazgo", "pensamiento critico", "trabajo en equipo", "comunicacion", "colaboracion"}

HUMAN_MATRIX_COLUMNS = (
    "document_name",
    "text_fragment",
    "detected_domain",
    "detected_subdomain",
    "entity_detected",
    "entity_type",
    "normalized_entity",
    "is_correct",
    "correction",
    "observation",
    "recommendation",
    "recommendation_is_correct",
)

RECOMMENDATION_COLUMNS = (
    "document_name",
    "expected_domain",
    "detected_domain",
    "recommendation_type",
    "recommendation",
    "confidence",
    "evidence",
    "is_coherent",
    "recommendation_is_correct_blank",
    "observation_blank",
)


def ensure_structure(input_root: Path = INPUT_ROOT) -> None:
    for folder in DOMAIN_FOLDERS:
        (input_root / folder).mkdir(parents=True, exist_ok=True)


def iter_documents(input_root: Path = INPUT_ROOT) -> list[tuple[Path, str, str | None]]:
    documents: list[tuple[Path, str, str | None]] = []
    for folder, expected_domain in DOMAIN_FOLDERS.items():
        domain_dir = input_root / folder
        if not domain_dir.exists():
            continue
        for path in sorted(domain_dir.iterdir(), key=lambda item: item.name.casefold()):
            if not path.is_file() or path.suffix.casefold() not in SUPPORTED_EXTENSIONS:
                continue
            documents.append((path, *expected_for_document(path, expected_domain)))
    if input_root == INPUT_ROOT:
        for path, expected_domain, expected_subdomain in EXTRA_DEMO_DOCUMENTS:
            if path.exists() and path.suffix.casefold() in SUPPORTED_EXTENSIONS:
                documents.append((path, expected_domain, expected_subdomain))
    return documents


def expected_for_document(path: Path, folder_domain: str) -> tuple[str, str | None]:
    normalized_name = normalize_text(path.name)
    for name, expected in EXPECTED_DOCUMENT_OVERRIDES.items():
        if normalize_text(name) == normalized_name:
            return expected
    return folder_domain, None


def document_diagnostics(path: Path) -> dict[str, Any]:
    if path.suffix.casefold() == ".pdf":
        return pdf_page_diagnostics(path)
    document = load_document(path, persist_original=False)
    return {
        "page_count": 1,
        "chars_by_page": [len(document.clean_text)],
        "extraction_probe": document.extraction_method,
        "extension": document.extension,
    }


def skill_domain(skill: str) -> str | None:
    definition = SKILL_BY_CANONICAL.get(skill)
    return definition.domain if definition else None


def contains_term(text: str, term: str) -> bool:
    return normalize_text(term) in normalize_text(text)


def expected_term_present(text: str, canonical: str) -> bool:
    definition = SKILL_BY_CANONICAL.get(canonical)
    aliases = (canonical, *(definition.aliases if definition else ()))
    return any(contains_term(text, alias) for alias in aliases)


def expected_terms_for(expected_domain: str, expected_subdomain: str | None) -> set[str]:
    if expected_subdomain and expected_subdomain in EXPECTED_TERMS_BY_SUBDOMAIN:
        return EXPECTED_TERMS_BY_SUBDOMAIN[expected_subdomain]
    return EXPECTED_TERMS.get(expected_domain, set())


def term_is_justified(clean_text: str, term: str) -> bool:
    aliases = {
        "api": ("api", "apis", "servicios", "peticiones", "respuestas"),
        "devops": ("devops", "integracion continua", "despliegue continuo", "ci cd"),
        "cloud": ("cloud", "nube", "computacion en la nube"),
        "docker": ("docker", "contenedores"),
        "kubernetes": ("kubernetes", "k8s"),
        "react": ("react",),
    }.get(term, (term,))
    return any(contains_term(clean_text, alias) for alias in aliases)


def recommendation_text(item: dict[str, Any]) -> str:
    return normalize_text(json.dumps(item, ensure_ascii=False, default=str))


def recommendation_is_coherent(item: dict[str, Any], *, expected_domain: str, clean_text: str) -> bool:
    forbidden = FORBIDDEN_BY_DOMAIN.get(expected_domain, set())
    text = recommendation_text(item)
    for term in forbidden:
        if term in text and not term_is_justified(clean_text, term):
            return False
    return True


def recommendation_allowed_by_subdomain(
    item: dict[str, Any],
    *,
    expected_subdomain: str | None,
    expected_domain: str,
) -> bool:
    if not expected_subdomain:
        return True
    text = recommendation_text(item)
    allowed = ALLOWED_BY_SUBDOMAIN.get(expected_subdomain, set())
    technical_forbidden = {"react", "docker", "kubernetes", "devops", "backend", "frontend"}
    if expected_subdomain in {"innovacion", "finanzas"} and any(term in text for term in technical_forbidden):
        return False
    if expected_subdomain == "inteligencia_artificial":
        return not any(term in text for term in {"react", "angular", "kubernetes"})
    if expected_domain == "management" and allowed:
        return any(term in text for term in allowed) or not any(term in text for term in technical_forbidden)
    return True


def evaluate_document(path: Path, expected_domain: str, expected_subdomain: str | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    diagnostics = document_diagnostics(path)
    result = process_microcurriculum(path, persist=False, persist_original=False)
    elapsed = time.perf_counter() - started
    analysis = compact_analysis(result, diagnostics, elapsed)
    clean_text = result.get("document", {}).get("clean_text") or ""
    entities = extract_curriculum_entities(clean_text)
    detected_domain = result.get("domain_prediction", {}).get("domain") or ""
    confidence = float(result.get("domain_prediction", {}).get("confidence") or 0)
    skills = [item.get("skill_normalized") for item in result.get("skills") or [] if item.get("skill_normalized")]
    detected_skills = set(skills)

    contamination = []
    for skill in sorted(detected_skills):
        domain = skill_domain(skill)
        if domain and detected_domain and not is_domain_compatible(detected_domain, domain):
            contamination.append({"skill": skill, "skill_domain": domain, "detected_domain": detected_domain})

    expected_terms = expected_terms_for(expected_domain, expected_subdomain)
    expected_present = sorted(term for term in expected_terms if expected_term_present(clean_text, term))
    expected_detected = sorted(term for term in expected_present if term in detected_skills or contains_term(" ".join(detected_skills), term))
    expected_missing = sorted(set(expected_present) - set(expected_detected))
    taxonomy_coverage = round(len(detected_skills) / max(1, len(detected_skills) + len(expected_missing)), 4)
    recall = round(len(expected_detected) / max(1, len(expected_present)), 4)

    recommendations = analysis.get("recommendations") or []
    incoherent = [
        item for item in recommendations
        if not recommendation_is_coherent(item, expected_domain=expected_domain, clean_text=clean_text)
        or not recommendation_allowed_by_subdomain(item, expected_subdomain=expected_subdomain, expected_domain=expected_domain)
    ]
    recommendation_coherence = round(1 - (len(incoherent) / max(1, len(recommendations))), 4)

    trans_detected = [skill for skill in detected_skills if skill in TRANSVERSAL_SKILLS]
    trans_ok = [
        skill for skill in trans_detected if skill_domain(skill) == "transversal"
    ]
    transversal_quality = round(len(trans_ok) / max(1, len(trans_detected)), 4)
    false_positive_count = len(contamination)
    precision = round(max(0.0, 1 - false_positive_count / max(1, len(detected_skills))), 4)

    return {
        "document_name": path.name,
        "path": str(path),
        "expected_domain": expected_domain,
        "expected_subdomain": expected_subdomain,
        "detected_domain": detected_domain,
        "confidence": confidence,
        "entities": entities,
        "skills": skills,
        "platforms": analysis.get("platforms") or [],
        "competencias": analysis.get("competencias") or [],
        "missing_market_skills": analysis.get("missing_market_skills") or [],
        "recommendations": recommendations,
        "scores": analysis.get("scores") or {},
        "validation": {
            "domain_ok": expected_domain == detected_domain or is_domain_compatible(expected_domain, detected_domain),
            "precision_approx": precision,
            "recall_approx": recall,
            "domain_contamination_rate": round(false_positive_count / max(1, len(detected_skills)), 4),
            "recommendation_coherence": recommendation_coherence,
            "taxonomy_coverage": taxonomy_coverage,
            "transversal_skill_separation_quality": transversal_quality,
            "false_positives": contamination,
            "false_negatives": expected_missing,
            "generic_recommendations": [
                item for item in recommendations if not item.get("evidence")
            ],
            "incoherent_recommendations": incoherent,
        },
        "diagnostics": {
            "pages": diagnostics.get("page_count"),
            "chars_by_page": diagnostics.get("chars_by_page"),
            "clean_text_chars": len(clean_text),
            "processing_seconds": round(elapsed, 3),
        },
    }


def aggregate_by_domain(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in results:
        grouped[item["expected_domain"]].append(item)
    metrics: dict[str, Any] = {}
    for domain, items in sorted(grouped.items()):
        validations = [item["validation"] for item in items]
        avg = lambda key: round(sum(float(item.get(key, 0)) for item in validations) / max(1, len(validations)), 4)
        metrics[domain] = {
            "documents": len(items),
            "precision_approx": avg("precision_approx"),
            "recall_approx": avg("recall_approx"),
            "domain_contamination_rate": avg("domain_contamination_rate"),
            "recommendation_coherence": avg("recommendation_coherence"),
            "taxonomy_coverage": avg("taxonomy_coverage"),
            "transversal_skill_separation_quality": avg("transversal_skill_separation_quality"),
            "domain_accuracy": round(sum(1 for item in validations if item.get("domain_ok")) / max(1, len(validations)), 4),
        }
    return metrics


def aggregate(results: list[dict[str, Any]], input_root: Path = INPUT_ROOT) -> dict[str, Any]:
    validations = [item["validation"] for item in results]
    count = len(results)
    avg = lambda key: round(sum(float(item.get(key, 0)) for item in validations) / max(1, count), 4)
    low_domains = [
        domain for domain, metrics in aggregate_by_domain(results).items()
        if metrics["precision_approx"] < 0.75 or metrics["recall_approx"] < 0.5 or metrics["domain_contamination_rate"] > 0.15
    ]
    evidence_units = {"/".join(filter(None, [item["expected_domain"], item.get("expected_subdomain")])) for item in results}
    readiness = "blocked_no_cross_domain_evidence"
    if count >= 3 and len(evidence_units) >= 3:
        readiness = "medio" if not low_domains else "bajo"
    if count >= 12 and not low_domains and avg("recommendation_coherence") >= 0.85:
        readiness = "alto"
    return {
        "documents_processed": count,
        "domains_with_documents": sorted({item["expected_domain"] for item in results}),
        "evidence_units": sorted(evidence_units),
        "precision_approx": avg("precision_approx"),
        "recall_approx": avg("recall_approx"),
        "domain_contamination_rate": avg("domain_contamination_rate"),
        "recommendation_coherence": avg("recommendation_coherence"),
        "taxonomy_coverage": avg("taxonomy_coverage"),
        "transversal_skill_separation_quality": avg("transversal_skill_separation_quality"),
        "domain_metrics": aggregate_by_domain(results),
        "low_performance_domains": low_domains,
        "readiness_for_controlled_pilot": readiness,
        "missing_domains": [
            folder
            for folder in DOMAIN_FOLDERS
            if not any(path.suffix.casefold() in SUPPORTED_EXTENSIONS for path in (input_root / folder).glob("*"))
        ],
    }


def write_human_matrix(results: list[dict[str, Any]]) -> None:
    HUMAN_MATRIX_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with HUMAN_MATRIX_OUTPUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=HUMAN_MATRIX_COLUMNS)
        writer.writeheader()
        for item in results:
            recommendations = item.get("recommendations") or [{}]
            first_recommendation = recommendations[0] if recommendations else {}
            for entity in item.get("entities") or []:
                writer.writerow(
                    {
                        "document_name": item["document_name"],
                        "detected_domain": item["detected_domain"],
                        "detected_subdomain": "/".join(filter(None, [item["expected_domain"], item.get("expected_subdomain")])),
                        "text_fragment": entity.get("text_fragment") or "",
                        "entity_detected": entity.get("entity"),
                        "entity_type": entity.get("entity_type"),
                        "normalized_entity": entity.get("normalized_skill"),
                        "is_correct": "",
                        "correction": "",
                        "observation": "",
                        "recommendation": first_recommendation.get("text") or first_recommendation.get("recommendation_text") or "",
                        "recommendation_is_correct": "",
                    }
                )


def write_recommendation_matrix(results: list[dict[str, Any]]) -> None:
    with RECOMMENDATION_MATRIX_OUTPUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=RECOMMENDATION_COLUMNS)
        writer.writeheader()
        for item in results:
            for recommendation in item.get("recommendations") or []:
                writer.writerow(
                    {
                        "document_name": item["document_name"],
                        "expected_domain": "/".join(filter(None, [item["expected_domain"], item.get("expected_subdomain")])),
                        "detected_domain": item["detected_domain"],
                        "recommendation_type": recommendation.get("recommendation_type") or recommendation.get("title"),
                        "recommendation": recommendation.get("text") or recommendation.get("recommendation_text"),
                        "confidence": recommendation.get("confidence") or recommendation.get("confidence_score"),
                        "evidence": json.dumps(recommendation.get("evidence") or {}, ensure_ascii=False, default=str),
                        "is_coherent": recommendation not in item["validation"]["incoherent_recommendations"],
                        "recommendation_is_correct_blank": "",
                        "observation_blank": "",
                    }
                )


def write_recommendation_hardening_report(payload: dict[str, Any]) -> None:
    lines = [
        "# Recommendation Engine Hardening",
        "",
        "## Resumen Ejecutivo",
        "",
        "El motor de recomendaciones fue endurecido con templates por subdominio y salida curricular estructurada para comite academico.",
        "",
        "## Campos Enterprise Generados",
        "",
        "- gap_detectado",
        "- evidencia_curricular",
        "- evidencia_laboral",
        "- asignatura_o_modulo_sugerido",
        "- accion_curricular",
        "- prioridad",
        "- justificacion",
        "- nivel_impacto",
        "- confidence",
        "- explanation",
        "",
        "## Recomendaciones Por Documento",
        "",
    ]
    for item in payload["results"]:
        lines.extend(
            [
                f"### {item['document_name']}",
                "",
                f"- Dominio/subdominio: `{item['expected_domain']}/{item.get('expected_subdomain') or 'n/a'}`",
                f"- Recomendaciones generadas: `{len(item.get('recommendations') or [])}`",
                "",
            ]
        )
        for recommendation in item.get("recommendations") or []:
            lines.extend(
                [
                    f"#### {recommendation.get('title')}",
                    "",
                    f"- Gap: {recommendation.get('gap_detectado')}",
                    f"- Modulo sugerido: {recommendation.get('asignatura_o_modulo_sugerido')}",
                    f"- Accion curricular: {recommendation.get('accion_curricular')}",
                    f"- Prioridad: `{recommendation.get('prioridad')}`",
                    f"- Impacto: `{recommendation.get('nivel_impacto')}`",
                    f"- Confidence: `{recommendation.get('confidence')}`",
                    f"- Justificacion: {recommendation.get('justificacion')}",
                    f"- Explicacion: {recommendation.get('explanation')}",
                    "",
                ]
            )
    lines.extend(
        [
            "## Riesgos Pendientes",
            "",
            "- Las recomendaciones ya son especificas por subdominio, pero la evidencia laboral sigue dependiendo de fallback cuando no hay Gold jobs suficientes.",
            "- Para readiness alto se recomienda conectar senales Gold reales por subdominio y revisar manualmente la matriz humana.",
        ]
    )
    RECOMMENDATION_HARDENING_REPORT.write_text("\n".join(lines), encoding="utf-8")


def write_report(payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# Cross-Domain Curriculum Validation",
        "",
        "## Resumen Ejecutivo",
        "",
        f"- Documentos procesados: `{summary['documents_processed']}`",
        f"- Dominios con evidencia: `{', '.join(summary['domains_with_documents']) or 'ninguno'}`",
        f"- Unidades de evidencia: `{', '.join(summary.get('evidence_units') or []) or 'ninguna'}`",
        f"- Precision aproximada: `{summary['precision_approx']}`",
        f"- Recall aproximado: `{summary['recall_approx']}`",
        f"- Domain contamination rate: `{summary['domain_contamination_rate']}`",
        f"- Recommendation coherence: `{summary['recommendation_coherence']}`",
        f"- Taxonomy coverage: `{summary['taxonomy_coverage']}`",
        f"- Transversal skill separation quality: `{summary['transversal_skill_separation_quality']}`",
        f"- Readiness piloto controlado: `{summary['readiness_for_controlled_pilot']}`",
        "",
    ]
    if not payload["results"]:
        lines.extend(
            [
                "## Bloqueo De Evidencia",
                "",
                "No se encontraron PDFs en `storage/test_microcurriculos/<dominio>/`.",
                "La estructura multi-dominio fue creada, pero el motor no puede afirmar readiness transversal sin microcurriculos reales por dominio.",
                "",
                "Carga PDFs en las carpetas `ti`, `analitica`, `ambiental`, `gerencia`, `educacion` y `derecho`, y vuelve a ejecutar:",
                "",
                "```powershell",
                "python -m microcurriculum_engine.evaluation.cross_domain_validator",
                "```",
                "",
            ]
        )
    lines.extend(["## Metricas Por Dominio", ""])
    for domain, metrics in summary["domain_metrics"].items():
        lines.extend(
            [
                f"### {domain}",
                "",
                f"- Documentos: `{metrics['documents']}`",
                f"- Precision: `{metrics['precision_approx']}`",
                f"- Recall: `{metrics['recall_approx']}`",
                f"- Contaminacion: `{metrics['domain_contamination_rate']}`",
                f"- Coherencia recomendaciones: `{metrics['recommendation_coherence']}`",
                f"- Separacion transversal: `{metrics['transversal_skill_separation_quality']}`",
                "",
            ]
        )
    lines.extend(["## Resultados Por Documento", ""])
    for item in payload["results"]:
        validation = item["validation"]
        lines.extend(
            [
                f"### {item['document_name']}",
                "",
                f"- Dominio esperado: `{item['expected_domain']}`",
                f"- Subdominio esperado: `{item.get('expected_subdomain') or 'n/a'}`",
                f"- Dominio detectado: `{item['detected_domain']}`",
                f"- Confidence: `{item['confidence']}`",
                f"- Skills: {', '.join(item.get('skills') or []) or 'sin skills'}",
                f"- Plataformas: {', '.join(item.get('platforms') or []) or 'sin plataformas'}",
                f"- Falsos positivos: {json.dumps(validation['false_positives'], ensure_ascii=False)}",
                f"- Falsos negativos: {', '.join(validation['false_negatives']) or 'no detectados'}",
                f"- Recomendaciones incoherentes: `{len(validation['incoherent_recommendations'])}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Criterio De Piloto",
            "",
            "- `alto`: minimo 12 documentos, 3+ dominios principales, sin dominios bajos y coherencia >= 0.85.",
            "- `medio`: minimo 3 documentos, 3+ unidades dominio/subdominio y sin dominios de bajo desempeno.",
            "- `bajo`: evidencia suficiente pero uno o mas dominios requieren hardening.",
            "- `blocked_no_cross_domain_evidence`: no hay evidencia multi-dominio real.",
        ]
    )
    REPORT_OUTPUT.write_text("\n".join(lines), encoding="utf-8")


def run(input_root: Path = INPUT_ROOT) -> dict[str, Any]:
    ensure_structure(input_root)
    documents = iter_documents(input_root)
    results = [evaluate_document(path, expected_domain, expected_subdomain) for path, expected_domain, expected_subdomain in documents]
    payload = {
        "input_root": str(input_root),
        "summary": aggregate(results, input_root),
        "results": results,
    }
    JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    write_human_matrix(results)
    write_recommendation_matrix(results)
    write_report(payload)
    write_recommendation_hardening_report(payload)
    print(
        json.dumps(
            {
                "documents_processed": payload["summary"]["documents_processed"],
                "domains_with_documents": payload["summary"]["domains_with_documents"],
                "readiness": payload["summary"]["readiness_for_controlled_pilot"],
                "json_output": str(JSON_OUTPUT),
                "report_output": str(REPORT_OUTPUT),
                "human_matrix": str(HUMAN_MATRIX_OUTPUT),
                "recommendation_matrix": str(RECOMMENDATION_MATRIX_OUTPUT),
            },
            ensure_ascii=False,
        )
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run cross-domain QA validation for microcurriculum intelligence.")
    parser.add_argument("--input-root", default=str(INPUT_ROOT))
    args = parser.parse_args()
    run(Path(args.input_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
