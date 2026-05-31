# Program Intelligence UX V1 - QA Audit

**Scope**
- Program Detail: `/programs/:programId`
- Microcurriculum: `/programs/:programId/microcurriculum`
- Forecast: `/programs/:programId/forecast`
- Simulation: `/programs/:programId/simulation`

**Method**
- Code-path review of the React frontend and API contracts.
- Build verification already completed successfully for the current implementation.
- This audit does **not** include live browser screenshots from this pass, so screenshot-dependent findings are marked as required evidence.

## Executive summary

The UX is structurally sound: all four screens have loading states, empty states, navigation, and live API wiring. The strongest parts are explainability and the move away from a generic dashboard toward a program-centric narrative.

The main production risk is in the forecast / simulation layer: the backend simulator currently uses the selected skills, but the horizon parameter does not materially influence the projection formulas, so 6/12/24 month cards can render identical values. Microcurriculum traceability is also still program-level rather than microcurriculum-entity-level, which limits committee review precision.

## Screen-by-screen audit

### 1) Program Detail

**Data present**
- `getPrograma(programId)`
- `getProgramIntelligenceDetail(programId)`
- `getCurriculumRisk(programId)`
- `getProgramAlignment(programId)`
- `getForecastSummary(25)`
- `getExecutiveObservatory()`

**Status**
- Loading state present
- Empty state present
- Navigation present (`ProgramTabs`, back to list)
- Explainability present (`narrative`, `risk_drivers`, `top_gaps`, `top_recommendations`)
- Evidence traceability present, but partly mixed with global market context

**Findings**
- Real program data is present.
- The page uses `forecastSummary` chips as market context, not program data; this is correctly labeled as market signals and does not appear to be a misrepresentation.
- The "updated at" label is derived from program intelligence or executive observatory metadata, which is acceptable but not a direct program-specific timestamp.

**Defects**
- No critical defect detected in the code path.

**Severity**
- Low

### 2) Microcurriculum

**Data present**
- `program.skills`
- `programIntelligence.top_gaps`
- `curriculumRisk`
- `alignment`

**Status**
- Loading state present
- Empty state present
- Navigation present
- Explainability present
- Evidence traceability partial

**Findings**
- The page is useful for a committee-style review.
- It currently relies on `program.skills` as the microcurriculum proxy.
- There is no explicit microcurriculum entity mapping exposed in the frontend contract, so the screen cannot yet show a true microcurriculum identifier / source mapping chain.

**Defects**
- Missing explicit microcurriculum mappings. The page can show skills covered, but not a distinct microcurriculum record or a source-table trace for each mapping.

**Severity**
- Medium

### 3) Forecast

**Data present**
- `alignment`
- `forecastSummary`
- `criticalPrograms`
- `useProgramSimulations(..., [6, 12, 24])`

**Status**
- Loading state present
- Empty state present
- Navigation present
- Explainability present
- Evidence traceability partial

**Findings**
- The page clearly separates current program metrics from institutional market signals.
- The right-hand signal cards are global forecast context, not program-only metrics.
- The risk panel is institution-level and is labeled as such.

**Defects**
- The forecast cards can show the same projection across 6/12/24 months because the simulator output currently does not use `horizon_months` in the projection formulas. The horizon affects persistence and keying, but not the math.

**Severity**
- High

### 4) Simulation

**Data present**
- `selectedSkills`
- `getCurriculumSimulator(programId, skills, horizon)`
- `curriculum_simulations`

**Status**
- Loading state present
- Empty state present
- Navigation present
- Explainability present
- Evidence traceability present via `supporting_evidence.source_tables`

**Findings**
- The UI allows skills to be toggled and custom skills to be added.
- The selected skills list is driven by live data and not mock content.
- The explanation block and evidence tables are visible, which is good for academic review.

**Defects**
- If the backend horizon logic remains unchanged, the simulation can appear static across horizons.

**Severity**
- High

## Aggregated data audit

**Aggregated data mistakenly shown as program data**
- No direct mislabeling was detected in the current code.
- The aggregated panels are labeled as market signals or institutional context.
- The only caution is that the forecast page mixes program-level and institutional-level context in one screen; this is acceptable if the labels remain explicit.

## Forecast / simulation behavior audit

### Forecast values across horizons

**Observation**
- The frontend requests 6, 12, and 24 month projections.
- The backend simulator persists horizon-specific rows, but the projection equations do not currently multiply or adjust the main output values by `horizon_months`.

**Impact**
- Users may see the same numbers across horizons, which weakens the purpose of the forecast view.

### Simulation values across selected skills

**Observation**
- The simulation engine does use the selected skills to derive normalized skills, gap matches, and evidence.
- A change in selected skills should influence the result.

**Risk**
- If the selected skill set is not materially different, or if the skill pool is too narrow, the output can feel unchanged. This is a data-content issue rather than a front-end defect.

## Screenshot evidence required

To close this QA pass, capture the following:

1. Program Detail after load, with:
   - header
   - narrative
   - top gaps
   - top recommendations
   - forecast cards

2. Microcurriculum after load, with:
   - skills covered
   - market demand bars
   - gap cards

3. Forecast after load, with:
   - the three horizon cards visible
   - market signals panel
   - critical programs panel

4. Simulation after load, with:
   - selected skills chips
   - one custom skill added
   - forecast cards
   - explanation and evidence

5. Loading state screenshot for one screen

6. Empty state screenshot for one screen

## Defects

| Defect | Severity | Impact | Quick fix |
|---|---:|---|---|
| Horizon outputs can remain unchanged across 6/12/24 months | High | Forecast loses predictive value and reads as repeated content | Make the simulator apply horizon weighting to alignment / risk / employability formulas |
| Microcurriculum lacks explicit entity-level mapping | Medium | Committee review cannot trace a skill to a distinct microcurriculum record | Add a microcurriculum mapping field or source-table trace if the backend exposes it |
| Forecast page mixes institutional context and program context in one screen | Low | Can confuse users if labels are not read carefully | Add a small context badge: "program" vs "institutional market" |
| Evidence traceability is weaker on some panels than on simulation | Low | Harder to audit source provenance in committee settings | Surface source tables and generated_at badges consistently |

## Quick wins

- Add a visible "context" badge to the forecast page panels.
- Surface source tables and freshness metadata on the program detail and forecast screens.
- Show a small note when horizons are identical because of insufficient signal separation.
- Add explicit microcurriculum labels if the API can return them.

## Usability scores

- **Executive usability score:** 7.1 / 10
- **Academic committee usability score:** 7.6 / 10

**Why**
- The narrative structure and explainability are strong.
- The remaining friction is mostly around horizon differentiation and mapping traceability, which matter a lot in decision meetings.

## Conclusion

Program Intelligence UX V1 is a strong step toward an academic decision-support experience. It already supports the right conversation shape: program, gap, recommendation, forecast, and simulation. The main next fix should be horizon-sensitive simulation behavior and stronger microcurriculum traceability.
