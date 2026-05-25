import { useEffect, useState } from "react";
import { getMyVendorApplication, submitVendorApplication } from "../../api/vendor";

function PendingBanner({ application }) {
  const statusLabel = {
    pending: "審核中",
    approved: "已通過",
    rejected: "已拒絕",
  };
  const statusColor = {
    pending: "var(--muted)",
    approved: "var(--success)",
    rejected: "var(--brand)",
  };

  return (
    <section className="panel" style={{ maxWidth: 560 }}>
      <p className="eyebrow">Vendor Application</p>
      <h2>{application.vendor_name}</h2>
      <p
        style={{
          display: "inline-block",
          padding: "4px 14px",
          borderRadius: 99,
          background: "var(--surface-strong)",
          color: statusColor[application.status] ?? "var(--text)",
          fontWeight: 600,
          fontSize: 13,
          marginBottom: 16,
        }}
      >
        {statusLabel[application.status] ?? application.status}
      </p>

      {application.status === "pending" && (
        <p className="panel-copy">您的申請已送出，管理員審核後將更新狀態。審核通過後請重新登入，即可開始管理菜單。</p>
      )}
      {application.status === "approved" && (
        <p className="panel-copy">申請已通過！請重新登入以更新權限，即可開始管理菜單。</p>
      )}
      {application.status === "rejected" && (
        <>
          <p className="panel-copy">申請未通過。{application.review_reason ? `原因：${application.review_reason}` : ""}</p>
        </>
      )}

      {application.status === "approved" && (
        <button
          className="btn-primary"
          style={{ marginTop: 16 }}
          onClick={() => window.location.reload()}
        >
          重新整理
        </button>
      )}
    </section>
  );
}

function ApplicationForm({ onSubmitted }) {
  const [form, setForm] = useState({
    vendor_name: "",
    address: "",
    business_hours: "",
    contact_phone: "",
    contact_email: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.vendor_name.trim()) {
      setError("廠商名稱為必填");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const result = await submitVendorApplication({
        vendor_name: form.vendor_name.trim(),
        address: form.address.trim() || null,
        business_hours: form.business_hours.trim() || null,
        contact_phone: form.contact_phone.trim() || null,
        contact_email: form.contact_email.trim() || null,
      });
      onSubmitted(result);
    } catch (err) {
      setError(err.message ?? "送出失敗，請稍後再試");
    } finally {
      setSubmitting(false);
    }
  }

  const fieldStyle = {
    display: "block",
    width: "100%",
    padding: "9px 14px",
    borderRadius: "var(--radius-md)",
    border: "1px solid var(--line)",
    background: "var(--surface-strong)",
    fontSize: 14,
    boxSizing: "border-box",
    outline: "none",
    marginTop: 6,
  };

  const labelStyle = {
    display: "block",
    fontSize: 13,
    fontWeight: 600,
    color: "var(--muted)",
    marginBottom: 16,
  };

  return (
    <section className="panel" style={{ maxWidth: 560 }}>
      <p className="eyebrow">Vendor Application</p>
      <h2>申請成為供應商</h2>
      <p className="panel-copy" style={{ marginBottom: 24 }}>
        填寫基本資料後送出，管理員審核通過後即可開始上架菜單。
      </p>

      <form onSubmit={handleSubmit}>
        <label style={labelStyle}>
          廠商名稱 *
          <input
            name="vendor_name"
            value={form.vendor_name}
            onChange={handleChange}
            placeholder="例：晴天廚房"
            style={fieldStyle}
          />
        </label>

        <label style={labelStyle}>
          地址
          <input
            name="address"
            value={form.address}
            onChange={handleChange}
            placeholder="例：台北市信義區..."
            style={fieldStyle}
          />
        </label>

        <label style={labelStyle}>
          營業時間
          <input
            name="business_hours"
            value={form.business_hours}
            onChange={handleChange}
            placeholder="例：11:00 – 14:00"
            style={fieldStyle}
          />
        </label>

        <label style={labelStyle}>
          聯絡電話
          <input
            name="contact_phone"
            value={form.contact_phone}
            onChange={handleChange}
            placeholder="例：02-1234-5678"
            style={fieldStyle}
          />
        </label>

        <label style={labelStyle}>
          聯絡 Email
          <input
            name="contact_email"
            type="email"
            value={form.contact_email}
            onChange={handleChange}
            placeholder="例：vendor@example.com"
            style={fieldStyle}
          />
        </label>

        {error && (
          <p style={{ color: "var(--brand)", fontSize: 13, marginBottom: 12 }}>{error}</p>
        )}

        <button
          type="submit"
          disabled={submitting}
          style={{
            padding: "10px 24px",
            borderRadius: "var(--radius-md)",
            border: "none",
            background: "var(--brand)",
            color: "#fff",
            fontWeight: 600,
            fontSize: 14,
            cursor: submitting ? "not-allowed" : "pointer",
            opacity: submitting ? 0.7 : 1,
          }}
        >
          {submitting ? "送出中..." : "送出申請"}
        </button>
      </form>
    </section>
  );
}

export default function VendorApplyPage() {
  const [application, setApplication] = useState(undefined);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMyVendorApplication()
      .then((data) => setApplication(data))
      .catch(() => setApplication(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="loading-state">載入中...</p>;

  return (
    <div>
      <div className="page-header">
        <p className="eyebrow">Vendor · Onboarding</p>
        <h2>供應商申請</h2>
      </div>

      {application ? (
        <PendingBanner application={application} />
      ) : (
        <ApplicationForm onSubmitted={(result) => setApplication(result)} />
      )}
    </div>
  );
}
