from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    source_name: str
    failure_threshold: int = 3
    recovery_timeout_seconds: float = 120.0
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    opened_at: float | None = None

    def allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN and self.opened_at is not None:
            if time.monotonic() - self.opened_at >= self.recovery_timeout_seconds:
                self.state = CircuitState.HALF_OPEN
                return True
        return self.state == CircuitState.HALF_OPEN

    def record_success(self) -> None:
        self.failure_count = 0
        self.opened_at = None
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = time.monotonic()

    def snapshot(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "opened": self.opened_at is not None,
        }


@dataclass
class CircuitBreakerRegistry:
    failure_threshold: int = 3
    recovery_timeout_seconds: float = 120.0
    breakers: dict[str, CircuitBreaker] = field(default_factory=dict)

    def for_source(self, source_name: str) -> CircuitBreaker:
        if source_name not in self.breakers:
            self.breakers[source_name] = CircuitBreaker(
                source_name=source_name,
                failure_threshold=self.failure_threshold,
                recovery_timeout_seconds=self.recovery_timeout_seconds,
            )
        return self.breakers[source_name]


BLOCK_MARKERS = (
    "captcha",
    "checkpoint",
    "security verification",
    "verificacion de seguridad",
    "verificación de seguridad",
    "access denied",
    "too many requests",
    "unusual activity",
)


def detect_blocking_signal(*, url: str = "", text: str = "", status_code: int | None = None) -> tuple[bool, str]:
    if status_code in {401, 403, 429}:
        return True, f"http_{status_code}"
    combined = f"{url} {text}".casefold()
    for marker in BLOCK_MARKERS:
        if marker in combined:
            return True, marker
    return False, ""


def fail_safe_shutdown(errors: list[dict[str, str]], *, source_name: str, reason: str) -> None:
    errors.append({"source": source_name, "error_type": "fail_safe_shutdown", "error_message": reason})
