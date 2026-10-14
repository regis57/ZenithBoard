// SPDX-License-Identifier: GPL-3.0-or-later
// Two small flags on the wall: where the aircraft is registered, and where it was built.
//
// The country comes from the registration the wall already has (OE-LMP is Austria, N1603 the United States).
// That is a published allocation table, not a lookup: no network, nothing to install, and it works offline.
// A flag is drawn straight into the dot grid at 11 x 7, so it scales with everything else by construction.
//
// At eleven dots wide a flag is bands of colour. Flags carrying an emblem keep their colours and lose the
// emblem: Portugal has no armillary sphere here, the United Kingdom's crosses do not have their true widths.
// They are meant to be recognised across a room, not reproduced. No manufacturer's logo is drawn, in dots or
// otherwise: those are protected marks, and a dotted copy is still a copy. The maker's country is not.
(function (root) {
  "use strict";
  var FW = 11, FH = 7;                                  // the flag itself; the white outline sits one dot around it

  // ---- the registration prefix -> country. Longest prefix first, so CN- is Morocco and not Canada.
  var PREFIX = {
    "A6": "AE", "A7": "QA", "A40": "OM", "A9C": "BH", "AP": "PK", "B": "CN", "C": "CA", "CC": "CL", "CN": "MA",
    "CS": "PT", "CU": "CU", "D": "DE", "D2": "AO", "EC": "ES", "EI": "IE", "EJ": "IE", "EK": "AM", "EP": "IR",
    "ER": "MD", "ES": "EE", "ET": "ET", "EW": "BY", "F": "FR", "G": "GB", "HA": "HU", "HB": "CH", "HC": "EC",
    "HI": "DO", "HK": "CO", "HL": "KR", "HP": "PA", "HS": "TH", "HZ": "SA", "I": "IT", "JA": "JP", "JY": "JO",
    "LN": "NO", "LV": "AR", "LX": "LU", "LY": "LT", "LZ": "BG", "N": "US", "OB": "PE", "OD": "LB", "OE": "AT",
    "OH": "FI", "OK": "CZ", "OM": "SK", "OO": "BE", "OY": "DK", "PH": "NL", "PK": "ID", "PP": "BR", "PR": "BR",
    "PS": "BR", "PT": "BR", "RA": "RU", "RF": "RU", "RP": "PH", "S2": "BD", "S5": "SI", "SE": "SE", "SP": "PL",
    "SU": "EG", "SX": "GR", "TC": "TR", "TF": "IS", "TS": "TN", "TU": "CI", "UK": "UZ", "UR": "UA", "VH": "AU",
    "VN": "VN", "VP": "GB", "VQ": "GB", "VT": "IN", "XA": "MX", "XB": "MX", "XC": "MX", "YL": "LV", "YR": "RO",
    "YU": "RS", "Z3": "MK", "ZA": "AL", "ZK": "NZ", "ZS": "ZA", "4X": "IL", "5A": "LY", "5B": "CY", "5N": "NG",
    "5Y": "KE", "6V": "SN", "7T": "DZ", "9A": "HR", "9H": "MT", "9K": "KW", "9V": "SG", "9Y": "TT"
  };

  // ---- where each maker builds. The marks themselves are protected; a country is not.
  var ORIGIN = {
    "AIRBUS": "EU", "ATR": "EU", "AIRBUS HELICOPTERS": "EU", "EUROCOPTER": "EU",
    "BOEING": "US", "MCDONNELL DOUGLAS": "US", "DOUGLAS": "US", "LOCKHEED": "US", "CESSNA": "US",
    "BEECHCRAFT": "US", "BEECH": "US", "PIPER": "US", "GULFSTREAM": "US", "LEARJET": "US", "CIRRUS": "US",
    "TEXTRON": "US", "BELL": "US", "SIKORSKY": "US", "ROBINSON": "US", "HONDA": "US",
    "EMBRAER": "BR", "BOMBARDIER": "CA", "CANADAIR": "CA", "DE HAVILLAND": "CA", "DE HAVILLAND CANADA": "CA",
    "DASSAULT": "FR", "AEROSPATIALE": "FR", "SAAB": "SE", "FOKKER": "NL", "COMAC": "CN", "ANTONOV": "UA",
    "ILYUSHIN": "RU", "TUPOLEV": "RU", "SUKHOI": "RU", "MIL": "RU", "AGUSTA": "IT", "LEONARDO": "IT",
    "BRITISH AEROSPACE": "GB", "BAE SYSTEMS": "GB", "PILATUS": "CH", "DIAMOND": "AT"
  };

  // ---- the flags themselves, as bands and a few shapes. Colours are the national ones, not web-safe guesses.
  var F = {
    AT: { h: ["#ed2939", "#ffffff", "#ed2939"] },      AL: { plain: "#e41e20", star: "#000000" },
    AE: { h: ["#00732f", "#ffffff", "#000000"], hoist: "#ff0000" },
    AR: { h: ["#74acdf", "#ffffff", "#74acdf"] },      AU: { ensign: "#00247d" },
    BE: { v: ["#000000", "#fdda24", "#ef3340"] },      BG: { h: ["#ffffff", "#00966e", "#d62612"] },
    BR: { brazil: 1 },                                  BY: { h: ["#d22730", "#d22730", "#009639"] },
    CA: { canada: 1 },                                  CH: { swiss: 1 },
    CL: { canton: ["#0039a6", "#ffffff", "#d52b1e"] },  CN: { plain: "#de2910", star: "#ffde00" },
    CO: { h3: ["#fcd116", "#003893", "#ce1126"] },      CY: { plain: "#ffffff", star: "#d57800" },
    CZ: { wedge: ["#ffffff", "#d7141a", "#11457e"] },   DE: { h: ["#000000", "#dd0000", "#ffce00"] },
    DK: { nordic: ["#c8102e", "#ffffff"] },             DZ: { split: ["#006233", "#ffffff"], star: "#d21034" },
    EC: { h3: ["#ffdd00", "#0072ce", "#ef3340"] },      EE: { h: ["#0072ce", "#000000", "#ffffff"] },
    EG: { h: ["#ce1126", "#ffffff", "#000000"] },       ES: { h3: ["#aa151b", "#f1bf00", "#aa151b"] },
    EU: { eu: 1 },                                      FI: { nordic: ["#ffffff", "#002f6c"] },
    FR: { v: ["#002395", "#ffffff", "#ed2939"] },       GB: { union: 1 },
    GR: { greece: 1 },                                  HR: { h: ["#ff0000", "#ffffff", "#171796"] },
    HU: { h: ["#cd2a3e", "#ffffff", "#436f4d"] },       ID: { hh: ["#ff0000", "#ffffff"] },
    IE: { v: ["#169b62", "#ffffff", "#ff883e"] },       IL: { israel: 1 },
    IN: { h3: ["#ff9933", "#ffffff", "#138808"] },      IR: { h3: ["#239f40", "#ffffff", "#da0000"] },
    IS: { nordic: ["#02529c", "#ffffff"] },             IT: { v: ["#008c45", "#f4f5f0", "#cd212a"] },
    JP: { plain: "#ffffff", disc: "#bc002d" },          KR: { plain: "#ffffff", disc: "#cd2e3a" },
    LT: { h: ["#fdb913", "#006a44", "#c1272d"] },       LU: { h: ["#ed2939", "#ffffff", "#00a1de"] },
    LV: { h3: ["#9e3039", "#ffffff", "#9e3039"] },      MA: { plain: "#c1272d", star: "#006233" },
    MT: { split: ["#ffffff", "#cf142b"] },              MX: { v: ["#006847", "#ffffff", "#ce1126"] },
    NG: { v: ["#008751", "#ffffff", "#008751"] },       NL: { h: ["#ae1c28", "#ffffff", "#21468b"] },
    NO: { nordic: ["#ba0c2f", "#ffffff"] },             NZ: { ensign: "#00247d" },
    PL: { hh: ["#ffffff", "#dc143c"] },                 PT: { split: ["#046a38", "#da291c"] },
    QA: { split: ["#ffffff", "#8a1538"] },              RO: { v: ["#002b7f", "#fcd116", "#ce1126"] },
    RS: { h: ["#c6363c", "#0c4076", "#ffffff"] },       RU: { h: ["#ffffff", "#0039a6", "#d52b1e"] },
    SA: { plain: "#006c35" },                           SE: { nordic: ["#006aa7", "#fecc00"] },
    SG: { hh: ["#ed2939", "#ffffff"] },                 SI: { h: ["#ffffff", "#0000ff", "#ff0000"] },
    SK: { h: ["#ffffff", "#0b4ea2", "#ee1c25"] },       TH: { h3: ["#a51931", "#2d2a4a", "#a51931"] },
    TN: { plain: "#e70013", disc: "#ffffff" },          TR: { plain: "#e30a17", star: "#ffffff" },
    UA: { hh: ["#0057b7", "#ffd700"] },                 US: { stars: 1 },
    VN: { plain: "#da251d", star: "#ffff00" },          ZA: { za: 1 }
  };

  function hex(c) { return Math.max(1, parseInt(c.slice(1), 16)); }   // 0 means "unlit", so never return it

  // Draw the flag into a 11 x 7 scratch of colours, then hand it back. The caller places it and outlines it.
  function pixels(code) {
    var f = F[code];
    if (!f) return null;
    var px = new Array(FW * FH), i;
    function fill(x0, y0, w, h, c) {
      for (var y = y0; y < y0 + h; y++) for (var x = x0; x < x0 + w; x++)
        if (x >= 0 && x < FW && y >= 0 && y < FH) px[y * FW + x] = c;
    }
    if (f.v) { fill(0, 0, 4, FH, f.v[0]); fill(4, 0, 3, FH, f.v[1]); fill(7, 0, 4, FH, f.v[2]); }
    else if (f.h) { fill(0, 0, FW, 2, f.h[0]); fill(0, 2, FW, 3, f.h[1]); fill(0, 5, FW, 2, f.h[2]); }
    else if (f.h3) { fill(0, 0, FW, 3, f.h3[0]); fill(0, 3, FW, 2, f.h3[1]); fill(0, 5, FW, 2, f.h3[2]); }
    else if (f.hh) { fill(0, 0, FW, 4, f.hh[0]); fill(0, 4, FW, 3, f.hh[1]); }
    else if (f.split) { fill(0, 0, 4, FH, f.split[0]); fill(4, 0, 7, FH, f.split[1]); }
    else if (f.nordic) { fill(0, 0, FW, FH, f.nordic[0]); fill(3, 0, 2, FH, f.nordic[1]); fill(0, 3, FW, 1, f.nordic[1]); }
    else if (f.swiss) { fill(0, 0, FW, FH, "#ff0000"); fill(5, 1, 1, 5, "#ffffff"); fill(3, 3, 5, 1, "#ffffff"); }
    else if (f.wedge) { fill(0, 0, FW, 4, f.wedge[0]); fill(0, 4, FW, 3, f.wedge[1]); for (i = 0; i < 4; i++) fill(0, 3 - i, i + 1, 1 + 2 * i, f.wedge[2]); }
    else if (f.canton) { fill(0, 0, FW, 4, f.canton[1]); fill(0, 4, FW, 3, f.canton[2]); fill(0, 0, 4, 4, f.canton[0]); fill(1, 1, 1, 1, "#ffffff"); }
    else if (f.greece) { for (i = 0; i < FH; i++) fill(0, i, FW, 1, i % 2 ? "#ffffff" : "#0d5eaf"); fill(0, 0, 5, 3, "#0d5eaf"); fill(2, 0, 1, 3, "#ffffff"); fill(0, 1, 5, 1, "#ffffff"); }
    else if (f.union) { fill(0, 0, FW, FH, "#012169"); fill(0, 0, 1, 1, "#ffffff"); fill(10, 0, 1, 1, "#ffffff"); fill(0, 6, 1, 1, "#ffffff"); fill(10, 6, 1, 1, "#ffffff"); fill(1, 1, 1, 1, "#ffffff"); fill(9, 1, 1, 1, "#ffffff"); fill(1, 5, 1, 1, "#ffffff"); fill(9, 5, 1, 1, "#ffffff"); fill(0, 3, FW, 1, "#c8102e"); fill(5, 0, 1, FH, "#c8102e"); }
    else if (f.stars) { for (i = 0; i < FH; i++) fill(0, i, FW, 1, i % 2 ? "#ffffff" : "#b31942"); fill(0, 0, 5, 3, "#0a3161"); fill(0, 0, 1, 1, "#ffffff"); fill(2, 0, 1, 1, "#ffffff"); fill(4, 0, 1, 1, "#ffffff"); fill(1, 1, 1, 1, "#ffffff"); fill(3, 1, 1, 1, "#ffffff"); fill(0, 2, 1, 1, "#ffffff"); fill(2, 2, 1, 1, "#ffffff"); fill(4, 2, 1, 1, "#ffffff"); }
    else if (f.ensign) { fill(0, 0, FW, FH, f.ensign); fill(0, 0, 5, 3, "#012169"); fill(2, 0, 1, 3, "#ffffff"); fill(0, 1, 5, 1, "#ffffff"); fill(8, 3, 1, 1, "#ffffff"); fill(7, 5, 1, 1, "#ffffff"); }
    else if (f.eu) { fill(0, 0, FW, FH, "#003399"); var ring = [[5, 0], [7, 1], [8, 3], [7, 5], [5, 6], [3, 5], [2, 3], [3, 1]]; for (i = 0; i < ring.length; i++) fill(ring[i][0], ring[i][1], 1, 1, "#ffcc00"); }
    else if (f.brazil) { fill(0, 0, FW, FH, "#009b3a"); fill(2, 1, 7, 5, "#fedf00"); fill(3, 2, 5, 3, "#fedf00"); fill(4, 2, 3, 3, "#002776"); }
    else if (f.canada) { fill(0, 0, FW, FH, "#ffffff"); fill(0, 0, 3, FH, "#ff0000"); fill(8, 0, 3, FH, "#ff0000"); fill(5, 1, 1, 5, "#ff0000"); fill(4, 2, 3, 2, "#ff0000"); }
    else if (f.israel) { fill(0, 0, FW, FH, "#ffffff"); fill(0, 0, FW, 1, "#0038b8"); fill(0, 6, FW, 1, "#0038b8"); fill(5, 2, 1, 1, "#0038b8"); fill(4, 3, 3, 1, "#0038b8"); fill(5, 4, 1, 1, "#0038b8"); }
    else if (f.za) { fill(0, 0, FW, 3, "#e03c31"); fill(0, 4, FW, 3, "#002395"); fill(0, 3, FW, 1, "#007749"); fill(0, 0, 3, FH, "#007749"); fill(0, 2, 2, 3, "#ffb81c"); fill(0, 3, 1, 1, "#000000"); }
    else if (f.plain) { fill(0, 0, FW, FH, f.plain); }
    if (f.hoist) fill(0, 0, 2, FH, f.hoist);
    if (f.disc) { fill(4, 2, 3, 3, f.disc); fill(5, 1, 1, 5, f.disc); }
    if (f.star) { fill(5, 2, 1, 1, f.star); fill(4, 3, 3, 1, f.star); fill(4, 4, 1, 1, f.star); fill(6, 4, 1, 1, f.star); }
    for (i = 0; i < px.length; i++) if (!px[i]) px[i] = "#000000";
    return px;
  }

  // Is this colour lost against a black wall? Only true black and its neighbours: a navy blue is dim but still
  // visible, and outlining every flag with a dark blue band would put a white box around most of Europe.
  function dark(c) {
    var v = parseInt(c.slice(1), 16);
    return (((v >> 16 & 255) * 299 + (v >> 8 & 255) * 587 + (v & 255) * 114) / 1000) < 20;
  }

  root.Flags = {
    W: FW, H: FH,

    // "OE-LMP" -> "AT". The part before the dash is the prefix; without a dash the leading letters are.
    country: function (reg) {
      reg = String(reg || "").toUpperCase().replace(/\s+/g, "");
      if (!reg) return null;
      var head = reg.indexOf("-") > 0 ? reg.slice(0, reg.indexOf("-")) : (reg.match(/^[A-Z]+/) || [""])[0];
      while (head.length) {
        if (PREFIX[head]) return PREFIX[head];
        head = head.slice(0, -1);
      }
      return null;
    },

    // "AIRBUS A321NEO" -> "EU". Only the maker's country; never the maker's mark.
    origin: function (typeName) {
      var s = String(typeName || "").toUpperCase();
      var best = null;
      for (var k in ORIGIN) if (Object.prototype.hasOwnProperty.call(ORIGIN, k)) {
        if (s.indexOf(k) === 0 && (!best || k.length > best.length)) best = k;
      }
      return best ? ORIGIN[best] : null;
    },

    known: function (code) { return !!F[code]; },

    // Draws the flag with put(x, y, value). A flag holding a dark colour at its edge gets a white outline,
    // or the black band of Germany and Belgium would simply be a hole in the wall.
    draw: function (code, x, y, put) {
      var px = pixels(code);
      if (!px) return false;
      var needsOutline = false, i, j;
      for (i = 0; i < FW; i++) if (dark(px[i]) || dark(px[(FH - 1) * FW + i])) needsOutline = true;
      for (j = 0; j < FH; j++) if (dark(px[j * FW]) || dark(px[j * FW + FW - 1])) needsOutline = true;
      if (needsOutline) {
        for (i = -1; i <= FW; i++) { put(x + i, y - 1, 0xffffff); put(x + i, y + FH, 0xffffff); }
        for (j = 0; j < FH; j++) { put(x - 1, y + j, 0xffffff); put(x + FW, y + j, 0xffffff); }
      }
      for (j = 0; j < FH; j++) for (i = 0; i < FW; i++) put(x + i, y + j, hex(px[j * FW + i]));
      return true;
    }
  };
})(typeof window !== "undefined" ? window : this);
