"""Smoke test: ingest news, score a subset, and run one chat turn."""
import asyncio
import json

from app.db.database import init_db
from app.news.ingest import ingest_all
from app.news.sentiment import score_unscored
from app.profiles.models import Profile
from app.reasoning.chat import respond


async def main() -> int:
    await init_db()

    print("Ingesting RSS feeds...")
    results = await ingest_all()
    total = sum(results.values())
    print(f"  inserted {total} new items across {len(results)} feeds")
    for src, n in results.items():
        if n:
            print(f"    {src}: +{n}")

    print("\nScoring up to 20 unscored items with Claude Haiku...")
    n = await score_unscored(limit=20)
    print(f"  scored {n}")

    print("\nChat turn: 'should I buy NVDA?'")
    profile = Profile(
        id=0, user_id=0, name="Smoke", risk="medium", timeline="long",
        capital_usd=5000, min_market_cap_usd=0, max_position_pct=15, max_sector_pct=40,
        sectors_exclude=[], sectors_prefer=[],
        dividend_only=False, esg_only=False, follow_investors=[], is_default=True,
    )
    result = await respond(profile, [], "Should I buy NVDA? Give me one paragraph.")
    print("\n--- assistant reply ---")
    print(result["reply"])
    print(f"\n(stop_reason: {result['stop_reason']})")
    return 0


if __name__ == "__main__":
    asyncio.run(main())
