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
  var COLS_FLAGS = 12;                             // ... and with the two flags, which take the last two
  var FLAG_X = 75, FLAG_Y1 = 8, FLAG_Y2 = 25;      // the flags: registration beside the REG row (0.20.0), maker beside the model
  var TEXT_MAX_X = 74;                             // text stops here when the flags are shown (the outline starts at 74)
  var ROW_MAX_X = 84;                              // without the flags: a whole row, fourteen letters, before the right-hand column
  var GW = 128, GH = 80;
  var RX = 90, RW = 38;                            // right-hand column
  var SIL_BOX = { x: RX, y: 0, w: RW, h: 34 };
  var PHOTO_BOX = { x: 86, y: 38, w: 42, h: 30 };  // 7:5, like the 3:2 Planespotters thumbnails
  var ON = 1;                                      // grid value: 1 = lit in the theme colour
  var FLAP_COLS = 16, FLAP_ROWS = 9, FLAP_W = 84;  // split-flap style: 16 letters x 9 rows on the left 84 dots (the photo keeps the right-hand column)

  var canvas = document.getElementById("wall"), ctx = canvas.getContext("2d");
  var server = { units: "metric", theme: "amber", radius: 10, radius_presets: [1, 2, 5, 10, 15, 30, 50], cycle_seconds: 14,
                 show_photos: true, flags: true };
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
    ["units", "radius", "cycle", "theme", "mode", "flags"].forEach(function (k) { if (q.has(k)) prefs[k] = q.get(k); });
    if (q.has("p")) prefs.preset = String(q.get("p")).toLowerCase();   // a named preset of the Pi's (0.21.0), applied once /api/config is in
    savePrefs();
  }
  // ?p=kitchen: the Pi's preset of that name sets this tablet's choices, as if they had been in the address.
  // Applied at every load, so changing the preset on the Pi changes the tablet at its next reload; a key the
  // preset does not name keeps whatever the tablet chose itself.
  function applyPreset() {
    var p = prefs.preset && server.presets ? server.presets[prefs.preset] : null;
    if (!p) return;
    Object.keys(p).forEach(function (k) { prefs[k] = p[k]; });
    savePrefs();
  }
  function savePrefs() { try { localStorage.setItem("zenithboard", JSON.stringify(prefs)); } catch (e) {} }
  function units() { return ["metric", "imperial", "aviation"].indexOf(prefs.units) >= 0 ? prefs.units : server.units; }
  function radius() { var r = parseFloat(prefs.radius); return r > 0 ? r : server.radius; }
  function cycleMs() { var c = parseFloat(prefs.cycle); return Math.max(2, c > 0 ? c : server.cycle_seconds) * 1000; }
  // A colour the wall no longer has (the dark blue, gone in 0.23.0), still in a tablet's memory or in its address,
  // falls back to the Pi's colour rather than to a page of unstyled dots with an empty choice in the gear panel
  var THEMES = ["amber", "green", "red", "white", "turquoise"];
  function theme() {
    var t = [prefs.theme, server.theme].filter(function (x) { return THEMES.indexOf(x) >= 0; })[0];
    return t || "amber";
  }
  function mode() { return prefs.mode === "flap" || prefs.mode === "dots" ? prefs.mode : (server.display_mode === "flap" ? "flap" : "dots"); }
  function flagsOn() { return prefs.flags !== undefined ? (prefs.flags === "1" || prefs.flags === true) : server.flags !== false; }
  function cols() { return flagsOn() ? COLS_FLAGS : COLS; }
  function applyTheme() { document.body.setAttribute("data-theme", theme()); }

  // ------------------------------------------------------------------ dot grid
  function blank() { return new Uint32Array(GW * GH); }
  function put(g, x, y, v) { if (x >= 0 && x < GW && y >= 0 && y < GH) g[y * GW + x] = v; }
  // One row of text, drawn from an offset and clipped before the flag column: this is what scrolls when a name
  // is longer than the row. offset is in dots, so the movement is one dot at a time rather than one letter.
  function textRow(g, s, y, offset, maxX) {
    s = String(s).toUpperCase();
    for (var i = 0; i < s.length; i++) {
      var gl = Font5x7.GLYPHS[s[i]] || Font5x7.GLYPHS["?"], x0 = i * 6 - offset;
      if (x0 > maxX) break;
      for (var r = 0; r < 7; r++) for (var c = 0; c < 5; c++) {
        if (gl[r][c] !== "#") continue;
        var x = x0 + c;
        if (x >= 0 && x < maxX) put(g, x, y + r, ON);
      }
    }
  }
  function rowWidth(s) { return Math.max(0, String(s).length * 6 - 1); }

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
  // The credit, 0.99.17 (review B9): on a phone the corner is a hundred pixels wide and "(c) name - planespotters.net"
  // ran out of it, cut by an ellipsis in the middle of the photographer's name. When it does not fit, the site's
  // name goes (the photo stays the link to its page there); when the name alone does not fit either, it wraps, and
  // the photo gives up the height of the extra lines.
  var credit = { full: "", short: "" };
  function fitPhoto(g) {
    var W = PHOTO_BOX.w * g.pitch, H = PHOTO_BOX.h * g.pitch, fs = Math.max(8, g.pitch * 1.5);
    var iw = photoImg.naturalWidth, ih = photoImg.naturalHeight, ratio = iw && ih ? iw / ih : 1.5;
    box.style.fontSize = fs + "px";
    box.style.left = "auto"; box.style.top = "auto"; box.style.height = "auto";
    box.style.right = (canvas.clientWidth - (g.ox + (PHOTO_BOX.x + PHOTO_BOX.w) * g.pitch)) + "px";
    box.style.bottom = (canvas.clientHeight - (g.oy + (PHOTO_BOX.y + PHOTO_BOX.h) * g.pitch)) + "px";
    var capH = fs * 1.6, w = Math.min(W, Math.max(10, H - capH) * ratio);
    box.style.width = w + "px";
    photoCap.classList.remove("wrap"); photoImg.style.width = "";
    if (photoCap.textContent !== credit.full) photoCap.textContent = credit.full;
    if (box.hidden || !credit.full) return;                   // nothing to measure
    function over() { return photoCap.scrollWidth > photoCap.clientWidth + 1; }
    if (over() && credit.short !== credit.full) photoCap.textContent = credit.short;
    if (!over()) return;
    // the name alone is too long: the caption takes the corner's whole width and wraps (two lines at most), and the
    // photo, centred above it, gives up the height of the extra line. A narrower box would wrap the name once more.
    box.style.width = W + "px";
    photoCap.classList.add("wrap");
    capH = Math.max(capH, box.offsetHeight - photoImg.offsetHeight);     // the caption and the box's border
    photoImg.style.width = Math.min(W, Math.max(10, H - capH) * ratio) + "px";
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
    scene.stop(); sceneCanvas.hidden = true; box.hidden = false;
    credit.short = p.photo_credit ? "\u00a9 " + p.photo_credit : "";
    credit.full = credit.short && p.photo_link ? credit.short + " \u00b7 planespotters.net" : credit.short;
    fitPhoto(geom());
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

  // The two flags: where the aircraft is registered, beside its registration (the REG row, since 0.20.0: it sat
  // beside the airline, which read as the airline's country), and where it was built, beside the model. A country
  // we have no flag for falls back to its two letters, which is still better than a hole.
  function badges(g, p) {
    var reg = window.Flags ? Flags.country(p.registration) : null;
    var made = window.Flags ? Flags.origin(p.type_name) : null;
    function at(code, y) {
      if (!code) return;
      if (!Flags.draw(code, FLAG_X, y, function (x, yy, v) { put(g, x, yy, v); })) text(g, code, FLAG_X, y, 1);
    }
    at(reg, FLAG_Y1); at(made, FLAG_Y2);
  }

  function centered(str) { str = String(str); var n = Math.max(0, Math.floor((FLAP_COLS - str.length) / 2)); return new Array(n + 1).join(" ") + str; }
  function buildScreen() {
    var g = blank(), u = units();
    if (error || !planes.length) scroll.stop();            // nothing with a long name on screen: stop moving
    if (error === "offline") {
      // 0.54.4: it is the tablet that lost the Pi (three polls failed: Wi-Fi, the Pi restarting), which the old screen
      // blamed on the decoder; and "RECEIVER NOT RESPONDING" (137 dots) was wider than the wall (128) and cut at both ends
      textCenter(g, "NO ANSWER", 8, 2); textCenter(g, "THE TABLET LOST", 32, 1); textCenter(g, "THE PI", 41, 1); textCenter(g, "CHECK THE WI-FI", 54, 1);
      return { g: g, sig: "offline", plane: null, lines: ["", centered("NO ANSWER"), "", centered("THE TABLET"), centered("LOST THE PI"), "", centered("CHECK THE"), centered("WI-FI")] };
    }
    if (error === "host") {
      // 0.99.17 (review B9): the Pi answered, and refused the name in the address bar. Only its address, its own name
      // (.local, .lan, .home) or a name listed in CONSOLE_HOSTS reach the wall's data (server.py, wall_host_ok)
      textCenter(g, "WRONG NAME", 8, 2); textCenter(g, "USE THE PI ADDRESS", 32, 1); textCenter(g, "OR ADD THIS NAME", 41, 1); textCenter(g, "TO CONSOLE_HOSTS", 54, 1);
      return { g: g, sig: "host", plane: null, lines: ["", centered("WRONG NAME"), "", centered("USE THE PI"), centered("ADDRESS"), "", centered("OR ADD THIS NAME"), centered("TO CONSOLE_HOSTS")] };
    }
    if (error) {
      textCenter(g, "NO DATA", 8, 2); textCenter(g, "RECEIVER NOT", 32, 1); textCenter(g, "RESPONDING", 41, 1); textCenter(g, "CHECK THE DECODER", 54, 1);
      return { g: g, sig: "error", plane: null, lines: ["", centered("NO DATA"), "", centered("RECEIVER NOT"), centered("RESPONDING"), "", centered("CHECK THE"), centered("DECODER")] };
    }
    var p = planes.filter(function (x) { return x.hex === curHex; })[0];
    if (!p) {
      textCenter(g, "NO FLIGHTS", 6, 2);
      textCenter(g, "WITHIN " + radius() + " " + Fmt.distUnit(u), 28, 1);
      textCenter(g, "SEEN " + total + " AIRCRAFT", 40, 1);
      textCenter(g, clock(), 54, 2);
      var within = "WITHIN " + radius() + " " + Fmt.distUnit(u);
      return { g: g, sig: "empty" + total + clock() + radius() + u, plane: null,
               lines: ["", centered("NO FLIGHTS"), "", centered(within), centered("SEEN " + total + " AIRCRAFT"), "", centered(clock()), ""] };
    }
    // With the flags, both rows stop before the flag column: the airline row has no flag beside it since 0.20.0,
    // but the REG row's flag can carry a one-dot outline whose last row is the one just above the airline's
    // letters. Without the flags, both stop before the right-hand column: before 0.20.0 they went on to the wall's
    // edge, and a long name ran under the silhouette rather than turning.
    var on = flagsOn(), maxX = on ? TEXT_MAX_X : ROW_MAX_X;
    var L = Fmt.planeLines(p, u, planes.indexOf(p), planes.length, cols());
    scroll.prepare(p.hex + "|" + L.airlineFull + "|" + L.typeFull + "|" + maxX,
                   [{ y: 16, text: L.airlineFull, mx: maxX }, { y: 25, text: L.typeFull, mx: maxX }]);
    text(g, L.flight, 0, 0, 1); text(g, L.reg, 0, 8, 1);                 // 0.19.0: FLT and REG rows, not a two-row callsign
    textRow(g, scroll.text(0, L.airlineFull), 16, scroll.off(0), maxX);
    textRow(g, scroll.text(1, L.typeFull), 25, scroll.off(1), maxX);
    text(g, L.alt, 0, 34, 1); text(g, L.spd, 0, 43, 1); text(g, L.from, 0, 52, 1); text(g, L.to, 0, 61, 1);       // where the flight comes from / goes to (blank when unknown)
    text(g, L.footer, 0, 72, 1);
    if (on) badges(g, p);
    silhouette(g, p.shape || "generic", SIL_BOX);
    return { g: g, sig: "p" + p.hex + L.flight + L.reg + L.footer + L.alt + L.spd + L.type + L.from + L.to + (p.photo || "") + (on ? "f" : ""), plane: p,
             lines: [L.flight, L.reg, L.airline, L.type, L.alt, L.spd, L.from, L.to, L.footer] };
  }

  // ------------------------------------------------------------------ scrolling rows
  // A name longer than the row scrolls, one dot at a time, with a pause at each end: with the flags in place a
  // row holds twelve characters, and ROYAL AIR MAROC does not. Only the two rows that scroll are repainted,
  // never the whole wall, so an old tablet is not asked to redraw ten thousand dots nine times a second.
  var scroll = (function () {
    var STEP_MS = 110, GAP = "   ";                // one dot every 110 ms, three spaces between the two passes
    var rows = [], key = "", maxX = GW, timer = 0;   // maxX: a row's own limit when it gives none
    function need() { return mode() === "dots" && rows.some(function (r) { return r.cycle > 0; }); }
    function tick() {
      var moved = [];
      rows.forEach(function (r) {
        if (r.cycle <= 0) return;
        r.off = (r.off + 1) % r.cycle;             // the name comes round again; it never jumps back
        moved.push(r);
      });
      moved.forEach(function (r) {
        for (var y = r.y; y < r.y + 7; y++) for (var x = 0; x < r.mx; x++) put(grid, x, y, 0);
        textRow(grid, r.draw, r.y, r.off, r.mx);
        drawRect(0, r.y, r.mx, r.y + 7);
      });
    }
    function sync() {
      if (timer) { clearInterval(timer); timer = 0; }
      if (need()) timer = setInterval(tick, STEP_MS);
    }
    function row(y, text, mx) {
      // A name that does not fit turns continuously: the row holds the name, a gap, then the name again, and
      // the window walks one length before starting over. What leaves on the left is already arriving on the
      // right, so there is nothing to jump back from.
      mx = mx || maxX;
      var scrolls = rowWidth(text) > mx;
      return { y: y, off: 0, mx: mx, cycle: scrolls ? (text.length + GAP.length) * 6 : 0,
               draw: scrolls ? text + GAP + text : text };
    }
    return {
      prepare: function (k, items) {
        if (k !== key) { key = k; rows = items.map(function (it) { return row(it.y, it.text, it.mx); }); }
        sync();
      },
      off: function (i) { return rows[i] ? rows[i].off : 0; },
      text: function (i, fallback) { return rows[i] ? rows[i].draw : fallback; },
      stop: function () { key = ""; rows = []; sync(); }
    };
  })();

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
  function geomPx() {
    var W = canvas.width, H = canvas.height, pitch = Math.min(W / (GW + 3), H / (GH + 3));
    return { pitch: pitch, ox: (W - pitch * GW) / 2, oy: (H - pitch * GH) / 2 };
  }
  // Repaint the dots of one rectangle of the grid, used by the scrolling rows. A lit dot carries a glow wider
  // than itself, so the painting is clipped to a rectangle three dots larger than the one asked for and the
  // dots just outside are drawn too. Without the clip the glow landed outside the cleared area and was added
  // again on every step, which drew a bright frame around whichever row was scrolling.
  var GLOW_PAD = 3;
  function drawRect(x0, y0, x1, y1) {
    var m = geomPx(), r = m.pitch * 0.42, p = GLOW_PAD;
    // 0.99.17 (review B9): on whole device pixels. The pitch is rarely a whole number (a phone at 2.75 pixels per dot,
    // a tablet at 1.5 device pixels per CSS pixel); a clip edge inside a pixel was cleared only in part and painted
    // again at every step, which left a faint line along the scrolling row's edges.
    var px = Math.floor(m.ox + (x0 - p) * m.pitch), py = Math.floor(m.oy + (y0 - p) * m.pitch);
    var pw = Math.ceil(m.ox + (x1 + p) * m.pitch) - px, ph = Math.ceil(m.oy + (y1 + p) * m.pitch) - py;
    ctx.save();
    ctx.beginPath(); ctx.rect(px, py, pw, ph); ctx.clip();
    ctx.clearRect(px, py, pw, ph);
    var off = new Path2D(), lit = {};
    for (var y = Math.max(0, y0 - 2 * p); y < Math.min(GH, y1 + 2 * p); y++)
      for (var x = Math.max(0, x0 - 2 * p); x < Math.min(GW, x1 + 2 * p); x++) {
        var v = grid[y * GW + x], cx = m.ox + (x + 0.5) * m.pitch, cy = m.oy + (y + 0.5) * m.pitch, path;
        if (!v) path = off; else { var k = v === ON ? "t" : hex6(v); path = lit[k] || (lit[k] = new Path2D()); }
        path.moveTo(cx + r, cy); path.arc(cx, cy, r, 0, 6.2832);
      }
    ctx.shadowBlur = 0; ctx.globalAlpha = 0.09; ctx.fillStyle = dotColor; ctx.fill(off);
    ctx.globalAlpha = 1; ctx.shadowBlur = m.pitch * 1.2;
    Object.keys(lit).forEach(function (k) { var col = k === "t" ? dotColor : k; ctx.fillStyle = col; ctx.shadowColor = col; ctx.fill(lit[k]); });
    ctx.shadowBlur = 0;
    ctx.restore();
  }
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
    var f = flapGeom(), dpr = canvas.width / canvas.clientWidth;
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
    // the dotted aircraft, top right, and nothing else: a screen without one (NO ANSWER, WRONG NAME, the empty sky) drew
    // the last letters of its dotted title there, beside the flaps (seen in the preview of 0.99.17)
    flapSil = screen.plane ? screen.g : null;
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
    flapStop(); scroll.stop(); lastSig = ""; grid = blank(); hideCorner(); firstFlap = true;
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
  // 0.99.17 (review B9): one request at a time, and none waits more than five seconds. A Pi that stops answering
  // without closing the connection (the server frozen, the Wi-Fi half up) left every poll waiting for ever: no
  // failure was counted, so the wall kept its last aircraft instead of saying it lost the Pi, and a new request
  // joined the queue every two seconds. A request that runs out of time is aborted, and counts as a failure.
  var POLL_TIMEOUT_MS = 5000, polling = false, pollAgain = false;
  function getTimed(url, read) {
    var ctl = typeof AbortController === "function" ? new AbortController() : null, timer = 0;
    var opts = { cache: "no-store" };
    if (ctl) opts.signal = ctl.signal;
    // the timer also covers reading the body, and gives up even in a browser that cannot abort a request
    return new Promise(function (resolve, reject) {
      timer = setTimeout(function () { if (ctl) ctl.abort(); reject(new Error("timeout")); }, POLL_TIMEOUT_MS);
      fetch(url, opts).then(read).then(resolve, reject);
    }).then(function (v) { clearTimeout(timer); return v; }, function (e) { clearTimeout(timer); throw e; });
  }
  function readPlanes(r) {
    // 0.99.17: the Pi answers, and refuses the name the wall was opened by (wall_host_ok in server.py). That is not
    // a lost Pi: counting it as one showed "NO ANSWER" and then reloaded the page every minute, for ever. The
    // ALLOW_FROM refusal carries its own text and stays a failure, as before.
    if (r.status === 403) return r.text().then(function (t) { if (t.indexOf("CONSOLE_HOSTS") >= 0) return { refused: true }; throw new Error("403"); });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }
  function poll() {
    if (polling) { pollAgain = true; return; }        // a change made in the panel is asked again once this one is back
    polling = true;
    var url = "/api/planes?radius_km=" + Fmt.radiusToKm(radius(), units()).toFixed(3);
    getTimed(url, readPlanes).then(function (d) {
      failures = 0;
      if (d.refused) { error = "host"; planes = []; total = 0; show(buildScreen(), false); return; }
      if (serverId && d.server_id && d.server_id !== serverId) { location.reload(); return; }   // server restarted/upgraded
      serverId = d.server_id || serverId;
      error = d.error ? d.error : null; planes = d.planes || []; total = d.total || 0;
      var switched = ensureCurrent();
      show(buildScreen(), switched);
    }).catch(function () {
      if (++failures === 3) { error = "offline"; show(buildScreen(), false); }
      // self-heal, 0.54.4: only when the Pi answers again. A reload with the network still down meets the browser's own
      // error page, and a tablet on the wall stays there until someone touches it
      if (failures >= 30 && failures % 30 === 0) getTimed("/api/health", function (r) { return r.ok; }).then(function (ok) { if (ok) location.reload(); }).catch(function () {});
    }).then(function () {
      polling = false;
      if (pollAgain) { pollAgain = false; poll(); }
    });
  }
  function pollTick() { if (!polling) poll(); }       // the two-second timer never queues behind a request still out
  function loadServerConfig() {
    // 0.99.17: a refusal (403, a wrong name) or an error page is not the Pi's settings: the wall keeps its defaults
    return getTimed("/api/config", function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(function (c) { server = c; serverId = c.server_id; applyPreset(); }).catch(function () {});
  }

  // ------------------------------------------------------------------ settings panel
  var panel = document.getElementById("settings");
  function fillPanel() {
    var rs = document.getElementById("s-radius"), u = units();
    rs.innerHTML = "";
    // the audit of 22-23 October 2026: a radius that is not a preset (set with config-set or ?radius=) showed the
    // first preset instead; it is listed too, where it falls, and selected
    var list = server.radius_presets.slice(), cur = radius();
    if (list.indexOf(cur) < 0 && cur > 0) { list.push(cur); list.sort(function (a, b) { return a - b; }); }
    list.forEach(function (v) {
      var o = document.createElement("option"); o.value = v; o.textContent = v + " " + (u === "aviation" ? "NM" : Fmt.distUnit(u).toLowerCase());
      if (v === cur) o.selected = true; rs.appendChild(o);
    });
    document.getElementById("s-units").value = u;
    document.getElementById("s-cycle").value = cycleMs() / 1000;
    document.getElementById("s-theme").value = theme();
    document.getElementById("s-mode").value = mode();
    document.getElementById("s-flags").value = flagsOn() ? "1" : "0";
    versionLine(document.getElementById("s-version"), server.version);
    // The way to the statistics page, beside the version and in the same grey. It is offered only while the page
    // has something to show: with statistics off, /stats says so rather than charting nothing, and a link to a
    // feature nobody switched on is an invitation to a dead end.
    document.getElementById("s-stats-sep").hidden = !server.stats;
  }
  // The version, and behind it what changed in it. The page asks GitHub for nothing: this is a link, followed
  // only if somebody taps it, so a wall with no way out to the internet still shows the number it is running.
  var RELEASES = "https://github.com/regis57/ZenithBoard/releases";
  function versionLine(a, version) {
    if (!a) return;
    a.textContent = version ? "ZenithBoard " + version : "ZenithBoard";
    a.href = version ? RELEASES + "/tag/v" + version : RELEASES;
  }
  function bindPanel() {
    document.getElementById("gear").onclick = function () { fillPanel(); panel.hidden = !panel.hidden; };
    document.getElementById("s-units").onchange = function () { prefs.units = this.value; savePrefs(); fillPanel(); lastSig = ""; poll(); };
    document.getElementById("s-radius").onchange = function () { prefs.radius = this.value; savePrefs(); lastSig = ""; poll(); };
    // whole seconds, 2 to 60, like the Pi's own setting; anything else puts back what applies (it kept 0 or 600 shown)
    document.getElementById("s-cycle").onchange = function () {
      var v = Math.round(Number(this.value));
      if (v >= 2 && v <= 60) { prefs.cycle = String(v); savePrefs(); startCycle(); }
      fillPanel();
    };
    document.getElementById("s-theme").onchange = function () { prefs.theme = this.value; savePrefs(); applyTheme(); resize(); };
    document.getElementById("s-mode").onchange = function () { prefs.mode = this.value; savePrefs(); applyMode(); };
    document.getElementById("s-flags").onchange = function () { prefs.flags = this.value; savePrefs(); scroll.stop(); lastSig = ""; poll(); };
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
    applyTheme(); bindPanel(); resize(); poll(); startCycle(); setInterval(pollTick, 2000); keepAwake();
  });
  window.addEventListener("resize", resize);
})();
