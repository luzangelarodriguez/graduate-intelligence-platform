# Functional AI Validation - Microcurriculum Engine

## Resumen Ejecutivo

- PDFs procesados: `6`
- Documentos unicos por hash: `1`
- Precision aproximada: `1.0`
- Recall aproximado: `0.6667`
- Domain contamination rate: `0.0`
- Recommendation coherence score: `1.0`
- Taxonomy coverage: `0.9524`
- Contextual understanding score: `0.9238`
- Readiness piloto universitario: `medio`

## Lectura Principal

- El sistema clasifica correctamente el caso de Ingenieria de Software como TI cuando el texto lo evidencia.
- La extraccion real de texto PDF funciona con `pdfplumber`.
- El motor todavia depende demasiado de taxonomia explicita: si una tecnologia no esta registrada, aparece como gap de recall.
- La calidad de recomendaciones es util para exploracion, pero requiere evidencia Gold laboral mas fuerte para produccion.

## Resultados Por PDF

### 20260520_183751_2d37515dd9551380_Anexo 3.1 Microcurriculos - Esp_ing_Software.pdf

- Dominio detectado: `ti`
- Dominio esperado: `ti`
- Confidence: `0.86` (high)
- Paginas: `21`
- Texto extraido: `47715` caracteres
- Skills detectadas: google cloud, mariadb, sql, .net, agile, devops, scrum, java, javascript, php, android, api, backend, cloud, android studio, eclipse, ide, netbeans, liderazgo, trabajo en equipo
- Plataformas detectadas: .net
- Skills faltantes importantes: innovacion
- Falsos positivos: no detectados
- Gaps: docker, python, react, rest api
- Riesgo contaminacion: `0.0`
- Calidad insight ejecutivo: `0.9238`

### 20260520_183929_2d37515dd9551380_20260520_183751_2d37515dd9551380_Anexo 3.1 Microcurriculos - Esp_ing_Software.pdf

- Dominio detectado: `ti`
- Dominio esperado: `ti`
- Confidence: `0.86` (high)
- Paginas: `21`
- Texto extraido: `47715` caracteres
- Skills detectadas: google cloud, mariadb, sql, .net, agile, devops, scrum, java, javascript, php, android, api, backend, cloud, android studio, eclipse, ide, netbeans, liderazgo, trabajo en equipo
- Plataformas detectadas: .net
- Skills faltantes importantes: innovacion
- Falsos positivos: no detectados
- Gaps: docker, python, react, rest api
- Riesgo contaminacion: `0.0`
- Calidad insight ejecutivo: `0.9238`

### 20260520_184116_2d37515dd9551380_20260520_183751_2d37515dd9551380_Anexo 3.1 Microcurriculos - Esp_ing_Software.pdf

- Dominio detectado: `ti`
- Dominio esperado: `ti`
- Confidence: `0.86` (high)
- Paginas: `21`
- Texto extraido: `47715` caracteres
- Skills detectadas: google cloud, mariadb, sql, .net, agile, devops, scrum, java, javascript, php, android, api, backend, cloud, android studio, eclipse, ide, netbeans, liderazgo, trabajo en equipo
- Plataformas detectadas: .net
- Skills faltantes importantes: innovacion
- Falsos positivos: no detectados
- Gaps: docker, python, react, rest api
- Riesgo contaminacion: `0.0`
- Calidad insight ejecutivo: `0.9238`

### 20260520_184335_2d37515dd9551380_Anexo 3.1 Microcurriculos - Esp_ing_Software.pdf

- Dominio detectado: `ti`
- Dominio esperado: `ti`
- Confidence: `0.86` (high)
- Paginas: `21`
- Texto extraido: `47715` caracteres
- Skills detectadas: google cloud, mariadb, sql, .net, agile, devops, scrum, java, javascript, php, android, api, backend, cloud, android studio, eclipse, ide, netbeans, liderazgo, trabajo en equipo
- Plataformas detectadas: .net
- Skills faltantes importantes: innovacion
- Falsos positivos: no detectados
- Gaps: docker, python, react, rest api
- Riesgo contaminacion: `0.0`
- Calidad insight ejecutivo: `0.9238`

### 20260520_184649_2d37515dd9551380_Anexo 3.1 Microcurriculos - Esp_ing_Software.pdf

- Dominio detectado: `ti`
- Dominio esperado: `ti`
- Confidence: `0.86` (high)
- Paginas: `21`
- Texto extraido: `47715` caracteres
- Skills detectadas: google cloud, mariadb, sql, .net, agile, devops, scrum, java, javascript, php, android, api, backend, cloud, android studio, eclipse, ide, netbeans, liderazgo, trabajo en equipo
- Plataformas detectadas: .net
- Skills faltantes importantes: innovacion
- Falsos positivos: no detectados
- Gaps: docker, python, react, rest api
- Riesgo contaminacion: `0.0`
- Calidad insight ejecutivo: `0.9238`

### Anexo 3.1 Microcurriculos - Esp_ing_Software.pdf

- Dominio detectado: `ti`
- Dominio esperado: `ti`
- Confidence: `0.86` (high)
- Paginas: `21`
- Texto extraido: `47715` caracteres
- Skills detectadas: google cloud, mariadb, sql, .net, agile, devops, scrum, java, javascript, php, android, api, backend, cloud, android studio, eclipse, ide, netbeans, liderazgo, trabajo en equipo
- Plataformas detectadas: .net
- Skills faltantes importantes: innovacion
- Falsos positivos: no detectados
- Gaps: docker, python, react, rest api
- Riesgo contaminacion: `0.0`
- Calidad insight ejecutivo: `0.9238`

## Fallas Detectadas

- Underclassification: `0` documentos.
- Overclassification: `0` documentos.
- Taxonomias/aliases faltantes: innovacion

## Prioridades De Hardening IA

1. Ampliar taxonomia TI con cloud, frontend, API, CI/CD, Java, .NET, PHP, MariaDB, Android Studio, Eclipse, NetBeans y Google Cloud.
2. Separar extraccion por columnas/tablas PDF para recuperar competencias y resultados de aprendizaje con mayor precision.
3. Calibrar confidence con gold set anotado por dominio y programa.
4. Marcar recomendaciones basadas en fallback como exploratorias cuando no haya evidencia laboral Gold.
5. Agregar evaluacion manual de falsos positivos por disciplina antes de piloto institucional.