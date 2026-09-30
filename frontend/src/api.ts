import type { CsTimeline, PlayerResponse } from './types';

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }

  return res.json();
}

export async function fetchPlayerStats(
  gameName: string,
  tagLine: string,
  platform: string
): Promise<PlayerResponse> {
  const url = `/api/player/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}?platform=${platform}`;
  return getJson<PlayerResponse>(url);
}

export async function fetchCsTimeline(
  puuid: string,
  platform: string,
  matchIds: string[]
): Promise<CsTimeline> {
  const params = new URLSearchParams({ puuid, platform });
  matchIds.forEach((id) => params.append('matchId', id));
  return getJson<CsTimeline>(`/api/cs-phases?${params}`);
}
