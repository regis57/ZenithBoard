// SPDX-License-Identifier: GPL-3.0-or-later
// graphs1090 in ZenithBoard's look (0.43.0): the name in the wall's 5 x 7 dots above graphs1090's own title, links
// back to the wall and the statistics page. Reads font5x7.js, copied beside it; the wall's colour is written in
// zenithboard.css when the look is applied (and again when the colour changes). Changes nothing else on the page.
// 0.47.0: in the visitor's language (i18n.js, copied beside it with the catalogues in zb-i18n/; zb-lang.js says the
// Pi's default language and the ones it has, written when the look is applied).
(function () {
  "use strict";
  var I = window.ZBI18N, conf = window.ZB_I18N_CONF || {};
  var wall = location.protocol + "//" + location.hostname + ":" + (conf.wallPort || 8080);
  if (!I) return draw(function (s) { return s; });
  // dir false: graphs1090's own page keeps its layout; only ZenithBoard's brand turns right to left (0.48.0)
  I.start({ part: "graphs", base: "zb-i18n/", config: { lang: conf.lang || "", langs: conf.langs || [] }, flagBase: wall + "/flags/",
    staticBase: wall + "/static/", dir: false }, function () { draw(I.t); });
  function draw(t) {
    var NS = "http://www.w3.org/2000/svg";
    function dots(text, pitch) {
      var F = window.Font5x7, s = document.createElementNS(NS, "svg");
      var cols = text.length * 6 + 1, rows = 9;
      s.setAttribute("viewBox", "0 0 " + cols * pitch + " " + rows * pitch);
      s.setAttribute("aria-hidden", "true");
      for (var i = 0; i < text.length; i++) {
        var g = (F && (F.GLYPHS[text[i]] || F.GLYPHS[" "])) || [];
        for (var y = 0; y < 7; y++) for (var x = 0; x < 5; x++) {
          var lit = g[y] && g[y][x] === "#", c = document.createElementNS(NS, "circle");
          c.setAttribute("class", lit ? "on" : "off");
          c.setAttribute("cx", (1 + i * 6 + x + 0.5) * pitch); c.setAttribute("cy", (1 + y + 0.5) * pitch);
          c.setAttribute("r", pitch * (lit ? 0.38 : 0.27));
          s.appendChild(c);
        }
      }
      return s;
    }
    var h1 = document.querySelector("h1");
    if (h1 && window.Font5x7) {
      var brand = document.createElement("div"); brand.className = "zb-brand";
      if (I && I.rtl()) brand.dir = "rtl";
      var name = document.createElement("div"); name.setAttribute("role", "img"); name.setAttribute("aria-label", "ZenithBoard"); name.appendChild(dots("ZENITHBOARD", 10));
      var sub = document.createElement("div"); sub.className = "zb-sub"; sub.setAttribute("role", "img"); sub.setAttribute("aria-label", t("Graphs")); var gw = t("GRAPHS"); sub.appendChild(dots(/^[A-Z0-9 ]+$/.test(gw) ? gw : "GRAPHS", 10));
      var links = document.createElement("div"); links.className = "zb-links";
      var q = I && I.lang() !== "en" ? "?lang=" + I.lang() : "";      // the other origin keeps the language chosen here
      [[t("The wall"), wall + "/" + q], [t("Statistics"), wall + "/stats" + q]].forEach(function (l) {
        var a = document.createElement("a"); a.href = l[1]; a.textContent = l[0]; links.appendChild(a);
      });
      if (I) links.appendChild(I.picker());
      brand.appendChild(name); brand.appendChild(sub); brand.appendChild(links);
      h1.parentNode.insertBefore(brand, h1);
      h1.textContent = t("graphs1090 · the receiver, the decoder and the Pi, over time");
    }
    // graphs1090's own period buttons and panel titles, by their English text (the graphs themselves are pictures
    // its script draws: they stay in English)
    var THEIRS = {
      "2 hours": t("2 hours"),
      "8 hours": t("8 hours"),
      "24 hours": t("24 hours"),
      "48 hours": t("48 hours"),
      "7 days": t("7 days"),
      "14 days": t("14 days"),
      "30 days": t("30 days"),
      "3 months": t("3 months"),
      "6 months": t("6 months"),
      "1 year": t("1 year"),
      "2 years": t("2 years"),
      "3 years": t("3 years"),
      "5 years": t("5 years"),
      "10 years": t("10 years"),
      "Crosshair": t("Crosshair"),
      "ADS-B 1090 Graphs": t("ADS-B 1090 Graphs"),
      "UAT 978 Graphs": t("UAT 978 Graphs"),
      "Airspy Graphs": t("Airspy Graphs"),
      "System Graphs": t("System Graphs")
    };
    Array.prototype.forEach.call(document.querySelectorAll(".btn-group .btn, .panel-heading"), function (el) {
      var k = el.textContent.trim();
      if (Object.prototype.hasOwnProperty.call(THEIRS, k) && THEIRS[k] !== k) el.textContent = THEIRS[k];
    });
    document.title = t("ZenithBoard graphs");
  }
})();
