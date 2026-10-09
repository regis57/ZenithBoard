// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tests/test_layout.js   The settings gear sits in the bottom-right corner of the screen (a TV browser bar covers the top edge).
// It must never touch the photo / animated scene box or the aircraft drawing. The geometry is read from app.js and style.css, so
// changing the layout there is checked here against common screen sizes.
const assert = require("assert"), fs = require("fs"), path = require("path");
const dir = path.join(__dirname, "..", "flightinfo", "static");
const js = fs.readFileSync(path.join(dir, "app.js"), "utf8"), css = fs.readFileSync(path.join(dir, "style.css"), "utf8");

const num = (re, src, what) => { const m = src.match(re); assert.ok(m, what + " not found"); return m.slice(1).map(Number); };
const [GW, GH] = num(/var GW = (\d+), GH = (\d+);/, js, "grid size");
const [RX, RW] = num(/var RX = (\d+), RW = (\d+);/, js, "right column");
const sil = num(/SIL_BOX = \{ x: RX, y: (\d+), w: RW, h: (\d+) \}/, js, "SIL_BOX");
const ph = num(/PHOTO_BOX = \{ x: (\d+), y: (\d+), w: (\d+), h: (\d+) \}/, js, "PHOTO_BOX");
const gearCss = css.match(/#gear \{([^}]*)\}/)[1];
assert.ok(/bottom:\s*\d+px/.test(gearCss) && /right:\s*\d+px/.test(gearCss), "the gear must be positioned from the bottom-right corner");
assert.ok(!/(^|[;\s])top:/.test(gearCss), "the gear must not be positioned from the top");
const [gb] = num(/bottom:\s*(\d+)px/, gearCss, "gear bottom"), [gr] = num(/right:\s*(\d+)px/, gearCss, "gear right"), [gw] = num(/width:\s*(\d+)px/, gearCss, "gear width"), [gh] = num(/height:\s*(\d+)px/, gearCss, "gear height");

// the same maths as geom() in app.js
const geom = (cw, ch) => { const pitch = Math.min(cw / (GW + 3), ch / (GH + 3)); return { pitch, ox: (cw - pitch * GW) / 2, oy: (ch - pitch * GH) / 2 }; };
const rect = (g, x, y, w, h) => ({ l: g.ox + x * g.pitch, t: g.oy + y * g.pitch, r: g.ox + (x + w) * g.pitch, b: g.oy + (y + h) * g.pitch });
const hit = (a, b) => a.l < b.r && a.r > b.l && a.t < b.b && a.b > b.t;

// width x height of TVs, tablets and phones, in both orientations
const screens = [[1920, 1080], [3840, 2160], [2560, 1440], [1366, 768], [1280, 800], [1280, 720], [1024, 768], [800, 480], [640, 360], [480, 320],
                 [1080, 1920], [768, 1024], [800, 1280], [360, 640], [412, 915]];
let worst = Infinity;
for (const [cw, ch] of screens) {
  const g = geom(cw, ch);
  const gear = { l: cw - gr - gw, t: ch - gb - gh, r: cw - gr, b: ch - gb };
  const photo = rect(g, ph[0], ph[1], ph[2], ph[3]), drawing = rect(g, RX, sil[0], RW, sil[1]);
  assert.ok(!hit(gear, photo), cw + "x" + ch + ": the gear covers the photo");
  assert.ok(!hit(gear, drawing), cw + "x" + ch + ": the gear covers the aircraft drawing");
  assert.ok(gear.l >= 0 && gear.t >= 0, cw + "x" + ch + ": the gear is off screen");
  worst = Math.min(worst, gear.t - photo.b);
}
assert.ok(worst >= 0, "the gear must stay clear of the photo");

// the settings panel opens above the gear and stays inside the screen
const panel = css.match(/#settings \{([^}]*)\}/)[1];
assert.ok(/bottom:\s*\d+px/.test(panel) && !/(^|[;\s])top:/.test(panel), "the settings panel must open upward from the gear");
assert.ok(/max-height:/.test(panel) && /overflow-y:\s*auto/.test(panel), "a tall panel must scroll on a short screen");
console.log("layout ok: gear bottom-right clear of photo and drawing on " + screens.length + " screens (smallest gap " + Math.round(worst) + " px)");
