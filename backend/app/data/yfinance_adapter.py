"""Yahoo Finance via yfinance. Fallback source for fields FMP doesn't expose
(insider %, short %, institutional ownership). Yahoo rate-limits scrapers
aggressively, so we use curl_cffi to impersonate a real Chrome session.

Returns are normalized to JSON-serializable dicts so the cache can persist them.
"""
from __future__ import annotations

from typing import Any

import pandas as pd
import yfinance as yf
from curl_cffi import requests as curl_requests

from .cache import DiskCache

_cache = DiskCache("yfinance")
_session = curl_requests.Session(impersonate="chrome")


def _df_to_jsonable(df: pd.DataFrame | None) -> dict:
    if df is None or df.empty:
        return {}
    out = {}
    for col in df.columns:
        out[str(col)] = {str(idx): (None if pd.isna(v) else float(v)) for idx, v in df[col].items()}
    return out


def get_info(ticker: str) -> dict[str, Any]:
    key = f"info_{ticker}"
    cached = _cache.get(key, ttl_seconds=3600)
    if cached is not None:
        return cached
    try:
        info = yf.Ticker(ticker, session=_session).info or {}
    except Exception:
        info = {}
    safe = {k: v for k, v in info.items() if isinstance(v, (str, int, float, bool, type(None)))}
    _cache.set(key, safe)
    return safe


def get_history(ticker: str, period: str = "1y") -> dict:
    key = f"history_{ticker}_{period}"
    cached = _cache.get(key, ttl_seconds=1800)
    if cached is not None:
        return cached
    try:
        df = yf.Ticker(ticker, session=_session).history(period=period, auto_adjust=False)
    except Exception:
        df = pd.DataFrame()
    if df.empty:
        out = {"index": [], "Open": [], "High": [], "Low": [], "Close": [], "Volume": []}
    else:
        out = {
            "index": [str(i) for i in df.index],
            "Open":  [float(v) if not pd.isna(v) else None for v in df["Open"]],
            "High":  [float(v) if not pd.isna(v) else None for v in df["High"]],
            "Low":   [float(v) if not pd.isna(v) else None for v in df["Low"]],
            "Close": [float(v) if not pd.isna(v) else None for v in df["Close"]],
            "Volume":[float(v) if not pd.isna(v) else None for v in df["Volume"]],
        }
    _cache.set(key, out)
    return out


def get_financials(ticker: str) -> dict:
    key = f"fin_{ticker}"
    cached = _cache.get(key, ttl_seconds=86400)
    if cached is not None:
        return cached
    try:
        t = yf.Ticker(ticker, session=_session)
        out = {
            "income_annual":    _df_to_jsonable(getattr(t, "income_stmt", None)),
            "income_quarterly": _df_to_jsonable(getattr(t, "quarterly_income_stmt", None)),
            "balance_annual":   _df_to_jsonable(getattr(t, "balance_sheet", None)),
            "cashflow_annual":  _df_to_jsonable(getattr(t, "cashflow", None)),
        }
    except Exception:
        out = {}
    _cache.set(key, out)
    return out
