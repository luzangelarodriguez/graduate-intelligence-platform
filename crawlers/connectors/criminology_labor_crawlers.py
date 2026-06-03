from __future__ import annotations

from graduate_intelligence_platform.backend.app.academic_job_acquisition import get_academic_search_intelligence, source_plan_for
from crawlers.connectors.api_wrappers import StructuredConnectorCrawler
from scrapers.connectors.criminology_labor_connector import make_criminology_connector


class InterpolCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2, search_intelligence: dict | None = None) -> None:
        intelligence = search_intelligence or get_academic_search_intelligence()
        plan = source_plan_for(intelligence.get('crawler_plans'), 'interpol')
        super().__init__(make_criminology_connector('interpol', max_jobs=max_jobs, max_pages=max_pages, source_plan=plan), 'interpol', source_plan=plan)


class EuropolCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2, search_intelligence: dict | None = None) -> None:
        intelligence = search_intelligence or get_academic_search_intelligence()
        plan = source_plan_for(intelligence.get('crawler_plans'), 'europol')
        super().__init__(make_criminology_connector('europol', max_jobs=max_jobs, max_pages=max_pages, source_plan=plan), 'europol', source_plan=plan)


class UNCareersCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2, search_intelligence: dict | None = None) -> None:
        intelligence = search_intelligence or get_academic_search_intelligence()
        plan = source_plan_for(intelligence.get('crawler_plans'), 'un_careers')
        super().__init__(make_criminology_connector('un_careers', max_jobs=max_jobs, max_pages=max_pages, source_plan=plan), 'un_careers', source_plan=plan)


class UNODCCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2, search_intelligence: dict | None = None) -> None:
        intelligence = search_intelligence or get_academic_search_intelligence()
        plan = source_plan_for(intelligence.get('crawler_plans'), 'unodc')
        super().__init__(make_criminology_connector('unodc', max_jobs=max_jobs, max_pages=max_pages, source_plan=plan), 'unodc', source_plan=plan)


class SecuritasCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2, search_intelligence: dict | None = None) -> None:
        intelligence = search_intelligence or get_academic_search_intelligence()
        plan = source_plan_for(intelligence.get('crawler_plans'), 'securitas')
        super().__init__(make_criminology_connector('securitas', max_jobs=max_jobs, max_pages=max_pages, source_plan=plan), 'securitas', source_plan=plan)


class G4SCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2, search_intelligence: dict | None = None) -> None:
        intelligence = search_intelligence or get_academic_search_intelligence()
        plan = source_plan_for(intelligence.get('crawler_plans'), 'g4s')
        super().__init__(make_criminology_connector('g4s', max_jobs=max_jobs, max_pages=max_pages, source_plan=plan), 'g4s', source_plan=plan)


class ProsegurCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2, search_intelligence: dict | None = None) -> None:
        intelligence = search_intelligence or get_academic_search_intelligence()
        plan = source_plan_for(intelligence.get('crawler_plans'), 'prosegur')
        super().__init__(make_criminology_connector('prosegur', max_jobs=max_jobs, max_pages=max_pages, source_plan=plan), 'prosegur', source_plan=plan)


class FiscaliaColombiaCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2, search_intelligence: dict | None = None) -> None:
        intelligence = search_intelligence or get_academic_search_intelligence()
        plan = source_plan_for(intelligence.get('crawler_plans'), 'fiscalia_colombia')
        super().__init__(make_criminology_connector('fiscalia_colombia', max_jobs=max_jobs, max_pages=max_pages, source_plan=plan), 'fiscalia_colombia', source_plan=plan)


class PoliciaColombiaCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2, search_intelligence: dict | None = None) -> None:
        intelligence = search_intelligence or get_academic_search_intelligence()
        plan = source_plan_for(intelligence.get('crawler_plans'), 'policia_colombia')
        super().__init__(make_criminology_connector('policia_colombia', max_jobs=max_jobs, max_pages=max_pages, source_plan=plan), 'policia_colombia', source_plan=plan)


class INPECCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2, search_intelligence: dict | None = None) -> None:
        intelligence = search_intelligence or get_academic_search_intelligence()
        plan = source_plan_for(intelligence.get('crawler_plans'), 'inpec')
        super().__init__(make_criminology_connector('inpec', max_jobs=max_jobs, max_pages=max_pages, source_plan=plan), 'inpec', source_plan=plan)


class ProcuraduriaCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2, search_intelligence: dict | None = None) -> None:
        intelligence = search_intelligence or get_academic_search_intelligence()
        plan = source_plan_for(intelligence.get('crawler_plans'), 'procuraduria')
        super().__init__(make_criminology_connector('procuraduria', max_jobs=max_jobs, max_pages=max_pages, source_plan=plan), 'procuraduria', source_plan=plan)


class DefensoriaCrawler(StructuredConnectorCrawler):
    def __init__(self, *, max_jobs: int = 20, max_pages: int = 2, search_intelligence: dict | None = None) -> None:
        intelligence = search_intelligence or get_academic_search_intelligence()
        plan = source_plan_for(intelligence.get('crawler_plans'), 'defensoria')
        super().__init__(make_criminology_connector('defensoria', max_jobs=max_jobs, max_pages=max_pages, source_plan=plan), 'defensoria', source_plan=plan)
