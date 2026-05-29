from crawlers.connectors.api_wrappers import StructuredConnectorCrawler
from scrapers.connectors.findjobit_connector import FindJobITConnector


class FindJobITCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2) -> None:
        super().__init__(FindJobITConnector(max_jobs=max_jobs, max_pages=max_pages), "findjobit")
