from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()  # load .env before any os.getenv() calls in imported modules

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text

import models  # noqa: F401 — registers all ORM models before create_all
from database import Base, SessionLocal, engine
from routers import advisor, meta, simulate, votes
from schemas import StatsResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (no-op if they already exist)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="FPL Rank Simulator API v2",
    version="2.0.0",
    description="FastAPI backend for the FPL Mini-League Rank Simulator — Monte Carlo engine, Cohere LLM advisor, community feedback loop.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten to Vercel URL in production via env var if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulate.router, prefix="/api", tags=["simulate"])
app.include_router(advisor.router, prefix="/api", tags=["advisor"])
app.include_router(votes.router, prefix="/api", tags=["votes"])
app.include_router(meta.router, prefix="/api", tags=["meta"])


@app.get("/health", tags=["infra"])
async def health():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "ok"
    except Exception as e:
        db_status = str(e)
    return {"status": "ok", "db": db_status}


@app.get("/api/current-gw", tags=["infra"])
async def current_gw():
    """Return the current active gameweek — used by the frontend to pre-fill the GW input."""
    import fpl_client as fc
    bootstrap = await fc.fetch_bootstrap()
    current = None
    for ev in bootstrap.get("events", []):
        if ev.get("is_current"):
            current = int(ev["id"])
            break
    if current is None:
        # Fall back to last finished
        finished = [int(e["id"]) for e in bootstrap.get("events", []) if e.get("finished")]
        current = max(finished) if finished else 1
    return {"gw": current}


@app.get("/api/stats", response_model=StatsResponse, tags=["infra"])
async def stats():
    from models import AdvisorRun, Suggestion, Vote

    db = SessionLocal()
    total_runs = db.execute(select(func.count(AdvisorRun.id))).scalar() or 0
    total_votes = db.execute(select(func.count(Vote.id))).scalar() or 0
    total_suggestions = db.execute(select(func.count(Suggestion.id))).scalar() or 0
    db.close()
    return StatsResponse(
        total_runs=int(total_runs),
        total_votes=int(total_votes),
        total_suggestions=int(total_suggestions),
    )
