from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from crawlers.core.human_behavior import random_user_agent, random_viewport


@dataclass(frozen=True)
class BrowserConfig:
    headless: bool = True
    storage_state_path: Path | None = None
    locale: str = "es-CO"
    timeout_ms: int = 30000


class BrowserManager:
    def __init__(self, config: BrowserConfig | None = None) -> None:
        self.config = config or BrowserConfig()

    def launch(self):
        from playwright.sync_api import sync_playwright

        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=self.config.headless)
        context_args: dict[str, Any] = {
            "user_agent": random_user_agent(),
            "viewport": random_viewport(),
            "locale": self.config.locale,
        }
        if self.config.storage_state_path and self.config.storage_state_path.exists():
            context_args["storage_state"] = str(self.config.storage_state_path)
        context = browser.new_context(**context_args)
        return playwright, browser, context

    @staticmethod
    def close(playwright: Any, browser: Any) -> None:
        try:
            browser.close()
        finally:
            try:
                playwright.stop()
            except Exception:
                pass
