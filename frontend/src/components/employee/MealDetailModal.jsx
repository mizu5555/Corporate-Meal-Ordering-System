import { useEffect, useState } from "react";
import { useCart } from "../../cart/CartContext";
import { formatPrice, photoUrl, quotaLabel } from "../../utils/format";

export default function MealDetailModal({ item, onClose }) {
  const photo = photoUrl(item.photo_path);
  const quota = quotaLabel(item.daily_quota);
  const soldOut = item.daily_quota === 0;
  const unavailable = !item.available || soldOut;

  const [quantity, setQuantity] = useState(1);
  const [added, setAdded] = useState(false);
  const { addItem } = useCart();

  const maxQty = item.daily_quota > 0 ? Math.min(item.daily_quota, 99) : 99;

  useEffect(() => {
    function onKey(e) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  function handleAddToCart() {
    addItem(item, item.vendor_id, quantity);
    setAdded(true);
    setTimeout(() => {
      setAdded(false);
      onClose();
    }, 800);
  }

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label={item.name}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="modal">
        {photo ? (
          <img className="modal-photo" src={photo} alt={item.name} />
        ) : (
          <div className="modal-photo-placeholder" aria-hidden="true">🍱</div>
        )}

        <div className="modal-body">
          <div>
            <h2 className="modal-title">{item.name}</h2>
            <p className="modal-price">{formatPrice(item.price_cents)}</p>
          </div>

          {item.description && (
            <p className="modal-description">{item.description}</p>
          )}

          <div>
            <div className="modal-detail-row">
              <span className="modal-detail-label">供應狀態</span>
              {unavailable ? (
                <span className="badge badge-unavailable">
                  {soldOut ? "今日售完" : "暫停供應"}
                </span>
              ) : (
                <span className="badge badge-available">供應中</span>
              )}
            </div>

            {quota && (
              <div className="modal-detail-row">
                <span className="modal-detail-label">今日配額</span>
                <span className="badge badge-quota">{quota}</span>
              </div>
            )}

            {item.daily_quota === null && (
              <div className="modal-detail-row">
                <span className="modal-detail-label">今日配額</span>
                <span style={{ color: "var(--muted)" }}>無限制</span>
              </div>
            )}
          </div>
        </div>

        <div className="modal-footer">
          {!unavailable && (
            <div className="quantity-stepper">
              <button
                className="stepper-btn"
                type="button"
                aria-label="減少數量"
                onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                disabled={quantity <= 1}
              >
                −
              </button>
              <span className="stepper-value">{quantity}</span>
              <button
                className="stepper-btn"
                type="button"
                aria-label="增加數量"
                onClick={() => setQuantity((q) => Math.min(maxQty, q + 1))}
                disabled={quantity >= maxQty}
              >
                ＋
              </button>
            </div>
          )}
          <button className="ghost-button" onClick={onClose} type="button"
            style={{ color: "var(--text)", borderColor: "var(--line)", background: "transparent" }}>
            關閉
          </button>
          {!unavailable && (
            <button
              className={`primary-button${added ? " primary-button-added" : ""}`}
              type="button"
              onClick={handleAddToCart}
              disabled={added}
            >
              {added ? "已加入！" : "加入購物車"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
