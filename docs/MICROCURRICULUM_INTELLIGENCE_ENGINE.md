# Microcurriculum Intelligence Engine

## Objetivo

Esta fase crea una capa enterprise para convertir microcurrículos oficiales en evidencia estructurada de pertinencia académica:

```text
PDF/DOCX/TXT -> extracción texto -> parsing académico -> skills -> matching laboral -> gaps -> recomendaciones -> PostgreSQL
```

No reemplaza pipelines existentes. Reutiliza taxonomía, aliases, clasificador disciplinar, embeddings y tablas laborales.

## Estructura

```text
microcurriculum_engine/
  ingestion/
  extraction/
  parsing/
  normalization/
  matching/
  recommendations/
  embeddings/
  storage/
  pipelines/
  evaluation/
```

## Flujo NLP

1. **Ingesta documental**
   - Guarda documentos originales en `storage/microcurriculos/`.
   - La carpeta está ignorada por Git para evitar subir PDFs oficiales.

2. **Extracción de texto**
   - PDF: `pdfplumber` primero, `PyMuPDF` como fallback.
   - DOCX: `python-docx` si está disponible.
   - TXT/MD/CSV: lectura directa UTF-8.
   - PDF imagen: queda marcado como `ocr_required` para OCR futuro.

3. **Limpieza**
   - Normalización Unicode.
   - Eliminación básica de headers/footers repetidos.
   - Compactación de whitespace.

4. **Parsing académico**
   - Programa.
   - Asignatura.
   - Semestre.
   - Créditos.
   - Competencias.
   - Resultados de aprendizaje.
   - Contenidos.
   - Metodologías.
   - Bibliografía.
   - Herramientas/plataformas/software.

5. **Extracción y normalización de skills**
   - Reutiliza `scrapers.normalization.normalize_skills`.
   - Reutiliza aliases de `scrapers.taxonomy.domain_taxonomy`.
   - Reutiliza `ml.inference.domain_classifier`.
   - Añade patrones documentales para plataformas, metodologías y frameworks.

6. **Matching laboral**
   - Cruza skills del microcurrículo contra `empleo_skills` y `empleos`.
   - Si PostgreSQL no está disponible, usa fallback controlado por dominio.

7. **Gap analysis**
   - Skills faltantes.
   - Skills débiles.
   - Skills con baja señal laboral.

8. **Recomendaciones**
   - Genera recomendaciones explicables con evidencia laboral.
   - Incluye confidence y evidence payload.

9. **Scoring**
   - Pertinencia curricular.
   - Cobertura de skills mercado.
   - Modernización tecnológica.
   - Alineación laboral.
   - Riesgo de obsolescencia.

10. **Embeddings**
   - Usa `all-MiniLM-L6-v2` cuando `sentence-transformers` está disponible.
   - Usa fallback TF-IDF compatible con pruebas locales.
   - Deja listo el payload para `pgvector`.

## Tablas Nuevas

- `microcurriculos`
- `microcurriculo_asignaturas`
- `microcurriculo_skills`
- `microcurriculo_competencias`
- `microcurriculo_plataformas`
- `microcurriculo_herramientas`
- `microcurriculo_embeddings`
- `microcurriculo_market_gaps`
- `microcurriculo_recommendations`
- `microcurriculo_processing_runs`

Todas incluyen trazabilidad mediante `source_document`, `confidence_score`, `lineage`, `created_at` y metadata asociada.

## Pipeline

```powershell
python -m microcurriculum_engine.pipelines.process_microcurriculum path\microcurriculo.pdf
```

Modo sin persistencia:

```powershell
python -m microcurriculum_engine.pipelines.process_microcurriculum path\microcurriculo.txt --no-persist
```

## Endpoints FastAPI

- `POST /api/microcurriculum/upload`
- `GET /api/microcurriculum/{id}`
- `GET /api/microcurriculum/{id}/skills`
- `GET /api/microcurriculum/{id}/gaps`
- `GET /api/microcurriculum/{id}/recommendations`
- `GET /api/microcurriculum/{id}/scores`

El upload soporta:

- `multipart/form-data` si `python-multipart` está instalado.
- Body binario directo con header `x-filename`.

## Ejemplo

Entrada de microcurrículo:

```text
Asignatura: Desarrollo de Aplicaciones Web
Competencias: Diseñar servicios backend con Python y SQL.
Contenidos: React, Docker, REST API.
Metodologías: Scrum, Agile.
```

Salida esperada:

```json
{
  "skills": ["python", "sql", "react", "docker", "rest api", "scrum", "agile"],
  "gaps": {
    "missing_skills": ["devops"]
  },
  "scores": {
    "alineacion_laboral": 0.0,
    "pertinencia_curricular": 0.0
  }
}
```

## Riesgos

- PDFs escaneados requieren OCR real en la siguiente fase.
- El matching productivo depende de estabilidad de empleos Gold y `empleo_skills`.
- Las recomendaciones actuales son explicables y determinísticas; aún no usan generación LLM.
- Los embeddings se guardan como JSONB hasta activar `pgvector`.

## Próximos Pasos

1. Instalar dependencias documentales opcionales:
   - `pdfplumber`
   - `PyMuPDF`
   - `python-docx`
   - OCR: `pytesseract` o servicio OCR gestionado.
2. Crear evaluación con microcurrículos oficiales anotados.
3. Conectar gaps contra `gold_validated_jobs` y señales temporales.
4. Activar `pgvector` para búsqueda semántica institucional.
5. Crear workflow batch para procesar carpetas completas de microcurrículos.
