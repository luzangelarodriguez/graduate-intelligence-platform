# Labor Engine Validation Phase 1

Fecha ejecucion: 2026-05-19T10:13:07

## Alcance

Validacion controlada por dominios del motor laboral enterprise. No se modifico frontend, no se eliminaron datos y la corrida se realizo con limites bajos por dominio.

## Resumen ejecutivo

| Dominio | Empleos normalizados | Duplicados | Precision observada | Score disciplinar promedio | Dominios asignados |
|---|---:|---:|---:|---:|---|
| ambiental_energia | 11 | 6 | 63.64% | 0.744 | {'gestion_humana': 1, 'energia': 4, 'ambiental': 3, 'management': 3} |
| datos_analitica | 1 | 0 | 0.0% | 0.778 | {'gestion_humana': 1} |
| ciberseguridad | 1 | 0 | 0.0% | 0.778 | {'gestion_humana': 1} |
| gestion_humana | 1 | 0 | 100.0% | 0.778 | {'gestion_humana': 1} |
| derecho_digital | 14 | 3 | 28.57% | 0.917 | {'gestion_humana': 1, 'legal-tech': 3, 'legal': 1, 'cybersecurity': 9} |
| educacion | 16 | 1 | 37.5% | 0.644 | {'gestion_humana': 2, 'management': 6, 'educacion': 6, 'ti': 2} |

## Resultados por dominio

### ambiental_energia

Query: `sostenibilidad ESG eficiencia energetica huella de carbono ISO 14001 energias renovables`

- Empleos extraidos raw: 17
- Empleos normalizados: 11
- Duplicados removidos: 6
- Precision observada: 63.64%
- Score disciplinar promedio: 0.744
- Dominios asignados: `{'gestion_humana': 1, 'energia': 4, 'ambiental': 3, 'management': 3}`
- Fuentes con resultados: `{'servicio_publico_empleo': 1, 'elempleo': 10}`

Skills aceptadas principales:

- eficiencia energetica: 1
- sostenibilidad: 1
- esg: 1
- transicion energetica: 1

Skills rechazadas principales:

- Sin skills rechazadas detectadas.

Contaminaciones detectadas:

- Inicio (servicio_publico_empleo): dominio `gestion_humana`
- Technical writer senior (gobernanza ti & normas iso) - bilingüe / analista de procesos y calidad ti (elempleo): dominio `management`
- ¿listo(a) para dejar huella y no solo cumplir metas? (md) (elempleo): dominio `management`
- ¿listo(a) para dejar huella y no solo cumplir metas? (bg) (elempleo): dominio `management`

Muestra de empleos:

- Inicio | servicio_publico_empleo | gestion_humana | 
- Ingeniero comercial de eficiencia energética | elempleo | energia | eficiencia energetica
- Director técnico energía | elempleo | energia | 
- Analista calidad - iso 9001 2015, 14001,45001 | elempleo | ambiental | 
- Analista de sostenibilidad y ambiente- bogotà | elempleo | ambiental | sostenibilidad

### datos_analitica

Query: `analista de datos power bi sql python big data visual analytics`

- Empleos extraidos raw: 1
- Empleos normalizados: 1
- Duplicados removidos: 0
- Precision observada: 0.0%
- Score disciplinar promedio: 0.778
- Dominios asignados: `{'gestion_humana': 1}`
- Fuentes con resultados: `{'servicio_publico_empleo': 1}`

Skills aceptadas principales:

- Sin skills aceptadas detectadas.

Skills rechazadas principales:

- Sin skills rechazadas detectadas.

Contaminaciones detectadas:

- Inicio (servicio_publico_empleo): dominio `gestion_humana`

Muestra de empleos:

- Inicio | servicio_publico_empleo | gestion_humana | 

### ciberseguridad

Query: `seguridad informatica ciberseguridad SOC ISO 27001 ethical hacking`

- Empleos extraidos raw: 1
- Empleos normalizados: 1
- Duplicados removidos: 0
- Precision observada: 0.0%
- Score disciplinar promedio: 0.778
- Dominios asignados: `{'gestion_humana': 1}`
- Fuentes con resultados: `{'servicio_publico_empleo': 1}`

Skills aceptadas principales:

- Sin skills aceptadas detectadas.

Skills rechazadas principales:

- Sin skills rechazadas detectadas.

Contaminaciones detectadas:

- Inicio (servicio_publico_empleo): dominio `gestion_humana`

Muestra de empleos:

- Inicio | servicio_publico_empleo | gestion_humana | 

### gestion_humana

Query: `recursos humanos talento humano compensacion seleccion bienestar organizacional`

- Empleos extraidos raw: 1
- Empleos normalizados: 1
- Duplicados removidos: 0
- Precision observada: 100.0%
- Score disciplinar promedio: 0.778
- Dominios asignados: `{'gestion_humana': 1}`
- Fuentes con resultados: `{'servicio_publico_empleo': 1}`

Skills aceptadas principales:

- Sin skills aceptadas detectadas.

Skills rechazadas principales:

- Sin skills rechazadas detectadas.

Contaminaciones detectadas:

- No se detectaron contaminaciones disciplinarias en la muestra normalizada.

Muestra de empleos:

- Inicio | servicio_publico_empleo | gestion_humana | 

### derecho_digital

Query: `derecho digital proteccion de datos habeas data compliance legaltech`

- Empleos extraidos raw: 17
- Empleos normalizados: 14
- Duplicados removidos: 3
- Precision observada: 28.57%
- Score disciplinar promedio: 0.917
- Dominios asignados: `{'gestion_humana': 1, 'legal-tech': 3, 'legal': 1, 'cybersecurity': 9}`
- Fuentes con resultados: `{'servicio_publico_empleo': 1, 'elempleo': 13}`

Skills aceptadas principales:

- derecho digital: 2
- proteccion de datos: 2
- compliance: 1

Skills rechazadas principales:

- Sin skills rechazadas detectadas.

Contaminaciones detectadas:

- Inicio (servicio_publico_empleo): dominio `gestion_humana`
- Analista de ciberseguridad (elempleo): dominio `cybersecurity`
- Administrador de ciberseguridad / microsoft defender (elempleo): dominio `cybersecurity`
- Analista de seguridad informatica (elempleo): dominio `cybersecurity`
- Administrador de ciberseguridad / vulnerabilidad (elempleo): dominio `cybersecurity`
- Analista de ciberseguridad (elempleo): dominio `cybersecurity`
- Jefe de ciberseguridad ti (elempleo): dominio `cybersecurity`
- Analista de seguridad de la información y ciberseguridad (elempleo): dominio `cybersecurity`
- Analista de ciberseguridad (elempleo): dominio `cybersecurity`
- Director de seguridad informatica (elempleo): dominio `cybersecurity`

Muestra de empleos:

- Inicio | servicio_publico_empleo | gestion_humana | 
- Analista de protección de datos y derecho digital bilingüe | elempleo | legal-tech | derecho digital, proteccion de datos
- Profesional de habeas data (abogado) | elempleo | legal-tech | proteccion de datos
- Docente hora cátedra derecho digital, legaltech o transformación digital | elempleo | legal-tech | derecho digital
- Abogado compliance | elempleo | legal | compliance

### educacion

Query: `educacion inclusiva orientacion familiar pedagogia TIC educativas`

- Empleos extraidos raw: 17
- Empleos normalizados: 16
- Duplicados removidos: 1
- Precision observada: 37.5%
- Score disciplinar promedio: 0.644
- Dominios asignados: `{'gestion_humana': 2, 'management': 6, 'educacion': 6, 'ti': 2}`
- Fuentes con resultados: `{'servicio_publico_empleo': 1, 'elempleo': 15}`

Skills aceptadas principales:

- diseno curricular: 1

Skills rechazadas principales:

- Sin skills rechazadas detectadas.

Contaminaciones detectadas:

- Inicio (servicio_publico_empleo): dominio `gestion_humana`
- Líder de modalidades educativas con el uso de tic (elempleo): dominio `management`
- Psicologa educativa (elempleo): dominio `management`
- Lider de formación y desarrollo / profesional de formación, bienestar y desarrollo (elempleo): dominio `gestion_humana`
- Director de formacion en seguros (elempleo): dominio `management`
- Auxiliar de entrenamiento / formación / capacitación comercial (elempleo): dominio `management`
- Analista de formación y desarrollo (elempleo): dominio `ti`
- Analista de formación (elempleo): dominio `management`
- Profesional en desarrollo y formación de personal (elempleo): dominio `ti`
- Director de formacion comercial (elempleo): dominio `management`

Muestra de empleos:

- Inicio | servicio_publico_empleo | gestion_humana | 
- Líder de modalidades educativas con el uso de tic | elempleo | management | 
- Psicologa educativa | elempleo | management | 
- Lider de formación y desarrollo / profesional de formación, bienestar y desarrollo | elempleo | gestion_humana | 
- Enfermera con formación en pedagogía infantil - cali | elempleo | educacion | 

## Fuentes que fallaron o quedaron sin evidencia

La tabla siguiente resume errores capturados por el runner. Cuando una fuente no entrega resultados puede deberse a selectores, carga JS, bloqueo, cambios de portal o ausencia de resultados para la query.

- SPE: devolvio una pagina institucional `Inicio` como si fuera vacante en la corrida inicial. Se endurecio el filtro posterior para descartar paginas no laborales y se ajustaron selectores hacia rutas de detalle. Verificacion posterior con SPE produjo `0` empleos y ya no acepto `Inicio` como vacante.
- Computrabajo: no entrego resultados con los selectores actuales durante esta corrida. Requiere inspeccion de DOM live o endpoint XHR antes de escalar volumen.
- El Empleo: fue la unica fuente con evidencia laboral util en ambiental/energia, derecho digital y educacion, pero presento timeouts `networkidle` en datos/analitica, ciberseguridad y gestion humana. Requiere estrategia de espera menos estricta o extraccion por XHR.
- Magneto y Torre no se incluyeron en esta matriz porque la solicitud priorizo SPE, Computrabajo y El Empleo.

## Endpoints XHR/API internas

No se identificaron endpoints XHR/API internas en esta corrida porque el objetivo fue validar Playwright end-to-end con limites bajos. La recomendacion es activar tracing por fuente y priorizar API directa en este orden:

1. El Empleo: mayor evidencia util, pero con timeouts de carga.
2. Computrabajo: selector actual no encuentra cards; posible renderizado/client API.
3. SPE: el portal institucional requiere identificar ruta real de consulta o servicio backend para evitar enlaces de navegacion.

## Ajustes aplicados tras la corrida

- Se agrego filtro `looks_like_non_job_page` para no aceptar paginas institucionales como vacantes.
- Se restringieron selectores SPE para evitar rutas como `registro-de-vacantes`.
- Se valido `py_compile` de los cambios.
- Se ejecuto chequeo SPE posterior con salida `outputs/labor_engine_validation_phase_1/spe_after_filter_check.csv`; resultado: `0` empleos aceptados y sin falso positivo `Inicio`.

## Recomendaciones de ajuste taxonomico

- Ampliar `skills_master` para gestion humana: compensacion, seleccion, bienestar, cultura organizacional y people analytics.
- Ampliar educacion: educacion inclusiva, orientacion familiar, TIC educativas, diseno universal de aprendizaje y neuroeducacion.
- Separar con mas fuerza `legal-tech` de `cybersecurity`: proteccion de datos puede convivir con seguridad, pero no debe convertir todo derecho digital en TI.
- Para datos/analitica, distinguir herramientas (`Power BI`, `SQL`, `Python`) de capacidades (`gobierno de datos`, `visual analytics`, `modelado`).
- Mantener reglas de exclusion ambiental/energia vs TI/cybersecurity, porque son criticas para pertinencia curricular.

## Proximos ajustes

1. Ejecutar corrida por fuente individual para ajustar selectores live.
2. Revisar screenshots en `logs/screenshots` cuando una fuente no entregue cards.
3. Identificar endpoints XHR/API de cada portal con Playwright tracing antes de aumentar volumen.
4. Crear pruebas unitarias de contaminacion disciplinar por dominio.
5. Solo conectar el dashboard cuando precision por dominio sea estable y trazable.
