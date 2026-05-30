import { useEffect, useRef } from "react";
import { generateQrMatrix } from "../utils/qrcode";

// Paints a QR matrix for `value` onto a canvas using the vendored generator.
// `size` is the rendered pixel size; a quiet-zone border is added per spec so
// scanners reliably detect the code.
export function QrCode({ value, size = 220 }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !value) return;
    let matrix;
    try {
      matrix = generateQrMatrix(value);
    } catch {
      // Leave canvas blank on failure; the page still shows the badge number.
      return;
    }
    const quiet = 4;
    const modules = matrix.length;
    const total = modules + quiet * 2;
    const scale = Math.max(1, Math.floor(size / total));
    const pixel = scale * total;
    canvas.width = pixel;
    canvas.height = pixel;

    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, pixel, pixel);
    ctx.fillStyle = "#0f172a";
    for (let r = 0; r < modules; r += 1) {
      for (let c = 0; c < modules; c += 1) {
        if (matrix[r][c]) {
          ctx.fillRect((c + quiet) * scale, (r + quiet) * scale, scale, scale);
        }
      }
    }
  }, [value, size]);

  return <canvas aria-label={`QR code for ${value}`} ref={canvasRef} role="img" />;
}

export default QrCode;
