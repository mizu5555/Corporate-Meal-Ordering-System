import { useNavigate } from "react-router-dom";
import { useVendorMenu } from "../../vendor/VendorMenuContext";
import { formatPrice } from "../../utils/format";

export default function VendorMenuListPage() {
  const navigate = useNavigate();
  const { items, loading, error, removeItem } = useVendorMenu();

  async function handleDelete(item) {
    if (!window.confirm(`確定要刪除「${item.name}」嗎？`)) return;
    try {
      await removeItem(item.id);
    } catch (err) {
      alert(err.message ?? "刪除失敗，請稍後再試。");
    }
  }

  return (
    <div>
      <div className="page-header" style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
        <div>
          <p className="eyebrow">Vendor · Menu</p>
          <h2>菜單管理</h2>
        </div>
        <button
          className="primary-button"
          type="button"
          onClick={() => navigate("/vendor/menu/new")}
        >
          + 新增餐點
        </button>
      </div>

      {loading && <p className="loading-state">載入菜單中...</p>}

      {error && <p className="error-state">無法載入菜單，請稍後再試。</p>}

      {!loading && !error && items.length === 0 && (
        <p className="empty-state">尚未建立任何餐點，點擊「新增餐點」開始。</p>
      )}

      {!loading && !error && items.length > 0 && (
        <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
          {items.map((item, idx) => (
            <div
              key={item.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 16,
                padding: "16px 20px",
                borderBottom: idx < items.length - 1 ? "1px solid var(--line)" : "none",
              }}
            >
              <div style={{ flex: 1 }}>
                <p style={{ fontWeight: 600, margin: 0 }}>{item.name}</p>
                {item.description && (
                  <p style={{ color: "var(--muted)", fontSize: 13, margin: "2px 0 0" }}>
                    {item.description}
                  </p>
                )}
              </div>

              <p style={{ width: 80, textAlign: "right", margin: 0 }}>
                {formatPrice(item.price_cents)}
              </p>

              <span className={`badge ${item.available ? "badge-available" : "badge-unavailable"}`}>
                {item.available ? "供應中" : "暫停供應"}
              </span>

              {item.daily_quota !== null && item.daily_quota !== undefined && (
                <span className="badge badge-quota">
                  {item.daily_quota === 0 ? "今日售完" : `配額 ${item.daily_quota}`}
                </span>
              )}

              <div style={{ display: "flex", gap: 8 }}>
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => navigate(`/vendor/menu/${item.id}/edit`)}
                >
                  編輯
                </button>
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => handleDelete(item)}
                  style={{ color: "var(--error, #e53e3e)", borderColor: "var(--error, #e53e3e)" }}
                >
                  刪除
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
