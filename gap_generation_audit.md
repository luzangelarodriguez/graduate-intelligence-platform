# Gap Generation Audit

## Scope

Audited the current curriculum gap generation flow for the Academic Pertinence Observatory using the production market skill intelligence output and the pipeline source code.

## Key sources

- `intelligence/run_intelligence_pipeline.py`
- `ml/labor/market_skill_intelligence_engine.py`
- `ml/curriculum/specialization_skill_affinity_engine.py`
- `ml/curriculum/curriculum_market_gap_engine.py`
- `intelligence/curriculum_gap_observatory.py`
- `intelligence/recommendation_api_engine.py`

## Executive summary

The production market skill universe contains 49 candidate skills in the latest market intelligence snapshot. Of those, only 4 are accepted as curriculum-gap candidates by the market gap map (`partial`), while 45 are rejected (`covered` or `irrelevant`).

The pipeline then applies a second, much narrower program-level matcher in `program_intelligence_engine.py`, which reduces the gap set from 4 accepted candidates down to 3 program-specific gaps in production.

The recommendation layer is also constrained by the same narrow gap inputs, which is why the observable recommendation output is only 2 items in the current run.

## Totals

- Total candidate gaps reviewed by the market skill intelligence map: **49**
- Accepted gaps for curriculum-gap generation: **4**
- Rejected gaps: **45**
- Program-level gaps ultimately surfaced in `program_intelligence`: **3**
- Recommendations surfaced in the current pipeline run: **2**

## Filtering rules

### 1) Pipeline hard filter

`intelligence/run_intelligence_pipeline.py` does not consume the full market gap map. Its `_compute_curriculum_gaps()` step hardcodes two exact-match sets:

- Emerging candidates:
  - `Databricks`
  - `Microsoft Fabric`
  - `Synapse`
  - `Copilot BI`
  - `LLM`
  - `RAG`
- Missing candidates:
  - `data governance`
  - `MLOps`
  - `DataOps`
  - `Azure`
  - `AWS`

Only exact string membership in those sets reaches the pipeline gap branch.

### 2) Market skill coverage filter

`ml/labor/market_skill_intelligence_engine.py` assigns each market skill to one of:

- `covered`
- `partial`
- `missing`
- `emerging`
- `irrelevant`

The rules are:

- `covered` if the curriculum affinity is exact.
- `partial` if semantic similarity to a curriculum skill is `>= 0.72`.
- `emerging` if the skill is in the emerging list or its cluster is `Cloud Analytics`, `DataOps`, or `GenAI Analytics`, and market confidence is `high`, `medium`, or `emerging`.
- `missing` if market confidence is `high` or `medium` and the skill is not already covered/partial/emerging.
- `irrelevant` otherwise.

### 3) Curriculum-gap observatory filter

`ml/curriculum/curriculum_market_gap_engine.py` and `intelligence/curriculum_gap_observatory.py` only surface:

- `partial`
- `missing`
- `emerging`

Everything in `covered` or `irrelevant` is discarded from the observatory layer.

### 4) Program-specific matching filter

`intelligence/program_intelligence_engine.py` further reduces gap visibility by matching observatory rows to a specific program using:

- specialization name token overlap
- missing-skill text overlap
- exact normalized overlap between the program's skill list and the gap skill

If a gap does not match those program-level rules, it is not surfaced in the final `program_intelligence` record.

## Minimum thresholds

- Strong market signal starts at `total_weight >= 0.7`, or evidence from:
  - `gold_job_posting`
  - `silver_job_posting`
  - `legacy_empleo_skill`
- `market_signal_confidence = high`:
  - gold evidence, or
  - silver evidence with score `>= 1.2`
- `market_signal_confidence = medium`:
  - silver evidence, or
  - legacy Empleo evidence
- `market_signal_confidence = emerging`:
  - skill is explicitly in the emerging list and score `>= 0.5`
- `calculate_skill_affinity()` thresholds:
  - `covered` when the skill exists exactly in the curriculum graph
  - `partial` when semantic similarity is `>= 0.72`
  - `irrelevant` when similarity is below threshold and the cluster is not enough to promote the skill into `missing` or `emerging`
- `curriculum_gap_observatory` does not add a numeric threshold of its own; it only consumes the three accepted buckets.

## Accepted gaps

- Covered: **14**
- Partial: **4**
- Missing: **0**
- Emerging: **0**

Interpretation:

In the latest market snapshot, the only accepted gap-like signals are the 4 `partial` skills. The rest of the market skills are either already covered or excluded.

## Rejected gaps

- Rejected as `covered`: **14**
- Rejected as `irrelevant`: **31**
- Total rejected: **45**

## Rejection reasons

### Rejection reason A

`Skill con baja relacion semantica frente al grafo curricular de la especializacion.`

This is the main reason behind `irrelevant` skills with weak semantic affinity.

### Rejection reason B

`Skill laboral relevante para el ecosistema de Visual Analytics y Big Data, pero sin cobertura curricular directa.`

This is the main reason for some cloud / data / GenAI terms that are relevant in the market, but still not strong enough to be promoted beyond the irrelevant bucket in the current snapshot.

## Discarded skills

Representative discarded skills from the current production snapshot:

- communication
- teamwork
- problem solving
- Oracle
- Agile
- analytical thinking
- leadership
- English
- Redis
- PostgreSQL
- ITIL
- scikit-learn
- pandas
- stakeholder management
- Scrum
- SSIS
- SQL Server
- MongoDB
- MLflow
- Kanban
- Kafka
- ELT
- LLM
- GCP
- executive reporting
- Qlik
- Copilot BI
- AWS
- Azure
- reporting
- data quality

## Why the pipeline only generates 3 gaps

The 4 accepted gap candidates are still narrowed further by program-specific matching.

In the current production data, only 3 of those accepted candidates are matched into the final `program_intelligence` view because the matcher requires:

- program token overlap, or
- exact overlap with the program skill list, or
- fallback handling when no gap match exists

This means the observatory is not failing to find data; it is applying a narrow match policy after the market-gap step.

## Why only 2 recommendations appear

The recommendation branch in `intelligence/run_intelligence_pipeline.py` is built from:

- `missing_skills`
- `emerging_skills`

Those lists are currently hand-filtered in the pipeline from a small exact-match set, so the recommendation count stays low even when the warehouse contains much richer evidence.

## Conclusion

The low gap count is caused by two stacked filters:

1. A hardcoded exact-match skill whitelist in the pipeline.
2. A market-gap model that discards most skills as `covered` or `irrelevant` before observatory generation.

To increase gap volume safely, the next remediation should widen the exact-match whitelist in `run_intelligence_pipeline.py` and loosen the program-level matching in `program_intelligence_engine.py` so that more `partial` and `missing` skills are allowed through with confidence scores instead of being suppressed.
