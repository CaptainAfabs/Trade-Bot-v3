"""Buy-and-hold backtest. Pure pandas, no vectorbt. Pulls history from FMP."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.data import fmp_adapter


@dataclass
class BacktestResult:
    ticker: str
    start_date: str
    end_date: str
    start_price: float
    end_price: float
    total_return_pct: float
    annualized_return_pct: float
    max_drawdown_pct: float
    annualized_vol_pct: float
    sharpe: float | None


def run(ticker: str, years: float = 5) -> BacktestResult | None:
    hist = fmp_adapter.get_history_eod(ticker, light=False)
    if not hist or not isinstance(hist, list):
        return None

    df = pd.DataFrame(hist)
    if df.empty:
        return None
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    cutoff = df["date"].max() - pd.DateOffset(years=int(years))
    df = df[df["date"] >= cutoff].reset_index(drop=True)
    if len(df) < 50:
        return None

    closes = df["close"].astype(float)
    start_price = float(closes.iloc[0])
    end_price   = float(closes.iloc[-1])
    days = (df["date"].iloc[-1] - df["date"].iloc[0]).days or 1
    yrs = days / 365.25

    total_return = (end_price / start_price) - 1
    annualized = (end_price / start_price) ** (1 / yrs) - 1 if start_price and yrs > 0 else 0

    rolling_max = closes.cummax()
    drawdown = (closes - rolling_max) / rolling_max
    max_dd = float(drawdown.min())

    daily_returns = closes.pct_change().dropna()
    vol = float(daily_returns.std() * (252 ** 0.5))
    sharpe = float(daily_returns.mean() * 252 / (daily_returns.std() * (252 ** 0.5))) if daily_returns.std() else None

    return BacktestResult(
        ticker=ticker.upper(),
        start_date=df["date"].iloc[0].strftime("%Y-%m-%d"),
        end_date=df["date"].iloc[-1].strftime("%Y-%m-%d"),
        start_price=start_price,
        end_price=end_price,
        total_return_pct=total_return * 100,
        annualized_return_pct=annualized * 100,
        max_drawdown_pct=max_dd * 100,
        annualized_vol_pct=vol * 100,
        sharpe=sharpe,
    )
