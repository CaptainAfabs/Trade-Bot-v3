"""Alpha Vantage — free tier 25 calls/day. Reserved primarily for NEWS_SENTIMENT
on Day 5. Fundamentals come from yfinance/FMP since AV's daily budget is tiny."""
from __future__ import annotations

from typing import Any

import httpx

from app.config import settings

from .cache import DiskCache

_cache = DiskCache("alphavantage")
BASE = "https://www.alphavantage.co/query"
TIMEOUT = 15.0


def _get(params: dict[str, str], ttl_seconds: int = 3600) -> Any:
    if not settings.alphavantage_api_key:
        return None
    params = {**params, "apikey": settings.alphavantage_api_key}
    key = "_".join(f"{k}-{v}" for k, v in sorted(params.items()) if k != "apikey")
    cached = _cache.get(key, ttl_seconds)
    if cached is not None:
        return cached
    try:
        r = httpx.get(BASE, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        # AV signals rate limit / errors via "Note" or "Information" keys
        if "Note" in data or "Information" in data:
            return None
    except Exception:
        return None
    _cache.set(key, data)
    return data


def get_news_sentiment(tickers: list[str], limit: int = 50) -> dict | None:
    if not tickers:
        return None
    return _get(
        {"function": "NEWS_SENTIMENT", "tickers": ",".join(tickers), "limit": str(limit)},
        ttl_seconds=900,
    )


def get_overview(ticker: str) -> dict | None:
    return _get({"function": "OVERVIEW", "symbol": ticker}, ttl_seconds=86400)
