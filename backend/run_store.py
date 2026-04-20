"""
In-memory store for simulation results.

After /simulate runs, the numpy arrays are stored here keyed by a UUID.
/advisor reads them by run_id to skip re-running the Monte Carlo.

This is intentionally simple — no Redis, no disk. Railway containers rarely
restart between a user's simulate→advise cycle, and for a demo the trade-off
(clean restart = stale run_id) is acceptable. Cap at 50 entries to avoid
unbounded memory growth.
"""
import uuid
from typing import Optional

import numpy as np
import pandas as pd

_store: dict[str, dict] = {}


def create_run(
    my_team_sims: np.ndarray,
    rivals_team_sims: list[np.ndarray],
    picks_df: pd.DataFrame,
    lookups: dict,
    mode: str,
    n_sims: int,
    expected_minutes_not_started: int,
    global_minutes_pregw: int,
) -> str:
    run_id = str(uuid.uuid4())
    _store[run_id] = {
        "my_team_sims": my_team_sims,
        "rivals_team_sims": rivals_team_sims,
        "picks_df": picks_df.copy(),
        "lookups": lookups,
        "mode": mode,
        "n_sims": n_sims,
        "expected_minutes_not_started": expected_minutes_not_started,
        "global_minutes_pregw": global_minutes_pregw,
    }
    # Evict oldest entries beyond cap
    if len(_store) > 50:
        oldest_key = next(iter(_store))
        del _store[oldest_key]
    return run_id


def get_run(run_id: str) -> Optional[dict]:
    return _store.get(run_id)
