# Stock Advisor

A personal AI investment assistant. Pick your risk + timeline, and an LLM-driven engine surfaces a tailored list of US stocks scored against your profile — backed by 60+ live quant metrics, 13F holdings from famous investors you can choose to follow, a real-time news feed scored for sentiment, and a chat panel that calls actual tools to ground every answer.

Built solo in one week as a portfolio piece.

![ci](https://github.com/CaptainAfabs/Trade-Bot-v3/actions/workflows/ci.yml/badge.svg) ![tech](https://img.shields.io/badge/python-3.13-blue) ![next](https://img.shields.io/badge/next-16-black) ![claude](https://img.shields.io/badge/AI-Claude%204.6%20%2B%204.5-orange) ![license](https://img.shields.io/badge/license-MIT-green)

📐 **[ARCHITECTURE.md](./ARCHITECTURE.md)** · 🤖 **[CLAUDE_USAGE.md](./CLAUDE_USAGE.md)** — deep dives on the engineering decisions and how the Claude API is used.

---

## Screenshots

> Drop screenshots into `screenshots/` and they'll render here. Suggested captures:
>
> - `screenshots/dashboard.png` — main hub with recommendations, portfolio, chat, news
> - `screenshots/score-nvda.png` — score page showing pillar breakdown + threshold bar
> - `screenshots/chat.png` — chat panel mid-conversation
> - `screenshots/investor-buffett.png` — Buffett's 13F holdings page

## What it does

Three sliders to onboard. After that:

| Section | What it gives you |
|---|---|
| **Recommended picks** | Claude generates ~40 candidate tickers tailored to your profile, the scorer ranks them all through your risk + timeline weights, and you see up to 15 that clear your threshold |
| **Score a ticker** | Type any US symbol → composite score with traffic-light pillar breakdown (valuation, profitability, growth, health, technicals, market signal, analyst, news) and ~60 underlying metrics |
| **Chat** | Ask anything ("Should I buy NVDA?", "What's Buffett's biggest position?"). Claude uses real tools — stock scoring, 13F lookups, news search, backtests — to answer with facts, not guesses |
| **Famous investors** | Browse 29 hedge fund managers and politicians. Follow any (Buffett, Burry, Ackman, Druckenmiller…) and their holdings get a score boost in your recommendations |
| **News** | 12 RSS feeds ingested hourly; Claude Haiku scores each headline for sentiment and impact 0-5 |
| **Portfolio** | Manual holdings entry with live prices, P/L, sector weights |
| **Daily email digest** | Morning brief over Resend with portfolio summary, top picks, high-impact news |

---

## Why I built it

Two reasons:

1. I wanted to learn what it actually takes to build a production-shaped LLM agent system end-to-end — tool use, prompt design, cost control, graceful degradation when external APIs flake.
2. I wanted to understand the financial data landscape from the inside instead of skimming it. Wiring up SEC EDGAR, FMP, Alpha Vantage, Finimpulse, yfinance, RSS, and Reddit-flavored aggregators teaches you more about how the sausage is made than any book would.

Side benefit: I have a stock screener for myself now.

---

## What the engineering looked like

### Multi-source data with graceful fallback

No single data API gives you everything cheaply, and free tiers love to rate-limit. The snapshot builder fans out across multiple providers and uses the first non-null source per field:

- **Price / valuation / 52-week / sector** → Finimpulse (paid, $0.0002/call, 2000 req/min)
- **Margins / ROE / ROIC / growth / cash flow / statements / analyst targets** → Financial Modeling Prep (free tier, 250 calls/day, 24h cache)
- **News sentiment** → Alpha Vantage News API (free, 25 calls/day)
- **13F filings** → SEC EDGAR direct (free, official, no key)
- **Insider / short / institutional %** → yfinance with `curl_cffi` Chrome impersonation (last-resort fallback because Yahoo aggressively throttles scrapers)

Every adapter caches to disk with per-endpoint TTLs so the dashboard isn't burning quota on every refresh.

### LLM agent with tool use

Chat is an Anthropic SDK loop that exposes five tools to Claude Sonnet:

- `get_stock_score(ticker, risk, timeline)` — full snapshot + scoring through user's profile
- `list_recent_news(ticker?, min_impact?)` — query the news DB
- `list_investors(kind?)` and `get_investor_holdings(slug)` — 13F lookups
- `backtest_buy_hold(ticker, years)` — pure-pandas backtest with Sharpe + max drawdown

The model decides which to call, the loop runs them, and the result feeds back until it returns plain text. Bulk work (news sentiment, candidate generation) uses Claude Haiku for cost.

### Composite scoring

Each of 8 pillars produces a 0-100 sub-score from threshold-band logic. Pillar weights are a function of `(risk, timeline)` — 12 hard-coded weight tables. "High risk + short" weighs technicals and news heavy; "low risk + generational" weighs profitability and health. Same stock can land an 80 for one profile and a 55 for another. Riskier picks need higher minimum scores ("support thresholds") to clear.

### Dynamic recommendation universe

Instead of a static stock list, the recommendations endpoint asks Claude Haiku to generate ~40 candidate tickers tailored to the active profile (with sector exclusions honored), then scores them all in parallel via the snapshot pipeline. Caching is per `(risk, timeline, exclusions)` for 24h on the candidate list, 6h on the scored results.

### "Follow an investor" with score boost

If you follow Warren Buffett on the investors page, the recommender pulls his latest 13F from EDGAR, builds a normalized-name index of his top 25 holdings, and any candidate matching a held name gets +6 per follower (capped +12). Tagged in the UI as `★ followed (+12)`. Effectively: consensus picks from people you trust float to the top.

### Stack

- **Backend**: Python 3.13, FastAPI, SQLite (WAL mode, foreign keys), APScheduler for cron, Anthropic SDK
- **Frontend**: Next.js 16, React 19, Tailwind v4 (CSS-first config), shadcn-style components, custom palette (cream `#FAF7F0` + British racing green `#004225`)
- **Email**: Resend
- **Deploy**: Docker Compose — laptop, Pi, or any Linux box

---

## Try it locally

Prereqs: Python 3.13, Node 22+, a few API keys (all have free tiers).

```bash
git clone https://github.com/CaptainAfabs/Trade-Bot-v3.git
cd Trade-Bot-v3

# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\activate          # or source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env              # fill in the keys you have
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

### API keys

| Service | Free tier | What it's used for |
|---|---|---|
| [Anthropic](https://console.anthropic.com/) | pay-as-you-go (~$5–30/mo for personal use) | Chat with tool use, news sentiment, monthly journal review, AI-add-investor |
| [Financial Modeling Prep](https://site.financialmodelingprep.com/developer) | 250 calls/day | Margins, ROE, growth, statements, analyst targets |
| [Alpha Vantage](https://www.alphavantage.co/support/#api-key) | 25 calls/day | News sentiment |
| [Finimpulse](https://finimpulse.com/api/) | Usage-based (~$5/mo for personal use) | Real-time price, valuation, 52w, OHLCV |
| [Resend](https://resend.com) | 3k emails/mo | Daily digest |

You can run with only the Anthropic + FMP keys and the rest degrades gracefully.

### Docker (Pi / server)

```bash
docker compose up --build -d
```

Backend on `:8000`, frontend on `:3000`. The APScheduler instance runs inside the backend container — news ingest every 60 min, sentiment scoring every 15 min, daily digest at 07:00 server time.

---

## What I'd build next

- **Sector-relative scoring** — current thresholds are absolute, so tech always looks "expensive." Percentile rank against the sector would be fairer.
- **Real broker execution** — the `ExecutionAdapter` interface is already wired with a `ManualAdapter`. An `IBKRAdapter` is a single class away from auto-execution with paper-trade mode first.
- **Politician PTRs** — investor pages exist for Pelosi / Tuberville / etc. but the trade feed isn't ingested yet (House clerk site needs scraping or Quiver Quant subscription).
- **Backtest beyond buy-and-hold** — vectorbt or backtrader would slot into `app/backtest/` cleanly. The interface is in place.
- **Multi-user with auth** — single-user today. The DB schema (`users` table, `profile.user_id` FK) is already structured for multi.
- **Crypto + global markets** — US-only by design for v1. Coinbase/CoinGecko adapter is small; TSX needs a different fundamentals provider.

---

## Honest tradeoffs

- **No sector-relative percentiles** (mentioned above) — chose absolute thresholds for v1 to keep the scoring logic readable.
- **yfinance is rate-limited from US IPs** — even with `curl_cffi`. FMP + Finimpulse cover the gap but a few yfinance-only fields (forward P/E, insider %, short %) come up null sometimes.
- **6h cache on recommendations** is a deliberate cost-control choice, not a bug. Refresh more aggressively by adding `?force_refresh=true`.
- **No formal eval suite** — I tested by hand. A proper LLM eval (golden cases, regression suite, automated benchmark) is the obvious next investment if this graduated past portfolio status.
- **Single-user, no auth** — would not deploy this to the open internet without changes.

---

## Disclaimer

Educational and personal-use project. Not financial advice. The bot will sometimes be confidently wrong; verify everything before acting on it.

## License

MIT — see [LICENSE](./LICENSE).
