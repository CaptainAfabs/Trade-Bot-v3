# Stock Advisor

Personalized AI stock recommendations. Quant ratios + famous-investor tracking + news reactivity + risk/timeline-aware scoring, served as a web app + dashboard with a Claude-powered chat and daily email digest.

US market, recommend-only (broker execution pluggable for later). Local-first, Pi-deployable via Docker.

## Stack

- **Backend**: Python 3.13 + FastAPI + SQLite + Claude (Anthropic SDK)
- **Frontend**: Next.js 15 + Tailwind + shadcn/ui (cream `#FAF7F0` + British racing green `#004225`)
- **Data**: yfinance, Alpha Vantage, FMP, SEC EDGAR, RSS, Reddit (PRAW), Nitter
- **Deploy**: Docker Compose — laptop or Raspberry Pi

## Quick start

```bash
# Backend
cd backend
py -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # fill in keys
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

## Docker (for Pi / server)

```bash
docker compose up --build -d
```

## Build phases

- Day 1 — Scaffold (this commit)
- Day 2 — Data adapters + 30+ quant indicators
- Day 3 — Composite scoring + risk/timeline weighting
- Day 4 — 13F + Congress trackers + investor roster
- Day 5 — News pipeline + Claude chat + backtest
- Day 6 — Email digest + portfolio + monthly journal
- Day 7 — Polish, defaults, README, simple/power mode toggle

## Disclaimer

Personal use. Educational. Not financial advice. You are the human in the loop for every real-money trade.
