# Source Governance Dashboard

Dashboard tecnico interno para confiabilidad de fuentes laborales.

| Fuente | Tier | Reliability | Freshness | Contaminacion | Blocked auth | Evidencia | Completitud | Acceso | Gold readiness |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| magneto_api | Bronze | 0.63 | 1.00 | 0.87 | 0.00 | 0.13 | 0.03 | scraping | False |
| servicio_publico_empleo | Bronze | 0.51 | 0.00 | 0.00 | 0.00 | 0.10 | 0.00 | scraping | False |
| computrabajo | Experimental | 0.36 | 0.00 | 0.00 | 0.00 | 0.10 | 0.00 | scraping | False |
| magneto | Experimental | 0.36 | 0.00 | 0.00 | 0.00 | 0.10 | 0.00 | scraping | False |
| spe | Experimental | 0.36 | 0.00 | 0.00 | 0.00 | 0.10 | 0.00 | scraping | False |
| elempleo | Experimental | 0.15 | 1.00 | 0.00 | 1.00 | 0.10 | 0.00 | partnership | False |

## Recomendaciones

- `computrabajo`: programar nueva corrida o revisar scheduler.
- `elempleo`: resolver acceso autorizado antes de promocionar fuente.
- `magneto`: programar nueva corrida o revisar scheduler.
- `magneto_api`: ajustar normalizacion y filtros anti-contaminacion.
- `servicio_publico_empleo`: programar nueva corrida o revisar scheduler.
- `spe`: programar nueva corrida o revisar scheduler.
