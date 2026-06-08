# Auditoría del Estado Actual del Motor de Matching ML
**Proyecto:** Observatorio Institucional de Inteligencia Curricular  
**Fecha:** 2026-06-07  
**Alcance:** Inventario completo de modelos, pipelines, features y datasets

---

## 1. INVENTARIO DE ARCHIVOS ML

### 1.1 Motor Principal de Matching (PRODUCCIÓN ACTIVA)

| Archivo | Líneas | Estado | Rol |
|---|---|---|---|
| `backend/services/program_market_matching_service.py` | 863 | **ACTIVO** | Orquestador principal, KNN, scoring |
| `ml/ml_match_program_jobs.py` | 811 | **ACTIVO** | Matching basado en reglas |
| `backend/services/domain_taxonomy.py` | 533 | **ACTIVO** | Clasificación de dominio |
| `intelligence/domain_taxonomy_layer.py` | 150+ | **ACTIVO** | Taxonomía rica con subdomains |
| `backend/services/scoring_service.py` | — | **ACTIVO** | Funciones de scoring |
| `backend/repositories/matches_repository.py` | — | **ACTIVO** | Consultas de matching |

### 1.2 Embeddings y Semántica (PARCIALMENTE ACTIVO)

| Archivo | Estado | Observación |
|---|---|---|
| `ml/embeddings/embedding_service.py` | **ACTIVO (fallback)** | Usa TF-IDF si sentence-transformers no disponible |
| `ml/ner/semantic_matcher.py` | **ACTIVO** | Entidades semánticas con cosine similarity |
| `ml/semantic_matching/visual_analytics_matcher.py` | **ACTIVO** | Matcher híbrido para Visual Analytics |

### 1.3 Inteligencia Curricular (ACTIVO PARCIAL)

| Archivo | Estado | Observación |
|---|---|---|
| `ml/curriculum/curriculum_market_gap_engine.py` | **ACTIVO** | Gap analysis curricular |
| `ml/curriculum/curriculum_alignment_engine.py` | **ACTIVO** | Score de alineación |
| `ml/curriculum/specialization_curriculum_graph_engine.py` | **ACTIVO** | Estructura de grafo |
| `ml/curriculum/specialization_skill_affinity_engine.py` | **ACTIVO** | Afinidad de skills |
| `microcurriculum_engine/embeddings/micro_embeddings.py` | **ACTIVO** | Embeddings de microcurrículos |

### 1.4 Inteligencia del Mercado Laboral (ACTIVO)

| Archivo | Estado | Observación |
|---|---|---|
| `ml/labor/labor_market_skill_extraction_engine.py` | **ACTIVO** | Extracción de skills laborales |
| `ml/labor/market_skill_intelligence_engine.py` | **ACTIVO** | Inteligencia de mercado |
| `ml/labor/labor_skill_taxonomy_expanded.py` | **ACTIVO** | Taxonomía expandida de skills |
| `ml/labor/occupational_skill_cluster_engine.py` | **ACTIVO** | Clustering ocupacional |
| `ml/labor/semantic_job_skill_extractor.py` | **ACTIVO** | Extracción semántica de jobs |

### 1.5 Clustering e Inferencia (ACTIVO PARCIAL)

| Archivo | Estado | Observación |
|---|---|---|
| `ml/clustering/labor_cluster_engine.py` | **ACTIVO** | Clustering de empleos por cluster |
| `ml/inference/domain_classifier.py` | **ACTIVO** | Predicción de dominio con fallbacks |
| `ml/inference/curriculum_market_inference_pipeline.py` | **ACTIVO** | Pipeline end-to-end |

### 1.6 NER y Extracción de Entidades (ACTIVO)

| Archivo | Estado | Observación |
|---|---|---|
| `ml/ner/curriculum_entity_ruler.py` | **ACTIVO** | 50+ patrones NER basados en reglas |
| `ml/ner/semantic_matcher.py` | **ACTIVO** | Entidades semánticas |
| `ml/ner/build_curriculum_gold_dataset.py` | **SOPORTE** | Construcción de gold set |
| `ml/ner/semantic_hardening_runner.py` | **SOPORTE** | Endurecimiento semántico |

### 1.7 Recomendaciones (ACTIVO)

| Archivo | Estado | Observación |
|---|---|---|
| `ml/recommendations/curriculum_recommendation_engine.py` | **ACTIVO** | Motor basado en reglas |
| `ml/recommendations/curriculum_ml_recommendation_engine.py` | **ACTIVO** | Motor ML (qué tan entrenado: desconocido) |

### 1.8 Training y Evaluación (SOPORTE — NO EN PRODUCCIÓN CONTINUA)

| Archivo | Estado | Observación |
|---|---|---|
| `ml/training/train_curriculum_ml_models.py` | **SOPORTE** | Orquestador de entrenamiento |
| `ml/training/build_curriculum_alignment_dataset.py` | **SOPORTE** | Dataset de alineación |
| `ml/training/build_curriculum_gold_dataset.py` | **SOPORTE** | Dataset gold |
| `ml/training/build_visual_analytics_match_dataset.py` | **SOPORTE** | Dataset VA |
| `ml/evaluation/evaluate.py` | **SOPORTE** | Métricas de evaluación |

---

## 2. MODELOS QUE EXISTEN ACTUALMENTE

### 2.1 Modelo Primario: Rule-Based Matching (`rules_v1`)
- **Archivo:** `ml/ml_match_program_jobs.py`
- **match_method registrado:** `'rules_v1'`
- **model_name registrado:** `'local_rules_v1'`
- **Descripción:** Matching determinístico basado en solapamiento de skills normalizados, afinidad de texto y penalizaciones de conflicto de rol.
- **Fórmula:**
  ```
  Final Score = (skill_overlap_score * 0.68) + (role_score * 0.32)
  skill_overlap_score = (program_coverage * 0.70) + (job_density * 0.30)
  ```

### 2.2 Modelo Secundario: KNN con Multi-Hot Encoding
- **Archivo:** `backend/services/program_market_matching_service.py`
- **Librería:** `scikit-learn NearestNeighbors(metric="cosine")`
- **Features:** Multi-hot encoding de `skill_keys` con `MultiLabelBinarizer`
- **k_values:** `(5, 10, 20)` vecinos
- **Propósito:** Descubrimiento de vecinos más cercanos (jobs similares, programas similares)
- **Fórmula:**
  ```
  Similarity = (1 - cosine_distance) * 100 * domain_factor
  domain_factor: 1.0 (mismo dominio) | 0.5 (relacionado) | 0.1 (no relacionado)
  ```

### 2.3 TF-IDF Vectorizer (Fallback Semántico)
- **Archivo:** `ml/embeddings/embedding_service.py`
- **Uso:** Fallback cuando `sentence-transformers` no está disponible
- **Propósito:** Similarity semántica entre textos

### 2.4 Clasificador de Dominio (Híbrido Reglas + TF-IDF)
- **Archivo:** `ml/inference/domain_classifier.py`
- **Métodos:** `taxonomy_similarity_predict()` + `rule_adjusted_prediction()`
- **12 dominios:** data_analytics, AI, cybersecurity, criminology_security, finance, project_management, business_management, marketing, logistics, legal, education, health

### 2.5 Matcher Semántico NER
- **Archivo:** `ml/ner/semantic_matcher.py`
- **Threshold:** `0.56` cosine similarity
- **8 referencias semánticas:** Backend, Frontend, API/REST, Cloud, CI/CD, Power BI, ETL
- **Chunking:** Segmentos de máx. 72 palabras

### 2.6 Sentence Transformers (Instalación Condicional)
- **Archivo:** `ml/embeddings/embedding_service.py`
- **Modelo por defecto:** `all-MiniLM-L6-v2`
- **Estado real:** Solo activo si el paquete está instalado en el entorno

---

## 3. MODELOS QUE REALMENTE ESTÁN EN USO (PRODUCCIÓN)

```
┌─────────────────────────────────────────────────────────────┐
│  API endpoints → build_program_market_alignment_report()    │
│                                                             │
│  CAPA ACTIVA EN PRODUCCIÓN:                                 │
│  1. Domain Classifier (Reglas + Keywords)   ← SIEMPRE      │
│  2. Rule-Based Skill Matching (rules_v1)    ← SIEMPRE      │
│  3. KNN NearestNeighbors (cosine)           ← SIEMPRE      │
│  4. TF-IDF Fallback Semántico               ← SI NO HAY ST │
│  5. Sentence Transformers (MiniLM)          ← CONDICIONAL  │
└─────────────────────────────────────────────────────────────┘
```

**Endpoints que consumen el motor:**
- `backend/app/api.py` líneas 1251, 1274, 1282, 1298

---

## 4. MODELOS OBSOLETOS O QUE NO LLEGAN A PRODUCCIÓN

| Modelo | Archivo | Problema |
|---|---|---|
| `curriculum_ml_recommendation_engine.py` | `ml/recommendations/` | Invocado desde API pero estado de entrenamiento desconocido |
| `train_curriculum_ml_models.py` | `ml/training/` | Script de entrenamiento sin evidencia de ejecución continua |
| `build_visual_analytics_match_dataset.py` | `ml/training/` | Dataset construido pero sin loop de re-entrenamiento |
| `ml/evaluation/evaluate.py` | `ml/evaluation/` | Sin evidencia de ejecución en CI/CD |
| `semantic_hardening_runner.py` | `ml/ner/` | Estado de uso no verificado |

---

## 5. FEATURES UTILIZADAS

### 5.1 Features de Programa (SkillProfile)
```
- program_id, program_name, program_level, faculty
- domain_key, domain_label, domain_subdomain, domain_confidence
- skills (list[str]), skill_keys (list[str normalized])
- labels_by_key (dict), source_breakdown (dict por source_kind)
```

### 5.2 Features de Empleo (JobProfile)
```
- job_id, job_title, company, location, source, job_url, posted_at
- domain_key, domain_label, domain_subdomain, domain_confidence
- skills (list[str]), skill_keys (list[str normalized])
- labels_by_key (dict)
```

### 5.3 Features de Matching Computadas
```
- common_skills: |program_skills ∩ job_skills|
- program_coverage: common / program_skills * 100
- job_density: common / job_skills * 100
- jaccard_score: common / (program + job - common) * 100
- cosine_score: common / sqrt(program_skills * job_skills) * 100
- match_score: (jaccard + cosine) / 2
- domain_factor: 1.0 | 0.5 | 0.1
- adjusted_match: (jaccard * 0.50) + (coverage * 0.30) + (domain_factor * 20)
- similarity_score: (1 - cosine_distance) * 100 * domain_factor
- role_score: text_affinity sobre tokens de rol
- skill_overlap_score: (coverage * 0.70) + (density * 0.30)
- conflict_penalty: 0.55 si conflicto de dominio software
```

### 5.4 Features AUSENTES (No utilizadas actualmente)
```
- Salary data / rango salarial
- Fecha de publicación del empleo (temporal trends)
- Número de postulantes / demanda
- Nivel de seniority requerido
- Modalidad (remoto/presencial/híbrido)
- Tamaño de empresa / sector
- Embeddings densos de descripción completa de empleo
- Historial de clicks / aceptación de recomendaciones
- Feedback humano de egresados
```

---

## 6. DATASETS UTILIZADOS

### 6.1 Tablas Operativas (PostgreSQL)

| Tabla | Contenido | Uso en Matching |
|---|---|---|
| `especializaciones` | Programas académicos | Fuente de programas |
| `microcurriculos` | Contenido de microcurrículos | Skills académicos |
| `microcurriculo_skills` | Skills de microcurrículos | Feature engineering |
| `competencias` | Competencias por programa | Skills académicos |
| `herramientas` | Herramientas por programa | Skills técnicos |
| `perfiles_egreso` | Perfiles de egreso | Texto de rol objetivo |
| `jobs` / `empleos` | Empleos del mercado | Target de matching |
| `job_skills` | Skills de empleos | Feature engineering |

### 6.2 Vistas Materializadas

| Vista | Propósito | Complejidad |
|---|---|---|
| `vw_programa_skills` | Skills unificados de programas | UNION de 4 fuentes |
| `vw_match_empleo_especializacion` | Cross-join con scoring | Jaccard, Cosine, Coverage |
| `vw_match_empleo_especializacion_positivo` | Solo matches positivos | Filtro skills_en_comun > 0 |
| `vw_program_recommended_jobs` | Top jobs recomendados | skills_en_comun >= 1 |
| `vw_program_skill_gaps` | Skills del mercado no cubiertos | LEFT JOIN con NULL |
| `vw_program_market_alignment` | Métricas de alineación por programa | AVG scores + TOP 10 gaps |
| `vw_program_program_similarity` | Similitud entre programas | Jaccard, Cosine, Coverage |
| `vw_latest_ml_program_job_matches` | Último run de matches | Para API endpoints |
| `vw_job_domain_taxonomy` | Taxonomía de dominios de empleos | Clasificación por dominio |

### 6.3 Tablas de Entrenamiento ML

| Tabla | Contenido | Estado de Uso |
|---|---|---|
| `ml_training_runs` | Registro de runs | Infraestructura lista |
| `ml_program_documents` | Documentos de programa normalizados | Infraestructura lista |
| `ml_program_skill_labels` | Labels con human/weak_supervision/model | Infraestructura lista |
| `ml_job_documents` | Documentos de empleo normalizados | Infraestructura lista |
| `ml_skill_labels` | Labels de skills de empleos | Infraestructura lista |
| `ml_program_job_matches` | Resultados de matching guardados | ACTIVO |

---

## 7. RESPUESTAS A LAS PREGUNTAS CLAVE

### ¿Qué modelos existen actualmente?
6 modelos/enfoques: Rule-Based (rules_v1), KNN (cosine), TF-IDF Fallback, Domain Classifier (Keywords+TF-IDF), Sentence Transformers (condicional), NER semántico.

### ¿Qué modelos están realmente en uso?
Rule-Based y KNN son los únicos que garantizadamente corren en producción. Sentence Transformers corre solo si está instalado. Domain Classifier siempre activo.

### ¿Qué modelos están obsoletos?
Ninguno está "obsoleto" pero los scripts de entrenamiento supervisado (`train_curriculum_ml_models.py`, `build_*_dataset.py`) son infraestructura sin loop continuo.

### ¿Qué modelos nunca llegan a producción?
El motor de recomendaciones ML (`curriculum_ml_recommendation_engine.py`) y el evaluador (`evaluate.py`) no tienen evidencia de ejecución continua en producción.

### ¿Qué componentes pueden eliminarse?
- Duplicación de taxonomías: `backend/services/domain_taxonomy.py` y `intelligence/domain_taxonomy_layer.py` y `scrapers/taxonomy/domain_taxonomy.py` — 3 versiones del mismo concepto.
- Los weights hardcodeados (0.68/0.32, 0.70/0.30) deberían ser configurables o aprendidos.
- El fallback TF-IDF puede eliminarse si se confirma que Sentence Transformers siempre está disponible.

---

## 8. PROBLEMAS IDENTIFICADOS

1. **Sin ground truth validado:** Las tablas `ml_program_skill_labels` existen pero sin evidencia de labels humanos masivos.
2. **Weights arbitrarios:** Los coeficientes (0.68, 0.32, 0.70, 0.30, 0.50, 0.30, 0.20) son heurísticos sin respaldo estadístico.
3. **KNN no entrenado supervisadamente:** Usa multi-hot binario sin aprendizaje de preferencias reales.
4. **Triplicación de taxonomías de dominio:** Tres archivos separados definen dominios de forma inconsistente.
5. **Sin métricas de evaluación en CI:** El `evaluate.py` no está conectado a ningún pipeline automático.
6. **Sin feedback loop:** No hay mecanismo para capturar si los matches recomendados fueron útiles.
7. **Temporal blindness:** No se captura la evolución temporal de skills ni tendencias del mercado.
8. **Skill vocabulary demasiado estrecho:** Los SKILL_ALIASES (~50) son insuficientes para cubrir la variabilidad del mercado laboral real.

---

*Documento generado: 2026-06-07 | Auditoría: FASE 1 COMPLETA*
