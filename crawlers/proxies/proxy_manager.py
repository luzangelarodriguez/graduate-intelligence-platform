from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class ProxyManager:
    use_proxies: bool = field(default_factory=lambda: os.getenv("CRAWLER_USE_PROXIES", "false").casefold() == "true")
    raw_proxies: str = field(default_factory=lambda: os.getenv("CRAWLER_PROXIES", ""))
    _index: int = 0

    def proxies(self) -> list[str]:
        return [item.strip() for item in self.raw_proxies.split(",") if item.strip()]

    def next_proxy(self) -> str | None:
        items = self.proxies()
        if not self.use_proxies or not items:
            return None
        proxy = items[self._index % len(items)]
        self._index += 1
        return proxy

    def validate_proxy(self, proxy: str | None) -> bool:
        if not proxy:
            return True
        return proxy.startswith(("http://", "https://", "socks5://"))
