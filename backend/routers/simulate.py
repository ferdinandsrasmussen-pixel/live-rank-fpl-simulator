import asyncio

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException

import fpl_client
import run_store
from schemas import SimulateRequest, SimulateResponse
from simulation import rank_distribution, simulate_player_deltas, summarize_player_sims

router = APIRouter()


@router.post("/simulate", response_model=SimulateResponse)
async def simulate(req: SimulateRequest):
    # Fetch bootstrap + optionally live data
    bootstrap = await fpl_client.fetch_bootstrap()
    lookups = fpl_client.build_lookups(bootstrap)

    live_maps = None
    if req.mode == "Live":
        try:
            live_json = await fpl_client.fetch_event_live(req.gw)
            live_maps = fpl_client.build_live_maps(live_json)
        except Exception:
            live_maps = fpl_client.build_live_maps({"elements": []})

    # Load my team
    try:
        my_picks_json = await fpl_client.fetch_entry_picks(req.entry_id, req.gw)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load team picks: {e}")

    my_df, my_entry_history, _ = fpl_client.build_picks_df(
        my_picks_json, lookups, live_maps, req.mode
    )

    expected_minutes = 75 if req.mode == "Live" else 90
    global_minutes_pregw = 90

    # Run my simulation in a thread (CPU-bound numpy work)
    rng = np.random.default_rng(42)
    my_player_sims, my_team_sims = await asyncio.to_thread(
        simulate_player_deltas,
        my_df, lookups, req.mode, req.n_sims, rng,
        expected_minutes, {}, global_minutes_pregw,
    )

    # Load league standings
    try:
        standings_json = await fpl_client.fetch_league_standings(req.league_id)
        results = standings_json.get("standings", {}).get("results", []) or []
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not load league: {e}")

    rivals = [
        {
            "entry": int(r.get("entry", 0)),
            "name": r.get("entry_name", ""),
            "league_rank": int(r.get("rank", 0) or 0),
        }
        for r in results
        if int(r.get("entry", 0)) not in (0, req.entry_id)
    ][: req.rivals_to_sim]

    rivals_team_sims: list[np.ndarray] = []
    rivals_summary = []

    for idx, rv in enumerate(rivals):
        rid = rv["entry"]
        try:
            rpicks_json = await fpl_client.fetch_entry_picks(rid, req.gw)
            rpicks_df, _, _ = fpl_client.build_picks_df(rpicks_json, lookups, live_maps, req.mode)
        except Exception:
            continue

        rrng = np.random.default_rng(1000 + idx)
        _, r_team_sims = await asyncio.to_thread(
            simulate_player_deltas,
            rpicks_df, lookups, req.mode, req.n_sims, rrng,
            expected_minutes, {}, global_minutes_pregw,
        )
        rivals_team_sims.append(r_team_sims)
        rp10, rp50, rp90 = np.percentile(r_team_sims, [10, 50, 90]).astype(int)
        rivals_summary.append({
            "entry": rid, "name": rv["name"], "league_rank": rv["league_rank"],
            "p10": int(rp10), "p50": int(rp50), "p90": int(rp90),
        })

    ranks = rank_distribution(my_team_sims, rivals_team_sims)
    r_p10, r_p50, r_p90 = np.percentile(ranks, [10, 50, 90]).astype(int)
    my_p10, my_p50, my_p90 = np.percentile(my_team_sims, [10, 50, 90]).astype(int)

    # Histogram for rank chart
    rank_counts = pd.Series(ranks).value_counts().sort_index()
    rank_histogram = [{"rank": int(k), "count": int(v)} for k, v in rank_counts.items()]

    # Stash arrays for /advisor
    run_id = run_store.create_run(
        my_team_sims=my_team_sims,
        rivals_team_sims=rivals_team_sims,
        picks_df=my_df,
        lookups=lookups,
        mode=req.mode,
        n_sims=req.n_sims,
        expected_minutes_not_started=expected_minutes,
        global_minutes_pregw=global_minutes_pregw,
    )

    return SimulateResponse(
        run_id=run_id,
        my_p10=int(my_p10), my_p50=int(my_p50), my_p90=int(my_p90),
        rank_p10=int(r_p10), rank_p50=int(r_p50), rank_p90=int(r_p90),
        p_win=float(np.mean(ranks == 1)),
        p_top3=float(np.mean(ranks <= 3)),
        rivals_summary=rivals_summary,
        player_projections=summarize_player_sims(my_df, my_player_sims),
        rank_histogram=rank_histogram,
    )
