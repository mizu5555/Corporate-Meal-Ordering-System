export default function VendorCard({ vendor, onClick }) {
  return (
    <button className="vendor-card" onClick={onClick} type="button">
      <div>
        <p className="eyebrow">Vendor</p>
        <h3 className="vendor-card-name">{vendor.name}</h3>
      </div>

      <div className="vendor-meta">
        {vendor.address && (
          <div className="vendor-meta-row">
            <span>📍</span>
            <span>{vendor.address}</span>
          </div>
        )}
        {vendor.business_hours && (
          <div className="vendor-meta-row">
            <span>🕐</span>
            <span>{vendor.business_hours}</span>
          </div>
        )}
        {vendor.contact_phone && (
          <div className="vendor-meta-row">
            <span>📞</span>
            <span>{vendor.contact_phone}</span>
          </div>
        )}
        {vendor.served_facilities?.length > 0 && (
          <div className="vendor-meta-row">
            <span>🏢</span>
            <span>{vendor.served_facilities.map((f) => f.name).join("、")}</span>
          </div>
        )}
      </div>

      <span className="vendor-cta">瀏覽菜單 →</span>
    </button>
  );
}
