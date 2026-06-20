"""Smoke test: pull Buffett's latest 13F and show top holdings."""
import sys

from app.data import edgar_adapter


def main(cik: str = "0001067983") -> int:
    print(f"Fetching latest 13F-HR for CIK {cik}...")
    data = edgar_adapter.fetch_13f_holdings(cik)
    if not data:
        print("No data returned (filing not found or parse error).")
        return 1
    print(f"period={data['period']}  filed={data['filed']}  total=${data['total_value_usd']:,.0f}")
    print(f"holdings: {len(data['holdings'])}\n")
    print(f"{'#':>3} {'name':<40s} {'value':>16s} {'pct':>7s}")
    print("-" * 70)
    for i, h in enumerate(data["holdings"][:15], 1):
        v = h.get("value_usd") or 0
        p = h.get("pct_portfolio") or 0
        print(f"{i:>3} {h['name'][:40]:<40s} ${v:>14,.0f} {p:>6.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "0001067983"))
