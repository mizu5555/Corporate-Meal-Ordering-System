import { formatPrice, photoUrl, quotaLabel } from "../../utils/format";

export default function MenuItemCard({ item, onClick }) {
  const photo = photoUrl(item.photo_path);
  const soldOut = item.remaining_quantity === 0;
  const unavailable = !item.available || soldOut;
  const quota = quotaLabel(item.remaining_quantity);

  return (
    <button
      className={`menu-item-card${unavailable ? " unavailable" : ""}`}
      onClick={onClick}
      type="button"
      aria-label={item.name}
    >
      <div className="item-photo-wrap">
        {photo ? (
          <img className="item-photo" src={photo} alt={item.name} loading="lazy" />
        ) : (
          <div className="item-photo-placeholder" aria-hidden="true">🍱</div>
        )}
      </div>

      <div className="item-info">
        <p className="item-name">{item.name}</p>
        <p className="item-price">{formatPrice(item.price_cents)}</p>
        <div className="item-badges">
          {unavailable ? (
            <span className="badge badge-unavailable">
              {soldOut ? "今日售完" : "暫停供應"}
            </span>
          ) : (
            <span className="badge badge-available">供應中</span>
          )}
          {quota && !soldOut && (
            <span className="badge badge-quota">{quota}</span>
          )}
        </div>
      </div>
    </button>
  );
}
