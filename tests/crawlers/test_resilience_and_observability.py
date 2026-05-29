from __future__ import annotations

import json

from crawlers.core.observability import JsonLogger, SourceMetrics, network_health_score
from crawlers.core.resilience import CircuitBreaker, CircuitState, detect_blocking_signal
from crawlers.core.retry_policy import RetryPolicy
from crawlers.core.security import sanitize_value


def test_circuit_breaker_opens_after_threshold() -> None:
    breaker = CircuitBreaker(source_name="test", failure_threshold=2)

    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED
    breaker.record_failure()

    assert breaker.state == CircuitState.OPEN
    assert breaker.allow_request() is False


def test_retry_policy_uses_increasing_delay() -> None:
    policy = RetryPolicy(base_delay_seconds=1.0, backoff_multiplier=2.0, jitter_seconds=0.0)

    assert policy.next_delay(1) > policy.next_delay(0)


def test_blocking_signal_detects_captcha_and_429() -> None:
    assert detect_blocking_signal(text="captcha required")[0] is True
    assert detect_blocking_signal(status_code=429)[0] is True


def test_json_logger_sanitizes_tokens(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    logger = JsonLogger("corr-1", path=path)

    logger.log("test", authorization="Bearer secret-token-value", nested={"cookie": "abc"})

    text = path.read_text(encoding="utf-8")
    assert "secret-token-value" not in text
    assert "abc" not in text
    assert "[REDACTED]" in text


def test_network_health_score_penalizes_failures_and_blocks() -> None:
    metrics = SourceMetrics("source")
    metrics.requests = 10
    metrics.failures = 2
    metrics.blocked = 1
    payload = metrics.to_dict()

    assert 0 < payload["health_score"] < 1


def test_sanitize_value_redacts_sensitive_keys() -> None:
    payload = sanitize_value({"access_token": "abc123456789", "safe": "ok"})

    assert payload["access_token"] == "[REDACTED]"
    assert payload["safe"] == "ok"
