// SPDX-License-Identifier: GPL-3.0-or-later
// Original generic aircraft silhouettes seen from above (nose to the right), drawn from simple geometry on a
// 32x32 canvas and rasterised to dots. One per class from flightinfo/aircraft.py. No brand artwork is used.
(function (root) {
  function E(cx, cy, rx, ry) { return { t: "e", cx: cx, cy: cy, rx: rx, ry: ry }; }
  function P(pts) { return { t: "p", pts: pts }; }
  function M(pts) { return pts.map(function (p) { return [p[0], 32 - p[1]]; }); }   // mirror top <-> bottom
  function PM(pts) { return [P(pts), P(M(pts))]; }
  function EM(cx, cy, rx, ry) { return [E(cx, cy, rx, ry), E(cx, 32 - cy, rx, ry)]; }
  function cat() { return [].concat.apply([], arguments); }
  function R(x0, y0, x1, y1) { return P([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]); }

  var SHAPES = {
    // single-aisle airliner: engines under the wings
    narrow: cat([E(16, 16, 15, 2.1)], PM([[18, 15], [9, 2], [12.5, 2], [22, 14.5]]), PM([[5, 15], [1, 9], [3.5, 9], [8, 15]]),
                EM(14, 8, 2.2, 1.1)),
    // twin wide-body: bigger, two big engines
    wide: cat([E(16, 16, 15.5, 2.8)], PM([[19, 14], [8, 1], [12.5, 1], [23, 13.5]]), PM([[5, 14], [1, 8], [4, 8], [9, 14]]),
              EM(14.5, 7, 2.5, 1.4)),
    // four engines
    quad: cat([E(16, 16, 15.5, 2.8)], PM([[19, 14], [8, 1], [12.5, 1], [23, 13.5]]), PM([[5, 14], [1, 8], [4, 8], [9, 14]]),
              EM(15, 7.2, 2.2, 1.1), EM(12.5, 11.3, 2.2, 1.1)),
    // rear-engined T-tail jet
    rearjet: cat([E(16, 16, 14.5, 1.9)], PM([[17, 15], [11, 4], [14.5, 4], [21, 14.5]]), PM([[5, 15], [0.5, 8], [3.5, 8], [8, 15]]),
                 EM(6.5, 12.6, 3.6, 1.2)),
    // twin turboprop: straight high wing, props
    turboprop: cat([E(16, 16, 15, 1.9)], PM([[15, 15], [14, 3], [18.5, 3], [19, 15]]), PM([[4, 15], [2, 10], [4, 10], [7, 15]]),
                   EM(17, 8, 2.5, 1), PM([[20.5, 4.5], [21.5, 4.5], [21.5, 11.5], [20.5, 11.5]])),
    // business jet: swept wing, tail engines
    bizjet: cat([E(16, 16, 14, 1.8)], PM([[17, 15], [11, 5], [14.5, 5], [20, 14.5]]), PM([[5, 15], [2, 9], [4.5, 9], [8, 15]]),
                EM(8, 12.5, 3, 1.1)),
    // single-engine light aircraft with propeller
    light: cat([E(15, 16, 12, 1.7)], PM([[14, 15], [13, 3], [18, 3], [19, 15]]), PM([[4, 15], [2, 10.5], [4.5, 10.5], [7, 15]]),
               [R(28, 10, 29.2, 22)]),
    // twin piston: two engines on the wing, two propellers
    twinprop: cat([E(16, 16, 13, 1.7)], PM([[14, 15], [13, 3.5], [18, 3.5], [19, 15]]), PM([[4, 15], [2, 10.5], [4.5, 10.5], [7, 15]]),
                  EM(16, 9, 3.3, 1.1), PM([[19.4, 6], [20.6, 6], [20.6, 12], [19.4, 12]])),
    heli: [R(2, 5, 30, 6.2), R(15, 6, 17, 9), E(18, 15, 8, 5),
           P([[11, 13], [1, 12.5], [1, 14.5], [11, 16.5]]), E(2, 12, 1.2, 3.5),
           R(10, 23, 27, 24.2), R(14, 19.5, 15.2, 23), R(21, 19.5, 22.2, 23)],
    // swept-wing combat jet: long pointed nose, swept wings and tailplanes
    fighter: cat([P([[31.5, 16], [26, 14.7], [8, 14], [1.5, 14.6], [1.5, 17.4], [8, 18], [26, 17.3]])],
                 PM([[21, 15], [11, 2.5], [7.5, 2.5], [9, 15]]), PM([[6, 15], [1, 9], [0.5, 8], [3, 8], [5.5, 14.5]])),
    // delta-wing jet
    delta: cat([P([[31.5, 16], [24, 14.8], [4, 14.4], [1, 15], [1, 17], [4, 17.6], [24, 17.2]])],
               PM([[22, 15], [2, 2], [1, 3], [1, 15]]), PM([[25, 14.5], [21, 11], [23, 10.5], [27, 14]])),
    // military transport: big body, high straight wing, four engines
    airlifter: cat([E(16, 16, 15, 2.7)], PM([[18, 14], [16.5, 1.5], [21, 1.5], [21.5, 13.5]]), PM([[5, 14], [1.5, 7], [4, 7], [8, 14]]),
                   EM(17.5, 6.2, 2.3, 0.9), EM(17.5, 10.4, 2.3, 0.9)),
    // bomber: long body, long swept wings with engine pods
    bomber: cat([E(16, 16, 15.5, 1.5)], PM([[19, 15], [5, 0.5], [9, 0.5], [22.5, 14.8]]), PM([[5, 15], [1, 10], [3, 10], [7, 15]]),
                EM(14, 7, 2.6, 0.9), EM(11.5, 10.5, 2.6, 0.9)),
    // glider: very long thin wing
    glider: cat([E(15, 16, 14, 1.1)], [R(13, 0.5, 17.5, 31.5)], PM([[3, 15], [1.2, 11], [3.4, 11], [5.5, 15]])),
    balloon: [E(16, 12, 10, 11), P([[13, 23], [19, 23], [18.5, 29], [13.5, 29]]), P([[8, 19], [9, 19], [13, 23], [12.3, 23]]),
              P([[24, 19], [23, 19], [19, 23], [19.7, 23]])]
  };
  SHAPES.generic = SHAPES.narrow;

  function inside(prim, x, y) {
    if (prim.t === "e") { var dx = (x - prim.cx) / prim.rx, dy = (y - prim.cy) / prim.ry; return dx * dx + dy * dy <= 1; }
    var pts = prim.pts, c = false;
    for (var i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      var xi = pts[i][0], yi = pts[i][1], xj = pts[j][0], yj = pts[j][1];
      if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) c = !c;
    }
    return c;
  }

  // Returns Uint8Array(w*h): 1 = lit dot. The silhouette is defined on a 32x32 canvas and scaled to w x h.
  function rasterize(name, w, h) {
    var prims = SHAPES[name] || SHAPES.generic, out = new Uint8Array(w * h);
    for (var y = 0; y < h; y++) for (var x = 0; x < w; x++) {
      var sx = (x + 0.5) * 32 / w, sy = (y + 0.5) * 32 / h;
      for (var k = 0; k < prims.length; k++) if (inside(prims[k], sx, sy)) { out[y * w + x] = 1; break; }
    }
    return out;
  }

  var api = { SHAPES: SHAPES, rasterize: rasterize };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Shapes = api;
})(typeof self !== "undefined" ? self : this);
