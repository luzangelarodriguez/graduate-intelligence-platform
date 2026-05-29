from __future__ import annotations

from bs4 import BeautifulSoup

from scrapers.connectors.base import BaseJobConnector, absolute_url, build_job, compact_text, parse_json_ld_jobs


class FindJobITConnector(BaseJobConnector):
    source_name = "FindJobIT"
    base_url = "https://findjobit.com/jobs/country/colombia"
    priority = "media"

    def search_urls(self) -> list[str]:
        return [self.base_url, absolute_url(self.base_url, "?q=data"), absolute_url(self.base_url, "?q=power%20bi")][: self.config.max_pages]

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
                    raw={"selector_source": "findjobit_cards"},
                )
            )
        return jobs
