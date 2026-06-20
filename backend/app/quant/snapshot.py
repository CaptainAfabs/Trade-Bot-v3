"""Build a StockSnapshot: 30+ quant data points across 8 pillars, normalized.

PRIMARY source = FMP stable (paid-style data on a free key, ~250 calls/day).
FALLBACK source = yfinance (when FMP rate-limits or lacks a field).
NEWS source = Alpha Vantage NEWS_SENTIMENT.

Each item may be None — Day 3 scoring code handles missing data per pillar.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
from pydantic import BaseModel

from app.data import alphavantage_adapter, fmp_adapter, yfinance_adapter

from . import indicators


class Pillar(BaseModel):
    name: str
    items: dict[str, Optional[float]]


class StockSnapshot(BaseModel):
    ticker: str
    company_name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    exchange: Optional[str] = None
    market_cap_usd: Optional[float] = None
    current_price: Optional[float] = None
    currency: str = "USD"
    pillars: list[Pillar]
    sources: list[str]
    as_of: str


def _num(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if pd.isna(f):
        return None
    return f


def _pct(v) -> float | None:
    """Many APIs return ratios as decimals (0.25 = 25%). Normalize to percent.
    If |v| >= 1 we assume it's already a percent."""
    f = _num(v)
    if f is None:
        return None
    return f * 100 if abs(f) < 1 and f != 0 else f


def build_snapshot(ticker: str) -> StockSnapshot:
    ticker = ticker.upper().strip()
    sources: list[str] = []

    profile = fmp_adapter.get_profile(ticker)
    quote   = fmp_adapter.get_quote(ticker)
    ratios  = fmp_adapter.get_ratios_ttm(ticker)
    metrics = fmp_adapter.get_key_metrics_ttm(ticker)
    growth_fmp = fmp_adapter.get_financial_growth(ticker)
    targets    = fmp_adapter.get_price_target_consensus(ticker)
    grades     = fmp_adapter.get_grades_consensus(ticker)
    balance    = fmp_adapter.get_latest_balance_sheet(ticker)
    cashflow   = fmp_adapter.get_latest_cash_flow(ticker)
    income     = fmp_adapter.get_latest_income(ticker)
    if any([profile, quote, ratios, metrics, growth_fmp, targets, grades, balance, cashflow, income]):
        sources.append("fmp")

    # yfinance fallback for fields FMP doesn't expose cleanly (insider %, short %)
    yf_info = yfinance_adapter.get_info(ticker)
    if yf_info:
        sources.append("yfinance")

    # Helper to read a key from any of several dicts, first non-null wins
    def pick(*candidates):
        for c in candidates:
            if c is not None:
                return c
        return None

    company_name = pick(
        profile.get("companyName") if profile else None,
        quote.get("name") if quote else None,
        yf_info.get("longName"),
        yf_info.get("shortName"),
    )
    sector   = pick(profile.get("sector") if profile else None, yf_info.get("sector"))
    industry = pick(profile.get("industry") if profile else None, yf_info.get("industry"))
    exchange = pick(profile.get("exchange") if profile else None, profile.get("exchangeFullName") if profile else None, yf_info.get("exchange"))
    market_cap = _num(pick(profile.get("marketCap") if profile else None, quote.get("marketCap") if quote else None, yf_info.get("marketCap")))
    current_price = _num(pick(quote.get("price") if quote else None, profile.get("price") if profile else None, yf_info.get("currentPrice"), yf_info.get("regularMarketPrice")))
    currency = pick(profile.get("currency") if profile else None, yf_info.get("currency")) or "USD"

    valuation = Pillar(name="valuation", items={
        "pe_ttm":             _num(pick(ratios.get("priceToEarningsRatioTTM") if ratios else None, yf_info.get("trailingPE"))),
        "pe_forward":         _num(yf_info.get("forwardPE")),
        "peg":                _num(pick(ratios.get("priceToEarningsGrowthRatioTTM") if ratios else None, yf_info.get("trailingPegRatio") or yf_info.get("pegRatio"))),
        "pb":                 _num(pick(ratios.get("priceToBookRatioTTM") if ratios else None, yf_info.get("priceToBook"))),
        "ps":                 _num(pick(ratios.get("priceToSalesRatioTTM") if ratios else None, yf_info.get("priceToSalesTrailing12Months"))),
        "ev_ebitda":          _num(pick(metrics.get("evToEBITDATTM") if metrics else None, yf_info.get("enterpriseToEbitda"))),
        "ev_revenue":         _num(pick(metrics.get("evToSalesTTM") if metrics else None, yf_info.get("enterpriseToRevenue"))),
        "p_fcf":              _num(pick(ratios.get("priceToFreeCashFlowRatioTTM") if ratios else None)),
        "dividend_yield_pct": _pct(pick(ratios.get("dividendYieldTTM") if ratios else None, yf_info.get("dividendYield"))),
        "payout_ratio":       _num(pick(ratios.get("dividendPayoutRatioTTM") if ratios else None, yf_info.get("payoutRatio"))),
    })

    profitability = Pillar(name="profitability", items={
        "roe_pct":              _pct(pick(metrics.get("returnOnEquityTTM") if metrics else None, yf_info.get("returnOnEquity"))),
        "roa_pct":              _pct(pick(metrics.get("returnOnAssetsTTM") if metrics else None, yf_info.get("returnOnAssets"))),
        "roic_pct":             _pct(pick(metrics.get("returnOnInvestedCapitalTTM") if metrics else None, ratios.get("returnOnCapitalEmployedTTM") if ratios else None)),
        "gross_margin_pct":     _pct(pick(ratios.get("grossProfitMarginTTM") if ratios else None, yf_info.get("grossMargins"))),
        "operating_margin_pct": _pct(pick(ratios.get("operatingProfitMarginTTM") if ratios else None, yf_info.get("operatingMargins"))),
        "net_margin_pct":       _pct(pick(ratios.get("netProfitMarginTTM") if ratios else None, yf_info.get("profitMargins"))),
    })

    growth = Pillar(name="growth", items={
        "revenue_growth_yoy_pct":   _pct(pick(growth_fmp.get("revenueGrowth") if growth_fmp else None, yf_info.get("revenueGrowth"))),
        "net_income_growth_yoy_pct": _pct(growth_fmp.get("netIncomeGrowth") if growth_fmp else None),
        "eps_growth_yoy_pct":       _pct(pick(growth_fmp.get("epsgrowth") if growth_fmp else None, yf_info.get("earningsGrowth"))),
        "fcf_growth_yoy_pct":       _pct(growth_fmp.get("freeCashFlowGrowth") if growth_fmp else None),
        "revenue_growth_3y_pct":    _pct(growth_fmp.get("threeYRevenueGrowthPerShare") if growth_fmp else None),
        "revenue_growth_5y_pct":    _pct(growth_fmp.get("fiveYRevenueGrowthPerShare") if growth_fmp else None),
        "revenue_per_share":        _num(pick(metrics.get("revenuePerShareTTM") if metrics else None, yf_info.get("revenuePerShare"))),
    })

    # Derive cash, debt, FCF from FMP statements (yfinance fallback if missing)
    total_cash = _num(pick(
        balance.get("cashAndShortTermInvestments") if balance else None,
        balance.get("cashAndCashEquivalents") if balance else None,
        yf_info.get("totalCash"),
    ))
    short_debt = _num(balance.get("shortTermDebt") if balance else None) or 0
    long_debt  = _num(balance.get("longTermDebt") if balance else None) or 0
    total_debt = _num(pick(
        (short_debt + long_debt) if balance else None,
        yf_info.get("totalDebt"),
    ))
    operating_cf = _num(pick(
        cashflow.get("netCashProvidedByOperatingActivities") if cashflow else None,
        yf_info.get("operatingCashflow"),
    ))
    capex = _num(cashflow.get("investmentsInPropertyPlantAndEquipment") if cashflow else None)
    free_cf = _num(pick(
        (operating_cf - abs(capex)) if (operating_cf is not None and capex is not None) else None,
        cashflow.get("freeCashFlow") if cashflow else None,
        yf_info.get("freeCashflow"),
    ))

    health = Pillar(name="health", items={
        "debt_to_equity":         _num(pick(ratios.get("debtToEquityRatioTTM") if ratios else None, yf_info.get("debtToEquity"))),
        "current_ratio":          _num(pick(ratios.get("currentRatioTTM") if ratios else None, yf_info.get("currentRatio"))),
        "quick_ratio":            _num(pick(ratios.get("quickRatioTTM") if ratios else None, yf_info.get("quickRatio"))),
        "interest_coverage":      _num(ratios.get("interestCoverageRatioTTM") if ratios else None),
        "net_debt_to_ebitda":     _num(metrics.get("netDebtToEBITDATTM") if metrics else None),
        "total_cash_usd":         total_cash,
        "total_debt_usd":         total_debt,
        "free_cashflow_usd":      free_cf,
        "operating_cashflow_usd": operating_cf,
    })

    # Build technicals from FMP historical EOD (preferred) or yfinance
    closes: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    fmp_hist = fmp_adapter.get_history_eod(ticker, light=False)
    if isinstance(fmp_hist, list) and fmp_hist:
        # FMP returns newest first; reverse for chronological
        rows = list(reversed(fmp_hist))
        closes = [r["close"] for r in rows if r.get("close") is not None]
        highs  = [r["high"]  for r in rows if r.get("high")  is not None]
        lows   = [r["low"]   for r in rows if r.get("low")   is not None]
    else:
        yf_hist = yfinance_adapter.get_history(ticker, period="1y")
        closes = [c for c in (yf_hist.get("Close") or []) if c is not None]
        highs  = [c for c in (yf_hist.get("High")  or []) if c is not None]
        lows   = [c for c in (yf_hist.get("Low")   or []) if c is not None]

    tech_items: dict[str, float | None] = {"beta": _num(pick(profile.get("beta") if profile else None, yf_info.get("beta")))}
    if len(closes) >= 30:
        close_s = pd.Series(closes)
        high_s  = pd.Series(highs) if highs else close_s
        low_s   = pd.Series(lows) if lows else close_s
        tech_items.update({
            "rsi_14":               indicators.rsi(close_s, 14),
            "sma_50":               indicators.sma(close_s, 50),
            "sma_200":              indicators.sma(close_s, 200),
            "atr_14":               indicators.atr(high_s, low_s, close_s, 14),
            "annualized_vol_pct":   indicators.annualized_volatility(close_s),
        })
        m = indicators.macd(close_s)
        tech_items.update({"macd": m["macd"], "macd_signal": m["signal"], "macd_histogram": m["histogram"]})
        tech_items.update(indicators.price_vs_52w(close_s))
    technicals = Pillar(name="technicals", items=tech_items)

    market_signal = Pillar(name="market_signal", items={
        "short_pct_of_float":   _pct(yf_info.get("shortPercentOfFloat")),
        "short_ratio_days":     _num(yf_info.get("shortRatio")),
        "insider_pct":          _pct(yf_info.get("heldPercentInsiders")),
        "institutional_pct":    _pct(yf_info.get("heldPercentInstitutions")),
        "shares_outstanding_m": _num((yf_info.get("sharesOutstanding") or 0) / 1_000_000) if yf_info.get("sharesOutstanding") else None,
    })

    # Analyst ratings: derive a 1-5 score where 1=Strong Buy, 5=Strong Sell (Yahoo convention)
    rec_mean: float | None = _num(yf_info.get("recommendationMean"))
    num_analysts: float | None = _num(yf_info.get("numberOfAnalystOpinions"))
    if grades and rec_mean is None:
        sb = _num(grades.get("strongBuy")) or 0
        b  = _num(grades.get("buy")) or 0
        h  = _num(grades.get("hold")) or 0
        s  = _num(grades.get("sell")) or 0
        ss = _num(grades.get("strongSell")) or 0
        total = sb + b + h + s + ss
        if total:
            rec_mean = (1 * sb + 2 * b + 3 * h + 4 * s + 5 * ss) / total
            num_analysts = total

    analyst_items = {
        "target_mean":         _num(pick(targets.get("targetConsensus") if targets else None, yf_info.get("targetMeanPrice"))),
        "target_median":       _num(targets.get("targetMedian") if targets else None),
        "target_high":         _num(pick(targets.get("targetHigh") if targets else None, yf_info.get("targetHighPrice"))),
        "target_low":          _num(pick(targets.get("targetLow") if targets else None, yf_info.get("targetLowPrice"))),
        "num_analysts":        num_analysts,
        "recommendation_mean": rec_mean,
    }
    if analyst_items["target_mean"] and current_price:
        analyst_items["target_upside_pct"] = (analyst_items["target_mean"] - current_price) / current_price * 100
    analyst = Pillar(name="analyst", items=analyst_items)

    av_news = alphavantage_adapter.get_news_sentiment([ticker], limit=10)
    news_items: dict[str, float | None] = {"recent_sentiment_score": None, "recent_relevance_score": None, "news_count": None}
    if av_news and av_news.get("feed"):
        sources.append("alphavantage")
        feed = av_news["feed"]
        rel_scores, sent_scores = [], []
        for item in feed:
            for ts in item.get("ticker_sentiment", []):
                if ts.get("ticker") == ticker:
                    try:
                        rel_scores.append(float(ts.get("relevance_score", 0)))
                        sent_scores.append(float(ts.get("ticker_sentiment_score", 0)))
                    except (TypeError, ValueError):
                        pass
        if sent_scores:
            news_items["recent_sentiment_score"] = sum(sent_scores) / len(sent_scores)
            news_items["recent_relevance_score"] = sum(rel_scores) / len(rel_scores)
            news_items["news_count"] = float(len(feed))
    news = Pillar(name="news", items=news_items)

    return StockSnapshot(
        ticker=ticker,
        company_name=company_name,
        sector=sector,
        industry=industry,
        exchange=exchange,
        market_cap_usd=market_cap,
        current_price=current_price,
        currency=currency,
        pillars=[valuation, profitability, growth, health, technicals, market_signal, analyst, news],
        sources=sources or ["none"],
        as_of=pd.Timestamp.utcnow().isoformat(),
    )
