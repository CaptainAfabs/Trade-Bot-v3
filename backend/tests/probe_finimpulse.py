"""Probe Finimpulse /histories for daily OHLCV."""
import json
from datetime import datetime, timedelta

import httpx

KEY = "live_10b8c30778d4b6e819f14ca22abdb3756e11868637b98ecb15ff4c11ab7"
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
BASE = "https://api.finimpulse.com/v1"

# Try a few histories request shapes
TODAY = datetime.utcnow().strftime("%Y-%m-%d")
ONE_YR = (datetime.utcnow() - timedelta(days=365)).strftime("%Y-%m-%d")

for body in [
    {"symbol": "AAPL"},
    {"symbol": "AAPL", "interval": "1d"},
    {"symbol": "AAPL", "interval": "1d", "range": "1y"},
    {"symbol": "AAPL", "interval": "1d", "from": ONE_YR, "to": TODAY},
    {"symbol": "AAPL", "interval": "1d", "start_date": ONE_YR, "end_date": TODAY},
    {"symbol": "AAPL", "period": "1y"},
]:
    r = httpx.post(BASE + "/histories", headers=H, json=body, timeout=20)
    j = r.json() if r.status_code == 200 else None
    payload = j.get("result") if j else None
    n = len(payload.get("items", [])) if isinstance(payload, dict) and payload.get("items") else 0
    items_preview = (payload.get("items", []) if isinstance(payload, dict) else [])[:2] if n else []
    print(f"body={body}  http={r.status_code}  rows={n}  cost={j.get('cost') if j else '-'}")
    if items_preview:
        print(f"  first 2: {json.dumps(items_preview, default=str)[:400]}")
    elif r.status_code != 200:
        print(f"  err: {r.text[:200]}")
    print()
