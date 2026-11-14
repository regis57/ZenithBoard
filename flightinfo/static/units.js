// SPDX-License-Identifier: GPL-3.0-or-later
// The units, in one place for the pages (lot 0 after 1.0): the wall (format.js) and the statistics (stats.js) each
// carried the factors. The same table as flightinfo/units.py; tests/units_table.json holds both to the same figures.
// Inside ZenithBoard everything is as the decoder gives it: kilometres, feet, knots. Only what is shown is converted.
(function (root) {
  var KM_PER_MI = 1.609344, KM_PER_NM = 1.852, KMH_PER_KT = 1.852, M_PER_FT = 0.3048;
  var SYSTEMS = ["metric", "imperial", "aviation"];       // 0.55.0: aviation = nautical miles, knots, feet
  var KM_PER = { metric: 1, imperial: KM_PER_MI, aviation: KM_PER_NM }, LABEL = { metric: "km", imperial: "mi", aviation: "NM" };
  function system(value, fallback) {
    var u = String(value == null ? "" : value).trim().toLowerCase();
    return SYSTEMS.indexOf(u) >= 0 ? u : (fallback === undefined ? "metric" : fallback);
  }
  function feetAndKnots(units) { return units === "imperial" || units === "aviation"; }
  function distance(km, units) { return km / (KM_PER[units] || 1); }
  function toKm(value, units) { return value * (KM_PER[units] || 1); }
  function distanceLabel(units) { return LABEL[units] || "km"; }
  function metres(feet) { return feet * M_PER_FT; }
  function kmh(knots) { return knots * KMH_PER_KT; }
  var api = { KM_PER_MI: KM_PER_MI, KM_PER_NM: KM_PER_NM, KMH_PER_KT: KMH_PER_KT, M_PER_FT: M_PER_FT, SYSTEMS: SYSTEMS, system: system,
              feetAndKnots: feetAndKnots, distance: distance, toKm: toKm, distanceLabel: distanceLabel, metres: metres, kmh: kmh };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Units = api;
})(this);
