from __future__ import annotations

import html
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

REPORT_PATH = ROOT_DIR / "outputs" / "indeed_publisher_plugin_integration_report.md"
PLUGIN_SCRIPT_URL = "https://plugins.indeed.com/publisher-plugin/main.js"
DEFAULT_PLUGIN_SEARCH = "Data Analyst OR Business Intelligence OR Power BI OR SQL OR Analytics"
DEFAULT_PLUGIN_WHERE = "Colombia"


@dataclass(frozen=True)
class IndeedPublisherPluginConfig:
    plugin_type: str
    partner_app_id: str
    placement_id: str
    search_limit: int
    search_what: str
    search_where: str
    search_job_types: str
    search_occupations: str
    source_status: str
    validation_errors: list[str]

    @property
    def is_ready(self) -> bool:
        return self.source_status == "ready" and not self.validation_errors


def _load_environment() -> None:
    for name in (".env.local", ".env", ".env.development"):
        path = ROOT_DIR / name
        if path.exists():
            load_dotenv(path, override=False)


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def load_publisher_plugin_config() -> IndeedPublisherPluginConfig:
    _load_environment()
    search_limit = _int_env("INDEED_PUBLISHER_SEARCH_LIMIT", 10)
    partner_app_id = os.getenv("INDEED_PUBLISHER_PARTNER_APP_ID", "")
    placement_id = os.getenv("INDEED_PUBLISHER_PLACEMENT_ID", "")
    search_what = os.getenv("INDEED_PUBLISHER_SEARCH_WHAT", DEFAULT_PLUGIN_SEARCH)
    search_where = os.getenv("INDEED_PUBLISHER_SEARCH_WHERE", DEFAULT_PLUGIN_WHERE)
    errors: list[str] = []
    if not partner_app_id:
        errors.append("missing_partner_app_id")
    if not placement_id:
        errors.append("missing_placement_id")
    if search_limit < 1 or search_limit > 20:
        errors.append("invalid_search_limit_must_be_1_to_20")
    if not search_what and not search_where:
        errors.append("missing_search_what_or_where")
    source_status = "credentials_missing" if any(item in errors for item in {"missing_partner_app_id", "missing_placement_id"}) else "ready"
    return IndeedPublisherPluginConfig(
        plugin_type="job-search",
        partner_app_id=partner_app_id,
        placement_id=placement_id,
        search_limit=min(max(search_limit, 1), 20),
        search_what=search_what,
        search_where=search_where,
        search_job_types=os.getenv("INDEED_PUBLISHER_SEARCH_JOB_TYPES", ""),
        search_occupations=os.getenv("INDEED_PUBLISHER_SEARCH_OCCUPATIONS", ""),
        source_status=source_status,
        validation_errors=errors,
    )


def plugin_search_query(config: IndeedPublisherPluginConfig | None = None) -> str:
    config = config or load_publisher_plugin_config()
    return config.search_what or DEFAULT_PLUGIN_SEARCH


def render_plugin_html(config: IndeedPublisherPluginConfig | None = None, *, root_id: str = "indeed-plugin-root") -> str:
    config = config or load_publisher_plugin_config()
    attributes = {
        "data-indeed-plugin-type": config.plugin_type,
        "data-indeed-partner-app-id": config.partner_app_id,
        "data-indeed-placement-id": config.placement_id,
        "data-indeed-search-limit": str(config.search_limit),
        "data-indeed-search-what": config.search_what,
        "data-indeed-search-where": config.search_where,
        "data-indeed-search-job-types": config.search_job_types,
        "data-indeed-search-occupations": config.search_occupations,
    }
    attribute_text = "\n    ".join(
        f'{name}="{html.escape(value, quote=True)}"'
        for name, value in attributes.items()
        if value
    )
    return f"""<script src="{PLUGIN_SCRIPT_URL}" crossorigin defer></script>
<div id="{html.escape(root_id, quote=True)}"
    {attribute_text}></div>
<script>
  document.getElementById("{html.escape(root_id, quote=True)}")?.addEventListener("indeed-plugin-event", (event) => {{
    const detail = event.detail || {{}};
    if (detail.type === "load") {{
      console.info("Indeed publisher plugin load", {{ success: Boolean(detail.payload && detail.payload.success) }});
    }}
  }});
</script>"""


def write_publisher_plugin_report(config: IndeedPublisherPluginConfig | None = None) -> dict[str, Any]:
    config = config or load_publisher_plugin_config()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(config)
    payload["plugin_script_url"] = PLUGIN_SCRIPT_URL
    payload["query_used_for_api_extraction"] = plugin_search_query(config)
    lines = [
        "# Indeed Publisher Plugin Integration Report",
        "",
        "La documentacion oficial describe un widget frontend de busqueda laboral, no una API de extraccion.",
        "El pipeline usa estos criterios del plugin como contrato de busqueda y mantiene la extraccion estructurada en Partner API.",
        "",
        f"- Source status: {config.source_status}",
        f"- Plugin type: {config.plugin_type}",
        f"- Search limit: {config.search_limit}",
        f"- Search what: {config.search_what}",
        f"- Search where: {config.search_where}",
        f"- Validation errors: {', '.join(config.validation_errors) or 'none'}",
        "",
        "## Embed HTML sugerido",
        "",
        "```html",
        render_plugin_html(config),
        "```",
        "",
        "## JSON",
        "",
        "```json",
        json.dumps(payload, indent=2, ensure_ascii=False),
        "```",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(write_publisher_plugin_report(), indent=2, ensure_ascii=False))
