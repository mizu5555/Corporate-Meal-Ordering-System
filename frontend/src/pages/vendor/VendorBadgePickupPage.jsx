import { useCallback, useEffect, useRef, useState } from "react";
import jsQR from "jsqr";
import { getOrdersByBadge, confirmPickup } from "../../api/vendor";

const STATUS_LABELS = {
  pending: "待確認",
  confirmed: "已確認",
  preparing: "準備中",
  ready: "待取餐",
  delivered: "已取餐",
  cancelled: "已取消",
};

function isToday(mealDateStr) {
  if (!mealDateStr) return false;
  const today = new Date();
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  return mealDateStr.slice(0, 10) === todayStr;
}

function formatItems(items) {
  return (items ?? []).map((item) => `${item.item_name} x${item.quantity}`).join("、");
}

// Vendor quick-pickup view: enter — or optionally scan — an employee badge
// number, look up that employee's ready orders for this shop, and confirm
// pickup one by one. Manual entry is the default/primary path; the camera QR
// scan is an opt-in extra. It prefers the native BarcodeDetector API (Chromium)
// for speed and falls back to the bundled jsQR decoder on browsers that lack it
// (notably iOS Safari), so scanning works cross-browser. Only when there is no
// camera at all do we fall back to manual-input-only.
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
  const canvasRef = useRef(null); // offscreen canvas for the jsQR fallback path

  // Scanning needs a camera. If there's no camera at all we fall back to
  // manual-input-only. The decoding engine itself can be either the native
  // BarcodeDetector (preferred) or the bundled jsQR (fallback for iOS etc.).
  const cameraSupported =
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
    canvasRef.current = null;
    setScanning(false);
  }, []);

  // Decode the current video frame with the native BarcodeDetector when present,
  // otherwise with jsQR over the raw pixels. Returns the decoded string or null.
  const decodeFrame = useCallback(async () => {
    const video = videoRef.current;
    if (!video) return null;

    // Preferred fast path: native BarcodeDetector (Chromium / Android).
    if (detectorRef.current) {
      try {
        const codes = await detectorRef.current.detect(video);
        if (codes && codes.length > 0 && codes[0].rawValue) {
          return codes[0].rawValue.trim();
        }
      } catch {
        // transient decode errors: keep scanning
      }
      return null;
    }

    // Fallback path: draw the frame to an offscreen canvas and run jsQR
    // (works on iOS Safari and anywhere BarcodeDetector is missing).
    const width = video.videoWidth;
    const height = video.videoHeight;
    if (!width || !height) return null;
    let canvas = canvasRef.current;
    if (!canvas) {
      canvas = document.createElement("canvas");
      canvasRef.current = canvas;
    }
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0, width, height);
    let imageData;
    try {
      imageData = ctx.getImageData(0, 0, width, height);
    } catch {
      return null;
    }
    const result = jsQR(imageData.data, width, height, { inversionAttempts: "dontInvert" });
    return result && result.data ? result.data.trim() : null;
  }, []);

  async function startScan() {
    setScanMsg(null);
    setError(null);
    if (!cameraSupported) {
      setScanMsg("此瀏覽器不支援掃描，請手動輸入");
      return;
    }
    try {
      // Use the native detector if available; otherwise jsQR handles decoding.
      if (typeof window !== "undefined" && "BarcodeDetector" in window) {
        detectorRef.current = new window.BarcodeDetector({ formats: ["qr_code"] });
      } else {
        detectorRef.current = null;
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      streamRef.current = stream;
      // The <video> only mounts once scanning is true, so wiring srcObject +
      // play + the decode loop is deferred to the effect below (running it here
      // synchronously would hit a not-yet-mounted videoRef → black video).
      setScanning(true);
    } catch {
      // permission denied / no camera -> graceful fallback to manual input
      stopScan();
      setScanMsg("此瀏覽器不支援掃描，請手動輸入");
    }
  }

  // Attach the stream and start decoding only after the <video> is mounted
  // (scanning === true). Doing it here — not synchronously in startScan — is what
  // fixes the black-video bug where srcObject was set on a not-yet-rendered element.
  useEffect(() => {
    if (!scanning) return undefined;
    const video = videoRef.current;
    const stream = streamRef.current;
    if (!video || !stream) return undefined;

    let cancelled = false;
    video.srcObject = stream;
    video.play().catch(() => {});

    const tick = async () => {
      if (cancelled || !streamRef.current) return;
      const value = await decodeFrame();
      if (value) {
        setInput(value);
        stopScan();
        await runLookup(value);
        return;
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      cancelled = true;
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, [scanning, decodeFrame, runLookup, stopScan]);

  // Always release the camera when the component unmounts.
  useEffect(() => stopScan, [stopScan]);

  async function handleConfirm(orderId) {
    setWorking(orderId);
    setError(null);
    try {
      const updated = await confirmPickup(orderId);
      // Reflect delivered: update the row in place. The pickup-confirm response is
      // a general vendor response (minimal disclosure → no employee identity), so
      // keep the masked_name / badge we already got from the by-badge lookup
      // instead of letting the confirm response's nulls overwrite them.
      setOrders((prev) =>
        prev.map((o) =>
          o.id === orderId
            ? {
                ...o,
                ...updated,
                masked_name: o.masked_name ?? updated.masked_name,
                employee_badge_code: o.employee_badge_code ?? updated.employee_badge_code,
                status: "delivered",
              }
            : o,
        ),
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

      <form onSubmit={handleLookup} style={{ display: "grid", gap: "1rem", marginTop: 24 }}>
        <div className="search-bar" style={{ margin: 0 }}>
          <span className="search-icon" aria-hidden="true">🏷️</span>
          <input
            autoFocus
            className="search-input"
            onChange={(e) => setInput(e.target.value)}
            placeholder="輸入員工編號，例如 EMP-0001"
            type="text"
            value={input}
            style={{ fontSize: "1.05rem", minHeight: 52 }}
          />
        </div>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button
            className="primary-button"
            disabled={loading || !input.trim()}
            type="submit"
          >
            {loading ? "查詢中..." : "查詢"}
          </button>
          {scanning ? (
            <button className="ghost-button" onClick={stopScan} type="button">
              停止掃描
            </button>
          ) : (
            <button className="ghost-button" onClick={startScan} type="button">
              📷 掃描 QR
            </button>
          )}
        </div>
      </form>

      {scanMsg && <p className="panel-copy" style={{ marginTop: 8 }}>{scanMsg}</p>}

      {scanning && (
        <div style={{ marginTop: "1rem" }}>
          <video
            ref={videoRef}
            muted
            playsInline
            style={{ width: "100%", maxWidth: 320, borderRadius: 8, background: "#000" }}
          />
          <p className="panel-copy" style={{ marginTop: 8 }}>將員工工牌 QR 對準鏡頭，辨識後自動查詢。</p>
        </div>
      )}

      {/* 分隔線：有查詢結果或錯誤時才顯示 */}
      {(error || status || orders.length > 0) && (
        <hr style={{ border: "none", borderTop: "1px solid var(--line)", margin: "24px 0" }} />
      )}

      {error && <p className="error-state">{error}</p>}

      {status === "not_found" ? (
        <p className="panel-copy">查無此員工編號。</p>
      ) : status === "empty" ? (
        <p className="panel-copy">此員工今日在本店無待領訂單。</p>
      ) : orders.length > 0 ? (
        <div style={{ display: "grid", gap: 12 }}>
          <p style={{ margin: 0, fontWeight: 700, fontSize: 15 }}>
            {orders[0].masked_name ?? "（未提供）"}
            <span style={{ marginLeft: 8, color: "var(--muted)", fontSize: 13, fontWeight: 500 }}>
              {orders[0].employee_badge_code ?? badgeCode}
            </span>
          </p>
          {orders.map((order) => (
            <div
              key={order.id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 16,
                padding: "14px 18px",
                border: "1px solid var(--line)",
                borderRadius: "var(--radius-md)",
                background: order.status === "delivered"
                  ? "rgba(47,125,74,0.05)"
                  : "rgba(255,255,255,0.55)",
                flexWrap: "wrap",
              }}
            >
              <div style={{ display: "grid", gap: 4 }}>
                <p style={{ margin: 0, fontWeight: 600, fontSize: 14 }}>
                  取餐碼 <span style={{ color: "var(--brand)", letterSpacing: "0.05em" }}>{order.pickup_code}</span>
                </p>
                <p style={{ margin: 0, color: "var(--muted)", fontSize: 13 }}>
                  {formatItems(order.items)}
                </p>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: order.status === "delivered" ? "var(--success)" : "var(--muted)",
                }}>
                  {STATUS_LABELS[order.status] ?? order.status}
                </span>
                {order.status === "delivered" ? null
                  : !isToday(order.meal_date) ? (
                    <button
                      className="ghost-button"
                      disabled
                      type="button"
                      title={`此訂單為 ${order.meal_date} 的餐點，無法今日取餐`}
                      style={{ minHeight: 38, padding: "0 14px", fontSize: 13 }}
                    >
                      非今日餐點
                    </button>
                  ) : (
                    <button
                      className="primary-button"
                      disabled={working === order.id}
                      onClick={() => handleConfirm(order.id)}
                      type="button"
                      style={{ minHeight: 38, padding: "0 18px", fontSize: 13 }}
                    >
                      {working === order.id ? "處理中..." : "確認領餐"}
                    </button>
                  )}
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

export default VendorBadgePickupPage;
