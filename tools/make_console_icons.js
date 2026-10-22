// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tools/make_console_icons.js   (0.53.0) Writes the web console's app icons in flightinfo/static/: the
// ZenithBoard logo in the wall's dots (the generic airliner of shapes.js, nose up, above "ZB" in font5x7.js, twice its size), amber
// on black, the unlit dots faint, as on the wall. 192 and 512 px for the manifest, 180 px for iPhones and iPads, and a
// "maskable" 512 px with the logo inside the middle 70 %, which Android crops to a circle or a squircle.
"use strict";
const fs = require("fs"), path = require("path"), zlib = require("zlib");
const STATIC = path.join(__dirname, "..", "flightinfo", "static");
const Shapes = require(path.join(STATIC, "shapes.js"));
const Font = require(path.join(STATIC, "font5x7.js"));

const ON = [0xff, 0xb0, 0x00], OFF = [0x26, 0x1c, 0x05], BG = [0x03, 0x03, 0x03];

// the logo as lit cells on a grid of `n` x `n`: the airliner (32 x 32, nose up) above "ZB" in letters of two cells
// a dot (22 x 14), centred, as the Bluesky account's picture draws it
function cells(n) {
  const lit = new Uint8Array(n * n), S = 32, plane = Shapes.rasterize("narrow", S, S), Z = 2;
  const top = Math.floor((n - (S + 3 + 7 * Z)) / 2), left = Math.floor((n - S) / 2);
  for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) if (plane[x * S + (S - 1 - y)]) lit[(top + y) * n + left + x] = 1;
  const ty = top + S + 3, tx = Math.floor((n - 11 * Z) / 2);
  ["Z", "B"].forEach((ch, k) => Font.GLYPHS[ch].forEach((row, y) => [...row].forEach((c, x) => {
    if (c !== "#") return;
    for (let dy = 0; dy < Z; dy++) for (let dx = 0; dx < Z; dx++) lit[(ty + y * Z + dy) * n + tx + (k * 6 + x) * Z + dx] = 1;
  })));
  return lit;
}

function draw(size, n) {
  const img = Buffer.alloc(size * size * 3), lit = cells(n), cell = size / n, r = cell * 0.36;
  for (let i = 0; i < size * size; i++) BG.forEach((v, c) => { img[i * 3 + c] = v; });
  for (let gy = 0; gy < n; gy++) for (let gx = 0; gx < n; gx++) {
    const col = lit[gy * n + gx] ? ON : OFF, cx = (gx + 0.5) * cell, cy = (gy + 0.5) * cell;
    for (let y = Math.floor(cy - r - 1); y <= Math.ceil(cy + r + 1); y++) for (let x = Math.floor(cx - r - 1); x <= Math.ceil(cx + r + 1); x++) {
      if (x < 0 || y < 0 || x >= size || y >= size) continue;
      const d = Math.hypot(x + 0.5 - cx, y + 0.5 - cy), a = Math.max(0, Math.min(1, r + 0.5 - d));
      if (a > 0) { const o = (y * size + x) * 3; for (let c = 0; c < 3; c++) img[o + c] = Math.round(img[o + c] * (1 - a) + col[c] * a); }
    }
  }
  return png(size, size, img);
}

function png(W, H, rgb) {                      // as tools/social-render.js writes its pictures
  const raw = Buffer.alloc((W * 3 + 1) * H);
  for (let y = 0; y < H; y++) { raw[y * (W * 3 + 1)] = 0; rgb.copy(raw, y * (W * 3 + 1) + 1, y * W * 3, (y + 1) * W * 3); }
  const table = new Int32Array(256);
  for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; table[n] = c; }
  const crc = (buf) => { let c = -1; for (const b of buf) c = table[(c ^ b) & 255] ^ (c >>> 8); return (c ^ -1) >>> 0; };
  const chunk = (type, data) => {
    const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
    const td = Buffer.concat([Buffer.from(type, "ascii"), data]), c = Buffer.alloc(4); c.writeUInt32BE(crc(td));
    return Buffer.concat([len, td, c]);
  };
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(W, 0); ihdr.writeUInt32BE(H, 4); ihdr[8] = 8; ihdr[9] = 2;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk("IHDR", ihdr),
    chunk("IDAT", zlib.deflateSync(raw, { level: 9 })), chunk("IEND", Buffer.alloc(0))]);
}

const out = { "console-icon-192.png": [192, 56], "console-icon-512.png": [512, 56], "console-icon-180.png": [180, 56],
              "console-icon-maskable-512.png": [512, 72] };
for (const [name, [size, n]] of Object.entries(out)) fs.writeFileSync(path.join(STATIC, name), draw(size, n));
console.log("console icons: " + Object.keys(out).join(", "));
