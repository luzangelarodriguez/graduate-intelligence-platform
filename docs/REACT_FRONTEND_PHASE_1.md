# React Frontend Phase 1

## Objetivo

Crear el frontend moderno oficial de la plataforma usando React + Vite, conectado al backend FastAPI PostgreSQL-first y coexistiendo con Flask como fallback legacy.

## Ubicacion

```text
graduate_intelligence_platform/frontend
```

## Stack

- React 18
- Vite
- TypeScript
- TailwindCSS
- Axios
- React Router
- Recharts

## Estructura frontend

```text
src/
  components/
    Charts.tsx
    EmptyState.tsx
    KpiCard.tsx
    LoadingState.tsx
    MatchCards.tsx
    RecommendationCards.tsx
    Sidebar.tsx
    SkillsGap.tsx
    Topbar.tsx
    TrendCards.tsx
  context/
    AppContext.tsx
  hooks/
    useDashboardData.ts
  layouts/
    AppLayout.tsx
  pages/
    AlumniOnboardingPage.tsx
    DashboardPage.tsx
    ProgramsPage.tsx
  services/
    api.ts
  styles/
    index.css
  types/
    api.ts
```

## Arquitectura de componentes

- `AppLayout`: shell principal con sidebar y topbar.
- `DashboardPage`: vista ejecutiva de KPIs, charts, matches, skills y recomendaciones.
- `ProgramsPage`: tabla operacional de programas desde PostgreSQL.
- `AlumniOnboardingPage`: onboarding multi-step conectado a FastAPI.
- `services/api.ts`: capa unica Axios para consumo HTTP.
- `types/api.ts`: contratos TypeScript alineados con respuestas FastAPI.

## Consumo APIs

```text
GET  /api/bootstrap
GET  /api/dashboard/kpis
GET  /api/programas
GET  /api/programas/{id}
GET  /api/matches
GET  /api/matches/programa/{id}
GET  /api/recommendations/programs
GET  /api/recommendations/jobs
POST /api/alumni/register
```

## Variables de entorno

```text
VITE_API_BASE_URL=http://127.0.0.1:8010
```

En desarrollo, Vite tambien tiene proxy `/api` hacia `VITE_API_BASE_URL`.

## Docker

El frontend incluye:

```text
graduate_intelligence_platform/frontend/Dockerfile
graduate_intelligence_platform/frontend/nginx.conf
```

La imagen compila React/Vite con Node y sirve `dist/` con Nginx. El proxy `/api/` apunta a `http://backend:8000/api/` para despliegues con red Docker interna.

## Estrategia de coexistencia Flask

- React se convierte en frontend oficial desacoplado.
- FastAPI queda como backend JSON oficial.
- Flask sigue sirviendo dashboard legacy y registro legacy como fallback.
- Ambos clientes consumen la misma base PostgreSQL y la misma logica compartida en `backend/services`.

## Plan eliminacion legacy

1. Estabilizar dashboard React con endpoints FastAPI.
2. Migrar vistas criticas de Flask a React: programa, recomendaciones, registro.
3. Sustituir HTML dinamico de Flask por endpoints JSON equivalentes.
4. Mantener Flask solo como fallback administrativo temporal.
5. Retirar rutas visuales Flask cuando React cubra paridad funcional.

## Riesgos tecnicos

- Recharts aumenta el bundle inicial; conviene aplicar lazy loading por pagina en la siguiente fase.
- El mapa de brechas todavia depende de datos disponibles por programa; se recomienda crear un endpoint dedicado `/api/skills/gaps`.
- `POST /api/alumni/register` escribe en PostgreSQL real; las pruebas E2E deben usar ambiente de staging o fixtures con rollback.
- El modo dark esta preparado a nivel visual, pero necesita una pasada completa de QA de contraste.

## Verificacion realizada

- `npm install`
- `npm run build`
- TypeScript OK
- Vite production build OK
- FastAPI + Vite levantados temporalmente OK.
- `GET /` desde Vite OK.
- `GET /api/health` directo y por proxy Vite OK.
- `GET /api/dashboard/kpis` por proxy Vite OK.

## QA pendiente

No habia Chrome, Edge, Chromium ni Playwright disponible en el entorno local, por lo que queda pendiente una pasada visual con navegador para screenshot desktop/mobile y revision responsive fina.
