import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { drawRandomMeal, getRecommendations } from "../../api/employee";
import { useCart } from "../../cart/CartContext";
import { useFacility } from "../../facility/FacilityContext";
import FacilityScopeLabel from "../../facility/FacilityScopeLabel";
import { useVendors } from "../../hooks/useVendors";
import { toLocalIso } from "../../utils/date";
import { formatPrice, quotaLabel } from "../../utils/format";

function addDaysIso(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return toLocalIso(date);
}

function drawErrorMessage(err) {
  if (err.code === "no_random_meal_available") {
    return "所選日期與餐廳目前沒有可抽的餐點。";
  }
  if (err.code === "validation_error") return err.message ?? "請選擇有效的日期與餐廳範圍。";
  return "抽籤失敗，請再試一次。";
}

export default function RandomMealPage() {
  const navigate = useNavigate();
  const { addItem } = useCart();
  const { selectedFacilityId } = useFacility();
  const { vendors, loading, error } = useVendors({ facilityId: selectedFacilityId });
  const minMealDate = addDaysIso(0);
  const maxMealDate = addDaysIso(6);
  const [mealDate, setMealDate] = useState(minMealDate);
  const [tab, setTab] = useState("recommend");

  // --- 隨機抽餐 state ---
  const [allVendors, setAllVendors] = useState(true);
  const [selectedVendorIds, setSelectedVendorIds] = useState([]);
  const [draw, setDraw] = useState(null);
  const [drawError, setDrawError] = useState(null);
  const [drawing, setDrawing] = useState(false);
  const [addedToCart, setAddedToCart] = useState(false);

  // --- 熱門推薦 state ---
  const [recommendations, setRecommendations] = useState([]);
  const [recLoading, setRecLoading] = useState(false);
  const [recError, setRecError] = useState(null);
  const [limit, setLimit] = useState(10);

  const selectedCount = allVendors ? vendors.length : selectedVendorIds.length;
  const mealDateInRange = mealDate >= minMealDate && mealDate <= maxMealDate;
  const canDraw = mealDateInRange && selectedCount > 0 && !drawing && !loading;
  const remainingLabel = useMemo(() => {
    if (!draw) return null;
    if (draw.remaining_quantity == null) return "不限量";
    return `剩餘 ${draw.remaining_quantity} 份`;
  }, [draw]);

  useEffect(() => {
    setSelectedVendorIds([]);
    setDraw(null);
    setAddedToCart(false);
  }, [selectedFacilityId]);

  // Fetch recommendations whenever the tab, mealDate, or facilityId changes
  useEffect(() => {
    if (tab !== "recommend") return;
    let cancelled = false;
    setRecLoading(true);
    setRecError(null);
    getRecommendations({ facilityId: selectedFacilityId, mealDate, limit })
      .then((data) => {
        if (!cancelled) setRecommendations(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setRecError("無法載入推薦餐點，請稍後再試。");
          setRecommendations([]);
        }
      })
      .finally(() => {
        if (!cancelled) setRecLoading(false);
      });
    return () => { cancelled = true; };
  }, [tab, mealDate, selectedFacilityId, limit]);

  function toggleVendor(vendorId) {
    setSelectedVendorIds((current) =>
      current.includes(vendorId)
        ? current.filter((id) => id !== vendorId)
        : [...current, vendorId],
    );
    setDraw(null);
  }

  async function handleDraw() {
    setDrawing(true);
    setDrawError(null);
    setAddedToCart(false);
    try {
      const result = await drawRandomMeal({
        mealDate,
        vendorIds: allVendors ? null : selectedVendorIds,
        facilityId: selectedFacilityId,
      });
      setDraw(result);
    } catch (err) {
      setDraw(null);
      setDrawError(drawErrorMessage(err));
    } finally {
      setDrawing(false);
    }
  }

  function handleAddDrawToCart() {
    if (!draw) return;
    addItem(draw.item, draw.vendor.id, 1, mealDate);
    setAddedToCart(true);
  }

  function handleAddRecToCart(rec) {
    addItem(rec.item, rec.vendor.id, 1, mealDate);
    setAddedToCart(true);
  }

  function recRemainingLabel(rec) {
    if (rec.remaining_quantity == null) return quotaLabel(rec.item.daily_quota);
    return `剩餘 ${rec.remaining_quantity} 份`;
  }

  return (
    <div>
      <div className="page-header">
        <FacilityScopeLabel label="隨機抽餐設施" />
        <p className="eyebrow">員工 / 推薦與隨機抽餐</p>
        <h2>今天吃什麼？</h2>
      </div>

      {addedToCart && (
        <div
          className="success-state"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            marginBottom: 16,
          }}
        >
          <span>✅ 已加入購物車</span>
          <button
            className="ghost-button"
            type="button"
            onClick={() => navigate("/employee/cart")}
          >
            去結帳
          </button>
        </div>
      )}

      {/* Shared selectors */}
      <section className="random-meal-layout">
        <div className="panel random-meal-controls">
          <label className="field-label" htmlFor="random-meal-date">
            用餐日期
          </label>
          <input
            className="date-input"
            id="random-meal-date"
            max={maxMealDate}
            min={minMealDate}
            type="date"
            value={mealDate}
            onChange={(event) => {
              setMealDate(event.target.value);
              setDraw(null);
              setAddedToCart(false);
            }}
          />

          {/* Vendor selector — only shown for 隨機抽餐 tab */}
          {tab === "random" && (
            <>
              <div className="random-vendor-header">
                <div>
                  <p className="field-label">餐廳</p>
                  <p className="panel-copy">已選 {selectedCount} 間</p>
                </div>
                <label className="toggle-row">
                  <input
                    type="checkbox"
                    checked={allVendors}
                    onChange={(event) => {
                      setAllVendors(event.target.checked);
                      setDraw(null);
                      setAddedToCart(false);
                    }}
                  />
                  <span>全部餐廳</span>
                </label>
              </div>

              {loading && <p className="loading-state compact-state">載入餐廳中…</p>}
              {error && <p className="error-state">無法載入餐廳。</p>}

              {!loading && !error && !allVendors && (
                <div className="vendor-check-list">
                  {vendors.map((vendor) => (
                    <label className="vendor-check-row" key={vendor.id}>
                      <input
                        type="checkbox"
                        checked={selectedVendorIds.includes(vendor.id)}
                        onChange={() => toggleVendor(vendor.id)}
                      />
                      <span>{vendor.name}</span>
                    </label>
                  ))}
                </div>
              )}

              <button
                className="primary-button random-draw-button"
                type="button"
                onClick={handleDraw}
                disabled={!canDraw}
              >
                {drawing ? "抽籤中…" : draw ? "重新抽" : "抽一份"}
              </button>
            </>
          )}
        </div>

        {/* Tab content panel */}
        <div className="panel random-meal-result">
          {/* Tab buttons */}
          <div className="range-pills" style={{ marginBottom: "16px" }}>
            <button
              type="button"
              className={`range-pill${tab === "recommend" ? " is-active" : ""}`}
              onClick={() => { setTab("recommend"); setAddedToCart(false); }}
            >
              熱門推薦
            </button>
            <button
              type="button"
              className={`range-pill${tab === "random" ? " is-active" : ""}`}
              onClick={() => { setTab("random"); setAddedToCart(false); }}
            >
              隨機抽餐
            </button>
          </div>

          {/* 熱門推薦 tab */}
          {tab === "recommend" && (
            <div className="recommend-panel">
              {/* 顯示數量 selector */}
              <div className="recommend-limit-row">
                <span className="field-label">顯示數量</span>
                <div className="range-pills" style={{ margin: 0 }}>
                  {[10, 20].map((n) => (
                    <button
                      key={n}
                      type="button"
                      className={`range-pill${limit === n ? " is-active" : ""}`}
                      onClick={() => setLimit(n)}
                    >
                      前 {n}
                    </button>
                  ))}
                </div>
              </div>

              {recLoading && <p className="loading-state compact-state">載入推薦中…</p>}
              {recError && <p className="error-state">{recError}</p>}
              {!recLoading && !recError && recommendations.length === 0 && (
                <p className="recommend-empty">目前沒有可推薦的餐點</p>
              )}
              {!recLoading && !recError && recommendations.length > 0 && (
                <div className="recommend-grid">
                  {recommendations.map((rec, index) => (
                    <div
                      key={`${rec.vendor.id}-${rec.item.id}`}
                      className="recommend-card"
                    >
                      <div className="recommend-card-rank" data-top={index < 3 || undefined}>
                        {index + 1}
                      </div>
                      <div className="recommend-card-body">
                        <p className="eyebrow" style={{ marginBottom: "2px" }}>{rec.vendor.name}</p>
                        <p className="recommend-card-name">{rec.item.name}</p>
                        <div className="item-badges">
                          <span className="badge badge-quota">
                            {formatPrice(rec.item.price_cents)}
                          </span>
                          {rec.from_sales && rec.quantity_sold > 0 && (
                            <span className="badge badge-available">
                              已售 {rec.quantity_sold} 份
                            </span>
                          )}
                          <span className="badge badge-quota">
                            {recRemainingLabel(rec)}
                          </span>
                        </div>
                      </div>
                      <div className="recommend-card-action">
                        <button
                          className="primary-button"
                          type="button"
                          onClick={() => handleAddRecToCart(rec)}
                        >
                          加入購物車
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 隨機抽餐 tab */}
          {tab === "random" && (
            <div className="random-draw-panel">
              {!draw && !drawError && (
                <div className="random-placeholder">
                  <p className="eyebrow">準備就緒</p>
                  <h3>選擇日期與餐廳範圍。</h3>
                  <p className="panel-copy">系統會從仍有額度的餐點中完全隨機抽出一份。</p>
                </div>
              )}

              {drawError && <p className="error-state">{drawError}</p>}

              {draw && (
                <div className="random-result-card">
                  <p className="eyebrow">{draw.vendor.name}</p>
                  <h3>{draw.item.name}</h3>
                  <p className="random-price">{formatPrice(draw.item.price_cents)}</p>
                  {draw.item.description && (
                    <p className="panel-copy">{draw.item.description}</p>
                  )}
                  <div className="item-badges">
                    <span className="badge badge-available">可供選擇</span>
                    <span className="badge badge-quota">
                      {remainingLabel ?? quotaLabel(draw.item.daily_quota)}
                    </span>
                  </div>

                  <div className="random-result-actions">
                    <button
                      className="ghost-button"
                      type="button"
                      onClick={handleDraw}
                      disabled={drawing}
                    >
                      重新抽
                    </button>
                    <button
                      className="primary-button"
                      type="button"
                      onClick={handleAddDrawToCart}
                    >
                      加入購物車
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
