from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from playwright.async_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


SOURCE_URL = "https://hecaa.mineducacion.gov.co/consultaspublicas/programas"
SOURCE_NAME = "HECAA - Ministerio de Educación Nacional"

LIST_COLUMNS = [
    "nombre_ies",
    "codigo_ies",
    "ies_padre",
    "registro_unico",
    "codigo_snies_programa",
    "nombre_programa",
    "estado_programa",
    "nivel_academico",
    "modalidad",
    "reconocimiento_ministerio",
]

DB_COLUMNS = [
    *LIST_COLUMNS,
    "municipio",
    "departamento",
    "metodologia",
    "area_conocimiento",
    "nucleo_basico_conocimiento",
    "creditos",
    "duracion",
    "periodicidad_admision",
    "fecha_registro",
    "fecha_vencimiento",
    "url_detalle",
    "raw_html",
    "timestamp_extraccion",
    "fuente",
]

FIELD_ALIASES = {
    "codigo institucion padre": "ies_padre",
    "codigo institucion": "codigo_ies",
    "nombre institucion": "nombre_ies",
    "nombre ies": "nombre_ies",
    "institucion de educacion superior": "nombre_ies",
    "codigo ies": "codigo_ies",
    "ies padre": "ies_padre",
    "registro unico": "registro_unico",
    "registro unico programa": "registro_unico",
    "codigo snies del programa": "codigo_snies_programa",
    "codigo snies programa": "codigo_snies_programa",
    "codigo snies": "codigo_snies_programa",
    "nombre del programa": "nombre_programa",
    "nombre programa": "nombre_programa",
    "estado programa": "estado_programa",
    "estado del programa": "estado_programa",
    "nivel academico": "nivel_academico",
    "nivel de formacion": "nivel_academico",
    "modalidad": "modalidad",
    "metodologia": "metodologia",
    "reconocimiento del ministerio": "reconocimiento_ministerio",
    "reconocimiento ministerio": "reconocimiento_ministerio",
    "municipio oferta programa": "municipio",
    "municipio": "municipio",
    "departamento oferta programa": "departamento",
    "departamento": "departamento",
    "area conocimiento": "area_conocimiento",
    "area de conocimiento": "area_conocimiento",
    "nucleo basico conocimiento": "nucleo_basico_conocimiento",
    "nucleo basico del conocimiento": "nucleo_basico_conocimiento",
    "numero creditos": "creditos",
    "creditos": "creditos",
    "numero periodos de duracion": "duracion",
    "duracion": "duracion",
    "periodicidad admisiones": "periodicidad_admision",
    "periodicidad admision": "periodicidad_admision",
    "periodicidad de admision": "periodicidad_admision",
    "fecha de registro en snies": "fecha_registro",
    "fecha registro": "fecha_registro",
    "fecha de registro": "fecha_registro",
    "fecha vencimiento": "fecha_vencimiento",
    "fecha de vencimiento": "fecha_vencimiento",
}


@dataclass
class ScraperConfig:
    headless: bool
    include_html: bool
    skip_db: bool
    max_pages: int | None
    limit_records: int | None
    timeout_ms: int
    max_retries: int
    slow_mo_ms: int
    output_dir: Path
    log_dir: Path
    screenshot_dir: Path
    ddl_path: Path


def setup_logging(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"mineducacion_scraper_{datetime.now():%Y%m%d_%H%M%S}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
    )
    return log_path


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text_value = re.sub(r"\s+", " ", str(value)).strip()
    return text_value


def normalize_label(value: Any) -> str:
    value = normalize_text(value).lower()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return normalize_text(value)


def canonical_field(label: str) -> str | None:
    normalized = normalize_label(label)
    if normalized in FIELD_ALIASES:
        return FIELD_ALIASES[normalized]
    if normalized.endswith("del programa") and "nombre" in normalized:
        return "nombre_programa"
    return None


def parse_int(value: Any) -> int | None:
    text_value = normalize_text(value)
    if not text_value:
        return None
    match = re.search(r"\d+", text_value.replace(".", "").replace(",", ""))
    return int(match.group(0)) if match else None


def parse_date(value: Any) -> str | None:
    text_value = normalize_text(value)
    if not text_value:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(text_value[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def sanitize_record(record: dict[str, Any], include_html: bool) -> dict[str, Any]:
    cleaned = {column: normalize_text(record.get(column)) or None for column in DB_COLUMNS}
    cleaned["creditos"] = parse_int(cleaned.get("creditos"))
    cleaned["fecha_registro"] = parse_date(cleaned.get("fecha_registro"))
    cleaned["fecha_vencimiento"] = parse_date(cleaned.get("fecha_vencimiento"))
    cleaned["timestamp_extraccion"] = record.get("timestamp_extraccion") or datetime.now(timezone.utc).isoformat()
    cleaned["fuente"] = SOURCE_NAME
    if not include_html:
        cleaned["raw_html"] = None
    return cleaned


def records_from_dataframe(df: pd.DataFrame, include_html: bool) -> list[dict[str, Any]]:
    mapped_columns: dict[str, str] = {}
    used_fields: set[str] = set()
    for column in df.columns:
        field = canonical_field(str(column))
        if field and field not in used_fields:
            mapped_columns[column] = field
            used_fields.add(field)
    normalized = df.rename(columns=mapped_columns)
    records = []
    for _, row in normalized.iterrows():
        record = {column: row.get(column) for column in DB_COLUMNS if column in normalized.columns}
        record["timestamp_extraccion"] = datetime.now(timezone.utc).isoformat()
        record["fuente"] = SOURCE_NAME
        record["url_detalle"] = record.get("url_detalle") or SOURCE_URL
        cleaned = sanitize_record(record, include_html)
        if normalize_label(cleaned.get("estado_programa")) == "activo" and normalize_label(cleaned.get("modalidad")) == "virtual":
            records.append(cleaned)
    return records


def db_url_from_env() -> str:
    sslmode = os.getenv("DB_SSLMODE", "prefer")
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "postgres")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}?sslmode={sslmode}"


def create_db_engine() -> Engine:
    return create_engine(db_url_from_env(), pool_pre_ping=True, pool_size=5, max_overflow=5)


def ensure_schema(engine: Engine, ddl_path: Path) -> None:
    ddl = ddl_path.read_text(encoding="utf-8")
    with engine.begin() as connection:
        connection.execute(text(ddl))


def upsert_records(engine: Engine, records: list[dict[str, Any]]) -> int:
    if not records:
        return 0
    insert_sql = text(
        """
        INSERT INTO public.mineducacion_programas_virtuales (
            nombre_ies, codigo_ies, ies_padre, registro_unico, codigo_snies_programa,
            nombre_programa, estado_programa, nivel_academico, modalidad,
            reconocimiento_ministerio, municipio, departamento, metodologia,
            area_conocimiento, nucleo_basico_conocimiento, creditos, duracion,
            periodicidad_admision, fecha_registro, fecha_vencimiento, url_detalle,
            raw_html, timestamp_extraccion, fuente
        )
        VALUES (
            :nombre_ies, :codigo_ies, :ies_padre, :registro_unico, :codigo_snies_programa,
            :nombre_programa, :estado_programa, :nivel_academico, :modalidad,
            :reconocimiento_ministerio, :municipio, :departamento, :metodologia,
            :area_conocimiento, :nucleo_basico_conocimiento, :creditos, :duracion,
            :periodicidad_admision, :fecha_registro, :fecha_vencimiento, :url_detalle,
            :raw_html, :timestamp_extraccion, :fuente
        )
        ON CONFLICT (codigo_snies_programa) DO UPDATE SET
            nombre_ies = EXCLUDED.nombre_ies,
            codigo_ies = EXCLUDED.codigo_ies,
            ies_padre = EXCLUDED.ies_padre,
            registro_unico = EXCLUDED.registro_unico,
            nombre_programa = EXCLUDED.nombre_programa,
            estado_programa = EXCLUDED.estado_programa,
            nivel_academico = EXCLUDED.nivel_academico,
            modalidad = EXCLUDED.modalidad,
            reconocimiento_ministerio = EXCLUDED.reconocimiento_ministerio,
            municipio = EXCLUDED.municipio,
            departamento = EXCLUDED.departamento,
            metodologia = EXCLUDED.metodologia,
            area_conocimiento = EXCLUDED.area_conocimiento,
            nucleo_basico_conocimiento = EXCLUDED.nucleo_basico_conocimiento,
            creditos = EXCLUDED.creditos,
            duracion = EXCLUDED.duracion,
            periodicidad_admision = EXCLUDED.periodicidad_admision,
            fecha_registro = EXCLUDED.fecha_registro,
            fecha_vencimiento = EXCLUDED.fecha_vencimiento,
            url_detalle = EXCLUDED.url_detalle,
            raw_html = COALESCE(EXCLUDED.raw_html, public.mineducacion_programas_virtuales.raw_html),
            timestamp_extraccion = EXCLUDED.timestamp_extraccion,
            fuente = EXCLUDED.fuente,
            updated_at = NOW()
        """
    )
    with engine.begin() as connection:
        connection.execute(insert_sql, records)
    return len(records)


async def safe_screenshot(page: Page, config: ScraperConfig, name: str) -> None:
    config.screenshot_dir.mkdir(parents=True, exist_ok=True)
    path = config.screenshot_dir / f"{name}_{datetime.now():%Y%m%d_%H%M%S}.png"
    try:
        await page.screenshot(path=str(path), full_page=True)
        logging.info("Screenshot de diagnóstico guardado: %s", path)
    except Exception as exc:
        logging.warning("No fue posible guardar screenshot: %s", exc)


async def wait_for_results(page: Page, timeout_ms: int) -> None:
    await page.wait_for_load_state("networkidle", timeout=timeout_ms)
    await page.wait_for_selector("table, [role='table'], text=/Visualizando/i", timeout=timeout_ms)


async def select_option_by_label(page: Page, label_patterns: list[str], option_pattern: str) -> bool:
    option_regex = re.compile(option_pattern, re.I)
    for pattern in label_patterns:
        label = page.get_by_text(re.compile(pattern, re.I)).first
        try:
            await label.wait_for(timeout=2500)
        except PlaywrightTimeoutError:
            continue

        for xpath in [
            "xpath=following::select[1]",
            "xpath=ancestor::*[self::div or self::section or self::fieldset][1]//select[1]",
        ]:
            try:
                select = label.locator(xpath).first
                await select.wait_for(timeout=1500)
                options = await select.locator("option").all()
                for option in options:
                    text_value = await option.inner_text()
                    if option_regex.search(text_value):
                        await select.select_option(label=text_value)
                        logging.info("Filtro aplicado: %s = %s", pattern, text_value)
                        return True
            except Exception:
                pass

        try:
            control = label.locator("xpath=following::*[self::button or @role='combobox' or contains(@class,'select')][1]").first
            await control.click(timeout=1500)
            await page.get_by_text(option_regex).first.click(timeout=2500)
            logging.info("Filtro aplicado con control dinámico: %s = %s", pattern, option_pattern)
            return True
        except Exception:
            pass
    return False


async def apply_filters(page: Page, config: ScraperConfig) -> None:
    state_ok = await select_option_by_label(page, [r"Estado del Programa", r"Estado Programa"], r"^Activo")
    modality_ok = await select_option_by_label(page, [r"Modalidad"], r"^Virtual\s*(\(|$)")
    if not state_ok:
        logging.warning("No se pudo confirmar filtro Estado programa=Activo; el scraper validará por datos.")
    if not modality_ok:
        logging.warning("No se pudo confirmar filtro Modalidad=Virtual; el scraper validará por datos.")

    try:
        visible_rows = await extract_listing_rows(page)
        if any(
            normalize_label(row.get("estado_programa")) == "activo"
            and normalize_label(row.get("modalidad")) == "virtual"
            for row in visible_rows
        ):
            logging.info("La tabla ya refleja filtros Activo + Virtual; se continúa sin forzar búsqueda adicional.")
            return
    except Exception:
        pass

    search_buttons = [
        page.get_by_role("button", name=re.compile(r"Buscar|Consultar|Filtrar", re.I)).last,
        page.get_by_text(re.compile(r"^Buscar$", re.I)).last,
        page.locator("input[type='submit'][value*='Buscar'], button:has-text('Buscar')").last,
    ]
    for button in search_buttons:
        try:
            await button.click(timeout=3000)
            try:
                await wait_for_results(page, config.timeout_ms)
            except PlaywrightTimeoutError:
                logging.warning("La búsqueda fue enviada, pero el portal tardó más de lo esperado en estabilizarse.")
            logging.info("Búsqueda ejecutada en portal HECAA.")
            return
        except Exception:
            continue
    raise RuntimeError("No se encontró o no respondió el botón de búsqueda.")


async def try_download_export(page: Page, config: ScraperConfig) -> list[dict[str, Any]]:
    download_button = page.get_by_text(re.compile(r"Descargar programas", re.I)).first
    try:
        await download_button.wait_for(timeout=5000)
    except PlaywrightTimeoutError:
        return []

    config.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        async with page.expect_download(timeout=config.timeout_ms) as download_info:
            await download_button.click(timeout=5000)
        download = await download_info.value
        suffix = Path(download.suggested_filename).suffix or ".xlsx"
        raw_path = config.output_dir / f"mineducacion_programas_export_{datetime.now():%Y%m%d_%H%M%S}{suffix}"
        await download.save_as(str(raw_path))
        logging.info("Export oficial HECAA descargado: %s", raw_path)

        if raw_path.suffix.lower() in {".xlsx", ".xls"}:
            df = pd.read_excel(raw_path)
        else:
            df = pd.read_csv(raw_path, sep=None, engine="python", encoding="utf-8-sig")
        records = records_from_dataframe(df, config.include_html)
        logging.info("Registros válidos desde export oficial HECAA: %s", len(records))
        return records
    except Exception as exc:
        logging.warning("No se pudo usar descarga oficial HECAA; se usará paginación visual. Motivo: %s", exc)
        return []


async def table_headers(page: Page) -> list[str]:
    headers = []
    for selector in ["table:visible thead th", "table:visible [role='columnheader']"]:
        try:
            values = [normalize_text(v) for v in await page.locator(selector).all_inner_texts()]
            headers = [v for v in values if v]
            if headers:
                return headers
        except Exception:
            pass
    return [
        "Nombre IES",
        "Código IES",
        "IES padre",
        "Registro único",
        "Código SNIES programa",
        "Nombre programa",
        "Estado programa",
        "Nivel académico",
        "Modalidad",
        "Reconocimiento del Ministerio",
    ]


async def extract_listing_rows(page: Page) -> list[dict[str, Any]]:
    headers = await table_headers(page)
    canonical_headers = [canonical_field(header) for header in headers]
    rows: list[dict[str, Any]] = []
    row_locator = page.locator("table:visible tbody tr").filter(has_not=page.locator("th"))
    count = await row_locator.count()
    for index in range(count):
        row = row_locator.nth(index)
        cells = [normalize_text(value) for value in await row.locator("td, [role='cell']").all_inner_texts()]
        if len(cells) < 5:
            continue
        record: dict[str, Any] = {}
        for cell_index, cell_value in enumerate(cells):
            field = canonical_headers[cell_index] if cell_index < len(canonical_headers) else None
            if field:
                record[field] = cell_value
        if not record.get("codigo_snies_programa") and len(cells) >= len(LIST_COLUMNS):
            record.update(dict(zip(LIST_COLUMNS, cells[: len(LIST_COLUMNS)])))
        detail_url = await extract_detail_url_from_row(row, page)
        if detail_url:
            record["url_detalle"] = detail_url
        if record.get("codigo_snies_programa") or record.get("nombre_programa"):
            rows.append(record)
    return rows


async def extract_detail_url_from_row(row: Any, page: Page) -> str | None:
    for selector in ["a[href]", "button", "[role='button']"]:
        try:
            locator = row.locator(selector).first
            if await locator.count() == 0:
                continue
            href = await locator.get_attribute("href")
            if href and href.strip() not in {"#", "javascript:void(0)", "javascript:void(0);"}:
                return page.url.rsplit("/", 1)[0] + "/" + href if href.startswith("/") else href
        except Exception:
            continue
    return None


async def extract_key_value_pairs(page: Page) -> dict[str, Any]:
    pairs: dict[str, Any] = {}
    scripts = [
        """
        () => {
          const out = [];
          document.querySelectorAll('tr').forEach(tr => {
            const cells = Array.from(tr.querySelectorAll('th,td')).map(td => td.innerText.trim()).filter(Boolean);
            if (cells.length >= 2) out.push([cells[0], cells.slice(1).join(' ')]);
          });
          document.querySelectorAll('dt').forEach(dt => {
            const dd = dt.nextElementSibling;
            if (dd) out.push([dt.innerText.trim(), dd.innerText.trim()]);
          });
          document.querySelectorAll('label').forEach(label => {
            const root = label.closest('.form-group, .row, div') || label.parentElement;
            if (root) {
              const text = root.innerText.replace(label.innerText, '').trim();
              if (text) out.push([label.innerText.trim(), text]);
            }
          });
          return out;
        }
        """
    ]
    for script in scripts:
        for label, value in await page.evaluate(script):
            field = canonical_field(label)
            if field and value and not pairs.get(field):
                pairs[field] = normalize_text(value)
    return pairs


async def enrich_with_detail(context: BrowserContext, row: dict[str, Any], config: ScraperConfig) -> dict[str, Any]:
    detail_url = row.get("url_detalle")
    if not detail_url:
        return row
    page = await context.new_page()
    try:
        await page.goto(detail_url, wait_until="networkidle", timeout=config.timeout_ms)
        detail = await extract_key_value_pairs(page)
        row.update({key: value for key, value in detail.items() if value})
        if config.include_html:
            row["raw_html"] = await page.content()
    except Exception as exc:
        logging.warning("No se pudo extraer detalle %s: %s", detail_url, exc)
        await safe_screenshot(page, config, "hecaa_detail_error")
    finally:
        await page.close()
    return row


async def go_next_page(page: Page, timeout_ms: int) -> bool:
    selectors = [
        "a.paginate_button.next:not(.disabled)",
        "button:has-text('Siguiente'):not([disabled])",
        "a:has-text('Siguiente')",
        "button[aria-label*='iguiente']",
        "a[aria-label*='iguiente']",
        "button:has-text('>')",
        "a:has-text('>')",
        "button:has-text('»')",
        "a:has-text('»')",
    ]
    for selector in selectors:
        try:
            next_button = page.locator(selector).last
            if await next_button.count() == 0:
                continue
            disabled = await next_button.get_attribute("disabled")
            classes = await next_button.get_attribute("class") or ""
            if disabled is not None or "disabled" in classes.lower():
                continue
            await next_button.click(timeout=2500)
            await page.wait_for_load_state("networkidle", timeout=timeout_ms)
            return True
        except Exception:
            continue
    return False


def attach_xhr_capture(page: Page, output_dir: Path) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    async def capture_response(response: Any) -> None:
        content_type = response.headers.get("content-type", "")
        url = response.url
        if not any(token in content_type.lower() for token in ["json", "csv", "excel", "octet"]):
            return
        if "hecaa" not in url.lower() and "mineducacion" not in url.lower():
            return
        item = {"url": url, "status": response.status, "content_type": content_type}
        try:
            if "json" in content_type.lower():
                payload = await response.json()
                item["sample"] = payload if isinstance(payload, dict) else payload[:2]
        except Exception:
            pass
        candidates.append(item)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"mineducacion_xhr_candidates_{datetime.now():%Y%m%d}.json"
        path.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")

    page.on("response", lambda response: asyncio.create_task(capture_response(response)))
    return candidates


async def scrape_programs(config: ScraperConfig) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=config.headless, slow_mo=config.slow_mo_ms)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 1000},
            user_agent="Mozilla/5.0 HECAA-DataPipeline/1.0",
        )
        page = await context.new_page()
        xhr_candidates = attach_xhr_capture(page, config.output_dir)
        try:
            await page.goto(SOURCE_URL, wait_until="networkidle", timeout=config.timeout_ms)
            await apply_filters(page, config)
            downloaded_records = await try_download_export(page, config)
            if downloaded_records:
                logging.info("Extracción completada usando export oficial HECAA.")
                return downloaded_records[: config.limit_records] if config.limit_records else downloaded_records
            page_number = 1
            while True:
                logging.info("Extrayendo página de resultados %s", page_number)
                page_rows = await extract_listing_rows(page)
                logging.info("Registros visibles en página %s: %s", page_number, len(page_rows))
                for row in page_rows:
                    row["timestamp_extraccion"] = datetime.now(timezone.utc).isoformat()
                    row["fuente"] = SOURCE_NAME
                    row["url_detalle"] = row.get("url_detalle") or page.url
                    if normalize_label(row.get("estado_programa")) != "activo":
                        continue
                    if normalize_label(row.get("modalidad")) != "virtual":
                        continue
                    key = row.get("codigo_snies_programa") or row.get("registro_unico") or row.get("nombre_programa")
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    row = await enrich_with_detail(context, row, config)
                    records.append(sanitize_record(row, config.include_html))
                    if config.limit_records and len(records) >= config.limit_records:
                        logging.info("Límite de registros alcanzado: %s", config.limit_records)
                        return records
                if config.max_pages and page_number >= config.max_pages:
                    break
                has_next = await go_next_page(page, config.timeout_ms)
                if not has_next:
                    break
                page_number += 1
            logging.info("Candidatos XHR detectados: %s", len(xhr_candidates))
        except Exception:
            await safe_screenshot(page, config, "hecaa_scraper_error")
            raise
        finally:
            await context.close()
            await browser.close()
    return records


async def run_with_retries(config: ScraperConfig) -> list[dict[str, Any]]:
    last_exc: Exception | None = None
    for attempt in range(1, config.max_retries + 1):
        try:
            logging.info("Intento de extracción %s/%s", attempt, config.max_retries)
            return await scrape_programs(config)
        except Exception as exc:
            last_exc = exc
            logging.exception("Intento %s falló: %s", attempt, exc)
            await asyncio.sleep(min(20, attempt * 5))
    raise RuntimeError(f"Extracción fallida tras {config.max_retries} intentos") from last_exc


def export_csv(records: list[dict[str, Any]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"mineducacion_programas_virtuales_{datetime.now():%Y%m%d_%H%M%S}.csv"
    pd.DataFrame(records, columns=DB_COLUMNS).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scraper HECAA: programas activos virtuales del MEN Colombia.")
    parser.add_argument("--headed", action="store_true", help="Ejecuta navegador visible para diagnóstico.")
    parser.add_argument("--include-html", action="store_true", help="Guarda HTML raw del detalle cuando exista.")
    parser.add_argument("--skip-db", action="store_true", help="Solo exporta CSV; no escribe PostgreSQL.")
    parser.add_argument("--max-pages", type=int, default=None, help="Límite de páginas para pruebas.")
    parser.add_argument("--limit-records", type=int, default=None, help="Límite de registros para pruebas.")
    parser.add_argument("--timeout-ms", type=int, default=int(os.getenv("HECAA_TIMEOUT_MS", "45000")))
    parser.add_argument("--max-retries", type=int, default=int(os.getenv("HECAA_MAX_RETRIES", "3")))
    parser.add_argument("--slow-mo-ms", type=int, default=0)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--log-dir", type=Path, default=Path("logs"))
    parser.add_argument("--screenshot-dir", type=Path, default=Path("logs/screenshots"))
    parser.add_argument("--ddl-path", type=Path, default=Path("database/mineducacion_programas_virtuales.sql"))
    return parser


def main() -> None:
    if Path(".env").exists():
        load_dotenv(".env")
    elif Path(".env.development").exists():
        load_dotenv(".env.development")
    else:
        load_dotenv()
    args = build_arg_parser().parse_args()
    config = ScraperConfig(
        headless=not args.headed and os.getenv("HECAA_HEADLESS", "true").lower() != "false",
        include_html=args.include_html or os.getenv("HECAA_INCLUDE_RAW_HTML", "false").lower() == "true",
        skip_db=args.skip_db,
        max_pages=args.max_pages,
        limit_records=args.limit_records,
        timeout_ms=args.timeout_ms,
        max_retries=args.max_retries,
        slow_mo_ms=args.slow_mo_ms,
        output_dir=args.output_dir,
        log_dir=args.log_dir,
        screenshot_dir=args.screenshot_dir,
        ddl_path=args.ddl_path,
    )
    log_path = setup_logging(config.log_dir)
    logging.info("Log activo: %s", log_path)
    records = asyncio.run(run_with_retries(config))
    csv_path = export_csv(records, config.output_dir)
    logging.info("CSV generado: %s (%s registros)", csv_path, len(records))
    if not config.skip_db:
        engine = create_db_engine()
        ensure_schema(engine, config.ddl_path)
        upserted = upsert_records(engine, records)
        logging.info("UPSERT PostgreSQL completado: %s registros", upserted)
    else:
        logging.info("Carga PostgreSQL omitida por --skip-db")


if __name__ == "__main__":
    main()
