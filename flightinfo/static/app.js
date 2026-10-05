// SPDX-License-Identifier: GPL-3.0-or-later
// ZenithBoard dot-matrix wall: polls the local API, renders aircraft on a canvas dot matrix,
// auto-cycles through the aircraft inside the chosen radius and refreshes itself.
(function () {
  "use strict";
  var COLS = 20, GW = COLS * 6 - 1, GH = 69;     // dot grid: 119 x 69
  var canvas = document.getElementById("wall"), ctx = canvas.getContext("2d");
  var server = { units: "metric", radius: 10, radius_presets: [1, 2, 5, 10, 15, 30, 50], cycle_seconds: 6, show_photos: false };
  var prefs = {};            // local overrides (units, radius, cycle, theme), kept in localStorage
  var planes = [], total = 0, error = null, curHex = null, serverId = null, failures = 0;
  var grid = blank(), lastSig = "", anim = null;

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
  function applyTheme() { document.body.setAttribute("data-theme", prefs.theme || "amber"); }

  // ------------------------------------------------------------------ dot grid
  function blank() { return new Uint8Array(GW * GH); }
  function text(g, s, x, y, scale) {
    s = String(s).toUpperCase();
    for (var i = 0; i < s.length; i++) {
      var gl = Font5x7.GLYPHS[s[i]] || Font5x7.GLYPHS["?"];
      for (var r = 0; r < 7; r++) for (var c = 0; c < 5; c++) {
        if (gl[r][c] !== "#") continue;
        for (var dy = 0; dy < scale; dy++) for (var dx = 0; dx < scale; dx++) {
          var px = x + (i * 6 + c) * scale + dx, py = y + r * scale + dy;
          if (px >= 0 && px < GW && py >= 0 && py < GH) g[py * GW + px] = 1;
        }
      }
    }
  }
  function textRight(g, s, y, scale) { s = String(s); text(g, s, GW - (s.length * 6 - 1) * scale, y, scale); }
  function textCenter(g, s, y, scale) { s = String(s); text(g, s, Math.round((GW - (s.length * 6 - 1) * scale) / 2), y, scale); }

  function clock() { var d = new Date(); return ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2); }
  function radiusText() { return Fmt.radiusLabel(radius(), units()); }

  function buildScreen() {
    var g = blank(), u = units();
    if (error) {
      textCenter(g, "NO DATA", 4, 2); textCenter(g, "RECEIVER NOT", 28, 1); textCenter(g, "RESPONDING", 37, 1);
      textCenter(g, "CHECK DECODER", 52, 1); return { g: g, sig: "error" };
    }
    var p = planes.filter(function (x) { return x.hex === curHex; })[0];
    if (!p) {
      textCenter(g, "NO FLIGHTS", 2, 2);
      textCenter(g, "WITHIN " + radius() + (u === "imperial" ? " MI" : " KM"), 22, 1);
      textCenter(g, "SEEN " + total + " AIRCRAFT", 32, 1);
      textCenter(g, clock(), 46, 2);
      return { g: g, sig: "empty" + total + clock() + radius() + u };
    }
    var L = Fmt.planeLines(p, u, planes.indexOf(p), planes.length, radiusText(), COLS);
    text(g, L.callsign, 0, 0, 2);
    textRight(g, L.dist, 0, 1); textRight(g, L.dir, 9, 1);
    text(g, L.type, 0, 17, 1); text(g, L.alt, 0, 26, 1); text(g, L.spd, 0, 35, 1);
    text(g, L.hdg, 0, 44, 1); text(g, L.vs, 0, 53, 1); text(g, L.footer, 0, 62, 1);
    return { g: g, sig: "p" + p.hex + L.dist + L.alt + L.spd + L.hdg + L.vs + L.footer, plane: p };
  }

  // ------------------------------------------------------------------ rendering
  var dotColor = "#ffb000";
  function resize() {
    var dpr = window.devicePixelRatio || 1, w = canvas.clientWidth, h = canvas.clientHeight;
    canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
    dotColor = getComputedStyle(document.body).getPropertyValue("--dot").trim() || dotColor;
    draw(grid, null, 1);
  }
  function draw(a, b, progress) {
    var W = canvas.width, H = canvas.height, pitch = Math.min(W / (GW + 3), H / (GH + 3));
    var ox = (W - pitch * GW) / 2, oy = (H - pitch * GH) / 2, r = pitch * 0.42;
    ctx.clearRect(0, 0, W, H);
    var off = new Path2D(), on = new Path2D(), cut = b ? Math.floor(progress * (GW + 6)) : GW + 6;
    for (var y = 0; y < GH; y++) for (var x = 0; x < GW; x++) {
      var lit = (b && x < cut) ? b[y * GW + x] : a[y * GW + x];
      var cx = ox + (x + 0.5) * pitch, cy = oy + (y + 0.5) * pitch, path = lit ? on : off;
      path.moveTo(cx + r, cy); path.arc(cx, cy, r, 0, 6.2832);
    }
    ctx.shadowBlur = 0; ctx.globalAlpha = 0.09; ctx.fillStyle = dotColor; ctx.fill(off);
    ctx.globalAlpha = 1; ctx.shadowColor = dotColor; ctx.shadowBlur = pitch * 1.2; ctx.fill(on);
    ctx.shadowBlur = 0;
  }
  function show(screen, wipe) {
    if (screen.sig === lastSig) return;
    lastSig = screen.sig;
    updatePhoto(screen.plane);
    if (!wipe) { grid = screen.g; draw(grid, null, 1); return; }
    var from = grid, to = screen.g, t0 = performance.now();
    if (anim) cancelAnimationFrame(anim);
    (function step(now) {
      var k = Math.min(1, (now - t0) / 450);
      draw(from, to, k);
      if (k < 1) anim = requestAnimationFrame(step); else { grid = to; anim = null; }
    })(t0);
  }
  function updatePhoto(p) {
    var img = document.getElementById("photo");
    if (server.show_photos && p && p.photo) { if (img.getAttribute("src") !== p.photo) img.src = p.photo; img.hidden = false; }
    else img.hidden = true;
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
    document.getElementById("s-theme").value = prefs.theme || "amber";
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
  loadPrefs(); applyTheme();
  loadServerConfig().then(function () {
    bindPanel(); resize(); poll(); startCycle(); setInterval(poll, 2000); keepAwake();
  });
  window.addEventListener("resize", resize);
})();
