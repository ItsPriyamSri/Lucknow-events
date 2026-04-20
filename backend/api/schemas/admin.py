from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ─── Auth ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Sources ─────────────────────────────────────────────────────────────────

class SourceOut(BaseModel):
    id: str
    name: str
    platform: str | None
    base_url: str
    enabled: bool
    crawl_strategy: str | None
    trust_score: float
    crawl_interval_hours: int
    last_crawled_at: datetime | None
    last_success_at: datetime | None
    consecutive_failures: int
    created_at: datetime

    class Config:
        from_attributes = True


class SourceCreate(BaseModel):
    name: str
    platform: str | None = None
    base_url: str
    crawl_strategy: str | None = None
    trust_score: float = 0.7
    crawl_interval_hours: int = 6
    config_json: dict[str, Any] = Field(default_factory=dict)


class SourcePatch(BaseModel):
    enabled: bool | None = None
    trust_score: float | None = None
    crawl_interval_hours: int | None = None
    config_json: dict[str, Any] | None = None


# ─── Moderation ──────────────────────────────────────────────────────────────

class ModerationItemOut(BaseModel):
    id: str
    entity_type: str | None
    entity_id: str | None
    reason: str | None
    severity: str | None
    status: str
    ai_verdict: dict[str, Any] | None
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Stats ────────────────────────────────────────────────────────────────────

class StatsOut(BaseModel):
    events_total: int
    events_this_week: int
    pending_moderation: int
    sources_active: int


# ─── Crawl runs ──────────────────────────────────────────────────────────────

class CrawlRunOut(BaseModel):
    id: str
    source_id: str
    started_at: datetime
    finished_at: datetime | None
    status: str | None
    events_found: int
    events_new: int
    events_published: int
    error_summary: str | None
    created_at: datetime

    class Config:
        from_attributes = True
