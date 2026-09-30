import React, { useState } from 'react';
import type { ChampionStats } from '../types';
import CsBreakdown from './CsBreakdown';

type SortKey = keyof ChampionStats;

interface Props {
  champions: ChampionStats[];
  puuid: string;
  platform: string;
}

export default function ChampionTable({ champions, puuid, platform }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('games');
  const [expanded, setExpanded] = useState<string | null>(null);

  const sorted = [...champions].sort((a, b) => (b[sortKey] as number) - (a[sortKey] as number));

  function toggle(champ: string) {
    setExpanded(expanded === champ ? null : champ);
  }

  return (
    <table className="champ-table">
      <thead>
        <tr>
          {(['champion', 'games', 'winRate', 'kda', 'csPerMin', 'damagePerMin', 'goldPerMin'] as SortKey[]).map((key) => (
            <th key={key} onClick={() => setSortKey(key)} className={sortKey === key ? 'active' : ''}>
              {headerLabel(key)}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {sorted.map((c) => (
          <React.Fragment key={c.champion}>
            <tr onClick={() => toggle(c.champion)} className="row">
              <td className="champ-name">{c.champion}</td>
              <td>{c.games}</td>
              <td>{c.winRate}%</td>
              <td>{c.kda}</td>
              <td>{c.csPerMin}</td>
              <td>{c.damagePerMin}</td>
              <td>{c.goldPerMin}</td>
            </tr>
            {expanded === c.champion && (
              <tr className="detail-row">
                <td colSpan={7}>
                  <div className="detail-grid">
                    <div>Avg KDA line: {c.avgKills} / {c.avgDeaths} / {c.avgAssists}</div>
                    <div>Avg vision score: {c.avgVisionScore}</div>
                    <div>Avg game length: {c.avgGameMinutes} min</div>
                    <div>Record: {c.wins}W – {c.losses}L</div>
                  </div>
                  <CsBreakdown puuid={puuid} platform={platform} matchIds={c.matchIds} />
                </td>
              </tr>
            )}
          </React.Fragment>
        ))}
      </tbody>
    </table>
  );
}

function headerLabel(key: SortKey): string {
  const labels: Record<string, string> = {
    champion: 'Champion',
    games: 'Games',
    winRate: 'Win Rate',
    kda: 'KDA',
    csPerMin: 'CS/min',
    damagePerMin: 'Dmg/min',
    goldPerMin: 'Gold/min',
  };
  return labels[key] ?? key;
}
