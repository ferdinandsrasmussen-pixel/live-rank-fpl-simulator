"""
FPL API client with in-memory TTL cache.
All HTTP calls use httpx (async). build_lookups / build_picks_df are sync
helpers that transform raw JSON into the structures simulation.py expects.
"""
import time
from typing import Optional

import httpx
import numpy as np
import pandas as pd

BASE = "https://fantasy.premierleague.com/api"

_cache: dict[str, tuple[float, object]] = {}  # url -> (timestamp, data)


async def _get(url: str, ttl: int = 300) -> dict:
    now = time.monotonic()
    if url in _cache:
        ts, data = _cache[url]
        if now - ts < ttl:
            return data  # type: ignore

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()

    _cache[url] = (now, data)
    return data  # type: ignore


async def fetch_bootstrap() -> dict:
    return await _get(f"{BASE}/bootstrap-static/", ttl=600)


async def fetch_event_live(gw: int) -> dict:
    return await _get(f"{BASE}/event/{gw}/live/", ttl=120)


async def fetch_entry_picks(entry_id: int, gw: int) -> dict:
    return await _get(f"{BASE}/entry/{entry_id}/event/{gw}/picks/", ttl=120)


async def fetch_league_standings(league_id: int, page: int = 1) -> dict:
    url = f"{BASE}/leagues-classic/{league_id}/standings/?page_standings={page}"
    return await _get(url, ttl=300)


async def fetch_fixtures() -> list:
    return await _get(f"{BASE}/fixtures/", ttl=3600)  # type: ignore


# ---------------------------------------------------------------------------
# Build lookup dicts from bootstrap JSON
# ---------------------------------------------------------------------------

def build_lookups(bootstrap: dict) -> dict:
    el_name: dict[int, str] = {}
    el_team: dict[int, int] = {}
    el_type: dict[int, int] = {}
    g_per90: dict[int, float] = {}
    a_per90: dict[int, float] = {}
    el_form: dict[int, float] = {}
    el_price: dict[int, float] = {}
    el_selected_by: dict[int, float] = {}
    el_status: dict[int, str] = {}
    el_news: dict[int, str] = {}

    for e in bootstrap["elements"]:
        el = int(e["id"])
        el_name[el] = e["web_name"]
        el_team[el] = int(e["team"])
        el_type[el] = int(e["element_type"])
        mins = float(e.get("minutes", 0) or 0)
        g = float(e.get("goals_scored", 0) or 0)
        a = float(e.get("assists", 0) or 0)
        g_per90[el] = (g / mins * 90.0) if mins > 0 else 0.0
        a_per90[el] = (a / mins * 90.0) if mins > 0 else 0.0
        el_form[el] = float(e.get("form", 0) or 0)
        el_price[el] = int(e.get("now_cost", 0) or 0) / 10.0
        el_selected_by[el] = float(e.get("selected_by_percent", 0) or 0)
        el_status[el] = e.get("status", "a")
        el_news[el] = e.get("news", "") or ""

    team_cs_prob: dict[int, float] = {}
    team_name: dict[int, str] = {}
    for t in bootstrap["teams"]:
        tid = int(t["id"])
        played = float(t.get("played", 0) or 0)
        cs = float(t.get("clean_sheets", 0) or 0)
        team_cs_prob[tid] = (cs / played) if played > 0 else 0.30
        team_name[tid] = t.get("short_name", str(tid))

    type_short: dict[int, str] = {}
    for et in bootstrap["element_types"]:
        type_short[int(et["id"])] = et["singular_name_short"]

    return {
        "el_name": el_name, "el_team": el_team, "el_type": el_type,
        "g_per90": g_per90, "a_per90": a_per90,
        "team_cs_prob": team_cs_prob, "team_name": team_name,
        "type_short": type_short,
        "el_form": el_form, "el_price": el_price,
        "el_selected_by": el_selected_by,
        "el_status": el_status, "el_news": el_news,
    }


def build_live_maps(live_json: dict) -> dict:
    minutes: dict[int, int] = {}
    total_points: dict[int, int] = {}
    clean_sheets: dict[int, int] = {}

    for it in live_json.get("elements", []):
        el = int(it["id"])
        stt = it.get("stats", {}) or {}
        minutes[el] = int(stt.get("minutes", 0) or 0)
        total_points[el] = int(stt.get("total_points", 0) or 0)
        clean_sheets[el] = int(stt.get("clean_sheets", 0) or 0)

    return {"minutes": minutes, "total_points": total_points, "clean_sheets": clean_sheets}


def build_picks_df(
    entry_picks_json: dict,
    lookups: dict,
    live_maps: Optional[dict],
    mode: str,
) -> tuple[pd.DataFrame, dict, Optional[str]]:
    picks = entry_picks_json.get("picks", [])
    entry_history = entry_picks_json.get("entry_history", {}) or {}
    chip = entry_picks_json.get("active_chip", None)

    rows = []
    for p in picks:
        el = int(p["element"])
        mult = int(p.get("multiplier", 1))
        pos = lookups["type_short"].get(lookups["el_type"].get(el, 0), "?")
        team_id = lookups["el_team"].get(el, 0)

        if mode == "Live" and live_maps is not None:
            mins = int(live_maps["minutes"].get(el, 0))
            live_pts = int(live_maps["total_points"].get(el, 0))
            cur_cs = int(live_maps["clean_sheets"].get(el, 0))
        else:
            mins, live_pts, cur_cs = 0, 0, 0

        rows.append({
            "element": el,
            "player": lookups["el_name"].get(el, str(el)),
            "pos": pos,
            "team_id": int(team_id),
            "multiplier": mult,
            "is_captain": bool(p.get("is_captain", False)),
            "minutes": mins,
            "live_points": live_pts,
            "cur_cs": cur_cs,
            "pick_position": int(p.get("position", 0)),
        })

    df = pd.DataFrame(rows).sort_values("pick_position").reset_index(drop=True)
    return df, entry_history, chip


async def get_upcoming_fixture_difficulty(
    bootstrap: dict,
    team_id: int,
    current_gw: int,
    n_ahead: int = 3,
) -> list[dict]:
    try:
        fixtures = await fetch_fixtures()
        team_fixtures = []
        for f in fixtures:
            gw = f.get("event")
            if gw is None or gw <= current_gw:
                continue
            if f.get("team_h") == team_id:
                team_fixtures.append({
                    "gw": gw,
                    "difficulty": f.get("team_h_difficulty", 3),
                    "home": True,
                })
            elif f.get("team_a") == team_id:
                team_fixtures.append({
                    "gw": gw,
                    "difficulty": f.get("team_a_difficulty", 3),
                    "home": False,
                })
        team_fixtures.sort(key=lambda x: x["gw"])
        return team_fixtures[:n_ahead]
    except Exception:
        return []
