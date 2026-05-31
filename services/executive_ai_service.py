from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.repositories import microcurriculum_context_repository, programas_repository
from backend.repositories.base import fetch_one, relation_exists
from intelligence.curriculum_impact_simulator import build_curriculum_impact_simulation
from intelligence.executive_observatory_engine import build_executive_observatory_v2
from intelligence.forecast_expansion_engine import build_forecast_summary
from intelligence.predictive_intelligence_engine import build_curriculum_risk_index, build_university_market_alignment
from intelligence.program_intelligence_engine import build_program_intelligence_for_program
from intelligence.common import normalize_key


DEFAULT_MODEL = os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
OPENAI_BASE_URL = (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
CACHE_TTL_SECONDS = int(os.getenv("EXECUTIVE_AI_CACHE_TTL_SECONDS") or "21600")

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


@dataclass(frozen=True)
class ExecutiveAIPayload:
    response: dict[str, Any]
    used_openai: bool
    model: str


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "to_dict"):
        try:
            return _json_safe(value.to_dict())
        except Exception:
            return str(value)
    if hasattr(value, "__dict__"):
        try:
            return _json_safe(vars(value))
        except Exception:
            return str(value)
    return str(value)


def _cache_key(prefix: str, payload: dict[str, Any]) -> str:
    raw = json.dumps({"prefix": prefix, "payload": _json_safe(payload), "model": DEFAULT_MODEL}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> dict[str, Any] | None:
    entry = _CACHE.get(key)
    if not entry:
        return None
    expires_at, value = entry
    if time.time() > expires_at:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: dict[str, Any]) -> None:
    _CACHE[key] = (time.time() + CACHE_TTL_SECONDS, value)


def _openai_enabled() -> bool:
    return bool(OPENAI_API_KEY)


def _strip_json_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
    return text.strip()


def _load_json(content: str) -> dict[str, Any]:
    text = _strip_json_fence(content)
    try:
        loaded = json.loads(text)
        return loaded if isinstance(loaded, dict) else {"answer": str(loaded)}
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                loaded = json.loads(text[start : end + 1])
                return loaded if isinstance(loaded, dict) else {"answer": str(loaded)}
            except Exception:
                pass
    return {"answer": text}


def _openai_chat_json(*, system_prompt: str, user_payload: dict[str, Any], cache_prefix: str) -> ExecutiveAIPayload | None:
    if not _openai_enabled():
        return None

    cache_key = _cache_key(cache_prefix, user_payload)
    cached = _cache_get(cache_key)
    if cached is not None:
        return ExecutiveAIPayload(response=cached, used_openai=False, model=DEFAULT_MODEL)

    request_body = {
        "model": DEFAULT_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False, default=str),
            },
        ],
    }
    request = Request(
        f"{OPENAI_BASE_URL}/chat/completions",
        data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=40) as response:
            raw = response.read().decode("utf-8")
        payload = json.loads(raw)
        content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not isinstance(content, str):
            content = json.dumps(content, ensure_ascii=False)
        parsed = _load_json(content)
        parsed.setdefault("model", DEFAULT_MODEL)
        _cache_set(cache_key, parsed)
        return ExecutiveAIPayload(response=parsed, used_openai=True, model=DEFAULT_MODEL)
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return None
    except Exception:
        return None


def _microcurriculum_context(program_id: int, program_name: str | None = None, db_name: str | None = None) -> dict[str, Any]:
    context = microcurriculum_context_repository.fetch_program_context(
        program_id,
        specialization_name=program_name,
        db_name=db_name,
    )
    return context or {}


def _program_base(program_id: int, db_name: str | None = None) -> dict[str, Any]:
    row = programas_repository.fetch_program_base_row(program_id, db_name=db_name)
    if not row:
        raise KeyError(f"programa {program_id} not found")
    return dict(row)


def _program_intelligence(program_id: int, db_name: str | None = None) -> dict[str, Any]:
    item = build_program_intelligence_for_program(program_id, db_name=db_name)
    return item.to_dict()


def _program_traceability(program_id: int, db_name: str | None = None) -> dict[str, Any]:
    program = _program_base(program_id, db_name=db_name)
    intelligence = _program_intelligence(program_id, db_name=db_name)
    context = _microcurriculum_context(program_id, str(program.get("nombre_especializacion") or ""), db_name=db_name)
    risk = build_curriculum_risk_index(program_id, persist=False, db_name=db_name).to_dict()
    alignment = build_university_market_alignment(program_id, persist=False, db_name=db_name).to_dict()
    forecast = build_forecast_summary(db_name=db_name, persist=False, limit=20)
    return {
        "program": program,
        "program_intelligence": intelligence,
        "microcurriculum_context": context,
        "curriculum_risk": risk,
        "alignment": alignment,
        "forecast_summary": forecast,
    }


def _deterministic_program_summary(program_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    program = payload["program"]
    context = payload["microcurriculum_context"]
    intelligence = payload["program_intelligence"]
    risk = payload["curriculum_risk"]
    alignment = payload["alignment"]
    forecast_summary = payload["forecast_summary"]
    risk_score = float(risk.get("risk_score") or intelligence.get("risk_score") or 0)
    alignment_score = float(alignment.get("alignment_score") or intelligence.get("alignment_score") or 0)
    narrative = (
        f"El programa '{program.get('nombre_especializacion')}' muestra una alineación de {alignment_score:.1f}% y un riesgo curricular de {risk_score:.1f}%. "
        f"Las brechas más relevantes están asociadas a {', '.join([str(item.get('missing_skill') or '') for item in intelligence.get('top_gaps', [])[:3] if str(item.get('missing_skill') or '').strip()]) or 'las competencias priorizadas por el observatorio'}. "
        f"El contexto microcurricular detecta {len(context.get('technical_skills') or [])} skills técnicas y {len(context.get('transversal_skills') or [])} competencias transversales."
    )
    why_at_risk = (
        f"El riesgo se explica por {len(risk.get('risk_drivers') or intelligence.get('top_gaps') or [])} señales activas, "
        f"con presión de mercado reflejada en {len(forecast_summary.get('top_skills') or [])} señales de forecast y {len(intelligence.get('top_recommendations') or [])} recomendaciones priorizadas."
    )
    evidence_sources = [
        "program_intelligence",
        "microcurriculum_program_contexts",
        "curriculum_gap_observatory",
        "recommendation_observatory",
        "market_forecasts",
        "program_risk_index",
        "program_employability_index",
    ]
    supporting_evidence = {
        "program": program,
        "microcurriculum_context": context,
        "risk": risk,
        "alignment": alignment,
        "program_intelligence": intelligence,
        "forecast_summary": forecast_summary,
    }
    return {
        "program_id": program_id,
        "program_name": str(program.get("nombre_especializacion") or ""),
        "summary": narrative,
        "why_at_risk": why_at_risk,
        "microcurriculum_traceability": {
            "microcurriculum_name": context.get("specialization_name") or program.get("nombre_especializacion"),
            "covered_skills": context.get("technical_skills") or [],
            "transversal_skills": context.get("transversal_skills") or [],
            "missing_skills": context.get("real_market_gaps") or [],
            "strengthening_areas": context.get("strengthening_areas") or [],
            "coverage": context.get("scores") or {},
            "labor_roles": context.get("labor_roles") or [],
        },
        "evidence_sources": evidence_sources,
        "source_tables": evidence_sources,
        "supporting_evidence": supporting_evidence,
        "confidence": round(min(0.95, 0.6 + alignment_score / 200.0 + (1.0 - risk_score / 100.0) / 4.0), 4),
        "model": "deterministic-fallback",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def build_program_summary(program_id: int, *, db_name: str | None = None) -> dict[str, Any]:
    payload = _program_traceability(program_id, db_name=db_name)
    program = payload["program"]
    context = payload["microcurriculum_context"]
    intelligence = payload["program_intelligence"]
    risk = payload["curriculum_risk"]
    alignment = payload["alignment"]
    forecast_summary = payload["forecast_summary"]

    cached = _openai_chat_json(
        system_prompt=(
            "Eres un asistente ejecutivo académico. Responde SOLO en JSON válido y conciso. "
            "No inventes métricas. Solo usa la evidencia suministrada. "
            "Campos requeridos: summary, why_at_risk, evidence_sources, confidence."
        ),
        user_payload={
            "task": "program_summary",
            "program": program,
            "microcurriculum_context": context,
            "program_intelligence": intelligence,
            "curriculum_risk": risk,
            "alignment": alignment,
            "forecast_summary": forecast_summary,
        },
        cache_prefix=f"program_summary:{program_id}",
    )
    if cached:
        response = cached.response
        summary = str(response.get("summary") or response.get("answer") or response.get("narrative") or "").strip()
        why_at_risk = str(response.get("why_at_risk") or "").strip()
        evidence_sources = response.get("evidence_sources") if isinstance(response.get("evidence_sources"), list) else []
        return {
            "program_id": program_id,
            "program_name": str(program.get("nombre_especializacion") or ""),
            "summary": summary or _deterministic_program_summary(program_id, payload)["summary"],
            "why_at_risk": why_at_risk or _deterministic_program_summary(program_id, payload)["why_at_risk"],
            "microcurriculum_traceability": {
                "microcurriculum_name": context.get("specialization_name") or program.get("nombre_especializacion"),
                "covered_skills": context.get("technical_skills") or [],
                "transversal_skills": context.get("transversal_skills") or [],
                "missing_skills": context.get("real_market_gaps") or [],
                "strengthening_areas": context.get("strengthening_areas") or [],
                "coverage": context.get("scores") or {},
                "labor_roles": context.get("labor_roles") or [],
            },
            "evidence_sources": evidence_sources or _deterministic_program_summary(program_id, payload)["evidence_sources"],
            "source_tables": evidence_sources or _deterministic_program_summary(program_id, payload)["source_tables"],
            "supporting_evidence": {
                "program": program,
                "microcurriculum_context": context,
                "program_intelligence": intelligence,
                "curriculum_risk": risk,
                "alignment": alignment,
                "forecast_summary": forecast_summary,
            },
            "confidence": float(response.get("confidence") or 0.0),
            "model": cached.model,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    return _deterministic_program_summary(program_id, payload)


def build_executive_narrative(*, program_id: int | None = None, db_name: str | None = None) -> dict[str, Any]:
    if program_id is not None:
        summary = build_program_summary(program_id, db_name=db_name)
        return {
            "program_id": program_id,
            "program_name": summary["program_name"],
            "narrative": summary["summary"],
            "why_at_risk": summary["why_at_risk"],
            "evidence_sources": summary["evidence_sources"],
            "source_tables": summary["source_tables"],
            "supporting_evidence": summary["supporting_evidence"],
            "confidence": summary["confidence"],
            "model": summary["model"],
            "generated_at": summary["generated_at"],
        }

    observatory = build_executive_observatory_v2(db_name=db_name).to_dict()
    cached = _openai_chat_json(
        system_prompt=(
            "Eres un asistente ejecutivo académico. Responde SOLO en JSON válido y conciso. "
            "No inventes métricas. Solo usa la evidencia suministrada. "
            "Campos requeridos: narrative, why_at_risk, evidence_sources, confidence."
        ),
        user_payload={
            "task": "executive_narrative",
            "executive_observatory": observatory,
        },
        cache_prefix="executive_narrative:global",
    )
    if cached:
        response = cached.response
        narrative = str(response.get("narrative") or response.get("answer") or "").strip()
        why_at_risk = str(response.get("why_at_risk") or "").strip()
        evidence_sources = response.get("evidence_sources") if isinstance(response.get("evidence_sources"), list) else []
        return {
            "program_id": None,
            "program_name": "",
            "narrative": narrative or str(observatory.get("executive_narrative") or ""),
            "why_at_risk": why_at_risk,
            "evidence_sources": evidence_sources or list(observatory.get("source_tables") or []),
            "source_tables": list(observatory.get("source_tables") or []),
            "supporting_evidence": observatory,
            "confidence": float(response.get("confidence") or observatory.get("confidence") or 0.0),
            "model": cached.model,
            "generated_at": str(observatory.get("generated_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        }

    return {
        "program_id": None,
        "program_name": "",
        "narrative": str(observatory.get("executive_narrative") or ""),
        "why_at_risk": "",
        "evidence_sources": list(observatory.get("source_tables") or []),
        "source_tables": list(observatory.get("source_tables") or []),
        "supporting_evidence": observatory,
        "confidence": float(observatory.get("confidence") or 0.0),
        "model": "deterministic-fallback",
        "generated_at": str(observatory.get("generated_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
    }


def _fetch_recommendation_row(recommendation_id: int, *, db_name: str | None = None) -> dict[str, Any]:
    if not relation_exists("recommendation_observatory", db_name=db_name):
        raise KeyError(f"recommendation {recommendation_id} not found")
    row = fetch_one(
        """
        SELECT *
        FROM recommendation_observatory
        WHERE id = %s
        """,
        (recommendation_id,),
        db_name=db_name,
    )
    if not row:
        raise KeyError(f"recommendation {recommendation_id} not found")
    return dict(row)


def build_recommendation_explanation(recommendation_id: int, *, db_name: str | None = None) -> dict[str, Any]:
    recommendation = _fetch_recommendation_row(recommendation_id, db_name=db_name)
    payload = {
        "task": "recommendation_explanation",
        "recommendation": recommendation,
    }
    cached = _openai_chat_json(
        system_prompt=(
            "Eres un asistente ejecutivo académico. Responde SOLO en JSON válido y conciso. "
            "No inventes métricas. Solo usa la evidencia suministrada. "
            "Campos requeridos: explanation, why_this_recommendation, evidence_sources, confidence."
        ),
        user_payload=payload,
        cache_prefix=f"recommendation_explanation:{recommendation_id}",
    )
    base_evidence_sources = ["recommendation_observatory", "curriculum_gap_observatory", "market_forecasts", "program_intelligence"]
    if cached:
        response = cached.response
        explanation = str(response.get("explanation") or response.get("answer") or "").strip()
        why_this = str(response.get("why_this_recommendation") or "").strip()
        evidence_sources = response.get("evidence_sources") if isinstance(response.get("evidence_sources"), list) else base_evidence_sources
        return {
            "recommendation_id": recommendation_id,
            "recommendation_title": str(recommendation.get("recommendation_type") or recommendation.get("target_role") or recommendation.get("target_company") or ""),
            "explanation": explanation or str(recommendation.get("recommendation_reasoning") or ""),
            "why_this_recommendation": why_this or str(recommendation.get("recommendation_reasoning") or ""),
            "evidence_sources": evidence_sources,
            "source_tables": evidence_sources,
            "supporting_evidence": recommendation,
            "confidence": float(response.get("confidence") or recommendation.get("recommendation_confidence") or 0.0),
            "model": cached.model,
            "generated_at": str(recommendation.get("generated_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        }

    return {
        "recommendation_id": recommendation_id,
        "recommendation_title": str(recommendation.get("recommendation_type") or recommendation.get("target_role") or recommendation.get("target_company") or ""),
        "explanation": str(recommendation.get("recommendation_reasoning") or ""),
        "why_this_recommendation": str(recommendation.get("recommendation_reasoning") or ""),
        "evidence_sources": base_evidence_sources,
        "source_tables": base_evidence_sources,
        "supporting_evidence": recommendation,
        "confidence": float(recommendation.get("recommendation_confidence") or 0.0),
        "model": "deterministic-fallback",
        "generated_at": str(recommendation.get("generated_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
    }


def ask_observatory(question: str, *, program_id: int | None = None, recommendation_id: int | None = None, context: dict[str, Any] | None = None, db_name: str | None = None) -> dict[str, Any]:
    context = context or {}
    payload: dict[str, Any] = {
        "task": "ask_observatory",
        "question": question,
        "program_id": program_id,
        "recommendation_id": recommendation_id,
        "context": context,
    }
    if program_id is not None:
        payload["program_summary"] = build_program_summary(program_id, db_name=db_name)
    if recommendation_id is not None:
        payload["recommendation"] = build_recommendation_explanation(recommendation_id, db_name=db_name)
    if not payload.get("program_summary"):
        payload["executive_observatory"] = build_executive_observatory_v2(db_name=db_name).to_dict()

    cached = _openai_chat_json(
        system_prompt=(
            "Eres un asistente ejecutivo académico. Responde SOLO en JSON válido y conciso. "
            "No inventes métricas. Solo usa la evidencia suministrada. "
            "Campos requeridos: answer, evidence_sources, confidence."
        ),
        user_payload=payload,
        cache_prefix=f"ask_observatory:{normalize_key(question)}:{program_id or ''}:{recommendation_id or ''}",
    )
    evidence_sources = ["program_intelligence", "executive_observatory", "curriculum_gap_observatory", "recommendation_observatory", "market_forecasts"]
    if cached:
        response = cached.response
        answer = str(response.get("answer") or response.get("narrative") or response.get("explanation") or "").strip()
        if not answer:
            answer = question
        return {
            "question": question,
            "answer": answer,
            "evidence_sources": response.get("evidence_sources") if isinstance(response.get("evidence_sources"), list) else evidence_sources,
            "source_tables": response.get("source_tables") if isinstance(response.get("source_tables"), list) else evidence_sources,
            "supporting_evidence": payload,
            "confidence": float(response.get("confidence") or 0.0),
            "model": cached.model,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    fallback = build_executive_narrative(program_id=program_id, db_name=db_name) if program_id is not None else build_executive_narrative(db_name=db_name)
    return {
        "question": question,
        "answer": str(fallback.get("narrative") or question),
        "evidence_sources": fallback.get("evidence_sources") or evidence_sources,
        "source_tables": fallback.get("source_tables") or evidence_sources,
        "supporting_evidence": payload,
        "confidence": float(fallback.get("confidence") or 0.0),
        "model": fallback.get("model") or "deterministic-fallback",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
