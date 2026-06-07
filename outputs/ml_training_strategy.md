# Estrategia de Entrenamiento ML
**Proyecto:** Observatorio Institucional de Inteligencia Curricular  
**Fecha:** 2026-06-07  
**Alcance:** Diseño de datasets, labels, feedback humano y active learning

---

## ESTADO ACTUAL DEL DATASET

### Infraestructura Existente (Lista pero Vacía)
```sql
ml_training_runs          → Registros de runs (infraestructura OK)
ml_program_documents      → Documentos normalizados (¿cuántos rows? desconocido)
ml_program_skill_labels   → Labels con label_source: human/weak_supervision/model
ml_job_documents          → Documentos de empleos normalizados
ml_skill_labels           → Labels de skills de empleos
ml_program_job_matches    → matches con match_method='rules_v1' (ACTIVO)
```

### Calidad Actual del Dataset
| Aspecto | Estado | Problema |
|---|---|---|
| Matches generados | ✅ Activo | Solo método `rules_v1`, sin validación humana |
| Labels positivos | ⚠️ Parcial | Generados automáticamente por reglas, no validados |
| Labels negativos | ❌ Ausente | No hay ejemplos negativos explícitos etiquetados |
| Feedback humano | ❌ Ausente | `label_source='human'` en schema pero sin datos reales |
| Active learning | ❌ Ausente | Sin loop de selección de ejemplos inciertos |
| Ground truth | ❌ Ausente | Sin pares (programa, empleo) validados externamente |

**Conclusión:** El sistema tiene la infraestructura de entrenamiento diseñada pero vacía de labels humanos reales.

---

## DISEÑO DE DATASETS

### Dataset 1: Program-Job Relevance (Principal)

**Propósito:** Entrenar el ranker de la Capa 4 (LightGBM-Rank).

**Esquema:**
```python
@dataclass
class ProgramJobRelevanceSample:
    # Identificadores
    program_id: int
    job_id: int
    
    # Features de Capa 3 (Skill Matching)
    exact_jaccard: float           # [0-100]
    exact_coverage: float          # [0-100]
    exact_gap: float               # [0-100]
    skill_semantic_score: float    # [0-1] (nuevo)
    common_skill_count: int
    missing_skill_count: int
    program_skill_count: int
    job_skill_count: int
    
    # Features de Capa 2 (Retrieval)
    bm25_score: float              # [0-∞]
    dense_retrieval_score: float   # [0-1]
    
    # Features de Capa 1 (Dominio)
    domain_match: float            # 1.0 | 0.5 | 0.1
    program_domain: str            # encoded categorically
    job_domain: str                # encoded categorically
    domain_confidence: float       # [0.35-0.98]
    
    # Features contextuales
    program_level: int             # especializacion=2, maestria=3, doctorado=4
    has_role_conflict: bool
    
    # Label
    relevance_label: int           # 3=high, 2=medium, 1=low, 0=no_match
    label_source: str              # "human", "rules_v1", "weak_supervision"
    label_confidence: float        # [0-1]
```

**Volumen Requerido:**
- **Mínimo viable:** 500 pares etiquetados por humanos (suficiente para LightGBM básico)
- **Recomendado:** 2,000-5,000 pares para métricas confiables
- **Óptimo:** 10,000+ pares para Learning-to-Rank competitivo

**Fuentes de Labels:**
1. **Weak supervision (inmediato):** Usar `rules_v1` scores como proxy
   - score ≥ 75 + common_count ≥ 2 → label = 3 (high)
   - score ≥ 50 + common_count ≥ 1 → label = 2 (medium)
   - score ≥ 30 + common_count ≥ 1 → label = 1 (low)
   - else → label = 0 (no_match)

2. **Human labels (3-6 meses):** Coordinadores de programa validan matches
3. **Egresado feedback (6-12 meses):** Encuesta de pertinencia laboral post-egreso

---

### Dataset 2: Domain Classification

**Propósito:** Entrenar/afinar el clasificador de dominio de la Capa 1.

**Esquema:**
```python
@dataclass
class DomainClassificationSample:
    entity_id: int
    entity_type: str          # "program" | "job"
    text: str                 # Texto completo normalizado
    domain_label: str         # "data_analytics", "artificial_intelligence", ...
    subdomain_label: str      # "visual_analytics", "data_engineering", ...
    label_source: str         # "human" | "keyword_rule" | "weak_supervision"
    confidence: float
```

**Volumen Requerido:**
- 50-100 ejemplos por dominio × 12 dominios = **600-1,200 mínimo**
- El sistema actual genera ~100 ejemplos por dominio via keywords

---

### Dataset 3: Skill Extraction NER

**Propósito:** Mejorar el extractor de skills de descripciones de empleo.

**Esquema (ya existe parcialmente):**
```python
@dataclass
class SkillNERSample:
    document_id: int
    text: str
    skill_spans: list[SkillSpan]  # [(start, end, skill_text, category)]
    label_source: str
```

**Volumen Requerido:**
- **Mínimo:** 200 documentos anotados (empleos con spans de skills marcados)
- **Recomendado:** 500-1,000 para NER robusto

---

### Dataset 4: Skill Relatedness (Para el Grafo de Skills)

**Propósito:** Construir el grafo de relaciones entre skills para la Capa 3.

**Esquema:**
```python
@dataclass
class SkillRelatednessTriple:
    skill_a: str
    skill_b: str
    relation_type: str    # "is_subset_of" | "related_to" | "prerequisite_for" | "synonym"
    similarity_score: float  # [0-1]
    source: str           # "esco" | "cooccurrence" | "human"
```

**Fuentes:**
1. **ESCO Taxonomy:** European Skills framework en español (gratuito, ~3,000 skills)
2. **Co-ocurrencias en job postings:** Skills que aparecen juntos en los mismos empleos
3. **Curación manual:** Para el vocabulario específico colombiano

---

## ETIQUETAS POSITIVAS Y NEGATIVAS

### Definición de Etiquetas Positivas (label=3, label=2)

Un par (programa, empleo) es **positivo** si:
1. El programa prepara directamente para el rol descrito en el empleo
2. Al menos 2 skills core del programa coinciden con requisitos del empleo
3. El dominio del programa es igual o relacionado al dominio del empleo
4. Un egresado del programa podría aplicar al empleo sin reentrenamiento mayor

**Evidencias:**
```
✅ "Analítica de Datos" → Data Analyst: jaccard > 40%, domain_match = 1.0
✅ "IA Aplicada" → ML Engineer: coverage > 60%, semantic_score > 0.75
✅ "Gerencia de Proyectos" → Project Manager: role_affinity > 70%
```

### Definición de Etiquetas Negativas (label=0)

Un par (programa, empleo) es **negativo** si:
1. El dominio es completamente diferente (doctor → data scientist)
2. Las skills no tienen solapamiento y no son relacionadas
3. Hay conflicto de rol explícito (domain_factor = 0.1)
4. Un egresado necesitaría más de 1 año de reentrenamiento

**Evidencias:**
```
❌ "Criminología" → Full Stack Developer: domain_factor = 0.1, jaccard ≈ 0%
❌ "Enfermería" → Data Engineer: skill overlap = 0, domain conflict
❌ "Derecho" → Machine Learning Engineer: domain mismatch completo
```

### Etiquetas Negativas Difíciles (Hard Negatives — Críticas para LTR)

Los ejemplos más útiles para entrenamiento son los **falsos positivos del sistema actual:**
```
⚠️ Programa de "Big Data" con skills obsoletos → empleo de Data Scientist moderno
   (sistema actual da score alto por keywords, pero está desactualizado curricularmente)

⚠️ "Gestión de Proyectos" → "Project Manager de Software"
   (match de rol pero sin skills técnicas de software)
```

**Estrategia:** Revisar los matches de `rules_v1` con score 50-70 para encontrar falsos positivos.

---

## FEEDBACK HUMANO

### Protocolo de Anotación

**Anotadores recomendados (en orden de prioridad):**
1. **Coordinadores de programa** — Saben qué empleos son pertinentes para su currícula
2. **Empleadores aliados** — Saben qué programas producen candidatos adecuados
3. **Egresados** — Saben si el programa los preparó para su empleo actual

**Interface de anotación:**
```
┌────────────────────────────────────────────────────────┐
│  Programa: Especialización en Analítica de Datos       │
│  Empleo: Data Analyst - Bancolombia                    │
│                                                        │
│  Skills comunes: SQL, Power BI, Excel                  │
│  Skills faltantes: Python, Spark, Databricks           │
│                                                        │
│  ¿Qué tan pertinente es este empleo para el programa?  │
│                                                        │
│  ○ Alta pertinencia (egresado aplica directamente)     │
│  ○ Media pertinencia (egresado necesita algo más)      │
│  ○ Baja pertinencia (egresado necesita reentrenamiento)│
│  ○ No pertinente (empleo fuera del alcance)            │
│                                                        │
│  Comentario opcional: ___________________________      │
└────────────────────────────────────────────────────────┘
```

**Meta de anotación:**
- Fase 1: 50 pares/semana × 4 coordinadores = 200 pares/mes
- Fase 2: Automatizar con active learning para priorizar los más inciertos

### Tabla para Feedback Humano

```sql
CREATE TABLE ml_human_feedback (
    id              BIGSERIAL PRIMARY KEY,
    program_id      INTEGER REFERENCES especializaciones(id),
    job_id          INTEGER REFERENCES empleos(id),
    relevance_score INTEGER CHECK (relevance_score BETWEEN 0 AND 3),
    annotator_id    TEXT NOT NULL,
    annotator_role  TEXT,  -- 'coordinator', 'employer', 'graduate'
    comment         TEXT,
    session_id      UUID,
    annotation_time_ms INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## ACTIVE LEARNING

### Estrategia: Uncertainty Sampling

Seleccionar para anotación humana los pares donde el modelo tiene menor certeza:

```python
def select_samples_for_annotation(
    predictions: list[float],  # probabilidades del modelo actual
    n: int = 50                # muestras a seleccionar
) -> list[int]:
    # Uncertainty = distancia al decision boundary
    uncertainty = 1 - np.abs(predictions - 0.5) * 2
    return np.argsort(uncertainty)[-n:]
```

### Pipeline de Active Learning

```
Iteración 1:
  ├── Entrenar modelo v0 con weak labels (rules_v1)
  ├── Seleccionar top-50 inciertos
  ├── Enviar a anotadores humanos
  └── Re-entrenar modelo v1 con nuevos labels

Iteración 2:
  ├── Entrenar modelo v1
  ├── Seleccionar top-50 inciertos (diferentes a iteración 1)
  ├── Priorizar: hard negatives + casos de dominio nuevo
  └── Re-entrenar modelo v2

... repetir cada 2-4 semanas
```

### Criterios de Selección Inteligente

```python
def smart_sample_selection(candidates):
    # Prioridad 1: Modelos con alta incertidumbre
    uncertain = get_uncertain_samples(candidates, threshold=0.45)
    
    # Prioridad 2: Nuevos dominios con pocos ejemplos
    underrepresented = get_underrepresented_domains(candidates, min_samples=20)
    
    # Prioridad 3: Hard negatives (score alto por reglas pero semántica baja)
    hard_negatives = get_potential_false_positives(candidates)
    
    return merge_and_deduplicate(uncertain, underrepresented, hard_negatives)
```

---

## CUÁNTOS EJEMPLOS SE NECESITAN

### Por Tarea y Fase

| Tarea | Mínimo | Recomendado | Óptimo | Plazo Estimado |
|---|---|---|---|---|
| **LightGBM Ranker** (Capa 4) | 500 pares | 2,000 pares | 10,000 pares | 3-6 meses con anotadores |
| **Domain Classifier** | 600 ejemplos | 1,200 ejemplos | 2,400 ejemplos | 1-2 meses (weak supervision) |
| **Skill NER** | 200 docs | 500 docs | 1,000 docs | 2-4 meses |
| **Skill Graph** | 500 triples | 2,000 triples | 10,000 triples | 1 mes (ESCO import) |
| **E5 Fine-tuning** | 1,000 pares | 5,000 pares | 20,000 pares | 6-12 meses |

### Estrategia de Bootstrap (Semana 1-4)

Sin esperar labels humanos, se puede entrenar un modelo baseline útil:

```python
# Semana 1: Exportar todos los matches de rules_v1 como weak labels
weak_labels = db.query("""
    SELECT program_document_id, job_document_id,
           score_match, relevance_label,
           skill_overlap_score, role_alignment
    FROM ml_program_job_matches
    WHERE match_method = 'rules_v1'
    AND relevance_label != 'no_match'
""")

# Semana 2: Construir feature matrix
features = build_feature_matrix(weak_labels)

# Semana 3: Entrenar LightGBM v0
model_v0 = lgb.LGBMRanker().fit(features, labels=weak_labels.relevance_ordinal)

# Semana 4: Evaluar vs rules_v1 y seleccionar muestras para anotación humana
```

---

## MÉTRICAS DE EVALUACIÓN

### Métricas de Ranking
```
NDCG@5:  Normalized Discounted Cumulative Gain (top 5 resultados)
NDCG@10: Idem para top 10
MRR:     Mean Reciprocal Rank (primera respuesta relevante)
MAP:     Mean Average Precision
```

### Métricas de Clasificación
```
Precision@K:  De los K resultados, cuántos son realmente relevantes
Recall@K:     De todos los relevantes, cuántos están en top K
F1@K:         Balance entre precision y recall
```

### Métricas de Negocio
```
Coverage Rate:     % de programas con al menos 5 matches "high"
Gap Detection:     % de gaps curriculares identificados correctamente
Actionability:     % de recomendaciones que resultan en actualización curricular
User Satisfaction: Calificación de coordinadores sobre pertinencia de matches
```

### Baseline para Comparar
```
Sistema actual (rules_v1): Establece el piso de NDCG@10
Meta: LightGBM v1 supere rules_v1 en NDCG@10 en al menos 10%
```

---

## PLAN DE ENTRENAMIENTO POR FASES

### Fase 0 — Infraestructura (2 semanas)
- [ ] Script de exportación de weak labels desde `ml_program_job_matches`
- [ ] Pipeline de features para LightGBM (usar features existentes)
- [ ] Evaluador offline con métricas NDCG, MRR
- [ ] Tabla `ml_human_feedback` en PostgreSQL

### Fase 1 — Bootstrap con Weak Labels (Mes 1)
- [ ] Exportar 10,000-50,000 pares con `rules_v1` scores
- [ ] Entrenar LightGBM-Rank v0 sobre weak labels
- [ ] Comparar contra rules_v1 baseline
- [ ] Seleccionar top-200 inciertos para anotación humana

### Fase 2 — Primers Labels Humanos (Mes 2-4)
- [ ] Lanzar UI de anotación para coordinadores
- [ ] Meta: 200 pares/mes × 3 meses = 600 pares humanos
- [ ] Re-entrenar LightGBM-Rank v1 con mix weak+human (peso x5 para humanos)
- [ ] Validar mejora en NDCG

### Fase 3 — Embeddings + FAISS (Mes 3-6)
- [ ] Generar embeddings con E5-multilingual-small (balance velocidad/calidad)
- [ ] Construir FAISS index de empleos
- [ ] Integrar retrieval híbrido (BM25 + FAISS) en pipeline
- [ ] Agregar retrieval scores como features al LightGBM

### Fase 4 — Active Learning Continuo (Mes 6+)
- [ ] Loop automático: entrenar → seleccionar inciertos → anotar → re-entrenar
- [ ] Meta: 1,000+ pares humanos acumulados
- [ ] Evaluar fine-tuning de E5 sobre el corpus específico

---

*Documento generado: 2026-06-07 | Estrategia de Entrenamiento: FASE 4 COMPLETA*
