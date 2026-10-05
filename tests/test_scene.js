// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tests/test_scene.js   (side-view profiles used for the animated scene and the demo photos)
const assert = require("assert"), fs = require("fs"), path = require("path");
const K = require("../flightinfo/static/scene.js");
const S = require("../flightinfo/static/shapes.js");

// the classes the server can send (flightinfo/aircraft.py) must all have a side profile and a top-view shape
const py = fs.readFileSync(path.join(__dirname, "..", "flightinfo", "aircraft.py"), "utf8");
const classes = py.match(/CLASSES = \(([^)]*)\)/)[1].match(/"(\w+)"/g).map(s => s.replace(/"/g, ""));
assert.ok(classes.length >= 15, "class list not parsed");
for (const c of classes) {
  assert.ok(K.CLASSES.includes(c), c + " has no side profile");
  assert.ok(c in S.SHAPES, c + " has no top-view shape");
}
const VARIANTS = { quad: ["hump", "deck", "hiwing"], wide: ["tri", "beluga"], rearjet: ["tri", "quad"], turboprop: ["quad"],
                   light: ["high"], twinprop: ["quad"], heli: ["tandem", "tilt"], airlifter: ["jet", "prop2", "prop4"] };
const PATH = /^M[-\d. ]+(?:[LQlaZ][-\d. ]*)*$/;
for (const c of classes) for (const v of [null].concat(VARIANTS[c] || [])) {
  const ops = K.profileOps(c, v);
  assert.ok(ops.length >= 3, c + "/" + v + " draws too little");
  for (const o of ops) {
    if (o.k) { assert.ok(["prop", "rotor", "tailrotor"].includes(o.k), "bad special op " + o.k); continue; }
    assert.ok(PATH.test(o.d), c + "/" + v + " bad path: " + o.d.slice(0, 60));
    assert.ok(!/NaN|undefined|Infinity/.test(o.d), c + "/" + v + " has a bad number");
    assert.ok(["body", "wing", "tail", "eng", "dark", "stripe", "glass"].includes(o.role), "unknown role " + o.role);
  }
}
// distinctive details of the models that matter
const d = (c, v) => K.profileOps(c, v).map(o => o.d || "").join("|");
assert.notStrictEqual(d("quad", "hump"), d("quad", null), "747 hump must change the drawing");
assert.notStrictEqual(d("quad", "deck"), d("quad", null), "A380 deck must change the drawing");
assert.ok(K.profileOps("turboprop").some(o => o.k === "prop"), "turboprops have propellers");
assert.ok(K.profileOps("heli").some(o => o.k === "rotor"), "helicopters have a rotor");
assert.ok(!K.profileOps("narrow").some(o => o.k), "jets have no propeller");

// colours: military is grey, civil gets a stable livery colour per airline
assert.strictEqual(K.palette(true, "x").body, "#9ba2a9");
assert.strictEqual(K.palette(false, "ZZA").tail, K.palette(false, "ZZA").tail);
assert.notStrictEqual(K.palette(false, "ZZA").tail, K.palette(false, "ZZB").tail);
// SVG export (demo photos)
const svg = K.svgOps(K.profileOps("narrow"), K.palette(false, "ZZA"));
assert.ok(svg.includes("<path") && !svg.includes("undefined"));

// sky: a continuous day, never a broken colour, and the sun/moon stays inside the box
assert.strictEqual(K.skyFor(14).night, false);
assert.strictEqual(K.skyFor(23).night, true);
assert.strictEqual(K.skyFor(13).sunUp, true, "the sun is up at midday");
assert.strictEqual(K.skyFor(2).sunUp, false, "the sun is down at 2am");
let noon = null, dusk = null;
for (let h = 0; h < 24; h += 0.25) {
  const s = K.skyFor(Math.floor(h), (h % 1) * 60);
  for (const k of ["top", "mid", "bottom", "light"]) {
    assert.ok(/^(#|rgb\()/.test(s[k]), "bad colour " + k + " at " + h + ": " + s[k]);
    assert.ok(!/NaN/.test(s[k]), "NaN colour " + k + " at " + h);
  }
  assert.ok(s.bodyX >= 0 && s.bodyX <= 1 && s.bodyY >= 0 && s.bodyY <= 1, "sun/moon outside the box at " + h);
  assert.ok(s.dark >= 0 && s.dark <= 1, "dark out of range at " + h);
  if (h === 13) noon = s;
  if (h === 20) dusk = s;
}
assert.strictEqual(noon.dark, 0, "midday is not dark");
assert.notStrictEqual(noon.top, dusk.top, "the sky must change between midday and dusk");
assert.ok(K.skyFor(8).bodyX < K.skyFor(18).bodyX, "the sun must travel across the sky");
assert.ok(K.skyFor(13).bodyY < K.skyFor(7).bodyY, "the sun must be higher at midday than at 7am");
console.log("scene tests OK");
