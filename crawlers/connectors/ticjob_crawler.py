from crawlers.connectors.api_wrappers import StructuredConnectorCrawler
from scrapers.connectors.ticjob_connector import TicjobConnector


class TicjobCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2) -> None:
        super().__init__(TicjobConnector(max_jobs=max_jobs, max_pages=max_pages), "ticjob")
