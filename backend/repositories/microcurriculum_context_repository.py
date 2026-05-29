from __future__ import annotations

from typing import Any

from backend.repositories.base import fetch_one, relation_exists


def fetch_program_context(
    especializacion_id: int,
    *,
    specialization_name: str | None = None,
    db_name: str | None = None,
) -> dict[str, Any] | None:
    if not relation_exists("public.microcurriculum_program_contexts", db_name=db_name):
        return None
    row = fetch_one(
        """
        SELECT
            specialization_id,
            specialization_name,
            source_directory,
            documents_processed,
            detected_domain,
            detected_subdomain,
            confidence,
            subjects,
            technical_skills,
            transversal_skills,
            methodologies,
            tools,
            platforms,
            technologies,
            bibliography,
            keywords,
            occupational_profiles,
            real_market_gaps,
            strengthening_areas,
            redundancies,
            labor_roles,
            benchmarking,
            scores,
            executive_narrative,
            indexed_at,
            updated_at
        FROM public.microcurriculum_program_contexts
        WHERE specialization_id = %s
           OR (
                %s <> ''
                AND lower(unaccent(specialization_name)) = lower(unaccent(%s))
           )
        ORDER BY CASE WHEN specialization_id = %s THEN 0 ELSE 1 END, updated_at DESC
        LIMIT 1
        """,
        (especializacion_id, specialization_name or "", specialization_name or "", especializacion_id),
        db_name=db_name,
    )
    return dict(row) if row else None
