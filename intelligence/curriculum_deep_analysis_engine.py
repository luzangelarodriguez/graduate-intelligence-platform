"""Motor de Análisis Curricular Profundo.

Genera un análisis estructurado (JSON) de todos los microcurrículos
de un programa, usando el mismo patrón de llamada OpenAI que
services/executive_ai_service.py (_openai_chat_json).

Uso:
    from intelligence.curriculum_deep_analysis_engine import build_deep_analysis
    result = build_deep_analysis(9)   # specialization_id=9
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

# ── OpenAI config (same env vars as executive_ai_service) ────────────────────
_MODEL = os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
_BASE_URL = (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT_SECONDS") or "60")  # deeper analysis needs more time


# ── DB helpers ────────────────────────────────────────────────────────────────

def _fetch_microcurriculos(specialization_id: int) -> list[dict[str, Any]]:
    """Return rows from microcurriculos for the given specialization."""
    from backend.repositories.base import fetch_all  # local import avoids circular dep
    rows = fetch_all(
        """
        SELECT id, asignatura, clean_text
        FROM microcurriculos
        WHERE specialization_id = %s
          AND clean_text IS NOT NULL
          AND length(clean_text) > 50
        ORDER BY asignatura NULLS LAST
        """,
        (specialization_id,),
    )
    return [dict(r) for r in (rows or [])]


def _fetch_program_name(specialization_id: int) -> str:
    from backend.repositories.base import fetch_one
    row = fetch_one(
        "SELECT nombre FROM especializaciones WHERE id = %s",
        (specialization_id,),
    )
    return str((row or {}).get("nombre") or f"Programa {specialization_id}")


# ── Prompt ────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
Eres un experto en diseño curricular y análisis académico de posgrados.
Recibirás el texto completo de los microcurrículos de una especialización
(asignaturas, resultados de aprendizaje y contenidos temáticos).

Tu tarea es producir un análisis curricular profundo y riguroso.

REGLAS OBLIGATORIAS:
1. Responde ÚNICAMENTE con JSON válido, sin texto antes ni después.
2. No inventes software, herramientas ni competencias que no estén mencionadas
   explícitamente en el texto. Si algo no está en el texto, indícalo como ausente.
3. Distingue entre competencia explícita (mencionada en texto) e inferida
   (deducida razonablemente). Cuando sea inferida, anótalo con "(inferida)".
4. Para la profundidad de metodologías usa exactamente uno de estos valores:
   "solo_mencionada" | "introductoria" | "aplicada" | "avanzada".
5. nivel_promedio en la matriz de competencias: 0 = no evidenciada,
   1 = introducción conceptual, 2 = desarrollo aplicado, 3 = dominio con práctica evaluable.
6. sintesis_ejecutiva: máximo 150 palabras.
7. fortalezas: máximo 5, cada una debe incluir entre paréntesis la evidencia concreta.

SCHEMA EXACTO A DEVOLVER:
{
  "programa": "string",
  "orientacion_predominante": "string",
  "competencia_global": "string — empieza con verbo observable en infinitivo",
  "matriz_competencias": [
    {
      "competencia": "string",
      "nivel_promedio": 0,
      "asignaturas_donde_aparece": ["string"],
      "es_transversal": false
    }
  ],
  "metodologias_identificadas": [
    {
      "nombre": "string",
      "categoria": "string",
      "profundidad": "solo_mencionada|introductoria|aplicada|avanzada"
    }
  ],
  "fortalezas": ["string con evidencia entre paréntesis — máx 5"],
  "debilidades": [
    {
      "hallazgo": "string",
      "impacto": "alto|medio|bajo",
      "recomendacion": "string"
    }
  ],
  "perfil_ocupacional": [
    {
      "cargo": "string",
      "correspondencia": "alta|media|baja",
      "observaciones": "string"
    }
  ],
  "recomendaciones_priorizadas": [
    {
      "prioridad": "alta|media|complementaria",
      "accion": "string",
      "razon": "string"
    }
  ],
  "sintesis_ejecutiva": "string — máx 150 palabras"
}
"""


def _build_user_payload(program_name: str, microcurriculos: list[dict[str, Any]]) -> str:
    """Builds the user message: program name + concatenated asignatura texts."""
    parts = [f"PROGRAMA: {program_name}\n", f"TOTAL ASIGNATURAS: {len(microcurriculos)}\n\n"]
    for mc in microcurriculos:
        asig = mc.get("asignatura") or f"id={mc['id']}"
        text = (mc.get("clean_text") or "").strip()
        parts.append(f"=== ASIGNATURA: {asig} ===\n{text}\n\n")
    return "".join(parts)


# ── OpenAI caller (same pattern as executive_ai_service._openai_chat_json) ───

def _strip_json_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
    return text.strip()


def _call_openai(system_prompt: str, user_text: str) -> dict[str, Any]:
    if not _API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set — cannot call OpenAI")

    request_body = {
        "model": _MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    }
    req = Request(
        f"{_BASE_URL}/chat/completions",
        data=json.dumps(request_body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=_TIMEOUT) as response:
            raw = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"OpenAI request failed: {exc}") from exc

    payload = json.loads(raw)
    content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False)

    text = _strip_json_fence(content)
    try:
        result = json.loads(text)
        if not isinstance(result, dict):
            raise ValueError(f"Expected JSON object, got {type(result)}")
        return result
    except (json.JSONDecodeError, ValueError):
        # Try to extract first {...} block
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            result = json.loads(text[start:end + 1])
            if isinstance(result, dict):
                return result
        raise ValueError(f"Could not parse JSON from OpenAI response: {text[:300]}")


# ── Persistence ───────────────────────────────────────────────────────────────

def _persist(specialization_id: int, analysis: dict[str, Any]) -> int:
    """Insert a new row in program_deep_analysis and return the new id."""
    from backend.db import get_conn

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO program_deep_analysis
                    (specialization_id, analysis_json, model_version)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (
                    specialization_id,
                    json.dumps(analysis, ensure_ascii=False),
                    _MODEL,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return row[0] if row else -1
    finally:
        conn.close()


def _fetch_latest(specialization_id: int) -> dict[str, Any] | None:
    """Return the most recent analysis row for the given specialization, or None."""
    from backend.repositories.base import fetch_one
    row = fetch_one(
        """
        SELECT id, specialization_id, analysis_json, model_version, created_at
        FROM program_deep_analysis
        WHERE specialization_id = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (specialization_id,),
    )
    if not row:
        return None
    result = dict(row)
    if isinstance(result.get("analysis_json"), str):
        try:
            result["analysis_json"] = json.loads(result["analysis_json"])
        except Exception:
            pass
    return result


# ── Public API ────────────────────────────────────────────────────────────────

def build_deep_analysis(
    specialization_id: int,
    *,
    persist: bool = True,
) -> dict[str, Any]:
    """Generate a deep curriculum analysis for the given program.

    Calls OpenAI with the full clean_text of all microcurriculos, parses
    the structured JSON response, and optionally persists it.

    Args:
        specialization_id: ID from the especializaciones table.
        persist: If True (default), insert the result into program_deep_analysis.

    Returns:
        dict with keys: specialization_id, program_name, analysis, model_version,
        generated_at, persisted_id (int or None).
    """
    program_name = _fetch_program_name(specialization_id)
    microcurriculos = _fetch_microcurriculos(specialization_id)

    if not microcurriculos:
        raise ValueError(
            f"No microcurriculos found for specialization_id={specialization_id}. "
            "Run load_microcurriculos.py --execute first."
        )

    logger.info(
        "[deep_analysis] specialization_id=%d program=%r asignaturas=%d",
        specialization_id, program_name, len(microcurriculos),
    )

    user_text = _build_user_payload(program_name, microcurriculos)
    analysis = _call_openai(_SYSTEM_PROMPT, user_text)

    # Ensure top-level required fields exist
    analysis.setdefault("programa", program_name)
    analysis.setdefault("sintesis_ejecutiva", "")

    persisted_id: int | None = None
    if persist:
        try:
            persisted_id = _persist(specialization_id, analysis)
            logger.info("[deep_analysis] persisted id=%d", persisted_id)
        except Exception as exc:
            logger.warning("[deep_analysis] persist failed (analysis still returned): %s", exc)

    return {
        "specialization_id": specialization_id,
        "program_name": program_name,
        "analysis": analysis,
        "model_version": _MODEL,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "persisted_id": persisted_id,
    }


def get_latest_deep_analysis(specialization_id: int) -> dict[str, Any] | None:
    """Return the most recent persisted analysis, or None if none exists."""
    return _fetch_latest(specialization_id)
