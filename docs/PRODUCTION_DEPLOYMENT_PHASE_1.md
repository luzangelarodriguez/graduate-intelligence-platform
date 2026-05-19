# Production Deployment Phase 1

## Objetivo

Preparar la plataforma SaaS React + FastAPI + PostgreSQL para despliegue cloud real, manteniendo compatibilidad con el entorno local y Flask legacy.

## Arquitectura cloud recomendada

```text
Vercel / Nginx static frontend
        |
        | HTTPS
        v
Railway / Render FastAPI backend
        |
        | PostgreSQL SSL
        v
Neon / Railway PostgreSQL
```

Componentes:

- Frontend: React/Vite servido como static build.
- Backend: FastAPI con Gunicorn + Uvicorn workers.
- Base de datos: PostgreSQL cloud con SSL obligatorio.
- Auth: JWT access token + refresh token opaco en PostgreSQL.
- Observabilidad: logs stdout/stderr, health checks, Sentry opcional.

## Artefactos creados

```text
graduate_intelligence_platform/backend/Dockerfile
graduate_intelligence_platform/backend/gunicorn_conf.py
graduate_intelligence_platform/backend/app/settings.py
graduate_intelligence_platform/backend/app/middleware.py
graduate_intelligence_platform/frontend/Dockerfile
graduate_intelligence_platform/frontend/nginx.conf
docker-compose.prod.yml
.env.development
.env.production
database/migrations/001_auth_schema.sql
database/backup_postgres.sh
.github/workflows/ci.yml
```

## Docker producción

Backend:

- Imagen Python slim.
- Usuario no-root.
- Gunicorn con `uvicorn.workers.UvicornWorker`.
- Healthcheck `GET /api/health`.
- Variables por `.env.production`.

Frontend:

- Multi-stage build Node + Nginx.
- Cache headers para `/assets/`.
- Secure headers básicos.
- Proxy `/api/` y `/auth/` hacia backend.

Comando local:

```powershell
docker compose -f docker-compose.prod.yml --env-file .env.production config
docker compose -f docker-compose.prod.yml --env-file .env.production build
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

## Variables de entorno

Backend:

```text
APP_ENV=production
LOG_LEVEL=INFO
DB_HOST=
DB_PORT=5432
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_SSLMODE=require
JWT_SECRET_KEY=
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=https://frontend.example.com
TRUSTED_HOSTS=api.example.com
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=120
SENTRY_DSN=
WEB_CONCURRENCY=2
PORT=8000
```

Frontend:

```text
VITE_API_BASE_URL=https://api.example.com
```

Para Docker/Nginx monolítico se usa `VITE_API_BASE_URL=/api`.

## FastAPI producción

Configurado:

- `TrustedHostMiddleware`.
- CORS por allowlist.
- GZip.
- Headers de seguridad.
- Rate limiting básico opcional.
- Logging stdout/stderr.
- Sentry opcional por `SENTRY_DSN`.
- Gunicorn config por variables.

Pendiente recomendado:

- Rate limiting distribuido con Redis para multi-worker/multi-instance.
- Cookies `HttpOnly Secure SameSite` para refresh token.
- Denylist de access-token `jti` si se requiere revocación inmediata.

## React producción

Configurado:

- Build de producción Vite.
- Manual chunks para `react`, `recharts` y `axios`.
- Nginx cachea assets versionados por 1 año.
- Proxy Nginx para `/api` y `/auth`.

Pendiente recomendado:

- Lazy loading por página con `React.lazy`.
- Monitoreo de web vitals.
- Sentry frontend si se define proyecto JS.

## PostgreSQL cloud

Configurado:

- `DB_SSLMODE=require` listo para Neon/Railway.
- `DB_CONNECT_TIMEOUT`.
- Migración inicial auth en `database/migrations/001_auth_schema.sql`.
- Script de backup `database/backup_postgres.sh`.

Backups:

- Neon: activar PITR/backups automáticos del proveedor.
- Railway/Render: activar snapshots automáticos y export programado.
- Backup manual:

```sh
DB_HOST=... DB_PORT=5432 DB_NAME=... DB_USER=... PGPASSWORD=... ./database/backup_postgres.sh
```

## CI/CD

GitHub Actions:

- Compila backend Python.
- Instala dependencias backend/dev.
- Construye frontend React.
- Construye imágenes Docker backend/frontend.

Deploy sugerido:

- Vercel: conectar `graduate_intelligence_platform/frontend`, build `npm run build`, output `dist`.
- Render/Railway backend: Dockerfile `graduate_intelligence_platform/backend/Dockerfile`.
- Neon/Railway PostgreSQL: cargar variables `DB_*` con SSL.

## Rollback

Frontend:

- Vercel permite rollback instantáneo a deployment anterior.
- Docker/Nginx: redeploy de tag anterior.

Backend:

- Versionar imagen Docker por SHA/tag.
- Mantener al menos una imagen previa disponible.
- Rollback de variables y redeploy del tag anterior.

Base de datos:

- Las migraciones deben ser aditivas.
- Antes de migraciones destructivas, crear snapshot.
- Restaurar desde PITR/snapshot si hay corrupción o pérdida de datos.

## Seguridad

Incluido:

- HTTPS-ready.
- CORS estricto por env.
- Trusted hosts.
- Secure headers.
- JWT expiration.
- Refresh token rotado y revocable.
- PostgreSQL SSL.

Pendiente para hardening fase 2:

- CSRF si se migran refresh tokens a cookies.
- Redis rate limit.
- Password reset seguro.
- MFA para admin/universidad.
- Auditoría de login/logout y cambios de rol.
- Gestión de secretos con Railway/Render/Vercel env vars, no archivos `.env` reales.

## Monitoreo

Health:

```text
GET /api/health
```

Logs:

- Backend: stdout/stderr Gunicorn.
- Frontend: logs Nginx del proveedor.
- DB: métricas del proveedor cloud.

Sentry:

- Backend: `SENTRY_DSN` activa integración FastAPI.
- Frontend: recomendado fase 2 con `@sentry/react`.

## Verificación fase 1

Checklist esperado:

- `python -m py_compile` backend.
- `npm run build` frontend.
- `docker compose -f docker-compose.prod.yml config`.
- `docker compose -f docker-compose.prod.yml build backend frontend`.
- `GET /api/health` responde 200.
- Auth: register/login/me/refresh/logout.
- DB cloud: conexión con `DB_SSLMODE=require`.

Validado en esta fase:

- `py_compile` backend OK.
- `npm run build` frontend OK.
- `docker compose -f docker-compose.prod.yml --env-file .env.production config` OK.
- `docker build` backend OK.
- `docker build` frontend OK.
- Contenedor backend producción con Gunicorn/Uvicorn OK.
- `GET /api/health` desde contenedor backend OK contra PostgreSQL local usando `DB_SSLMODE=prefer`.

No validado localmente:

- Conexión contra PostgreSQL cloud con `DB_SSLMODE=require`, porque requiere credenciales reales Neon/Railway/Render.
