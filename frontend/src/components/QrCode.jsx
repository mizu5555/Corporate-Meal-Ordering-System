import { useEffect, useRef } from "react";
import QRCode from "qrcode";

// Renders a standards-compliant, scannable QR for `value` onto a canvas using
// the `qrcode` npm library (bundled by Vite, so it works offline). `size` is the
// rendered pixel width; a 2-module quiet zone and ECC level M keep it reliably
// readable by phone cameras and normal scanners.
export function QrCode({ value, size = 220 }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    if (!value) {
      // Nothing to encode yet: clear any previous render, render nothing.
      const ctx = canvas.getContext("2d");
      if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
      return;
    }
    QRCode.toCanvas(
      canvas,
      String(value),
      { width: size, margin: 2, errorCorrectionLevel: "M" },
      (err) => {
        // Leave canvas blank on failure; the page still shows the badge number.
        if (err) {
          // eslint-disable-next-line no-console
          console.error("QR render failed", err);
        }
      },
    );
  }, [value, size]);

  return <canvas aria-label={`QR code for ${value}`} ref={canvasRef} role="img" />;
}

export default QrCode;
