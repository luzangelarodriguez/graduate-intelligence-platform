# Frontend Route Audit

## Scope
Audit of the current React routing used by the Graduate Intelligence Platform frontend.

## Source files reviewed
- `graduate_intelligence_platform/frontend/src/App.tsx`
- `graduate_intelligence_platform/frontend/src/layouts/AppLayout.tsx`
- `graduate_intelligence_platform/frontend/src/pages/DashboardPage.tsx`
- `graduate_intelligence_platform/frontend/src/pages/ProgramsPage.tsx`
- `graduate_intelligence_platform/frontend/src/pages/ProgramIntelligenceDetailPage.tsx`
- `graduate_intelligence_platform/frontend/src/pages/ProgramMicrocurriculumPage.tsx`
- `graduate_intelligence_platform/frontend/src/pages/ProgramForecastPage.tsx`
- `graduate_intelligence_platform/frontend/src/pages/ProgramSimulationPage.tsx`
- `graduate_intelligence_platform/frontend/src/components/program-intelligence/ProgramIntelligenceBlocks.tsx`

## Route map

| URL | Rendered page | Notes |
|---|---|---|
| `/` | `DashboardPage` | Protected route inside `AppLayout`; institutional dashboard with selector and program ranking. |
| `/dashboard` | `DashboardPage` | Same component as `/`; legacy dashboard entry now resolved into the institutional observatory. |
| `/programas` | `ProgramsPage` | New program ranking and selector view. This is the primary entry for one-by-one program analysis. |
| `/programs/:programId` | `ProgramIntelligenceDetailPage` | Executive program detail page. |
| `/programs/:programId/microcurriculum` | `ProgramMicrocurriculumPage` | Microcurriculum traceability and coverage view. |
| `/programs/:programId/forecast` | `ProgramForecastPage` | Forecast view with 6/12/24 month horizons. |
| `/programs/:programId/simulation` | `ProgramSimulationPage` | Curriculum simulation view. |
| `/observatorio-institucional` | `ExecutiveSummaryPage` | Institutional summary surface, kept as a secondary route. |
| `/login` | `LoginPage` | Authentication entry. |
| `/microcurriculum-demo` | `MicrocurriculumDemoPage` | Legacy/demo view retained for compatibility. |

## Findings

1. The root `/` route no longer points to the old public executive summary. It renders the protected `DashboardPage` inside `AppLayout`.
2. `AppLayout` now renders the sidebar, so protected pages show the institutional shell instead of a stripped content-only view.
3. `/programas` is the dedicated program experience and exposes the visible selector, selected program, domain/subdomain, benchmark, and program ranking.
4. `/programs/:programId` and its sibling views are the canonical Program Intelligence routes for detail, microcurriculum, forecast, and simulation.
5. There is no active `src/routes/*` route tree. Routing is centralized in `App.tsx`.

## Legacy visibility check

No active route still renders the old isolated observatory as the default landing page.
The old institutional summary still exists only as a secondary route:

- `/observatorio-institucional`

## Validation

- Frontend build passes.
- Visual QA confirms the selector is visible on the program views and the protected shell includes the sidebar.

