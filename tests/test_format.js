// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tests/test_format.js
const assert = require("assert");
const Fmt = require("../flightinfo/static/format.js");
const F = require("../flightinfo/static/font5x7.js");
const plane = { hex: "3944ed", flight: "AFR1234", type: "A320", registration: "F-GKXA", alt_ft: 35000, gs_kt: 450,
  track: 270, vrate_fpm: 1200, distance_km: 12.3, bearing: 20, on_ground: false };

let L = Fmt.planeLines({ ...plane, airline: "Air France" }, "metric", 1, 5, 14);
assert.strictEqual(L.callsign, "AFR1234"); assert.strictEqual(L.airline, "AIR FRANCE");
assert.strictEqual(L.alt, "ALT  10670 M"); assert.strictEqual(L.spd, "SPD  833 KMH");
assert.strictEqual(L.footer, "2/5 12KM NNE");
assert.strictEqual(Fmt.planeLines({ ...plane, bearing: 337 }, "metric", 9, 11, 14).footer, "10/11 12KM NNW", "the footer is not cut to the 14-character column");
assert.ok(!("hdg" in L) && !("vs" in L) && !("footerRight" in L), "heading, vertical speed and radius are no longer shown");

L = Fmt.planeLines(plane, "imperial", 0, 1, 14);
assert.strictEqual(L.airline, "");                                  // unknown airline: line left blank
assert.strictEqual(L.alt, "ALT  35000 FT"); assert.strictEqual(L.spd, "SPD  450 KT");
assert.strictEqual(L.footer, "1/1 7.6MI NNE");
assert.strictEqual(L.from, ""); assert.strictEqual(L.to, "");       // no route known -> two blank rows

assert.ok(Math.abs(Fmt.radiusToKm(10, "imperial") - 16.09344) < 1e-6);
assert.strictEqual(Fmt.compass(359), "N"); assert.strictEqual(Fmt.compass(90), "E");

// ---- route rows: the airport's name when it fits, otherwise its city; plain capitals only
const ap = (name, city) => ({ name, city });
const name = (n, c, w) => Fmt.placeName(ap(n, c), w || 14);
assert.strictEqual(name("Munich Airport", "Munich"), "MUNICH");                         // generic words dropped
assert.strictEqual(name("John F Kennedy International Airport", "New York"), "JOHN F KENNEDY");   // the name fits: use it
assert.strictEqual(name("John F Kennedy International Airport", "New York", 13), "NEW YORK");     // too long for 13: the city
assert.strictEqual(name("Charles de Gaulle International Airport", "Paris"), "PARIS");            // name too long: city
assert.strictEqual(name("Z\u00fcrich Airport", "Zurich"), "ZURICH");                                // accents folded
assert.strictEqual(name("Nice-C\u00f4te d'Azur Airport", "Nice"), "NICE");
assert.strictEqual(name("Reykjav\u00edk Keflav\u00edk International Airport", "Keflav\u00edk"), "KEFLAVIK");
assert.strictEqual(name("\u00d8rland Main Air Station", "Brekstad"), "BREKSTAD");                  // fold \u00d8 even though NFD does not
assert.strictEqual(name("Frankfurt am Main Airport", "Frankfurt am Main"), "FRANKFURT AM");        // cut at a word, not mid-word
assert.strictEqual(name("International Airport", "Metz"), "METZ");                                // nothing left after stripping: city
assert.strictEqual(name("", ""), ""); assert.strictEqual(Fmt.placeName({ iata: "XYZ" }, 14), "XYZ");
assert.strictEqual(Fmt.placeName(null, 14), "");
const R = Fmt.routeLines({ from: ap("Munich Airport", "Munich"), to: ap("Sofia Airport", "Sofia") }, 14);
assert.deepStrictEqual(R, { from: "MUNICH", to: "\u2192SOFIA" });
assert.deepStrictEqual(Fmt.routeLines({ from: ap("Munich Airport", "Munich"), to: null }, 14), { from: "MUNICH", to: "" });
assert.deepStrictEqual(Fmt.routeLines(null, 14), { from: "", to: "" });
L = Fmt.planeLines({ ...plane, route: { from: ap("Luxembourg-Findel International Airport", "Luxembourg"), to: ap("Charles de Gaulle International Airport", "Paris") } }, "metric", 0, 3, 14);
assert.strictEqual(L.from, "LUXEMBOURG"); assert.strictEqual(L.to, "\u2192PARIS");

// every text row must fit the 14-character text column and use only glyphs that exist, whatever the data looks like
const NASTY = [ap("\u00c5lesund Airport, Vigra \u2013 \u201cLong\u201d & Odd/Name #1 (Intl)", "\u00c5lesund"), ap("\u5317\u4eac\u9996\u90fd\u56fd\u9645\u673a\u573a", "\u5317\u4eac"),
               ap("A".repeat(80), "B".repeat(80)), ap("x", ""), { iata: "ZZZ" }];
for (const u of ["metric", "imperial"]) for (const from of NASTY) for (const to of NASTY) {
  const l = Fmt.planeLines({ ...plane, flight: "LONGCALLSIGN", airline: "A VERY LONG AIRLINE NAME", alt_ft: 41000, gs_kt: 999, route: { from, to } }, u, 99, 120, 14);
  assert.ok(l.callsign.length <= 7, "callsign too long");
  for (const k of ["airline", "type", "alt", "spd", "from", "to", "footer"]) {
    assert.ok(l[k].length <= (k === "footer" ? 21 : 14), k + " too long: " + l[k]);
    for (const ch of l[k]) assert.ok(F.GLYPHS[ch.toUpperCase()], "missing glyph " + JSON.stringify(ch) + " in " + k + ": " + l[k]);
  }
}
const g = Fmt.planeLines({ ...plane, on_ground: true }, "metric", 0, 1, 14);
assert.strictEqual(g.alt, "ALT  GROUND");
console.log("format tests OK");
