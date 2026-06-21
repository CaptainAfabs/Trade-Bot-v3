# Claude API usage

This project uses the Anthropic API in five places. Each one is documented here with the model choice, the prompt pattern, the cost order-of-magnitude, and the rationale.

---

## 1. Chat — Sonnet 4.6 + tool use

**File:** `backend/app/reasoning/chat.py`

The chat endpoint is an agentic tool-use loop:

```python
resp = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=2048,
    system=system_prompt,    # profile + house rules
    tools=TOOLS,             # 5-tool schema
    messages=history + [{"role": "user", "content": user_message}],
)

while resp.stop_reason == "tool_use":
    # execute each tool_use block, append tool_result, re-call
    ...
```

Five tools defined:

| Tool | Purpose |
|---|---|
| `get_stock_score(ticker, risk?, timeline?)` | Full snapshot + composite score for one US ticker |
| `list_recent_news(ticker?, min_impact?, limit?)` | Pull from `news_items` table |
| `list_investors(kind?)` | Browse the 29-name roster |
| `get_investor_holdings(slug)` | Live SEC EDGAR 13F fetch |
| `backtest_buy_hold(ticker, years)` | Returns total/annualized return, Sharpe, max drawdown |

The loop is capped at 6 iterations to avoid runaway costs. In practice 1-3 are typical.

**System prompt design.** The system prompt baked into every chat:
- Restates the user's profile (risk, timeline, capital, position-size limits, sector excludes)
- Encodes house rules — *"never invent numbers, always cite tools, riskier picks need more support"*
- Reminds the model this is recommend-only — *"never claim to have executed anything"*

**Why Sonnet not Haiku for chat.** Tool-use loops reward reasoning. Haiku is fine for the first tool call but struggles to synthesize 2-3 tool results into a profile-aware paragraph that quotes the user's specific limits. Sonnet 4.6 nails it in one shot.

**Sample successful run** (real, from `tests/smoke_news_chat.py`):

> *User: "Should I buy NVDA? Give me one paragraph."*
>
> Claude calls `get_stock_score(ticker="NVDA")` → 72.3, Grade B
> Claude calls `backtest_buy_hold(ticker="NVDA", years=5)` → 1043% / 63% annualized / 1.2 Sharpe / -66% max DD
> Claude returns:
>
> *"Yes, NVDA is a reasonable buy for your profile, but size it carefully. It scores a 72.3/100 (Grade B) — clearing your medium-risk threshold of 65 — driven by exceptional growth (91/100) and profitability (88/100): revenue has grown 65% YoY and over 1,200% in five years… For your $5,000 portfolio, the 15% max position rule limits you to ~$750 — that's the right discipline here given the volatility."*

Every number in that paragraph came from a tool call. The position-size math used the user's actual profile.

**Cost order-of-magnitude:** typical 2-tool turn ≈ **$0.02**. The system prompt is the same every turn and is a perfect candidate for prompt caching (planned, see *Optimizations* below).

---

## 2. News sentiment scoring — Haiku 4.5 + batched JSON

**File:** `backend/app/news/sentiment.py`

Every 15 minutes, pull up to 50 unscored headlines, batch into chunks of 25, send to Haiku:

```python
SYSTEM = """You score financial news headlines.

For each numbered headline below, return ONE line of JSON with this shape:
{"id": <int>, "sentiment": <-1.0..1.0>, "impact": <0..5>}
...
Return ONLY the lines of JSON, no preamble, no markdown fences."""

# user message: "1. Fed pauses rate hikes...\n2. NVDA beats earnings...\n..."
```

Parser is line-by-line JSON.loads tolerant of partial outputs (drops malformed lines, keeps valid ones). Updates `news_items` table with scores.

**Why Haiku.** Pure classification, no reasoning loop. Cost-sensitive (~200 headlines/day = 8 batches). Haiku 4.5 is fast enough and accurate enough on this task — verified by sampling outputs and comparing to my own labels.

**Cost:** ~$0.001 per batch of 25 → ~$0.10/month.

---

## 3. Candidate generation — Haiku 4.5 + JSON output

**File:** `backend/app/api/recommendations.py`

Replaces the older hardcoded 15-stock list. For each `(risk, timeline, sector_exclude)` profile combination, ask Haiku for 40 candidate tickers:

```python
SCREENER_SYSTEM = """You are a stock screener for a personal AI investment assistant.

Generate a list of US-listed stocks (NYSE / NASDAQ only, no OTC, no ADRs of micro-caps,
no penny stocks under $5) tailored to the investor profile below.

Match the candidates to the profile:
- low risk + long/generational: durable franchises, quality compounders, dividend payers...
- high risk + short: high-momentum names, recent breakouts, volatile growth stocks...
- avoid any sectors the user excluded

Return ONLY a JSON array of ticker strings. No commentary, no fences."""
```

Output is parsed with a forgiving JSON-array extractor (handles fences and stray prose if the model goes off-script). Cached 24h per profile config so we don't re-pay this cost on every dashboard load.

**Quality check** (real outputs from a medium-risk-long profile):
- AAPL, MSFT, GOOGL, AMZN, NVDA, META — expected mega-cap anchors
- TSLA, JPM, BAC, WFC, GS, BLK, SCHW, AXP — financials with reasonable diversity
- JNJ, PFE, UNH, ABBV, LLY, MRK — healthcare
- TJX, PYPL, HD, NFLX, LOW, SBUX — these surface real diversity the hardcoded list never would

One delisted ticker (SQ → Block, renamed XYZ) got rejected gracefully by the snapshot builder.

**Cost:** ~$0.001 per generation, cached 24h.

---

## 4. AI-add-investor — Haiku 4.5 + structured JSON

**File:** `backend/app/api/investors.py`

User types "Add Mohnish Pabrai" → Claude returns a single JSON object:

```json
{
  "slug": "pabrai-funds",
  "display_name": "Mohnish Pabrai",
  "kind": "individual",
  "cik": "0001394831",
  "description": "Value investor inspired by Buffett. Concentrated bets, low turnover.",
  "bio": "Founder of Pabrai Investment Funds. The Dhandho Investor author...",
  "photo_url": "https://upload.wikimedia.org/..."
}
```

System prompt mandates the exact JSON shape with no commentary. The endpoint inserts directly into the `investors` table on success.

**Why Haiku.** Cheap, fast, and the task is structured-output retrieval over general knowledge — no reasoning needed.

**Cost:** ~$0.002 per add.

---

## 5. Monthly journal review — Haiku 4.5 + Markdown synthesis

**File:** `backend/app/api/journal.py`

Pulls the last 30 days of `trade_journal` entries (decisions the user logged, with theses, bot scores, ratings, outcomes), serializes to JSON, asks Haiku for a structured Markdown summary:

```python
REVIEW_SYSTEM = """You are reviewing a personal investor's recent trade-decision journal.
Output a concise monthly review with these sections (markdown):

## Wins
## Misses
## Patterns to lean into
## Patterns to break
## One thing to try next month

Be specific — cite tickers and decisions. Two-to-four sentences per section."""
```

Returned text is rendered directly on the portfolio page.

**Cost:** ~$0.005 per review.

---

## Cost summary

Approximate per-month cost for typical personal use:

| Feature | Frequency | Cost/mo |
|---|---|---|
| Chat | 20 turns/day | ~$10 |
| News sentiment | 200 headlines/day | ~$0.10 |
| Candidate generation | Refreshed daily | ~$0.03 |
| AI-add-investor | Occasional | ~$0.01 |
| Monthly review | 1/month | ~$0.005 |
| **Total** | | **~$10/month** |

Well within the $50/month budget I set for personal use.

---

## Optimizations (in flight / future)

**Prompt caching.** The chat system prompt and the tool schema are stable across turns. Wrapping them with `cache_control: {"type": "ephemeral"}` would cut chat cost ~50% on multi-turn conversations. Not yet implemented — it's the next thing I'd ship.

**Streaming responses.** The chat endpoint currently uses sync `messages.create`. Switching to `messages.stream()` with SSE to the frontend would dramatically improve perceived latency (the first token arrives in 200-400ms vs waiting 3-8s for the full reply). Not yet implemented.

**Extended thinking for complex theses.** For deep ad-hoc questions ("Build me a thesis for buying ASML over TSMC"), extended thinking with Sonnet would justify the cost. Currently not used; the regular `messages.create` is sufficient for the chat patterns I tested.

**Vision for chart analysis.** Future: paste a stock chart into chat, have Claude analyze it. Trivial to add via the vision API once a use case demands it.

---

## Why this architecture

The project intentionally separates *data access* (snapshot builder, deterministic), *quant* (scoring engine, pure functions), and *reasoning* (Claude). Claude never directly fetches data — it calls our tools, which call our adapters, which return structured snapshots. This means:

1. **Determinism where it matters.** Stock scores don't change based on which model variant we use — they're a deterministic function of cached input data.
2. **Cost control.** Claude calls happen only at reasoning boundaries (chat, sentiment, screening). The expensive bits (60+ data points, scoring) are pure code.
3. **Auditability.** Every recommendation is reproducible from cached data + the scoring weights. The Claude calls are documented and bounded.
4. **Eval-friendly.** I can run the same input through the scoring engine deterministically and unit-test it. The Claude layer can be evaluated separately with its own rubric.

This was the single most important architectural decision in the project. LLMs are great at reasoning over structured data — bad at being the structured data source.
