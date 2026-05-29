from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from microcurriculum_engine.embeddings.micro_embeddings import generate_microcurriculum_embeddings
from microcurriculum_engine.evaluation.scoring import score_microcurriculum
from microcurriculum_engine.ingestion.document_loader import LoadedDocument, load_document
from microcurriculum_engine.matching.market_matching import compare_microcurriculum_to_market
from microcurriculum_engine.normalization.skill_extractor import extract_microcurriculum_skills
from microcurriculum_engine.parsing.academic_parser import parse_microcurriculum
from microcurriculum_engine.recommendations.recommendation_engine import generate_recommendations
from microcurriculum_engine.storage.repository import new_run_id, persist_result


def _document_payload(document: LoadedDocument) -> dict[str, Any]:
    return {
        "source_document": document.source_document,
        "stored_path": document.stored_path,
        "filename": document.filename,
        "extension": document.extension,
        "content_hash": document.content_hash,
        "clean_text": document.clean_text,
        "extraction_method": document.extraction_method,
    }


def process_microcurriculum(
    path: str | Path,
    *,
    db_name: str | None = None,
    persist: bool = True,
    persist_original: bool = True,
    market_skills: list[str] | None = None,
) -> dict[str, Any]:
    if persist and not os.getenv("DB_HOST"):
        try:
            from dotenv import load_dotenv

            load_dotenv(".env")
            load_dotenv(".env.development")
        except Exception:
            pass
    run_id = new_run_id()
    document = load_document(path, persist_original=persist_original)
    parsed = parse_microcurriculum(document.clean_text)
    title = parsed.asignatura or parsed.programa or document.filename
    extracted = extract_microcurriculum_skills(document.clean_text, title=title)
    skills = extracted["skills"]
    domain = extracted["domain_prediction"]["domain"]
    skill_names = [skill["skill_normalized"] for skill in skills]
    comparison = compare_microcurriculum_to_market(skill_names, domain=domain, db_name=db_name, market_skills=market_skills)
    recommendations = generate_recommendations(domain=domain, comparison=comparison)
    scores = score_microcurriculum(
        comparison=comparison,
        skills_count=len(skill_names),
        competencies_count=len(parsed.competencias) + len(parsed.resultados_aprendizaje),
        recommendations_count=len(recommendations),
    )
    embedding_inputs = {
        "programa": parsed.programa or title,
        "asignatura": title,
        "competencias": " ".join(parsed.competencias + parsed.resultados_aprendizaje),
        "skills": " ".join(skill_names),
        "documento": document.clean_text[:6000],
    }
    embeddings = generate_microcurriculum_embeddings(embedding_inputs)
    result = {
        "run_id": run_id,
        "document": _document_payload(document),
        "parsed": parsed.to_dict(),
        "domain_prediction": extracted["domain_prediction"],
        "skills": skills,
        "rejected_skills": extracted["rejected_skills"],
        "market_comparison": asdict(comparison),
        "gaps": {
            "missing_skills": comparison.missing_skills,
            "weak_skills": comparison.weak_skills,
            "obsolete_skills": comparison.obsolete_skills,
        },
        "recommendations": recommendations,
        "scores": scores,
        "embeddings": embeddings,
        "lineage": {
            "pipeline": "microcurriculum_engine",
            "run_id": run_id,
            "source_document": document.source_document,
            "stored_path": document.stored_path,
            "taxonomy": "scrapers.taxonomy.domain_taxonomy",
            "domain_classifier": extracted["domain_prediction"].get("model_name"),
        },
        "metadata": {
            "skills_count": len(skills),
            "missing_skills_count": len(comparison.missing_skills),
            "recommendations_count": len(recommendations),
            "scores": scores,
        },
    }
    if persist:
        result["microcurriculo_id"] = persist_result(result, db_name=db_name)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Process one microcurriculum document into structured intelligence.")
    parser.add_argument("path")
    parser.add_argument("--no-persist", action="store_true")
    parser.add_argument("--db-name", default=None)
    parser.add_argument("--output", default="outputs/microcurriculum_result.json")
    args = parser.parse_args()
    result = process_microcurriculum(args.path, db_name=args.db_name, persist=not args.no_persist)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"microcurriculo_id": result.get("microcurriculo_id"), "output": str(target)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
