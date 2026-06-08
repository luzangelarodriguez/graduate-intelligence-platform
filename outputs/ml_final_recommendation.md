# Recomendación Final: Motor de Matching Académico-Laboral
**Proyecto:** Observatorio Institucional de Inteligencia Curricular  
**Fecha:** 2026-06-07  
**Estado:** RECOMENDACIÓN BASADA EN AUDITORÍA CIENTÍFICA

---

## VEREDICTO EJECUTIVO

> **El KNN actual debe MANTENERSE como componente de exploración pero debe DEJAR DE SER el motor primario de ranking.**
>
> La arquitectura óptima es un **ensemble híbrido de 5 capas** que supera al KNN en precisión, explicabilidad y escalabilidad sin requerir reemplazo inmediato del sistema existente.

---

## RESPUESTAS EXPLÍCITAS

### 1. ¿Debe mantenerse KNN?

**SÍ, parcialmente.** El KNN con multi-hot encoding tiene utilidad como:
- Explorador de programas similares entre sí (programa-a-programa)
- Generador de candidatos iniciales cuando no haya FAISS disponible
- Baseline de comparación para nuevos modelos

**NO como motor principal de ranking** porque:
- Multi-hot binario ignora la semántica interna de cada skill
- No aprende de feedback; los weights son fijos
- Sin FAISS indexing, es O(n) en búsqueda — no escala
- La explicación "vecinos más cercanos" no es útil para directivos académicos

### 2. ¿Debe eliminarse KNN?

**NO inmediatamente.** Eliminar sin un reemplazo validado es riesgo operativo. El plan correcto es:
1. Mantener KNN mientras se construye y valida FAISS + LightGBM
2. Ejecutar ambos en paralelo durante 2-3 meses para comparar
3. Deprecar KNN solo cuando el nuevo motor supere NDCG@10 en ≥10%

### 3. ¿Debe coexistir con otros modelos?

**SÍ, en el período de transición.** El plan de coexistencia:

```
Período actual:   Rules (68%) + KNN (exploración) → API
Período v1.5:     Rules (68%) + KNN + LightGBM (shadow mode)
Período v2.0:     Rules (explicabilidad) + FAISS + LightGBM (primario) + KNN (deprecado)
```

### 4. ¿Cuál sería el motor ideal por área?

#### Software / Tecnología
```
Motor ideal:
  - Capa 2: BGE-M3 embeddings (captura variaciones técnicas como "backend" ≈ "servidor")
  - Capa 3: Skill graph con ESCO + relaciones Python→scripting→automatización
  - Capa 4: LightGBM con features de seniority y tecnologías específicas
  - Prioridad: Semántica fuerte porque los job titles varían mucho
  
Riesgo actual: El conflict_penalty de "software" es heurístico y penaliza mal
               programas legítimamente técnicos que aplican a empleos de software.
```

#### IA (Inteligencia Artificial)
```
Motor ideal:
  - Capa 2: E5-Multilingual (detecta "aprendizaje automático" ≈ "machine learning")
  - Capa 3: Grafo de skills IA: LLM → NLP → transformers → BERT
  - Capa 4: LightGBM con señal de emerging_skills (MLOps, GenAI, RAG)
  - Especial: Skill taxonomy actualizada cada 3 meses (campo evoluciona rápido)
  
Riesgo actual: SKILL_ALIASES no incluye términos modernos (RAG, LLM, GenAI, Agents).
               Empleos de IA tienen score bajo artificialmente.
```

#### Data Analytics
```
Motor ideal: (El sistema actual ya está mejor calibrado para este dominio)
  - Capa 2: BM25 + TF-IDF funciona bien (terminología estable)
  - Capa 3: Rules actuales + expansion BI_clusters (Power BI → Tableau → Looker)
  - Capa 4: LightGBM con señal de herramientas específicas
  - Prioridad: Subdomains claros (visual_analytics vs data_engineering vs governance)
  
Ventaja: El sistema fue originalmente diseñado para Visual Analytics.
         Es el dominio con mayor cobertura de aliases y taxonomía.
```

#### Educación
```
Motor ideal:
  - Capa 1: Clasificador especializado (ROLE_GROUPS["educacion"] es muy básico)
  - Capa 3: Skill set pedagógico expandido: "diseño curricular", "evaluación educativa"
  - Capa 4: LightGBM con features de nivel académico (básica/media/universitaria)
  - Especial: Diferenciación presencial/virtual/STEM/humanidades
  
Riesgo actual: "educacion" en ROLE_GROUPS tiene solo 6 keywords. Cobertura mínima.
```

#### Salud
```
Motor ideal:
  - Capa 1: Clasificador especializado con terminología médica/clínica
  - Capa 3: Ontología médica (SNOMED, CIE-10 para habilidades clínicas)
  - Capa 4: LightGBM con features de especialidad, nivel (técnico/profesional)
  - Especial: Regulación colombiana (habilitación, secretarías de salud)
  
Riesgo actual: "salud" en ROLE_GROUPS = 4 keywords. Completamente insuficiente.
               Los empleos de salud tienen skills muy específicos no cubiertos.
```

#### Criminología
```
Motor ideal:
  - Capa 1: Clasificador con prioridad alta (domain_priority=1 ya en DOMAIN_ORDER)
  - Capa 3: Skills específicos: análisis criminal, SIG forense, derecho penal
  - Capa 4: LightGBM calibrado para bajo volumen de empleos (pocos jobs de criminología)
  - Especial: Integrar con empleos del sector público (Fiscalía, INPEC, Policía)
  
Ventaja: Ya tiene prioridad máxima en DOMAIN_ORDER (criminology_security).
Riesgo actual: Pocos empleos de criminología en el corpus.
               Matches con seguridad privada/ciberseguridad pueden ser falsos positivos.
```

---

## ARQUITECTURA ACTUAL (AS-IS)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ARQUITECTURA ACTUAL (AS-IS)                         │
│                                                                             │
│  Input: program_id                                                          │
│         │                                                                   │
│  ┌──────▼──────────────────────────────────────────────────────────────┐   │
│  │  DOMAIN CLASSIFICATION                                              │   │
│  │  Método: Keywords lookup en DOMAIN_ORDER (12 dominios)             │   │
│  │  Confidence: lineal (0.35 + hits*0.12 + keywords*0.03)             │   │
│  │  Problema: 3 archivos duplicados, sin ML                           │   │
│  └──────┬──────────────────────────────────────────────────────────────┘   │
│         │ domain_key, confidence                                            │
│  ┌──────▼──────────────────────────────────────────────────────────────┐   │
│  │  SKILL MATCHING (rules_v1)  ← MOTOR PRINCIPAL                       │   │
│  │  Método: Jaccard + Cosine + Coverage con weights heurísticos        │   │
│  │  score = (skill_overlap*0.68) + (role_affinity*0.32)               │   │
│  │  Vocabulario: ~50 SKILL_ALIASES (estático)                          │   │
│  │  Problema: Solo coincidencias exactas, weights sin respaldo         │   │
│  └──────┬──────────────────────────────────────────────────────────────┘   │
│         │ scores, labels                                                    │
│  ┌──────▼──────────────────────────────────────────────────────────────┐   │
│  │  KNN DISCOVERY (scikit-learn NearestNeighbors)  ← SECUNDARIO        │   │
│  │  Método: Multi-hot encoding de skills + cosine                      │   │
│  │  k = (5, 10, 20) vecinos                                            │   │
│  │  Problema: Multi-hot pierde semántica, sin indexing FAISS            │   │
│  └──────┬──────────────────────────────────────────────────────────────┘   │
│         │ nearest_jobs, nearest_programs                                    │
│  ┌──────▼──────────────────────────────────────────────────────────────┐   │
│  │  OUTPUT (sin capa de explicabilidad estructurada)                   │   │
│  │  skills_comunes[], skills_faltantes[], score_match                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  FORTALEZAS: Transparente, rápido, sin dependencias GPU, explicable        │
│  DEBILIDADES: Solo léxico, weights heurísticos, sin aprendizaje            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ARQUITECTURA OBJETIVO (TO-BE)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ARQUITECTURA OBJETIVO (TO-BE)                       │
│                                                                             │
│  Input: program_id / microcurriculum_id / query                            │
│         │                                                                   │
│  ┌──────▼────────────────────────────────────────────────────────────────┐ │
│  │  CAPA 1: DOMAIN CLASSIFIER (Unificado)                               │ │
│  │  Keywords (actual) → fallback E5-Multilingual (nuevo)                │ │
│  │  1 archivo consolidado, 12 dominios, subdomains                      │ │
│  └──────┬────────────────────────────────────────────────────────────────┘ │
│         │ domain_key, subdomain, confidence                                 │
│  ┌──────▼────────────────────────────────────────────────────────────────┐ │
│  │  CAPA 2: HYBRID RETRIEVAL                                            │ │
│  │  BM25 (lexical) + FAISS/BGE-M3 (semantic) → RRF Fusion              │ │
│  │  Output: top-100 job candidates                                      │ │
│  │  Embeddings: pre-computados y cacheados en PostgreSQL                │ │
│  └──────┬────────────────────────────────────────────────────────────────┘ │
│         │ candidates[] con retrieval_scores                                 │
│  ┌──────▼────────────────────────────────────────────────────────────────┐ │
│  │  CAPA 3: SKILL MATCHING (Enhanced)                                   │ │
│  │  Rules (mantener) + Skill Graph Expansion (ESCO)                     │ │
│  │  exact_jaccard + expanded_jaccard + skill_semantic_score             │ │
│  │  Output: structured skill_features[]                                 │ │
│  └──────┬────────────────────────────────────────────────────────────────┘ │
│         │ skill_features[], common[], gaps[]                                │
│  ┌──────▼────────────────────────────────────────────────────────────────┐ │
│  │  CAPA 4: LIGHTGBM RANKER                                             │ │
│  │  LambdaRank sobre features de capas 1-3 + contextuales              │ │
│  │  Labels: rules_v1 (weak) → human feedback (strong)                  │ │
│  │  Output: ranked_matches[] con score_final                            │ │
│  └──────┬────────────────────────────────────────────────────────────────┘ │
│         │ ranked_matches[]                                                   │
│  ┌──────▼────────────────────────────────────────────────────────────────┐ │
│  │  CAPA 5: EXPLAINABILITY                                              │ │
│  │  SHAP (features) + Rules Templates (textos) + Gap Analysis           │ │
│  │  Audiencias: directivos / coordinadores / egresados                  │ │
│  │  Output: explanation_text, why_matched, curriculum_recommendations   │ │
│  └──────┬────────────────────────────────────────────────────────────────┘ │
│         │                                                                   │
│  ┌──────▼────────────────────────────────────────────────────────────────┐ │
│  │  API Response: ranked_matches[] + explanations + curriculum_gaps      │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  FORTALEZAS: Semántico + Léxico, aprende de feedback, explicable, escalable│
│  TRADE-OFFS: Más complejo, requiere labels humanos, embeddings necesitan   │
│              ~500MB RAM adicional para modelo multilingual                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## BENEFICIOS DE LA MIGRACIÓN

| Beneficio | Sistema Actual | Sistema Objetivo | Mejora Estimada |
|---|---|---|---|
| Precisión de matching | Léxico (jaccard exacto) | Semántico + léxico | +25-40% relevancia percibida |
| Cobertura de vocabulario | ~50 aliases estáticos | Grafo dinámico (ESCO + co-ocurrencia) | +10x skills cubiertos |
| Explicabilidad | Skills comunes/faltantes | Skills + SHAP + templates por audiencia | Directivos/coordinadores/egresados |
| Escalabilidad | O(n) KNN sin indexing | FAISS sub-linear search | 100x más rápido con 10K+ empleos |
| Mejora continua | Sin aprendizaje | Active learning + feedback loop | Mejora cada mes con nuevos labels |
| Detección de gaps | Lista estática | Grafo expandido + tendencias | Gaps curriculares más precisos |
| Dominios cubiertos | Todos igual de mal | Cada dominio con taxonomía propia | Salud, Educación, IA significativamente mejor |

---

## RIESGOS Y MITIGACIONES

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| LightGBM peor que rules_v1 sin labels suficientes | Media | Alto | Usar weak labels + validar antes de reemplazar |
| Embeddings lentos sin GPU en Railway | Alta | Medio | Usar MiniLM-L12 (384d, 3x más rápido que L6) |
| FAISS index desincronizado al agregar empleos | Media | Medio | Rebuild index nightly en job batch |
| Coordinadores no anotan suficientes labels | Alta | Alto | Gamificación + incentivo + interfaz simple |
| Regresión en dominios actuales bien cubiertos | Baja | Alto | A/B testing silencioso antes de cutover |
| Deuda técnica por 3 taxonomías duplicadas | Alta | Medio | Sprint de consolidación antes de migración |

---

## PLAN DE MIGRACIÓN

### Sprint 0 — Limpieza (2 semanas, SIN MODIFICAR PRODUCCIÓN)
```
□ Consolidar los 3 archivos de domain_taxonomy en 1 módulo canónico
□ Documentar qué endpoints usan qué archivos de taxonomía
□ Crear rama feature/ml-v2 para desarrollo aislado
□ Establecer métricas baseline de rules_v1 (NDCG@10, Precision@5)
```

### Sprint 1 — LightGBM con Weak Labels (4 semanas)
```
□ Exportar todos los ml_program_job_matches como weak training data
□ Implementar feature matrix completa (15 features por par)
□ Entrenar LightGBM-Rank v0 sobre weak labels
□ Comparar offline vs rules_v1 (NDCG@10 debe ser ≥ rules_v1)
□ Shadow mode: ejecutar LightGBM en paralelo sin afectar API
```

### Sprint 2 — Embeddings + FAISS (4 semanas)
```
□ Instalar sentence-transformers con multilingual-e5-small
□ Script de indexación batch: generar embeddings de todos los empleos
□ Construir FAISS IndexFlatIP y persistir en disco
□ Integrar retrieval híbrido BM25 + FAISS en pipeline de test
□ Medir latencia en Railway sin GPU
```

### Sprint 3 — Skill Graph (4 semanas)
```
□ Importar ESCO taxonomy en español (3,000+ skills)
□ Computar co-ocurrencias de skills en job_skills
□ Construir grafo de relaciones top-500 skills
□ Integrar expanded_jaccard como feature adicional
□ Validar que expanded_jaccard mejora recall
```

### Sprint 4 — Human Labels + Active Learning (ongoing)
```
□ Implementar tabla ml_human_feedback en PostgreSQL
□ Construir UI de anotación (formulario simple en admin panel)
□ Lanzar primera ronda de anotación con 3-4 coordinadores
□ Meta: 200 pares/mes con label_source='human'
□ Re-entrenar LightGBM mensualmente con nuevos labels
```

### Sprint 5 — Explicabilidad Estructurada (4 semanas)
```
□ Integrar shap library en LightGBM inference
□ Implementar templates de explicación por audiencia
□ Conectar SHAP features con textos de skills legibles
□ Test con coordinadores: ¿la explicación es útil?
```

### Sprint 6 — Cutover a v2 (2 semanas)
```
□ A/B test: 50% tráfico a v1 (rules + KNN), 50% a v2 (LightGBM + FAISS)
□ Medir satisfacción de usuarios (coordinadores)
□ Si v2 ≥ v1 en NDCG@10 y user satisfaction: cutover completo
□ Deprecar KNN (mantener 3 meses como fallback)
□ Archivar ml_match_program_jobs.py rules V1 en legacy/
```

### Timeline Total Estimado
```
Mes 1:  Sprint 0 + Sprint 1 (LightGBM baseline funcional)
Mes 2:  Sprint 2 (embeddings + FAISS)
Mes 3:  Sprint 3 (skill graph)
Mes 4+: Sprint 4 ongoing + Sprint 5 (explicabilidad)
Mes 6:  Sprint 6 (cutover)
```

---

## ARQUITECTURA RAILWAY/VERCEL RECOMENDADA

```
┌─────────────────────────────────────────────────────────────┐
│                  PRODUCCIÓN EN RAILWAY                       │
│                                                             │
│  ┌─────────────────┐   ┌──────────────────────────────┐   │
│  │   FastAPI App   │   │    Background Workers         │   │
│  │  (stateless)    │   │  (embedding indexer, trainer) │   │
│  │                 │   │                               │   │
│  │  /api/match     │   │  nightly_faiss_rebuild.py     │   │
│  │  /api/gaps      │   │  weekly_lightgbm_retrain.py   │   │
│  │  /api/explain   │   │  monthly_active_learning.py   │   │
│  └────────┬────────┘   └──────────────┬────────────────┘   │
│           │                           │                     │
│  ┌────────▼───────────────────────────▼──────────────────┐ │
│  │                PostgreSQL                              │ │
│  │  - Tablas operativas (especializaciones, empleos)      │ │
│  │  - ml_* tables (training, labels, matches)             │ │
│  │  - ml_embeddings_cache (pgvector)                      │ │
│  │  - ml_human_feedback                                   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Persistent Volume (Railway)                         │   │
│  │  - faiss_index.bin (vector index)                    │   │
│  │  - lgbm_ranker_v{n}.pkl (model)                      │   │
│  │  - bm25_index.pkl (lexical index)                    │   │
│  │  - e5_embeddings/ (model cache)                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  RAM recomendada: 4-8 GB (E5-small ~500MB, FAISS ~200MB)   │
│  CPU: Funciona sin GPU con MiniLM o E5-small               │
└─────────────────────────────────────────────────────────────┘
```

---

## RESUMEN DE DECISIÓN

| Pregunta | Respuesta |
|---|---|
| ¿Eliminar KNN? | **NO** — Deprecar gradualmente en 6 meses |
| ¿Reemplazar rules_v1? | **NO** — Mantener como capa de explicabilidad |
| ¿Nuevo motor principal? | **SÍ** — LightGBM-Rank como capa 4 de ranking |
| ¿Embeddings? | **SÍ** — E5-Multilingual-Small (sin GPU viable) |
| ¿Vector search? | **SÍ** — FAISS para retrieval semántico |
| ¿Cuándo modificar producción? | **Sprint 6** — Solo después de validar A/B test |
| ¿Costo de migración? | **Bajo-Medio** — Incrementalmente, sin reescritura total |
| ¿Qué mejora más rápido? | **LightGBM sobre features actuales** — 4 semanas, sin GPU |

---

*Documento generado: 2026-06-07 | Recomendación Final: FASE 5 COMPLETA*  
*Auditoría basada en análisis del código fuente real del sistema. Sin modificaciones a producción.*
