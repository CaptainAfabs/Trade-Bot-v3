"""Score a ticker across all 12 risk/timeline combos."""
import sys

from app.quant.scoring import score_snapshot
from app.quant.snapshot import build_snapshot


def main(ticker: str = "AAPL") -> int:
    snap = build_snapshot(ticker)
    print(f"=== {snap.ticker} {snap.company_name} ({snap.sector}) ===")
    print(f"price: {snap.current_price}  mcap: {snap.market_cap_usd}\n")

    print(f"{'risk':8s} {'timeline':14s} {'composite':>10s} {'grade':>6s}  drivers")
    print("-" * 100)
    for risk in ("low", "medium", "high"):
        for timeline in ("short", "medium", "long", "generational"):
            sc = score_snapshot(snap, risk=risk, timeline=timeline)
            pos = ", ".join(sc.drivers_positive)
            neg = " | weak: " + ", ".join(sc.drivers_negative) if sc.drivers_negative else ""
            comp = f"{sc.composite:.1f}" if sc.composite is not None else "N/A"
            print(f"{risk:8s} {timeline:14s} {comp:>10s} {sc.grade:>6s}  {pos}{neg}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "AAPL"))
