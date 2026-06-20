"""Smoke test: build a snapshot for a real ticker and print the result."""
import sys

from app.quant.snapshot import build_snapshot


def main(ticker: str = "AAPL") -> int:
    s = build_snapshot(ticker)
    d = s.model_dump()
    print(f"ticker: {d['ticker']} | {d['company_name']} | {d['sector']}")
    print(f"price : {d['current_price']}  mcap: {d['market_cap_usd']}")
    print(f"src   : {d['sources']}")
    print()
    populated = 0
    total = 0
    for p in d["pillars"]:
        print(f"--- {p['name']} ---")
        for k, v in p["items"].items():
            total += 1
            if v is None:
                print(f"  {k:30s} = None")
            else:
                populated += 1
                print(f"  {k:30s} = {v:.4f}" if isinstance(v, float) else f"  {k:30s} = {v}")
    print()
    print(f"populated: {populated}/{total}")
    return 0 if populated >= total * 0.5 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "AAPL"))
