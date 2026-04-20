"""
Meta-analysis endpoint — Layer 3 of the feedback loop.
POST /api/meta/run: reads vote patterns, calls Cohere, stores summary.
GET  /api/meta:     returns the latest stored summary.
"""
import json
import os
import re

import cohere
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from database import get_db
from models import AdvisorRun, MetaAnalysis, Suggestion, Vote
from schemas import MetaAnalysisResponse

router = APIRouter()
MODEL = "command-a-03-2025"


@router.get("/meta", response_model=MetaAnalysisResponse)
def get_meta(db: Session = Depends(get_db)):
    row = db.execute(
        select(MetaAnalysis).order_by(desc(MetaAnalysis.created_at)).limit(1)
    ).scalar_one_or_none()

    if not row:
        return MetaAnalysisResponse()

    return MetaAnalysisResponse(
        id=row.id,
        summary=row.summary,
        liked_patterns=row.liked_patterns,
        rejected_patterns=row.rejected_patterns,
        gameweek_range=row.gameweek_range,
        created_at=str(row.created_at),
    )


@router.post("/meta/run", response_model=MetaAnalysisResponse)
def run_meta_analysis(db: Session = Depends(get_db)):
    api_key = os.getenv("COHERE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="COHERE_API_KEY not configured")

    # Pull suggestions that have at least one vote
    rows = db.execute(
        select(
            Suggestion.gameweek,
            Suggestion.player_out_name,
            Suggestion.player_in_name,
            Suggestion.position,
            Suggestion.confidence,
            Suggestion.reasoning,
            func.sum(Vote.value).label("net_votes"),
            func.count(Vote.id).label("total_votes"),
        )
        .join(Vote, Vote.suggestion_id == Suggestion.id)
        .group_by(Suggestion.id)
        .having(func.count(Vote.id) >= 1)
        .order_by(desc(func.count(Vote.id)))
        .limit(30)
    ).all()

    if not rows:
        raise HTTPException(status_code=400, detail="No voted suggestions yet — cast some votes first.")

    total_runs = db.execute(select(func.count(AdvisorRun.id))).scalar() or 0
    gw_min = db.execute(select(func.min(Suggestion.gameweek))).scalar() or 0
    gw_max = db.execute(select(func.max(Suggestion.gameweek))).scalar() or 0
    gameweek_range = f"GW{gw_min}–GW{gw_max}" if gw_min else "—"

    liked = [
        {
            "transfer": f"{r.player_out_name} -> {r.player_in_name}",
            "position": r.position,
            "gameweek": r.gameweek,
            "net_votes": int(r.net_votes or 0),
            "reasoning": (r.reasoning or "")[:150],
        }
        for r in rows if (r.net_votes or 0) > 0
    ]
    rejected = [
        {
            "transfer": f"{r.player_out_name} -> {r.player_in_name}",
            "position": r.position,
            "gameweek": r.gameweek,
            "net_votes": int(r.net_votes or 0),
            "reasoning": (r.reasoning or "")[:150],
        }
        for r in rows if (r.net_votes or 0) < 0
    ]

    prompt = f"""You are an FPL community analyst. Review this vote data on AI transfer suggestions.

Liked transfers (net upvotes):
{json.dumps(liked, indent=2)}

Rejected transfers (net downvotes):
{json.dumps(rejected, indent=2)}

Total advisor sessions run: {total_runs}
Gameweek range: {gameweek_range}

Write a short community insight (3-4 sentences). Focus on:
1. What patterns made suggestions popular vs rejected
2. Which position/type of transfer the community consistently liked or hated
3. One actionable takeaway for future recommendations

Return ONLY this JSON object, no other text:
{{
  "summary": "your 3-4 sentence community insight",
  "liked_patterns": ["pattern 1", "pattern 2"],
  "rejected_patterns": ["pattern 1", "pattern 2"]
}}"""

    client = cohere.Client(api_key=api_key)
    response = client.chat(model=MODEL, message=prompt)

    match = re.search(r"\{.*\}", response.text, re.DOTALL)
    if not match:
        raise HTTPException(status_code=500, detail="LLM did not return parseable JSON")

    parsed = json.loads(match.group())

    meta = MetaAnalysis(
        summary=parsed.get("summary", ""),
        liked_patterns=parsed.get("liked_patterns", []),
        rejected_patterns=parsed.get("rejected_patterns", []),
        gameweek_range=gameweek_range,
    )
    db.add(meta)
    db.commit()
    db.refresh(meta)

    return MetaAnalysisResponse(
        id=meta.id,
        summary=meta.summary,
        liked_patterns=meta.liked_patterns,
        rejected_patterns=meta.rejected_patterns,
        gameweek_range=meta.gameweek_range,
        created_at=str(meta.created_at),
    )
