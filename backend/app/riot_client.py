"""
Thin async client around the Riot Games REST API.

Handles:
- Account-V5 lookup (Riot ID -> PUUID)
- Match-V5 match id list
- Match-V5 match details (with a simple in-memory cache, since match
  data is immutable once a game is finished)
- Basic rate-limit awareness (respects 429 Retry-After)
"""
import asyncio
import httpx
from fastapi import HTTPException

from .config import RIOT_API_KEY, PLATFORM_TO_REGION

# Very small in-memory cache: match_id -> match json.
# Fine for a portfolio project / dev key usage; swap for redis/sqlite
# if this ever needs to survive restarts or run multi-process.
_match_cache: dict[str, dict] = {}
_timeline_cache: dict[str, dict] = {}
_item_data: dict[str, dict] | None = None

DDRAGON = "https://ddragon.leagueoflegends.com"


def _headers():
    if not RIOT_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Server is missing RIOT_API_KEY. Set it in backend/.env",
        )
    return {"X-Riot-Token": RIOT_API_KEY}


async def _get(client: httpx.AsyncClient, url: str, params: dict | None = None):
    """GET with basic 429 retry handling."""
    for attempt in range(3):
        resp = await client.get(url, headers=_headers(), params=params)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "1"))
            await asyncio.sleep(retry_after)
            continue
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Not found on Riot's side.")
        if resp.status_code == 403:
            raise HTTPException(
                status_code=403,
                detail="Riot API key rejected (expired or invalid). "
                "Dev keys expire every 24h — grab a new one from the Riot dev portal.",
            )
        resp.raise_for_status()
        return resp.json()
    raise HTTPException(status_code=429, detail="Rate limited by Riot API, try again shortly.")


def region_for_platform(platform: str) -> str:
    region = PLATFORM_TO_REGION.get(platform.lower())
    if not region:
        raise HTTPException(status_code=400, detail=f"Unknown platform '{platform}'.")
    return region


async def get_puuid(game_name: str, tag_line: str, platform: str) -> str:
    region = region_for_platform(platform)
    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    async with httpx.AsyncClient(timeout=10) as client:
        data = await _get(client, url)
    return data["puuid"]


async def get_match_ids(puuid: str, platform: str, count: int) -> list[str]:
    region = region_for_platform(platform)
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    async with httpx.AsyncClient(timeout=10) as client:
        data = await _get(client, url, params={"start": 0, "count": count})
    return data


async def get_match(match_id: str, platform: str) -> dict:
    if match_id in _match_cache:
        return _match_cache[match_id]

    region = region_for_platform(platform)
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    async with httpx.AsyncClient(timeout=10) as client:
        data = await _get(client, url)

    _match_cache[match_id] = data
    return data


async def get_timeline(match_id: str, platform: str) -> dict:
    """Minute-by-minute frames for a match. Only fetched on demand (e.g.
    for CS-by-phase) since it's one extra request per match."""
    if match_id in _timeline_cache:
        return _timeline_cache[match_id]

    region = region_for_platform(platform)
    url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
    async with httpx.AsyncClient(timeout=10) as client:
        data = await _get(client, url)

    _timeline_cache[match_id] = data
    return data


async def get_item_data() -> dict[str, dict] | None:
    """Item prices/recipes from Data Dragon (static CDN, no API key or
    rate limit). Uses the latest patch for every game, so prices from
    older patches can be slightly off. Returns None if unreachable."""
    global _item_data
    if _item_data is not None:
        return _item_data
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            versions = (await client.get(f"{DDRAGON}/api/versions.json")).raise_for_status().json()
            resp = await client.get(f"{DDRAGON}/cdn/{versions[0]}/data/en_US/item.json")
            _item_data = resp.raise_for_status().json()["data"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError):
        return None
    return _item_data


async def _gather_limited(fetch_one, match_ids: list[str], platform: str, concurrency: int):
    semaphore = asyncio.Semaphore(concurrency)

    async def fetch(mid: str):
        async with semaphore:
            return await fetch_one(mid, platform)

    return await asyncio.gather(*(fetch(mid) for mid in match_ids))


async def get_matches(match_ids: list[str], platform: str, concurrency: int = 5) -> list[dict]:
    """Fetch several matches concurrently, capped so we don't blow past
    Riot's dev-key rate limit (20 req / 1s, 100 req / 2min)."""
    return await _gather_limited(get_match, match_ids, platform, concurrency)


async def get_timelines(match_ids: list[str], platform: str, concurrency: int = 5) -> list[dict]:
    return await _gather_limited(get_timeline, match_ids, platform, concurrency)
