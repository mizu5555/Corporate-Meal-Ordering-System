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
