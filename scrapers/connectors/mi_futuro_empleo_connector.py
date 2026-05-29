from __future__ import annotations

from bs4 import BeautifulSoup

from scrapers.connectors.base import BaseJobConnector, absolute_url, build_job, compact_text, parse_json_ld_jobs


class MiFuturoEmpleoConnector(BaseJobConnector):
    source_name = "Mi Futuro Empleo"
    base_url = "https://mifuturoempleo.co/empleos"
    priority = "media"

    def search_urls(self) -> list[str]:
        return [absolute_url(self.base_url, "?q=analista%20datos"), absolute_url(self.base_url, "?q=power%20bi")][: self.config.max_pages]

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
        for card in soup.select("article, div[class*='empleo'], div[class*='job'], div[class*='vacante']"):
            title_node = card.select_one("h1,h2,h3,a,[class*='title'],[class*='cargo']")
            if not title_node:
                continue
            link = card.select_one("a[href]")
            text = compact_text(card.get_text(" ", strip=True))
            jobs.append(
                build_job(
                    source_name=self.source_name,
                    base_url=url,
                    title=title_node.get_text(" ", strip=True),
                    company=(card.select_one("[class*='empresa'],[class*='company']") or card).get_text(" ", strip=True)[:120],
                    location=(card.select_one("[class*='ciudad'],[class*='location']") or card).get_text(" ", strip=True)[:120],
                    publication_date=(card.select_one("time,[class*='fecha']") or card).get_text(" ", strip=True)[:80],
                    description=text,
                    source_url=link.get("href") if link else url,
                    raw={"selector_source": "mi_futuro_empleo_cards"},
                )
            )
        return jobs
