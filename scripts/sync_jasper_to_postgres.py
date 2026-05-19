import csv
import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from io import StringIO
from urllib.parse import quote
from typing import Dict, Iterable, List, Tuple

import requests
import psycopg2
from psycopg2 import sql


DEFAULT_URL = "https://enelcom.sharepoint.com/sites/CarguedeInformacinTablerosCASA/Shared%20Documents/Archivos%20CASA%20-%20EMERGIA/2025/08.Ago/Jasper_31_08_2025.csv"
DEFAULT_SCHEMA = "BI1"
DEFAULT_TABLE = "jasper"
DEFAULT_GRAPH_SITE_HOSTNAME = "enelcom.sharepoint.com"
DEFAULT_GRAPH_SITE_PATH = "sites/CarguedeInformacinTablerosCASA"
DEFAULT_GRAPH_FILE_PATH = "Archivos CASA - EMERGIA/2025/08.Ago/Jasper_31_08_2025.csv"
DEFAULT_GRAPH_FOLDER_PATH = "Archivos CASA - EMERGIA/2025/08.Ago"
TARGET_COLUMNS = [
    "fecha",
    "hora",
    "nombre_agente",
    "id_cliente",
    "nombres_cliente",
    "primer_apellido_cliente",
    "segundo_apellido_cliente",
    "email_personal",
    "celular",
    "telefono_casa",
    "telefono_fijo",
    "solicitud",
    "subsolicitud_1",
    "subsolicitud_2",
    "subsolicitud_3",
    "subsolicitud_4",
    "canal_solicitud",
    "sede",
    "estado_solicitud",
    "numero_ticket",
    "servicio_efectivo",
    "servicio_completo",
    "justificacion_servicio",
    "escala",
    "mejora",
    "justificacion_mejora",
    "comentario",
    "seguimiento",
    "motivo",
    "tipo_gestion_motivo",
    "observaciones_caso",
]

SOURCE_TO_TARGET = {
    "fecha": "fecha",
    "hora": "hora",
    "nombre_agente": "nombre_agente",
    "identificacion": "id_cliente",
    "nombre_cliente": "nombres_cliente",
    "primer_apellido_cliente": "primer_apellido_cliente",
    "segundo_apellido_cliente": "segundo_apellido_cliente",
    "email_personal": "email_personal",
    "celular": "celular",
    "telefono_casa": "telefono_casa",
    "telefono_fijo": "telefono_fijo",
    "solicitud": "solicitud",
    "subsolicitud_1": "subsolicitud_1",
    "subsolicitud_2": "subsolicitud_2",
    "subsolicitud_3": "subsolicitud_3",
    "subsolicitud_4": "subsolicitud_4",
    "canal_solicitud": "canal_solicitud",
    "sede": "sede",
    "estado_solicitud": "estado_solicitud",
    "numero_de_ticket": "numero_ticket",
    "el_servicio_fue_efectivamente_presatdo": "servicio_efectivo",
    "servicio_fue_efectivamente_prestado": "servicio_efectivo",
    "servicio_fue_efectivamente_presatdo": "servicio_efectivo",
    "el_servicio_fue_prestado_de_manera_oportuna_y_completa": "servicio_completo",
    "el_servicio_fue_presatdo_de_manera_oportuna_y_completa": "servicio_completo",
    "porque": "justificacion_servicio",
    "porque_2": "justificacion_mejora",
    "por_que": "justificacion_mejora",
    "en_una_escala_de_1_a_5": "escala",
    "en_una_escala_de_1_a_5_siendo_5_muy_saisfecho_y_1_muy_insatisfecho": "escala",
    "que_le_mejoraria": "mejora",
    "desea_compartirnos_algun_comentario_adicional_sobre_su_experiencia_por_favor_registrelo_a_continuacion": "comentario",
    "seguimiento": "seguimiento",
    "motivo": "motivo",
    "tipo_gestion_motivo": "tipo_gestion_motivo",
    "observaciones_caso": "observaciones_caso",
}

TARGET_ALIASES = {
    "id_cliente": ["identificacion", "id_cliente", "numero_identificacion", "documento"],
    "nombres_cliente": ["nombre_cliente", "nombres_cliente", "nombres del cliente"],
    "numero_ticket": ["numero_de_ticket", "nro_ticket", "numero ticket", "numero_ticket"],
    "servicio_efectivo": ["servicio_fue_efectivamente_prestado", "el_servicio_fue_efectivamente_prestado", "servicio efectivo"],
    "servicio_completo": [
        "el_servicio_fue_presatdo_de_manera_oportuna_y_completa",
        "el_servicio_fue_prestado_de_manera_oportuna_y_completa",
        "servicio completo",
    ],
    "justificacion_servicio": ["porque", "por_que", "justificacion_servicio"],
    "justificacion_mejora": ["porque_2", "por_que", "por_que_2", "justificacion_mejora"],
    "escala": ["en_una_escala_de_1_a_5", "escala", "valoracion"],
    "mejora": ["que_le_mejoraria", "que le mejoraria", "mejora"],
    "comentario": [
        "desea_compartirnos_algun_comentario_adicional_sobre_su_experiencia_por_favor_registrelo_a_continuacion",
        "comentario",
        "comentarios",
    ],
    "seguimiento": ["seguimiento"],
    "motivo": ["motivo"],
    "tipo_gestion_motivo": ["tipo_gestion_motivo", "tipo gestion motivo"],
    "observaciones_caso": ["observaciones_caso", "observaciones caso"],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def normalize_identifier(value: str) -> str:
    value = (value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "column"


def unique_columns(columns: Iterable[str]) -> List[str]:
    seen = {}
    out = []
    for col in columns:
        base = normalize_identifier(col)
        name = base
        idx = 2
        while name in seen:
            name = f"{base}_{idx}"
            idx += 1
        seen[name] = True
        out.append(name)
    return out


def unique_normalized_columns(columns: Iterable[str]) -> List[str]:
    counts = {}
    out = []
    for col in columns:
        base = normalize_column_name(col)
        counts[base] = counts.get(base, 0) + 1
        out.append(base if counts[base] == 1 else f"{base}_{counts[base]}")
    return out


def normalize_column_name(value: str) -> str:
    return normalize_identifier(value).lower()


def map_row_to_target(row: Dict[str, str]) -> Dict[str, str]:
    prepared = {target: "" for target in TARGET_COLUMNS}
    for source_name, value in row.items():
        source_key = normalize_column_name(source_name)
        target = SOURCE_TO_TARGET.get(source_key)
        if target:
            prepared[target] = value
    for target, aliases in TARGET_ALIASES.items():
        if prepared.get(target):
            continue
        for alias in aliases:
            alias_key = normalize_column_name(alias)
            if alias_key in row and row[alias_key]:
                prepared[target] = row[alias_key]
                break
    return prepared


def parse_headers_json(raw: str) -> Dict[str, str]:
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("SHAREPOINT_HEADERS_JSON must be a JSON object")
    return {str(k): str(v) for k, v in data.items()}


def load_state(path: str) -> Dict[str, str]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_state(path: str, state: Dict[str, str]) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False, sort_keys=True)


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_csv(url: str, headers: Dict[str, str], state: Dict[str, str]) -> requests.Response:
    conditional_headers = dict(headers)
    if state.get("etag"):
        conditional_headers["If-None-Match"] = state["etag"]
    if state.get("last_modified"):
        conditional_headers["If-Modified-Since"] = state["last_modified"]

    response = requests.get(url, headers=conditional_headers, timeout=120)
    if response.status_code == 304:
        return response
    response.raise_for_status()
    return response


def decode_csv(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def parse_csv(content: bytes) -> Tuple[List[str], List[Dict[str, str]]]:
    text = decode_csv(content)
    sample = text[:4096]
    delimiter = ";"
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        if text.count(";") < text.count(","):
            delimiter = ","

    reader = csv.reader(StringIO(text), delimiter=delimiter)
    try:
        raw_headers = next(reader)
    except StopIteration as exc:
        raise ValueError("CSV file is empty") from exc

    if not raw_headers:
        raise ValueError("CSV file does not contain headers")

    original_fields = [((field or "").strip() or f"column_{idx + 1}") for idx, field in enumerate(raw_headers)]
    normalized_fields = unique_normalized_columns(original_fields)
    rows = []
    for row in reader:
        normalized_row = {}
        if not any((cell or "").strip() for cell in row):
            continue
        for idx, normalized in enumerate(normalized_fields):
            normalized_row[normalized] = (row[idx] if idx < len(row) else "").strip()
        rows.append(normalized_row)
    return normalized_fields, rows


def connect_postgres():
    dsn = env("POSTGRES_DSN")
    if dsn:
        return psycopg2.connect(dsn)

    host = env("POSTGRES_HOST")
    port = env("POSTGRES_PORT", "5432")
    dbname = env("POSTGRES_DBNAME")
    user = env("POSTGRES_USER")
    password = env("POSTGRES_PASSWORD")

    if not all([host, port, dbname, user, password]):
        raise ValueError(
            "Define POSTGRES_DSN or the individual variables POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DBNAME, POSTGRES_USER and POSTGRES_PASSWORD"
        )

    return psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)


def get_graph_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    response = requests.post(
        token_url,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": "https://graph.microsoft.com/.default",
        },
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise ValueError("Microsoft Graph token response did not include an access_token")
    return token


def download_csv_from_graph(
    tenant_id: str,
    client_id: str,
    client_secret: str,
    site_hostname: str,
    site_path: str,
    file_path: str,
) -> requests.Response:
    token = get_graph_token(tenant_id, client_id, client_secret)
    headers = {"Authorization": f"Bearer {token}"}

    site_url = f"https://graph.microsoft.com/v1.0/sites/{quote(site_hostname, safe='')}:/{site_path.lstrip('/')}"
    site_response = requests.get(site_url, headers=headers, timeout=120)
    site_response.raise_for_status()
    site_id = site_response.json().get("id")
    if not site_id:
        raise ValueError("Microsoft Graph site lookup did not return a site id")

    file_url = f"https://graph.microsoft.com/v1.0/sites/{quote(site_id, safe=',')}/drive/root:/{quote(file_path.lstrip('/'), safe='/')}:/content"
    response = requests.get(file_url, headers=headers, timeout=120)
    if response.status_code >= 400:
        response.raise_for_status()
    return response


def find_latest_jasper_in_graph_folder(
    tenant_id: str,
    client_id: str,
    client_secret: str,
    site_hostname: str,
    site_path: str,
    folder_path: str,
) -> Tuple[str, requests.Response]:
    token = get_graph_token(tenant_id, client_id, client_secret)
    headers = {"Authorization": f"Bearer {token}"}

    site_url = f"https://graph.microsoft.com/v1.0/sites/{quote(site_hostname, safe='')}:/{site_path.lstrip('/')}"
    site_response = requests.get(site_url, headers=headers, timeout=120)
    site_response.raise_for_status()
    site_id = site_response.json().get("id")
    if not site_id:
        raise ValueError("Microsoft Graph site lookup did not return a site id")

    folder_url = f"https://graph.microsoft.com/v1.0/sites/{quote(site_id, safe=',')}/drive/root:/{quote(folder_path.lstrip('/'), safe='/')}:/children"
    folder_response = requests.get(folder_url, headers=headers, timeout=120)
    folder_response.raise_for_status()
    items = folder_response.json().get("value", [])

    csv_items = []
    for item in items:
        name = item.get("name", "")
        if not name.lower().endswith(".csv"):
            continue
        if "jasper" not in name.lower():
            continue
        csv_items.append(item)

    if not csv_items:
        raise FileNotFoundError(f"No Jasper CSV files found in SharePoint folder: {folder_path}")

    csv_items.sort(key=lambda item: item.get("lastModifiedDateTime", ""), reverse=True)
    latest = csv_items[0]
    download_url = latest.get("@microsoft.graph.downloadUrl")
    if not download_url:
        raise ValueError("Graph did not return a download URL for the latest CSV")

    response = requests.get(download_url, timeout=120)
    if response.status_code >= 400:
        response.raise_for_status()
    return latest.get("name", ""), response


def ensure_schema(conn, schema_name: str) -> None:
    with conn.cursor() as cur:
        cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema_name)))


def ensure_table(conn, schema_name: str, table_name: str, columns: List[str]) -> None:
    with conn.cursor() as cur:
        create_columns = ", ".join([f"{col} TEXT" for col in columns])
        cur.execute(
            sql.SQL("CREATE TABLE IF NOT EXISTS {}.{} ({})").format(
                sql.Identifier(schema_name),
                sql.Identifier(table_name),
                sql.SQL(create_columns),
            )
        )

        cur.execute(
            sql.SQL(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s"
            ),
            [schema_name, table_name],
        )
        existing = {row[0] for row in cur.fetchall()}

        for col in columns:
            if col not in existing:
                cur.execute(
                    sql.SQL("ALTER TABLE {}.{} ADD COLUMN {} TEXT").format(
                        sql.Identifier(schema_name),
                        sql.Identifier(table_name),
                        sql.Identifier(col),
                    )
                )


def truncate_table(conn, schema_name: str, table_name: str) -> None:
    with conn.cursor() as cur:
        cur.execute(sql.SQL("TRUNCATE TABLE {}.{}").format(sql.Identifier(schema_name), sql.Identifier(table_name)))


def insert_rows(conn, schema_name: str, table_name: str, columns: List[str], rows: List[Dict[str, str]]) -> int:
    if not rows:
        return 0

    placeholders = ", ".join(["%s"] * len(columns))
    query = sql.SQL("INSERT INTO {}.{} ({}) VALUES ({})").format(
        sql.Identifier(schema_name),
        sql.Identifier(table_name),
        sql.SQL(", ").join(map(sql.Identifier, columns)),
        sql.SQL(placeholders),
    )

    values = []
    for row in rows:
        values.append([row.get(col, "") for col in columns])

    with conn.cursor() as cur:
        cur.executemany(query.as_string(conn), values)
    return len(rows)


def main() -> int:
    url = env("JASPER_CSV_URL", DEFAULT_URL)
    schema_name = env("POSTGRES_SCHEMA", DEFAULT_SCHEMA)
    table_name = env("POSTGRES_TABLE", DEFAULT_TABLE)
    state_file = env("SYNC_STATE_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "jasper_sync_state.json"))
    load_mode = env("LOAD_MODE", "replace").lower()
    headers = parse_headers_json(env("SHAREPOINT_HEADERS_JSON", "{}"))

    if load_mode not in {"replace", "append"}:
        raise ValueError("LOAD_MODE must be 'replace' or 'append'")

    graph_tenant_id = env("GRAPH_TENANT_ID")
    graph_client_id = env("GRAPH_CLIENT_ID")
    graph_client_secret = env("GRAPH_CLIENT_SECRET")
    graph_site_hostname = env("GRAPH_SITE_HOSTNAME", DEFAULT_GRAPH_SITE_HOSTNAME)
    graph_site_path = env("GRAPH_SITE_PATH", DEFAULT_GRAPH_SITE_PATH)
    graph_source_mode = env("GRAPH_SOURCE_MODE", "file").lower()
    graph_file_path = env("GRAPH_FILE_PATH", DEFAULT_GRAPH_FILE_PATH)
    graph_folder_path = env("GRAPH_FOLDER_PATH", DEFAULT_GRAPH_FOLDER_PATH)

    state = load_state(state_file)
    if graph_tenant_id and graph_client_id and graph_client_secret:
        if graph_source_mode == "folder":
            _, response = find_latest_jasper_in_graph_folder(
                graph_tenant_id,
                graph_client_id,
                graph_client_secret,
                graph_site_hostname,
                graph_site_path,
                graph_folder_path,
            )
        else:
            response = download_csv_from_graph(
                graph_tenant_id,
                graph_client_id,
                graph_client_secret,
                graph_site_hostname,
                graph_site_path,
                graph_file_path,
            )
    else:
        response = download_csv(url, headers, state)

    if response.status_code == 304:
        print(f"[{utc_now()}] No changes detected for {url}")
        return 0

    checksum = compute_sha256(response.content)
    if state.get("checksum") == checksum:
        print(f"[{utc_now()}] Content checksum unchanged for {url}")
        return 0

    parsed_columns, rows = parse_csv(response.content)
    if parsed_columns:
        print(f"[{utc_now()}] CSV columns detected: {', '.join(parsed_columns)}")
    columns = TARGET_COLUMNS
    prepared_rows = [map_row_to_target(row) for row in rows]

    conn = connect_postgres()
    try:
        ensure_schema(conn, schema_name)
        ensure_table(conn, schema_name, table_name, columns)
        if load_mode == "replace":
            truncate_table(conn, schema_name, table_name)
        inserted = insert_rows(conn, schema_name, table_name, columns, prepared_rows)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    new_state = {
        "url": url,
        "etag": response.headers.get("ETag", ""),
        "last_modified": response.headers.get("Last-Modified", ""),
        "checksum": checksum,
        "imported_at": utc_now(),
        "rows": str(inserted),
        "schema": schema_name,
        "table": table_name,
        "load_mode": load_mode,
    }
    save_state(state_file, new_state)

    print(f"[{new_state['imported_at']}] Imported {inserted} rows into {schema_name}.{table_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
