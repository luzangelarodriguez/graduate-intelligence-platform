# Labor Intelligence Stabilization

## Objetivo

Estabilizar la adquisicion de evidencia laboral antes de conectar el motor al KPI productivo institucional. Esta fase convierte el sistema desde scraper laboral hacia motor institucional de inteligencia laboral basada en evidencia confiable.

## Regla de gobierno

El motor laboral no queda conectado al KPI principal. Los datos producidos en esta fase son QA/DataOps y deben usarse para calibrar fuentes, taxonomia, confianza y drift.

## Implementacion

### 1. XHR/API discovery

Modulo creado:

```text
scrapers/quality/xhr_discovery.py
```

Comando:

```powershell
python scrapers\quality\xhr_discovery.py --sources computrabajo elempleo magneto torre --write-db
```

Salida:

```text
outputs/labor_intelligence_stabilization/xhr_endpoint_discovery.json
```

Resultado de la corrida:

- Total endpoints/recursos candidatos: `192`
- Magneto: `98`
- El Empleo: `82`
- Torre: `12`
- Computrabajo: `0` candidatos detectados en la corrida

Hallazgos relevantes:

- Magneto expone endpoints prometedores:
  - `https://api.magneto365.com/seo/v1/mega-menu/by-sector`
  - `https://api.magneto365.com/seo/v1/mega-menu/by-company`
  - `https://api.magneto365.com/jobs/v1/public/locations?term=all&country_id=47`
  - `https://api.magneto365.com/jobs/v1/vacancies/ia/suggested?...`
- El Empleo genero mucho trafico de analytics/ads y algunos recursos contextuales; requiere filtrado adicional para aislar endpoints de ofertas.
- Torre redirige fuertemente hacia accounts/analytics; no se detecto endpoint laboral directo util en esta corrida.
- Computrabajo no produjo endpoints XHR candidatos con la URL inspeccionada; requiere tracing manual o ajuste de URL/query.

Tabla PostgreSQL:

```text
public.xhr_endpoint_discovery
```

### 2. Source quality score

Tabla creada:

```text
public.source_quality_metrics
```

Campos principales:

- `source`
- `success_rate`
- `relevance_rate`
- `timeout_rate`
- `duplication_rate`
- `extraction_date`

Modulo:

```text
scrapers/quality/source_quality.py
```

Salida:

```text
outputs/labor_intelligence_stabilization/source_quality_metrics.json
```

Resultado inicial calculado desde `LABOR_ENGINE_VALIDATION_PHASE_1`:

| Fuente | Success rate | Relevance rate | Timeout rate | Duplication rate | Observacion |
|---|---:|---:|---:|---:|---|
| Computrabajo | 0.0000 | 0.0000 | 0.0000 | 0.0000 | Sin evidencia con selectores actuales |
| El Empleo | 0.3750 | 0.4474 | 1.0000 | 0.1316 | Mejor evidencia util, pero timeouts altos |
| Servicio Publico de Empleo | 0.7500 | 0.1667 | 0.0000 | 0.1754 | Bajo valor por falsos positivos institucionales previos |

Nota: SPE ya fue endurecido despues de la validacion para no aceptar la pagina `Inicio` como empleo.

### 3. Confidence score real

Modulo creado:

```text
scrapers/quality/confidence_score.py
```

El pipeline laboral ahora calcula:

- `confidence_score`
- `confidence_factors`

Factores:

- calidad fuente
- densidad de skills
- coherencia disciplinar
- disponibilidad de embeddings
- longitud descripcion
- fuerza de aliases/canonicos

Pesos iniciales:

- source quality: 20%
- skill density: 20%
- domain coherence: 25%
- embedding similarity/readiness: 10%
- description length: 15%
- alias strength: 10%

Columnas agregadas a `public.empleos`:

- `confidence_score`
- `confidence_factors`

### 4. Gold dataset

Tabla creada:

```text
public.validated_jobs_gold
```

Objetivo:

Guardar empleos manualmente aprobados como evidencia confiable para calibrar precision y entrenar reglas/ML.

Campos:

- `empleo_id`
- `dominio`
- `validado`
- `reviewer`
- `fecha`
- `observaciones`

Uso recomendado:

1. Tomar muestra por dominio.
2. Validar manualmente pertinencia.
3. Marcar `validado=true`.
4. Usar esa base como benchmark contra scrapers y scoring.

### 5. Drift detection

Modulo creado:

```text
scrapers/quality/drift_detection.py
```

Tabla creada:

```text
public.skill_drift_events
```

Salida:

```text
outputs/labor_intelligence_stabilization/skill_drift_events.json
```

Eventos iniciales:

- `derecho digital`
- `proteccion de datos`

Ambos aparecen como crecimiento en la muestra de derecho digital. Se deben confirmar con mas volumen antes de convertirlos en tendencia institucional.

## Dashboards QA internos

En esta fase no se construyo UI productiva. Los dashboards QA internos quedan representados por salidas auditables:

```text
outputs/labor_intelligence_stabilization/source_quality_metrics.json
outputs/labor_intelligence_stabilization/skill_drift_events.json
outputs/labor_intelligence_stabilization/xhr_endpoint_discovery.json
```

Estas salidas son suficientes para revision DataOps y pueden convertirse luego en dashboard interno separado del observatorio institucional.

## Umbrales recomendados antes de conectar KPI

No conectar una fuente al KPI institucional hasta cumplir:

- `relevance_rate >= 0.70`
- `timeout_rate <= 0.15`
- `duplication_rate <= 0.20`
- `confidence_score promedio >= 0.68`
- minimo `30` empleos validados por dominio en `validated_jobs_gold`
- cero falsos positivos institucionales tipo `Inicio`, menus o paginas de navegacion

## Riesgos actuales

- El Empleo ofrece evidencia util, pero la espera `networkidle` genera inestabilidad.
- Computrabajo requiere discovery mas profundo de DOM/API.
- Torre puede requerir autenticacion o endpoints no visibles sin sesion.
- Magneto parece el candidato mas prometedor para API directa.
- La taxonomia aun esta corta para gestion humana y educacion.

## Proximos pasos

1. Construir extractor API-first para Magneto usando endpoints `api.magneto365.com`.
2. Hacer tracing dedicado de El Empleo y aislar endpoint real de ofertas.
3. Crear una cola de revision manual para poblar `validated_jobs_gold`.
4. Ejecutar drift semanal por dominio.
5. Recalibrar pesos de confidence con el gold dataset.
6. Agregar reporte QA separado para `source_quality_metrics`.
7. Mantener el KPI institucional desconectado hasta estabilizar precision.
