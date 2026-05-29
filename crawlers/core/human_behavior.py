from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any


USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 Version/16.6 Safari/605.1.15",
)

VIEWPORTS = (
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 850},
)


@dataclass(frozen=True)
class HumanBehaviorProfile:
    min_delay_ms: int = 900
    max_delay_ms: int = 2600
    min_scroll_px: int = 350
    max_scroll_px: int = 1100


def random_user_agent() -> str:
    return random.choice(USER_AGENTS)


def random_viewport() -> dict[str, int]:
    return dict(random.choice(VIEWPORTS))


def random_delay(profile: HumanBehaviorProfile | None = None) -> float:
    profile = profile or HumanBehaviorProfile()
    return random.randint(profile.min_delay_ms, profile.max_delay_ms) / 1000


def sleep_like_human(profile: HumanBehaviorProfile | None = None) -> None:
    time.sleep(random_delay(profile))


def human_scroll(page: Any, profile: HumanBehaviorProfile | None = None) -> None:
    profile = profile or HumanBehaviorProfile()
    try:
        page.mouse.wheel(0, random.randint(profile.min_scroll_px, profile.max_scroll_px))
    except Exception:
        return None
