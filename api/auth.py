from __future__ import annotations

import bcrypt
import hashlib
import logging
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Iterable, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field, field_validator

from api.database import connection, fetch_one


logger = logging.getLogger(__name__)
auth_router = APIRouter(prefix="", tags=["auth"])
_bearer_scheme = HTTPBearer(auto_error=False)

T = TypeVar("T")


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value not in {None, ""} else default


def _jwt_secret_key() -> str:
    return _env("JWT_SECRET_KEY", _env("JWT_SECRET", "dev-only-change-me"))


def _jwt_algorithm() -> str:
    return _env("JWT_ALGORITHM", "HS256")


def _jwt_issuer() -> str:
    return _env("JWT_ISSUER", "graduate-intelligence-platform")


def _jwt_audience() -> str:
    return _env("JWT_AUDIENCE", "graduate-intelligence-platform-web")


def _token_expire_minutes() -> int:
    try:
        return max(5, int(_env("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "720")))
    except ValueError:
        return 720


def _bcrypt_rounds() -> int:
    try:
        return max(4, int(_env("BCRYPT_ROUNDS", "12")))
    except ValueError:
        return 12


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=_bcrypt_rounds())
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=256)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValueError("Invalid email")
        return email


class AuthenticatedUser(BaseModel):
    id: int
    email: str
    full_name: str
    primary_role: str
    roles: list[str] = Field(default_factory=list)
    active: bool = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthenticatedUser


class LogoutResponse(BaseModel):
    status: str
    detail: str


def _normalize_roles(primary_role: str | None, roles: Iterable[str] | None) -> list[str]:
    normalized: list[str] = []
    if primary_role:
        normalized.append(str(primary_role))
    for role in roles or []:
        candidate = str(role)
        if candidate and candidate not in normalized:
            normalized.append(candidate)
    return normalized


def _token_hash(jti: str) -> str:
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()


def _extract_client_metadata(request: Request | None) -> tuple[str | None, str | None]:
    if request is None:
        return None, None
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or None
    user_agent = request.headers.get("user-agent")
    ip_address = forwarded_for or (request.client.host if request.client else None)
    return ip_address, user_agent


def _query_user_by_email(email: str) -> dict[str, Any] | None:
    row = fetch_one(
        """
        SELECT
            u.id,
            u.email,
            u.password_hash,
            u.full_name,
            u.role AS primary_role,
            u.active,
            COALESCE(
                ARRAY_REMOVE(ARRAY_AGG(DISTINCT r.name), NULL),
                ARRAY[]::TEXT[]
            ) AS roles
        FROM users u
        LEFT JOIN user_roles ur ON ur.user_id = u.id
        LEFT JOIN roles r ON r.id = ur.role_id
        WHERE lower(u.email) = lower(%s)
        GROUP BY u.id, u.email, u.password_hash, u.full_name, u.role, u.active
        """,
        (email,),
    )
    return dict(row) if row else None


def _query_user_by_id(user_id: int) -> dict[str, Any] | None:
    row = fetch_one(
        """
        SELECT
            u.id,
            u.email,
            u.password_hash,
            u.full_name,
            u.role AS primary_role,
            u.active,
            COALESCE(
                ARRAY_REMOVE(ARRAY_AGG(DISTINCT r.name), NULL),
                ARRAY[]::TEXT[]
            ) AS roles
        FROM users u
        LEFT JOIN user_roles ur ON ur.user_id = u.id
        LEFT JOIN roles r ON r.id = ur.role_id
        WHERE u.id = %s
        GROUP BY u.id, u.email, u.password_hash, u.full_name, u.role, u.active
        """,
        (user_id,),
    )
    return dict(row) if row else None


def _access_session_is_active(jti_hash: str) -> bool:
    row = fetch_one(
        """
        SELECT revoked_at, expires_at
        FROM sessions
        WHERE refresh_token_hash = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (jti_hash,),
    )
    if not row:
        return True
    if row.get("revoked_at") is not None:
        return False
    expires_at = row.get("expires_at")
    if expires_at is not None and hasattr(expires_at, "astimezone"):
        return expires_at.astimezone(UTC) > datetime.now(UTC)
    return True


def _store_access_session(
    *,
    user_id: int,
    jti_hash: str,
    expires_at: datetime,
    request: Request | None,
) -> None:
    ip_address, user_agent = _extract_client_metadata(request)
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sessions (user_id, refresh_token_hash, user_agent, ip_address, expires_at, revoked_at)
                VALUES (%s, %s, %s, %s, %s, NULL)
                ON CONFLICT (refresh_token_hash) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    user_agent = EXCLUDED.user_agent,
                    ip_address = EXCLUDED.ip_address,
                    expires_at = EXCLUDED.expires_at,
                    revoked_at = NULL
                """,
                (user_id, jti_hash, user_agent, ip_address, expires_at),
            )


def _revoke_access_session(jti_hash: str) -> bool:
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE sessions
                SET revoked_at = now()
                WHERE refresh_token_hash = %s AND revoked_at IS NULL
                RETURNING id
                """,
                (jti_hash,),
            )
            return cur.rowcount > 0


def _create_access_token(user: AuthenticatedUser) -> tuple[str, str, datetime]:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=_token_expire_minutes())
    jti = secrets.token_urlsafe(32)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "roles": user.roles,
        "primary_role": user.primary_role,
        "jti": jti,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": _jwt_issuer(),
        "aud": _jwt_audience(),
    }
    token = jwt.encode(payload, _jwt_secret_key(), algorithm=_jwt_algorithm())
    return token, _token_hash(jti), expires_at


def _decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        _jwt_secret_key(),
        algorithms=[_jwt_algorithm()],
        audience=_jwt_audience(),
        issuer=_jwt_issuer(),
        options={"require_exp": True, "require_iat": True, "require_nbf": True, "require_sub": True},
    )


def _user_from_row(row: dict[str, Any]) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=int(row["id"]),
        email=row["email"],
        full_name=str(row["full_name"]),
        primary_role=str(row.get("primary_role") or row.get("role") or "egresado"),
        roles=_normalize_roles(str(row.get("primary_role") or row.get("role") or "egresado"), row.get("roles")),
        active=bool(row.get("active", True)),
    )


def authenticate_user(email: str, password: str) -> AuthenticatedUser:
    row = _query_user_by_email(email)
    if not row or not row.get("active", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(password, str(row["password_hash"])):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _user_from_row(row)


def login_user(email: str, password: str, request: Request | None = None) -> tuple[str, AuthenticatedUser]:
    user = authenticate_user(email, password)
    token, jti_hash, expires_at = _create_access_token(user)
    _store_access_session(user_id=user.id, jti_hash=jti_hash, expires_at=expires_at, request=request)
    return token, user


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme)) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = _decode_access_token(credentials.credentials)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    token_id = str(payload.get("jti") or "")
    if not token_id or not _access_session_is_active(_token_hash(token_id)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    user_id = int(payload["sub"])
    row = _query_user_by_id(user_id)
    if not row or not row.get("active", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return _user_from_row(row)


def require_roles(*allowed_roles: str) -> Callable[[AuthenticatedUser], AuthenticatedUser]:
    normalized_allowed = {role.strip().casefold() for role in allowed_roles if role.strip()}

    def _dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        user_roles = {role.casefold() for role in user.roles}
        if normalized_allowed and user_roles.isdisjoint(normalized_allowed):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return _dependency


@auth_router.post("/login", response_model=TokenResponse, summary="Authenticate a user and return a JWT access token")
def login(payload: LoginRequest, request: Request) -> dict[str, Any]:
    token, user = login_user(payload.email, payload.password, request=request)
    return {"access_token": token, "token_type": "bearer", "user": user.model_dump()}


@auth_router.post("/logout", response_model=LogoutResponse, summary="Revoke the current JWT access token")
def logout(current_user: AuthenticatedUser = Depends(get_current_user), credentials: HTTPAuthorizationCredentials | None = Security(_bearer_scheme)) -> dict[str, Any]:
    assert credentials is not None
    payload = _decode_access_token(credentials.credentials)
    token_id = str(payload.get("jti") or "")
    revoked = _revoke_access_session(_token_hash(token_id)) if token_id else False
    detail = "Session revoked" if revoked else "Session already inactive or unavailable"
    return {"status": "ok", "detail": detail}


@auth_router.get("/me", response_model=AuthenticatedUser, summary="Return the authenticated user profile")
def me(current_user: AuthenticatedUser = Depends(get_current_user)) -> dict[str, Any]:
    return current_user.model_dump()


def ensure_admin_user(*, email: str, password: str, full_name: str, role_name: str = "admin") -> dict[str, Any]:
    password_hash = hash_password(password)
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO roles (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (role_name,))
            cur.execute(
                """
                INSERT INTO users (email, password_hash, full_name, role, active)
                VALUES (%s, %s, %s, %s, TRUE)
                ON CONFLICT (email) DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    full_name = EXCLUDED.full_name,
                    role = EXCLUDED.role,
                    active = TRUE,
                    updated_at = now()
                RETURNING id
                """,
                (email, password_hash, full_name, role_name),
            )
            user_id = int(cur.fetchone()["id"])
            cur.execute("SELECT id FROM roles WHERE name = %s", (role_name,))
            role_row = cur.fetchone()
            if role_row:
                cur.execute(
                    """
                    INSERT INTO user_roles (user_id, role_id)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id, role_id) DO NOTHING
                    """,
                    (user_id, int(role_row["id"])),
                )
    return {"user_id": user_id, "email": email, "role": role_name}
