import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getVendorApplications } from "../../api/admin";

const STATUS_FILTERS = [
  { label: "全部", value: "" },
  { label: "待審核", value: "pending" },
  { label: "已通過", value: "approved" },
  { label: "已拒絕", value: "rejected" },
];

const STATUS_LABEL = {
  pending: "待審核",
  approved: "已通過",
  rejected: "已拒絕",
};

const STATUS_COLOR = {
  pending: { background: "rgba(180,140,0,0.10)", color: "#9a7800" },
  approved: { background: "rgba(47,125,74,0.12)", color: "var(--success)" },
  rejected: { background: "rgba(200,92,44,0.12)", color: "var(--brand)" },
};

function StatusBadge({ status }) {
  const style = {
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: 99,
    fontSize: 12,
    fontWeight: 600,
    ...(STATUS_COLOR[status] ?? {}),
  };
  return <span style={style}>{STATUS_LABEL[status] ?? status}</span>;
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString("zh-TW");
}

export default function AdminVendorReviewListPage() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState("pending");
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getVendorApplications(statusFilter || null)
      .then(setApplications)
      .catch((err) => setError(err.message ?? "無法載入申請列表"))
      .finally(() => setLoading(false));
  }, [statusFilter]);

  return (
    <div>
      <div className="page-header">
        <p className="eyebrow">Admin · Vendor Review</p>
        <h2>供應商申請審核</h2>
      </div>

      <div className="filter-bar" style={{ marginBottom: 20 }}>
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            className={`filter-pill${statusFilter === f.value ? " filter-pill-active" : ""}`}
            onClick={() => setStatusFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading && <p className="loading-state">載入中...</p>}
      {error && <p className="error-state">{error}</p>}

      {!loading && !error && applications.length === 0 && (
        <p className="empty-state">目前沒有符合條件的申請。</p>
      )}

      {!loading && !error && applications.length > 0 && (
        <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 180px 120px 100px 100px",
              padding: "10px 20px",
              borderBottom: "1px solid var(--line)",
              color: "var(--muted)",
              fontSize: 12,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            <span>廠商</span>
            <span>申請人</span>
            <span>狀態</span>
            <span>申請日期</span>
            <span />
          </div>

          {applications.map((app, idx) => (
            <div
              key={app.application_id}
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 180px 120px 100px 100px",
                alignItems: "center",
                padding: "14px 20px",
                borderBottom: idx < applications.length - 1 ? "1px solid var(--line)" : "none",
                cursor: "pointer",
              }}
              onClick={() => navigate(`/admin/vendors/${app.application_id}`)}
            >
              <div>
                <p style={{ margin: 0, fontWeight: 500, fontSize: 14 }}>{app.vendor_name}</p>
                <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--muted)" }}>
                  ID #{app.application_id}
                </p>
              </div>
              <div>
                <p style={{ margin: 0, fontSize: 13 }}>{app.submitter_name ?? "—"}</p>
                <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--muted)" }}>
                  {app.submitter_email ?? ""}
                </p>
              </div>
              <StatusBadge status={app.status} />
              <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>
                {formatDate(app.submitted_at)}
              </p>
              <p style={{ margin: 0, fontSize: 13, color: "var(--muted)", textAlign: "right" }}>
                審核 →
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
