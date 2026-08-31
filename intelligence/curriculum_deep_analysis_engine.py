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
import traceback
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
Recibirás el texto completo de los microcurrículos de una especialización:
descripción, resultados de aprendizaje declarados, Y el contenido temático
detallado (Tema 1, Tema 2, ... con sus subtemas y bullets).

Tu tarea es producir un análisis curricular profundo y riguroso.

═══════════════════════════════════════════════════════════
PASO 0 — EXCLUSIONES OBLIGATORIAS (aplica ANTES de analizar)
═══════════════════════════════════════════════════════════
IGNORA completamente el siguiente contenido al identificar herramientas,
competencias, marcos o cualquier elemento del análisis:
- Bibliografía y referencias: autores, iniciales (ej. "R. Turner", "J. Kerzner"),
  títulos de libros, editoriales, URLs, años de publicación. Una letra suelta
  como "R." en contexto de referencia bibliográfica NO es la tecnología R.
- Nombres propios de docentes o perfil docente.
- Encabezados, pies de página, textos administrativos repetidos.
- Instrumentos de evaluación genéricos (ej. "examen final", "quiz", "asistencia").
Solo cuenta como evidencia lo que aparece en la descripción de la asignatura,
los resultados de aprendizaje o el contenido temático sustantivo.

═══════════════════════════════════════════════════════════
INSTRUCCIONES DE EXTRACCIÓN
═══════════════════════════════════════════════════════════

A. FUENTE PRINCIPAL: el CONTENIDO TEMÁTICO, no solo los resultados de aprendizaje.
   Los resultados de aprendizaje son una frase general (ej. "Planificar proyectos").
   El contenido temático es donde están las competencias específicas reales:
   "Tema 4 - Gestión del Valor Ganado: SPI, CPI, EAC, curva S, fórmulas de control".
   Lee TODOS los temas y subtemas de TODAS las asignaturas y extrae de ahí
   las competencias, técnicas, estándares y metodologías específicas mencionadas.

B. CINCO CATEGORÍAS DE COMPETENCIAS — mínimo 15 entradas en total, idealmente 20-30:
   Clasifica cada elemento en exactamente una de estas 5 categorías:

   1. herramientas_tecnicas: técnicas cuantitativas y herramientas operativas concretas
      específicas del dominio del programa.
      Ejemplos (gestión de proyectos): EVM, EDT/WBS, CPM, Gantt, MS Project, Jira.
      Ejemplos (analítica/IA): regresión, clustering, redes neuronales, pipelines ETL,
        SQL/NoSQL, TensorFlow, PyTorch, Tableau, Power BI, Spark, modelos de ML.
      Ejemplos (neuropsicología): escalas neuropsicológicas (WAIS, Stroop, TMT),
        técnicas de neuroimagen, EEG/neurofeedback, baterías de evaluación cognitiva.
      Ejemplos (criminología): análisis estadístico de datos criminales, SIG/mapeo del
        delito, técnicas de entrevista forense, análisis de escena del crimen.

   2. competencias_metodologicas: capacidades de proceso y habilidades analíticas
      que el estudiante desarrolla como competencia propia.
      Ejemplos (gestión de proyectos): planificación, estimación de costos, gestión de
        riesgos como competencia, elaboración de propuestas técnicas.
      Ejemplos (analítica/IA): diseño experimental, validación de modelos, interpretación
        de resultados estadísticos, evaluación de sesgos algorítmicos.
      Ejemplos (neuropsicología): evaluación neuropsicológica, diagnóstico diferencial,
        diseño de intervenciones cognitivas, elaboración de informes clínicos.
      Ejemplos (criminología): metodología de investigación criminal, análisis victimológico,
        elaboración de peritajes, análisis cualitativo/cuantitativo de fenómenos delictivos.
      NO incluyas marcos o estándares aquí — van en marcos_estandares_referentes.

   3. habilidades_transversales: habilidades blandas y comunicativas.
      Ejemplos: liderazgo, trabajo en equipo, comunicación efectiva, pensamiento crítico,
      ética profesional, gestión del cambio, inteligencia emocional, presentación ejecutiva.

   4. gestion_y_negocio: conocimiento de dominio de negocio, organizacional o institucional.
      Ejemplos (gestión de proyectos): análisis financiero, gestión de contratos, gobernanza.
      Ejemplos (analítica/IA): data governance, privacidad de datos, gestión de productos
        digitales, monetización de datos, cumplimiento regulatorio (GDPR).
      Ejemplos (neuropsicología): gestión de servicios de salud mental, marco legal clínico,
        diseño de programas de intervención educativa, políticas de inclusión.
      Ejemplos (criminología): política criminal, gestión de sistemas penitenciarios,
        marco jurídico-penal, seguridad ciudadana, reinserción social.

   5. marcos_estandares_referentes: marcos, estándares, metodologías y certificaciones.
      Ejemplos (gestión de proyectos): PMI, PMBOK, PMP, Prince2, Scrum, Agile, Kanban,
        SAFe, ISO 21500.
      Ejemplos (analítica/IA): CRISP-DM, MLOps, FAIR (datos), ISO/IEC 25010, marcos de
        ética en IA (IEEE, EU AI Act), certificaciones de nube (AWS/Azure/GCP).
      Ejemplos (neuropsicología): DSM-5, CIE-11, modelos de neuropsicología cognitiva
        (Luria, Baddeley), marcos de neurociencia educativa.
      Ejemplos (criminología): teorías criminológicas clásicas y contemporáneas (Sutherland,
        Becker, Hirschi), marcos de justicia restaurativa, estándares forenses internacionales.
      Nunca pongas PMI/PMBOK/PMP/Scrum/Agile en herramientas_tecnicas ni en
      competencias_metodologicas.

   Escala de evidencia por elemento:
   - 3 = Aplicado: aparece en resultados de aprendizaje Y actividades/productos evaluables
   - 2 = Desarrollado: aparece como contenido temático con profundidad propia
   - 1 = Mencionado: solo referencia o concepto aislado/introductorio
   - 0 = Sin evidencia: OMITIR del array (no incluir)

   Para cada elemento lista TODAS las asignaturas donde aparece.

C. AUSENCIAS NOTABLES — checklist de dominio:
   Identifica el dominio principal del programa y aplica ÚNICAMENTE el checklist
   correspondiente. NO uses el checklist de otro dominio.

   - Para gestión de proyectos:
     herramientas tecnológicas de PM (MS Project, Jira, etc.), metodologías ágiles
     (Scrum, Kanban, SAFe), sostenibilidad/ESG en proyectos, analítica financiera de
     inversión (VAN, TIR, payback), gestión de portafolios, transformación digital,
     gestión de contratos y adquisiciones avanzada.

   - Para analítica de datos / visual analytics / big data:
     MLOps y ciclo de vida de modelos en producción, data governance y calidad de datos,
     privacidad/GDPR y regulación de datos, computación en nube (AWS/Azure/GCP),
     herramientas de visualización específicas (Tableau, Power BI, D3 si no mencionadas),
     pipelines de datos y orquestación (Airflow, dbt), testing y validación de modelos.

   - Para inteligencia artificial:
     MLOps y despliegue de modelos en producción, ética y sesgo algorítmico, explicabilidad
     de modelos (XAI/LIME/SHAP), frameworks de desarrollo (TensorFlow, PyTorch si no
     mencionados), IA generativa y LLMs, evaluación de riesgos de IA, certificaciones
     o marcos regulatorios (EU AI Act, ISO/IEC 42001).

   - Para neuropsicología y educación:
     neurociencia cognitiva aplicada al aula, instrumentos de evaluación neuropsicológica
     estandarizados (WAIS, Stroop, baterías Luria si no mencionados), tecnologías de
     neurofeedback y biofeedback, inclusión educativa y NEE, diseño universal del
     aprendizaje (DUA), neuropsicología del desarrollo infantil y del envejecimiento.

   - Para criminología:
     metodologías de investigación cuantitativa aplicadas a datos criminales, herramientas
     de análisis forense digital, SIG y mapeo geoespacial del delito, perspectiva de género
     en criminología, criminología ambiental y situacional, marco legal actualizado
     (reformas recientes), victimología avanzada.

   Reporta como debilidad ÚNICAMENTE las ausencias del checklist de SU dominio, con
   impacto estimado. No importes ítems de otros dominios como brechas.

═══════════════════════════════════════════════════════════
REGLAS OBLIGATORIAS
═══════════════════════════════════════════════════════════
1. Responde ÚNICAMENTE con JSON válido, sin texto antes ni después.
2. No inventes herramientas ni competencias que no estén en el texto.
   Si algo no está en el texto sustantivo (excluida bibliografía), omítelo.
3. Distingue entre competencia explícita e inferida; cuando sea inferida,
   anótalo con "(inferida)" al final del nombre.
4. NOMENCLATURA OBLIGATORIA — usa exactamente estas formas, sin variantes:
   - "PMBOK" (nunca Pmbok, pmbok, PmBok)
   - "PMI" (nunca Pmi, pmi)
   - "PMP" (nunca Pmp, pmp)
   - "Gestión del Valor Ganado (EVM)" (nunca "Valor Ganado" a secas)
   - "Scrum" (nunca scrum, SCRUM)
   - "Agile" (nunca agile, AGILE)
5. sintesis_ejecutiva: máximo 150 palabras, empieza describiendo la orientación
   central y termina con la brecha más crítica.
6. fortalezas: máximo 5, cada una debe incluir entre paréntesis la evidencia
   concreta del texto (nombre de asignatura y/o actividad específica).
7. Las categorías son mutuamente excluyentes: un elemento va en UNA sola categoría.

SCHEMA EXACTO A DEVOLVER — no agregues ni quites claves:
{
  "programa": "string",
  "orientacion_predominante": "string",
  "competencia_global": "string — empieza con verbo observable en infinitivo",
  "herramientas_tecnicas": [
    {"nombre": "string", "evidencia": 1, "asignaturas": ["string"]}
  ],
  "competencias_metodologicas": [
    {"nombre": "string", "evidencia": 1, "asignaturas": ["string"]}
  ],
  "habilidades_transversales": [
    {"nombre": "string", "evidencia": 1, "asignaturas": ["string"]}
  ],
  "gestion_y_negocio": [
    {"nombre": "string", "evidencia": 1, "asignaturas": ["string"]}
  ],
  "marcos_estandares_referentes": [
    {"nombre": "string", "evidencia": 1, "asignaturas": ["string"]}
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
    from psycopg2.extras import Json as PgJson

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
                    PgJson(analysis),
                    _MODEL,
                ),
            )
            row = cur.fetchone()
        conn.commit()
        return row["id"] if row else -1
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
    # Convert datetime fields to ISO strings so json.dumps can serialize them
    if hasattr(result.get("created_at"), "isoformat"):
        result["created_at"] = result["created_at"].isoformat()
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
    for cat in ("herramientas_tecnicas", "competencias_metodologicas",
                "habilidades_transversales", "gestion_y_negocio",
                "marcos_estandares_referentes"):
        analysis.setdefault(cat, [])

    persisted_id: int | None = None
    if persist:
        try:
            persisted_id = _persist(specialization_id, analysis)
            logger.info("[deep_analysis] persisted id=%d", persisted_id)
        except Exception as exc:
            logger.warning(
                "[deep_analysis] persist failed (analysis still returned):\n%s",
                traceback.format_exc(),
            )

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
