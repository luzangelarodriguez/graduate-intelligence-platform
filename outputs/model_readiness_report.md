# Model Readiness Report

## Resumen Ejecutivo

La validación funcional multi-dominio procesó 4 microcurrículos reales y mantiene el motor en readiness `medio` para piloto institucional controlado. No se entrenó modelo final con esta muestra; los documentos se usan como evidencia de validación y como base para construir una matriz Gold humana.

## Documentos Usados

- `aprendizaje automatico.docx`
- `ADE _S.5 _B. 1 _Gerencia Financiera.docx`
- `Diseño de proyectos orientados a la innovación.docx`
- `Anexo 3.1 Microcurriculos - Esp_ing_Software.pdf`

## Dominios Cubiertos

- `analitica/inteligencia_artificial`
- `management/finanzas`
- `management/innovacion`
- `ti/ingenieria_software`

## Métricas

- Precision aproximada: `0.9773`
- Recall aproximado: `1.0`
- Contaminación disciplinar: `0.0227`
- Coherencia de recomendaciones: `1.0`
- Cobertura taxonómica: `1.0`
- Separación de competencias transversales: `0.5`

## Riesgo De Sobreajuste

Riesgo `medio`: la muestra ya cubre 4 subdominios relevantes, pero sigue siendo pequeña. No se recomienda entrenar ni calibrar un modelo final hasta contar con matriz humana validada y mayor diversidad documental por dominio.

## Estado Del Gold Dataset

Se generó `ml/datasets/curriculum_gold_dataset.csv` desde `outputs/human_validation_matrix.csv`. Como la matriz todavía no tiene validación humana marcada en `is_correct`, el dataset Gold queda con encabezados y `0` filas validadas. Este comportamiento es intencional para evitar entrenar con datos no aprobados.

## Criterio Para Piloto

Listo para demo ejecutiva y piloto controlado si:

- Las recomendaciones son revisadas por comité académico antes de uso formal.
- La matriz humana empieza a poblar `is_correct`, `correction` y `recommendation_is_correct`.
- No se conecta evidencia laboral no Gold al KPI institucional.

