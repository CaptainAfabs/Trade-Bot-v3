"""Finimpulse (api.finimpulse.com) — paid, usage-based.

Used as the PRIMARY source for price, valuation ratios, and a year of OHLCV.
FMP remains primary for the deep statements (margins, growth, FCF, balance
sheet, analyst targets) since Finimpulse's surface doesn't expose them
through the endpoints we tried.

Auth: Authorization: Bearer <key>
Body: POST with JSON {"symbol": "AAPL", ...optional select_identifiers}
Response: {task_id, status_code (20000=OK), status_message, cost, data, result}
Rate limit: 2000 req/min default, X-RateLimit-Remaining header.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.config import settings

from .cache import DiskCache

_cache = DiskCache("finimpulse")
BASE = "https://api.finimpulse.com/v1"
TIMEOUT = 20.0


def _post(path: str, body: dict, ttl_seconds: int) -> Any:
    if not settings.finimpulse_api_key:
        return None
    key = f"{path}_{body.get('symbol', '')}_{ttl_seconds}"
    cached = _cache.get(key, ttl_seconds)
    if cached is not None:
        return cached
    try:
        r = httpx.post(
            f"{BASE}{path}",
            json=body,
            headers={
                "Authorization": f"Bearer {settings.finimpulse_api_key}",
                "Content-Type": "application/json",
            },
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return None
        j = r.json()
    except Exception:
        return None
    if j.get("status_code") != 20000:
        return None
    payload = j.get("result")
    if payload is None:
        return None
    _cache.set(key, payload)
    return payload


def get_summary_lite(ticker: str) -> dict | None:
    """Cheapest single call — price, P/E, P/B, P/S, dividend, beta, 52w, sector."""
    return _post("/summary-lite", {"symbol": ticker.upper()}, ttl_seconds=900)


def get_profile(ticker: str) -> dict | None:
    """Full profile: long business summary, address, executives."""
    return _post("/profile", {"symbol": ticker.upper()}, ttl_seconds=86400)


def get_histories(ticker: str) -> list[dict] | None:
    """Daily OHLCV, last ~100 trading days. Cost: $0.00045."""
    result = _post("/histories", {"symbol": ticker.upper(), "interval": "1d"}, ttl_seconds=3600)
    if not result:
        return None
    items = result.get("items") if isinstance(result, dict) else None
    if not items:
        return None
    return items
