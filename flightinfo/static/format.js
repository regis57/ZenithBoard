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
    var o = {
      dist: imp ? p.distance_km / KM_PER_MI : p.distance_km, distUnit: imp ? "MI" : "KM",
      speed: p.gs_kt == null ? null : (imp ? p.gs_kt : p.gs_kt * KMH_PER_KT), speedUnit: imp ? "KT" : "KMH",
      alt: p.alt_ft == null ? null : (imp ? p.alt_ft : p.alt_ft * M_PER_FT), altUnit: imp ? "FT" : "M",
      vs: p.vrate_fpm == null ? null : (imp ? p.vrate_fpm : p.vrate_fpm * MS_PER_FPM), vsUnit: imp ? "FPM" : "M/S"
    };
    return o;
  }

  // Returns the text rows shown for one aircraft. W = characters per row.
  function planeLines(p, units, index, total, radiusLabel, W) {
    W = W || 20;
    var c = convert(p, units), imp = units === "imperial";
    var callsign = (p.flight || p.hex || "UNKNOWN").toUpperCase().slice(0, 8);
    var distTxt = (c.dist < 10 ? c.dist.toFixed(1) : String(Math.round(c.dist))) + c.distUnit;
    var type = [p.type, p.registration].filter(Boolean).join(" ").toUpperCase();
    var alt = p.on_ground ? "GROUND" : (c.alt == null ? "---" : String(Math.round(imp ? c.alt : c.alt / 10) * (imp ? 1 : 10)) + " " + c.altUnit);
    var spd = c.speed == null ? "---" : Math.round(c.speed) + " " + c.speedUnit;
    var hdg = p.track == null ? "---" : Math.round(p.track) + "° " + compass(p.track);
    var vs = "---";
    if (c.vs != null) {
      var mag = imp ? Math.round(Math.abs(c.vs)) : Math.abs(c.vs).toFixed(1);
      var arrow = Math.abs(c.vs) < (imp ? 100 : 0.5) ? "=" : (c.vs > 0 ? "↑" : "↓");
      vs = arrow + (arrow === "=" ? "" : mag) + " " + c.vsUnit;
    }
    return {
      callsign: callsign,
      dist: distTxt,
      dir: compass(p.bearing),
      type: pad(type || "TYPE UNKNOWN", W).trim(),
      alt: "ALT  " + alt,
      spd: "SPD  " + spd,
      hdg: "HDG  " + hdg,
      vs: "V/S  " + vs,
      footer: spread((index + 1) + "/" + total, radiusLabel, W)
    };
  }

  function radiusLabel(value, units) { return "R " + value + (units === "imperial" ? " MI" : " KM"); }

  var api = { compass: compass, radiusToKm: radiusToKm, convert: convert, planeLines: planeLines,
              radiusLabel: radiusLabel, spread: spread, pad: pad, KM_PER_MI: KM_PER_MI };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Fmt = api;
})(typeof self !== "undefined" ? self : this);
