# Architecture

This is the engineering walkthrough. For *what the app does*, read the README.

---

## High-level data flow

```
                          ┌──────────────────────────────────┐
                          │   Next.js 16 frontend (port 3000)│
                          │  Onboard / Dashboard / Score /   │
                          │  Chat / News / Portfolio / Inv.  │
                          └────────────────┬─────────────────┘
                                           │  HTTPS / JSON
                                           ▼
                          ┌──────────────────────────────────┐
                          │   FastAPI backend  (port 8000)   │
                          │   ┌──────────────────────────┐   │
                          │   │  API routes              │   │
                          │   │  • profiles  • stocks    │   │
                          │   │  • recommendations       │   │
                          │   │  • investors  • news     │   │
                          │   │  • chat  • portfolio     │   │
                          │   │  • journal  • backtest   │   │
                          │   │  • email                 │   │
                          │   └─────────┬────────────────┘   │
                          │             │                    │
                          │   ┌─────────▼────────────────┐   │
                          │   │  Snapshot builder        │   │
                          │   │  (quant pillars)         │   │
                          │   └──┬──────┬──────┬─────┬───┘   │
                          │      │      │      │     │       │
                          │   Finimp. │  FMP  yfinance AV    │
                          │      ▼      ▼      ▼     ▼       │
                          │  ┌─────────────────────────┐     │
                          │  │  Per-source disk cache  │     │
                          │  │  (TTL: 15min – 24h)     │     │
                          │  └─────────────────────────┘     │
                          │                                  │
                          │   ┌──────────────────────────┐   │
                          │   │  Scoring engine          │   │
                          │   │  • 8 pillar sub-scores   │   │
                          │   │  • Risk/timeline weights │   │
                          │   │  • Investor-follow boost │   │
                          │   └──────────────────────────┘   │
                          │                                  │
                          │   ┌──────────────────────────┐   │
                          │   │  Claude reasoning layer  │   │
                          │   │  • Chat (Sonnet 4.6)     │   │
                          │   │  • Sentiment (Haiku 4.5) │   │
                          │   │  • Candidate gen (Haiku) │   │
                          │   │  • Monthly review (Haiku)│   │
                          │   │  • AI-add-investor       │   │
                          │   └──────────────────────────┘   │
                          │                                  │
                          │   ┌──────────────────────────┐   │
                          │   │  APScheduler             │   │
                          │   │  • RSS ingest  /60min    │   │
                          │   │  • Sentiment   /15min    │   │
                          │   │  • Daily email digest    │   │
                          │   └──────────────────────────┘   │
                          └─────────────────┬────────────────┘
                                            │
                          ┌─────────────────▼────────────────┐
                          │  SQLite (WAL, FK enforced)       │
                          │  users, profiles, holdings,      │
                          │  investors, investor_holdings,   │
                          │  news_items, chat_messages,      │
                          │  trade_journal, watchlist,       │
                          │  quant_cache                     │
                          └──────────────────────────────────┘
```

External data sources called from the snapshot builder:
- **Finimpulse** (`api.finimpulse.com`) — primary: price, valuation ratios, 52w, beta, OHLCV
- **FMP** (`financialmodelingprep.com/stable`) — fundamentals: ROE, ROIC, margins, growth, statements, analyst targets
- **Alpha Vantage** (`alphavantage.co`) — news sentiment
- **SEC EDGAR** (`data.sec.gov`) — 13F filings
- **yfinance** (with `curl_cffi` Chrome impersonation) — last-resort fallback for insider/short/institutional %

---

## Snapshot builder (the multi-source fan-out)

`backend/app/quant/snapshot.py` calls every source in parallel-by-cache, then a single `pick(*candidates)` helper takes the first non-null. Per-source TTLs respect each provider's pricing/staleness sweet spot.

```
ticker AAPL
  │
  ├─ finimpulse.get_summary_lite(AAPL)    [15min TTL, ~$0.0002]
  │     → price, P/E, fwd P/E, P/B, P/S, dividend yield, beta, 52w, sector
  │
  ├─ fmp.get_ratios_ttm(AAPL)             [24h TTL, free tier]
  │     → 35+ ratio fields including grossProfitMarginTTM, interestCoverageRatioTTM…
  │
  ├─ fmp.get_key_metrics_ttm(AAPL)        [24h TTL]
  │     → ROE, ROA, ROIC, EV/EBITDA, capex/revenue, working capital…
  │
  ├─ fmp.get_financial_growth(AAPL)       [24h TTL]
  │     → revenueGrowth, netIncomeGrowth, epsgrowth, fcfGrowth, 3y/5y CAGRs
  │
  ├─ fmp.get_price_target_consensus(AAPL) [1h TTL]
  │     → targetHigh, targetLow, targetConsensus, targetMedian
  │
  ├─ fmp.get_grades_consensus(AAPL)       [1h TTL]
  │     → strongBuy, buy, hold, sell, strongSell counts
  │
  ├─ fmp.get_balance_sheet(AAPL, limit=1) [24h TTL]
  ├─ fmp.get_cash_flow(AAPL, limit=1)     [24h TTL]
  ├─ finimpulse.get_histories(AAPL)       [1h TTL]   → for technicals
  └─ yfinance.get_info(AAPL)              [1h TTL]   → fallback for short/insider/institutional %

→ assembles StockSnapshot with 8 pillars × 60+ metrics
```

Every adapter has the same shape: `_cache.get(key, ttl)` first, network call only on miss, `_cache.set(key, response)` on success. Failures silently return `None` and the next source picks up the slack.

---

## Scoring engine

`backend/app/quant/scoring.py`. Two stages:

**Stage 1 — per-pillar sub-scores (0-100).** Each pillar has 4-9 metrics. Each metric maps to a sub-score via threshold bands:
```python
score_valuation(items) = avg([
  _band_score(items.pe_ttm,    [(10, 90), (15, 80), (20, 70), …], "lower"),
  _band_score(items.peg,       [(0.5, 90), (1, 75), (1.5, 60), …], "lower"),
  _band_score(items.pb,        [(1, 90), (1.5, 75), (3, 60), …], "lower"),
  …
])
```
Missing metrics are skipped, not penalized — only available data influences the pillar score.

**Stage 2 — composite via (risk, timeline) weights.** A 12-row weight matrix:
```
                  val  prof  growth health  tech  analyst  news
low/generational   15   25     5     30     5     10       10
low/long           18   22     8     27     5     10       10
…
high/short          5    5    20     5     30     15       20
```
The composite is a weighted mean over present pillars (weights renormalized so missing pillars don't penalize).

**Threshold by risk:** low=55, medium=65, high=75. Riskier picks need higher composites — codified directly per the user's onboarding answer that "the riskier the stock, the more support it needs."

---

## Dynamic recommendation universe

`backend/app/api/recommendations.py`. Replaces the older hardcoded 15-stock list with LLM-driven candidate generation.

```
Profile (risk=medium, timeline=long, capital=$5000, exclude=[])
  │
  │  (cache 24h on profile config hash)
  ▼
Claude Haiku 4.5  ← screener system prompt + profile JSON
  │
  ▼
~40 ticker strings  ["AAPL", "MSFT", "NVDA", "TJX", "PYPL", "HD", "NFLX", …]
  │
  │  (parallel asyncio.gather over snapshot builder)
  ▼
40 × StockSnapshot  →  40 × CompositeScore (weighted for this profile)
  │
  ├─ Cross-reference followed investors' top 25 13F holdings
  │     → if matched: +6 per follower (capped +12) added to composite
  │
  ▼
Sort descending by composite, partition by threshold
  │
  ├─ Top N clearing threshold
  └─ Top M near-misses to fill the card

Cache result 6h per (profile_id, risk, timeline, limit).
```

Cost: 40 × Finimpulse summary ($0.0002) + 40 × cached FMP ($0) + 1 × Claude Haiku candidate gen ($0.001) ≈ **~$0.01 per fresh refresh**.

---

## Claude chat with tool use

`backend/app/reasoning/chat.py` — the agentic loop.

```
user message + profile context
  │
  ▼
Claude Sonnet 4.6 (with 5 tools: get_stock_score, list_recent_news,
                   list_investors, get_investor_holdings, backtest_buy_hold)
  │
  ▼
stop_reason == "tool_use"?
  │
  ├─ yes → execute each tool_use block in parallel
  │         append [tool_result, …] to messages
  │         loop back to Claude (max 6 iterations)
  │
  └─ no  → return assistant text to caller
                                            │
                                            ▼
                              persist to chat_messages table
```

Sample successful run (from the smoke test):
- User: "Should I buy NVDA?"
- Loop 1: Claude calls `get_stock_score(ticker="NVDA")` → returns 72.3 composite, full snapshot
- Loop 2: Claude calls `backtest_buy_hold(ticker="NVDA", years=5)` → returns 1043% total / 63% annualized / Sharpe 1.2 / -66% max DD
- Loop 3: Claude returns plain text synthesizing both, applying the user's 15% max-position rule to their $5,000 → "$750 starter position"

The chat reply paragraph quoted the real data verbatim. No hallucinated numbers.

---

## Follow-an-investor scoring boost

When a user follows Warren Buffett:
```
profile.follow_investors = ["buffett-berkshire", "burry-scion"]
  │
  ▼  (during recommendations scoring, cached 24h via EDGAR adapter)
edgar_adapter.fetch_13f_holdings(CIK=0001067983)  → top 90 positions
edgar_adapter.fetch_13f_holdings(CIK=0001649339)  → top N positions
  │
  ▼  (build normalized-name index)
{ "APPLE":          ["buffett-berkshire"],
  "AMERICAN EXPRESS": ["buffett-berkshire"],
  "COCA COLA":       ["buffett-berkshire"],
  …                                          }
  │
  ▼  (when scoring each candidate)
if normalized(candidate.company_name) in index:
    composite += min(6 * len(matchers), 12)
    pick.followed_by = matchers
    pick.investor_boost = boost
```

UI tags boosted picks with `★ followed (+12)`. Multi-investor consensus → biggest boost.

---

## News pipeline

`backend/app/news/`. APScheduler runs:
- **`ingest_all`** every 60 min → 12 RSS feeds (Reuters, MarketWatch, WSJ, CNBC, Yahoo Finance, BBC, FT, SeekingAlpha, Fed press, Treasury press, USGS earthquakes, NOAA hurricanes) → `feedparser` → dedupe by URL → insert into `news_items` with auto-extracted tickers
- **`score_unscored`** every 15 min → pull up to 50 unscored items → batch of 25 to Claude Haiku → JSON-per-line sentiment + impact → UPDATE rows

System prompt for sentiment scoring is tight on purpose: one line of JSON per headline, no markdown fences. Cost per 200 headlines/day ≈ $0.10/mo.

---

## Caching strategy

| Layer | Mechanism | TTL |
|---|---|---|
| Per-source per-endpoint | JSON-on-disk under `data/cache/{namespace}/{key}.json` | 15min – 24h, source-dependent |
| Recommendation result | Same disk cache, key=`recs_{profile_id}_{risk}_{timeline}_{limit}` | 6h |
| Candidate list (Claude output) | Same, key=`cand_{risk}_{timeline}_…` | 24h |
| 13F holdings | Same, key=`13f_{cik}_{accession}` | 24h |
| News (DB row) | Persistent in `news_items` table | forever, refreshed by ingest |
| Chat history | Persistent in `chat_messages` table per profile | forever, user-deletable |

Cold dashboard load on first profile: ~30s. Subsequent loads within 6h: <500ms.

---

## Storage

SQLite with `PRAGMA foreign_keys = ON` enforced per connection (see `_FKConnection` wrapper in `app/db/database.py` — the PRAGMA resets per connection and we caught a real bug from a missed enforcement).

10 tables:
- `users` (single user today; schema supports multi)
- `profiles` (named strategies — each has risk/timeline/capital/excludes/follow_investors)
- `holdings` (manual portfolio entries per profile)
- `watchlist` (tickers per profile)
- `investors` (the 29-name roster + AI-added)
- `investor_holdings` (cached 13F positions per investor per period)
- `news_items` (RSS-ingested headlines with sentiment + impact)
- `chat_messages` (assistant + user turns per profile)
- `trade_journal` (decisions logged, rated, outcome-tagged)
- `quant_cache` (legacy, not actively used — disk cache replaced it)

---

## Execution adapter (future broker integration)

`backend/app/execution/base.py` defines an `ExecutionAdapter` ABC with three methods: `submit(order)`, `positions()`, `cash_balance()`. The only implementation today is `ManualAdapter` which returns a string telling the user to place the trade by hand. Adding `IBKRAdapter` for actual auto-execution is one subclass and a factory-registration line away — no other code changes.

This was a deliberate v1 choice: keep humans in the loop until the model has earned trust through a real eval suite.

---

## What's NOT in the diagram

- **No auth.** Single-user. Add OAuth/JWT layer if going multi.
- **No queue.** Tool calls are synchronous in-request. Long backtests would deserve a job queue (RQ/Celery).
- **No real eval suite.** Smoke tests catch import and integration breakage; LLM correctness is hand-validated for now.
- **No real-money execution.** By design — see above.
