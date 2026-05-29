# Cross-Domain Curriculum Validation

## Resumen Ejecutivo

- Documentos procesados: `4`
- Dominios con evidencia: `analitica, management, ti`
- Unidades de evidencia: `analitica/inteligencia_artificial, management/finanzas, management/innovacion, ti/ingenieria_software`
- Precision aproximada: `0.9773`
- Recall aproximado: `1.0`
- Domain contamination rate: `0.0227`
- Recommendation coherence: `1.0`
- Taxonomy coverage: `1.0`
- Transversal skill separation quality: `0.5`
- Readiness piloto controlado: `medio`

## Metricas Por Dominio

### analitica

- Documentos: `1`
- Precision: `1.0`
- Recall: `1.0`
- Contaminacion: `0.0`
- Coherencia recomendaciones: `1.0`
- Separacion transversal: `0.0`

### management

- Documentos: `2`
- Precision: `1.0`
- Recall: `1.0`
- Contaminacion: `0.0`
- Coherencia recomendaciones: `1.0`
- Separacion transversal: `0.5`

### ti

- Documentos: `1`
- Precision: `0.9091`
- Recall: `1.0`
- Contaminacion: `0.0909`
- Coherencia recomendaciones: `1.0`
- Separacion transversal: `1.0`

## Resultados Por Documento

### aprendizaje automatico.docx

- Dominio esperado: `analitica`
- Subdominio esperado: `inteligencia_artificial`
- Dominio detectado: `analitica`
- Confidence: `0.88`
- Skills: ia, machine learning
- Plataformas: sin plataformas
- Falsos positivos: []
- Falsos negativos: no detectados
- Recomendaciones incoherentes: `0`

### ADE _S.5 _B. 1 _Gerencia Financiera.docx

- Dominio esperado: `management`
- Subdominio esperado: `finanzas`
- Dominio detectado: `finanzas`
- Confidence: `0.88`
- Skills: analisis de escenarios, indicadores financieros, modelacion financiera, excel avanzado
- Plataformas: excel avanzado
- Falsos positivos: []
- Falsos negativos: no detectados
- Recomendaciones incoherentes: `0`

### Diseño de proyectos orientados a la innovación.docx

- Dominio esperado: `management`
- Subdominio esperado: `innovacion`
- Dominio detectado: `management`
- Confidence: `0.84`
- Skills: innovacion, inteligencia competitiva, vigilancia tecnologica, gestion de proyectos, trabajo en equipo
- Plataformas: sin plataformas
- Falsos positivos: []
- Falsos negativos: no detectados
- Recomendaciones incoherentes: `0`

### Anexo 3.1 Microcurriculos - Esp_ing_Software.pdf

- Dominio esperado: `ti`
- Subdominio esperado: `ingenieria_software`
- Dominio detectado: `ti`
- Confidence: `0.86`
- Skills: google cloud, mariadb, sql, .net, agile, devops, scrum, java, javascript, php, android, api, backend, cloud, innovacion, modelacion financiera, android studio, eclipse, ide, netbeans, liderazgo, trabajo en equipo
- Plataformas: .net, android studio, eclipse, google cloud, ide, mariadb, netbeans, sql
- Falsos positivos: [{"skill": "innovacion", "skill_domain": "management", "detected_domain": "ti"}, {"skill": "modelacion financiera", "skill_domain": "finanzas", "detected_domain": "ti"}]
- Falsos negativos: no detectados
- Recomendaciones incoherentes: `0`

## Criterio De Piloto

- `alto`: minimo 12 documentos, 3+ dominios principales, sin dominios bajos y coherencia >= 0.85.
- `medio`: minimo 3 documentos, 3+ unidades dominio/subdominio y sin dominios de bajo desempeno.
- `bajo`: evidencia suficiente pero uno o mas dominios requieren hardening.
- `blocked_no_cross_domain_evidence`: no hay evidencia multi-dominio real.