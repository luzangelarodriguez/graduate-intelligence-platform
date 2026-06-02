from __future__ import annotations

import os
import re
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse

from backend.repositories import empleos_repository, matches_repository, microcurriculum_context_repository, programas_repository, skills_repository
from backend.repositories.base import fetch_all, fetch_one
from backend.services import alumni_service, dashboard_service, recommendation_service
from backend.services.normalization_service import basic_text_key, normalize_program_row
from .academic_job_acquisition import build_academic_job_acquisition_intelligence
from ml.inference.domain_classifier import input_hash, predict_domain, prediction_to_dict
from ml.clustering.labor_cluster_engine import build_labor_occupational_clusters, cluster_to_dict
from ml.curriculum.curriculum_market_gap_engine import build_curriculum_market_gap_map, gap_map_to_dict
from ml.inference.curriculum_market_inference_pipeline import run_program_market_inference
from ml.labor.market_skill_intelligence_engine import build_market_skill_intelligence_map, market_skill_intelligence_to_dict
from ml.recommendations.curriculum_ml_recommendation_engine import generate_ml_curriculum_recommendations
from ml.registry import register_prediction
from microcurriculum_engine.pipelines.process_microcurriculum import process_microcurriculum
from microcurriculum_engine.rewrite import rewrite_microcurriculum, rewrite_microcurriculum_batch
from microcurriculum_engine.storage.repository import fetch_child_rows, fetch_microcurriculum, to_jsonable

from .schemas import AlumniRegistrationIn, AlumniRegistrationOut, DashboardKpisResponse, HealthResponse, Page
from .auth import require_current_user

router = APIRouter()

DB_NAME = os.getenv("DB_NAME")
MAX_LIMIT = 100

AREA_KEYWORDS_BY_KEY = {
    "datos": ("datos", "data", "analytics", "analitica", "bi", "business intelligence"),
    "tecnologia": ("software", "tecnologia", "cloud", "devops", "arquitectura", "sistemas"),
    "negocios": ("negocio", "gerencia", "marketing", "ventas", "finanzas", "gestion"),
    "operaciones": ("operaciones", "proyectos", "procesos", "calidad", "riesgo", "cumplimiento"),
}

MICRO_OUTPUTS_DIR = Path("outputs")
MICRO_DEMO_RESULTS = MICRO_OUTPUTS_DIR / "cross_domain_validation_results.json"
MICRO_STORAGE_DIR = Path("storage/microcurriculos")
MICRO_TEST_STORAGE_DIR = Path("storage/test_microcurriculos")
MICRO_SEARCH_DIRS = (MICRO_STORAGE_DIR, MICRO_TEST_STORAGE_DIR)
SUPPORTED_MICRO_EXTENSIONS = {".pdf", ".docx", ".txt"}
REWRITE_OUTPUT_DIR = Path("outputs/rewritten_microcurricula")
VISUAL_ANALYTICS_NAME = "Especialización en Visual Analytics y Big Data"
VISUAL_ANALYTICS_FALLBACK_ID = "visual-analytics-big-data"
VISUAL_ANALYTICS_TERMS = {
    "power bi",
    "tableau",
    "sql",
    "python",
    "r",
    "big data",
    "etl",
    "machine learning",
    "data visualization",
    "dashboards",
    "storytelling with data",
    "data governance",
    "data warehousing",
    "cloud analytics",
    "azure",
    "aws",
    "google cloud",
    "spark",
    "hadoop",
    "databricks",
    "snowflake",
    "power platform",
}


def _score_value(scores: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return round(float(scores.get(key, default) or default), 4)
    except Exception:
        return default


def _recommendation_text(item: dict[str, Any]) -> str:
    return str(item.get("recommendation_text") or item.get("text") or "")


def _microcurriculum_entities(result: dict[str, Any]) -> list[dict[str, Any]]:
    from ml.ner import extract_curriculum_entities

    return jsonable_encoder(extract_curriculum_entities(result.get("document", {}).get("clean_text") or ""))


def _group_skill_values(skills: list[dict[str, Any]], types: set[str]) -> list[str]:
    values = [
        str(item.get("skill_normalized") or "")
        for item in skills
        if str(item.get("tipo_skill") or "") in types and item.get("skill_normalized")
    ]
    return sorted(set(values))


def _entity_value(item: Any) -> str:
    if isinstance(item, dict):
        return str(
            item.get("normalized_skill")
            or item.get("skill_normalized")
            or item.get("entity")
            or item.get("skill")
            or item.get("name")
            or ""
        )
    return str(item or "")


def _unique_values(items: list[Any]) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for item in items:
        value = _entity_value(item).strip()
        key = basic_text_key(value)
        if value and key and key not in seen:
            seen.add(key)
            values.append(value)
    return values


def _merge_unique(*groups: list[Any]) -> list[str]:
    merged: list[Any] = []
    for group in groups:
        merged.extend(group or [])
    return _unique_values(merged)


def classify_gap_status(entity: Any, detected_entities: list[Any], market_signals: list[Any]) -> str:
    """Classify an entity against curriculum evidence and labor-market signals.

    Detected curriculum evidence is never reported as a real market gap. If the
    same entity appears in market signals, it becomes a strengthening area.
    """

    entity_key = basic_text_key(_entity_value(entity))
    if not entity_key:
        return "not_applicable"
    detected_keys = {basic_text_key(_entity_value(item)) for item in detected_entities if _entity_value(item)}
    market_keys = {basic_text_key(_entity_value(item)) for item in market_signals if _entity_value(item)}
    in_curriculum = entity_key in detected_keys
    in_market = entity_key in market_keys
    if in_curriculum and in_market:
        return "strengthening_area"
    if in_curriculum:
        return "detected"
    if in_market:
        return "missing_gap"
    return "not_applicable"


def _normalized_file_key(value: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.casefold()).strip()


def _compact_key(value: str) -> str:
    return _normalized_file_key(value).replace(" ", "")


def _specialization_row(program: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(program.get("especializacion_id") or program.get("id") or ""),
        "nombre": str(program.get("nombre_especializacion") or program.get("nombre") or ""),
        "facultad": str(program.get("facultad") or program.get("rol") or ""),
        "nivel": str(program.get("nivel") or "Especialización"),
        "estado": str(program.get("estado") or "Activo"),
    }


def _list_specializations() -> list[dict[str, Any]]:
    rows = [_specialization_row(item) for item in programs()]
    seen = {_compact_key(item["nombre"]) for item in rows}
    if _compact_key(VISUAL_ANALYTICS_NAME) not in seen:
        rows.append(
            {
                "id": VISUAL_ANALYTICS_FALLBACK_ID,
                "nombre": VISUAL_ANALYTICS_NAME,
                "facultad": "Escuela de Ingeniería y Tecnología",
                "nivel": "Especialización",
                "estado": "Activo",
            }
        )
    return sorted(rows, key=lambda item: item["nombre"].casefold())


def _specialization_by_id(specialization_id: str) -> dict[str, Any] | None:
    for item in _list_specializations():
        if str(item["id"]) == str(specialization_id):
            return item
    try:
        program = program_by_id(int(specialization_id))
    except Exception:
        program = None
    return _specialization_row(program) if program else None


def _folder_similarity_tokens(value: str) -> set[str]:
    stopwords = {"en", "de", "del", "la", "el", "y", "especializacion", "especializacion"}
    return {token for token in _normalized_file_key(value).split() if token and token not in stopwords}


def _documents_for_specialization_name(name: str) -> list[Path]:
    name_key = _compact_key(name)
    name_tokens = _folder_similarity_tokens(name)
    candidate_dirs: list[Path] = []
    for root in MICRO_SEARCH_DIRS:
        if not root.exists():
            continue
        for directory in [root, *[item for item in root.iterdir() if item.is_dir()]]:
            dir_key = _compact_key(directory.name)
            dir_tokens = _folder_similarity_tokens(directory.name)
            if directory == root or dir_key in name_key or name_key in dir_key or len(name_tokens & dir_tokens) >= 2:
                candidate_dirs.append(directory)
    files: list[Path] = []
    for directory in candidate_dirs:
        for path in directory.iterdir():
            if path.is_file() and path.suffix.casefold() in SUPPORTED_MICRO_EXTENSIONS:
                file_key = _compact_key(path.name)
                file_tokens = _folder_similarity_tokens(path.name)
                if any(directory.parent == root for root in MICRO_SEARCH_DIRS):
                    dir_key = _compact_key(directory.name)
                    dir_tokens = _folder_similarity_tokens(directory.name)
                    directory_matches = dir_key in name_key or name_key in dir_key or len(name_tokens & dir_tokens) >= 2
                else:
                    directory_matches = False
                if directory_matches or file_key in name_key or name_key in file_key or len(name_tokens & file_tokens) >= 2:
                    files.append(path)
    return sorted(set(files), key=lambda path: path.name.casefold())


def _document_payload(path: Path) -> dict[str, Any]:
    return {
        "file_name": path.name,
        "path": str(path),
        "extension": path.suffix.casefold(),
        "status": "available",
    }


def _rewrite_download_path(rewrite_id: str) -> Path | None:
    if not REWRITE_OUTPUT_DIR.exists():
        return None
    candidates = [
        REWRITE_OUTPUT_DIR / f"{rewrite_id}.docx",
        REWRITE_OUTPUT_DIR / rewrite_id,
    ]
    candidates.extend(REWRITE_OUTPUT_DIR.glob(f"{rewrite_id}*.docx"))
    for candidate in candidates:
        if candidate.exists() and candidate.is_file() and candidate.suffix.casefold() == ".docx":
            return candidate
    return None


def _visual_analytics_recommendations(detected_values: list[str], real_gaps: list[str], strengthening: list[str]) -> list[dict[str, Any]]:
    detected_keys = {basic_text_key(item) for item in detected_values}
    gap_keys = {basic_text_key(item) for item in real_gaps}
    strengthen_keys = {basic_text_key(item) for item in strengthening}

    def term_status(terms: tuple[str, ...]) -> tuple[list[str], list[str]]:
        gap_terms = [term for term in terms if basic_text_key(term) in gap_keys]
        strengthen_terms = [
            term
            for term in terms
            if basic_text_key(term) in detected_keys or basic_text_key(term) in strengthen_keys
        ]
        return gap_terms, strengthen_terms

    templates = [
        (
            "Analitica avanzada aplicada con Python y R",
            ("python", "r", "machine learning"),
            "Fortalecer analitica avanzada con laboratorios en Python/R, notebooks reproducibles y validacion de modelos predictivos aplicados a datos institucionales.",
            "Laboratorio de analitica avanzada y modelos predictivos",
            "Mayor capacidad para construir evidencia cuantitativa, modelos aplicados y analisis replicables.",
        ),
        (
            "Visualizacion ejecutiva y storytelling con datos",
            ("power bi", "tableau", "dashboards", "storytelling with data"),
            "Incorporar practicas de visualizacion ejecutiva, diseno de dashboards, narrativa con datos y criterios de decision para perfiles directivos.",
            "Taller de visual analytics y storytelling ejecutivo",
            "Mejora la comunicacion de hallazgos y la toma de decisiones basada en datos.",
        ),
        (
            "Gobierno de datos y arquitectura lakehouse",
            ("data governance", "data warehousing", "databricks", "snowflake"),
            "Reforzar gobierno de datos, calidad, linaje, modelado dimensional y arquitectura lakehouse para escenarios de big data empresarial.",
            "Modulo de gobierno de datos, data warehousing y lakehouse",
            "Reduce brechas entre analisis visual y gestion enterprise de datos.",
        ),
        (
            "Cloud analytics y plataformas modernas de datos",
            ("azure", "aws", "google cloud", "cloud analytics", "spark"),
            "Incluir experiencias guiadas con servicios cloud analytics, procesamiento distribuido y despliegue de pipelines de datos en entornos reales.",
            "Practica de cloud analytics y procesamiento distribuido",
            "Alinea el programa con arquitecturas modernas de analitica escalable.",
        ),
    ]
    recommendations = []
    for title, terms, action, module, impact in templates:
        gap_terms, strengthen_terms = term_status(terms)
        if gap_terms:
            gap_label = f"brecha real: {', '.join(gap_terms)}"
        elif strengthen_terms:
            gap_label = f"area a fortalecer: {', '.join(strengthen_terms)}"
        else:
            gap_label = f"brecha real: {', '.join(terms)}"
        recommendations.append(
            {
                "recommendation_type": "visual_analytics_big_data",
                "title": title,
                "recommendation_text": action,
                "gap_detectado": gap_label,
                "evidencia_curricular": ", ".join(strengthen_terms) or "No se identifico evidencia curricular suficiente.",
                "evidencia_laboral": "Senales priorizadas para visual analytics, big data, inteligencia de negocios y cloud analytics.",
                "asignatura_o_modulo_sugerido": module,
                "accion_curricular": action,
                "prioridad": "alta" if gap_terms else "media",
                "justificacion": "La especializacion requiere evidencia practica y trazable en capacidades analiticas modernas para sostener pertinencia laboral.",
                "nivel_impacto": impact,
                "confidence": 0.86,
                "confidence_score": 0.86,
                "explanation": "Recomendacion especifica para el piloto de Visual Analytics y Big Data.",
                "subdomain": "analitica/visual_analytics_big_data",
            }
        )
    return recommendations


def _consolidate_specialization_analysis(specialization: dict[str, Any], analyses: list[dict[str, Any]]) -> dict[str, Any]:
    detected_entities = [entity for analysis in analyses for entity in analysis.get("detected_entities") or analysis.get("entities") or []]
    detected_values = _merge_unique(
        [entity.get("normalized_skill") or entity.get("entity") for entity in detected_entities],
        *[analysis.get("skills") or [] for analysis in analyses],
    )
    market_signals = _merge_unique(
        list(VISUAL_ANALYTICS_TERMS) if "visual analytics" in _normalized_file_key(specialization["nombre"]) or "big data" in _normalized_file_key(specialization["nombre"]) else [],
        *[analysis.get("real_market_gaps") or analysis.get("market_gaps") or [] for analysis in analyses],
        *[analysis.get("strengthening_areas") or [] for analysis in analyses],
    )
    real_market_gaps = [
        item for item in market_signals if classify_gap_status(item, detected_values, market_signals) == "missing_gap"
    ]
    strengthening_areas = [
        item for item in market_signals if classify_gap_status(item, detected_values, market_signals) == "strengthening_area"
    ]
    scores = [analysis.get("score_percent") or {} for analysis in analyses]
    avg = lambda key: int(round(sum(float(item.get(key, 0) or 0) for item in scores) / max(1, len(scores))))
    score_percent = {
        "pertinencia_curricular": avg("pertinencia_curricular"),
        "cobertura_skills_mercado": avg("cobertura_skills_mercado"),
        "modernizacion_tecnologica": avg("modernizacion_tecnologica"),
        "alineacion_laboral": avg("alineacion_laboral"),
        "riesgo_obsolescencia": avg("riesgo_obsolescencia"),
    }
    detected_domain = "analitica" if _compact_key(specialization["nombre"]) == _compact_key(VISUAL_ANALYTICS_NAME) else (analyses[0].get("detected_domain") if analyses else "")
    detected_subdomain = "analitica/visual_analytics_big_data" if detected_domain == "analitica" else (analyses[0].get("detected_subdomain") if analyses else "")
    confidence = round(sum(float(analysis.get("confidence") or 0) for analysis in analyses) / max(1, len(analyses)), 4)
    recommendations = (
        _visual_analytics_recommendations(detected_values, real_market_gaps, strengthening_areas)
        if detected_subdomain == "analitica/visual_analytics_big_data"
        else [item for analysis in analyses for item in analysis.get("recommendations") or []][:8]
    )
    summary_text = (
        f"La {specialization['nombre']} fue analizada con {len(analyses)} microcurriculo(s). "
        f"El dominio consolidado es {detected_domain} con foco {detected_subdomain}. "
        f"Se identificaron {len(detected_values)} evidencias curriculares, {len(real_market_gaps)} brechas reales "
        f"y {len(strengthening_areas)} areas a fortalecer para comite academico."
    )
    return jsonable_encoder(
        {
            "specialization": specialization["nombre"],
            "documents_processed": len(analyses),
            "detected_domain": detected_domain,
            "detected_subdomain": detected_subdomain,
            "confidence": confidence,
            "detected_entities": detected_entities,
            "technical_skills": _merge_unique(*[analysis.get("technical_skills") or [] for analysis in analyses]),
            "transversal_skills": _merge_unique(*[analysis.get("transversal_skills") or [] for analysis in analyses]),
            "methodologies": _merge_unique(*[analysis.get("methodologies") or [] for analysis in analyses]),
            "tools": _merge_unique(*[analysis.get("tools") or [] for analysis in analyses]),
            "platforms": _merge_unique(*[analysis.get("platforms") or [] for analysis in analyses]),
            "databases": _merge_unique(*[analysis.get("databases") or [] for analysis in analyses]),
            "cloud_providers": _merge_unique(*[analysis.get("cloud_providers") or [] for analysis in analyses]),
            "frameworks": _merge_unique(*[analysis.get("frameworks") or [] for analysis in analyses]),
            "skills": detected_values,
            "real_market_gaps": real_market_gaps,
            "strengthening_areas": strengthening_areas,
            "market_gaps": real_market_gaps,
            "recommendations": recommendations,
            "scores": {key: value / 100 for key, value in score_percent.items()},
            "score_percent": score_percent,
            "documents": [analysis.get("document") for analysis in analyses],
            "executive_summary": {
                "headline": f"Pertinencia curricular {score_percent['pertinencia_curricular']}% para {specialization['nombre']}.",
                "narrative": summary_text,
                "decision_signal": "Listo para revision de comite academico" if score_percent["pertinencia_curricular"] >= 45 else "Requiere priorizacion curricular",
                "top_actions": [item.get("accion_curricular") for item in recommendations[:3]],
            },
        }
    )


def _detected_subdomain(result: dict[str, Any]) -> str:
    recommendations = result.get("recommendations") or []
    for item in recommendations:
        if item.get("subdomain"):
            return str(item["subdomain"])
        evidence = item.get("evidence") or {}
        if evidence.get("subdomain"):
            return str(evidence["subdomain"])
    domain = str(result.get("domain_prediction", {}).get("domain") or "")
    document_name = str(result.get("document", {}).get("filename") or "")
    if domain == "finanzas":
        return "management/finanzas"
    if "aprendizaje" in basic_text_key(document_name):
        return "analitica/inteligencia_artificial"
    if "innovacion" in basic_text_key(document_name):
        return "management/innovacion"
    if domain == "ti":
        return "ti/ingenieria_software"
    return domain


def _executive_summary(payload: dict[str, Any]) -> dict[str, Any]:
    scores = payload.get("scores") or {}
    recommendations = payload.get("recommendations") or []
    domain = payload.get("detected_domain") or "no clasificado"
    subdomain = payload.get("detected_subdomain") or domain
    gaps = payload.get("real_market_gaps") or payload.get("market_gaps") or []
    score = int(round(_score_value(scores, "pertinencia_curricular") * 100))
    top_actions = [
        str(item.get("accion_curricular") or _recommendation_text(item))
        for item in recommendations[:3]
        if item.get("accion_curricular") or _recommendation_text(item)
    ]
    return {
        "headline": f"Pertinencia curricular {score}% para {subdomain}.",
        "narrative": (
            f"El documento fue clasificado en {domain} con foco {subdomain}. "
            f"Se identificaron {len(payload.get('detected_entities') or payload.get('skills') or [])} evidencias curriculares y "
            f"{len(gaps)} brechas reales de mercado priorizables para comite academico."
        ),
        "decision_signal": "Listo para revision de comite" if score >= 45 else "Requiere priorizacion curricular",
        "top_actions": top_actions,
    }


def _format_microcurriculum_analysis(result: dict[str, Any], *, uploaded_filename: str | None = None) -> dict[str, Any]:
    skills = result.get("skills") or []
    scores = result.get("scores") or {}
    recommendations = result.get("recommendations") or []
    entities = _microcurriculum_entities(result)
    detected_values = _unique_values(
        entities
        + [
            {
                "skill_normalized": item.get("skill_normalized"),
                "entity_type": item.get("tipo_skill"),
            }
            for item in skills
        ]
    )
    market_comparison = result.get("market_comparison") or {}
    market_signals = _unique_values(
        list(market_comparison.get("market_skills") or [])
        + list(result.get("gaps", {}).get("missing_skills", []) or [])
    )
    real_market_gaps = [
        value for value in market_signals if classify_gap_status(value, detected_values, market_signals) == "missing_gap"
    ]
    strengthening_areas = [
        value
        for value in market_signals
        if classify_gap_status(value, detected_values, market_signals) == "strengthening_area"
    ]
    payload = {
        "id": result.get("microcurriculo_id") or result.get("run_id"),
        "run_id": result.get("run_id"),
        "document": {
            "filename": uploaded_filename or result.get("document", {}).get("filename"),
            "source_document": result.get("document", {}).get("source_document"),
            "extension": result.get("document", {}).get("extension"),
            "content_hash": result.get("document", {}).get("content_hash"),
            "extraction_method": result.get("document", {}).get("extraction_method"),
            "clean_text_chars": len(result.get("document", {}).get("clean_text") or ""),
        },
        "detected_domain": result.get("domain_prediction", {}).get("domain"),
        "detected_subdomain": _detected_subdomain(result),
        "confidence": result.get("domain_prediction", {}).get("confidence"),
        "confidence_level": result.get("domain_prediction", {}).get("confidence_level"),
        "detected_entities": entities,
        "entities": entities,
        "skills": sorted({str(item.get("skill_normalized")) for item in skills if item.get("skill_normalized")}),
        "technical_skills": _group_skill_values(skills, {"technical_skill", "tecnica", "programming_language"}),
        "transversal_skills": _group_skill_values(skills, {"transversal_skill"}),
        "platforms": _group_skill_values(skills, {"platform", "plataforma"}),
        "tools": _group_skill_values(skills, {"tool", "herramienta"}),
        "databases": _group_skill_values(skills, {"database"}),
        "cloud_providers": _group_skill_values(skills, {"cloud_provider"}),
        "frameworks": _group_skill_values(skills, {"framework"}),
        "methodologies": _group_skill_values(skills, {"methodology", "metodologia"}),
        "real_market_gaps": real_market_gaps,
        "strengthening_areas": strengthening_areas,
        "market_gaps": real_market_gaps,
        "recommendations": recommendations,
        "scores": scores,
        "score_percent": {
            "pertinencia_curricular": int(round(_score_value(scores, "pertinencia_curricular") * 100)),
            "cobertura_skills_mercado": int(round(_score_value(scores, "cobertura_skills_mercado") * 100)),
            "modernizacion_tecnologica": int(round(_score_value(scores, "modernizacion_tecnologica") * 100)),
            "alineacion_laboral": int(round(_score_value(scores, "alineacion_laboral") * 100)),
            "riesgo_obsolescencia": int(round(_score_value(scores, "riesgo_obsolescencia") * 100)),
        },
        "market_comparison": market_comparison,
        "metadata": result.get("metadata") or {},
    }
    payload["executive_summary"] = _executive_summary(payload)
    return jsonable_encoder(payload)


def _read_demo_results() -> dict[str, Any]:
    if not MICRO_DEMO_RESULTS.exists():
        return {"summary": {}, "results": []}
    try:
        import json

        return json.loads(MICRO_DEMO_RESULTS.read_text(encoding="utf-8"))
    except Exception:
        return {"summary": {}, "results": []}


def _demo_case_id(item: dict[str, Any], index: int) -> str:
    return str(item.get("id") or item.get("run_id") or basic_text_key(str(item.get("document_name") or f"case-{index}")))


def _demo_case_to_analysis(item: dict[str, Any], index: int) -> dict[str, Any]:
    recommendations = item.get("recommendations") or []
    scores = item.get("scores") or {}
    entities = item.get("entities") or []
    skills = item.get("skills") or []
    market_signals = _unique_values(item.get("missing_market_skills") or [])
    detected_values = _unique_values(entities + skills)
    real_market_gaps = [
        value for value in market_signals if classify_gap_status(value, detected_values, market_signals) == "missing_gap"
    ]
    strengthening_areas = [
        value
        for value in market_signals
        if classify_gap_status(value, detected_values, market_signals) == "strengthening_area"
    ]
    payload = {
        "id": _demo_case_id(item, index),
        "document": {
            "filename": item.get("document_name"),
            "source_document": item.get("path"),
            "extension": Path(str(item.get("document_name") or "")).suffix,
            "clean_text_chars": (item.get("diagnostics") or {}).get("clean_text_chars"),
        },
        "detected_domain": item.get("detected_domain"),
        "detected_subdomain": "/".join(filter(None, [item.get("expected_domain"), item.get("expected_subdomain")])),
        "confidence": item.get("confidence"),
        "detected_entities": entities,
        "entities": entities,
        "skills": skills,
        "technical_skills": [
            entity.get("normalized_skill")
            for entity in entities
            if entity.get("entity_type") in {"technical_skill", "programming_language"}
        ],
        "transversal_skills": [
            entity.get("normalized_skill")
            for entity in entities
            if entity.get("entity_type") == "transversal_skill"
        ],
        "platforms": item.get("platforms") or [],
        "tools": [
            entity.get("normalized_skill")
            for entity in entities
            if entity.get("entity_type") == "tool"
        ],
        "databases": [
            entity.get("normalized_skill")
            for entity in entities
            if entity.get("entity_type") == "database"
        ],
        "cloud_providers": [
            entity.get("normalized_skill")
            for entity in entities
            if entity.get("entity_type") == "cloud_provider"
        ],
        "frameworks": [
            entity.get("normalized_skill")
            for entity in entities
            if entity.get("entity_type") == "framework"
        ],
        "methodologies": [
            entity.get("normalized_skill")
            for entity in entities
            if entity.get("entity_type") == "methodology"
        ],
        "real_market_gaps": real_market_gaps,
        "strengthening_areas": strengthening_areas,
        "market_gaps": real_market_gaps,
        "recommendations": recommendations,
        "scores": scores,
        "score_percent": {
            "pertinencia_curricular": int(round(_score_value(scores, "pertinencia_curricular") * 100)),
            "cobertura_skills_mercado": int(round(_score_value(scores, "cobertura_skills_mercado") * 100)),
            "modernizacion_tecnologica": int(round(_score_value(scores, "modernizacion_tecnologica") * 100)),
            "alineacion_laboral": int(round(_score_value(scores, "alineacion_laboral") * 100)),
            "riesgo_obsolescencia": int(round(_score_value(scores, "riesgo_obsolescencia") * 100)),
        },
    }
    payload["executive_summary"] = _executive_summary(payload)
    return jsonable_encoder(payload)


def _analysis_to_markdown(analysis: dict[str, Any]) -> str:
    summary = analysis.get("executive_summary") or {}
    lines = [
        "# Informe Ejecutivo De Inteligencia Curricular",
        "",
        f"## {analysis.get('document', {}).get('filename') or 'Documento'}",
        "",
        f"- Dominio detectado: `{analysis.get('detected_domain')}`",
        f"- Subdominio: `{analysis.get('detected_subdomain')}`",
        f"- Confidence: `{analysis.get('confidence')}`",
        f"- Pertinencia curricular: `{analysis.get('score_percent', {}).get('pertinencia_curricular')}%`",
        "",
        "## Resumen Ejecutivo",
        "",
        str(summary.get("headline") or ""),
        "",
        str(summary.get("narrative") or ""),
        "",
        "## Brechas Reales Frente Al Mercado",
        "",
        *[f"- {item}" for item in (analysis.get("real_market_gaps") or analysis.get("market_gaps") or [])[:12]],
        "",
        "## Areas A Fortalecer",
        "",
        *[f"- {item}" for item in (analysis.get("strengthening_areas") or [])[:12]],
        "",
        "## Recomendaciones Curriculares",
        "",
    ]
    for item in analysis.get("recommendations") or []:
        lines.extend(
            [
                f"### {item.get('title')}",
                "",
                f"- Gap: {item.get('gap_detectado')}",
                f"- Accion curricular: {item.get('accion_curricular')}",
                f"- Prioridad: {item.get('prioridad')}",
                f"- Justificacion: {item.get('justificacion')}",
                "",
            ]
        )
    return "\n".join(lines)


def bounded_limit(limit: int) -> int:
    return max(1, min(int(limit or 25), MAX_LIMIT))


def not_found(resource: str, identifier: Any) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource} {identifier} not found")


def page(items: list[dict[str, Any]], *, limit: int, offset: int) -> Page:
    return Page(items=jsonable_encoder(items), count=len(items), limit=limit, offset=max(0, offset))


def programs() -> list[dict[str, Any]]:
    return dashboard_service.list_programs_base(db_name=DB_NAME)


def program_by_id(program_id: int) -> dict[str, Any] | None:
    resolved_id = programas_repository.resolve_program_id(program_id, db_name=DB_NAME)
    row = programas_repository.fetch_program_base_row(resolved_id, db_name=DB_NAME)
    if not row:
        return None
    normalized = normalize_program_row(row)
    for item in programs():
        if int(item.get("especializacion_id") or 0) == resolved_id:
            normalized.update(item)
            break
    normalized["skills"] = dashboard_service.normalize_skill_rows(
        programas_repository.fetch_program_skill_rows(resolved_id, db_name=DB_NAME)
    )
    micro_context = microcurriculum_context_repository.fetch_program_context(
        resolved_id,
        specialization_name=normalized.get("nombre_especializacion"),
        db_name=DB_NAME,
    )
    if micro_context:
        contextual_skills = [
            {"nombre": item.get("name"), "conteo": item.get("frequency", 1)}
            for item in (micro_context.get("technologies") or micro_context.get("technical_skills") or [])
        ]
        scores = micro_context.get("scores") or {}
        normalized.update(
            {
                "curricular_context_source": "microcurriculum_program_contexts",
                "microcurriculum_context": jsonable_encoder(micro_context),
                "skills": contextual_skills,
                "skills_reales_microcurriculo": contextual_skills,
                "competencias_reales_microcurriculo": micro_context.get("transversal_skills") or [],
                "herramientas_reales_microcurriculo": (micro_context.get("tools") or []) + (micro_context.get("platforms") or []),
                "brechas_reales_microcurriculo": micro_context.get("real_market_gaps") or [],
                "areas_a_fortalecer": micro_context.get("strengthening_areas") or [],
                "roles_laborales_contextuales": micro_context.get("labor_roles") or [],
                "benchmarking_contextual": micro_context.get("benchmarking") or [],
                "narrativa_ia": micro_context.get("executive_narrative") or "",
                "total_skills_programa": len(contextual_skills),
                "promedio_match_mercado": float(scores.get("market_skill_coverage") or normalized.get("promedio_match_mercado") or 0),
                "porcentaje_match": float(scores.get("market_skill_coverage") or normalized.get("porcentaje_match") or 0),
                "max_match_mercado": float(scores.get("curricular_relevance") or normalized.get("max_match_mercado") or 0),
                "total_empleos_relacionados": len(micro_context.get("labor_roles") or []),
            }
        )
    return normalized


def role_candidates(program: dict[str, Any], limit: int = 4) -> list[str]:
    values = [
        str(program.get("rol", "") or "").strip(),
        str(program.get("nombre_especializacion", "") or "").strip(),
    ]
    return [value for value in values if value][:limit]


def skill_identity_key(value: str) -> str:
    return basic_text_key(value)


@router.get("/")
def root() -> dict[str, str]:
    return {
        "name": "Graduate Intelligence Platform API",
        "status": "running",
        "docs": "/docs",
        "health": "/api/health",
    }


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        row = fetch_one("SELECT current_database() AS database", db_name=DB_NAME)
        return HealthResponse(
            status="ok",
            service="fastapi-postgresql",
            database="ok",
            db_name=str((row or {}).get("database") or DB_NAME),
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from exc


@router.get("/api/bootstrap")
def bootstrap(_current_user=Depends(require_current_user)) -> dict[str, Any]:
    current_programs = programs()
    return {
        "platform": "Graduate Intelligence Platform",
        "source": "postgresql",
        "summary": dashboard_service.global_kpis(current_programs, db_name=DB_NAME),
        "programas": current_programs[:20],
    }


@router.get("/api/programas", response_model=Page)
def list_programas(
    limit: int = Query(25, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    _current_user=Depends(require_current_user),
) -> Page:
    limit = bounded_limit(limit)
    rows = programs()
    return page(rows[offset : offset + limit], limit=limit, offset=offset)


@router.get("/api/programas/{program_id}")
def get_programa(program_id: int, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    program = program_by_id(program_id)
    if not program:
        raise not_found("programa", program_id)
    return jsonable_encoder(program)


@router.get("/api/specializations")
def list_specializations() -> list[dict[str, Any]]:
    return jsonable_encoder(_list_specializations())


def _program_affinity_key(program: dict[str, Any] | None) -> str:
    if not program:
        return ""
    return _compact_key(str(program.get("nombre_especializacion") or program.get("nombre") or ""))


def _cluster_affinity_for_program(cluster: dict[str, Any], program: dict[str, Any]) -> float:
    program_key = _program_affinity_key(program)
    affinities = cluster.get("specialization_affinity") or {}
    if not program_key:
        return 0.0
    for name, score in affinities.items():
        if _compact_key(str(name)) == program_key:
            return float(score or 0.0)
    if "visualanalyticsbigdata" in program_key:
        return float(affinities.get("Especializacion en Visual Analytics y Big Data") or 0.0)
    if "inteligenciaartificial" in program_key:
        return float(affinities.get("Especializacion en Inteligencia Artificial Aplicada") or 0.0)
    return 0.0


@router.get("/api/labor/clusters")
def list_labor_clusters(_current_user=Depends(require_current_user)) -> dict[str, Any]:
    clusters = [cluster_to_dict(cluster) for cluster in build_labor_occupational_clusters(write_outputs=True)]
    return jsonable_encoder(
        {
            "items": clusters,
            "count": len(clusters),
            "source": "job_posting_only",
            "excludes": ["portal_taxonomy", "search_listing", "filter_page", "unknown"],
        }
    )


@router.get("/api/labor/clusters/{cluster_id}")
def get_labor_cluster(cluster_id: int, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    clusters = [cluster_to_dict(cluster) for cluster in build_labor_occupational_clusters(write_outputs=True)]
    for cluster in clusters:
        if int(cluster.get("id") or 0) == cluster_id:
            return jsonable_encoder(cluster)
    raise not_found("labor_cluster", cluster_id)


@router.get("/api/labor/search-intelligence")
def labor_search_intelligence(
    mode: str = Query("academic_alignment"),
    market_discovery_mode: bool = Query(False),
    keyword_limit: int = Query(24, ge=1, le=80),
    role_limit: int = Query(12, ge=1, le=40),
    _current_user=Depends(require_current_user),
) -> dict[str, Any]:
    base_programs = programs()
    enriched_programs: list[dict[str, Any]] = []
    for program in base_programs:
        resolved_id = int(program.get("especializacion_id") or program.get("id") or 0)
        enriched = program_by_id(resolved_id) if resolved_id else None
        if enriched:
            enriched_programs.append(enriched)
        else:
            enriched_programs.append(program)

    selected_mode = "market_discovery" if market_discovery_mode else mode
    market_intelligence = {}
    curriculum_gap_map = {}
    occupational_clusters = []
    try:
        market_intelligence = market_skill_intelligence_to_dict(
            build_market_skill_intelligence_map(include_database=True, write_output=False)
        )
    except Exception:
        market_intelligence = {}
    try:
        curriculum_gap_map = gap_map_to_dict(build_curriculum_market_gap_map(write_output=False))
    except Exception:
        curriculum_gap_map = {}
    try:
        occupational_clusters = [cluster_to_dict(cluster) for cluster in build_labor_occupational_clusters(write_outputs=False)]
    except Exception:
        occupational_clusters = []

    intelligence = build_academic_job_acquisition_intelligence(
        enriched_programs,
        mode=selected_mode,
        market_skill_intelligence={
            "market_skills": market_intelligence.get("market_skills") or market_intelligence.get("top_skills") or [],
            "emerging_skills": market_intelligence.get("emerging_skills") or [],
            "missing_market_skills": curriculum_gap_map.get("missing_market_skills") or curriculum_gap_map.get("missing_skills") or [],
            "strengthening_areas": curriculum_gap_map.get("strengthening_areas") or [],
            "clusters": occupational_clusters,
        },
        curriculum_gap_map=curriculum_gap_map,
        occupational_clusters=occupational_clusters,
        keyword_limit=keyword_limit,
        role_limit=role_limit,
    )
    intelligence["market_discovery_mode"] = market_discovery_mode
    intelligence["source_context"] = {
        "programs_loaded": len(base_programs),
        "programs_enriched": len(enriched_programs),
        "market_intelligence_available": bool(market_intelligence),
        "curriculum_gap_map_available": bool(curriculum_gap_map),
        "occupational_clusters_available": bool(occupational_clusters),
    }
    return jsonable_encoder(intelligence)


@router.get("/api/programas/{program_id}/occupational-affinity")
def program_occupational_affinity(program_id: int, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    program = program_by_id(program_id)
    if not program:
        raise not_found("programa", program_id)
    clusters = [cluster_to_dict(cluster) for cluster in build_labor_occupational_clusters(write_outputs=True)]
    items = []
    for cluster in clusters:
        affinity = _cluster_affinity_for_program(cluster, program)
        if affinity > 0:
            items.append(
                {
                    "cluster_id": cluster["id"],
                    "cluster_name": cluster["cluster_name"],
                    "affinity_score": round(affinity, 4),
                    "dominant_skills": cluster.get("dominant_skills", []),
                    "dominant_roles": cluster.get("dominant_roles", []),
                    "market_frequency": cluster.get("market_frequency", 0),
                    "growth_signal": cluster.get("growth_signal", "estable"),
                }
            )
    return jsonable_encoder(
        {
            "program_id": program_id,
            "program_name": program.get("nombre_especializacion") or program.get("nombre"),
            "items": sorted(items, key=lambda item: item["affinity_score"], reverse=True),
            "count": len(items),
        }
    )


@router.get("/api/programas/{program_id}/market-gaps")
def program_market_gaps(program_id: int, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    program = program_by_id(program_id)
    if not program:
        raise not_found("programa", program_id)
    clusters = [cluster_to_dict(cluster) for cluster in build_labor_occupational_clusters(write_outputs=True)]
    gaps: list[dict[str, Any]] = []
    for cluster in clusters:
        affinity = _cluster_affinity_for_program(cluster, program)
        if affinity <= 0:
            continue
        for gap in cluster.get("market_gaps", []):
            gaps.append(
                {
                    **gap,
                    "cluster_id": cluster["id"],
                    "cluster_name": cluster["cluster_name"],
                    "affinity_score": round(affinity, 4),
                }
            )
    gaps = sorted(gaps, key=lambda item: (item.get("gap_score", 0), item.get("affinity_score", 0)), reverse=True)
    return jsonable_encoder(
        {
            "program_id": program_id,
            "program_name": program.get("nombre_especializacion") or program.get("nombre"),
            "items": gaps,
            "count": len(gaps),
        }
    )


@router.get("/api/programas/{program_id}/curriculum-market-gap-map")
def program_curriculum_market_gap_map(program_id: int, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    program = program_by_id(program_id)
    if not program:
        raise not_found("programa", program_id)
    gap_map = gap_map_to_dict(build_curriculum_market_gap_map(write_output=True))
    return jsonable_encoder(
        {
            "program_id": program_id,
            "program_name": program.get("nombre_especializacion") or program.get("nombre"),
            "analysis_scope": gap_map["specialization_name"],
            "covered_skills": gap_map["covered_skills"],
            "partial_skills": gap_map["partial_skills"],
            "missing_skills": gap_map["missing_skills"],
            "emerging_skills": gap_map["emerging_skills"],
            "irrelevant_skills": gap_map["irrelevant_skills"],
            "occupational_clusters": gap_map["occupational_clusters"],
            "recommended_curriculum_updates": gap_map["recommended_curriculum_updates"],
        }
    )


@router.get("/api/programas/{program_id}/market-skill-intelligence")
def program_market_skill_intelligence(program_id: int, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    program = program_by_id(program_id)
    if not program:
        raise not_found("programa", program_id)
    intelligence = market_skill_intelligence_to_dict(build_market_skill_intelligence_map(include_database=True, write_output=True))
    return jsonable_encoder(
        {
            "program_id": program_id,
            "program_name": program.get("nombre_especializacion") or program.get("nombre"),
            "analysis_scope": intelligence["specialization_name"],
            "market_skills": intelligence["market_skills"],
            "covered_skills": intelligence["covered_skills"],
            "partial_skills": intelligence["partial_skills"],
            "missing_skills": intelligence["missing_skills"],
            "emerging_skills": intelligence["emerging_skills"],
            "irrelevant_skills": intelligence["irrelevant_skills"],
            "occupational_clusters": intelligence["occupational_clusters"],
            "curriculum_gaps": intelligence["curriculum_gaps"],
            "recommended_updates": intelligence["recommended_updates"],
        }
    )


@router.get("/api/ml/programa/{program_id}/market-intelligence")
def program_ml_market_intelligence(program_id: int, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    program = program_by_id(program_id)
    if not program:
        raise not_found("programa", program_id)
    result = run_program_market_inference(program_id=program_id, include_database=True, write_reports=True)
    result["program_name"] = program.get("nombre_especializacion") or program.get("nombre")
    return jsonable_encoder(result)


@router.get("/api/ml/programa/{program_id}/gap-predictions")
def program_ml_gap_predictions(program_id: int, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    program = program_by_id(program_id)
    if not program:
        raise not_found("programa", program_id)
    result = run_program_market_inference(program_id=program_id, include_database=True, write_reports=True)
    return jsonable_encoder(
        {
            "program_id": program_id,
            "program_name": program.get("nombre_especializacion") or program.get("nombre"),
            "specialization_name": result["specialization_name"],
            "gap_predictions": result["gap_predictions"],
            "occupational_clusters": result["occupational_clusters"],
            "embedding_backend": result["embedding_backend"],
            "model_metadata": result["model_metadata"],
        }
    )


@router.get("/api/ml/programa/{program_id}/recommendations")
def program_ml_recommendations(program_id: int, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    program = program_by_id(program_id)
    if not program:
        raise not_found("programa", program_id)
    recommendations = generate_ml_curriculum_recommendations(program_id=program_id, include_database=True, write_report=True)
    recommendations["program_name"] = program.get("nombre_especializacion") or program.get("nombre")
    return jsonable_encoder(recommendations)


@router.get("/api/programs/related-universities/{program_id}", response_model=Page)
def related_universities_for_program(
    program_id: int,
    limit: int = Query(10, ge=1, le=MAX_LIMIT),
    _current_user=Depends(require_current_user),
) -> Page:
    program = program_by_id(program_id)
    if not program:
        raise not_found("programa", program_id)
    program_name = str(program.get("nombre_especializacion") or "")
    rows = programas_repository.fetch_related_virtual_programs(
        program_name,
        limit=bounded_limit(limit),
        db_name=DB_NAME,
    )
    return page(rows, limit=bounded_limit(limit), offset=0)


@router.get("/api/empleos", response_model=Page)
def list_empleos(
    limit: int = Query(25, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    _current_user=Depends(require_current_user),
) -> Page:
    limit = bounded_limit(limit)
    rows = empleos_repository.fetch_jobs_basic(db_name=DB_NAME)
    return page(rows[offset : offset + limit], limit=limit, offset=offset)


@router.get("/api/empleos/{empleo_id}")
def get_empleo(empleo_id: str, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    empleo = empleos_repository.fetch_job_metadata(empleo_id, db_name=DB_NAME)
    if not empleo:
        raise not_found("empleo", empleo_id)
    empleo["skills"] = skills_repository.fetch_job_skill_names(empleo_id, db_name=DB_NAME)
    return jsonable_encoder(empleo)


@router.get("/api/matches", response_model=Page)
def list_matches(
    limit: int = Query(25, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    _current_user=Depends(require_current_user),
) -> Page:
    relation = matches_repository.match_relation_name(db_name=DB_NAME)
    if not relation:
        return page([], limit=bounded_limit(limit), offset=offset)
    limit = bounded_limit(limit)
    rows = fetch_all(
        f"""
        SELECT
            especializacion_id,
            empleo_id,
            titulo_empleo,
            total_skills_empleo,
            total_skills_especializacion,
            skills_en_comun,
            porcentaje_match
        FROM {relation}
        WHERE skills_en_comun >= 1
        ORDER BY porcentaje_match DESC, skills_en_comun DESC, titulo_empleo
        LIMIT %s OFFSET %s
        """,
        (limit, offset),
        db_name=DB_NAME,
    )
    return page(rows, limit=limit, offset=offset)


@router.get("/api/matches/programa/{program_id}", response_model=Page)
def list_matches_for_program(
    program_id: int,
    limit: int = Query(25, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    _current_user=Depends(require_current_user),
) -> Page:
    relation = matches_repository.match_relation_name(db_name=DB_NAME)
    if not relation:
        return page([], limit=bounded_limit(limit), offset=offset)
    resolved_id = programas_repository.resolve_program_id(program_id, db_name=DB_NAME)
    limit = bounded_limit(limit)
    rows = matches_repository.fetch_match_rows_for_program(
        relation,
        resolved_id,
        limit=None,
        db_name=DB_NAME,
    )
    return page(rows[offset : offset + limit], limit=limit, offset=offset)


@router.get("/api/dashboard/kpis", response_model=DashboardKpisResponse)
def dashboard_kpis(_current_user=Depends(require_current_user)) -> DashboardKpisResponse:
    current_programs = programs()
    return DashboardKpisResponse(
        kpis=dashboard_service.global_kpis(current_programs, db_name=DB_NAME),
        source=matches_repository.match_relation_name(db_name=DB_NAME) or "empleo_skills",
    )


@router.get("/api/dashboard/programa/{program_id}")
def dashboard_programa(program_id: int, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    selected = program_by_id(program_id)
    if not selected:
        raise not_found("programa", program_id)

    relation = matches_repository.match_relation_name(db_name=DB_NAME)
    resolved_id = int(selected.get("especializacion_id") or programas_repository.resolve_program_id(program_id, db_name=DB_NAME))
    matches = (
        matches_repository.fetch_match_rows_for_program(relation, resolved_id, limit=25, db_name=DB_NAME)
        if relation
        else []
    )
    missing_skills = (
        skills_repository.fetch_missing_market_skill_rows_for_program(relation, resolved_id, 22, db_name=DB_NAME)
        if relation
        else []
    )
    current_programs = programs()
    recommendations = recommendation_service.recommended_program_cards(
        current_programs,
        selected,
        "",
        [],
        [],
        [],
        "",
        area_keywords_by_key=AREA_KEYWORDS_BY_KEY,
        get_program_skill_rows=lambda current_id: programas_repository.fetch_program_skill_rows(current_id, db_name=DB_NAME),
        skill_identity_key=skill_identity_key,
        program_role_candidates=role_candidates,
        limit=5,
    )
    payload = dashboard_service.program_context_dashboard(
        selected,
        matches=matches,
        missing_skills=missing_skills,
        recommendations=recommendations,
    )
    micro_context = selected.get("microcurriculum_context")
    if micro_context:
        real_gaps = micro_context.get("real_market_gaps") or []
        strengthening = micro_context.get("strengthening_areas") or []
        scores = micro_context.get("scores") or {}
        labor_roles = micro_context.get("labor_roles") or []
        payload["microcurriculum_context"] = micro_context
        payload["missing_skills"] = [
            {"skill_id": index + 1, "nombre": item.get("name"), "conteo": 1, "priority": item.get("priority")}
            for index, item in enumerate(real_gaps)
        ]
        payload["matches"] = [
            {
                "empleo_id": f"context-role-{index + 1}",
                "titulo_empleo": role,
                "total_skills_empleo": len(micro_context.get("technologies") or []),
                "total_skills_especializacion": len(micro_context.get("technologies") or []),
                "skills_en_comun": max(1, len(micro_context.get("technologies") or []) - len(real_gaps)),
                "porcentaje_match": scores.get("market_skill_coverage") or 0,
                "source": "microcurriculum_context",
            }
            for index, role in enumerate(labor_roles)
        ]
        payload["kpis"].update(
            {
                "alignment_score": scores.get("market_skill_coverage") or payload["kpis"].get("alignment_score", 0),
                "missing_critical_skills": len(real_gaps),
                "high_demand_roles": len(labor_roles),
                "employability_trend": scores.get("curricular_relevance") or payload["kpis"].get("employability_trend", 0),
                "digital_coverage": scores.get("market_skill_coverage") or payload["kpis"].get("digital_coverage", 0),
                "curricular_update_signal": "Alta" if len(real_gaps) >= 6 else "Media" if strengthening else "Baja",
            }
        )
        payload["status"].update(
            {
                "curricular_status": "Contextualizado",
                "curricular_status_detail": f"Análisis basado en {micro_context.get('documents_processed')} microcurrículos reales del programa.",
                "ai_signal": micro_context.get("executive_narrative") or payload["status"].get("ai_signal", ""),
                "trend_label": "Tendencia contextual de Visual Analytics y Big Data",
            }
        )
        payload["insights"].update(
            {
                "detected": micro_context.get("executive_narrative") or payload["insights"].get("detected", ""),
                "ai_recommends": [
                    f"Fortalecer {item.get('name')} con mayor profundidad aplicada."
                    for item in real_gaps[:5]
                ],
                "emerging_gap": real_gaps[0].get("name") if real_gaps else "Sin brechas críticas detectadas",
                "critical_signal": "Microcurrículo real indexado",
            }
        )
    payload["source"] = relation or "empleo_skills"
    return jsonable_encoder(payload)


@router.get("/api/ml/domain-classification")
def ml_domain_classification(
    title: str = "",
    description: str = "",
    skills: str = "",
    _current_user=Depends(require_current_user),
) -> dict[str, Any]:
    skill_values = [item.strip() for item in skills.split(",") if item.strip()]
    prediction = predict_domain(title=title, description=description, skills=skill_values)
    return jsonable_encoder(prediction_to_dict(prediction))


@router.post("/api/ml/inference")
def ml_inference(payload: dict[str, Any], _current_user=Depends(require_current_user)) -> dict[str, Any]:
    prediction = predict_domain(
        title=str(payload.get("title") or payload.get("titulo") or ""),
        description=str(payload.get("description") or payload.get("descripcion") or ""),
        skills=payload.get("skills") or [],
    )
    result = prediction_to_dict(prediction)
    result["input_hash"] = input_hash(payload)
    result["publish_allowed"] = not prediction.blocked
    register_prediction(
        model_name=prediction.model_name,
        model_version="phase1",
        input_hash=result["input_hash"],
        input_payload=payload,
        predicted_domain=prediction.domain,
        confidence=prediction.confidence,
        confidence_level=prediction.confidence_level,
        blocked=prediction.blocked,
        scores=prediction.scores,
    )
    return jsonable_encoder(result)


async def _uploaded_document_from_request(request: Request) -> tuple[Path, str]:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        try:
            form = await request.form()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"multipart upload unavailable: {exc}") from exc
        upload = form.get("file") or form.get("document")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(status_code=400, detail="Expected multipart field 'file' or 'document'.")
        filename = str(getattr(upload, "filename", "") or "microcurriculo.txt")
        data = await upload.read()
    else:
        filename = request.headers.get("x-filename") or request.query_params.get("filename") or "microcurriculo.txt"
        data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="Empty document payload.")
    suffix = Path(filename).suffix or ".txt"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(data)
    tmp.close()
    return Path(tmp.name), filename


@router.post("/api/microcurriculum/upload")
async def upload_microcurriculum(request: Request, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    tmp_path, filename = await _uploaded_document_from_request(request)
    try:
        result = process_microcurriculum(tmp_path, db_name=DB_NAME, persist=True)
        result["uploaded_filename"] = filename
        return jsonable_encoder(result)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


@router.post("/api/microcurriculum/analyze")
async def analyze_microcurriculum(request: Request) -> dict[str, Any]:
    tmp_path, filename = await _uploaded_document_from_request(request)
    try:
        result = process_microcurriculum(tmp_path, db_name=DB_NAME, persist=False, persist_original=False)
        return _format_microcurriculum_analysis(result, uploaded_filename=filename)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


@router.post("/api/microcurriculum/rewrite")
async def rewrite_uploaded_microcurriculum(request: Request) -> dict[str, Any]:
    tmp_path, filename = await _uploaded_document_from_request(request)
    try:
        specialization = str(request.query_params.get("specialization") or VISUAL_ANALYTICS_NAME)
        result = rewrite_microcurriculum(tmp_path, specialization=specialization)
        result["uploaded_filename"] = filename
        result["download_url"] = f"/api/microcurriculum/rewrite/{result['rewrite_id']}/download"
        return jsonable_encoder(result)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


@router.get("/api/microcurriculum/demo-cases")
def microcurriculum_demo_cases() -> dict[str, Any]:
    payload = _read_demo_results()
    items = [
        {
            "id": _demo_case_id(item, index),
            "document_name": item.get("document_name"),
            "expected_domain": item.get("expected_domain"),
            "expected_subdomain": item.get("expected_subdomain"),
            "detected_domain": item.get("detected_domain"),
            "confidence": item.get("confidence"),
            "score": (item.get("scores") or {}).get("pertinencia_curricular"),
            "recommendations_count": len(item.get("recommendations") or []),
        }
        for index, item in enumerate(payload.get("results") or [])
    ]
    return jsonable_encoder({"items": items, "summary": payload.get("summary") or {}})


@router.get("/api/microcurriculum/specialization/{specialization_id}/documents")
def microcurriculum_specialization_documents(specialization_id: str) -> dict[str, Any]:
    specialization = _specialization_by_id(specialization_id)
    if not specialization:
        raise not_found("specialization", specialization_id)
    documents = [_document_payload(path) for path in _documents_for_specialization_name(specialization["nombre"])]
    return jsonable_encoder({"specialization": specialization["nombre"], "documents": documents})


@router.post("/api/microcurriculum/specialization/{specialization_id}/analyze")
def analyze_microcurriculum_specialization(specialization_id: str) -> dict[str, Any]:
    specialization = _specialization_by_id(specialization_id)
    if not specialization:
        raise not_found("specialization", specialization_id)
    document_paths = _documents_for_specialization_name(specialization["nombre"])
    if not document_paths:
        raise HTTPException(status_code=404, detail=f"No microcurriculum documents found for {specialization['nombre']}.")
    analyses: list[dict[str, Any]] = []
    for path in document_paths:
        result = process_microcurriculum(path, db_name=DB_NAME, persist=False, persist_original=False)
        analyses.append(_format_microcurriculum_analysis(result, uploaded_filename=path.name))
    return _consolidate_specialization_analysis(specialization, analyses)


@router.post("/api/microcurriculum/specialization/{specialization_id}/rewrite")
def rewrite_microcurriculum_specialization(specialization_id: str) -> dict[str, Any]:
    specialization = _specialization_by_id(specialization_id)
    if not specialization:
        raise not_found("specialization", specialization_id)
    document_paths = _documents_for_specialization_name(specialization["nombre"])
    if not document_paths:
        raise HTTPException(status_code=404, detail=f"No microcurriculum documents found for {specialization['nombre']}.")
    result = rewrite_microcurriculum_batch(document_paths, specialization=specialization["nombre"])
    for item in result.get("items") or []:
        item["download_url"] = f"/api/microcurriculum/rewrite/{item['rewrite_id']}/download"
    result["traceability_download_url"] = "/api/microcurriculum/rewrite/traceability/download"
    return jsonable_encoder(result)


@router.get("/api/microcurriculum/rewrite/traceability/download")
def download_rewrite_traceability() -> FileResponse:
    path = Path("outputs/curriculum_change_traceability.csv")
    if not path.exists():
        raise not_found("rewrite traceability", "curriculum_change_traceability.csv")
    return FileResponse(path, filename=path.name, media_type="text/csv")


@router.get("/api/microcurriculum/rewrite/{rewrite_id}/download")
def download_rewritten_microcurriculum(rewrite_id: str) -> FileResponse:
    path = _rewrite_download_path(rewrite_id)
    if not path:
        raise not_found("rewritten microcurriculum", rewrite_id)
    return FileResponse(
        path,
        filename=path.name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.get("/api/microcurriculum/{case_id}/executive-report")
def microcurriculum_executive_report(case_id: str, format: str = Query("json")) -> dict[str, Any]:
    payload = _read_demo_results()
    for index, item in enumerate(payload.get("results") or []):
        if _demo_case_id(item, index) == case_id or str(item.get("document_name") or "") == case_id:
            analysis = _demo_case_to_analysis(item, index)
            markdown = _analysis_to_markdown(analysis)
            if format == "markdown":
                return {"id": case_id, "format": "markdown", "markdown": markdown}
            return {"id": case_id, "format": "json", "analysis": analysis, "markdown": markdown}
    raise not_found("microcurriculum demo case", case_id)


@router.get("/api/microcurriculum/{microcurriculum_id}")
def get_microcurriculum(microcurriculum_id: int, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    row = fetch_microcurriculum(microcurriculum_id, db_name=DB_NAME)
    if not row:
        raise not_found("microcurriculum", microcurriculum_id)
    return jsonable_encoder(to_jsonable(row))


@router.get("/api/microcurriculum/{microcurriculum_id}/skills")
def get_microcurriculum_skills(microcurriculum_id: int, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    return {"items": jsonable_encoder(to_jsonable(fetch_child_rows("microcurriculo_skills", microcurriculum_id, db_name=DB_NAME)))}


@router.get("/api/microcurriculum/{microcurriculum_id}/gaps")
def get_microcurriculum_gaps(microcurriculum_id: int, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    return {"items": jsonable_encoder(to_jsonable(fetch_child_rows("microcurriculo_market_gaps", microcurriculum_id, db_name=DB_NAME)))}


@router.get("/api/microcurriculum/{microcurriculum_id}/recommendations")
def get_microcurriculum_recommendations(microcurriculum_id: int, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    return {"items": jsonable_encoder(to_jsonable(fetch_child_rows("microcurriculo_recommendations", microcurriculum_id, db_name=DB_NAME)))}


@router.get("/api/microcurriculum/{microcurriculum_id}/scores")
def get_microcurriculum_scores(microcurriculum_id: int, _current_user=Depends(require_current_user)) -> dict[str, Any]:
    row = fetch_microcurriculum(microcurriculum_id, db_name=DB_NAME)
    if not row:
        raise not_found("microcurriculum", microcurriculum_id)
    metadata = row.get("metadata") or {}
    return jsonable_encoder({"scores": metadata.get("scores", {}), "confidence_score": row.get("confidence_score")})


@router.post("/api/alumni/register", response_model=AlumniRegistrationOut)
def register_alumni(payload: AlumniRegistrationIn, _current_user=Depends(require_current_user)) -> AlumniRegistrationOut:
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    record_id = alumni_service.save_mentor_registration(data, programs(), db_name=DB_NAME)
    return AlumniRegistrationOut(
        id=record_id,
        status="created",
        message="Alumni profile registered in PostgreSQL.",
    )


@router.get("/api/recommendations/programs", response_model=Page)
def recommendations_programs(
    program_id: int = Query(..., description="Current especializacion/program id"),
    area_actual: str = "",
    skills_actuales: str = "",
    roles_interes: str = "",
    areas_interes: str = "",
    objetivo_laboral: str = "",
    limit: int = Query(5, ge=1, le=MAX_LIMIT),
    _current_user=Depends(require_current_user),
) -> Page:
    selected = program_by_id(program_id)
    if not selected:
        raise not_found("programa", program_id)
    current_programs = programs()
    items = recommendation_service.recommended_program_cards(
        current_programs,
        selected,
        area_actual,
        alumni_service.csv_values(skills_actuales),
        alumni_service.csv_values(roles_interes),
        alumni_service.csv_values(areas_interes),
        objetivo_laboral,
        area_keywords_by_key=AREA_KEYWORDS_BY_KEY,
        get_program_skill_rows=lambda current_id: programas_repository.fetch_program_skill_rows(current_id, db_name=DB_NAME),
        skill_identity_key=skill_identity_key,
        program_role_candidates=role_candidates,
        limit=bounded_limit(limit),
    )
    return page(items, limit=bounded_limit(limit), offset=0)


@router.get("/api/recommendations/jobs", response_model=Page)
def recommendations_jobs(
    program_id: int = Query(..., description="Especializacion/program id used for job matching"),
    limit: int = Query(10, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    _current_user=Depends(require_current_user),
) -> Page:
    relation = matches_repository.match_relation_name(db_name=DB_NAME)
    if not relation:
        return page([], limit=bounded_limit(limit), offset=offset)
    resolved_id = programas_repository.resolve_program_id(program_id, db_name=DB_NAME)
    rows = matches_repository.fetch_match_rows_for_program(
        relation,
        resolved_id,
        limit=None,
        db_name=DB_NAME,
    )
    return page(rows[offset : offset + bounded_limit(limit)], limit=bounded_limit(limit), offset=offset)
