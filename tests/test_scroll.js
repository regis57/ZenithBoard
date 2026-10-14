// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tests/test_scroll.js   A name too long for its row turns continuously. This takes the real
// textRow and the real row() out of app.js (the source itself, not a copy of it) and walks every offset of a
// full turn: each step must be the previous one moved exactly one dot to the left. A jump back to the start
// would break that, which is what 0.14.1 did and 0.14.2 fixes.
const assert = require("assert"), fs = require("fs"), path = require("path");
const dir = path.join(__dirname, "..", "flightinfo", "static");
const app = fs.readFileSync(path.join(dir, "app.js"), "utf8");
const Font5x7 = require(path.join(dir, "font5x7.js"));

function lift(name) {                       // the function as it is written in app.js, braces balanced
  const at = app.indexOf("function " + name + "(");
  assert.ok(at > 0, name + " not found in app.js");
  let depth = 0, i = app.indexOf("{", at);
  for (let j = i; j < app.length; j++) {
    if (app[j] === "{") depth++;
    else if (app[j] === "}" && --depth === 0) return app.slice(at, j + 1);
  }
  throw new Error("unbalanced " + name);
}
const GAP = app.match(/GAP = "(\s+)"/)[1];
const ON = Number(app.match(/var ON = (\d+)/)[1]);
const sandbox = new Function("Font5x7", "put", "GAP", "maxX", "ON",
  lift("textRow") + lift("rowWidth") + lift("row") + "return { textRow: textRow, row: row, rowWidth: rowWidth };");

const MAXX = Number(app.match(/TEXT_MAX_X = (\d+)/)[1]);
function run(text, maxX) {
  const lit = [];
  const api = sandbox(Font5x7, (g, x, y, v) => { lit[lit.length - 1].add(x + "," + y + "," + v); }, GAP, maxX, ON);
  const r = api.row(16, text);
  const frames = [];
  const turns = r.cycle > 0 ? r.cycle : 1;
  for (let off = 0; off < turns; off++) {
    lit.push(new Set());
    api.textRow(null, r.draw, 16, off, maxX);
    frames.push(lit[lit.length - 1]);
  }
  return { r, frames };
}

// ---- a short name does not move at all
const short = run("SWISS", MAXX);
assert.strictEqual(short.r.cycle, 0, "a name that fits must not scroll");
assert.strictEqual(short.r.draw, "SWISS", "a name that fits is drawn as it is");

// ---- a long one turns, and every step is the one before it moved one dot left
for (const name of ["ROYAL AIR MAROC", "BRUSSELS AIRLINES", "AIRBUS A319-100", "SCANDINAVIAN AIRLINES SYSTEM"]) {
  const { r, frames } = run(name, MAXX);
  assert.ok(r.cycle > 0, name + " is too long for the row and must scroll");
  assert.strictEqual(r.draw, name + GAP + name, name + " must be followed by a gap and itself again");
  for (let off = 0; off < frames.length; off++) {
    const now = frames[off], next = frames[(off + 1) % frames.length];
    let checked = 0;
    for (const dot of now) {
      const [x, y, v] = dot.split(",");
      if (Number(x) === 0) continue;                     // this one walks off the left edge
      assert.ok(next.has((Number(x) - 1) + "," + y + "," + v),
                name + ": at offset " + off + " the dot " + x + "," + y + " did not move one to the left");
      checked++;
    }
    assert.ok(checked > 0, name + ": offset " + off + " drew nothing");
  }
  // the row is never left half empty: the gap between the two passes is three characters, never more
  const widest = frames.map((f) => Math.max(...[...f].map((d) => Number(d.split(",")[0]))));
  assert.ok(Math.min(...widest) >= MAXX - (GAP.length + 1) * 6,
            name + ": a hole wider than the gap opened at the right-hand edge");
}

console.log("scroll ok: a name that fits stays still; a longer one turns one dot at a time with no jump back");
