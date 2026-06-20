from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.portfolio.service import add_holding, delete_holding, portfolio_summary

router = APIRouter()


class HoldingIn(BaseModel):
    profile_id: int
    ticker: str = Field(min_length=1, max_length=10)
    shares: float = Field(gt=0)
    avg_cost_usd: float = Field(gt=0)
    notes: str | None = None


@router.get("/{profile_id}")
async def get_portfolio(profile_id: int):
    return await portfolio_summary(profile_id)


@router.post("", status_code=201)
async def post_holding(payload: HoldingIn):
    hid = await add_holding(
        payload.profile_id, payload.ticker, payload.shares,
        payload.avg_cost_usd, payload.notes,
    )
    return {"id": hid}


@router.delete("/{holding_id}", status_code=204)
async def remove_holding(holding_id: int):
    await delete_holding(holding_id)
