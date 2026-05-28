import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import MealDetailModal from "../../components/employee/MealDetailModal";
import MenuItemCard from "../../components/employee/MenuItemCard";
import { useFacility } from "../../facility/FacilityContext";
import FacilityScopeLabel from "../../facility/FacilityScopeLabel";
import { useVendor } from "../../hooks/useVendor";
import { useVendorMenu } from "../../hooks/useVendorMenu";

const FILTERS = [
  { label: "全部菜單", value: undefined },
  { label: "供應中", value: true },
];

export default function VendorMenuPage() {
  const { vendorId } = useParams();
  const navigate = useNavigate();

  const [availableFilter, setAvailableFilter] = useState(undefined);
  const [selectedItem, setSelectedItem] = useState(null);
  const { selectedFacilityId } = useFacility();

  const { vendor, loading: vendorLoading } = useVendor(vendorId, { facilityId: selectedFacilityId });
  const { items, loading: menuLoading, error } = useVendorMenu(vendorId, {
    available: availableFilter,
    facilityId: selectedFacilityId,
  });

  const loading = vendorLoading || menuLoading;

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
        <div className="menu-grid">
          {items.map((item) => (
            <MenuItemCard
              key={item.id}
              item={item}
              onClick={() => setSelectedItem(item)}
            />
          ))}
        </div>
      )}

      {selectedItem && (
        <MealDetailModal
          item={selectedItem}
          onClose={() => setSelectedItem(null)}
        />
      )}
    </div>
  );
}
