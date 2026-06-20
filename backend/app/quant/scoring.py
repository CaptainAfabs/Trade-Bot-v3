"""Composite scoring. Two stages:

1. Each pillar emits a 0-100 sub-score (average of available metric sub-scores).
2. Pillars are weighted by (risk, timeline) into a composite 0-100.

Thresholds are absolute (not sector-relative) for v1. Day 7 can swap in
sector-percentile rankings if needed. Missing metrics are skipped, not
penalized — only available data influences the score.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.profiles.models import Risk, Timeline

from .snapshot import StockSnapshot

Direction = Literal["higher", "lower"]


def _band_score(value: float | None, bands: list[tuple[float, float]], direction: Direction = "higher") -> float | None:
    """Map value to 0-100 via threshold bands. Bands are auto-sorted ascending by threshold.

    higher: pick score for the highest threshold that value >= threshold.
    lower:  pick score for the lowest threshold that value <= threshold.
    """
    if value is None:
        return None
    bands_sorted = sorted(bands, key=lambda x: x[0])
    if direction == "lower":
        for threshold, score in bands_sorted:
            if value <= threshold:
                return float(score)
        return float(bands_sorted[-1][1])
    best = bands_sorted[0][1]
    for threshold, score in bands_sorted:
        if value >= threshold:
            best = score
    return float(best)


def _avg(scores: list[float | None]) -> float | None:
    vals = [s for s in scores if s is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def score_valuation(items: dict) -> float | None:
    return _avg([
        _band_score(items.get("pe_ttm"),    [(100, 10), (60, 25), (40, 40), (30, 55), (20, 70), (15, 80), (10, 90)], "lower"),
        _band_score(items.get("peg"),       [(3, 20), (2, 40), (1.5, 60), (1, 75), (0.5, 90)], "lower"),
        _band_score(items.get("pb"),        [(10, 20), (5, 40), (3, 60), (1.5, 75), (1, 90)], "lower"),
        _band_score(items.get("ps"),        [(20, 20), (10, 40), (5, 60), (3, 75), (1, 90)], "lower"),
        _band_score(items.get("ev_ebitda"), [(30, 25), (25, 45), (18, 65), (12, 80), (8, 90)], "lower"),
        _band_score(items.get("p_fcf"),     [(50, 20), (30, 40), (20, 60), (12, 80), (8, 90)], "lower"),
    ])


def score_profitability(items: dict) -> float | None:
    return _avg([
        _band_score(items.get("roe_pct"),              [(0, 10), (8, 40), (15, 65), (25, 80), (40, 90)]),
        _band_score(items.get("roic_pct"),             [(0, 10), (6, 35), (12, 60), (20, 80), (30, 90)]),
        _band_score(items.get("roa_pct"),              [(0, 10), (5, 40), (10, 65), (15, 80), (25, 90)]),
        _band_score(items.get("gross_margin_pct"),     [(10, 25), (20, 40), (30, 55), (50, 70), (70, 85)]),
        _band_score(items.get("operating_margin_pct"), [(0, 10), (5, 35), (15, 55), (25, 70), (40, 85)]),
        _band_score(items.get("net_margin_pct"),       [(0, 10), (5, 35), (10, 55), (20, 70), (30, 85)]),
    ])


def score_growth(items: dict) -> float | None:
    return _avg([
        _band_score(items.get("revenue_growth_yoy_pct"),     [(-10, 10), (0, 35), (5, 55), (15, 70), (25, 85), (40, 95)]),
        _band_score(items.get("net_income_growth_yoy_pct"),  [(-20, 10), (0, 40), (10, 60), (25, 75), (50, 90)]),
        _band_score(items.get("eps_growth_yoy_pct"),         [(-20, 10), (0, 40), (10, 60), (25, 75), (50, 90)]),
        _band_score(items.get("fcf_growth_yoy_pct"),         [(-20, 15), (0, 45), (10, 65), (25, 80), (50, 90)]),
    ])


def score_health(items: dict) -> float | None:
    return _avg([
        _band_score(items.get("debt_to_equity"),   [(3, 15), (2, 35), (1, 55), (0.5, 75), (0.2, 90)], "lower"),
        _band_score(items.get("current_ratio"),    [(2, 85), (1.5, 75), (1, 60), (0.7, 40), (0.5, 20)]),
        _band_score(items.get("quick_ratio"),      [(1.5, 85), (1, 70), (0.7, 50), (0.5, 35), (0.3, 15)]),
        _band_score(items.get("interest_coverage"),[(10, 90), (5, 75), (2, 60), (1, 40), (0, 15)]),
        _band_score(items.get("net_debt_to_ebitda"),[(5, 15), (3, 40), (1, 65), (0, 80), (-1, 90)], "lower"),
    ])


def score_technicals(items: dict) -> float | None:
    sub = []
    rsi = items.get("rsi_14")
    if rsi is not None:
        if 40 <= rsi <= 60:   sub.append(75)
        elif 30 <= rsi < 40:  sub.append(70)
        elif 60 < rsi <= 70:  sub.append(70)
        elif 25 <= rsi < 30:  sub.append(55)
        elif 70 < rsi <= 80:  sub.append(45)
        else:                 sub.append(25)
    macd_hist = items.get("macd_histogram")
    if macd_hist is not None:
        sub.append(75 if macd_hist > 0 else 40)
    pct_off_high = items.get("pct_off_high")
    if pct_off_high is not None:
        if pct_off_high >= -5:    sub.append(80)
        elif pct_off_high >= -15: sub.append(65)
        elif pct_off_high >= -30: sub.append(50)
        else:                     sub.append(35)
    vol = items.get("annualized_vol_pct")
    if vol is not None:
        if vol < 20:   sub.append(75)
        elif vol < 40: sub.append(60)
        elif vol < 60: sub.append(45)
        else:          sub.append(30)
    return _avg(sub) if sub else None


def score_analyst(items: dict, current_price: float | None) -> float | None:
    sub = []
    rec = items.get("recommendation_mean")
    if rec is not None:
        if rec <= 2:   sub.append(85)
        elif rec <= 2.5: sub.append(75)
        elif rec <= 3: sub.append(55)
        elif rec <= 4: sub.append(35)
        else:          sub.append(20)
    upside = items.get("target_upside_pct")
    if upside is not None:
        if upside >= 30:   sub.append(85)
        elif upside >= 15: sub.append(75)
        elif upside >= 5:  sub.append(60)
        elif upside >= -5: sub.append(45)
        else:              sub.append(20)
    return _avg(sub) if sub else None


def score_news(items: dict) -> float | None:
    s = items.get("recent_sentiment_score")
    if s is None:
        return None
    if s >= 0.3:    return 80.0
    if s >= 0.1:    return 65.0
    if s >= -0.1:   return 50.0
    if s >= -0.3:   return 35.0
    return 20.0


# Pillar weights per (risk, timeline). Sum to 100. Missing pillar score => weight redistributed.
WEIGHTS: dict[tuple[Risk, Timeline], dict[str, int]] = {
    ("low",    "generational"): {"valuation": 15, "profitability": 25, "growth": 5,  "health": 30, "technicals": 5,  "analyst": 10, "news": 10},
    ("low",    "long"):         {"valuation": 18, "profitability": 22, "growth": 8,  "health": 27, "technicals": 5,  "analyst": 10, "news": 10},
    ("low",    "medium"):       {"valuation": 20, "profitability": 18, "growth": 10, "health": 22, "technicals": 8,  "analyst": 12, "news": 10},
    ("low",    "short"):        {"valuation": 18, "profitability": 15, "growth": 12, "health": 18, "technicals": 12, "analyst": 13, "news": 12},

    ("medium", "generational"): {"valuation": 18, "profitability": 22, "growth": 13, "health": 17, "technicals": 5,  "analyst": 12, "news": 13},
    ("medium", "long"):         {"valuation": 18, "profitability": 18, "growth": 18, "health": 12, "technicals": 8,  "analyst": 13, "news": 13},
    ("medium", "medium"):       {"valuation": 15, "profitability": 15, "growth": 18, "health": 10, "technicals": 12, "analyst": 15, "news": 15},
    ("medium", "short"):        {"valuation": 10, "profitability": 10, "growth": 15, "health": 5,  "technicals": 25, "analyst": 15, "news": 20},

    ("high",   "generational"): {"valuation": 12, "profitability": 18, "growth": 25, "health": 10, "technicals": 10, "analyst": 12, "news": 13},
    ("high",   "long"):         {"valuation": 10, "profitability": 15, "growth": 28, "health": 7,  "technicals": 12, "analyst": 13, "news": 15},
    ("high",   "medium"):       {"valuation": 8,  "profitability": 10, "growth": 25, "health": 5,  "technicals": 20, "analyst": 15, "news": 17},
    ("high",   "short"):        {"valuation": 5,  "profitability": 5,  "growth": 20, "health": 5,  "technicals": 30, "analyst": 15, "news": 20},
}


class PillarScore(BaseModel):
    name: str
    score: float | None
    weight: int


class CompositeScore(BaseModel):
    composite: float | None
    grade: str
    risk: Risk
    timeline: Timeline
    pillars: list[PillarScore]
    drivers_positive: list[str]
    drivers_negative: list[str]
    support_required: float
    note: str | None = None


def _grade(score: float | None) -> str:
    if score is None: return "N/A"
    if score >= 80:   return "A"
    if score >= 70:   return "B"
    if score >= 60:   return "C"
    if score >= 50:   return "D"
    return "F"


def _required_support(risk: Risk) -> float:
    """Risker stocks need a higher composite to clear. Per user direction:
    'the riskier the stock, the more support it needs to be a viable purchase'."""
    return {"low": 55, "medium": 65, "high": 75}[risk]


def score_snapshot(snapshot: StockSnapshot, risk: Risk, timeline: Timeline) -> CompositeScore:
    by_name = {p.name: p.items for p in snapshot.pillars}

    pillar_scores: dict[str, float | None] = {
        "valuation":     score_valuation(by_name.get("valuation", {})),
        "profitability": score_profitability(by_name.get("profitability", {})),
        "growth":        score_growth(by_name.get("growth", {})),
        "health":        score_health(by_name.get("health", {})),
        "technicals":    score_technicals(by_name.get("technicals", {})),
        "analyst":       score_analyst(by_name.get("analyst", {}), snapshot.current_price),
        "news":          score_news(by_name.get("news", {})),
    }
    weights = WEIGHTS[(risk, timeline)]

    # Composite: weighted mean over PRESENT pillars (renormalize weights)
    present = [(n, pillar_scores[n], weights.get(n, 0)) for n in weights if pillar_scores.get(n) is not None]
    total_w = sum(w for _, _, w in present)
    composite = sum(s * w for _, s, w in present) / total_w if total_w else None

    pillars_out = [PillarScore(name=n, score=pillar_scores.get(n), weight=w) for n, w in weights.items()]

    # Drivers: top 2 highest- and lowest-scoring pillars (only those that materially weigh)
    ranked = sorted(
        [(n, s, weights.get(n, 0)) for n, s in pillar_scores.items() if s is not None and weights.get(n, 0) > 0],
        key=lambda x: x[1],
        reverse=True,
    )
    drivers_positive = [f"{n} {s:.0f}" for n, s, _ in ranked[:2]]
    drivers_negative = [f"{n} {s:.0f}" for n, s, _ in ranked[-2:] if s < 60]

    required = _required_support(risk)
    note = None
    if composite is None:
        note = "Insufficient data."
    elif composite < required:
        note = f"Below the {required:.0f} support threshold for {risk} risk — not a viable buy."
    else:
        note = f"Clears the {required:.0f} support threshold for {risk} risk."

    return CompositeScore(
        composite=round(composite, 1) if composite is not None else None,
        grade=_grade(composite),
        risk=risk,
        timeline=timeline,
        pillars=pillars_out,
        drivers_positive=drivers_positive,
        drivers_negative=drivers_negative,
        support_required=required,
        note=note,
    )
