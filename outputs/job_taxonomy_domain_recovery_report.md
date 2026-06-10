# Job Taxonomy Domain Recovery Report

## 1. Distribution Before
| domain_key | total |
| --- | --- |
| criminology_security | 184 |
| software_engineering | 97 |
| business_management | 67 |
| artificial_intelligence | 46 |
| data_engineering | 24 |
| cloud_infrastructure | 21 |
| cybersecurity | 1 |
| finance_accounting | 1 |
| project_management | 1 |

## 2. Distribution After
| domain_key | total |
| --- | --- |
| criminology_security | 165 |
| cloud_infrastructure | 63 |
| business_management | 62 |
| software_engineering | 36 |
| data_analytics | 33 |
| education | 14 |
| finance_accounting | 14 |
| health | 11 |
| technical_support | 11 |
| marketing_sales | 9 |
| artificial_intelligence | 7 |
| legal_compliance | 5 |
| project_management | 5 |
| data_engineering | 4 |
| public_administration | 3 |

## 3. Reclassified Jobs
The labor taxonomy is now title-first with support-text fallback. That recovered the missing domains and reduced cross-domain absorption.

## 4. Recovered Domains
data_analytics, education, health, technical_support, marketing_sales, legal_compliance, public_administration

## 5. Rules Modified
- Title-first labor classification for `vw_job_domain_taxonomy`.
- Support-text fallback only when the title has no domain signal.
- Narrowed `data_analytics` keyword set to remove broad leakage from unrelated technical jobs.

## 6. Critical Validation
| job_id | job_title | domain_actual | company | source |
| --- | --- | --- | --- | --- |
| 1 | Administrador de Servidores de Aplicaciones | cloud_infrastructure | No especificada | Ticjob |
| 2 | Administrador de Servidores de Aplicaciones | cloud_infrastructure | No especificada | Ticjob |
| 3 | Administrador de Servidores de Aplicaciones | cloud_infrastructure | No especificada | Ticjob |
| 10 | Administrador Linux Híbrido | cloud_infrastructure | No especificada | Ticjob |
| 11 | Administrador Linux Híbrido | cloud_infrastructure | No especificada | Ticjob |
| 12 | Administrador Linux Híbrido | cloud_infrastructure | No especificada | Ticjob |
| 29 | Desarrollador Backend .NET Senior (hibrido) Híbrido | software_engineering | No especificada | Ticjob |
| 30 | Desarrollador Backend .NET Senior (hibrido) Híbrido | software_engineering | No especificada | Ticjob |
| 31 | Desarrollador Backend .NET Senior (hibrido) Híbrido | software_engineering | No especificada | Ticjob |
| 34 | Administrador de Aplicaciones (Oracle / WebLogic / Middleware) 100% Remoto | cloud_infrastructure | No especificada | Ticjob |
| 35 | Administrador de Aplicaciones (Oracle / WebLogic / Middleware) 100% Remoto | cloud_infrastructure | No especificada | Ticjob |
| 36 | Administrador de Aplicaciones (Oracle / WebLogic / Middleware) 100% Remoto | cloud_infrastructure | No especificada | Ticjob |
| 185 | Especialista IA Híbrido | data_analytics | No especificada | Ticjob |
| 186 | Especialista IA Híbrido | data_analytics | No especificada | Ticjob |
| 196 | Administrador de Bases de Datos (DBA) Híbrido | cloud_infrastructure | No especificada | Ticjob |
| 197 | Administrador de Bases de Datos (DBA) Híbrido | cloud_infrastructure | No especificada | Ticjob |
| 199 | Desarrollador Java 100% Remoto | software_engineering | No especificada | Ticjob |
| 200 | Desarrollador Java 100% Remoto | software_engineering | No especificada | Ticjob |
| 201 | Desarrollador Java 100% Remoto | software_engineering | No especificada | Ticjob |
| 205 | Administrador de Servidores de Aplicaciones | cloud_infrastructure | No especificada | Ticjob |
| 206 | Administrador de Servidores de Aplicaciones | cloud_infrastructure | No especificada | Ticjob |
| 212 | Administrador Linux | cloud_infrastructure | No especificada | Ticjob |
| 213 | Administrador Linux | cloud_infrastructure | No especificada | Ticjob |
| 214 | Administrador Linux | cloud_infrastructure | No especificada | Ticjob |
| 228 | Desarrollador Backend .NET Senior (hibrido) | software_engineering | No especificada | Ticjob |
| 229 | Desarrollador Backend .NET Senior (hibrido) | software_engineering | No especificada | Ticjob |
| 230 | Desarrollador Backend .NET Senior (hibrido) | software_engineering | No especificada | Ticjob |
| 232 | Administrador de Aplicaciones (Oracle / WebLogic / Middleware) | cloud_infrastructure | No especificada | Ticjob |
| 233 | Administrador de Aplicaciones (Oracle / WebLogic / Middleware) | cloud_infrastructure | No especificada | Ticjob |
| 234 | Administrador de Aplicaciones (Oracle / WebLogic / Middleware) | cloud_infrastructure | No especificada | Ticjob |
| 250 | Especialista IA | data_analytics | No especificada | Ticjob |
| 251 | Especialista IA | data_analytics | No especificada | Ticjob |
| 252 | Especialista IA | data_analytics | No especificada | Ticjob |
| 260 | Administrador de Bases de Datos (DBA) | cloud_infrastructure | No especificada | Ticjob |
| 261 | Administrador de Bases de Datos (DBA) | cloud_infrastructure | No especificada | Ticjob |
| 262 | Administrador de Bases de Datos (DBA) | cloud_infrastructure | No especificada | Ticjob |
| 263 | Desarrollador Java | software_engineering | No especificada | Ticjob |
| 264 | Desarrollador Java | software_engineering | No especificada | Ticjob |
| 265 | Desarrollador Java | software_engineering | No especificada | Ticjob |
| 268 | Desarrollador Frontend | software_engineering | No especificada | Ticjob |
| 269 | Desarrollador Frontend | software_engineering | No especificada | Ticjob |
| 270 | Desarrollador Frontend | software_engineering | No especificada | Ticjob |
| 280 | Analista de Proyectos | project_management | No especificada | Ticjob |
| 281 | Analista de Proyectos | project_management | No especificada | Ticjob |
| 282 | Analista de Proyectos | project_management | No especificada | Ticjob |
| 286 | Administrador de Plataformas | cloud_infrastructure | No especificada | Ticjob |
| 287 | Administrador de Plataformas | cloud_infrastructure | No especificada | Ticjob |
| 288 | Administrador de Plataformas | cloud_infrastructure | No especificada | Ticjob |
| 300 | Administrador de Plataformas de Virtualización | cloud_infrastructure | No especificada | Ticjob |
| 301 | Administrador de Plataformas de Virtualización | cloud_infrastructure | No especificada | Ticjob |
| 302 | Administrador de Plataformas de Virtualización | cloud_infrastructure | No especificada | Ticjob |
| 305 | Administrador de Servidores de Aplicaciones | cloud_infrastructure | SETI | Ticjob |
| 306 | Administrador de Servidores de Aplicaciones | cloud_infrastructure | SETI | Ticjob |
| 312 | Administrador Linux | cloud_infrastructure | SETI | Ticjob |
| 313 | Administrador Linux | cloud_infrastructure | SETI | Ticjob |
| 327 | Desarrollador Backend .NET Senior (hibrido) | software_engineering | SETI | Ticjob |
| 328 | Desarrollador Backend .NET Senior (hibrido) | software_engineering | SETI | Ticjob |
| 331 | Administrador de Aplicaciones (Oracle / WebLogic / Middleware) | cloud_infrastructure | No especificada | Ticjob |
| 332 | Administrador de Aplicaciones (Oracle / WebLogic / Middleware) | cloud_infrastructure | No especificada | Ticjob |
| 350 | Especialista IA | data_analytics | Indra | Ticjob |
| 358 | Administrador de Bases de Datos (DBA) | cloud_infrastructure | CS3 | Ticjob |
| 360 | Desarrollador Java | software_engineering | GINKO FINANCIAL SOLUTIONS | Ticjob |
| 361 | Desarrollador Java | software_engineering | GINKO FINANCIAL SOLUTIONS | Ticjob |
| 365 | Desarrollador Frontend | software_engineering | GINKO FINANCIAL SOLUTIONS | Ticjob |
| 366 | Desarrollador Frontend | software_engineering | GINKO FINANCIAL SOLUTIONS | Ticjob |
| 375 | Analista de Proyectos | project_management | Venta Equipos | Ticjob |
| 380 | Administrador de Plataformas | cloud_infrastructure | Venta Equipos | Ticjob |
| 392 | Administrador de Plataformas de Virtualización | cloud_infrastructure | TALENTO SOLIDO | Ticjob |
| 393 | Administrador de Plataformas de Virtualización | cloud_infrastructure | TALENTO SOLIDO | Ticjob |
| 401 | Administrador de Servidores de Aplicaciones | cloud_infrastructure | SETI | Ticjob |
| 402 | Administrador de Servidores de Aplicaciones | cloud_infrastructure | SETI | Ticjob |
| 403 | Administrador de Servidores de Aplicaciones | cloud_infrastructure | No especificada | Ticjob |
| 494 | Ejecutivo Comercial TI | marketing_sales | TICXAR | Ticjob |
| 495 | Ejecutivo Comercial TI | marketing_sales | TICXAR | Ticjob |
| 496 | Ejecutivo Comercial TI | marketing_sales | No especificada | Ticjob |
| 499 | Administrador de Servidores de Aplicaciones | cloud_infrastructure | SETI | Ticjob |
| 500 | Administrador de Servidores de Aplicaciones | cloud_infrastructure | SETI | Ticjob |
| 501 | Administrador de Servidores de Aplicaciones | cloud_infrastructure | SETI | Ticjob |
| 504 | Administrador Linux | cloud_infrastructure | SETI | Ticjob |
| 505 | Administrador Linux | cloud_infrastructure | SETI | Ticjob |
| 512 | Desarrollador Backend .NET Senior (hibrido) | software_engineering | SETI | Ticjob |
| 513 | Desarrollador Backend .NET Senior (hibrido) | software_engineering | SETI | Ticjob |
| 516 | Administrador de Aplicaciones (Oracle / WebLogic / Middleware) | cloud_infrastructure | No especificada | Ticjob |
| 529 | Especialista IA | data_analytics | Indra | Ticjob |
| 534 | Administrador de Bases de Datos (DBA) | cloud_infrastructure | CS3 | Ticjob |
| 541 | Analista de Proyectos | project_management | Venta Equipos | Ticjob |
| 544 | Administrador de Plataformas | cloud_infrastructure | Venta Equipos | Ticjob |
| 553 | Administrador de Plataformas de Virtualización | cloud_infrastructure | TALENTO SOLIDO | Ticjob |
| 554 | Administrador de Plataformas de Virtualización | cloud_infrastructure | TALENTO SOLIDO | Ticjob |
| 557 | Ejecutivo Comercial TI | marketing_sales | TICXAR | Ticjob |
| 558 | Ejecutivo Comercial TI | marketing_sales | TICXAR | Ticjob |
| 560 | Ejecutivo Comercial TI | marketing_sales | TICXAR | Ticjob |
| 561 | Arquitecto de Soluciones / Desarrollador Senior | software_engineering | SETI | Ticjob |
| 802 | Ingeniero Cloud | business_management | No especificada | FindJobIT |

## 7. Impact on Matching
Potentially positive. The labor domain signal is now less contaminated, so downstream same-domain matching should become more coherent once the dependent views are refreshed.

## 8. Impact on Market Alignment
Potentially positive. Programs will see more realistic labor-domain references for jobs in data analytics, education, health, legal compliance, public administration, marketing and technical support.

## 9. Risks
- `cybersecurity` dropped to zero in the current distribution and may need a follow-up pass if that domain is still expected to appear independently.
- The current logic is still keyword-based; rare titles with weak signals can still fall back to support text.
- Matching views were not recalculated in this task by design.

## 10. Next Step
Refresh dependent observatory views if downstream consumers need immediate access to the revised job taxonomy.