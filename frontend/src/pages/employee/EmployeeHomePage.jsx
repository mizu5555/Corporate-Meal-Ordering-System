import { useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";

export default function EmployeeHomePage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <section className="dashboard-grid">
      <article className="panel hero-banner">
        <p className="eyebrow">Employee Workspace</p>
        <h2>歡迎回來，{user?.name ?? "Employee"}</h2>
        <p className="panel-copy" style={{ marginTop: 12 }}>
          瀏覽今日供應廠商、挑選餐點，快速完成訂餐。
        </p>
        <button
          className="primary-button inline-button"
          style={{ marginTop: 24 }}
          onClick={() => navigate("/employee/menu")}
          type="button"
        >
          瀏覽今日菜單 →
        </button>
      </article>

      <article className="panel">
        <h3>快速入口</h3>
        <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
          <button
            className="role-card"
            onClick={() => navigate("/employee/menu")}
            type="button"
          >
            <strong>🍱 瀏覽菜單</strong>
            <span>查看廠商與今日供應餐點</span>
          </button>
          <button
            className="role-card"
            onClick={() => navigate("/employee/orders")}
            type="button"
          >
            <strong>📋 我的訂單</strong>
            <span>查看目前訂單狀態</span>
          </button>
        </div>
      </article>

      <article className="panel">
        <h3>本期進度</h3>
        <p className="panel-copy">
          菜單瀏覽（E2）、搜尋篩選（E3）、餐點詳情（E4）已完成。
          訂購流程（E5–E7）將在下一個分支實作。
        </p>
      </article>
    </section>
  );
}
