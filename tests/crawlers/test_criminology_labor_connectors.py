from crawlers.connectors.api_wrappers import make_connector
from scrapers.connectors.criminology_labor_connector import criminology_source_keys, make_criminology_connector
from scrapers.normalization.visual_analytics_skill_taxonomy import extract_visual_analytics_skills


def test_all_requested_criminology_sources_are_registered() -> None:
    expected = {
        "interpol",
        "europol",
        "un_careers",
        "unodc",
        "securitas",
        "g4s",
        "prosegur",
        "fiscalia_colombia",
        "policia_colombia",
        "inpec",
        "procuraduria",
        "defensoria",
    }

    assert expected <= set(criminology_source_keys())
    for source in expected:
        crawler = make_connector(source, max_jobs=1, max_pages=1)
        assert crawler.source_name == source


def test_criminology_connector_extracts_structured_job_evidence() -> None:
    connector = make_criminology_connector("fiscalia_colombia", max_jobs=3, max_pages=1)
    html = """
    <article class="convocatoria empleo">
      <h2>Tecnico Investigador Criminalistico</h2>
      <p>Funciones de investigacion criminal, criminalistica, cadena de custodia,
      analisis forense, inteligencia criminal y apoyo a policia judicial.</p>
      <p>Requisitos: experiencia en investigacion judicial y certificaciones de seguridad.</p>
    </article>
    """

    jobs = connector.extract_from_html(html, connector.base_url)

    assert jobs
    job = jobs[0]
    assert job.title == "Tecnico Investigador Criminalistico"
    assert job.company == "Fiscalia General de la Nacion"
    assert "criminal investigation" in job.skills
    assert "forensic analysis" in job.skills
    assert "chain of custody" in job.skills
    assert "responsibilities" in job.raw["extraction_contract"]


def test_criminology_skill_aliases_feed_existing_skill_extractor() -> None:
    text = "Investigacion criminal, victimologia, ciberdelito, lavado de activos, cadena de custodia y seguridad publica."
    skills = {item.normalized for item in extract_visual_analytics_skills(text)}

    assert {
        "criminal investigation",
        "victimology",
        "cybercrime",
        "financial crime",
        "chain of custody",
        "public safety",
    } <= skills
