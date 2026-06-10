# Audit: ml/ml_match_program_jobs.py — Motor de Matching
**Fecha:** 2026-06-09  
**Rama:** `codex/dashboard-v1`

---

## 1. Fórmula del score_match

```
score = clamp( skill_overlap_score × 0.68  +  role_score × 0.32 )

skill_overlap_score = clamp( program_coverage × 0.70  +  job_density × 0.30 )
  program_coverage  = len(common_skills) / max(len(program_skills), 1)  × 100
  job_density       = len(common_skills) / max(len(job_skills),     1)  × 100

role_score = text_affinity(program_text, job_text) × 100
  text_affinity = token_overlap × 0.45
               + sequence_similarity × 0.20
               + role_group_score × 0.35

Penalización por conflicto de rol:
  score     = score × 0.55
  role_score = role_score × 0.50
```

### Etiquetas de relevancia
| score | common_count | label |
|---|---|---|
| ≥ 75 y ≥ 2 skills | — | `high` |
| ≥ 50 y ≥ 1 skill  | — | `medium` |
| ≥ 30 y ≥ 1 skill  | — | `low` |
| resto              | — | `no_match` |

---

## 2. Fuente de skills del programa

**Tabla:** `ml_program_skill_labels`  
**Condición:** `label_type = 'positive'`  
**Join:** `ml_program_documents` → `ml_program_skill_labels`

> ⚠️ **Problema**: NO lee de `microcurriculo_skills`. Los skills del programa vienen de labels manuales/etiquetados ML, no del microcurrículo real. Si la tabla `ml_program_skill_labels` está vacía o desactualizada, los programas tendrán `program_skills = []` y el score basado en skills será siempre 0.

---

## 3. Fuente de skills del empleo

**Tabla principal:** `empleos`  
**Columnas de texto usadas:**
- `matched_skills` (texto libre)
- `missing_skills` (texto libre)
- `skills_text` (texto libre)
- `titulo` y `descripcion` (para extracción implícita)

**Join adicional:** `empleo_skills` → `skills.nombre` (tabla de skills normalizada)

> ⚠️ **Problema**: Lee de la tabla `empleos` con columnas españolas (`titulo`, `empresa`, `ubicacion`, `fuente`), pero los scrapers nuevos insertan en una tabla `jobs` con columnas en inglés (`title`, `company`, `location`, `source`). Si los empleos nuevos están en `jobs` y no en `empleos`, el motor no los procesa.

---

## 4. skill_overlap_score — análisis detallado

```python
program_coverage = common / program_skills  # ¿qué parte del programa cubre el empleo?
job_density      = common / job_skills       # ¿qué tan denso es el empleo en skills del programa?
skill_overlap    = program_coverage×0.70 + job_density×0.30
```

**Sesgo observado:** pondera 70% `program_coverage`. Un programa con pocos skills etiquetados obtendrá cobertura artificialmente alta con 1 skill en común (ej: 1/2 = 50%). Un programa con 20 skills etiquetados necesitará 14 en común para llegar al mismo score.

**Corrección sugerida:** usar F1-score de conjuntos:
```
precision = common / job_skills
recall    = common / program_skills
skill_overlap = 2 × precision × recall / (precision + recall)
```

---

## 5. role_alignment — análisis detallado

```python
text_affinity(program_text, job_text):
  token_overlap     = |tokens_P ∩ tokens_J| / |tokens_J|   # jaccard asimétrico
  sequence_sim      = SequenceMatcher ratio (primeros 300 chars cada uno)
  role_group_score  = 45 + (program_hits×12) + (job_hits×12)  cuando hay co-presencia en mismo grupo
```

**Problemas:**
1. `token_overlap` divide por `|tokens_J|` (job), no por la unión — favorece empleos con vocabulario pequeño.
2. `sequence_sim` sobre los primeros 300 caracteres ignora el cuerpo del texto si el inicio no es representativo.
3. `role_group_score` puede alcanzar máximo de 45+(5×12)+(5×12)=165, pero se divide por 100 antes de aplicar peso — efectivamente puede exceder 1.0 antes del clamp final.

---

## 6. Diagnóstico general

| Componente | Estado | Severidad |
|---|---|---|
| Skills del programa de `microcurriculo_skills` | ❌ No se usa | Alta |
| Jobs de tabla `jobs` (scrapers nuevos) | ❌ No se procesa | Alta |
| `program_coverage` sesgado por programas con pocos skills | ⚠️ Sesgo | Media |
| `sequence_sim` sobre 300 chars | ⚠️ Parcial | Baja |
| `role_group_score` puede > 1.0 antes de clamp | ⚠️ Límite | Baja |
| Normalización SKILL_ALIASES cubre herramientas clave (SQL, Python, Power BI) | ✅ Correcto | — |
| Penalización por conflicto de rol (software ↔ datos) | ✅ Correcto | — |
| `ON CONFLICT` en todos los INSERTs (idempotente) | ✅ Correcto | — |

---

## 7. Propuestas de mejora

### Alta prioridad

**A. Conectar con `microcurriculo_skills`**  
Reemplazar la fuente de skills del programa en `load_latest_programs()`:
```sql
-- Reemplazar join con ml_program_skill_labels por:
LEFT JOIN microcurriculos mc ON mc.specialization_id = mp.especializacion_id
LEFT JOIN microcurriculo_skills ms ON ms.microcurriculo_id = mc.id
-- skill: COALESCE(NULLIF(ms.skill_normalized,''), NULLIF(ms.skill_original,''))
```

**B. Unificar `empleos` y `jobs`**  
La query `load_jobs()` debería incluir un `UNION ALL` o vista que combine ambas tablas:
```sql
SELECT id, titulo AS title, empresa AS company, ... FROM empleos
UNION ALL
SELECT id, title, company, ... FROM jobs
```

### Media prioridad

**C. Usar F1-score en skill_overlap**
```python
precision = common / max(job_skills, 1)
recall    = common / max(program_skills, 1)
if precision + recall > 0:
    skill_overlap = 2 * precision * recall / (precision + recall) * 100
```

**D. Extender `sequence_sim` a más texto**  
Cambiar `:300` a `:800` o usar el promedio de múltiples ventanas.

---

*Reporte generado: 2026-06-09 | Motor: rules_v1 | Rama: codex/dashboard-v1*
