// SPDX-License-Identifier: GPL-3.0-or-later
// The wall's own flags (flightinfo/static/flags.js) as dots, for the weekly posts' pictures (0.36.0), drawn by
// Python: node tools/flag-pixels.js FR US DE ... prints {"FR": [[x, y, rgb], ...], ...}, x and y from -1 (the
// white outline a dark flag gets) to 11 x 7. A country without a flag drawing is left out.
"use strict";
const path = require("path");
global.window = {};
require(path.join(__dirname, "..", "flightinfo", "static", "flags.js"));
const Flags = global.window.Flags;
const out = {};
for (const code of process.argv.slice(2)) {
  if (!/^[A-Z]{2}$/.test(code) || !Flags.known(code)) continue;
  const px = [];
  Flags.draw(code, 0, 0, (x, y, v) => px.push([x, y, v]));
  out[code] = px;
}
process.stdout.write(JSON.stringify(out));
