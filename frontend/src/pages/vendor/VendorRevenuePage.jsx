import FacilityScopeLabel from "../../facility/FacilityScopeLabel";

export default function VendorRevenuePage() {
  return (
    <div>
      <div className="page-header">
        <FacilityScopeLabel label="Revenue facility" />
        <p className="eyebrow">商家 · 營收</p>
        <h2>收益總覽</h2>
      </div>

      <section className="panel" style={{ padding: "32px 24px", textAlign: "center" }}>
        <p style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>營收報表即將推出</p>
        <p className="panel-copy">
          本月度帳款由福委會統一結算。詳細帳款資料請聯繫系統管理員或等待後續功能上線。
        </p>
      </section>
    </div>
  );
}
