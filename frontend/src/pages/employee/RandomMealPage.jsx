import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { drawRandomMeal, getRecommendations, submitSelection } from "../../api/employee";
import { useFacility } from "../../facility/FacilityContext";
import FacilityScopeLabel from "../../facility/FacilityScopeLabel";
import { useVendors } from "../../hooks/useVendors";
import { formatPrice, quotaLabel } from "../../utils/format";

function toLocalIso(date) {
  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return localDate.toISOString().slice(0, 10);
}

function addDaysIso(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return toLocalIso(date);
}

function drawErrorMessage(err) {
  if (err.code === "no_random_meal_available") {
    return "No available meals remain for the selected date and restaurants.";
  }
  if (err.code === "validation_error") return err.message ?? "Choose a valid date and restaurant range.";
  return "Could not draw a meal. Please try again.";
}

export default function RandomMealPage() {
  const navigate = useNavigate();
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
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  // --- 熱門推薦 state ---
  const [recommendations, setRecommendations] = useState([]);
  const [recLoading, setRecLoading] = useState(false);
  const [recError, setRecError] = useState(null);
  const [recSubmitting, setRecSubmitting] = useState(null); // item id being submitted
  const [recSubmitted, setRecSubmitted] = useState(null);   // item id successfully submitted
  const [recSubmitError, setRecSubmitError] = useState(null);

  const selectedCount = allVendors ? vendors.length : selectedVendorIds.length;
  const mealDateInRange = mealDate >= minMealDate && mealDate <= maxMealDate;
  const canDraw = mealDateInRange && selectedCount > 0 && !drawing && !loading;
  const remainingLabel = useMemo(() => {
    if (!draw) return null;
    if (draw.remaining_quantity == null) return "Unlimited";
    return `${draw.remaining_quantity} left`;
  }, [draw]);

  useEffect(() => {
    setSelectedVendorIds([]);
    setDraw(null);
    setSubmitted(false);
    setRecSubmitted(null);
    setRecSubmitError(null);
  }, [selectedFacilityId]);

  // Fetch recommendations whenever the tab, mealDate, or facilityId changes
  useEffect(() => {
    if (tab !== "recommend") return;
    let cancelled = false;
    setRecLoading(true);
    setRecError(null);
    setRecSubmitted(null);
    setRecSubmitError(null);
    getRecommendations({ facilityId: selectedFacilityId, mealDate })
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
  }, [tab, mealDate, selectedFacilityId]);

  function toggleVendor(vendorId) {
    setSelectedVendorIds((current) =>
      current.includes(vendorId)
        ? current.filter((id) => id !== vendorId)
        : [...current, vendorId],
    );
    setDraw(null);
    setSubmitted(false);
  }

  async function handleDraw() {
    setDrawing(true);
    setDrawError(null);
    setSubmitted(false);
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

  async function handleConfirm() {
    if (!draw) return;
    setSubmitting(true);
    setDrawError(null);
    try {
      await submitSelection(draw.vendor.id, {
        itemId: draw.item.id,
        quantity: 1,
        mealDate,
        facilityId: selectedFacilityId,
      });
      setSubmitted(true);
    } catch (err) {
      setDrawError(drawErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRecOrder(rec) {
    setRecSubmitting(rec.item.id);
    setRecSubmitError(null);
    try {
      await submitSelection(rec.vendor.id, {
        itemId: rec.item.id,
        quantity: 1,
        mealDate,
        facilityId: selectedFacilityId,
      });
      setRecSubmitted(rec.item.id);
    } catch (err) {
      setRecSubmitError(
        err?.message ?? "訂購失敗，請稍後再試。"
      );
    } finally {
      setRecSubmitting(null);
    }
  }

  function recRemainingLabel(rec) {
    if (rec.remaining_quantity == null) return quotaLabel(rec.item.daily_quota);
    return `剩餘 ${rec.remaining_quantity} 份`;
  }

  return (
    <div>
      <div className="page-header">
        <FacilityScopeLabel label="Random meal facility" />
        <p className="eyebrow">Employee / 推薦與隨機抽餐</p>
        <h2>今天吃什麼？</h2>
      </div>

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
              setSubmitted(false);
            }}
          />

          {/* Vendor selector — only shown for 隨機抽餐 tab */}
          {tab === "random" && (
            <>
              <div className="random-vendor-header">
                <div>
                  <p className="field-label">Restaurants</p>
                  <p className="panel-copy">{selectedCount} selected</p>
                </div>
                <label className="toggle-row">
                  <input
                    type="checkbox"
                    checked={allVendors}
                    onChange={(event) => {
                      setAllVendors(event.target.checked);
                      setDraw(null);
                      setSubmitted(false);
                    }}
                  />
                  <span>All restaurants</span>
                </label>
              </div>

              {loading && <p className="loading-state compact-state">Loading restaurants...</p>}
              {error && <p className="error-state">Could not load restaurants.</p>}

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
                {drawing ? "Drawing..." : draw ? "Draw again" : "Draw a meal"}
              </button>
            </>
          )}
        </div>

        {/* Tab content panel */}
        <div className="panel random-meal-result" style={{ flexDirection: "column", alignItems: "stretch" }}>
          {/* Tab buttons */}
          <div className="range-pills" style={{ marginBottom: "16px" }}>
            <button
              type="button"
              className={`range-pill${tab === "recommend" ? " is-active" : ""}`}
              onClick={() => setTab("recommend")}
            >
              熱門推薦
            </button>
            <button
              type="button"
              className={`range-pill${tab === "random" ? " is-active" : ""}`}
              onClick={() => setTab("random")}
            >
              隨機抽餐
            </button>
          </div>

          {/* 熱門推薦 tab */}
          {tab === "recommend" && (
            <div>
              {recLoading && <p className="loading-state compact-state">載入推薦中…</p>}
              {recError && <p className="error-state">{recError}</p>}
              {!recLoading && !recError && recommendations.length === 0 && (
                <p className="panel-copy" style={{ textAlign: "center", marginTop: "24px" }}>
                  目前沒有可推薦的餐點
                </p>
              )}
              {recSubmitError && <p className="error-state">{recSubmitError}</p>}
              {!recLoading && !recError && recommendations.length > 0 && (
                <ol style={{ listStyle: "none", padding: 0, margin: 0 }}>
                  {recommendations.map((rec, index) => (
                    <li
                      key={`${rec.vendor.id}-${rec.item.id}`}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "12px",
                        padding: "12px 0",
                        borderBottom: "1px solid var(--line)",
                      }}
                    >
                      <span
                        style={{
                          minWidth: "28px",
                          fontWeight: 700,
                          fontSize: "1.1rem",
                          color: index < 3 ? "var(--brand)" : "var(--muted)",
                        }}
                      >
                        {index + 1}
                      </span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <p className="eyebrow" style={{ marginBottom: "2px" }}>{rec.vendor.name}</p>
                        <p style={{ fontWeight: 600, margin: "0 0 4px" }}>{rec.item.name}</p>
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
                      {recSubmitted === rec.item.id ? (
                        <div style={{ textAlign: "center" }}>
                          <p className="eyebrow" style={{ color: "var(--brand)", marginBottom: "4px" }}>已訂購</p>
                          <button
                            className="ghost-button"
                            type="button"
                            onClick={() => navigate("/employee/orders")}
                          >
                            查看訂單
                          </button>
                        </div>
                      ) : (
                        <button
                          className="primary-button"
                          type="button"
                          style={{ whiteSpace: "nowrap", flexShrink: 0 }}
                          onClick={() => handleRecOrder(rec)}
                          disabled={recSubmitting === rec.item.id}
                        >
                          {recSubmitting === rec.item.id ? "訂購中…" : "訂購"}
                        </button>
                      )}
                    </li>
                  ))}
                </ol>
              )}
            </div>
          )}

          {/* 隨機抽餐 tab */}
          {tab === "random" && (
            <div>
              {!draw && !drawError && (
                <div className="random-placeholder">
                  <p className="eyebrow">Ready</p>
                  <h3>Pick a date and restaurant range.</h3>
                  <p className="panel-copy">The result will be selected completely at random from meals that still have quota left.</p>
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
                    <span className="badge badge-available">Available</span>
                    <span className="badge badge-quota">
                      {remainingLabel ?? quotaLabel(draw.item.daily_quota)}
                    </span>
                  </div>

                  {submitted ? (
                    <div className="success-state">
                      <p>Order sent for {mealDate}.</p>
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={() => navigate("/employee/orders")}
                      >
                        View orders
                      </button>
                    </div>
                  ) : (
                    <div className="random-result-actions">
                      <button
                        className="ghost-button"
                        type="button"
                        onClick={handleDraw}
                        disabled={drawing || submitting}
                      >
                        Draw again
                      </button>
                      <button
                        className="primary-button"
                        type="button"
                        onClick={handleConfirm}
                        disabled={submitting}
                      >
                        {submitting ? "Sending..." : "Choose this meal"}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
