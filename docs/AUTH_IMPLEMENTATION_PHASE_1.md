# Auth Implementation Phase 1

## Objetivo

Implementar autenticacion y autorizacion enterprise para la plataforma SaaS React + FastAPI + PostgreSQL-first.

## Arquitectura auth

- FastAPI expone router `/auth`.
- PostgreSQL almacena usuarios, roles, relaciones usuario-rol y sesiones refresh.
- Passwords se almacenan con `passlib[bcrypt]`.
- Access tokens son JWT firmados con `python-jose`.
- Refresh tokens son opacos, se guardan como SHA-256 en `sessions` y rotan en cada refresh.
- React persiste access/refresh token en `localStorage` y restaura sesion con `/auth/me` o `/auth/refresh`.

## Tablas PostgreSQL

```text
roles
  id
  name
  created_at

users
  id
  email
  password_hash
  full_name
  role
  active
  created_at
  updated_at

user_roles
  user_id
  role_id
  created_at

sessions
  id
  user_id
  refresh_token_hash
  user_agent
  ip_address
  expires_at
  revoked_at
  created_at
```

Las tablas se crean en startup con `ensure_auth_schema()`.

## Roles

```text
admin
universidad
egresado
mentor
```

## Endpoints

```text
POST /auth/register
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
```

## Flujo JWT

1. El usuario hace login o registro.
2. FastAPI valida credenciales y emite:
   - `access_token` JWT con expiracion corta.
   - `refresh_token` opaco con expiracion larga.
3. React envia `Authorization: Bearer <access_token>` en requests protegidos.
4. Si la sesion se restaura y el access token no sirve, React usa refresh token.
5. `/auth/refresh` revoca el refresh token anterior y emite uno nuevo.
6. `/auth/logout` revoca el refresh token enviado; React limpia almacenamiento local.

## Rutas protegidas

Las APIs productivas quedan protegidas por `require_current_user`, incluyendo:

```text
GET  /api/bootstrap
GET  /api/dashboard/kpis
GET  /api/programas
GET  /api/programas/{id}
GET  /api/empleos
GET  /api/empleos/{id}
GET  /api/matches
GET  /api/matches/programa/{id}
POST /api/alumni/register
GET  /api/recommendations/programs
GET  /api/recommendations/jobs
```

`GET /api/health` queda publico para health checks.

## Frontend

- `AuthContext.tsx`: login, registro, logout, session restore y refresh.
- `ProtectedRoute.tsx`: protege dashboard, programas y onboarding.
- `LoginPage.tsx`: login/registro de usuarios.
- `services/api.ts`: interceptor Axios para Bearer token.
- `Topbar.tsx`: muestra usuario/roles y logout.

## Variables de entorno

```text
JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

## Seguridad

- Usar un `JWT_SECRET_KEY` largo, aleatorio y externo al repo.
- Usar HTTPS en produccion.
- Rotar refresh tokens.
- Revocar refresh tokens en logout.
- Mantener CORS limitado a dominios reales.
- No usar usuarios demo en produccion.

## Riesgos y siguientes pasos

- Los access tokens son stateless; logout revoca refresh token, pero el access token actual vive hasta expirar.
- Para revocacion inmediata de access tokens, agregar denylist por `jti`.
- Migrar refresh tokens a cookies `HttpOnly Secure SameSite` para reducir exposicion XSS.
- Agregar rate limiting en `/auth/login`.
- Agregar politicas de password y recuperacion segura.
- Agregar auditoria de login/logout y cambios de rol.
- Crear endpoints administrativos para gestionar usuarios y roles.

## Verificacion realizada

- `py_compile` backend OK.
- `npm run build` frontend OK.
- `GET /api/dashboard/kpis` sin token devuelve `401`.
- `POST /auth/register` crea usuario real en PostgreSQL y devuelve tokens.
- `GET /auth/me` valida JWT.
- `GET /api/dashboard/kpis` con Bearer token devuelve KPIs reales.
- `POST /auth/login` valida password real.
- `POST /auth/refresh` rota refresh token.
- `POST /auth/logout` revoca refresh token.
- Refresh con token revocado devuelve `401`.
- Vite sirve `/login` correctamente.

## Usuario de verificacion

Se creo un usuario de prueba para validar login real:

```text
auth_test_20260515091249@example.local
```

No se elimino automaticamente para mantener trazabilidad de la prueba.
