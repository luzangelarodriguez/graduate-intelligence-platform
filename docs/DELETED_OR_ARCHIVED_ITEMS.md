# Deleted Or Archived Items

Fecha: 2026-05-25

## Criterio De Limpieza

La limpieza se ejecutó de forma conservadora para no romper backend Railway, PostgreSQL, JWT, Vercel, microcurriculum engine, labor matching ni endpoints existentes. No se eliminaron datos institucionales, documentos de prueba, outputs analíticos ni scripts operativos.

## Archivado En `_archive_cleanup/`

| Origen | Destino | Motivo | Riesgo |
|---|---|---|---|
| `frontend/` | `_archive_cleanup/frontend_placeholder/` | Placeholder raíz sin app Vite productiva. El frontend oficial está en `graduate_intelligence_platform/frontend`. | Bajo |
| `estructura.txt` | `_archive_cleanup/generated_inventory/estructura.txt` | Inventario generado, pesado y regenerable. | Bajo |
| `estructura_proyecto.csv` | `_archive_cleanup/generated_inventory/estructura_proyecto.csv` | Inventario generado, pesado y regenerable. | Bajo |
| `graduate_intelligence_platform/ui_preview.html` | `_archive_cleanup/ui_preview/ui_preview.html` | Preview HTML antiguo, no productivo. | Bajo |
| `graduate_intelligence_platform/ui_bootstrap.js` | `_archive_cleanup/ui_preview/ui_bootstrap.js` | Script asociado al preview HTML antiguo. | Bajo |

## Eliminado Definitivamente

Solo se eliminaron artefactos regenerables:

- `.pytest_cache/`
- `__pycache__/` en todo el workspace
- `graduate_intelligence_platform/frontend/dist/`

El build de frontend regenera `dist/` con `npm run build`.

## No Movido Por Seguridad

| Ruta | Motivo |
|---|---|
| `app.py`, `templates/`, `static/` | Flask legacy/fallback. Se documenta como deuda, pero no se mueve sin aprobación explícita. |
| `db.py`, `queries.py`, `scraper.py`, `ml_match_program_jobs.py` | Wrappers de compatibilidad todavía referenciados por scripts o documentación operativa. |
| `vendor/`, `selenium_deps/`, `graduate_intelligence_platform/backend/deps/`, `graduate_intelligence_platform/backend/vendor/` | Dependencias vendorizadas. Deben salir de Git a futuro, pero moverlas puede romper ejecuciones locales existentes. |
| `outputs/`, `logs/`, `scrapers/lakehouse/**` | Evidencia y reportes generados. Pueden rotarse por política de retención, no eliminarse a ciegas. |
| `storage/test_microcurriculos/**` | Documentos institucionales reales de piloto. No borrar. |

## Riesgos Pendientes

- La raíz aún conserva coexistencia con Flask legacy.
- Existen dependencias vendorizadas pesadas que deben reemplazarse por instalación reproducible desde `requirements.txt`.
- `outputs/` y `scrapers/lakehouse/**` requieren política de retención para evitar crecimiento indefinido.
- Algunos scripts raíz son operativos pero convendría moverlos gradualmente a `scripts/` con imports estables.

## Validación Posterior

- `python -m py_compile scripts\workspace_audit.py sync_to_railway.py verify_railway_data.py diagnose_labor_matching.py build_labor_program_matches.py microcurriculum_context_engine.py`: OK.
- `python -c "from graduate_intelligence_platform.backend.app.main import app; print(app.title)"`: `Graduate Intelligence Platform API`.
- `npm run build` en `graduate_intelligence_platform/frontend`: OK.
- `python -m pytest tests`: 34 passed, 4 skipped.
