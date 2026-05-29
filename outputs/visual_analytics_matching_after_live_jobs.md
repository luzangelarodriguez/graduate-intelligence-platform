# Visual Analytics Matching After Live Jobs

Fecha: 2026-05-26

## Resultado De La Corrida Viva

- Run ID: `visual-analytics-20260526152121-0825c11c`
- Quality score: `0.1500`
- Umbral de persistencia: `0.70`
- Decision: no persistir en PostgreSQL ni publicar a Gold.

## Efecto En Matching

No se recalcularon matches productivos con empleos vivos porque la compuerta de calidad bloqueó la persistencia. Esto evita contaminar el motor curricular con HTML incompleto, fuentes restringidas o vacantes sin evidencia suficiente.

## Evidencia Laboral Aceptada

- Empleos aceptados: 0
- Gold jobs validos: 0
- Skills laborales nuevas: 0
- Roles laborales nuevos: 0
- Duplicados suprimidos: 0

## Errores Y Hallazgos Por Fuente

- LinkedIn: fuente restringida/manual; requiere autenticación, partnership o API fallback.
- Servicio Público de Empleo: error SSL local al resolver certificado.
- Ticjob: se detectaron 4 elementos sin título; fueron descartados por `missing_title`.
- Computrabajo, Elempleo, Hireline, SENA, Mi Futuro Empleo y FindJobIT: no entregaron empleos aceptables con el parser HTML genérico en esta corrida.

## Dataset Y Matcher

Se reconstruyó el dataset controlado:

- Archivo: `ml/datasets/visual_analytics_match_training.jsonl`
- Registros: 1375

Evaluación controlada del matcher:

- Casos evaluados: 3
- Casos aprobados: 3
- Quality: 1.0

## Próximo Ajuste Recomendado

La extracción viva requiere conectores por fuente, no parser genérico:

1. Priorizar El Empleo API-first con `/api/joboffers/findbyfilter` y `/api/joboffers/getjoboffer`.
2. Resolver SPE mediante certificado confiable o endpoint oficial documentado.
3. Para LinkedIn, mantener modo `restricted/manual/API-fallback`.
4. Crear parser específico para Ticjob antes de publicar evidencia.
5. Mantener release gate: no publicar a Gold si `quality_score < 0.70`.
