# Classification Relaxation Report

## Scope
This change addresses the persistence bottleneck identified in `outputs/job_funnel_audit.md`.
The objective was to stop losing recovered jobs between classification and `jobs` persistence,
without changing crawlers, scheduler, or academic acquisition logic.

## Filters found

### 1. Persistence gate in `crawlers/storage/postgres_warehouse.py`
- Hard block on:
  - `document_type in {"portal_taxonomy", "filter_page", "category_page"}`
  - `source_url.startswith("javascript:")`
- Previous behavior also implicitly depended on the classifier's `gold_job` path because only highly curated rows were consistently propagated with skills and evidence.

### 2. Classification thresholds in `agents/visual_analytics_labor_agent.py`
- `PROBABLE_JOB_THRESHOLD = 0.30`
- `CURATED_JOB_THRESHOLD = 0.55`
- `GOLD_JOB_THRESHOLD = 0.75`

### 3. `document_type` gate in the classifier
- `job_posting` is assigned only when `job_probability_score >= 0.30`
- lower-confidence rows become `unknown`, `search_listing`, `filter_page`, or `portal_taxonomy`

### 4. `curation_level` gate in the classifier
- `gold_job`
- `curated_job`
- `probable_job`
- else `rejected`

### 5. Gold-only propagation path
- `normalize_to_silver()` still requires:
  - `curation_level in {"probable_job", "curated_job", "gold_job"}`
  - `document_type == "job_posting"`
  - no portal-taxonomy catalog signal
- `promote_to_gold()` still requires:
  - `document_type == "job_posting"`
  - `is_real_job_posting`
  - a normalized company
  - a valid http(s) source URL
  - job evidence skills

### 6. Skills propagation gap
- Before this fix, `_job_skills()` used:
  - `semantic_skill_evidence`
  - `job_evidence_skills`
  - `extracted_skills`
- It did not preserve `portal_taxonomy_skills` for low-confidence rows.

## Changes made

### Persistence
- Added `processing_stage` to `public.jobs`.
- Persisted stage values:
  - `candidate_job`
  - `probable_job`
  - `curated_job`
  - `gold_job`
- Relaxed `jobs` persistence so valid http(s) rows are written unless they are hard taxonomy/navigation pages or javascript links.
- Preserved:
  - `source`
  - `source_url`
  - `title`
  - `description`
  - `raw_context`
  - `job_probability_score`
  - `curation_level`
  - `processing_stage`

### Skills
- `_job_skills()` now also persists `portal_taxonomy_skills` as fallback evidence.
- This keeps lower-confidence rows useful for matching and downstream skill graphs.

### Tests
- Added regression coverage for:
  - persistable candidate-like rows
  - hard-blocked taxonomy/javascript URLs
  - `processing_stage` mapping
  - title/description fallback
  - portal-taxonomy skill preservation

## Conversion before

Observed in `outputs/job_funnel_audit.md`:

- LinkedIn: `200 recovered -> 0 jobs`
- Elempleo: `8 recovered -> 0 jobs`
- Indeed: `2 recovered -> 0 jobs`
- FindJobIT: `40 recovered -> 0 jobs`
- Ticjob: `200 recovered -> 75 jobs`
- Europol: `153 recovered -> 82 jobs`

## Conversion after

This change was not rerun against the crawlers, so these numbers are the expected
conversion profile if the same recovered input is replayed through the relaxed persistence path.

- LinkedIn: expected close to `200 -> 200`
- Elempleo: expected close to `8 -> 8`
- Indeed: expected close to `2 -> 2`
- FindJobIT: expected to rise materially from `40 -> up to 40`, subject to hard-blocked pages
- Ticjob: expected to move closer to `200 -> 200`
- Europol: expected to move closer to `153 -> 153`

The real ceiling is still bounded by:
- hard taxonomy/navigation pages
- invalid javascript links
- any future parser failures upstream

## Risk of noise
- Medium to high.
- Persisting candidate/probable rows increases recall, but some search/listing pages and weakly structured results can now land in `jobs`.
- Mitigation:
  - `processing_stage`
  - `job_probability_score`
  - `curation_level`
  - `document_type`
  - existing duplicate grouping

## Risk of duplicates
- Medium.
- Higher recall increases repeated insert attempts from paginated or semi-duplicated source pages.
- Existing mitigations remain in place:
  - `content_hash`
  - `duplicate_group_id`
  - `job_fingerprint`
  - upsert behavior on `jobs`

## Recommendation
1. Keep the relaxed persistence path.
2. Monitor `processing_stage` distributions by source for one full daily cycle.
3. Review `document_type` and `job_probability_score` histograms after the next run.
4. If noise rises too much, reintroduce source-specific soft scoring, not a hard gold-only gate.
5. Treat `candidate_job`, `probable_job`, and `curated_job` as first-class persisted rows for matching and observability.

## Validation
- `python -m py_compile` on:
  - `crawlers/storage/postgres_warehouse.py`
  - `agents/visual_analytics_labor_agent.py`
  - `tests/crawlers/test_postgres_warehouse_relaxation.py`
- Focused tests:
  - `11 passed`
