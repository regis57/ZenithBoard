#!/usr/bin/env node
// SPDX-License-Identifier: GPL-3.0-or-later
// The picture a social post carries: the dot-matrix wall as it is for one aircraft, and in the right-hand column
// the aircraft's track over the last minutes, drawn into the same grid of dots. No browser, no library: the text
// rows come from the wall's own code (app.js is read and its functions lifted, the way the tests do), the flags
// from flags.js, the names from format.js, and the PNG is written here with Node's zlib.
//
//   node tools/social-render.js IN.json OUT.png
//
// IN.json: { "plane": <one entry of /api/planes>, "trace": [[lat, lon, alt_ft, t_seconds], ...] (oldest first),
//            "units": "metric"|"imperial", "theme": "amber", "clock": "09:50", "flags": true, "pitch": 10 }
//
// What is deliberately NOT in the picture: the distance and the direction from the receiver (the last row shows
// the time instead), the receiver's position (the track is centred on the aircraft, north up, with no map), and
// the Planespotters photo (their terms forbid re-hosting it).
"use strict";
const fs = require("fs"), path = require("path"), zlib = require("zlib");

const STATIC = path.join(__dirname, "..", "flightinfo", "static");
global.window = {};
require(path.join(STATIC, "font5x7.js"));
require(path.join(STATIC, "flags.js"));
const Font5x7 = global.window.Font5x7 || require(path.join(STATIC, "font5x7.js"));
const Flags = global.window.Flags;
const Fmt = require(path.join(STATIC, "format.js"));
const app = fs.readFileSync(path.join(STATIC, "app.js"), "utf8");

// ---- lifted from app.js: the same functions the wall runs, not a copy of them
function lift(name) {
  const at = app.indexOf("function " + name + "(");
  if (at < 0) throw new Error(name + " not found in app.js");
  let depth = 0;
  for (let j = app.indexOf("{", at); j < app.length; j++) {
    if (app[j] === "{") depth++;
    else if (app[j] === "}" && --depth === 0) return app.slice(at, j + 1);
  }
  throw new Error("unbalanced " + name);
}
function constant(re) { const m = app.match(re); if (!m) throw new Error("constant missing: " + re); return Number(m[1]); }
const GW = constant(/var GW = (\d+)/), GH = constant(/GW = \d+, GH = (\d+)/), ON = constant(/var ON = (\d+)/);
const COLS = constant(/var COLS = (\d+)/), COLS_FLAGS = constant(/var COLS_FLAGS = (\d+)/);
const FLAG_X = constant(/var FLAG_X = (\d+)/), FLAG_Y1 = constant(/FLAG_Y1 = (\d+)/), FLAG_Y2 = constant(/FLAG_Y2 = (\d+)/);
const TEXT_MAX_X = constant(/TEXT_MAX_X = (\d+)/);
const wall = new Function("Font5x7", "GW", "GH", "ON",
  lift("put") + lift("text") + lift("textRow") + "return { put: put, text: text, textRow: textRow };")(Font5x7, GW, GH, ON);

// ---- the track panel: the right-hand column, where the photo would be on the tablet
const PANEL = { x: 86, y: 0, w: 42, h: 68 };                       // 42 x 68 dots, the photo box grown to the top
const DIM = 0x404040, FAINT = 0x2a2a2a;

function haversineKm(a, b) {
  const R = 6371.0088, toR = Math.PI / 180;
  const dLat = (b[0] - a[0]) * toR, dLon = (b[1] - a[1]) * toR;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a[0] * toR) * Math.cos(b[0] * toR) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

// A scale that keeps the whole track inside the panel: 1 to 500 km per bar, the smallest that fits.
// The scale bar is BAR dots long and stands for one round distance; the track must fit HALF dots either side of the
// aircraft (the panel is 42 dots wide). 0.18.2 used a 14-dot bar and let the track run twice past the edge, and a
// "10KM" label pushed the bar out of the frame; an A380 covers 165 km in ten minutes, so "100KM" has to fit too.
const BAR = 8, HALF = 18;
function pickScaleKm(extentKm) {
  for (const s of [1, 2, 5, 10, 20, 50, 100, 200]) if (extentKm * BAR / s <= HALF) return s;
  return 500;
}

function drawTrack(g, trace, track) {
  const P = PANEL, cx = P.x + Math.floor(P.w / 2), cy = P.y + Math.floor(P.h / 2) + 2;
  // frame
  for (let x = P.x; x < P.x + P.w; x++) { wall.put(g, x, P.y, DIM); wall.put(g, x, P.y + P.h - 1, DIM); }
  for (let y = P.y; y < P.y + P.h; y++) { wall.put(g, P.x, y, DIM); wall.put(g, P.x + P.w - 1, y, DIM); }
  // north
  wall.text(g, "N", cx - 2, P.y + 2, 1);
  if (!trace || trace.length < 2) {
    wall.text(g, "NO TRACK", P.x + 3, cy - 3, 1);
    return;
  }
  const last = trace[trace.length - 1];
  // local flat projection around the aircraft, km east / km north
  const toR = Math.PI / 180, kmPerLat = 111.32, kmPerLon = 111.32 * Math.cos(last[0] * toR);
  const pts = trace.map(p => [(p[1] - last[1]) * kmPerLon, (p[0] - last[0]) * kmPerLat]);
  let extent = 0;
  for (const p of pts) extent = Math.max(extent, Math.abs(p[0]), Math.abs(p[1]));
  const scaleKm = pickScaleKm(extent);
  const dotsPerKm = BAR / scaleKm;
  // graticule every two scale bars, faint, clipped to the panel
  for (let k = -4; k <= 4; k++) {
    const gx = Math.round(cx + k * 2 * BAR), gy = Math.round(cy + k * 2 * BAR);
    for (let y = P.y + 2; y < P.y + P.h - 2; y += 3) if (gx > P.x && gx < P.x + P.w - 1) wall.put(g, gx, y, FAINT);
    for (let x = P.x + 2; x < P.x + P.w - 2; x += 3) if (gy > P.y && gy < P.y + P.h - 1) wall.put(g, x, gy, FAINT);
  }
  // the track, older dimmer, inside the frame only
  pts.forEach((p, i) => {
    const x = Math.round(cx + p[0] * dotsPerKm), y = Math.round(cy - p[1] * dotsPerKm);
    if (x <= P.x || x >= P.x + P.w - 1 || y <= P.y || y >= P.y + P.h - 1) return;
    const k = i / pts.length, lvl = Math.round(0x70 + k * 0x70);
    wall.put(g, x, y, (lvl << 16) | (Math.round(lvl * 0.68) << 8));
  });
  // the aircraft: a small plan-view arrow along its track
  const hd = ((track == null ? 0 : track) - 90) * toR;             // track 0 = north = up
  const fwd = k => [cx + Math.cos(hd) * k, cy + Math.sin(hd) * k];
  const side = (k, s) => [cx + Math.cos(hd) * k - Math.sin(hd) * s, cy + Math.sin(hd) * k + Math.cos(hd) * s];
  const dot = p => wall.put(g, Math.round(p[0]), Math.round(p[1]), ON);
  for (let k = -4; k <= 5; k++) dot(fwd(k));
  for (let w = -4; w <= 4; w++) dot(side(0, w));
  for (let w = -2; w <= 2; w++) dot(side(-4, w));
  dot(fwd(6));
  // legend
  const minutes = Math.max(1, Math.round((last[3] - trace[0][3]) / 60));
  wall.text(g, minutes + " MIN", P.x + 3, P.y + P.h - 17, 1);
  wall.text(g, scaleKm + "KM", P.x + 3, P.y + P.h - 9, 1);
  const bx = P.x + P.w - 2 - BAR;                                   // the bar against the right edge, inside the frame
  for (let x = bx; x < bx + BAR; x++) wall.put(g, x, P.y + P.h - 6, ON);
  wall.put(g, bx, P.y + P.h - 7, ON); wall.put(g, bx + BAR - 1, P.y + P.h - 7, ON);
}

// ---- the wall rows, as buildScreen lays them out, without silhouette, photo, or distance
function drawWall(g, p, units, clock, flags) {
  const cols = flags ? COLS_FLAGS : COLS, maxX = flags ? TEXT_MAX_X : 84;
  const L = Fmt.planeLines(p, units, 0, 1, cols);
  // The tablet's big callsign takes two rows; the picture has it at the size of the others and the registration
  // under it, so a reader sees which airframe it was (0.18.3)
  wall.text(g, L.callsign, 0, 0, 1);
  wall.text(g, String(p.registration || "").toUpperCase().slice(0, flags ? 12 : 14), 0, 8, 1);
  wall.textRow(g, L.airline, 16, 0, maxX);
  wall.textRow(g, L.type, 25, 0, maxX);
  wall.text(g, L.alt, 0, 34, 1); wall.text(g, L.spd, 0, 43, 1); wall.text(g, L.from, 0, 52, 1); wall.text(g, L.to, 0, 61, 1);
  wall.text(g, clock, 0, 72, 1);
  if (flags) {
    const reg = Flags.country(p.registration), made = Flags.origin(p.type_name);
    const at = (code, y) => { if (code) Flags.draw(code, FLAG_X, y, (x, yy, v) => wall.put(g, x, yy, v)); };
    at(reg, FLAG_Y1); at(made, FLAG_Y2);
  }
}

// ---- dots to pixels: the look of the wall, a lit dot with a soft halo, an unlit dot faint
const THEMES = { amber: 0xffb000, green: 0x33ff55, red: 0xff3b30, white: 0xf2f2f2, turquoise: 0x00d6d7, blue: 0x0404e2 };
function render(g, pitch, themeHex) {
  const M = Math.round(pitch * 1.5);                                // a margin, as the tablet has around the grid
  const W = GW * pitch + 2 * M, H = GH * pitch + 2 * M, img = Buffer.alloc(W * H * 3, 0);
  const tr = (themeHex >> 16) & 255, tg = (themeHex >> 8) & 255, tb = themeHex & 255;
  const r = pitch * 0.42, halo = pitch * 0.75;
  function blend(x, y, cr, cg, cb, a) {
    if (x < 0 || y < 0 || x >= W || y >= H) return;
    const i = (y * W + x) * 3;
    img[i] = Math.min(255, img[i] + cr * a); img[i + 1] = Math.min(255, img[i + 1] + cg * a); img[i + 2] = Math.min(255, img[i + 2] + cb * a);
  }
  for (let gy = 0; gy < GH; gy++) for (let gx = 0; gx < GW; gx++) {
    const v = g[gy * GW + gx], cx = M + (gx + 0.5) * pitch, cy = M + (gy + 0.5) * pitch;
    let cr, cg, cb, alpha;
    if (!v) { cr = tr; cg = tg; cb = tb; alpha = 0.09; }
    else if (v === ON) { cr = tr; cg = tg; cb = tb; alpha = 1; }
    else { cr = (v >> 16) & 255; cg = (v >> 8) & 255; cb = v & 255; alpha = 1; }
    const reach = v ? halo : r;
    for (let y = Math.floor(cy - reach); y <= Math.ceil(cy + reach); y++) for (let x = Math.floor(cx - reach); x <= Math.ceil(cx + reach); x++) {
      const d = Math.hypot(x + 0.5 - cx, y + 0.5 - cy);
      if (d <= r) blend(x, y, cr, cg, cb, alpha);
      else if (v && d <= halo) blend(x, y, cr, cg, cb, 0.22 * (1 - (d - r) / (halo - r)));
    }
  }
  return { W, H, img };
}

function png(W, H, rgb) {
  const raw = Buffer.alloc((W * 3 + 1) * H);
  for (let y = 0; y < H; y++) { raw[y * (W * 3 + 1)] = 0; rgb.copy(raw, y * (W * 3 + 1) + 1, y * W * 3, (y + 1) * W * 3); }
  const crcTable = new Int32Array(256);
  for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; crcTable[n] = c; }
  const crc = buf => { let c = -1; for (const b of buf) c = crcTable[(c ^ b) & 255] ^ (c >>> 8); return (c ^ -1) >>> 0; };
  const chunk = (type, data) => {
    const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
    const td = Buffer.concat([Buffer.from(type, "ascii"), data]);
    const c = Buffer.alloc(4); c.writeUInt32BE(crc(td));
    return Buffer.concat([len, td, c]);
  };
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(W, 0); ihdr.writeUInt32BE(H, 4); ihdr[8] = 8; ihdr[9] = 2; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk("IHDR", ihdr),
    chunk("IDAT", zlib.deflateSync(raw, { level: 9 })), chunk("IEND", Buffer.alloc(0))]);
}

function main() {
  const [inFile, outFile] = process.argv.slice(2);
  if (!inFile || !outFile) { console.error("usage: social-render.js IN.json OUT.png"); process.exit(2); }
  const spec = JSON.parse(fs.readFileSync(inFile, "utf8"));
  const g = new Uint32Array(GW * GH);
  drawWall(g, spec.plane || {}, spec.units || "metric", spec.clock || "", spec.flags !== false);
  drawTrack(g, spec.trace || [], (spec.plane || {}).track);
  const pitch = spec.pitch || 10;
  const { W, H, img } = render(g, pitch, THEMES[spec.theme] || THEMES.amber);
  fs.writeFileSync(outFile, png(W, H, img));
  console.log(JSON.stringify({ width: W, height: H, bytes: fs.statSync(outFile).size }));
}

if (require.main === module) main();
module.exports = { drawWall, drawTrack, render, png, PANEL, pickScaleKm, BAR, HALF, GW, GH };
