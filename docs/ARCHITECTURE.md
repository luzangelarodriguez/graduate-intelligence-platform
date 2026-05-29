# Architecture

## Data flow

`sources -> acquisition workers -> Bronze -> Silver -> Gold -> warehouse intelligence -> observatory metrics -> dashboard datasets`

## Services

- `api/` - public FastAPI observatory API
- `intelligence/` - company, role, recommendation, forecasting and observatory engines
- `ml/` - market skill intelligence, curriculum alignment, training and inference
- `crawlers/` - Playwright-based acquisition runtime
- `pipelines/` - orchestration entrypoints

## Storage

- PostgreSQL warehouse
- JSON outputs for dashboard datasets
- QA feedback tables for human review

