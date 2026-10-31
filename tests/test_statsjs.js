// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tests/test_statsjs.js   The axis of the statistics charts takes the real ticks() out of stats.js.
// 0.16.0 used a fixed step of 10 000 above 20 000 messages, so an hour with three million drew about four
// hundred labels on top of each other down the left edge of the chart. Whatever the size, the axis must carry a
// handful of lines, every one a round number, starting at 0 and reaching close to the top.
const assert = require("assert"), fs = require("fs"), path = require("path");
const src = fs.readFileSync(path.join(__dirname, "..", "flightinfo", "static", "stats.js"), "utf8");
const at = src.indexOf("function ticks(");
assert.ok(at > 0, "ticks() not found in stats.js");
let depth = 0, end = -1;
for (let j = src.indexOf("{", at); j < src.length; j++) {
  if (src[j] === "{") depth++;
  else if (src[j] === "}" && --depth === 0) { end = j + 1; break; }
}
const ticks = new Function(src.slice(at, end) + "return ticks;")();

for (const max of [1.08, 5, 12, 90, 450, 2500, 9000, 21000, 43000, 330000, 3368719 * 1.08, 25000000, 4e9]) {
  const t = ticks(max);
  assert.ok(t.length >= 2 && t.length <= 8, "max " + max + " gives " + t.length + " lines: " + t.join(","));
  assert.strictEqual(t[0], 0);
  assert.ok(t[t.length - 1] <= max && t[t.length - 1] >= max * 0.5, "top line " + t[t.length - 1] + " for max " + max);
  const step = t[1] - t[0], lead = step / Math.pow(10, Math.floor(Math.log10(step) + 1e-9));
  assert.ok([1, 2, 5].some(k => Math.abs(lead - k) < 1e-6), "step " + step + " is not 1, 2 or 5 times a power of ten");
  t.forEach((v, i) => assert.ok(Math.abs(v - i * step) < 1e-6 * Math.max(1, step), "uneven step"));
}
console.log("stats axis: ok");

// ---- the version line (0.17.2): the number the page runs, and behind it what changed in that version.
// It must never ask GitHub for anything by itself: a wall with no way out to the internet still shows its number.
{
  const at2 = src.indexOf("function versionLine(");
  assert.ok(at2 > 0, "versionLine() not found in stats.js");
  let d2 = 0, end2 = -1;
  for (let j = src.indexOf("{", at2); j < src.length; j++) {
    if (src[j] === "{") d2++;
    else if (src[j] === "}" && --d2 === 0) { end2 = j + 1; break; }
  }
  const RELEASES = src.match(/RELEASES = "([^"]+)"/)[1];
  assert.ok(/^https:\/\/github\.com\/regis57\/ZenithBoard\/releases$/.test(RELEASES), "the link must point at this project's releases");
  const el = {};
  const make = new Function("RELEASES", "$", src.slice(at2, end2) + "return versionLine;");
  make(RELEASES, () => el)("0.17.2");
  assert.strictEqual(el.textContent, "ZenithBoard 0.17.2");
  assert.strictEqual(el.href, RELEASES + "/tag/v0.17.2", "the link goes to that version's own notes");
  make(RELEASES, () => el)(undefined);
  assert.strictEqual(el.textContent, "ZenithBoard", "no version: the name alone, no empty space after it");
  assert.strictEqual(el.href, RELEASES, "and the list of releases rather than a tag that does not exist");
  make(RELEASES, () => null)("0.17.2");          // no such element: must not throw
}
console.log("stats version line: ok");

// ---- the farthest aircraft in words (0.22.0): the real fmt(), shortDay(), altText(), place() and farthestLine()
// taken out of stats.js. What is not known is left out, never guessed, and nothing in the line says where the
// aircraft was in coordinates.
{
  const grab = (name) => {
    const a = src.indexOf("function " + name + "(");
    assert.ok(a > 0, name + "() not found in stats.js");
    let d = 0;
    for (let j = src.indexOf("{", a); j < src.length; j++) {
      if (src[j] === "{") d++;
      else if (src[j] === "}" && --d === 0) return src.slice(a, j + 1);
    }
  };
  // 0.47.0: its words go through t(); English here (the key itself), French below
  const T = "var t = function (s, v) { var c = (CAT && CAT[s]) || s; return v ? c.replace(/\\{(\\w+)\\}/g, function (m, k) { return v[k]; }) : c; };\n";
  const H = ["fmt", "shortDay", "altText", "unitName", "dist", "place", "farthestLine"];
  const line = new Function("CAT", T + "var UNITS = 'metric';\n" + H.map(grab).join("\n") + "return farthestLine;")(null);
  const full = {day: "2026-10-18", time: "14:32", hex: "406a1b", flight: "EZY1234", flight_iata: "U21234", airline: "easyJet",
    registration: "G-EZAB", type: "A319", type_name: "Airbus A319", alt_ft: 37000, km: 318.4,
    route: {from: {city: "Edinburgh", iata: "EDI", name: "Edinburgh Airport"}, to: {city: "Saint-Louis", iata: "BSL"}},
    near: {name: "Charleroi", country: "BE", km: 35}};
  assert.strictEqual(line(full, "metric"),
    "18/10 14:32 \u00b7 easyJet U21234 (EZY1234) \u00b7 Edinburgh (EDI) \u2192 Saint-Louis (BSL) \u00b7 Airbus A319 G-EZAB \u00b7 11\u202f280 m \u00b7 318 km, near Charleroi, BE (35 km)");
  assert.ok(/ 37\u202f000 ft /.test(line(full, "imperial")), "imperial: the altitude in feet");
  // 0.55.0: aviation, as pilots count: feet, and the distances in nautical miles (318.4 km = 172 NM; 35 km = 19 NM)
  assert.ok(/ 37\u202f000 ft \u00b7 172 NM, near Charleroi, BE \(19 NM\)$/.test(line(full, "aviation")), line(full, "aviation"));
  assert.ok(/ 198 mi, near Charleroi, BE \(22 mi\)$/.test(line(full, "imperial")), line(full, "imperial"));
  // a light aircraft: no callsign, no airline, no route, no city found
  assert.strictEqual(line({day: "2026-10-18", time: "09:05", hex: "3c0001", registration: "D-EABC", type: "C172", alt_ft: 4500, km: 205.2}, "metric"),
    "18/10 09:05 \u00b7 D-EABC \u00b7 C172 \u00b7 1\u202f370 m \u00b7 205 km");
  // nothing but the address: the hex, in capitals as trackers show it
  assert.strictEqual(line({day: "2026-10-18", hex: "3c0001", km: 99}, "metric"), "18/10 \u00b7 3C0001 \u00b7 99 km");
  // a callsign the built-in list and adsbdb do not name: the callsign alone, no "undefined" anywhere
  const bare = line({day: "2026-10-18", time: "10:00", hex: "abcdef", flight: "BGA113J", airline: null, km: 300}, "metric");
  assert.strictEqual(bare, "18/10 10:00 \u00b7 BGA113J \u00b7 300 km");
  assert.ok(!/undefined|null|NaN/.test(line(full, "metric") + bare), "no undefined, null or NaN in a line");
  // a military aircraft is said so; half a route keeps its known end
  assert.ok(/RCH123 \(military\)/.test(line({day: "2026-10-18", flight: "RCH123", airline: "MILITARY", hex: "ae0001", km: 250}, "metric")));
  assert.ok(/\? \u2192 Basel \(BSL\)/.test(line(Object.assign({}, full, {route: {from: null, to: {city: "Basel", iata: "BSL"}}}), "metric")));
  // far from any large city (over the sea, say): the distance to it, not "near"
  assert.ok(/\u00b7 318 km, 85 km from Brugge, BE$/.test(line(Object.assign({}, full, {near: {name: "Brugge", country: "BE", km: 85}}), "metric")));
  assert.strictEqual(line(null, "metric"), null);
  // the same line in French, from the shipped catalogue: the words translated, the names and numbers as they were
  const fr = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "flightinfo", "static", "i18n", "fr", "stats.json"), "utf8"));
  const lineFr = new Function("CAT", T + "var UNITS = 'metric';\n" + H.map(grab).join("\n") + "return farthestLine;")(fr);
  assert.ok(/318 km, près de Charleroi, BE \(35 km\)$/.test(lineFr(full, "metric")), lineFr(full, "metric"));
  assert.ok(/RCH123 \(militaire\)/.test(lineFr({day: "2026-10-18", flight: "RCH123", airline: "MILITARY", hex: "ae0001", km: 250}, "metric")));
  assert.ok(/318 km, à 85 km de Brugge, BE$/.test(lineFr(Object.assign({}, full, {near: {name: "Brugge", country: "BE", km: 85}}), "metric")));
}
console.log("stats farthest line: ok");

// ---- 0.99.15 (review B7): the note under the farthest line gave the box's distance in kilometres whatever the page's
// unit ("The box above says 485 km" under a box saying 262 NM). It is the box's distance in the page's unit now, and the
// unit is inside the placeholder, so Arabic isolates the number and its unit together.
{
  const grab = (name) => {
    const a = src.indexOf("function " + name + "(");
    assert.ok(a > 0, name + "() not found in stats.js");
    let d = 0;
    for (let j = src.indexOf("{", a); j < src.length; j++) {
      if (src[j] === "{") d++;
      else if (src[j] === "}" && --d === 0) return src.slice(a, j + 1);
    }
  };
  const T = "var t = function (s, v) { var c = (CAT && CAT[s]) || s; return v ? c.replace(/\\{(\\w+)\\}/g, function (m, k) { return (RTL ? '\\u2066' : '') + v[k] + (RTL ? '\\u2069' : ''); }) : c; };\n";
  const make = (units, cat, rtl) => new Function("CAT", "RTL", T + "var UNITS = '" + units + "';\n" +
    ["fmt", "shortDay", "unitName", "dist", "farthestNote"].map(grab).join("\n") + "return farthestNote;")(cat || null, !!rtl);
  const rec = { km: 300 }, tot = { farthest_km: 485, farthest_when: "2026-10-25 15:17" };
  const en = make("aviation")(rec, tot, true);
  assert.ok(/^The box above says 262 NM, on 25\/10: its details were not written down \(they are since/.test(en), en);
  assert.ok(!/km/.test(en), "no km under aviation units: " + en);
  assert.ok(/^The box above says 485 km, on 25\/10:/.test(make("metric")(rec, tot, true)));
  assert.ok(/^The box above says 301 mi: its details/.test(make("imperial")(rec, { farthest_km: 485 }, false)));
  assert.strictEqual(make("metric")({ km: 485.2 }, tot, true), "", "the line already says as much: no note");
  assert.strictEqual(make("metric")(null, tot, true), "", "no line: no note");
  // every shipped language has the note with its {dist}, and Arabic keeps "262 NM" in one isolate
  const dir = path.join(__dirname, "..", "flightinfo", "static", "i18n");
  for (const lang of fs.readdirSync(dir).filter(l => fs.existsSync(path.join(dir, l, "stats.json")))) {
    const cat = JSON.parse(fs.readFileSync(path.join(dir, lang, "stats.json"), "utf8"));
    for (const k of ["The box above says {dist}, on {day}: its details were not written down", "The box above says {dist}: its details were not written down"])
      assert.ok(cat[k] && cat[k].includes("{dist}") && !/\bkm\b/.test(cat[k]), lang + ": " + k + " -> " + cat[k]);
  }
  const ar = JSON.parse(fs.readFileSync(path.join(dir, "ar", "stats.json"), "utf8"));
  assert.ok(make("aviation", ar, true)(rec, tot, true).includes("\u2066262 NM\u2069"), "Arabic: the number and its unit isolated together");
}
console.log("stats farthest note: ok");


// ---- 0.54.18: a week's messages did not fit its box ("386 530 3…" on the owner's page): from ten million on, short
{
  const pick = name => { const a = src.indexOf("function " + name + "("); let d = 0;
    for (let j = src.indexOf("{", a); j < src.length; j++) { if (src[j] === "{") d++; else if (src[j] === "}" && --d === 0) return src.slice(a, j + 1); } };
  for (const [loc, n, want] of [["fr", 386530314, "386,5 M"], ["en", 57200000, "57.2M"], ["fr", 9999999, null]]) {
    const big = new Function("I", pick("fmt") + pick("big") + "return big;")({ locale: () => loc });
    const got = big(n);
    if (want) assert.strictEqual(got, want);
    else assert.ok(/^9.999.999$/.test(got), "under ten million the whole number stays: " + got);
  }
  assert.ok(/t-messages"\)\.title = fmt\(/.test(src), "the whole number is in the tooltip");
  console.log("stats messages box: ok");
}
