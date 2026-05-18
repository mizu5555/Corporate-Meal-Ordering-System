export default function SearchBar({ value, onChange, placeholder = "搜尋..." }) {
  return (
    <div className="search-bar">
      <span className="search-icon" aria-hidden="true">🔍</span>
      <input
        className="search-input"
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
      />
    </div>
  );
}
