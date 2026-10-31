// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tests/test_poll.js   How the wall talks to the Pi (0.99.17, review B9). The whole of app.js runs here, as the
// browser runs it, against a stand-in page (a canvas that draws nothing), a clock of our own and a fetch of our own:
//   - a Pi that hangs without answering: never more than one request out, each given up after five seconds, and the
//     "NO ANSWER" screen after the third, where before the requests piled up and the wall kept its last aircraft;
//   - a Pi that refuses the name the wall was opened by (403, wall_host_ok): the "WRONG NAME" screen, on the dots
//     and on the split-flap board, never "NO ANSWER", never a reload, no failure counted;
//   - the ALLOW_FROM refusal stays a failure, and /api/config answering an error leaves the wall's defaults.
const assert = require("assert"), fs = require("fs"), path = require("path"), vm = require("vm");
const dir = path.join(__dirname, "..", "flightinfo", "static");
const read = (f) => fs.readFileSync(path.join(dir, f), "utf8");
const font = require(path.join(dir, "font5x7.js"));
const serverPy = fs.readFileSync(path.join(__dirname, "..", "flightinfo", "server.py"), "utf8");

// the server's two refusals, as server.py writes them: the wall tells them apart by the host one naming CONSOLE_HOSTS
const HOST_403 = serverPy.match(/not wall_host_ok[\s\S]*?_send\(403, (b"[\s\S]*?"), "text\/plain"\)/)[1].replace(/"\s*b"/g, "").replace(/^b"|"$/g, "");
const ALLOW_403 = serverPy.match(/_send\(403, b"([^"]*ALLOW_FROM[^"]*)"/)[1];
assert.ok(HOST_403.indexOf("CONSOLE_HOSTS") >= 0, "the host refusal must name CONSOLE_HOSTS: the wall recognises it by that");
assert.ok(ALLOW_403.indexOf("CONSOLE_HOSTS") < 0, "the ALLOW_FROM refusal must not name CONSOLE_HOSTS");

function wall(opts) {
  // ---- a clock of our own: timers run when the test moves time on
  let now = 0, seq = 0, timers = [];
  const addTimer = (fn, ms, every) => { const id = ++seq; timers.push({ id, at: now + Math.max(0, ms || 0), fn, every }); return id; };
  const clearTimer = (id) => { timers = timers.filter((t) => t.id !== id); };
  // ---- the page
  const reloads = [], requests = [];
  const el = () => ({ style: {}, hidden: true, textContent: "", classList: { add() {}, remove() {} }, setAttribute() {},
                      removeAttribute() {}, appendChild() {}, scrollWidth: 0, clientWidth: 0, offsetHeight: 0 });
  const arcs = [];
  const ctx2d = new Proxy({}, { get: (o, k) => (k in o ? o[k] : k === "arc" ? () => { arcs.push(now); } : () => ({ width: 10, addColorStop() {} })),
                                set: (o, k, v) => { o[k] = v; return true; } });
  const els = {};
  const document = {
    getElementById: (id) => els[id] || (els[id] = Object.assign(el(), id === "wall" || id === "scene"
      ? { getContext: () => ctx2d, clientWidth: 1280, clientHeight: 800, width: 1280, height: 800 } : {})),
    addEventListener() {}, hidden: false, body: { setAttribute() {} }, documentElement: {},
  };
  // what the wall wrote: every letter of the dots drawn, and every set of rows given to the split-flap board
  const glyphs = [], flapRows = [];
  const Font5x7 = { W: 5, H: 7, GLYPHS: new Proxy(font.GLYPHS, { get: (g, k) => { glyphs.push(k); return g[k]; } }) };
  function Board() {}
  Board.prototype.setRows = function (lines) { flapRows.push(lines.join("|")); };
  Board.prototype.update = () => false;
  Board.prototype.cell = () => ({ prev: " ", next: " ", phase: 0, flipping: false });
  function Scene() {}
  ["setPlane", "start", "stop", "resize", "render"].forEach((k) => { Scene.prototype[k] = () => {}; });
  const store = {};
  const sandbox = {
    document, console, URLSearchParams, AbortController, Promise, Error, addEventListener() {},
    navigator: {}, performance: { now: () => now },
    location: { search: opts.search || "", reload: () => reloads.push(now) },
    localStorage: { getItem: (k) => store[k] || null, setItem: (k, v) => { store[k] = String(v); } },
    matchMedia: () => ({ matches: true }),
    getComputedStyle: () => ({ getPropertyValue: () => "#ffb000" }),
    Path2D: function () { this.moveTo = () => {}; this.arc = () => {}; },
    requestAnimationFrame: (fn) => addTimer(() => fn(now), 16, 0), cancelAnimationFrame: clearTimer,
    setTimeout: (fn, ms) => addTimer(fn, ms, 0), clearTimeout: clearTimer,
    setInterval: (fn, ms) => addTimer(fn, ms, ms), clearInterval: clearTimer,
    Font5x7, Fmt: require(path.join(dir, "format.js")), Shapes: { rasterize: (n, w, h) => new Uint8Array(w * h) },
    FlapKit: { Board }, SceneKit: { Scene },
    fetch: (url, o) => {
      const req = { url: String(url), at: now, settled: false };
      requests.push(req);
      const answer = opts.answer(req.url, now);
      return new Promise((resolve, reject) => {
        const done = (f) => (v) => { if (!req.settled) { req.settled = true; f(v); } };
        if (o && o.signal) o.signal.addEventListener("abort", () => done(reject)(new Error("AbortError")));
        if (answer) Promise.resolve(answer).then(done(resolve), done(reject));
      });
    },
  };
  sandbox.window = sandbox; sandbox.self = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(read("app.js"), sandbox, { filename: "app.js" });
  const flush = () => new Promise((r) => setImmediate(r));
  return {
    reloads, requests, glyphs, flapRows, arcs,
    drawn: () => glyphs.join(""),
    outstanding: () => requests.filter((r) => !r.settled).length,
    async run(ms, each) {
      const end = now + ms;
      for (let i = 0; i < 5; i++) await flush();
      for (;;) {
        timers.sort((a, b) => a.at - b.at || a.id - b.id);
        const t = timers[0];
        if (!t || t.at > end) break;
        now = t.at;
        if (t.every) t.at += t.every; else timers.shift();
        t.fn();
        for (let i = 0; i < 5; i++) await flush();
        if (each) each(now);
      }
      now = end;
    },
  };
}
const json = (body, status) => ({ status: status || 200, ok: !status || status < 300,
                                  json: () => Promise.resolve(body), text: () => Promise.resolve(JSON.stringify(body)) });
const plain = (text, status) => ({ status, ok: status < 300, text: () => Promise.resolve(text),
                                   json: () => Promise.reject(new SyntaxError("Unexpected token")) });
const CONFIG = { units: "metric", theme: "amber", radius: 10, radius_presets: [5, 10], cycle_seconds: 14, show_photos: true,
                 flags: true, server_id: "s1", version: "test" };
const PLANES = { planes: [], total: 3, server_id: "s1" };

(async () => {
  // ---- a Pi that stops answering, without closing the connection
  {
    let hung = false;
    const w = wall({ answer: (url) => (url.startsWith("/api/config") ? json(CONFIG) : hung ? null : json(PLANES)) });
    await w.run(10000);
    assert.ok(w.drawn().indexOf("NO FLIGHTS") >= 0, "the wall must show the empty sky while the Pi answers");
    assert.strictEqual(w.drawn().indexOf("NO ANSWER"), -1);
    hung = true; const from = w.requests.length; let most = 0, offlineAt = -1;
    w.glyphs.length = 0;
    await w.run(60000, (t) => {
      most = Math.max(most, w.outstanding());
      if (offlineAt < 0 && w.drawn().indexOf("NO ANSWER") >= 0) offlineAt = t;
    });
    const sent = w.requests.slice(from).filter((r) => r.url.startsWith("/api/planes"));
    assert.ok(most <= 1, "a hung Pi must never have more than one request out at a time (" + most + " were)");
    assert.ok(sent.length >= 6 && sent.length <= 13, "one request every five to seven seconds while the Pi hangs (" + sent.length + " in a minute)");
    assert.ok(offlineAt > 0, "a Pi that hangs must bring the NO ANSWER screen, as one that refuses the connection does");
    assert.ok(offlineAt - 10000 >= 15000 && offlineAt - 10000 <= 22000,
              "NO ANSWER after the third request given up, not sooner and not later (" + (offlineAt - 10000) + " ms)");
    assert.strictEqual(w.reloads.length, 0, "no reload while the Pi does not answer");
  }

  // ---- the wall opened by a name the Pi refuses: the dots
  for (const mode of ["dots", "flap"]) {
    const w = wall({ search: "?mode=" + mode,
                     answer: (url) => (url.startsWith("/api/config") ? json(CONFIG) : plain(HOST_403, 403)) });
    await w.run(200000);
    const planes = w.requests.filter((r) => r.url.startsWith("/api/planes")).length;
    assert.ok(planes >= 90, mode + ": the wall keeps asking, so it recovers once the name is allowed (" + planes + ")");
    assert.strictEqual(w.reloads.length, 0, mode + ": a refused name must never reload the page");
    assert.strictEqual(w.requests.filter((r) => r.url.startsWith("/api/health")).length, 0,
                       mode + ": a refusal is not a lost Pi: no failure counted, so no self-heal either");
    if (mode === "dots") {
      assert.ok(w.drawn().indexOf("WRONG NAME") >= 0, "dots: the WRONG NAME screen must be drawn");
      assert.ok(w.drawn().indexOf("TO CONSOLE_HOSTS") >= 0, "dots: it must say where a name of one's own goes");
      assert.strictEqual(w.drawn().indexOf("NO ANSWER"), -1, "dots: a refusal is not NO ANSWER");
    } else {
      const last = w.flapRows[w.flapRows.length - 1] || "";
      assert.ok(/WRONG NAME/.test(last) && /TO CONSOLE_HOSTS/.test(last), "flap: the WRONG NAME rows must be shown (" + last + ")");
      assert.ok(!w.flapRows.some((r) => /NO ANSWER/.test(r)), "flap: a refusal is not NO ANSWER");
      // the split-flap board draws its dots only for the aircraft's silhouette: the dotted screen's title, drawn
      // for the dot wall, showed its last letters there (0.99.17)
      assert.strictEqual(w.arcs.length, 0, "flap: no dots beside the flaps on a screen without an aircraft");
      w.flapRows.slice(-1)[0].split("|").forEach((r) => assert.ok(r.length <= 16, "flap: '" + r + "' is wider than the board's 16 letters"));
    }
  }

  // ---- once the name is allowed, the wall comes back by itself
  {
    let refused = true;
    const w = wall({ answer: (url) => (url.startsWith("/api/config") ? json(CONFIG) : refused ? plain(HOST_403, 403) : json(PLANES)) });
    await w.run(8000);
    refused = false; w.glyphs.length = 0;
    await w.run(4000);
    assert.ok(w.drawn().indexOf("NO FLIGHTS") >= 0, "the wall must leave WRONG NAME once the Pi answers");
  }

  // ---- the ALLOW_FROM refusal is still counted as a failure (its own advice is not CONSOLE_HOSTS)
  {
    const w = wall({ answer: (url) => (url.startsWith("/api/config") ? json(CONFIG) : plain(ALLOW_403, 403)) });
    await w.run(10000);
    assert.ok(w.drawn().indexOf("NO ANSWER") >= 0, "an ALLOW_FROM refusal must stay a failure");
    assert.strictEqual(w.drawn().indexOf("WRONG NAME"), -1, "an ALLOW_FROM refusal is not a wrong name");
  }

  // ---- /api/config answering an error: the wall keeps its own defaults rather than an error page's fields
  {
    const w = wall({ answer: (url) => (url.startsWith("/api/config") ? json({ error: "busy" }, 500) : json(PLANES)) });
    await w.run(3000);
    const p = w.requests.find((r) => r.url.startsWith("/api/planes"));
    assert.ok(p && /radius_km=10\.000$/.test(p.url), "an error from /api/config must leave the default radius (" + (p && p.url) + ")");
  }

  // ---- every screen fits the wall: 21 letters a row at size 1, 10 at size 2 (6 dots a letter, 128 dots)
  const app = read("app.js");
  for (const m of app.matchAll(/textCenter\(g, "([^"]+)", \d+, (\d)\)/g)) {
    const width = (m[1].length * 6 - 1) * Number(m[2]);
    assert.ok(width <= 128, "'" + m[1] + "' is " + width + " dots wide, the wall 128");
    for (const ch of m[1]) assert.ok(font.GLYPHS[ch.toUpperCase()], "'" + ch + "' of '" + m[1] + "' has no letter in font5x7.js");
  }
  const flapChars = require(path.join(dir, "flap.js")).CHARS;
  for (const m of app.matchAll(/centered\("([^"]+)"\)/g)) {
    assert.ok(m[1].length <= 16, "'" + m[1] + "' is wider than the split-flap board");
    for (const ch of m[1]) assert.ok(flapChars.indexOf(ch) >= 0, "'" + ch + "' of '" + m[1] + "' has no flap");
  }

  console.log("poll ok: a hung Pi -> one request at a time, NO ANSWER after three given up; a refused name -> WRONG NAME, no reload");
})().catch((e) => { console.error(e); process.exit(1); });
