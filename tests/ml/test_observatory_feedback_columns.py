from __future__ import annotations

from ml.feedback.ingest_human_feedback import _parse_optional_bool


def test_parse_optional_bool_supports_observatory_feedback_values() -> None:
    assert _parse_optional_bool("yes") is True
    assert _parse_optional_bool("accept") is True
    assert _parse_optional_bool("no") is False
    assert _parse_optional_bool("reject") is False
    assert _parse_optional_bool("") is None
