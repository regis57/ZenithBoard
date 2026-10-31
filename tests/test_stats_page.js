// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tests/test_stats_page.js [--shots DIR]   The statistics page and graphs1090's page in ZenithBoard's look, in
// a real browser (headless Chromium, through Playwright), on phones and tablets (0.99.20, review B12). The pages and
// their scripts are the release's own; /api/stats is the real read_stats() of server.py over eight days of made-up
// samples, with a made-up fleet; graphs1090's page is a stand-in of its index.html (its structure, read in wiedehopf's
// html/index.html, 31 October 2026) patched by the real graphs_look_apply, and a stand-in of its graphs.js doing what
// the real one does to the address as it starts (history.replaceState to ?timeframe=):
//   - on a phone the military list drops its bar (a base rule after the phone's block showed it);
//   - a chart's tooltip stays inside the screen at both ends of a chart and at its top, and a scroll hides it;
//   - the tiles' figures fit their tile at 768, 900 and 1024 px, in English, Arabic and Finnish ("386,5 milj.");
//   - in Arabic the grey words after a cargo airline keep their gap from its name;
//   - graphs1090's page opened with ?lang=fr or ?lang=ar is in that language, and its brand fits a 320 px phone.
// 0.99.21 (review B13), right to left and the words in dots:
//   - in Arabic the busiest hour reads 07:00 and its count 249 195 in order, the farthest line the day before the time
//     and "Lyon, FR (12 km)" with 12 before km; a Latin name too long for its list is cut at its end;
//   - Finnish and Japanese write the hour their way (07.00, 07:00台);
//   - Spanish and Portuguese show their own word in dots (ESTADISTICAS, GRAFICOS), the catalogue keeping its accent;
//   - Arabic headings use the system's font, not a monospace one.
// With --shots DIR it also writes the pictures of the release's preview into DIR.
const assert = require("assert"), fs = require("fs"), os = require("os"), path = require("path"), { execFileSync } = require("child_process");
let chromium;
try { ({ chromium } = require("playwright")); } catch (e) {
  console.error("test_stats_page.js needs Playwright (npm install playwright, then npx playwright install chromium)");
  process.exit(1);
}
const ROOT = path.join(__dirname, "..");
const STATIC = path.join(ROOT, "flightinfo", "static"), FLAGS = path.join(ROOT, "flightinfo", "data", "flags");
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml" };
const BASE = "http://zb.test", GRAPHS = "http://graphs.test:8542";
const LANGS = fs.readdirSync(path.join(STATIC, "i18n")).filter((c) => fs.existsSync(path.join(STATIC, "i18n", c, "stats.json")));
const shotAt = process.argv.indexOf("--shots"), SHOTS = shotAt > 0 ? process.argv[shotAt + 1] : "";
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "zb-stats-page-"));
process.on("exit", () => fs.rmSync(tmp, { recursive: true, force: true }));

// ---- /api/stats: server.py's own read_stats() over eight days of quarter hours, busy by day, quiet by night
const STATS = JSON.parse(execFileSync("python3", ["-c", `
import datetime, json, os, random, sys
import server
d = sys.argv[1]; now = datetime.datetime(2026, 10, 31, 14, 7); random.seed(7)
with open(os.path.join(d, "stats.csv"), "w") as f:
    f.write("when,messages,farthest_km,aircraft_pos,aircraft_seen\\n")
    t = now - datetime.timedelta(days=8)
    while t <= now:
        busy = max(0.05, 1 - abs(t.hour - 13) / 11.0)
        f.write("%s,%d,%d,%d,%d\\n" % (t.strftime("%Y-%m-%d %H:%M"), int(busy * 1100000 + random.random() * 90000),
                int(170 + busy * 180 + random.random() * 40), int(busy * 42), int(busy * 2100)))
        t += datetime.timedelta(minutes=15)
pool = ["%06x" % (0x380000 + i * 37) for i in range(12000)]
for i in range(9):                     # the day files: about 1 900 aircraft a day, a third of them seen again the next
    day = (now - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
    with open(os.path.join(d, "seen-" + day), "w") as f:
        f.write("\\n".join(pool[i * 1200:i * 1200 + (900 if i == 0 else 1900)]) + "\\n")
with open(os.path.join(d, "farthest-2026-10-29"), "w") as f:
    json.dump({"km": 402.6, "time": "15:42", "hex": "4ca7b5", "flight": "RYR8526", "flight_iata": "FR8526", "airline": "Ryanair",
               "registration": "EI-DCL", "type_name": "Boeing 737-800", "alt_ft": 37000,
               "route": {"from": {"city": "Charleroi", "iata": "CRL"}, "to": {"city": "Reggio Calabria", "iata": "REG"}},
               "near": {"name": "Lyon", "country": "FR", "km": 12}}, f)
print(json.dumps({r: server.read_stats(d, now, r) for r in ("24h", "7d", "30d")}))
`, tmp], { cwd: path.join(ROOT, "flightinfo") }).toString());
// the fleet, made up: long names and big counts, where a page is cut first
const FLEET = {
  aircraft: 2148,
  airlines: [["Ryanair", 214], ["easyJet", 131], ["Lufthansa", 96], ["Air France", 88], ["Wizz Air", 61], ["KLM Royal Dutch Airlines", 44], ["Turkish Airlines", 38], ["British Airways", 31]],
  airline_cc: { "Ryanair": "IE", "easyJet": "GB", "Lufthansa": "DE", "Air France": "FR", "Wizz Air": "HU", "KLM Royal Dutch Airlines": "NL", "Turkish Airlines": "TR", "British Airways": "GB", "DHL Air": "GB", "FedEx Express": "US", "ASL Airlines Belgium": "BE" },
  types: [["Airbus A320neo", 260], ["Boeing 737-800", 231], ["Airbus A321neo", 140], ["Airbus A319", 77], ["Embraer E190", 41], ["Boeing 787-9 Dreamliner", 22]],
  cargo: [["DHL Air", 18], ["FedEx Express", 9], ["ASL Airlines Belgium", 7]], cargo_total: 34,
  cargo_models: { "DHL Air": ["Boeing 757-200PCF", 11], "FedEx Express": ["Boeing 777F", 6], "ASL Airlines Belgium": ["Boeing 737-400SF", 5] },
  bizjets: [["Cessna 560XL Citation Excel", 12], ["Dassault Falcon 2000LX", 7], ["Bombardier Global 6000", 4]], bizjet_total: 23,
  bizjet_countries: [["FR", 9], ["DE", 6], ["CH", 4], ["MT", 4]], bizjet_country_total: 4,
  country_names: { FR: "France", DE: "Germany", CH: "Switzerland", MT: "Malta", US: "United States" },
  military: [{ cc: "FR", country: "France", total: 14, models: [["Airbus A400M Atlas", 6], ["Dassault Rafale", 5], ["Airbus A330 MRTT Phénix", 3]] },
    { cc: "US", country: "United States", total: 9, models: [["Boeing KC-135R Stratotanker", 5], ["Lockheed C-130J Hercules", 4]] },
    { cc: "DE", country: "Germany", total: 4, models: [["Airbus A400M Atlas", 4]] }],
  military_total: 27,
  misc: { heli: { total: 11, rows: [["Airbus H145", "DE", 6], ["Airbus H135", "FR", 5]] }, light: { total: 19, rows: [["Robin DR400", "FR", 9], ["Cessna 172 Skyhawk", "DE", 6]] },
    glider: { total: 3, rows: [["Schleicher ASK 21", "DE", 3]] }, drone: { total: 0, rows: [] }, balloon: { total: 1, rows: [["Cameron Z-105", "FR", 1]] } },
  altitudes: { labels: ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13+"], counts: [40, 61, 52, 47, 58, 66, 73, 88, 120, 197, 284, 410, 236, 18] },
  alt_unit: "km"
};
function statsAnswer(range, patch) {
  const a = Object.assign({}, JSON.parse(JSON.stringify(STATS[range])), { version: "0.99.20", units: "metric", theme: "amber", fleet: FLEET });
  if (patch) patch(a);
  return a;
}

let pass = 0, fail = 0;
async function check(name, fn) {
  try { await fn(); pass++; console.log("ok   " + name); } catch (e) { fail++; console.log("FAIL " + name + "\n     " + (e && e.message || e)); }
}
function file(route, f) {
  // read once and answer 404 on any error (a folder too): no check-then-read race (CodeQL, 0.99.20)
  let body;
  try { body = fs.readFileSync(f); } catch (e) { return route.fulfill({ status: 404, body: "" }); }
  return route.fulfill({ status: 200, contentType: TYPES[path.extname(f)] || "application/octet-stream", body });
}
async function statsPage(browser, width, height, lang, range, patch) {
  const ctx = await browser.newContext({ viewport: { width, height } });
  const page = await ctx.newPage();
  await page.route(BASE + "/**", (route) => {
    const u = new URL(route.request().url()), p = u.pathname;
    const json = (o) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(o) });
    if (p === "/api/config") return json({ lang: "", langs: LANGS });
    if (p === "/api/stats") return json(statsAnswer(u.searchParams.get("range") || "30d", patch));
    if (p === "/stats") return file(route, path.join(STATIC, "stats.html"));
    if (p.indexOf("/static/") === 0) { const f = path.join(STATIC, p.slice(8)); return f.indexOf(STATIC) === 0 ? file(route, f) : route.fulfill({ status: 404, body: "" }); }
    if (p.indexOf("/flags/") === 0) return file(route, path.join(FLAGS, path.basename(p)));
    return route.fulfill({ status: 404, body: "" });
  });
  await page.goto(BASE + "/stats" + (lang && lang !== "en" ? "?lang=" + lang : "") + "#" + (range || "7d"));
  await page.waitForSelector("#dash:not([hidden])");
  await page.waitForFunction(() => document.querySelectorAll("#c-msgs rect.hit").length > 0 && document.querySelectorAll("#c-mil .row").length > 0);
  await page.waitForTimeout(150);
  return { page, ctx };
}
// where the tooltip is, after the pointer is put on an element (its centre, or a point in it given in fractions)
async function tipAt(page, sel, fx, fy, scrolled) {
  if (!scrolled) await page.locator(sel).scrollIntoViewIfNeeded();
  await page.waitForTimeout(150);                           // a scroll before (its event hides the tip) is over
  const box = await page.locator(sel).boundingBox();
  await page.mouse.move(box.x + box.width * (fx === undefined ? 0.5 : fx), box.y + box.height * (fy === undefined ? 0.5 : fy));
  return page.evaluate(() => {
    const t = document.getElementById("tip"), r = t.getBoundingClientRect();
    return { hidden: t.hidden, text: t.textContent, left: r.left, right: r.right, top: r.top, bottom: r.bottom,
      vw: document.documentElement.clientWidth, vh: document.documentElement.clientHeight };
  });
}
function inside(t, what) {
  assert.ok(!t.hidden && t.text, what + ": the tooltip shows (" + JSON.stringify(t) + ")");
  assert.ok(t.left >= 0 && t.right <= t.vw && t.top >= 0 && t.bottom <= t.vh, what + ": the tooltip is inside the screen " + JSON.stringify(t));
}

// ---- graphs1090's page: its stand-in, patched by the real graphs_look_apply
const GROOT = path.join(tmp, "graphs");
function graphsPage() {
  const html = path.join(GROOT, "usr/share/graphs1090/html");
  fs.mkdirSync(html, { recursive: true }); fs.mkdirSync(path.join(GROOT, "etc/default"), { recursive: true });
  fs.mkdirSync(path.join(tmp, "etc"), { recursive: true }); fs.writeFileSync(path.join(tmp, "etc", "config.env"), "");
  fs.writeFileSync(path.join(GROOT, "etc/default/graphs1090"), "colorscheme=default\n");
  const graph = (name) => '<div class="column"><img src="g.svg" alt="' + name + '"></div>';
  fs.writeFileSync(path.join(html, "index.html"), '<!DOCTYPE HTML>\n<html>\n\t<head>\n\t\t<meta charset="utf-8">\n\t\t<title>graphs1090</title>\n' +
    '\t\t<meta name="viewport" content="width=device-width, initial-scale=1.0">\n\t\t<link rel="stylesheet" href="bootstrap.custom.light.css">\n' +
    '\t\t<link rel="stylesheet" href="portal.css">\n\t</head>\n\t<body>\n\t\t<div class="container">\n\t\t\t<h1>Performance Graphs</h1>\n' +
    '\t\t\t<div class="sticky-bar"><div class="btn-group sticky-bar" role="group">' +
    ["2 hours", "8 hours", "24 hours", "48 hours", "7 days", "14 days", "30 days", "3 months", "6 months", "1 year"].map((b, i) =>
      '<button type="button" class="btn btn-default btn-sm' + (i ? "" : " active") + '">' + b + "</button>").join("") + "</div></div>\n" +
    '\t\t\t<div class="panel panel-default"><div class="panel-heading">ADS-B 1090 Graphs</div><div class="panel-body"><div class="row">' +
    graph("Aircraft Seen") + graph("Range") + "</div></div></div>\n" +
    '\t\t\t<div class="panel panel-default"><div class="panel-heading">System Graphs</div><div class="panel-body"><div class="row">' +
    graph("CPU") + graph("Temperature") + "</div></div></div>\n\t\t</div>\n" +
    '\t\t<script src="graphs.js"></script>\n\n\t</body>\n</html>\n');
  // bootstrap's normalize, as far as the page's edges go (body margin 0); graphs1090's portal.css is left out
  fs.writeFileSync(path.join(html, "bootstrap.custom.light.css"), "body { margin: 0; }\n");
  // what graphs1090's graphs.js does to the address as it starts (its switchView, called at once)
  fs.writeFileSync(path.join(html, "graphs.js"), 'window.history.replaceState("object or string", "Title", location.origin + location.pathname + "?timeframe=2h");\n');
  fs.writeFileSync(path.join(html, "g.svg"), '<svg xmlns="http://www.w3.org/2000/svg" width="1097" height="400"><rect width="1097" height="400" fill="#0a0a0a"/><path d="M80 340 L300 200 L520 260 L760 120 L1060 180" stroke="#ffb000" stroke-width="4" fill="none"/></svg>');
  execFileSync("bash", ["-c", ". lib/common.sh; . lib/graphs.sh; graphs_look_apply"], { cwd: ROOT,
    env: Object.assign({}, process.env, { ZB_GRAPHS_ROOT: GROOT, ZENITHBOARD_HOME: ROOT, ZENITHBOARD_ETC: path.join(tmp, "etc"), ZB_SKIP_SERVICES: "1" }) });
  return html;
}
async function openGraphs(browser, html, width, lang) {
  const ctx = await browser.newContext({ viewport: { width, height: 760 } });
  const page = await ctx.newPage();
  await page.route("http://graphs.test:*/**", (route) => {
    const u = new URL(route.request().url()), p = u.pathname;
    if (u.port === "8542") { const f = path.join(html, p === "/" ? "index.html" : p.slice(1)); return f.indexOf(html) === 0 ? file(route, f) : route.fulfill({ status: 404, body: "" }); }
    if (p.indexOf("/flags/") === 0) return file(route, path.join(FLAGS, path.basename(p)));
    if (p.indexOf("/static/") === 0) return file(route, path.join(STATIC, p.slice(8)));
    return route.fulfill({ status: 404, body: "" });
  });
  await page.goto(GRAPHS + "/" + (lang ? "?lang=" + lang : ""));
  await page.waitForSelector(".zb-brand");
  await page.waitForTimeout(200);
  return { page, ctx };
}
function catalogue(lang, part) { return JSON.parse(fs.readFileSync(path.join(STATIC, "i18n", lang, part + ".json"), "utf8")); }
function tr(cat, key) { const v = cat[key]; return typeof v === "string" ? v : v && v.text ? v.text : key; }

(async () => {
  const browser = await chromium.launch();
  try {
    await check("a 360 px phone: the military list has no bar, the page does not scroll sideways", async () => {
      const { page, ctx } = await statsPage(browser, 360, 740, "en");
      const r = await page.evaluate(() => ({
        bars: Array.prototype.map.call(document.querySelectorAll("#c-mil .row .bw"), (b) => getComputedStyle(b).display),
        wide: document.documentElement.scrollWidth }));
      assert.ok(r.bars.length >= 6, "the made-up fleet draws its rows");
      assert.ok(r.bars.every((d) => d === "none"), "every bar is display: none on a phone, got " + r.bars.join(","));
      assert.ok(r.wide <= 360, "the page is " + r.wide + " px wide");
      await ctx.close();
    });

    for (const [w, h] of [[360, 740], [1280, 860]]) {
      await check(w + " px: the tooltip stays inside the screen at a chart's ends and top; a scroll hides it", async () => {
        const { page, ctx } = await statsPage(browser, w, h, "en");
        await page.locator("#c-msgs").scrollIntoViewIfNeeded();
        inside(await tipAt(page, "#c-msgs rect.hit >> nth=0", 0.1), "the first bar");
        inside(await tipAt(page, "#c-msgs rect.hit >> nth=-1", 0.9), "the last bar");
        // (the last point's hit area is half outside its drawing: the pointer goes on its inner half)
        inside(await tipAt(page, "#c-far rect.hit >> nth=-1", 0.4), "the farthest line's last point");
        // the chart at the very top of the screen: no room above the pointer
        await page.evaluate(() => { const r = document.querySelector("#c-planes svg").getBoundingClientRect(); window.scrollBy(0, r.top + 20); });
        await page.waitForTimeout(100);
        await page.mouse.move(0, 0);
        inside(await tipAt(page, "#c-planes rect.hit >> nth=0", 0.1, 0.02, true), "the top of a chart at the top of the screen");
        await page.evaluate(() => window.scrollBy(0, -200));  // a finger's scroll: the tip stays where it was, the chart goes
        await page.waitForTimeout(250);
        assert.ok(await page.evaluate(() => document.getElementById("tip").hidden), "a scroll hides the tooltip");
        await ctx.close();
      });
    }

    for (const w of [768, 900, 1024]) {
      await check(w + " px: every tile's figure fits its tile, in English, Arabic and Finnish (30 days)", async () => {
        for (const lang of ["en", "ar", "fi"]) {
          const { page, ctx } = await statsPage(browser, w, 900, lang, "30d");
          const cut = await page.evaluate(() => Array.prototype.filter.call(document.querySelectorAll(".tile .v"), (v) => v.scrollWidth > v.clientWidth + 1)
            .map((v) => v.textContent + " " + v.scrollWidth + ">" + v.clientWidth));
          assert.deepStrictEqual(cut, [], lang + ": cut figures");
          await ctx.close();
        }
      });
    }

    await check("Arabic: the grey model after a cargo airline keeps its gap from the name", async () => {
      const { page, ctx } = await statsPage(browser, 1280, 860, "ar");
      const g = await page.evaluate(() => {
        const n = document.querySelector("#c-cargo .name"), i = n.querySelector("i"), r = document.createRange();
        r.selectNodeContents(n.firstChild);
        const a = r.getBoundingClientRect(), b = i.getBoundingClientRect();
        return { dir: document.documentElement.dir, nameLeft: a.left, nameRight: a.right, iLeft: b.left, iRight: b.right };
      });
      assert.strictEqual(g.dir, "rtl");
      const gap = g.iLeft >= g.nameRight ? g.iLeft - g.nameRight : g.nameLeft - g.iRight;
      assert.ok(gap >= 6, "a gap of " + gap.toFixed(1) + " px between the name and its model " + JSON.stringify(g));
      await ctx.close();
    });

    // 0.99.21 (review B13): right to left, what is Latin or a number reads in its own order
    await check("Arabic: the busiest hour reads 07:00 and its count in order", async () => {
      const { page, ctx } = await statsPage(browser, 1280, 860, "ar", "7d", (a) => { a.window.totals.busiest_hour = 7; a.window.totals.busiest_messages = 249195; });
      const r = await page.evaluate(() => {
        const n = document.getElementById("t-busiest").firstChild, s = n.nodeValue;
        const x = (sub, from) => { const i = s.indexOf(sub, from || 0), g = document.createRange(); g.setStart(n, i); g.setEnd(n, i + sub.length); return g.getBoundingClientRect().left; };
        const c = s.indexOf("249");
        return { text: s, h: x("07"), m: x("00", s.indexOf("07") + 2), a: x("249", c), b: x("195", c) };
      });
      assert.ok(r.text.includes("07:00"), r.text);
      assert.ok(r.h < r.m, "the hour before its minutes, left to right: " + JSON.stringify(r));
      assert.ok(r.a < r.b, "249 before 195, left to right: " + JSON.stringify(r));
      await ctx.close();
      // the hour the language's way, as its reviewers wrote it (0.53.4): Finnish 07.00, Japanese 07:00台
      for (const [lang, want] of [["fi", "klo 07.00,"], ["ja", "07:00台"], ["fr", "07:00, 249"]]) {
        const p = await statsPage(browser, 1280, 860, lang, "7d", (a) => { a.window.totals.busiest_hour = 7; a.window.totals.busiest_messages = 249195; });
        const txt = await p.page.locator("#t-busiest").textContent();
        assert.ok(txt.includes(want), lang + ": " + txt);
        await p.ctx.close();
      }
    });
    await check("Arabic: the farthest line keeps the day before the time and Lyon, FR (12 km) in order", async () => {
      const { page, ctx } = await statsPage(browser, 1280, 860, "ar", "7d");
      const r = await page.evaluate(() => {
        const n = document.querySelector("#r-period > span").firstChild, s = n.nodeValue;
        // the box of `len` characters of `sub` from its `skip`th (all of it by default)
        const box = (sub, skip, len) => { const i = s.indexOf(sub) + (skip || 0), g = document.createRange(); g.setStart(n, i); g.setEnd(n, i + (len || sub.length - (skip || 0)));
          const b = g.getBoundingClientRect(); return { l: b.left, r: b.right, t: Math.round(b.top) }; };
        return { text: s, day: box("29/10"), time: box("15:42"), lyon: box("Lyon"), twelve: box("(\u206612 km", 2, 2), km: box("(\u206612 km", 5, 2) };
      });
      assert.ok(r.day.l < r.time.l, "29/10 before 15:42: " + JSON.stringify(r));
      assert.ok(r.twelve.l < r.km.l, "12 before km: " + JSON.stringify(r));
      assert.strictEqual(r.lyon.t, r.twelve.t, "Lyon and its distance on one line");
      assert.ok(r.lyon.l > r.km.r, "Lyon, FR first (on the right), then (12 km): " + JSON.stringify(r));
      await ctx.close();
    });
    await check("Arabic, 360 px: a Latin name too long for its list is cut at its end", async () => {
      const { page, ctx } = await statsPage(browser, 360, 740, "ar", "7d");
      const r = await page.evaluate(() => Array.prototype.map.call(document.querySelectorAll("#c-cargo .name, #c-types .name, #c-airlines .name"), (e) => {
        const g = document.createRange(); g.setStart(e.firstChild, 0); g.setEnd(e.firstChild, 1);
        const a = g.getBoundingClientRect(), b = e.getBoundingClientRect();
        return { name: e.firstChild.nodeValue, cut: e.scrollWidth > e.clientWidth, firstIn: a.left >= b.left - 0.5 && a.right <= b.right + 0.5, dir: getComputedStyle(e).direction };
      }));
      assert.ok(r.some((x) => x.cut), "a name is cut at 360 px: " + JSON.stringify(r));
      const bad = r.filter((x) => !x.firstIn);
      assert.deepStrictEqual(bad, [], "a name's first letter is cut away");
      assert.ok(r.every((x) => x.dir === "ltr"), "Latin names run left to right");
      await ctx.close();
    });
    await check("Spanish and Portuguese: the word in dots is the language's own, its accent left out of the dots", async () => {
      for (const [lang, word] of [["es", "ESTADISTICAS"], ["pt-BR", "ESTATISTICAS"]]) {
        const { page, ctx } = await statsPage(browser, 1280, 860, lang, "7d");
        const vb = await page.evaluate(() => document.querySelector("#logo-sub svg").getAttribute("viewBox"));
        assert.strictEqual(vb, "0 0 " + (word.length * 6 + 1) * 5 + " 45", lang + ": " + vb);
        assert.ok(/Í/.test(catalogue(lang, "stats").STATISTICS), lang + ": the catalogue keeps its accent");
        await ctx.close();
      }
    });
    await check("Arabic: the headings in capitals are in the system's font, not a monospace one", async () => {
      for (const lang of ["ar", "en"]) {
        const { page, ctx } = await statsPage(browser, 1280, 860, lang, "7d");
        const f = await page.evaluate(() => [getComputedStyle(document.querySelector("h2")).fontFamily, getComputedStyle(document.querySelector(".tile .k")).fontFamily]);
        for (const x of f) assert.ok(lang === "ar" ? /^system-ui/.test(x) : /^ui-monospace/.test(x), lang + ": " + x);
        await ctx.close();
      }
    });

    const html = graphsPage();
    await check("graphs1090's page: zb-lang.js comes before graphs.js in the patched page", async () => {
      const s = fs.readFileSync(path.join(html, "index.html"), "utf8");
      assert.ok(s.indexOf("zb-lang.js") > 0 && s.indexOf("zb-lang.js") < s.indexOf("graphs.js") && s.indexOf("graphs.js") < s.indexOf("i18n.js"));
    });
    for (const lang of ["fr", "ar"]) {
      await check("graphs1090's page opened with ?lang=" + lang + " is in that language (graphs.js rewrites the address first)", async () => {
        const { page, ctx } = await openGraphs(browser, html, 360, lang);
        const g = await page.evaluate(() => ({ lang: document.documentElement.lang, h1: document.querySelector("h1").textContent,
          search: location.search, dir: document.querySelector(".zb-brand").dir }));
        assert.strictEqual(g.search, "?timeframe=2h", "the stand-in rewrote the address");
        assert.strictEqual(g.lang, lang);
        assert.strictEqual(g.h1, tr(catalogue(lang, "graphs"), "graphs1090 · the receiver, the decoder and the Pi, over time"));
        assert.strictEqual(g.dir, lang === "ar" ? "rtl" : "");
        await ctx.close();
      });
    }
    await check("graphs1090's page in Spanish and Portuguese: GRÁFICOS in dots, without its accent", async () => {
      for (const lang of ["es", "pt-BR"]) {
        const { page, ctx } = await openGraphs(browser, html, 1280, lang);
        const vb = await page.evaluate(() => document.querySelectorAll(".zb-brand svg")[1].getAttribute("viewBox"));
        assert.strictEqual(vb, "0 0 " + (8 * 6 + 1) * 10 + " 90", lang + ": " + vb);
        await ctx.close();
      }
    });
    for (const w of [320, 360]) {
      await check(w + " px: graphs1090's brand fits the screen, GRAPHS keeps its size (English and Arabic)", async () => {
        for (const lang of ["", "ar"]) {
          const { page, ctx } = await openGraphs(browser, html, w, lang);
          const b = await page.evaluate(() => {
            const s = document.querySelectorAll(".zb-brand svg"), a = s[0].getBoundingClientRect(), g = s[1].getBoundingClientRect();
            return { left: a.left, right: a.right, subH: g.height, subRight: g.right, wide: document.documentElement.scrollWidth, vw: document.documentElement.clientWidth };
          });
          assert.ok(b.left >= 15.5 && b.right <= b.vw - 15.5, (lang || "en") + ": the name from " + b.left + " to " + b.right + " in " + b.vw);
          assert.ok(Math.abs(b.subH - 22) < 0.5 && b.subRight <= b.vw, (lang || "en") + ": GRAPHS " + JSON.stringify(b));
          assert.ok(b.wide <= b.vw, (lang || "en") + ": the page is " + b.wide + " px wide");
          await ctx.close();
        }
      });
    }

    if (SHOTS) {
      fs.mkdirSync(SHOTS, { recursive: true });
      for (const lang of ["en", "ar", "fi"]) for (const w of [360, 768, 900, 1024]) {
        const { page, ctx } = await statsPage(browser, w, w < 700 ? 740 : 900, lang, "7d");
        await page.screenshot({ path: path.join(SHOTS, "stats-" + lang + "-" + w + ".png"), fullPage: true });
        await ctx.close();
      }
      { // the tooltip at a phone's edge
        const { page, ctx } = await statsPage(browser, 360, 740, "en", "7d");
        await page.locator("#c-msgs").scrollIntoViewIfNeeded();
        await tipAt(page, "#c-msgs rect.hit >> nth=-1", 0.9);
        await page.screenshot({ path: path.join(SHOTS, "stats-en-360-tip.png") });
        await ctx.close();
      }
      for (const lang of ["", "fr", "ar"]) for (const w of [320, 360]) {
        const { page, ctx } = await openGraphs(browser, html, w, lang);
        await page.screenshot({ path: path.join(SHOTS, "graphs-" + (lang || "en") + "-" + w + ".png") });
        await ctx.close();
      }
      console.log("pictures in " + SHOTS);
    }
  } finally {
    await browser.close();
  }
  console.log(pass + " passed, " + fail + " failed");
  process.exit(fail ? 1 : 0);
})();
