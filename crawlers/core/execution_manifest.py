from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
MANIFEST_DIR = ROOT_DIR / "outputs" / "labor_acquisition_manifests"


@dataclass
class ExecutionManifest:
    correlation_id: str
    sources: list[str]
    execute_network: bool
    max_jobs: int
    max_pages: int
    persist: bool
    quality_review: bool
    started_at: float = field(default_factory=time.time)
    checkpoints: dict[str, Any] = field(default_factory=dict)
    finished_at: float | None = None
    cancelled: bool = False

    @property
    def path(self) -> Path:
        return MANIFEST_DIR / f"{self.correlation_id}.json"

    def save(self) -> None:
        MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")

    def checkpoint(self, name: str, payload: Any) -> None:
        self.checkpoints[name] = payload
        self.save()

    def finish(self) -> None:
        self.finished_at = time.time()
        self.save()


def load_manifest(correlation_id: str) -> ExecutionManifest | None:
    path = MANIFEST_DIR / f"{correlation_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return ExecutionManifest(**data)
