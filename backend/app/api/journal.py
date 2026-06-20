"""Trade journal. Log decisions, rate suggestions, monthly review via Claude."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db.database import connect
from app.reasoning import claude

router = APIRouter()


class JournalEntry(BaseModel):
    profile_id: int
    ticker: str = Field(min_length=1, max_length=10)
    action: str  # buy | sell | hold | watch
    thesis: str | None = None
    bot_score: float | None = None
    user_rating: int | None = Field(default=None, ge=1, le=5)


class JournalRecord(JournalEntry):
    id: int
    decided_at: str
    outcome_pct: float | None = None
    reviewed_at: str | None = None


@router.post("", status_code=201, response_model=JournalRecord)
async def add_entry(e: JournalEntry):
    if e.action not in ("buy", "sell", "hold", "watch"):
        raise HTTPException(400, "action must be buy|sell|hold|watch")
    async with connect() as db:
        cur = await db.execute(
            """INSERT INTO trade_journal (profile_id, ticker, action, thesis, bot_score, user_rating)
               VALUES (?,?,?,?,?,?)""",
            (e.profile_id, e.ticker.upper(), e.action, e.thesis, e.bot_score, e.user_rating),
        )
        await db.commit()
        new_id = cur.lastrowid
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute("SELECT * FROM trade_journal WHERE id = ?", (new_id,))
        row = await cur.fetchone()
    return JournalRecord(**{k: row[k] for k in row if k != "user_id"})


@router.get("/{profile_id}", response_model=list[JournalRecord])
async def list_entries(profile_id: int, limit: int = 100):
    async with connect() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute(
            "SELECT * FROM trade_journal WHERE profile_id = ? ORDER BY decided_at DESC LIMIT ?",
            (profile_id, limit),
        )
        rows = await cur.fetchall()
    return [JournalRecord(**{k: r[k] for k in r}) for r in rows]


@router.post("/{profile_id}/rate/{entry_id}")
async def rate_entry(profile_id: int, entry_id: int, rating: int):
    if not 1 <= rating <= 5:
        raise HTTPException(400, "rating must be 1-5")
    async with connect() as db:
        await db.execute(
            "UPDATE trade_journal SET user_rating = ? WHERE id = ? AND profile_id = ?",
            (rating, entry_id, profile_id),
        )
        await db.commit()
    return {"ok": True}


_REVIEW_SYSTEM = """You are reviewing a personal investor's recent trade-decision journal.
Output a concise monthly review with these sections (markdown):

## Wins
## Misses
## Patterns to lean into
## Patterns to break
## One thing to try next month

Be specific — cite tickers and decisions. Two-to-four sentences per section."""


@router.get("/{profile_id}/monthly-review")
async def monthly_review(profile_id: int):
    async with connect() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute(
            """SELECT ticker, action, thesis, bot_score, user_rating, outcome_pct, decided_at
               FROM trade_journal
               WHERE profile_id = ? AND decided_at >= datetime('now', '-30 days')
               ORDER BY decided_at DESC""",
            (profile_id,),
        )
        rows = await cur.fetchall()
    if not rows:
        return {"review": "No journal entries in the last 30 days — start logging your decisions to enable review."}
    user_text = "Trades over the last 30 days:\n\n" + json.dumps([dict(r) for r in rows], indent=2, default=str)
    try:
        review = await asyncio.to_thread(claude.complete, _REVIEW_SYSTEM, user_text, None, 1500)
    except Exception as e:
        raise HTTPException(502, f"Claude error: {e!s}")
    return {"review": review, "n_entries": len(rows)}
