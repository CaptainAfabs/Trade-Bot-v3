"""Score recently-ingested news with Claude Haiku (cheap, fast).

Per-row sentiment in [-1, 1] and impact in [0, 5]. We batch ~25 headlines per
Claude call to stay efficient.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from app.db.database import connect
from app.reasoning import claude

BATCH_SIZE = 25

_SYSTEM = """You score financial news headlines.

For each numbered headline below, return ONE line of JSON with this shape:
{"id": <int>, "sentiment": <-1.0..1.0>, "impact": <0..5>}

- sentiment: -1 very bearish, 0 neutral, +1 very bullish for the equities mentioned.
- impact: 0 noise, 1 tiny, 2 minor, 3 notable, 4 big, 5 market-moving.

Return ONLY the lines of JSON, one per headline, no preamble, no markdown fences."""


def _parse_response(text: str) -> dict[int, dict[str, float]]:
    out: dict[int, dict[str, float]] = {}
    for line in text.splitlines():
        line = line.strip().rstrip(",")
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
            out[int(obj["id"])] = {
                "sentiment": float(obj.get("sentiment", 0)),
                "impact": float(obj.get("impact", 0)),
            }
        except Exception:
            continue
    return out


async def _score_batch(rows: list[tuple[int, str]]) -> dict[int, dict[str, float]]:
    numbered = "\n".join(f"{i}. {title}" for i, title in rows)
    try:
        text = await asyncio.to_thread(claude.complete, _SYSTEM, numbered, None, 1200)
    except Exception:
        return {}
    return _parse_response(text)


async def score_unscored(limit: int = 50) -> int:
    """Pull up to `limit` unscored news_items and write sentiment/impact."""
    async with connect() as db:
        cur = await db.execute(
            "SELECT id, title FROM news_items WHERE sentiment IS NULL ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows: list[tuple[int, str]] = await cur.fetchall()
    if not rows:
        return 0

    scored: dict[int, dict[str, float]] = {}
    for i in range(0, len(rows), BATCH_SIZE):
        chunk = rows[i:i + BATCH_SIZE]
        scored.update(await _score_batch(chunk))

    if not scored:
        return 0
    async with connect() as db:
        for rid, s in scored.items():
            await db.execute(
                "UPDATE news_items SET sentiment = ?, impact = ? WHERE id = ?",
                (s["sentiment"], s["impact"], rid),
            )
        await db.commit()
    return len(scored)
