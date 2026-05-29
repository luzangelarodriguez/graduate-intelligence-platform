from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class SourceRateLimiter:
    min_interval_seconds: float = 2.0
    max_requests: int = 50
    _last_request_at: float = 0.0
    _request_count: int = 0

    def allow(self) -> bool:
        return self._request_count < self.max_requests

    def wait(self) -> None:
        if not self.allow():
            raise RuntimeError("source_rate_limit_exceeded")
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_request_at = time.monotonic()
        self._request_count += 1


@dataclass
class RateLimiterRegistry:
    default_interval_seconds: float = 2.0
    default_max_requests: int = 50
    limiters: dict[str, SourceRateLimiter] = field(default_factory=dict)

    def for_source(self, source_name: str) -> SourceRateLimiter:
        if source_name not in self.limiters:
            self.limiters[source_name] = SourceRateLimiter(self.default_interval_seconds, self.default_max_requests)
        return self.limiters[source_name]
