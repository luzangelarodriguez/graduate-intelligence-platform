from __future__ import annotations

from scrapers.governance.source_reliability import clamp, get_connection


def compute_contamination_rate(source: str) -> float:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*)::int AS total,
                COUNT(*) FILTER (
                    WHERE titulo IS NULL
                       OR length(trim(COALESCE(titulo, ''))) < 4
                       OR lower(COALESCE(titulo, '')) IN ('inicio', 'empleos', 'ofertas')
                       OR length(trim(COALESCE(descripcion, ''))) < 40
                )::int AS contaminated
            FROM public.silver_normalized_jobs
            WHERE source = %s
            """,
            (source,),
        )
        row = cur.fetchone()
    total = int(row["total"] or 0) if row else 0
    contaminated = int(row["contaminated"] or 0) if row else 0
    return clamp(contaminated / total if total else 0.0)


def compute_evidence_quality(source: str) -> dict[str, float]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COALESCE(AVG(confidence_score), 0)::float AS confidence_avg,
                COALESCE(AVG(jsonb_array_length(COALESCE(skills, '[]'::jsonb))), 0)::float AS avg_skills,
                COALESCE(AVG(length(COALESCE(descripcion, ''))), 0)::float AS avg_description_len
            FROM public.silver_normalized_jobs
            WHERE source = %s
            """,
            (source,),
        )
        row = cur.fetchone() or {}
    confidence = float(row.get("confidence_avg") or 0)
    skill_density = min(1.0, float(row.get("avg_skills") or 0) / 8)
    description_quality = min(1.0, float(row.get("avg_description_len") or 0) / 1200)
    contamination = compute_contamination_rate(source)
    quality = confidence * 0.45 + skill_density * 0.25 + description_quality * 0.20 + (1 - contamination) * 0.10
    return {
        "evidence_quality": clamp(quality),
        "confidence_avg": clamp(confidence),
        "skill_density": clamp(skill_density),
        "description_quality": clamp(description_quality),
        "contamination_rate": contamination,
    }
