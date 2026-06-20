import asyncio

from fastapi import APIRouter, HTTPException, Query

from app.backtest.buy_hold import run

router = APIRouter()


@router.get("/{ticker}")
async def backtest(ticker: str, years: float = Query(default=5, ge=1, le=20)):
    try:
        result = await asyncio.to_thread(run, ticker.upper(), years)
    except Exception as e:
        raise HTTPException(502, f"Backtest failed: {e!s}")
    if not result:
        raise HTTPException(404, "Insufficient price history")
    return result.__dict__
