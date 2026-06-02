/**
 * VendorMenuSchedulePage — 菜單品項每日排程設定
 *
 * 顯示訂餐視窗內 7 天的每日覆寫設定，廠商可針對各日期覆寫
 * 供應狀態、份數上限、售價。未設定覆寫的日期沿用品項基礎值。
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  deleteMenuItemScheduleDate,
  getMyProfile,
  getMenuItemSchedule,
  upsertMenuItemScheduleDate,
} from "../../api/vendor";
import { useVendorMenu } from "../../vendor/VendorMenuContext";
import { formatPrice } from "../../utils/format";

const WINDOW_DAYS = 7;
const WEEKDAY = ["日", "一", "二", "三", "四", "五", "六"];

function addDays(d, n) {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

function toIso(d) {
  return d.toISOString().slice(0, 10);
}

/** Build the 7-day window starting from today. */
function buildWindow() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Array.from({ length: WINDOW_DAYS }, (_, i) => {
    const d = addDays(today, i);
    return { iso: toIso(d), label: `${d.getMonth() + 1}/${d.getDate()} (${WEEKDAY[d.getDay()]})` };
  });
}

const WINDOW = buildWindow();

// ── Edit panel for a single day ───────────────────────────────────────────────

function DayEditor({ item, override, onSave, onDelete, onClose }) {
  const hasOverride = override != null;

  const [form, setForm] = useState({
    available: hasOverride && override.available != null ? override.available : item.available,
    daily_quota:
      hasOverride && override.daily_quota != null
        ? String(override.daily_quota)
        : item.daily_quota != null
        ? String(item.daily_quota)
        : "",
    price_cents:
      hasOverride && override.price_cents != null
        ? String(override.price_cents / 100)
        : String(item.price_cents / 100),
    is_recommended: hasOverride ? Boolean(override.is_recommended) : false,
    // track which fields the vendor actually wants to override
    override_available: hasOverride && override.available != null,
    override_quota: hasOverride && override.daily_quota != null,
    override_price: hasOverride && override.price_cents != null,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
  }

  async function handleSave() {
    const payload = {
      available: form.override_available ? form.available : null,
      daily_quota: form.override_quota
        ? form.daily_quota === ""
          ? null
          : Number(form.daily_quota)
        : null,
      price_cents: form.override_price
        ? Math.round(parseFloat(form.price_cents) * 100)
        : null,
      is_recommended: form.is_recommended,
    };
    // If nothing is being overridden, treat as delete
    if (
      payload.available === null &&
      payload.daily_quota === null &&
      payload.price_cents === null &&
      payload.is_recommended === false
    ) {
      await handleDelete();
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSave(payload);
      onClose();
    } catch (err) {
      setError(err.message ?? "儲存失敗");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setSaving(true);
    setError(null);
    try {
      await onDelete();
      onClose();
    } catch (err) {
      setError(err.message ?? "刪除失敗");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 16 }}>
      {error && <p style={{ color: "var(--brand)", margin: 0, fontSize: 13 }}>{error}</p>}

      {/* Available */}
      <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
        <input
          type="checkbox"
          name="override_available"
          checked={form.override_available}
          onChange={handleChange}
          style={{ width: 16, height: 16 }}
        />
        <span style={{ fontWeight: 600, fontSize: 13 }}>覆寫供應狀態</span>
      </label>
      {form.override_available && (
        <label style={{ display: "flex", alignItems: "center", gap: 10, marginLeft: 26, cursor: "pointer" }}>
          <input
            type="checkbox"
            name="available"
            checked={form.available}
            onChange={handleChange}
            style={{ width: 16, height: 16 }}
          />
          <span style={{ fontSize: 13 }}>當日供應中</span>
        </label>
      )}

      {/* Quota */}
      <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
        <input
          type="checkbox"
          name="override_quota"
          checked={form.override_quota}
          onChange={handleChange}
          style={{ width: 16, height: 16 }}
        />
        <span style={{ fontWeight: 600, fontSize: 13 }}>覆寫份數上限</span>
      </label>
      {form.override_quota && (
        <input
          className="form-input"
          name="daily_quota"
          type="number"
          min="0"
          value={form.daily_quota}
          onChange={handleChange}
          placeholder="0 = 當日售完；留空 = 不限"
          style={{ marginLeft: 26 }}
        />
      )}

      {/* Price */}
      <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
        <input
          type="checkbox"
          name="override_price"
          checked={form.override_price}
          onChange={handleChange}
          style={{ width: 16, height: 16 }}
        />
        <span style={{ fontWeight: 600, fontSize: 13 }}>覆寫售價（元）</span>
      </label>
      {form.override_price && (
        <input
          className="form-input"
          name="price_cents"
          type="number"
          min="0"
          step="0.5"
          value={form.price_cents}
          onChange={handleChange}
          placeholder="例：90"
          style={{ marginLeft: 26 }}
        />
      )}

      <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
        <input
          type="checkbox"
          name="is_recommended"
          checked={form.is_recommended}
          onChange={handleChange}
          style={{ width: 16, height: 16 }}
        />
        <span style={{ fontWeight: 600, fontSize: 13 }}>標記為今日推薦</span>
      </label>

      <div style={{ display: "flex", gap: 10, marginTop: 4 }}>
        <button
          className="primary-button"
          type="button"
          onClick={handleSave}
          disabled={saving}
          style={{ flex: 1 }}
        >
          {saving ? "儲存中…" : "儲存"}
        </button>
        {hasOverride && (
          <button
            type="button"
            onClick={handleDelete}
            disabled={saving}
            style={{
              padding: "8px 14px",
              borderRadius: "var(--radius-md)",
              border: "1px solid rgba(200,92,44,0.3)",
              background: "rgba(200,92,44,0.07)",
              color: "var(--brand)",
              fontWeight: 600,
              fontSize: 13,
              cursor: saving ? "not-allowed" : "pointer",
              opacity: saving ? 0.6 : 1,
            }}
          >
            清除
          </button>
        )}
        <button className="ghost-button" type="button" onClick={onClose} disabled={saving}>
          取消
        </button>
      </div>
    </div>
  );
}

// ── Day card ──────────────────────────────────────────────────────────────────

function DayCard({ day, item, override, isEditing, onEdit, onSave, onDelete, onClose }) {
  const effectiveAvailable = override?.available ?? item.available;
  const effectiveQuota =
    override?.daily_quota != null ? override.daily_quota : item.daily_quota;
  const effectivePrice =
    override?.price_cents != null ? override.price_cents : item.price_cents;
  const effectiveRecommended = override?.is_recommended === true;
  const hasOverride = override != null;

  return (
    <div
      className="panel"
      style={{
        padding: "16px 20px",
        borderLeft: hasOverride
          ? "3px solid var(--brand)"
          : "3px solid transparent",
        transition: "border-color 140ms ease",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <div>
          <p style={{ margin: 0, fontWeight: 700, fontSize: 15 }}>{day.label}</p>
          {hasOverride && (
            <p style={{ margin: "2px 0 0", fontSize: 11, color: "var(--brand)", fontWeight: 600 }}>
              已設定覆寫
            </p>
          )}
        </div>
        {!isEditing && (
          <button
            className="ghost-button"
            type="button"
            style={{ minHeight: 32, padding: "0 12px", fontSize: 12 }}
            onClick={onEdit}
          >
            {hasOverride ? "編輯" : "設定"}
          </button>
        )}
      </div>

      {/* Effective values */}
      {!isEditing && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <span
            className={`badge ${effectiveAvailable ? "badge-available" : "badge-unavailable"}`}
          >
            {effectiveAvailable ? "供應中" : "暫停供應"}
          </span>
          {effectiveQuota != null && (
            <span className="badge badge-quota">
              {effectiveQuota === 0 ? "今日售完" : `配額 ${effectiveQuota}`}
            </span>
          )}
          <span style={{ fontSize: 13, color: "var(--muted)", alignSelf: "center" }}>
            {formatPrice(effectivePrice)}
          </span>
          {effectiveRecommended && (
            <span className="badge badge-recommended">今日推薦</span>
          )}
        </div>
      )}

      {isEditing && (
        <DayEditor
          item={item}
          override={override}
          onSave={(payload) => onSave(day.iso, payload)}
          onDelete={() => onDelete(day.iso)}
          onClose={onClose}
        />
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function VendorMenuSchedulePage() {
  const { itemId } = useParams();
  const navigate = useNavigate();
  const { getItem, loading: menuLoading } = useVendorMenu();

  const [overrides, setOverrides] = useState({}); // { iso: override }
  const [loadingSchedule, setLoadingSchedule] = useState(true);
  const [scheduleError, setScheduleError] = useState(null);
  const [editingDate, setEditingDate] = useState(null);
  const [recommendationLimit, setRecommendationLimit] = useState(3);

  const item = getItem(Number(itemId));

  useEffect(() => {
    let active = true;
    getMyProfile()
      .then((profile) => {
        if (active) setRecommendationLimit(profile.daily_recommendation_limit ?? 3);
      })
      .catch(() => {
        if (active) setRecommendationLimit(3);
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (menuLoading) return;
    if (!item) return;
    setLoadingSchedule(true);
    getMenuItemSchedule(Number(itemId))
      .then((list) => {
        const map = {};
        for (const ov of list) map[ov.meal_date] = ov;
        setOverrides(map);
      })
      .catch((err) => setScheduleError(err.message ?? "無法載入排程"))
      .finally(() => setLoadingSchedule(false));
  }, [itemId, menuLoading, item]);

  async function handleSave(iso, payload) {
    const ov = await upsertMenuItemScheduleDate(Number(itemId), iso, payload);
    setOverrides((prev) => ({ ...prev, [iso]: ov }));
  }

  async function handleDelete(iso) {
    await deleteMenuItemScheduleDate(Number(itemId), iso);
    setOverrides((prev) => {
      const next = { ...prev };
      delete next[iso];
      return next;
    });
  }

  if (menuLoading) {
    return (
      <div>
        <div className="page-header">
          <p className="eyebrow">Vendor · Menu</p>
          <h2>每日排程</h2>
        </div>
        <p className="loading-state">載入中…</p>
      </div>
    );
  }

  if (!item) {
    return (
      <div>
        <div className="page-header">
          <p className="eyebrow">Vendor · Menu</p>
          <h2>每日排程</h2>
        </div>
        <p className="error-state">找不到此餐點。</p>
        <button className="ghost-button" type="button" onClick={() => navigate("/vendor/menu")}>
          返回菜單
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header" style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
        <div>
          <p className="eyebrow">Vendor · Menu</p>
          <h2>每日排程 — {item.name}</h2>
          <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: 13 }}>
            基礎值：{item.available ? "供應中" : "暫停"} ·{" "}
            {item.daily_quota != null ? `配額 ${item.daily_quota}` : "不限份數"} ·{" "}
            {formatPrice(item.price_cents)} · 今日推薦每日最多 {recommendationLimit} 道
          </p>
        </div>
        <button className="ghost-button" type="button" onClick={() => navigate("/vendor/menu")}>
          返回菜單
        </button>
      </div>

      {scheduleError && <p className="error-state">{scheduleError}</p>}
      {loadingSchedule && <p className="loading-state">載入排程中…</p>}

      {!loadingSchedule && !scheduleError && (
        <>
          <p style={{ color: "var(--muted)", fontSize: 13, marginBottom: 20 }}>
            橘色左邊框的日期已設定覆寫；點擊「設定」新增覆寫，「清除」則回歸基礎值。
          </p>
          <div style={{ display: "grid", gap: 12 }}>
            {WINDOW.map((day) => (
              <DayCard
                key={day.iso}
                day={day}
                item={item}
                override={overrides[day.iso] ?? null}
                isEditing={editingDate === day.iso}
                onEdit={() => setEditingDate(day.iso)}
                onSave={handleSave}
                onDelete={handleDelete}
                onClose={() => setEditingDate(null)}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
