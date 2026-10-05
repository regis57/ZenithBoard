// SPDX-License-Identifier: GPL-3.0-or-later
// Side-view aircraft profiles (original geometric drawings, nose to the right) and the animated "sky" scene that
// the wall shows in the photo corner when no real photo is available. The same drawing operations are also used
// by tools/make_demo_photos.js to build the demo's mock photos, so mock and live drawings always match.
(function (root) {
  "use strict";
  var CY = 21;                                   // fuselage centre line in the 100 x 40 drawing box

  function f(n) { return Math.round(n * 100) / 100; }
  function poly(pts) { return "M" + pts.map(function (p) { return f(p[0]) + " " + f(p[1]); }).join("L") + "Z"; }
  function ell(cx, cy, rx, ry) {
    return "M" + f(cx - rx) + " " + f(cy) + "a" + f(rx) + " " + f(ry) + " 0 1 0 " + f(2 * rx) + " 0a" + f(rx) + " " + f(ry) + " 0 1 0 " + f(-2 * rx) + " 0Z";
  }
  function P(d, role) { return { d: d, role: role }; }
  function fus(x0, x1, cy, h, tl, nl, nose) {   // fuselage: tail upsweep at x0, rounded nose at x1
    tl = tl || 16; nl = nl || 12; nose = nose === undefined ? 0.08 : nose;
    return "M" + f(x0) + " " + f(cy - h * 0.18) + "L" + f(x0 + tl) + " " + f(cy - h / 2) + "L" + f(x1 - nl) + " " + f(cy - h / 2) +
      "Q" + f(x1) + " " + f(cy - h / 2) + " " + f(x1) + " " + f(cy + h * nose) + "Q" + f(x1 - 1) + " " + f(cy + h / 2) + " " + f(x1 - nl * 0.8) + " " + f(cy + h / 2) +
      "L" + f(x0 + tl * 1.4) + " " + f(cy + h / 2) + "Q" + f(x0 + 3) + " " + f(cy + h * 0.38) + " " + f(x0) + " " + f(cy - h * 0.18) + "Z";
  }
  function cockpit(x, cy, h, w) { w = w || 6; return P(poly([[x - w, cy - h * 0.38], [x, cy - h * 0.38], [x + 1.6, cy - h * 0.05], [x - w - 0.6, cy - h * 0.12]]), "glass"); }
  function stripe(x0, x1, y, t) { return P(poly([[x0, y], [x1, y], [x1, y + (t || 1.2)], [x0, y + (t || 1.2)]]), "stripe"); }
  function engine(cx, cy, rx, ry) { return [P(ell(cx, cy, rx, ry), "eng"), P(ell(cx + rx - 0.6, cy, 0.9, ry * 0.8), "dark")]; }
  function prop(cx, cy, r) { return { k: "prop", cx: cx, cy: cy, r: r }; }
  function rotor(cx, cy, r) { return { k: "rotor", cx: cx, cy: cy, r: r }; }

  function cat() { return [].concat.apply([], arguments); }

  // ------------------------------------------------------------------ profiles
  var B = {};

  B.narrow = function () {
    var cy = CY;
    return cat([
      P(poly([[10, cy - 2], [2, cy - 7.5], [5, cy - 7.5], [20, cy - 2]]), "wing"),
      P(poly([[22, cy - 4], [9, cy - 18], [3, cy - 18], [8, cy - 3]]), "tail"),
      P(fus(3, 97, cy, 9.4), "body"), stripe(14, 88, cy + 0.6), cockpit(94, cy, 9.4, 5.5),
      P(poly([[61, cy + 2.6], [47, cy + 2.6], [29, cy + 10], [37, cy + 10]]), "wing"),
      P(poly([[48, cy + 3], [55, cy + 3], [54, cy + 7], [49, cy + 7]]), "eng")], engine(50, cy + 8.2, 6.4, 2.7));
  };

  B.wide = function (v) {
    var cy = CY, o = [];
    o.push(P(poly([[11, cy - 2], [2, cy - 8], [6, cy - 8], [21, cy - 2]]), "wing"));
    o.push(P(poly([[24, cy - 5], [9, cy - 20], [2, cy - 20], [7, cy - 4]]), "tail"));
    if (v === "tri") o.push.apply(o, engine(15, cy - 9.2, 7.5, 3.1));
    o.push(P(fus(2, 98, cy, 11.4, 18, 13), "body"));
    if (v === "beluga") o.push(P("M62 " + f(cy - 5.7) + "Q70 " + f(cy - 19) + " 90 " + f(cy - 11) + "Q96 " + f(cy - 8) + " 97 " + f(cy - 3) + "Z", "body"));
    o.push(stripe(14, 90, cy + 0.9), cockpit(95, cy, 11.4, 5.2));
    o.push(P(poly([[64, cy + 3], [48, cy + 3], [27, cy + 11.5], [36, cy + 11.5]]), "wing"));
    o.push(P(poly([[48, cy + 3.5], [56, cy + 3.5], [55, cy + 8], [49, cy + 8]]), "eng"));
    o.push.apply(o, engine(51, cy + 9.6, 7.4, 3.3));
    return o;
  };

  B.quad = function (v) {
    var cy = v === "deck" ? 19.5 : CY, o = [], h = v === "deck" ? 15 : (v === "hiwing" ? 7.6 : 11.4);
    if (v === "hiwing") {                           // BAe 146 / Avro RJ: high wing, four small engines, T-tail
      o.push(P(poly([[10, cy - 14.4], [4, cy - 15.5], [20, cy - 14.4]]), "wing"));
      o.push(P(poly([[22, cy - 3], [11, cy - 15], [6, cy - 15], [9, cy - 3]]), "tail"));
      o.push(P(poly([[3, cy - 16], [18, cy - 16], [18, cy - 14.6], [3, cy - 14.6]]), "wing"));
      o.push(P(fus(5, 94, cy, h, 18, 11), "body"), stripe(16, 86, cy + 0.6), cockpit(91, cy, h, 5));
      o.push(P(poly([[66, cy - 3.8], [38, cy - 3.8], [30, cy - 1], [64, cy - 1]]), "wing"));
      o.push.apply(o, cat(engine(56, cy + 2, 5, 2), engine(44, cy + 2, 5, 2)));
      return o;
    }
    o.push(P(poly([[12, cy - 2], [2, cy - 8], [6, cy - 8], [22, cy - 2]]), "wing"));
    o.push(P(poly([[24, cy - 5], [9, cy - 21], [2, cy - 21], [7, cy - 4]]), "tail"));
    o.push(P(fus(2, 98, cy, h, 18, v === "deck" ? 9 : 13), "body"));
    if (v === "hump") o.push(P("M58 " + f(cy - h / 2) + "Q64 " + f(cy - 14.5) + " 80 " + f(cy - 11.6) + "Q89 " + f(cy - 9.5) + " 93 " + f(cy - h / 2 + 0.4) + "Z", "body"));
    o.push(stripe(14, 90, cy + 1.2));
    o.push(cockpit(v === "hump" ? 86 : 95, v === "hump" ? cy - 6 : cy, h, 4.5));
    if (v === "deck") o.push(stripe(20, 86, cy - 3.8, 0.8));
    o.push(P(poly([[66, cy + 3], [48, cy + 3], [26, cy + 12], [36, cy + 12]]), "wing"));
    o.push.apply(o, cat(engine(60, cy + 9, 6.4, 2.9), engine(46, cy + 10.2, 6.4, 2.9)));
    return o;
  };

  B.rearjet = function (v) {
    var cy = CY, o = [];
    o.push(P(poly([[19, cy - 2.4], [8, cy - 15], [4, cy - 15], [8, cy - 2.4]]), "tail"));
    o.push(P(poly([[3, cy - 16.4], [17, cy - 16.4], [17, cy - 14.6], [3, cy - 14.6]]), "wing"));
    if (v === "tri") o.push.apply(o, engine(9, cy - 8, 6.5, 2.4));
    o.push(P(fus(3, 94, cy, 7.8, 20, 11), "body"), stripe(24, 84, cy + 0.5, 1), cockpit(91, cy, 7.8, 5));
    o.push(P(poly([[60, cy + 2], [47, cy + 2], [32, cy + 8.5], [39, cy + 8.5]]), "wing"));
    o.push.apply(o, engine(19, cy - 1.6, 7.2, 2.5));
    o.push(P(poly([[22, cy - 0.5], [26, cy - 0.5], [26, cy + 1.3], [22, cy + 1.3]]), "eng"));
    if (v === "quad") o.push.apply(o, engine(27, cy - 4.3, 6, 2.2));
    return o;
  };

  B.turboprop = function (v) {
    var cy = CY, o = [];
    o.push(P(poly([[22, cy - 3], [10, cy - 16], [4, cy - 16], [8, cy - 3]]), "tail"));
    o.push(P(poly([[3, cy - 17.6], [16, cy - 17.6], [16, cy - 16.2], [3, cy - 16.2]]), "wing"));
    o.push(P(fus(4, 90, cy, 8.6, 20, 12), "body"), stripe(16, 82, cy + 0.6, 1.1), cockpit(87, cy, 8.6, 4.6));
    o.push(P(poly([[66, cy - 4.4], [38, cy - 4.4], [38, cy - 3], [66, cy - 3]]), "wing"));
    o.push(P(ell(54, cy + 4.6, 8, 2.3), "eng"));                      // landing-gear fairing
    o.push.apply(o, engine(55, cy - 3.2, 10, 2.5));
    o.push(prop(66.6, cy - 3.2, 8.2));
    if (v === "quad") { o.push.apply(o, engine(40, cy - 3.2, 10, 2.5)); o.push(prop(51.6, cy - 3.2, 8.2)); }
    return o;
  };

  B.bizjet = function () {
    var cy = CY;
    return cat([
      P(poly([[24, cy - 2.4], [13, cy - 15], [8, cy - 15], [10, cy - 2.4]]), "tail"),
      P(poly([[4, cy - 16.2], [18, cy - 16.2], [18, cy - 14.6], [4, cy - 14.6]]), "wing"),
      P(fus(4, 96, cy, 6.6, 18, 15, 0.12), "body"), stripe(24, 86, cy + 0.4, 0.9), cockpit(92, cy, 6.6, 5),
      P(poly([[58, cy + 1.6], [48, cy + 1.6], [37, cy + 6.8], [43, cy + 6.8]]), "wing"),
      P(poly([[37, cy + 6.4], [38.6, cy + 4.4], [40, cy + 6.4]]), "wing")], engine(21, cy - 2.6, 7, 2.3));
  };

  B.light = function (v) {
    var cy = CY + 1, hi = v === "high", o = [];
    o.push(P(poly([[26, cy - 2], [17, cy - 13], [12, cy - 13], [14, cy - 2]]), "tail"));
    o.push(P(poly([[10, cy - 1.4], [22, cy - 1.4], [22, cy - 0.2], [8, cy + 0.5]]), "wing"));
    o.push(P(fus(12, 84, cy, 7.4, 24, 12, 0.15), "body"), stripe(20, 70, cy + 0.6, 0.9));
    o.push(P(poly([[64, cy - 3.7], [66.5, cy - 0.7], [58, cy - 0.7], [56, cy - 3.7]]), "glass"));
    if (hi) {
      o.push(P(poly([[62, cy - 7], [38, cy - 7], [38, cy - 5.6], [62, cy - 5.6]]), "wing"));
      o.push(P(poly([[50, cy - 5.6], [52, cy - 5.6], [58, cy + 2.4], [56, cy + 2.4]]), "eng"));
    } else {
      o.push(P(poly([[62, cy + 1.2], [44, cy + 1.2], [38, cy + 4.2], [56, cy + 4.2]]), "wing"));
    }
    o.push(P(ell(86, cy + 0.6, 3.2, 3), "eng"));
    o.push(P(poly([[50, cy + 3.7], [51.2, cy + 3.7], [49, cy + 8], [47.8, cy + 8]]), "eng"), P(ell(48.6, cy + 8.2, 2.6, 2.6), "dark"));
    o.push(P(ell(17, cy + 3.4, 1, 1), "dark"));
    o.push(prop(88, cy + 0.6, 7.6));
    return o;
  };

  B.twinprop = function (v) {
    var o = B.light("low"), cy = CY + 1;
    o.push.apply(o, engine(60, cy + 2.7, 7, 2.1));
    o.push(prop(67.2, cy + 2.7, 6));
    if (v === "quad") { o.push.apply(o, engine(46, cy + 3.4, 7, 2.1)); o.push(prop(53.2, cy + 3.4, 6)); }
    return o;
  };

  B.heli = function (v) {
    var cy = CY + 1, o = [];
    if (v === "tandem") {                           // Chinook
      o.push(P(poly([[16, cy - 9.5], [20, cy - 9.5], [22, cy - 3], [18, cy - 3]]), "dark"), P(poly([[76, cy - 7], [80, cy - 7], [80, cy - 3], [76, cy - 3]]), "dark"));
      o.push(P(fus(14, 90, cy + 1, 11, 22, 12, 0.2), "body"), stripe(24, 80, cy + 2, 1.1), cockpit(87, cy + 1, 11, 4.5));
      o.push(P(poly([[20, cy - 3], [10, cy - 11], [6, cy - 11], [14, cy - 3]]), "tail"));
      o.push(P(ell(34, cy + 8.2, 4, 2.5), "eng"), P(ell(72, cy + 8.2, 3.4, 2.4), "dark"));
      o.push(rotor(18, cy - 10, 20), rotor(78, cy - 8, 20));
      return o;
    }
    if (v === "tilt") {                             // V-22 style tilt-rotor
      o.push(P(poly([[22, cy - 2], [10, cy - 13], [5, cy - 13], [10, cy - 2]]), "tail"));
      o.push(P(fus(8, 92, cy + 1, 9, 24, 14, 0.15), "body"), stripe(20, 80, cy + 2, 1), cockpit(89, cy + 1, 9, 4));
      o.push(P(poly([[62, cy - 3.4], [34, cy - 3.4], [34, cy - 1.8], [62, cy - 1.8]]), "wing"));
      o.push.apply(o, engine(56, cy - 5.2, 6, 2.2));
      o.push({ k: "prop", cx: 62.5, cy: cy - 5.2, r: 10 });
      return o;
    }
    o.push(P(poly([[34, cy - 2], [10, cy - 4.5], [8, cy - 2.5], [34, cy + 4]]), "body"));
    o.push(P(poly([[14, cy - 3], [8, cy - 13], [4, cy - 13], [9, cy - 3]]), "tail"));
    o.push(P(ell(52, cy + 1.2, 17, 7.6), "body"), stripe(36, 66, cy + 2.6, 1.1));
    o.push(P(poly([[63, cy - 4.6], [70, cy - 4.6], [69, cy + 1.6], [61, cy + 1.6]]), "glass"));
    o.push(P(poly([[48, cy - 8.4], [56, cy - 8.4], [55, cy - 12], [49, cy - 12]]), "eng"));
    o.push(P(poly([[40, cy + 9], [70, cy + 9], [70, cy + 10.2], [40, cy + 10.2]]), "dark"));
    o.push(P(poly([[46, cy + 7], [47.4, cy + 7], [47.4, cy + 9.4], [46, cy + 9.4]]), "dark"), P(poly([[62, cy + 7], [63.4, cy + 7], [63.4, cy + 9.4], [62, cy + 9.4]]), "dark"));
    o.push(rotor(52, cy - 12, 32), { k: "tailrotor", cx: 6, cy: cy - 8.5, r: 6 });
    return o;
  };

  B.fighter = function () {
    var cy = CY;
    return [
      P(poly([[19, cy + 2], [3, cy + 5], [7, cy + 6.4], [25, cy + 3.6]]), "wing"),
      P(poly([[32, cy - 4], [19, cy - 17.5], [12, cy - 17.5], [16, cy - 4]]), "tail"),
      P("M4 " + (cy - 2.6) + "L38 " + (cy - 4.7) + "L66 " + (cy - 4.5) + "Q86 " + (cy - 3.4) + " 99 " + (cy + 1.6) + "Q80 " + (cy + 4.6) + " 66 " + (cy + 4.9) + "L30 " + (cy + 4.2) + "L4 " + (cy + 2.6) + "Z", "body"),
      P(poly([[2, cy - 2.4], [6, cy - 2.7], [6, cy + 2.7], [2, cy + 2.4]]), "dark"),
      P(poly([[60, cy + 4.6], [76, cy + 4.6], [76, cy + 8.4], [62, cy + 8]]), "eng"), P(poly([[75, cy + 4.6], [76.8, cy + 4.6], [76.8, cy + 8.4], [75, cy + 8.4]]), "dark"),
      P("M64 " + (cy - 4.4) + "Q71 " + (cy - 9.8) + " 82 " + (cy - 3.9) + "Z", "glass"),
      P(poly([[58, cy + 2], [38, cy + 2], [26, cy + 9], [34, cy + 9.4]]), "wing"),
      stripe(20, 60, cy - 0.4, 0.9)];
  };

  B.delta = function () {
    var cy = CY;
    return [
      P(poly([[34, cy - 3.6], [16, cy - 17.6], [8, cy - 17.6], [10, cy - 3]]), "tail"),
      P(poly([[78, cy + 2.6], [8, cy + 3.2], [3, cy + 9.4], [30, cy + 9.4]]), "wing"),
      P("M4 " + (cy - 2.6) + "L40 " + (cy - 4.2) + "L66 " + (cy - 4) + "Q86 " + (cy - 2.6) + " 99 " + (cy + 2) + "Q82 " + (cy + 4.5) + " 66 " + (cy + 4.8) + "L8 " + (cy + 3.4) + "Z", "body"),
      P(poly([[2, cy - 2.2], [6, cy - 2.7], [6, cy + 2.8], [2, cy + 2.4]]), "dark"),
      P(poly([[72, cy - 1], [64, cy - 6.4], [68, cy - 6.4], [76, cy - 1.4]]), "wing"),
      P("M62 " + (cy - 4) + "Q68 " + (cy - 8.8) + " 78 " + (cy - 3.4) + "Z", "glass"),
      P(poly([[56, cy + 4.6], [68, cy + 4.6], [68, cy + 7.8], [58, cy + 7.6]]), "eng"),
      stripe(18, 56, cy - 0.3, 0.9)];
  };

  B.airlifter = function (v) {
    var cy = 19.5, o = [];
    o.push(P(poly([[22, cy - 6], [10, cy - 20.5], [3, cy - 20.5], [8, cy - 5]]), "tail"));
    o.push(P(poly([[1, cy - 22], [18, cy - 22], [18, cy - 20.4], [1, cy - 20.4]]), "wing"));
    o.push(P("M3 " + (cy - 1) + "L18 " + (cy - 6.5) + "L80 " + (cy - 6.5) + "Q96 " + (cy - 6.5) + " 96 " + (cy + 1.5) + "Q94 " + (cy + 6.6) + " 84 " + (cy + 6.6) + "L24 " + (cy + 6.6) + "Q8 " + (cy + 5) + " 3 " + (cy - 1) + "Z", "body"));
    o.push(P(poly([[72, cy - 5.6], [88, cy - 5.6], [93, cy - 1.8], [74, cy - 2.4]]), "glass"));
    o.push(stripe(20, 72, cy + 1.5, 1.1));
    o.push(P(poly([[66, cy - 7.4], [36, cy - 7.4], [36, cy - 6], [66, cy - 6]]), "wing"));
    if (v === "jet") {
      o.push.apply(o, cat(engine(56, cy - 1.8, 6.5, 2.7), engine(43, cy - 1.8, 6.5, 2.7)));
      o.push(P(ell(60, cy + 6.4, 12, 2.8), "eng"));
    } else if (v === "prop2") {
      o.push(P(ell(60, cy + 6.4, 11, 2.8), "eng"));
      o.push.apply(o, engine(54, cy - 5.3, 9.5, 2.4)); o.push(prop(64.2, cy - 5.3, 8.5));
    } else {
      o.push(P(ell(58, cy + 6.4, 14, 3.2), "body"));
      o.push.apply(o, cat(engine(59, cy - 5.4, 9, 2.3), engine(45, cy - 5.4, 9, 2.3)));
      o.push(prop(68, cy - 5.4, 8.2), prop(54, cy - 5.4, 8.2));
    }
    return o;
  };

  B.bomber = function () {
    var cy = CY;
    return [
      P(poly([[36, cy - 3], [16, cy - 23], [7, cy - 23], [11, cy - 3]]), "tail"),
      P(poly([[8, cy - 1.8], [16, cy - 6], [20, cy - 6], [24, cy - 1.8]]), "wing"),
      P("M3 " + (cy - 2) + "L40 " + (cy - 3.4) + "L78 " + (cy - 3.2) + "Q96 " + (cy - 2.4) + " 99 " + (cy + 0.6) + "Q92 " + (cy + 3.4) + " 78 " + (cy + 3.6) + "L40 " + (cy + 3.8) + "L3 " + (cy + 1.8) + "Z", "body"),
      P(poly([[70, cy - 2.6], [78, cy - 2.6], [82, cy - 0.4], [68, cy - 0.8]]), "glass"),
      P(poly([[66, cy - 1], [46, cy - 1], [24, cy + 8], [36, cy + 8]]), "wing"),
      P(ell(52, cy + 4.6, 7, 2), "eng"), P(ell(40, cy + 6.2, 7, 2), "eng"), P(ell(32, cy + 7.2, 6, 1.8), "eng"),
      stripe(14, 70, cy + 0.2, 0.7)];
  };

  B.glider = function () {
    var cy = CY;
    return [
      P(poly([[14, cy - 1.4], [9, cy - 11], [14, cy - 11], [20, cy - 1.4]]), "tail"),
      P(poly([[6, cy - 12], [16, cy - 12], [16, cy - 10.6], [6, cy - 10.6]]), "wing"),
      P("M6 " + (cy - 1) + "L50 " + (cy - 2.4) + "L72 " + (cy - 2.6) + "Q92 " + (cy - 2) + " 95 " + (cy + 0.6) + "Q80 " + (cy + 2.4) + " 50 " + (cy + 2.2) + "L6 " + (cy + 0.2) + "Z", "body"),
      P("M52 " + (cy - 2.4) + "Q62 " + (cy - 7) + " 78 " + (cy - 2.4) + "Z", "glass"),
      P("M20 " + (cy - 3.4) + "Q50 " + (cy - 5.4) + " 80 " + (cy - 3.4) + "L80 " + (cy - 2.4) + "Q50 " + (cy - 3.4) + " 20 " + (cy - 2.4) + "Z", "wing"),
      P(ell(54, cy + 3.4, 2, 2), "dark")];
  };

  B.balloon = function () {
    return [
      P(poly([[43, 26], [44.2, 26], [48, 33], [47, 33]]), "dark"), P(poly([[57, 26], [55.8, 26], [52, 33], [53, 33]]), "dark"),
      P(ell(50, 14, 15.5, 14), "tail"),
      P("M50 0.4Q40 14 46 27L54 27Q60 14 50 0.4Z", "stripe"),
      P(poly([[46.4, 33], [53.6, 33], [53, 38], [47, 38]]), "dark")];
  };

  var ZOOM = { heli: 1.35, light: 1.2, twinprop: 1.2, bizjet: 1.05, glider: 1.0, rearjet: 1.05, turboprop: 1.05 };   // small types are drawn larger
  function profileOps(shape, variant) {
    var b = B[shape] || B.narrow;
    return b(variant || null);
  }

  // ------------------------------------------------------------------ colours
  function hashStr(s) { var h = 2166136261; s = String(s || ""); for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
  function palette(military, seed) {
    if (military) return { body: "#9ba2a9", wing: "#8a9199", tail: "#7a828a", eng: "#5f666e", dark: "#2b3139", stripe: "#6f767e", glass: "#202c38", line: "rgba(0,0,0,.35)" };
    var hue = hashStr(seed) % 360, acc = "hsl(" + hue + ",68%,44%)";
    return { body: "#f4f6f9", wing: "#cdd4dc", tail: acc, eng: "#a9b1bb", dark: "#2b3441", stripe: acc, glass: "#1f2b3a", line: "rgba(0,0,0,.30)" };
  }

  // ------------------------------------------------------------------ drawing the profile
  function drawSpecial(ctx, o, pal, t) {
    var ph = t * 23, c = Math.abs(Math.cos(ph));
    ctx.save();
    if (o.k === "prop") {                         // propeller seen edge-on: a faint disc + a blade that shortens and lengthens
      ctx.fillStyle = "rgba(30,30,30,.20)"; ctx.beginPath(); ctx.ellipse(o.cx, o.cy, 0.9, o.r, 0, 0, 6.2832); ctx.fill();
      ctx.fillStyle = "rgba(25,25,25,.75)"; ctx.fillRect(o.cx - 0.5, o.cy - o.r * c, 1, 2 * o.r * c);
    } else if (o.k === "rotor") {                 // main rotor: flat disc + blade
      ctx.fillStyle = "rgba(30,30,30,.16)"; ctx.beginPath(); ctx.ellipse(o.cx, o.cy, o.r, 1.1, 0, 0, 6.2832); ctx.fill();
      ctx.strokeStyle = "rgba(25,25,25,.85)"; ctx.lineWidth = 0.8; ctx.beginPath();
      ctx.moveTo(o.cx - o.r * c, o.cy - 0.3 * c); ctx.lineTo(o.cx + o.r * c, o.cy + 0.3 * c); ctx.stroke();
    } else if (o.k === "tailrotor") {
      ctx.fillStyle = "rgba(30,30,30,.2)"; ctx.beginPath(); ctx.ellipse(o.cx, o.cy, 0.9, o.r, 0, 0, 6.2832); ctx.fill();
      ctx.fillStyle = "rgba(25,25,25,.8)"; ctx.fillRect(o.cx - 0.4, o.cy - o.r * c, 0.8, 2 * o.r * c);
    }
    ctx.restore();
  }

  // Draws the ops into a 100x40 box whose top-left is (x, y) and whose width is w (pixels).
  function drawProfile(ctx, ops, pal, x, y, w, t) {
    var s = w / 100;
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
    ctx.lineJoin = "round"; ctx.lineWidth = 0.3; ctx.strokeStyle = pal.line;
    ops.forEach(function (o) {
      if (o.k) { drawSpecial(ctx, o, pal, t || 0); return; }
      var p = new Path2D(o.d);
      ctx.fillStyle = pal[o.role] || pal.body; ctx.fill(p); ctx.stroke(p);
    });
    ctx.restore();
  }

  // Same drawing as SVG elements (static pose) - used for demo photos.
  function svgOps(ops, pal) {
    var out = [];
    ops.forEach(function (o) {
      if (o.k === "prop" || o.k === "tailrotor") out.push('<ellipse cx="' + f(o.cx) + '" cy="' + f(o.cy) + '" rx="0.9" ry="' + f(o.r) + '" fill="rgba(30,30,30,.22)"/><rect x="' + f(o.cx - 0.5) + '" y="' + f(o.cy - o.r * 0.8) + '" width="1" height="' + f(o.r * 1.6) + '" fill="rgba(25,25,25,.7)"/>');
      else if (o.k === "rotor") out.push('<ellipse cx="' + f(o.cx) + '" cy="' + f(o.cy) + '" rx="' + f(o.r) + '" ry="1.1" fill="rgba(30,30,30,.16)"/><line x1="' + f(o.cx - o.r * 0.85) + '" y1="' + f(o.cy - 0.2) + '" x2="' + f(o.cx + o.r * 0.85) + '" y2="' + f(o.cy + 0.2) + '" stroke="rgba(25,25,25,.85)" stroke-width="0.8"/>');
      else out.push('<path d="' + o.d + '" fill="' + (pal[o.role] || pal.body) + '" stroke="' + pal.line + '" stroke-width="0.3" stroke-linejoin="round"/>');
    });
    return out.join("");
  }

  // ------------------------------------------------------------------ animated sky scene
  // One continuous day rather than three fixed looks: the colours, the sun and the moon are interpolated from
  // the clock, so the light really moves from dawn to noon to dusk. Everything is plain canvas on a small
  // corner box, so an old tablet keeps up.
  function rgb(c) {                                 // accepts "#rrggbb" and the "rgb(r,g,b)" that mixHex returns
    if (c.charAt(0) !== "#") { var m = c.match(/-?\d+/g); return [+m[0], +m[1], +m[2]]; }
    var n = parseInt(c.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function lerp(a, b, k) { return a + (b - a) * k; }
  function mixHex(a, b, k) {
    var x = rgb(a), y = rgb(b);
    return "rgb(" + Math.round(lerp(x[0], y[0], k)) + "," + Math.round(lerp(x[1], y[1], k)) + "," + Math.round(lerp(x[2], y[2], k)) + ")";
  }
  function rgba(c, a) { var x = rgb(c); return "rgba(" + x[0] + "," + x[1] + "," + x[2] + "," + a + ")"; }
  function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }

  // hour -> sky gradient (top / middle / bottom) and how dark it is (1 = full night)
  var SKY_KEYS = [
    { h: 0.0, top: "#050a1c", mid: "#0b1733", bot: "#17284d", dark: 1 },
    { h: 4.8, top: "#08122c", mid: "#1b2b55", bot: "#46406d", dark: 1 },
    { h: 6.2, top: "#2c3d73", mid: "#9c6f8e", bot: "#f2a35e", dark: 0.35 },
    { h: 7.5, top: "#3e79c9", mid: "#86b9e8", bot: "#e8f1ff", dark: 0 },
    { h: 13.0, top: "#2f7ad8", mid: "#6fb0ee", bot: "#c4e6ff", dark: 0 },
    { h: 18.5, top: "#3a74c6", mid: "#8fb3dd", bot: "#f3dcb4", dark: 0 },
    { h: 20.2, top: "#2b3a70", mid: "#8a5f82", bot: "#f09a55", dark: 0.35 },
    { h: 21.8, top: "#070e24", mid: "#121d3e", bot: "#243457", dark: 1 },
    { h: 24.0, top: "#050a1c", mid: "#0b1733", bot: "#17284d", dark: 1 }
  ];
  var SUNRISE = 6.0, SUNSET = 20.5;

  // Where a body sits on its arc: 0 = rising at the left, 1 = setting at the right.
  function arcPos(k) { return { x: 0.12 + 0.76 * k, y: 0.82 - Math.sin(Math.PI * clamp01(k)) * 0.66 }; }

  function skyFor(hour, minute) {
    var t = ((hour || 0) + (minute || 0) / 60) % 24; if (t < 0) t += 24;
    var i = 0; while (i < SKY_KEYS.length - 2 && SKY_KEYS[i + 1].h <= t) i++;
    var a = SKY_KEYS[i], b = SKY_KEYS[i + 1], k = (t - a.h) / (b.h - a.h);
    var dark = lerp(a.dark, b.dark, k);
    var sunK = (t - SUNRISE) / (SUNSET - SUNRISE), sunUp = sunK >= 0 && sunK <= 1;
    // the moon takes the other half of the clock, from sunset round to sunrise
    var moonK = t > SUNSET ? (t - SUNSET) / (24 - SUNSET + SUNRISE) : (t + 24 - SUNSET) / (24 - SUNSET + SUNRISE);
    var low = sunUp ? Math.min(sunK, 1 - sunK) / 0.18 : 1;                 // 0 right at the horizon, 1 high up
    var warm = mixHex("#ff9a4d", "#fff6cf", clamp01(low));
    var body = sunUp ? arcPos(sunK) : arcPos(moonK);
    return {
      top: mixHex(a.top, b.top, k), mid: mixHex(a.mid, b.mid, k), bottom: mixHex(a.bot, b.bot, k),
      dark: dark, night: dark > 0.5, sunUp: sunUp,
      sun: sunUp ? warm : null,                                            // kept for callers that only want the warm tint
      light: sunUp ? warm : "#cdd8f0",                                      // colour that lights the clouds
      bodyX: body.x, bodyY: body.y, bodyLow: sunUp ? clamp01(low) : 1,
      hour: t
    };
  }

  function makeClouds(seed) {
    var r = seed || 7, out = [];
    function rnd() { r = (r * 1664525 + 1013904223) >>> 0; return r / 4294967296; }
    var layers = [{ n: 4, size: 0.085, y0: 0.10, y1: 0.40, speed: 0.012, a: 0.40, front: false },
                  { n: 3, size: 0.13, y0: 0.18, y1: 0.58, speed: 0.026, a: 0.58, front: false },
                  { n: 2, size: 0.21, y0: 0.88, y1: 1.08, speed: 0.06, a: 0.72, front: true }];
    layers.forEach(function (L) {
      for (var i = 0; i < L.n; i++) out.push({ x: rnd() * 1.4 - 0.2, y: L.y0 + rnd() * (L.y1 - L.y0), size: L.size * (0.8 + rnd() * 0.5), speed: L.speed, a: L.a, front: L.front });
    });
    return out;
  }
  // High, thin cirrus: barely moving streaks that give the daytime sky some depth.
  function makeCirrus(seed) {
    var r = seed || 3, out = [];
    function rnd() { r = (r * 1664525 + 1013904223) >>> 0; return r / 4294967296; }
    for (var i = 0; i < 5; i++) out.push({ x: rnd() * 1.4 - 0.2, y: 0.05 + rnd() * 0.3, w: 0.18 + rnd() * 0.22, speed: 0.004 + rnd() * 0.004, a: 0.2 + rnd() * 0.18 });
    return out;
  }

  var PUFFS = [[-1.1, 0.18, 0.55], [-0.5, -0.12, 0.75], [0.25, -0.24, 0.85], [0.95, -0.02, 0.66], [1.45, 0.2, 0.46], [0.2, 0.2, 0.7], [-0.4, 0.28, 0.5]];
  // A cloud is drawn twice: the shaded body, then the puffs facing the sun in the light of the moment.
  function drawCloud(ctx, cx, cy, s, a, sky) {
    var shade = sky.night ? rgba("#49567d", a * 0.42) : mixHex("#dbe4f0", "#a7b6ce", sky.dark);
    var lit = sky.night ? rgba("#7f8db4", a * 0.45) : rgba(sky.light, Math.min(0.95, a + 0.15));
    var dir = sky.bodyX < 0.5 ? -1 : 1;
    ctx.fillStyle = sky.night ? shade : rgba(shade, a);
    PUFFS.forEach(function (c) { ctx.beginPath(); ctx.arc(cx + c[0] * s, cy + c[1] * s, c[2] * s, 0, 6.2832); ctx.fill(); });
    ctx.fillStyle = lit;
    PUFFS.forEach(function (c, i) {
      if (i % 2) return;                                                   // only the upper, sunlit puffs
      ctx.beginPath(); ctx.arc(cx + (c[0] + dir * 0.12) * s, cy + (c[1] - 0.14) * s, c[2] * s * 0.82, 0, 6.2832); ctx.fill();
    });
  }

  function Scene(canvas) {
    this.canvas = canvas; this.ctx = canvas.getContext("2d");
    this.clouds = makeClouds(11); this.cirrus = makeCirrus(23); this.stars = null;
    this.ops = null; this.pal = null; this.label = ""; this.raf = 0; this.last = 0; this.t0 = 0;
  }
  Scene.prototype.setPlane = function (plane) {
    this.ops = profileOps(plane.shape, plane.variant); this.zoom = ZOOM[plane.shape] || 1;
    this.pal = palette(plane.military, plane.airline_icao || plane.hex || plane.type);
    this.label = String(plane.type_name || plane.type || "").toUpperCase();
    this.t0 = performance.now();
    this.render(performance.now());
  };
  Scene.prototype.resize = function () {
    var dpr = window.devicePixelRatio || 1;
    this.canvas.width = Math.max(2, Math.round(this.canvas.clientWidth * dpr));
    this.canvas.height = Math.max(2, Math.round(this.canvas.clientHeight * dpr));
    this.stars = null;
  };
  Scene.prototype.render = function (now) {
    var c = this.canvas, ctx = this.ctx, W = c.width, H = c.height, t = (now - this.t0) / 1000;
    if (!W || !H) return;
    var now_ = new Date(), sky = skyFor(now_.getHours(), now_.getMinutes()), self = this;
    var g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, sky.top); g.addColorStop(0.55, sky.mid); g.addColorStop(1, sky.bottom);
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);

    // stars fade in and out around dusk and dawn instead of snapping on
    var starA = clamp01((sky.dark - 0.2) / 0.55) * 0.85;
    if (starA > 0.02) {
      if (!this.stars) { var r = 5, st = []; for (var i = 0; i < 40; i++) { r = (r * 1664525 + 1013904223) >>> 0; var a = r / 4294967296; r = (r * 1664525 + 1013904223) >>> 0; st.push([a, (r / 4294967296) * 0.7, (r % 97) / 97]); } this.stars = st; }
      var px = Math.max(1, W / 300);
      this.stars.forEach(function (s) {
        var tw = 0.55 + 0.45 * Math.sin(t * 1.6 + s[2] * 6.2832);          // slow twinkle
        ctx.fillStyle = "rgba(255,255,255," + (starA * tw) + ")";
        ctx.fillRect(s[0] * W, s[1] * H, px, px);
      });
    }

    // the sun (or the moon) on its arc, with a glow that breathes
    var bx = sky.bodyX * W, by = sky.bodyY * H, rad = H * (sky.sunUp ? 0.085 : 0.07);
    var glowR = H * (sky.sunUp ? 0.40 - 0.08 * sky.bodyLow : 0.24) * (1 + 0.04 * Math.sin(t * 0.7));
    var glow = ctx.createRadialGradient(bx, by, 0, bx, by, glowR);
    var gc = sky.sunUp ? sky.light : "#dfe7ff";
    glow.addColorStop(0, rgba(gc, sky.sunUp ? 0.5 : 0.34));
    glow.addColorStop(0.3, rgba(gc, sky.sunUp ? 0.16 : 0.1));
    glow.addColorStop(1, rgba(gc, 0));
    ctx.fillStyle = glow; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = sky.sunUp ? rgba(sky.light, 0.98) : "rgba(238,243,255,.92)";
    ctx.beginPath(); ctx.arc(bx, by, rad, 0, 6.2832); ctx.fill();
    if (!sky.sunUp) {                                                      // a bite out of the disc makes it a moon
      ctx.fillStyle = sky.top;
      ctx.beginPath(); ctx.arc(bx + rad * 0.45, by - rad * 0.3, rad * 0.88, 0, 6.2832); ctx.fill();
    }

    // high cirrus, almost still
    this.cirrus.forEach(function (ci) {
      var span = 1.7, x = ((((ci.x - t * ci.speed) % span) + span) % span - 0.3) * W, y = ci.y * H, w2 = ci.w * W;
      ctx.fillStyle = rgba(sky.night ? "#6a79a6" : sky.light, ci.a * (sky.night ? 0.5 : 0.75));
      for (var j = 0; j < 3; j++) {
        ctx.beginPath();
        ctx.ellipse(x + j * w2 * 0.33, y + j * H * 0.018, w2 * (0.5 - j * 0.1), H * 0.012, -0.08, 0, 6.2832);
        ctx.fill();
      }
    });

    function clouds(front) {
      self.clouds.forEach(function (cl) {
        if (cl.front !== front) return;
        var span = 1.6, x = (((cl.x - t * cl.speed) % span) + span) % span - 0.3;     // drifting left, wrapping around
        drawCloud(ctx, x * W, cl.y * H, cl.size * H, cl.a, sky);
      });
    }
    clouds(false);

    // warm haze sitting on the horizon, strongest when the sun is low
    var hz = ctx.createLinearGradient(0, H * 0.55, 0, H);
    hz.addColorStop(0, rgba(sky.bottom, 0));
    hz.addColorStop(1, rgba(sky.sunUp ? sky.light : sky.bottom, sky.sunUp ? 0.16 + 0.26 * (1 - sky.bodyLow) : 0.1));
    ctx.fillStyle = hz; ctx.fillRect(0, H * 0.55, W, H * 0.45);

    if (this.ops) {
      var w = Math.min(W * 0.92, H * 0.62 * 2.5 * (this.zoom || 1)), bob = Math.sin(t * 1.3) * H * 0.012, tilt = Math.sin(t * 0.8) * 0.012;
      ctx.save(); ctx.translate(W / 2, H * 0.44 + bob); ctx.rotate(tilt);
      drawProfile(ctx, this.ops, this.pal, -w / 2, -w * 0.2, w, t);
      ctx.restore();
    }
    clouds(true);
    if (this.label) {
      var fs = Math.max(9, Math.round(H * 0.085)); ctx.font = "600 " + fs + "px system-ui, sans-serif";
      var tw = ctx.measureText(this.label).width, pad = fs * 0.5;
      ctx.fillStyle = "rgba(0,0,0,.45)"; ctx.fillRect(0, H - fs - pad * 1.4, Math.min(W, tw + pad * 2), fs + pad * 1.4);
      ctx.fillStyle = "#fff"; ctx.textBaseline = "middle"; ctx.fillText(this.label, pad, H - (fs + pad * 1.4) / 2);
    }
  };
  Scene.prototype.start = function () {
    var self = this; if (this.raf) return;
    (function loop(now) {
      self.raf = requestAnimationFrame(loop);
      if (now - self.last < 45) return;           // ~22 fps is plenty for drifting clouds and keeps old tablets cool
      self.last = now; self.render(now);
    })(performance.now());
  };
  Scene.prototype.stop = function () { if (this.raf) cancelAnimationFrame(this.raf); this.raf = 0; };

  var api = { profileOps: profileOps, ZOOM: ZOOM, palette: palette, drawProfile: drawProfile, svgOps: svgOps, Scene: Scene, skyFor: skyFor,
              CLASSES: Object.keys(B) };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.SceneKit = api;
})(typeof self !== "undefined" ? self : this);
