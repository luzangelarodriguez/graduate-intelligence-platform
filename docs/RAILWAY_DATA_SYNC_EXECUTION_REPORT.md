# Railway Data Sync Execution Report

Fecha de preparación: 2026-05-24

## Alcance

Se preparó la ejecución segura para poblar PostgreSQL Railway desde PostgreSQL local sin borrar datos remotos.

Backend productivo:

```text
https://graduate-intelligence-platform-production.up.railway.app
```

Tablas objetivo iniciales:

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

## Seguridad

- No usa `DROP`.
- No usa `TRUNCATE`.
- No elimina datos en Railway.
- Usa `UPSERT`.
- Preserva IDs.
- Ejecuta transacción y rollback automático ante error.
- No registra passwords reales en logs.
- `.env`, `.env.*` quedan ignorados en Git; solo se versionan ejemplos sin secretos.

## Estado de ejecución

Dry-run ejecutado el 2026-05-24.

Resultado:

```text
Bloqueado por seguridad: el entorno local no tiene RAILWAY_DATABASE_URL,
DATABASE_URL ni RAILWAY_DB_* configurado. La configuración DB_* disponible
proviene del entorno local/desarrollo y no debe usarse como destino Railway.
```

No se insertó ningún dato en Railway.

Conteo confirmado en PostgreSQL local:

| Tabla | Registros locales |
|---|---:|
| especializaciones | 26 |
| skills | 10 |
| especializacion_skills | 154 |
| herramientas | 10 |
| competencias | 15 |
| habilidades_blandas | 12 |
| perfiles_egreso | No existe en local |

Validación API productiva sin token:

```text
GET https://graduate-intelligence-platform-production.up.railway.app/api/programas?limit=25&offset=0
HTTP 401 Unauthorized
{"detail":"missing bearer token"}
```

Conclusión: el endpoint está protegido correctamente. Para validar `items` y `count` se requiere un Bearer token válido generado por `/auth/login`.

Comandos:

```powershell
python -m py_compile sync_to_railway.py verify_railway_data.py
python sync_to_railway.py --dry-run
python sync_to_railway.py
python verify_railway_data.py --api-base-url https://graduate-intelligence-platform-production.up.railway.app
```

## Resultado esperado

Después de la sincronización:

- `especializaciones` debe tener registros en Railway.
- `skills` debe tener registros en Railway.
- `especializacion_skills` debe tener relaciones en Railway.
- `GET /api/programas?limit=25&offset=0` debe devolver `count > 0`.

## Registro de resultados

Completar tras ejecución:

| Tabla | Antes Railway | Local | Upsert | Después Railway | Estado |
|---|---:|---:|---:|---:|---|
| especializaciones | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |
| skills | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |
| herramientas | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |
| competencias | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |
| habilidades_blandas | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |
| perfiles_egreso | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |
| especializacion_skills | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |
| especializacion_herramientas | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |
| especializacion_competencias | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |
| especializacion_habilidades_blandas | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |

## Próximos pasos

1. Configurar `RAILWAY_DATABASE_URL` en `.env.local` local.
2. Ejecutar dry-run.
3. Ejecutar sincronización real si dry-run pasa.
4. Verificar `/api/programas`.
5. Si la API requiere token Bearer, generar token con `/auth/login` y validar con cliente HTTP autenticado.
