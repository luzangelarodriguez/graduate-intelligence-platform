from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import socket
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import unicodedata
from html import unescape
from html.parser import HTMLParser
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple
from urllib.parse import parse_qs, quote, urlencode, urljoin, urlparse, urlunparse


BASE_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = BASE_DIR / "graduate_intelligence_platform" / "backend"
if BACKEND_DIR.exists() and str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
try:
    import requests
except Exception:  # pragma: no cover - optional dependency fallback
    requests = None
SELENIUM_DEPS_DIR = BASE_DIR / "selenium_deps"
if SELENIUM_DEPS_DIR.exists() and str(SELENIUM_DEPS_DIR) not in sys.path:
    sys.path.insert(0, str(SELENIUM_DEPS_DIR))
VENDOR_DIR = BASE_DIR / "vendor"
if VENDOR_DIR.exists() and str(VENDOR_DIR) not in sys.path:
    sys.path.append(str(VENDOR_DIR))

try:
    from app.engine import SKILL_CATALOG, extract_skills_from_text, normalize_text, repair_text
except Exception:  # pragma: no cover - import fallback for isolated use
    SKILL_CATALOG = []

    def repair_text(value: Any) -> str:
        return "" if value is None else str(value)

    def normalize_text(value: Any) -> str:
        if value is None:
            return ""
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(value).lower())).strip()

    def extract_skills_from_text(text: str) -> List[Dict[str, Any]]:
        return []


JOB_FIELDS = ["job_id", "job_title", "company", "description", "location", "date", "source"]
JOB_SKILL_FIELDS = ["job_id", "job_title", "skill_name", "confidence"]
TRAINING_JSONL_SYSTEM_PROMPT = (
    "Extrae habilidades laborales normalizadas desde una vacante. "
    "Devuelve solo JSON valido con esta forma: "
    '{"skills":[{"skill_name":"...","confidence":0.0}],"role_hint":"...","quality_flags":[]}. '
    "No incluyas requisitos academicos, horarios, beneficios, frases largas ni texto que no sea habilidad."
)
MIN_JOB_DATE = date(2026, 4, 1)

FIELD_ALIASES = {
    "job_id": ["job_id", "id", "external_id", "listing_id", "uuid", "jobId"],
    "job_title": ["job_title", "title", "position", "role", "jobTitle"],
    "company": ["company", "company_name", "employer", "organization", "employer_name"],
    "description": ["description", "summary", "job_description", "body", "content", "details"],
    "location": ["location", "city", "workplace", "place", "remote"],
    "date": [
        "date",
        "datePosted",
        "datePublished",
        "postedAt",
        "publishedAt",
        "createdAt",
        "publishedDate",
        "postedOn",
        "publishedOn",
        "createdOn",
        "posted_at",
        "published_at",
        "created_at",
        "published_date",
        "date_posted",
        "dateposted",
        "postedon",
        "publishedon",
        "createdon",
    ],
    "source": ["source", "source_name", "origin"],
}

SPANISH_MONTHS = {
    "enero": 1,
    "ene": 1,
    "febrero": 2,
    "feb": 2,
    "marzo": 3,
    "mar": 3,
    "abril": 4,
    "abr": 4,
    "mayo": 5,
    "may": 5,
    "junio": 6,
    "jun": 6,
    "julio": 7,
    "jul": 7,
    "agosto": 8,
    "ago": 8,
    "septiembre": 9,
    "setiembre": 9,
    "sep": 9,
    "sept": 9,
    "octubre": 10,
    "oct": 10,
    "noviembre": 11,
    "nov": 11,
    "diciembre": 12,
    "dic": 12,
}

SKILL_ALIAS_TO_CANONICAL: Dict[str, str] = {}
for item in SKILL_CATALOG:
    canonical = repair_text(item.get("name", "")).strip()
    if not canonical:
        continue
    SKILL_ALIAS_TO_CANONICAL[normalize_text(canonical)] = canonical
    for alias in item.get("aliases") or []:
        alias_key = normalize_text(alias)
        if alias_key:
            SKILL_ALIAS_TO_CANONICAL[alias_key] = canonical


def coalesce(*values: Any, default: str = "") -> str:
    for value in values:
        if value is None:
            continue
        text = repair_text(value).strip()
        if text:
            return text
    return default


def unique(values: Sequence[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for value in values:
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def find_browser_executable() -> Optional[str]:
    candidates = [
        os.getenv("CHROME_BIN"),
        os.getenv("EDGE_BIN"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for executable_path in candidates:
        if executable_path and Path(executable_path).exists():
            return executable_path
    return None


def render_html_via_cdp(url: str, timeout: int = 30) -> str:
    browser_executable = find_browser_executable()
    if not browser_executable:
        raise RuntimeError("No Chromium-based browser executable was found.")

    try:
        from websocket import create_connection  # type: ignore
    except Exception as exc:
        raise RuntimeError("Browser rendering requested but websocket-client is not installed.") from exc

    profile_dir = Path(tempfile.mkdtemp(prefix="job_crawl_browser_"))
    proc: Optional[subprocess.Popen[Any]] = None
    ws = None

    try:
        args = [
            browser_executable,
            "--remote-debugging-port=0",
            f"--user-data-dir={profile_dir}",
            "--headless",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-background-networking",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-sync",
            "--remote-allow-origins=*",
            "--no-first-run",
            "--no-default-browser-check",
            "--mute-audio",
            "--window-size=1440,2200",
            "about:blank",
        ]
        proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            cwd=str(BASE_DIR),
        )

        devtools_file = profile_dir / "DevToolsActivePort"
        deadline = time.time() + max(timeout, 10)
        version_payload: Dict[str, Any] = {}
        while time.time() < deadline:
            if devtools_file.exists():
                try:
                    lines = devtools_file.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if len(lines) >= 2 and lines[0].strip().isdigit():
                        port = int(lines[0].strip())
                        websocket_path = lines[1].strip()
                        if websocket_path:
                            version_payload["webSocketDebuggerUrl"] = f"ws://127.0.0.1:{port}{websocket_path}"
                            break
                except Exception:
                    pass
            time.sleep(0.25)
        else:
            raise RuntimeError("Chromium remote debugging endpoint did not become ready.")

        target_url = f"http://127.0.0.1:{port}/json/new?{quote(url, safe='')}"
        target_response = requests.put(target_url, timeout=5)
        if not target_response.ok:
            raise RuntimeError(f"Chromium page target could not be created: {target_response.status_code}")
        target_payload = target_response.json()
        ws_url = target_payload.get("webSocketDebuggerUrl")
        if not ws_url:
            raise RuntimeError("Chromium page target did not expose a webSocketDebuggerUrl.")

        ws = create_connection(str(ws_url), timeout=timeout)
        message_id = 0

        def cdp_call(method: str, params: Optional[Dict[str, Any]] = None, wait_for_result: bool = True) -> Dict[str, Any]:
            nonlocal message_id
            message_id += 1
            payload: Dict[str, Any] = {"id": message_id, "method": method}
            if params:
                payload["params"] = params
            ws.send(json.dumps(payload))
            if not wait_for_result:
                return {}
            while True:
                raw = ws.recv()
                data = json.loads(raw)
                if data.get("id") == message_id:
                    if "error" in data:
                        raise RuntimeError(f"CDP {method} failed: {data['error']}")
                    return data.get("result") or {}

        cdp_call("Page.enable")
        cdp_call("Runtime.enable")
        cdp_call("Network.enable")
        cdp_call("Page.setLifecycleEventsEnabled", {"enabled": True})
        cdp_call("Page.navigate", {"url": url})

        page_loaded = False
        poll_deadline = time.time() + timeout
        while time.time() < poll_deadline:
            remaining = max(1, int(poll_deadline - time.time()))
            ws.settimeout(remaining)
            try:
                raw = ws.recv()
            except Exception:
                break
            data = json.loads(raw)
            event = data.get("method")
            if event in {"Page.loadEventFired", "Page.domContentEventFired"}:
                page_loaded = True
                break
            if event == "Page.lifecycleEvent" and data.get("params", {}).get("name") in {"load", "networkIdle"}:
                page_loaded = True
                break
        if not page_loaded:
            time.sleep(1)

        result = cdp_call(
            "Runtime.evaluate",
            {
                "expression": "document.documentElement.outerHTML",
                "returnByValue": True,
                "awaitPromise": True,
            },
        )
        value = result.get("result", {}).get("value")
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError("Chromium CDP renderer returned empty HTML.")
        return value
    finally:
        try:
            if ws is not None:
                ws.close()
        except Exception:
            pass
        try:
            if proc is not None:
                proc.terminate()
                proc.wait(timeout=5)
        except Exception:
            try:
                if proc is not None:
                    proc.kill()
            except Exception:
                pass
        try:
            import shutil

            shutil.rmtree(profile_dir, ignore_errors=True)
        except Exception:
            pass


def safe_json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def get_path(value: Any, path: Optional[str]) -> Any:
    if value is None or not path:
        return value
    current = value
    for part in str(path).split("."):
        if current is None:
            return None
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
            continue
        if isinstance(current, dict):
            current = current.get(part)
            continue
        return None
    return current


def resolve_path(path: str, base_dir: Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return (base_dir / candidate).resolve()


def read_text_with_fallback(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


class PortalHTMLCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: List[Dict[str, Any]] = []
        self.scripts: List[Dict[str, Any]] = []
        self.metas: List[Dict[str, str]] = []
        self._current_link: Optional[Dict[str, Any]] = None
        self._current_script: Optional[Dict[str, Any]] = None

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr_map = {key.lower(): (value or "") for key, value in attrs}
        if tag.lower() == "a":
            self._current_link = {"href": attr_map.get("href", ""), "text": "", "attrs": attr_map}
        elif tag.lower() == "script":
            self._current_script = {"text": "", "attrs": attr_map}
        elif tag.lower() == "meta":
            self.metas.append(attr_map)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current_link is not None:
            text = repair_text(self._current_link.get("text", "")).strip()
            self._current_link["text"] = text
            self.links.append(self._current_link)
            self._current_link = None
        elif tag.lower() == "script" and self._current_script is not None:
            text = repair_text(self._current_script.get("text", "")).strip()
            self._current_script["text"] = text
            self.scripts.append(self._current_script)
            self._current_script = None

    def handle_data(self, data: str) -> None:
        if self._current_link is not None:
            self._current_link["text"] = f"{self._current_link.get('text', '')}{data}"
        if self._current_script is not None:
            self._current_script["text"] = f"{self._current_script.get('text', '')}{data}"


def strip_html(value: Any) -> str:
    text = repair_text(value)
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_header_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", repair_text(value).lower())


def normalize_job_value(raw: Dict[str, Any], field: str) -> str:
    aliases = FIELD_ALIASES[field]
    return coalesce(*(get_path(raw, alias) for alias in aliases))


def month_days(year: int, month: int) -> int:
    next_month = date(year + (month // 12), (month % 12) + 1, 1)
    return (next_month - timedelta(days=1)).day


def subtract_months(reference: date, months: int) -> date:
    year = reference.year
    month = reference.month - months
    while month <= 0:
        year -= 1
        month += 12
    day = min(reference.day, month_days(year, month))
    return date(year, month, day)


def parse_job_date(value: Any, reference_date: Optional[date] = None) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = strip_html(value)
    if not text:
        return None

    normalized = strip_accents(text).lower()
    normalized = re.sub(r"\s+", " ", normalized).strip(" .,:;|-")
    normalized = re.sub(r"^(?:publicado(?:s|a)?|fecha de publicacion|publicacion)\s*[:\-]?\s*", "", normalized)
    reference = reference_date or date.today()

    if normalized in {"hoy", "today"}:
        return reference
    if normalized in {"ayer", "yesterday"}:
        return reference - timedelta(days=1)

    relative_match = re.search(
        r"\bhace\s+(?:(?P<count>\d+)|(?P<word>un|una|uno|unos|unas))\s+"
        r"(?P<unit>dia|dias|semana|semanas|mes|meses|ano|anos|hora|horas|minuto|minutos)\b",
        normalized,
    )
    if relative_match:
        raw_count = relative_match.group("count")
        raw_word = relative_match.group("word")
        count = int(raw_count) if raw_count else {"un": 1, "una": 1, "uno": 1, "unos": 3, "unas": 3}.get(raw_word or "", 1)
        unit = relative_match.group("unit")
        if unit.startswith("dia"):
            return reference - timedelta(days=count)
        if unit.startswith("semana"):
            return reference - timedelta(days=count * 7)
        if unit.startswith("mes"):
            return subtract_months(reference, count)
        if unit.startswith("ano"):
            try:
                return date(reference.year - count, reference.month, reference.day)
            except ValueError:
                return date(reference.year - count, reference.month, month_days(reference.year - count, reference.month))
        if unit.startswith("hora"):
            return (datetime.combine(reference, datetime.min.time()) - timedelta(hours=count)).date()
        if unit.startswith("minuto"):
            return (datetime.combine(reference, datetime.min.time()) - timedelta(minutes=count)).date()

    iso_candidate = normalized.replace("z", "+00:00")
    try:
        return datetime.fromisoformat(iso_candidate).date()
    except ValueError:
        pass

    year_first = re.search(r"\b(?P<year>\d{4})[/-](?P<month>\d{1,2})[/-](?P<day>\d{1,2})\b", normalized)
    if year_first:
        try:
            return date(int(year_first.group("year")), int(year_first.group("month")), int(year_first.group("day")))
        except ValueError:
            return None

    day_first = re.search(r"\b(?P<day>\d{1,2})[/-](?P<month>\d{1,2})[/-](?P<year>\d{4})\b", normalized)
    if day_first:
        try:
            return date(int(day_first.group("year")), int(day_first.group("month")), int(day_first.group("day")))
        except ValueError:
            return None

    month_name = re.search(
        r"\b(?P<day>\d{1,2})(?:\s+de)?\s+(?P<month>[a-z.]+)(?:\s+de)?\s+(?P<year>\d{4})\b",
        normalized,
    )
    if month_name:
        month_key = month_name.group("month").strip(".")
        month_number = SPANISH_MONTHS.get(month_key)
        if month_number:
            try:
                return date(int(month_name.group("year")), month_number, int(month_name.group("day")))
            except ValueError:
                return None

    return None


def normalize_job_date(value: Any, reference_date: Optional[date] = None) -> Optional[str]:
    parsed = parse_job_date(value, reference_date=reference_date)
    if parsed is None:
        return None
    return parsed.isoformat()


def is_job_recent(job_date: str, minimum_date: date = MIN_JOB_DATE) -> bool:
    try:
        parsed = date.fromisoformat(job_date)
    except ValueError:
        return False
    return parsed >= minimum_date


def iter_json_nodes(value: Any) -> Iterator[Dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_json_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_json_nodes(child)


def extract_json_ld_blocks(html: str) -> List[Any]:
    collector = PortalHTMLCollector()
    collector.feed(html)
    payloads: List[Any] = []
    for script in collector.scripts:
        script_type = normalize_text(script.get("attrs", {}).get("type"))
        if script_type and "json" not in script_type:
            continue
        text = repair_text(script.get("text", "")).strip()
        if not text:
            continue
        cleaned = text.strip().strip(";")
        cleaned = cleaned.replace("\u2028", " ").replace("\u2029", " ")
        for candidate in (cleaned, re.sub(r"^\s*<!--|-->\s*$", "", cleaned).strip()):
            try:
                payloads.append(json.loads(candidate))
                break
            except Exception:
                continue
    return payloads


def extract_jsonld_job_postings(html: str) -> List[Dict[str, Any]]:
    postings: List[Dict[str, Any]] = []
    for payload in extract_json_ld_blocks(html):
        for node in iter_json_nodes(payload):
            node_type = node.get("@type")
            if isinstance(node_type, list):
                node_types = {normalize_text(item) for item in node_type}
            else:
                node_types = {normalize_text(node_type)}
            if "jobposting" in node_types:
                postings.append(node)
    return postings


def extract_itemlist_links(html: str, base_url: str) -> List[str]:
    links: List[str] = []
    for payload in extract_json_ld_blocks(html):
        for node in iter_json_nodes(payload):
            node_type = node.get("@type")
            if isinstance(node_type, list):
                node_types = {normalize_text(item) for item in node_type}
            else:
                node_types = {normalize_text(node_type)}
            if "itemlist" not in node_types:
                continue
            items = node.get("itemListElement") or node.get("itemlistelement") or []
            for item in items if isinstance(items, list) else [items]:
                if isinstance(item, dict):
                    href = coalesce(item.get("url"), item.get("@id"))
                    nested = item.get("item")
                    if isinstance(nested, dict):
                        href = coalesce(href, nested.get("url"), nested.get("@id"))
                    if href:
                        links.append(urljoin(base_url, href))
    return unique(links)


def infer_portal_kind(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    if "computrabajo" in netloc:
        return "computrabajo"
    if "elempleo" in netloc:
        return "elempleo"
    if "magneto365" in netloc or "magneto" in netloc:
        return "magneto"
    if "bumeran" in netloc:
        return "bumeran"
    if "trabajando" in netloc or "trabajos" in netloc:
        return "trabajando"
    if "indeed" in netloc:
        return "indeed"
    if "jooble" in netloc:
        return "jooble"
    if "linkedin" in netloc:
        return "linkedin"
    return "generic"


def allowed_portal_link(kind: str, url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    netloc = parsed.netloc.lower()
    if not path or any(block in path for block in ("/login", "/signup", "/register", "/help", "/privacy", "/terms", "/about")):
        return False
    if kind == "computrabajo":
        return "computrabajo" in netloc and any(token in path for token in ("trabajo", "empleo", "ofertas"))
    if kind == "elempleo":
        return "elempleo" in netloc and any(token in path for token in ("ofertas-empleo", "trabajo", "empleo"))
    if kind == "magneto":
        return "magneto" in netloc and ("empleo" in path or "empleos" in path)
    if kind == "bumeran":
        return "bumeran" in netloc and any(token in path for token in ("empleos", "empleo", "trabajo", "jobs", "ofertas"))
    if kind == "trabajando":
        return "trabajando" in netloc and any(token in path for token in ("empleos", "empleo", "trabajo", "vacantes", "ofertas"))
    if kind == "indeed":
        return "indeed" in netloc and any(token in path for token in ("jobs", "empleos", "trabajo"))
    if kind == "jooble":
        return "jooble" in netloc and any(token in path for token in ("trabajo", "jdp"))
    if kind == "linkedin":
        return "linkedin" in netloc and ("jobs/view" in path or "/company/" in path and "/jobs" in path)
    return any(token in path for token in ("job", "empleo", "trabajo", "vacante", "oferta"))


def build_aggressive_portal_seeds(source_url: str, kind: str, aggressive: bool = True) -> List[str]:
    parsed = urlparse(source_url)
    base_url = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
    seeds = [source_url, base_url]
    if not aggressive:
        return unique(seeds)

    cities = ["bogota", "medellin", "cali", "barranquilla", "cartagena", "bucaramanga", "pereira", "remoto"]
    if kind == "elempleo":
        seeds.extend(
            [f"{base_url}/co/ofertas-empleo/{city}" for city in cities]
            + [f"{base_url}/co/ofertas-empleo"]
        )
    elif kind == "computrabajo":
        seeds.extend(
            [f"{base_url}/trabajo-de-{city}" for city in cities if city != "remoto"]
            + [f"{base_url}/trabajo-remoto", f"{base_url}/trabajo-de-colombia"]
        )
    elif kind == "bumeran":
        seeds.extend(
            [
                f"{base_url}/empleos",
                f"{base_url}/empleos/colombia",
                f"{base_url}/empleos/bogota",
                f"{base_url}/empleos/medellin",
                f"{base_url}/empleos/cali",
                f"{base_url}/empleos?query=empleos",
                f"{base_url}/empleos?search=empleos",
            ]
        )
    elif kind == "trabajando":
        seeds.extend(
            [
                f"{base_url}/empleos",
                f"{base_url}/empleos/bogota",
                f"{base_url}/empleos/medellin",
                f"{base_url}/empleos/cali",
                f"{base_url}/empleos/colombia",
                f"{base_url}/trabajo",
                f"{base_url}/trabajos",
            ]
        )
    elif kind == "magneto":
        query_targets = [
            ("query", city) for city in cities
        ] + [
            ("location", city) for city in cities
        ] + [
            ("q", "empleos"),
        ]
        seeds.append(f"{base_url}/co/empleos")
        for key, value in query_targets:
            seeds.append(f"{base_url}/co/empleos?{urlencode({key: value})}")
    elif kind == "indeed":
        seeds.extend(
            [
                f"{base_url}/jobs?l=Colombia&q=empleos",
                f"{base_url}/jobs?l=Bogota&q=empleos",
            ]
        )
    elif kind == "jooble":
        seeds.extend(
            [
                f"{base_url}/trabajo/Bogot%C3%A1",
                f"{base_url}/trabajo/Colombia",
            ]
        )

    return unique([seed for seed in seeds if seed])


def build_pagination_variants(page_url: str, max_pages: int, kind: str) -> List[str]:
    if max_pages <= 1:
        return []
    parsed = urlparse(page_url)
    path = parsed.path.rstrip("/")
    if not path:
        return []
    lower_path = path.lower()
    if not any(token in lower_path for token in ("job", "jobs", "empleo", "empleos", "trabajo", "vacante", "oferta")):
        return []

    variants: List[str] = []
    existing_query = parse_qs(parsed.query)
    for page_num in range(2, max_pages + 1):
        for key in ("page", "pagina", "p"):
            query = dict(existing_query)
            query[key] = [str(page_num)]
            variants.append(urlunparse(parsed._replace(query=urlencode(query, doseq=True))))
        if kind in {"elempleo", "computrabajo", "magneto", "generic"}:
            variants.append(urlunparse(parsed._replace(path=f"{path}/page/{page_num}")))
            variants.append(urlunparse(parsed._replace(path=f"{path}/pagina/{page_num}")))
    return unique(variants)


def default_render_mode_for_kind(kind: str) -> str:
    if kind in {"bumeran", "trabajando", "indeed", "jooble", "linkedin"}:
        return "browser"
    return "auto"


def extract_anchor_links(html: str, base_url: str, kind: str) -> List[str]:
    collector = PortalHTMLCollector()
    collector.feed(html)
    links: List[str] = []
    for item in collector.links:
        href = item.get("href") or ""
        text = normalize_text(item.get("text"))
        if not href:
            continue
        absolute = urljoin(base_url, href)
        if allowed_portal_link(kind, absolute) or any(token in text for token in ("trabajo", "empleo", "vacante", "job", "oferta")):
            links.append(absolute)
    return unique(links)


def extract_next_links(html: str, base_url: str) -> List[str]:
    collector = PortalHTMLCollector()
    collector.feed(html)
    next_links: List[str] = []
    for meta in collector.metas:
        if normalize_text(meta.get("rel")) == "next" and meta.get("href"):
            next_links.append(urljoin(base_url, meta["href"]))
    for link in collector.links:
        attrs = link.get("attrs") or {}
        rel = normalize_text(attrs.get("rel"))
        text = normalize_text(link.get("text"))
        href = link.get("href") or ""
        if not href:
            continue
        if "next" in rel or text in {"siguiente", "next", "more", "ver mas", "ver mas empleos", "load more"}:
            next_links.append(urljoin(base_url, href))
    return unique(next_links)


def html_fetch(url: str, session: Any, headers: Dict[str, str], render_mode: str = "requests", timeout: int = 30) -> str:
    try:
        response = session.get(url, headers=headers, timeout=timeout)
        html = response.text
        status = response.status_code
    except Exception:
        if render_mode in {"auto", "browser"}:
            try:
                return browser_render_html(url, timeout=timeout)
            except Exception:
                raise
        raise

    if status >= 400:
        if render_mode in {"auto", "browser"} and status in {403, 408, 429, 500, 502, 503, 504}:
            try:
                return browser_render_html(url, timeout=timeout)
            except Exception:
                response.raise_for_status()
        response.raise_for_status()

    if render_mode == "requests":
        return html
    if render_mode == "auto" and len(extract_jsonld_job_postings(html)) >= 1:
        return html
    if render_mode in {"auto", "browser"}:
        try:
            return browser_render_html(url, timeout=timeout)
        except Exception:
            return html
    return html


def browser_render_html(url: str, timeout: int = 30) -> str:
    last_cdp_error: Optional[Exception] = None
    try:
        return render_html_via_cdp(url, timeout=timeout)
    except Exception as cdp_error:
        last_cdp_error = cdp_error

    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception:
        sync_playwright = None

    if sync_playwright is not None:
        with sync_playwright() as playwright:
            browser_candidates = [
                os.getenv("CHROME_BIN"),
                os.getenv("EDGE_BIN"),
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            ]
            browser = None
            for executable_path in browser_candidates:
                if not executable_path or not Path(executable_path).exists():
                    continue
                try:
                    browser = playwright.chromium.launch(
                        headless=True,
                        executable_path=executable_path,
                        args=["--disable-gpu", "--no-sandbox"],
                    )
                    break
                except Exception:
                    browser = None
            if browser is None:
                browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                try:
                    page.wait_for_timeout(1000)
                except Exception:
                    pass
                return page.content()
            finally:
                browser.close()

    try:
        from selenium import webdriver  # type: ignore
        from selenium.webdriver.chrome.options import Options  # type: ignore
        from selenium.webdriver.edge.options import Options as EdgeOptions  # type: ignore
    except Exception as exc:
        raise RuntimeError("Browser rendering requested but Playwright/Selenium is not installed.") from exc

    last_error: Optional[Exception] = None

    for driver_factory, options_factory in (
        (getattr(webdriver, "Chrome", None), Options),
        (getattr(webdriver, "Edge", None), EdgeOptions),
    ):
        if driver_factory is None:
            continue
        options = options_factory()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        try:
            driver = driver_factory(options=options)
        except Exception as exc:
            last_error = exc
            continue
        try:
            driver.set_page_load_timeout(timeout)
            driver.get(url)
            return driver.page_source
        except Exception as exc:
            last_error = exc
        finally:
            try:
                driver.quit()
            except Exception:
                pass

    if last_error is not None:
        raise RuntimeError(f"Browser rendering failed: {last_error}") from last_error
    if last_cdp_error is not None:
        raise RuntimeError(f"Browser rendering failed: {last_cdp_error}") from last_cdp_error
    raise RuntimeError("Browser rendering failed: no supported Selenium driver was available.")


def normalize_job_payload(payload: Dict[str, Any], source_name: str, page_url: str, kind: str) -> Optional[Dict[str, Any]]:
    title = coalesce(payload.get("title"), payload.get("headline"), payload.get("name"))
    if not title:
        return None

    company = ""
    hiring_org = payload.get("hiringOrganization") or payload.get("hiringorganisation") or payload.get("employer")
    if isinstance(hiring_org, dict):
        company = coalesce(hiring_org.get("name"), hiring_org.get("legalName"))
    else:
        company = coalesce(payload.get("companyName"), payload.get("company"))

    location = ""
    job_location = payload.get("jobLocation") or payload.get("joblocation")
    if isinstance(job_location, list):
        for item in job_location:
            if isinstance(item, dict):
                addr = item.get("address") or item.get("jobLocationAddress")
                if isinstance(addr, dict):
                    location = coalesce(
                        addr.get("addressLocality"),
                        addr.get("addressRegion"),
                        addr.get("addressCountry"),
                    )
                    if location:
                        break
    elif isinstance(job_location, dict):
        addr = job_location.get("address") or job_location.get("jobLocationAddress")
        if isinstance(addr, dict):
            location = coalesce(addr.get("addressLocality"), addr.get("addressRegion"), addr.get("addressCountry"))

    if not location:
        location = coalesce(payload.get("location"), payload.get("jobLocationType"))

    description = coalesce(payload.get("description"), payload.get("summary"), payload.get("snippet"))
    description = strip_html(description)
    date_value = coalesce(payload.get("datePosted"), payload.get("datePublished"))
    url_value = coalesce(payload.get("url"), payload.get("@id"), page_url)

    raw_id = coalesce(
        payload.get("identifier", {}).get("value") if isinstance(payload.get("identifier"), dict) else "",
        payload.get("jobId"),
        url_value,
        title,
    )
    job_id = hashlib.sha1(f"{normalize_text(raw_id)}|{normalize_text(source_name)}".encode("utf-8")).hexdigest()[:20]

    if not description:
        description = title

    return {
        "job_id": job_id,
        "job_title": repair_text(title).strip(),
        "company": repair_text(company).strip() or "Unknown",
        "description": repair_text(description).strip(),
        "location": repair_text(location).strip(),
        "date": repair_text(date_value).strip(),
        "source": repair_text(source_name).strip() or kind,
        "url": repair_text(url_value).strip(),
    }


def scrape_portal_jobs(spec: Dict[str, Any], base_dir: Path) -> Iterator[Dict[str, Any]]:
    source_url = str(spec.get("url") or spec.get("path") or "").strip()
    if not source_url:
        raise ValueError("portal source requires a URL.")

    source_name = str(spec.get("name") or infer_portal_kind(source_url)).strip() or infer_portal_kind(source_url)
    kind = str(spec.get("kind") or infer_portal_kind(source_url)).strip() or infer_portal_kind(source_url)
    render_mode = str(spec.get("render_mode") or spec.get("browser") or default_render_mode_for_kind(kind)).strip().lower()
    if render_mode == "auto":
        render_mode = default_render_mode_for_kind(kind)
    timeout = int(spec.get("timeout") or 30)
    max_pages = int(spec.get("max_pages") or 12)
    aggressive = bool(spec.get("aggressive", True))
    headers = {
        "User-Agent": spec.get(
            "user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        ),
        "Accept-Language": spec.get("accept_language", "es-CO,es;q=0.9,en;q=0.8"),
    }

    session = requests.Session() if requests is not None else None
    if session is None:
        raise RuntimeError("The `requests` package is required for portal scraping.")

    page_queue: List[str] = build_aggressive_portal_seeds(source_url, kind, aggressive=aggressive)
    seen_pages: set[str] = set()
    seen_jobs: set[str] = set()
    page_count = 0

    while page_queue:
        page_url = page_queue.pop(0)
        if page_url in seen_pages:
            continue
        if max_pages and page_count >= max_pages:
            break
        page_count += 1
        seen_pages.add(page_url)

        html = html_fetch(page_url, session, headers, render_mode=render_mode, timeout=timeout)
        postings = extract_jsonld_job_postings(html)

        if postings:
            for posting in postings:
                job = normalize_job_payload(posting, source_name, page_url, kind)
                if job is None:
                    continue
                if job["job_id"] in seen_jobs:
                    continue
                seen_jobs.add(job["job_id"])
                yield job
        else:
            item_links = extract_itemlist_links(html, page_url)
            anchor_links = extract_anchor_links(html, page_url, kind)
            for candidate in unique(item_links + anchor_links):
                if candidate not in seen_pages:
                    page_queue.append(candidate)

        next_links = extract_next_links(html, page_url)
        if not next_links:
            next_links = build_pagination_variants(page_url, max_pages=max_pages, kind=kind)
        for next_url in next_links:
            if next_url not in seen_pages:
                page_queue.append(next_url)



def stable_job_id(source_name: str, raw: Dict[str, Any], job_title: str, company: str, location: str, date: str, description: str) -> str:
    external_id = normalize_job_value(raw, "job_id")
    if external_id:
        return f"{normalize_text(source_name) or 'source'}:{external_id}"
    payload = "|".join(
        [
            normalize_text(source_name),
            normalize_text(job_title),
            normalize_text(company),
            normalize_text(location),
            normalize_text(date),
            normalize_text(description[:500]),
        ]
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:20]


def build_job_record(raw: Dict[str, Any], source_name: str) -> Optional[Dict[str, str]]:
    job_title = normalize_job_value(raw, "job_title") or "Untitled job"
    company = normalize_job_value(raw, "company") or "Unknown"
    description = normalize_job_value(raw, "description")
    location = normalize_job_value(raw, "location")
    date = normalize_job_date(normalize_job_value(raw, "date"))
    source = normalize_job_value(raw, "source") or source_name

    if not normalize_job_value(raw, "job_title") and not description:
        return None
    if not date:
        return None
    if not is_job_recent(date):
        return None

    job_id = stable_job_id(source_name, raw, job_title, company, location, date, description)
    return {
        "job_id": job_id,
        "job_title": repair_text(job_title).strip() or "Untitled job",
        "company": repair_text(company).strip() or "Unknown",
        "description": repair_text(description).strip(),
        "location": repair_text(location).strip(),
        "date": repair_text(date).strip(),
        "source": repair_text(source).strip() or source_name,
    }


def merge_job_records(existing: Dict[str, str], incoming: Dict[str, str]) -> Dict[str, str]:
    merged = dict(existing)
    for field in JOB_FIELDS:
        if field == "job_id":
            continue
        current = merged.get(field, "")
        candidate = incoming.get(field, "")
        if not current and candidate:
            merged[field] = candidate
        elif field == "description" and len(candidate) > len(current):
            merged[field] = candidate
    return merged


def load_local_jobs(path: Path) -> Iterator[Dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        text = read_text_with_fallback(path)
        sample = text[:4096]
        delimiter = ","
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
            delimiter = dialect.delimiter
        except csv.Error:
            pass
        reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
        for row in reader:
            yield dict(row)
        return
    if suffix == ".jsonl":
        for line in read_text_with_fallback(path).splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            yield json.loads(stripped)
        return
    if suffix == ".json":
        payload = json.loads(read_text_with_fallback(path))
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    yield item
            return
        if isinstance(payload, dict):
            items = payload.get("jobs") or payload.get("items") or payload.get("results") or payload
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        yield item
                return
        raise ValueError(f"Unsupported JSON structure in {path}")
    raise ValueError(f"Unsupported local source format: {path.suffix}")


def load_real_jobs(file_path: str) -> List[Dict[str, str]]:
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    if path.suffix.lower() != ".csv":
        raise ValueError("Real mode currently expects a CSV file with job_title plus company/location and either description or skill text columns.")

    text = read_text_with_fallback(path)
    sample = text[:4096]
    delimiter = ","
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        pass

    reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("CSV file does not contain headers.")

    normalized_headers = {normalize_header_name(field): field for field in reader.fieldnames}
    description_header = next(
        (
            normalized_headers[normalize_header_name(alias)]
            for alias in [
                *FIELD_ALIASES["description"],
                "skills",
                "signals",
                "matched_skills",
                "missing_skills",
                "requirements",
                "responsibilities",
            ]
            if normalize_header_name(alias) in normalized_headers
        ),
        None,
    )
    required_fields = {"jobtitle", "company", "location"}
    missing = [field for field in required_fields if field not in normalized_headers]
    if description_header is None:
        missing.append("description_or_skills")
    if missing:
        raise ValueError(
            "CSV file is missing required columns: "
            + ", ".join(sorted(missing))
            + ". Accepted text columns include description, skills, signals, matched_skills, missing_skills, requirements."
        )

    jobs: List[Dict[str, str]] = []
    date_header = next(
        (normalized_headers[normalize_header_name(alias)] for alias in FIELD_ALIASES["date"] if normalize_header_name(alias) in normalized_headers),
        None,
    )
    source_header = next(
        (normalized_headers[normalize_header_name(alias)] for alias in FIELD_ALIASES["source"] if normalize_header_name(alias) in normalized_headers),
        None,
    )
    job_id_header = next(
        (normalized_headers[normalize_header_name(alias)] for alias in FIELD_ALIASES["job_id"] if normalize_header_name(alias) in normalized_headers),
        None,
    )
    for index, row in enumerate(reader, start=1):
        job_title = repair_text(row.get(normalized_headers["jobtitle"], "")).strip()
        company = repair_text(row.get(normalized_headers["company"], "")).strip()
        description_parts = [repair_text(row.get(description_header, "")).strip() if description_header else ""]
        for optional_text_field in ("skills", "signals", "matched_skills", "missing_skills"):
            header = normalized_headers.get(normalize_header_name(optional_text_field))
            value = repair_text(row.get(header, "")).strip() if header else ""
            if value and value not in description_parts:
                description_parts.append(value)
        description = ". ".join(part for part in description_parts if part)
        location = repair_text(row.get(normalized_headers["location"], "")).strip()
        if not job_title or not description:
            continue
        date_value = repair_text(row.get(date_header, "")).strip() if date_header else ""
        source_value = repair_text(row.get(source_header, "")).strip() if source_header else ""
        external_id = repair_text(row.get(job_id_header, "")).strip() if job_id_header else ""
        job_id = external_id or hashlib.sha1(
            "|".join([normalize_text(job_title), normalize_text(company), normalize_text(location), normalize_text(description[:500]), str(index)]).encode("utf-8")
        ).hexdigest()[:20]
        jobs.append(
            {
                "job_id": job_id,
                "job_title": job_title,
                "company": company or "Unknown",
                "description": description,
                "location": location,
                "date": date_value,
                "source": source_value or path.stem,
            }
        )
    if not jobs:
        raise ValueError("CSV file did not yield any valid job rows.")
    return jobs


def fetch_json(url: str, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Dict[str, Any]:
    if requests is None:
        raise RuntimeError("The `requests` package is required for HTTP sources.")
    response = requests.get(url, headers=headers, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_json_api_jobs(spec: Dict[str, Any], base_dir: Path) -> Iterator[Dict[str, Any]]:
    if requests is None:
        raise RuntimeError("The `requests` package is required for HTTP sources.")
    url = str(spec.get("url") or "").strip()
    if not url:
        raise ValueError("json_api source requires `url`.")

    headers = dict(spec.get("headers") or {})
    timeout = int(spec.get("timeout") or 30)
    items_path = spec.get("items_path")
    pagination = dict(spec.get("pagination") or {})
    params = dict(spec.get("params") or {})
    mode = str(pagination.get("mode") or "page").lower()
    stop_when_empty = bool(pagination.get("stop_when_empty", True))
    seen_pages: set[str] = set()

    if mode == "cursor":
        cursor_param = str(pagination.get("cursor_param") or "cursor")
        next_cursor_path = pagination.get("next_cursor_path") or pagination.get("next_page_field")
        cursor = pagination.get("start_cursor")
        while True:
            request_params = dict(params)
            if cursor:
                request_params[cursor_param] = cursor
            data = fetch_json(url, headers=headers, params=request_params, timeout=timeout)
            items = get_path(data, items_path)
            if items is None and isinstance(data, list):
                items = data
            page_items = [item for item in items or [] if isinstance(item, dict)]
            fingerprint = hashlib.sha1(safe_json_dumps(page_items).encode("utf-8")).hexdigest()
            if fingerprint in seen_pages:
                break
            seen_pages.add(fingerprint)
            for item in page_items:
                yield item
            if stop_when_empty and not page_items:
                break
            next_cursor = get_path(data, next_cursor_path) if next_cursor_path else None
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
        return

    if mode == "next_url":
        next_url_path = pagination.get("next_url_path") or pagination.get("next_page_field") or "next"
        next_url = url
        while next_url:
            data = fetch_json(next_url, headers=headers, params=params, timeout=timeout)
            items = get_path(data, items_path)
            if items is None and isinstance(data, list):
                items = data
            page_items = [item for item in items or [] if isinstance(item, dict)]
            fingerprint = hashlib.sha1(safe_json_dumps(page_items).encode("utf-8")).hexdigest()
            if fingerprint in seen_pages:
                break
            seen_pages.add(fingerprint)
            for item in page_items:
                yield item
            if stop_when_empty and not page_items:
                break
            next_url = get_path(data, next_url_path)
            if next_url:
                next_url = str(next_url)
        return

    page_param = str(pagination.get("page_param") or "page")
    page_size_param = str(pagination.get("page_size_param") or "per_page")
    page_size = pagination.get("page_size")
    start_page = int(pagination.get("start_page") or 1)
    max_pages = pagination.get("max_pages")
    current_page = start_page
    while True:
        request_params = dict(params)
        request_params[page_param] = current_page
        if page_size:
            request_params[page_size_param] = page_size
        data = fetch_json(url, headers=headers, params=request_params, timeout=timeout)
        items = get_path(data, items_path)
        if items is None and isinstance(data, list):
            items = data
        page_items = [item for item in items or [] if isinstance(item, dict)]
        fingerprint = hashlib.sha1(safe_json_dumps(page_items).encode("utf-8")).hexdigest()
        if fingerprint in seen_pages:
            break
        seen_pages.add(fingerprint)
        for item in page_items:
            yield item
        if stop_when_empty and not page_items:
            break
        current_page += 1
        if max_pages and current_page > int(max_pages):
            break


def load_source_items(spec: Dict[str, Any], base_dir: Path) -> Tuple[str, Iterator[Dict[str, Any]]]:
    source_type = str(spec.get("type") or "").strip().lower()
    source_name = str(spec.get("name") or "").strip()
    if not source_name:
        if source_type in {"csv", "json", "jsonl", "real"}:
            raw_path = spec.get("path") or spec.get("url") or "source"
            source_name = Path(str(raw_path)).stem
        elif source_type == "portal":
            source_name = infer_portal_kind(str(spec.get("url") or spec.get("path") or "portal"))
        else:
            source_name = source_type or "source"

    if source_type == "real":
        raw_path = spec.get("path") or spec.get("input")
        if not raw_path:
            raise ValueError("real source requires `path` or `input`.")
        return source_name, iter(load_real_jobs(str(raw_path)))

    if source_type == "portal":
        return source_name, scrape_portal_jobs(spec, base_dir)

    if source_type in {"csv", "json", "jsonl"}:
        raw_location = spec.get("path") or spec.get("url")
        if not raw_location:
            raise ValueError(f"{source_type} source requires `path` or `url`.")
        if str(raw_location).startswith(("http://", "https://")):
            if requests is None:
                raise RuntimeError("The `requests` package is required for HTTP sources.")
            response = requests.get(str(raw_location), timeout=int(spec.get("timeout") or 30))
            response.raise_for_status()
            tmp_path = base_dir / ".job_extraction_cache"
            tmp_path.mkdir(parents=True, exist_ok=True)
            cache_file = tmp_path / f"{normalize_text(source_name) or 'source'}.{source_type}"
            cache_file.write_bytes(response.content)
            iterator = load_local_jobs(cache_file)
            return source_name, iterator
        resolved = resolve_path(str(raw_location), base_dir)
        return source_name, load_local_jobs(resolved)

    if source_type == "json_api":
        return source_name, fetch_json_api_jobs(spec, base_dir)

    raise ValueError(f"Unsupported source type: {source_type}")


def catalog_match(phrase: str) -> Optional[str]:
    normalized = normalize_text(phrase)
    if not normalized:
        return None
    if normalized in SKILL_ALIAS_TO_CANONICAL:
        return SKILL_ALIAS_TO_CANONICAL[normalized]
    singular = normalized[:-1] if normalized.endswith("s") else ""
    if singular and singular in SKILL_ALIAS_TO_CANONICAL:
        return SKILL_ALIAS_TO_CANONICAL[singular]
    return None


def split_skill_phrase(phrase: str) -> List[str]:
    parts = re.split(r"\s*(?:,|;|/|\band\b|\bor\b|&|\+)\s*", phrase, flags=re.IGNORECASE)
    cleaned: List[str] = []
    for part in parts:
        token = re.sub(r"^\s*(?:skills?|knowledge|experience|proficiency|familiarity|background|expertise|ability|understanding)\s+", "", part, flags=re.IGNORECASE)
        token = re.sub(r"^(?:in|with|of|using|for)\s+", "", token, flags=re.IGNORECASE)
        token = re.sub(r"\s+(?:skills?|experience|knowledge|ability|background|expertise)$", "", token, flags=re.IGNORECASE)
        token = re.sub(r"[()\[\]{}<>]", " ", token)
        token = re.sub(r"\s+", " ", token).strip(" .:-\t")
        if token:
            cleaned.append(token)
    return cleaned


def infer_candidate_confidence(phrase: str, source_kind: str, hit_count: int, appears_in_title: bool) -> float:
    base = {"catalog": 0.93, "phrase": 0.8, "chunk": 0.75, "title": 0.84, "acronym": 0.78}.get(source_kind, 0.74)
    base += min(0.06, max(hit_count - 1, 0) * 0.02)
    if appears_in_title:
        base += 0.04
    if re.search(r"[A-Z]{2,}", phrase) or re.search(r"[/.-]", phrase):
        base += 0.02
    if len(phrase.split()) >= 3:
        base += 0.01
    return round(min(base, 0.99), 2)


def mine_skill_phrases(text: str) -> List[Tuple[str, str]]:
    patterns = [
        r"(?:experience|expertise|knowledge|proficiency|familiarity|background|hands[- ]?on(?: experience)?|strong understanding|skills?)\s+(?:in|with|of|using|for)\s+([^.\n;:]+)",
        r"(?:proficient|experienced|skilled)\s+in\s+([^.\n;:]+)",
        r"(?:must have|required|required skills?|nice to have|we are looking for|you will need|what you'll need)\s*[:\-]?\s*([^.\n;:]+)",
        r"(?:tools?|technologies?|stack|platforms?)\s*[:\-]?\s*([^.\n;:]+)",
    ]
    hits: List[Tuple[str, str]] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            phrase = match.group(1).strip()
            for candidate in split_skill_phrase(phrase):
                if candidate:
                    hits.append((candidate, "phrase"))

    acronym_candidates = re.findall(r"\b(?:[A-Z]{2,}(?:/[A-Z]{2,})+|[A-Z]{2,}|[A-Z][a-z]+(?:\s+[A-Z]{2,})+|[A-Z]{2,}(?:\.[A-Z0-9]+)+)\b", text)
    for candidate in acronym_candidates:
        normalized = normalize_text(candidate)
        if len(normalized) >= 2:
            hits.append((candidate, "acronym"))

    return hits


def extract_job_skills(job: Dict[str, str]) -> List[Dict[str, Any]]:
    text = " ".join([job.get("job_title", ""), job.get("description", "")]).strip()
    normalized_text = normalize_text(text)
    results: Dict[str, Dict[str, Any]] = {}

    def upsert(skill_name: str, source_kind: str, confidence: float, source_phrase: Optional[str] = None) -> None:
        canonical = catalog_match(skill_name) or repair_text(skill_name).strip()
        if not canonical:
            return
        key = normalize_text(canonical)
        if not key:
            return
        current = results.get(key)
        if current is None:
            results[key] = {
                "job_id": job["job_id"],
                "job_title": job["job_title"],
                "skill_name": canonical,
                "confidence": round(float(confidence), 2),
                "_source_kind": source_kind,
                "_source_phrase": source_phrase or canonical,
            }
            return
        current["confidence"] = round(min(max(current["confidence"], float(confidence)), 0.99), 2)
        if len(canonical) > len(current["skill_name"]):
            current["skill_name"] = canonical

    for skill in extract_skills_from_text(text):
        name = repair_text(skill.get("name", "")).strip()
        if not name:
            continue
        confidence = float(skill.get("confidence_score") or 0.78)
        source_phrase = skill.get("source_phrase") or name
        source_kind = "catalog" if normalize_text(name) in SKILL_ALIAS_TO_CANONICAL else "chunk"
        upsert(name, source_kind, confidence, source_phrase)

    for phrase, source_kind in mine_skill_phrases(text):
        canonical = catalog_match(phrase) or phrase
        hit_count = len(re.findall(rf"\b{re.escape(normalize_text(phrase))}\b", normalized_text))
        upsert(
            canonical,
            source_kind,
            infer_candidate_confidence(canonical, source_kind, hit_count, appears_in_title=normalize_text(canonical) in normalize_text(job["job_title"])),
            phrase,
        )

    for phrase in split_skill_phrase(job.get("job_title", "")):
        canonical = catalog_match(phrase) or phrase
        upsert(canonical, "title", infer_candidate_confidence(canonical, "title", 1, True), phrase)

    ordered = sorted(results.values(), key=lambda item: (-float(item["confidence"]), item["skill_name"].lower()))
    for item in ordered:
        item.pop("_source_kind", None)
        item.pop("_source_phrase", None)
    return ordered


def write_csv(path: Path, rows: Sequence[Dict[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def split_for_training(job_id: str, validation_ratio: float = 0.1, test_ratio: float = 0.1) -> str:
    digest = hashlib.sha1(job_id.encode("utf-8", errors="ignore")).hexdigest()
    bucket = int(digest[:8], 16) % 1000
    if bucket < int(test_ratio * 1000):
        return "test"
    if bucket < int((test_ratio + validation_ratio) * 1000):
        return "validation"
    return "train"


def is_training_skill_label(skill_name: str, job_title: str = "") -> bool:
    cleaned = repair_text(skill_name).strip()
    normalized = normalize_text(cleaned)
    title_key = normalize_text(job_title)
    if not normalized:
        return False
    if catalog_match(cleaned):
        return True
    if normalized == title_key:
        return False
    if title_key and normalized in title_key:
        return False
    if len(cleaned) > 48:
        return False
    words = normalized.split()
    if len(words) > 4:
        return False
    if len(words) == 1 and cleaned.isupper():
        return False
    blocked_fragments = {
        "trabaja con nosotros",
        "ver todo",
        "http",
        "www",
        "postulate",
        "postulate ahora",
        "bogota zona norte",
        "norte trabaja",
        "agentes",
    }
    if any(fragment in normalized for fragment in blocked_fragments):
        return False
    return True


def skills_for_job(job_id: str, job_skills: Sequence[Dict[str, Any]], job_title: str = "") -> List[Dict[str, Any]]:
    by_key: Dict[str, Dict[str, Any]] = {}
    for item in job_skills:
        if str(item.get("job_id", "")) != str(job_id):
            continue
        raw_name = repair_text(item.get("skill_name", "")).strip()
        if not raw_name or not is_training_skill_label(raw_name, job_title):
            continue
        canonical = catalog_match(raw_name) or raw_name
        key = normalize_text(canonical)
        if not key:
            continue
        row = {
            "skill_name": canonical,
            "confidence": round(float(item.get("confidence") or 0), 2),
        }
        current = by_key.get(key)
        if current is None or float(row["confidence"]) > float(current["confidence"]):
            by_key[key] = row
    rows = list(by_key.values())
    rows.sort(key=lambda item: (-float(item["confidence"]), normalize_text(item["skill_name"])))
    return rows


def build_training_payload(job: Dict[str, str], job_skills: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    title = repair_text(job.get("job_title", "")).strip()
    company = repair_text(job.get("company", "")).strip()
    location = repair_text(job.get("location", "")).strip()
    description = repair_text(job.get("description", "")).strip()
    input_text = "\n".join(
        [
            f"Titulo: {title}",
            f"Empresa: {company}",
            f"Ubicacion: {location}",
            "Descripcion:",
            description,
        ]
    ).strip()
    skills = skills_for_job(job["job_id"], job_skills, title)
    quality_flags: List[str] = []
    if not description:
        quality_flags.append("missing_description")
    if not skills:
        quality_flags.append("no_positive_skill_labels")
    return {
        "input_text": input_text,
        "output": {
            "skills": skills,
            "role_hint": title,
            "quality_flags": quality_flags,
        },
        "metadata": {
            "job_id": job["job_id"],
            "job_title": title,
            "company": company,
            "location": location,
            "date": repair_text(job.get("date", "")).strip(),
            "source": repair_text(job.get("source", "")).strip(),
            "split": split_for_training(job["job_id"]),
            "label_source": "weak_supervision",
            "task": "job_skill_extraction",
        },
    }


def training_payload_to_chat_jsonl(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": TRAINING_JSONL_SYSTEM_PROMPT},
            {"role": "user", "content": payload["input_text"]},
            {
                "role": "assistant",
                "content": json.dumps(payload["output"], ensure_ascii=False, separators=(",", ":")),
            },
        ],
        "metadata": payload["metadata"],
    }


def training_payload_to_record_jsonl(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "input": payload["input_text"],
        "output": payload["output"],
        "metadata": payload["metadata"],
    }


def build_training_examples(
    jobs: Sequence[Dict[str, str]],
    job_skills: Sequence[Dict[str, Any]],
    *,
    jsonl_format: str = "chat",
    include_empty_labels: bool = False,
) -> List[Dict[str, Any]]:
    examples: List[Dict[str, Any]] = []
    for job in jobs:
        payload = build_training_payload(job, job_skills)
        if not include_empty_labels and not payload["output"]["skills"]:
            continue
        if jsonl_format == "record":
            examples.append(training_payload_to_record_jsonl(payload))
        else:
            examples.append(training_payload_to_chat_jsonl(payload))
    return examples


def write_jsonl(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_sqlite(db_path: Path, jobs: Sequence[Dict[str, str]], job_skills: Sequence[Dict[str, Any]]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                job_title TEXT NOT NULL,
                company TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                date TEXT NOT NULL,
                source TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS job_skills (
                job_id TEXT NOT NULL,
                job_title TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                confidence REAL NOT NULL,
                PRIMARY KEY (job_id, skill_name)
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO jobs (job_id, job_title, company, description, location, date, source)
            VALUES (:job_id, :job_title, :company, :description, :location, :date, :source)
            ON CONFLICT(job_id) DO UPDATE SET
                job_title=excluded.job_title,
                company=excluded.company,
                description=excluded.description,
                location=excluded.location,
                date=excluded.date,
                source=excluded.source
            """,
            jobs,
        )
        conn.executemany(
            """
            INSERT INTO job_skills (job_id, job_title, skill_name, confidence)
            VALUES (:job_id, :job_title, :skill_name, :confidence)
            ON CONFLICT(job_id, skill_name) DO UPDATE SET
                job_title=excluded.job_title,
                confidence=excluded.confidence
            """,
            job_skills,
        )
        conn.commit()


def load_config(config_path: Optional[Path], base_dir: Path) -> Dict[str, Any]:
    if not config_path:
        return {}
    payload = json.loads(read_text_with_fallback(config_path))
    if not isinstance(payload, dict):
        raise ValueError("Config file must contain a JSON object.")
    payload["_config_dir"] = str(config_path.parent)
    return payload


def parse_shorthand_source(value: str) -> Dict[str, Any]:
    raw = value.strip()
    if ":" not in raw:
        raise ValueError(
            "Shorthand sources must be `real:path`, `portal:url`, `csv:path`, `json:path`, `jsonl:path`, or `api:url`."
        )
    prefix, remainder = raw.split(":", 1)
    prefix = prefix.strip().lower()
    remainder = remainder.strip()
    if prefix in {"real", "csv", "json", "jsonl"}:
        return {"type": prefix, "path": remainder, "name": Path(remainder).stem}
    if prefix == "portal":
        return {"type": "portal", "url": remainder, "name": infer_portal_kind(remainder)}
    if prefix in {"api", "json_api"}:
        return {"type": "json_api", "url": remainder, "name": Path(remainder).stem or "api"}
    raise ValueError(f"Unsupported shorthand source: {value}")


def collect_source_specs(args: argparse.Namespace, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    for item in config.get("sources") or []:
        if isinstance(item, dict):
            specs.append(dict(item))
    if args.input:
        specs.append({"type": "real", "path": args.input, "name": Path(args.input).stem})
    for raw in args.source or []:
        if raw.strip().lower() == "real":
            continue
        specs.append(parse_shorthand_source(raw))
    if not specs:
        raise ValueError("At least one source is required.")
    return specs


def collect_jobs(
    specs: Sequence[Dict[str, Any]], base_dir: Path
) -> Tuple[List[Dict[str, str]], List[str], Dict[str, int], Dict[str, int]]:
    jobs_by_id: Dict[str, Dict[str, str]] = {}
    errors: List[str] = []
    source_counts: Counter[str] = Counter()
    stats: Counter[str] = Counter()

    for spec in specs:
        try:
            source_name, iterator = load_source_items(spec, base_dir)
            count_before = len(jobs_by_id)
            for raw in iterator:
                stats["total_found"] += 1
                if not isinstance(raw, dict):
                    stats["discarded"] += 1
                    continue
                job = build_job_record(raw, source_name)
                if job is None:
                    stats["discarded"] += 1
                    continue
                source_counts[job["source"]] += 1
                existing = jobs_by_id.get(job["job_id"])
                if existing is None:
                    jobs_by_id[job["job_id"]] = job
                    stats["filtered"] += 1
                else:
                    jobs_by_id[job["job_id"]] = merge_job_records(existing, job)
                    stats["deduplicated"] += 1
            count_after = len(jobs_by_id)
            print(f"[source] {source_name}: +{count_after - count_before} jobs")
        except Exception as exc:
            message = f"{spec.get('name') or spec.get('type') or 'source'}: {exc}"
            errors.append(message)
            print(f"[warning] {message}", file=sys.stderr)

    jobs = sorted(jobs_by_id.values(), key=lambda item: (normalize_text(item["job_title"]), normalize_text(item["company"]), item["job_id"]))
    stats["discarded"] = max(
        int(stats.get("discarded", 0)),
        int(stats.get("total_found", 0)) - int(stats.get("filtered", 0)) - int(stats.get("deduplicated", 0)),
    )
    return jobs, errors, dict(source_counts), dict(stats)


def build_skill_rows(jobs: Sequence[Dict[str, str]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for job in jobs:
        for skill in extract_job_skills(job):
            rows.append(
                {
                    "job_id": job["job_id"],
                    "job_title": job["job_title"],
                    "skill_name": skill["skill_name"],
                    "confidence": float(skill["confidence"]),
                }
            )
    rows.sort(key=lambda item: (normalize_text(item["job_title"]), normalize_text(item["skill_name"]), item["job_id"]))
    return rows


def ensure_output_dir(output_dir: Optional[str], base_dir: Path) -> Path:
    if not output_dir:
        return (base_dir / "job_extraction_output").resolve()
    return resolve_path(output_dir, base_dir)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract job offers from multiple sources and persist jobs + skills to CSV, SQLite, and ML-ready JSONL."
    )
    parser.add_argument(
        "--source",
        action="append",
        help="Use `real` with `--input`, or add `portal:https://...`, `csv:path`, `json:path`, `jsonl:path`, or `api:url` sources.",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="CSV file with real job offers. Required when using `--source real`.",
    )
    parser.add_argument("--config", type=str, help="JSON config file with `sources`, `output_dir`, and/or `db_path`.")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory for jobs.csv and job_skills.csv.")
    parser.add_argument("--db-path", type=str, default=None, help="SQLite database path.")
    parser.add_argument("--no-csv", action="store_true", help="Skip CSV outputs and write only SQLite.")
    parser.add_argument("--no-sqlite", action="store_true", help="Skip SQLite output and write only CSV.")
    parser.add_argument("--no-jsonl", action="store_true", help="Skip ML-ready JSONL export.")
    parser.add_argument(
        "--jsonl-format",
        choices=("chat", "record"),
        default="chat",
        help="JSONL shape: `chat` for chat fine-tuning messages, or `record` for generic ML pipelines.",
    )
    parser.add_argument(
        "--jsonl-path",
        type=str,
        default=None,
        help="Optional output path for the JSONL training file. Defaults to output-dir/training_skill_extraction.<format>.jsonl.",
    )
    parser.add_argument(
        "--jsonl-include-empty-labels",
        action="store_true",
        help="Include jobs with no extracted positive skills as negative/empty-label examples.",
    )
    args = parser.parse_args(argv)

    config_path = resolve_path(args.config, BASE_DIR) if args.config else None
    config = load_config(config_path, BASE_DIR) if config_path else {}
    config_dir = Path(config.get("_config_dir") or BASE_DIR)
    has_any_source = bool(args.input) or bool(args.source) or bool(config.get("sources"))
    if not has_any_source:
        raise ValueError("Provide `--input` for CSV mode or `--source portal:URL` / config for portal scraping.")
    specs = collect_source_specs(args, config)

    output_dir = ensure_output_dir(args.output_dir or config.get("output_dir"), BASE_DIR if not config_path else config_dir)
    db_path_value = args.db_path or config.get("db_path") or str(output_dir / "job_extraction.sqlite3")
    db_path = resolve_path(db_path_value, BASE_DIR if not config_path else config_dir)

    jobs, errors, source_counts, stats = collect_jobs(specs, BASE_DIR if not config_path else config_dir)
    job_skills = build_skill_rows(jobs)

    if not args.no_csv:
        write_csv(output_dir / "jobs.csv", jobs, JOB_FIELDS)
        write_csv(output_dir / "job_skills.csv", job_skills, JOB_SKILL_FIELDS)

    if not args.no_sqlite:
        write_sqlite(db_path, jobs, job_skills)

    training_examples: List[Dict[str, Any]] = []
    jsonl_path: Optional[Path] = None
    if not args.no_jsonl:
        training_examples = build_training_examples(
            jobs,
            job_skills,
            jsonl_format=args.jsonl_format,
            include_empty_labels=args.jsonl_include_empty_labels,
        )
        default_jsonl_name = f"training_skill_extraction.{args.jsonl_format}.jsonl"
        jsonl_path = (
            resolve_path(args.jsonl_path, BASE_DIR if not config_path else config_dir)
            if args.jsonl_path
            else output_dir / default_jsonl_name
        )
        write_jsonl(jsonl_path, training_examples)

    print(f"[done] jobs: {len(jobs)}")
    print(f"[done] job_skills: {len(job_skills)}")
    if not args.no_jsonl:
        print(f"[done] training_examples: {len(training_examples)}")
        print(f"[done] jsonl: {jsonl_path}")
    print(
        "[done] job_volume: "
        f"total_found={int(stats.get('total_found', 0))}, "
        f"filtered={int(stats.get('filtered', 0))}, "
        f"discarded={int(stats.get('discarded', 0))}"
    )
    top_skills = Counter(item["skill_name"] for item in job_skills)
    if top_skills:
        print(
            "[done] top_skills: "
            + ", ".join(f"{skill}={count}" for skill, count in top_skills.most_common(10))
        )
    print(f"[done] sources: {len(specs)}")
    if source_counts:
        top_sources = ", ".join(f"{name}={count}" for name, count in sorted(source_counts.items(), key=lambda item: (-item[1], item[0]))[:8])
        print(f"[done] source_counts: {top_sources}")
    print(f"[done] csv_dir: {output_dir}")
    print(f"[done] sqlite: {db_path}")
    if errors:
        print(f"[done] warnings: {len(errors)} source(s) failed. See stderr for details.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
