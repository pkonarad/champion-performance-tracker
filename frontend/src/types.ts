export interface ChampionStats {
  champion: string;
  games: number;
  wins: number;
  losses: number;
  winRate: number;
  kda: number;
  avgKills: number;
  avgDeaths: number;
  avgAssists: number;
  csPerMin: number;
  damagePerMin: number;
  goldPerMin: number;
  avgVisionScore: number;
  avgGameMinutes: number;
  matchIds: string[];
}

export interface CsPhase {
  phase: string;
  csPerMin: number | null;
  games: number;
}

export interface CsMinute {
  minute: number;
  cs: number;       // avg CS gained during this minute
  totalCs: number;  // avg total CS at the end of this minute
  games: number;
}

export interface LaneDiff {
  minute: number;
  cs: number | null;        // your avg CS at this minute
  csDiff: number | null;    // vs. lane opponent; positive = ahead
  goldDiff: number | null;
  games: number;
}

export interface Death {
  matchId: string;
  x: number;       // Summoner's Rift game units, origin bottom-left
  y: number;
  minute: number;
  killer: string;  // champion name, or "Executed"
  unspentGold: number | null;  // estimate; null if item prices were unavailable
}

export interface CsTimeline {
  phases: CsPhase[];
  perMinute: CsMinute[];
  laneAt10: LaneDiff;
  deaths: Death[];
}

export interface Highlights {
  mostPlayed?: ChampionStats;
  highestWinRate?: ChampionStats;
  bestKda?: ChampionStats;
  highestDamagePerMin?: ChampionStats;
}

export interface PlayerResponse {
  riotId: string;
  puuid: string;
  platform: string;
  matchesAnalyzed: number;
  champions: ChampionStats[];
  highlights: Highlights;
}
