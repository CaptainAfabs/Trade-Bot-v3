"""Daily digest builder. Assembles portfolio + watchlist + news into HTML and ships via Resend."""
from __future__ import annotations

import json
from datetime import datetime

import httpx

from app.config import settings
from app.db.database import connect
from app.portfolio.service import portfolio_summary
from app.quant.scoring import score_snapshot
from app.quant.snapshot import build_snapshot

RESEND_URL = "https://api.resend.com/emails"


async def _gather_watchlist(profile_id: int, risk: str, timeline: str) -> list[dict]:
    async with connect() as db:
        cur = await db.execute("SELECT ticker FROM watchlist WHERE profile_id = ? LIMIT 25", (profile_id,))
        rows = await cur.fetchall()
    out = []
    for (ticker,) in rows:
        try:
            snap = build_snapshot(ticker)
            score = score_snapshot(snap, risk=risk, timeline=timeline)
            out.append({
                "ticker": ticker,
                "name": snap.company_name,
                "price": snap.current_price,
                "score": score.composite,
                "grade": score.grade,
                "drivers": ", ".join(score.drivers_positive[:2]) or "—",
            })
        except Exception:
            pass
    out.sort(key=lambda x: (x["score"] or 0), reverse=True)
    return out


async def _gather_news(min_impact: float = 3, limit: int = 10) -> list[dict]:
    async with connect() as db:
        cur = await db.execute(
            """SELECT title, source, url, sentiment, impact, tickers
               FROM news_items
               WHERE impact >= ?
                 AND COALESCE(published_at, fetched_at) >= datetime('now', '-1 day')
               ORDER BY impact DESC, COALESCE(published_at, fetched_at) DESC
               LIMIT ?""",
            (min_impact, limit),
        )
        rows = await cur.fetchall()
    return [
        {"title": r[0], "source": r[1], "url": r[2], "sentiment": r[3], "impact": r[4],
         "tickers": json.loads(r[5] or "[]")}
        for r in rows
    ]


def _render_html(profile: dict, portfolio: dict, watchlist: list[dict], news: list[dict]) -> str:
    today = datetime.now().strftime("%A, %B %d, %Y")
    pnl_color = "#2E7D32" if portfolio["total_pnl_usd"] >= 0 else "#B22222"

    holding_rows = "".join(
        f"<tr><td style='padding:6px;border-bottom:1px solid #E5DCC2'>{h['ticker']}</td>"
        f"<td style='padding:6px;border-bottom:1px solid #E5DCC2;text-align:right'>{h['shares']:.2f}</td>"
        f"<td style='padding:6px;border-bottom:1px solid #E5DCC2;text-align:right'>${(h['market_value_usd'] or 0):,.0f}</td>"
        f"<td style='padding:6px;border-bottom:1px solid #E5DCC2;text-align:right;color:{'#2E7D32' if (h['pnl_pct'] or 0) >= 0 else '#B22222'}'>"
        f"{'+' if (h['pnl_pct'] or 0) >= 0 else ''}{(h['pnl_pct'] or 0):.1f}%</td></tr>"
        for h in portfolio["holdings"][:15]
    )
    watch_rows = "".join(
        f"<tr><td style='padding:6px;border-bottom:1px solid #E5DCC2'><strong>{w['ticker']}</strong></td>"
        f"<td style='padding:6px;border-bottom:1px solid #E5DCC2'>{w['name'] or ''}</td>"
        f"<td style='padding:6px;border-bottom:1px solid #E5DCC2;text-align:right'>{w['score']:.0f} ({w['grade']})</td>"
        f"<td style='padding:6px;border-bottom:1px solid #E5DCC2;font-size:12px;color:#6B6B6B'>{w['drivers']}</td></tr>"
        for w in watchlist[:10]
    ) or "<tr><td colspan='4' style='padding:6px;color:#6B6B6B'>No watchlist yet — add tickers from the dashboard.</td></tr>"
    news_items = "".join(
        f"<li style='margin:6px 0'><a href='{n['url']}' style='color:#004225;text-decoration:none'>{n['title']}</a>"
        f" <span style='color:#6B6B6B;font-size:12px'>· {n['source']}</span></li>"
        for n in news
    ) or "<li style='color:#6B6B6B'>Quiet news day.</li>"

    return f"""<!doctype html>
<html><body style='margin:0;padding:0;background:#FAF7F0;font-family:-apple-system,BlinkMacSystemFont,sans-serif;color:#1A1A1A'>
  <div style='max-width:640px;margin:0 auto;padding:24px'>
    <header style='border-bottom:2px solid #004225;padding-bottom:12px'>
      <h1 style='margin:0;color:#004225;font-size:22px'>Stock Advisor — daily brief</h1>
      <div style='color:#6B6B6B;font-size:13px;margin-top:4px'>{today} · profile: {profile['name']}</div>
    </header>

    <section style='margin-top:24px'>
      <h2 style='color:#004225;font-size:16px;border-bottom:1px solid #E5DCC2;padding-bottom:4px'>Portfolio</h2>
      <p style='margin:8px 0;font-size:15px'>
        ${portfolio['total_value_usd']:,.0f} across {portfolio['n_positions']} positions ·
        <span style='color:{pnl_color}'>{'+' if portfolio['total_pnl_usd'] >= 0 else ''}${portfolio['total_pnl_usd']:,.0f} ({portfolio['total_pnl_pct']:+.1f}%)</span>
      </p>
      <table style='border-collapse:collapse;width:100%;font-size:14px;margin-top:8px'>
        <thead><tr style='color:#6B6B6B;text-align:left'>
          <th style='padding:6px'>Ticker</th>
          <th style='padding:6px;text-align:right'>Shares</th>
          <th style='padding:6px;text-align:right'>Value</th>
          <th style='padding:6px;text-align:right'>P/L</th>
        </tr></thead><tbody>{holding_rows or "<tr><td colspan='4' style='padding:6px;color:#6B6B6B'>No positions yet.</td></tr>"}</tbody>
      </table>
    </section>

    <section style='margin-top:24px'>
      <h2 style='color:#004225;font-size:16px;border-bottom:1px solid #E5DCC2;padding-bottom:4px'>Top picks from your watchlist</h2>
      <table style='border-collapse:collapse;width:100%;font-size:14px;margin-top:8px'>
        <thead><tr style='color:#6B6B6B;text-align:left'>
          <th style='padding:6px'>Ticker</th>
          <th style='padding:6px'>Name</th>
          <th style='padding:6px;text-align:right'>Score</th>
          <th style='padding:6px'>Drivers</th>
        </tr></thead><tbody>{watch_rows}</tbody>
      </table>
    </section>

    <section style='margin-top:24px'>
      <h2 style='color:#004225;font-size:16px;border-bottom:1px solid #E5DCC2;padding-bottom:4px'>High-impact news</h2>
      <ul style='list-style:none;padding-left:0;margin-top:8px'>{news_items}</ul>
    </section>

    <footer style='margin-top:32px;padding-top:12px;border-top:1px solid #E5DCC2;color:#6B6B6B;font-size:12px'>
      Personal use · educational · not financial advice. Generated locally.
    </footer>
  </div>
</body></html>"""


async def build_and_send_digest(profile_id: int) -> dict:
    async with connect() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        cur = await db.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
        profile = await cur.fetchone()
    if not profile:
        return {"ok": False, "error": "profile not found"}

    portfolio = await portfolio_summary(profile_id)
    watchlist = await _gather_watchlist(profile_id, profile["risk"], profile["timeline"])
    news = await _gather_news(min_impact=3, limit=10)
    html = _render_html(profile, portfolio, watchlist, news)

    if not settings.resend_api_key or not settings.email_to:
        return {"ok": False, "error": "Resend not configured", "preview_html": html}

    try:
        r = httpx.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}", "Content-Type": "application/json"},
            json={
                "from": settings.email_from,
                "to": [settings.email_to],
                "subject": f"Stock Advisor brief — {datetime.now().strftime('%a %b %d')}",
                "html": html,
            },
            timeout=20,
        )
        r.raise_for_status()
    except Exception as e:
        return {"ok": False, "error": str(e), "preview_html": html}

    return {"ok": True, "to": settings.email_to, "id": r.json().get("id")}
