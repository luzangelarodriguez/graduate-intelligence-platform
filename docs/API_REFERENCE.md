# API Reference

Base URL: `/`

## System

- `GET /health`
- `GET /readiness`
- `GET /liveness`
- `GET /metrics`

## Observatory

- `GET /recommendations`
- `GET /emerging-skills`
- `GET /semantic-roles`
- `GET /curriculum-gaps`
- `GET /company-intelligence`
- `GET /career-paths`
- `GET /market-forecast`

## Search

- `GET /semantic-search?q=...&entity_type=job|company|skill|role`

## Pagination

Most list endpoints support `limit` and `offset`.

