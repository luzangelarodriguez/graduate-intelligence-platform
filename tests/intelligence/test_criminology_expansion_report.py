from scripts.generate_criminology_labor_intelligence_expansion import build_report


def test_criminology_expansion_report_contains_requested_sections() -> None:
    report = build_report()

    assert "# Criminology Labor Intelligence Expansion" in report
    assert "New engines created: none." in report
    assert "## New Sources" in report
    assert "## New Roles" in report
    assert "## New Skills" in report
    assert "## New Graph Edges" in report
    assert "## New Benchmark Coverage" in report
    assert "## Impact On Program 108" in report
    assert "Interpol Careers" in report
    assert "Fiscalia Colombia Convocatorias" in report
    assert "criminal investigation" in report
    assert "recommendation_observatory" in report
