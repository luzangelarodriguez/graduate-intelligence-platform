from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from psycopg2.extras import Json

from backend.db import get_conn


SCHEMA_PATH = Path("database/enterprise_labor_intelligence_schema.sql")


def apply_schema(conn) -> None:
    with SCHEMA_PATH.open("r", encoding="utf-8") as fh, conn.cursor() as cur:
        cur.execute(fh.read())


def new_run_id() -> str:
    return f"micro_{uuid.uuid4().hex[:12]}"


def persist_result(result: dict[str, Any], *, db_name: str | None = None) -> int | None:
    try:
        with get_conn(db_name=db_name) as conn:
            apply_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.microcurriculo_processing_runs (
                        run_id, source_document, status, finished_at, metadata
                    )
                    VALUES (%s, %s, %s, now(), %s)
                    ON CONFLICT (run_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        finished_at = EXCLUDED.finished_at,
                        metadata = EXCLUDED.metadata
                    """,
                    (
                        result["run_id"],
                        result["document"]["source_document"],
                        "completed",
                        Json(result.get("metadata") or {}),
                    ),
                )
                parsed = result["parsed"]
                prediction = result["domain_prediction"]
                scores = result["scores"]
                cur.execute(
                    """
                    INSERT INTO public.microcurriculos (
                        run_id, programa, asignatura, semestre, creditos, source_document,
                        stored_path, document_hash, extraction_method, clean_text,
                        detected_domain, domain_confidence, confidence_score, lineage, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (document_hash) DO UPDATE SET
                        run_id = EXCLUDED.run_id,
                        programa = EXCLUDED.programa,
                        asignatura = EXCLUDED.asignatura,
                        semestre = EXCLUDED.semestre,
                        creditos = EXCLUDED.creditos,
                        clean_text = EXCLUDED.clean_text,
                        detected_domain = EXCLUDED.detected_domain,
                        domain_confidence = EXCLUDED.domain_confidence,
                        confidence_score = EXCLUDED.confidence_score,
                        lineage = EXCLUDED.lineage,
                        metadata = EXCLUDED.metadata,
                        updated_at = now()
                    RETURNING id
                    """,
                    (
                        result["run_id"],
                        parsed.get("programa"),
                        parsed.get("asignatura"),
                        parsed.get("semestre"),
                        parsed.get("creditos"),
                        result["document"]["source_document"],
                        result["document"]["stored_path"],
                        result["document"]["content_hash"],
                        result["document"]["extraction_method"],
                        result["document"]["clean_text"],
                        prediction["domain"],
                        prediction["confidence"],
                        scores["pertinencia_curricular"],
                        Json(result["lineage"]),
                        Json(result.get("metadata") or {}),
                    ),
                )
                micro_id = int(cur.fetchone()["id"])
                cur.execute("DELETE FROM public.microcurriculo_asignaturas WHERE microcurriculo_id = %s", (micro_id,))
                cur.execute("DELETE FROM public.microcurriculo_competencias WHERE microcurriculo_id = %s", (micro_id,))
                cur.execute("DELETE FROM public.microcurriculo_skills WHERE microcurriculo_id = %s", (micro_id,))
                cur.execute("DELETE FROM public.microcurriculo_plataformas WHERE microcurriculo_id = %s", (micro_id,))
                cur.execute("DELETE FROM public.microcurriculo_herramientas WHERE microcurriculo_id = %s", (micro_id,))
                cur.execute("DELETE FROM public.microcurriculo_embeddings WHERE microcurriculo_id = %s", (micro_id,))
                cur.execute("DELETE FROM public.microcurriculo_market_gaps WHERE microcurriculo_id = %s", (micro_id,))
                cur.execute("DELETE FROM public.microcurriculo_recommendations WHERE microcurriculo_id = %s", (micro_id,))
                cur.execute(
                    """
                    INSERT INTO public.microcurriculo_asignaturas (
                        microcurriculo_id, nombre, semestre, creditos, contenidos,
                        metodologias, bibliografia, source_document, confidence_score, lineage
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        micro_id,
                        parsed.get("asignatura") or "Microcurriculo",
                        parsed.get("semestre"),
                        parsed.get("creditos"),
                        Json(parsed.get("contenidos") or []),
                        Json(parsed.get("metodologias") or []),
                        Json(parsed.get("bibliografia") or []),
                        result["document"]["source_document"],
                        0.82,
                        Json(result["lineage"]),
                    ),
                )
                for competencia in [*parsed.get("competencias", []), *parsed.get("resultados_aprendizaje", [])]:
                    cur.execute(
                        """
                        INSERT INTO public.microcurriculo_competencias (
                            microcurriculo_id, competencia_text, competencia_type,
                            confidence_score, source_document, lineage
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (micro_id, competencia, "competencia", 0.78, result["document"]["source_document"], Json(result["lineage"])),
                    )
                for skill in result["skills"]:
                    cur.execute(
                        """
                        INSERT INTO public.microcurriculo_skills (
                            microcurriculo_id, skill_original, skill_normalized, skill_domain,
                            tipo_skill, confidence_score, source_document, lineage
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (microcurriculo_id, skill_normalized, tipo_skill) DO NOTHING
                        """,
                        (
                            micro_id,
                            skill.get("skill_original"),
                            skill.get("skill_normalized"),
                            skill.get("skill_domain"),
                            skill.get("tipo_skill"),
                            skill.get("confianza_extraccion", 0),
                            result["document"]["source_document"],
                            Json(result["lineage"]),
                        ),
                    )
                    if skill.get("tipo_skill") == "plataforma":
                        cur.execute(
                            """
                            INSERT INTO public.microcurriculo_plataformas (
                                microcurriculo_id, plataforma, plataforma_normalized,
                                confidence_score, source_document, lineage
                            )
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (microcurriculo_id, plataforma_normalized) DO NOTHING
                            """,
                            (micro_id, skill["skill_original"], skill["skill_normalized"], skill.get("confianza_extraccion", 0), result["document"]["source_document"], Json(result["lineage"])),
                        )
                    if skill.get("tipo_skill") in {"herramienta", "framework", "metodologia", "tecnica"}:
                        cur.execute(
                            """
                            INSERT INTO public.microcurriculo_herramientas (
                                microcurriculo_id, herramienta, herramienta_normalized,
                                tipo, confidence_score, source_document, lineage
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (microcurriculo_id, herramienta_normalized) DO NOTHING
                            """,
                            (micro_id, skill["skill_original"], skill["skill_normalized"], skill.get("tipo_skill"), skill.get("confianza_extraccion", 0), result["document"]["source_document"], Json(result["lineage"])),
                        )
                for gap in result["gaps"]["missing_skills"]:
                    cur.execute(
                        """
                        INSERT INTO public.microcurriculo_market_gaps (
                            microcurriculo_id, gap_type, skill_normalized, severity,
                            demand_count, confidence_score, evidence, source_document, lineage
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            micro_id,
                            "missing_skill",
                            gap,
                            "high" if result["market_comparison"]["demand_counts"].get(gap, 0) >= 3 else "medium",
                            result["market_comparison"]["demand_counts"].get(gap, 0),
                            0.76,
                            Json(result["market_comparison"]),
                            result["document"]["source_document"],
                            Json(result["lineage"]),
                        ),
                    )
                for recommendation in result["recommendations"]:
                    cur.execute(
                        """
                        INSERT INTO public.microcurriculo_recommendations (
                            microcurriculo_id, recommendation_type, title, recommendation_text,
                            confidence_score, evidence, source_document, lineage
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            micro_id,
                            recommendation["recommendation_type"],
                            recommendation["title"],
                            recommendation["recommendation_text"],
                            recommendation["confidence_score"],
                            Json(recommendation.get("evidence") or {}),
                            result["document"]["source_document"],
                            Json(result["lineage"]),
                        ),
                    )
                for entity_type, payload in result["embeddings"].items():
                    cur.execute(
                        """
                        INSERT INTO public.microcurriculo_embeddings (
                            microcurriculo_id, entity_type, entity_id, model_name,
                            embedding, dimensions, source_document, confidence_score, lineage
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            micro_id,
                            entity_type,
                            entity_type,
                            payload["model_name"],
                            Json(payload["embedding"]),
                            payload["dimensions"],
                            result["document"]["source_document"],
                            0.75,
                            Json(result["lineage"]),
                        ),
                    )
                return micro_id
    except Exception:
        return None


def fetch_microcurriculum(micro_id: int, *, db_name: str | None = None) -> dict[str, Any] | None:
    try:
        with get_conn(db_name=db_name) as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM public.microcurriculos WHERE id = %s", (micro_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception:
        return None


def fetch_child_rows(table: str, micro_id: int, *, db_name: str | None = None) -> list[dict[str, Any]]:
    allowed = {
        "microcurriculo_skills",
        "microcurriculo_market_gaps",
        "microcurriculo_recommendations",
    }
    if table not in allowed:
        return []
    try:
        with get_conn(db_name=db_name) as conn, conn.cursor() as cur:
            cur.execute(f"SELECT * FROM public.{table} WHERE microcurriculo_id = %s ORDER BY id", (micro_id,))
            return [dict(row) for row in cur.fetchall()]
    except Exception:
        return []


def to_jsonable(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str, ensure_ascii=False))
