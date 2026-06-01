from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from microcurriculum_engine.ingestion.document_loader import extract_text


OFFICIAL_SECTIONS = (
    "PROGRAMA ACADÉMICO",
    "DENOMINACIÓN DE LA ASIGNATURA",
    "SEMESTRE",
    "CRÉDITOS/HORAS",
    "TIPO DE ASIGNATURA",
    "COMPONENTE FORMATIVO DE LA ASIGNATURA",
    "DESCRIPCIÓN DE LA ASIGNATURA",
    "RESULTADOS DE APRENDIZAJE",
    "CONTENIDO TEMÁTICO",
    "ACTIVIDADES FORMATIVAS",
    "EVALUACIÓN Y CALIFICACIÓN",
    "MEDIOS EDUCATIVOS",
    "PERFIL DEL DOCENTE DE LA ASIGNATURA",
)

IMMUTABLE_SECTIONS = {
    "PROGRAMA ACADÉMICO",
    "DENOMINACIÓN DE LA ASIGNATURA",
    "SEMESTRE",
    "CRÉDITOS/HORAS",
    "TIPO DE ASIGNATURA",
    "EVALUACIÓN Y CALIFICACIÓN",
}

REWRITABLE_SECTIONS = {
    "DESCRIPCIÓN DE LA ASIGNATURA",
    "RESULTADOS DE APRENDIZAJE",
    "CONTENIDO TEMÁTICO",
    "ACTIVIDADES FORMATIVAS",
    "MEDIOS EDUCATIVOS",
    "PERFIL DEL DOCENTE DE LA ASIGNATURA",
}


def normalize_heading(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
    aliases = {
        "programa academico": "PROGRAMA ACADÉMICO",
        "denominacion de la asignatura": "DENOMINACIÓN DE LA ASIGNATURA",
        "asignatura": "DENOMINACIÓN DE LA ASIGNATURA",
        "semestre": "SEMESTRE",
        "creditos": "CRÉDITOS/HORAS",
        "creditos horas": "CRÉDITOS/HORAS",
        "horas": "CRÉDITOS/HORAS",
        "tipo de asignatura": "TIPO DE ASIGNATURA",
        "componente formativo de la asignatura": "COMPONENTE FORMATIVO DE LA ASIGNATURA",
        "descripcion de la asignatura": "DESCRIPCIÓN DE LA ASIGNATURA",
        "resultados de aprendizaje": "RESULTADOS DE APRENDIZAJE",
        "contenido tematico": "CONTENIDO TEMÁTICO",
        "contenidos": "CONTENIDO TEMÁTICO",
        "actividades formativas": "ACTIVIDADES FORMATIVAS",
        "evaluacion y calificacion": "EVALUACIÓN Y CALIFICACIÓN",
        "evaluacion": "EVALUACIÓN Y CALIFICACIÓN",
        "medios educativos": "MEDIOS EDUCATIVOS",
        "perfil del docente de la asignatura": "PERFIL DEL DOCENTE DE LA ASIGNATURA",
    }
    return aliases.get(text, "")


def _field_value(text: str, labels: tuple[str, ...]) -> str:
    pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"(?im)^\s*(?:{pattern})\s*:?\s*(.+?)\s*$", text)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def extract_template_sections(path: str | Path) -> dict[str, str]:
    raw_text, _method = extract_text(path)
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    sections: dict[str, list[str]] = {}
    current = ""
    for line in lines:
        heading = normalize_heading(line.rstrip(":"))
        if heading:
            current = heading
            sections.setdefault(current, [])
            continue
        inline_heading = normalize_heading(line.split(":", 1)[0]) if ":" in line else ""
        if inline_heading:
            current = inline_heading
            sections.setdefault(current, [])
            value = line.split(":", 1)[1].strip()
            if value:
                sections[current].append(value)
            continue
        if current:
            sections.setdefault(current, []).append(line)

    mapped = {section: "\n".join(sections.get(section, [])).strip() for section in OFFICIAL_SECTIONS}
    mapped["PROGRAMA ACADÉMICO"] = mapped["PROGRAMA ACADÉMICO"] or _field_value(raw_text, ("programa academico", "programa académico", "programa"))
    mapped["DENOMINACIÓN DE LA ASIGNATURA"] = mapped["DENOMINACIÓN DE LA ASIGNATURA"] or _field_value(raw_text, ("denominacion de la asignatura", "denominación de la asignatura", "asignatura"))
    mapped["SEMESTRE"] = mapped["SEMESTRE"] or _field_value(raw_text, ("semestre",))
    mapped["CRÉDITOS/HORAS"] = mapped["CRÉDITOS/HORAS"] or _field_value(raw_text, ("creditos", "créditos", "horas"))
    return mapped


def assignment_focus(name: str) -> str:
    key = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode("ascii").casefold()
    if any(
        term in key
        for term in (
            "criminologia",
            "criminalistica",
            "criminalistics",
            "investigacion criminal",
            "investigacion criminalistica",
            "forense",
            "forensic",
            "victimologia",
            "victimology",
            "inteligencia criminal",
            "criminal intelligence",
            "prevencion del delito",
            "crime prevention",
            "seguridad ciudadana",
            "public security",
            "ciberdelito",
            "cybercrime",
            "cadena de custodia",
            "chain of custody",
            "crimen organizado",
            "organized crime",
        )
    ):
        if "ciberdelito" in key or "cybercrime" in key:
            return "criminology_cybercrime"
        if "victim" in key:
            return "criminology_victimology"
        if "forens" in key or "criminalistic" in key:
            return "criminology_forensic_analysis"
        if "prevencion" in key or "security" in key or "seguridad" in key:
            return "criminology_public_security"
        return "criminology_criminal_investigation"
    if "visualizacion" in key or "interactiva" in key:
        return "visualizacion_interactiva"
    if "inteligencia artificial" in key or "aprendizaje automatico" in key or "tecnicas de inteligencia" in key:
        return "inteligencia_artificial"
    if "gobierno" in key or "dato" in key and "toma" in key:
        return "gobierno_dato"
    if "procesado masivo" in key or "masivo de datos" in key:
        return "procesado_masivo"
    if "proyectos" in key or "inteligencia de negocio" in key:
        return "gestion_proyectos_bi"
    if "fundamentos" in key or "tratamiento de datos" in key:
        return "fundamentos_datos"
    if "seguridad" in key:
        return "seguridad_big_data"
    if "innovacion" in key or "transformacion digital" in key:
        return "innovacion_digital"
    return "visual_analytics_big_data"
