"""Claude chat with tool use over our data layer.

Tools the model can call:
  - get_stock_score(ticker, risk, timeline)
  - list_recent_news(ticker?, hours)
  - list_investors(kind?)
  - get_investor_holdings(slug)
  - backtest_buy_hold(ticker, years)

The endpoint loops on tool_use blocks until the model returns plain text.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from app.backtest.buy_hold import run as run_backtest
from app.config import settings
from app.data import edgar_adapter
from app.db.database import connect
from app.profiles.models import Profile
from app.quant.scoring import score_snapshot
from app.quant.snapshot import build_snapshot
from app.reasoning import claude

TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_stock_score",
        "description": "Get full quant data and risk/timeline-weighted composite score for one US ticker.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "risk": {"type": "string", "enum": ["low", "medium", "high"]},
                "timeline": {"type": "string", "enum": ["short", "medium", "long", "generational"]},
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "list_recent_news",
        "description": "List recent financial news. Optionally filter by ticker or minimum impact (0-5).",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker":      {"type": "string"},
                "min_impact":  {"type": "number"},
                "limit":       {"type": "integer"},
            },
        },
    },
    {
        "name": "list_investors",
        "description": "List the roster of famous investors. Optional filter: kind in {fund, politician, individual}.",
        "input_schema": {
            "type": "object",
            "properties": {"kind": {"type": "string"}},
        },
    },
    {
        "name": "get_investor_holdings",
        "description": "Get top 13F holdings for a famous investor by slug (e.g. 'buffett-berkshire').",
        "input_schema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
    },
    {
        "name": "backtest_buy_hold",
        "description": "Backtest a buy-and-hold position. Returns total/annualized return, max drawdown, volatility, sharpe.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "years":  {"type": "number"},
            },
            "required": ["ticker"],
        },
    },
]


async def _t_get_stock_score(args: dict, profile: Profile) -> dict:
    ticker = (args.get("ticker") or "").upper()
    risk = args.get("risk") or profile.risk
    timeline = args.get("timeline") or profile.timeline
    snap = await asyncio.to_thread(build_snapshot, ticker)
    score = score_snapshot(snap, risk=risk, timeline=timeline)
    return {"snapshot": snap.model_dump(), "score": score.model_dump()}


async def _t_list_recent_news(args: dict) -> list[dict]:
    ticker = args.get("ticker")
    min_impact = float(args.get("min_impact") or 0)
    limit = min(int(args.get("limit") or 20), 50)
    sql = "SELECT source, url, title, published_at, tickers, sentiment, impact FROM news_items"
    where = []
    params: list = []
    if ticker:
        where.append("tickers LIKE ?")
        params.append(f"%\"{ticker.upper()}\"%")
    if min_impact > 0:
        where.append("impact >= ?")
        params.append(min_impact)
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY COALESCE(published_at, fetched_at) DESC LIMIT ?"
    params.append(limit)
    async with connect() as db:
        cur = await db.execute(sql, params)
        rows = await cur.fetchall()
    return [
        {"source": r[0], "url": r[1], "title": r[2], "published_at": r[3],
         "tickers": json.loads(r[4] or "[]"), "sentiment": r[5], "impact": r[6]}
        for r in rows
    ]


async def _t_list_investors(args: dict) -> list[dict]:
    kind = args.get("kind")
    sql = "SELECT slug, display_name, kind, description FROM investors"
    params: list = []
    if kind:
        sql += " WHERE kind = ?"
        params.append(kind)
    sql += " ORDER BY display_name"
    async with connect() as db:
        cur = await db.execute(sql, params)
        rows = await cur.fetchall()
    return [{"slug": r[0], "name": r[1], "kind": r[2], "description": r[3]} for r in rows]


async def _t_get_investor_holdings(args: dict) -> dict:
    slug = args.get("slug")
    async with connect() as db:
        cur = await db.execute("SELECT slug, display_name, kind, cik FROM investors WHERE slug = ?", (slug,))
        row = await cur.fetchone()
    if not row:
        return {"error": f"unknown slug: {slug}"}
    if row[2] == "politician" or not row[3]:
        return {"note": "13F not available for this investor (politicians or no CIK)."}
    data = await asyncio.to_thread(edgar_adapter.fetch_13f_holdings, row[3])
    if not data:
        return {"error": "no 13F found"}
    return {
        "investor": row[1],
        "period": data["period"],
        "total_value_usd": data["total_value_usd"],
        "top_holdings": data["holdings"][:15],
    }


async def _t_backtest_buy_hold(args: dict) -> dict:
    ticker = (args.get("ticker") or "").upper()
    years = float(args.get("years") or 5)
    result = await asyncio.to_thread(run_backtest, ticker, years)
    return result.__dict__ if result else {"error": "no price history"}


TOOL_HANDLERS = {
    "get_stock_score":         _t_get_stock_score,
    "list_recent_news":        _t_list_recent_news,
    "list_investors":          _t_list_investors,
    "get_investor_holdings":   _t_get_investor_holdings,
    "backtest_buy_hold":       _t_backtest_buy_hold,
}


def _system_prompt(profile: Profile) -> str:
    return f"""You are a personal stock-recommendation assistant for the user described below.

USER PROFILE
- name: {profile.name}
- risk: {profile.risk}
- timeline: {profile.timeline}
- capital: ${profile.capital_usd:,.0f}
- max position: {profile.max_position_pct}% per name
- max sector: {profile.max_sector_pct}%
- sectors excluded: {profile.sectors_exclude or 'none'}
- dividend-only mode: {profile.dividend_only}
- ESG-only mode: {profile.esg_only}

HOUSE RULES
- US market only.
- Use the tools to ground every recommendation in real data — never invent numbers.
- For low risk + generational: prioritize quality compounders, dividends, healthy balance sheets.
- For high risk + short: technicals matter most; growth and news matter; tolerate higher valuation.
- Riskier picks need MORE supporting evidence. State the composite score and which pillars are driving it.
- Be specific: name tickers, quote ratios, cite news.
- Be honest about misses ("insufficient data", "score below the threshold for your risk level").
- This is recommend-only — the user places trades themselves. Never claim to have executed anything."""


async def respond(profile: Profile, history: list[dict[str, Any]], message: str) -> dict[str, Any]:
    """history is a list of {role, content} messages from prior turns."""
    messages = list(history) + [{"role": "user", "content": message}]
    system = _system_prompt(profile)

    cli = claude.client()
    for _ in range(6):  # max 6 tool-use loops
        resp = await asyncio.to_thread(
            cli.messages.create,
            model=settings.claude_chat_model,
            max_tokens=2048,
            system=system,
            tools=TOOLS,
            messages=messages,
        )
        if resp.stop_reason != "tool_use":
            # final assistant text
            text_parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
            return {"reply": "".join(text_parts).strip(), "stop_reason": resp.stop_reason}

        # Run tools, append results
        messages.append({"role": "assistant", "content": [b.model_dump() for b in resp.content]})
        tool_results: list[dict[str, Any]] = []
        for block in resp.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            name = block.name
            handler = TOOL_HANDLERS.get(name)
            if not handler:
                output = {"error": f"unknown tool {name}"}
            else:
                try:
                    if name == "get_stock_score":
                        output = await handler(block.input, profile)
                    else:
                        output = await handler(block.input)
                except Exception as e:
                    output = {"error": str(e)}
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(output, default=str),
            })
        messages.append({"role": "user", "content": tool_results})

    return {"reply": "(reached tool-loop limit without final answer)", "stop_reason": "max_loops"}
