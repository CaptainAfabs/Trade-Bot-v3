from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, profiles, stocks
from app.config import settings
from app.db.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


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
