from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from crawlers.core.security import sanitize_value

ROOT_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT_DIR / "outputs"
EVENT_LOG_PATH = LOG_DIR / "labor_acquisition_events.jsonl"


def new_correlation_id(prefix: str = "lap") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


@dataclass
class SourceMetrics:
    source_name: str
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    requests: int = 0
    successes: int = 0
    failures: int = 0
    blocked: int = 0
    latency_ms: list[float] = field(default_factory=list)

    def record_latency(self, elapsed_ms: float) -> None:
        self.latency_ms.append(round(elapsed_ms, 3))

    def finish(self) -> None:
        self.finished_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        avg_latency = sum(self.latency_ms) / len(self.latency_ms) if self.latency_ms else 0.0
        payload = asdict(self)
        payload["duration_seconds"] = round((self.finished_at or time.time()) - self.started_at, 4)
        payload["avg_latency_ms"] = round(avg_latency, 3)
        payload["health_score"] = network_health_score(payload)
        return payload


def network_health_score(metrics: dict[str, Any]) -> float:
    requests = max(int(metrics.get("requests", 0)), 1)
    failures = int(metrics.get("failures", 0))
    blocked = int(metrics.get("blocked", 0))
    score = 1.0 - min(failures / requests, 1.0) * 0.45 - min(blocked / requests, 1.0) * 0.45
    avg_latency = float(metrics.get("avg_latency_ms", 0.0) or 0.0)
    if avg_latency > 10000:
        score -= 0.10
    return round(max(score, 0.0), 4)


class JsonLogger:
    def __init__(self, correlation_id: str, path: Path = EVENT_LOG_PATH) -> None:
        self.correlation_id = correlation_id
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: str, **payload: Any) -> None:
        record = {
            "ts": time.time(),
            "correlation_id": self.correlation_id,
            "event": event,
            **sanitize_value(payload),
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
