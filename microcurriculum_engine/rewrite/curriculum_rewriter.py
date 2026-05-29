from __future__ import annotations

from pathlib import Path
from typing import Any

from microcurriculum_engine.rewrite.curriculum_change_tracker import CurriculumChange, write_traceability_csv
from microcurriculum_engine.rewrite.docx_template_mapper import (
    IMMUTABLE_SECTIONS,
    OFFICIAL_SECTIONS,
    REWRITABLE_SECTIONS,
    assignment_focus,
    extract_template_sections,
)
from microcurriculum_engine.rewrite.rewritten_microcurriculum_exporter import (
    OUTPUT_DIR,
    export_rewritten_docx,
    write_summary_markdown,
)


TRACEABILITY_OUTPUT = Path("outputs/curriculum_change_traceability.csv")

FOCUS_ENHANCEMENTS = {
    "visualizacion_interactiva": {
        "signals": "Power BI, Tableau, dashboards ejecutivos, storytelling with data, UX de visualización",
        "description": "Se fortalece el enfoque en visual analytics, diseño de dashboards ejecutivos, criterios de usabilidad y narrativa con datos para la toma de decisiones.",
        "outcomes": [
            "Diseñar visualizaciones interactivas orientadas a decisiones ejecutivas, aplicando principios de claridad, jerarquía visual y storytelling with data.",
            "Construir dashboards en Power BI o Tableau integrando métricas, segmentaciones y evidencia para públicos estratégicos.",
        ],
        "content": [
            "Storytelling with data y comunicación ejecutiva de hallazgos.",
            "Diseño de dashboards, interacción, navegación y criterios UX para analítica visual.",
            "Buenas prácticas en Power BI, Tableau y visualización orientada a indicadores.",
        ],
    },
    "inteligencia_artificial": {
        "signals": "Python, R, machine learning aplicado, validación de modelos, ética de IA",
        "description": "Se orienta la asignatura hacia modelos predictivos aplicados, validación, interpretación y uso responsable de técnicas de inteligencia artificial.",
        "outcomes": [
            "Aplicar modelos predictivos con Python o R considerando preparación de datos, entrenamiento, validación e interpretación de resultados.",
            "Evaluar la pertinencia y límites de modelos de machine learning en escenarios de analítica institucional y empresarial.",
        ],
        "content": [
            "Flujo aplicado de machine learning: datos, entrenamiento, validación y evaluación.",
            "Métricas de desempeño, sesgo, explicabilidad y ética de IA.",
            "Notebooks reproducibles y comunicación de resultados predictivos.",
        ],
    },
    "gobierno_dato": {
        "signals": "data governance, calidad, linaje, seguridad, data stewardship",
        "description": "Se profundiza el gobierno del dato, calidad, linaje, seguridad y responsabilidades institucionales sobre activos de información.",
        "outcomes": [
            "Definir criterios de gobierno, calidad y linaje de datos para soportar decisiones confiables.",
            "Proponer controles de seguridad, privacidad y uso responsable de datos en entornos analíticos.",
        ],
        "content": [
            "Gobierno del dato, roles, políticas, catálogo y data stewardship.",
            "Calidad, trazabilidad, linaje y ciclo de vida de datos.",
            "Seguridad, privacidad y gestión de riesgos asociados al uso de datos.",
        ],
    },
    "procesado_masivo": {
        "signals": "Spark, lakehouse, cloud analytics, Databricks, procesamiento distribuido",
        "description": "Se actualiza el enfoque hacia procesamiento distribuido, arquitecturas lakehouse y servicios cloud analytics para big data.",
        "outcomes": [
            "Diseñar flujos de procesamiento masivo usando principios de arquitectura lakehouse y procesamiento distribuido.",
            "Comparar tecnologías como Spark, Databricks y servicios cloud analytics para escenarios de alto volumen.",
        ],
        "content": [
            "Procesamiento distribuido con Spark y patrones de ingesta masiva.",
            "Arquitecturas data lake, data warehouse y lakehouse.",
            "Servicios cloud analytics y criterios de selección tecnológica.",
        ],
    },
    "gestion_proyectos_bi": {
        "signals": "gobierno de proyectos analíticos, KPI, priorización, valor de negocio",
        "description": "Se refuerza la gestión de proyectos de inteligencia de negocio con indicadores, priorización de valor y gobierno de iniciativas analíticas.",
        "outcomes": [
            "Formular proyectos de BI alineados con objetivos estratégicos, indicadores y generación de valor.",
            "Priorizar iniciativas analíticas usando criterios de impacto, viabilidad, riesgos y adopción organizacional.",
        ],
        "content": [
            "Gobierno de proyectos analíticos y portafolio de iniciativas BI.",
            "Indicadores, OKR/KPI y medición de valor de negocio.",
            "Gestión del cambio, adopción y comunicación ejecutiva.",
        ],
    },
    "fundamentos_datos": {
        "signals": "SQL, ETL, data warehousing, modelado de datos",
        "description": "Se conserva la base tecnológica y se profundiza en SQL, ETL, modelado y preparación de datos para analítica.",
        "outcomes": [
            "Aplicar SQL y procesos ETL para integrar, depurar y preparar datos con fines analíticos.",
            "Explicar fundamentos de modelado, almacenamiento y calidad de datos en soluciones BI.",
        ],
        "content": [
            "SQL aplicado a consulta, transformación y validación de datos.",
            "Procesos ETL/ELT y preparación de datos para visual analytics.",
            "Fundamentos de data warehousing y modelado dimensional.",
        ],
    },
    "seguridad_big_data": {
        "signals": "seguridad del dato, privacidad, controles, cloud security",
        "description": "Se mantiene el foco de seguridad y se conecta con gobierno, privacidad y protección de datos en ecosistemas big data.",
        "outcomes": [
            "Identificar riesgos de seguridad, privacidad y acceso en plataformas de datos y analítica.",
            "Proponer controles para proteger datos, aplicaciones y servicios cloud usados en soluciones big data.",
        ],
        "content": [
            "Seguridad y privacidad en ecosistemas de datos.",
            "Controles de acceso, cifrado, auditoría y cumplimiento.",
            "Riesgos de seguridad en servicios cloud analytics y aplicaciones de datos.",
        ],
    },
    "innovacion_digital": {
        "signals": "vigilancia tecnológica, inteligencia competitiva, transformación digital",
        "description": "Se fortalece la conexión entre innovación tecnológica, vigilancia, inteligencia competitiva y transformación digital basada en datos.",
        "outcomes": [
            "Analizar tendencias tecnológicas y señales competitivas para orientar iniciativas de transformación digital.",
            "Diseñar propuestas de innovación basadas en datos, viabilidad y generación de valor.",
        ],
        "content": [
            "Vigilancia tecnológica e inteligencia competitiva.",
            "Transformación digital, modelos de adopción y gestión del cambio.",
            "Evaluación de viabilidad, impacto y valor de iniciativas digitales.",
        ],
    },
}


def _append_lines(original: str, additions: list[str]) -> str:
    lines = [line.strip() for line in (original or "").splitlines() if line.strip()]
    for addition in additions:
        if addition and addition not in lines:
            lines.append(addition)
    return "\n".join(lines)


def _rewrite_sections(document_name: str, sections: dict[str, str], focus: str) -> tuple[dict[str, str], list[CurriculumChange]]:
    enhancement = FOCUS_ENHANCEMENTS.get(focus, FOCUS_ENHANCEMENTS["visualizacion_interactiva"])
    rewritten = dict(sections)
    changes: list[CurriculumChange] = []
    for section in OFFICIAL_SECTIONS:
        original = sections.get(section, "")
        if section in IMMUTABLE_SECTIONS:
            action = "conservar"
            new_text = original
            reason = "Campo institucional sensible; no se modifica sin autorización explícita."
            signal = "formato institucional"
        elif section == "DESCRIPCIÓN DE LA ASIGNATURA":
            action = "actualizar"
            new_text = _append_lines(original, [enhancement["description"]])
            reason = "Se actualiza la descripción para alinear la asignatura con señales actuales del mercado laboral."
            signal = enhancement["signals"]
        elif section == "RESULTADOS DE APRENDIZAJE":
            action = "profundizar"
            new_text = _append_lines(original, enhancement["outcomes"])
            reason = "Se incorporan resultados de aprendizaje observables y pertinentes frente al subdominio."
            signal = enhancement["signals"]
        elif section == "CONTENIDO TEMÁTICO":
            action = "profundizar"
            new_text = _append_lines(original, enhancement["content"])
            reason = "Se profundiza contenido pertinente sin eliminar los temas vigentes del documento original."
            signal = enhancement["signals"]
        elif section == "ACTIVIDADES FORMATIVAS":
            action = "actualizar"
            new_text = _append_lines(
                original,
                [
                    "Desarrollo de un caso aplicado con datos reales o simulados, evidencia de decisiones y sustentación ejecutiva.",
                    "Laboratorio guiado para producir un entregable verificable alineado con el foco de la asignatura.",
                ],
            )
            reason = "Se agregan actividades prácticas trazables, manteniendo la orientación académica original."
            signal = enhancement["signals"]
        elif section == "MEDIOS EDUCATIVOS":
            action = "actualizar"
            new_text = _append_lines(
                original,
                [
                    "Datasets de práctica, notebooks o herramientas de analítica visual según disponibilidad institucional.",
                    "Recursos digitales para documentación, visualización, gobierno o procesamiento de datos según el foco de la asignatura.",
                ],
            )
            reason = "Se incorporan recursos educativos coherentes con analítica aplicada y trabajo práctico."
            signal = enhancement["signals"]
        elif section == "PERFIL DEL DOCENTE DE LA ASIGNATURA":
            action = "profundizar"
            new_text = _append_lines(
                original,
                [
                    "Experiencia demostrable en proyectos aplicados de analítica, inteligencia de negocio, gobierno de datos o big data relacionados con el foco de la asignatura.",
                ],
            )
            reason = "Se sugiere perfil docente alineado con práctica profesional y pertinencia laboral."
            signal = enhancement["signals"]
        elif section in REWRITABLE_SECTIONS:
            action = "conservar"
            new_text = original
            reason = "El contenido se considera pertinente y no requiere modificación automática."
            signal = "sin brecha crítica"
        else:
            action = "conservar"
            new_text = original
            reason = "Se conserva la estructura institucional original."
            signal = "formato institucional"
        rewritten[section] = new_text
        if new_text != original or action != "conservar":
            changes.append(
                CurriculumChange(
                    document_name=document_name,
                    section=section,
                    original_text=original,
                    action=action,
                    rewritten_text=new_text,
                    reason=reason,
                    market_signal=signal,
                    confidence=0.86 if action in {"actualizar", "profundizar"} else 0.74,
                )
            )
    return rewritten, changes


def rewrite_microcurriculum(path: str | Path, *, specialization: str = "Especialización en Visual Analytics y Big Data") -> dict[str, Any]:
    source = Path(path)
    sections = extract_template_sections(source)
    assignment = sections.get("DENOMINACIÓN DE LA ASIGNATURA") or source.stem
    if len(assignment) > 90 or "SEMESTRE" in assignment.upper() or "CR" in assignment.upper():
        assignment = source.stem.replace("Microcurrículos V5_", "").replace("Microcurriculos V5_", "")
        sections["DENOMINACIÓN DE LA ASIGNATURA"] = assignment
    focus = assignment_focus(f"{assignment} {source.name}")
    rewritten_sections, changes = _rewrite_sections(source.name, sections, focus)
    output_path = export_rewritten_docx(document_name=source.name, sections=rewritten_sections)
    return {
        "rewrite_id": output_path.stem,
        "document_name": source.name,
        "specialization": specialization,
        "assignment": assignment,
        "focus": focus,
        "file_path": str(output_path),
        "rewritten_curriculum": rewritten_sections,
        "change_traceability": [change.to_row() for change in changes],
    }


def rewrite_microcurriculum_batch(paths: list[Path], *, specialization: str) -> dict[str, Any]:
    items = [rewrite_microcurriculum(path, specialization=specialization) for path in paths]
    all_changes = [
        CurriculumChange(**change)
        for item in items
        for change in item.get("change_traceability", [])
    ]
    write_traceability_csv(all_changes, TRACEABILITY_OUTPUT)
    summary_path = write_summary_markdown(items, OUTPUT_DIR)
    return {
        "specialization": specialization,
        "documents_processed": len(items),
        "items": items,
        "traceability_path": str(TRACEABILITY_OUTPUT),
        "summary_path": str(summary_path),
        "output_dir": str(OUTPUT_DIR),
    }
