from __future__ import annotations

import os
import re
from collections.abc import Mapping
from typing import Any

SECRET_KEYWORDS = ("token", "secret", "password", "cookie", "authorization", "api_key", "apikey", "access")
REDACTION = "[REDACTED]"


def is_sensitive_key(key: str) -> bool:
    normalized = key.casefold().replace("-", "_")
    return any(marker in normalized for marker in SECRET_KEYWORDS)


def sanitize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): (REDACTION if is_sensitive_key(str(key)) else sanitize_value(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_value(item) for item in value)
    if not isinstance(value, str):
        return value
    sanitized = value
    sanitized = re.sub(r"Bearer\s+[A-Za-z0-9._\-]+", f"Bearer {REDACTION}", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"(api[_-]?key=)[^&\s]+", rf"\1{REDACTION}", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"(access[_-]?token=)[^&\s]+", rf"\1{REDACTION}", sanitized, flags=re.IGNORECASE)
    for env_key, env_value in os.environ.items():
        if env_value and is_sensitive_key(env_key) and len(env_value) >= 8:
            sanitized = sanitized.replace(env_value, REDACTION)
    return sanitized


def validate_required_env(names: list[str]) -> dict[str, Any]:
    missing = [name for name in names if not os.getenv(name)]
    return {"valid": not missing, "missing": missing}
