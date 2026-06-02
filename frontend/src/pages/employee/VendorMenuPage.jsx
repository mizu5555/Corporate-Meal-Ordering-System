import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import MealDetailModal from "../../components/employee/MealDetailModal";
import MenuItemCard from "../../components/employee/MenuItemCard";
import { useFacility } from "../../facility/FacilityContext";
import FacilityScopeLabel from "../../facility/FacilityScopeLabel";
import { useVendor } from "../../hooks/useVendor";
import { useVendorMenu } from "../../hooks/useVendorMenu";
import { todayIso, toLocalIso } from "../../utils/date";

const FILTERS = [
  { label: "全部菜單", value: undefined },
  { label: "供應中", value: true },
];

function addDaysIso(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return toLocalIso(date);
}

export default function VendorMenuPage() {
  const { vendorId } = useParams();
  const navigate = useNavigate();

  const minMealDate = todayIso();
  const maxMealDate = addDaysIso(6);
  const [mealDate, setMealDate] = useState(minMealDate);
  const [availableFilter, setAvailableFilter] = useState(undefined);
  const [selectedItem, setSelectedItem] = useState(null);
  const { selectedFacilityId } = useFacility();

  const { vendor, loading: vendorLoading } = useVendor(vendorId, { facilityId: selectedFacilityId });
  const { items, loading: menuLoading, error } = useVendorMenu(vendorId, {
    available: availableFilter,
    facilityId: selectedFacilityId,
    mealDate,
  });

  const loading = vendorLoading || menuLoading;
  const isToday = mealDate === minMealDate;
  const recommendationTitle = isToday ? "今日推薦" : "當日推薦";
  const recommendedItems = items.filter(
    (item) => item.is_recommended && item.available && item.remaining_quantity !== 0,
  );
  const regularItems = recommendedItems.length > 0
    ? items.filter((item) => !recommendedItems.some((recommended) => recommended.id === item.id))
    : items;

  return (
    <div>
      <div className="menu-page-header">
        <button
          className="back-button"
          type="button"
          onClick={() => navigate("/employee/menu")}
        >
          ← 返回
        </button>
        <div className="menu-page-title">
          <FacilityScopeLabel label="Menu facility" />
          <p className="eyebrow">Vendor Menu</p>
          <h2>{vendor?.name ?? "載入中..."}</h2>
        </div>
      </div>

      {vendor?.address && (
        <p className="panel-copy" style={{ marginBottom: 20 }}>
          📍 {vendor.address}
          {vendor.business_hours && <span> &nbsp;·&nbsp; 🕐 {vendor.business_hours}</span>}
        </p>
      )}

      <div className="menu-toolbar">
        <div className="menu-date-control">
          <label className="field-label" htmlFor="vendor-menu-meal-date">
            Meal date
          </label>
          <input
            className="date-input"
            id="vendor-menu-meal-date"
            max={maxMealDate}
            min={minMealDate}
            type="date"
            value={mealDate}
            onChange={(event) => {
              setMealDate(event.target.value);
              setSelectedItem(null);
            }}
          />
        </div>
      </div>

      <div className="filter-bar">
        {FILTERS.map((f) => (
          <button
            key={String(f.value)}
            type="button"
            className={`filter-pill${availableFilter === f.value ? " filter-pill-active" : ""}`}
            onClick={() => setAvailableFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading && <p className="loading-state">載入菜單中...</p>}

      {error && (
        <p className="error-state">無法載入菜單，請稍後再試。</p>
      )}

      {!loading && !error && items.length === 0 && (
        <p className="empty-state">
          {availableFilter ? "目前沒有供應中的餐點。" : "此廠商尚未上架菜單。"}
        </p>
      )}

      {!loading && !error && items.length > 0 && (
        <>
          {recommendedItems.length > 0 && (
            <section className="today-recommendations">
              <div className="section-heading">
                <p className="eyebrow">{isToday ? "Today" : "Meal Date"}</p>
                <h3>{recommendationTitle}</h3>
              </div>
              <div className="menu-grid">
                {recommendedItems.map((item) => (
                  <MenuItemCard
                    key={item.id}
                    item={item}
                    onClick={() => setSelectedItem(item)}
                  />
                ))}
              </div>
            </section>
          )}

          {regularItems.length > 0 && (
            <section className={recommendedItems.length > 0 ? "regular-menu-section" : undefined}>
              {recommendedItems.length > 0 && (
                <div className="section-heading">
                  <h3>全部餐點</h3>
                </div>
              )}
              <div className="menu-grid">
                {regularItems.map((item) => (
                  <MenuItemCard
                    key={item.id}
                    item={item}
                    onClick={() => setSelectedItem(item)}
                  />
                ))}
              </div>
            </section>
          )}
        </>
      )}

      {selectedItem && (
        <MealDetailModal
          item={selectedItem}
          mealDate={mealDate}
          onClose={() => setSelectedItem(null)}
        />
      )}
    </div>
  );
}
