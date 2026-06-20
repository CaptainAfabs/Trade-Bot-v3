import json

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.db.database import connect
from app.news.ingest import ingest_all
from app.news.sentiment import score_unscored

router = APIRouter()


class NewsItem(BaseModel):
    id: int
    source: str
    url: str
    title: str
    summary: str | None
    published_at: str | None
    tickers: list[str]
    sentiment: float | None
    impact: float | None


@router.get("", response_model=list[NewsItem])
async def list_news(
    ticker: str | None = None,
    min_impact: float = 0,
    limit: int = Query(default=50, le=200),
):
    sql = "SELECT id, source, url, title, summary, published_at, tickers, sentiment, impact FROM news_items"
    params: list = []
    where = []
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
    out = []
    for r in rows:
        out.append(NewsItem(
            id=r[0], source=r[1], url=r[2], title=r[3], summary=r[4],
            published_at=r[5], tickers=json.loads(r[6] or "[]"),
            sentiment=r[7], impact=r[8],
        ))
    return out


@router.post("/ingest")
async def trigger_ingest():
    """Manual trigger; scheduler runs this hourly in the background."""
    results = await ingest_all()
    return {"inserted": results, "total": sum(results.values())}


@router.post("/score")
async def trigger_score(limit: int = 50):
    n = await score_unscored(limit=limit)
    return {"scored": n}
