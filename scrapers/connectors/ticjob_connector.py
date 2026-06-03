from __future__ import annotations

import re
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from bs4.element import Tag

from graduate_intelligence_platform.backend.app.academic_job_acquisition import source_plan_for
from ml.relevance.contextual_job_relevance_engine import score_contextual_relevance
from scrapers.connectors.base import BaseJobConnector, absolute_url, build_job, compact_text, parse_json_ld_jobs


COMPANY_SUFFIX_RE = re.compile(r"(s\.?a\.?s\.?|ltda\.?|inc\.?|corp\.?|solutions|consulting|technology|technologies)", re.IGNORECASE)


def _card_container(node: Tag) -> Tag:
    if node.name != "a":
        return node
    parent = node.find_parent(["article", "li", "div"], class_=re.compile(r"(job|card|vacante|oferta|empleo|result)", re.IGNORECASE))
    return parent if isinstance(parent, Tag) else node


def _first_text(card: Tag, selectors: tuple[str, ...]) -> str:
    for selector in selectors:
        node = card.select_one(selector)
        value = compact_text(node.get_text(" ", strip=True) if node else "")
        if value:
            return value
    return ""


def _looks_like_company(value: str) -> bool:
    value = compact_text(value or "")
    if not value or len(value) > 90 or len(value.split()) > 8:
        return False
    if re.search(r"(rol|requisitos|responsabilidades|condiciones laborales|salario|modalidad|experiencia|vacante)", value, re.IGNORECASE):
        return False
    return bool(COMPANY_SUFFIX_RE.search(value)) or bool(re.search(r"(colombia|latam|group|empresa)", value, re.IGNORECASE))


class TicjobConnector(BaseJobConnector):
    source_name = "Ticjob"
    base_url = "https://ticjob.co/"
    priority = "alta"

    def __init__(self, *, source_plan: dict | None = None, max_jobs: int = 20, max_pages: int = 2) -> None:
        super().__init__(max_pages=max_pages, max_jobs=max_jobs)
        self.source_plan = source_plan_for(source_plan, 'ticjob') if source_plan is not None else {"keywords": [], "roles": [], "families": [], "query": ""}

    def search_items(self) -> list[tuple[str, dict[str, object]]]:
        keywords = [str(item).strip() for item in (self.source_plan.get('keywords') or []) if str(item).strip()]
        if not keywords:
            keywords = ["data analyst", "business intelligence", "power bi", "data engineer"]
        items: list[tuple[str, dict[str, object]]] = []
        for keyword in keywords[: self.config.max_pages]:
            query = quote_plus(keyword)
            url = absolute_url(self.base_url, f"/es/search?q={query}")
            items.append((url, {"source": "ticjob", "search_keyword": keyword, "search_keyword_source": "academic_plan", "search_plan": self.source_plan}))
        return items

    def search_urls(self) -> list[str]:
        return [url for url, _ in self.search_items()]

    def fetch_detail_text(self, url: str) -> tuple[str, dict[str, str]]:
        try:
            html = self.fetch_html(url)
        except Exception:
            return "", {}
        soup = BeautifulSoup(html, "html.parser")
        containers = soup.select("main, article, [class*='description'], [class*='detalle'], [class*='job-detail'], [class*='content']")
        text = compact_text(" ".join(container.get_text(" ", strip=True) for container in containers)) or compact_text(soup.get_text(" ", strip=True))
        metadata = {}
        for label in ("salario", "modalidad", "seniority", "fecha"):
            node = soup.find(string=lambda value: value and label in value.casefold())
            if node:
                metadata[label] = compact_text(str(node))
        return text, metadata

    def extract_from_html(self, html: str, url: str):
        jobs = [
            build_job(
                source_name=self.source_name,
                base_url=url,
                title=item.get("title", ""),
                company=item.get("company", ""),
                location=item.get("location", "Colombia"),
                publication_date=item.get("publication_date", ""),
                description=item.get("description", ""),
                source_url=item.get("source_url", url),
                raw=item,
            )
            for item in parse_json_ld_jobs(html, self.source_name, url)
        ]
        soup = BeautifulSoup(html, "html.parser")
        selectors = [
            "article[class*='job']",
            "div[class*='job-card']",
            "div[class*='vacante']",
            "div[class*='oferta']",
            "div[class*='result']",
            "div[class*='offer']",
            "li[class*='job']",
            "a[href*='it-job-openings']",
            "a[href*='oferta']",
            "a[href*='empleo']",
        ]
        cards = []
        seen_cards: set[int] = set()
        for selector in selectors:
            for node in soup.select(selector):
                card = _card_container(node)
                identity = id(card)
                if identity in seen_cards:
                    continue
                seen_cards.add(identity)
                cards.append(card)
        for card in cards:
            title = _first_text(card, ("h1", "h2", "h3", "h4", "[class*='title']", "[class*='puesto']", "[class*='cargo']"))
            company = _first_text(
                card,
                (
                    "[class*='company']",
                    "[class*='empresa']",
                    "[class*='employer']",
                    "[class*='organization']",
                    "[class*='cliente']",
                    "[class*='client']",
                ),
            )
            location_node = card.select_one("[class*='location'],[class*='ubicacion'],[class*='city']")
            date_node = card.select_one("time,[class*='date'],[class*='fecha']")
            tag_nodes = card.select("[class*='tag'],[class*='skill'],[class*='badge']")
            link = card if card.name == "a" else card.select_one("a[href]")
            text = compact_text(card.get_text(" ", strip=True))
            if not title:
                title = compact_text(link.get_text(" ", strip=True) if link else "")
            if title and not company and _looks_like_company(title):
                company = title
                title = _first_text(card, ("[class*='job-title']", "[class*='vacancy-title']", "[class*='offer-title']"))
            if not company:
                for candidate_node in card.select("a,span"):
                    candidate = compact_text(candidate_node.get_text(" ", strip=True))
                    if candidate and candidate != title and _looks_like_company(candidate):
                        company = candidate
                        break
            if not title and len(text) < 180:
                title = text[:90]
            if not title or _looks_like_company(title) and not any(token in text.casefold() for token in ("analista", "developer", "desarrollador", "ingeniero", "consultor", "architect", "admin")):
                continue
            detail_url = absolute_url(url, link.get("href") if link else url)
            detail_text = ""
            detail_meta: dict[str, str] = {}
            preview_job = build_job(
                source_name=self.source_name,
                base_url=url,
                title=title,
                company=company,
                location=location_node.get_text(" ", strip=True) if location_node else "Colombia",
                publication_date=date_node.get_text(" ", strip=True) if date_node else "",
                description=text,
                tags=[node.get_text(" ", strip=True) for node in tag_nodes],
                source_url=detail_url,
                raw={"selector_source": "ticjob_cards", "phase": "list", "search_plan": self.source_plan},
            )
            preview_score = score_contextual_relevance(
                title=preview_job.title,
                description=preview_job.description,
                tags=preview_job.tags,
                skills=preview_job.skills,
                technologies=preview_job.technologies,
            )
            if preview_score.contextual_relevance_score >= 0.20 or detail_url != url:
                detail_text, detail_meta = self.fetch_detail_text(detail_url)
            description = compact_text(f"{text} {detail_text}")
            jobs.append(
                build_job(
                    source_name=self.source_name,
                    base_url=url,
                    title=title,
                    company=company,
                    location=location_node.get_text(" ", strip=True) if location_node else "Colombia",
                    publication_date=date_node.get_text(" ", strip=True) if date_node else "",
                    description=description,
                    tags=[node.get_text(" ", strip=True) for node in tag_nodes],
                    seniority=detail_meta.get("seniority", ""),
                    modality=detail_meta.get("modalidad", ""),
                    salary=detail_meta.get("salario", ""),
                    source_url=detail_url,
                    raw={
                        "selector_source": "ticjob_cards",
                        "list_text": text,
                        "detail_fetched": bool(detail_text),
                        "contextual_preview": preview_score.__dict__,
                        "search_plan": self.source_plan,
                    },
                )
            )
        return jobs
