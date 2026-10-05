// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tests/test_shapes.js
const assert = require("assert");
const S = require("../flightinfo/static/shapes.js");

const NAMES = ["narrow", "wide", "quad", "rearjet", "turboprop", "bizjet", "light", "twinprop", "heli", "fighter",
               "delta", "airlifter", "bomber", "glider", "balloon", "generic"];
for (const name of NAMES) {
  const m = S.rasterize(name, 32, 32), on = m.reduce((a, b) => a + b, 0);
  assert.ok(on > 60 && on < 700, name + " has an implausible dot count: " + on);
  let maxX = 0; for (let y = 0; y < 32; y++) for (let x = 0; x < 32; x++) if (m[y * 32 + x]) maxX = Math.max(maxX, x);
  if (name !== "balloon") assert.ok(maxX >= 26, name + " should extend to the right side");   // nose points right
}
assert.deepStrictEqual(Array.from(S.rasterize("nope", 8, 8)), Array.from(S.rasterize("generic", 8, 8)));   // unknown shape -> generic

// every class must look different from every other (no accidental copies)
const seen = new Map();
for (const name of NAMES.filter(n => n !== "generic")) {
  const key = Array.from(S.rasterize(name, 32, 32)).join("");
  assert.ok(!seen.has(key), name + " is identical to " + seen.get(key));
  seen.set(key, name);
}
assert.ok(!("decodeLogo" in S), "logos were removed");
console.log("shape tests OK");
