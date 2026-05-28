import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import FacilityScopeLabel from "../../facility/FacilityScopeLabel";
import { formatPrice, photoUrl } from "../../utils/format";
import { useVendorMenu } from "../../vendor/VendorMenuContext";

// ── Photo thumbnail cell ──────────────────────────────────────────────────────

function MenuItemPhoto({ item, onUpload, onDelete }) {
  const inputRef = useRef(null);
  const [state, setState] = useState("idle"); // "idle" | "uploading" | "deleting"
  const [hover, setHover] = useState(false);
  const url = photoUrl(item.photo_path, item._photo_v);
  const busy = state !== "idle";

  async function handleFileChange(e) {
    const file = e.target.files[0];
    if (!file) return;
    setState("uploading");
    try {
      await onUpload(item.id, file);
    } catch (err) {
      alert(err.message ?? "上傳失敗，請稍後再試。");
    } finally {
      setState("idle");
      e.target.value = "";
    }
  }

  async function handleDelete(e) {
    e.stopPropagation();
    if (!window.confirm(`確定要刪除「${item.name}」的照片嗎？`)) return;
    setState("deleting");
    try {
      await onDelete(item.id);
    } catch (err) {
      alert(err.message ?? "刪除失敗，請稍後再試。");
    } finally {
      setState("idle");
    }
  }

  return (
    <div
      style={{ position: "relative", width: 72, height: 72, flexShrink: 0 }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      {/* Thumbnail / placeholder — click to upload */}
      <button
        type="button"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
        title={url ? "點擊更換照片" : "點擊上傳照片"}
        style={{
          display: "block",
          width: "100%",
          height: "100%",
          padding: 0,
          border: url ? "none" : "1.5px dashed var(--line)",
          borderRadius: "var(--radius-md)",
          overflow: "hidden",
          background: url ? "transparent" : "rgba(23,33,43,0.04)",
          cursor: busy ? "not-allowed" : "pointer",
          position: "relative",
        }}
      >
        {url ? (
          <img
            src={url}
            alt={item.name}
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
          />
        ) : (
          <span
            style={{
              display: "grid",
              placeItems: "center",
              height: "100%",
              fontSize: 26,
              color: "var(--muted)",
            }}
          >
            🍽️
          </span>
        )}

        {/* Hover / busy overlay */}
        {(hover || busy) && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: "rgba(0,0,0,0.46)",
              display: "grid",
              placeItems: "center",
              color: "#fff",
              fontSize: 11,
              fontWeight: 700,
              borderRadius: "var(--radius-md)",
              pointerEvents: "none",
            }}
          >
            {state === "uploading" ? "上傳中…" : state === "deleting" ? "刪除中…" : url ? "更換" : "上傳"}
          </div>
        )}
      </button>

      {/* ✕ delete badge — only shown when there's a photo and hovering */}
      {url && hover && !busy && (
        <button
          type="button"
          onClick={handleDelete}
          title="刪除照片"
          style={{
            position: "absolute",
            top: -7,
            right: -7,
            width: 20,
            height: 20,
            borderRadius: "50%",
            border: "2px solid var(--surface-strong)",
            background: "var(--brand)",
            color: "#fff",
            fontSize: 13,
            lineHeight: 1,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 0,
            zIndex: 2,
          }}
        >
          ×
        </button>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        style={{ display: "none" }}
        onChange={handleFileChange}
      />
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function VendorMenuListPage() {
  const navigate = useNavigate();
  const { items, loading, error, removeItem, uploadPhoto, removePhoto } = useVendorMenu();

  async function handleDelete(item) {
    if (!window.confirm(`確定要刪除「${item.name}」嗎？`)) return;
    try {
      await removeItem(item.id);
    } catch (err) {
      alert(err.message ?? "刪除失敗，請稍後再試。");
    }
  }

  return (
    <div>
      <div
        className="page-header"
        style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}
      >
        <div>
          <FacilityScopeLabel label="Managing facility" />
          <p className="eyebrow">Vendor · Menu</p>
          <h2>菜單管理</h2>
        </div>
        <button
          className="primary-button"
          type="button"
          onClick={() => navigate("/vendor/menu/new")}
        >
          + 新增餐點
        </button>
      </div>

      {loading && <p className="loading-state">載入菜單中…</p>}
      {error && <p className="error-state">無法載入菜單，請稍後再試。</p>}
      {!loading && !error && items.length === 0 && (
        <p className="empty-state">尚未建立任何餐點，點擊「新增餐點」開始。</p>
      )}

      {!loading && !error && items.length > 0 && (
        <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
          {/* Header row */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "72px 1fr 90px 120px auto",
              gap: 12,
              alignItems: "center",
              padding: "10px 20px",
              borderBottom: "1px solid var(--line)",
              color: "var(--muted)",
              fontSize: 12,
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            <span>照片</span>
            <span>餐點</span>
            <span style={{ textAlign: "right" }}>售價</span>
            <span style={{ textAlign: "center" }}>狀態</span>
            <span />
          </div>

          {items.map((item, idx) => (
            <div
              key={item.id}
              style={{
                display: "grid",
                gridTemplateColumns: "72px 1fr 90px 120px auto",
                gap: 12,
                alignItems: "center",
                padding: "14px 20px",
                borderBottom: idx < items.length - 1 ? "1px solid var(--line)" : "none",
              }}
            >
              {/* Photo cell */}
              <MenuItemPhoto
                item={item}
                onUpload={uploadPhoto}
                onDelete={removePhoto}
              />

              {/* Name + description */}
              <div style={{ minWidth: 0 }}>
                <p style={{ fontWeight: 600, margin: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {item.name}
                </p>
                {item.description && (
                  <p
                    style={{
                      color: "var(--muted)",
                      fontSize: 13,
                      margin: "2px 0 0",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {item.description}
                  </p>
                )}
              </div>

              {/* Price */}
              <p style={{ textAlign: "right", margin: 0, fontWeight: 600 }}>
                {formatPrice(item.price_cents)}
              </p>

              {/* Badges */}
              <div style={{ display: "flex", gap: 6, justifyContent: "center", flexWrap: "wrap" }}>
                <span className={`badge ${item.available ? "badge-available" : "badge-unavailable"}`}>
                  {item.available ? "供應中" : "暫停供應"}
                </span>
                {item.daily_quota !== null && item.daily_quota !== undefined && (
                  <span className="badge badge-quota">
                    {item.daily_quota === 0 ? "今日售完" : `配額 ${item.daily_quota}`}
                  </span>
                )}
              </div>

              {/* Actions */}
              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                <button
                  className="ghost-button"
                  type="button"
                  style={{ minHeight: 36, padding: "0 14px", fontSize: 13 }}
                  onClick={() => navigate(`/vendor/menu/${item.id}/edit`)}
                >
                  編輯
                </button>
                <button
                  className="ghost-button"
                  type="button"
                  style={{
                    minHeight: 36,
                    padding: "0 14px",
                    fontSize: 13,
                    color: "var(--brand)",
                    borderColor: "rgba(200,92,44,0.35)",
                  }}
                  onClick={() => handleDelete(item)}
                >
                  刪除
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
