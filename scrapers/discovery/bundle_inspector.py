from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scrapers.discovery.api_registry import (
    ApiEndpointCandidate,
    apply_schema,
    create_discovery_run,
    finish_discovery_run,
    register_candidates,
)
from scrapers.discovery.graphql_detector import extract_graphql_operations, is_graphql_endpoint


TARGETS = {
    "magneto": "https://www.magneto365.com/co/trabajos/buscar?search=analista%20de%20datos",
    "computrabajo": "https://co.computrabajo.com/trabajo-de-analista-de-datos",
    "elempleo": "https://www.elempleo.com/co/ofertas-empleo/trabajo-analista%20de%20datos",
    "torre": "https://torre.ai/search/jobs?q=analista%20de%20datos&location=Colombia",
    "spe": "https://www.serviciodeempleo.gov.co/busqueda-empleo?search=analista%20de%20datos&location=Colombia",
}


@dataclass(frozen=True)
class BundleFinding:
    source: str
    page_url: str
    bundle_url: str
    endpoint: str
    method: str
    evidence_type: str
    graphql_operations: list[str]


SCRIPT_RE = re.compile(r"<script[^>]+src=[\"']([^\"']+\.js[^\"']*)[\"']", re.IGNORECASE)
ENDPOINT_RE = re.compile(
    r"(https?://[^\"'`\\\s)]+|/[A-Za-z0-9_./-]*(?:api|graphql|search|vacanc|jobs|empleos|ofertas)[^\"'`\\\s)]*)",
    re.IGNORECASE,
)
FETCH_RE = re.compile(r"\b(fetch|axios\.(?:get|post|put)|XMLHttpRequest|WebSocket)\s*\(?\s*[\"'`]([^\"'`]+)", re.IGNORECASE)


def fetch_text(url: str) -> str:
    response = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"})
    response.raise_for_status()
    return response.text


def find_bundles(page_url: str, html: str) -> list[str]:
    bundles = [urljoin(page_url, match) for match in SCRIPT_RE.findall(html)]
    bundles.extend(urljoin(page_url, match) for match in re.findall(r"href=[\"']([^\"']+\.js[^\"']*)[\"']", html, flags=re.I))
    return list(dict.fromkeys(url for url in bundles if "_next/static" in url or ".js" in url))


def inspect_bundle(source: str, page_url: str, bundle_url: str, text: str) -> list[BundleFinding]:
    findings: list[BundleFinding] = []
    for endpoint in sorted(set(ENDPOINT_RE.findall(text))):
        endpoint_url = urljoin(page_url, endpoint)
        evidence = "graphql" if is_graphql_endpoint(endpoint_url, text) else "endpoint_literal"
        findings.append(BundleFinding(source, page_url, bundle_url, endpoint_url, "GET", evidence, extract_graphql_operations(text)))
    for _, endpoint in FETCH_RE.findall(text):
        endpoint_url = urljoin(page_url, endpoint)
        evidence = "graphql" if is_graphql_endpoint(endpoint_url, text) else "fetch_call"
        findings.append(BundleFinding(source, page_url, bundle_url, endpoint_url, "GET", evidence, extract_graphql_operations(text)))
    deduped = {(item.endpoint, item.bundle_url): item for item in findings}
    return list(deduped.values())


def inspect_source(source: str, page_url: str, *, max_bundles: int) -> list[BundleFinding]:
    html = fetch_text(page_url)
    bundles = find_bundles(page_url, html)[:max_bundles]
    findings: list[BundleFinding] = []
    findings.extend(inspect_bundle(source, page_url, page_url, html))
    for bundle_url in bundles:
        try:
            findings.extend(inspect_bundle(source, page_url, bundle_url, fetch_text(bundle_url)))
        except Exception:
            continue
    deduped = {(item.source, item.endpoint): item for item in findings}
    return list(deduped.values())


def to_candidate(finding: BundleFinding) -> ApiEndpointCandidate:
    response_type = "graphql" if finding.evidence_type == "graphql" else "bundle_literal"
    return ApiEndpointCandidate(
        source=finding.source,
        endpoint=finding.endpoint,
        method=finding.method,
        response_type=response_type,
        payload_sample={"bundle_url": finding.bundle_url, "evidence_type": finding.evidence_type, "graphql_operations": finding.graphql_operations[:20]},
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect JS bundles for API/XHR/GraphQL endpoints.")
    parser.add_argument("--sources", nargs="+", choices=sorted(TARGETS), default=sorted(TARGETS))
    parser.add_argument("--max-bundles", type=int, default=18)
    parser.add_argument("--output", default="outputs/api_discovery/bundle_findings.json")
    parser.add_argument("--write-db", action="store_true")
    parser.add_argument("--run-id", default=f"bundle_inspector_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
    args = parser.parse_args()
    findings: list[BundleFinding] = []
    errors = 0
    for source in args.sources:
        try:
            findings.extend(inspect_source(source, TARGETS[source], max_bundles=args.max_bundles))
        except Exception:
            errors += 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps([asdict(item) for item in findings], ensure_ascii=False, indent=2), encoding="utf-8")
    if args.write_db:
        apply_schema()
        create_discovery_run(args.run_id, source=",".join(args.sources), mode="bundle_inspector", metadata={"sources": args.sources})
        register_candidates([to_candidate(item) for item in findings], run_id=args.run_id)
        finish_discovery_run(args.run_id, endpoints_found=len(findings), errors=errors)
    print(json.dumps({"findings": len(findings), "errors": errors, "output": args.output, "run_id": args.run_id}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

