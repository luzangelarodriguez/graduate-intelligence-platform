from agents.visual_analytics_labor_agent import parse_detail_html
from crawlers.storage.postgres_warehouse import duplicate_group_key, normalize_company, semantic_title_family


def test_parse_detail_html_extracts_company_from_json_ld() -> None:
    html = """
    <html><head>
      <script type="application/ld+json">
      {"@type":"JobPosting","title":"Analista BI","hiringOrganization":{"@type":"Organization","name":"IBM Colombia"}}
      </script>
    </head><body>
      <h1>Analista BI</h1>
      <main>Responsabilidades: dashboards, SQL, Power BI y KPIs.</main>
    </body></html>
    """

    _bronze, payload = parse_detail_html(html, source_name="Ticjob", source_url="https://jobs.example.com/1")

    assert payload["company"] == "IBM Colombia"


def test_company_normalization_maps_aliases() -> None:
    company, confidence = normalize_company("International Business Machines Colombia SAS")

    assert company == "IBM"
    assert confidence >= 0.8


def test_company_normalization_rejects_description_blocks() -> None:
    company, confidence = normalize_company(
        "Analista Funcional Rol: Analista Funcional de Procesos de Software Requisitos: experiencia documentando procesos funcionales"
    )

    assert company == "No especificada"
    assert confidence < 0.5


def test_duplicate_group_uses_semantic_job_signature() -> None:
    left = duplicate_group_key(title="Analytics Engineer", company="IBM", location="Bogota", skills=["SQL", "Power BI"])
    right = duplicate_group_key(title="Analytics Engineer", company="IBM", location="Bogota", skills=["Power BI", "SQL"])

    assert left == right


def test_semantic_title_family_infers_hybrid_role() -> None:
    family, inference, score = semantic_title_family("Analytics Engineer", ["SQL", "ETL", "Power BI"])

    assert family == "Analytics Engineering"
    assert "Data Engineer" in inference
    assert score >= 0.8
