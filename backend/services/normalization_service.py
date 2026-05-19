from __future__ import annotations

import re
import unicodedata
from typing import Any


def basic_text_key(text: str) -> str:
    raw = unicodedata.normalize("NFKD", str(text or ""))
    raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
    raw = re.sub(r"[^a-zA-Z0-9]+", " ", raw.lower())
    return " ".join(raw.split())


def row_value(row: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return row[name]
    return default


def safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def normalize_program_row(row: dict[str, Any]) -> dict[str, Any]:
    promedio_match = safe_float(row_value(row, "promedio_match_mercado", "match_mercado", "match", default=0))
    total_skills = int(row_value(row, "total_skills_programa", "skills_programa", "total_programa", default=0) or 0)
    return {
        "especializacion_id": int(row_value(row, "especializacion_id", "id", "programa_id", default=0) or 0),
        "nombre_especializacion": str(row_value(row, "nombre_especializacion", "nombre_programa", "programa", "nombre", default="")),
        "rol": str(row_value(row, "rol", "perfil", default="") or ""),
        "total_skills_programa": total_skills,
        "total_herramientas": int(row_value(row, "total_herramientas", default=0) or 0),
        "total_competencias": int(row_value(row, "total_competencias", default=0) or 0),
        "total_habilidades_blandas": int(row_value(row, "total_habilidades_blandas", default=0) or 0),
        "promedio_match_mercado": promedio_match,
        "porcentaje_match": promedio_match,
        "max_match_mercado": safe_float(row_value(row, "max_match_mercado", "mejor_match_mercado", "max_match", default=0)),
        "total_empleos_relacionados": int(row_value(row, "total_empleos_relacionados", "empleos_relacionados", "total_empleos", default=0) or 0),
        "skills_cubiertas": int(round(int(row_value(row, "skills_cubiertas", default=0) or 0) or (total_skills * promedio_match / 100.0))),
    }


def normalize_skill_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "skill_id": int(row_value(row, "skill_id", "id", default=0) or 0),
        "nombre": str(row_value(row, "skill", "nombre", "skill_nombre", default="")),
        "conteo": int(row_value(row, "conteo", "count", "total", "empleos", default=0) or 0),
    }
