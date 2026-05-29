# Labor Matching Engine Phase 1

Fecha: 2026-05-25

## Objetivo

Diagnosticar y corregir programas con `0 empleos relacionados` en la plataforma Graduate Intelligence Platform.

## Diagnóstico inicial

Railway tenía datos curriculares, pero no tenía tablas laborales:

- `especializaciones`: 52
- `skills`: 179
- `especializacion_skills`: 250
- `empleos`: no existía
- `empleo_skills`: no existía
- `ml_program_job_matches`: no existía
- `vw_labor_program_job_matches`: no existía

Causa raíz:

El backend podía listar programas porque las tablas curriculares estaban cargadas, pero no podía calcular empleo relacionado porque faltaba la capa laboral en Railway.

## Correcciones implementadas

### 1. Migración de puente laboral

Archivo:

```text
database/migrations/008_labor_matching_bridge.sql
```

Crea:

- `labor_program_skill_matches`
- `vw_labor_program_job_matches`
- `vw_labor_program_metrics`

La migración es no destructiva:

- no usa `DROP` de tablas
- no usa `TRUNCATE`
- no borra datos
- usa `CREATE IF NOT EXISTS`
- usa `CREATE OR REPLACE VIEW`

### 2. Diagnóstico reproducible

Archivo:

```text
diagnose_labor_matching.py
```

Genera:

- `outputs/labor_matching_diagnosis.md`
- `outputs/labor_matching_diagnosis.json`

Incluye:

- conteos de tablas curriculares
- conteos de tablas laborales
- conteos de vistas de matching
- programas con 0 empleos
- skills curriculares sin match laboral
- causas probables

### 3. Builder de matches

Archivo:

```text
build_labor_program_matches.py
```

Proceso:

1. lee especializaciones y skills curriculares
2. lee empleos y skills laborales
3. normaliza nombres
4. calcula match exacto por `skill_id`
5. calcula match por nombre normalizado
6. aplica fuzzy matching básico
7. calcula `match_score`
8. inserta con UPSERT en `labor_program_skill_matches`

No elimina datos existentes.

### 4. Backend actualizado

Archivos:

- `backend/repositories/matches_repository.py`
- `backend/services/dashboard_service.py`

Cambio:

El backend ahora prioriza `vw_labor_program_job_matches` cuando tiene datos. Si no existe o no tiene filas, mantiene fallback hacia:

- `vw_latest_ml_program_job_matches`
- `vw_match_empleo_especializacion_positivo`

## Resultados Railway después de corrección

Datos laborales sincronizados:

- `empleos`: 119
- `empleo_skills`: 199
- `ml_training_runs`: 5
- `ml_job_documents`: 476
- `ml_program_documents`: 26
- `ml_program_job_matches`: 559

Matches construidos:

- programas evaluados: 52
- empleos evaluados: 119
- filas en `labor_program_skill_matches`: 777
- programas con matches: 41
- relaciones programa-empleo: 605

Diagnóstico posterior:

- `vw_labor_program_job_matches`: 605 filas
- programas con matches: 41
- empleos relacionados: 108
- match promedio: 52.78

## Programas aún con 0 empleos

Algunos programas siguen sin evidencia laboral directa por cobertura limitada del dataset laboral, no por error de joins:

- Administración y Gerencia de la Salud
- Derecho Digital
- Derechos Humanos
- Educación Inclusiva
- Educación y Orientación Familiar
- Gerencia Financiera
- Ingeniería de Software
- Neuropsicología y Educación
- Pedagogía y Docencia
- TIC para la Enseñanza

## Skills sin match laboral frecuente

Top detectado:

- gestión de calidad
- analítica de datos
- sostenibilidad
- talento humano
- inclusión educativa
- pedagogía
- transformación digital
- gestión educativa
- liderazgo
- derechos humanos

Esto indica que la siguiente fase debe ampliar evidencia laboral Gold por dominio, especialmente salud, legal, educación y gerencia financiera.

## Validación de programas piloto

Se validó que el motor ya produce matches agregados; sin embargo, algunos nombres piloto no aparecen por diferencias de nombres/acentos o porque la especialización cargada en Railway no coincide exactamente con la denominación esperada.

Programas objetivo:

- Especialización en Visual Analytics y Big Data
- Especialización en Inteligencia Artificial Aplicada
- Especialización en Dirección y Gestión de Tecnologías de la Información

Siguiente ajuste recomendado:

- normalizar nombres con `unaccent`
- revisar duplicados curriculares con nombres en minúscula/mojibake
- mapear aliases de programas piloto

## Comandos ejecutados

```powershell
python diagnose_labor_matching.py
python apply_railway_migrations.py database/migrations/003_enterprise_labor_intelligence_schema.sql database/migrations/005_ml_training_schema.sql database/migrations/008_labor_matching_bridge.sql --dry-run
python apply_railway_migrations.py database/migrations/003_enterprise_labor_intelligence_schema.sql database/migrations/005_ml_training_schema.sql database/migrations/008_labor_matching_bridge.sql
python sync_to_railway.py --tables empleos,empleo_skills,ml_training_runs,ml_job_documents,ml_program_documents,ml_program_job_matches --dry-run
python sync_to_railway.py --tables empleos,empleo_skills,ml_training_runs,ml_job_documents,ml_program_documents,ml_program_job_matches
python build_labor_program_matches.py --dry-run
python build_labor_program_matches.py
python diagnose_labor_matching.py
```

## Riesgos

- El dataset laboral actual es pequeño para algunos dominios.
- `gold_validated_jobs` sigue vacío.
- `canonical_jobs` y `silver_normalized_jobs` están disponibles pero sin datos útiles en Railway.
- La calidad de matches depende de la normalización de skills y la cobertura de `empleo_skills`.

## Próximos pasos

1. Poblar evidencia laboral Gold por dominio.
2. Resolver encoding/mojibake de nombres de programas.
3. Agregar aliases de especializaciones piloto.
4. Construir matches por dominio/subdominio, no solo por skill.
5. Conectar release gates Gold antes de usar métricas como KPI institucional definitivo.

