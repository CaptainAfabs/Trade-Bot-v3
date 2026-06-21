"""Smoke: verify Claude generates sensible candidates and scoring filters cleanly."""
import asyncio

from app.api.recommendations import get_candidates, get_recommendations
from app.db.database import connect, init_db
from app.profiles.models import Profile


async def main() -> int:
    await init_db()

    # Use existing profile or build a synthetic one
    async with connect() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute("SELECT * FROM profiles ORDER BY id LIMIT 1")
        row = await cur.fetchone()
    pid = row["id"] if row else None
    if not pid:
        print("No profile in DB — onboard first")
        return 1

    profile_obj = Profile(
        id=row["id"], user_id=row["user_id"], name=row["name"],
        risk=row["risk"], timeline=row["timeline"],
        capital_usd=row["capital_usd"], min_market_cap_usd=row["min_market_cap_usd"],
        max_position_pct=row["max_position_pct"], max_sector_pct=row["max_sector_pct"],
        sectors_exclude=[], sectors_prefer=[],
        dividend_only=False, esg_only=False, follow_investors=[], is_default=True,
    )

    # 1. Claude candidates
    print(f"Asking Claude for candidates ({profile_obj.risk} risk, {profile_obj.timeline} timeline)...")
    candidates = await get_candidates(profile_obj)
    print(f"  -> {len(candidates)} tickers")
    print(f"  preview: {', '.join(candidates[:20])}{'...' if len(candidates) > 20 else ''}")
    print()

    # 2. Full pipeline
    print(f"Running full recommendations (this scores all {len(candidates)} candidates)...")
    r = await get_recommendations(profile_id=pid, limit=15, force_refresh=True)
    print(f"  cached: {r.cached}  universe_size: {r.universe_size}  cleared: {r.n_cleared}  near_misses: {r.n_near_misses}")
    print(f"  threshold for {r.risk} risk: {r.support_required:.0f}")
    print()

    print(f"{'#':>3} {'ticker':<8s} {'score':>6s} {'grade':>6s} {'price':>10s} {'thresh':>7s} {'name':<35s} {'sector'}")
    print("-" * 110)
    for i, p in enumerate(r.picks, 1):
        flag = "PASS" if p.clears_threshold else "near"
        price = f"${p.price:.2f}" if p.price else "-"
        print(f"{i:>3} {p.ticker:<8s} {(p.score or 0):>6.1f} {p.grade:>6s} {price:>10s} {flag:>7s} {(p.name or '')[:35]:<35s} {p.sector or ''}")
    return 0


if __name__ == "__main__":
    asyncio.run(main())
