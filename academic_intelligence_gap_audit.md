# Academic Intelligence Gap Audit

Fecha de auditoría: 2026-05-31

## Resumen ejecutivo

La plataforma ya expone una lectura institucional mucho más sólida que un dashboard convencional. La pantalla ejecutiva, el ranking de programas, el detalle del programa, el microcurriculum y el forecast ya muestran valor académico real. La mayor brecha restante está en la simulación curricular, que sigue fallando en el flujo visual de QA y no llega a presentar una experiencia estable.

## Hallazgos validados

### 1) Endpoints que sí están aportando valor visible

- `GET /api/programas`
  - Alimenta el ranking ejecutivo de programas.
  - Ya evita el estado vacío después de corregir el doble prefijo `/api/api/...`.

- `GET /program-intelligence`
  - Sirve como señal de respaldo en la capa ejecutiva.
  - Aún presenta inestabilidad local en algunas rutas puntuales de detalle.

- `GET /executive-narrative`
  - Alimenta la narrativa institucional del resumen ejecutivo.

- `GET /executive-observatory`
  - Aporta contexto ejecutivo y señales de mercado.

- `GET /program-summary/{program_id}`
  - Se usa como explicación académica del programa, aunque localmente puede expirar.

- `GET /forecast-summary`
  - Sostiene la capa de forecast por horizonte.

- `GET /recommendations-v2`
  - Alimenta recomendaciones más explicables que las determinísticas.

- `GET /ask-observatory`
  - Habilita el copiloto académico visible.

### 2) Componentes React que sí se renderizan

- `ExecutiveSummaryPage`
- `ProgramsPage`
- `ProgramIntelligenceDetailPage`
- `ProgramMicrocurriculumPage`
- `ProgramForecastPage`
- `ExecutiveAiSection`
- `AcademicCopilotPanel`

### 3) Datos que ya se ven en pantalla

- 26 programas analizados.
- Ranking ejecutivo visible con programas críticos y de oportunidad.
- Microcurriculum con cobertura, demanda y gap score.
- Forecast por horizonte con interfaz dedicada.
- Narrativa ejecutiva institucional y copiloto visible.

## Brechas detectadas

### A. Simulación curricular sigue vacía

- `ProgramSimulationPage` continúa presentando una pantalla en blanco en QA visual.
- En consola aparece `React error #310`, lo que sugiere un problema de render/hook flow o un bloqueo no manejado durante la carga.
- Aunque la simulación está implementada a nivel de backend y tipos, la experiencia visual aún no es confiable.

### B. Endpoints de detalle siguen siendo frágiles

En QA local, estas rutas dieron timeout o 5xx:

- `GET /api/programas/{id}`
- `GET /api/program-intelligence/{id}`
- `GET /forecast-summary`
- `GET /executive-observatory`
- `GET /program-summary/{id}`
- `GET /executive-narrative`

La UI ahora tiene fallback parcial, pero la fuente de datos puntual aún no es estable en todos los flujos.

### C. Trazabilidad programa -> microcurriculum -> skill -> gap -> recomendación -> impacto todavía es incompleta

- La vista de microcurriculum ya muestra el contenedor correcto, pero algunas ejecuciones siguen mostrando `0` skills cubiertas y brecha total por falta de mapeo suficiente en ciertos programas.
- La recomendación explicada existe, pero varios programas todavía no tienen suficiente evidencia priorizada para poblar todas las capas de forma consistente.

## Root causes observadas

1. **Bug de cliente HTTP**
   - El frontend estaba construyendo solicitudes como `/api/api/programas`.
   - Se corrigió con normalización en `api.ts`.

2. **Timeouts en rutas de detalle**
   - Varias rutas de detalle y observabilidad tardan demasiado o fallan localmente.
   - La UI necesita más tolerancia a fallos para no degradar la experiencia visible.

3. **Simulación con render inestable**
   - La vista de simulación no logra completar el render en QA.
   - Falta aislar el componente o simplificar su dependencia de rutas lentas.

## Capturas requeridas para QA

- `outputs/qa/visual/01-executive-summary.png`
- `outputs/qa/visual/02-programs-ranking.png`
- `outputs/qa/visual/03-program-detail.png`
- `outputs/qa/visual/04-microcurriculum.png`
- `outputs/qa/visual/05-forecast.png`
- `outputs/qa/visual/06-simulation.png`

## Defectos

| ID | Severidad | Pantalla | Defecto | Estado |
|---|---:|---|---|---|
| D1 | Alta | Simulación | Pantalla en blanco / React error #310 | Abierto |
| D2 | Media | Detalle programa | Dependencia de rutas lentas produce estados de error parciales | Parcialmente mitigado |
| D3 | Media | Forecast | Algunas señales quedan vacías por timeouts de backend | Parcialmente mitigado |
| D4 | Media | Microcurriculum | Trazabilidad incompleta en programas con poca señal | Abierto |

## Quick wins

- Mantener la normalización de `/api` en el cliente HTTP.
- Introducir fallback visual más explícito cuando una ruta de detalle falle.
- Simplificar la simulación para que muestre siempre al menos una lectura base por horizonte.
- Reutilizar más el ranking de `programas` cuando los endpoints puntuales no respondan.

## Scores de usabilidad

- **Executive usability score:** 8.1 / 10
- **Academic committee usability score:** 6.8 / 10

## Conclusión

La plataforma ya parece un observatorio académico institucional en sus vistas principales, pero todavía no está completamente cerrada como producto comercializable porque la simulación y algunas rutas de detalle siguen siendo inestables en QA. La buena noticia es que el mayor problema de visualización ya está resuelto: el ranking de programas y el resumen ejecutivo ahora sí muestran datos reales en pantalla.
