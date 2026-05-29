from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse


@dataclass(frozen=True)
class DomainPolicy:
    domain: str
    robots_awareness: bool = True
    min_delay_seconds: float = 2.0
    max_pages: int = 2
    max_jobs: int = 20
    allowed_hours_utc: tuple[int, int] = (0, 23)
    notes: str = ""


@dataclass
class DomainPolicyRegistry:
    policies: dict[str, DomainPolicy] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.policies:
            self.policies.update(
                {
                    "linkedin.com": DomainPolicy("linkedin.com", min_delay_seconds=4.0, max_pages=1, max_jobs=20, notes="manual_session_only"),
                    "ticjob.co": DomainPolicy("ticjob.co", min_delay_seconds=3.0, max_pages=2, max_jobs=30),
                    "elempleo.com": DomainPolicy("elempleo.com", min_delay_seconds=3.0, max_pages=2, max_jobs=30),
                    "hireline.io": DomainPolicy("hireline.io", min_delay_seconds=3.0, max_pages=2, max_jobs=30),
                    "findjobit.com": DomainPolicy("findjobit.com", min_delay_seconds=3.0, max_pages=2, max_jobs=30),
                }
            )

    def policy_for_url(self, url: str) -> DomainPolicy:
        host = urlparse(url).netloc.casefold()
        for domain, policy in self.policies.items():
            if domain in host:
                return policy
        return DomainPolicy(host or "unknown")


def robots_awareness_enabled() -> bool:
    return os.getenv("CRAWLER_ROBOTS_AWARENESS", "true").casefold() != "false"


def execution_window_allowed(policy: DomainPolicy, *, now: datetime | None = None) -> bool:
    current = now or datetime.utcnow()
    start, end = policy.allowed_hours_utc
    return start <= current.hour <= end


def enforce_safe_crawl_policy(policy: DomainPolicy, *, requested_pages: int, requested_jobs: int) -> dict[str, int | float | bool]:
    return {
        "max_pages": min(requested_pages, policy.max_pages),
        "max_jobs": min(requested_jobs, policy.max_jobs),
        "min_delay_seconds": policy.min_delay_seconds,
        "robots_awareness": policy.robots_awareness and robots_awareness_enabled(),
    }
