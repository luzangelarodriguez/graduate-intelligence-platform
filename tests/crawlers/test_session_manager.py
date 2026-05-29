from pathlib import Path

from crawlers.sessions.session_manager import SessionManager


def test_session_manager_reports_without_printing_cookie_content(tmp_path: Path) -> None:
    manager = SessionManager(session_dir=tmp_path)
    path = manager.session_path("linkedin")
    path.write_text('{"cookies":[{"value":"secret-cookie"}]}', encoding="utf-8")

    status = manager.safe_status("linkedin")

    assert status["exists"] is True
    assert "secret-cookie" not in str(status)
    assert str(status["path"]).endswith("linkedin_storage_state.json")
