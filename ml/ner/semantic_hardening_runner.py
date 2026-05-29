from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from microcurriculum_engine.evaluation.functional_ai_validator import run as run_functional_validation
from ml.ner.build_curriculum_gold_dataset import DEFAULT_OUTPUT as GOLD_DATASET_OUTPUT
from ml.ner.build_curriculum_gold_dataset import build_gold_dataset


BASELINE_OUTPUT = Path("outputs/ml_validation_results.json")
COMPARISON_OUTPUT = Path("outputs/semantic_metrics_comparison.json")
REPORT_OUTPUT = Path("outputs/semantic_hardening_report.md")

PRE_HARDENING_BASELINE = {
    "documents_processed": 6,
    "unique_document_hashes": 1,
    "precision_approx": 0.8333,
    "recall_approx": 0.0833,
    "domain_contamination_rate": 0.1667,
    "recommendation_coherence_score": 1.0,
    "taxonomy_coverage": 0.375,
    "contextual_understanding_score": 0.65,
    "recommendation_quality_score": 0.94,
    "domain_accuracy_heuristic": 1.0,
    "readiness_for_university_pilot": "bajo",
    "missing_taxonomies": [
        ".net",
        "android studio",
        "cloud",
        "eclipse",
        "google cloud",
        "innovacion",
        "java",
        "mariadb",
        "netbeans",
        "php",
    ],
    "contamination_events": [{"skill": "liderazgo", "skill_domain": "management", "predicted_domain": "ti"}],
    "overclassification_count": 0,
    "underclassification_count": 6,
}


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {}
    return dict(payload.get("summary") or {})


def _looks_pre_hardening(summary: dict[str, Any]) -> bool:
    if not summary:
        return False
    return (
        float(summary.get("recall_approx", 0)) < 0.5
        or float(summary.get("taxonomy_coverage", 0)) < 0.7
        or float(summary.get("domain_contamination_rate", 0)) > 0.01
    )


def select_baseline() -> tuple[dict[str, Any], str]:
    current = _summary(_load_json(BASELINE_OUTPUT))
    previous_comparison = _load_json(COMPARISON_OUTPUT) or {}
    previous_before = dict(previous_comparison.get("before") or {})
    if _looks_pre_hardening(current):
        return current, str(BASELINE_OUTPUT)
    if _looks_pre_hardening(previous_before):
        return previous_before, f"{COMPARISON_OUTPUT}:before"
    return dict(PRE_HARDENING_BASELINE), "embedded_pre_hardening_baseline"


def _delta(before: dict[str, Any], after: dict[str, Any], metric: str) -> float | None:
    try:
        return round(float(after.get(metric, 0)) - float(before.get(metric, 0)), 4)
    except Exception:
        return None


def write_report(comparison: dict[str, Any]) -> None:
    before = comparison["before"]
    after = comparison["after"]
    gold = comparison["gold_dataset"]
    lines = [
        "# Curriculum Semantic Hardening",
        "",
        "## Resumen Ejecutivo",
        "",
        "Se agrego una capa NER curricular hibrida basada en reglas, EntityRuler opcional y patrones contextuales para recuperar tecnologias implicitas en microcurriculos.",
        "",
        f"- Baseline comparativo: `{comparison.get('baseline_source')}`.",
        f"- Gold dataset semilla: `{gold['rows_generated']}` entidades candidatas en `{gold['output']}`.",
        f"- Documentos escaneados para Gold dataset: `{gold['documents_scanned']}`.",
        f"- Precision antes/despues: `{before.get('precision_approx')}` -> `{after.get('precision_approx')}`.",
        f"- Recall antes/despues: `{before.get('recall_approx')}` -> `{after.get('recall_approx')}`.",
        f"- Contaminacion disciplinar antes/despues: `{before.get('domain_contamination_rate')}` -> `{after.get('domain_contamination_rate')}`.",
        f"- Taxonomy coverage antes/despues: `{before.get('taxonomy_coverage')}` -> `{after.get('taxonomy_coverage')}`.",
        f"- Contextual understanding antes/despues: `{before.get('contextual_understanding_score')}` -> `{after.get('contextual_understanding_score')}`.",
        f"- Readiness piloto universitario: `{after.get('readiness_for_university_pilot')}`.",
        "",
        "## Cambios Implementados",
        "",
        "- Taxonomia TI ampliada con lenguajes, frameworks, bases de datos, cloud, DevOps, IDEs y herramientas de analitica.",
        "- Dominio `transversal` creado para liderazgo, pensamiento critico y trabajo en equipo.",
        "- NER curricular en `ml/ner/` con separacion de tipos de entidad.",
        "- Inferencia contextual para tecnologias implicitas como desarrollo movil, nube, API, backend, IDE y CI/CD.",
        "- Gold dataset semilla en `ml/datasets/curriculum_gold_dataset.csv` para revision humana posterior.",
        "",
        "## Riesgos",
        "",
        "- El Gold dataset generado sigue siendo automatico; requiere curaduria humana antes de entrenar un NER supervisado.",
        "- Los PDFs disponibles parecen duplicados por hash, por lo que la validacion mejora recall funcional pero no prueba diversidad disciplinar real.",
        "- La inferencia contextual aumenta recall y debe seguir monitoreandose con muestras ambientales, juridicas y gerenciales para evitar sesgo TI.",
        "",
        "## Siguientes Pasos",
        "",
        "1. Anotar manualmente 100-300 fragmentos por dominio en el Gold dataset.",
        "2. Entrenar un NER supervisado con spaCy cuando exista volumen validado.",
        "3. Calibrar confidence con falsos positivos por disciplina.",
        "4. Agregar muestras reales no TI para medir contaminacion fuera de Ingenieria de Software.",
    ]
    REPORT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUTPUT.write_text("\n".join(lines), encoding="utf-8")


def run(input_dir: Path) -> dict[str, Any]:
    before, baseline_source = select_baseline()
    gold_summary = build_gold_dataset([input_dir], GOLD_DATASET_OUTPUT)
    validation_payload = run_functional_validation(input_dir)
    after = _summary(validation_payload)
    comparison = {
        "before": before,
        "after": after,
        "deltas": {
            metric: _delta(before, after, metric)
            for metric in (
                "precision_approx",
                "recall_approx",
                "domain_contamination_rate",
                "taxonomy_coverage",
                "contextual_understanding_score",
                "recommendation_quality_score",
            )
        },
        "gold_dataset": gold_summary,
        "baseline_source": baseline_source,
        "outputs": {
            "functional_validation_json": str(BASELINE_OUTPUT),
            "comparison_json": str(COMPARISON_OUTPUT),
            "report": str(REPORT_OUTPUT),
        },
    }
    COMPARISON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    COMPARISON_OUTPUT.write_text(json.dumps(comparison, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    write_report(comparison)
    print(json.dumps(comparison["deltas"], ensure_ascii=False))
    return comparison


def main() -> int:
    parser = argparse.ArgumentParser(description="Run curriculum semantic hardening and compare validation metrics.")
    parser.add_argument("--input-dir", default="storage/microcurriculos")
    args = parser.parse_args()
    run(Path(args.input_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
