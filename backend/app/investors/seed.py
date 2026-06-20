"""Seed the investors table from roster.json. Idempotent — safe to re-run."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import aiosqlite

from app.db.database import connect, init_db

ROSTER = Path(__file__).parent / "roster.json"


async def seed() -> int:
    await init_db()
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    n = 0
    async with connect() as db:
        for inv in roster:
            await db.execute(
                """
                INSERT INTO investors (slug, display_name, kind, cik, bio, photo_url, description, is_seeded)
                VALUES (?,?,?,?,?,?,?,1)
                ON CONFLICT(slug) DO UPDATE SET
                    display_name=excluded.display_name,
                    kind=excluded.kind,
                    cik=excluded.cik,
                    bio=excluded.bio,
                    photo_url=excluded.photo_url,
                    description=excluded.description
                """,
                (
                    inv["slug"], inv["display_name"], inv["kind"], inv.get("cik"),
                    inv.get("bio"), inv.get("photo_url"), inv.get("description"),
                ),
            )
            n += 1
        await db.commit()
    return n


if __name__ == "__main__":
    n = asyncio.run(seed())
    print(f"seeded {n} investors")
