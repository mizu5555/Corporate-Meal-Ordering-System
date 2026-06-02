import { useEffect, useState } from "react";

import {
  createFacility,
  getFacilities,
  getVendorApplications,
  getVendorFacilities,
  getVendorRecommendationLimit,
  setVendorFacilities,
  setVendorRecommendationLimit,
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

// ── Shared button style helper ────────────────────────────────────────────────

function inlineBtnStyle(variant) {
  const base = {
    padding: "5px 14px",
    borderRadius: "var(--radius-md)",
    border: "none",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
  };
  if (variant === "save")
    return { ...base, background: "rgba(47,125,74,0.12)", color: "var(--success)" };
  if (variant === "config")
    return { ...base, background: "rgba(47,100,200,0.10)", color: "#2b5cc8" };
  return { ...base, background: "var(--line)", color: "var(--text)" };
}

// ── Panel B: 商家服務廠區一覽 ─────────────────────────────────────────────────

const VENDOR_GRID = "minmax(180px, 1fr) 1fr 120px";

function VendorFacilityEditor({ vendorId, allFacilities, onClose, onSaved }) {
  const [checkedIds, setCheckedIds]             = useState(new Set());
  const [recommendationLimit, setRecommendationLimit] = useState(3);
  const [loading, setLoading]                   = useState(true);
  const [saving, setSaving]                     = useState(false);
  const [error, setError]                       = useState(null);
  const [success, setSuccess]                   = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    setSuccess(false);
    Promise.all([
      getVendorFacilities(vendorId),
      getVendorRecommendationLimit(vendorId),
    ])
      .then(([facs, limitData]) => {
        if (!active) return;
        setCheckedIds(new Set(facs.map((f) => f.id)));
        setRecommendationLimit(limitData.daily_recommendation_limit ?? 3);
      })
      .catch(() => { if (active) setError("無法載入商家設定"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [vendorId]);

  function toggleFacility(id) {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setSuccess(false);
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      await Promise.all([
        setVendorFacilities(vendorId, Array.from(checkedIds)),
        setVendorRecommendationLimit(vendorId, recommendationLimit),
      ]);
      setSuccess(true);
      onSaved?.();
    } catch {
      setError("儲存失敗，請稍後再試。");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      style={{
        gridColumn: "1 / -1",
        padding: "14px 20px 16px",
        borderTop: "1px dashed var(--line)",
        background: "rgba(47,100,200,0.03)",
      }}
    >
      {loading && <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>載入中…</p>}

      {!loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {/* Facility checkboxes */}
          <div>
            <p style={{ margin: "0 0 8px", fontSize: 13, fontWeight: 600, color: "#2b5cc8" }}>
              服務廠區（可多選；空選表示不限廠區）
            </p>
            {allFacilities.length === 0 ? (
              <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>
                尚無廠區可指派，請先在廠區面板新增。
              </p>
            ) : (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px 24px" }}>
                {allFacilities.map((f) => (
                  <label
                    key={f.id}
                    style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 13 }}
                  >
                    <input
                      type="checkbox"
                      checked={checkedIds.has(f.id)}
                      onChange={() => toggleFacility(f.id)}
                    />
                    <span>{f.code}　{f.name}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Recommendation limit */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <span style={{ fontSize: 13, fontWeight: 600 }}>今日推薦上限：</span>
            <select
              value={recommendationLimit}
              onChange={(e) => { setRecommendationLimit(Number(e.target.value)); setSuccess(false); }}
              style={{
                padding: "5px 10px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--line)",
                background: "var(--surface-strong)",
                fontSize: 13,
                cursor: "pointer",
              }}
            >
              <option value={1}>每天最多 1 道</option>
              <option value={2}>每天最多 2 道</option>
              <option value={3}>每天最多 3 道</option>
            </select>
          </div>

          {/* Actions */}
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <button type="button" onClick={handleSave} disabled={saving} style={inlineBtnStyle("save")}>
              {saving ? "儲存中…" : "儲存"}
            </button>
            <button type="button" onClick={onClose} style={inlineBtnStyle()}>
              關閉
            </button>
            {success && (
              <span style={{ fontSize: 13, color: "var(--success)", fontWeight: 600 }}>✓ 已儲存</span>
            )}
            {error && (
              <span style={{ fontSize: 13, color: "var(--brand)" }}>{error}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function VendorFacilitiesPanel() {
  const [vendors, setVendors]                   = useState([]);
  const [allFacilities, setAllFacilities]       = useState([]);
  const [facilityMap, setFacilityMap]           = useState({});  // vendor_id -> Facility[]
  const [loading, setLoading]                   = useState(true);
  const [error, setError]                       = useState(null);
  const [expandedVendorId, setExpandedVendorId] = useState(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    Promise.all([getVendorApplications("approved"), getFacilities()])
      .then(([vendorData, facilityData]) => {
        if (!active) return;
        setVendors(vendorData);
        setAllFacilities(facilityData);
        // Progressively load each vendor's facility assignments
        vendorData.forEach((v) => {
          getVendorFacilities(v.vendor_id)
            .then((facs) => {
              if (active) setFacilityMap((prev) => ({ ...prev, [v.vendor_id]: facs }));
            })
            .catch(() => {});
        });
      })
      .catch(() => { if (active) setError("無法載入資料"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  function toggleExpand(vendorId) {
    setExpandedVendorId((prev) => (prev === vendorId ? null : vendorId));
  }

  function refreshVendorFacilities(vendorId) {
    getVendorFacilities(vendorId)
      .then((facs) => setFacilityMap((prev) => ({ ...prev, [vendorId]: facs })))
      .catch(() => {});
  }

  return (
    <article className="panel">
      <p className="eyebrow">廠區管理</p>
      <h2>商家服務廠區</h2>

      {loading && <p className="panel-copy">載入中…</p>}
      {error && <p className="error-state">{error}</p>}

      {!loading && !error && vendors.length === 0 && (
        <p className="panel-copy">目前沒有已核准的商家。</p>
      )}

      {!loading && !error && vendors.length > 0 && (
        <div
          style={{
            border: "1px solid var(--line)",
            borderRadius: "var(--radius-md)",
            overflow: "hidden",
            marginTop: 12,
          }}
        >
          {/* Header */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: VENDOR_GRID,
              padding: "8px 16px",
              background: "var(--surface-strong)",
              borderBottom: "1px solid var(--line)",
              fontSize: 12,
              fontWeight: 600,
              color: "var(--muted)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            <span>商家名稱</span>
            <span>服務廠區</span>
            <span style={{ textAlign: "right" }}>操作</span>
          </div>

          {vendors.map((v, idx) => {
            const isExpanded   = expandedVendorId === v.vendor_id;
            const isLast       = idx === vendors.length - 1;
            const vFacilities  = facilityMap[v.vendor_id];   // undefined = still loading

            return (
              <div
                key={v.vendor_id}
                style={{
                  display: "grid",
                  gridTemplateColumns: VENDOR_GRID,
                  borderBottom: (!isLast || isExpanded) ? "1px solid var(--line)" : "none",
                  alignItems: "center",
                }}
              >
                {/* Vendor name */}
                <div style={{ padding: "12px 16px", fontSize: 14, fontWeight: 500 }}>
                  {v.vendor_name}
                </div>

                {/* Facility chips */}
                <div style={{ padding: "12px 8px", fontSize: 13 }}>
                  {vFacilities === undefined ? (
                    <span style={{ color: "var(--muted)", fontSize: 12 }}>…</span>
                  ) : vFacilities.length === 0 ? (
                    <span style={{ color: "var(--muted)", fontSize: 12 }}>不限廠區</span>
                  ) : (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                      {vFacilities.map((f) => (
                        <span
                          key={f.id}
                          style={{
                            padding: "2px 9px",
                            borderRadius: 99,
                            fontSize: 12,
                            fontWeight: 600,
                            background: "rgba(47,100,200,0.10)",
                            color: "#2b5cc8",
                          }}
                        >
                          {f.code}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Action */}
                <div style={{ padding: "12px 16px", textAlign: "right" }}>
                  <button
                    type="button"
                    onClick={() => toggleExpand(v.vendor_id)}
                    style={inlineBtnStyle(isExpanded ? "default" : "config")}
                  >
                    {isExpanded ? "收起" : "設定"}
                  </button>
                </div>

                {/* Inline editor */}
                {isExpanded && (
                  <VendorFacilityEditor
                    vendorId={v.vendor_id}
                    allFacilities={allFacilities}
                    onClose={() => setExpandedVendorId(null)}
                    onSaved={() => refreshVendorFacilities(v.vendor_id)}
                  />
                )}
              </div>
            );
          })}
        </div>
      )}
    </article>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function AdminFacilitiesPage() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(280px, 340px) 1fr", gap: 18, alignItems: "start" }}>
      <FacilitiesPanel />
      <VendorFacilitiesPanel />
    </div>
  );
}
