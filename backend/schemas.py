from typing import Optional
from pydantic import BaseModel, field_validator


class SimulateRequest(BaseModel):
    entry_id: int
    gw: int
    league_id: int
    mode: str = "Live"
    n_sims: int = 2000
    rivals_to_sim: int = 8

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ("Live", "Pre-GW"):
            raise ValueError("mode must be 'Live' or 'Pre-GW'")
        return v

    @field_validator("n_sims")
    @classmethod
    def validate_n_sims(cls, v: int) -> int:
        return max(500, min(v, 10000))


class RivalSummary(BaseModel):
    entry: int
    name: str
    league_rank: int
    p10: int
    p50: int
    p90: int


class PlayerProjection(BaseModel):
    player: str
    pos: str
    p10: float
    p50: float
    p90: float
    mean: float


class SimulateResponse(BaseModel):
    run_id: str
    my_p10: int
    my_p50: int
    my_p90: int
    rank_p10: int
    rank_p50: int
    rank_p90: int
    p_win: float
    p_top3: float
    rivals_summary: list[RivalSummary]
    player_projections: list[PlayerProjection]
    rank_histogram: list[dict]


class AdvisorRequest(BaseModel):
    run_id: str
    budget: float = 0.5
    free_transfers: int = 1
    session_id: str
    entry_id: int
    gw: int


class RiskEntry(BaseModel):
    name: str
    element_id: int
    position: str
    sell_urgency: int
    risk_factors: list[str]
    reasoning: str


class Recommendation(BaseModel):
    rank: int
    player_out: str
    player_out_id: int
    player_in: str
    player_in_id: int
    position: str
    cost_hit: int = 0
    reasoning: str
    confidence: str
    projected_rank_p50: Optional[int] = None
    projected_rank_p10: Optional[int] = None
    projected_rank_p90: Optional[int] = None
    rank_improvement: Optional[int] = None
    projected_pts_p50: Optional[int] = None
    suggestion_id: Optional[int] = None
    thumbs_up: int = 0
    thumbs_down: int = 0
    user_vote: Optional[int] = None


class AdvisorResponse(BaseModel):
    risk_analysis: list[RiskEntry]
    recommendations: list[Recommendation]
    current_rank_p50: int
    community_context_used: bool
    community_votes_count: int
    message: Optional[str] = None


class VoteRequest(BaseModel):
    suggestion_id: int
    session_id: str
    value: int  # +1 or -1

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: int) -> int:
        if v not in (1, -1):
            raise ValueError("value must be 1 or -1")
        return v


class VoteResponse(BaseModel):
    ok: bool
    thumbs_up: int
    thumbs_down: int
    net_votes: int


class VoteStatus(BaseModel):
    thumbs_up: int
    thumbs_down: int
    net_votes: int
    user_vote: Optional[int] = None


class MetaAnalysisResponse(BaseModel):
    id: Optional[int] = None
    summary: Optional[str] = None
    liked_patterns: Optional[list] = None
    rejected_patterns: Optional[list] = None
    gameweek_range: Optional[str] = None
    created_at: Optional[str] = None


class StatsResponse(BaseModel):
    total_runs: int
    total_votes: int
    total_suggestions: int
