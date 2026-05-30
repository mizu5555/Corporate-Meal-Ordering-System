import { useEffect, useState } from "react";
import { getMyBadge } from "../../api/employee";
import { QrCode } from "../../components/QrCode";

// Employee quick-pickup view: shows the employee's own badge number large plus a
// scannable QR encoding that number, so a vendor can scan it (or read it aloud)
// at the counter. The 404 `badge_not_assigned` case shows a friendly empty state.
export function BadgePage() {
  const [badge, setBadge] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notAssigned, setNotAssigned] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    getMyBadge()
      .then((data) => {
        if (active) setBadge(data);
      })
      .catch((err) => {
        if (!active) return;
        if (err.status === 404 || err.code === "badge_not_assigned") {
          setNotAssigned(true);
        } else {
          setError(err.message || "無法載入員工編號");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) return <p className="panel-copy">載入員工編號中...</p>;

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Quick Pickup</p>
          <h2>我的取餐編號</h2>
        </div>
      </div>

      {notAssigned ? (
        <p className="panel-copy">尚未配發員工編號，請洽福委會。</p>
      ) : error ? (
        <p className="form-error">{error}</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}>
          <QrCode value={badge.badge_code} />
          <div style={{ textAlign: "center" }}>
            <p className="stat-value" style={{ letterSpacing: "0.05em" }}>{badge.badge_code}</p>
            <p className="panel-copy">{badge.display_name}</p>
          </div>
          <p className="panel-copy">取餐時請出示此 QR code 或告知上方編號。</p>
        </div>
      )}
    </section>
  );
}

export default BadgePage;
