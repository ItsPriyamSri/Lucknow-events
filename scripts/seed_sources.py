#!/usr/bin/env python
"""Seed the database with initial scraping sources (requirements §17).

Usage (inside the api container):
    python scripts/seed_sources.py
"""
from __future__ import annotations

import asyncio
import sys
import os

# Ensure the backend package root is on the path regardless of where this is called from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from api.core.database import SessionLocal
from api.models.source import Source


log = structlog.get_logger(__name__)

INITIAL_SOURCES = [
    {
        "name": "Meetup Lucknow (Tech)",
        "platform": "meetup",
        "base_url": "https://www.meetup.com/find/",
        "crawl_strategy": "graphql_or_playwright",
        "trust_score": 0.72,
        "enabled": False,
        "crawl_interval_hours": 6,
        "config_json": {
            "find_url": "https://www.meetup.com/find/?source=EVENTS&location=in--Lucknow--India&distance=twentyFiveMiles",
            "max_items": 12,
        },
    },
    {
        "name": "GDG Lucknow",
        "platform": "gdg",
        "base_url": "https://gdg.community.dev/gdg-lucknow/",
        "crawl_strategy": "json_feed",
        "trust_score": 0.95,
        "enabled": True,
        "crawl_interval_hours": 6,
        "config_json": {"chapter_slug": "gdg-lucknow"},
    },
    {
        "name": "GDSC IIIT Lucknow",
        "platform": "gdg",
        "base_url": "https://gdg.community.dev/gdsc-iiit-lucknow/",
        "crawl_strategy": "json_feed",
        "trust_score": 0.90,
        "enabled": True,
        "crawl_interval_hours": 6,
        "config_json": {"chapter_slug": "gdsc-iiit-lucknow"},
    },
    {
        "name": "Commudle Lucknow Events",
        "platform": "commudle",
        "base_url": "https://www.commudle.com/events",
        "crawl_strategy": "playwright",
        "trust_score": 0.80,
        "enabled": False,
        "crawl_interval_hours": 6,
        "config_json": {"city_filter": "lucknow", "max_items": 10},
    },
    {
        "name": "Devfolio India Hackathons",
        "platform": "devfolio",
        "base_url": "https://devfolio.co/hackathons",
        "crawl_strategy": "playwright",
        "trust_score": 0.75,
        "enabled": False,
        "crawl_interval_hours": 6,
        "config_json": {"location_filter": "lucknow", "max_items": 10},
    },
    {
        "name": "Unstop Lucknow",
        "platform": "unstop",
        "base_url": "https://unstop.com/competitions",
        "crawl_strategy": "api_then_playwright",
        "trust_score": 0.70,
        "enabled": True,
        "crawl_interval_hours": 6,
        "config_json": {"location": "Lucknow", "max_items": 20},
    },
]


async def seed() -> None:
    async with SessionLocal() as db:
        for src_data in INITIAL_SOURCES:
            existing = (
                await db.execute(
                    select(Source).where(Source.name == src_data["name"])
                )
            ).scalar_one_or_none()

            if existing:
                log.info("seed.already_exists", name=src_data["name"])
                continue

            import uuid
            src = Source(id=str(uuid.uuid4()), **src_data)
            db.add(src)
            log.info("seed.inserted", name=src_data["name"])

        await db.commit()
    log.info("seed.done", total=len(INITIAL_SOURCES))


if __name__ == "__main__":
    asyncio.run(seed())
