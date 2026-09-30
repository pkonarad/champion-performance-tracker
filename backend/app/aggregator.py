"""
Turns a list of raw Match-V5 match objects into per-champion aggregate
statistics for one player (identified by puuid).
"""


def _empty_stats():
    return {
        "games": 0,
        "wins": 0,
        "kills": 0,
        "deaths": 0,
        "assists": 0,
        "cs": 0,
        "damage": 0,
        "gold": 0,
        "vision": 0,
        "seconds": 0,
        "matchIds": [],
    }


def aggregate_by_champion(matches: list[dict], puuid: str) -> dict:
    champions: dict[str, dict] = {}

    for match in matches:
        info = match.get("info", {})
        # Skip remakes / very short games — they skew CS/min and damage/min.
        if info.get("gameDuration", 0) < 300:
            continue

        participant = next(
            (p for p in info.get("participants", []) if p.get("puuid") == puuid),
            None,
        )
        if participant is None:
            continue

        champ = participant["championName"]
        stats = champions.setdefault(champ, _empty_stats())

        stats["matchIds"].append(match["metadata"]["matchId"])
        stats["games"] += 1
        stats["wins"] += int(participant["win"])
        stats["kills"] += participant["kills"]
        stats["deaths"] += participant["deaths"]
        stats["assists"] += participant["assists"]
        stats["cs"] += (
            participant.get("totalMinionsKilled", 0)
            + participant.get("neutralMinionsKilled", 0)
        )
        stats["damage"] += participant.get("totalDamageDealtToChampions", 0)
        stats["gold"] += participant.get("goldEarned", 0)
        stats["vision"] += participant.get("visionScore", 0)
        stats["seconds"] += info.get("gameDuration", 0)

    results = []
    for champ, s in champions.items():
        minutes = s["seconds"] / 60 if s["seconds"] else 1
        games = s["games"]
        results.append({
            "champion": champ,
            "games": games,
            "wins": s["wins"],
            "losses": games - s["wins"],
            "winRate": round(s["wins"] / games * 100, 1),
            "kda": round((s["kills"] + s["assists"]) / max(1, s["deaths"]), 2),
            "avgKills": round(s["kills"] / games, 1),
            "avgDeaths": round(s["deaths"] / games, 1),
            "avgAssists": round(s["assists"] / games, 1),
            "csPerMin": round(s["cs"] / minutes, 1),
            "damagePerMin": round(s["damage"] / minutes, 0),
            "goldPerMin": round(s["gold"] / minutes, 0),
            "avgVisionScore": round(s["vision"] / games, 1),
            "avgGameMinutes": round(minutes / games, 1),
            "matchIds": s["matchIds"],
        })

    results.sort(key=lambda r: r["games"], reverse=True)
    return results


# (label, start minute, end minute); None = until the game ends.
CS_PHASES = [("0-15", 0, 15), ("15-25", 15, 25), ("25+", 25, None)]


def cs_timeline_stats(timelines: list[dict], puuid: str) -> dict:
    """CS breakdowns from Match-V5 timelines, averaged across games.
    Timeline frames land roughly once per minute (frame N ~ minute N),
    and the last frame is the end of the game.

    - phases: CS/min in each game phase. Totals are summed across games
      before dividing, so a game that only lasted 3 minutes into a phase
      doesn't count as much as a full one.
    - perMinute: CS gained during each minute, averaged over the games
      that lasted through that whole minute."""
    totals = {label: {"cs": 0, "minutes": 0.0, "games": 0} for label, _, _ in CS_PHASES}
    # minute -> [cs gained that minute summed across games, total cs at end of minute, games]
    per_minute: dict[int, list[int]] = {}

    for timeline in timelines:
        info = timeline.get("info", {})
        frames = info.get("frames", [])
        pid = next(
            (p["participantId"] for p in info.get("participants", []) if p.get("puuid") == puuid),
            None,
        )
        # Same remake/short-game cutoff as aggregate_by_champion.
        if pid is None or len(frames) < 2 or frames[-1]["timestamp"] < 300_000:
            continue

        def cs_at(i: int) -> int:
            pf = frames[i]["participantFrames"][str(pid)]
            return pf.get("minionsKilled", 0) + pf.get("jungleMinionsKilled", 0)

        last = len(frames) - 1
        for label, start, end in CS_PHASES:
            if start >= last:
                continue  # game ended before this phase began
            stop = last if end is None else min(end, last)
            minutes = (frames[stop]["timestamp"] - frames[start]["timestamp"]) / 60_000
            if minutes <= 0:
                continue
            t = totals[label]
            t["cs"] += cs_at(stop) - cs_at(start)
            t["minutes"] += minutes
            t["games"] += 1

        # Skip the final frame: it's a partial minute ending at game end.
        for minute in range(1, last):
            m = per_minute.setdefault(minute, [0, 0, 0])
            m[0] += cs_at(minute) - cs_at(minute - 1)
            m[1] += cs_at(minute)
            m[2] += 1

    phases = [
        {
            "phase": label,
            "csPerMin": round(totals[label]["cs"] / totals[label]["minutes"], 1)
            if totals[label]["minutes"] else None,
            "games": totals[label]["games"],
        }
        for label, _, _ in CS_PHASES
    ]
    minutes = [
        {
            "minute": minute,
            "cs": round(gained / games, 1),
            "totalCs": round(total / games, 1),
            "games": games,
        }
        for minute, (gained, total, games) in sorted(per_minute.items())
    ]
    return {"phases": phases, "perMinute": minutes}


def lane_diff_at(timelines: list[dict], matches: list[dict], puuid: str, minute: int = 10) -> dict:
    """Your CS and gold vs. your lane opponent (the enemy with the same
    teamPosition) at a given minute, averaged across games. Games with no
    clear opponent (ARAM, role swaps Riot couldn't label) or that ended
    before the minute are skipped."""
    matches_by_id = {m["metadata"]["matchId"]: m for m in matches}
    cs_total = cs_diff = gold_diff = games = 0

    for timeline in timelines:
        frames = timeline.get("info", {}).get("frames", [])
        match = matches_by_id.get(timeline.get("metadata", {}).get("matchId"))
        # Need a full frame at `minute`, not the partial end-of-game frame.
        if match is None or len(frames) <= minute + 1:
            continue

        participants = match["info"]["participants"]
        me = next((p for p in participants if p.get("puuid") == puuid), None)
        if me is None or not me.get("teamPosition"):
            continue
        opp = next(
            (p for p in participants
             if p.get("teamPosition") == me["teamPosition"] and p["teamId"] != me["teamId"]),
            None,
        )
        if opp is None:
            continue

        pf = frames[minute]["participantFrames"]
        mine, theirs = pf[str(me["participantId"])], pf[str(opp["participantId"])]
        my_cs = mine.get("minionsKilled", 0) + mine.get("jungleMinionsKilled", 0)
        their_cs = theirs.get("minionsKilled", 0) + theirs.get("jungleMinionsKilled", 0)

        cs_total += my_cs
        cs_diff += my_cs - their_cs
        gold_diff += mine.get("totalGold", 0) - theirs.get("totalGold", 0)
        games += 1

    if not games:
        return {"minute": minute, "cs": None, "csDiff": None, "goldDiff": None, "games": 0}
    return {
        "minute": minute,
        "cs": round(cs_total / games, 1),
        "csDiff": round(cs_diff / games, 1),
        "goldDiff": round(gold_diff / games),
        "games": games,
    }


PASSIVE_GOLD_PER_SEC = 2.04  # Summoner's Rift passive income (20.4g / 10s)


def _recipe_ids(item_id: str, items: dict) -> set[str]:
    """Every component anywhere in an item's build tree."""
    out: set[str] = set()
    for component in items.get(item_id, {}).get("from", []):
        out.add(component)
        out |= _recipe_ids(component, items)
    return out


def _net_spent(events: list[dict], items: dict) -> int:
    """Gold spent across a list of one player's item events. Buying an
    item consumes components you own (ITEM_DESTROYED at the same
    timestamp), and you only pay the difference."""
    destroyed = [e for e in events if e["type"] == "ITEM_DESTROYED"]
    spent = 0
    for e in events:
        if e["type"] == "ITEM_PURCHASED":
            item_id = str(e["itemId"])
            cost = items.get(item_id, {}).get("gold", {}).get("total", 0)
            recipe = _recipe_ids(item_id, items)
            for d in list(destroyed):
                if d["timestamp"] == e["timestamp"] and str(d["itemId"]) in recipe:
                    cost -= items.get(str(d["itemId"]), {}).get("gold", {}).get("total", 0)
                    destroyed.remove(d)
            spent += max(cost, 0)
        elif e["type"] == "ITEM_SOLD":
            spent -= items.get(str(e["itemId"]), {}).get("gold", {}).get("sell", 0)
        elif e["type"] == "ITEM_UNDO":
            spent -= e.get("goldGain", 0)
    return spent


def _unspent_gold_at_death(
    frames: list[dict], my_events: list[dict], pid: int, death_ts: int, items: dict
) -> int | None:
    """Estimate unspent gold at the moment of death. Frames only snapshot
    gold once a minute, so: take the snapshot before the death, subtract
    purchases made since, and add gold earned since. Kill bounties are
    exact. The rest of the minute's income (CS, assists, passive) is
    split on the basis that passive gold keeps coming in while you're
    dead but nothing else does, so everything beyond passive income for
    the time after death is credited to before the death."""
    i = next((i for i in range(len(frames) - 1, -1, -1) if frames[i]["timestamp"] <= death_ts), None)
    if i is None or i + 1 >= len(frames):
        return None
    t0, t1 = frames[i]["timestamp"], frames[i + 1]["timestamp"]
    f0 = frames[i]["participantFrames"][str(pid)]
    f1 = frames[i + 1]["participantFrames"][str(pid)]

    def kill_gold(e: dict) -> int:
        return e.get("bounty", 0) + e.get("shutdownBounty", 0)

    kills = [e for e in my_events
             if e["type"] == "CHAMPION_KILL" and e.get("killerId") == pid and t0 < e["timestamp"] <= t1]
    kills_before = sum(kill_gold(e) for e in kills if e["timestamp"] < death_ts)
    other_income = max(0, f1.get("totalGold", 0) - f0.get("totalGold", 0) - sum(kill_gold(e) for e in kills))
    after_death = min(other_income, PASSIVE_GOLD_PER_SEC * (t1 - death_ts) / 1000)
    earned = kills_before + other_income - after_death

    item_events = [e for e in my_events
                   if e["type"].startswith("ITEM_") and t0 < e["timestamp"] <= death_ts]
    spent = _net_spent(item_events, items)

    return max(0, round(f0.get("currentGold", 0) + earned - spent))


def deaths_from_timelines(
    timelines: list[dict], matches: list[dict], puuid: str, items: dict | None
) -> list[dict]:
    """Every time the player died: map position (Summoner's Rift game
    units, origin bottom-left), when it happened, who got the kill, and
    estimated unspent gold (None if item prices were unavailable).
    killerId 0 means executed by a tower/minion/monster."""
    matches_by_id = {m["metadata"]["matchId"]: m for m in matches}
    deaths = []

    for timeline in timelines:
        match_id = timeline.get("metadata", {}).get("matchId")
        match = matches_by_id.get(match_id)
        # Positions only make sense on Summoner's Rift (mapId 11), not ARAM etc.
        if match is None or match["info"].get("mapId") != 11:
            continue
        champs = {p["participantId"]: p["championName"] for p in match["info"]["participants"]}
        pid = next(
            (p["participantId"] for p in match["info"]["participants"] if p.get("puuid") == puuid),
            None,
        )
        if pid is None:
            continue

        frames = timeline.get("info", {}).get("frames", [])
        # Flatten and sort rather than trusting which frame an event is filed under.
        my_events = sorted(
            (e for f in frames for e in f.get("events", [])
             if e.get("participantId") == pid or e.get("killerId") == pid or e.get("victimId") == pid),
            key=lambda e: e["timestamp"],
        )

        for event in my_events:
            if event.get("type") != "CHAMPION_KILL" or event.get("victimId") != pid:
                continue
            pos = event.get("position")
            if not pos:
                continue
            deaths.append({
                "matchId": match_id,
                "x": pos["x"],
                "y": pos["y"],
                "minute": round(event["timestamp"] / 60_000, 1),
                "killer": champs.get(event.get("killerId"), "Executed"),
                "unspentGold": _unspent_gold_at_death(frames, my_events, pid, event["timestamp"], items)
                if items else None,
            })

    return deaths


def compute_highlights(rows: list[dict]) -> dict:
    """Pick out a few 'best of' stats to headline the dashboard.
    Only considers champions with at least 3 games so a single lucky
    game doesn't dominate the highlight reel."""
    qualified = [r for r in rows if r["games"] >= 3] or rows
    if not qualified:
        return {}

    return {
        "mostPlayed": max(qualified, key=lambda r: r["games"]),
        "highestWinRate": max(qualified, key=lambda r: r["winRate"]),
        "bestKda": max(qualified, key=lambda r: r["kda"]),
        "highestDamagePerMin": max(qualified, key=lambda r: r["damagePerMin"]),
    }
