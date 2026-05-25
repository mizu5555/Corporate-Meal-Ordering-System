import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getVendorApplication, reviewVendorApplication } from "../../api/admin";

const STATUS_LABEL = { pending: "待審核", approved: "已通過", rejected: "已拒絕" };
const STATUS_COLOR = {
  pending: { background: "rgba(180,140,0,0.10)", color: "#9a7800" },
  approved: { background: "rgba(47,125,74,0.12)", color: "var(--success)" },
  rejected: { background: "rgba(200,92,44,0.12)", color: "var(--brand)" },
};

function StatusBadge({ status }) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "3px 12px",
        borderRadius: 99,
        fontSize: 13,
        fontWeight: 600,
        ...(STATUS_COLOR[status] ?? {}),
      }}
    >
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}

function InfoRow({ label, value }) {
  if (!value) return null;
  return (
    <div style={{ display: "flex", gap: 16, marginBottom: 10 }}>
      <span style={{ width: 100, flexShrink: 0, fontSize: 13, color: "var(--muted)", fontWeight: 600 }}>
        {label}
      </span>
      <span style={{ fontSize: 14 }}>{value}</span>
    </div>
  );
}

export default function AdminVendorReviewDetailPage() {
  const { applicationId } = useParams();
  const navigate = useNavigate();
  const [application, setApplication] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState(null);

  useEffect(() => {
    getVendorApplication(applicationId)
      .then(setApplication)
      .catch((err) => setError(err.message ?? "無法載入申請資料"))
      .finally(() => setLoading(false));
  }, [applicationId]);

  async function handleReview(decision) {
    if (!window.confirm(`確定要 ${decision === "approved" ? "核准" : "拒絕"} 此申請？`)) return;
    setSubmitting(true);
    setActionError(null);
    try {
      await reviewVendorApplication(applicationId, { decision, reason: reason.trim() || null });
      setApplication((prev) => ({ ...prev, status: decision, review_reason: reason.trim() || null }));
    } catch (err) {
      setActionError(err.message ?? "操作失敗");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <p className="loading-state">載入中...</p>;
  if (error) return <p className="error-state">{error}</p>;
  if (!application) return null;

  const isPending = application.status === "pending";

  return (
    <div>
      <div className="page-header">
        <button
          type="button"
          className="back-button"
          onClick={() => navigate("/admin/vendors")}
        >
          ← 返回列表
        </button>
        <p className="eyebrow">Admin · Vendor Review</p>
        <h2>{application.vendor_name}</h2>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 20, alignItems: "start" }}>
        <div className="panel">
          <p className="eyebrow" style={{ marginBottom: 16 }}>申請資料</p>
          <InfoRow label="廠商名稱" value={application.vendor_name} />
          <InfoRow label="地址" value={application.address} />
          <InfoRow label="營業時間" value={application.business_hours} />
          <InfoRow label="聯絡電話" value={application.contact_phone} />
          <InfoRow label="聯絡 Email" value={application.contact_email} />
          <hr style={{ border: "none", borderTop: "1px solid var(--line)", margin: "16px 0" }} />
          <InfoRow label="申請人" value={application.submitter_name} />
          <InfoRow label="Email" value={application.submitter_email} />
          <InfoRow
            label="申請日期"
            value={new Date(application.submitted_at).toLocaleString("zh-TW")}
          />
          {application.review_reason && (
            <InfoRow label="審核備注" value={application.review_reason} />
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="panel">
            <p className="eyebrow" style={{ marginBottom: 12 }}>申請狀態</p>
            <StatusBadge status={application.status} />
          </div>

          {isPending && (
            <div className="panel">
              <p className="eyebrow" style={{ marginBottom: 12 }}>審核決定</p>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "var(--muted)", marginBottom: 6 }}>
                備注（選填）
              </label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="填寫拒絕原因或補充說明..."
                rows={3}
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--line)",
                  background: "var(--surface-strong)",
                  fontSize: 14,
                  resize: "vertical",
                  boxSizing: "border-box",
                  outline: "none",
                  marginBottom: 12,
                }}
              />

              {actionError && (
                <p style={{ color: "var(--brand)", fontSize: 13, marginBottom: 10 }}>{actionError}</p>
              )}

              <div style={{ display: "flex", gap: 10 }}>
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleReview("approved")}
                  style={{
                    flex: 1,
                    padding: "9px 0",
                    borderRadius: "var(--radius-md)",
                    border: "none",
                    background: "rgba(47,125,74,0.15)",
                    color: "var(--success)",
                    fontWeight: 600,
                    fontSize: 14,
                    cursor: submitting ? "not-allowed" : "pointer",
                    opacity: submitting ? 0.7 : 1,
                  }}
                >
                  核准
                </button>
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleReview("rejected")}
                  style={{
                    flex: 1,
                    padding: "9px 0",
                    borderRadius: "var(--radius-md)",
                    border: "none",
                    background: "rgba(200,92,44,0.12)",
                    color: "var(--brand)",
                    fontWeight: 600,
                    fontSize: 14,
                    cursor: submitting ? "not-allowed" : "pointer",
                    opacity: submitting ? 0.7 : 1,
                  }}
                >
                  拒絕
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
