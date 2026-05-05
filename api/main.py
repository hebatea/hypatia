"""
Hypatia History API.

Separate FastAPI service that shares the same database layer as the bot.
Run: uvicorn api.main:app --host 0.0.0.0 --port 8000

Endpoints:
  GET /health            — liveness check
  GET /history?token=xx  — validate magic link, return user history
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.db.engine import init_db, get_session
from app.db import repository as repo


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Hypatia API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ─── Response schemas ──────────────────────────────────────────────────────


class CheckinItem(BaseModel):
    date: str
    challenge: str
    gratitude: str
    intention: str


class HistoryResponse(BaseModel):
    first_name: str
    streak: int
    checkins: list[CheckinItem]


# ─── Endpoints ─────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/history", response_model=HistoryResponse)
async def get_history(token: str = Query(..., description="Magic link token")):
    async with get_session() as session:
        user_id = await repo.validate_token(session, token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or expired link.")

        user = await repo.get_user(session, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        checkins = await repo.get_recent_checkins(session, user_id, limit=30)

    return HistoryResponse(
        first_name=user.first_name or "Friend",
        streak=user.streak_count,
        checkins=[
            CheckinItem(
                date=c.created_at.strftime("%d %b %Y"),
                challenge=c.challenge,
                gratitude=c.gratitude,
                intention=c.intention,
            )
            for c in checkins
        ],
    )
