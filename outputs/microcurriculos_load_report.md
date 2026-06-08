# Reporte: Carga de Microcurrículos
**Fecha:** 2026-06-08  
**Script:** `scripts/load_microcurriculos.py`  

---

## Resumen

| Métrica | Valor |
|---------|-------|
| Archivos .docx encontrados | 13 |
| Asignaturas extraídas | 22 |
| Skills extraídos | 104 |
| DB disponible | ❌ No (sin .env.local) |
| Ya en DB (duplicados) | 0 |
| A insertar (nuevos) | 22 |

## Archivos encontrados

| # | Archivo | Programa | Asignaturas |
|---|---------|----------|------------|
| 1 | `ADE _S.5 _B. 1 _Gerencia Financiera.docx` | Administración de Empresas | 1 |
| 2 | `Diseño de proyectos orientados a la innovación.docx` | Especialización en Dirección y Gestión de Proyecto | 1 |
| 3 | `INFORMACIÓN ESP CRIMINOLOGIA - piloto app - v1 - 28may26.doc` | Especialización en Criminología y Victimología | 10 |
| 4 | `Microcurrículos V5_Análisis e interpretación de datos.docx` | Especialización en Visual Analytics y Big Data | 1 |
| 5 | `Microcurrículos V5_Electiva Innovación Tecnológica y Transfo` | Especialización en Visual Analytics y Big Data | 1 |
| 6 | `Microcurrículos V5_Fundamentos tecnológicos para el tratamie` | Especialización en Visual Analytics y Big Data | 1 |
| 7 | `Microcurrículos V5_Gestión de proyectos de inteligencia de n` | Especialización en Visual Analytics y Big Data | 1 |
| 8 | `Microcurrículos V5_Gobierno del dato y toma de decisiones.do` | Especialización en Visual Analytics y Big Data | 1 |
| 9 | `Microcurrículos V5_Ingenieria para el procesado masivo de da` | Especialización en Visual Analytics y Big Data | 1 |
| 10 | `Microcurrículos V5_Seguridad en Sistemas, Aplicaciones y el ` | Especialización en Visual Analytics y Big Data | 1 |
| 11 | `Microcurrículos V5_Tecnicas de Inteligencia Artificial.docx` | Especialización en Visual Analytics y Big Data | 1 |
| 12 | `Microcurrículos V5_Visualización Interactiva de la Informaci` | Especialización en Visual Analytics y Big Data | 1 |
| 13 | `aprendizaje automatico.docx` | Especialización en Inteligencia Artificial | 1 |

## Detalle por programa

### Administración de Empresas
- `especializacion_id` = None  
- `domain_key` = `business`  
- Asignaturas: 1

| Asignatura | RA | Skills | Estado |
|------------|-----|--------|--------|
| Gerencia Financiera | 2 | 4 | Nuevo |

### Especialización en Criminología y Victimología
- `especializacion_id` = None  
- `domain_key` = `criminology`  
- Asignaturas: 10

| Asignatura | RA | Skills | Estado |
|------------|-----|--------|--------|
| Fundamentos teóricos y marcos legales en Psicología criminal | 2 | 4 | Nuevo |
| Psicopatología Forense | 2 | 4 | Nuevo |
| Victimología Forense | 2 | 4 | Nuevo |
| Pruebas Psicométricas: Análisis Aplicado | 2 | 4 | Nuevo |
| La Prueba Pericial y el Informe Forense | 2 | 4 | Nuevo |
| Técnicas de perfilación criminal | 2 | 4 | Nuevo |
| Valoración Psicológica del Testimonio en Contextos Forenses | 2 | 4 | Nuevo |
| Electiva opción 1: Peritaje Psicológico en la Jurisdicción P | 2 | 4 | Nuevo |
| Electiva opción 2: Herramientas de Análisis Criminológico | 2 | 4 | Nuevo |
| Resultados de Aprendizaje de la Asignatura | 0 | 4 | Nuevo |

### Especialización en Dirección y Gestión de Proyectos
- `especializacion_id` = None  
- `domain_key` = `business`  
- Asignaturas: 1

| Asignatura | RA | Skills | Estado |
|------------|-----|--------|--------|
| Diseño de proyectos orientados a la innovación | 1 | 2 | Nuevo |

### Especialización en Inteligencia Artificial
- `especializacion_id` = None  
- `domain_key` = `artificial_intelligence`  
- Asignaturas: 1

| Asignatura | RA | Skills | Estado |
|------------|-----|--------|--------|
| Aprendizaje automático | 1 | 5 | Nuevo |

### Especialización en Visual Analytics y Big Data
- `especializacion_id` = None  
- `domain_key` = `data_analytics`  
- Asignaturas: 9

| Asignatura | RA | Skills | Estado |
|------------|-----|--------|--------|
| Análisis e interpretación de datos | 2 | 3 | Nuevo |
| Innovación tecnológica y transformación digital en las empre | 2 | 5 | Nuevo |
| Fundamentos Tecnológicos par el Tratamiento de Datos | 2 | 4 | Nuevo |
| Gestión de proyectos de inteligencia de negocio | 2 | 3 | Nuevo |
| Gobierno del dato y toma de decisiones | 2 | 12 | Nuevo |
| Ingeniería para el procesado masivo de datos | 3 | 8 | Nuevo |
| Seguridad en Sistemas, Aplicaciones y el Big Data | 2 | 1 | Nuevo |
| Técnicas de Inteligencia Artificial | 3 | 11 | Nuevo |
| Visualización Interactiva de la Información | 1 | 6 | Nuevo |

## Mapeo de domain_key

| Programa (fragmento) | domain_key |
|----------------------|------------|
| `visual analytics` | `data_analytics` |
| `big data` | `data_analytics` |
| `inteligencia artificial` | `artificial_intelligence` |
| `machine learning` | `artificial_intelligence` |
| `criminolog` | `criminology` |
| `victimolog` | `criminology` |
| `gerencia` | `business` |
| `administracion` | `business` |
| `gestion de proyectos` | `business` |
| `direccion` | `business` |
| `derecho` | `law` |
| `educacion` | `education` |
| `ambiental` | `health` |
| `salud` | `health` |

## Estructura de tablas usadas

### microcurriculos
```
programa, asignatura, semestre, source_document, document_hash,
clean_text, detected_domain, specialization_id, specialization_name, lineage
```

### microcurriculo_skills
```
microcurriculo_id, skill_original, skill_normalized,
skill_domain, tipo_skill (tecnologia|skill_tecnica|herramienta|
plataforma|skill_transversal|metodologia), confidence_score=0.70, source_document
```

### especializaciones (UPDATE detected_domain si columna existe)
```
UPDATE especializaciones SET detected_domain = <domain_key> WHERE id = <esp_id>
```

## Instrucciones de ejecución

```bash
# 1. Crear .env.local con la URL de producción
echo 'RAILWAY_DATABASE_URL=postgresql://...' > .env.local

# 2. Preview (sin tocar la DB)
python scripts/load_microcurriculos.py --preview

# 3. Ejecutar inserts (pide confirmación)
python scripts/load_microcurriculos.py --execute
```

---

*Reporte generado: 2026-06-08*