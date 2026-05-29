from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SESSION_DIR = ROOT_DIR / ".local_sessions"
STORAGE_STATE_PATH = SESSION_DIR / "linkedin_storage_state.json"


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        print("Playwright no esta disponible. Instala playwright antes de ejecutar este script.")
        raise SystemExit(1) from exc

    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    print("Se abrira LinkedIn en un navegador visible.")
    print("Haz login manualmente. No escribas usuario ni contraseña en esta consola.")
    print("Cuando termines el login y veas LinkedIn cargado, vuelve aqui y presiona ENTER.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1366, "height": 850},
            locale="es-CO",
        )
        page = context.new_page()
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=60000)
        input("Presiona ENTER para guardar la sesion local de LinkedIn...")
        context.storage_state(path=str(STORAGE_STATE_PATH))
        browser.close()

    if not STORAGE_STATE_PATH.exists():
        print("No se pudo crear .local_sessions/linkedin_storage_state.json")
        return 1
    print("Sesion guardada en .local_sessions/linkedin_storage_state.json")
    print("El contenido del storage_state no se imprime por seguridad.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
