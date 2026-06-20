import asyncio
import json
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.data import edgar_adapter
from app.db.database import connect
from app.reasoning import claude

router = APIRouter()


class Investor(BaseModel):
    slug: str
    display_name: str
    kind: str
    cik: str | None
    bio: str | None
    photo_url: str | None
    description: str | None


class Holding(BaseModel):
    name: str
    cusip: str | None = None
    cls: str | None = None
    value_usd: float | None = None
    shares: int | None = None
    pct_portfolio: float | None = None


class InvestorDetail(Investor):
    period: str | None = None
    filed: str | None = None
    accession: str | None = None
    total_value_usd: float | None = None
    top_holdings: list[Holding] = []
    holdings_note: str | None = None


def _row_to_investor(row) -> Investor:
    return Investor(
        slug=row["slug"],
        display_name=row["display_name"],
        kind=row["kind"],
        cik=row["cik"],
        bio=row["bio"],
        photo_url=row["photo_url"],
        description=row["description"],
    )


@router.get("", response_model=list[Investor])
async def list_investors():
    async with connect() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute("SELECT * FROM investors ORDER BY kind, display_name")
        rows = await cur.fetchall()
        return [_row_to_investor(r) for r in rows]


@router.get("/{slug}", response_model=InvestorDetail)
async def get_investor(slug: str, limit: int = 25):
    async with connect() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute("SELECT * FROM investors WHERE slug = ?", (slug,))
        row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Investor not found")
        base = _row_to_investor(row)

    if base.kind == "politician":
        return InvestorDetail(
            **base.model_dump(),
            holdings_note="STOCK Act PTR ingestion is wired for v1.1. Until then, "
                          "check capitoltrades.com or quiverquant.com.",
        )
    if not base.cik:
        return InvestorDetail(**base.model_dump(), holdings_note="No CIK on file; cannot pull 13F.")

    try:
        data = await asyncio.to_thread(edgar_adapter.fetch_13f_holdings, base.cik)
    except Exception as e:
        return InvestorDetail(**base.model_dump(), holdings_note=f"EDGAR fetch error: {e!s}")

    if not data:
        return InvestorDetail(**base.model_dump(), holdings_note="No recent 13F-HR found on EDGAR.")

    top = []
    for h in data["holdings"][:limit]:
        top.append(Holding(
            name=h.get("name", ""),
            cusip=h.get("cusip"),
            cls=h.get("class"),
            value_usd=h.get("value_usd"),
            shares=h.get("shares"),
            pct_portfolio=h.get("pct_portfolio"),
        ))

    # Persist into investor_holdings for offline querying
    async with connect() as db:
        for h in data["holdings"][:200]:
            try:
                await db.execute(
                    """INSERT OR REPLACE INTO investor_holdings
                       (investor, period, ticker, shares, value_usd, pct_portfolio, filed_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (slug, data["period"], h.get("name", ""), h.get("shares"), h.get("value_usd"),
                     h.get("pct_portfolio"), data["filed"]),
                )
            except Exception:
                pass
        await db.commit()

    return InvestorDetail(
        **base.model_dump(),
        period=data["period"],
        filed=data["filed"],
        accession=data["accession"],
        total_value_usd=data["total_value_usd"],
        top_holdings=top,
    )


class AddInvestorRequest(BaseModel):
    query: str  # e.g. "Bill Gross" or "Stanley Druckenmiller"


_AI_INVESTOR_SYSTEM = """You research famous public-markets investors and return a single JSON object with these exact fields:

{
  "slug": "kebab-case-name-firm",       # e.g. "buffett-berkshire"
  "display_name": "Full Name",
  "kind": "fund" | "individual" | "politician",
  "cik": "0001067983" or null,          # 10-digit padded SEC CIK if they file 13F
  "description": "One-sentence style label, no longer than 110 chars.",
  "bio": "Two to four sentences. Concrete and specific, no fluff.",
  "photo_url": "https://upload.wikimedia.org/... or null"
}

Return ONLY the JSON object — no preamble, no markdown fences."""


@router.post("", response_model=Investor, status_code=201)
async def ai_add_investor(payload: AddInvestorRequest):
    """Ask Claude to research an investor and add them to the roster."""
    q = payload.query.strip()
    if not q or len(q) > 120:
        raise HTTPException(400, "Provide a 1-120 char query, e.g. 'Bill Gross'")

    try:
        data = await asyncio.to_thread(
            claude.complete_json,
            _AI_INVESTOR_SYSTEM,
            f"Add this investor to the roster: {q}",
        )
    except Exception as e:
        raise HTTPException(502, f"Claude failed: {e!s}")

    slug = re.sub(r"[^a-z0-9-]", "", (data.get("slug") or "").lower())
    if not slug:
        raise HTTPException(502, "Claude returned no slug")
    kind = data.get("kind") if data.get("kind") in ("fund", "individual", "politician") else "individual"

    async with connect() as db:
        try:
            await db.execute(
                """INSERT INTO investors (slug, display_name, kind, cik, bio, photo_url, description, is_seeded)
                   VALUES (?,?,?,?,?,?,?,0)""",
                (slug, data.get("display_name") or q, kind, data.get("cik"),
                 data.get("bio"), data.get("photo_url"), data.get("description")),
            )
            await db.commit()
        except Exception as e:
            raise HTTPException(409, f"Investor already exists or insert failed: {e!s}")

    return Investor(
        slug=slug,
        display_name=data.get("display_name") or q,
        kind=kind,
        cik=data.get("cik"),
        bio=data.get("bio"),
        photo_url=data.get("photo_url"),
        description=data.get("description"),
    )
