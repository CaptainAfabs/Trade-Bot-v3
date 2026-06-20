"""Smoke: add a couple holdings, summarize, render the digest, and (if Resend
configured) send it."""
import asyncio

from app.db.database import init_db
from app.email.digest import build_and_send_digest
from app.portfolio.service import add_holding, portfolio_summary


async def main() -> int:
    await init_db()

    # Find or create a profile to attach holdings to
    from app.db.database import connect
    async with connect() as db:
        cur = await db.execute("SELECT id FROM profiles ORDER BY id LIMIT 1")
        row = await cur.fetchone()
        if row:
            profile_id = row[0]
            await db.execute("DELETE FROM holdings WHERE profile_id = ? AND notes = 'v1 smoke'", (profile_id,))
            await db.commit()
        else:
            cur = await db.execute("SELECT id FROM users LIMIT 1")
            uid = (await cur.fetchone())[0]
            cur = await db.execute(
                """INSERT INTO profiles (user_id, name, risk, timeline, capital_usd, max_position_pct, max_sector_pct, is_default)
                   VALUES (?, 'Smoke', 'medium', 'long', 5000, 15, 40, 1)""",
                (uid,),
            )
            await db.commit()
            profile_id = cur.lastrowid

    print(f"Adding two fake holdings to profile {profile_id}...")
    await add_holding(profile_id, "AAPL", 5, 180.0, "v1 smoke")
    await add_holding(profile_id, "NVDA", 10, 100.0, "v1 smoke")

    summary = await portfolio_summary(profile_id)
    print(f"portfolio: ${summary['total_value_usd']:,.0f} across {summary['n_positions']} positions")
    print(f"P/L: ${summary['total_pnl_usd']:,.0f} ({summary['total_pnl_pct']:+.1f}%)")
    for h in summary["holdings"]:
        print(f"  {h['ticker']:6s} {h['shares']:>6.2f} @ ${h['avg_cost_usd']:>7.2f} -> ${(h['market_value_usd'] or 0):>10,.0f} ({(h['pnl_pct'] or 0):+.1f}%)")

    print("\nBuilding digest (will not send unless Resend configured)...")
    result = await build_and_send_digest(profile_id)
    if result.get("ok"):
        print(f"sent: {result}")
    else:
        print(f"not sent: {result.get('error')}")
        if result.get("preview_html"):
            print(f"  (preview HTML is {len(result['preview_html'])} chars)")
    return 0


if __name__ == "__main__":
    asyncio.run(main())
