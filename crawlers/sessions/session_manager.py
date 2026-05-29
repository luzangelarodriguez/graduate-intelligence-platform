from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
LOCAL_SESSION_DIR = ROOT_DIR / ".local_sessions"


@dataclass(frozen=True)
class SessionManager:
    session_dir: Path = LOCAL_SESSION_DIR

    def session_path(self, source_name: str) -> Path:
        return self.session_dir / f"{source_name}_storage_state.json"

    def exists(self, source_name: str) -> bool:
        return self.session_path(source_name).exists()

    def ensure_dir(self) -> Path:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        return self.session_dir

    def safe_status(self, source_name: str) -> dict[str, str | bool]:
        path = self.session_path(source_name)
        try:
            safe_path = str(path.relative_to(ROOT_DIR))
        except ValueError:
            safe_path = str(path)
        return {
            "source_name": source_name,
            "exists": path.exists(),
            "path": safe_path,
        }

    def assert_exists(self, source_name: str) -> Path:
        path = self.session_path(source_name)
        if not path.exists():
            raise FileNotFoundError(f"Ejecuta primero scripts/{source_name}_manual_login.py")
        return path
