import asyncio
import re

from fastapi import APIRouter, HTTPException

from app.quant.snapshot import StockSnapshot, build_snapshot

router = APIRouter()

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


@router.get("/{ticker}", response_model=StockSnapshot)
async def get_stock(ticker: str):
    t = ticker.upper().strip()
    if not _TICKER_RE.match(t):
        raise HTTPException(400, "Invalid ticker")
    try:
        return await asyncio.to_thread(build_snapshot, t)
    except Exception as e:
        raise HTTPException(502, f"Failed to fetch {t}: {e!s}")
