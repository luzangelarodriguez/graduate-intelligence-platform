from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from backend.repositories.base import fetch_all


@dataclass(frozen=True)
class MarketComparison:
    market_skills: list[str]
    shared_skills: list[str]
    missing_skills: list[str]
    weak_skills: list[str]
    obsolete_skills: list[str]
    demand_counts: dict[str, int]
    evidence_jobs: list[dict[str, Any]]
    coverage: float


def load_market_skills(domain: str, *, db_name: str | None = None, limit: int = 30) -> tuple[list[str], dict[str, int], list[dict[str, Any]]]:
    try:
        rows = fetch_all(
            """
            SELECT
                es.skill_normalized,
                COUNT(*) AS demand_count
            FROM public.empleo_skills es
            JOIN public.empleos e ON e.id = es.empleo_id
            WHERE (%s = '' OR e.dominio = %s OR es.skill_domain = %s)
              AND es.skill_normalized IS NOT NULL
            GROUP BY es.skill_normalized
            ORDER BY COUNT(*) DESC, es.skill_normalized
            LIMIT %s
            """,
            (domain or "", domain or "", domain or "", limit),
            db_name=db_name,
        )
        skills = [str(row["skill_normalized"]) for row in rows]
        counts = {str(row["skill_normalized"]): int(row["demand_count"] or 0) for row in rows}
        jobs = fetch_all(
            """
            SELECT id, titulo, empresa, ciudad, dominio, url, confidence_score
            FROM public.empleos
            WHERE (%s = '' OR dominio = %s)
            ORDER BY confidence_score DESC NULLS LAST, created_at DESC
            LIMIT 8
            """,
            (domain or "", domain or ""),
            db_name=db_name,
        )
        return skills, counts, jobs
    except Exception:
        return [], {}, []


def fallback_market_skills(domain: str) -> list[str]:
    by_domain = {
        "ti": ["python", "sql", "docker", "devops", "rest api", "javascript", "react"],
        "analitica": ["sql", "power bi", "python", "big data", "business intelligence", "visual analytics"],
        "ambiental": ["sostenibilidad", "esg", "iso 14001", "huella de carbono", "economia circular"],
        "energia": ["eficiencia energetica", "energias renovables", "iso 50001", "auditoria energetica"],
        "legal-tech": ["derecho digital", "proteccion de datos", "compliance", "contratos tecnologicos"],
        "management": ["liderazgo", "gestion de proyectos", "scrum", "agile"],
        "finanzas": ["excel avanzado", "power bi financiero", "modelacion financiera", "analisis de escenarios", "indicadores financieros"],
    }
    return by_domain.get(domain, ["liderazgo", "gestion de proyectos", "pensamiento critico"])


def compare_microcurriculum_to_market(
    micro_skills: list[str],
    *,
    domain: str,
    db_name: str | None = None,
    market_skills: list[str] | None = None,
) -> MarketComparison:
    normalized_micro = sorted({skill for skill in micro_skills if skill})
    loaded_market, demand_counts, jobs = load_market_skills(domain, db_name=db_name)
    selected_market = market_skills or loaded_market or fallback_market_skills(domain)
    demand = Counter({skill: demand_counts.get(skill, 1) for skill in selected_market})
    shared = sorted(set(normalized_micro) & set(selected_market))
    missing = sorted(set(selected_market) - set(normalized_micro), key=lambda skill: (-demand[skill], skill))
    weak = [skill for skill in shared if demand[skill] <= 1]
    obsolete = [skill for skill in normalized_micro if skill not in selected_market and skill not in {"liderazgo", "pensamiento critico", "trabajo en equipo"}]
    coverage = round(len(shared) / max(1, len(set(selected_market))), 4)
    return MarketComparison(
        market_skills=selected_market,
        shared_skills=shared,
        missing_skills=missing,
        weak_skills=weak,
        obsolete_skills=obsolete,
        demand_counts=dict(demand),
        evidence_jobs=jobs,
        coverage=coverage,
    )
