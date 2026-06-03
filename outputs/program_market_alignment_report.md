# Program Market Alignment Report

## Methodology
- Matching explicable basado en skills.
- Vectores multi-hot por programa y por empleo.
- Similitud calculada con Jaccard y Cosine.
- Vecinos cercanos calculados con `scikit-learn NearestNeighbors`.

## Formulas
- Coverage = shared_skills / program_skills.
- Gap = 1 - coverage.
- Jaccard = shared_skills / union_skills.
- Cosine = shared_skills / sqrt(program_skills * job_skills).
- Match score = average(Jaccard, Cosine).

## Summary
- Programs analyzed: 27
- Jobs analyzed: 119
- Average program alignment: 8.04
- Average specialization alignment: 8.04
- Matched jobs total: 342

## Top Programs

### Especialización en Alta Gerencia
- Level: Especialización
- Faculty: n/a
- Market alignment score: 13.68
- Coverage score: 5.0
- Gap score: 95.0
- Matched jobs: 1
- Missing skills: none
- Top jobs: ingeniero en seguridad

### Especialización en Administración y Gerencia de la Salud
- Level: Especialización
- Faculty: n/a
- Market alignment score: 13.29
- Coverage score: 4.76
- Gap score: 95.24
- Matched jobs: 1
- Missing skills: none
- Top jobs: ingeniero en seguridad

### Especialización en Derecho de la Empresa
- Level: Especialización
- Faculty: n/a
- Market alignment score: 13.29
- Coverage score: 4.76
- Gap score: 95.24
- Matched jobs: 1
- Missing skills: none
- Top jobs: ingeniero en seguridad

### Especialización en Gestión Humana
- Level: Especialización
- Faculty: n/a
- Market alignment score: 12.93
- Coverage score: 4.55
- Gap score: 95.45
- Matched jobs: 1
- Missing skills: none
- Top jobs: ingeniero en seguridad

### Especialización en Seguridad Informática
- Level: Especialización
- Faculty: n/a
- Market alignment score: 12.44
- Coverage score: 6.56
- Gap score: 93.44
- Matched jobs: 26
- Missing skills: none
- Top jobs: Data Protection Officer, Compliance Officer, Lider SOC, Desarrollador Full Stack, Ingeniero Residente de Redes y Ciberseguridad

### Especialización en Gerencia Financiera
- Level: Especialización
- Faculty: n/a
- Market alignment score: 12.29
- Coverage score: 4.17
- Gap score: 95.83
- Matched jobs: 1
- Missing skills: none
- Top jobs: ingeniero en seguridad

### Especialización en Revisoría Fiscal y Auditoría de Cuentas
- Level: Especialización
- Faculty: n/a
- Market alignment score: 12.07
- Coverage score: 7.14
- Gap score: 92.86
- Matched jobs: 17
- Missing skills: none
- Top jobs: Técnico de Soporte, Ingeniero de Integración y Desarrollo, Gestor de Activos TI, Compliance and Risk Lead, Data Protection Officer

### Especialización en Dirección Comercial y Ventas
- Level: Especialización
- Faculty: n/a
- Market alignment score: 12.0
- Coverage score: 4.0
- Gap score: 96.0
- Matched jobs: 1
- Missing skills: none
- Top jobs: ingeniero en seguridad

### Especialización en Marketing Digital
- Level: Especialización
- Faculty: n/a
- Market alignment score: 12.0
- Coverage score: 4.0
- Gap score: 96.0
- Matched jobs: 1
- Missing skills: none
- Top jobs: ingeniero en seguridad

### Especialización en Educación y Orientación Familiar
- Level: Especialización
- Faculty: n/a
- Market alignment score: 11.98
- Coverage score: 5.0
- Gap score: 95.0
- Matched jobs: 20
- Missing skills: none
- Top jobs: analista de datos, ingeniero en seguridad, analista de datos, analista de datos, auditor en sst

## Top Specializations

### Especialización en Alta Gerencia
- Market alignment score: 13.68
- Coverage score: 5.0
- Gap score: 95.0
- Matched jobs: 1

### Especialización en Administración y Gerencia de la Salud
- Market alignment score: 13.29
- Coverage score: 4.76
- Gap score: 95.24
- Matched jobs: 1

### Especialización en Derecho de la Empresa
- Market alignment score: 13.29
- Coverage score: 4.76
- Gap score: 95.24
- Matched jobs: 1

### Especialización en Gestión Humana
- Market alignment score: 12.93
- Coverage score: 4.55
- Gap score: 95.45
- Matched jobs: 1

### Especialización en Seguridad Informática
- Market alignment score: 12.44
- Coverage score: 6.56
- Gap score: 93.44
- Matched jobs: 26

### Especialización en Gerencia Financiera
- Market alignment score: 12.29
- Coverage score: 4.17
- Gap score: 95.83
- Matched jobs: 1

### Especialización en Revisoría Fiscal y Auditoría de Cuentas
- Market alignment score: 12.07
- Coverage score: 7.14
- Gap score: 92.86
- Matched jobs: 17

### Especialización en Dirección Comercial y Ventas
- Market alignment score: 12.0
- Coverage score: 4.0
- Gap score: 96.0
- Matched jobs: 1

### Especialización en Marketing Digital
- Market alignment score: 12.0
- Coverage score: 4.0
- Gap score: 96.0
- Matched jobs: 1

### Especialización en Educación y Orientación Familiar
- Market alignment score: 11.98
- Coverage score: 5.0
- Gap score: 95.0
- Matched jobs: 20

## Top Missing Skills

- compliance (1)
- financial crime (2)
- chain of custody (3)

## Top Emerging Skills

- compliance
- financial crime
- chain of custody
- Google Cloud Analytics
- Azure
- AWS

## KNN Results

### Especialización en Alta Gerencia
- K=5 jobs: ingeniero en seguridad, Desarrollador Backend, Desarrollador Mobile, Senior Full Stack (Back-end oriented) (Node.js) Developer/Architect, Gestor de Activos TI
- K=10 jobs: ingeniero en seguridad, Desarrollador Backend, Desarrollador Mobile, Senior Full Stack (Back-end oriented) (Node.js) Developer/Architect, Gestor de Activos TI, Project Manager, Desarrollador Full Stack, Arquitecto de Soluciones / Arquitecto de Software .NET - Azure, Administrador de Plataformas VMware Junior, Technical QA Analyst
- K=20 jobs: ingeniero en seguridad, Desarrollador Backend, Desarrollador Mobile, Senior Full Stack (Back-end oriented) (Node.js) Developer/Architect, Gestor de Activos TI, Project Manager, Desarrollador Full Stack, Arquitecto de Soluciones / Arquitecto de Software .NET - Azure, Administrador de Plataformas VMware Junior, Technical QA Analyst, Inside Sales, Técnico de Soporte, Ingeniero de Infraestructura, Ingeniero de Datos GCP, Analista de Monitoreo, Lider SOC, Accounting & Reporting-Contador Sector Bancario TI, Técnico de Soporte - Inventarios, Ingeniero de Integración y Desarrollo, Administrador Servidores de Aplicaciones IBM y Oracle
- K=5 programs: Especialización en Administración y Gerencia de la Salud, Especialización en Gerencia Educativa, Especialización en Gestión Pública, Especialización en Derecho de la Empresa, Especialización en Dirección Comercial y Ventas

### Especialización en Administración y Gerencia de la Salud
- K=5 jobs: ingeniero en seguridad, Desarrollador Backend, Desarrollador Mobile, Senior Full Stack (Back-end oriented) (Node.js) Developer/Architect, Gestor de Activos TI
- K=10 jobs: ingeniero en seguridad, Desarrollador Backend, Desarrollador Mobile, Senior Full Stack (Back-end oriented) (Node.js) Developer/Architect, Gestor de Activos TI, Project Manager, Desarrollador Full Stack, Arquitecto de Soluciones / Arquitecto de Software .NET - Azure, Administrador de Plataformas VMware Junior, Technical QA Analyst
- K=20 jobs: ingeniero en seguridad, Desarrollador Backend, Desarrollador Mobile, Senior Full Stack (Back-end oriented) (Node.js) Developer/Architect, Gestor de Activos TI, Project Manager, Desarrollador Full Stack, Arquitecto de Soluciones / Arquitecto de Software .NET - Azure, Administrador de Plataformas VMware Junior, Technical QA Analyst, Inside Sales, Técnico de Soporte, Ingeniero de Infraestructura, Ingeniero de Datos GCP, Analista de Monitoreo, Lider SOC, Accounting & Reporting-Contador Sector Bancario TI, Técnico de Soporte - Inventarios, Ingeniero de Integración y Desarrollo, Administrador Servidores de Aplicaciones IBM y Oracle
- K=5 programs: Especialización en Alta Gerencia, Especialización en Gerencia Educativa, Especialización en Gestión Pública, Especialización en Gestión Humana, Especialización en Dirección y Gestión de Tecnologías de la Información

### Especialización en Derecho de la Empresa
- K=5 jobs: ingeniero en seguridad, Desarrollador Backend, Desarrollador Mobile, Senior Full Stack (Back-end oriented) (Node.js) Developer/Architect, Gestor de Activos TI
- K=10 jobs: ingeniero en seguridad, Desarrollador Backend, Desarrollador Mobile, Senior Full Stack (Back-end oriented) (Node.js) Developer/Architect, Gestor de Activos TI, Project Manager, Desarrollador Full Stack, Arquitecto de Soluciones / Arquitecto de Software .NET - Azure, Administrador de Plataformas VMware Junior, Technical QA Analyst
- K=20 jobs: ingeniero en seguridad, Desarrollador Backend, Desarrollador Mobile, Senior Full Stack (Back-end oriented) (Node.js) Developer/Architect, Gestor de Activos TI, Project Manager, Desarrollador Full Stack, Arquitecto de Soluciones / Arquitecto de Software .NET - Azure, Administrador de Plataformas VMware Junior, Technical QA Analyst, Inside Sales, Técnico de Soporte, Ingeniero de Infraestructura, Ingeniero de Datos GCP, Analista de Monitoreo, Lider SOC, Accounting & Reporting-Contador Sector Bancario TI, Técnico de Soporte - Inventarios, Ingeniero de Integración y Desarrollo, Administrador Servidores de Aplicaciones IBM y Oracle
- K=5 programs: Especialización en Alta Gerencia, Especialización en Gestión Pública, Especialización en Administración y Gerencia de la Salud, Especialización en Dirección Comercial y Ventas, Especialización en Gerencia Educativa

### Especialización en Gestión Humana
- K=5 jobs: ingeniero en seguridad, Desarrollador Backend, Desarrollador Mobile, Senior Full Stack (Back-end oriented) (Node.js) Developer/Architect, Gestor de Activos TI
- K=10 jobs: ingeniero en seguridad, Desarrollador Backend, Desarrollador Mobile, Senior Full Stack (Back-end oriented) (Node.js) Developer/Architect, Gestor de Activos TI, Project Manager, Desarrollador Full Stack, Arquitecto de Soluciones / Arquitecto de Software .NET - Azure, Administrador de Plataformas VMware Junior, Technical QA Analyst
- K=20 jobs: ingeniero en seguridad, Desarrollador Backend, Desarrollador Mobile, Senior Full Stack (Back-end oriented) (Node.js) Developer/Architect, Gestor de Activos TI, Project Manager, Desarrollador Full Stack, Arquitecto de Soluciones / Arquitecto de Software .NET - Azure, Administrador de Plataformas VMware Junior, Technical QA Analyst, Inside Sales, Técnico de Soporte, Ingeniero de Infraestructura, Ingeniero de Datos GCP, Analista de Monitoreo, Lider SOC, Accounting & Reporting-Contador Sector Bancario TI, Técnico de Soporte - Inventarios, Ingeniero de Integración y Desarrollo, Administrador Servidores de Aplicaciones IBM y Oracle
- K=5 programs: Especialización en Gerencia Educativa, Especialización en Administración y Gerencia de la Salud, Especialización en Dirección Comercial y Ventas, Especialización en Gestión Pública, Especialización en Gestión de la Seguridad y Salud en el Trabajo

### Especialización en Seguridad Informática
- K=5 jobs: Data Protection Officer, Compliance Officer, Desarrollador Full Stack, Lider SOC, Ingeniero Residente de Redes y Ciberseguridad
- K=10 jobs: Data Protection Officer, Compliance Officer, Desarrollador Full Stack, Lider SOC, Ingeniero Residente de Redes y Ciberseguridad, Cybersecurity Analyst, Técnico de Soporte, Ingeniero de Integración y Desarrollo, Especialista, Gestor de Activos TI
- K=20 jobs: Data Protection Officer, Compliance Officer, Desarrollador Full Stack, Lider SOC, Ingeniero Residente de Redes y Ciberseguridad, Cybersecurity Analyst, Técnico de Soporte, Ingeniero de Integración y Desarrollo, Especialista, Gestor de Activos TI, Data Governance Analyst, Compliance and Risk Lead, Project Manager Middle – Servicios Integrados de Telecomunicaciones, Public Health Program Coordinator, Corporate Counsel, analista de datos, Contract and Procurement Manager, Coordinador ambiental - Sector Avicola, Ingeniero de Seguridad de Aplicaciones / DevSecOps, Analista de Monitoreo
- K=5 programs: Especialización en Dirección y Gestión de Tecnologías de la Información, Especialización en Ingeniería de Software, Especialización en Gestión de la Seguridad y Salud en el Trabajo, Especialización en Gerencia Financiera, Especialización en Revisoría Fiscal y Auditoría de Cuentas

## Risks
- If the skill taxonomy remains shallow, coverage can be inflated by a narrow canonical set.
- Jobs without skills remain low-signal and may understate market alignment.
- KNN is only as good as the current vocabulary; no supervised labels are used yet.

## Limitations
- Current DB materializes programs mostly at specialization grain.
- Faculty metadata is not fully materialized in the operational schema.
- Microcurriculum context is used opportunistically when available.

## Next Steps
- Promote the alignment views to Power BI and Deneb dashboards.
- Re-run the report after extending canonical skills and aliases.
- Add longitudinal trend views for market skill growth once historical snapshots are available.
