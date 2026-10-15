// SPDX-License-Identifier: GPL-3.0-or-later
// The statistics page: reads /api/stats and draws three charts, one series each, with a hover tooltip.
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
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

  function bars(mount, labels, values, unit, labelEvery, hot, W) {
    W = W || 720;
    var H = 220, L = 50, R = 8, T = 16, B = 28, w = W - L - R, h = H - T - B;
    var max = Math.max(1, Math.max.apply(null, values)) * 1.08, tk = ticks(max);
    var s = el("svg", { viewBox: "0 0 " + W + " " + H }), g = el("g", { "class": "grid" }), ax = el("g", { "class": "axis" });
    tk.forEach(function (v) { var y = T + h - v / max * h; g.appendChild(el("line", { x1: L, x2: W - R, y1: y, y2: y })); ax.appendChild(el("text", { x: L - 6, y: y + 4, "text-anchor": "end" }, axisFmt(v))); });
    s.appendChild(g); s.appendChild(ax);
    var n = values.length, gap = 2, bw = Math.max(1, (w - gap * (n - 1)) / n);
    values.forEach(function (v, i) {
      var x = L + i * (bw + gap), bh = v / max * h, y = T + h - bh;
      s.appendChild(el("rect", { "class": "bar" + (i === hot ? " hot" : ""), x: x, y: y, width: bw, height: bh, rx: Math.min(3, bw / 2) }));
      if (i === hot && v > 0) s.appendChild(el("text", { "class": "lbl", x: x + bw / 2, y: y - 5, "text-anchor": "middle" }, fmt(v) + unit));
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
    var H = 220, L = 50, R = 10, T = 16, B = 28, w = W - L - R, h = H - T - B;
    var lo = Math.min.apply(null, values), hi = Math.max.apply(null, values), pad = (hi - lo) * 0.25 || 10;
    var min = Math.max(0, Math.floor((lo - pad) / 50) * 50), max = Math.ceil((hi + pad) / 50) * 50 || 50;
    var s = el("svg", { viewBox: "0 0 " + W + " " + H }), g = el("g", { "class": "grid" }), ax = el("g", { "class": "axis" });
    for (var v = min; v <= max; v += 50) { var y = T + h - (v - min) / (max - min) * h; g.appendChild(el("line", { x1: L, x2: W - R, y1: y, y2: y })); ax.appendChild(el("text", { x: L - 6, y: y + 4, "text-anchor": "end" }, fmt(v))); }
    s.appendChild(g); s.appendChild(ax);
    var step = values.length > 1 ? w / (values.length - 1) : 0;
    var pts = values.map(function (v, i) { return [L + (values.length > 1 ? i * step : w / 2), T + h - (v - min) / (max - min) * h]; });
    var d = pts.map(function (p, i) { return (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1); }).join(" ");
    if (pts.length > 1) {
      s.appendChild(el("path", { "class": "area", d: d + " L" + pts[pts.length - 1][0] + " " + (T + h) + " L" + pts[0][0] + " " + (T + h) + " Z" }));
      s.appendChild(el("path", { "class": "line", d: d }));
    }
    pts.forEach(function (p, i) {
      if (i === hot || pts.length === 1) { s.appendChild(el("circle", { "class": "dot", cx: p[0], cy: p[1], r: 5 })); s.appendChild(el("text", { "class": "lbl", x: p[0], y: p[1] - 10, "text-anchor": "middle" }, fmt(values[i]) + unit)); }
      var hw = pts.length > 1 ? step : w;
      var hit = el("rect", { "class": "hit", x: p[0] - hw / 2, y: T, width: hw, height: h });
      hit.addEventListener("mousemove", function (e) { showTip(e, labels[i] + ": " + fmt(values[i]) + unit); });
      hit.addEventListener("mouseleave", hideTip);
      s.appendChild(hit);
      if (i % labelEvery === 0) ax.appendChild(el("text", { x: p[0], y: H - 8, "text-anchor": "middle" }, labels[i]));
    });
    mount.innerHTML = ""; mount.appendChild(s);
  }

  function render(d) {
    $("sub").textContent = d.samples + " samples of 15 minutes since " + d.since + ", 30 days kept.";
    var t = d.today || {};
    $("t-aircraft").textContent = fmt(t.aircraft || 0);
    $("t-messages").textContent = fmt(t.messages || 0);
    $("t-busiest").textContent = t.busiest_hour === null || t.busiest_hour === undefined ? "nothing yet today" : "busiest hour " + (t.busiest_hour < 10 ? "0" : "") + t.busiest_hour + ":00, " + fmt(t.busiest_messages);
    $("t-far").textContent = (t.farthest_km || 0) + " km";
    $("t-best").textContent = d.best ? d.best.farthest_km + " km" : "–";
    $("t-bestday").textContent = d.best ? "on " + shortDay(d.best.day) : "";
    var hl = d.hours.map(function (h) { return (h.hour < 10 ? "0" : "") + h.hour + "h"; }), hv = d.hours.map(function (h) { return h.messages; });
    var hot = hv.indexOf(Math.max.apply(null, hv));
    bars($("c-msgs"), hl, hv, "", 3, hot);
    var dl = d.days.map(function (x) { return shortDay(x.day); });
    var fv = d.days.map(function (x) { return x.farthest_km; }), pv = d.days.map(function (x) { return x.aircraft; });
    var every = d.days.length > 14 ? 7 : d.days.length > 7 ? 2 : 1;
    // the two half-width charts get a narrower drawing, so their text is the same size as the wide one
    var half = window.innerWidth >= 760 ? 360 : 720;
    line($("c-far"), dl, fv, " km", every, fv.indexOf(Math.max.apply(null, fv)), half);
    bars($("c-planes"), dl, pv, "", every, pv.indexOf(Math.max.apply(null, pv)), half);
    var rows = "<tr><th>Day</th><th>Aircraft</th><th>Messages</th><th>Farthest km</th><th>Samples</th></tr>";
    d.days.slice().reverse().forEach(function (x) { rows += "<tr><td>" + x.day + "</td><td>" + fmt(x.aircraft) + "</td><td>" + fmt(x.messages) + "</td><td>" + x.farthest_km + "</td><td>" + x.samples + "</td></tr>"; });
    $("table").innerHTML = rows;
  }

  fetch("/api/stats", { cache: "no-store" }).then(function (r) { return r.json(); }).then(function (d) {
    if (!d.enabled) { $("sub").textContent = "Off."; $("off").hidden = false; return; }
    if (!d.samples) { $("sub").textContent = "On, waiting for the first sample."; $("empty").hidden = false; return; }
    $("dash").hidden = false; render(d);
  }).catch(function () { $("sub").textContent = "Could not read /api/stats."; });
})();
