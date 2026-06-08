# Arquitectura Objetivo del Motor de Matching ML
**Proyecto:** Observatorio Institucional de Inteligencia Curricular  
**Fecha:** 2026-06-07  
**Alcance:** Diseño de arquitectura de producción de 5 capas

---

## PRINCIPIOS DE DISEÑO

1. **Compatibilidad hacia atrás:** La arquitectura nueva debe coexistir con el sistema actual sin romper APIs.
2. **Explicabilidad primero:** En contexto educativo institucional, cada recomendación debe ser justificable.
3. **Escalabilidad incremental:** Cada capa puede mejorarse independientemente sin reemplazar todo.
4. **Sin dependencias externas críticas:** No depender de APIs de terceros (OpenAI) para funciones core.
5. **Railway/Vercel compatible:** Diseño stateless con persistencia en PostgreSQL + vectorDB ligero.

---

## ARQUITECTURA DE 5 CAPAS

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    MOTOR DE MATCHING ACADÉMICO-LABORAL v2                    │
│                                                                              │
│  Input: program_id / microcurriculum_id / query_text                        │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  CAPA 1: CLASIFICACIÓN DE DOMINIO                                    │   │
│  │  Modelo: Hybrid Keywords + E5-Multilingual fine-tuned                │   │
│  │  Output: domain_key, subdomain, confidence [0-1]                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│                              ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  CAPA 2: RECUPERACIÓN SEMÁNTICA                                      │   │
│  │  Modelo: BM25 + BGE-M3 Embeddings + FAISS Index                     │   │
│  │  Output: top-K candidatos (k=50-200) con scores                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│                              ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  CAPA 3: MATCHING DE SKILLS                                          │   │
│  │  Modelo: Rule-Based (actual) + Skill Graph Expansion                 │   │
│  │  Output: skill_overlap, gaps, coverage, jaccard, cosine              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│                              ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  CAPA 4: RANKING FINAL                                               │   │
│  │  Modelo: LightGBM-Rank (Learning-to-Rank)                           │   │
│  │  Features: todas las capas anteriores + señales de mercado           │   │
│  │  Output: ranked_jobs[], score_final [0-100]                          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                              │                                               │
│                              ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  CAPA 5: EXPLICABILIDAD                                              │   │
│  │  Modelo: SHAP + Rules Template + Gap Analysis                        │   │
│  │  Output: explanation_text, skills_comunes[], gaps[], why_matched     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  Output Final: ranked_matches[] con scores + explicaciones                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## CAPA 1: CLASIFICACIÓN DE DOMINIO

### Objetivo
Determinar el dominio principal de un programa académico o empleo antes de cualquier matching, para restringir el espacio de búsqueda y aplicar pesos de dominio correctamente.

### Modelo Recomendado
**Híbrido: Keywords actuales + E5-Multilingual (fine-tuning ligero)**

```python
class DomainClassifier:
    def predict(self, text: str, metadata: dict) -> DomainResult:
        # Paso 1: Clasificación por keywords (actual, 0ms)
        keyword_result = infer_domain_from_texts([text])
        
        # Paso 2: Si confianza < 0.6, activar clasificador semántico
        if keyword_result.confidence < 0.6:
            embedding = e5_model.encode(f"classify: {text}")
            semantic_result = domain_classifier_head.predict(embedding)
            return merge_predictions(keyword_result, semantic_result)
        
        return keyword_result
```

### Features Utilizadas
- `program_name`, `faculty`, `plan_estudios`, `campo_laboral` (programas)
- `job_title`, `description`, `requirements`, `responsibilities` (empleos)
- Skill keywords por dominio (catálogo actual)

### Output
```python
@dataclass
class DomainResult:
    domain_key: str        # "data_analytics", "artificial_intelligence", ...
    subdomain: str         # "visual_analytics", "data_engineering", ...
    confidence: float      # [0.35 - 0.98]
    top_keywords: list[str]  # Evidence keywords para explicabilidad
```

### Datos que Faltan
- Labels de dominio validados por humanos (actualmente solo heurísticos)
- Programas nuevos que no encajan en los 12 dominios actuales

### Datos que Sobran
- Triple duplicación de taxonomías de dominio (3 archivos separados) → consolidar en 1

---

## CAPA 2: RECUPERACIÓN SEMÁNTICA

### Objetivo
Dado un perfil de programa/microcurrículo, recuperar eficientemente los K empleos más relevantes del corpus (actualmente cientos, potencialmente miles).

### Modelo Recomendado
**Hybrid Retrieval: BM25 + BGE-M3 con RRF Fusion**

```python
class SemanticRetriever:
    def __init__(self):
        self.bm25_index = BM25Index(job_documents)          # Léxico
        self.faiss_index = FAISSIndex(bge_embeddings)       # Semántico
    
    def retrieve(self, program_profile: SkillProfile, k: int = 100) -> list[Candidate]:
        # Canal 1: BM25 sobre skills + descripción
        bm25_query = " ".join(program_profile.skills)
        bm25_results = self.bm25_index.search(bm25_query, k=k)
        
        # Canal 2: Dense embeddings de descripción del programa
        dense_query = bge_model.encode(program_profile.full_text)
        dense_results = self.faiss_index.search(dense_query, k=k)
        
        # Fusión RRF: Reciprocal Rank Fusion
        return reciprocal_rank_fusion(bm25_results, dense_results, k=k)
```

### Embeddings por Texto (Pre-computados y Cacheados)
- **Programa:** `f"specialization: {name} skills: {', '.join(skills)} profile: {perfil_egreso}"`
- **Empleo:** `f"job: {title} company: {company} skills: {', '.join(skills)} requirements: {description[:500]}"`

### FAISS Configuration para Railway
```python
# Sin GPU: IndexFlatIP (exacto, hasta ~10K docs sin problema)
# Con volumen: IndexIVFFlat (aproximado, para 100K+ docs)
index = faiss.IndexFlatIP(768)  # BGE-M3 dimensión
```

### Infraestructura Requerida
- PostgreSQL `pgvector` extension (ya probablemente disponible) O FAISS persistido en disco
- Tabla `ml_embeddings_cache` con `(entity_type, entity_id, model_name, embedding vector, created_at)`

### Datos que Faltan
- Embeddings pre-computados de todos los empleos y programas
- Tabla de cache de embeddings en DB
- Texto completo normalizado de empleos (description + requirements + responsibilities)

### Datos que Sobran
- El KNN con multi-hot binario actual es redundante si se implementa FAISS con embeddings densos

---

## CAPA 3: MATCHING DE SKILLS

### Objetivo
Para cada candidato recuperado en capa 2, calcular el score preciso de matching de skills con evidencia estructurada.

### Modelo Recomendado
**Rule-Based (mantener) + Skill Graph Expansion**

```python
class SkillMatcher:
    def score(self, program: SkillProfile, job: JobProfile) -> SkillMatchResult:
        # Paso 1: Matching exacto (sistema actual)
        exact_match = compute_exact_skill_overlap(program.skill_keys, job.skill_keys)
        
        # Paso 2: Expansión por grafo de skills (NUEVO)
        # Ejemplo: "python" → relacionado con "scripting", "automatizacion", "data analysis"
        expanded_program = expand_skills_via_graph(program.skill_keys)
        expanded_job = expand_skills_via_graph(job.skill_keys)
        expanded_match = compute_exact_skill_overlap(expanded_program, expanded_job)
        
        # Paso 3: Match por embeddings de skills individuales (NUEVO)
        skill_embedding_score = compute_skill_semantic_similarity(
            program.skills, job.skills, threshold=0.82
        )
        
        return SkillMatchResult(
            exact_jaccard=exact_match.jaccard,
            exact_coverage=exact_match.coverage,
            expanded_jaccard=expanded_match.jaccard,
            skill_semantic_score=skill_embedding_score,
            common_skills=exact_match.common,
            gaps=exact_match.gaps,
            domain_factor=compute_domain_factor(program.domain_key, job.domain_key)
        )
```

### Skill Graph (A Construir)
```
python ──related_to──► scripting
python ──related_to──► data_analysis
python ──related_to──► machine_learning
sql ──related_to──► bases_de_datos
sql ──related_to──► data_engineering
power_bi ──related_to──► visualizacion_datos
power_bi ──related_to──► business_intelligence
```

**Fuentes para construir el grafo:**
1. Taxonomía ESCO (European Skills/Competences)
2. Co-ocurrencias en job postings actuales
3. Curación manual por dominio

### Features de Output
```python
- exact_jaccard, exact_coverage, exact_gap       # Match exacto (actual)
- expanded_jaccard, expanded_coverage             # Con grafo de skills (nuevo)
- skill_semantic_score                            # Similitud semántica de skills
- common_skills, missing_skills, extra_skills     # Listas estructuradas
- domain_factor                                   # 1.0 | 0.5 | 0.1
- role_conflict                                   # boolean (actual)
- program_skill_count, job_skill_count            # Densidad
```

### Datos que Faltan
- Grafo de relaciones entre skills (actualmente solo aliases planos)
- Skills laborales con mayor cobertura (actualmente limitadas a ~50 aliases)

---

## CAPA 4: RANKING FINAL

### Objetivo
Dado el conjunto de candidatos con scores de las capas 1-3, aprender a ordenarlos según relevancia real usando un modelo supervisado.

### Modelo Recomendado
**LightGBM con objective='lambdarank'**

```python
class FinalRanker:
    def __init__(self):
        self.model = lgb.LGBMRanker(
            objective='lambdarank',
            metric='ndcg',
            ndcg_eval_at=[5, 10, 20]
        )
    
    def predict_rank(self, candidates: list[SkillMatchResult]) -> list[RankedMatch]:
        features = self._build_features(candidates)
        scores = self.model.predict(features)
        return sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    
    def _build_features(self, results) -> np.ndarray:
        return np.array([[
            r.exact_jaccard,
            r.exact_coverage,
            r.expanded_jaccard,
            r.skill_semantic_score,
            r.domain_factor,
            r.bm25_retrieval_score,       # De Capa 2
            r.dense_retrieval_score,      # De Capa 2
            r.domain_confidence,          # De Capa 1
            r.program_skill_count,
            r.job_skill_count,
            r.common_skill_count,
            r.missing_skill_count,
            int(r.role_conflict),
            r.program_level_encoded,      # especializacion=2, maestria=3
            r.job_seniority_encoded,      # junior=1, mid=2, senior=3
        ] for r in results])
```

### Labels de Entrenamiento
```
relevance_label → ordinal score:
  "high"     → 3
  "medium"   → 2
  "low"      → 1
  "no_match" → 0
```

### Fase de Arranque (sin labels suficientes)
Usar el **scoring actual** (`rules_v1`) como proxy de labels para pre-entrenar. Refinar con feedback humano.

### Datos que Faltan
- Pares (programa, empleo) con labels de relevancia validados por humanos
- Feedback de egresados: "¿Este empleo fue pertinente para tu programa?"
- Datos de seniority y salario de empleos

---

## CAPA 5: EXPLICABILIDAD

### Objetivo
Traducir los scores técnicos en explicaciones comprensibles para directivos académicos, coordinadores de programa y egresados.

### Modelo Recomendado
**SHAP + Template Engine + Gap Analysis (Rule-Based)**

```python
class ExplainabilityEngine:
    def explain(self, match: RankedMatch, audience: str = "academic") -> Explanation:
        # SHAP para feature importance del LightGBM
        shap_values = self.explainer.shap_values(match.features)
        top_features = get_top_shap_features(shap_values, n=3)
        
        # Template de explicación según audiencia
        if audience == "academic":
            return AcademicExplanation(
                why_matched=self._build_why_text(match, top_features),
                common_skills=match.common_skills,
                missing_skills=match.missing_skills,  # Para currícula update
                market_relevance=match.domain_alignment_text
            )
        elif audience == "student":
            return StudentExplanation(
                job_fit=match.final_score,
                skills_you_have=match.common_skills,
                skills_to_develop=match.missing_skills[:5],
                why_relevant=match.domain_explanation
            )
```

### Templates de Explicación

**Para directivos académicos:**
> "El programa [NOMBRE] cubre el **{coverage}%** de las competencias que demanda el mercado en [DOMINIO].  
> Skills con alta demanda no cubiertos: [GAPS_TOP_5].  
> Skills del programa sin demanda actual: [EXTRA_SKILLS]."

**Para coordinadores de programa:**
> "[N] empleos de alta pertinencia identificados. Las skills más demandadas y no cubiertas son: [GAPS]. 
> Recomendación curricular: incorporar [SKILL_1] y [SKILL_2] al plan de estudios."

**Para egresados:**
> "Tu programa te preparó para el [X]% de las competencias de este empleo.  
> Para mejorar tu perfil: [TOP_3_GAPS] son altamente valoradas en este rol."

### Datos que Faltan
- Rango salarial para contextualizar pertinencia económica
- Tendencias temporales de skills (crecimiento o declive)

---

## DIAGRAMA DE FLUJO COMPLETO

```
                    ┌─────────────────┐
                    │   program_id    │
                    │ microcurriculum │
                    │   query_text    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    CAPA 1       │
                    │ Domain Classify │
                    │ Keywords + E5   │
                    └────────┬────────┘
                             │ domain_key, confidence
                    ┌────────▼────────┐
                    │    CAPA 2       │
                    │ Semantic Recall │◄─── FAISS Index
                    │ BM25 + BGE-M3   │◄─── BM25 Index
                    └────────┬────────┘
                             │ top-100 candidates
                    ┌────────▼────────┐
                    │    CAPA 3       │
                    │ Skill Matching  │◄─── Skill Graph
                    │ Rules + Graph   │◄─── NER + Taxonomy
                    └────────┬────────┘
                             │ skill_features[]
                    ┌────────▼────────┐
                    │    CAPA 4       │
                    │ Final Ranking   │◄─── Human Labels
                    │ LightGBM-Rank   │
                    └────────┬────────┘
                             │ ranked_matches[]
                    ┌────────▼────────┐
                    │    CAPA 5       │
                    │ Explainability  │
                    │ SHAP + Rules    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   API Response  │
                    │ matches[]       │
                    │ + explanations  │
                    └─────────────────┘
```

---

## STACK TECNOLÓGICO RECOMENDADO

### Producción Railway (Sin GPU)

| Componente | Tecnología | Justificación |
|---|---|---|
| Domain Classifier | Keywords + scikit-learn | Sin GPU, rápido |
| BM25 Index | `rank-bm25` | Puro Python |
| Embeddings Model | `sentence-transformers` (MiniLM-L12) | Balance velocidad/precisión |
| Vector Index | FAISS `IndexFlatIP` | Sin GPU para corpus < 50K |
| Skill Matcher | Rule-Based (actual) | Mantener |
| Ranker | LightGBM | Sin GPU, rápido |
| SHAP | `shap` library | Explicabilidad |
| Storage | PostgreSQL + pgvector | Unificado |

### Producción con GPU (Futuro)

| Componente | Tecnología | Mejora |
|---|---|---|
| Embeddings | BGE-M3 o E5-Large | +15-20% precisión |
| Vector Index | FAISS GPU o Weaviate | 10x velocidad |
| Ranker | LightGBM GPU mode | 3x velocidad entrenamiento |

---

## DATOS FALTANTES (CRÍTICOS)

| Dato | Impacto | Cómo Obtenerlo |
|---|---|---|
| Labels de relevancia humanos (programa-empleo) | Alto — sin esto no hay LTR | Formulario para coordinadores de programa |
| Embeddings pre-computados de todos los jobs | Alto — requerido para FAISS | Script de indexación batch |
| Rango salarial de empleos | Medio — contextualiza pertinencia | Scraping adicional o API de mercado |
| Skill graph / relaciones entre skills | Medio — mejora matching | Importar ESCO + co-ocurrencias |
| Feedback de egresados | Alto — signal de relevancia real | Encuesta post-egreso |
| Temporal trends de skills | Bajo-Medio — tendencias | Histórico de job postings con fecha |

## DATOS REDUNDANTES (ELIMINAR O CONSOLIDAR)

| Dato/Componente | Problema | Acción |
|---|---|---|
| 3 archivos de domain_taxonomy | Inconsistencia y duplicación | Consolidar en 1 módulo |
| KNN multi-hot binario | Reemplazado por FAISS + embeddings | Deprecar en v2 |
| SKILL_ALIASES (50 entries) | Vocabulario insuficiente y estático | Extender con skill graph dinámico |
| Weights hardcodeados (0.68, 0.32...) | Sin respaldo estadístico | Aprender via LightGBM |
| TF-IDF fallback | Redundante con embeddings propios | Mantener solo como último fallback |

---

*Documento generado: 2026-06-07 | Arquitectura Objetivo: FASE 3 COMPLETA*
