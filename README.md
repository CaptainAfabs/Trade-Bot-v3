# Stock Advisor

A personalized AI stock-recommendation assistant. Combines 30+ quant indicators, 13F filings from famous investors, real-time news with Claude-scored sentiment, and risk/timeline-aware scoring. Web + chat + daily email digest. US market, recommend-only (broker execution pluggable). Local-first, Pi-deployable via Docker.

Built solo in a week. Personal use, not a service.

## What it does

1. **Onboard in three sliders** — capital, risk, timeline → defaults set everything else.
2. **Score any US ticker** — composite 0–100 across 8 pillars (valuation, profitability, growth, health, technicals, market signal, analyst, news), weighted differently per your risk + timeline.
3. **Chat with Claude** — grounded in your profile and powered by tool-use over the data layer. "Should I buy NVDA?" pulls the score + 5-year backtest + applies your position-size rule.
4. **Famous investors** — 29-investor roster with photos and bios; click any hedge-fund manager to see their latest 13F holdings parsed live from SEC EDGAR. Ask the AI to research and add anyone else.
5. **News feed** — 12 RSS sources ingested hourly; Claude Haiku scores sentiment + impact in batches.
6. **Portfolio** — manual entry with live FMP quotes, P/L, sector weights.
7. **Daily email digest** — 7am morning brief over Resend (free tier).
8. **Monthly Claude review** — Claude summarizes your trade-decision journal: wins, misses, patterns to lean into vs break.

## Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.13, FastAPI, SQLite, APScheduler |
| AI | Anthropic Claude (Sonnet 4.6 for chat, Haiku 4.5 for bulk) |
| Frontend | Next.js 16, React 19, Tailwind v4, shadcn-style components |
| Theme | Cream `#FAF7F0` + British racing green `#004225` |
| Data | FMP stable (primary), yfinance + curl_cffi (fallback), Alpha Vantage (news), SEC EDGAR (13F), 12 RSS feeds |
| Email | Resend HTTP API |
| Deploy | Docker Compose — laptop or Raspberry Pi |

## Quick start (dev)

Prereqs: Python 3.13, Node 22+.

```powershell
# Backend
cd backend
py -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env       # fill in API keys
uvicorn app.main:app --reload
```

```powershell
# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

## Deploy (Raspberry Pi or any Linux box)

```bash
git clone <repo>
cd stock-advisor
cp backend/.env.example backend/.env
# fill in: ANTHROPIC_API_KEY, ALPHAVANTAGE_API_KEY, FMP_API_KEY, RESEND_API_KEY, EMAIL_TO
docker compose up --build -d
```

Backend on `:8000`, frontend on `:3000`. The scheduler runs inside the backend container — news ingest every 60min, sentiment scoring every 15min, daily digest at 07:00 server time.

For exposure over the internet, put a reverse proxy (Caddy / Cloudflare Tunnel) in front. There's no auth — keep it on your tailnet or a VPN.

## API keys needed

| Service | Tier | Used for |
|---|---|---|
| [Anthropic](https://console.anthropic.com/) | pay-as-you-go (~$5–30/mo for personal use) | Chat, sentiment scoring, monthly review, AI-add-investor |
| [Financial Modeling Prep](https://site.financialmodelingprep.com/developer) | Free (250 calls/day) | Primary fundamentals + statements + 13F-adjacent |
| [Alpha Vantage](https://www.alphavantage.co/support/#api-key) | Free (25 calls/day) | News sentiment fallback |
| [Resend](https://resend.com) | Free (3k/mo) | Daily digest email |

## Project layout

```
backend/
  app/
    api/         FastAPI routes (profiles, stocks, investors, news, chat, backtest, portfolio, journal, email)
    data/        FMP / yfinance / EDGAR / Alpha Vantage adapters + TTL disk cache
    quant/       30+ indicators + composite scoring with risk/timeline weights
    investors/   roster.json (29 seeded) + EDGAR 13F fetcher
    news/        12 RSS feeds + Claude-scored sentiment/impact
    reasoning/   Anthropic client + chat tool-use loop
    backtest/    Pure-pandas buy-and-hold
    portfolio/   Holdings CRUD with live FMP quotes
    email/       HTML digest renderer + Resend sender
    execution/   ExecutionAdapter interface (ManualAdapter today, IBKRAdapter slot for v1.1)
    db/          SQLite schema (9 tables) + connection helpers
  tests/         Smoke scripts for each phase
frontend/
  src/
    app/         /onboard, /dashboard, /portfolio, /investors, /investors/[slug]
    lib/api.ts   Typed client for the backend
```

## Adding broker execution (v1.1)

The `ExecutionAdapter` interface in `backend/app/execution/base.py` is the only point a real broker needs to plug in:

```python
class IBKRAdapter(ExecutionAdapter):
    async def submit(self, order: Order) -> OrderResult: ...
    async def positions(self) -> list[dict]: ...
    async def cash_balance(self) -> float: ...
```

Register it in `manual.py::get_adapter()` and wire to the chat tool-use loop. No other code changes.

## Tradeoffs and limits

- **Single-user.** All endpoints assume one user. The schema supports multi but I haven't wired auth — fine for personal use.
- **US only.** TSX support would add a currency conversion layer plus a different fundamentals provider.
- **No backtesting beyond buy-and-hold.** vectorbt or backtrader would slot into `app/backtest/` cleanly.
- **Scoring thresholds are absolute, not sector-relative.** Tech will look "expensive" vs utilities. A sector-percentile pass would help — but reasonable for v1.
- **yfinance is rate-limited from US IPs.** I fall back to FMP for almost everything, but a few fields (forward P/E, insider %, short %) intermittently miss.
- **Politicians' PTRs not ingested yet.** Profile pages exist but trade feed waits for v1.1 (House clerk scraper or Quiver API).

## Disclaimer

Personal use. Educational. **Not financial advice.** You are the human in the loop for every real-money trade. The bot will be wrong, sometimes confidently. Verify before acting.
