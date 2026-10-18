#!/usr/bin/env node
// SPDX-License-Identifier: GPL-3.0-or-later
// The picture a social post carries: the dot-matrix wall as it is for one aircraft, and in the right-hand column
// the aircraft's track over the last minutes, drawn into the same grid of dots. No browser, no library: the text
// rows come from the wall's own code (app.js is read and its functions lifted, the way the tests do), the flags
// from flags.js, the names from format.js, and the PNG is written here with Node's zlib.
//
//   node tools/social-render.js IN.json OUT.png      the dot-matrix picture (with "map": true, the right-hand
//                                                    column is left dark: social_card.py lays a map there, 0.23.0)
//   node tools/social-render.js IN.json --lines      the split-flap board's rows and the colour, as JSON (the
//                                                    board itself is drawn by flightinfo/social_card.py, Pillow)
//
// IN.json: { "plane": <one entry of /api/planes>, "trace": [[lat, lon, alt_ft, t_seconds], ...] (oldest first),
//            "units": "metric"|"imperial", "theme": "amber", "clock": "09:50 GMT+2", "flags": true, "pitch": 10,
//            "map": false, "cols": 14 (--lines only) }
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
const TEXT_MAX_X = constant(/TEXT_MAX_X = (\d+)/), ROW_MAX_X = constant(/ROW_MAX_X = (\d+)/);
const wall = new Function("Font5x7", "GW", "GH", "ON",
  lift("put") + lift("text") + lift("textRow") + "return { put: put, text: text, textRow: textRow };")(Font5x7, GW, GH, ON);

// ---- the track panel: the right-hand column, where the photo would be on the tablet
// It starts at dot 88, two dots clear of the flags: they take dots 75 to 85, and an outlined flag (Germany, the United
// Kingdom) dots 74 to 86. Until 0.23.0 the panel started at 86 and its frame was drawn over the outline's last
// column, so a German flag lost its right-hand edge (seen in a post, 18 October 2026).
const PANEL = { x: 88, y: 0, w: 40, h: 68 };                       // 40 x 68 dots, the photo box grown to the top
// The map's place in the "dotmap" look (0.23.0): the same column, the whole height. Nothing on the left reaches it:
// the rows stop at dot 84, the flags at 86, the clock at 66.
const MAP_BOX = { x: 88, y: 0, w: 40, h: 80 };
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

// A colour of the theme at a given brightness, as a grid value (an RGB integer, not ON)
function shade(hex, k) {
  const r = (hex >> 16) & 255, gg = (hex >> 8) & 255, b = hex & 255;
  return (Math.round(r * k) << 16) | (Math.round(gg * k) << 8) | Math.round(b * k);
}

function drawTrack(g, trace, track, themeHex) {
  themeHex = themeHex == null ? THEMES.amber : themeHex;
  const P = PANEL, cx = P.x + Math.floor(P.w / 2), cy = P.y + Math.floor(P.h / 2) + 2;
  // frame
  for (let x = P.x; x < P.x + P.w; x++) { wall.put(g, x, P.y, DIM); wall.put(g, x, P.y + P.h - 1, DIM); }
  for (let y = P.y; y < P.y + P.h; y++) { wall.put(g, P.x, y, DIM); wall.put(g, P.x + P.w - 1, y, DIM); }
  // north
  wall.text(g, "N", cx - 2, P.y + 2, 1);
  if (!trace || trace.length < 2) {                                // two lines: "NO TRACK" is 47 dots, the panel 40
    wall.text(g, "NO", cx - 5, cy - 8, 1); wall.text(g, "TRACK", cx - 14, cy + 1, 1);
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
  // the track, older dimmer, in the picture's colour, inside the frame only
  const trail = k => shade(themeHex, 0.44 + k * 0.44);
  pts.forEach((p, i) => {
    const x = Math.round(cx + p[0] * dotsPerKm), y = Math.round(cy - p[1] * dotsPerKm);
    if (x <= P.x || x >= P.x + P.w - 1 || y <= P.y || y >= P.y + P.h - 1) return;
    wall.put(g, x, y, trail(i / pts.length));
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
  // the legend, as a key: a piece of the trail, then how long the trail is ("....... 10MIN"); the scale bar, then
  // what it measures ("|------| 10KM"). 0.18 wrote "10 MIN" and "10KM" one above the other, and a reader asked
  // what they meant (0.19.0).
  const minutes = Math.max(1, Math.round((last[3] - trace[0][3]) / 60));
  // one dot from the frame, one between the key and its words: "100KM" (29 dots) then ends a dot before the frame
  const ly1 = P.y + P.h - 17, ly2 = P.y + P.h - 9, lx = P.x + 1;
  for (let x = 0; x < BAR; x++) wall.put(g, lx + x, ly1 + 3, trail(x / BAR));
  wall.text(g, minutes + "MIN", lx + BAR + 1, ly1, 1);
  for (let x = 0; x < BAR; x++) wall.put(g, lx + x, ly2 + 3, ON);
  wall.put(g, lx, ly2 + 2, ON); wall.put(g, lx + BAR - 1, ly2 + 2, ON);
  wall.put(g, lx, ly2 + 4, ON); wall.put(g, lx + BAR - 1, ly2 + 4, ON);
  wall.text(g, scaleKm + "KM", lx + BAR + 1, ly2, 1);
}

// ---- the two top rows, "FLT  ETD11K" and "REG  A6-APD": the wall's own (format.js), the same on the tablet since 0.19.0
function rows(p, L, cols) { void L; return Fmt.topRows(p, cols || 14); }

// ---- the split-flap board's rows (social_card.py draws them): the dot-matrix rows, no flags, the time last
function flapLines(p, units, clock, cols) {
  const L = Fmt.planeLines(p, units, 0, 1, cols), R = rows(p, L);
  return [R.flight, R.reg, L.airline, L.type, L.alt, L.spd, L.from, L.to, clock].map(s => String(s || "").slice(0, cols));
}

// ---- the wall rows, as buildScreen lays them out, without silhouette, photo, or distance
function drawWall(g, p, units, clock, flags) {
  const cols = flags ? COLS_FLAGS : COLS, maxX = flags ? TEXT_MAX_X : ROW_MAX_X;
  const L = Fmt.planeLines(p, units, 0, 1, cols);
  // The tablet's big callsign takes two rows; the picture has the flight and the registration on one row each, at
  // the size of the others and labelled like ALT and SPD under them (0.19.0, from the owner's mock-up)
  const R = rows(p, L, cols);                    // twelve letters with the flags: the REG row has its flag beside it
  wall.text(g, R.flight, 0, 0, 1);
  wall.text(g, R.reg, 0, 8, 1);
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
// The theme colours, read from the wall's own style.css so the picture is the colour the tablet shows
const THEMES = (function () {
  const css = fs.readFileSync(path.join(STATIC, "style.css"), "utf8"), out = {};
  const amber = css.match(/body\s*\{[^}]*--dot:\s*#([0-9a-fA-F]{6})/);
  out.amber = parseInt(amber ? amber[1] : "ffb000", 16);
  const re = /body\[data-theme="([a-z]+)"\]\s*\{\s*--dot:\s*#([0-9a-fA-F]{6})/g;
  let m;
  while ((m = re.exec(css))) out[m[1]] = parseInt(m[2], 16);
  return out;
})();
function margin(pitch) { return Math.round(pitch * 1.5); }          // a margin, as the tablet has around the grid
function render(g, pitch, themeHex) {
  const M = margin(pitch);
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

// Node's own peak memory, said by Node: the service cannot measure it from outside, because Python starts it with
// vfork and the kernel then credits the child with the parent's peak (0.19.10: "Node 104 MB" was Python's 104 MB)
function maxRssKb() {
  try { return process.resourceUsage().maxRSS; } catch (e) { return 0; }
}

function main() {
  const [inFile, outFile] = process.argv.slice(2);
  if (!inFile || !outFile) { console.error("usage: social-render.js IN.json OUT.png | social-render.js IN.json --lines"); process.exit(2); }
  const spec = JSON.parse(fs.readFileSync(inFile, "utf8"));
  const theme = THEMES[spec.theme] != null ? THEMES[spec.theme] : THEMES.amber;
  if (outFile === "--lines") {
    console.log(JSON.stringify({ lines: flapLines(spec.plane || {}, spec.units || "metric", spec.clock || "", spec.cols || 14),
                                 color: "#" + ("000000" + theme.toString(16)).slice(-6), maxrss_kb: maxRssKb() }));
    return;
  }
  const g = new Uint32Array(GW * GH);
  drawWall(g, spec.plane || {}, spec.units || "metric", spec.clock || "", spec.flags !== false);
  if (!spec.map) drawTrack(g, spec.trace || [], (spec.plane || {}).track, theme);
  const pitch = spec.pitch || 10, M = margin(pitch);
  const { W, H, img } = render(g, pitch, theme);
  fs.writeFileSync(outFile, png(W, H, img));
  // with a map to come: where it goes, in pixels of this picture, and the colour to draw its track in
  const box = spec.map ? [M + MAP_BOX.x * pitch, M + MAP_BOX.y * pitch, MAP_BOX.w * pitch, MAP_BOX.h * pitch] : null;
  console.log(JSON.stringify({ width: W, height: H, bytes: fs.statSync(outFile).size, maxrss_kb: maxRssKb(),
                               map_box: box, color: "#" + ("000000" + theme.toString(16)).slice(-6) }));
}

if (require.main === module) main();
module.exports = { drawWall, drawTrack, render, png, PANEL, MAP_BOX, margin, pickScaleKm, BAR, HALF, GW, GH, THEMES, rows, flapLines };
