// SPDX-License-Identifier: GPL-3.0-or-later
// ZenithBoard dot-matrix wall: polls the local API, renders aircraft on a canvas dot matrix,
// auto-cycles through the aircraft inside the chosen radius and refreshes itself.
//
// Layout (128 x 80 dots, 16:10):  text on the left | logo (or aircraft silhouette) top-right | photo bottom-right
(function () {
  "use strict";
  var COLS = 14;                                   // characters per text row on the left
  var GW = 128, GH = 80;
  var RX = 90, RW = 38;                            // right-hand column
  var LOGO_BOX = { x: RX, y: 0, w: RW, h: 34 };
  var PHOTO_BOX = { x: RX, y: 38, w: RW, h: 32 };
  var ON = 1;                                      // grid value: 1 = theme colour, otherwise 0x1000000 | rgb (logo colours)

  var canvas = document.getElementById("wall"), ctx = canvas.getContext("2d");
  var server = { units: "metric", theme: "amber", radius: 10, radius_presets: [1, 2, 5, 10, 15, 30, 50], cycle_seconds: 6,
                 show_photos: true, show_logos: true };
  var prefs = {};            // local overrides (units, radius, cycle, theme), kept in localStorage
  var planes = [], total = 0, error = null, curHex = null, serverId = null, failures = 0;
  var grid = blank(), lastSig = "", anim = null, curPhotoUrl = null;
  var logos = {}, photos = {};                     // caches: icao -> bitmap | null ; url -> {img, ok}

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
  function textRight(g, s, y, scale) { s = String(s); text(g, s, GW - (s.length * 6 - 1) * scale, y, scale); }
  function textCenter(g, s, y, scale) { s = String(s); text(g, s, Math.round((GW - (s.length * 6 - 1) * scale) / 2), y, scale); }
  function bitmap(g, bmp, box) {                    // coloured logo, centred in its box
    var ox = box.x + Math.floor((box.w - bmp.w) / 2), oy = box.y + Math.floor((box.h - bmp.h) / 2);
    bmp.cells.forEach(function (c) { put(g, ox + c.x, oy + c.y, 0x1000000 | c.color); });
  }
  function silhouette(g, name, box) {               // theme-coloured aircraft shape
    var s = 32, m = Shapes.rasterize(name, s, s), ox = box.x + Math.floor((box.w - s) / 2), oy = box.y + Math.floor((box.h - s) / 2);
    for (var y = 0; y < s; y++) for (var x = 0; x < s; x++) if (m[y * s + x]) put(g, ox + x, oy + y, ON);
  }

  function clock() { var d = new Date(); return ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2); }
  function radiusText() { return Fmt.radiusLabel(radius(), units()); }

  // ------------------------------------------------------------------ logos + photos (lazy, cached)
  function getLogo(icao) {
    if (!icao || !server.show_logos) return null;
    if (logos.hasOwnProperty(icao)) return logos[icao];
    logos[icao] = null;                               // pending / not found -> silhouette is shown meanwhile
    fetch("/api/logo/" + icao, { cache: "no-store" }).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      if (j && j.rows) { logos[icao] = Shapes.decodeLogo(j); lastSig = ""; show(buildScreen(), false); }
    }).catch(function () {});
    return null;
  }
  function getPhoto(url) {
    if (!url || !server.show_photos) return null;
    var e = photos[url];
    if (!e) {
      e = photos[url] = { img: new Image(), ok: false };
      e.img.onload = function () { e.ok = true; if (curPhotoUrl === url && !anim) draw(grid, null, 1); };
      e.img.src = url;
    }
    return e.ok ? e.img : null;
  }

  function buildScreen() {
    var g = blank(), u = units();
    curPhotoUrl = null;
    if (error) {
      textCenter(g, "NO DATA", 8, 2); textCenter(g, "RECEIVER NOT RESPONDING", 36, 1); textCenter(g, "CHECK THE DECODER", 48, 1);
      return { g: g, sig: "error" };
    }
    var p = planes.filter(function (x) { return x.hex === curHex; })[0];
    if (!p) {
      textCenter(g, "NO FLIGHTS", 6, 2);
      textCenter(g, "WITHIN " + radius() + (u === "imperial" ? " MI" : " KM"), 28, 1);
      textCenter(g, "SEEN " + total + " AIRCRAFT", 40, 1);
      textCenter(g, clock(), 54, 2);
      return { g: g, sig: "empty" + total + clock() + radius() + u };
    }
    var L = Fmt.planeLines(p, u, planes.indexOf(p), planes.length, radiusText(), COLS);
    text(g, L.callsign, 0, 0, 2);
    text(g, L.airline, 0, 16, 1); text(g, L.type, 0, 25, 1);
    text(g, L.alt, 0, 34, 1); text(g, L.spd, 0, 43, 1); text(g, L.hdg, 0, 52, 1); text(g, L.vs, 0, 61, 1);
    text(g, L.footerLeft, 0, 72, 1); textRight(g, L.footerRight, 72, 1);
    var logo = getLogo(p.airline_icao);
    if (logo) bitmap(g, logo, LOGO_BOX); else silhouette(g, p.shape || "generic", LOGO_BOX);
    curPhotoUrl = p.photo || null;
    var credit = document.getElementById("credit");
    credit.textContent = p.photo && p.photo_credit ? "PHOTO: " + p.photo_credit : ""; 
    return { g: g, sig: "p" + p.hex + L.callsign + L.footerLeft + L.alt + L.spd + L.hdg + L.vs + (logo ? "L" : "S") + (p.photo || "") };
  }

  // ------------------------------------------------------------------ rendering
  var dotColor = "#ffb000", tile = null;
  function themeColor() { return getComputedStyle(document.body).getPropertyValue("--dot").trim() || "#ffb000"; }
  function resize() {
    var dpr = window.devicePixelRatio || 1, w = canvas.clientWidth, h = canvas.clientHeight;
    canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
    dotColor = themeColor();
    draw(grid, null, 1);
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
    if (!b || progress >= 1) drawPhoto(ox, oy, pitch);
  }
  function drawPhoto(ox, oy, pitch) {
    var img = getPhoto(curPhotoUrl);
    if (!img) return;
    var x = ox + PHOTO_BOX.x * pitch, y = oy + PHOTO_BOX.y * pitch, w = PHOTO_BOX.w * pitch, h = PHOTO_BOX.h * pitch;
    var iw = img.naturalWidth, ih = img.naturalHeight, k = Math.min(w / iw, h / ih);   // fit inside the box, keep the whole aircraft visible
    var dw = iw * k, dh = ih * k;
    ctx.save();
    ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip();
    ctx.fillStyle = "#000"; ctx.fillRect(x, y, w, h);
    ctx.drawImage(img, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh);
    // LED "screen door": dark mask with a round hole per dot, so the photo looks like part of the panel
    if (!tile) {
      tile = document.createElement("canvas"); tile.width = tile.height = 16;
      var t = tile.getContext("2d"); t.fillStyle = "rgba(0,0,0,0.78)"; t.fillRect(0, 0, 16, 16);
      t.globalCompositeOperation = "destination-out"; t.beginPath(); t.arc(8, 8, 6.7, 0, 6.2832); t.fill();
    }
    ctx.translate(x, y); ctx.scale(pitch / 16, pitch / 16);
    ctx.fillStyle = ctx.createPattern(tile, "repeat"); ctx.fillRect(0, 0, w * 16 / pitch, h * 16 / pitch);
    ctx.restore();
  }
  function show(screen, wipe) {
    if (screen.sig === lastSig) return;
    lastSig = screen.sig;
    if (!wipe) {
      if (anim) { cancelAnimationFrame(anim); anim = null; }      // a late logo/photo must not be overwritten by a running wipe
      grid = screen.g; draw(grid, null, 1); return;
    }
    var from = grid, to = screen.g, t0 = performance.now();
    if (anim) cancelAnimationFrame(anim);
    (function step(now) {
      var k = Math.min(1, (now - t0) / 450);
      anim = k < 1 ? requestAnimationFrame(step) : null;
      if (k >= 1) grid = to;
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
