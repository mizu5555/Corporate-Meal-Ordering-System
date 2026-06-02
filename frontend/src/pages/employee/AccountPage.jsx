import { useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { changePassword } from "../../api/employee";
import { useFacility } from "../../facility/FacilityContext";
import { saveHomeFacilityId } from "../../facility/facilitySelection";

function PasswordInput({ label, value, onChange, autoComplete, minLength, placeholder }) {
  const [visible, setVisible] = useState(false);

  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <span className="pw-field">
        <input
          className="form-input"
          required
          type={visible ? "text" : "password"}
          value={value}
          onChange={onChange}
          autoComplete={autoComplete}
          minLength={minLength}
          placeholder={placeholder}
        />
        <button
          type="button"
          className="pw-toggle"
          onClick={() => setVisible((show) => !show)}
          aria-label={visible ? `隱藏${label}` : `顯示${label}`}
          aria-pressed={visible}
          title={visible ? `隱藏${label}` : `顯示${label}`}
        >
          {visible ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
              <line x1="1" y1="1" x2="23" y2="23" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          )}
        </button>
      </span>
    </label>
  );
}

function ChangePasswordForm() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (next !== confirm) {
      setError("新密碼與確認密碼不一致");
      return;
    }
    if (next.length < 8) {
      setError("新密碼至少需要 8 個字元");
      return;
    }

    setSaving(true);
    try {
      await changePassword(current, next);
      setSuccess(true);
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (err) {
      if (err.code === "wrong_current_password") {
        setError("目前密碼不正確");
      } else {
        setError(err.message ?? "修改失敗，請稍後再試");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="panel" style={{ marginBottom: 24 }}>
      <div className="account-form-header">
        <h3 style={{ margin: 0 }}>修改密碼</h3>
        <p className="panel-copy">建議使用至少 8 個字元，並避免與其他系統共用密碼。</p>
      </div>
      <form className="account-password-form" onSubmit={handleSubmit}>
        <PasswordInput
          label="目前密碼"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          autoComplete="current-password"
          placeholder="輸入目前密碼"
        />
        <PasswordInput
          label="新密碼"
          value={next}
          onChange={(e) => setNext(e.target.value)}
          autoComplete="new-password"
          minLength={8}
          placeholder="至少 8 個字元"
        />
        <PasswordInput
          label="確認新密碼"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          autoComplete="new-password"
          placeholder="再次輸入新密碼"
        />
        {error && <p className="error-state" style={{ margin: 0, textAlign: "left" }}>{error}</p>}
        {success && <p style={{ margin: 0, color: "var(--success)", fontSize: 14, fontWeight: 700 }}>密碼修改成功。</p>}
        <button className="primary-button" disabled={saving} type="submit" style={{ alignSelf: "flex-start" }}>
          {saving ? "儲存中..." : "儲存"}
        </button>
      </form>
    </div>
  );
}

function HomeFacilityForm() {
  const { user } = useAuth();
  const { facilities, selectedFacilityId, setSelectedFacilityId } = useFacility();
  const [saved, setSaved] = useState(false);

  if (!facilities || facilities.length === 0) return null;

  function handleChange(e) {
    const id = Number(e.target.value);
    saveHomeFacilityId(user?.numericId, id);
    setSelectedFacilityId(id);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="panel">
      <h3 style={{ margin: "0 0 8px" }}>預設廠區</h3>
      <p className="panel-copy" style={{ margin: "0 0 14px" }}>
        設定後，每次登入自動選取這個廠區，不再每次從第一個開始。
      </p>
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <select
          value={selectedFacilityId ?? ""}
          onChange={handleChange}
          style={{
            padding: "8px 14px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--line)",
            background: "var(--surface-strong)",
            fontSize: 14,
            cursor: "pointer",
          }}
        >
          {facilities.map((f) => (
            <option key={f.id} value={f.id}>
              {f.code} — {f.name}
            </option>
          ))}
        </select>
        {saved && <span style={{ fontSize: 13, color: "var(--success)" }}>已儲存</span>}
      </div>
    </div>
  );
}

export default function AccountPage() {
  return (
    <div>
      <div className="page-header">
        <p className="eyebrow">Employee · Account</p>
        <h2>帳號設定</h2>
      </div>
      <ChangePasswordForm />
      <HomeFacilityForm />
    </div>
  );
}
