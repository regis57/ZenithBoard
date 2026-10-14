// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tests/test_flags.js   The two flags on the wall: the country read from the registration, the
// country the aircraft was built in, and the drawing itself — which has to fit its box, stay distinguishable
// from its neighbours, and never leave a black band invisible against a black wall.
const assert = require("assert"), fs = require("fs"), path = require("path");
const dir = path.join(__dirname, "..", "flightinfo", "static");
global.window = {};
require(path.join(dir, "flags.js"));
const Flags = global.window.Flags;

// ---- registration -> country
const REG = [["OE-LMP", "AT"], ["HB-JCN", "CH"], ["D-ABYA", "DE"], ["F-GKXL", "FR"], ["G-EZBA", "GB"],
             ["EI-DWA", "IE"], ["N1603", "US"], ["N9", "US"], ["9H-QAA", "MT"], ["4X-EDA", "IL"],
             ["CN-RGH", "MA"], ["C-GHPQ", "CA"], ["PH-BXA", "NL"], ["OO-SNA", "BE"], ["TC-JRA", "TR"],
             ["JA8089", "JP"], ["HL7700", "KR"], ["VT-ANA", "IN"], ["SE-ROA", "SE"], ["LX-VCA", "LU"],
             ["I-BIKA", "IT"], ["EC-MXA", "ES"], ["CS-TVA", "PT"], ["SP-LRA", "PL"], ["OK-TVA", "CZ"]];
for (const [reg, want] of REG) assert.strictEqual(Flags.country(reg), want, reg);
assert.strictEqual(Flags.country("CN-RGH"), "MA", "CN- is Morocco, not Canada: the longest prefix wins");
assert.strictEqual(Flags.country(""), null);
assert.strictEqual(Flags.country(null), null);
assert.strictEqual(Flags.country("ZZ-ZZZ"), null, "an unknown prefix must say so rather than guess");

// ---- maker -> where it is built (never the maker's mark, which is protected)
const MADE = [["AIRBUS A320-214", "EU"], ["BOEING 737-800", "US"], ["EMBRAER ERJ-190", "BR"],
              ["DE HAVILLAND CANADA DHC-8", "CA"], ["ATR 72-600", "EU"], ["DASSAULT FALCON 900", "FR"],
              ["PILATUS PC-12", "CH"], ["SAAB 340", "SE"], ["CESSNA 172", "US"]];
for (const [name, want] of MADE) assert.strictEqual(Flags.origin(name), want, name);
assert.strictEqual(Flags.origin("A320"), null, "a bare type code names no maker");
assert.strictEqual(Flags.origin(""), null);

// ---- the drawing
function render(code) {
  const px = new Map();
  const ok = Flags.draw(code, 10, 10, (x, y, v) => px.set(x + "," + y, v));
  return ok ? px : null;
}
assert.strictEqual(render("ZZ"), null, "an unknown country draws nothing, so the caller can fall back");

const codes = ["AT", "CH", "DE", "FR", "GB", "US", "IE", "BE", "IT", "NL", "ES", "PT", "SE", "NO", "DK", "FI",
               "PL", "CZ", "GR", "TR", "MA", "EU", "BR", "CA", "JP", "RU", "UA", "IL", "IN", "CN", "ZA", "MT"];
const shapes = new Map();
for (const code of codes) {
  const px = render(code);
  assert.ok(px, code + " must have a flag");
  // every flag dot inside its 11 x 7 box, plus at most a one-dot outline around it
  for (const key of px.keys()) {
    const [x, y] = key.split(",").map(Number);
    assert.ok(x >= 9 && x <= 10 + Flags.W, code + " draws outside its box at x " + x);
    assert.ok(y >= 9 && y <= 10 + Flags.H, code + " draws outside its box at y " + y);
  }
  // the flag itself is always complete: 11 x 7 dots, none of them unlit
  for (let y = 0; y < Flags.H; y++) for (let x = 0; x < Flags.W; x++) {
    const v = px.get((10 + x) + "," + (10 + y));
    assert.ok(v > 0, code + " leaves a hole at " + x + "," + y);
  }
  const key = codes.map(() => 0) && JSON.stringify([...Array(Flags.H).keys()].map(y =>
    [...Array(Flags.W).keys()].map(x => px.get((10 + x) + "," + (10 + y))).join(",")));
  assert.ok(!shapes.has(key), code + " is drawn exactly like " + shapes.get(key));
  shapes.set(key, code);
}

// ---- a black band at the edge gets a white outline, or it is a hole in the wall
function outlined(code) { return render(code).has("9,9"); }
for (const code of ["DE", "BE", "EE", "EG", "AE", "ZA"]) assert.ok(outlined(code), code + " has black at its edge and needs the white outline");
for (const code of ["FR", "AT", "CH", "IT", "SE", "US", "EU", "MA"]) assert.ok(!outlined(code), code + " has no black at its edge and must not be boxed in");
const white = [...render("DE").entries()].filter(([k]) => k === "9,9").map(([, v]) => v)[0];
assert.strictEqual(white, 0xffffff, "the outline is white, not the wall colour");

// ---- the flags fit the wall: the text column, the silhouette and the photo are all clear of them
const app = fs.readFileSync(path.join(dir, "app.js"), "utf8");
const n = (re) => Number(app.match(re)[1]);
const FLAG_X = n(/FLAG_X = (\d+)/), Y1 = n(/FLAG_Y1 = (\d+)/), Y2 = n(/FLAG_Y2 = (\d+)/);
const MAXX = n(/TEXT_MAX_X = (\d+)/), RX = n(/var RX = (\d+)/), COLS = n(/COLS_FLAGS = (\d+)/);
const PH = app.match(/PHOTO_BOX = \{ x: (\d+), y: (\d+)/).slice(1).map(Number);
assert.ok(FLAG_X - 1 >= MAXX, "the outline must start at or after the last text dot");
assert.ok(COLS * 6 - 1 <= MAXX, COLS + " characters do not fit before the flags");
assert.ok(FLAG_X + Flags.W <= RX - 1, "the flags must stay clear of the aircraft silhouette");
assert.ok(Y2 + Flags.H < PH[1], "the flags must stay above the photo");
assert.ok(Y1 + Flags.H <= Y2 - 1, "the two flags must not touch each other");

console.log("flags ok: " + REG.length + " registrations, " + MADE.length + " makers, " + codes.length +
            " flags all distinct and inside the grid, outlines only where black would be invisible");
