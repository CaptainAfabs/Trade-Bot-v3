"""Financial Modeling Prep — stable API. Free tier: ~250 calls/day, US-only.

Used as the PRIMARY data source (yfinance is fallback because Yahoo aggressively
rate-limits scrapers). Endpoints follow the stable schema: query-param style
`?symbol=AAPL`, never the legacy `/api/v3/.../{ticker}` path.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.config import settings

from .cache import DiskCache

_cache = DiskCache("fmp")
BASE = "https://financialmodelingprep.com/stable"
TIMEOUT = 15.0


def _get(path_with_query: str, ttl_seconds: int = 3600) -> Any:
    if not settings.fmp_api_key:
        return None
    key = path_with_query.replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "_")
    cached = _cache.get(key, ttl_seconds)
    if cached is not None:
        return cached
    sep = "&" if "?" in path_with_query else "?"
    url = f"{BASE}/{path_with_query}{sep}apikey={settings.fmp_api_key}"
    try:
        r = httpx.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
    except Exception:
        return None
    _cache.set(key, data)
    return data


def _first(rows: list | None) -> dict | None:
    return rows[0] if isinstance(rows, list) and rows else None


def get_profile(ticker: str) -> dict | None:
    return _first(_get(f"profile?symbol={ticker}", ttl_seconds=86400))


def get_quote(ticker: str) -> dict | None:
    return _first(_get(f"quote?symbol={ticker}", ttl_seconds=900))


def get_ratios_ttm(ticker: str) -> dict | None:
    return _first(_get(f"ratios-ttm?symbol={ticker}", ttl_seconds=86400))


def get_key_metrics_ttm(ticker: str) -> dict | None:
    return _first(_get(f"key-metrics-ttm?symbol={ticker}", ttl_seconds=86400))


def get_income_statement(ticker: str, limit: int = 5) -> list | None:
    return _get(f"income-statement?symbol={ticker}&limit={limit}", ttl_seconds=86400)


def get_latest_income(ticker: str) -> dict | None:
    return _first(get_income_statement(ticker, limit=1))


def get_balance_sheet(ticker: str, limit: int = 5) -> list | None:
    return _get(f"balance-sheet-statement?symbol={ticker}&limit={limit}", ttl_seconds=86400)


def get_latest_balance_sheet(ticker: str) -> dict | None:
    return _first(get_balance_sheet(ticker, limit=1))


def get_cash_flow(ticker: str, limit: int = 5) -> list | None:
    return _get(f"cash-flow-statement?symbol={ticker}&limit={limit}", ttl_seconds=86400)


def get_latest_cash_flow(ticker: str) -> dict | None:
    return _first(get_cash_flow(ticker, limit=1))


def get_analyst_estimates(ticker: str, period: str = "annual") -> list | None:
    return _get(f"analyst-estimates?symbol={ticker}&period={period}")


def get_financial_growth(ticker: str) -> dict | None:
    return _first(_get(f"financial-growth?symbol={ticker}", ttl_seconds=86400))


def get_price_target_consensus(ticker: str) -> dict | None:
    return _first(_get(f"price-target-consensus?symbol={ticker}", ttl_seconds=3600))


def get_grades_consensus(ticker: str) -> dict | None:
    return _first(_get(f"grades-consensus?symbol={ticker}", ttl_seconds=3600))


def get_grades(ticker: str) -> list | None:
    """Analyst rating changes (upgrades/downgrades)."""
    return _get(f"grades?symbol={ticker}", ttl_seconds=3600)


def get_insider_trading(ticker: str, limit: int = 20) -> list | None:
    return _get(f"insider-trading/latest?symbol={ticker}&limit={limit}", ttl_seconds=3600)


def get_history_eod(ticker: str, light: bool = True) -> list | None:
    """Daily OHLCV. light=True returns just price/volume (cheaper)."""
    variant = "light" if light else "full"
    return _get(f"historical-price-eod/{variant}?symbol={ticker}", ttl_seconds=3600)
