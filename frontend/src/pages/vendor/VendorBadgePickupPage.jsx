import { useCallback, useEffect, useRef, useState } from "react";
import { getOrdersByBadge, confirmPickup } from "../../api/vendor";

const STATUS_LABELS = {
  pending: "待確認",
  confirmed: "已確認",
  preparing: "準備中",
  ready: "待取餐",
  delivered: "已取餐",
  cancelled: "已取消",
};

function formatItems(items) {
  return (items ?? []).map((item) => `${item.item_name} x${item.quantity}`).join("、");
}

// Vendor quick-pickup view: enter — or optionally scan — an employee badge
// number, look up that employee's ready orders for this shop, and confirm
// pickup one by one. Manual entry is the default/primary path; the camera QR
// scan is an opt-in extra built on the native BarcodeDetector API (Chromium),
// with graceful fallback to manual entry when it is unavailable.
export function VendorBadgePickupPage() {
  const [input, setInput] = useState("");
  const [badgeCode, setBadgeCode] = useState(null);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [working, setWorking] = useState(null);
  const [status, setStatus] = useState(null); // "empty" | "not_found" | null
  const [error, setError] = useState(null);

  // Scanning is opt-in; the page opens in manual-input mode.
  const [scanning, setScanning] = useState(false);
  const [scanMsg, setScanMsg] = useState(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const rafRef = useRef(null);
  const detectorRef = useRef(null);

  // Native, dependency-free QR engine. If absent we fall back to manual input.
  const scanSupported =
    typeof window !== "undefined" &&
    "BarcodeDetector" in window &&
    typeof navigator !== "undefined" &&
    navigator.mediaDevices &&
    typeof navigator.mediaDevices.getUserMedia === "function";

  const runLookup = useCallback(async (rawCode) => {
    const code = (rawCode ?? "").trim();
    if (!code) return;
    setLoading(true);
    setError(null);
    setStatus(null);
    setOrders([]);
    setBadgeCode(code);
    try {
      const result = await getOrdersByBadge(code);
      const list = Array.isArray(result) ? result : [];
      setOrders(list);
      if (list.length === 0) setStatus("empty");
    } catch (err) {
      if (err.status === 404 || err.code === "badge_not_found") {
        setStatus("not_found");
      } else {
        setError(err.message || "查詢失敗，請稍後再試。");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  async function handleLookup(event) {
    event.preventDefault();
    await runLookup(input);
  }

  const stopScan = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) videoRef.current.srcObject = null;
    detectorRef.current = null;
    setScanning(false);
  }, []);

  async function startScan() {
    setScanMsg(null);
    setError(null);
    if (!scanSupported) {
      setScanMsg("此瀏覽器不支援掃描，請手動輸入");
      return;
    }
    try {
      detectorRef.current = new window.BarcodeDetector({ formats: ["qr_code"] });
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      streamRef.current = stream;
      setScanning(true);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }
      const tick = async () => {
        if (!detectorRef.current || !videoRef.current) return;
        try {
          const codes = await detectorRef.current.detect(videoRef.current);
          if (codes && codes.length > 0 && codes[0].rawValue) {
            const value = codes[0].rawValue.trim();
            setInput(value);
            stopScan();
            await runLookup(value);
            return;
          }
        } catch {
          // transient decode errors: keep scanning
        }
        rafRef.current = requestAnimationFrame(tick);
      };
      rafRef.current = requestAnimationFrame(tick);
    } catch {
      // permission denied / no camera / detector failure -> graceful fallback
      stopScan();
      setScanMsg("此瀏覽器不支援掃描，請手動輸入");
    }
  }

  // Always release the camera when the component unmounts.
  useEffect(() => stopScan, [stopScan]);

  async function handleConfirm(orderId) {
    setWorking(orderId);
    setError(null);
    try {
      const updated = await confirmPickup(orderId);
      // Reflect delivered: update the row in place (server returns the order).
      setOrders((prev) =>
        prev.map((o) => (o.id === orderId ? { ...o, ...updated, status: "delivered" } : o)),
      );
    } catch (err) {
      setError(err.message || "確認領餐失敗。");
    } finally {
      setWorking(null);
    }
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Vendor Console</p>
          <h2>掃碼 / 編號取餐</h2>
        </div>
      </div>

      <form onSubmit={handleLookup} style={{ display: "flex", gap: "0.75rem", alignItems: "flex-end", flexWrap: "wrap" }}>
        <label className="field" style={{ flex: "1 1 220px" }}>
          <span>員工編號</span>
          <input
            autoFocus
            onChange={(e) => setInput(e.target.value)}
            placeholder="例如 EMP-0001"
            type="text"
            value={input}
          />
        </label>
        <button className="button-primary" disabled={loading || !input.trim()} type="submit">
          {loading ? "查詢中..." : "查詢"}
        </button>
        {scanning ? (
          <button className="button-secondary" onClick={stopScan} type="button">
            停止掃描
          </button>
        ) : (
          <button className="button-secondary" onClick={startScan} type="button">
            掃描 QR
          </button>
        )}
      </form>

      {scanMsg ? <p className="panel-copy">{scanMsg}</p> : null}

      {scanning ? (
        <div style={{ marginTop: "0.75rem" }}>
          <video
            ref={videoRef}
            muted
            playsInline
            style={{ width: "100%", maxWidth: 320, borderRadius: 8, background: "#000" }}
          />
          <p className="panel-copy">將員工工牌 QR 對準鏡頭，辨識後自動查詢。</p>
        </div>
      ) : null}

      {error ? <p className="form-error">{error}</p> : null}

      {status === "not_found" ? (
        <p className="panel-copy">查無此員工編號。</p>
      ) : status === "empty" ? (
        <p className="panel-copy">此員工今日在本店無待領訂單。</p>
      ) : orders.length > 0 ? (
        <ul className="data-list">
          {orders.map((order) => (
            <li className="data-row" key={order.id}>
              <div>
                <p className="data-title">
                  {order.masked_name ?? "（未提供）"} · {order.employee_badge_code ?? badgeCode}
                </p>
                <p className="data-subtitle">
                  取餐碼 {order.pickup_code} · {formatItems(order.items)} · {STATUS_LABELS[order.status] ?? order.status}
                </p>
              </div>
              <div className="data-actions">
                {order.status === "delivered" ? (
                  <span className="panel-copy">已領餐</span>
                ) : (
                  <button
                    className="button-primary"
                    disabled={working === order.id}
                    onClick={() => handleConfirm(order.id)}
                    type="button"
                  >
                    {working === order.id ? "處理中..." : "確認領餐"}
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

export default VendorBadgePickupPage;
