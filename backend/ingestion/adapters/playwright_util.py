"""Shared Playwright / HTTP helpers for listing adapters."""

from __future__ import annotations

import random
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import structlog

log = structlog.get_logger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 LucknowTechEventsBot/0.1"
)


async def playwright_render(url: str) -> str:
    """Render page and return visible text; falls back to httpx HTML on failure."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = await browser.new_context(user_agent=USER_AGENT)
            page = await ctx.new_page()
            import asyncio

            await asyncio.sleep(random.uniform(0.5, 2.0))
            try:
                await page.goto(url, wait_until="networkidle", timeout=45_000)
            except Exception:
                await page.goto(url, timeout=45_000)
            content = await page.inner_text("body")
            await browser.close()
            return content
    except Exception as exc:
        log.warning("playwright.render_failed", url=url, error=str(exc))
        return await httpx_fetch_text(url)


async def httpx_fetch_text(url: str) -> str:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=45, headers={"User-Agent": USER_AGENT}) as client:
            r = await client.get(url, follow_redirects=True)
            return r.text
    except Exception as exc:
        log.error("httpx.fetch_failed", url=url, error=str(exc))
        return ""


def unique_hrefs(html: str, base: str, pattern: re.Pattern[str], *, limit: int) -> list[str]:
    """Extract absolute unique URLs matching regex from HTML."""
    seen: set[str] = set()
    out: list[str] = []
    for m in pattern.finditer(html):
        href = m.group(1)
        if href.startswith("//"):
            href = "https:" + href
        abs_url = href if href.startswith("http") else urljoin(base, href)
        if abs_url in seen:
            continue
        seen.add(abs_url)
        out.append(abs_url)
        if len(out) >= limit:
            break
    return out


def same_domain(url: str, allowed: str) -> bool:
    return urlparse(url).netloc.endswith(allowed)
