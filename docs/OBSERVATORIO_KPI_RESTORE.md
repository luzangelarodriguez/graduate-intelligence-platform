# Restauracion de KPIs Ejecutivos - Observatorio UNIR

## Objetivo

Restaurar la primera vista del dashboard para que vuelva a comunicar una narrativa ejecutiva de Observatorio Institucional UNIR, usando los datos actuales del analisis de microcurriculos de la Especializacion en Visual Analytics y Big Data.

La pantalla ya no inicia con cards tecnicas de diagnostico. Ahora prioriza:

- contexto institucional del programa activo
- franja ejecutiva de estado curricular
- lectura estrategica del indice de pertinencia curricular
- cinco KPIs ejecutivos orientados a decision academica

## KPIs restaurados

### Franja ejecutiva superior

1. **Estado curricular**
   - Fuente: puntaje de pertinencia curricular.
   - Regla:
     - Alta: score >= 75
     - Media: score >= 60 y < 75
     - Baja: score < 60

2. **Recomendacion academica**
   - Texto ejecutivo:
     "Brecha emergente: el mercado esta pidiendo competencias que el programa no cubre con suficiente fuerza."
   - Se mantiene como lectura institucional breve para comite academico.

3. **Alineacion actual**
   - Fuente: `score_percent.pertinencia_curricular` o score consolidado disponible.
   - Formato: porcentaje ejecutivo.

### Bloque principal

**Lectura estrategica**

- Titulo: Lectura estrategica.
- Subtitulo: Indice de pertinencia curricular.
- Texto:
  "El programa registra {score}% de alineacion curricular consolidada con base en los microcurriculos procesados."
- Visual:
  - porcentaje grande
  - barra horizontal azul de avance

### Cards KPI ejecutivas

1. **Skills criticas faltantes**
   - Fuente: `real_market_gaps.length`.
   - Texto: "Competencias de mercado con baja cobertura curricular."

2. **Roles laborales con alta demanda**
   - Fuente: evidencia laboral Gold futura.
   - Estado actual: "Pendiente".
   - Texto: "Pendiente de validacion laboral Gold."

3. **Tendencia de empleabilidad**
   - Fuente: `score_percent.alineacion_laboral` cuando existe.
   - Fallback: "Pendiente".
   - Texto: "Mejor senal detectada en vacantes del programa."

4. **Cobertura de habilidades digitales**
   - Fuente: `score_percent.cobertura_skills_mercado`.
   - Fallback: "Pendiente".
   - Texto: "Herramientas y capacidades digitales del programa activo."

5. **Senal de actualizacion curricular**
   - Fuente: regla derivada de score y brechas.
   - Regla:
     - Alta: brechas criticas > 10 o pertinencia < 60%.
     - Media: pertinencia entre 60% y 75%.
     - Baja: pertinencia > 75%.
   - Texto: "Prioridad sugerida para revision academica."

## Mapeo de datos

| Dato API | Uso en dashboard |
| --- | --- |
| `score_percent.pertinencia_curricular` | Indice de pertinencia curricular y alineacion actual |
| `real_market_gaps.length` | Skills criticas faltantes |
| `score_percent.cobertura_skills_mercado` | Cobertura de habilidades digitales |
| `score_percent.alineacion_laboral` | Tendencia de empleabilidad |
| `documents_processed` | Resumen colapsado de microcurriculos procesados |
| `detected_domain` / `detected_subdomain` | Detalle inferior del analisis |
| `confidence` | Confianza del analisis curricular en detalle inferior |

## Cambios frontend

Archivos principales:

- `graduate_intelligence_platform/frontend/src/pages/MicrocurriculumDemoPage.tsx`
- `graduate_intelligence_platform/frontend/src/styles/index.css`

Cambios aplicados:

- Restaurada franja ejecutiva de tres cards.
- Restaurado bloque grande de lectura estrategica.
- Restauradas cinco cards KPI ejecutivas.
- Movidas las cards tecnicas hacia secciones inferiores de detalle.
- La lista de documentos queda colapsada por defecto con el texto "10 microcurriculos procesados" y accion "Ver documentos".
- Se mantiene el flujo de selector de especializacion y analisis de microcurriculos.
- Se mantiene el flujo de reescritura curricular y descarga de DOCX/matriz de trazabilidad.

## Pendientes

- Roles laborales con alta demanda queda como "Pendiente" hasta que exista evidencia laboral Gold validada y conectada al analisis del programa.
- La tendencia de empleabilidad depende de `alineacion_laboral`; si el backend no devuelve ese score, se muestra pendiente sin inventar evidencia.
- Se recomienda revisar acentos y copy final antes de demo formal si se decide estandarizar encoding y textos institucionales.

## Validacion

1. Abrir:
   `http://127.0.0.1:5173/`

2. Seleccionar:
   `Especializacion en Visual Analytics y Big Data`

3. Ejecutar:
   `Analizar microcurriculos`

4. Verificar:
   - aparece la franja ejecutiva: Estado curricular, Recomendacion academica, Alineacion actual
   - aparece el bloque Lectura estrategica con Indice de pertinencia curricular
   - aparecen las cinco cards KPI ejecutivas
   - no aparecen cards tecnicas como primera experiencia visual
   - los microcurriculos aparecen colapsados por defecto
   - las secciones inferiores siguen mostrando entidades, brechas, areas a fortalecer y microcurriculo propuesto

## Validacion tecnica ejecutada

- `npm run build`
- `python -m pytest tests`

Resultado:

- Build frontend exitoso.
- Suite de pruebas backend/ML/microcurriculum exitosa: 34 passed, 4 skipped.
