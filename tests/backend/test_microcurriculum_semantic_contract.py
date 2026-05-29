from graduate_intelligence_platform.backend.app.api import classify_gap_status


def test_detected_entity_is_not_a_market_gap():
    detected = ["python", "power bi", "modelacion financiera"]
    market = ["python", "mlops", "power bi"]

    assert classify_gap_status("python", detected, market) == "strengthening_area"
    assert classify_gap_status("mlops", detected, market) == "missing_gap"
    assert classify_gap_status("modelacion financiera", detected, market) == "detected"
    assert classify_gap_status("", detected, market) == "not_applicable"
