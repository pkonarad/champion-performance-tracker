import { useState } from 'react';
import SearchBar from './components/SearchBar';
import TopStats from './components/TopStats';
import ChampionTable from './components/ChampionTable';
import { fetchPlayerStats } from './api';
import type { PlayerResponse } from './types';
import './App.css';

export default function App() {
  const [data, setData] = useState<PlayerResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(gameName: string, tagLine: string, platform: string) {
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const result = await fetchPlayerStats(gameName, tagLine, platform);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <h1>Champion Performance Tracker</h1>
      <p className="subtitle">Enter a Riot ID to see win rate, KDA, and CS/min by champion.</p>

      <SearchBar onSearch={handleSearch} loading={loading} />

      {error && <div className="error">{error}</div>}

      {data && (
        <div className="results">
          <div className="results-header">
            <h2>{data.riotId}</h2>
            <span className="meta">{data.matchesAnalyzed} matches analyzed · {data.platform.toUpperCase()}</span>
          </div>

          <TopStats highlights={data.highlights} />
          <ChampionTable champions={data.champions} puuid={data.puuid} platform={data.platform} />
        </div>
      )}

      <footer className="legal">
        Champion Performance Tracker isn't endorsed by Riot Games and doesn't reflect the views or
        opinions of Riot Games or anyone officially involved in producing or managing Riot Games
        properties. Riot Games, and all associated properties are trademarks or registered
        trademarks of Riot Games, Inc.
      </footer>
    </div>
  );
}
