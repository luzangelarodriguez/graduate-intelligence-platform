# Enterprise Labor Intelligence Phase 1

## Objetivo

Crear la base enterprise del motor laboral para que la plataforma priorice calidad del dato, taxonomia disciplinar, normalizacion semantica, deduplicacion, embeddings y matching contextual antes de seguir ampliando dashboards.

## Estructura creada

```text
scrapers/
  sources/
    base.py
    computrabajo_scraper.py
    elempleo_scraper.py
    magneto_scraper.py
    spe_scraper.py
    torre_scraper.py
  normalization/
    classify_domains.py
    deduplicate_jobs.py
    normalize_roles.py
    normalize_skills.py
  taxonomy/
    domain_taxonomy.py
    skills_master_loader.py
  pipelines/
    jobs_pipeline.py
    semantic_matching_pipeline.py
  embeddings/
    generate_embeddings.py
database/
  enterprise_labor_intelligence_schema.sql
```

## PostgreSQL

Migracion aditiva y no destructiva:

- `domains`
- `skills_master`
- `skills_alias`
- ampliacion segura de `empleos`
- ampliacion segura de `empleo_skills`

La tabla `empleos` conserva compatibilidad con el backend existente e incorpora:

- `portal`
- `titulo_normalizado`
- `empresa`
- `ciudad`
- `modalidad`
- `salario`
- `descripcion`
- `seniority`
- `sector`
- `dominio`
- `fecha_publicacion`
- `url`
- `hash_contenido`
- `embedding`
- `created_at`

La tabla `empleo_skills` incorpora:

- `skill_original`
- `skill_normalized`
- `skill_domain`
- `tipo_skill`
- `confianza_extraccion`

## Taxonomia disciplinar

Dominios iniciales:

- ambiental
- energia
- legal
- legal-tech
- salud
- educacion
- marketing
- ti
- cybersecurity
- analitica
- finanzas
- logistica
- gestion_humana
- management

Regla critica implementada:

`Especializacion en Gestion Ambiental y Energetica` se clasifica como `ambiental` con dominio secundario `energia`.

Con dominio `ambiental`, la normalizacion admite:

- sostenibilidad
- ESG
- ISO 14001
- huella de carbono
- eficiencia energetica
- energias renovables

y bloquea contaminacion desde:

- backend
- fullstack
- ciberseguridad
- desarrollo web

## Scrapers laborales

Se crearon adaptadores Playwright para:

- Servicio Publico de Empleo
- Computrabajo Colombia
- El Empleo
- Magneto
- Torre

Todos usan una capa comun:

- retries basicos por fuente
- espera `networkidle`
- paginacion por selector `next`
- extraccion de detalle
- captura de screenshots de error
- normalizacion de titulo, dominio y skills

Nota operativa: los portales laborales suelen cambiar selectores y pueden aplicar controles anti-bot. Los adaptadores estan listos para ajuste fino por fuente sin modificar el pipeline central.

## Pipeline laboral

Entrada:

- scraping live por fuente
- o fixture CSV/JSON

Proceso:

1. extraccion
2. normalizacion de cargo
3. clasificacion disciplinar
4. extraccion de skills con filtro de dominio
5. hash de contenido
6. deduplicacion
7. export CSV
8. upsert PostgreSQL

Comando base:

```powershell
python scrapers\pipelines\jobs_pipeline.py --sources spe computrabajo elempleo --query "sostenibilidad ESG eficiencia energetica" --limit 100
```

Modo seguro sin base de datos:

```powershell
python scrapers\pipelines\jobs_pipeline.py --fixture outputs\jobs_sample.json --skip-db
```

## Embeddings

Modulo preparado:

```powershell
python scrapers\embeddings\generate_embeddings.py --limit 250
```

Modelo por defecto:

- `intfloat/multilingual-e5-large`

Alternativa recomendada:

- `BAAI/bge-m3`

La fase actual guarda embeddings como `JSONB`. En una fase posterior se recomienda migrar a `pgvector` para busqueda ANN y ranking semantico en PostgreSQL.

## Matching contextual

Scoring implementado:

- 35% similitud semantica
- 20% skills compartidas
- 15% herramientas
- 10% demanda de mercado
- 10% benchmark universitario
- 10% tendencias emergentes

Antes de calcular score se valida compatibilidad disciplinar. Si un empleo TI se cruza contra un programa ambiental/energetico incompatible, el score queda en `0.0`.

## Verificacion realizada

- `py_compile` en todos los modulos nuevos.
- Migracion PostgreSQL aplicada sin `DROP`.
- Carga de catalogo maestro:
  - 14 dominios
  - 36 skills canonicas
  - 102 aliases
- Prueba critica:
  - `Gestion Ambiental y Energetica` => `ambiental`, secundario `energia`
  - extraccion devuelve ESG, ISO 14001, huella de carbono, eficiencia energetica y renovables
  - backend/fullstack/ciberseguridad quedan filtrados
- Matching cruzado ambiental vs TI devuelve score `0.0`.

## Riesgos tecnicos

- Los selectores de portales laborales deben validarse con corrida live por cada fuente.
- Algunos portales pueden requerir APIs internas o consentimiento de uso para extraccion masiva.
- `sentence-transformers` requiere descarga de modelo y recursos de memoria.
- La tabla legacy `empleo_skills` aun convive con joins por `skill_id`; la nueva normalizacion canonica debe armonizarse gradualmente con esas vistas.

## Proximos pasos

1. Ejecutar corrida controlada por fuente con `limit` bajo.
2. Identificar APIs XHR internas de cada portal y priorizar ingestion directa cuando exista.
3. Ampliar taxonomia por facultad/programa UNIR.
4. Migrar embeddings a `pgvector`.
5. Crear vista `vw_empleos_semanticos` para no romper vistas legacy.
6. Reentrenar o recalibrar `ml/ml_match_program_jobs.py` para consumir `dominio`, `skill_normalized` y `embedding`.
7. Agregar tests automatizados de no contaminacion disciplinar.

