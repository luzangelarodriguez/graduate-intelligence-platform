from __future__ import annotations

from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from graduate_intelligence_platform.backend.app.academic_job_acquisition import source_plan_for
from scrapers.connectors.base import BaseJobConnector, absolute_url, build_job, compact_text, parse_json_ld_jobs


class FindJobITConnector(BaseJobConnector):
    source_name = "FindJobIT"
    base_url = "https://findjobit.com/jobs/country/colombia"
    priority = "media"

    def __init__(self, *, source_plan: dict | None = None, max_jobs: int = 20, max_pages: int = 2) -> None:
        super().__init__(max_pages=max_pages, max_jobs=max_jobs)
        self.source_plan = source_plan_for(source_plan, 'findjobit') if source_plan is not None else {"keywords": [], "roles": [], "families": [], "query": ""}

    def search_items(self) -> list[tuple[str, dict[str, object]]]:
        keywords = [str(item).strip() for item in (self.source_plan.get('keywords') or []) if str(item).strip()]
        if not keywords:
            keywords = ["data", "power bi", "analytics", "engineering"]
        items: list[tuple[str, dict[str, object]]] = []
        for keyword in keywords[: self.config.max_pages]:
            url = absolute_url(self.base_url, f"?q={quote_plus(keyword)}")
            items.append((url, {"source": "findjobit", "search_keyword": keyword, "search_keyword_source": "academic_plan", "search_plan": self.source_plan}))
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
        for card in soup.select("article, div[class*='job'], li[class*='job'], a[href*='/jobs/']"):
            title_node = card.select_one("h1,h2,h3,a,[class*='title']")
            if not title_node:
                continue
            link = card if card.name == "a" else card.select_one("a[href]")
            text = compact_text(card.get_text(" ", strip=True))
            jobs.append(
                build_job(
                    source_name=self.source_name,
                    base_url=url,
                    title=title_node.get_text(" ", strip=True),
                    company=(card.select_one("[class*='company']") or card).get_text(" ", strip=True)[:120],
                    location=(card.select_one("[class*='location']") or card).get_text(" ", strip=True)[:120],
                    publication_date=(card.select_one("time,[class*='date']") or card).get_text(" ", strip=True)[:80],
                    description=text,
                    tags=[node.get_text(" ", strip=True) for node in card.select("[class*='tag'],[class*='skill'],[class*='badge']")],
                    source_url=link.get("href") if link else url,
                    raw={"selector_source": "findjobit_cards", "search_plan": self.source_plan},
                )
            )
        return jobs
