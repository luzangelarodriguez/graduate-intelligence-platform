from __future__ import annotations

from typing import Any

from backend.repositories import matches_repository, programas_repository, skills_repository
from backend.repositories.base import pick_relation
from backend.services.normalization_service import normalize_program_row, normalize_skill_row, safe_float


def ml_program_metric_map(*, db_name: str | None = None) -> dict[int, dict[str, Any]]:
    relation = matches_repository.match_relation_name(db_name=db_name)
    if relation != "vw_latest_ml_program_job_matches":
        return {}
    metrics: dict[int, dict[str, Any]] = {}
    for row in matches_repository.fetch_ml_program_metric_rows(relation, db_name=db_name):
        metrics[int(row["especializacion_id"])] = {
            "promedio_match_mercado": safe_float(row.get("promedio_match_mercado")),
            "porcentaje_match": safe_float(row.get("promedio_match_mercado")),
            "max_match_mercado": safe_float(row.get("max_match_mercado")),
            "total_empleos_relacionados": int(row.get("total_empleos_relacionados", 0) or 0),
        }
    return metrics


def list_programs_base(*, db_name: str | None = None) -> list[dict[str, Any]]:
    metrics_relation = pick_relation(("mv_dashboard_especializacion", "vw_dashboard_especializacion"), db_name=db_name)
    rows = programas_repository.fetch_program_rows_with_metrics(metrics_relation=metrics_relation, db_name=db_name)
    if not rows:
        rows = programas_repository.fetch_fallback_program_rows(db_name=db_name)
    ml_metrics = ml_program_metric_map(db_name=db_name)
    programs: list[dict[str, Any]] = []
    for row in rows:
        normalized = normalize_program_row(row)
        normalized.update(ml_metrics.get(int(normalized["especializacion_id"]), {}))
        programs.append(normalized)
    return programs


def global_kpis(programs: list[dict[str, Any]], *, db_name: str | None = None) -> dict[str, Any]:
    relation = matches_repository.match_relation_name(db_name=db_name)
    total_jobs = matches_repository.count_related_jobs(relation, db_name=db_name)
    total_market_skills = skills_repository.count_market_skills(db_name=db_name)
    return {
        "total_programas": len(programs),
        "total_skills_programa": sum(int(row.get("total_skills_programa", 0) or 0) for row in programs),
        "total_skills_mercado": total_market_skills,
        "total_empleos": total_jobs,
        "total_empleos_relacionados": total_jobs,
        "promedio_global_match": round(sum(safe_float(row.get("promedio_match_mercado", 0)) for row in programs) / len(programs), 2) if programs else 0,
        "mejor_match_global": round(max((safe_float(row.get("max_match_mercado", 0)) for row in programs), default=0), 2),
    }


def alignment_level(match: float) -> tuple[str, str]:
    if match >= 75:
        return "Alta", "El programa está bien alineado con el mercado y ya cubre una parte importante de la demanda."
    if match >= 45:
        return "Media", "Hay una base razonable de alineación, pero todavía existen brechas que conviene cerrar."
    return "Baja", "La cobertura frente al mercado es limitada y requiere refuerzo para mejorar la empleabilidad."


def match_band(match: float) -> tuple[str, str, str]:
    if match >= 70:
        return "Alta", "good", "alineacion alta"
    if match >= 40:
        return "Media", "warn", "alineacion media"
    return "Baja", "bad", "alineacion baja"


def normalize_skill_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_skill_row(row) for row in rows]


def program_context_dashboard(
    program: dict[str, Any],
    *,
    matches: list[dict[str, Any]],
    missing_skills: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    alignment = round(safe_float(program.get("promedio_match_mercado", 0)), 2)
    max_match = round(max((safe_float(row.get("porcentaje_match", 0)) for row in matches), default=safe_float(program.get("max_match_mercado", 0))), 2)
    total_program_skills = int(program.get("total_skills_programa", 0) or 0)
    total_tools = int(program.get("total_herramientas", 0) or 0)
    digital_coverage = round((total_tools * 100.0 / max(total_program_skills, 1)), 2) if total_program_skills else 0
    roles_high_demand = sum(1 for row in matches if safe_float(row.get("porcentaje_match", 0)) >= 50)
    missing_count = len(missing_skills)
    status, status_detail = alignment_level(alignment)
    update_signal = "Alta" if alignment >= 60 and missing_count <= 5 else "Media" if alignment >= 40 else "Crítica"

    if missing_count >= 10:
        ai_signal = "Brecha emergente: el mercado está pidiendo competencias que el programa no cubre con suficiente fuerza."
    elif alignment >= 60:
        ai_signal = "Programa con evidencia fuerte de pertinencia laboral y oportunidades puntuales de ajuste."
    else:
        ai_signal = "Señal IA: conviene revisar resultados de aprendizaje, herramientas y profundidad técnica."

    trend_label = "Tendencia creciente" if max_match >= alignment else "Tendencia estable"
    recommendations_text = [
        "Priorizar las skills faltantes con mayor frecuencia en vacantes relacionadas.",
        "Contrastar resultados de aprendizaje contra roles laborales con match superior al 50%.",
        "Actualizar herramientas digitales cuando la cobertura sea inferior al 35%.",
    ]
    if recommendations:
        recommendations_text.insert(0, str(recommendations[0].get("reason", "") or "Revisar programas complementarios con evidencia fuerte."))

    return {
        "program_id": int(program.get("especializacion_id", 0) or 0),
        "program": program,
        "kpis": {
            "alignment_score": alignment,
            "missing_critical_skills": missing_count,
            "high_demand_roles": roles_high_demand,
            "employability_trend": max_match,
            "digital_coverage": digital_coverage,
            "curricular_update_signal": update_signal,
        },
        "status": {
            "curricular_status": status,
            "curricular_status_detail": status_detail,
            "ai_signal": ai_signal,
            "trend_label": trend_label,
        },
        "missing_skills": normalize_skill_rows(missing_skills),
        "matches": matches,
        "recommendations": recommendations,
        "insights": {
            "detected": f"El programa registra {alignment:.1f}% de alineación laboral con {len(matches)} roles relacionados.",
            "ai_recommends": recommendations_text,
            "emerging_gap": missing_skills[0]["nombre"] if missing_skills else "Sin brechas críticas detectadas",
            "critical_signal": update_signal,
        },
    }
