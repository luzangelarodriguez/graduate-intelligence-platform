# Graduate Intelligence & Employability Platform

SaaS MVP for higher education teams that need to measure graduate employability, detect career changes, compare market demand, and simulate curriculum impact.

## What this repo includes

- `backend/` FastAPI API with:
  - graduate capture
  - event detection
  - market analysis
  - curriculum simulator
  - dashboard summary endpoints
- `frontend/` React + Vite dashboard with:
  - executive KPIs
  - graduate intake
  - market radar
  - impact simulator
- `backend/app/engine.py` domain engine with:
  - skill normalization
  - program-market matching
  - employability alignment score
  - skill gap index
  - micro-survey generation

## Current architecture

- Backend: FastAPI
- Frontend: React
- Target database: PostgreSQL
- Vector layer: pgvector or any vector DB
- Current demo store: in-memory repository seeded with representative data

The engine is isolated so it can be swapped from the demo store to PostgreSQL without changing the UI contract.

## Main API endpoints

- `GET /api/bootstrap`
- `GET /api/dashboard/summary`
- `GET /api/programs`
- `GET /api/graduates`
- `POST /api/graduates`
- `PATCH /api/graduates/{id}`
- `POST /api/graduates/{id}/scan`
- `GET /api/graduates/{id}/analysis`
- `GET /api/events`
- `GET /api/market/jobs`
- `POST /api/match/analyze`
- `POST /api/simulate`
- `POST /api/surveys/micro`

## Run locally

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL=http://127.0.0.1:8010` if the frontend runs on another host or port.

## Next production step

Replace the in-memory store with a PostgreSQL repository and add a vector index for semantic matching between:

- graduate profiles
- job postings
- curriculum learning outcomes

That will let the platform scale from demo to institutional rollout.
