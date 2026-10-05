#!/usr/bin/env node
// SPDX-License-Identifier: GPL-3.0-or-later
// Builds the demo's mock "photos" (flightinfo/demo/photos/*.svg) from the same side-view drawings the wall uses,
// so each mock photo shows the right aircraft model. Run:  node tools/make_demo_photos.js
"use strict";
const fs = require("fs"), path = require("path");
const K = require("../flightinfo/static/scene.js");

const OUT = path.join(__dirname, "..", "flightinfo", "demo", "photos");
// file, shape, variant, colour seed (same seed the wall uses: airline code, else hex), military
const PHOTOS = [
  ["zza210", "narrow", null, "ZZA"], ["zzb88k", "bizjet", null, "ZZB"], ["zzc404", "quad", "deck", "ZZC"],
  ["zza77t", "turboprop", null, "ZZA"], ["samu34", "heli", null, "3e1a2b"], ["c172", "light", "high", "dd0013"]
];

function rng(seed) { let r = seed >>> 0; return () => { r = (Math.imul(r, 1664525) + 1013904223) >>> 0; return r / 4294967296; }; }
function cloud(cx, cy, s, a) {
  return [[-1.1, 0.18, 0.55], [-0.5, -0.12, 0.75], [0.25, -0.24, 0.85], [0.95, -0.02, 0.66], [1.45, 0.2, 0.46], [0.2, 0.2, 0.7]]
    .map(c => `<circle cx="${(cx + c[0] * s).toFixed(1)}" cy="${(cy + c[1] * s).toFixed(1)}" r="${(c[2] * s).toFixed(1)}" fill="#fff" fill-opacity="${a}"/>`).join("");
}

PHOTOS.forEach(([file, shape, variant, seed], n) => {
  const r = rng(100 + n * 7), W = 420, H = 280, zoom = K.ZOOM[shape] || 1;
  const pal = K.palette(false, seed), ops = K.profileOps(shape, variant);
  const w = Math.min(W * 0.84, 300 * zoom), x = (W - w) / 2, y = 112 - w * 0.2;
  let clouds = "";
  for (let i = 0; i < 6; i++) clouds += cloud(r() * W, 30 + r() * 150, 16 + r() * 22, (0.55 + r() * 0.35).toFixed(2));
  const hills = `<path d="M0 232 Q70 200 140 224 T290 214 T420 226 V280 H0Z" fill="#6f8f72"/><path d="M0 250 Q100 232 210 248 T420 244 V280 H0Z" fill="#587a5c"/>`;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
<defs><linearGradient id="s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3b86dc"/><stop offset="1" stop-color="#cfe9ff"/></linearGradient></defs>
<rect width="${W}" height="${H}" fill="url(#s)"/>${clouds}${hills}
<g transform="translate(${x.toFixed(1)} ${y.toFixed(1)}) rotate(-3 ${(w / 2).toFixed(1)} ${(w * 0.2).toFixed(1)}) scale(${(w / 100).toFixed(4)})">${K.svgOps(ops, pal)}</g>
<text x="8" y="272" font-family="sans-serif" font-size="10" fill="#fff" fill-opacity=".8">DEMO MOCK-UP</text></svg>\n`;
  fs.writeFileSync(path.join(OUT, file + ".svg"), svg);
  console.log("wrote", file + ".svg");
});
