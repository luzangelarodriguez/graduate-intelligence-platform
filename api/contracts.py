from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: datetime
    checks: dict[str, bool] = Field(default_factory=dict)
    observatory_freshness: dict[str, Any] = Field(default_factory=dict)


class PaginatedResponse(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0
    limit: int = 0
    offset: int = 0
    filters: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    entity_type: str
    count: int
    limit: int
    items: list[dict[str, Any]] = Field(default_factory=list)

