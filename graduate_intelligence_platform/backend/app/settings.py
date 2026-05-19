from __future__ import annotations

import os


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class Settings:
    app_env = os.getenv("APP_ENV", "development")
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    cors_origins = os.getenv(
        "CORS_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174",
    )
    trusted_hosts = os.getenv("TRUSTED_HOSTS", "127.0.0.1,localhost,*")
    sentry_dsn = os.getenv("SENTRY_DSN", "")
    rate_limit_enabled = env_bool("RATE_LIMIT_ENABLED", False)
    rate_limit_per_minute = env_int("RATE_LIMIT_PER_MINUTE", 120)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        values: list[str] = []
        for item in self.trusted_hosts.split(","):
            value = item.strip().replace("\\*", "*")
            if value:
                values.append(value)
        return values


settings = Settings()
