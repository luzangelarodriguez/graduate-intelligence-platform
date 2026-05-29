from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from bs4 import BeautifulSoup


def _compact(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


@dataclass(frozen=True)
class JobDetail:
    title: str
    company: str
    location: str
    salary: str
    modality: str
    contract_type: str
    seniority: str
    description: str
    responsibilities: list[str]
    requirements: list[str]
    technologies: list[str]
    application_url: str
    source_url: str
    raw_text: str
    raw_html: str = ""
    screenshot_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def infer_modality(text: str) -> str:
    lowered = text.casefold()
    if "remoto" in lowered or "remote" in lowered:
        return "remote"
    if "hibrido" in lowered or "híbrido" in lowered or "hybrid" in lowered:
        return "hybrid"
    if "presencial" in lowered or "onsite" in lowered:
        return "onsite"
    return ""


def split_requirements_and_responsibilities(text: str) -> tuple[list[str], list[str]]:
    chunks = [item.strip(" -•\t") for item in re.split(r"[\n\r]+|(?<=[.;])\s+", text) if item.strip()]
    requirements = [item for item in chunks if any(token in item.casefold() for token in ("requisito", "experiencia", "conocimiento", "debes", "required"))]
    responsibilities = [item for item in chunks if any(token in item.casefold() for token in ("responsabilidad", "funcion", "función", "actividad", "haras", "harás"))]
    return requirements[:12], responsibilities[:12]


def extract_job_detail_from_html(html: str, *, source_url: str, fallback_title: str = "") -> JobDetail:
    soup = BeautifulSoup(html or "", "html.parser")
    raw_text = _compact(soup.get_text(" ", strip=True))
    title_node = soup.select_one("h1,h2,[class*='title'],[class*='cargo']")
    company_node = soup.select_one("[class*='company'],[class*='empresa']")
    location_node = soup.select_one("[class*='location'],[class*='ubicacion'],[class*='ciudad']")
    salary_node = soup.select_one("[class*='salary'],[class*='salario']")
    description_nodes = soup.select("main,article,[class*='description'],[class*='descripcion'],[class*='detalle'],[class*='content']")
    description = _compact(" ".join(node.get_text(" ", strip=True) for node in description_nodes)) or raw_text
    requirements, responsibilities = split_requirements_and_responsibilities(description)
    tags = [_compact(node.get_text(" ", strip=True)) for node in soup.select("[class*='tag'],[class*='skill'],[class*='badge'],[class*='tech']")]
    apply = soup.select_one("a[href*='apply'],a[href*='postul'],a[href*='solic']")
    return JobDetail(
        title=_compact(title_node.get_text(" ", strip=True) if title_node else fallback_title),
        company=_compact(company_node.get_text(" ", strip=True) if company_node else ""),
        location=_compact(location_node.get_text(" ", strip=True) if location_node else ""),
        salary=_compact(salary_node.get_text(" ", strip=True) if salary_node else ""),
        modality=infer_modality(description),
        contract_type="",
        seniority="",
        description=description,
        responsibilities=responsibilities,
        requirements=requirements,
        technologies=[tag for tag in tags if tag],
        application_url=_compact(apply.get("href") if apply else ""),
        source_url=source_url,
        raw_text=raw_text,
        raw_html=html or "",
    )
