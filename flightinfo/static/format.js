// SPDX-License-Identifier: GPL-3.0-or-later
// Pure formatting helpers (units, compass, text lines). No DOM -> unit-testable with node.
(function (root) {
  var KM_PER_MI = 1.609344, KMH_PER_KT = 1.852, M_PER_FT = 0.3048, MS_PER_FPM = 0.00508;
  var PTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];

  function compass(deg) {
    if (deg === null || deg === undefined || isNaN(deg)) return "";
    return PTS[Math.round((((deg % 360) + 360) % 360) / 22.5) % 16];
  }
  function radiusToKm(value, units) { return units === "imperial" ? value * KM_PER_MI : value; }

  function pad(s, n) { s = String(s); return s.length >= n ? s.slice(0, n) : s + new Array(n - s.length + 1).join(" "); }
  function spread(left, right, width) {   // left text, right-aligned text, total width
    left = String(left); right = String(right);
    var gap = width - left.length - right.length;
    return gap >= 1 ? left + new Array(gap + 1).join(" ") + right : (left + " " + right).slice(0, width);
  }

  function convert(p, units) {
    var imp = units === "imperial";
    return {
      dist: imp ? p.distance_km / KM_PER_MI : p.distance_km, distUnit: imp ? "MI" : "KM",
      speed: p.gs_kt == null ? null : (imp ? p.gs_kt : p.gs_kt * KMH_PER_KT), speedUnit: imp ? "KT" : "KMH",
      alt: p.alt_ft == null ? null : (imp ? p.alt_ft : p.alt_ft * M_PER_FT), altUnit: imp ? "FT" : "M"
    };
  }

  // ------------------------------------------------------------------ places (route rows)
  // The dot font has no accents and few symbols, so place names are folded to plain capitals first.
  var SPECIAL = { "\u00df": "SS", "\u00f8": "O", "\u00d8": "O", "\u00e6": "AE", "\u00c6": "AE", "\u0153": "OE", "\u0152": "OE",
                  "\u0142": "L", "\u0141": "L", "\u0111": "D", "\u0110": "D", "\u0131": "I", "\u00fe": "TH", "\u00f0": "D" };
  function plain(s) {
    s = String(s == null ? "" : s).replace(/[\u00df\u00f8\u00d8\u00e6\u00c6\u0153\u0152\u0142\u0141\u0111\u0110\u0131\u00fe\u00f0]/g, function (c) { return SPECIAL[c]; });
    s = s.normalize ? s.normalize("NFD").replace(/[\u0300-\u036f]/g, "") : s;
    return s.toUpperCase().replace(/['\u2019`]/g, "").replace(/[^A-Z0-9 .,\-\/+():]/g, " ").replace(/\s+/g, " ").replace(/^[ \-]+|[ \-]+$/g, "");
  }
  // Words that say "this is an airport" but tell the reader nothing, so they are dropped to save room.
  var GENERIC = /\b(INTERNATIONAL|INTL|AIRPORT|AIRFIELD|AERODROME|REGIONAL|MUNICIPAL|AEROPORT|AEROPUERTO|AEROPORTO|FLUGHAFEN)\b/g;
  function cut(s, width) {                          // cut at a word boundary when that leaves something readable
    if (s.length <= width) return s;
    var i = s.lastIndexOf(" ", width);
    return (i >= 5 ? s.slice(0, i) : s.slice(0, width)).replace(/[ \-]+$/, "");
  }
  // The airport's name when it fits, otherwise its city, otherwise the name cut to size.
  function placeName(ap, width) {
    if (!ap) return "";
    var name = plain(plain(ap.name).replace(GENERIC, " ")), city = plain(ap.city);
    var options = [name, city].filter(Boolean);
    for (var i = 0; i < options.length; i++) if (options[i].length <= width) return options[i];
    return cut(options[0] || plain(ap.iata || ap.icao), width);
  }
  // Two rows: where the flight comes from, then "\u2192" and where it is going. Blank when the route is unknown.
  function routeLines(route, W) {
    W = W || 14;
    if (!route) return { from: "", to: "" };
    return { from: placeName(route.from, W), to: route.to ? "\u2192" + placeName(route.to, W - 1) : "" };
  }

  // Returns the text rows shown for one aircraft. W = characters per text row (the right-hand column holds the silhouette + photo).
  function planeLines(p, units, index, total, W) {
    W = W || 14;
    var c = convert(p, units), imp = units === "imperial";
    var callsign = (p.flight || p.hex || "UNKNOWN").toUpperCase().slice(0, 7);
    var distTxt = (c.dist < 10 ? c.dist.toFixed(1) : String(Math.round(c.dist))) + c.distUnit;
    var type = [p.type, p.registration].filter(Boolean).join(" ").toUpperCase();
    var alt = p.on_ground ? "GROUND" : (c.alt == null ? "---" : String(Math.round(imp ? c.alt : c.alt / 10) * (imp ? 1 : 10)) + " " + c.altUnit);
    var spd = c.speed == null ? "---" : Math.round(c.speed) + " " + c.speedUnit;
    function fit(s) { return String(s).slice(0, W); }
    var r = routeLines(p.route, W);
    return {
      callsign: callsign,
      airline: fit((p.airline || "").toUpperCase()),
      type: fit(type || ""),
      alt: fit("ALT  " + alt),
      spd: fit("SPD  " + spd),
      from: r.from,
      to: r.to,
      footer: (index + 1) + "/" + total + " " + distTxt + " " + compass(p.bearing).slice(0, 3)      // full-width row: nothing on its right any more
    };
  }

  function radiusLabel(value, units) { return "R " + value + (units === "imperial" ? " MI" : " KM"); }

  var api = { compass: compass, radiusToKm: radiusToKm, convert: convert, planeLines: planeLines,
              radiusLabel: radiusLabel, spread: spread, pad: pad, KM_PER_MI: KM_PER_MI,
              placeName: placeName, routeLines: routeLines, plain: plain };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Fmt = api;
})(typeof self !== "undefined" ? self : this);
