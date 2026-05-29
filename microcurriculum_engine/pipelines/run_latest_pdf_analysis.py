from __future__ import annotations

import argparse
import json
import time
import os
from pathlib import Path
from typing import Any

from microcurriculum_engine.pipelines.process_microcurriculum import process_microcurriculum


STORAGE_DIR = Path("storage/microcurriculos")
JSON_OUTPUT = Path("outputs/microcurriculum_analysis.json")
INSIGHTS_OUTPUT = Path("outputs/microcurriculum_insights.md")


def latest_pdf(storage_dir: Path = STORAGE_DIR) -> Path:
    import re

    all_pdfs = sorted(storage_dir.glob("*.pdf"), key=lambda path: path.stat().st_mtime, reverse=True)
    pdfs = [path for path in all_pdfs if not re.match(r"^\d{8}_\d{6}_", path.name)] or all_pdfs
    if not pdfs:
        raise FileNotFoundError(f"No PDF files found in {storage_dir}")
    return pdfs[0]


def pdf_page_diagnostics(path: Path) -> dict[str, Any]:
    try:
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            page_texts = [page.extract_text() or "" for page in pdf.pages]
        return {
            "page_count": len(page_texts),
            "chars_by_page": [len(text) for text in page_texts],
            "extraction_probe": "pdfplumber",
        }
    except Exception as pdfplumber_error:
        try:
            import fitz

            with fitz.open(path) as document:
                page_texts = [page.get_text("text") for page in document]
            return {
                "page_count": len(page_texts),
                "chars_by_page": [len(text) for text in page_texts],
                "extraction_probe": "pymupdf",
            }
        except Exception as pymupdf_error:
            return {
                "page_count": 0,
                "chars_by_page": [],
                "extraction_probe": "unavailable",
                "errors": [str(pdfplumber_error), str(pymupdf_error)],
            }


def compact_analysis(result: dict[str, Any], diagnostics: dict[str, Any], elapsed_seconds: float) -> dict[str, Any]:
    parsed = result.get("parsed") or {}
    clean_text = result.get("document", {}).get("clean_text") or ""
    detected_subjects = detect_subjects(clean_text)
    skills = result.get("skills") or []
    platforms = [
        skill["skill_normalized"]
        for skill in skills
        if skill.get("tipo_skill") in {
            "plataforma",
            "herramienta",
            "framework",
            "platform",
            "tool",
            "cloud_provider",
            "database",
        }
    ]
    competencias = [*(parsed.get("competencias") or []), *(parsed.get("resultados_aprendizaje") or [])]
    recommendations = result.get("recommendations") or []
    return {
        "programa": parsed.get("programa") or "",
        "asignaturas": detected_subjects or [
            {
                "nombre": parsed.get("asignatura") or "",
                "semestre": parsed.get("semestre") or "",
                "creditos": parsed.get("creditos") or "",
                "contenidos": parsed.get("contenidos") or [],
                "metodologias": parsed.get("metodologias") or [],
            }
        ],
        "skills": [skill["skill_normalized"] for skill in skills],
        "platforms": sorted(set(platforms)),
        "competencias": competencias,
        "missing_market_skills": result.get("gaps", {}).get("missing_skills", []),
        "recommendations": [
            {
                **item,
                "text": item.get("recommendation_text"),
                "confidence": item.get("confidence_score"),
            }
            for item in recommendations
        ],
        "scores": result.get("scores") or {},
        "diagnostics": {
            "source_document": result.get("document", {}).get("source_document"),
            "stored_path": result.get("document", {}).get("stored_path"),
            "microcurriculo_id": result.get("microcurriculo_id"),
            "run_id": result.get("run_id"),
            "page_count": diagnostics.get("page_count"),
            "chars_by_page": diagnostics.get("chars_by_page"),
            "extraction_probe": diagnostics.get("extraction_probe"),
            "extraction_method": result.get("document", {}).get("extraction_method"),
            "clean_text_chars": len(result.get("document", {}).get("clean_text") or ""),
            "clean_text_preview": (result.get("document", {}).get("clean_text") or "")[:1200],
            "domain": result.get("domain_prediction", {}).get("domain"),
            "confidence": result.get("domain_prediction", {}).get("confidence"),
            "confidence_level": result.get("domain_prediction", {}).get("confidence_level"),
            "processing_seconds": round(elapsed_seconds, 3),
        },
    }


def detect_subjects(text: str) -> list[dict[str, Any]]:
    patterns = (
        (r"Plataformas de\s+desarrollo de\s+software", "Plataformas de desarrollo de software"),
        (r"Desarrollo de\s+aplicaciones\s+WEB", "Desarrollo de aplicaciones WEB"),
        (r"Dise[ñn]o y arquitectura\s+de software", "Diseno y arquitectura de software"),
        (r"Direcci[oó]n y gesti[oó]n\s+de proyectos", "Direccion y gestion de proyectos"),
        (r"Calidad de software", "Calidad de software"),
        (r"Seguridad en el desarrollo\s+de software", "Seguridad en el desarrollo de software"),
        (r"Computaci[oó]n en la nube", "Computacion en la nube"),
        (r"DevOps", "DevOps"),
    )
    subjects: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pattern, name in patterns:
        if re_search(pattern, text) and name.casefold() not in seen:
            subjects.append({"nombre": name, "semestre": "", "creditos": "", "contenidos": [], "metodologias": []})
            seen.add(name.casefold())
    return subjects


def re_search(pattern: str, text: str) -> bool:
    import re

    return re.search(pattern, text, re.I | re.S) is not None


def write_insights(analysis: dict[str, Any], output: Path = INSIGHTS_OUTPUT) -> None:
    scores = analysis.get("scores") or {}
    diagnostics = analysis.get("diagnostics") or {}
    lines = [
        "# Microcurriculum Insights",
        "",
        f"- Documento: `{diagnostics.get('source_document')}`",
        f"- Microcurriculo ID: `{diagnostics.get('microcurriculo_id')}`",
        f"- Paginas procesadas: `{diagnostics.get('page_count')}`",
        f"- Caracteres extraidos: `{diagnostics.get('clean_text_chars')}`",
        f"- Dominio detectado: `{diagnostics.get('domain')}`",
        f"- Confidence: `{diagnostics.get('confidence')}` ({diagnostics.get('confidence_level')})",
        f"- Tiempo procesamiento: `{diagnostics.get('processing_seconds')}s`",
        "",
        "## Programa y Asignatura",
        "",
        f"- Programa: {analysis.get('programa') or 'No detectado'}",
        f"- Asignatura: {(analysis.get('asignaturas') or [{}])[0].get('nombre') or 'No detectada'}",
        "",
        "## Skills Detectadas",
        "",
        ", ".join(analysis.get("skills") or []) or "Sin skills detectadas.",
        "",
        "## Plataformas y Herramientas",
        "",
        ", ".join(analysis.get("platforms") or []) or "Sin plataformas detectadas.",
        "",
        "## Competencias Detectadas",
        "",
        *[f"- {item}" for item in (analysis.get("competencias") or [])[:12]],
        "",
        "## Gaps Frente al Mercado",
        "",
        *[f"- {item}" for item in (analysis.get("missing_market_skills") or [])[:12]],
        "",
        "## Recomendaciones",
        "",
        *[
            f"- **{item.get('title')}** ({item.get('confidence')}): {item.get('text')}"
            for item in (analysis.get("recommendations") or [])[:8]
        ],
        "",
        "## Scores",
        "",
        *[f"- {key}: {value}" for key, value in scores.items()],
        "",
        "## Validacion Cualitativa",
        "",
        f"- Tecnologias modernas detectadas: {'si' if analysis.get('platforms') else 'parcial/no'}",
        f"- Gaps coherentes: {'si' if analysis.get('missing_market_skills') else 'requiere mas evidencia laboral'}",
        f"- Recomendaciones curriculares: {'si' if analysis.get('recommendations') else 'no generadas'}",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def run(*, storage_dir: Path = STORAGE_DIR, persist: bool = True) -> dict[str, Any]:
    if not os.getenv("DB_HOST"):
        try:
            from dotenv import load_dotenv

            load_dotenv(".env")
            load_dotenv(".env.development")
        except Exception:
            pass
    pdf = latest_pdf(storage_dir)
    diagnostics = pdf_page_diagnostics(pdf)
    started = time.perf_counter()
    result = process_microcurriculum(pdf, persist=persist)
    elapsed = time.perf_counter() - started
    analysis = compact_analysis(result, diagnostics, elapsed)
    JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT.write_text(json.dumps(analysis, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    write_insights(analysis)
    print(json.dumps({
        "pdf": str(pdf),
        "microcurriculo_id": analysis["diagnostics"]["microcurriculo_id"],
        "pages": analysis["diagnostics"]["page_count"],
        "skills": len(analysis["skills"]),
        "gaps": len(analysis["missing_market_skills"]),
        "json_output": str(JSON_OUTPUT),
        "insights_output": str(INSIGHTS_OUTPUT),
    }, ensure_ascii=False))
    return analysis


def main() -> int:
    parser = argparse.ArgumentParser(description="Run end-to-end analysis on the latest PDF in storage/microcurriculos.")
    parser.add_argument("--storage-dir", default=str(STORAGE_DIR))
    parser.add_argument("--no-persist", action="store_true")
    args = parser.parse_args()
    run(storage_dir=Path(args.storage_dir), persist=not args.no_persist)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
