# Executive Frontend Demo

## Objetivo

Primera experiencia ejecutiva para demo institucional de Graduate Intelligence Platform. Permite cargar microcurriculos en PDF, DOCX o TXT, ejecutar analisis IA local y presentar resultados en lenguaje de rectoria, decanatura y comite academico.

## Backend

Endpoints creados:

- `POST /api/microcurriculum/analyze`
  - Recibe `multipart/form-data` con campo `file`.
  - Soporta `.pdf`, `.docx` y `.txt`.
  - Ejecuta extraccion, parsing, clasificacion disciplinar, NER curricular, matching, gaps, recomendaciones y scoring.
  - No persiste por defecto; es endpoint de demo/staging.

- `GET /api/microcurriculum/demo-cases`
  - Lista casos disponibles desde `outputs/cross_domain_validation_results.json`.

- `GET /api/microcurriculum/{id}/executive-report`
  - Devuelve reporte ejecutivo en JSON y Markdown para casos demo existentes.

## Frontend

Ruta publica:

- `/`
- `/microcurriculum-demo`

Pantallas/secciones incluidas:

- Upload Microcurriculum
- Analysis Results
- Skills & Entities
- Market Gaps
- Curriculum Recommendations
- Pertinence Score
- Executive Summary
- Export executive report

## API Local

El frontend consume:

```text
http://127.0.0.1:8010
```

mediante `VITE_API_BASE_URL` cuando exista, o proxy/base URL configurada en runtime.

## Casos Demo

Microcurriculos usados para validacion:

- `storage/test_microcurriculos/analitica/aprendizaje automatico.docx`
- `storage/test_microcurriculos/gerencia/Diseño de proyectos orientados a la innovación.docx`
- `storage/test_microcurriculos/gerencia/ADE _S.5 _B. 1 _Gerencia Financiera.docx`

## Validacion Ejecutada

```powershell
python -m py_compile graduate_intelligence_platform\backend\app\api.py microcurriculum_engine\recommendations\recommendation_engine.py
python -m pytest tests
npm install
npm run build
```

Resultado:

- Python tests: `32 passed, 5 skipped`
- Frontend build: OK
- `npm install`: OK, con 2 vulnerabilidades moderadas reportadas por npm audit.

## Nota De Validacion Pendiente

La prueba directa con `FastAPI TestClient` sobre `POST /api/microcurriculum/analyze` no pudo ejecutarse en esta sesion porque el entorno rechazo la aprobacion externa por limite de uso. El codigo compila y la build frontend pasa; queda recomendado probar manualmente con FastAPI local en `http://127.0.0.1:8010`.

## Criterio De Demo

La experiencia esta lista para demo institucional controlada si:

- FastAPI esta activo en `8010`.
- `outputs/cross_domain_validation_results.json` existe.
- El usuario carga uno de los tres DOCX validados o selecciona un caso demo.

## Siguientes Pasos

1. Ejecutar prueba manual de upload en navegador.
2. Agregar version PDF del reporte ejecutivo.
3. Conectar persistencia opcional para guardar analisis institucionales revisados.
4. Agregar control de acceso cuando auth sea parte estable del flujo demo.
