# Railway Data Sync

Este proceso carga datos curriculares desde PostgreSQL local hacia PostgreSQL Railway sin eliminar datos remotos.

## Objetivo

Poblar las tablas que alimentan `/api/programas` y el observatorio curricular:

- `especializaciones`
- `skills`
- `herramientas`
- `competencias`
- `habilidades_blandas`
- `perfiles_egreso`
- `especializacion_skills`
- `especializacion_herramientas`
- `especializacion_competencias`
- `especializacion_habilidades_blandas`

El script usa `UPSERT`, preserva IDs originales y ejecuta la carga en una transacción. Si algo falla, hace rollback en Railway.

## Configuración local

1. Copiar `.env.example` a `.env.local`.
2. Configurar origen local:

```powershell
LOCAL_DB_HOST=127.0.0.1
LOCAL_DB_PORT=5433
LOCAL_DB_NAME=cliente_a_db
LOCAL_DB_USER=postgres
LOCAL_DB_PASSWORD=postgres
```

3. Configurar destino Railway:

```powershell
RAILWAY_DATABASE_URL=postgresql://user:password@host:5432/db
RAILWAY_DB_SSLMODE=require
```

También puede usarse `DATABASE_URL` o variables `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
En ejecución local se recomienda usar `RAILWAY_DATABASE_URL` o variables `RAILWAY_DB_*`.
El fallback a `DB_*` está bloqueado por seguridad salvo que `ALLOW_DB_ENV_TARGET=true`, pensado para ejecución dentro de Railway.

## Validación sin carga

```powershell
python sync_to_railway.py --dry-run
```

## Ejecutar sincronización

```powershell
python sync_to_railway.py
```

Para ajustar tamaño de lote:

```powershell
python sync_to_railway.py --batch-size 500
```

Para migrar tablas específicas:

```powershell
python sync_to_railway.py --tables especializaciones,skills,especializacion_skills
```

## Verificar Railway

```powershell
python verify_railway_data.py
```

Con validación del backend desplegado:

```powershell
python verify_railway_data.py --api-base-url https://your-backend.up.railway.app
```

La verificación revisa:

- conexión a Railway
- conteo de registros por tabla
- tablas vacías
- consistencia referencial básica
- respuesta opcional de `GET /api/programas`

Si una tabla existe en Railway pero no existe en PostgreSQL local, `sync_to_railway.py` la registra como `skipped_missing_source` y continúa con las demás tablas. Las tablas faltantes en Railway sí detienen el proceso porque indican migraciones de estructura incompletas.

## Logs

Los scripts generan logs en:

```text
logs/sync_to_railway_YYYYMMDD_HHMMSS.log
logs/verify_railway_data_YYYYMMDD_HHMMSS.log
logs/verify_railway_data_YYYYMMDD_HHMMSS.json
```

## Seguridad

- No elimina datos en Railway.
- No usa `TRUNCATE`.
- No hace `DROP`.
- No toca producción si no se configuran variables Railway.
- Bloquea por defecto si origen y destino parecen ser la misma base.

## Resultado esperado

Después de ejecutar:

```powershell
python sync_to_railway.py
python verify_railway_data.py --api-base-url https://your-backend.up.railway.app
```

`GET /api/programas` debe devolver programas reales en lugar de una lista vacía.
