import { useEffect, useState } from 'react';
import type { Death } from '../types';

interface Props {
  deaths: Death[];
  games: number;
}

// Summoner's Rift playable bounds in game units (from Riot's docs).
const MAP_MIN = { x: -120, y: -120 };
const MAP_MAX = { x: 14870, y: 14980 };

const PHASES = [
  { label: '0–15 min', color: '#facc15', test: (m: number) => m < 15 },
  { label: '15–25 min', color: '#fb923c', test: (m: number) => m >= 15 && m < 25 },
  { label: '25+ min', color: '#f43f5e', test: (m: number) => m >= 25 },
];

function phaseOf(minute: number) {
  return PHASES.find((p) => p.test(minute)) ?? PHASES[0];
}

// Percent offsets within the map box; game y grows upward, CSS top grows down.
function toPercent(d: Death) {
  return {
    left: ((d.x - MAP_MIN.x) / (MAP_MAX.x - MAP_MIN.x)) * 100,
    top: (1 - (d.y - MAP_MIN.y) / (MAP_MAX.y - MAP_MIN.y)) * 100,
  };
}

// Data Dragon URLs are versioned; grab the latest once per page load.
let mapUrlPromise: Promise<string | null> | null = null;
function getMapUrl() {
  mapUrlPromise ??= fetch('https://ddragon.leagueoflegends.com/api/versions.json')
    .then((r) => r.json())
    .then((versions: string[]) => `https://ddragon.leagueoflegends.com/cdn/${versions[0]}/img/map/map11.png`)
    .catch(() => null);
  return mapUrlPromise;
}

export default function DeathMap({ deaths, games }: Props) {
  const [mapUrl, setMapUrl] = useState<string | null>(null);
  const [hovered, setHovered] = useState<number | null>(null);

  useEffect(() => {
    getMapUrl().then(setMapUrl);
  }, []);

  const perGame = games ? (deaths.length / games).toFixed(1) : '0';
  const golds = deaths.map((d) => d.unspentGold).filter((g): g is number => g !== null);
  const avgGold = golds.length ? Math.round(golds.reduce((a, b) => a + b, 0) / golds.length) : null;
  const hoveredDeath = hovered !== null ? deaths[hovered] : null;

  return (
    <div className="death-map-section">
      <div className="cs-section-title">
        Deaths · {deaths.length} total, {perGame} per game
      </div>
      <div className="death-map-layout">
        <div className="death-map">
          {mapUrl && <img src={mapUrl} alt="Summoner's Rift minimap" />}
          {deaths.map((d, i) => {
            const { left, top } = toPercent(d);
            return (
              <span
                key={i}
                className={`death-dot${hovered === i ? ' hovered' : ''}`}
                style={{ left: `${left}%`, top: `${top}%`, background: phaseOf(d.minute).color }}
                onMouseEnter={() => setHovered(i)}
                onMouseLeave={() => setHovered(null)}
              />
            );
          })}
          {hoveredDeath && (
            <div
              className="cs-tooltip death-tooltip"
              style={{
                left: `${toPercent(hoveredDeath).left}%`,
                top: `${toPercent(hoveredDeath).top}%`,
              }}
            >
              <div className="cs-tooltip-title">{formatMinute(hoveredDeath.minute)}</div>
              <div>
                {hoveredDeath.killer === 'Executed' ? 'Executed' : `Killed by ${hoveredDeath.killer}`}
              </div>
              {hoveredDeath.unspentGold !== null && (
                <div>~{hoveredDeath.unspentGold.toLocaleString()}g unspent</div>
              )}
            </div>
          )}
        </div>

        <div className="death-side">
          <div className="cs-phase">
            <div className="stat-label">Avg unspent gold at death</div>
            <div className="cs-phase-value">
              {avgGold !== null ? `~${avgGold.toLocaleString()}g` : '—'}
            </div>
            <div className="meta">Estimated from per-minute snapshots</div>
          </div>
          <ul className="death-legend">
            {PHASES.map((p) => (
              <li key={p.label}>
                <span className="death-swatch" style={{ background: p.color }} />
                {p.label}
                <span className="meta">
                  {deaths.filter((d) => p.test(d.minute)).length}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function formatMinute(minute: number) {
  const m = Math.floor(minute);
  const s = Math.round((minute - m) * 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}
