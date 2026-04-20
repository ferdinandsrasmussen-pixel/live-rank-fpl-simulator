from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, JSON

from database import Base


class Suggestion(Base):
    """
    One row per unique (gameweek, player_out, player_in) triplet.
    Votes from all users who received this recommendation aggregate here.
    """
    __tablename__ = "suggestions"

    id = Column(Integer, primary_key=True, index=True)
    gameweek = Column(Integer, nullable=False)
    player_out_id = Column(Integer, nullable=False)
    player_in_id = Column(Integer, nullable=False)
    player_out_name = Column(String(100))
    player_in_name = Column(String(100))
    position = Column(String(10))
    reasoning = Column(Text)
    confidence = Column(String(20))
    rank_improvement = Column(Integer, nullable=True)
    cost_hit = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("gameweek", "player_out_id", "player_in_id", name="uq_suggestion"),
    )


class Vote(Base):
    """One vote per (suggestion, session). value is +1 or -1."""
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True)
    suggestion_id = Column(Integer, ForeignKey("suggestions.id"), nullable=False)
    session_id = Column(String(64), nullable=False)
    value = Column(Integer, nullable=False)  # +1 or -1
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("suggestion_id", "session_id", name="uq_vote"),
    )


class MetaAnalysis(Base):
    """Stores one LLM-generated community summary per run."""
    __tablename__ = "meta_analyses"

    id = Column(Integer, primary_key=True, index=True)
    summary = Column(Text)
    liked_patterns = Column(JSON)
    rejected_patterns = Column(JSON)
    gameweek_range = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)


class AdvisorRun(Base):
    """Lightweight usage log — one row per advisor session."""
    __tablename__ = "advisor_runs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64))
    entry_id = Column(Integer)
    gameweek = Column(Integer)
    n_recommendations = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
