import { useEffect, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid,
} from 'recharts';
import { fetchCsTimeline } from '../api';
import type { CsMinute, CsTimeline } from '../types';
import DeathMap from './DeathMap';

interface Props {
  puuid: string;
  platform: string;
  matchIds: string[];
}

const PHASE_LABELS: Record<string, string> = {
  '0-15': '0–15 min',
  '15-25': '15–25 min',
  '25+': '25+ min',
};

const MIN_GAMES_PER_MINUTE = 3;

export default function CsBreakdown({ puuid, platform, matchIds }: Props) {
  const [data, setData] = useState<CsTimeline | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setError(null);
    fetchCsTimeline(puuid, platform, matchIds)
      .then((d) => { if (!cancelled) setData(d); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load CS timeline.'); });
    return () => { cancelled = true; };
  }, [puuid, platform, matchIds]);

  if (error) return <div className="cs-breakdown meta">{error}</div>;
  if (!data) return <div className="cs-breakdown meta">Loading match timelines…</div>;

  const lane = data.laneAt10;

  // Late minutes are often reached by only one or two long games, where a
  // single death or big wave swings the average wildly. Hide those.
  const maxGames = Math.max(0, ...data.perMinute.map((m) => m.games));
  const minGames = Math.min(MIN_GAMES_PER_MINUTE, maxGames);
  const perMinute = data.perMinute.filter((m) => m.games >= minGames);
  const hidden = data.perMinute.filter((m) => m.games < minGames).map((m) => m.minute);

  return (
    <div className="cs-breakdown">
      <div className="cs-section-title">Lane @{lane.minute} min vs. opponent</div>
      <div className="cs-phases-grid">
        <div className="cs-phase">
          <div className="stat-label">CS @{lane.minute}</div>
          <div className="cs-phase-value">{lane.cs ?? '—'}</div>
          <div className="meta">{gamesLabel(lane.games)}</div>
        </div>
        <div className="cs-phase">
          <div className="stat-label">CS lead @{lane.minute}</div>
          <div className={`cs-phase-value ${diffClass(lane.csDiff)}`}>{signed(lane.csDiff)}</div>
          <div className="meta">{gamesLabel(lane.games)}</div>
        </div>
        <div className="cs-phase">
          <div className="stat-label">Gold lead @{lane.minute}</div>
          <div className={`cs-phase-value ${diffClass(lane.goldDiff)}`}>{signed(lane.goldDiff)}</div>
          <div className="meta">{gamesLabel(lane.games)}</div>
        </div>
      </div>

      <div className="cs-section-title">CS/min by game phase</div>
      <div className="cs-phases-grid">
        {data.phases.map((p) => (
          <div key={p.phase} className="cs-phase">
            <div className="stat-label">{PHASE_LABELS[p.phase] ?? p.phase}</div>
            <div className="cs-phase-value">{p.csPerMin ?? '—'}</div>
            <div className="meta">
              {p.games} {p.games === 1 ? 'game' : 'games'} reached
            </div>
          </div>
        ))}
      </div>

      <div className="cs-section-title">Average CS each minute</div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={perMinute} margin={{ top: 8, right: 12, bottom: 4, left: -16 }}>
          <CartesianGrid stroke="#22252f" vertical={false} />
          <XAxis
            dataKey="minute"
            stroke="#6b7280"
            tick={{ fontSize: 12 }}
            ticks={perMinute.filter((m) => m.minute % 5 === 0).map((m) => m.minute)}
          />
          <YAxis stroke="#6b7280" tick={{ fontSize: 12 }} allowDecimals={false} />
          <ReferenceLine x={15} stroke="#3a3e4c" strokeDasharray="4 4" />
          <ReferenceLine x={25} stroke="#3a3e4c" strokeDasharray="4 4" />
          <Tooltip content={<MinuteTooltip />} cursor={{ stroke: '#3a3e4c' }} />
          <Line
            type="monotone"
            dataKey="cs"
            stroke="#5865f2"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
      {hidden.length > 0 && (
        <div className="meta">
          {hidden.length === 1 ? `Minute ${hidden[0]}` : `Minutes ${hidden[0]}–${hidden[hidden.length - 1]}`}{' '}
          not shown: fewer than {minGames} games lasted that long.
        </div>
      )}

      <DeathMap deaths={data.deaths} games={matchIds.length} />
    </div>
  );
}

function signed(n: number | null): string {
  if (n === null) return '—';
  return n > 0 ? `+${n}` : `${n}`;
}

function diffClass(n: number | null): string {
  if (n === null || n === 0) return '';
  return n > 0 ? 'ahead' : 'behind';
}

function gamesLabel(games: number): string {
  return `${games} ${games === 1 ? 'game' : 'games'}`;
}

function MinuteTooltip({ active, payload }: { active?: boolean; payload?: { payload: CsMinute }[] }) {
  if (!active || !payload?.length) return null;
  const m = payload[0].payload;
  return (
    <div className="cs-tooltip">
      <div className="cs-tooltip-title">Minute {m.minute}</div>
      <div>{m.cs} CS that minute</div>
      <div>{m.totalCs} total CS</div>
      <div className="meta">{m.games} {m.games === 1 ? 'game' : 'games'}</div>
    </div>
  );
}
