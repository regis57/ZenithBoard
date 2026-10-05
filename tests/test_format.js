// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tests/test_format.js
const assert = require("assert");
const Fmt = require("../flightinfo/static/format.js");
const F = require("../flightinfo/static/font5x7.js");
const plane = { hex: "3944ed", flight: "AFR1234", type: "A320", registration: "F-GKXA", alt_ft: 35000, gs_kt: 450,
  track: 270, vrate_fpm: 1200, distance_km: 12.3, bearing: 20, on_ground: false };

let L = Fmt.planeLines(plane, "metric", 1, 5, Fmt.radiusLabel(10, "metric"), 20);
assert.strictEqual(L.dist, "12KM"); assert.strictEqual(L.alt, "ALT  10670 M");
assert.strictEqual(L.spd, "SPD  833 KMH"); assert.strictEqual(L.vs, "V/S  ↑6.1 M/S");
assert.strictEqual(L.dir, "NNE"); assert.strictEqual(L.footer, "2/5" + " ".repeat(10) + "R 10 KM");

L = Fmt.planeLines(plane, "imperial", 0, 1, Fmt.radiusLabel(5, "imperial"), 20);
assert.strictEqual(L.dist, "7.6MI"); assert.strictEqual(L.alt, "ALT  35000 FT");
assert.strictEqual(L.spd, "SPD  450 KT"); assert.strictEqual(L.vs, "V/S  ↑1200 FPM");
assert.strictEqual(L.hdg, "HDG  270° W");

assert.ok(Math.abs(Fmt.radiusToKm(10, "imperial") - 16.09344) < 1e-6);
assert.strictEqual(Fmt.compass(359), "N"); assert.strictEqual(Fmt.compass(90), "E");

// every row must fit in 20 columns and use only glyphs that exist
for (const u of ["metric", "imperial"]) {
  const l = Fmt.planeLines({ ...plane, flight: "LONGCALLSIGN", vrate_fpm: -3000, alt_ft: 41000, gs_kt: 999 }, u, 9, 12, Fmt.radiusLabel(50, u), 20);
  for (const k of ["type", "alt", "spd", "hdg", "vs", "footer"]) {
    assert.ok(l[k].length <= 20, k + " too long: " + l[k]);
    for (const ch of l[k]) assert.ok(F.GLYPHS[ch], "missing glyph " + JSON.stringify(ch) + " in " + k);
  }
}
const g = Fmt.planeLines({ ...plane, on_ground: true, vrate_fpm: 0 }, "metric", 0, 1, "R 1 KM", 20);
assert.strictEqual(g.alt, "ALT  GROUND"); assert.strictEqual(g.vs, "V/S  = M/S");
console.log("format tests OK");
