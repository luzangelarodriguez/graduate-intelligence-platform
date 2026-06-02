from __future__ import annotations

from crawlers.connectors.api_wrappers import StructuredConnectorCrawler
from scrapers.connectors.criminology_labor_connector import make_criminology_connector


class InterpolCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2) -> None:
        super().__init__(make_criminology_connector("interpol", max_jobs=max_jobs, max_pages=max_pages), "interpol")


class EuropolCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2) -> None:
        super().__init__(make_criminology_connector("europol", max_jobs=max_jobs, max_pages=max_pages), "europol")


class UNCareersCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2) -> None:
        super().__init__(make_criminology_connector("un_careers", max_jobs=max_jobs, max_pages=max_pages), "un_careers")


class UNODCCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2) -> None:
        super().__init__(make_criminology_connector("unodc", max_jobs=max_jobs, max_pages=max_pages), "unodc")


class SecuritasCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2) -> None:
        super().__init__(make_criminology_connector("securitas", max_jobs=max_jobs, max_pages=max_pages), "securitas")


class G4SCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2) -> None:
        super().__init__(make_criminology_connector("g4s", max_jobs=max_jobs, max_pages=max_pages), "g4s")


class ProsegurCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2) -> None:
        super().__init__(make_criminology_connector("prosegur", max_jobs=max_jobs, max_pages=max_pages), "prosegur")


class FiscaliaColombiaCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2) -> None:
        super().__init__(make_criminology_connector("fiscalia_colombia", max_jobs=max_jobs, max_pages=max_pages), "fiscalia_colombia")


class PoliciaColombiaCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2) -> None:
        super().__init__(make_criminology_connector("policia_colombia", max_jobs=max_jobs, max_pages=max_pages), "policia_colombia")


class INPECCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2) -> None:
        super().__init__(make_criminology_connector("inpec", max_jobs=max_jobs, max_pages=max_pages), "inpec")


class ProcuraduriaCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2) -> None:
        super().__init__(make_criminology_connector("procuraduria", max_jobs=max_jobs, max_pages=max_pages), "procuraduria")


class DefensoriaCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2) -> None:
        super().__init__(make_criminology_connector("defensoria", max_jobs=max_jobs, max_pages=max_pages), "defensoria")
