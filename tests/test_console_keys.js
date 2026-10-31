// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tests/test_console_keys.js   The console in a real browser (headless Chromium, through Playwright), with
// the keyboard (0.99.18, review B10). The page and its scripts are the release's own; the Pi's answers (/console/api/*)
// are stand-ins, the catalogue of actions the real one (flightinfo/console_actions.py):
//   - Enter in a field runs its action once: the card shows one output, and its button waits ("…") instead of being
//     clicked a second time (before: the page was not drawn under the typing finger, the button stayed live);
//   - Space on a switch, then Enter on the question, leaves the focus on the switch drawn again (before: on the page);
//   - the Activity drawer takes the focus to its ×, Tab stays inside it, Escape gives the focus back to Activity;
//   - the page reads the Pi again every two minutes and when its tab is shown again, never while a field is typed in.
const assert = require("assert"), fs = require("fs"), path = require("path"), { execFileSync } = require("child_process");
let chromium;
try { ({ chromium } = require("playwright")); } catch (e) {
  console.error("test_console_keys.js needs Playwright (npm install playwright, then npx playwright install chromium)");
  process.exit(1);
}
const ROOT = path.join(__dirname, "..");
const STATIC = path.join(ROOT, "flightinfo", "static");
const CAT = JSON.parse(execFileSync("python3", ["-c",
  "import json, console_actions as a; print(json.dumps({'catalog': a.catalog(), 'sections': a.SECTIONS}))"],
  { cwd: path.join(ROOT, "flightinfo") }).toString());
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml" };
const BASE = "http://zb.test";

let pass = 0, fail = 0;
async function check(name, fn) {
  try { await fn(); pass++; console.log("ok   " + name); } catch (e) { fail++; console.log("FAIL " + name + "\n     " + (e && e.message || e)); }
}

// a page of the console, signed in, against stand-in answers; `now` is the page's clock in seconds (the facts' age)
async function consolePage(browser, opts) {
  opts = opts || {};
  const ctx = await browser.newContext({ viewport: opts.viewport || { width: 1280, height: 860 } });
  const page = await ctx.newPage();
  const seen = { state: 0, runs: [] };
  let jobs = 0;
  if (opts.clock) await page.clock.install({ time: opts.clock });
  const now = () => Math.floor((opts.clock || Date.now()) / 1000);
  await page.route(BASE + "/**", async (route) => {
    const u = new URL(route.request().url()), p = u.pathname;
    const json = (o) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(o) });
    if (p === "/api/config") return json({ lang: "", langs: [] });
    if (p === "/console" || p === "/console/") return route.fulfill({ status: 200, contentType: "text/html", body: fs.readFileSync(path.join(STATIC, "console.html")) });
    if (p.indexOf("/static/") === 0) {
      const f = path.join(STATIC, p.slice(8));
      if (f.indexOf(STATIC) !== 0 || !fs.existsSync(f)) return route.fulfill({ status: 404, body: "" });
      return route.fulfill({ status: 200, contentType: TYPES[path.extname(f)] || "application/octet-stream", body: fs.readFileSync(f) });
    }
    const api = p.replace(/^\/console\/api\//, "");
    if (api === "session") return json({ enabled: true, signed_in: true, has_password: true, csrf: "c", wizard_done: true, version: "0.99.18", writable: true });
    if (api === "state") {
      seen.state++;
      return json({ cfg: { THEME: "amber", CYCLE_SECONDS: "8", RADIUS: "5", UNITS: "metric", DISPLAY_MODE: "dots", CONSOLE_LANG: "en" },
        facts: { watchdog: "off", netwatch: "off", graphs: "off", svc_readsb: "active" }, facts_at: now(),
        catalog: CAT.catalog, sections: CAT.sections, now: now() });
    }
    if (api === "run") {
      const b = JSON.parse(route.request().postData() || "{}");
      if (b.action !== "refresh" && b.action !== "console-lang") seen.runs.push(b.action);
      return json({ job: "j" + (++jobs) });
    }
    if (api.indexOf("job") === 0) return json({ state: "running", log: "$ zenithboard …\n", next: 1 });
    if (api === "activity") return json({ jobs: [], journal: [], audit: [] });
    return json({});
  });
  await page.goto(BASE + "/console#" + (opts.section || "overview"));
  await page.waitForSelector("#view .card");
  return { page, ctx, seen };
}
const active = (page) => page.evaluate(() => {
  const a = document.activeElement;
  return { tag: a.tagName, role: a.getAttribute("role"), label: a.getAttribute("aria-label"), text: a.textContent,
    off: a.getAttribute("aria-disabled") === "true" || a.disabled === true, inDrawer: !!a.closest("#drawer"), id: a.id, inView: !!a.closest("#view") };
});

(async () => {
  const browser = await chromium.launch();
  try {
    await check("Enter in a field runs it once: one output in its card, its button waiting", async () => {
      const { page, ctx, seen } = await consolePage(browser, { section: "wall" });
      const inp = page.locator('input[aria-label="Seconds per aircraft"]');
      await inp.fill("12");
      await inp.press("Enter");
      await page.locator('input[aria-label="Seconds per aircraft"] + button').click({ force: true, timeout: 2000 }).catch(() => {});
      await page.waitForTimeout(800);
      assert.deepStrictEqual(seen.runs, ["cycle"], "one run of cycle, got " + JSON.stringify(seen.runs));
      assert.strictEqual(await page.locator(".term.inline").count(), 1, "one output card");
      const b = await page.evaluate(() => { const x = document.querySelector('input[aria-label="Seconds per aircraft"] + button');
        return { text: x.textContent, off: x.disabled || x.getAttribute("aria-disabled") === "true" }; });
      assert.deepStrictEqual(b, { text: "…", off: true });
      await ctx.close();
    });

    await check("Space on Hardware watchdog, Enter on the question: the focus is on the switch drawn again", async () => {
      const { page, ctx, seen } = await consolePage(browser, { section: "reliability" });
      await page.locator('#view button[role=switch][aria-label="Hardware watchdog"]').focus();
      await page.keyboard.press(" ");
      await page.waitForFunction(() => document.activeElement && document.activeElement.closest("#modal-panel") && document.activeElement.classList.contains("primary"));
      await page.keyboard.press("Enter");
      await page.waitForFunction(() => document.querySelector("#modal").hidden);
      await page.waitForTimeout(600);
      assert.deepStrictEqual(seen.runs, ["watchdog"]);
      const a = await active(page);
      assert.deepStrictEqual([a.role, a.label, a.off, a.inView], ["switch", "Hardware watchdog", true, true], JSON.stringify(a));
      // waiting, it does nothing: Space again runs nothing more and asks nothing
      await page.keyboard.press(" ");
      await page.waitForTimeout(300);
      assert.ok(await page.evaluate(() => document.querySelector("#modal").hidden), "no second question");
      assert.deepStrictEqual(seen.runs, ["watchdog"]);
      await ctx.close();
    });

    await check("the question gives the focus back and the page behind it is inert while it is open", async () => {
      const { page, ctx } = await consolePage(browser, { section: "reliability" });
      await page.locator('#view button[role=switch][aria-label="Hardware watchdog"]').focus();
      await page.keyboard.press("Enter");
      await page.waitForFunction(() => document.activeElement && document.activeElement.closest("#modal-panel"));
      assert.ok(await page.evaluate(() => document.querySelector("#app").inert), "the page is inert behind the question");
      for (let i = 0; i < 5; i++) {
        await page.keyboard.press("Tab");
        assert.ok(await page.evaluate(() => !!document.activeElement.closest("#modal-panel")), "Tab " + (i + 1) + " stays in the question");
      }
      await page.locator("#modal-panel .modal-foot button.btn").click();       // Cancel
      const a = await active(page);
      assert.deepStrictEqual([a.role, a.label, a.off], ["switch", "Hardware watchdog", false]);
      assert.ok(!(await page.evaluate(() => document.querySelector("#app").inert)), "the page is back");
      await ctx.close();
    });

    await check("the Activity drawer focuses its ×, Tab stays inside, Escape gives the focus back", async () => {
      const { page, ctx } = await consolePage(browser, { viewport: { width: 360, height: 740 } });
      await page.locator("#open-activity").focus();
      await page.keyboard.press("Enter");
      await page.waitForSelector("#drawer:not([hidden])");
      await page.waitForTimeout(200);
      let a = await active(page);
      assert.deepStrictEqual([a.inDrawer, a.label, a.text.trim()], [true, "Close", "×"], JSON.stringify(a));
      assert.ok(await page.evaluate(() => document.querySelector("#app").inert), "the page is inert behind the drawer");
      for (let i = 0; i < 6; i++) {
        await page.keyboard.press(i % 2 ? "Shift+Tab" : "Tab");
        assert.ok((await active(page)).inDrawer, "Tab " + (i + 1) + " stays in the drawer");
      }
      await page.keyboard.press("Escape");
      a = await active(page);
      assert.strictEqual(a.id, "open-activity");
      await ctx.close();
    });

    await check("every two minutes, and when the tab is shown again, the page reads the Pi again", async () => {
      const { page, ctx, seen } = await consolePage(browser, { clock: Date.parse("2026-10-31T10:00:00Z") });
      await page.waitForTimeout(300);
      const first = seen.state;
      await page.clock.fastForward(125000);
      await page.waitForTimeout(300);
      assert.ok(seen.state > first, "a reading after two minutes (" + first + " → " + seen.state + ")");
      assert.ok(await page.locator("text=/Read on the Pi 2 min ago/").count(), "its time drawn again");
      // a field being typed in: nothing is read under the finger
      await page.evaluate(() => { location.hash = "#wall"; });
      await page.waitForSelector('input[aria-label="Seconds per aircraft"]');
      await page.locator('input[aria-label="Seconds per aircraft"]').focus();
      let before = seen.state;
      await page.clock.fastForward(125000);
      await page.waitForTimeout(300);
      assert.strictEqual(seen.state, before, "no reading while a field has the focus");
      await page.locator("#title").click();
      // hidden, then shown again
      before = seen.state;
      await page.evaluate(() => {
        let v = "hidden";
        Object.defineProperty(document, "visibilityState", { configurable: true, get: () => v });
        document.dispatchEvent(new Event("visibilitychange"));
        v = "visible";
        document.dispatchEvent(new Event("visibilitychange"));
      });
      await page.waitForTimeout(300);
      assert.ok(seen.state > before, "a reading when the tab is shown again");
      await ctx.close();
    });
  } finally {
    await browser.close();
  }
  console.log(pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
