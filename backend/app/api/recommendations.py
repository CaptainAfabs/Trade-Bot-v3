"""Dynamic recommendations.

Old behavior: score a hardcoded 15-stock universe → return top N.
New behavior: Claude generates ~40 candidate tickers tailored to the user's risk
+ timeline + exclusions, we score them all via Finimpulse + FMP, and return up
to N that clear the user's threshold (plus a small bucket of near-misses).

Caching:
  - Candidate list per (risk, timeline, exclusions): 24h
  - Final scored response per profile: 6h
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.data.cache import DiskCache
from app.db.database import connect
from app.profiles.models import Profile
from app.quant.scoring import score_snapshot
from app.quant.snapshot import build_snapshot
from app.reasoning import claude

router = APIRouter()

_cache = DiskCache("recommendations")
_candidate_cache = DiskCache("candidates")

CANDIDATE_COUNT = 40   # ask Claude for this many
MIN_NEAR_MISS = 3      # how many below-threshold fillers we'll show


class Pick(BaseModel):
    ticker: str
    name: str | None
    sector: str | None
    price: float | None
    score: float | None
    grade: str
    clears_threshold: bool
    drivers: list[str]
    sources: list[str] = []


class RecsResponse(BaseModel):
    profile_id: int
    risk: str
    timeline: str
    support_required: float
    picks: list[Pick]
    n_cleared: int
    n_near_misses: int
    universe_size: int
    cached: bool


_SCREENER_SYSTEM = """You are a stock screener for a personal AI investment assistant.

Generate a list of US-listed stocks (NYSE / NASDAQ only, no OTC, no ADRs of micro-caps, no penny stocks under $5) tailored to the investor profile below.

Match the candidates to the profile:
- low risk + long/generational: durable franchises, quality compounders, dividend payers, healthy balance sheets, wide moats
- low risk + medium/short: defensives, consumer staples, utilities, established cash-flow machines
- medium risk: balanced mix of growth + value across sectors
- high risk + long: secular growth, semiconductors, AI, biotech leaders, fintech
- high risk + short: high-momentum names, recent breakouts, volatile growth stocks
- avoid any sectors the user excluded

Return ONLY a JSON array of ticker strings. No commentary, no fences. Example: ["AAPL", "MSFT", "NVDA"]"""


def _user_prompt(profile: Profile, count: int) -> str:
    excl = ", ".join(profile.sectors_exclude) if profile.sectors_exclude else "(none)"
    prefer = ", ".join(profile.sectors_prefer) if profile.sectors_prefer else "(none)"
    return (
        f"Generate {count} candidate tickers for this profile:\n"
        f"- risk: {profile.risk}\n"
        f"- timeline: {profile.timeline}\n"
        f"- capital: ${profile.capital_usd:,.0f}\n"
        f"- excluded sectors: {excl}\n"
        f"- preferred sectors: {prefer}\n"
        f"- dividend_only: {profile.dividend_only}\n"
        f"- esg_only: {profile.esg_only}\n"
        f"- min_market_cap: ${profile.min_market_cap_usd:,.0f}\n\n"
        f"Mix sectors unless excluded. Return JSON array of {count} tickers."
    )


_TICKER_OK = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


def _generate_candidates_sync(profile: Profile, count: int) -> list[str]:
    """Sync Claude call — must run in threadpool."""
    text = claude.complete(
        system=_SCREENER_SYSTEM,
        user=_user_prompt(profile, count),
        model=None,                  # bulk model — fast + cheap
        max_tokens=1500,
    )
    # Extract JSON array
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON array in Claude response: {text[:200]}")
    arr = json.loads(text[start:end + 1])
    out: list[str] = []
    seen: set[str] = set()
    for t in arr:
        if not isinstance(t, str):
            continue
        t = t.upper().strip()
        if not _TICKER_OK.match(t) or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out[:count]


def _candidates_cache_key(profile: Profile) -> str:
    excl = ",".join(sorted(profile.sectors_exclude))
    return f"cand_{profile.risk}_{profile.timeline}_div{int(profile.dividend_only)}_esg{int(profile.esg_only)}_x{excl}"


async def get_candidates(profile: Profile) -> list[str]:
    key = _candidates_cache_key(profile)
    cached = _candidate_cache.get(key, ttl_seconds=24 * 3600)
    if cached:
        return cached
    try:
        tickers = await asyncio.to_thread(_generate_candidates_sync, profile, CANDIDATE_COUNT)
    except Exception:
        tickers = []
    if not tickers:
        # Fallback to a stable seed list so the UI still shows *something*
        tickers = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA",
            "JPM", "V", "BRK-B", "JNJ", "UNH", "WMT", "KO", "XOM", "CAT",
        ]
    _candidate_cache.set(key, tickers)
    return tickers


def _score_one(ticker: str, risk, timeline) -> dict[str, Any] | None:
    try:
        snap = build_snapshot(ticker)
    except Exception:
        return None
    score = score_snapshot(snap, risk=risk, timeline=timeline)
    if score.composite is None or not snap.company_name or snap.current_price is None:
        return None
    return {
        "ticker":            snap.ticker,
        "name":              snap.company_name,
        "sector":            snap.sector,
        "price":             snap.current_price,
        "score":             score.composite,
        "grade":             score.grade,
        "clears_threshold":  score.composite >= score.support_required,
        "drivers":           score.drivers_positive,
        "support_required":  score.support_required,
        "sources":           snap.sources,
    }


@router.get("", response_model=RecsResponse)
async def get_recommendations(
    profile_id: int = Query(...),
    limit: int = Query(default=15, ge=1, le=30),
    force_refresh: bool = Query(default=False),
):
    async with connect() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Profile not found")
    profile = Profile(
        id=row["id"], user_id=row["user_id"], name=row["name"],
        risk=row["risk"], timeline=row["timeline"],
        capital_usd=row["capital_usd"], min_market_cap_usd=row["min_market_cap_usd"],
        max_position_pct=row["max_position_pct"], max_sector_pct=row["max_sector_pct"],
        sectors_exclude=json.loads(row["sectors_exclude"] or "[]"),
        sectors_prefer=json.loads(row["sectors_prefer"] or "[]"),
        dividend_only=bool(row["dividend_only"]), esg_only=bool(row["esg_only"]),
        follow_investors=json.loads(row["follow_investors"] or "[]"),
        is_default=bool(row["is_default"]),
    )

    cache_key = f"recs_{profile_id}_{profile.risk}_{profile.timeline}_{limit}"
    if not force_refresh:
        cached = _cache.get(cache_key, ttl_seconds=6 * 3600)
        if cached:
            return RecsResponse(
                profile_id=profile_id,
                risk=profile.risk,
                timeline=profile.timeline,
                support_required=cached["support_required"],
                picks=[Pick(**p) for p in cached["picks"]],
                n_cleared=cached["n_cleared"],
                n_near_misses=cached["n_near_misses"],
                universe_size=cached["universe_size"],
                cached=True,
            )

    # 1. Claude generates candidate tickers
    candidates = await get_candidates(profile)

    # 2. Score them all in parallel (FMP/Finimpulse cached per ticker)
    results = await asyncio.gather(
        *[asyncio.to_thread(_score_one, t, profile.risk, profile.timeline) for t in candidates],
        return_exceptions=False,
    )
    scored = [r for r in results if r]

    # 3. Honor sector exclusions (defense in depth — Claude usually handles)
    if profile.sectors_exclude:
        excluded = {s.lower() for s in profile.sectors_exclude}
        scored = [s for s in scored if (s.get("sector") or "").lower() not in excluded]

    # 4. Split into clearing vs near-misses
    cleared    = [s for s in scored if s["clears_threshold"]]
    near_miss  = [s for s in scored if not s["clears_threshold"]]
    cleared.sort(key=lambda x: x["score"] or 0, reverse=True)
    near_miss.sort(key=lambda x: x["score"] or 0, reverse=True)

    # 5. Compose: up to `limit` cleared, then top N near-misses to pad if short
    picks = cleared[:limit]
    if len(picks) < limit:
        picks.extend(near_miss[: limit - len(picks)])
    elif len(picks) == limit:
        picks.extend(near_miss[:MIN_NEAR_MISS])

    support = scored[0]["support_required"] if scored else (
        {"low": 55, "medium": 65, "high": 75}[profile.risk]
    )

    payload = {
        "support_required": support,
        "picks":            picks,
        "n_cleared":        len(cleared),
        "n_near_misses":    len(near_miss),
        "universe_size":    len(candidates),
    }
    _cache.set(cache_key, payload)

    return RecsResponse(
        profile_id=profile_id,
        risk=profile.risk,
        timeline=profile.timeline,
        support_required=support,
        picks=[Pick(**p) for p in payload["picks"]],
        n_cleared=payload["n_cleared"],
        n_near_misses=payload["n_near_misses"],
        universe_size=payload["universe_size"],
        cached=False,
    )
