import { useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { changePassword } from "../../api/employee";
import { useFacility } from "../../facility/FacilityContext";
import { saveHomeFacilityId } from "../../facility/facilitySelection";

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
      <h3 style={{ margin: "0 0 16px" }}>修改密碼</h3>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14, maxWidth: 360 }}>
        <label className="field">
          <span>目前密碼</span>
          <input
            required
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            autoComplete="current-password"
          />
        </label>
        <label className="field">
          <span>新密碼</span>
          <input
            required
            type="password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            autoComplete="new-password"
            minLength={8}
          />
        </label>
        <label className="field">
          <span>確認新密碼</span>
          <input
            required
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password"
          />
        </label>
        {error && <p className="form-error" style={{ margin: 0 }}>{error}</p>}
        {success && <p style={{ margin: 0, color: "var(--success)", fontSize: 14 }}>密碼修改成功。</p>}
        <button className="button-primary" disabled={saving} type="submit" style={{ alignSelf: "flex-start" }}>
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
