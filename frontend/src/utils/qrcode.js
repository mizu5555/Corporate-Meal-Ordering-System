// Minimal, dependency-free QR Code generator (model 2, byte mode, ECC level L,
// auto version up to 10). Vendored on purpose: the badge quick-pickup view must
// render a scannable QR offline / in demos, and we don't want to pull in an npm
// dependency for a single small feature. Adapted from the public-domain
// "qrcode-generator" algorithm (Kazuhiko Arase), trimmed to byte mode only.
//
// Public API: generateQrMatrix(text) -> boolean[][] (true = dark module).
// The page paints the matrix onto a <canvas>, so no DOM/lib coupling here.

const PAD0 = 0xec;
const PAD1 = 0x11;

// --- Galois field tables for Reed-Solomon ECC -------------------------------
const EXP = new Array(256);
const LOG = new Array(256);
(function initGaloisTables() {
  for (let i = 0; i < 8; i += 1) EXP[i] = 1 << i;
  for (let i = 8; i < 256; i += 1) {
    EXP[i] = EXP[i - 4] ^ EXP[i - 5] ^ EXP[i - 6] ^ EXP[i - 8];
  }
  for (let i = 0; i < 255; i += 1) LOG[EXP[i]] = i;
})();

function gfMul(x, y) {
  if (x === 0 || y === 0) return 0;
  return EXP[(LOG[x] + LOG[y]) % 255];
}

// RS generator polynomial of the given degree.
function rsPolynomial(degree) {
  let poly = [1];
  for (let i = 0; i < degree; i += 1) {
    const next = new Array(poly.length + 1).fill(0);
    for (let j = 0; j < poly.length; j += 1) {
      next[j] ^= poly[j];
      next[j + 1] ^= gfMul(poly[j], EXP[i]);
    }
    poly = next;
  }
  return poly;
}

function rsEncode(data, ecCount) {
  const gen = rsPolynomial(ecCount);
  const res = data.concat(new Array(ecCount).fill(0));
  for (let i = 0; i < data.length; i += 1) {
    const coef = res[i];
    if (coef !== 0) {
      for (let j = 0; j < gen.length; j += 1) {
        res[i + j] ^= gfMul(gen[j], coef);
      }
    }
  }
  return res.slice(data.length);
}

// --- Version capacity tables (byte mode, ECC level L) -----------------------
// [version] = { totalCodewords, ecPerBlock, group1Blocks, group1Data }
// Single error-correction group is enough for versions 1-9 at level L; version
// 10 uses two groups. We keep just what we need for short badge strings.
const VERSIONS = {
  1: { ec: 7, blocks: [[1, 19]] },
  2: { ec: 10, blocks: [[1, 34]] },
  3: { ec: 15, blocks: [[1, 55]] },
  4: { ec: 20, blocks: [[1, 80]] },
  5: { ec: 26, blocks: [[1, 108]] },
  6: { ec: 18, blocks: [[2, 68]] },
  7: { ec: 20, blocks: [[2, 78]] },
  8: { ec: 24, blocks: [[2, 97]] },
  9: { ec: 30, blocks: [[2, 116]] },
  10: { ec: 18, blocks: [[2, 68], [2, 69]] },
};

const ALIGN_POSITIONS = {
  1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30],
  6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50],
};

function dataCapacityBytes(version) {
  return VERSIONS[version].blocks.reduce((sum, [count, data]) => sum + count * data, 0);
}

function pickVersion(byteLen) {
  // 4 bits mode + 8 bits length (versions 1-9) or 16 bits (>=10) overhead.
  for (let v = 1; v <= 10; v += 1) {
    const lenBits = v < 10 ? 8 : 16;
    const overheadBytes = Math.ceil((4 + lenBits) / 8);
    if (byteLen + overheadBytes <= dataCapacityBytes(v)) return v;
  }
  throw new Error("QR payload too large for vendored generator (max ~150 bytes).");
}

function utf8Bytes(str) {
  return Array.from(new TextEncoder().encode(str));
}

// --- Bit buffer -------------------------------------------------------------
function buildDataCodewords(text, version) {
  const bytes = utf8Bytes(text);
  const bits = [];
  const push = (value, length) => {
    for (let i = length - 1; i >= 0; i -= 1) bits.push((value >> i) & 1);
  };

  push(0b0100, 4); // byte mode indicator
  push(bytes.length, version < 10 ? 8 : 16);
  for (const b of bytes) push(b, 8);

  const capacityBits = dataCapacityBytes(version) * 8;
  push(0, Math.min(4, capacityBits - bits.length)); // terminator
  while (bits.length % 8 !== 0) bits.push(0); // byte align

  const codewords = [];
  for (let i = 0; i < bits.length; i += 8) {
    let byte = 0;
    for (let j = 0; j < 8; j += 1) byte = (byte << 1) | bits[i + j];
    codewords.push(byte);
  }
  let pad = 0;
  while (codewords.length < dataCapacityBytes(version)) {
    codewords.push(pad === 0 ? PAD0 : PAD1);
    pad ^= 1;
  }
  return codewords;
}

// Interleave data + EC codewords across blocks per the QR spec.
function buildFinalCodewords(dataCodewords, version) {
  const { ec, blocks } = VERSIONS[version];
  const dataBlocks = [];
  const ecBlocks = [];
  let offset = 0;
  for (const [count, dataLen] of blocks) {
    for (let b = 0; b < count; b += 1) {
      const slice = dataCodewords.slice(offset, offset + dataLen);
      offset += dataLen;
      dataBlocks.push(slice);
      ecBlocks.push(rsEncode(slice, ec));
    }
  }
  const result = [];
  const maxData = Math.max(...dataBlocks.map((b) => b.length));
  for (let i = 0; i < maxData; i += 1) {
    for (const block of dataBlocks) if (i < block.length) result.push(block[i]);
  }
  for (let i = 0; i < ec; i += 1) {
    for (const block of ecBlocks) result.push(block[i]);
  }
  return result;
}

// --- Matrix construction ----------------------------------------------------
function createMatrix(version, codewords) {
  const size = version * 4 + 17;
  const modules = Array.from({ length: size }, () => new Array(size).fill(null));
  const reserved = Array.from({ length: size }, () => new Array(size).fill(false));

  const placeFinder = (row, col) => {
    for (let r = -1; r <= 7; r += 1) {
      for (let c = -1; c <= 7; c += 1) {
        const rr = row + r;
        const cc = col + c;
        if (rr < 0 || rr >= size || cc < 0 || cc >= size) continue;
        const isBorder = (r >= 0 && r <= 6 && (c === 0 || c === 6))
          || (c >= 0 && c <= 6 && (r === 0 || r === 6));
        const isCenter = r >= 2 && r <= 4 && c >= 2 && c <= 4;
        modules[rr][cc] = isBorder || isCenter;
        reserved[rr][cc] = true;
      }
    }
  };
  placeFinder(0, 0);
  placeFinder(0, size - 7);
  placeFinder(size - 7, 0);

  // Timing patterns
  for (let i = 8; i < size - 8; i += 1) {
    const dark = i % 2 === 0;
    if (modules[6][i] === null) { modules[6][i] = dark; reserved[6][i] = true; }
    if (modules[i][6] === null) { modules[i][6] = dark; reserved[i][6] = true; }
  }

  // Alignment patterns
  const positions = ALIGN_POSITIONS[version];
  for (const r of positions) {
    for (const c of positions) {
      if (reserved[r][c]) continue; // overlaps a finder
      for (let dr = -2; dr <= 2; dr += 1) {
        for (let dc = -2; dc <= 2; dc += 1) {
          const ring = Math.max(Math.abs(dr), Math.abs(dc));
          modules[r + dr][c + dc] = ring !== 1;
          reserved[r + dr][c + dc] = true;
        }
      }
    }
  }

  // Dark module + reserve format/version areas
  modules[size - 8][8] = true;
  reserved[size - 8][8] = true;
  const reserveFormat = () => {
    for (let i = 0; i <= 8; i += 1) {
      if (i !== 6) { reserved[8][i] = true; reserved[i][8] = true; }
    }
    for (let i = 0; i < 8; i += 1) {
      reserved[8][size - 1 - i] = true;
      reserved[size - 1 - i][8] = true;
    }
  };
  reserveFormat();

  // Place data bits in zigzag, skipping reserved modules.
  let bitIndex = 0;
  const totalBits = codewords.length * 8;
  const getBit = () => {
    if (bitIndex >= totalBits) return 0;
    const byte = codewords[bitIndex >> 3];
    const bit = (byte >> (7 - (bitIndex & 7))) & 1;
    bitIndex += 1;
    return bit;
  };
  let upward = true;
  for (let col = size - 1; col > 0; col -= 2) {
    if (col === 6) col -= 1; // skip vertical timing column
    for (let i = 0; i < size; i += 1) {
      const row = upward ? size - 1 - i : i;
      for (let c = 0; c < 2; c += 1) {
        const cc = col - c;
        if (reserved[row][cc]) continue;
        modules[row][cc] = getBit() === 1;
      }
    }
    upward = !upward;
  }

  return { modules, reserved, size };
}

// Mask pattern 0: (row + col) % 2 === 0
function applyMask0(modules, reserved, size) {
  for (let r = 0; r < size; r += 1) {
    for (let c = 0; c < size; c += 1) {
      if (reserved[r][c]) continue;
      if ((r + c) % 2 === 0) modules[r][c] = !modules[r][c];
    }
  }
}

// Format info for ECC level L (01) + mask pattern 0, with BCH + mask 0x5412.
function placeFormatInfo(modules, size) {
  const data = 0b01000; // 5 bits: level L (01) + mask 000
  let bch = data << 10;
  const g = 0b10100110111;
  for (let i = 4; i >= 0; i -= 1) {
    if ((bch >> (i + 10)) & 1) bch ^= g << i;
  }
  let format = ((data << 10) | bch) ^ 0b101010000010010;

  const bitOf = (n) => (format >> n) & 1;
  // Around top-left finder
  for (let i = 0; i <= 5; i += 1) modules[8][i] = bitOf(i) === 1;
  modules[8][7] = bitOf(6) === 1;
  modules[8][8] = bitOf(7) === 1;
  modules[7][8] = bitOf(8) === 1;
  for (let i = 9; i <= 14; i += 1) modules[14 - i][8] = bitOf(i) === 1;
  // Mirrored copy near other finders
  for (let i = 0; i <= 7; i += 1) modules[size - 1 - i][8] = bitOf(i) === 1;
  for (let i = 8; i <= 14; i += 1) modules[8][size - 15 + i] = bitOf(i) === 1;
}

export function generateQrMatrix(text) {
  if (text == null || text === "") throw new Error("QR text is empty.");
  const bytes = utf8Bytes(String(text));
  const version = pickVersion(bytes.length);
  const dataCodewords = buildDataCodewords(String(text), version);
  const finalCodewords = buildFinalCodewords(dataCodewords, version);
  const { modules, reserved, size } = createMatrix(version, finalCodewords);
  applyMask0(modules, reserved, size);
  placeFormatInfo(modules, size);
  return modules.map((row) => row.map((cell) => cell === true));
}

export default generateQrMatrix;
