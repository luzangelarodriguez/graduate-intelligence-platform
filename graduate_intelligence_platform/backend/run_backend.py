from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import parse_qs, unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

print("1) Cargando motor...", flush=True)
from app.engine import InMemoryStore


print("2) Inicializando store...", flush=True)
store = InMemoryStore()


def json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "GraduateIntel/1.0"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def _set_headers(self, status: int = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def _send(self, payload: object, status: int = HTTPStatus.OK) -> None:
        self._set_headers(status)
        self.wfile.write(json_bytes(payload))

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._set_headers(HTTPStatus.NO_CONTENT)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            self._send({"message": "Graduate Intelligence & Employability Platform"})
            return
        if path == "/api/health":
            self._send({"status": "ok", "service": "graduate-intelligence"})
            return
        if path == "/api/bootstrap":
            self._send(store.bootstrap())
            return
        if path == "/api/dashboard/summary":
            self._send(store.dashboard())
            return
        if path == "/api/programs":
            self._send(store.list_programs())
            return
        if path == "/api/graduates":
            self._send(store.list_graduates())
            return
        if path == "/api/jobs":
            self._send(store.list_jobs())
            return
        if path == "/api/job-offers":
            self._send({"job_offers": store.list_job_offers()})
            return
        if path == "/api/events":
            self._send(store.list_events())
            return
        if path == "/api/metrics":
            self._send(store.dashboard())
            return
        if path == "/api/recommendations":
            query = parse_qs(urlparse(self.path).query)
            program_id = int((query.get("program_id") or [0])[0] or 0)
            self._send(store.recommend(program_id or 1))
            return
        if path.startswith("/api/programs/") and path.endswith("/market"):
            program_id = int(path.split("/")[3])
            self._send(store.get_program_market_report(program_id))
            return
        if path.startswith("/api/programs/") and path.endswith("/market/offers"):
            program_id = int(path.split("/")[3])
            self._send({"program_id": program_id, "offers": store.list_program_market_jobs(program_id)})
            return
        if path == "/api/audit/job-sources":
            self._send({"logs": store.job_sources_sync_log})
            return
        if path == "/api/skills/offers":
            query = parse_qs(urlparse(self.path).query)
            skill_name = query.get("skill", [""])[0]
            self._send({"skill_name": skill_name, "offers": store.list_skill_offers(skill_name)})
            return
        if path.startswith("/api/skills/") and path.endswith("/offers"):
            skill_name = unquote(path.split("/")[3])
            self._send({"skill_name": skill_name, "offers": store.list_skill_offers(skill_name)})
            return
        self._send({"detail": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        payload = self._read_json()
        try:
            if path == "/api/graduates":
                self._send(store.create_graduate(payload), HTTPStatus.CREATED)
                return
            if path == "/api/match/analyze":
                self._send(store.analyze_job_text(str(payload.get("text", ""))))
                return
            if path == "/api/simulate":
                self._send(
                    store.simulate(
                        int(payload.get("program_id") or 0),
                        payload.get("add_skills") or [],
                        payload.get("remove_skills") or [],
                    )
                )
                return
            if path == "/api/surveys/micro":
                self._send(store.micro_survey_for_graduate(int(payload.get("graduate_id") or 0)))
                return
            if path.startswith("/api/programs/") and path.endswith("/market/recompute"):
                program_id = int(path.split("/")[3])
                self._send(store.recompute_program_market(program_id))
                return
        except KeyError as exc:
            self._send({"detail": str(exc)}, HTTPStatus.NOT_FOUND)
            return
        except Exception as exc:  # pragma: no cover - defensive
            self._send({"detail": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._send({"detail": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_PATCH(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        payload = self._read_json()
        if path.startswith("/api/graduates/"):
            try:
                graduate_id = int(path.rsplit("/", 1)[-1])
                self._send(store.update_graduate(graduate_id, payload))
                return
            except KeyError as exc:
                self._send({"detail": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            except Exception as exc:  # pragma: no cover - defensive
                self._send({"detail": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
        self._send({"detail": "Not found"}, HTTPStatus.NOT_FOUND)


def main() -> None:
    print("3) Creando servidor HTTP...", flush=True)
    server = ThreadingHTTPServer(("127.0.0.1", 8000), ApiHandler)
    print("4) Servidor activo en http://127.0.0.1:8010", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
