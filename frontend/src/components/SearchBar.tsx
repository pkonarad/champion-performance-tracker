import { useState, FormEvent } from 'react';

const PLATFORMS = [
  { value: 'na1', label: 'North America' },
  { value: 'euw1', label: 'Europe West' },
  { value: 'eun1', label: 'Europe Nordic & East' },
  { value: 'kr', label: 'Korea' },
  { value: 'jp1', label: 'Japan' },
  { value: 'br1', label: 'Brazil' },
  { value: 'la1', label: 'Latin America North' },
  { value: 'la2', label: 'Latin America South' },
  { value: 'oc1', label: 'Oceania' },
  { value: 'tr1', label: 'Turkey' },
  { value: 'ru', label: 'Russia' },
];

interface Props {
  onSearch: (gameName: string, tagLine: string, platform: string) => void;
  loading: boolean;
}

export default function SearchBar({ onSearch, loading }: Props) {
  const [gameName, setGameName] = useState('');
  const [tagLine, setTagLine] = useState('');
  const [platform, setPlatform] = useState('na1');

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!gameName.trim() || !tagLine.trim()) return;
    onSearch(gameName.trim(), tagLine.trim(), platform);
  }

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <input
        value={gameName}
        onChange={(e) => setGameName(e.target.value)}
        placeholder="Riot ID"
        aria-label="Riot ID name"
      />
      <span className="hash">#</span>
      <input
        value={tagLine}
        onChange={(e) => setTagLine(e.target.value)}
        placeholder="TAG"
        aria-label="Riot ID tag"
        className="tag-input"
      />
      <select value={platform} onChange={(e) => setPlatform(e.target.value)}>
        {PLATFORMS.map((p) => (
          <option key={p.value} value={p.value}>{p.label}</option>
        ))}
      </select>
      <button type="submit" disabled={loading}>
        {loading ? 'Analyzing…' : 'Analyze'}
      </button>
    </form>
  );
}
