# /api/programas Reference Audit

## Frontend contract consumers

| Archivo | Línea | Estructura esperada de respuesta | Backend equivalente disponible actualmente | Propuesta de adaptación |
| --- | --- | --- | --- | --- |
| `graduate_intelligence_platform/frontend/src/services/api.ts` | 113 | `Page<Program>` con `items`, `count`, `limit`, `offset` | `graduate_intelligence_platform/backend/app/api.py:781-792` implementa `GET /api/programas` con `Page`; `backend/routes/programas.py:8-12` devuelve una lista simple | Mantener el contrato `Page<Program>` en el backend nuevo; si se usa Flask, envolver la lista en `{items,count,limit,offset}` |
| `graduate_intelligence_platform/frontend/src/services/api.ts` | 125 | `Program` para `GET /api/programas/{programId}` | `graduate_intelligence_platform/backend/app/api.py:792-799` devuelve un `dict` enriquecido; `backend/routes/programas.py` no expone detalle | Exponer alias `GET /api/programas/{id}` en el backend nuevo y normalizar a `Program`; si se necesita el detalle enriquecido, usar `/api/dashboard/programa/{id}` |
| `graduate_intelligence_platform/frontend/src/types/api.ts` | 1, 71 | `Page<T>` y `Program` definen el contrato del frontend | El frontend depende de la forma `{items,count,limit,offset}` y de campos base como `especializacion_id`, `nombre_especializacion`, `rol`, `total_skills_programa`, `promedio_match_mercado`, `max_match_mercado`, `total_empleos_relacionados` | Mantener estos nombres o hacer una capa de mapeo/normalización antes de serializar la respuesta |

## Backend equivalente disponible actualmente

| Archivo | Línea | Estructura esperada de respuesta | Backend equivalente disponible actualmente | Propuesta de adaptación |
| --- | --- | --- | --- | --- |
| `graduate_intelligence_platform/backend/app/api.py` | 781-792 | `Page` paginado para lista | `GET /api/programas` con `Page` real; usa `programs()` + `page(...)` | Este es el equivalente más fiel al frontend; mantenerlo como fuente canónica o replicar su contrato en el servicio FastAPI actual |
| `graduate_intelligence_platform/backend/app/api.py` | 792-799 | `Program` enriquecido por programa | `GET /api/programas/{program_id}` devuelve el programa normalizado más contexto microcurricular | Si se expone al frontend actual, recortar o tipar el payload para que siga siendo compatible con `Program` |
| `backend/routes/programas.py` | 8-12 | Lista JSON simple | Blueprint Flask `/api/programas` que devuelve `list_programs_base(...)` sin envoltorio paginado | Solo sirve como fallback interno; para el frontend habría que paginar y envolver la respuesta |

## Tests y verificaciones operativas

| Archivo | Línea | Estructura esperada de respuesta | Backend equivalente disponible actualmente | Propuesta de adaptación |
| --- | --- | --- | --- | --- |
| `tests/backend/test_api_endpoints.py` | 35, 57 | `GET /api/programas` debe responder con página válida | Depende del backend legado en `graduate_intelligence_platform/backend/app/api.py` | Si el backend nuevo reemplaza al legado, asegurar un alias compatible antes de cambiar el frontend |
| `verify_railway_data.py` | 73, 117-120 | Se espera un conteo de programas en `/api/programas` | Verificación de humo sobre el endpoint legado | Mantener esta verificación como smoke test de compatibilidad |
| `logs/verify_railway_data_20260524_154705.json` | 28 | URL `/api/programas` accesible en Railway | Evidencia operativa de uso real del endpoint | Útil para trazabilidad; no requiere cambio funcional |

## Docs que mencionan `/api/programas`

- `docs/AUTH_IMPLEMENTATION_PHASE_1.md:89-90`
- `docs/BACKEND_REFACTOR_PHASE_1.md:43,127`
- `docs/BACKEND_REFACTOR_PHASE_2.md:120,176`
- `docs/FASTAPI_MIGRATION_PHASE_1.md:23-24,60`
- `docs/HARDENING_QA_ML_PHASE_1.md:33`
- `docs/MICROCURRICULUM_CONTEXT_ENGINE_PHASE_1.md:116`
- `docs/RAILWAY_DATA_SYNC.md:7,88,119`
- `docs/RAILWAY_DATA_SYNC_EXECUTION_REPORT.md:68,91,115`
- `docs/REACT_FRONTEND_PHASE_1.md:70-71`

## Adaptación recomendada

1. Añadir `GET /api/programas` y `GET /api/programas/{id}` al FastAPI actual si todavía no están montados allí.
2. Hacer que `GET /api/programas` devuelva exactamente `Page<Program>` (`items`, `count`, `limit`, `offset`).
3. Mantener `GET /api/programas/{id}` como `Program` compatible con el frontend; si hace falta el enriquecimiento microcurricular, exponerlo en un endpoint paralelo o en `/api/dashboard/programa/{id}`.
4. Si el nuevo backend reemplaza al legado, conservar la semántica de campos del `Program` frontend para no romper el cliente.

