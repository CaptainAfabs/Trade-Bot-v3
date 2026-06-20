import asyncio
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.profiles.models import Risk, Timeline
from app.quant.scoring import CompositeScore, score_snapshot
from app.quant.snapshot import StockSnapshot, build_snapshot

router = APIRouter()

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


def _validate(ticker: str) -> str:
    t = ticker.upper().strip()
    if not _TICKER_RE.match(t):
        raise HTTPException(400, "Invalid ticker")
    return t


class ScoredStock(BaseModel):
    snapshot: StockSnapshot
    score: CompositeScore


@router.get("/{ticker}", response_model=StockSnapshot)
async def get_stock(ticker: str):
    t = _validate(ticker)
    try:
        return await asyncio.to_thread(build_snapshot, t)
    except Exception as e:
        raise HTTPException(502, f"Failed to fetch {t}: {e!s}")


@router.get("/{ticker}/score", response_model=ScoredStock)
async def get_stock_scored(
    ticker: str,
    risk: Risk = "medium",
    timeline: Timeline = "long",
):
    t = _validate(ticker)
    try:
        snap = await asyncio.to_thread(build_snapshot, t)
    except Exception as e:
        raise HTTPException(502, f"Failed to fetch {t}: {e!s}")
    score = score_snapshot(snap, risk=risk, timeline=timeline)
    return ScoredStock(snapshot=snap, score=score)
