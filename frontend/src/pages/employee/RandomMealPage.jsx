import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { drawRandomMeal, submitSelection } from "../../api/employee";
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
  const [allVendors, setAllVendors] = useState(true);
  const [selectedVendorIds, setSelectedVendorIds] = useState([]);
  const [draw, setDraw] = useState(null);
  const [drawError, setDrawError] = useState(null);
  const [drawing, setDrawing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

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
  }, [selectedFacilityId]);

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

  return (
    <div>
      <div className="page-header">
        <FacilityScopeLabel label="Random meal facility" />
        <p className="eyebrow">Employee / Random Meal</p>
        <h2>Let the menu decide</h2>
      </div>

      <section className="random-meal-layout">
        <div className="panel random-meal-controls">
          <label className="field-label" htmlFor="random-meal-date">
            Meal date
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
        </div>

        <div className="panel random-meal-result">
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
      </section>
    </div>
  );
}
