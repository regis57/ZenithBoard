// SPDX-License-Identifier: GPL-3.0-or-later
// The statistics page (0.37.0 in ZenithBoard's look): the name in the wall's dots, a period toggle (24 hours, 7 days,
// 30 days) that every box, chart and list follows (0.43.0: the sky by hour, the fourth box and the farthest aircraft
// too), in the order of the summary's posts: the aircraft, cargo and business jets, military, general aviation; then
// how high, the messages, and the rest. Every airline with its flag first. Reads /api/stats?range=...
// 0.47.0: in the visitor's language (flightinfo/static/i18n.js): started once its catalogue is read.
window.ZBI18N.start({ part: "stats" }, function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var I = window.ZBI18N, t = I.t, tn = I.tn;
  // a country's name in the page's language, from the browser's own (CLDR) data; the Pi's English name otherwise
  var regionNames = null;
  try { if (I.lang() !== "en" && window.Intl && Intl.DisplayNames) regionNames = new Intl.DisplayNames([I.locale()], { type: "region" }); } catch (e) { regionNames = null; }
  function country(cc, english) {
    if (regionNames && /^[A-Z]{2}$/.test(cc || "")) { try { var n = regionNames.of(cc); if (n && n !== cc) return n; } catch (e) { /* unknown code */ } }
    return english || cc;
  }
  function esc(x) { return String(x).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  var tip = $("tip");
  function showTip(e, text) { tip.textContent = text; tip.hidden = false; tip.style.left = e.clientX + "px"; tip.style.top = e.clientY + "px"; }
  function hideTip() { tip.hidden = true; }
  function fmt(n) { return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, " "); }
  // the axis needs short labels: "2 M" fits the margin where "2 000 000" is cut off (the numbers above the bars stay whole)
  function axisFmt(n) {
    if (n >= 1e6) return String(Math.round(n / 1e5) / 10).replace(".0", "") + " M";
    if (n >= 1e4) return String(Math.round(n / 100) / 10).replace(".0", "") + " k";
    return fmt(n);
  }
  var NS = "http://www.w3.org/2000/svg";
  function el(name, attrs, text) {
    var n = document.createElementNS(NS, name);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (text !== undefined) n.textContent = text;
    return n;
  }
  // A round step that gives about four to six lines whatever the size: 10 000 messages and 3 000 000 both read well.
  // (A fixed step drew nearly four hundred labels on top of each other once an hour passed a million messages.)
  function ticks(max) {
    var raw = max / 4, mag = Math.pow(10, Math.floor(Math.log(raw) / Math.LN10)), m = raw / mag;
    var step = (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * mag, out = [];
    if (!(step > 0)) return [0];
    for (var v = 0; v <= max; v += step) out.push(v);
    return out;
  }
  function shortDay(d) { var p = d.split("-"); return p[2] + "/" + p[1]; }


  // ---- the brand: the name in the 5 x 7 dots of the wall, the unlit ones faint behind
  var THEME_HEX = { amber: "#ffb000", green: "#39ff6a", red: "#ff3b30", white: "#e8e8e8", turquoise: "#00d6d7" };
  function dots(mount, text, pitch) {
    var F = window.Font5x7;
    if (!mount || !F) { if (mount) mount.textContent = text; return; }
    var cols = text.length * 6 + 1, rows = 9, r = pitch * 0.38;
    var s = el("svg", { viewBox: "0 0 " + cols * pitch + " " + rows * pitch, "aria-hidden": "true" });
    for (var i = 0; i < text.length; i++) {
      var g = F.GLYPHS[text[i]] || F.GLYPHS[" "] || [];
      for (var y = 0; y < 7; y++) for (var x = 0; x < 5; x++) {
        var lit = g[y] && g[y][x] === "#";
        s.appendChild(el("circle", { "class": lit ? "d-on" : "d-off", cx: (1 + i * 6 + x + 0.5) * pitch, cy: (1 + y + 0.5) * pitch, r: lit ? r : r * 0.7 }));
      }
    }
    mount.innerHTML = ""; mount.appendChild(s);
  }
  function lighter(hex) {
    var n = parseInt(hex.slice(1), 16), c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map(function (v) { return Math.round(v + (255 - v) * 0.4); });
    return "#" + c.map(function (v) { return ("0" + v.toString(16)).slice(-2); }).join("");
  }
  function theme(name) {
    var hex = THEME_HEX[name] || THEME_HEX.amber, st = document.documentElement.style;
    st.setProperty("--on", hex); st.setProperty("--on-hot", lighter(hex));
  }

  function bars(mount, labels, values, unit, labelEvery, hot, W) {
    W = W || 720;
    var H = 220, L = 50, R = 8, T = 18, B = 28, w = W - L - R, h = H - T - B;
    var max = Math.max(4, Math.max.apply(null, values)) * 1.1, tk = ticks(max);   // small counts: whole lines
    var s = el("svg", { viewBox: "0 0 " + W + " " + H }), g = el("g", { "class": "grid" }), ax = el("g", { "class": "axis" });
    tk.forEach(function (v) { var y = T + h - v / max * h; g.appendChild(el("line", { x1: L, x2: W - R, y1: y, y2: y })); ax.appendChild(el("text", { x: L - 6, y: y + 4, "text-anchor": "end" }, axisFmt(v))); });
    s.appendChild(g); s.appendChild(ax);
    var n = values.length, gap = n > 20 ? 2 : 4, bw = Math.max(1, (w - gap * (n - 1)) / n);
    values.forEach(function (v, i) {
      var x = L + i * (bw + gap), bh = v / max * h, y = T + h - bh;
      s.appendChild(el("rect", { "class": "bar" + (i === hot ? " hot" : ""), x: x, y: y, width: bw, height: bh, rx: Math.min(2, bw / 2) }));
      if (i === hot && v > 0) s.appendChild(el("text", { "class": "lbl", x: Math.min(Math.max(x + bw / 2, L + 30), W - 30), y: y - 6, "text-anchor": "middle" }, fmt(v) + unit));
      var hit = el("rect", { "class": "hit", x: x - gap / 2, y: T, width: bw + gap, height: h });
      hit.addEventListener("mousemove", function (e) { showTip(e, labels[i] + ": " + fmt(v) + unit); });
      hit.addEventListener("mouseleave", hideTip);
      s.appendChild(hit);
      if (i % labelEvery === 0) ax.appendChild(el("text", { x: x + bw / 2, y: H - 8, "text-anchor": "middle" }, labels[i]));
    });
    mount.innerHTML = ""; mount.appendChild(s);
  }
  function line(mount, labels, values, unit, labelEvery, hot, W) {
    W = W || 720;
    var H = 220, L = 50, R = 12, T = 18, B = 28, w = W - L - R, h = H - T - B;
    var known = values.filter(function (v) { return v !== null && v !== undefined; });
    if (!known.length) known = [0];
    var lo = Math.min.apply(null, known), hi = Math.max.apply(null, known), pad = (hi - lo) * 0.25 || 10;
    var min = Math.max(0, Math.floor((lo - pad) / 50) * 50), max = Math.ceil((hi + pad) / 50) * 50 || 50;
    var s = el("svg", { viewBox: "0 0 " + W + " " + H }), g = el("g", { "class": "grid" }), ax = el("g", { "class": "axis" });
    for (var v = min; v <= max; v += 50) { var y = T + h - (v - min) / (max - min) * h; g.appendChild(el("line", { x1: L, x2: W - R, y1: y, y2: y })); ax.appendChild(el("text", { x: L - 6, y: y + 4, "text-anchor": "end" }, fmt(v))); }
    s.appendChild(g); s.appendChild(ax);
    var step = values.length > 1 ? w / (values.length - 1) : 0;
    // a slot with no sample is a gap: the line stops and starts again (0.37.0), never drops to zero
    var pts = values.map(function (v, i) { return v === null || v === undefined ? null : [L + (values.length > 1 ? i * step : w / 2), T + h - (v - min) / (max - min) * h]; });
    var runs = [], cur = [];
    pts.forEach(function (p) { if (p) cur.push(p); else if (cur.length) { runs.push(cur); cur = []; } });
    if (cur.length) runs.push(cur);
    runs.forEach(function (r) {
      if (r.length < 2) return;
      var d = r.map(function (p, i) { return (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1); }).join(" ");
      s.appendChild(el("path", { "class": "area", d: d + " L" + r[r.length - 1][0] + " " + (T + h) + " L" + r[0][0] + " " + (T + h) + " Z" }));
      s.appendChild(el("path", { "class": "line", d: d }));
    });
    pts.forEach(function (p, i) {
      if (!p) return;
      if (i === hot || pts.length === 1) { s.appendChild(el("circle", { "class": "dot", cx: p[0], cy: p[1], r: 5 })); s.appendChild(el("text", { "class": "lbl", x: Math.min(Math.max(p[0], L + 30), W - 30), y: p[1] - 10, "text-anchor": "middle" }, fmt(values[i]) + unit)); }
      var hw = pts.length > 1 ? step : w;
      var hit = el("rect", { "class": "hit", x: p[0] - hw / 2, y: T, width: hw, height: h });
      hit.addEventListener("mousemove", function (e) { showTip(e, labels[i] + ": " + fmt(values[i]) + unit); });
      hit.addEventListener("mouseleave", hideTip);
      s.appendChild(hit);
      if (i % labelEvery === 0) ax.appendChild(el("text", { x: p[0], y: H - 8, "text-anchor": "middle" }, labels[i]));
    });
    mount.innerHTML = ""; mount.appendChild(s);
  }
  // the sky by hour: a lit dot per hour, as on the weekly card, brighter where more aircraft had a position
  function heat(mount, rows, W) {
    W = W || 980;
    var one = rows.length === 1 && rows[0].labels;           // 0.43.0: the 24 hours, one row of the window's own hours
    var L = 52, T = 4, B = 22, R = 6, cw = (W - L - R) / 24, ch = one ? cw : W < 600 ? 12 : 15, H = T + rows.length * ch + B;
    var max = 0;
    rows.forEach(function (r) { r.hours.forEach(function (v) { if (v !== null && v > max) max = v; }); });
    var s = el("svg", { viewBox: "0 0 " + W + " " + H }), ax = el("g", { "class": "axis" });
    var rad = Math.min(cw, ch) * 0.36;
    rows.forEach(function (r, i) {
      var y = T + i * ch;
      if (!one && (i % 3 === 0 || i === rows.length - 1)) ax.appendChild(el("text", { x: L - 8, y: y + ch / 2 + 4, "text-anchor": "end" }, shortDay(r.day)));
      if (one) ax.appendChild(el("text", { x: L - 8, y: y + ch / 2 + 4, "text-anchor": "end" }, t("24 h")));
      r.hours.forEach(function (v, hh) {
        var c = el("circle", { "class": "cell" + (v === null ? " none" : ""), cx: L + hh * cw + cw / 2, cy: y + ch / 2, r: rad });
        if (v !== null) c.setAttribute("opacity", (0.1 + 0.9 * (max ? v / max : 0)).toFixed(2));
        c.addEventListener("mousemove", function (e) { showTip(e, (one ? r.labels[hh] : shortDay(r.day) + " " + (hh < 10 ? "0" : "") + hh + "h") + ": " + (v === null ? t("no sample") : tn(v, "{n} aircraft", "{n} aircraft", { n: fmt(v) }))); });
        c.addEventListener("mouseleave", hideTip);
        s.appendChild(c);
      });
    });
    for (var hh = 0; hh < 24; hh += W < 600 ? 6 : 3) ax.appendChild(el("text", { x: L + hh * cw + cw / 2, y: H - 6, "text-anchor": "middle" }, one ? rows[0].labels[hh] : (hh < 10 ? "0" : "") + hh + "h"));
    s.appendChild(ax);
    mount.innerHTML = ""; mount.appendChild(s);
  }
  function node(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; }
  function flag(cc) {
    if (!/^[A-Z]{2}$/.test(cc || "")) return node("span", "noflag", "?");
    var img = node("img", "flag"); img.src = "/flags/" + cc + ".png"; img.alt = cc;
    img.onerror = function () { var n = node("span", "noflag", cc); if (img.parentNode) img.parentNode.replaceChild(n, img); };
    return img;
  }
  // a ranked list: [lead (a flag)], the name (and, in grey, what goes with it), the count, a bar under it
  function ranks(mount, pairs, empty, opts) {
    opts = opts || {};
    mount.innerHTML = "";
    if (!pairs || !pairs.length) { mount.appendChild(node("p", "empty", empty)); return; }
    var max = pairs[0][1], ol = node("ol");
    pairs.slice(0, opts.top || 10).forEach(function (kv) {
      var li = node("li", opts.flags || opts.cc ? "flag" : ""), name = node("span", "name", opts.label ? opts.label(kv[0]) : kv[0]);
      li.appendChild(opts.cc ? flag(opts.cc(kv[0])) : opts.flags ? flag(kv[0]) : node("span"));
      if (opts.extra && opts.extra(kv[0])) name.appendChild(node("i", "", opts.extra(kv[0])));
      li.appendChild(name); li.appendChild(node("span", "n", fmt(kv[1])));
      var f = node("span", "fill"); f.style.width = (100 * kv[1] / max).toFixed(1) + "%"; li.appendChild(f);
      ol.appendChild(li);
    });
    mount.appendChild(ol);
  }
  function military(mount, list) {
    mount.innerHTML = "";
    var rows = [];
    (list || []).forEach(function (e) { e.models.slice(0, 3).forEach(function (m, i) { rows.push([e, m, i]); }); });
    if (!rows.length) { mount.appendChild(node("p", "empty", t("None heard in this period."))); return; }
    var max = Math.max.apply(null, rows.map(function (r) { return r[1][1]; }));
    rows.forEach(function (r) {
      var e = r[0], m = r[1], first = r[2] === 0, row = node("div", "row" + (first && rows[0] !== r ? " next" : ""));
      var fl = first ? flag(e.cc) : node("span"); fl.classList.add("f"); row.appendChild(fl);
      row.appendChild(node("span", "c", first ? country(e.cc, e.country) + " · " + fmt(e.total) : ""));
      row.appendChild(node("span", "m", m[0]));
      var b = node("span", "b"); b.style.width = (100 * m[1] / max).toFixed(1) + "%"; var bw = node("span", "bw"); bw.appendChild(b); row.appendChild(bw);
      row.appendChild(node("span", "n", fmt(m[1])));
      mount.appendChild(row);
    });
  }
  var GA = [["heli", t("Helicopters")], ["light", t("Light aircraft")], ["glider", t("Gliders")], ["other", t("Drones and balloons")]];
  function general(mount, misc) {
    mount.innerHTML = "";
    misc = misc || {};
    var other = {};
    var orows = {};
    ["drone", "balloon"].forEach(function (g) {
      ((misc[g] || {}).models || []).forEach(function (kv) { other[kv[0]] = (other[kv[0]] || 0) + kv[1]; });
      ((misc[g] || {}).rows || []).forEach(function (x) { var k = x[0] + "\u0000" + (x[1] || ""); orows[k] = (orows[k] || 0) + x[2]; });
    });
    var o = Object.keys(other).map(function (k) { return [k, other[k]]; }).sort(function (a, b) { return b[1] - a[1]; });
    var orr = Object.keys(orows).map(function (k) { var p = k.split("\u0000"); return [p[0], p[1], orows[k]]; }).sort(function (a, b) { return b[2] - a[2]; });
    misc.other = { total: o.reduce(function (sum, kv) { return sum + kv[1]; }, 0), models: o, rows: orr };
    GA.forEach(function (g) {
      var e = misc[g[0]] || { total: 0, models: [] }, fig = node("figure"), big = node("div", "big");
      big.appendChild(node("b", "", fmt(e.total))); big.appendChild(node("span", "", g[1]));
      fig.appendChild(big); fig.appendChild(node("figcaption", "", t("Make and model")));
      var r = node("div", "ranks flags"); fig.appendChild(r); mount.appendChild(fig);
      // 0.43.0: a row per model and country, the flag first, as on the summary's fourth card
      var rows = (e.rows || []).map(function (x) { return [x[0] + "\u0000" + (x[1] || ""), x[2]]; });
      if (!rows.length) rows = (e.models || []).map(function (kv) { return [kv[0] + "\u0000", kv[1]]; });
      ranks(r, rows, t("None heard in this period."), { top: 6, cc: function (k) { return k.split("\u0000")[1]; }, label: function (k) { return k.split("\u0000")[0]; } });
    });
  }

  // The farthest aircraft, in words (0.22.0): "18/10 14:32 · Ryanair FR8526 (RYR8526) · Charleroi (CRL) → Reggio
  // Calabria (REG) · Boeing 737-800 EI-DCL · 11 280 m · 322 km, near Lyon, FR (12 km)". Whatever is not known is left
  // out rather than guessed: no airline, no route, no city each simply drop their part.
  function altText(ft, units) {
    if (typeof ft !== "number") return null;
    return units === "imperial" ? fmt(Math.round(ft / 100) * 100) + " ft" : fmt(Math.round(ft * 0.3048 / 10) * 10) + " m";
  }
  function place(a) {
    if (!a) return null;
    var where = a.city || a.name, code = a.iata || a.icao;
    return where ? where + (code ? " (" + code + ")" : "") : code || null;
  }
  function farthestLine(r, units) {
    if (!r) return null;
    var parts = [shortDay(r.day) + (r.time ? " " + r.time : "")];
    var num = r.flight_iata || r.flight, who = r.airline && r.airline !== "MILITARY" ? r.airline + (num ? " " + num : "") : num || "";
    if (r.flight_iata && r.flight && r.flight_iata !== r.flight) who += " (" + r.flight + ")";
    if (r.airline === "MILITARY") who = (who ? who + " " : "") + t("(military)");
    parts.push(who || r.registration || String(r.hex || "").toUpperCase());
    if (r.route && (r.route.from || r.route.to)) parts.push((place(r.route.from) || "?") + " \u2192 " + (place(r.route.to) || "?"));
    var model = [r.type_name || r.type, who ? r.registration : null].filter(Boolean).join(" ");
    if (model) parts.push(model);
    var alt = altText(r.alt_ft, units);
    if (alt) parts.push(alt);
    // "near" up to 50 km; beyond, over the sea or open country, the distance says how near it really was
    var city = r.near && r.near.name ? r.near.name + (r.near.country ? ", " + r.near.country : "") : "";
    var near = !city ? "" : r.near.km <= 50 ? t(", near {city} ({km} km)", { city: city, km: fmt(r.near.km) }) : t(", {km} km from {city}", { city: city, km: fmt(r.near.km) });
    parts.push(fmt(r.km) + " km" + near);
    return parts.join(" \u00b7 ");
  }

  // The version, and behind it what changed in it. Nothing is asked of GitHub: it is a link, followed only if
  // somebody clicks it, so the page still names its version with no way out to the internet.
  var RELEASES = "https://github.com/regis57/ZenithBoard/releases";
  function versionLine(version) {
    var a = $("s-version");
    if (!a) return;
    a.textContent = version ? "ZenithBoard " + version : "ZenithBoard";
    a.href = version ? RELEASES + "/tag/v" + version : RELEASES;
  }


  function render(d) {
    var w = d.window || {}, tot = w.totals || {}, per = t(w.label || "the last 30 days"), days = w.range !== "24h";
    $("sub").textContent = tn(d.samples, "{n} sample of 15 minutes since {since}, 30 days kept · {period}", "{n} samples of 15 minutes since {since}, 30 days kept · {period}", { n: fmt(d.samples), since: d.since, period: per });
    // the four boxes: all of them the period's (0.43.0: the fourth was the thirty days' best, whatever the toggle)
    $("t-aircraft").textContent = fmt(tot.aircraft || 0);
    $("t-aircraft-d").textContent = t("distinct aircraft, {period}, a floor", { period: per });
    $("t-messages").textContent = fmt(tot.messages || 0);
    $("t-busiest").textContent = tot.busiest_hour === null || tot.busiest_hour === undefined ? t("nothing yet") :
      t("busiest hour {hour}:00, {n}", { hour: (tot.busiest_hour < 10 ? "0" : "") + tot.busiest_hour, n: fmt(tot.busiest_messages) });
    $("t-far").textContent = (tot.farthest_km || 0) + " km";
    $("t-far-d").textContent = tot.farthest_when ? t("on {day} at {time}", { day: shortDay(tot.farthest_when.slice(0, 10)), time: tot.farthest_when.slice(11) }) : per;
    var b = w.busiest;
    $("t-best-k").textContent = days ? t("Busiest day") : t("Busiest hour");
    $("t-best").textContent = b ? (days ? b.label : b.label.replace("h", ":00")) : "–";
    $("t-bestday").textContent = b ? (days ? tn(b.aircraft, "{n} distinct aircraft", "{n} distinct aircraft", { n: fmt(b.aircraft) }) : tn(b.aircraft, "{n} aircraft with a position, on average", "{n} aircraft with a position, on average", { n: fmt(b.aircraft) })) : per;
    // the farthest aircraft of the period, in words, its flag first
    var f = d.farthest || {}, rec = f.period, fline = farthestLine(rec, d.units), rp = $("r-period");
    $("r-period-k").textContent = t("Farthest, {period}", { period: per });
    rp.innerHTML = "";
    if (fline) { rp.appendChild(flag(rec.cc)); rp.appendChild(node("span", "", fline)); }
    else rp.appendChild(node("span", "", t("No details written down in this period yet: the next sample, on the quarter hour, does it.")));
    if (rec && tot.farthest_km && Math.round(rec.km) < tot.farthest_km)
      rp.appendChild(node("span", "rnote", (tot.farthest_when ? t("The box above says {km} km, on {day}: its details were not written down", { km: tot.farthest_km, day: shortDay(tot.farthest_when.slice(0, 10)) }) :
        t("The box above says {km} km: its details were not written down", { km: tot.farthest_km })) +
        (days ? t(" (they are since ZenithBoard 0.22.0, one aircraft a day: the day's farthest).") : t(" (one aircraft is written down a day, the day's farthest: yesterday's was outside these 24 hours)."))));
    var labels = w.labels || [], n = labels.length, every = n > 24 ? 5 : n > 12 ? 3 : 1;
    // drawings sized to the screen, so their text stays the same size on a phone as on a desk (0.37.0)
    var phone = window.innerWidth < 760, wide = phone ? 440 : 980, half = phone ? 440 : 480;
    if (phone) every = n > 24 ? 7 : n > 12 ? 4 : 2;
    // 1 · the aircraft: the sky by hour, the airlines and the models (the summary's first card)
    if (w.heat && w.heat.length) heat($("c-heat"), w.heat, wide); else $("c-heat").innerHTML = "";
    $("c-heat-sub").textContent = t("· aircraft with a position, on average, {period}", { period: per });
    var fl = d.fleet || {}, names = fl.country_names || {}, cm = fl.cargo_models || {}, acc = fl.airline_cc || {};
    var ccOf = function (k) { return acc[k]; };
    Array.prototype.forEach.call(document.querySelectorAll(".per"), function (s) { s.textContent = t("· distinct aircraft, {period}", { period: per }); });
    ranks($("c-airlines"), fl.airlines, t("Nothing in this period yet: the lists start with ZenithBoard 0.31.0."), { cc: ccOf });
    ranks($("c-types"), fl.types, fl.aircraft ? t("No model known: the decoder has no aircraft database. Turn on tar1090's, offline: sudo zenithboard data localdb on") : t("Nothing in this period yet."));
    // 2 · cargo and business jets
    $("n-cargo").textContent = fmt(fl.cargo_total || 0);
    $("n-biz").textContent = fmt(fl.bizjet_total || 0);
    $("n-bizc").textContent = fmt(fl.bizjet_country_total || (fl.bizjet_countries || []).length);
    ranks($("c-cargo"), fl.cargo, t("None heard in this period."), { top: 6, cc: ccOf, extra: function (k) { return cm[k] ? cm[k][0] + " (" + fmt(cm[k][1]) + ")" : ""; } });
    ranks($("c-biz"), fl.bizjets, t("None heard in this period."), { top: 6 });
    ranks($("c-bizc"), fl.bizjet_countries, t("None heard in this period."), { top: 6, flags: true, label: function (cc) { return country(cc, names[cc]); } });
    // 3 · military, 4 · general aviation
    $("n-mil").textContent = fmt(fl.military_total || 0);
    $("n-milc").textContent = fmt((fl.military || []).length);
    military($("c-mil"), fl.military);
    general($("c-ga"), fl.misc);
    // then how high, then the messages, then the rest
    if (fl.altitudes && fl.aircraft) {
      bars($("c-alt"), fl.altitudes.labels, fl.altitudes.counts, "", phone ? 2 : 1, fl.altitudes.counts.indexOf(Math.max.apply(null, fl.altitudes.counts)), wide);
      $("c-alt-sub").textContent = t("· distinct aircraft by the altitude last seen, in {unit}, {period}", { unit: fl.alt_unit || "km", period: per });
    } else { $("c-alt").innerHTML = ""; $("c-alt-sub").textContent = t("· nothing in this period yet"); }
    var mv = w.messages || [], fv = w.farthest || [], av = w.aircraft || [];
    $("c-msgs-sub").textContent = days ? t("· per day, {period}", { period: per }) : t("· per hour, {period}", { period: per });
    bars($("c-msgs"), labels, mv, "", every, mv.indexOf(Math.max.apply(null, mv)), wide);
    $("c-far-sub").textContent = days ? t("· km, the farthest each day, {period}", { period: per }) : t("· km, the farthest each hour, {period}", { period: per });
    $("c-planes-sub").textContent = "· " + t(w.aircraft_note || "") + ", " + per;
    line($("c-far"), labels, fv, " km", every, fv.indexOf(Math.max.apply(null, fv.filter(function (v) { return v !== null; }).concat([0]))), half);
    bars($("c-planes"), labels, av, "", every, av.indexOf(Math.max.apply(null, av)), half);
    var rows = "<tr><th>" + esc(days ? t("Day") : t("Hour")) + "</th><th>" + esc(days ? t("Aircraft") : t("With a position")) + "</th><th>" + esc(t("Messages")) + "</th><th>" + esc(t("Farthest km")) + "</th></tr>";
    for (var i = n - 1; i >= 0; i--) rows += "<tr><td>" + labels[i] + "</td><td>" + fmt(av[i] || 0) + "</td><td>" + fmt(mv[i] || 0) + "</td><td>" + (fv[i] === null || fv[i] === undefined ? "\u2013" : fv[i]) + "</td></tr>";
    $("table").innerHTML = rows;
  }

  // ---- the period: kept in the address (#7d) and, when the browser allows it, for the next visit
  var RANGES = ["24h", "7d", "30d"];
  function chosen() {
    var h = (location.hash || "").slice(1);
    if (RANGES.indexOf(h) >= 0) return h;
    try { var s = localStorage.getItem("zb-stats-range"); if (RANGES.indexOf(s) >= 0) return s; } catch (e) { /* private mode */ }
    return "30d";
  }
  function load(range) {
    Array.prototype.forEach.call(document.querySelectorAll("#toggle button"), function (b) {
      b.classList.toggle("on", b.getAttribute("data-range") === range);
      b.setAttribute("aria-pressed", b.getAttribute("data-range") === range ? "true" : "false");
    });
    fetch("/api/stats?range=" + range, { cache: "no-store" }).then(function (r) { return r.json(); }).then(function (d) {
      versionLine(d.version);
      theme(d.theme);
      if (!d.enabled) { $("sub").textContent = t("Off."); $("off").hidden = false; return; }
      if (!d.samples) { $("sub").textContent = t("On, waiting for the first sample."); $("empty").hidden = false; return; }
      $("toggle").hidden = false; $("dash").hidden = false; render(d);
    }).catch(function (e) { $("sub").textContent = t("Could not read /api/stats."); if (window.console) console.error(e); });
  }
  Array.prototype.forEach.call(document.querySelectorAll("#toggle button"), function (b) {
    b.addEventListener("click", function () {
      var r = b.getAttribute("data-range");
      try { localStorage.setItem("zb-stats-range", r); } catch (e) { /* private mode: the address keeps it */ }
      if (history.replaceState) history.replaceState(null, "", "#" + r); else location.hash = r;
      load(r);
    });
  });
  dots($("logo"), "ZENITHBOARD", 10);
  // the word in the dots in the page's language when the 5 x 7 font has its letters (capitals, no accent yet)
  var sw = t("STATISTICS"); dots($("logo-sub"), /^[A-Z0-9 ]+$/.test(sw) ? sw : "STATISTICS", 5);
  var lp = $("lang"); if (lp) lp.appendChild(I.picker());
  load(chosen());
});
