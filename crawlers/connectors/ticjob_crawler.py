from __future__ import annotations

from graduate_intelligence_platform.backend.app.academic_job_acquisition import get_academic_search_intelligence, source_plan_for
from crawlers.connectors.api_wrappers import StructuredConnectorCrawler
from scrapers.connectors.ticjob_connector import TicjobConnector


class TicjobCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2, search_intelligence: dict | None = None) -> None:
        intelligence = search_intelligence or get_academic_search_intelligence()
        plan = source_plan_for(intelligence.get('crawler_plans'), 'ticjob')
        super().__init__(TicjobConnector(max_jobs=max_jobs, max_pages=max_pages, source_plan=plan), 'ticjob', source_plan=plan)
