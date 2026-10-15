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
