"""Portfolio service: CRUD over holdings + live valuation via current prices.

Live prices come from FMP quote endpoint (cached). All values returned in USD.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.data import fmp_adapter
from app.db.database import connect


@dataclass
class HoldingRow:
    id: int
    ticker: str
    shares: float
    avg_cost_usd: float
    current_price_usd: float | None
    market_value_usd: float | None
    cost_basis_usd: float
    pnl_usd: float | None
    pnl_pct: float | None
    weight_pct: float | None
    sector: str | None
    notes: str | None


async def add_holding(profile_id: int, ticker: str, shares: float, avg_cost_usd: float, notes: str | None = None) -> int:
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO holdings (profile_id, ticker, shares, avg_cost_usd, notes) VALUES (?,?,?,?,?)",
            (profile_id, ticker.upper(), shares, avg_cost_usd, notes),
        )
        await db.commit()
        return cur.lastrowid


async def delete_holding(holding_id: int) -> None:
    async with connect() as db:
        await db.execute("DELETE FROM holdings WHERE id = ?", (holding_id,))
        await db.commit()


async def list_holdings(profile_id: int) -> list[HoldingRow]:
    async with connect() as db:
        cur = await db.execute(
            "SELECT id, ticker, shares, avg_cost_usd, notes FROM holdings WHERE profile_id = ? ORDER BY ticker",
            (profile_id,),
        )
        rows = await cur.fetchall()

    enriched: list[HoldingRow] = []
    for rid, ticker, shares, avg_cost, notes in rows:
        quote = fmp_adapter.get_quote(ticker)
        profile_data = fmp_adapter.get_profile(ticker)
        price = float(quote["price"]) if quote and quote.get("price") is not None else None
        market_value = price * shares if price else None
        cost_basis = avg_cost * shares
        pnl = market_value - cost_basis if market_value is not None else None
        pnl_pct = (pnl / cost_basis * 100) if pnl is not None and cost_basis else None
        enriched.append(HoldingRow(
            id=rid, ticker=ticker, shares=shares, avg_cost_usd=avg_cost,
            current_price_usd=price, market_value_usd=market_value,
            cost_basis_usd=cost_basis, pnl_usd=pnl, pnl_pct=pnl_pct,
            weight_pct=None,  # filled in below
            sector=profile_data.get("sector") if profile_data else None,
            notes=notes,
        ))

    total_value = sum(h.market_value_usd or 0 for h in enriched)
    if total_value:
        for h in enriched:
            if h.market_value_usd is not None:
                h.weight_pct = h.market_value_usd / total_value * 100
    return enriched


async def portfolio_summary(profile_id: int) -> dict:
    rows = await list_holdings(profile_id)
    total_value  = sum(h.market_value_usd or 0 for h in rows)
    total_cost   = sum(h.cost_basis_usd or 0 for h in rows)
    total_pnl    = total_value - total_cost if total_cost else 0
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0
    by_sector: dict[str, float] = {}
    for h in rows:
        key = h.sector or "Unknown"
        by_sector[key] = by_sector.get(key, 0) + (h.market_value_usd or 0)
    sector_pcts = {
        k: round(v / total_value * 100, 2) if total_value else 0
        for k, v in sorted(by_sector.items(), key=lambda kv: -kv[1])
    }
    return {
        "n_positions":       len(rows),
        "total_value_usd":   total_value,
        "total_cost_usd":    total_cost,
        "total_pnl_usd":     total_pnl,
        "total_pnl_pct":     total_pnl_pct,
        "by_sector_pct":     sector_pcts,
        "holdings":          [h.__dict__ for h in rows],
    }
