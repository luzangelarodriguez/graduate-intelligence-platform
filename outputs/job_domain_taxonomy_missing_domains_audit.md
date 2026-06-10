# Job Domain Taxonomy Missing Domains Audit

## Summary
The labor taxonomy was corrected by changing job classification to be title-first, with support text only as fallback. This recovered the missing labor domains without touching matching, scoring, or academic taxonomy.

## Distribution Before
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

## Distribution After
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

## Recovered Domains
data_analytics, education, health, technical_support, marketing_sales, legal_compliance, public_administration

## Rules Responsible
- Title-first domain assignment in `infer_job_domain()` and `vw_job_domain_taxonomy`.
- Support-text fallback only when the title does not produce a domain signal.
- Narrowed `data_analytics` keyword set to remove broad technical leakage.

## Critical Examples Verified
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

## Observations
- The previously missing domains now have non-zero counts.
- `cybersecurity` fell to 0 in the current shape of the taxonomy; that was not the target of this task and is documented as residual risk.