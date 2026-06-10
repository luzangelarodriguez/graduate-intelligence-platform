# Program skill gap domain fix report

## Before / after
- Targeted audited rows before fix: **212**
- Targeted audited rows after fix: **0**
- Overall rows currently returned by `vw_program_skill_gaps`: **54**
- Overall rows currently returned by `vw_program_market_alignment`: **27**

## Programs affected
- 102 `Especializacion en Educacion y Orientacion Familiar`
- 103 `Especializacion en TIC para la Ensenanza`
- 104 `Especializacion en Gerencia Educativa`
- 106 `Especializacion en Pedagogia y Docencia`
- 83 `Especializacion en Gestion de la Seguridad y Salud en el Trabajo`
- 107 `Especializacion en Administracion y Gerencia de la Salud`

## Counts before and after
| program_id | program_name | before_gap_rows | after_gap_rows | market_alignment_missing_skills |
|---|---|---:|---:|---|
| 102 | Especializacion en Educacion y Orientacion Familiar | 34 | 0 | [] |
| 103 | Especializacion en TIC para la Ensenanza | 34 | 0 | [] |
| 104 | Especializacion en Gerencia Educativa | 34 | 0 | [] |
| 106 | Especializacion en Pedagogia y Docencia | 34 | 0 | [] |
| 83 | Especializacion en Gestion de la Seguridad y Salud en el Trabajo | 42 | 0 | [] |
| 107 | Especializacion en Administracion y Gerencia de la Salud | 34 | 0 | [] |

## Skills eliminated
The following contaminated skills disappeared from the audited programs because they came exclusively from cross-domain positives:
- AI
- APIs
- Azure
- AWS
- ELT
- MLflow
- pandas
- Python
- scikit-learn
- dashboarding
- BI
- Power BI
- SQL
- GCP
- data governance
- privacy
- executive reporting
- Oracle
- PL/SQL
- ITIL
- Scrum
- Kanban
- compliance
- reporting
- pipelines
- machine learning
- security
- trabajo en equipo
- gestion de stakeholders
- pensamiento analitico

## Skills conserved
For the audited programs, the post-fix `missing_skills` payload is now empty.
That is the intended result: only same-domain positives are allowed to contribute gap skills.

## Impact on market alignment
- `vw_program_market_alignment` keeps the same alignment score formulas.
- The `missing_skills` arrays for the audited programs are now empty instead of showing foreign technical skills.
- The dashboard no longer shows AI / cloud / software / analytics noise as education or health gaps.

## Validation result
Live PostgreSQL validation after the fix:
- `SELECT * FROM vw_program_skill_gaps WHERE program_id IN (102,103,104,106,83,107);` -> **0 rows**
- `SELECT * FROM vw_program_market_alignment WHERE program_id IN (102,103,104,106,83,107);` -> **6 rows** with empty `missing_skills`
