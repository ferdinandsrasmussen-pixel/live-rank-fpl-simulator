import traceback

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import fpl_client
import llm
import run_store
from database import get_db
from models import AdvisorRun, Suggestion, Vote
from schemas import AdvisorRequest, AdvisorResponse

router = APIRouter()


def _build_community_context(db: Session, current_gw: int) -> tuple[str, int]:
    """
    Query recent votes and build a prose context string for Layer 2 RAG injection.
    Returns (context_string, total_relevant_votes).
    """
    min_gw = max(1, current_gw - 5)

    # Aggregate net votes per suggestion
    agg = db.execute(
        select(Vote.suggestion_id, func.sum(Vote.value).label("net"))
        .group_by(Vote.suggestion_id)
    ).all()

    rejected_ids = [r.suggestion_id for r in agg if (r.net or 0) <= -2]
    liked_ids = [r.suggestion_id for r in agg if (r.net or 0) >= 2]
    total_relevant = len(rejected_ids) + len(liked_ids)

    parts: list[str] = []

    if rejected_ids:
        rows = db.execute(
            select(Suggestion).where(
                Suggestion.id.in_(rejected_ids),
                Suggestion.gameweek >= min_gw,
            )
        ).scalars().all()
        if rows:
            parts.append("Transfers the community has REJECTED (net downvotes <= -2):")
            for s in rows[:5]:
                snippet = (s.reasoning or "")[:120]
                parts.append(f"  - {s.player_out_name} -> {s.player_in_name} (GW{s.gameweek}, {s.position}): {snippet}")

    if liked_ids:
        rows = db.execute(
            select(Suggestion).where(
                Suggestion.id.in_(liked_ids),
                Suggestion.gameweek >= min_gw,
            )
        ).scalars().all()
        if rows:
            parts.append("Transfers the community has LIKED (net upvotes >= 2):")
            for s in rows[:3]:
                snippet = (s.reasoning or "")[:120]
                parts.append(f"  - {s.player_out_name} -> {s.player_in_name} (GW{s.gameweek}, {s.position}): {snippet}")

    return "\n".join(parts), total_relevant


def _get_vote_counts(
    db: Session, suggestion_id: int, session_id: str
) -> tuple[int, int, int | None]:
    rows = db.execute(
        select(Vote.value, func.count(Vote.id).label("cnt"))
        .where(Vote.suggestion_id == suggestion_id)
        .group_by(Vote.value)
    ).all()
    thumbs_up = sum(r.cnt for r in rows if r.value == 1)
    thumbs_down = sum(r.cnt for r in rows if r.value == -1)

    user_vote = db.execute(
        select(Vote.value).where(
            Vote.suggestion_id == suggestion_id,
            Vote.session_id == session_id,
        )
    ).scalar_one_or_none()

    return thumbs_up, thumbs_down, user_vote


@router.post("/advisor", response_model=AdvisorResponse)
async def advisor(req: AdvisorRequest, db: Session = Depends(get_db)):
    stored = run_store.get_run(req.run_id)
    if not stored:
        raise HTTPException(
            status_code=404,
            detail="run_id not found — please run /api/simulate first, or refresh if the server restarted.",
        )

    bootstrap = await fpl_client.fetch_bootstrap()
    community_context, community_votes_count = _build_community_context(db, req.gw)

    try:
        result = await llm.run_advisor_pipeline(
            picks_df=stored["picks_df"],
            lookups=stored["lookups"],
            bootstrap=bootstrap,
            current_gw=req.gw,
            budget=req.budget,
            free_transfers=req.free_transfers,
            my_team_sims=stored["my_team_sims"],
            rivals_team_sims=stored["rivals_team_sims"],
            mode=stored["mode"],
            n_sims=stored["n_sims"],
            expected_minutes_not_started=stored["expected_minutes_not_started"],
            global_minutes_pregw=stored["global_minutes_pregw"],
            fpl_client_mod=fpl_client,
            community_context=community_context,
        )
    except Exception as exc:
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}\n\n{tb}")

    # Log this advisor run
    db.add(AdvisorRun(
        session_id=req.session_id,
        entry_id=req.entry_id,
        gameweek=req.gw,
        n_recommendations=len(result.get("recommendations", [])),
    ))

    # Upsert each suggestion; attach vote counts
    enriched: list[dict] = []
    for rec in result.get("recommendations", []):
        out_id = rec.get("player_out_id")
        in_id = rec.get("player_in_id")

        if not out_id or not in_id:
            enriched.append({**rec, "suggestion_id": None, "thumbs_up": 0, "thumbs_down": 0, "user_vote": None})
            continue

        existing = db.execute(
            select(Suggestion).where(
                Suggestion.gameweek == req.gw,
                Suggestion.player_out_id == out_id,
                Suggestion.player_in_id == in_id,
            )
        ).scalar_one_or_none()

        if existing:
            suggestion_id = existing.id
        else:
            s = Suggestion(
                gameweek=req.gw,
                player_out_id=out_id,
                player_in_id=in_id,
                player_out_name=rec.get("player_out"),
                player_in_name=rec.get("player_in"),
                position=rec.get("position"),
                reasoning=rec.get("reasoning"),
                confidence=rec.get("confidence"),
                rank_improvement=rec.get("rank_improvement"),
                cost_hit=rec.get("cost_hit", 0),
            )
            db.add(s)
            db.flush()
            suggestion_id = s.id

        up, down, user_vote = _get_vote_counts(db, suggestion_id, req.session_id)
        enriched.append({**rec, "suggestion_id": suggestion_id, "thumbs_up": up, "thumbs_down": down, "user_vote": user_vote})

    db.commit()

    return AdvisorResponse(
        risk_analysis=result.get("risk_analysis", []),
        recommendations=enriched,
        current_rank_p50=result.get("current_rank_p50", 0),
        community_context_used=bool(community_context),
        community_votes_count=community_votes_count,
        message=result.get("message"),
    )
