// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tests/test_pages_smoke.js   The wall, /stats and /console loaded in a real browser (headless Chromium,
// through Playwright) from the release's own server, started as bin/zenithboard-demo starts it (invented flights, no
// antenna, no network). It fails on any page error (an exception in a page's script), on a script, style or page of
// ours that does not load, and on a page left empty. 1.0.1, the first step of the lots after 1.0 (lot 0): the other
// tests read the scripts or drive one page with a stand-in server; none loaded the three pages from server.py itself,
// so a mistake that breaks a page at load (0.99.8's review, T1) had nothing to stop it before the changes of the lot.
const assert = require("assert"), fs = require("fs"), os = require("os"), path = require("path"), net = require("net"), { spawn } = require("child_process");
let chromium;
try { ({ chromium } = require("playwright")); } catch (e) {
  console.error("test_pages_smoke.js needs Playwright (npm install playwright, then npx playwright install chromium)");
  process.exit(1);
}
const ROOT = path.join(__dirname, "..");
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "zb-smoke-"));
let server = null, fail = 0;
function end(code) { if (server) server.kill("SIGTERM"); fs.rmSync(tmp, { recursive: true, force: true }); process.exit(code); }
const freePort = () => new Promise((ok) => { const s = net.createServer(); s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => ok(p)); }); });
async function check(name, fn) {
  try { await fn(); console.log("ok   " + name); } catch (e) { fail++; console.log("FAIL " + name + "\n     " + String(e && e.message || e).split("\n").join("\n     ")); }
}

(async () => {
  const port = await freePort(), base = "http://127.0.0.1:" + port;
  const cfg = path.join(tmp, "config.env");
  // what bin/zenithboard-demo writes, on a port of our own; the statistics and the console's folders in the temp folder
  fs.writeFileSync(cfg, ["UNITS=metric", "THEME=amber", "LAT=49.246", "LON=6.223", "RADIUS=10", "CYCLE_SECONDS=4", "PORT=" + port, "DEMO=1",
    "SHOW_PHOTOS=1", "DEMO_REAL_PHOTOS=0", "USER_DATA_DIR=/nonexistent", "AIRCRAFT_JSON=" + path.join(ROOT, "flightinfo", "demo", "aircraft.json"), ""].join("\n"));
  let log = "";
  server = spawn("python3", [path.join(ROOT, "flightinfo", "server.py")], {
    env: Object.assign({}, process.env, { ZENITHBOARD_CONFIG: cfg, ZB_STATS_DIR: path.join(tmp, "stats"), ZB_CONSOLE_DIR: path.join(tmp, "console"), ZB_VAR_DIR: tmp }),
    stdio: ["ignore", "pipe", "pipe"] });
  server.stdout.on("data", (d) => { log += d; }); server.stderr.on("data", (d) => { log += d; });
  let up = false;
  for (let i = 0; i < 80 && !up; i++) {
    up = await new Promise((ok) => { const s = net.connect(port, "127.0.0.1", () => { s.destroy(); ok(true); }); s.on("error", () => ok(false)); });
    if (!up) await new Promise((r) => setTimeout(r, 250));
  }
  if (!up) { console.log("FAIL the server did not start\n" + log); end(1); }

  const browser = await chromium.launch();
  const PAGES = [
    { name: "the wall (/)", url: "/", ready: "canvas, #wall, body" },
    { name: "the statistics (/stats)", url: "/stats", ready: "body" },
    { name: "the web console (/console)", url: "/console", ready: "body" },
  ];
  for (const p of PAGES) {
    await check(p.name + " loads with no page error and none of our files missing", async () => {
      const ctx = await browser.newContext({ viewport: { width: 1024, height: 768 } }), page = await ctx.newPage();
      const errors = [], missing = [];
      page.on("pageerror", (e) => errors.push(String(e && e.message || e)));
      // ours only: the page's own scripts, styles and data, not a photo or a map tile asked of the outside
      page.on("response", (r) => { const u = r.url(); if (u.startsWith(base) && r.status() >= 400 && !/\/api\//.test(u)) missing.push(r.status() + " " + u.slice(base.length)); });
      page.on("requestfailed", (r) => { const u = r.url(); if (u.startsWith(base) && /\.(js|css|html|json)(\?|$)/.test(u)) missing.push("failed " + u.slice(base.length)); });
      const res = await page.goto(base + p.url, { waitUntil: "load", timeout: 30000 });
      assert.ok(res && res.status() === 200, p.url + " answered " + (res && res.status()));
      await page.waitForTimeout(2500);                 // the first poll, the first frame, the catalogue of the language
      const seen = await page.evaluate(() => ({ text: document.body.innerText.trim().length, nodes: document.body.querySelectorAll("*").length, canvas: document.querySelectorAll("canvas").length }));
      assert.deepStrictEqual(errors, [], "page errors:\n" + errors.join("\n"));
      assert.deepStrictEqual(missing, [], "not loaded:\n" + missing.join("\n"));
      assert.ok(seen.nodes > 5 && (seen.text > 0 || seen.canvas > 0), "the page is empty: " + JSON.stringify(seen));
      await ctx.close();
    });
  }
  await browser.close();
  console.log(fail ? "\n" + fail + " FAILED" : "\nall " + PAGES.length + " pages passed");
  end(fail ? 1 : 0);
})().catch((e) => { console.log("FAIL " + (e && e.stack || e)); end(1); });
