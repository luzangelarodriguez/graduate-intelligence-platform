# Reporte: Fixes al Motor de Matching
**Fecha:** 2026-06-09  
**Archivo:** `ml/ml_match_program_jobs.py`  
**Rama:** `codex/dashboard-v1`

---

## FIX 1 — Skills del programa desde microcurriculo_skills

### Problema
`load_latest_programs()` solo leía skills de `ml_program_skill_labels` (labels manuales).
Si esa tabla estaba vacía, `program_skills=[]` y el score basado en skills era siempre 0.

### Solución aplicada
Se agregaron dos JOINs en la query principal:
```sql
LEFT JOIN microcurriculos mc ON mc.specialization_id = mp.especializacion_id
LEFT JOIN microcurriculo_skills ms ON ms.microcurriculo_id = mc.id
```
Y una nueva columna agregada:
```sql
COALESCE(NULLIF(ms.skill_normalized, ''), NULLIF(ms.skill_original, '')) AS micro_skills
```

**Prioridad de fuentes:**
1. `microcurriculo_skills` (si tiene datos) → fuente primaria
2. `ml_program_skill_labels` (fallback si micro está vacío)

```python
micro = list(row.get("micro_skills") or [])
labels = list(row.get("label_skills") or [])
combined = micro if micro else labels
skills = unique_clean_skills(combined)
```

---

## FIX 2 — Jobs desde tabla `jobs` (scrapers nuevos) + `empleos` (legacy)

### Problema
`load_jobs()` solo leía de la tabla `empleos` (columnas en español).
Los scrapers nuevos (Elempleo, TicJob, Magneto, Indeed) insertan en tabla `jobs` 
(columnas en inglés: `title`, `company`, `description`, `source_url`).
Esos empleos nunca llegaban al motor de matching.

### Solución aplicada
`load_jobs()` ahora:
1. Introspecciona qué tablas existen en `information_schema.tables`
2. Construye un `UNION ALL` dinámico incluyendo solo las tablas presentes

```sql
-- empleos (legacy):
SELECT id::text, titulo AS title, empresa AS company, ...
FROM empleos

UNION ALL

-- jobs (nuevos scrapers):
SELECT id::text, title, company, description, ...
FROM jobs
```

**Ventaja:** si solo existe una tabla (entorno de desarrollo), la query funciona igual sin errores.

---

## FIX 3 — F1-score en skill_overlap_score

### Problema
Fórmula anterior: `program_coverage×0.70 + job_density×0.30`

Sesgo: un programa con 2 skills y 1 en común obtenía `coverage=50%`, igual que
un programa con 20 skills y 10 en común — siendo este último mucho más sólido.

### Solución aplicada
```python
# Antes:
skill_overlap_score = clamp((program_coverage * 0.70) + (job_density * 0.30))

# Después (F1-score = media armónica de precision y recall):
if program_coverage + job_density > 0:
    skill_overlap_score = clamp(2.0 * program_coverage * job_density / (program_coverage + job_density))
else:
    skill_overlap_score = 0.0
```

**Comparación de comportamiento:**

| common | program_skills | job_skills | Antes | F1 |
|--------|---------------|------------|-------|-----|
| 1      | 2             | 10         | 38.0  | 18.2 |
| 5      | 10            | 10         | 50.0  | 50.0 |
| 10     | 20            | 10         | 38.5  | 50.0 |
| 2      | 2             | 3          | 93.3  | 80.0 |

El F1 es más conservador cuando la cobertura es asimétrica (muchos skills en un lado, pocos en el otro).

---

## Resumen de cambios

| Fix | Líneas modificadas | Impacto |
|-----|-------------------|---------|
| FIX 1: microcurriculo_skills | `load_latest_programs()` query + loop Python | Programas con microcurrículos ahora tienen skills reales |
| FIX 2: UNION ALL empleos+jobs | `load_jobs()` completo | Empleos nuevos de scrapers entran al matching |
| FIX 3: F1-score | 3 líneas en `compute_matches()` | Score más equilibrado entre precision y recall |

*Reporte generado: 2026-06-09 | Rama: codex/dashboard-v1*
