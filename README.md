# AI Labor & Curriculum Observatory

Enterprise platform for controlled labor acquisition, semantic skill intelligence, company intelligence, curriculum gaps, recommendations and observatory dashboards.

## What ships now

- Acquisition workers with Playwright and controlled crawling.
- PostgreSQL warehouse with probabilistic scoring.
- Semantic extraction, clustering, embeddings and QA feedback.
- Company, role, career and forecasting intelligence.
- Observatory metrics and dashboard datasets for Vercel consumption.
- Public FastAPI layer in `api/` for deployment.

## Quick start

```powershell
copy .env.example .env.local
docker compose up --build
```

The public API runs in the `api` service from `api.main:app`.

## Main docs

- [Architecture](docs/ARCHITECTURE.md)
- [Deployment](docs/DEPLOYMENT.md)
- [API Reference](docs/API_REFERENCE.md)

