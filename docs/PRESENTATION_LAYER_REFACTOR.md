# Presentation Layer Refactor

## Objetivo

Separar la capa de presentacion Flask que estaba embebida en `app.py` sin romper rutas, dashboard, registro ni compatibilidad PostgreSQL-first.

## Cambios realizados

- `app.py` conserva el rol de entrypoint Flask y orquestador de rutas.
- El layout principal del dashboard se movio a `templates/dashboard/base.html`.
- El formulario/vista de registro se movio a `templates/dashboard/registration.html`.
- El sidebar del dashboard se separo como componente reutilizable en `templates/components/sidebar.html`.
- Los estilos del dashboard se extrajeron a `static/css/dashboard.css`.
- Los estilos de registro se extrajeron a `static/css/registration.css`.
- El JavaScript del wizard de registro se extrajo a `static/js/registration.js`.
- `.dockerignore` ahora incluye `templates/` y `static/` para mantener compatibilidad en contenedores.

## Estructura actual

```text
templates/
  components/
    sidebar.html
  dashboard/
    base.html
    registration.html

static/
  css/
    dashboard.css
    registration.css
  js/
    registration.js
  img/
```

## Que queda en app.py

- Definicion de rutas Flask actuales.
- Llamadas a services y repositories.
- Construccion dinamica de bloques HTML de dashboard.
- Scripts dinamicos de Chart.js generados desde payloads calculados en Python.
- Render final mediante `render_template(...)`.

## Riesgos encontrados

- Aun existen componentes de dashboard generados como strings HTML en Python; deben extraerse por grupos para no romper el flujo actual.
- El payload de graficas Chart.js sigue en `app.py` porque depende de datos dinamicos ya agregados por la ruta.
- Algunas vistas mezclan presentacion y datos mediante `body|safe`; esto debe reemplazarse gradualmente por templates con variables estructuradas.

## Proximos pasos recomendados

1. Extraer componentes Jinja para KPI cards, tablas, filtros, rankings y tarjetas de recomendacion.
2. Cambiar helpers que devuelven HTML por helpers que devuelvan diccionarios/listas serializables.
3. Mover Chart.js a `static/js/dashboard.js` usando un objeto `window.dashboardPayload`.
4. Separar templates por pantalla: resumen general, programa, registro y futuras vistas de matching.
5. Mantener endpoints JSON como contrato previo a React.

## Estrategia React futura

- Mantener Flask como backend/API mientras los templates se reducen progresivamente.
- Convertir las rutas de dashboard a APIs JSON versionadas.
- Reutilizar `backend/services` como capa de negocio para Flask y FastAPI.
- Crear `frontend/` con React/Vite cuando los contratos JSON esten estables.
- Migrar primero componentes visuales de bajo riesgo: KPI cards, tablas y filtros.

## Verificacion esperada

- `python -m py_compile app.py`
- Import de `app`.
- Listado de rutas Flask.
- Render de `/dashboard`.
- Render de `/registro`.
- Carga de `/static/css/dashboard.css`.
- Carga de `/static/css/registration.css`.
- Carga de `/static/js/registration.js`.
