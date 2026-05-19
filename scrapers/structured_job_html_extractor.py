from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


DESCRIPTION_HINTS = (
    "description",
    "job-description",
    "jobdescription",
    "vacancy-description",
    "vacancydescription",
    "offer-description",
    "offerdescription",
    "job-desc",
    "jobdesc",
    "details",
    "descripcion",
    "descripci",
)


def repair_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_key(value: str) -> str:
    value = strip_accents(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return collapse_spaces(value)


def clean_skill_text(value: str) -> str:
    text = collapse_spaces(strip_accents(unescape(repair_text(value))))
    text = text.strip(" .,:;|-")
    text = re.sub(
        r"^(?:(?:buscamos|requerimos|necesitamos|solicitamos|se requiere|se requieren|se busca|se buscan)\s+)?"
        r"(?:metodologia|conocimiento en|experiencia en)\s+",
        "",
        text,
        flags=re.I,
    )
    text = collapse_spaces(text)
    return text.strip(" .,:;|-")


def dedupe_skills(values: Sequence[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for value in values:
        candidate = collapse_spaces(repair_text(value)).strip(" .,:;|-")
        if not candidate:
            continue
        key = normalize_key(candidate)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result


def split_skill_phrase(value: str) -> List[str]:
    text = clean_skill_text(value)
    if not text:
        return []

    version_match = re.match(
        r"^(?P<prefix>.+?)\s+(?P<left>v?\d+(?:\.\d+)?[a-z]*)\s+(?:y|o)\s+(?P<right>v?\d+(?:\.\d+)?[a-z]*)$",
        text,
        flags=re.I,
    )
    if version_match:
        prefix = collapse_spaces(version_match.group("prefix")).strip(" .,:;|-")
        left = version_match.group("left").strip(" .,:;|-")
        right = version_match.group("right").strip(" .,:;|-")
        if prefix:
            return dedupe_skills([f"{prefix} {left}".strip(), f"{prefix} {right}".strip()])

    parts = re.split(r"\s*(?:,|\by\b|\bo\b)\s*", text, flags=re.I)
    cleaned: List[str] = []
    for part in parts:
        candidate = clean_skill_text(part)
        if not candidate:
            continue
        if candidate.lower() in {"y", "o"}:
            continue
        cleaned.append(candidate)
    return dedupe_skills(cleaned)


class StructuredJobHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.job_title = ""
        self._title_active = False
        self._title_fragments: List[str] = []
        self._strong_buffers: List[List[str]] = []
        self._strong_texts: List[str] = []
        self._li_buffers: List[List[str]] = []
        self._li_texts: List[str] = []
        self._description_stack: List[bool] = []
        self._description_fragments: List[str] = []

    @staticmethod
    def _class_id_text(attrs: Dict[str, str]) -> str:
        return f"{attrs.get('class', '')} {attrs.get('id', '')}".lower()

    def _is_description_container(self, tag: str, attrs: Dict[str, str]) -> bool:
        if tag not in {"div", "section", "article", "main", "aside", "p", "ul", "ol"}:
            return False
        class_id = self._class_id_text(attrs)
        return any(hint in class_id for hint in DESCRIPTION_HINTS)

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        attr_map = {key.lower(): (value or "") for key, value in attrs}
        class_id = self._class_id_text(attr_map)

        if tag == "h2" and "job-title" in class_id and not self.job_title:
            self._title_active = True
            self._title_fragments = []

        if tag == "strong":
            self._strong_buffers.append([])

        if tag == "li":
            self._li_buffers.append([])

        self._description_stack.append(self._is_description_container(tag, attr_map))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "h2" and self._title_active:
            self.job_title = collapse_spaces(unescape(" ".join(self._title_fragments)))
            self._title_fragments = []
            self._title_active = False
        if tag == "strong" and self._strong_buffers:
            buffer = self._strong_buffers.pop()
            text = collapse_spaces(unescape(" ".join(buffer)))
            if text:
                self._strong_texts.append(text)
        if tag == "li" and self._li_buffers:
            buffer = self._li_buffers.pop()
            text = collapse_spaces(unescape(" ".join(buffer)))
            if text:
                self._li_texts.append(text)
        if self._description_stack:
            is_description_container = self._description_stack.pop()
            if is_description_container and not self._title_active:
                pass

    def handle_data(self, data: str) -> None:
        text = repair_text(data)
        if not text.strip():
            return
        if self._title_active:
            self._title_fragments.append(text)
        if self._strong_buffers:
            self._strong_buffers[-1].append(text)
        if self._li_buffers:
            self._li_buffers[-1].append(text)
        if self._description_stack and any(self._description_stack) and not self._title_active:
            self._description_fragments.append(text)

    @property
    def strong_texts(self) -> List[str]:
        return list(self._strong_texts)

    @property
    def li_texts(self) -> List[str]:
        return list(self._li_texts)

    @property
    def description_text(self) -> str:
        return collapse_spaces(unescape(" ".join(self._description_fragments)))


def parse_html(html: str) -> StructuredJobHTMLParser:
    parser = StructuredJobHTMLParser()
    parser.feed(html)
    parser.close()
    if not parser.job_title:
        match = re.search(r"<h2[^>]*class=[\"'][^\"']*job-title[^\"']*[\"'][^>]*>(.*?)</h2>", html, flags=re.I | re.S)
        if match:
            parser.job_title = collapse_spaces(re.sub(r"<[^>]+>", " ", match.group(1)))
    return parser


def choose_skill_source(parser: StructuredJobHTMLParser) -> List[str]:
    sources = [parser.strong_texts, parser.li_texts, [parser.description_text]]
    for source in sources:
        cleaned: List[str] = []
        for text in source:
            cleaned.extend(split_skill_phrase(text))
        cleaned = dedupe_skills(cleaned)
        if cleaned:
            return cleaned
    return []


def extract_job_from_html(html: str) -> Dict[str, Any]:
    parser = parse_html(html)
    return {
        "job_title": collapse_spaces(parser.job_title),
        "skills": choose_skill_source(parser),
    }


def read_input(path_value: Optional[str]) -> str:
    if path_value:
        return Path(path_value).read_text(encoding="utf-8", errors="replace")
    return sys.stdin.read()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Extract job title and skills from structured HTML.")
    parser.add_argument("--input", type=str, default=None, help="HTML file path. If omitted, reads from stdin.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args(argv)

    html = read_input(args.input)
    result = extract_job_from_html(html)
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
