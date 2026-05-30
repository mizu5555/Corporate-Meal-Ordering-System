import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { photoUrl } from "../../utils/format";
import { useVendorMenu } from "../../vendor/VendorMenuContext";

const EMPTY_FORM = {
  name: "",
  description: "",
  price_cents: "",
  available: true,
  daily_quota: "",
};

function formToData(form) {
  return {
    name: form.name.trim(),
    description: form.description.trim() || null,
    price_cents: Math.round(parseFloat(form.price_cents) * 100),
    available: form.available,
    daily_quota: form.daily_quota === "" ? null : Number(form.daily_quota),
  };
}

export default function VendorMenuFormPage() {
  const { itemId } = useParams();
  const navigate = useNavigate();
  const { getItem, loading, addItem, updateItem, uploadPhoto, removePhoto } = useVendorMenu();
  const isEdit = Boolean(itemId);

  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState(null);
  const [notFound, setNotFound] = useState(false);

  // Photo state — edit mode only
  const photoInputRef = useRef(null);
  const [photoState, setPhotoState] = useState("idle"); // "idle" | "uploading" | "deleting"

  useEffect(() => {
    if (!isEdit) return;
    // Wait for the menu to finish loading before deciding the item is missing —
    // otherwise a refresh / deep link redirects away before data arrives.
    if (loading) return;
    const item = getItem(Number(itemId));
    if (!item) { setNotFound(true); return; }
    setNotFound(false);
    setForm({
      name: item.name,
      description: item.description ?? "",
      price_cents: (item.price_cents / 100).toString(),
      available: item.available,
      daily_quota: item.daily_quota === null || item.daily_quota === undefined ? "" : String(item.daily_quota),
    });
  }, [isEdit, itemId, loading, getItem]);

  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (!form.name.trim()) { setError("請填寫餐點名稱。"); return; }
    if (!form.price_cents || isNaN(parseFloat(form.price_cents))) { setError("請填寫有效價格。"); return; }

    try {
      const data = formToData(form);
      if (isEdit) {
        await updateItem(Number(itemId), data);
      } else {
        await addItem(data);
      }
      navigate("/vendor/menu");
    } catch (err) {
      setError(err.message ?? "儲存失敗，請稍後再試。");
    }
  }

  async function handlePhotoUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setPhotoState("uploading");
    setError(null);
    try {
      await uploadPhoto(Number(itemId), file);
    } catch (err) {
      setError(err.message ?? "照片上傳失敗，請稍後再試。");
    } finally {
      setPhotoState("idle");
      e.target.value = "";
    }
  }

  async function handlePhotoDelete() {
    const item = getItem(Number(itemId));
    if (!item?.photo_path) return;
    if (!window.confirm("確定要刪除這張照片嗎？")) return;
    setPhotoState("deleting");
    setError(null);
    try {
      await removePhoto(Number(itemId));
    } catch (err) {
      setError(err.message ?? "照片刪除失敗，請稍後再試。");
    } finally {
      setPhotoState("idle");
    }
  }

  // Live item — reflects photo_path changes without re-mounting
  const currentItem = isEdit ? getItem(Number(itemId)) : null;
  const currentPhotoUrl = photoUrl(currentItem?.photo_path, currentItem?._photo_v);
  const photoBusy = photoState !== "idle";

  if (isEdit && loading) {
    return (
      <div>
        <div className="page-header">
          <p className="eyebrow">Vendor · Menu</p>
          <h2>編輯餐點</h2>
        </div>
        <p className="panel-copy">載入中…</p>
      </div>
    );
  }

  if (isEdit && notFound) {
    return (
      <div>
        <div className="page-header">
          <p className="eyebrow">Vendor · Menu</p>
          <h2>編輯餐點</h2>
        </div>
        <p className="error-state" style={{ marginBottom: 16 }}>找不到此餐點，可能已被刪除。</p>
        <button className="ghost-button" type="button" onClick={() => navigate("/vendor/menu")}>
          返回菜單
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <p className="eyebrow">Vendor · Menu</p>
        <h2>{isEdit ? "編輯餐點" : "新增餐點"}</h2>
      </div>

      {error && <p className="error-state" style={{ marginBottom: 16 }}>{error}</p>}

      <form className="panel" onSubmit={handleSubmit} style={{ maxWidth: 560 }}>
        <div style={{ display: "grid", gap: 20 }}>

          {/* ── Photo section (edit mode only) ── */}
          {isEdit && (
            <div style={{ display: "grid", gap: 10 }}>
              <span style={{ fontWeight: 600 }}>餐點照片</span>

              {/* Preview */}
              <div
                style={{
                  width: "100%",
                  height: 200,
                  borderRadius: "var(--radius-lg)",
                  overflow: "hidden",
                  border: "1px solid var(--line)",
                  background: "linear-gradient(135deg, #f0e8d8 0%, #e8dcc8 100%)",
                  display: "grid",
                  placeItems: "center",
                  position: "relative",
                }}
              >
                {currentPhotoUrl ? (
                  <img
                    src={currentPhotoUrl}
                    alt={currentItem?.name}
                    style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                  />
                ) : (
                  <span style={{ fontSize: 52, opacity: 0.5 }}>🍽️</span>
                )}

                {/* Busy overlay */}
                {photoBusy && (
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      background: "rgba(0,0,0,0.46)",
                      display: "grid",
                      placeItems: "center",
                      color: "#fff",
                      fontWeight: 700,
                      fontSize: 15,
                    }}
                  >
                    {photoState === "uploading" ? "上傳中…" : "刪除中…"}
                  </div>
                )}
              </div>

              {/* Photo action buttons */}
              <div style={{ display: "flex", gap: 10 }}>
                <button
                  type="button"
                  disabled={photoBusy}
                  onClick={() => photoInputRef.current?.click()}
                  style={{
                    padding: "8px 18px",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--line)",
                    background: "var(--surface-strong)",
                    cursor: photoBusy ? "not-allowed" : "pointer",
                    fontWeight: 600,
                    fontSize: 13,
                    opacity: photoBusy ? 0.6 : 1,
                    transition: "opacity 140ms ease",
                  }}
                >
                  {currentPhotoUrl ? "更換照片" : "上傳照片"}
                </button>

                {currentPhotoUrl && (
                  <button
                    type="button"
                    disabled={photoBusy}
                    onClick={handlePhotoDelete}
                    style={{
                      padding: "8px 18px",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid rgba(200,92,44,0.3)",
                      background: "rgba(200,92,44,0.07)",
                      color: "var(--brand)",
                      cursor: photoBusy ? "not-allowed" : "pointer",
                      fontWeight: 600,
                      fontSize: 13,
                      opacity: photoBusy ? 0.6 : 1,
                      transition: "opacity 140ms ease",
                    }}
                  >
                    刪除照片
                  </button>
                )}
              </div>

              <p style={{ color: "var(--muted)", fontSize: 12, margin: 0 }}>
                支援 JPEG、PNG、WebP，檔案大小上限 5 MB，長邊會自動縮至 1600px。
              </p>

              <input
                ref={photoInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                style={{ display: "none" }}
                onChange={handlePhotoUpload}
              />
            </div>
          )}

          {/* ── Name ── */}
          <label style={{ display: "grid", gap: 6 }}>
            <span style={{ fontWeight: 600 }}>餐點名稱 *</span>
            <input
              className="form-input"
              name="name"
              value={form.name}
              onChange={handleChange}
              required
              placeholder="例：雞腿飯"
            />
          </label>

          {/* ── Description ── */}
          <label style={{ display: "grid", gap: 6 }}>
            <span style={{ fontWeight: 600 }}>描述</span>
            <textarea
              className="form-input"
              name="description"
              value={form.description}
              onChange={handleChange}
              rows={3}
              placeholder="食材、口味、配菜說明..."
              style={{ resize: "vertical" }}
            />
          </label>

          {/* ── Price ── */}
          <label style={{ display: "grid", gap: 6 }}>
            <span style={{ fontWeight: 600 }}>價格（元）*</span>
            <input
              className="form-input"
              name="price_cents"
              type="number"
              min="0"
              step="0.5"
              value={form.price_cents}
              onChange={handleChange}
              required
              placeholder="例：90"
            />
          </label>

          {/* ── Daily quota ── */}
          <label style={{ display: "grid", gap: 6 }}>
            <span style={{ fontWeight: 600 }}>今日配額</span>
            <input
              className="form-input"
              name="daily_quota"
              type="number"
              min="0"
              value={form.daily_quota}
              onChange={handleChange}
              placeholder="留空表示不限制"
            />
            <span style={{ color: "var(--muted)", fontSize: 13 }}>
              填 0 表示今日售完；留空表示無限制
            </span>
          </label>

          {/* ── Available toggle ── */}
          <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
            <input
              type="checkbox"
              name="available"
              checked={form.available}
              onChange={handleChange}
              style={{ width: 18, height: 18 }}
            />
            <span style={{ fontWeight: 600 }}>供應中</span>
          </label>

        </div>

        <div style={{ display: "flex", gap: 12, marginTop: 28 }}>
          <button className="primary-button" type="submit">
            {isEdit ? "儲存變更" : "建立餐點"}
          </button>
          <button
            className="ghost-button"
            type="button"
            onClick={() => navigate("/vendor/menu")}
          >
            取消
          </button>
        </div>
      </form>
    </div>
  );
}
