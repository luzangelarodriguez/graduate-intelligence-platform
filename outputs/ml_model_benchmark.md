# Benchmark Conceptual de Modelos de Matching Académico-Laboral
**Proyecto:** Observatorio Institucional de Inteligencia Curricular  
**Fecha:** 2026-06-07  
**Alcance:** Evaluación comparativa de 17 enfoques para matching programa-empleo

---

## CRITERIOS DE EVALUACIÓN

| Criterio | Descripción | Escala |
|---|---|---|
| **Precisión** | Calidad del match semántico y relevancia | 1-5 |
| **Interpretabilidad** | ¿Se puede explicar por qué hubo match? | 1-5 |
| **Velocidad** | Latencia de inferencia en producción | 1-5 (5=rápido) |
| **Costo** | Costo computacional/económico | 1-5 (5=barato) |
| **Mantenimiento** | Facilidad de actualizar y evolucionar | 1-5 |
| **Escalabilidad** | Crece bien con más programas/empleos | 1-5 |
| **Explicabilidad** | Capacidad de justificar recomendaciones al usuario | 1-5 |

---

## 1. RULE-BASED MATCHING (Sistema Actual)

**Descripción:** Matching determinístico por solapamiento de skill_keys normalizados + afinidad de texto por tokens.

**Implementación actual:**
```
score = (skill_overlap * 0.68) + (role_affinity * 0.32)
skill_overlap = (program_coverage * 0.70) + (job_density * 0.30)
```

| Criterio | Puntuación | Justificación |
|---|---|---|
| Precisión | ⭐⭐⭐ (3/5) | Solo captura coincidencias exactas de skills normalizados; pierde variaciones semánticas |
| Interpretabilidad | ⭐⭐⭐⭐⭐ (5/5) | Completamente transparente: lista exacta de skills comunes y faltantes |
| Velocidad | ⭐⭐⭐⭐⭐ (5/5) | O(n) determinístico, sin inferencia ML |
| Costo | ⭐⭐⭐⭐⭐ (5/5) | Sin dependencias externas, sin GPU |
| Mantenimiento | ⭐⭐ (2/5) | Requiere actualización manual de aliases y reglas constantemente |
| Escalabilidad | ⭐⭐⭐⭐ (4/5) | Escala linealmente, sin reentrenamiento |
| Explicabilidad | ⭐⭐⭐⭐⭐ (5/5) | Skills comunes/faltantes son la explicación directa |

**Total: 29/35**

**Veredicto:** Excelente como baseline y capa de explicabilidad. Insuficiente como motor único porque falla en variaciones semánticas y relaciones implícitas de skills.

---

## 2. TF-IDF + COSINE SIMILARITY

**Descripción:** Vectorización de texto por frecuencia inversa de documentos + similitud coseno entre vectores.

**Implementación actual:** Activo como fallback en `embedding_service.py`.

| Criterio | Puntuación | Justificación |
|---|---|---|
| Precisión | ⭐⭐⭐ (3/5) | Captura similitud léxica pero no semántica; "programación" ≠ "python" |
| Interpretabilidad | ⭐⭐⭐⭐ (4/5) | Los términos de mayor peso son explicables |
| Velocidad | ⭐⭐⭐⭐⭐ (5/5) | Muy rápido después del fit inicial |
| Costo | ⭐⭐⭐⭐⭐ (5/5) | Sin GPU, scikit-learn puro |
| Mantenimiento | ⭐⭐⭐⭐ (4/5) | Re-fit necesario cuando se agregan documentos |
| Escalabilidad | ⭐⭐⭐⭐ (4/5) | Matrices dispersas, escala razonablemente |
| Explicabilidad | ⭐⭐⭐ (3/5) | Top-n términos pero no skills estructuradas |

**Total: 29/35**

**Veredicto:** Buena capa de recuperación léxica. Complementario a embeddings. No reemplaza matching semántico profundo.

---

## 3. BM25

**Descripción:** Variante probabilística de TF-IDF con normalización por longitud de documento. Estándar en sistemas de recuperación de información.

| Criterio | Puntuación | Justificación |
|---|---|---|
| Precisión | ⭐⭐⭐ (3/5) | Mejor que TF-IDF puro en recuperación pero aún léxico |
| Interpretabilidad | ⭐⭐⭐⭐ (4/5) | Scores explicables por término |
| Velocidad | ⭐⭐⭐⭐⭐ (5/5) | Muy rápido, diseñado para motores de búsqueda |
| Costo | ⭐⭐⭐⭐⭐ (5/5) | Librería `rank-bm25` sin GPU |
| Mantenimiento | ⭐⭐⭐⭐ (4/5) | Index rebuild al agregar documentos |
| Escalabilidad | ⭐⭐⭐⭐ (4/5) | Muy usado en retrieval a escala |
| Explicabilidad | ⭐⭐⭐ (3/5) | Términos rankeados pero no skills estructuradas |

**Total: 29/35**

**Veredicto:** Excelente como primera etapa de retrieval en un pipeline híbrido (BM25 → reranking semántico). No debe usarse solo.

---

## 4. KNN (Sistema Actual Secundario)

**Descripción:** K vecinos más cercanos con multi-hot encoding de skills y distancia coseno.

**Implementación actual:** `scikit-learn NearestNeighbors(metric="cosine")` en `program_market_matching_service.py`.

| Criterio | Puntuación | Justificación |
|---|---|---|
| Precisión | ⭐⭐⭐ (3/5) | Depende de riqueza del vocabulario; multi-hot ignora semántica dentro de skills |
| Interpretabilidad | ⭐⭐⭐ (3/5) | "Vecinos más cercanos" no es intuitivo para usuarios no técnicos |
| Velocidad | ⭐⭐⭐⭐ (4/5) | Rápido para k pequeños; lento con corpus grande sin indexing |
| Costo | ⭐⭐⭐⭐⭐ (5/5) | Sin GPU, scikit-learn puro |
| Mantenimiento | ⭐⭐⭐ (3/5) | Requiere re-fit cuando cambia el corpus |
| Escalabilidad | ⭐⭐⭐ (3/5) | O(n) en búsqueda sin FAISS o HNSW |
| Explicabilidad | ⭐⭐ (2/5) | Difícil explicar al usuario por qué un job es "vecino" |

**Total: 23/35**

**Veredicto:** Adecuado como herramienta exploratoria pero no óptimo para producción escalable. Se mejora significativamente con embeddings densos en lugar de multi-hot binario.

---

## 5. RANDOM FOREST

**Descripción:** Ensemble de árboles de decisión entrenado sobre features de matching para clasificar relevancia (high/medium/low/no_match).

| Criterio | Puntuación | Justificación |
|---|---|---|
| Precisión | ⭐⭐⭐⭐ (4/5) | Muy buena con features bien diseñadas y labels suficientes |
| Interpretabilidad | ⭐⭐⭐⭐ (4/5) | Feature importance + partial dependence plots |
| Velocidad | ⭐⭐⭐⭐ (4/5) | Inferencia rápida; entrenamiento moderado |
| Costo | ⭐⭐⭐⭐ (4/5) | Sin GPU, scikit-learn |
| Mantenimiento | ⭐⭐⭐ (3/5) | Requiere labels y re-entrenamiento periódico |
| Escalabilidad | ⭐⭐⭐⭐ (4/5) | Buena paralelización |
| Explicabilidad | ⭐⭐⭐⭐ (4/5) | SHAP values disponibles, features interpretables |

**Total: 27/35**

**Veredicto:** Excelente candidato para la capa de ranking final si se tienen labels de entrenamiento. Requiere ~500-2000 ejemplos etiquetados.

---

## 6. XGBoost

**Descripción:** Gradient Boosting optimizado. Estándar de la industria para tabular data con features numéricas.

| Criterio | Puntuación | Justificación |
|---|---|---|
| Precisión | ⭐⭐⭐⭐⭐ (5/5) | Estado del arte en tabular data con features bien diseñadas |
| Interpretabilidad | ⭐⭐⭐⭐ (4/5) | SHAP nativo, feature importance, gain |
| Velocidad | ⭐⭐⭐⭐ (4/5) | Rápido en inferencia; entrenamiento moderado |
| Costo | ⭐⭐⭐⭐ (4/5) | CPU funciona bien; GPU opcional |
| Mantenimiento | ⭐⭐⭐ (3/5) | Requiere labels y re-entrenamiento |
| Escalabilidad | ⭐⭐⭐⭐ (4/5) | Distribuible, buen soporte |
| Explicabilidad | ⭐⭐⭐⭐⭐ (5/5) | SHAP es estándar, top en interpretabilidad ML |

**Total: 29/35**

**Veredicto:** **Candidato principal para la capa de scoring final.** Con features numéricas existentes (jaccard, cosine, coverage, domain_factor) + labels de relevancia, supera a KNN de forma medible.

---

## 7. LightGBM

**Descripción:** Gradient Boosting optimizado por Microsoft. Más rápido que XGBoost, especialmente con datos categóricos.

| Criterio | Puntuación | Justificación |
|---|---|---|
| Precisión | ⭐⭐⭐⭐⭐ (5/5) | Equiparable a XGBoost, superior en algunas benchmarks |
| Interpretabilidad | ⭐⭐⭐⭐ (4/5) | SHAP disponible |
| Velocidad | ⭐⭐⭐⭐⭐ (5/5) | Más rápido que XGBoost en training |
| Costo | ⭐⭐⭐⭐ (4/5) | Muy eficiente en memoria |
| Mantenimiento | ⭐⭐⭐ (3/5) | Requiere labels y re-entrenamiento |
| Escalabilidad | ⭐⭐⭐⭐⭐ (5/5) | Diseñado para datasets grandes |
| Explicabilidad | ⭐⭐⭐⭐ (4/5) | SHAP disponible |

**Total: 31/35**

**Veredicto:** **Alternativa superior a XGBoost para producción.** Especialmente útil si el corpus de empleos crece significativamente. Primera opción para la capa de ranking.

---

## 8. CatBoost

**Descripción:** Gradient Boosting de Yandex, especializado en variables categóricas sin codificación manual.

| Criterio | Puntuación | Justificación |
|---|---|---|
| Precisión | ⭐⭐⭐⭐⭐ (5/5) | Excelente con categorías (domain, skill_category) |
| Interpretabilidad | ⭐⭐⭐⭐ (4/5) | SHAP disponible |
| Velocidad | ⭐⭐⭐⭐ (4/5) | Más lento que LightGBM en training |
| Costo | ⭐⭐⭐ (3/5) | GPU recomendado para máximo rendimiento |
| Mantenimiento | ⭐⭐⭐ (3/5) | Requiere labels |
| Escalabilidad | ⭐⭐⭐⭐ (4/5) | Buena escalabilidad |
| Explicabilidad | ⭐⭐⭐⭐ (4/5) | SHAP disponible |

**Total: 27/35**

**Veredicto:** Ventaja específica para features categóricas como domain_key y skill_category. Considerar si LightGBM no maneja bien las categorías del sistema.

---

## 9. SENTENCE TRANSFORMERS

**Descripción:** Modelos BERT fine-tuned para generar embeddings de oraciones semánticamente significativos.

**Modelos relevantes para español:**
- `paraphrase-multilingual-mpnet-base-v2` (768d, multilingüe)
- `paraphrase-multilingual-MiniLM-L12-v2` (384d, rápido)
- `hiiamsid/sentence_similarity_spanish_es` (español específico)

| Criterio | Puntuación | Justificación |
|---|---|---|
| Precisión | ⭐⭐⭐⭐⭐ (5/5) | Captura similitud semántica real, no solo léxica |
| Interpretabilidad | ⭐⭐ (2/5) | Embeddings densos no son interpretables directamente |
| Velocidad | ⭐⭐⭐ (3/5) | Inferencia ~50-200ms por texto sin GPU |
| Costo | ⭐⭐⭐ (3/5) | Requiere GPU para producción a escala; RAM significativa |
| Mantenimiento | ⭐⭐⭐⭐ (4/5) | Modelos pre-entrenados, sin re-entrenamiento frecuente |
| Escalabilidad | ⭐⭐⭐ (3/5) | Requiere FAISS o vectorDB para escala |
| Explicabilidad | ⭐⭐ (2/5) | Sin técnica adicional, caja negra |

**Total: 22/35**

**Veredicto:** **Componente esencial para recuperación semántica** pero no como motor único. Debe combinarse con reglas para explicabilidad y con un reranker para precisión final.

---

## 10. EMBEDDINGS OpenAI (text-embedding-3-small / large)

**Descripción:** API de embeddings de OpenAI. `text-embedding-3-small` (1536d), `text-embedding-3-large` (3072d).

| Criterio | Puntuación | Justificación |
|---|---|---|
| Precisión | ⭐⭐⭐⭐⭐ (5/5) | Estado del arte en benchmarks MTEB |
| Interpretabilidad | ⭐⭐ (2/5) | Caja negra de API externa |
| Velocidad | ⭐⭐⭐ (3/5) | Latencia de API ~100-500ms; cacheable |
| Costo | ⭐⭐ (2/5) | $0.02/1M tokens (small), $0.13/1M (large); acumula en escala |
| Mantenimiento | ⭐⭐⭐ (3/5) | Dependencia de proveedor externo; modelo puede cambiar |
| Escalabilidad | ⭐⭐ (2/5) | Batch API disponible pero costo escala |
| Explicabilidad | ⭐⭐ (2/5) | Sin explicabilidad nativa |

**Total: 19/35**

**Veredicto:** Excelente precisión pero **dependencia de tercero inaceptable para producción crítica** en contexto educativo institucional. Usar para prototipos y comparación, no en producción.

---

## 11. EMBEDDINGS BGE (BAAI/bge-m3)

**Descripción:** Beijing Academy of AI. Modelo multilingüe de alta precisión, open source.

**Modelos:** `BAAI/bge-m3` (dense + sparse + colbert), `BAAI/bge-large-en-v1.5`

| Criterio | Puntuación | Justificación |
|---|---|---|
| Precisión | ⭐⭐⭐⭐⭐ (5/5) | Top en MTEB, especialmente en retrieval |
| Interpretabilidad | ⭐⭐ (2/5) | Embeddings densos |
| Velocidad | ⭐⭐⭐ (3/5) | Requiere GPU para producción óptima |
| Costo | ⭐⭐⭐⭐ (4/5) | Open source, self-hosted |
| Mantenimiento | ⭐⭐⭐⭐ (4/5) | Sin dependencia externa, stable releases |
| Escalabilidad | ⭐⭐⭐ (3/5) | Con FAISS/Weaviate escala bien |
| Explicabilidad | ⭐⭐ (2/5) | Sin explicabilidad nativa |

**Total: 23/35**

**Veredicto:** **Candidato preferido** sobre OpenAI para embeddings en producción institucional. Open source, multilingüe, alta precisión.

---

## 12. EMBEDDINGS E5 (intfloat/multilingual-e5)

**Descripción:** Microsoft Research. `multilingual-e5-large` soporta 100+ idiomas incluyendo español.

| Criterio | Puntuación | Justificación |
|---|---|---|
| Precisión | ⭐⭐⭐⭐⭐ (5/5) | Top en benchmarks multilingüe, especialmente español |
| Interpretabilidad | ⭐⭐ (2/5) | Embeddings densos |
| Velocidad | ⭐⭐⭐ (3/5) | Similar a BGE, requiere GPU |
| Costo | ⭐⭐⭐⭐ (4/5) | Open source |
| Mantenimiento | ⭐⭐⭐⭐ (4/5) | Stable, Microsoft Research |
| Escalabilidad | ⭐⭐⭐ (3/5) | Con vectorDB |
| Explicabilidad | ⭐⭐ (2/5) | Sin explicabilidad nativa |

**Total: 23/35**

**Veredicto:** **Igual de válido que BGE.** Especialmente fuerte para textos en español como descripciones de programas académicos colombianos.

---

## 13. HYBRID RETRIEVAL (BM25 + Dense Embeddings)

**Descripción:** Combina recuperación léxica (BM25) con semántica (embeddings) usando RRF (Reciprocal Rank Fusion) o score interpolation.

**Patrón:** `final_score = α * bm25_score + (1-α) * embedding_similarity`

| Criterio | Puntuación | Justificación |
|---|---|---|
| Precisión | ⭐⭐⭐⭐⭐ (5/5) | Captura tanto coincidencias exactas como semánticas |
| Interpretabilidad | ⭐⭐⭐ (3/5) | BM25 parte es interpretable; embeddings no |
| Velocidad | ⭐⭐⭐⭐ (4/5) | BM25 muy rápido; embeddings cacheables |
| Costo | ⭐⭐⭐ (3/5) | Requiere GPU para embeddings |
| Mantenimiento | ⭐⭐⭐ (3/5) | Dos sistemas a mantener + calibración de α |
| Escalabilidad | ⭐⭐⭐⭐ (4/5) | Arquitectura de retrieval a escala |
| Explicabilidad | ⭐⭐⭐ (3/5) | BM25 contribución explicable |

**Total: 25/35**

**Veredicto:** **Arquitectura recomendada para la capa de recuperación.** Estándar de la industria en sistemas RAG y motores de búsqueda modernos.

---

## 14. LEARNING-TO-RANK (LTR)

**Descripción:** Modelos supervisados que aprenden a ordenar candidatos según relevancia (pairwise o listwise). Implementaciones: LambdaMART, RankNet, LightGBM-rank.

| Criterio | Puntuación | Justificación |
|---|---|---|
| Precisión | ⭐⭐⭐⭐⭐ (5/5) | Optimiza directamente para ranking, no clasificación |
| Interpretabilidad | ⭐⭐⭐⭐ (4/5) | Con SHAP si usa LightGBM-rank |
| Velocidad | ⭐⭐⭐⭐ (4/5) | Rápida inferencia después de retrieval |
| Costo | ⭐⭐⭐ (3/5) | Requiere pares de preferencia etiquetados |
| Mantenimiento | ⭐⭐⭐ (3/5) | Necesita colección de feedback continua |
| Escalabilidad | ⭐⭐⭐⭐ (4/5) | Usado a escala en motores de búsqueda |
| Explicabilidad | ⭐⭐⭐⭐ (4/5) | Features de ranking explicables |

**Total: 27/35**

**Veredicto:** **Candidato ideal para la capa de ranking final** una vez que haya suficiente feedback humano. Requiere ~200-500 pares etiquetados mínimo.

---

## 15. GRAPH-BASED MATCHING

**Descripción:** Modela programas, empleos y skills como nodos en un grafo. Usa algoritmos de proximidad (PageRank, random walks, GNN) para matching.

| Criterio | Puntuación | Justificación |
|---|---|---|
| Precisión | ⭐⭐⭐⭐ (4/5) | Captura relaciones transitivas entre skills |
| Interpretabilidad | ⭐⭐⭐ (3/5) | Paths en el grafo son explicables |
| Velocidad | ⭐⭐ (2/5) | GNN complejas son lentas sin optimización |
| Costo | ⭐⭐⭐ (3/5) | Infraestructura de grafo adicional |
| Mantenimiento | ⭐⭐ (2/5) | Alta complejidad de mantenimiento |
| Escalabilidad | ⭐⭐⭐ (3/5) | Requiere graph DB (Neo4j, etc.) |
| Explicabilidad | ⭐⭐⭐ (3/5) | Paths explicables pero complejos |

**Total: 20/35**

**Veredicto:** Valor arquitectónico en el mediano plazo cuando el grafo de skills sea rico. No recomendado para primera iteración de producción.

---

## 16. KNOWLEDGE GRAPH

**Descripción:** Grafo de conocimiento estructurado con ontologías de skills (ESCO, O*NET, skills colombianas). Permite razonamiento sobre relaciones entre competencias.

| Criterio | Puntuación | Justificación |
|---|---|---|
| Precisión | ⭐⭐⭐⭐ (4/5) | Alta si el KG es completo y actualizado |
| Interpretabilidad | ⭐⭐⭐⭐⭐ (5/5) | Relaciones explícitas y trazables |
| Velocidad | ⭐⭐⭐ (3/5) | SPARQL queries pueden ser lentas |
| Costo | ⭐⭐ (2/5) | Alto costo de construcción y mantenimiento del KG |
| Mantenimiento | ⭐ (1/5) | Requiere curación continua de ontologías |
| Escalabilidad | ⭐⭐⭐ (3/5) | Triple stores escalan pero con complejidad |
| Explicabilidad | ⭐⭐⭐⭐⭐ (5/5) | Máxima explicabilidad por diseño |

**Total: 23/35**

**Veredicto:** Excelente para explicabilidad regulatoria (contexto educativo). **Alta fricción de construcción.** Recomendado solo en fase 3+ de madurez del sistema. Integrar ESCO como taxonomía de referencia.

---

## 17. ENSEMBLE MODELS

**Descripción:** Combinación de múltiples modelos (Stacking, Voting, Blending) para aprovechar las fortalezas de cada uno.

**Ejemplo de ensemble para este caso:**
```
Layer 1: BM25 (recall) + BGE Embeddings (semántica)
Layer 2: LightGBM reranker (scoring tabular)
Layer 3: Rules postprocessing (explicabilidad + filtros)
```

| Criterio | Puntuación | Justificación |
|---|---|---|
| Precisión | ⭐⭐⭐⭐⭐ (5/5) | Combina fortalezas, reduce debilidades individuales |
| Interpretabilidad | ⭐⭐⭐ (3/5) | Depende de componentes; las reglas aportan interpretabilidad |
| Velocidad | ⭐⭐⭐ (3/5) | Múltiples modelos en pipeline; latencia acumulada |
| Costo | ⭐⭐ (2/5) | Infraestructura compleja; múltiples modelos |
| Mantenimiento | ⭐⭐ (2/5) | Múltiples componentes para mantener |
| Escalabilidad | ⭐⭐⭐⭐ (4/5) | Cada capa puede escalar independientemente |
| Explicabilidad | ⭐⭐⭐⭐ (4/5) | Layer de reglas provee justificación al usuario |

**Total: 23/35**

**Veredicto:** **Arquitectura óptima a largo plazo.** El sistema actual ya es un ensemble implícito (reglas + KNN). Formalizar y optimizar la arquitectura de ensemble es el camino correcto.

---

## TABLA COMPARATIVA CONSOLIDADA

| # | Modelo | Precisión | Interpretabilidad | Velocidad | Costo | Mantenimiento | Escalabilidad | Explicabilidad | **TOTAL** |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Rule-Based (actual) | 3 | 5 | 5 | 5 | 2 | 4 | 5 | **29** |
| 2 | TF-IDF + Cosine | 3 | 4 | 5 | 5 | 4 | 4 | 3 | **28** |
| 3 | BM25 | 3 | 4 | 5 | 5 | 4 | 4 | 3 | **28** |
| 4 | KNN (actual) | 3 | 3 | 4 | 5 | 3 | 3 | 2 | **23** |
| 5 | Random Forest | 4 | 4 | 4 | 4 | 3 | 4 | 4 | **27** |
| 6 | XGBoost | 5 | 4 | 4 | 4 | 3 | 4 | 5 | **29** |
| **7** | **LightGBM** | **5** | **4** | **5** | **4** | **3** | **5** | **4** | **🏆 30** |
| 8 | CatBoost | 5 | 4 | 4 | 3 | 3 | 4 | 4 | **27** |
| 9 | Sentence Transformers | 5 | 2 | 3 | 3 | 4 | 3 | 2 | **22** |
| 10 | OpenAI Embeddings | 5 | 2 | 3 | 2 | 3 | 2 | 2 | **19** |
| **11** | **BGE Embeddings** | **5** | **2** | **3** | **4** | **4** | **3** | **2** | **23** |
| **12** | **E5 Multilingual** | **5** | **2** | **3** | **4** | **4** | **3** | **2** | **23** |
| **13** | **Hybrid Retrieval** | **5** | **3** | **4** | **3** | **3** | **4** | **3** | **🥈 25** |
| 14 | Learning-to-Rank | 5 | 4 | 4 | 3 | 3 | 4 | 4 | **27** |
| 15 | Graph-Based | 4 | 3 | 2 | 3 | 2 | 3 | 3 | **20** |
| 16 | Knowledge Graph | 4 | 5 | 3 | 2 | 1 | 3 | 5 | **23** |
| **17** | **Ensemble (híbrido)** | **5** | **3** | **3** | **2** | **2** | **4** | **4** | **23** |

---

## CONCLUSIONES DEL BENCHMARK

### Para producción inmediata (0-3 meses):
**LightGBM** como reranker sobre features existentes (jaccard, cosine, coverage, domain_factor, skill_count) es la mejora de mayor impacto con menor fricción. Solo requiere ~500-1000 pares etiquetados.

### Para recuperación semántica (1-6 meses):
**BGE-m3 o E5 multilingual** como capa de embeddings, combinado con **BM25** para hybrid retrieval. Elimina la dependencia de vocabulario estático actual.

### Para explicabilidad en contexto educativo:
**Rules layer + SHAP sobre LightGBM** proveen la combinación de explicabilidad institucional que requiere un observatorio educativo.

### Para la visión a largo plazo (6-18 meses):
**Learning-to-Rank** sobre pares de preferencia recolectados, combinado con Knowledge Graph basado en ESCO.

---

*Documento generado: 2026-06-07 | Benchmark: FASE 2 COMPLETA*
