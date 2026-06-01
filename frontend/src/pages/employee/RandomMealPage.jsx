import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { drawRandomMeal, getRecommendations } from "../../api/employee";
import MealDetailModal from "../../components/employee/MealDetailModal";
import { useFacility } from "../../facility/FacilityContext";
import FacilityScopeLabel from "../../facility/FacilityScopeLabel";
import { useVendors } from "../../hooks/useVendors";
import { toLocalIso } from "../../utils/date";
import { dietaryTagLabel, normalizeDietaryTags } from "../../utils/dietaryTags";
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
  const location = useLocation();
  const { selectedFacilityId } = useFacility();
  const { vendors, loading, error } = useVendors({ facilityId: selectedFacilityId });
  const minMealDate = addDaysIso(0);
  const maxMealDate = addDaysIso(6);
  const requestedMealDate = new URLSearchParams(location.search).get("meal_date");
  const initialMealDate = requestedMealDate && requestedMealDate >= minMealDate && requestedMealDate <= maxMealDate
    ? requestedMealDate
    : minMealDate;
  const [mealDate, setMealDate] = useState(initialMealDate);
  const [tab, setTab] = useState("recommend");

  // --- 隨機抽餐 state ---
  const [allVendors, setAllVendors] = useState(true);
  const [selectedVendorIds, setSelectedVendorIds] = useState([]);
  const [draw, setDraw] = useState(null);
  const [drawError, setDrawError] = useState(null);
  const [drawing, setDrawing] = useState(false);
  const [detail, setDetail] = useState(null); // { item, remaining } shown in the meal-detail modal

  // --- 熱門推薦 state ---
  const [recommendations, setRecommendations] = useState([]);
  const [recLoading, setRecLoading] = useState(false);
  const [recError, setRecError] = useState(null);
  const [limit, setLimit] = useState(10);
  const [filters, setFilters] = useState({
    excludeBeef: false,
    excludePork: false,
    vegetarian: false,
    ovoLactoVegetarian: false,
  });

  const selectedCount = allVendors ? vendors.length : selectedVendorIds.length;
  const mealDateInRange = mealDate >= minMealDate && mealDate <= maxMealDate;
  const canDraw = mealDateInRange && selectedCount > 0 && !drawing && !loading;
  const includeTags = useMemo(() => {
    const tags = [];
    if (filters.vegetarian) tags.push("vegetarian");
    if (filters.ovoLactoVegetarian) tags.push("ovo_lacto_vegetarian");
    return tags;
  }, [filters.vegetarian, filters.ovoLactoVegetarian]);
  const excludeTags = useMemo(() => {
    const tags = [];
    if (filters.excludeBeef) tags.push("contains_beef");
    if (filters.excludePork) tags.push("contains_pork");
    return tags;
  }, [filters.excludeBeef, filters.excludePork]);
  const remainingLabel = useMemo(() => {
    if (!draw) return null;
    if (draw.remaining_quantity == null) return "不限量";
    return `剩餘 ${draw.remaining_quantity} 份`;
  }, [draw]);

  useEffect(() => {
    setSelectedVendorIds([]);
    setDraw(null);
  }, [selectedFacilityId]);

  // Fetch recommendations whenever the tab, mealDate, or facilityId changes
  useEffect(() => {
    if (tab !== "recommend") return;
    let cancelled = false;
    setRecLoading(true);
    setRecError(null);
    getRecommendations({ facilityId: selectedFacilityId, mealDate, limit, includeTags, excludeTags })
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
  }, [tab, mealDate, selectedFacilityId, limit, includeTags, excludeTags]);

  function toggleVendor(vendorId) {
    setSelectedVendorIds((current) =>
      current.includes(vendorId)
        ? current.filter((id) => id !== vendorId)
        : [...current, vendorId],
    );
    setDraw(null);
  }

  function toggleDietaryFilter(name) {
    setFilters((current) => {
      const next = { ...current, [name]: !current[name] };
      if (name === "vegetarian" && next.vegetarian) next.ovoLactoVegetarian = false;
      if (name === "ovoLactoVegetarian" && next.ovoLactoVegetarian) next.vegetarian = false;
      return next;
    });
    setDraw(null);
  }

  async function handleDraw() {
    setDrawing(true);
    setDrawError(null);
    setDraw(null);
    try {
      const result = await drawRandomMeal({
        mealDate,
        vendorIds: allVendors ? null : selectedVendorIds,
        facilityId: selectedFacilityId,
        includeTags,
        excludeTags,
      });
      setDraw(result);
    } catch (err) {
      setDraw(null);
      setDrawError(drawErrorMessage(err));
    } finally {
      setDrawing(false);
    }
  }

  function recRemainingLabel(rec) {
    if (rec.remaining_quantity == null) return quotaLabel(rec.item.daily_quota);
    return `剩餘 ${rec.remaining_quantity} 份`;
  }

  function DietaryBadges({ item }) {
    const tags = normalizeDietaryTags(item.dietary_tags);
    return tags.map((tag) => (
      <span className="badge badge-quota" key={tag}>
        {dietaryTagLabel(tag)}
      </span>
    ));
  }

  return (
    <div>
      <div className="page-header">
        <FacilityScopeLabel label="Ordering facility" />
        <p className="eyebrow">員工 / 推薦與隨機抽餐</p>
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
            }}
          />

          <div style={{ display: "grid", gap: 10 }}>
            <span className="field-label">飲食偏好</span>
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={filters.excludeBeef}
                onChange={() => toggleDietaryFilter("excludeBeef")}
              />
              <span>不含牛肉</span>
            </label>
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={filters.excludePork}
                onChange={() => toggleDietaryFilter("excludePork")}
              />
              <span>不含豬肉</span>
            </label>
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={filters.vegetarian}
                onChange={() => toggleDietaryFilter("vegetarian")}
              />
              <span>只看素食</span>
            </label>
            <label className="toggle-row">
              <input
                type="checkbox"
                checked={filters.ovoLactoVegetarian}
                onChange={() => toggleDietaryFilter("ovoLactoVegetarian")}
              />
              <span>只看蛋奶素</span>
            </label>
          </div>

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
                      role="button"
                      tabIndex={0}
                      aria-label={rec.item.name}
                      style={{ cursor: "pointer" }}
                      onClick={() => setDetail({ item: rec.item, remaining: rec.remaining_quantity })}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          setDetail({ item: rec.item, remaining: rec.remaining_quantity });
                        }
                      }}
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
                          <DietaryBadges item={rec.item} />
                        </div>
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
                <div
                  className="random-result-card"
                  role="button"
                  tabIndex={0}
                  aria-label={draw.item.name}
                  style={{ cursor: "pointer" }}
                  onClick={() => setDetail({ item: draw.item, remaining: draw.remaining_quantity })}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      setDetail({ item: draw.item, remaining: draw.remaining_quantity });
                    }
                  }}
                >
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
                    <DietaryBadges item={draw.item} />
                  </div>

                </div>
              )}
            </div>
          )}
        </div>
      </section>

      {detail && (
        <MealDetailModal
          item={detail.item}
          mealDate={mealDate}
          remaining={detail.remaining}
          onClose={() => setDetail(null)}
        />
      )}
    </div>
  );
}
