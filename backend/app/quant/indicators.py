"""Technical indicators computed from price series. Pure pandas — no ta-lib."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _safe_float(v) -> float | None:
    try:
        f = float(v)
        if pd.isna(f) or np.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def sma(close: pd.Series, period: int) -> float | None:
    if len(close) < period:
        return None
    return _safe_float(close.tail(period).mean())


def rsi(close: pd.Series, period: int = 14) -> float | None:
    if len(close) < period + 1:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    return _safe_float(rsi_series.iloc[-1])


def macd(close: pd.Series) -> dict[str, float | None]:
    if len(close) < 26:
        return {"macd": None, "signal": None, "histogram": None}
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9, adjust=False).mean()
    return {
        "macd": _safe_float(macd_line.iloc[-1]),
        "signal": _safe_float(signal.iloc[-1]),
        "histogram": _safe_float(macd_line.iloc[-1] - signal.iloc[-1]),
    }


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float | None:
    if len(close) < period + 1:
        return None
    prev_close = close.shift()
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return _safe_float(tr.rolling(period).mean().iloc[-1])


def annualized_volatility(close: pd.Series) -> float | None:
    if len(close) < 30:
        return None
    daily_returns = close.pct_change().dropna()
    return _safe_float(daily_returns.std() * (252 ** 0.5) * 100)


def price_vs_52w(close: pd.Series) -> dict[str, float | None]:
    if len(close) < 5:
        return {"high_52w": None, "low_52w": None, "pct_off_high": None, "pct_off_low": None}
    window = close.tail(252) if len(close) >= 252 else close
    high_52w = float(window.max())
    low_52w = float(window.min())
    current = float(close.iloc[-1])
    return {
        "high_52w": high_52w,
        "low_52w": low_52w,
        "pct_off_high": _safe_float((current - high_52w) / high_52w * 100) if high_52w else None,
        "pct_off_low": _safe_float((current - low_52w) / low_52w * 100) if low_52w else None,
    }
