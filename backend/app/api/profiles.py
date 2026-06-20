import json

from fastapi import APIRouter, HTTPException

from app.db.database import connect
from app.profiles.models import Profile, ProfileIn, derive_position_limits

router = APIRouter()


def _row_to_profile(row) -> Profile:
    return Profile(
        id=row["id"],
        user_id=row["user_id"],
        name=row["name"],
        risk=row["risk"],
        timeline=row["timeline"],
        capital_usd=row["capital_usd"],
        min_market_cap_usd=row["min_market_cap_usd"],
        max_position_pct=row["max_position_pct"],
        max_sector_pct=row["max_sector_pct"],
        sectors_exclude=json.loads(row["sectors_exclude"] or "[]"),
        sectors_prefer=json.loads(row["sectors_prefer"] or "[]"),
        dividend_only=bool(row["dividend_only"]),
        esg_only=bool(row["esg_only"]),
        follow_investors=json.loads(row["follow_investors"] or "[]"),
        is_default=bool(row["is_default"]),
    )


@router.get("", response_model=list[Profile])
async def list_profiles():
    async with connect() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute("SELECT * FROM profiles ORDER BY is_default DESC, id ASC")
        rows = await cur.fetchall()
        return [_row_to_profile(r) for r in rows]


@router.post("", response_model=Profile, status_code=201)
async def create_profile(payload: ProfileIn):
    max_pos, max_sec = derive_position_limits(payload.risk, payload.timeline)
    max_pos = payload.max_position_pct or max_pos
    max_sec = payload.max_sector_pct or max_sec

    async with connect() as db:
        cur = await db.execute("SELECT id FROM users LIMIT 1")
        row = await cur.fetchone()
        if not row:
            raise HTTPException(500, "No user seeded")
        user_id = row[0]

        if payload.is_default:
            await db.execute("UPDATE profiles SET is_default = 0 WHERE user_id = ?", (user_id,))

        cur = await db.execute(
            """
            INSERT INTO profiles (
                user_id, name, risk, timeline, capital_usd, min_market_cap_usd,
                max_position_pct, max_sector_pct, sectors_exclude, sectors_prefer,
                dividend_only, esg_only, follow_investors, is_default
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                user_id, payload.name, payload.risk, payload.timeline,
                payload.capital_usd, payload.min_market_cap_usd, max_pos, max_sec,
                json.dumps(payload.sectors_exclude), json.dumps(payload.sectors_prefer),
                int(payload.dividend_only), int(payload.esg_only),
                json.dumps(payload.follow_investors), int(payload.is_default),
            ),
        )
        await db.commit()
        new_id = cur.lastrowid

        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute("SELECT * FROM profiles WHERE id = ?", (new_id,))
        return _row_to_profile(await cur.fetchone())


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(profile_id: int):
    async with connect() as db:
        await db.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        await db.commit()
