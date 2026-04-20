"""
Cohere multi-call LLM pipeline with community RAG injection.

Three-layer feedback loop:
  Layer 1 — votes are collected via /api/votes (see routers/votes.py)
  Layer 2 — community_context string (built in routers/advisor.py from vote DB)
             is injected into Call 2 prompt here
  Layer 3 — meta-analysis runs on demand via /api/meta/run (routers/meta.py)
"""
import json
import os
import re
from typing import Any

import cohere
import numpy as np

from simulation import simulate_with_transfer, rank_distribution

MODEL = "command-a-03-2025"


def _client() -> cohere.Client:
    key = os.getenv("COHERE_API_KEY", "")
    if not key:
        raise RuntimeError("COHERE_API_KEY not set — add it to your .env file")
    return cohere.Client(api_key=key)


def _parse_json_array(raw: str) -> list:
    """Robustly extract a JSON array from LLM output that may include prose."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"No JSON array found in LLM response: {raw[:300]}")


# ---------------------------------------------------------------------------
# Call 1 — Squad risk analysis
# ---------------------------------------------------------------------------

def call_risk_analysis(client: cohere.Client, player_contexts: list[dict]) -> list[dict]:
    prompt = f"""You are an expert Fantasy Premier League analyst.

I will give you data on a manager's starting XI players. For each player, assess:
1. Their SELL URGENCY (1-10, where 10 = must sell immediately)
2. Their key risk factors (injury, form, fixtures, ownership)
3. A brief one-line reasoning

Return ONLY a valid JSON array, no other text, no markdown, no backticks.
Format exactly like this:
[
  {{
    "name": "player name",
    "element_id": 123,
    "position": "MID",
    "sell_urgency": 7,
    "risk_factors": ["poor form", "difficult fixtures"],
    "reasoning": "One line explanation"
  }}
]

Squad data:
{json.dumps(player_contexts, indent=2)}

Scoring rules:
- Status not 'a' (injured/suspended): +4 urgency
- Form below 3.0: +2 urgency
- Average fixture difficulty next 3 GWs above 4.0: +2 urgency
- Goals+assists per90 below 0.1 for attackers/midfielders: +1 urgency
- Price above 10.0 with poor form: +1 urgency

Return only the JSON array."""

    response = client.chat(model=MODEL, message=prompt)
    return _parse_json_array(response.text)


# ---------------------------------------------------------------------------
# Call 2 — Transfer recommendations (with optional community RAG)
# ---------------------------------------------------------------------------

def call_transfer_recommendations(
    client: cohere.Client,
    risk_analysis: list[dict],
    targets_by_position: dict[str, list[dict]],
    budget: float,
    free_transfers: int,
    community_context: str = "",
) -> list[dict]:
    community_block = ""
    if community_context:
        community_block = (
            f"\n--- Community feedback from past suggestions ---\n"
            f"{community_context}\n"
            f"Factor this into your confidence scoring — if a transfer type has been "
            f"consistently downvoted, lower confidence accordingly.\n"
            f"---\n"
        )

    # --- SMOKE TEST LOG (remove before final submission) ---
    def _safe_print(s: str) -> None:
        """Print without crashing on Windows cp1252 terminals."""
        print(s.encode("ascii", errors="replace").decode("ascii"))
    _safe_print("\n" + "=" * 60)
    _safe_print("LLM CALL 2 -- community context injected:")
    if community_context:
        _safe_print(community_context)
    else:
        _safe_print("(none -- no votes with net <= -2 or >= +2 yet)")
    _safe_print("=" * 60 + "\n")

    prompt = f"""You are an expert Fantasy Premier League transfer advisor.
{community_block}
Context:
- Available budget: £{budget:.1f}m
- Free transfers available: {free_transfers}
- Taking extra transfers costs 4 points each

Risk analysis of current squad:
{json.dumps(risk_analysis, indent=2)}

Available transfer targets by position (sorted by form):
{json.dumps(targets_by_position, indent=2)}

Return ONLY a valid JSON array, no other text, no markdown, no backticks.
Format exactly like this:
[
  {{
    "rank": 1,
    "player_out": "Name of player to sell",
    "player_out_id": 123,
    "player_in": "Name of player to buy",
    "player_in_id": 456,
    "position": "MID",
    "cost_hit": 0,
    "reasoning": "2-3 sentences. Mention fixtures, form, and expected points impact.",
    "confidence": "High/Medium/Low"
  }}
]

Rules:
- Only recommend transfers where player_in appears in the targets list
- Account for budget constraints — player_in price must be affordable
- Prioritise players with sell_urgency >= 6
- If free_transfers >= 2, you may recommend 2 transfers
- confidence = High if sell_urgency >= 7 AND target form > 5, else Medium, else Low

Return only the JSON array."""

    response = client.chat(model=MODEL, message=prompt)
    print(f"[DIAG] Call 2 raw Cohere response (first 500 chars):")
    print(response.text[:500].encode("ascii", errors="replace").decode("ascii"))
    return _parse_json_array(response.text)


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------

async def build_player_context(
    picks_df: Any,
    lookups: dict,
    bootstrap: dict,
    current_gw: int,
    fpl_client_mod: Any,
) -> list[dict]:
    contexts = []
    for _, r in picks_df.iterrows():
        if int(r.get("pick_position", 99)) > 11:
            continue
        el = int(r["element"])
        team_id = int(r["team_id"])
        et = int(lookups["el_type"].get(el, 0))
        pos = lookups["type_short"].get(et, "?")

        upcoming = await fpl_client_mod.get_upcoming_fixture_difficulty(
            bootstrap, team_id, current_gw, n_ahead=3
        )
        avg_fdr = round(np.mean([f["difficulty"] for f in upcoming]), 1) if upcoming else 3.0
        next_fdr = upcoming[0]["difficulty"] if upcoming else 3

        contexts.append({
            "name": lookups["el_name"].get(el, str(el)),
            "element_id": el,
            "position": pos,
            "team": lookups["team_name"].get(team_id, str(team_id)),
            "price": lookups["el_price"].get(el, 0),
            "form": lookups["el_form"].get(el, 0),
            "goals_per90": round(lookups["g_per90"].get(el, 0), 3),
            "assists_per90": round(lookups["a_per90"].get(el, 0), 3),
            "selected_by_pct": lookups["el_selected_by"].get(el, 0),
            "status": lookups["el_status"].get(el, "a"),
            "news": lookups["el_news"].get(el, ""),
            "next_fixture_fdr": next_fdr,
            "avg_fdr_next3": avg_fdr,
            "is_captain": bool(r["is_captain"]),
            "multiplier": int(r["multiplier"]),
        })
    return contexts


async def get_top_targets(
    bootstrap: dict,
    lookups: dict,
    position: str,
    budget: float,
    current_gw: int,
    squad_ids: set,
    fpl_client_mod: Any,
    n: int = 8,
) -> list[dict]:
    targets = []
    for el, name in lookups["el_name"].items():
        et = lookups["el_type"].get(el, 0)
        pos = lookups["type_short"].get(et, "?")
        if pos != position or el in squad_ids:
            continue
        price = lookups["el_price"].get(el, 0)
        if price > budget + 0.1:
            continue
        if lookups["el_status"].get(el, "a") not in ("a", "d"):
            continue

        team_id = lookups["el_team"].get(el, 0)
        upcoming = await fpl_client_mod.get_upcoming_fixture_difficulty(
            bootstrap, team_id, current_gw, n_ahead=3
        )
        avg_fdr = round(np.mean([f["difficulty"] for f in upcoming]), 1) if upcoming else 3.0

        targets.append({
            "name": name, "element_id": el, "position": pos,
            "team": lookups["team_name"].get(team_id, str(team_id)),
            "price": price,
            "form": lookups["el_form"].get(el, 0),
            "goals_per90": round(lookups["g_per90"].get(el, 0), 3),
            "assists_per90": round(lookups["a_per90"].get(el, 0), 3),
            "selected_by_pct": lookups["el_selected_by"].get(el, 0),
            "avg_fdr_next3": avg_fdr,
            "next_fixture_fdr": upcoming[0]["difficulty"] if upcoming else 3,
        })

    targets.sort(key=lambda x: float(x["form"]), reverse=True)
    return targets[:n]


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

async def run_advisor_pipeline(
    picks_df: Any,
    lookups: dict,
    bootstrap: dict,
    current_gw: int,
    budget: float,
    free_transfers: int,
    my_team_sims: np.ndarray,
    rivals_team_sims: list[np.ndarray],
    mode: str,
    n_sims: int,
    expected_minutes_not_started: int,
    global_minutes_pregw: int,
    fpl_client_mod: Any,
    community_context: str = "",
) -> dict:
    client = _client()

    # Step 1: Player context for the starting XI
    player_contexts = await build_player_context(
        picks_df, lookups, bootstrap, current_gw, fpl_client_mod
    )

    # Step 2: LLM Call 1 — risk analysis
    risk_analysis = call_risk_analysis(client, player_contexts)

    # Step 3: Transfer targets for high-urgency positions
    high_urgency = [p for p in risk_analysis if p.get("sell_urgency", 0) >= 5]
    if not high_urgency:
        high_urgency = sorted(risk_analysis, key=lambda x: x.get("sell_urgency", 0), reverse=True)[:3]
    positions_needed = list(set(p["position"] for p in high_urgency)) or ["MID", "FWD"]

    squad_ids = set(int(picks_df["element"].iloc[i]) for i in range(len(picks_df)))

    # Budget ceiling per position = most expensive squad player in that slot + free bank
    squad_price_by_pos: dict[str, float] = {}
    for _, r in picks_df.iterrows():
        el = int(r["element"])
        pos = lookups["type_short"].get(lookups["el_type"].get(el, 0), "?")
        price = lookups["el_price"].get(el, 0)
        if pos not in squad_price_by_pos or price > squad_price_by_pos[pos]:
            squad_price_by_pos[pos] = price

    def _sp(s: str) -> None:
        """Safe print: won't crash on Windows cp1252 terminals."""
        print(s.encode("ascii", errors="replace").decode("ascii"))

    targets_by_position: dict[str, list] = {}
    for pos in positions_needed:
        # Widen budget: sell price of most expensive squad player + bank + 0.5 tolerance
        base_price = squad_price_by_pos.get(pos, 8.0)
        pos_budget = base_price + budget + 0.5  # extra tolerance for sideways moves

        targets = await get_top_targets(
            bootstrap, lookups, pos, pos_budget, current_gw, squad_ids, fpl_client_mod
        )
        _sp(f"[DIAG] pos={pos}  base={base_price}  bank={budget}  ceiling={pos_budget:.1f}  found={len(targets)}")

        # Progressive fallback: if < 5 targets, relax price cap to ALL affordable
        if len(targets) < 5:
            targets = await get_top_targets(
                bootstrap, lookups, pos, 99.0, current_gw, squad_ids, fpl_client_mod
            )
            _sp(f"[DIAG]   fallback (no price cap) -> found={len(targets)}")

        for t in targets[:3]:
            _sp(f"         {t['name']}  price={t['price']}  form={t['form']}")

        if targets:
            targets_by_position[pos] = targets
        else:
            _sp(f"[DIAG] WARNING: still 0 targets for {pos} after fallback — skipping")

    _sp(f"[DIAG] positions with targets: {list(targets_by_position.keys())}")

    if not targets_by_position:
        current_ranks = rank_distribution(my_team_sims, rivals_team_sims)
        return {
            "risk_analysis": risk_analysis,
            "recommendations": [],
            "current_rank_p50": int(np.percentile(current_ranks, 50)),
            "message": "No affordable transfer targets found. Try increasing your budget.",
        }

    # Step 4: LLM Call 2 — recommendations with community RAG
    recommendations = call_transfer_recommendations(
        client, risk_analysis, targets_by_position,
        budget, free_transfers, community_context
    )

    # Step 5: Monte Carlo validation per recommendation
    current_ranks = rank_distribution(my_team_sims, rivals_team_sims)
    current_rank_p50 = int(np.percentile(current_ranks, 50))

    for rec in recommendations:
        out_id = rec.get("player_out_id")
        in_id = rec.get("player_in_id")
        if not out_id or not in_id:
            continue

        new_sims = simulate_with_transfer(
            picks_df=picks_df,
            player_out_id=int(out_id),
            player_in_id=int(in_id),
            lookups=lookups,
            mode=mode,
            n_sims=n_sims,
            expected_minutes_not_started=expected_minutes_not_started,
            global_minutes_pregw=global_minutes_pregw,
        )
        if new_sims is not None:
            new_ranks = rank_distribution(new_sims, rivals_team_sims)
            rec["projected_rank_p50"] = int(np.percentile(new_ranks, 50))
            rec["projected_rank_p10"] = int(np.percentile(new_ranks, 10))
            rec["projected_rank_p90"] = int(np.percentile(new_ranks, 90))
            rec["rank_improvement"] = current_rank_p50 - rec["projected_rank_p50"]
            rec["projected_pts_p50"] = int(np.percentile(new_sims, 50))

    return {
        "risk_analysis": risk_analysis,
        "recommendations": recommendations,
        "current_rank_p50": current_rank_p50,
    }
