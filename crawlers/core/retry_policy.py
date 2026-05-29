from __future__ import annotations

import time
import random
from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 2
    base_delay_seconds: float = 1.5
    backoff_multiplier: float = 1.8
    jitter_seconds: float = 0.35
    adaptive: bool = True

    def run(self, fn: Callable[[], T]) -> T:
        last_error: Exception | None = None
        for attempt in range(self.max_attempts + 1):
            try:
                return fn()
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_attempts:
                    break
                delay = self.next_delay(attempt, last_error=exc)
                time.sleep(delay)
        assert last_error is not None
        raise last_error

    def next_delay(self, attempt: int, *, last_error: Exception | None = None) -> float:
        multiplier = self.backoff_multiplier
        if self.adaptive and last_error is not None:
            message = str(last_error).casefold()
            if any(token in message for token in ("429", "timeout", "rate", "captcha", "checkpoint")):
                multiplier += 0.7
        return self.base_delay_seconds * (multiplier**attempt) + random.uniform(0, self.jitter_seconds)
