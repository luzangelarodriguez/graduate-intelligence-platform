from scrapers.discovery.api_endpoint_detector import endpoint_confidence, is_interesting_request, run_api_discovery


def test_endpoint_detector_prioritizes_json_job_apis() -> None:
    confidence, reason = endpoint_confidence("https://example.com/api/jobs/search?query=data", "xhr", "application/json")

    assert confidence >= 0.65
    assert "api/" in reason
    assert is_interesting_request("https://example.com/graphql", "fetch")


def test_api_discovery_dry_run_does_not_touch_network() -> None:
    result = run_api_discovery(sources=["ticjob", "elempleo"], execute_network=False)

    assert result["dry_run"] is True
    assert result["endpoints"] == 2
