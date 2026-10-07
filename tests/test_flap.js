// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tests/test_flap.js   Split-flap model: letters flip through the alphabet, row by row, and always arrive.
const assert = require("assert");
const K = require("../flightinfo/static/flap.js");
const rand = () => 0;

assert.strictEqual(K.norm("a"), "A"); assert.strictEqual(K.norm("é"), " "); assert.strictEqual(K.norm("→"), "→");
assert.strictEqual(K.stepsBetween("A", "A"), 0); assert.strictEqual(K.stepsBetween("A", "C"), 2);
assert.strictEqual(K.stepsBetween("C", "A"), K.CHARS.length - 2, "flaps only turn one way: going back means going round");
assert.ok(K.CHARS.indexOf("→") > 0);

const b = new K.Board(8, 3, rand);
b.setRows(["LGL8FM", "LUXAIR", ""], 1000, true);
assert.deepStrictEqual(b.text(1000), ["LGL8FM  ", "LUXAIR  ", "        "], "instant: no flipping");
assert.strictEqual(b.update(1000), false);

// a new aircraft: every changed letter flips, row 1 starts before row 2, nothing changes where the text is the same
b.setRows(["LGL8FM", "WIZZ", "ALT 4600"], 2000);
const t0 = b.text(2000); assert.strictEqual(t0[0], "LGL8FM  ", "nothing has moved yet");
assert.strictEqual(b.cell(0, 0, 2000).flipping, false, "row 0, letter 0 is unchanged and stays still");
assert.ok(b.update(2000), "busy while letters are waiting");
// the second row's first letter changes L->W: it waits ROW_MS, then flips through the alphabet
assert.strictEqual(b.cell(1, 0, 2000 + K.ROW_MS - 1).flipping, false);
const mid = b.cell(1, 0, 2000 + K.ROW_MS + K.STEP_MS * 3 + 5);
assert.ok(mid.flipping && mid.prev !== "L" && mid.prev !== "W", "an intermediate letter is shown: " + mid.prev);
assert.ok(mid.phase >= 0 && mid.phase < 1);
// the letters it passes through are consecutive in the alphabet
const seen = []; for (let t = 0; t < 40; t++) seen.push(b.cell(1, 0, 2000 + K.ROW_MS + t * K.STEP_MS + 1).prev);
for (let i = 1; i < seen.length; i++) if (seen[i] !== seen[i - 1]) assert.strictEqual(K.stepsBetween(seen[i - 1], seen[i]), 1, seen[i - 1] + ">" + seen[i]);

// it always ends on the target, and update() reports idle only then
const end = 2000 + 8 * K.ROW_MS + 8 * K.COL_MS + K.CHARS.length * K.STEP_MS + 100;
assert.strictEqual(b.update(end), false);
assert.deepStrictEqual(b.text(end), ["LGL8FM  ", "WIZZ    ", "ALT 4600"]);

// a change that arrives while letters are still flipping retargets from where they are, and still ends right
const c = new K.Board(6, 1, rand);
c.setRows(["AAAAAA"], 0, true);
c.setRows(["ZZZZZZ"], 100);
c.setRows(["MMMMMM"], 100 + K.STEP_MS * 4);
const done = 100 + K.STEP_MS * 4 + 6 * K.COL_MS + K.CHARS.length * K.STEP_MS + 100;
assert.strictEqual(c.update(done), false); assert.strictEqual(c.text(done)[0], "MMMMMM");

// too-long and too-short lines are cut / padded; unknown characters become blanks
const d = new K.Board(4, 1, rand); d.setRows(["ABCDEFG"], 0, true); assert.strictEqual(d.text(0)[0], "ABCD");
d.setRows(["éB"], 0, true); assert.strictEqual(d.text(0)[0], " B  ");
console.log("flap tests OK");
