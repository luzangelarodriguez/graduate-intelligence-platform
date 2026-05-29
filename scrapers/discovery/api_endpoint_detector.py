from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

OUTPUT_JSON = ROOT_DIR / "outputs" / "job_api_discovery_report.json"
OUTPUT_MD = ROOT_DIR / "outputs" / "job_api_discovery_report.md"

PORTALS = {
    "linkedin": "https://www.linkedin.com/jobs",
    "elempleo": "https://www.elempleo.com/co/ofertas-empleo/",
    "ticjob": "https://ticjob.co/es/search",
    "hireline": "https://hireline.io/co/empleos",
    "computrabajo": "https://co.computrabajo.com",
    "spe": "https://www.buscadordeempleo.gov.co/#/home",
    "sena": "https://agenciapublicadeempleo.sena.edu.co",
    "findjobit": "https://findjobit.com/jobs/country/colombia",
}

API_PATTERNS = (
    "graphql",
    "/api/",
    "api/",
    "jobs/search",
    "joboffers",
    "vacancies",
    "vacantes",
    "ofertas",
    "ajax",
    "json",
    "search",
)

USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 Version/16.6 Safari/605.1.15",
)


@dataclass(frozen=True)
class DiscoveredEndpoint:
    source_name: str
    portal_url: str
    endpoint: str
    method: str
    resource_type: str
    response_type: str
    confidence: float
    reason: str
    discovered_at: str


def endpoint_confidence(url: str, resource_type: str, response_type: str) -> tuple[float, str]:
    normalized = url.casefold()
    hits = [pattern for pattern in API_PATTERNS if pattern in normalized]
    score = min(0.35 + len(hits) * 0.12, 0.92)
    if resource_type in {"xhr", "fetch"}:
        score += 0.08
    if "json" in response_type.casefold() or "graphql" in normalized:
        score += 0.1
    return round(min(score, 0.99), 4), ", ".join(hits) or resource_type


def is_interesting_request(url: str, resource_type: str) -> bool:
    normalized = url.casefold()
    return resource_type in {"xhr", "fetch"} or any(pattern in normalized for pattern in API_PATTERNS)


def detect_endpoints_for_portal(source_name: str, url: str, *, timeout_ms: int = 20000) -> list[DiscoveredEndpoint]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - optional runtime
        raise RuntimeError("Playwright is required for API endpoint discovery") from exc

    endpoints: dict[str, DiscoveredEndpoint] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport=random.choice(({"width": 1366, "height": 768}, {"width": 1440, "height": 900}, {"width": 1280, "height": 800})),
            locale="es-CO",
        )
        page = context.new_page()

        def on_response(response: Any) -> None:
            request = response.request
            resource_type = request.resource_type
            request_url = request.url
            if not is_interesting_request(request_url, resource_type):
                return
            response_type = response.headers.get("content-type", "")
            confidence, reason = endpoint_confidence(request_url, resource_type, response_type)
            endpoints.setdefault(
                f"{request.method}:{request_url}",
                DiscoveredEndpoint(
                    source_name=source_name,
                    portal_url=url,
                    endpoint=request_url,
                    method=request.method,
                    resource_type=resource_type,
                    response_type=response_type,
                    confidence=confidence,
                    reason=reason,
                    discovered_at=datetime.now(UTC).isoformat(),
                ),
            )

        page.on("response", on_response)
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(random.randint(1200, 2400))
        page.mouse.wheel(0, random.randint(500, 1200))
        page.wait_for_timeout(random.randint(800, 1600))
        browser.close()
    return sorted(endpoints.values(), key=lambda item: item.confidence, reverse=True)


def write_report(endpoints: list[DiscoveredEndpoint], errors: list[dict[str, str]]) -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps({"endpoints": [asdict(item) for item in endpoints], "errors": errors}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    lines = ["# Job API Discovery Report", "", f"- Endpoints detectados: {len(endpoints)}", f"- Errores: {len(errors)}", ""]
    for item in endpoints[:80]:
        lines.extend(
            [
                f"## {item.source_name}",
                f"- Endpoint: `{item.endpoint}`",
                f"- Metodo: {item.method}",
                f"- Tipo: {item.resource_type}",
                f"- Content-Type: {item.response_type or 'N/A'}",
                f"- Confidence: {item.confidence}",
                f"- Motivo: {item.reason}",
                "",
            ]
        )
    if errors:
        lines.extend(["## Errores", ""])
        lines.extend([f"- {error['source_name']}: {error['error_type']} - {error['error_message']}" for error in errors])
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_api_discovery(*, sources: list[str], execute_network: bool = False) -> dict[str, Any]:
    selected = {key: PORTALS[key] for key in sources if key in PORTALS} if sources else PORTALS
    if not execute_network:
        endpoints = [
            DiscoveredEndpoint(
                source_name=name,
                portal_url=url,
                endpoint=url,
                method="GET",
                resource_type="dry_run",
                response_type="unknown",
                confidence=0.0,
                reason="network_not_executed",
                discovered_at=datetime.now(UTC).isoformat(),
            )
            for name, url in selected.items()
        ]
        write_report(endpoints, [])
        return {"endpoints": len(endpoints), "errors": 0, "dry_run": True}

    endpoints: list[DiscoveredEndpoint] = []
    errors: list[dict[str, str]] = []
    for source_name, url in selected.items():
        try:
            endpoints.extend(detect_endpoints_for_portal(source_name, url))
        except Exception as exc:  # pragma: no cover - network behavior changes by portal
            errors.append({"source_name": source_name, "error_type": type(exc).__name__, "error_message": str(exc)[:500]})
    write_report(endpoints, errors)
    return {"endpoints": len(endpoints), "errors": len(errors), "dry_run": False}


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect labor portal API/XHR endpoints.")
    parser.add_argument("--sources", nargs="*", default=list(PORTALS))
    parser.add_argument("--execute-network", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run_api_discovery(sources=args.sources, execute_network=args.execute_network), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

