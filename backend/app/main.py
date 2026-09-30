import asyncio
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from . import riot_client
from .aggregator import (
    aggregate_by_champion,
    compute_highlights,
    cs_timeline_stats,
    deaths_from_timelines,
    lane_diff_at,
)
from .config import MATCH_COUNT, DEFAULT_PLATFORM

app = FastAPI(title="Champion Performance Tracker API")

# No CORS middleware: the frontend is served from this same server in
# production and through Vite's /api proxy in dev, so every request is
# same-origin. Leaving CORS closed stops other sites from using this API
# (and your Riot rate limit) from their visitors' browsers.

# Built frontend (npm run build). Served at / when present so one process
# hosts the whole site; in dev the Vite server handles this instead.
FRONTEND_DIST = Path(
    os.getenv("FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist")
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/player/{game_name}/{tag_line}")
async def get_player_champion_stats(
    game_name: str,
    tag_line: str,
    platform: str = Query(default=DEFAULT_PLATFORM, description="e.g. na1, euw1, kr"),
    count: int = Query(default=MATCH_COUNT, ge=1, le=100),
):
    puuid = await riot_client.get_puuid(game_name, tag_line, platform)
    match_ids = await riot_client.get_match_ids(puuid, platform, count)

    if not match_ids:
        raise HTTPException(status_code=404, detail="No recent matches found for this player.")

    matches = await riot_client.get_matches(match_ids, platform)
    rows = aggregate_by_champion(matches, puuid)

    if not rows:
        raise HTTPException(status_code=404, detail="No usable match data (all games too short/remade?).")

    return {
        "riotId": f"{game_name}#{tag_line}",
        "puuid": puuid,
        "platform": platform,
        "matchesAnalyzed": len(matches),
        "champions": rows,
        "highlights": compute_highlights(rows),
    }


@app.get("/api/cs-phases")
async def get_cs_phases(
    puuid: str,
    match_ids: list[str] = Query(alias="matchId", max_length=100),
    platform: str = Query(default=DEFAULT_PLATFORM),
):
    """CS/min split into 0-15 / 15-25 / 25+, CS per game minute, and
    CS/gold vs. lane opponent @10. Separate from the main lookup because
    it needs one timeline request per match, so the frontend only calls it
    when a champion is expanded. Match details are normally cache hits."""
    timelines, matches, items = await asyncio.gather(
        riot_client.get_timelines(match_ids, platform),
        riot_client.get_matches(match_ids, platform),
        riot_client.get_item_data(),
    )
    return {
        **cs_timeline_stats(timelines, puuid),
        "laneAt10": lane_diff_at(timelines, matches, puuid, minute=10),
        "deaths": deaths_from_timelines(timelines, matches, puuid, items),
    }


# Mounted last so the /api routes above take precedence.
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
