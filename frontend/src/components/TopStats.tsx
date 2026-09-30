import type { Highlights } from '../types';

interface Props {
  highlights: Highlights;
}

function Card({ label, champ, value }: { label: string; champ: string; value: string }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-champ">{champ}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

export default function TopStats({ highlights }: Props) {
  return (
    <div className="top-stats">
      {highlights.mostPlayed && (
        <Card label="Most Played" champ={highlights.mostPlayed.champion} value={`${highlights.mostPlayed.games} games`} />
      )}
      {highlights.highestWinRate && (
        <Card label="Highest Win Rate" champ={highlights.highestWinRate.champion} value={`${highlights.highestWinRate.winRate}%`} />
      )}
      {highlights.bestKda && (
        <Card label="Best KDA" champ={highlights.bestKda.champion} value={`${highlights.bestKda.kda}`} />
      )}
      {highlights.highestDamagePerMin && (
        <Card label="Highest Dmg/min" champ={highlights.highestDamagePerMin.champion} value={`${highlights.highestDamagePerMin.damagePerMin}`} />
      )}
    </div>
  );
}
