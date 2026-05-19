from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scrapers.discovery.api_registry import (
    ApiEndpointCandidate,
    apply_schema,
    create_discovery_run,
    finish_discovery_run,
    register_candidates,
    register_response_snapshots,
)


TARGETS = {
    "magneto": "https://www.magneto365.com/co/trabajos/buscar?search=analista%20de%20datos",
    "computrabajo": "https://co.computrabajo.com/trabajo-de-analista-de-datos",
    "elempleo": "https://www.elempleo.com/co/ofertas-empleo/trabajo-analista%20de%20datos",
    "torre": "https://torre.ai/search/jobs?q=analista%20de%20datos&location=Colombia",
    "spe": "https://www.serviciodeempleo.gov.co/busqueda-empleo?search=analista%20de%20datos&location=Colombia",
}


@dataclass(frozen=True)
class CapturedRequest:
    source: str
    url: str
    method: str
    resource_type: str
    status: int | None
    content_type: str
    duration_ms: int | None
    request_headers: dict[str, Any]
    request_payload: Any | None
    response_sample: Any | None


def interesting_url(url: str, resource_type: str, content_type: str) -> bool:
    low = url.casefold()
    if resource_type in {"xhr", "fetch"}:
        return True
    if "json" in content_type.casefold():
        return True
    return any(token in low for token in ("api", "graphql", "algolia", "elastic", "search", "vacanc", "job", "empleo", "oferta"))


async def capture_source(source: str, url: str, *, wait_ms: int, timeout_ms: int) -> list[CapturedRequest]:
    captured: list[CapturedRequest] = []
    started: dict[Any, float] = {}
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(locale="es-CO")
        page = await context.new_page()

        def on_request(request):
            started[request] = time.perf_counter()

        async def on_response(response):
            try:
                request = response.request
                content_type = response.headers.get("content-type", "")
                if not interesting_url(response.url, request.resource_type, content_type):
                    return
                sample = None
                if "json" in content_type.casefold():
                    try:
                        body = await response.json()
                        sample = body if len(json.dumps(body, ensure_ascii=False, default=str)) < 30000 else {"sample_too_large": True}
                    except Exception:
                        sample = {"json_error": "unreadable"}
                duration = None
                if request in started:
                    duration = int((time.perf_counter() - started[request]) * 1000)
                captured.append(
                    CapturedRequest(
                        source,
                        response.url,
                        request.method,
                        request.resource_type,
                        response.status,
                        content_type,
                        duration,
                        await request.all_headers(),
                        request.post_data_json if request.post_data else None,
                        sample,
                    )
                )
            except Exception:
                return

        page.on("request", on_request)
        page.on("response", on_response)
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            await page.wait_for_timeout(wait_ms)
        finally:
            await context.close()
            await browser.close()
    deduped = {item.url: item for item in captured}
    return list(deduped.values())


async def capture_all(sources: list[str], *, wait_ms: int, timeout_ms: int) -> list[CapturedRequest]:
    output: list[CapturedRequest] = []
    for source in sources:
        output.extend(await capture_source(source, TARGETS[source], wait_ms=wait_ms, timeout_ms=timeout_ms))
    return output


def to_candidate(item: CapturedRequest) -> ApiEndpointCandidate:
    return ApiEndpointCandidate(
        source=item.source,
        endpoint=item.url,
        method=item.method,
        response_type=item.content_type,
        status=item.status,
        resource_type=item.resource_type,
        payload_sample=item.response_sample,
        request_headers=item.request_headers,
        request_payload=item.request_payload,
        duration_ms=item.duration_ms,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture XHR/fetch/API traffic for labor portals.")
    parser.add_argument("--sources", nargs="+", choices=sorted(TARGETS), default=sorted(TARGETS))
    parser.add_argument("--wait-ms", type=int, default=9000)
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--output", default="outputs/api_discovery/xhr_capture.json")
    parser.add_argument("--write-db", action="store_true")
    parser.add_argument("--run-id", default=f"xhr_capture_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
    args = parser.parse_args()
    hits = asyncio.run(capture_all(args.sources, wait_ms=args.wait_ms, timeout_ms=args.timeout_ms))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps([asdict(hit) for hit in hits], ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    if args.write_db:
        apply_schema()
        create_discovery_run(args.run_id, source=",".join(args.sources), mode="xhr_capture", metadata={"sources": args.sources})
        candidates = [to_candidate(hit) for hit in hits]
        register_candidates(candidates, run_id=args.run_id)
        register_response_snapshots(candidates)
        finish_discovery_run(args.run_id, endpoints_found=len(candidates))
    print(json.dumps({"hits": len(hits), "output": args.output, "run_id": args.run_id}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

