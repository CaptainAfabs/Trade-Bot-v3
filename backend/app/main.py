from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.api import backtest, chat, health, investors, news, profiles, stocks
from app.config import settings
from app.db.database import init_db
from app.news.ingest import ingest_all
from app.news.sentiment import score_unscored


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(ingest_all, "interval", minutes=60, id="news_ingest", coalesce=True, max_instances=1)
    scheduler.add_job(score_unscored, "interval", minutes=15, id="news_score", coalesce=True, max_instances=1)
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="Stock Advisor",
    version="0.1.0",
    description="Personalized AI stock recommendations.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(profiles.router, prefix="/api/profiles", tags=["profiles"])
app.include_router(stocks.router, prefix="/api/stocks", tags=["stocks"])
app.include_router(investors.router, prefix="/api/investors", tags=["investors"])
app.include_router(news.router, prefix="/api/news", tags=["news"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
