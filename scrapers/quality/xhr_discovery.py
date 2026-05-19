from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import Json, execute_values
from playwright.async_api import async_playwright

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


TARGETS = {
    "computrabajo": "https://co.computrabajo.com/trabajo-de-analista-de-datos",
    "elempleo": "https://www.elempleo.com/co/ofertas-empleo/?trabajo=analista%20de%20datos",
    "magneto": "https://www.magneto365.com/co/empleos?search=analista%20de%20datos",
    "torre": "https://torre.ai/search/jobs?q=analista%20de%20datos&location=Colombia",
}


@dataclass(frozen=True)
class EndpointHit:
    source: str
    url: str
    method: str
    resource_type: str
    status: int | None
    content_type: str
    sample: dict[str, Any]


def is_interesting(url: str, resource_type: str, content_type: str) -> bool:
    low = url.casefold()
    if resource_type in {"xhr", "fetch"}:
        return True
    if "json" in content_type.casefold():
        return True
    return any(token in low for token in ("api", "graphql", "search", "jobs", "empleos", "vacantes", "ofertas"))


async def discover_source(source: str, url: str, *, timeout_ms: int) -> list[EndpointHit]:
    hits: list[EndpointHit] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(locale="es-CO")
        page = await context.new_page()

        async def on_response(response):
            try:
                request = response.request
                content_type = response.headers.get("content-type", "")
                if not is_interesting(response.url, request.resource_type, content_type):
                    return
                sample: dict[str, Any] = {}
                if "json" in content_type.casefold():
                    try:
                        body = await response.json()
                        sample = {"json_type": type(body).__name__, "keys": list(body.keys())[:20] if isinstance(body, dict) else []}
                    except Exception:
                        sample = {"json_error": "unreadable"}
                hits.append(
                    EndpointHit(
                        source=source,
                        url=response.url,
                        method=request.method,
                        resource_type=request.resource_type,
                        status=response.status,
                        content_type=content_type,
                        sample=sample,
                    )
                )
            except Exception:
                return

        page.on("response", on_response)
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            await page.wait_for_timeout(9000)
        finally:
            await context.close()
            await browser.close()
    deduped = {hit.url: hit for hit in hits}
    return list(deduped.values())


async def discover_all(sources: list[str], *, timeout_ms: int) -> list[EndpointHit]:
    all_hits: list[EndpointHit] = []
    for source in sources:
        all_hits.extend(await discover_source(source, TARGETS[source], timeout_ms=timeout_ms))
    return all_hits


def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "cliente_a_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        sslmode=os.getenv("DB_SSLMODE", "prefer"),
    )


def upsert_hits(hits: list[EndpointHit]) -> None:
    if not hits:
        return
    with get_connection() as conn, conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO public.xhr_endpoint_discovery (
                source, url, method, resource_type, status, content_type, sample
            )
            VALUES %s
            ON CONFLICT (source, url)
            DO UPDATE SET
                method = EXCLUDED.method,
                resource_type = EXCLUDED.resource_type,
                status = EXCLUDED.status,
                content_type = EXCLUDED.content_type,
                sample = EXCLUDED.sample,
                discovered_at = now()
            """,
            [
                (
                    hit.source,
                    hit.url,
                    hit.method,
                    hit.resource_type,
                    hit.status,
                    hit.content_type,
                    Json(hit.sample),
                )
                for hit in hits
            ],
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover XHR/API/GraphQL endpoints for labor sources.")
    parser.add_argument("--sources", nargs="+", choices=sorted(TARGETS), default=sorted(TARGETS))
    parser.add_argument("--timeout-ms", type=int, default=30000)
    parser.add_argument("--output", default="outputs/labor_intelligence_stabilization/xhr_endpoint_discovery.json")
    parser.add_argument("--write-db", action="store_true")
    args = parser.parse_args()
    hits = asyncio.run(discover_all(args.sources, timeout_ms=args.timeout_ms))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps([asdict(hit) for hit in hits], ensure_ascii=False, indent=2), encoding="utf-8")
    if args.write_db:
        upsert_hits(hits)
    print(json.dumps({"hits": len(hits), "output": args.output}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

