from pathlib import Path

import aiosqlite

from app.config import settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def init_db() -> None:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    async with aiosqlite.connect(settings.db_path) as db:
        await db.executescript(schema)
        await db.commit()
        await _seed_default_user(db)


async def _seed_default_user(db: aiosqlite.Connection) -> None:
    cursor = await db.execute("SELECT COUNT(*) FROM users")
    (count,) = await cursor.fetchone()
    if count:
        return
    await db.execute(
        "INSERT INTO users (email, display_name) VALUES (?, ?)",
        (settings.email_to or "you@example.com", "Owner"),
    )
    await db.commit()


def connect() -> aiosqlite.Connection:
    return aiosqlite.connect(settings.db_path)
