from __future__ import annotations

from bs4 import BeautifulSoup

from scrapers.connectors.base import BaseJobConnector, absolute_url, build_job, compact_text, parse_json_ld_jobs


class ServicioPublicoEmpleoConnector(BaseJobConnector):
    source_name = "Buscador de Empleo"
    base_url = "https://www.buscadordeempleo.gov.co/#/home"
    priority = "alta"

    def search_urls(self) -> list[str]:
        return [self.base_url]

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
        for card in soup.select("app-vacante, .vacante, .card-vacante, div[class*='vacante'], div[class*='job']"):
            title_node = card.select_one("h1,h2,h3,[class*='cargo'],[class*='title']")
            if not title_node:
                continue
            text = compact_text(card.get_text(" ", strip=True))
            jobs.append(
                build_job(
                    source_name=self.source_name,
                    base_url=url,
                    title=title_node.get_text(" ", strip=True),
                    company=(card.select_one("[class*='empresa']") or card).get_text(" ", strip=True)[:120],
                    location=(card.select_one("[class*='ubicacion'],[class*='municipio']") or card).get_text(" ", strip=True)[:120],
                    publication_date=(card.select_one("time,[class*='fecha']") or card).get_text(" ", strip=True)[:80],
                    description=text,
                    source_url=url,
                    raw={"selector_source": "servicio_publico_cards"},
                )
            )
        return jobs
