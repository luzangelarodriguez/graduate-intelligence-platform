# Matching Rebalance Implementation

## Resumen

Se rebalanceó el motor de matching para recuperar recomendaciones útiles sin reintroducir el filtro excesivo anterior.

Cambios aplicados:
- `backend/queries.py`
  - nueva lógica de `passes_skill_threshold`
  - nueva fórmula de `match_score`
  - corrección de columnas reales del esquema `empleos` para recomputar vistas en PostgreSQL
- `backend/services/program_market_matching_service.py`
  - misma política de aceptación y score compuesto en el servicio de matching
  - priorización de vecinos con `domain_factor >= 0.5`

## Reglas aplicadas

- `match_score = (base_similarity_score * 0.50) + (coverage_score * 0.30) + (domain_score * 20)`
- `domain_score = 1.0`:
  - permitido con `skills_en_comun >= 1`
- `domain_score >= 0.5`:
  - permitido con `skills_en_comun >= 2`
- `domain_score = 0.1`:
  - excluido automáticamente si `skills_en_comun < 3`

## Validación real en PostgreSQL

Después de recomputar las vistas:
- `vw_match_empleo_especializacion`: `6307`
- `vw_match_empleo_especializacion_positivo`: `176`
- `vw_program_recommended_jobs`: `176`
- `vw_program_market_alignment`: `53`

## Comparativa antes vs después

### Total recomendaciones
- Antes: `2`
- Después: `176`
- Incremento absoluto: `+174`

### Lectura funcional
- El cuello de botella de persistencia se recuperó.
- El motor dejó de estar sobre-restringido.
- La salida volvió a mostrar recomendaciones por programa con señales útiles.

## Ejemplos reales por programa

### Revisoría Fiscal
Programa: `Especialización en Revisoría Fiscal y Auditoría de Cuentas`

Top recomendaciones reales:
- `Técnico de Soporte`
- `Ingeniero de Integración y Desarrollo`
- `Gestor de Activos TI`
- `Corporate Counsel`
- `Senior Full Stack (Back-end oriented) (Node.js) Developer/Architect`
- `QA Coordinador / Líder de Pruebas`
- `Financial Controller`

Observación:
- El set ya recupera `Financial Controller`.
- No aparecen recomendaciones de IA, Data o Analytics en este bloque.

### Inteligencia de Negocio
Programa: `Especialización en Inteligencia de Negocio`

Top recomendaciones reales:
- `Desarrollador`
- `Analista de Soporte de Aplicaciones`
- `ingeniero en seguridad`
- `analista de datos`
- `analista de datos`

Observación:
- El corpus laboral ya contiene títulos afines como `BI Analyst` y `Data Analyst`.
- La salida activa del programa ya volvió a producir matches de analítica y SQL.

### Seguridad Informática
Programa: `Especialización en Seguridad Informática`

Top recomendaciones reales:
- `Data Protection Officer`
- `Desarrollador Full Stack`
- `Ingeniero Residente de Redes y Ciberseguridad`
- `Cybersecurity Analyst`
- `Compliance Officer`

Observación:
- El set recupera señales correctas de ciberseguridad y compliance.
- `Lider SOC` también existe en el corpus laboral real.

### Criminología
Programa: `Especializaci?n en Criminolog?a`

Resultado real:
- No se recuperaron recomendaciones en el corpus `empleos` consultado por esta ruta.

Observación:
- Esto apunta a una brecha de cobertura del corpus actual para ese dominio en la ruta usada por el motor.
- El rebalance de scoring no puede inventar empleos que no están en la base consultada.

## Riesgo residual

- `176` recomendaciones quedan por encima del rango objetivo aproximado `50-150`.
- La salida actual es funcional y mucho menos restrictiva que antes.
- Criminología sigue dependiendo de cobertura de corpus para mostrar recomendaciones.

## Estado final

- Rebalance aplicado.
- Vistas recompiladas en PostgreSQL real.
- Validación funcional ejecutada.
