// SPDX-License-Identifier: GPL-3.0-or-later
// Original generic aircraft silhouettes (drawn from simple geometry, nose to the right) and the
// dot-matrix logo decoder. No airline artwork is bundled: logos come from the user's own library.
(function (root) {
  function E(cx, cy, rx, ry) { return { t: "e", cx: cx, cy: cy, rx: rx, ry: ry }; }
  function P(pts) { return { t: "p", pts: pts }; }
  function M(pts) { return pts.map(function (p) { return [p[0], 32 - p[1]]; }); }   // mirror top <-> bottom
  function PM(pts) { return [P(pts), P(M(pts))]; }
  function cat() { return [].concat.apply([], arguments); }

  var SHAPES = {
    narrow: cat([E(16, 16, 15, 2.1)], PM([[18, 15], [9, 2], [12.5, 2], [22, 14.5]]), PM([[5, 15], [1, 9], [3.5, 9], [8, 15]]),
                [E(14, 8, 2.2, 1.1), E(14, 24, 2.2, 1.1)]),
    wide: cat([E(16, 16, 15.5, 2.8)], PM([[19, 14], [8, 1], [12.5, 1], [23, 13.5]]), PM([[5, 14], [1, 8], [4, 8], [9, 14]]),
              [E(15, 7, 2.2, 1.2), E(12.5, 11, 2, 1.1), E(15, 25, 2.2, 1.2), E(12.5, 21, 2, 1.1)]),
    turboprop: cat([E(16, 16, 15, 1.9)], PM([[15, 15], [14, 3], [18.5, 3], [19, 15]]), PM([[4, 15], [2, 10], [4, 10], [7, 15]]),
                   [E(17, 8, 2.5, 1), E(17, 24, 2.5, 1)], PM([[20.5, 4.5], [21.5, 4.5], [21.5, 11.5], [20.5, 11.5]])),
    bizjet: cat([E(16, 16, 14, 1.8)], PM([[17, 15], [11, 5], [14.5, 5], [20, 14.5]]), PM([[5, 15], [2, 9], [4.5, 9], [8, 15]]),
                [E(8, 12.5, 3, 1.1), E(8, 19.5, 3, 1.1)]),
    light: cat([E(15, 16, 12, 1.7)], PM([[14, 15], [13, 3], [18, 3], [19, 15]]), PM([[4, 15], [2, 10.5], [4.5, 10.5], [7, 15]]),
               [P([[28, 10], [29.2, 10], [29.2, 22], [28, 22]])]),
    heli: [P([[2, 5], [30, 5], [30, 6.2], [2, 6.2]]), P([[15, 6], [17, 6], [17, 9], [15, 9]]), E(18, 15, 8, 5),
           P([[11, 13], [1, 12.5], [1, 14.5], [11, 16.5]]), E(2, 12, 1.2, 3.5),
           P([[10, 23], [27, 23], [27, 24.2], [10, 24.2]]), P([[14, 19.5], [15.2, 19.5], [15.2, 23], [14, 23]]),
           P([[21, 19.5], [22.2, 19.5], [22.2, 23], [21, 23]])]
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

  // Logo file format: {"w":W,"h":H,"palette":["#rrggbb",...],"rows":["..0011..",...]}  ('.' = transparent, 0-9a-z = palette index)
  function decodeLogo(logo) {
    var cells = [];
    if (!logo || !logo.rows || !logo.palette) return { w: 0, h: 0, cells: cells };
    for (var y = 0; y < logo.rows.length; y++) {
      var row = logo.rows[y];
      for (var x = 0; x < row.length; x++) {
        var ch = row[x]; if (ch === "." || ch === " ") continue;
        var col = logo.palette[parseInt(ch, 36)];
        if (col) cells.push({ x: x, y: y, color: parseInt(col.replace("#", ""), 16) });
      }
    }
    return { w: logo.w || 0, h: logo.h || logo.rows.length, cells: cells };
  }

  var api = { SHAPES: SHAPES, rasterize: rasterize, decodeLogo: decodeLogo };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Shapes = api;
})(typeof self !== "undefined" ? self : this);
