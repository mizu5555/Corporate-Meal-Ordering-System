import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
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
  const { getItem, addItem, updateItem } = useVendorMenu();
  const isEdit = Boolean(itemId);

  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isEdit) return;
    const item = getItem(Number(itemId));
    if (!item) { navigate("/vendor/menu"); return; }
    setForm({
      name: item.name,
      description: item.description ?? "",
      price_cents: (item.price_cents / 100).toString(),
      available: item.available,
      daily_quota: item.daily_quota === null || item.daily_quota === undefined ? "" : String(item.daily_quota),
    });
  }, [isEdit, itemId, navigate, getItem]);

  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (!form.name.trim()) { setError("請填寫餐點名稱。"); return; }
    if (!form.price_cents || isNaN(parseFloat(form.price_cents))) { setError("請填寫有效價格。"); return; }

    const data = formToData(form);
    if (isEdit) {
      updateItem(Number(itemId), data);
    } else {
      addItem(data);
    }
    navigate("/vendor/menu");
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
