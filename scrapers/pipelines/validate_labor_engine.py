from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scrapers.normalization.classify_domains import is_domain_compatible
from scrapers.normalization.deduplicate_jobs import deduplicate_jobs
from scrapers.pipelines.jobs_pipeline import configure_logging, normalize_job, scrape_sources


DOMAIN_QUERIES = {
    "ambiental_energia": {
        "expected_domains": {"ambiental", "energia"},
        "query": "sostenibilidad ESG eficiencia energetica huella de carbono ISO 14001 energias renovables",
    },
    "datos_analitica": {
        "expected_domains": {"analitica", "ti"},
        "query": "analista de datos power bi sql python big data visual analytics",
    },
    "ciberseguridad": {
        "expected_domains": {"cybersecurity", "ti"},
        "query": "seguridad informatica ciberseguridad SOC ISO 27001 ethical hacking",
    },
    "gestion_humana": {
        "expected_domains": {"gestion_humana", "management"},
        "query": "recursos humanos talento humano compensacion seleccion bienestar organizacional",
    },
    "derecho_digital": {
        "expected_domains": {"legal-tech", "legal"},
        "query": "derecho digital proteccion de datos habeas data compliance legaltech",
    },
    "educacion": {
        "expected_domains": {"educacion"},
        "query": "educacion inclusiva orientacion familiar pedagogia TIC educativas",
    },
}


def summarize_domain(
    domain_key: str,
    query: str,
    expected_domains: set[str],
    raw_jobs: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    accepted_skills = Counter(skill for job in jobs for skill in job.get("skills", []))
    rejected_skills = Counter(skill for job in jobs for skill in job.get("skills_rechazadas", []))
    assigned_domains = Counter(job.get("dominio") or "sin_dominio" for job in jobs)
    source_counts = Counter(job.get("portal") or "sin_fuente" for job in jobs)
    contaminated = [
        {
            "id": job.get("id"),
            "portal": job.get("portal"),
            "titulo": job.get("titulo"),
            "dominio": job.get("dominio"),
            "skills": job.get("skills", []),
        }
        for job in jobs
        if not any(is_domain_compatible(expected, job.get("dominio")) for expected in expected_domains)
    ]
    duplicate_count = max(0, len(raw_jobs) - len(jobs))
    precision = round(((len(jobs) - len(contaminated)) / len(jobs)) * 100, 2) if jobs else 0.0
    avg_disciplinary = (
        round(sum(float(job.get("score_disciplinar") or 0) for job in jobs) / len(jobs), 3) if jobs else 0.0
    )
    return {
        "domain": domain_key,
        "query": query,
        "expected_domains": sorted(expected_domains),
        "raw_jobs": len(raw_jobs),
        "normalized_jobs": len(jobs),
        "duplicates_removed": duplicate_count,
        "precision_observed_pct": precision,
        "avg_disciplinary_score": avg_disciplinary,
        "assigned_domains": dict(assigned_domains),
        "source_counts": dict(source_counts),
        "top_accepted_skills": accepted_skills.most_common(15),
        "top_rejected_skills": rejected_skills.most_common(15),
        "contaminations": contaminated[:20],
        "sample_jobs": [
            {
                "portal": job.get("portal"),
                "titulo": job.get("titulo"),
                "empresa": job.get("empresa"),
                "ciudad": job.get("ciudad"),
                "dominio": job.get("dominio"),
                "skills": job.get("skills", [])[:8],
                "skills_rechazadas": job.get("skills_rechazadas", [])[:8],
                "url": job.get("url"),
            }
            for job in jobs[:10]
        ],
    }


def write_json(path: Path, data: Any) -> None:
    def default(value: Any) -> Any:
        if is_dataclass(value):
            return asdict(value)
        if isinstance(value, set):
            return sorted(value)
        return str(value)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=default), encoding="utf-8")


def write_markdown_report(path: Path, results: list[dict[str, Any]], source_errors: dict[str, Any]) -> None:
    lines: list[str] = [
        "# Labor Engine Validation Phase 1",
        "",
        f"Fecha ejecucion: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Alcance",
        "",
        "Validacion controlada por dominios del motor laboral enterprise. No se modifico frontend, no se eliminaron datos y la corrida se realizo con limites bajos por dominio.",
        "",
        "## Resumen ejecutivo",
        "",
        "| Dominio | Empleos normalizados | Duplicados | Precision observada | Score disciplinar promedio | Dominios asignados |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for item in results:
        lines.append(
            f"| {item['domain']} | {item['normalized_jobs']} | {item['duplicates_removed']} | "
            f"{item['precision_observed_pct']}% | {item['avg_disciplinary_score']} | {item['assigned_domains']} |"
        )

    lines.extend(["", "## Resultados por dominio", ""])
    for item in results:
        lines.extend(
            [
                f"### {item['domain']}",
                "",
                f"Query: `{item['query']}`",
                "",
                f"- Empleos extraidos raw: {item['raw_jobs']}",
                f"- Empleos normalizados: {item['normalized_jobs']}",
                f"- Duplicados removidos: {item['duplicates_removed']}",
                f"- Precision observada: {item['precision_observed_pct']}%",
                f"- Score disciplinar promedio: {item['avg_disciplinary_score']}",
                f"- Dominios asignados: `{item['assigned_domains']}`",
                f"- Fuentes con resultados: `{item['source_counts']}`",
                "",
                "Skills aceptadas principales:",
                "",
            ]
        )
        if item["top_accepted_skills"]:
            lines.extend([f"- {skill}: {count}" for skill, count in item["top_accepted_skills"]])
        else:
            lines.append("- Sin skills aceptadas detectadas.")
        lines.extend(["", "Skills rechazadas principales:", ""])
        if item["top_rejected_skills"]:
            lines.extend([f"- {skill}: {count}" for skill, count in item["top_rejected_skills"]])
        else:
            lines.append("- Sin skills rechazadas detectadas.")
        lines.extend(["", "Contaminaciones detectadas:", ""])
        if item["contaminations"]:
            for contamination in item["contaminations"][:10]:
                lines.append(f"- {contamination.get('titulo')} ({contamination.get('portal')}): dominio `{contamination.get('dominio')}`")
        else:
            lines.append("- No se detectaron contaminaciones disciplinarias en la muestra normalizada.")
        lines.extend(["", "Muestra de empleos:", ""])
        if item["sample_jobs"]:
            for job in item["sample_jobs"][:5]:
                lines.append(f"- {job.get('titulo') or 'Sin titulo'} | {job.get('portal')} | {job.get('dominio')} | {', '.join(job.get('skills', [])[:5])}")
        else:
            lines.append("- Sin empleos disponibles para muestra.")
        lines.append("")

    lines.extend(
        [
            "## Fuentes que fallaron o quedaron sin evidencia",
            "",
            "La tabla siguiente resume errores capturados por el runner. Cuando una fuente no entrega resultados puede deberse a selectores, carga JS, bloqueo, cambios de portal o ausencia de resultados para la query.",
            "",
        ]
    )
    if source_errors:
        for key, value in source_errors.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- No se capturaron excepciones de alto nivel en el runner. Revisar `logs/labor_engine_validation_phase_1.log` para errores internos por fuente.")

    lines.extend(
        [
            "",
            "## Recomendaciones de ajuste taxonomico",
            "",
            "- Ampliar `skills_master` para gestion humana: compensacion, seleccion, bienestar, cultura organizacional y people analytics.",
            "- Ampliar educacion: educacion inclusiva, orientacion familiar, TIC educativas, diseno universal de aprendizaje y neuroeducacion.",
            "- Separar con mas fuerza `legal-tech` de `cybersecurity`: proteccion de datos puede convivir con seguridad, pero no debe convertir todo derecho digital en TI.",
            "- Para datos/analitica, distinguir herramientas (`Power BI`, `SQL`, `Python`) de capacidades (`gobierno de datos`, `visual analytics`, `modelado`).",
            "- Mantener reglas de exclusion ambiental/energia vs TI/cybersecurity, porque son criticas para pertinencia curricular.",
            "",
            "## Proximos ajustes",
            "",
            "1. Ejecutar corrida por fuente individual para ajustar selectores live.",
            "2. Revisar screenshots en `logs/screenshots` cuando una fuente no entregue cards.",
            "3. Identificar endpoints XHR/API de cada portal con Playwright tracing antes de aumentar volumen.",
            "4. Crear pruebas unitarias de contaminacion disciplinar por dominio.",
            "5. Solo conectar el dashboard cuando precision por dominio sea estable y trazable.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_validation(args: argparse.Namespace) -> list[dict[str, Any]]:
    output_dir = Path(args.output_dir)
    results: list[dict[str, Any]] = []
    source_errors: dict[str, str] = {}
    for domain_key, config in DOMAIN_QUERIES.items():
        logging.info("validating domain=%s", domain_key)
        raw_jobs: list[dict[str, Any]] = []
        try:
            raw_jobs = scrape_sources(args.sources, config["query"], args.location, args.limit, args.headless)
        except Exception as exc:
            logging.exception("domain=%s failed", domain_key)
            source_errors[domain_key] = repr(exc)
        normalized_jobs = deduplicate_jobs([normalize_job(job) for job in raw_jobs])
        result = summarize_domain(
            domain_key,
            config["query"],
            set(config["expected_domains"]),
            raw_jobs,
            normalized_jobs,
        )
        results.append(result)
        write_json(output_dir / f"{domain_key}.json", {"raw_jobs": raw_jobs, "normalized_jobs": normalized_jobs, "summary": result})

    write_json(output_dir / "summary.json", {"results": results, "source_errors": source_errors})
    write_markdown_report(Path(args.report), results, source_errors)
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate labor engine extraction and domain quality.")
    parser.add_argument("--sources", nargs="+", choices=("spe", "computrabajo", "elempleo", "magneto", "torre"), default=["spe", "computrabajo", "elempleo"])
    parser.add_argument("--limit", type=int, default=50, help="Limit per domain distributed across sources.")
    parser.add_argument("--location", default="Colombia")
    parser.add_argument("--headless", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--output-dir", default="outputs/labor_engine_validation_phase_1")
    parser.add_argument("--report", default="docs/LABOR_ENGINE_VALIDATION_PHASE_1.md")
    parser.add_argument("--log-file", default="logs/labor_engine_validation_phase_1.log")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(Path(args.log_file))
    results = run_validation(args)
    print(json.dumps({"domains": len(results), "report": args.report}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
