// SPDX-License-Identifier: GPL-3.0-or-later
// ZenithBoard dot-matrix wall: polls the local API, renders aircraft on a canvas dot matrix,
// auto-cycles through the aircraft inside the chosen radius and refreshes itself.
//
// Layout (128 x 80 dots, 16:10):  text on the left | aircraft silhouette (dots) top-right | photo bottom-right.
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

  var canvas = document.getElementById("wall"), ctx = canvas.getContext("2d");
  var server = { units: "metric", theme: "amber", radius: 10, radius_presets: [1, 2, 5, 10, 15, 30, 50], cycle_seconds: 6,
                 show_photos: true };
  var prefs = {};            // local overrides (units, radius, cycle, theme), kept in localStorage
  var planes = [], total = 0, error = null, curHex = null, serverId = null, failures = 0;
  var grid = blank(), lastSig = "", anim = null;
  var box = document.getElementById("photobox"), photoImg = document.getElementById("photo"), photoLink = document.getElementById("photolink");
  var photoCap = document.getElementById("photocap"), sceneCanvas = document.getElementById("scene");
  var scene = new SceneKit.Scene(sceneCanvas), cornerKey = null, photoToken = 0;

  // ------------------------------------------------------------------ preferences
  function loadPrefs() {
    try { prefs = JSON.parse(localStorage.getItem("zenithboard") || "{}") || {}; } catch (e) { prefs = {}; }
    var q = new URLSearchParams(location.search);       // ?units=imperial&radius=5&cycle=8&theme=green
    ["units", "radius", "cycle", "theme"].forEach(function (k) { if (q.has(k)) prefs[k] = q.get(k); });
    savePrefs();
  }
  function savePrefs() { try { localStorage.setItem("zenithboard", JSON.stringify(prefs)); } catch (e) {} }
  function units() { return prefs.units === "imperial" || prefs.units === "metric" ? prefs.units : server.units; }
  function radius() { var r = parseFloat(prefs.radius); return r > 0 ? r : server.radius; }
  function cycleMs() { var c = parseFloat(prefs.cycle); return Math.max(2, c > 0 ? c : server.cycle_seconds) * 1000; }
  function theme() { return prefs.theme || server.theme || "amber"; }
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

  function buildScreen() {
    var g = blank(), u = units();
    if (error) {
      textCenter(g, "NO DATA", 8, 2); textCenter(g, "RECEIVER NOT RESPONDING", 36, 1); textCenter(g, "CHECK THE DECODER", 48, 1);
      return { g: g, sig: "error", plane: null };
    }
    var p = planes.filter(function (x) { return x.hex === curHex; })[0];
    if (!p) {
      textCenter(g, "NO FLIGHTS", 6, 2);
      textCenter(g, "WITHIN " + radius() + (u === "imperial" ? " MI" : " KM"), 28, 1);
      textCenter(g, "SEEN " + total + " AIRCRAFT", 40, 1);
      textCenter(g, clock(), 54, 2);
      return { g: g, sig: "empty" + total + clock() + radius() + u, plane: null };
    }
    var L = Fmt.planeLines(p, u, planes.indexOf(p), planes.length, COLS);
    text(g, L.callsign, 0, 0, 2);
    text(g, L.airline, 0, 16, 1); text(g, L.type, 0, 25, 1);
    text(g, L.alt, 0, 34, 1); text(g, L.spd, 0, 43, 1); text(g, L.from, 0, 52, 1); text(g, L.to, 0, 61, 1);       // where the flight comes from / goes to (blank when unknown)
    text(g, L.footer, 0, 72, 1);
    silhouette(g, p.shape || "generic", SIL_BOX);
    return { g: g, sig: "p" + p.hex + L.callsign + L.footer + L.alt + L.spd + L.from + L.to + (p.photo || ""), plane: p };
  }

  // ------------------------------------------------------------------ rendering
  var dotColor = "#ffb000";
  function themeColor() { return getComputedStyle(document.body).getPropertyValue("--dot").trim() || "#ffb000"; }
  function resize() {
    var dpr = window.devicePixelRatio || 1, w = canvas.clientWidth, h = canvas.clientHeight;
    canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
    dotColor = themeColor();
    draw(grid, null, 1); placeCorner();
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
  function show(screen, wipe) {
    if (screen.sig === lastSig) return;
    lastSig = screen.sig;
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
  }
  function bindPanel() {
    document.getElementById("gear").onclick = function () { fillPanel(); panel.hidden = !panel.hidden; };
    document.getElementById("s-units").onchange = function () { prefs.units = this.value; savePrefs(); fillPanel(); lastSig = ""; poll(); };
    document.getElementById("s-radius").onchange = function () { prefs.radius = this.value; savePrefs(); lastSig = ""; poll(); };
    document.getElementById("s-cycle").onchange = function () { prefs.cycle = this.value; savePrefs(); startCycle(); };
    document.getElementById("s-theme").onchange = function () { prefs.theme = this.value; savePrefs(); applyTheme(); resize(); };
    document.getElementById("s-reset").onclick = function () { prefs = {}; savePrefs(); applyTheme(); fillPanel(); lastSig = ""; startCycle(); poll(); resize(); };
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
