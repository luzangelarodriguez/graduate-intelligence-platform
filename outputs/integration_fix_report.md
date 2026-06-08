# Reporte de Integración — Nuevos Conectores Colombianos
**Fecha:** 2026-06-08  
**Archivos modificados:** 3  
**Correcciones aplicadas:** 4 de 5

---

## RESUMEN EJECUTIVO

| # | Corrección | Estado | Archivo |
|---|---|---|---|
| 1 | Agregar 4 fuentes a CRAWLER_TARGETS | ✅ Aplicado | `academic_job_acquisition.py` |
| 2 | Queries en español para portales colombianos | ✅ Aplicado | `academic_job_acquisition.py` |
| 3 | ScraperAdapterCrawler + 4 conectores en make_connector() | ✅ Aplicado | `crawlers/connectors/api_wrappers.py` |
| 4 | Selector de detalle en ElempleoConnector | ✅ Aplicado | `scrapers/connectors/elempleo_connector.py` |
| 5 | language_hint="es" en extract_semantic_job_skills | ⏭️ Omitido | `ml/labor/semantic_job_skill_extractor.py` |

---

## DETALLE POR CORRECCIÓN

### Corrección 1 — CRAWLER_TARGETS ampliado
**Archivo:** `graduate_intelligence_platform/backend/app/academic_job_acquisition.py`

Se agregaron 4 fuentes al tuple `CRAWLER_TARGETS`:
```python
# Antes
CRAWLER_TARGETS = ("linkedin", "elempleo", "ticjob", "indeed", "jooble", "hireline", "findjobit", "criminology")

# Después
CRAWLER_TARGETS = (
    "linkedin", "elempleo", "ticjob", "indeed", "jooble",
    "hireline", "findjobit", "criminology",
    "computrabajo", "magneto", "torre", "spe",   # ← NUEVO
)
```

Adicionalmente se definió la constante `_COLOMBIAN_PORTALS` (frozenset) para centralizar qué fuentes son portales colombianos, evitando duplicación en `_source_payload`.

---

### Corrección 2 — Queries en español para portales colombianos
**Archivo:** `graduate_intelligence_platform/backend/app/academic_job_acquisition.py` — función `_source_payload()`

**Antes:**
```python
elif source in {"elempleo", "ticjob", "hireline", "findjobit", "criminology"}:
    payload["search_terms"] = keywords[:keyword_limit]
```

**Después:**
```python
elif source in _COLOMBIAN_PORTALS:
    payload["search_terms"] = keywords[:keyword_limit]
    # Spanish-first query for Colombian portals: build from existing keywords (already in Spanish)
    payload["query_es"] = _build_query(keywords[:8])
```

**Razonamiento:** Los `keywords` ya están en español (provienen del currículo académico). `query_es` usa los 8 primeros keywords con el formato `OR` de `_build_query`, preferido por motores de búsqueda colombianos. El `ScraperAdapterCrawler` usa `query_es` en primer lugar antes de caer a `query`.

---

### Corrección 3 — ScraperAdapterCrawler y 4 nuevos conectores
**Archivo:** `crawlers/connectors/api_wrappers.py`

**Nuevos imports agregados:**
```python
from scrapers.sources.computrabajo_scraper import scrape_jobs as _computrabajo_scrape
from scrapers.sources.magneto_api_scraper import scrape_jobs as _magneto_scrape   # usa API, no Playwright
from scrapers.sources.torre_scraper import scrape_jobs as _torre_scrape
from scrapers.sources.spe_scraper import scrape_jobs as _spe_scrape
```

**Clase `ScraperAdapterCrawler` (nueva):**
- Adapta funciones `scrape_jobs(query) -> list[dict]` al protocolo `run() -> tuple[results, errors]`
- Usa `query_es` del `source_plan` antes de `query` (preferencia español)
- Fallback de query: `" ".join(keywords[:3])` o `"analista datos"`
- Construye HTML inline por job y lo pasa a `EnterpriseAgenticJobExtractor.inspect_detail_html()`
- Si `execute_network=False`, retorna vacío sin error (modo dry-run seguro)

**Nota sobre magneto:** Se usa `magneto_api_scraper` (que consume la API REST de Magneto365) en lugar de `magneto_scraper` (Playwright). La versión API es más estable y no requiere browser headless.

**Nuevas ramas en `make_connector()`:**
```python
if source == "computrabajo":
    return ScraperAdapterCrawler(_computrabajo_scrape, "computrabajo", source_plan=plan)
if source == "magneto":
    return ScraperAdapterCrawler(_magneto_scrape, "magneto", source_plan=plan)
if source == "torre":
    return ScraperAdapterCrawler(_torre_scrape, "torre", source_plan=plan)
if source == "spe":
    return ScraperAdapterCrawler(_spe_scrape, "spe", source_plan=plan)
```

---

### Corrección 4 — Selector de detalle en ElempleoConnector
**Archivo:** `scrapers/connectors/elempleo_connector.py` — método `extract_from_html()`

**Antes:**
```python
title_node = card.select_one("h1,h2,h3,a[href*='oferta'],[class*='title'],[class*='cargo']")
link = card.select_one("a[href]")
```

**Después:**
```python
title_node = card.select_one("h1,h2,h3,a[href*='detalle-oferta'],[class*='title'],[class*='cargo']")
link = card.select_one("a[href*='detalle-oferta']") or card.select_one("a[href]")
```

**Problema corregido:** El selector `a[href*='oferta']` coincidía con URLs de páginas de búsqueda (`/co/ofertas-empleo/`) en lugar de páginas de detalle. Las URLs de detalle en Elempleo tienen el patrón `/co/detalle-oferta/...`. El nuevo selector prioriza el link de detalle correcto y hace fallback a cualquier `a[href]` si no encuentra ninguno.

---

### Corrección 5 — language_hint="es" en extract_semantic_job_skills
**Estado: OMITIDA — condición no se cumple**

**Motivo:** La función `extract_expanded_labor_skills` en `ml/labor/labor_skill_taxonomy_expanded.py` tiene la firma:
```python
def extract_expanded_labor_skills(text: str, *, section: str = "description") -> list[ExpandedLaborSkill]:
```

No acepta el parámetro `language_hint`. La instrucción dice **"solo si el parámetro existe"** — al no existir en la función subyacente, agregar `language_hint` a `extract_semantic_job_skills` y pasarlo a `extract_expanded_labor_skills` causaría un `TypeError`. Corrección omitida correctamente.

**Acción recomendada futura:** Si se agrega soporte de `language_hint` a `extract_expanded_labor_skills`, actualizar `extract_semantic_job_skills` así:
```python
def extract_semantic_job_skills(
    *,
    ...
    language_hint: str | None = None,
) -> list[SemanticSkillEvidence]:
    ...
    expanded.extend(extract_expanded_labor_skills(fragment, section=section, language_hint=language_hint))
```

---

## ANÁLISIS DE IMPACTO

| Componente | Impacto | Riesgo |
|---|---|---|
| `CRAWLER_TARGETS` | Los 4 nuevos portales generan `source_plans` en `build_academic_job_acquisition_intelligence()` | Bajo — solo agrega keys al dict |
| `_source_payload` con `_COLOMBIAN_PORTALS` | Refactor limpio — usa frozenset en lugar de set literal duplicado | Bajo — lógica idéntica para fuentes existentes |
| `query_es` en payload | Campo nuevo en source_plan; sin cambios en conectores existentes | Bajo — campo ignorado si el conector no lo lee |
| `ScraperAdapterCrawler` | Clase nueva aislada; no modifica código existente | Bajo — solo se activa si `make_connector("computrabajo/magneto/torre/spe")` es llamado |
| Elempleo selector fix | Cambia selector de links en tarjetas de Elempleo | Medio — si Elempleo cambia estructura HTML puede romper; pero es corrección necesaria |

---

## DEPENDENCIAS VERIFICADAS

| Import | Origen | ¿Existe? |
|---|---|---|
| `scrapers.sources.computrabajo_scraper.scrape_jobs` | `scrapers/sources/computrabajo_scraper.py` | ✅ |
| `scrapers.sources.magneto_api_scraper.scrape_jobs` | `scrapers/sources/magneto_api_scraper.py` | ✅ |
| `scrapers.sources.torre_scraper.scrape_jobs` | `scrapers/sources/torre_scraper.py` | ✅ |
| `scrapers.sources.spe_scraper.scrape_jobs` | `scrapers/sources/spe_scraper.py` | ✅ |
| `EnterpriseAgenticJobExtractor` | `agents/agentic_job_extractor.py` (ya importado) | ✅ |
| `_COLOMBIAN_PORTALS` | Definido en el mismo archivo | ✅ |

---

*Reporte generado: 2026-06-08*
