import { useEffect, useState } from "react";

import {
  createFacility,
  getFacilities,
  getVendorApplications,
  getVendorFacilities,
  setVendorFacilities,
} from "../../api/admin";

// ── Panel A: 廠區列表 + 新增表單 ────────────────────────────────────────────

function FacilitiesPanel() {
  const [facilities, setFacilities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState(null);

  function loadFacilities() {
    let active = true;
    setLoading(true);
    setError(null);
    getFacilities()
      .then((data) => { if (active) setFacilities(data); })
      .catch(() => { if (active) setError("無法載入廠區資料。"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }

  useEffect(loadFacilities, []);

  function handleCreate(e) {
    e.preventDefault();
    if (!code.trim() || !name.trim()) return;
    setCreating(true);
    setCreateError(null);
    createFacility({ code: code.trim(), name: name.trim() })
      .then((newFac) => {
        setFacilities((prev) => [...prev, newFac]);
        setCode("");
        setName("");
      })
      .catch(() => setCreateError("新增廠區失敗，請稍後再試。"))
      .finally(() => setCreating(false));
  }

  return (
    <article className="panel">
      <p className="eyebrow">廠區管理</p>
      <h2>廠區</h2>

      {loading && <p className="panel-copy">載入中…</p>}
      {error && <p className="error-state">{error}</p>}

      {!loading && !error && (
        <table className="data-table">
          <thead>
            <tr>
              <th>代碼</th>
              <th>名稱</th>
            </tr>
          </thead>
          <tbody>
            {facilities.map((f) => (
              <tr key={f.id}>
                <td>{f.code}</td>
                <td>{f.name}</td>
              </tr>
            ))}
            {facilities.length === 0 && (
              <tr>
                <td colSpan={2} className="table-empty">尚無廠區</td>
              </tr>
            )}
          </tbody>
        </table>
      )}

      <form onSubmit={handleCreate} style={{ marginTop: 20, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span style={{ fontSize: "0.8rem" }}>代碼</span>
          <input
            className="form-input"
            type="text"
            placeholder="例：A棟"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            required
            style={{ width: 120 }}
          />
        </label>
        <label style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span style={{ fontSize: "0.8rem" }}>名稱</span>
          <input
            className="form-input"
            type="text"
            placeholder="例：研發一廠"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            style={{ width: 180 }}
          />
        </label>
        <button
          type="submit"
          className="range-pill is-active"
          disabled={creating || !code.trim() || !name.trim()}
          style={{ alignSelf: "flex-end" }}
        >
          {creating ? "新增中…" : "新增廠區"}
        </button>
      </form>
      {createError && <p className="error-state" style={{ marginTop: 8 }}>{createError}</p>}
    </article>
  );
}

// ── Panel B: 商家服務廠區指派 ────────────────────────────────────────────────

function VendorFacilitiesPanel() {
  const [vendors, setVendors] = useState([]);
  const [vendorsLoading, setVendorsLoading] = useState(true);
  const [vendorsError, setVendorsError] = useState(null);

  const [allFacilities, setAllFacilities] = useState([]);
  const [facLoading, setFacLoading] = useState(true);
  const [facError, setFacError] = useState(null);

  const [selectedVendorId, setSelectedVendorId] = useState("");
  const [checkedIds, setCheckedIds] = useState(new Set());
  const [assignLoading, setAssignLoading] = useState(false);
  const [assignError, setAssignError] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Load approved vendors
  useEffect(() => {
    let active = true;
    setVendorsLoading(true);
    setVendorsError(null);
    getVendorApplications("approved")
      .then((data) => { if (active) setVendors(data); })
      .catch(() => { if (active) setVendorsError("無法載入商家清單。"); })
      .finally(() => { if (active) setVendorsLoading(false); });
    return () => { active = false; };
  }, []);

  // Load all facilities
  useEffect(() => {
    let active = true;
    setFacLoading(true);
    setFacError(null);
    getFacilities()
      .then((data) => { if (active) setAllFacilities(data); })
      .catch(() => { if (active) setFacError("無法載入廠區清單。"); })
      .finally(() => { if (active) setFacLoading(false); });
    return () => { active = false; };
  }, []);

  // When vendor changes, fetch its current facilities
  useEffect(() => {
    if (!selectedVendorId) {
      setCheckedIds(new Set());
      return;
    }
    let active = true;
    setAssignLoading(true);
    setAssignError(null);
    setSaveSuccess(false);
    getVendorFacilities(Number(selectedVendorId))
      .then((data) => {
        if (active) setCheckedIds(new Set(data.map((f) => f.id)));
      })
      .catch(() => {
        if (active) setAssignError("無法載入商家已指派廠區。");
      })
      .finally(() => {
        if (active) setAssignLoading(false);
      });
    return () => { active = false; };
  }, [selectedVendorId]);

  function toggleFacility(id) {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setSaveSuccess(false);
  }

  function handleSave(e) {
    e.preventDefault();
    if (!selectedVendorId) return;
    setAssignLoading(true);
    setAssignError(null);
    setSaveSuccess(false);
    setVendorFacilities(Number(selectedVendorId), Array.from(checkedIds))
      .then(() => setSaveSuccess(true))
      .catch(() => setAssignError("儲存失敗，請稍後再試。"))
      .finally(() => setAssignLoading(false));
  }

  const isLoading = vendorsLoading || facLoading;
  const hasError = vendorsError || facError;

  return (
    <article className="panel">
      <p className="eyebrow">廠區管理</p>
      <h2>商家服務廠區</h2>

      {isLoading && <p className="panel-copy">載入中…</p>}
      {hasError && <p className="error-state">{vendorsError ?? facError}</p>}

      {!isLoading && !hasError && (
        <>
          <label style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 16 }}>
            <span style={{ fontSize: "0.8rem" }}>選擇商家（已核准）</span>
            <select
              className="form-input"
              value={selectedVendorId}
              onChange={(e) => setSelectedVendorId(e.target.value)}
              style={{ maxWidth: 280 }}
            >
              <option value="">— 請選擇 —</option>
              {vendors.map((v) => (
                <option key={v.vendor_id} value={v.vendor_id}>
                  {v.vendor_name}
                </option>
              ))}
            </select>
          </label>

          {selectedVendorId && (
            <form onSubmit={handleSave}>
              {assignLoading && <p className="panel-copy">載入中…</p>}
              {!assignLoading && (
                <>
                  {allFacilities.length === 0 ? (
                    <p className="panel-copy">尚無廠區可指派，請先在上方新增廠區。</p>
                  ) : (
                    <fieldset style={{ border: "none", padding: 0, marginBottom: 12 }}>
                      <legend style={{ fontSize: "0.85rem", marginBottom: 8 }}>服務廠區（可多選）</legend>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 20px" }}>
                        {allFacilities.map((f) => (
                          <label key={f.id} style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
                            <input
                              type="checkbox"
                              checked={checkedIds.has(f.id)}
                              onChange={() => toggleFacility(f.id)}
                            />
                            <span>{f.code}　{f.name}</span>
                          </label>
                        ))}
                      </div>
                    </fieldset>
                  )}
                  <button
                    type="submit"
                    className="range-pill is-active"
                    disabled={assignLoading}
                  >
                    儲存
                  </button>
                </>
              )}
              {assignError && <p className="error-state" style={{ marginTop: 8 }}>{assignError}</p>}
              {saveSuccess && <p className="panel-copy" style={{ marginTop: 8, color: "var(--accent)" }}>已儲存。</p>}
            </form>
          )}
        </>
      )}
    </article>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function AdminFacilitiesPage() {
  return (
    <section className="dashboard-grid">
      <FacilitiesPanel />
      <VendorFacilitiesPanel />
    </section>
  );
}
