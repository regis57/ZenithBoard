// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tests/test_shapes.js
const assert = require("assert");
const S = require("../flightinfo/static/shapes.js");

for (const name of ["narrow", "wide", "turboprop", "bizjet", "light", "heli", "generic"]) {
  const m = S.rasterize(name, 32, 32), on = m.reduce((a, b) => a + b, 0);
  assert.ok(on > 120 && on < 500, name + " has an implausible dot count: " + on);
  // nose points right: the right half must reach further than the left tip of the fuselage
  let maxX = 0; for (let y = 0; y < 32; y++) for (let x = 0; x < 32; x++) if (m[y * 32 + x]) maxX = Math.max(maxX, x);
  assert.ok(maxX >= 26, name + " should extend to the right side");
}
assert.deepStrictEqual(Array.from(S.rasterize("nope", 8, 8)), Array.from(S.rasterize("generic", 8, 8)));   // unknown shape -> generic

const logo = S.decodeLogo({ w: 4, h: 2, palette: ["#ff0000", "#00ff00"], rows: ["0..1", ".01."] });
assert.strictEqual(logo.cells.length, 4);
assert.deepStrictEqual(logo.cells[0], { x: 0, y: 0, color: 0xff0000 });
assert.deepStrictEqual(logo.cells[1], { x: 3, y: 0, color: 0x00ff00 });
assert.strictEqual(S.decodeLogo(null).cells.length, 0);
console.log("shape tests OK");
