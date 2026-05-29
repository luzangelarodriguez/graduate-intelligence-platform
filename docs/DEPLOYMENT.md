# Deployment Guide

## Local

1. Copy `.env.example` to `.env.local`.
2. Fill `DATABASE_URL` or the `DB_*` variables.
3. Run:

```powershell
docker compose up --build
```

## Railway

Deploy the root `Dockerfile` with `railway.json`.

Services:

- `api` - FastAPI observatory API
- `acquisition-worker` - controlled crawling
- `intelligence-worker` - observatory and ML jobs
- `postgres` - managed PostgreSQL

## Vercel

Frontend contracts are exported to `frontend_contracts/openapi.json` and `frontend_contracts/contracts.json`.

