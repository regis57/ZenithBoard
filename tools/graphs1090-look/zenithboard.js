// SPDX-License-Identifier: GPL-3.0-or-later
// graphs1090 in ZenithBoard's look (0.43.0): the name in the wall's 5 x 7 dots above graphs1090's own title, links
// back to the wall and the statistics page. Reads font5x7.js, copied beside it; the wall's colour is written in
// zenithboard.css when the look is applied (and again when the colour changes). Changes nothing else on the page.
(function () {
  "use strict";
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
  var wall = location.protocol + "//" + location.hostname + ":8080";
  var h1 = document.querySelector("h1");
  if (h1 && window.Font5x7) {
    var brand = document.createElement("div"); brand.className = "zb-brand";
    var name = document.createElement("div"); name.setAttribute("role", "img"); name.setAttribute("aria-label", "ZenithBoard"); name.appendChild(dots("ZENITHBOARD", 10));
    var sub = document.createElement("div"); sub.className = "zb-sub"; sub.setAttribute("role", "img"); sub.setAttribute("aria-label", "Graphs"); sub.appendChild(dots("GRAPHS", 10));
    var links = document.createElement("div"); links.className = "zb-links";
    [["The wall", wall + "/"], ["Statistics", wall + "/stats"]].forEach(function (l) {
      var a = document.createElement("a"); a.href = l[1]; a.textContent = l[0]; links.appendChild(a);
    });
    brand.appendChild(name); brand.appendChild(sub); brand.appendChild(links);
    h1.parentNode.insertBefore(brand, h1);
    h1.textContent = "graphs1090 · the receiver, the decoder and the Pi, over time";
  }
  document.title = "ZenithBoard graphs";
})();
