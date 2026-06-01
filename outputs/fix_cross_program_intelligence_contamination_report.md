# Fix Cross-Program Intelligence Contamination

## Root cause

The simulation layer was using a loose evidence check that could keep producing projections even when a specialization had no processed microcurriculum. That allowed signals from other programs to leak into empty specializations through shared program-intelligence fallbacks.

The contamination risk was highest in `build_curriculum_impact_simulation(...)`, where the code had to distinguish between:

- real curricular evidence for the selected program
- program-intelligence evidence for that same program
- inherited signals from other specializations

The bug was that empty programs could still pick up non-empty intelligence paths too early.

## Fix

The simulator now returns an explicit empty-evidence state **only when both** conditions are true:

1. the program has no curricular evidence in `microcurriculum_context`
2. the program has no program-intelligence evidence of its own

That means:

- programs with no microcurriculum, no competencies, and no extracted skills return a zero-state
- programs with real evidence, including Program 108 Criminology, still generate projections
- the simulator no longer falls back to signals from other specializations

## Before

For programs without curricular evidence:

- alignment could be inherited from other intelligence paths
- gaps and recommendations could appear even when the program had no real evidence
- forecasts and simulation outputs could be populated from unrelated specialization signals
- the UI could show academic intelligence that did not belong to the selected program

## After

For programs without curricular evidence:

- `alignment_score = 0`
- `employability_score = 0`
- `coverage_score = 0`
- `gap_count = 0`
- `forecast_signals = []`
- `role_signals = []`
- `recommendations = []`
- `benchmark = []`
- `simulation = null`

And the UI shows:

- `No curricular evidence available`
- `Upload or process a microcurriculum to generate academic intelligence.`

## Validation

### Backend

- `python -m pytest tests/ml/test_curriculum_impact_simulator.py tests/ml/test_curriculum_impact_horizons.py tests/backend/test_executive_ai_endpoints.py`
  - `6 passed`
- `python -m py_compile intelligence/curriculum_impact_simulator.py tests/ml/test_curriculum_impact_simulator.py`
  - OK

### Frontend

- `npm run build`
  - OK

## Behavior confirmed

- **Program 108 Criminology** keeps real criminology-oriented signals.
- **Programs without microcurriculum evidence** now render an empty academic-intelligence state instead of inheriting data from other specializations.
- The contamination path is removed from the simulator and the main program-intelligence flow.

## Files changed in this fix

- `intelligence/curriculum_impact_simulator.py`
- `tests/ml/test_curriculum_impact_simulator.py`

## Notes

The repository contains many pre-existing modified files from earlier workstreams. This fix only changes the simulator logic and adds a regression test to protect the empty-evidence behavior.
