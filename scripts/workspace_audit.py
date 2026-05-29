from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUTPUT = DOCS / "WORKSPACE_AUDIT.md"
JSON_OUTPUT = DOCS / "workspace_audit_inventory.json"

ACTIVE_CORE_PREFIXES = (
    "graduate_intelligence_platform/backend/app/",
    "graduate_intelligence_platform/frontend/src/",
    "backend/repositories/",
    "backend/services/",
    "microcurriculum_engine/",
    "ml/",
    "scrapers/pipelines/",
    "scrapers/sources/",
    "scrapers/taxonomy/",
    "scrapers/normalization/",
    "database/migrations/",
    "tests/",
    "requirements/",
)

LEGACY_PREFIXES = (
    "archive/",
    "templates/",
    "static/",
    "frontend/",
)

TEMP_PARTS = (
    "__pycache__",
    ".pytest_cache",
    ".vite",
    "node_modules",
    "dist",
    "build",
)

MOCK_PATTERNS = (
    "mock",
    "snies_benchmark_mock",
    "placeholder",
)

SAFE_DELETE_SUFFIXES = (
    ".pyc",
    ".pyo",
    ".tmp",
    ".bak",
    ".old",
)

UNKNOWN_IGNORE_DIRS = {".git", ".venv", ".venv_software"}


@dataclass
class InventoryItem:
    path: str
    size: int
    category: str
    reason: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def classify(path: Path) -> tuple[str, str]:
    value = rel(path)
    lower = value.lower()
    parts = set(path.parts)
    if any(part in parts for part in TEMP_PARTS) or lower.endswith(SAFE_DELETE_SUFFIXES):
        return "SAFE_TO_DELETE", "Regenerable cache/build/temp artifact."
    if any(pattern in lower for pattern in MOCK_PATTERNS):
        return "MOCK", "Contains mock/placeholder naming; review before production use."
    if lower.startswith(ACTIVE_CORE_PREFIXES):
        return "ACTIVE_CORE", "Referenced production architecture or tests."
    if lower.startswith(LEGACY_PREFIXES):
        return "LEGACY", "Legacy coexistence or archived material."
    if lower.startswith("outputs/") or lower.startswith("logs/"):
        return "TEMP", "Generated runtime output/log artifact."
    if lower.startswith("scrapers/lakehouse/bronze/") or lower.startswith("scrapers/lakehouse/silver/") or lower.startswith("scrapers/lakehouse/gold/"):
        return "EXPERIMENTAL", "Generated lakehouse snapshot/evidence artifact."
    if lower in {"app.py", "scraper.py", "queries.py", "db.py"}:
        return "LEGACY", "Root-level compatibility/legacy module."
    if lower.endswith((".md", ".txt", ".csv", ".jsonl", ".json")):
        return "UNKNOWN", "Data/documentation artifact; requires owner decision."
    return "UNKNOWN", "No automated safe classification."


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative_parts = set(path.relative_to(ROOT).parts)
        if relative_parts & UNKNOWN_IGNORE_DIRS:
            continue
        files.append(path)
    return files


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    items: list[InventoryItem] = []
    for path in iter_files():
        category, reason = classify(path)
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        items.append(InventoryItem(rel(path), size, category, reason))

    by_category: dict[str, list[InventoryItem]] = {}
    for item in items:
        by_category.setdefault(item.category, []).append(item)

    lines = [
        "# Workspace Audit",
        "",
        "Workspace: `C:\\\\Users\\\\SoporteTI\\\\Desktop\\\\SOFTWARE`",
        "",
        "## Summary",
        "",
    ]
    for category in sorted(by_category):
        category_items = by_category[category]
        total_size = sum(item.size for item in category_items)
        lines.append(f"- `{category}`: {len(category_items)} files, {total_size:,} bytes")

    lines.extend(
        [
            "",
            "## Productive Core",
            "",
            "- Backend oficial: `graduate_intelligence_platform/backend/app/main.py`",
            "- API routes: `graduate_intelligence_platform/backend/app/api.py`",
            "- Auth/JWT: `graduate_intelligence_platform/backend/app/auth.py`",
            "- Frontend oficial: `graduate_intelligence_platform/frontend`",
            "- Repositories/services compartidos: `backend/repositories`, `backend/services`",
            "- Microcurriculum engine: `microcurriculum_engine`",
            "- Labor matching: `build_labor_program_matches.py`, `diagnose_labor_matching.py`, `database/migrations/008_labor_matching_bridge.sql`",
            "- Contextual curriculum: `microcurriculum_context_engine.py`, `database/migrations/009_microcurriculum_program_context.sql`",
            "",
            "## High-Risk Areas",
            "",
            "- `.env.local` contains operational credentials and must remain ignored.",
            "- Root `app.py`, `templates/`, `static/` are Flask legacy fallback; archive only after explicit approval.",
            "- `scrapers/lakehouse/**` contains generated evidence snapshots; archive/compress by retention policy, not blindly.",
            "- `storage/test_microcurriculos/**` contains pilot institutional documents; do not delete.",
            "- `outputs/**` contains generated reports; safe to regenerate but useful for audit history.",
            "",
            "## Candidates By Category",
            "",
        ]
    )

    for category in sorted(by_category):
        lines.append(f"### {category}")
        lines.append("")
        for item in sorted(by_category[category], key=lambda entry: (-entry.size, entry.path))[:80]:
            lines.append(f"- `{item.path}` ({item.size:,} bytes): {item.reason}")
        if len(by_category[category]) > 80:
            lines.append(f"- ... {len(by_category[category]) - 80} more in JSON inventory")
        lines.append("")

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    JSON_OUTPUT.write_text(
        json.dumps([asdict(item) for item in items], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"files": len(items), "report": str(OUTPUT), "json": str(JSON_OUTPUT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

