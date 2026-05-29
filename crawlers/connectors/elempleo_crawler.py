from crawlers.connectors.api_wrappers import StructuredConnectorCrawler
from scrapers.connectors.elempleo_connector import ElempleoConnector


class ElempleoCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2) -> None:
        super().__init__(ElempleoConnector(max_jobs=max_jobs, max_pages=max_pages), "elempleo")
