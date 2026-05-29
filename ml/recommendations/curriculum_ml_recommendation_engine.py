from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.inference.curriculum_market_inference_pipeline import run_program_market_inference  # noqa: E402

RECOMMENDATION_REPORT = ROOT_DIR / "outputs" / "ml_curriculum_recommendations.md"


MODULE_TEMPLATES = {
    "BI & Visualization": "Laboratorio de visualizacion ejecutiva y storytelling con datos",
    "Reporting & KPI": "Modulo de indicadores, reporting corporativo y tableros de gestion",
    "Data Engineering": "Modulo aplicado de ingenieria de datos, ETL/ELT y arquitectura lakehouse",
    "Cloud Analytics": "Modulo de analitica cloud y plataformas modernas de datos",
    "AI Analytics": "Modulo de modelos predictivos, IA aplicada y evaluacion de modelos",
    "Data Governance": "Modulo de gobierno, calidad, linaje y seguridad del dato",
    "Governance": "Modulo de gobierno, calidad, linaje y seguridad del dato",
    "DataOps": "Modulo de DataOps, versionamiento y operacion continua de productos de datos",
    "Enterprise Analytics": "Modulo de analitica empresarial y toma de decisiones basada en evidencia",
}


def _module_for_cluster(cluster: str) -> str:
    return MODULE_TEMPLATES.get(cluster, "Modulo electivo de capacidades emergentes para analitica y datos")


def _action_for_coverage(coverage: str) -> str:
    if coverage == "emerging":
        return "Incorporar como contenido emergente con practica aplicada y criterios de evaluacion."
    if coverage == "missing":
        return "Agregar una unidad curricular explicita y evidencias de desempeno asociadas."
    if coverage == "partial":
        return "Profundizar la cobertura existente con casos reales, herramientas y resultados medibles."
    return "Mantener como fortaleza y actualizar evidencia de mercado periodicamente."


def generate_ml_curriculum_recommendations(
    *,
    program_id: int | str = 0,
    inference_result: dict[str, Any] | None = None,
    include_database: bool = True,
    write_report: bool = True,
) -> dict[str, Any]:
    result = inference_result or run_program_market_inference(program_id=program_id, include_database=include_database, write_reports=True)
    candidates = result["gap_predictions"] or result["skill_predictions"][:8]
    recommendations: list[dict[str, Any]] = []
    for item in candidates[:12]:
        cluster = item["occupational_affinity"]
        recommendations.append(
            {
                "skill": item["skill"],
                "coverage_status": item["coverage_status"],
                "occupational_cluster": cluster,
                "priority": "alta" if item["coverage_status"] in {"missing", "emerging"} else "media",
                "suggested_module": _module_for_cluster(cluster),
                "curriculum_action": _action_for_coverage(item["coverage_status"]),
                "expected_outcome": (
                    f"El estudiante evidencia dominio aplicado de {item['skill']} en contextos de "
                    f"{cluster.lower()} y toma de decisiones basada en datos."
                ),
                "rationale": item["explanation"],
                "confidence": item["prediction_confidence"],
                "explainability": {
                    "predicted_relevance": item["predicted_relevance"],
                    "skill_importance_score": item["skill_importance_score"],
                    "feature_importance": item["feature_importance"],
                    "evidence_sources": item["evidence_sources"],
                },
            }
        )
    payload = {
        "program_id": result["program_id"],
        "specialization_name": result["specialization_name"],
        "recommendations": recommendations,
        "generation_mode": "ml_supervised_semantic_pipeline",
    }
    if write_report:
        write_recommendation_report(payload)
    return payload


def write_recommendation_report(payload: dict[str, Any], path: Path = RECOMMENDATION_REPORT) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# ML Curriculum Recommendations",
        "",
        f"- Programa: {payload['specialization_name']}",
        f"- Recomendaciones: {len(payload['recommendations'])}",
        "",
    ]
    for item in payload["recommendations"]:
        lines.extend(
            [
                f"## {item['skill']}",
                "",
                f"- Prioridad: {item['priority']}",
                f"- Cluster: {item['occupational_cluster']}",
                f"- Modulo sugerido: {item['suggested_module']}",
                f"- Accion curricular: {item['curriculum_action']}",
                f"- Resultado esperado: {item['expected_outcome']}",
                f"- Confianza: {item['confidence']}",
                f"- Justificacion: {item['rationale']}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate ML curriculum recommendations.")
    parser.add_argument("--program-id", default="visual-analytics-big-data")
    parser.add_argument("--no-db", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            generate_ml_curriculum_recommendations(program_id=args.program_id, include_database=not args.no_db),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
