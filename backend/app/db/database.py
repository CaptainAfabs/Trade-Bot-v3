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
        await _seed_investors_if_empty(db)


async def _seed_investors_if_empty(db: aiosqlite.Connection) -> None:
    cur = await db.execute("SELECT COUNT(*) FROM investors")
    (count,) = await cur.fetchone()
    if count:
        return
    import json
    from pathlib import Path
    roster_path = Path(__file__).parent.parent / "investors" / "roster.json"
    if not roster_path.exists():
        return
    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    for inv in roster:
        await db.execute(
            """INSERT OR IGNORE INTO investors
               (slug, display_name, kind, cik, bio, photo_url, description, is_seeded)
               VALUES (?,?,?,?,?,?,?,1)""",
            (inv["slug"], inv["display_name"], inv["kind"], inv.get("cik"),
             inv.get("bio"), inv.get("photo_url"), inv.get("description")),
        )
    await db.commit()


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


class _FKConnection:
    """Wraps aiosqlite.connect to enforce PRAGMA foreign_keys = ON per connection.
    SQLite resets this PRAGMA each connection, so we set it on every open."""
    def __init__(self, ctx):
        self._ctx = ctx
        self._conn: aiosqlite.Connection | None = None

    async def __aenter__(self) -> aiosqlite.Connection:
        self._conn = await self._ctx.__aenter__()
        await self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    async def __aexit__(self, *a):
        return await self._ctx.__aexit__(*a)


def connect() -> _FKConnection:
    return _FKConnection(aiosqlite.connect(settings.db_path))
