from __future__ import annotations

import os
import logging
import site
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BASE_DIR = Path(__file__).resolve().parents[1]
DEPS_DIR = BASE_DIR / "deps"
VENDOR_DIR = BASE_DIR / "vendor"

local_dependency_paths = [PROJECT_ROOT]
if os.getenv("USE_LOCAL_DEPS", "false").lower() in {"1", "true", "yes"}:
    local_dependency_paths.extend([DEPS_DIR, VENDOR_DIR])

for path in local_dependency_paths:
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

user_site = site.getusersitepackages()
if user_site and user_site not in sys.path:
    sys.path.insert(0, user_site)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .api import router
from .auth import ensure_auth_schema, router as auth_router
from .middleware import InMemoryRateLimitMiddleware, SecurityHeadersMiddleware
from .settings import settings

if settings.sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            integrations=[FastApiIntegration()],
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.05")),
        )
    except Exception:
        logging.getLogger(__name__).exception("Sentry initialization failed")


def cors_origins() -> list[str]:
    return settings.cors_origin_list


logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


app = FastAPI(
    title="Graduate Intelligence Platform API",
    version="1.1.0",
    description="PostgreSQL-first API for curriculum intelligence, labor-market matching, alumni registration, and ML dashboard data.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SecurityHeadersMiddleware)
if settings.rate_limit_enabled:
    app.add_middleware(InMemoryRateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)

app.include_router(router)
app.include_router(auth_router)


@app.on_event("startup")
def startup() -> None:
    ensure_auth_schema()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "graduate_intelligence_platform.backend.app.main:app",
        host=os.getenv("FASTAPI_HOST", "0.0.0.0"),
        port=int(os.getenv("FASTAPI_PORT", "8010")),
        reload=os.getenv("FASTAPI_RELOAD", "false").lower() in {"1", "true", "yes"},
    )
