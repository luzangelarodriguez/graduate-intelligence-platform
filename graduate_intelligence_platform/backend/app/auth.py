from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.repositories.base import cursor, fetch_one

from .schemas import AuthLoginIn, AuthRegisterIn, LogoutIn, RefreshTokenIn, TokenPair, UserPublic

DB_NAME = os.getenv("DB_NAME")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("AUTH_SECRET_KEY", "dev-insecure-change-me"))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
ALLOWED_ROLES = ("admin", "universidad", "egresado", "mentor")

password_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)
bearer_scheme = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/auth", tags=["auth"])


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def ensure_auth_schema(*, db_name: str | None = None) -> None:
    with cursor(db_name=db_name or DB_NAME) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS roles (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'egresado',
                active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        for statement in (
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'egresado'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now()",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now()",
        ):
            cur.execute(statement)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role_id BIGINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (user_id, role_id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                refresh_token_hash TEXT NOT NULL UNIQUE,
                user_agent TEXT,
                ip_address TEXT,
                expires_at TIMESTAMPTZ NOT NULL,
                revoked_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_users_email ON users (lower(email))")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_sessions_user_id ON sessions (user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_sessions_refresh_hash ON sessions (refresh_token_hash)")
        for role in ALLOWED_ROLES:
            cur.execute("INSERT INTO roles (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (role,))


def password_hash(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_context.verify(password, hashed_password)


def normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def serialize_user(row: dict[str, Any]) -> UserPublic:
    roles = row.get("roles") or []
    if isinstance(roles, str):
        roles = [roles]
    return UserPublic(
        id=int(row["id"]),
        email=str(row["email"]),
        full_name=str(row.get("full_name") or ""),
        roles=[str(role) for role in roles if role],
        active=bool(row.get("active", True)),
    )


def fetch_user_by_email(email: str) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT
            u.id,
            u.email,
            u.password_hash,
            u.full_name,
            u.active,
            COALESCE(array_remove(array_agg(r.name ORDER BY r.name), NULL), '{}') AS roles
        FROM users u
        LEFT JOIN user_roles ur ON ur.user_id = u.id
        LEFT JOIN roles r ON r.id = ur.role_id
        WHERE lower(u.email) = lower(%s)
        GROUP BY u.id
        """,
        (normalize_email(email),),
        db_name=DB_NAME,
    )


def fetch_user_by_id(user_id: int) -> dict[str, Any] | None:
    return fetch_one(
        """
        SELECT
            u.id,
            u.email,
            u.password_hash,
            u.full_name,
            u.active,
            COALESCE(array_remove(array_agg(r.name ORDER BY r.name), NULL), '{}') AS roles
        FROM users u
        LEFT JOIN user_roles ur ON ur.user_id = u.id
        LEFT JOIN roles r ON r.id = ur.role_id
        WHERE u.id = %s
        GROUP BY u.id
        """,
        (user_id,),
        db_name=DB_NAME,
    )


def create_user(payload: AuthRegisterIn) -> UserPublic:
    role = payload.role if payload.role in ALLOWED_ROLES else "egresado"
    email = normalize_email(payload.email)
    if fetch_user_by_email(email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")
    with cursor(db_name=DB_NAME) as cur:
        cur.execute(
            """
            INSERT INTO users (email, password_hash, full_name, role)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (email, password_hash(payload.password), payload.full_name.strip(), role),
        )
        user_id = int((cur.fetchone() or {})["id"])
        cur.execute("SELECT id FROM roles WHERE name = %s", (role,))
        role_id = int((cur.fetchone() or {})["id"])
        cur.execute(
            "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (user_id, role_id),
        )
    row = fetch_user_by_id(user_id)
    if not row:
        raise HTTPException(status_code=500, detail="created user could not be loaded")
    return serialize_user(row)


def create_access_token(user: UserPublic) -> str:
    expires_at = utc_now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "roles": user.roles,
        "type": "access",
        "iat": int(utc_now().timestamp()),
        "exp": expires_at,
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_session(user: UserPublic, request: Request | None = None) -> str:
    refresh_token = secrets.token_urlsafe(48)
    expires_at = utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    user_agent = request.headers.get("user-agent", "")[:500] if request else ""
    ip_address = request.client.host if request and request.client else ""
    with cursor(db_name=DB_NAME) as cur:
        cur.execute(
            """
            INSERT INTO sessions (user_id, refresh_token_hash, user_agent, ip_address, expires_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user.id, token_hash(refresh_token), user_agent, ip_address, expires_at),
        )
    return refresh_token


def issue_tokens(user: UserPublic, request: Request | None = None) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user),
        refresh_token=create_refresh_session(user, request),
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user,
    )


def authenticate(email: str, password: str) -> UserPublic:
    row = fetch_user_by_email(email)
    if not row or not verify_password(password, str(row.get("password_hash") or "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    if not row.get("active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="inactive user")
    return serialize_user(row)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token type")
    return payload


def require_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> UserPublic:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    payload = decode_access_token(credentials.credentials)
    row = fetch_user_by_id(int(payload["sub"]))
    if not row or not row.get("active", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user unavailable")
    return serialize_user(row)


def require_roles(*allowed_roles: str):
    def dependency(user: UserPublic = Depends(require_current_user)) -> UserPublic:
        if not set(user.roles).intersection(allowed_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient role")
        return user

    return dependency


def refresh_tokens(refresh_token: str, request: Request) -> TokenPair:
    hashed = token_hash(refresh_token)
    session = fetch_one(
        """
        SELECT s.id, s.user_id
        FROM sessions s
        WHERE s.refresh_token_hash = %s
          AND s.revoked_at IS NULL
          AND s.expires_at > now()
        """,
        (hashed,),
        db_name=DB_NAME,
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token")
    with cursor(db_name=DB_NAME) as cur:
        cur.execute("UPDATE sessions SET revoked_at = now() WHERE id = %s", (session["id"],))
    row = fetch_user_by_id(int(session["user_id"]))
    if not row or not row.get("active", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user unavailable")
    return issue_tokens(serialize_user(row), request)


def revoke_refresh_token(refresh_token: str) -> None:
    with cursor(db_name=DB_NAME) as cur:
        cur.execute(
            "UPDATE sessions SET revoked_at = now() WHERE refresh_token_hash = %s AND revoked_at IS NULL",
            (token_hash(refresh_token),),
        )


@router.post("/register", response_model=TokenPair)
def register(payload: AuthRegisterIn, request: Request) -> TokenPair:
    ensure_auth_schema(db_name=DB_NAME)
    user = create_user(payload)
    return issue_tokens(user, request)


@router.post("/login", response_model=TokenPair)
def login(payload: AuthLoginIn, request: Request) -> TokenPair:
    ensure_auth_schema(db_name=DB_NAME)
    user = authenticate(payload.email, payload.password)
    return issue_tokens(user, request)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshTokenIn, request: Request) -> TokenPair:
    ensure_auth_schema(db_name=DB_NAME)
    return refresh_tokens(payload.refresh_token, request)


@router.post("/logout")
def logout(payload: LogoutIn) -> dict[str, str]:
    if payload.refresh_token:
        revoke_refresh_token(payload.refresh_token)
    return {"status": "ok"}


@router.get("/me", response_model=UserPublic)
def me(current_user: UserPublic = Depends(require_current_user)) -> UserPublic:
    return current_user
