# Scraping Gold Quality Report

## Regla De Gobierno

Ningún dato laboral debe alimentar recomendaciones curriculares si no pasa la cadena:

`bronze -> silver -> gold -> relevance_score -> release_gate`

La evidencia de mercado usada para demo debe mantenerse desacoplada del KPI institucional principal hasta que cada fuente tenga calidad Gold verificable.

## Estado Por Fuente

| Fuente | Estado | Jobs reales | Jobs descartados | Razón de descarte | Señales SEO | Confidence promedio | Gold jobs válidos |
|---|---:|---:|---:|---|---|---:|---:|
| El Empleo | `degraded_no_jobs` | 0 | 0 | Pipeline Gold API-first creado, pero los snapshots locales no publicaron jobs Gold válidos en la última corrida inspeccionada. | No concluyente | 0.00 | 0 |
| Magneto | `silver_candidate` | 114 | 0 | Hay extracción API-first en Silver con relevance_score; requiere release gate explícito antes de alimentar recomendaciones institucionales. | Bajo en API, revisar payloads de listado | Pendiente de agregación | 0 |
| Computrabajo | `degraded_no_jobs` | 0 | 0 | Fuente disponible como scraper/config, sin evidencia local Gold válida inspeccionada. | Posible `seo_noise` en páginas de categoría | 0.00 | 0 |
| SPE | `degraded_no_jobs` | 0 | 0 | Fuente registrada para discovery/scraping, sin snapshots Gold válidos inspeccionados. | No concluyente | 0.00 | 0 |
| Torre | `blocked_auth` | 0 | 0 | Fuente priorizada para discovery, pero se considera no apta para Gold hasta resolver acceso/API estable. | No concluyente | 0.00 | 0 |

## Hallazgos

- `scrapers/lakehouse/silver/magneto_api/.../normalized_jobs.json` contiene evidencia Silver para Magneto, pero no debe alimentar recomendaciones sin publicación Gold y release gate.
- `scrapers/lakehouse/gold/elempleo/.../gold_publication_summary.json` existe, pero la inspección local indica `0` publicaciones válidas.
- Computrabajo, SPE y Torre deben permanecer fuera de recomendaciones institucionales hasta evidenciar payloads reales, relevancia suficiente y control anti-SEO.

## Recomendaciones

- Priorizar el cierre del release gate para Magneto API-first.
- Reintentar El Empleo Gold Pipeline con auditoría de request/response y logging de rechazo.
- Marcar categorías, páginas SEO y listados genéricos como `seo_noise`.
- Exigir `confidence_avg >= 0.75`, `gold_jobs_validos > 0` y trazabilidad Bronze/Silver/Gold antes de habilitar fuente en recomendaciones.

