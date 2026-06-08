from __future__ import annotations

from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from graduate_intelligence_platform.backend.app.academic_job_acquisition import source_plan_for
from scrapers.connectors.base import BaseJobConnector, absolute_url, build_job, compact_text, parse_json_ld_jobs


class ElempleoConnector(BaseJobConnector):
    source_name = "Elempleo"
    base_url = "https://www.elempleo.com/co/ofertas-empleo/"
    priority = "alta"

    def __init__(self, *, source_plan: dict | None = None, max_jobs: int = 20, max_pages: int = 2) -> None:
        super().__init__(max_pages=max_pages, max_jobs=max_jobs)
        self.source_plan = source_plan_for(source_plan, 'elempleo') if source_plan is not None else {"keywords": [], "roles": [], "families": [], "query": ""}

    def search_items(self) -> list[tuple[str, dict[str, object]]]:
        keywords = [str(item).strip() for item in (self.source_plan.get('keywords') or []) if str(item).strip()]
        if not keywords:
            keywords = ["analista datos", "business intelligence", "power bi", "ingeniero datos"]
        items: list[tuple[str, dict[str, object]]] = []
        for keyword in keywords[: self.config.max_pages]:
            query = quote_plus(keyword).replace('+', '-')
            url = absolute_url(self.base_url, f"?trabajo={query}")
            items.append((url, {"source": "elempleo", "search_keyword": keyword, "search_keyword_source": "academic_plan", "search_plan": self.source_plan}))
        return items

    def search_urls(self) -> list[str]:
        return [url for url, _ in self.search_items()]

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
        for card in soup.select("article, div[class*='offer'], div[class*='oferta'], div[class*='job']"):
            title_node = card.select_one("h1,h2,h3,a[href*='detalle-oferta'],[class*='title'],[class*='cargo']")
            if not title_node:
                continue
            link = card.select_one("a[href*='detalle-oferta']") or card.select_one("a[href]")
            company_node = card.select_one("[class*='company'],[class*='empresa']")
            location_node = card.select_one("[class*='location'],[class*='ubicacion'],[class*='ciudad']")
            date_node = card.select_one("time,[class*='date'],[class*='fecha']")
            text = compact_text(card.get_text(" ", strip=True))
            jobs.append(
                build_job(
                    source_name=self.source_name,
                    base_url=url,
                    title=title_node.get_text(" ", strip=True),
                    company=company_node.get_text(" ", strip=True) if company_node else "",
                    location=location_node.get_text(" ", strip=True) if location_node else "Colombia",
                    publication_date=date_node.get_text(" ", strip=True) if date_node else "",
                    description=text,
                    tags=[node.get_text(" ", strip=True) for node in card.select("[class*='tag'],[class*='skill'],[class*='badge']")],
                    source_url=link.get("href") if link else url,
                    raw={"selector_source": "elempleo_cards", "search_plan": self.source_plan},
                )
            )
        return jobs
