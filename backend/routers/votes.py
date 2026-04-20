from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import get_db
from models import Suggestion, Vote
from schemas import VoteRequest, VoteResponse, VoteStatus

router = APIRouter()


def _vote_counts(db: Session, suggestion_id: int) -> tuple[int, int]:
    rows = db.execute(
        select(Vote.value, func.count(Vote.id).label("cnt"))
        .where(Vote.suggestion_id == suggestion_id)
        .group_by(Vote.value)
    ).all()
    up = sum(r.cnt for r in rows if r.value == 1)
    down = sum(r.cnt for r in rows if r.value == -1)
    return up, down


@router.post("/votes", response_model=VoteResponse)
def cast_vote(req: VoteRequest, db: Session = Depends(get_db)):
    if not db.get(Suggestion, req.suggestion_id):
        raise HTTPException(status_code=404, detail="Suggestion not found")

    existing = db.execute(
        select(Vote).where(
            Vote.suggestion_id == req.suggestion_id,
            Vote.session_id == req.session_id,
        )
    ).scalar_one_or_none()

    if existing:
        existing.value = req.value  # toggle / change
    else:
        db.add(Vote(
            suggestion_id=req.suggestion_id,
            session_id=req.session_id,
            value=req.value,
        ))

    db.commit()
    up, down = _vote_counts(db, req.suggestion_id)
    return VoteResponse(ok=True, thumbs_up=up, thumbs_down=down, net_votes=up - down)


@router.get("/votes/{suggestion_id}", response_model=VoteStatus)
def get_votes(suggestion_id: int, session_id: str = "", db: Session = Depends(get_db)):
    up, down = _vote_counts(db, suggestion_id)

    user_vote = None
    if session_id:
        user_vote = db.execute(
            select(Vote.value).where(
                Vote.suggestion_id == suggestion_id,
                Vote.session_id == session_id,
            )
        ).scalar_one_or_none()

    return VoteStatus(thumbs_up=up, thumbs_down=down, net_votes=up - down, user_vote=user_vote)
