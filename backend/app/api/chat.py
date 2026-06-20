import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.database import connect
from app.profiles.models import Profile
from app.reasoning.chat import respond

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    profile_id: int
    message: str


class ChatResponse(BaseModel):
    reply: str
    stop_reason: str


async def _load_profile(profile_id: int) -> Profile:
    async with connect() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
        row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Profile not found")
    return Profile(
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


async def _load_history(profile_id: int, limit: int = 20) -> list[dict[str, Any]]:
    async with connect() as db:
        cur = await db.execute(
            "SELECT role, content FROM chat_messages WHERE profile_id = ? ORDER BY id DESC LIMIT ?",
            (profile_id, limit),
        )
        rows = await cur.fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


async def _save(profile_id: int, role: str, content: str) -> None:
    async with connect() as db:
        await db.execute(
            "INSERT INTO chat_messages (profile_id, role, content) VALUES (?,?,?)",
            (profile_id, role, content),
        )
        await db.commit()


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    profile = await _load_profile(req.profile_id)
    history = await _load_history(req.profile_id)
    try:
        result = await respond(profile, history, req.message)
    except Exception as e:
        raise HTTPException(502, f"Claude error: {e!s}")
    await _save(req.profile_id, "user", req.message)
    await _save(req.profile_id, "assistant", result["reply"])
    return ChatResponse(reply=result["reply"], stop_reason=result["stop_reason"])


@router.get("/history/{profile_id}", response_model=list[ChatMessage])
async def get_history(profile_id: int, limit: int = 50):
    history = await _load_history(profile_id, limit)
    return [ChatMessage(role=h["role"], content=h["content"]) for h in history]


@router.delete("/history/{profile_id}", status_code=204)
async def clear_history(profile_id: int):
    async with connect() as db:
        await db.execute("DELETE FROM chat_messages WHERE profile_id = ?", (profile_id,))
        await db.commit()
