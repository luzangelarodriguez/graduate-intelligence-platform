from __future__ import annotations

from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
LAKEHOUSE_DIR = ROOT_DIR / "scrapers" / "lakehouse"


def dated_layer_path(layer: str, source: str, run_id: str) -> Path:
    stamp = datetime.utcnow().strftime("%Y%m%d")
    path = LAKEHOUSE_DIR / layer / source / stamp / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path

