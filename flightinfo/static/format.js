// SPDX-License-Identifier: GPL-3.0-or-later
// Pure formatting helpers (units, compass, text lines). No DOM -> unit-testable with node.
(function (root) {
  var KM_PER_MI = 1.609344, KMH_PER_KT = 1.852, KM_PER_NM = 1.852, M_PER_FT = 0.3048;
  var PTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];

  function compass(deg) {
    if (deg === null || deg === undefined || isNaN(deg)) return "";
    return PTS[Math.round((((deg % 360) + 360) % 360) / 22.5) % 16];
  }
  // 0.55.0: aviation, as pilots and controllers count: nautical miles, knots, feet
  function radiusToKm(value, units) { return units === "imperial" ? value * KM_PER_MI : units === "aviation" ? value * KM_PER_NM : value; }
  function distUnit(units) { return units === "imperial" ? "MI" : units === "aviation" ? "NM" : "KM"; }

  function pad(s, n) { s = String(s); return s.length >= n ? s.slice(0, n) : s + new Array(n - s.length + 1).join(" "); }
  function spread(left, right, width) {   // left text, right-aligned text, total width
    left = String(left); right = String(right);
    var gap = width - left.length - right.length;
    return gap >= 1 ? left + new Array(gap + 1).join(" ") + right : (left + " " + right).slice(0, width);
  }

  function convert(p, units) {
    var feet = units === "imperial" || units === "aviation";        // knots and feet in both
    return {
      dist: units === "imperial" ? p.distance_km / KM_PER_MI : units === "aviation" ? p.distance_km / KM_PER_NM : p.distance_km,
      distUnit: distUnit(units),
      speed: p.gs_kt == null ? null : (feet ? p.gs_kt : p.gs_kt * KMH_PER_KT), speedUnit: feet ? "KT" : "KMH",
      alt: p.alt_ft == null ? null : (feet ? p.alt_ft : p.alt_ft * M_PER_FT), altUnit: feet ? "FT" : "M"
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
  // A word a cut place name must not end on: "FRANKFURT AM" says less than "FRANKFURT".
  // One word at a time, in a loop: a repeated group here would backtrack (CodeQL); an open bracket and what follows go first.
  var DANGLING = /\s+(?:AM|AN|DE|DES|DU|LA|LE|LES|DI|DEL|DELLA|EL|ST|STE|SUR|SOUS|EN|DER|VON|OF|THE|AND|ET|Y)$/;
  function cut(s, width) {                          // cut at a word boundary when that leaves something readable
    if (s.length <= width) return s;
    var i = s.lastIndexOf(" ", width);
    var t = (i >= 5 ? s.slice(0, i) : s.slice(0, width)).replace(/[ \-]+$/, "");
    var u = t, i0 = u.indexOf(" (");
    if (i0 >= 0) u = u.slice(0, i0);
    while (DANGLING.test(u)) u = u.replace(DANGLING, "");
    return u.length >= 3 ? u : t;
  }
  // The city when it fits, the way a departure board reads ("SAN JOSE", not the airport "JUAN SANTAMARIA"); else the
  // airport's name; else the city cut at a word (0.19.3: the name came first, and the board showed "JUAN SANTAMAR").
  function placeName(ap, width) {
    if (!ap) return "";
    var name = plain(plain(ap.name).replace(GENERIC, " ")), city = plain(ap.city);
    var options = [city, name].filter(Boolean);
    for (var i = 0; i < options.length; i++) if (options[i].length <= width) return options[i];
    return cut(options[0] || plain(ap.iata || ap.icao), width);
  }
  // Two rows: where the flight comes from, then "\u2192" and where it is going. Blank when the route is unknown.
  function routeLines(route, W) {
    W = W || 14;
    if (!route) return { from: "", to: "" };
    return { from: placeName(route.from, W), to: route.to ? "\u2192" + placeName(route.to, W - 1) : "" };
  }

  // The model row: the aircraft's name when it fits ("AIRBUS A321NEO"), else the name without the maker, else the
  // ICAO code with the registration (the decoder alone only knows the code).
  // Longest first: an alternation takes the first branch that matches, so DE HAVILLAND CANADA has to come
  // before DE HAVILLAND or the model row keeps a lonely CANADA.
  var MAKERS = /^(AIRBUS|BOEING|EMBRAER|BOMBARDIER|DE HAVILLAND CANADA|DE HAVILLAND|CESSNA|BEECHCRAFT|BEECH|PIPER|DASSAULT|GULFSTREAM|SAAB|FOKKER|COMAC|MCDONNELL DOUGLAS|CANADAIR|DIAMOND|PILATUS|TEXTRON|LEARJET|HONDA|CIRRUS|ROBINSON|BELL|SIKORSKY|LOCKHEED|ANTONOV|ILYUSHIN|TUPOLEV|SUKHOI|MIL|AGUSTA|LEONARDO|EUROCOPTER|AEROSPATIALE|BRITISH AEROSPACE|BAE SYSTEMS)\s+/;
  function modelLine(p, W) {
    var name = plain(p.type_name || "");
    if (name) {
      if (name.length <= W) return name;
      var rest = name.replace(MAKERS, "");
      return cut(rest, W);
    }
    return [p.type, p.registration].filter(Boolean).join(" ").toUpperCase().slice(0, W);
  }
  // The model row for the dot-matrix wall, which scrolls what does not fit. The maker's name is dropped as soon
  // as the whole thing is too long, because "A-380-800" standing still is read at a glance where "AIRBUS
  // A-380-800" walking past is not. Only a model that is still too long without its maker scrolls.
  function modelScroll(p, W) {
    var name = plain(p.type_name || "");
    if (!name) return modelLine(p, 99);
    if (name.length <= W) return name;
    return name.replace(MAKERS, "");
  }

  // The two top rows (0.19.0): the flight and the registration, one row each, labelled like ALT and SPD under them
  // ("FLT  EZY1234", "REG  G-UZHA"). Before, the callsign alone stood two rows high. An aircraft without a callsign
  // shows its hex code as "HEX"; without a registration, nothing. The same rows on the wall and in the posts.
  function topRows(p, W) {
    W = W || 14;
    var flight = String(p.flight || "").trim().toUpperCase(), reg = String(p.registration || "").trim().toUpperCase();
    return { flight: (flight ? "FLT  " + flight.slice(0, 7) : "HEX  " + String(p.hex || "").toUpperCase()).slice(0, W),
             reg: reg ? ("REG  " + reg).slice(0, W) : "" };
  }

  // Returns the text rows shown for one aircraft. W = characters per text row (the right-hand column holds the silhouette + photo).
  function planeLines(p, units, index, total, W) {
    W = W || 14;
    var c = convert(p, units), imp = units === "imperial" || units === "aviation";
    var callsign = (p.flight || p.hex || "UNKNOWN").toUpperCase().slice(0, 7);
    var distTxt = (c.dist < 10 ? c.dist.toFixed(1) : String(Math.round(c.dist))) + c.distUnit;
    var alt = p.on_ground ? "GROUND" : (c.alt == null ? "---" : String(Math.round(imp ? c.alt : c.alt / 10) * (imp ? 1 : 10)) + " " + c.altUnit);
    var spd = c.speed == null ? "---" : Math.round(c.speed) + " " + c.speedUnit;
    function fit(s) { return String(s).slice(0, W); }
    var r = routeLines(p.route, W), top = topRows(p, W);
    return {
      callsign: callsign,
      flight: top.flight, reg: top.reg,
      airline: fit((p.airline || "").toUpperCase()),
      type: modelLine(p, W),
      // The same two rows uncut. The dot-matrix wall scrolls them when the flag has taken the last characters.
      airlineFull: (p.airline || "").toUpperCase(),
      typeFull: modelScroll(p, W),
      alt: fit("ALT  " + alt),
      spd: fit("SPD  " + spd),
      from: r.from,
      to: r.to,
      footer: (index + 1) + "/" + total + " " + distTxt + " " + compass(p.bearing).slice(0, 3)      // full-width row: nothing on its right any more
    };
  }

  function radiusLabel(value, units) { return "R " + value + " " + distUnit(units); }

  var api = { compass: compass, radiusToKm: radiusToKm, distUnit: distUnit, convert: convert, planeLines: planeLines,
              radiusLabel: radiusLabel, spread: spread, pad: pad, KM_PER_MI: KM_PER_MI,
              placeName: placeName, routeLines: routeLines, plain: plain, modelLine: modelLine, modelScroll: modelScroll, topRows: topRows };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Fmt = api;
})(typeof self !== "undefined" ? self : this);
