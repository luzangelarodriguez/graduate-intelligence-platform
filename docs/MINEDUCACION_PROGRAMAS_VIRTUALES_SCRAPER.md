# Scraper HECAA - Programas virtuales activos

Pipeline productivo para consolidar en PostgreSQL el catálogo nacional de programas académicos activos y virtuales desde:

<https://hecaa.mineducacion.gov.co/consultaspublicas/programas>

## Qué extrae

- Institución, código IES e IES padre.
- Registro único y código SNIES del programa.
- Nombre, estado, nivel académico, modalidad y reconocimiento del Ministerio.
- Municipio, departamento, metodología, área de conocimiento, núcleo básico, créditos, duración, periodicidad y vigencias cuando estén disponibles en detalle.
- URL de detalle, timestamp, fuente y HTML raw opcional.

## Instalación

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

Configurar `.env` con las variables PostgreSQL:

```env
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=cliente_a_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_SSLMODE=prefer
```

Existe una plantilla en `config/mineducacion.env.example`.

## Base de datos

```powershell
psql -h 127.0.0.1 -p 5433 -U postgres -d cliente_a_db -f database/mineducacion_programas_virtuales.sql
```

La tabla oficial es `public.mineducacion_programas_virtuales`.

La clave única es `codigo_snies_programa`, y la carga usa `ON CONFLICT DO UPDATE` para evitar duplicados.

## Ejecución

Prueba corta sin escribir en base de datos:

```powershell
python scrapers/mineducacion_programas_virtuales_scraper.py --headed --max-pages 1 --limit-records 20 --skip-db
```

Ejecución productiva:

```powershell
python scrapers/mineducacion_programas_virtuales_scraper.py
```

Guardar HTML raw de detalles:

```powershell
python scrapers/mineducacion_programas_virtuales_scraper.py --include-html
```

## Outputs

- CSV: `outputs/mineducacion_programas_virtuales_YYYYMMDD_HHMMSS.csv`
- Logs: `logs/mineducacion_scraper_YYYYMMDD_HHMMSS.log`
- Screenshots de error: `logs/screenshots/`
- Candidatos XHR/API detectados: `outputs/mineducacion_xhr_candidates_YYYYMMDD.json`

## Paginación

El scraper detecta controles comunes de paginación:

- Botones o enlaces `Siguiente`.
- DataTables `paginate_button next`.
- Controles `>`, `»` y `aria-label`.

En cada página valida que los registros sean `Activo` y `Virtual` antes de exportar o cargar.

## Estrategia API/XHR

Durante la navegación Playwright captura respuestas JSON/CSV/Excel provenientes de dominios HECAA/Mineducación. Si el portal expone un endpoint interno estable, queda registrado en `outputs/mineducacion_xhr_candidates_*.json` para promoverlo como extractor directo más rápido.

La implementación actual prioriza robustez:

1. Aplica filtros en la UI oficial.
2. Escucha endpoints internos.
3. Extrae tabla de resultados.
4. Abre detalle si hay URL disponible.
5. Exporta CSV.
6. Ejecuta UPSERT PostgreSQL.

## Riesgos operativos

- El portal puede cambiar selectores, textos o controles de paginación.
- Algunos campos ampliados dependen de que la página exponga detalle navegable.
- Si HECAA sirve resultados con lazy loading, se debe mantener `networkidle` y timeouts altos.
- Si el portal bloquea automatización, ejecutar temporalmente con `--headed --slow-mo-ms 200`.
