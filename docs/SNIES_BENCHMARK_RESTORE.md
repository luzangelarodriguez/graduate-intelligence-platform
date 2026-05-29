# Restauracion Benchmark SNIES

## Objetivo

Eliminar placeholders visuales del observatorio y restaurar un benchmarking competitivo visible para la Especializacion en Visual Analytics y Big Data.

La pantalla debe comunicar:

- UNIR comparada frente a instituciones similares.
- Ranking competitivo universitario virtual.
- Diferencia frente al promedio competidor.
- Pertinencia curricular como indicador principal.

## Placeholders eliminados

Se eliminaron de la primera vista los tres bloques superiores que no aportaban accion ejecutiva:

- Estado curricular
- Recomendacion academica
- Alineacion actual

El dashboard ahora inicia con:

1. Header institucional.
2. Hero con programa activo.
3. Indice de pertinencia curricular.
4. KPIs ejecutivos interactivos.
5. Benchmarking curricular SNIES.

Tambien se elimino el uso visual de:

- "Pendiente"
- "Sin evidencia"
- "No se identifico evidencia suficiente"

Cuando un dato aun no proviene de Gold laboral, la interfaz usa:

**Senal exploratoria**

## Benchmark temporal

Mientras se conecta el endpoint SNIES definitivo o se estabiliza la consulta para todos los programas, el frontend usa un dataset temporal ubicado en:

`graduate_intelligence_platform/frontend/src/data/snies_benchmark_mock.ts`

Este dataset permite que el observatorio no se vea vacio y mantenga una narrativa ejecutiva realista para demo institucional.

## Estructura del mock

Cada registro contiene:

- `universidad`
- `programa`
- `ciudad`
- `modalidad`
- `score`
- `posicionCompetitiva`

Instituciones incluidas:

- UNIR Colombia
- Areandina
- UNAD
- Catolica del Norte
- Asturias
- CUN
- UNAC

Programas comparables:

- Visual Analytics y Big Data
- Analitica de Datos
- Big Data
- Inteligencia de Negocios
- Ciencia de Datos
- Analitica Empresarial

## Visualizacion implementada

La seccion **Benchmarking curricular SNIES** muestra:

- posicion competitiva
- promedio competidores
- diferencia competitiva
- ranking lateral
- barras comparativas
- cards con universidad, programa, ciudad, modalidad y score

## Conexion futura SNIES/API

El componente ya intenta consumir:

`GET /api/programs/related-universities/{program_id}`

Regla actual:

- Si el API devuelve resultados, se usan como benchmark.
- Si el API no devuelve resultados, se usa el mock temporal.

Esto evita placeholders sin bloquear la demo institucional.

## Validacion funcional

Validar en:

`http://127.0.0.1:5173/`

Flujo:

1. Seleccionar `Especializacion en Visual Analytics y Big Data`.
2. Ejecutar `Analizar microcurriculos`.
3. Confirmar que no aparecen las tres cards superiores eliminadas.
4. Confirmar que aparece el ranking SNIES con UNIR, Areandina, UNAD, Catolica del Norte, Asturias, CUN y UNAC.
5. Confirmar que no aparece "Pendiente", "Sin evidencia" ni "No se identifico evidencia suficiente" en el bloque principal.

## Validacion tecnica

Comandos requeridos:

- `npm run build`
- `python -m pytest tests`

## Riesgos

- El benchmark temporal es apto para demo y narrativa de producto, pero debe reemplazarse por datos SNIES reales gobernados antes de produccion.
- Los scores competitivos del mock son referenciales y deben calibrarse con datos institucionales y criterios academicos formales.
