from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/{ticker}")
async def get_stock(ticker: str):
    """Stub. Day 2 wires in real data adapters."""
    ticker = ticker.upper()
    if not ticker.isalpha() or len(ticker) > 6:
        raise HTTPException(400, "Invalid ticker")
    return {
        "ticker": ticker,
        "note": "Stub response — Day 2 will return real quant data.",
    }
