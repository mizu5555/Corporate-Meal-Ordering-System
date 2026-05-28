import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { submitSelection } from "../../api/employee";
import { useCart } from "../../cart/CartContext";
import { useFacility } from "../../facility/FacilityContext";
import FacilityScopeLabel from "../../facility/FacilityScopeLabel";
import { formatPrice } from "../../utils/format";

function errorMessage(item, err) {
  if (err.code === "ITEM_UNAVAILABLE" || err.code === "item_unavailable") {
    return `${item.item.name} 已停止供應`;
  }
  if (
    err.code === "QUOTA_EXHAUSTED" ||
    err.code === "quantity_exceeds_daily_quota" ||
    err.code === "quota_exhausted"
  ) {
    return `${item.item.name} 今日配額已售完，請調整數量或選其他餐點`;
  }
  if (err.code === "CONCURRENT_CONFLICT") {
    return `${item.item.name} 下單時有人同時更新庫存，請再試一次`;
  }
  return `${item.item.name} 送出失敗，請稍後再試`;
}

export default function CartPage() {
  const { items, updateQuantity, removeItem, clearCart, totalCount } = useCart();
  const { selectedFacilityId } = useFacility();
  const navigate = useNavigate();

  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const totalCents = items.reduce(
    (sum, i) => sum + i.item.price_cents * i.quantity,
    0,
  );

  async function handleSubmit() {
    setSubmitting(true);
    setResult(null);

    const errors = [];
    for (const cartItem of items) {
      try {
        await submitSelection(cartItem.vendorId, {
          itemId: cartItem.item.id,
          quantity: cartItem.quantity,
          facilityId: selectedFacilityId,
        });
      } catch (err) {
        errors.push(errorMessage(cartItem, err));
      }
    }

    setSubmitting(false);

    if (errors.length === 0) {
      clearCart();
      setResult({ ok: true });
    } else {
      setResult({ ok: false, errors });
    }
  }

  if (result?.ok) {
    return (
      <div>
        <div className="page-header">
          <p className="eyebrow">Employee · Order</p>
          <h2>訂單已送出</h2>
        </div>
        <div className="panel" style={{ marginTop: 24 }}>
          <p className="panel-copy">您的餐點已成功送出，請等待廠商確認。</p>
          <div style={{ display: "flex", gap: 12, marginTop: 20 }}>
            <button
              className="primary-button"
              type="button"
              onClick={() => navigate("/employee/orders")}
            >
              查看訂單
            </button>
            <button
              className="ghost-button"
              type="button"
              onClick={() => navigate("/employee/menu")}
            >
              繼續點餐
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (totalCount === 0) {
    return (
      <div>
        <div className="page-header">
          <p className="eyebrow">Employee · Cart</p>
          <h2>購物車</h2>
        </div>
        <p className="empty-state" style={{ marginTop: 40 }}>購物車是空的</p>
        <button
          className="ghost-button"
          type="button"
          style={{ marginTop: 16 }}
          onClick={() => navigate("/employee/menu")}
        >
          ← 去瀏覽菜單
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <FacilityScopeLabel label="Order facility" />
        <p className="eyebrow">Employee · Cart</p>
        <h2>購物車</h2>
      </div>

      {result?.errors && (
        <div className="error-state" style={{ marginBottom: 20 }}>
          <strong>部分品項送出失敗：</strong>
          <ul style={{ margin: "8px 0 0 16px" }}>
            {result.errors.map((msg, i) => <li key={i}>{msg}</li>)}
          </ul>
        </div>
      )}

      <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
        {items.map((cartItem, idx) => (
          <div
            key={cartItem.item.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 16,
              padding: "16px 20px",
              borderBottom: idx < items.length - 1 ? "1px solid var(--line)" : "none",
            }}
          >
            <div style={{ flex: 1 }}>
              <p style={{ fontWeight: 600, margin: 0 }}>{cartItem.item.name}</p>
              <p style={{ color: "var(--muted)", fontSize: 13, margin: "2px 0 0" }}>
                {formatPrice(cartItem.item.price_cents)} / 份
              </p>
            </div>

            <div className="quantity-stepper">
              <button
                className="stepper-btn"
                type="button"
                aria-label="減少數量"
                onClick={() => updateQuantity(cartItem.item.id, cartItem.quantity - 1)}
                disabled={cartItem.quantity <= 1}
              >
                −
              </button>
              <span className="stepper-value">{cartItem.quantity}</span>
              <button
                className="stepper-btn"
                type="button"
                aria-label="增加數量"
                onClick={() => updateQuantity(cartItem.item.id, cartItem.quantity + 1)}
              >
                ＋
              </button>
            </div>

            <p style={{ width: 80, textAlign: "right", fontWeight: 600, margin: 0 }}>
              {formatPrice(cartItem.item.price_cents * cartItem.quantity)}
            </p>

            <button
              type="button"
              aria-label={`移除 ${cartItem.item.name}`}
              onClick={() => removeItem(cartItem.item.id)}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "var(--muted)",
                fontSize: 18,
                padding: "4px 8px",
              }}
            >
              ×
            </button>
          </div>
        ))}
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginTop: 20,
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>合計</p>
          <p style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>{formatPrice(totalCents)}</p>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          <button
            className="ghost-button"
            type="button"
            onClick={clearCart}
            disabled={submitting}
          >
            清空購物車
          </button>
          <button
            className="primary-button"
            type="button"
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? "送出中..." : "送出訂單"}
          </button>
        </div>
      </div>
    </div>
  );
}
