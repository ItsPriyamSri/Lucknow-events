from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ─── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Sources ──────────────────────────────────────────────────────────────────

class SourceOut(BaseModel):
    id: str
    name: str
    platform: str | None
    base_url: str
    enabled: bool
    status: str  # active | whitelisted | blacklisted
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
    status: str | None = None  # active | whitelisted | blacklisted
    trust_score: float | None = None
    crawl_interval_hours: int | None = None
    config_json: dict[str, Any] | None = None


class SourceStatusUpdate(BaseModel):
    status: str  # active | whitelisted | blacklisted


# ─── Events (admin) ───────────────────────────────────────────────────────────

class AdminEventOut(BaseModel):
    id: str
    slug: str
    title: str
    start_at: datetime
    end_at: datetime | None
    mode: str | None
    event_type: str | None
    city: str | None
    locality: str | None
    venue: str | None = Field(default=None, validation_alias="venue_name")
    community_name: str | None
    canonical_url: str
    registration_url: str | None
    is_featured: bool
    is_cancelled: bool
    is_free: bool
    published_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdminEventListResponse(BaseModel):
    items: list[AdminEventOut]
    page: int
    limit: int
    total: int


class EventUpdate(BaseModel):
    """Admin-only full event update."""
    title: str | None = None
    description: str | None = None
    short_description: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    timezone: str | None = None
    city: str | None = None
    locality: str | None = None
    venue_name: str | None = None
    address: str | None = None
    mode: str | None = None
    event_type: str | None = None
    organizer_name: str | None = None
    community_name: str | None = None
    canonical_url: str | None = None
    registration_url: str | None = None
    poster_url: str | None = None
    price_type: str | None = None
    is_free: bool | None = None
    is_featured: bool | None = None
    is_cancelled: bool | None = None


# ─── Moderation ───────────────────────────────────────────────────────────────

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
    sources_blacklisted: int = 0


# ─── Crawl runs ───────────────────────────────────────────────────────────────

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


# ─── Discovery ────────────────────────────────────────────────────────────────

class DiscoveryRunRequest(BaseModel):
    custom_queries: list[str] | None = None


class DiscoveryRunResult(BaseModel):
    task_id: str
    status: str = "queued"
    message: str = "Discovery agent has been triggered"
