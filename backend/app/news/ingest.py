"""Pull RSS feeds and insert new items into news_items. Idempotent on URL."""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime

import feedparser

from app.db.database import connect

from .feeds import FEEDS

# Simple ticker detector. Avoids common false positives by requiring caps + length.
_TICKER_RE = re.compile(r"\b([A-Z]{2,5})\b")
_TICKER_STOPWORDS = {
    "USA", "CEO", "CFO", "CTO", "COO", "IPO", "ETF", "GDP", "CPI", "PPI", "FED",
    "FOMC", "EPS", "USD", "EUR", "GBP", "JPY", "CAD", "OPEC", "BIDEN", "TRUMP",
    "NYSE", "NASDAQ", "SEC", "FTC", "DOJ", "EPA", "FDA", "API", "AI", "ML",
}


def _extract_tickers(text: str) -> list[str]:
    candidates = set(_TICKER_RE.findall(text or ""))
    return sorted(t for t in candidates if t not in _TICKER_STOPWORDS and len(t) <= 5)


def _published_iso(entry) -> str | None:
    try:
        if entry.get("published_parsed"):
            return datetime(*entry.published_parsed[:6]).isoformat()
    except Exception:
        pass
    return entry.get("published")


async def _insert_items(items: list[dict]) -> int:
    if not items:
        return 0
    n = 0
    async with connect() as db:
        for it in items:
            try:
                cur = await db.execute(
                    """INSERT OR IGNORE INTO news_items
                       (source, url, title, summary, published_at, tickers)
                       VALUES (?,?,?,?,?,?)""",
                    (it["source"], it["url"], it["title"], it.get("summary"),
                     it.get("published_at"), json.dumps(it.get("tickers", []))),
                )
                if cur.rowcount:
                    n += 1
            except Exception:
                pass
        await db.commit()
    return n


def _fetch_one(feed_meta: dict) -> list[dict]:
    parsed = feedparser.parse(feed_meta["url"])
    out = []
    for entry in parsed.entries[:30]:
        title = (entry.get("title") or "").strip()
        url = (entry.get("link") or "").strip()
        if not title or not url:
            continue
        summary = (entry.get("summary") or "").strip()[:1500]
        tickers = _extract_tickers(f"{title} {summary}")
        out.append({
            "source": feed_meta["source"],
            "url": url,
            "title": title,
            "summary": summary,
            "published_at": _published_iso(entry),
            "tickers": tickers,
        })
    return out


async def ingest_all() -> dict[str, int]:
    """Returns {feed_name: rows_inserted}."""
    results: dict[str, int] = {}
    # feedparser is sync; run in threadpool, but per-feed (small, parallel-safe)
    tasks = [asyncio.to_thread(_fetch_one, f) for f in FEEDS]
    fetched = await asyncio.gather(*tasks, return_exceptions=True)
    for f, items in zip(FEEDS, fetched):
        if isinstance(items, Exception):
            results[f["source"]] = 0
            continue
        results[f["source"]] = await _insert_items(items)
    return results
