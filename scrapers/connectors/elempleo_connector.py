from __future__ import annotations

from bs4 import BeautifulSoup

from scrapers.connectors.base import BaseJobConnector, absolute_url, build_job, compact_text, parse_json_ld_jobs


class ElempleoConnector(BaseJobConnector):
    source_name = "Elempleo"
    base_url = "https://www.elempleo.com/co/ofertas-empleo/"
    priority = "alta"

    def search_urls(self) -> list[str]:
        queries = ["analista-datos", "analista-bi", "power-bi", "ingeniero-datos"]
        return [absolute_url(self.base_url, f"?trabajo={query}") for query in queries][: self.config.max_pages]

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
            title_node = card.select_one("h1,h2,h3,a[href*='oferta'],[class*='title'],[class*='cargo']")
            if not title_node:
                continue
            link = card.select_one("a[href]")
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
                    raw={"selector_source": "elempleo_cards"},
                )
            )
        return jobs
