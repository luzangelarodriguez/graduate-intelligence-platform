from __future__ import annotations

from bs4 import BeautifulSoup

from scrapers.connectors.base import BaseJobConnector, absolute_url, build_job, compact_text, parse_json_ld_jobs


class HirelineConnector(BaseJobConnector):
    source_name = "Hireline"
    base_url = "https://hireline.io/co/empleos"
    priority = "media-alta"

    def search_urls(self) -> list[str]:
        queries = ["power%20bi", "data%20analyst", "business%20intelligence", "data%20engineer"]
        return [absolute_url(self.base_url, f"?q={query}") for query in queries][: self.config.max_pages]

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
        for card in soup.select("[data-testid*='job'], article, div[class*='vacancy'], div[class*='job-card']"):
            title_node = card.select_one("h1,h2,h3,a,[class*='title']")
            if not title_node:
                continue
            link = card.select_one("a[href]")
            text = compact_text(card.get_text(" ", strip=True))
            jobs.append(
                build_job(
                    source_name=self.source_name,
                    base_url=url,
                    title=title_node.get_text(" ", strip=True),
                    company=(card.select_one("[class*='company'],[class*='empresa']") or card).get_text(" ", strip=True)[:120],
                    location=(card.select_one("[class*='location'],[class*='ubicacion']") or card).get_text(" ", strip=True)[:120],
                    publication_date=(card.select_one("time,[class*='date']") or card).get_text(" ", strip=True)[:80],
                    description=text,
                    tags=[node.get_text(" ", strip=True) for node in card.select("[class*='tag'],[class*='skill'],[class*='badge']")],
                    source_url=link.get("href") if link else url,
                    raw={"selector_source": "hireline_cards"},
                )
            )
        return jobs
