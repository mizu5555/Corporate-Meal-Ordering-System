import { useState } from "react";
import { useNavigate } from "react-router-dom";
import SearchBar from "../../components/employee/SearchBar";
import VendorCard from "../../components/employee/VendorCard";
import { useVendors } from "../../hooks/useVendors";

export default function MenuListPage() {
  const { vendors, loading, error } = useVendors();
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const filtered = vendors.filter((v) =>
    v.name.toLowerCase().includes(query.toLowerCase()) ||
    (v.address ?? "").toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div>
      <div className="page-header">
        <p className="eyebrow">Employee · Browse</p>
        <h2>今日供應廠商</h2>
      </div>

      <SearchBar
        value={query}
        onChange={setQuery}
        placeholder="搜尋廠商名稱或地點..."
      />

      {loading && <p className="loading-state">載入廠商中...</p>}

      {error && (
        <p className="error-state">
          無法載入廠商資料，請確認後端服務正常運行。
        </p>
      )}

      {!loading && !error && filtered.length === 0 && (
        <p className="empty-state">
          {query ? `找不到符合「${query}」的廠商` : "目前沒有可供應的廠商。"}
        </p>
      )}

      {!loading && !error && filtered.length > 0 && (
        <div className="vendor-grid">
          {filtered.map((vendor) => (
            <VendorCard
              key={vendor.id}
              vendor={vendor}
              onClick={() => navigate(`/employee/menu/${vendor.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
