import { MOCK_VENDOR_SELECTIONS } from "../../api/mockData";
import FacilityScopeLabel from "../../facility/FacilityScopeLabel";
import { formatPrice } from "../../utils/format";

const MOCK_WEEKLY_REVENUE = 284500;
const MOCK_MONTHLY_REVENUE = 1138000;

const MOCK_DAILY_TREND = [
  { label: "週一", revenue_cents: 52000 },
  { label: "週二", revenue_cents: 67500 },
  { label: "週三", revenue_cents: 43000 },
  { label: "週四", revenue_cents: 78000 },
  { label: "週五", revenue_cents: 61500 },
  { label: "週六", revenue_cents: 0 },
  { label: "今日", revenue_cents: null },
];

function buildItemStats(selections) {
  const map = {};
  for (const s of selections) {
    if (!map[s.item_id]) {
      map[s.item_id] = {
        item_id: s.item_id,
        item_name: s.item_name,
        order_count: 0,
        total_quantity: 0,
        total_revenue_cents: 0,
      };
    }
    map[s.item_id].order_count += 1;
    map[s.item_id].total_quantity += s.quantity;
    map[s.item_id].total_revenue_cents += s.total_price_cents;
  }
  return Object.values(map).sort((a, b) => b.total_revenue_cents - a.total_revenue_cents);
}

export default function VendorRevenuePage() {
  const todayRevenue = MOCK_VENDOR_SELECTIONS.reduce((sum, s) => sum + s.total_price_cents, 0);
  const todayOrders = MOCK_VENDOR_SELECTIONS.length;
  const itemStats = buildItemStats(MOCK_VENDOR_SELECTIONS);

  const trend = MOCK_DAILY_TREND.map((d) => ({
    ...d,
    revenue_cents: d.revenue_cents === null ? todayRevenue : d.revenue_cents,
  }));
  const maxRevenue = Math.max(...trend.map((d) => d.revenue_cents));

  return (
    <div>
      <div className="page-header">
        <FacilityScopeLabel label="Revenue facility" />
        <p className="eyebrow">Vendor · Revenue</p>
        <h2>收益總覽</h2>
      </div>

      {/* 收入摘要 */}
      <div style={{ display: "flex", gap: 16, marginBottom: 32 }}>
        <div className="panel" style={{ flex: 1, padding: "16px 20px" }}>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>今日收入</p>
          <p style={{ margin: "4px 0 0", fontWeight: 700, fontSize: 22 }}>{formatPrice(todayRevenue)}</p>
          <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: 12 }}>{todayOrders} 筆訂單</p>
        </div>
        <div className="panel" style={{ flex: 1, padding: "16px 20px" }}>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>本週收入</p>
          <p style={{ margin: "4px 0 0", fontWeight: 700, fontSize: 22 }}>{formatPrice(MOCK_WEEKLY_REVENUE)}</p>
        </div>
        <div className="panel" style={{ flex: 1, padding: "16px 20px" }}>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>本月收入</p>
          <p style={{ margin: "4px 0 0", fontWeight: 700, fontSize: 22 }}>{formatPrice(MOCK_MONTHLY_REVENUE)}</p>
        </div>
      </div>

      {/* 歷史收入趨勢 */}
      <div style={{ marginBottom: 32 }}>
        <p style={{ fontWeight: 600, marginBottom: 16 }}>本週收入趨勢</p>
        <div className="panel" style={{ padding: "20px 24px" }}>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 12, height: 120 }}>
            {trend.map((d) => {
              const pct = maxRevenue > 0 ? d.revenue_cents / maxRevenue : 0;
              const isToday = d.label === "今日";
              return (
                <div key={d.label} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                  <p style={{ margin: 0, fontSize: 11, color: "var(--muted)", fontWeight: 600 }}>
                    {formatPrice(d.revenue_cents)}
                  </p>
                  <div
                    style={{
                      width: "100%",
                      height: `${Math.max(pct * 72, d.revenue_cents > 0 ? 4 : 0)}px`,
                      background: isToday ? "var(--accent, #3b82f6)" : "var(--line, #e5e7eb)",
                      borderRadius: 4,
                      transition: "height 0.3s",
                    }}
                  />
                  <p style={{ margin: 0, fontSize: 12, color: isToday ? "var(--accent, #3b82f6)" : "var(--muted)", fontWeight: isToday ? 700 : 400 }}>
                    {d.label}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 今日品項銷售明細 */}
      <p style={{ fontWeight: 600, marginBottom: 16 }}>今日品項銷售</p>
      {itemStats.length === 0 ? (
        <p className="empty-state">今日尚無銷售資料。</p>
      ) : (
        <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 80px 80px 120px",
              padding: "10px 20px",
              borderBottom: "1px solid var(--line)",
              color: "var(--muted)",
              fontSize: 12,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            <span>品項</span>
            <span style={{ textAlign: "right" }}>訂單數</span>
            <span style={{ textAlign: "right" }}>總份數</span>
            <span style={{ textAlign: "right" }}>銷售額</span>
          </div>

          {itemStats.map((stat, idx) => (
            <div
              key={stat.item_id}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 80px 80px 120px",
                alignItems: "center",
                padding: "14px 20px",
                borderBottom: idx < itemStats.length - 1 ? "1px solid var(--line)" : "none",
              }}
            >
              <p style={{ margin: 0, fontWeight: 500 }}>{stat.item_name}</p>
              <p style={{ margin: 0, textAlign: "right", color: "var(--muted)" }}>{stat.order_count}</p>
              <p style={{ margin: 0, textAlign: "right", color: "var(--muted)" }}>{stat.total_quantity} 份</p>
              <p style={{ margin: 0, textAlign: "right", fontWeight: 600 }}>
                {formatPrice(stat.total_revenue_cents)}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
