# Product Demo Readiness

## Qué Está Listo

- Backend FastAPI oficial con endpoint consolidado `POST /api/microcurriculum/analyze`.
- Contrato semántico separado para skills técnicas, transversales, metodologías, herramientas, plataformas, bases de datos, cloud providers y frameworks.
- Corrección de brechas falsas: una entidad detectada en el currículo ya no se reporta como `real_market_gap`; pasa a `strengthening_area` si también aparece como señal de mercado.
- Frontend ejecutivo en `graduate_intelligence_platform/frontend` con lenguaje institucional en español y estilo visual alineado a UNIR.
- Recommendation Engine por subdominio con recomendaciones accionables para `analitica/inteligencia_artificial`, `management/innovacion`, `management/finanzas` y `ti/ingenieria_software`.
- Validación multi-dominio con 4 documentos reales y readiness `medio`.

## Qué Falta

- Poblar manualmente `outputs/human_validation_matrix.csv` para construir un Gold Dataset humano real.
- Ampliar muestra por dominio: ambiental, derecho, educación y más documentos por analítica, gerencia y TI.
- Completar release gates Gold para fuentes laborales antes de usar scraping como evidencia institucional productiva.
- Agregar revisión de comité académico sobre recomendaciones antes del piloto formal.

## Riesgos

- Muestra documental todavía pequeña para entrenamiento final.
- `transversal_skill_separation_quality` quedó en `0.5`; conviene revisar aliases y reglas para competencias transversales.
- La evidencia laboral Gold todavía no está suficientemente poblada para alimentar KPIs institucionales principales.
- Magneto tiene evidencia Silver, pero no debe alimentar recomendaciones sin Gold/release gate.

## Criterios De Demo

- El frontend debe levantar en `http://127.0.0.1:5173/`.
- El backend debe responder en `http://127.0.0.1:8010/api/health`.
- La demo debe mostrar: resumen ejecutivo, puntaje de pertinencia, dominio/subdominio, confianza curricular, fortalezas detectadas, brechas reales, áreas a fortalecer y recomendaciones curriculares.
- No deben aparecer Docker/React/Kubernetes como recomendaciones de finanzas o innovación.

## Criterios De Piloto

- Al menos 3 documentos validados por dominio prioritario.
- Matriz humana con correcciones y aprobación de recomendaciones.
- `precision >= 0.75`, `recall >= 0.50`, contaminación disciplinar `< 0.10`.
- Recomendaciones explicables y revisadas por experto curricular.

## Criterios De Producción

- Gold Dataset humano versionado.
- Evaluación automática por release.
- Evidencia laboral exclusivamente Gold con lineage completo.
- Monitoreo de drift de skills y fuentes laborales.
- Trazabilidad KPI -> recomendación -> evidencia curricular -> evidencia laboral.

