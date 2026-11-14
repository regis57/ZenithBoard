// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tests/test_units_table.js   The pages' side of the one table of units (lot 0 after 1.0):
// flightinfo/static/units.js against tests/units_table.json, the same table tests/test_units_table.py holds
// flightinfo/units.py to. And no factor written in another page script: a conversion added outside units.js fails here.
const assert = require("assert"), fs = require("fs"), path = require("path");
const STATIC = path.join(__dirname, "..", "flightinfo", "static");
const U = require(path.join(STATIC, "units.js")), T = JSON.parse(fs.readFileSync(path.join(__dirname, "units_table.json"), "utf8"));
const near = (a, b, what) => assert.ok(Math.abs(a - b) < 1e-6, what + ": " + a + " is not " + b);

for (const name of Object.keys(T.factors)) assert.strictEqual(U[name], T.factors[name], name);
assert.deepStrictEqual(U.SYSTEMS, T.systems);
for (const [given, want] of T.system) assert.strictEqual(U.system(given), want, JSON.stringify(given));
assert.strictEqual(U.system("nautical", null), null);
for (const u of Object.keys(T.feet_and_knots)) assert.strictEqual(U.feetAndKnots(u), T.feet_and_knots[u], u);
for (const u of Object.keys(T.label)) assert.strictEqual(U.distanceLabel(u), T.label[u], u);
for (const [km, u, want] of T.distance) near(U.distance(km, u), want, km + " km in " + u);
for (const [v, u, want] of T.to_km) near(U.toKm(v, u), want, v + " " + u + " in km");
for (const [ft, want] of T.metres) near(U.metres(ft), want, ft + " ft");
for (const [kt, want] of T.kmh) near(U.kmh(kt), want, kt + " kt");
console.log("units table: ok");

// no factor outside units.js, in the pages' scripts and the posts' picture
const factor = /(?<![\w.])(1\.609344|1\.852|0\.3048|1609\.344)(?![\w])/;
const found = [];
for (const dir of [STATIC, path.join(__dirname, "..", "tools")]) {
  for (const name of fs.readdirSync(dir).filter((n) => n.endsWith(".js") && n !== "units.js").sort()) {
    fs.readFileSync(path.join(dir, name), "utf8").split("\n").forEach((line, i) => {
      if (factor.test(line.split("//")[0])) found.push(name + ":" + (i + 1) + " " + line.trim().slice(0, 80));
    });
  }
}
assert.deepStrictEqual(found, [], "a unit factor outside flightinfo/static/units.js");
console.log("no factor outside units.js: ok");

// the wall's page and the statistics page load units.js before the script that uses it
for (const [page, user] of [["index.html", "format.js"], ["stats.html", "stats.js"]]) {
  const html = fs.readFileSync(path.join(STATIC, page), "utf8");
  const a = html.indexOf("/static/units.js"), b = html.indexOf("/static/" + user);
  assert.ok(a > 0 && a < b, page + " loads units.js before " + user);
}
console.log("pages load units.js first: ok");
