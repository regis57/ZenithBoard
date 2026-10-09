// SPDX-License-Identifier: GPL-3.0-or-later
// ZenithBoard dot-matrix wall: polls the local API, renders aircraft on a canvas dot matrix,
// auto-cycles through the aircraft inside the chosen radius and refreshes itself.
//
// Layout (128 x 80 dots, 16:10):  text on the left | aircraft silhouette (dots) top-right | photo right, above the settings gear (bottom-right corner).
// The photo corner is a real picture (Planespotters) with credit; without a photo it shows an animated sky scene
// with a side view of the matching aircraft model (see scene.js).
(function () {
  "use strict";
  var COLS = 14;                                   // characters per text row on the left
  var GW = 128, GH = 80;
  var RX = 90, RW = 38;                            // right-hand column
  var SIL_BOX = { x: RX, y: 0, w: RW, h: 34 };
  var PHOTO_BOX = { x: 86, y: 38, w: 42, h: 30 };  // 7:5, like the 3:2 Planespotters thumbnails
  var ON = 1;                                      // grid value: 1 = lit in the theme colour
  var FLAP_COLS = 16, FLAP_ROWS = 8, FLAP_W = 84;  // split-flap style: 16 letters x 8 rows on the left 84 dots (the photo keeps the right-hand column)

  var canvas = document.getElementById("wall"), ctx = canvas.getContext("2d");
  var server = { units: "metric", theme: "amber", radius: 10, radius_presets: [1, 2, 5, 10, 15, 30, 50], cycle_seconds: 6,
                 show_photos: true };
  var prefs = {};            // local overrides (units, radius, cycle, theme), kept in localStorage
  var planes = [], total = 0, error = null, curHex = null, serverId = null, failures = 0;
  var grid = blank(), lastSig = "", anim = null;
  var box = document.getElementById("photobox"), photoImg = document.getElementById("photo"), photoLink = document.getElementById("photolink");
  var photoCap = document.getElementById("photocap"), sceneCanvas = document.getElementById("scene");
  var scene = new SceneKit.Scene(sceneCanvas), cornerKey = null, photoToken = 0;
  var board = new FlapKit.Board(FLAP_COLS, FLAP_ROWS), flapRaf = 0, flapSil = null, flapTimer = 0;
  var reduceMotion = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);

  // ------------------------------------------------------------------ preferences
  function loadPrefs() {
    try { prefs = JSON.parse(localStorage.getItem("zenithboard") || "{}") || {}; } catch (e) { prefs = {}; }
    var q = new URLSearchParams(location.search);       // ?units=imperial&radius=5&cycle=8&theme=green&mode=flap
    ["units", "radius", "cycle", "theme", "mode"].forEach(function (k) { if (q.has(k)) prefs[k] = q.get(k); });
    savePrefs();
  }
  function savePrefs() { try { localStorage.setItem("zenithboard", JSON.stringify(prefs)); } catch (e) {} }
  function units() { return prefs.units === "imperial" || prefs.units === "metric" ? prefs.units : server.units; }
  function radius() { var r = parseFloat(prefs.radius); return r > 0 ? r : server.radius; }
  function cycleMs() { var c = parseFloat(prefs.cycle); return Math.max(2, c > 0 ? c : server.cycle_seconds) * 1000; }
  function theme() { return prefs.theme || server.theme || "amber"; }
  function mode() { return prefs.mode === "flap" || prefs.mode === "dots" ? prefs.mode : (server.display_mode === "flap" ? "flap" : "dots"); }
  function applyTheme() { document.body.setAttribute("data-theme", theme()); }

  // ------------------------------------------------------------------ dot grid
  function blank() { return new Uint32Array(GW * GH); }
  function put(g, x, y, v) { if (x >= 0 && x < GW && y >= 0 && y < GH) g[y * GW + x] = v; }
  function text(g, s, x, y, scale) {
    s = String(s).toUpperCase();
    for (var i = 0; i < s.length; i++) {
      var gl = Font5x7.GLYPHS[s[i]] || Font5x7.GLYPHS["?"];
      for (var r = 0; r < 7; r++) for (var c = 0; c < 5; c++) {
        if (gl[r][c] !== "#") continue;
        for (var dy = 0; dy < scale; dy++) for (var dx = 0; dx < scale; dx++) put(g, x + (i * 6 + c) * scale + dx, y + r * scale + dy, ON);
      }
    }
  }
  function textCenter(g, s, y, scale) { s = String(s); text(g, s, Math.round((GW - (s.length * 6 - 1) * scale) / 2), y, scale); }
  function silhouette(g, name, area) {              // theme-coloured aircraft shape (top view)
    var s = 32, m = Shapes.rasterize(name, s, s), ox = area.x + Math.floor((area.w - s) / 2), oy = area.y + Math.floor((area.h - s) / 2);
    for (var y = 0; y < s; y++) for (var x = 0; x < s; x++) if (m[y * s + x]) put(g, ox + x, oy + y, ON);
  }

  function clock() { var d = new Date(); return ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2); }

  // ------------------------------------------------------------------ photo corner (real photo, or animated scene)
  function geom() {                                  // dot-grid geometry in CSS pixels (same maths as draw())
    var cw = canvas.clientWidth, ch = canvas.clientHeight, pitch = Math.min(cw / (GW + 3), ch / (GH + 3));
    return { pitch: pitch, ox: (cw - pitch * GW) / 2, oy: (ch - pitch * GH) / 2 };
  }
  // The animated scene fills the whole corner; a real photo is shown COMPLETE (never cropped): it keeps its own
  // proportions, is as large as the corner allows, sits in the bottom-right and carries its credit underneath.
  function fitPhoto(g) {
    var W = PHOTO_BOX.w * g.pitch, H = PHOTO_BOX.h * g.pitch, fs = Math.max(8, g.pitch * 1.5);
    var iw = photoImg.naturalWidth, ih = photoImg.naturalHeight, ratio = iw && ih ? iw / ih : 1.5;
    var imgH = Math.max(10, H - fs * 1.6), w = Math.min(W, imgH * ratio);
    box.style.fontSize = fs + "px";
    box.style.left = "auto"; box.style.top = "auto"; box.style.height = "auto"; box.style.width = w + "px";
    box.style.right = (canvas.clientWidth - (g.ox + (PHOTO_BOX.x + PHOTO_BOX.w) * g.pitch)) + "px";
    box.style.bottom = (canvas.clientHeight - (g.oy + (PHOTO_BOX.y + PHOTO_BOX.h) * g.pitch)) + "px";
  }
  function placeCorner() {
    var g = geom(), el = sceneCanvas;
    el.style.left = (g.ox + PHOTO_BOX.x * g.pitch) + "px"; el.style.top = (g.oy + PHOTO_BOX.y * g.pitch) + "px";
    el.style.width = (PHOTO_BOX.w * g.pitch) + "px"; el.style.height = (PHOTO_BOX.h * g.pitch) + "px";
    fitPhoto(g);
    scene.resize(); if (!sceneCanvas.hidden && scene.ops) scene.render(performance.now());
  }
  function hideCorner() { cornerKey = null; photoToken++; box.hidden = true; sceneCanvas.hidden = true; scene.stop(); }
  function showScene() { box.hidden = true; sceneCanvas.hidden = false; placeCorner(); scene.start(); }   // size it only once it is visible
  function showPhoto(p) {
    scene.stop(); sceneCanvas.hidden = true; box.hidden = false; fitPhoto(geom());
    photoCap.textContent = p.photo_credit ? "\u00a9 " + p.photo_credit + (p.photo_link ? " \u00b7 planespotters.net" : "") : "";
    if (p.photo_link) { photoLink.href = p.photo_link; photoLink.setAttribute("target", "_blank"); } else photoLink.removeAttribute("href");
  }
  function updateCorner(p) {
    var key = p ? p.hex + "|" + (p.photo || "") : "";
    if (key === cornerKey) return;
    if (!p) { hideCorner(); return; }
    cornerKey = key; var token = ++photoToken;
    scene.setPlane(p); showScene();                // the scene is shown at once; a real photo replaces it when it has loaded
    if (p.photo && server.show_photos) {
      photoImg.onload = function () { if (token === photoToken) showPhoto(p); };
      photoImg.onerror = function () { if (token === photoToken) showScene(); };
      photoImg.src = p.photo;
    }
  }

  function centered(str) { str = String(str); var n = Math.max(0, Math.floor((FLAP_COLS - str.length) / 2)); return new Array(n + 1).join(" ") + str; }
  function buildScreen() {
    var g = blank(), u = units();
    if (error) {
      textCenter(g, "NO DATA", 8, 2); textCenter(g, "RECEIVER NOT RESPONDING", 36, 1); textCenter(g, "CHECK THE DECODER", 48, 1);
      return { g: g, sig: "error", plane: null, lines: ["", centered("NO DATA"), "", centered("RECEIVER NOT"), centered("RESPONDING"), "", centered("CHECK THE"), centered("DECODER")] };
    }
    var p = planes.filter(function (x) { return x.hex === curHex; })[0];
    if (!p) {
      textCenter(g, "NO FLIGHTS", 6, 2);
      textCenter(g, "WITHIN " + radius() + (u === "imperial" ? " MI" : " KM"), 28, 1);
      textCenter(g, "SEEN " + total + " AIRCRAFT", 40, 1);
      textCenter(g, clock(), 54, 2);
      var within = "WITHIN " + radius() + (u === "imperial" ? " MI" : " KM");
      return { g: g, sig: "empty" + total + clock() + radius() + u, plane: null,
               lines: ["", centered("NO FLIGHTS"), "", centered(within), centered("SEEN " + total + " AIRCRAFT"), "", centered(clock()), ""] };
    }
    var L = Fmt.planeLines(p, u, planes.indexOf(p), planes.length, COLS);
    text(g, L.callsign, 0, 0, 2);
    text(g, L.airline, 0, 16, 1); text(g, L.type, 0, 25, 1);
    text(g, L.alt, 0, 34, 1); text(g, L.spd, 0, 43, 1); text(g, L.from, 0, 52, 1); text(g, L.to, 0, 61, 1);       // where the flight comes from / goes to (blank when unknown)
    text(g, L.footer, 0, 72, 1);
    silhouette(g, p.shape || "generic", SIL_BOX);
    return { g: g, sig: "p" + p.hex + L.callsign + L.footer + L.alt + L.spd + L.type + L.from + L.to + (p.photo || ""), plane: p,
             lines: [L.callsign, L.airline, L.type, L.alt, L.spd, L.from, L.to, L.footer] };
  }

  // ------------------------------------------------------------------ rendering
  var dotColor = "#ffb000";
  function themeColor() { return getComputedStyle(document.body).getPropertyValue("--dot").trim() || "#ffb000"; }
  function resize() {
    var dpr = window.devicePixelRatio || 1, w = canvas.clientWidth, h = canvas.clientHeight;
    canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
    dotColor = themeColor();
    if (mode() === "flap") renderFlap(performance.now()); else draw(grid, null, 1);
    placeCorner();
  }
  function hex6(v) { return "#" + ("000000" + (v & 0xffffff).toString(16)).slice(-6); }
  function draw(a, b, progress) {
    var W = canvas.width, H = canvas.height, pitch = Math.min(W / (GW + 3), H / (GH + 3));
    var ox = (W - pitch * GW) / 2, oy = (H - pitch * GH) / 2, r = pitch * 0.42;
    ctx.clearRect(0, 0, W, H);
    var off = new Path2D(), lit = {}, cut = b ? Math.floor(progress * (GW + 6)) : GW + 6;
    for (var y = 0; y < GH; y++) for (var x = 0; x < GW; x++) {
      var v = (b && x < cut) ? b[y * GW + x] : a[y * GW + x];
      var cx = ox + (x + 0.5) * pitch, cy = oy + (y + 0.5) * pitch, path;
      if (!v) path = off; else { var k = v === ON ? "t" : hex6(v); path = lit[k] || (lit[k] = new Path2D()); }
      path.moveTo(cx + r, cy); path.arc(cx, cy, r, 0, 6.2832);
    }
    ctx.shadowBlur = 0; ctx.globalAlpha = 0.09; ctx.fillStyle = dotColor; ctx.fill(off);
    ctx.globalAlpha = 1; ctx.shadowBlur = pitch * 1.2;
    Object.keys(lit).forEach(function (k) { var col = k === "t" ? dotColor : k; ctx.fillStyle = col; ctx.shadowColor = col; ctx.fill(lit[k]); });
    ctx.shadowBlur = 0;
  }
  // ------------------------------------------------------------------ split-flap style (?mode=flap)
  function flapGeom() {
    var g = geom(), cw = FLAP_W * g.pitch / FLAP_COLS, ch = GH * g.pitch / FLAP_ROWS;
    var f = { ox: g.ox, oy: g.oy, cw: cw, ch: ch, pitch: g.pitch, pad: Math.max(1, cw * 0.06) };
    f.font = "bold " + Math.round(ch * 0.66) + "px 'Arial Narrow','Roboto Condensed','DejaVu Sans Condensed',Arial,sans-serif";
    ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.font = f.font; var wide = ctx.measureText("W").width / (canvas.width / canvas.clientWidth); ctx.restore();
    f.sx = Math.min(1, (cw - 2 * f.pad) * 0.9 / Math.max(1, wide));          // squeeze wide fonts so every letter fits its flap
    return f;
  }
  function flapHalf(f, x, y, ch, top, scale, shade) {            // one half of a flap, optionally folded towards the hinge
    var dpr = canvas.width / canvas.clientWidth, w = f.cw - 2 * f.pad, h = f.ch - 2 * f.pad, hx = x + f.pad, hy = y + f.pad, mid = hy + h / 2;
    ctx.save(); ctx.translate(0, mid); ctx.scale(1, Math.max(0.001, scale)); ctx.translate(0, -mid);
    ctx.beginPath(); ctx.rect(hx, top ? hy : mid, w, h / 2); ctx.clip();
    var gr = ctx.createLinearGradient(0, hy, 0, hy + h); gr.addColorStop(0, "#202020"); gr.addColorStop(0.5, "#151515"); gr.addColorStop(0.5, "#121212"); gr.addColorStop(1, "#0b0b0b");
    ctx.fillStyle = gr; ctx.fillRect(hx, hy, w, h);
    if (ch !== " ") {
      ctx.fillStyle = dotColor; ctx.font = f.font; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.translate(hx + w / 2, 0); ctx.scale(f.sx, 1); ctx.fillText(ch, 0, hy + h * 0.53);
    }
    if (shade) { ctx.fillStyle = "rgba(0,0,0," + shade + ")"; ctx.fillRect(hx, hy, w, h); }
    ctx.restore(); void dpr;
  }
  function renderFlap(now) {
    var f = flapGeom(), W = canvas.width, H = canvas.height, dpr = W / canvas.clientWidth;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
    ctx.shadowBlur = 0; ctx.globalAlpha = 1;
    for (var r = 0; r < FLAP_ROWS; r++) for (var c = 0; c < FLAP_COLS; c++) {
      var st = board.cell(r, c, now), x = f.ox + c * f.cw, y = f.oy + r * f.ch, hy = y + f.pad, h = f.ch - 2 * f.pad;
      if (!st.flipping) { flapHalf(f, x, y, st.prev, true, 1); flapHalf(f, x, y, st.prev, false, 1); }
      else {
        flapHalf(f, x, y, st.next, true, 1); flapHalf(f, x, y, st.prev, false, 1);              // what is revealed / what is left
        var a = st.phase * Math.PI;
        if (st.phase < 0.5) flapHalf(f, x, y, st.prev, true, Math.cos(a), 0.15 + 0.4 * st.phase);   // the top flap falls
        else flapHalf(f, x, y, st.next, false, -Math.cos(a), 0.4 * (1 - st.phase));                // and lands as the bottom flap of the new letter
      }
      ctx.fillStyle = "#000"; ctx.fillRect(x + f.pad, hy + h / 2 - 0.75, f.cw - 2 * f.pad, 1.5);  // the hinge
    }
    if (flapSil) {                                            // the aircraft pictogram stays dotted, top right
      var rr = f.pitch * 0.42; ctx.fillStyle = dotColor; ctx.shadowColor = dotColor; ctx.shadowBlur = f.pitch * 1.2; ctx.beginPath();
      for (var y2 = SIL_BOX.y; y2 < SIL_BOX.y + SIL_BOX.h; y2++) for (var x2 = SIL_BOX.x; x2 < SIL_BOX.x + SIL_BOX.w; x2++) if (flapSil[y2 * GW + x2]) {
        var cx = f.ox + (x2 + 0.5) * f.pitch, cy = f.oy + (y2 + 0.5) * f.pitch; ctx.moveTo(cx + rr, cy); ctx.arc(cx, cy, rr, 0, 6.2832);
      }
      ctx.fill(); ctx.shadowBlur = 0;
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
  }
  function flapLoop(now) {
    flapRaf = 0;
    var busy = board.update(now); renderFlap(now);
    if (busy) flapRaf = requestAnimationFrame(flapLoop);
  }
  function flapKick() { if (!flapRaf) flapRaf = requestAnimationFrame(flapLoop); }
  function flapStop() { if (flapRaf) cancelAnimationFrame(flapRaf); flapRaf = 0; clearTimeout(flapTimer); }
  function showFlap(screen, wipe) {
    if (anim) { cancelAnimationFrame(anim); anim = null; }
    flapSil = screen.g;
    var changed = wipe || !screen.plane || !cornerKey || cornerKey.indexOf(screen.plane.hex) !== 0;
    if (changed) hideCorner();
    board.setRows(screen.lines, performance.now(), reduceMotion || firstFlap);
    firstFlap = false;
    flapKick();
    clearTimeout(flapTimer);
    flapTimer = setTimeout(function () { updateCorner(screen.plane); }, changed && !reduceMotion ? 1400 : 0);   // the photo comes back once the letters have settled
  }
  var firstFlap = true;
  function applyMode() {                                      // switching style on a running wall
    flapStop(); lastSig = ""; grid = blank(); hideCorner(); firstFlap = true;
    ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (mode() === "flap") { board = new FlapKit.Board(FLAP_COLS, FLAP_ROWS); }
    resize(); poll();
  }

  function show(screen, wipe) {
    if (screen.sig === lastSig) return;
    lastSig = screen.sig;
    if (mode() === "flap") { showFlap(screen, wipe); return; }
    if (!wipe) {
      if (anim) { cancelAnimationFrame(anim); anim = null; }      // a late update must not be overwritten by a running wipe
      grid = screen.g; draw(grid, null, 1); updateCorner(screen.plane); return;
    }
    var from = grid, to = screen.g, t0 = performance.now();
    if (anim) cancelAnimationFrame(anim);
    hideCorner();                                                 // photo/scene reappear once the new dots are in place
    (function step(now) {
      var k = Math.min(1, (now - t0) / 450);
      anim = k < 1 ? requestAnimationFrame(step) : null;
      if (k >= 1) { grid = to; updateCorner(screen.plane); }
      draw(from, to, k);
    })(t0);
  }

  // ------------------------------------------------------------------ data + cycling
  function ensureCurrent() {
    if (!planes.length) { curHex = null; return false; }
    if (!planes.some(function (p) { return p.hex === curHex; })) { curHex = planes[0].hex; return true; }
    return false;
  }
  function advance() {
    if (planes.length > 1) {
      var i = 0; planes.forEach(function (p, n) { if (p.hex === curHex) i = n; });
      curHex = planes[(i + 1) % planes.length].hex;
    } else ensureCurrent();
    show(buildScreen(), true);
  }
  function poll() {
    var url = "/api/planes?radius_km=" + Fmt.radiusToKm(radius(), units()).toFixed(3);
    fetch(url, { cache: "no-store" }).then(function (r) { return r.json(); }).then(function (d) {
      failures = 0;
      if (serverId && d.server_id && d.server_id !== serverId) { location.reload(); return; }   // server restarted/upgraded
      serverId = d.server_id || serverId;
      error = d.error ? d.error : null; planes = d.planes || []; total = d.total || 0;
      var switched = ensureCurrent();
      show(buildScreen(), switched);
    }).catch(function () {
      if (++failures === 3) { error = "offline"; show(buildScreen(), false); }
      if (failures >= 30 && failures % 30 === 0) location.reload();                            // self-heal
    });
  }
  function loadServerConfig() {
    return fetch("/api/config", { cache: "no-store" }).then(function (r) { return r.json(); })
      .then(function (c) { server = c; serverId = c.server_id; }).catch(function () {});
  }

  // ------------------------------------------------------------------ settings panel
  var panel = document.getElementById("settings");
  function fillPanel() {
    var rs = document.getElementById("s-radius"), u = units();
    rs.innerHTML = "";
    server.radius_presets.forEach(function (v) {
      var o = document.createElement("option"); o.value = v; o.textContent = v + (u === "imperial" ? " mi" : " km");
      if (v === radius()) o.selected = true; rs.appendChild(o);
    });
    document.getElementById("s-units").value = u;
    document.getElementById("s-cycle").value = cycleMs() / 1000;
    document.getElementById("s-theme").value = theme();
    document.getElementById("s-mode").value = mode();
  }
  function bindPanel() {
    document.getElementById("gear").onclick = function () { fillPanel(); panel.hidden = !panel.hidden; };
    document.getElementById("s-units").onchange = function () { prefs.units = this.value; savePrefs(); fillPanel(); lastSig = ""; poll(); };
    document.getElementById("s-radius").onchange = function () { prefs.radius = this.value; savePrefs(); lastSig = ""; poll(); };
    document.getElementById("s-cycle").onchange = function () { prefs.cycle = this.value; savePrefs(); startCycle(); };
    document.getElementById("s-theme").onchange = function () { prefs.theme = this.value; savePrefs(); applyTheme(); resize(); };
    document.getElementById("s-mode").onchange = function () { prefs.mode = this.value; savePrefs(); applyMode(); };
    document.getElementById("s-reset").onclick = function () { var m = mode(); prefs = {}; savePrefs(); applyTheme(); fillPanel(); startCycle(); if (mode() !== m) applyMode(); else { lastSig = ""; poll(); resize(); } };
    document.getElementById("s-full").onclick = function () {
      var el = document.documentElement; (el.requestFullscreen || el.webkitRequestFullscreen || function () {}).call(el); keepAwake();
    };
    document.getElementById("s-close").onclick = function () { panel.hidden = true; };
  }
  var wake = null;
  function keepAwake() { try { if (navigator.wakeLock) navigator.wakeLock.request("screen").then(function (l) { wake = l; }).catch(function () {}); } catch (e) {} }
  document.addEventListener("visibilitychange", function () { if (!document.hidden) keepAwake(); });

  var cycleTimer = null;
  function startCycle() { clearInterval(cycleTimer); cycleTimer = setInterval(advance, cycleMs()); }

  // ------------------------------------------------------------------ boot
  loadPrefs();
  loadServerConfig().then(function () {
    applyTheme(); bindPanel(); resize(); poll(); startCycle(); setInterval(poll, 2000); keepAwake();
  });
  window.addEventListener("resize", resize);
})();
