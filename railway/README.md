# Railway deployment layout

This folder documents the split used for Railway services:

- `backend/` - FastAPI public API
- `acquisition-worker/` - controlled crawling and warehouse writes
- `intelligence-worker/` - observatory, ML, forecasting and recommendation jobs
- `postgres/` - managed PostgreSQL service reference

