# Domain Taxonomy Implementation Report

## Scope
- Implemented a first-level disciplinary taxonomy for academic pertinence.
- Reused the existing matching and recommendation pipeline.
- No physical tables were added.
- The new taxonomy is exposed through views and matching logic only.

## Implemented Domains
1. Data & Analytics
2. Artificial Intelligence
3. Cybersecurity
4. Criminology & Security
5. Finance & Accounting
6. Project Management
7. Business Management
8. Marketing & Commercial
9. Logistics & Operations
10. Education
11. Health
12. Legal & Compliance

The prior `Psychology` branch was canonicalized into `Business Management` so the public domain set stays at exactly 12 domains.

## What Changed
- Skills, aliases, programs, specializations, jobs, and job-skill rows are now classified into disciplinary domains.
- Matching now applies a domain factor:
  - same domain: `1.0`
  - related domain: `0.5`
  - different domain: `0.1`
- KNN ranking now prioritizes same-domain neighbors before cross-domain suggestions.
- The reusable dashboard views were regenerated with domain fields and weighted similarity.

## Views Regenerated
- `vw_skill_domain_taxonomy`
- `vw_skill_alias_domain_taxonomy`
- `vw_program_domain_taxonomy`
- `vw_job_domain_taxonomy`
- `vw_job_skill_domain_taxonomy`
- `vw_program_market_alignment`
- `vw_program_skill_gaps`
- `vw_program_recommended_jobs`
- `vw_program_program_similarity`

## Programs Reclassified
Evidence from the previous validation artifacts shows the following corrections:

- `Especializacion en Revisoria Fiscal y Auditoria de Cuentas`
  - Before: absorbed by analytic / technical similarity
  - After: `Finance & Accounting`
  - Effect: stops inheriting `Data Engineer`, `Reporting Analyst`, and similar false positives

- `Especializacion en Criminologia`
  - Before: contaminated by generic analytics / technology buckets
  - After: `Criminology & Security`
  - Effect: aligns with criminal investigation, forensic analysis, public safety, and security roles

- `Especializacion en Derecho Digital`
  - After: `Legal & Compliance`

- `Especializacion en Visual Analytics y Big Data`
  - After: `Data & Analytics`

- `Especializacion en Inteligencia Artificial`
  - After: `Artificial Intelligence`

- `Especializacion en Seguridad Informatica`
  - After: `Cybersecurity`

## Employment Reclassification Impact
The criminology/security sources previously landed in generic domains. The audit evidence showed:

- Europol Careers: 164 jobs
- Interpol Careers: 4 jobs
- UNODC Careers: 4 jobs
- Fiscalia Colombia Convocatorias: 2 jobs
- Securitas Colombia Careers: 10 jobs

Total source-level coverage reviewed: `184` jobs.

These records were previously split across `Tecnologia y datos`, `Educacion`, and `Financiero`. With the new taxonomy, they can be represented under `Criminology & Security` instead of being absorbed by generic domains.

## Reduction in False Positives
The biggest false-positive pattern was domain drift:
- finance and audit programs receiving data-engineering recommendations
- criminology/security records being shown as analytics or finance
- non-technical programs inheriting BI / software suggestions from shared keywords

The domain factor now suppresses that drift:
- unrelated domains are penalized to `0.1`
- related domains keep partial transfer at `0.5`
- same-domain matches remain fully weighted at `1.0`

Concrete example already validated in prior artifacts:
- `Especializacion en Revisoria Fiscal y Auditoria de Cuentas`
  - previously received `Data Engineer`, `Reporting Analyst`, `Cloud Analytics Engineer`
  - now stays within `Finance & Accounting`

## Impact on Matching
- `vw_match_empleo_especializacion` now exposes:
  - `program_domain`
  - `job_domain`
  - `domain_weight`
  - `base_match_score`
  - adjusted `match_score`
- `vw_program_program_similarity` now includes domain-aware similarity and weighted adjustment.
- KNN ranking now favors neighbors inside the same disciplinary domain, which reduces semantic leakage across unrelated fields.

## Impact on Recommendations
- `vw_program_recommended_jobs` now carries domain-aware scoring instead of pure lexical overlap.
- `vw_program_market_alignment` now includes the program domain label, making dashboard interpretation easier.
- Recommendations for audit, criminology, legal, finance, education, health, and management programs are less likely to be polluted by generic analytics vacancies.

## Validation Evidence Used
- `outputs/domain_constrained_matching_report.md`
- `outputs/program_market_matching_validation.md`
- `outputs/criminology_domain_audit.md`

## Risks and Limitations
- This session validated the implementation at the code/view level.
- A fresh warehouse recomputation under the new views should be run to persist final before/after metrics in a single snapshot.
- The underlying crawlers and scheduler were intentionally left unchanged.

