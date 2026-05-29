from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from api import auth
from api.main import app


def _fake_user() -> auth.AuthenticatedUser:
    return auth.AuthenticatedUser(
        id=7,
        email="admin@example.com",
        full_name="Admin User",
        primary_role="admin",
        roles=["admin", "egresado"],
        active=True,
    )


def test_login_me_logout_flow(monkeypatch) -> None:
    monkeypatch.setattr(
        auth,
        "_query_user_by_email",
        lambda _email: {
            "id": 7,
            "email": "admin@example.com",
            "password_hash": "hash",
            "full_name": "Admin User",
            "primary_role": "admin",
            "active": True,
            "roles": ["admin", "egresado"],
        },
    )
    monkeypatch.setattr(auth, "verify_password", lambda password, password_hash: password == "CorrectHorse123")
    stored_sessions: list[tuple[int, str]] = []
    revoked_sessions: list[str] = []

    def fake_store_access_session(*, user_id: int, jti_hash: str, expires_at, request) -> None:
        stored_sessions.append((user_id, jti_hash))

    monkeypatch.setattr(auth, "_store_access_session", fake_store_access_session)
    monkeypatch.setattr(auth, "_access_session_is_active", lambda _jti_hash: True)
    monkeypatch.setattr(
        auth,
        "_query_user_by_id",
        lambda user_id: {
            "id": user_id,
            "email": "admin@example.com",
            "password_hash": "hash",
            "full_name": "Admin User",
            "primary_role": "admin",
            "active": True,
            "roles": ["admin", "egresado"],
        },
    )
    monkeypatch.setattr(auth, "_revoke_access_session", lambda jti_hash: revoked_sessions.append(jti_hash) or True)

    client = TestClient(app)

    login_response = client.post("/auth/login", json={"email": "admin@example.com", "password": "CorrectHorse123"})
    assert login_response.status_code == 200, login_response.text
    login_payload = login_response.json()
    assert login_payload["token_type"] == "bearer"
    assert "access_token" in login_payload
    assert login_payload["user"]["email"] == "admin@example.com"
    assert stored_sessions and stored_sessions[0][0] == 7

    token = login_payload["access_token"]
    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200, me_response.text
    me_payload = me_response.json()
    assert me_payload["email"] == "admin@example.com"
    assert "admin" in me_payload["roles"]

    logout_response = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_response.status_code == 200, logout_response.text
    logout_payload = logout_response.json()
    assert logout_payload["status"] == "ok"
    assert revoked_sessions


def test_require_roles_blocks_unauthorized_user() -> None:
    test_app = FastAPI()

    @test_app.get("/admin-only")
    def admin_only(current_user: auth.AuthenticatedUser = Depends(auth.require_roles("admin"))):
        return {"email": current_user.email}

    client = TestClient(test_app)

    test_app.dependency_overrides[auth.get_current_user] = lambda: auth.AuthenticatedUser(
        id=8,
        email="student@example.com",
        full_name="Student User",
        primary_role="egresado",
        roles=["egresado"],
        active=True,
    )
    response = client.get("/admin-only")

    assert response.status_code == 403


def test_require_roles_allows_admin_user() -> None:
    test_app = FastAPI()

    @test_app.get("/admin-only")
    def admin_only(current_user: auth.AuthenticatedUser = Depends(auth.require_roles("admin"))):
        return {"email": current_user.email}

    client = TestClient(test_app)

    test_app.dependency_overrides[auth.get_current_user] = _fake_user
    response = client.get("/admin-only")

    assert response.status_code == 200
    assert response.json()["email"] == "admin@example.com"
