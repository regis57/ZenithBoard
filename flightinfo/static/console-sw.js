// SPDX-License-Identifier: GPL-3.0-or-later
// The console's service worker (0.53.0). It is there so that a browser that can install the console as an app offers
// to: Chrome's own Install button asks for one with a fetch handler. It keeps nothing: every page and every answer
// comes from the Pi as before, so nothing stale is ever shown. Browsers register it only over https (a Tailscale or
// domain address); on the Pi's plain http home address the page works without it.
"use strict";
self.addEventListener("install", function () { self.skipWaiting(); });
self.addEventListener("activate", function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener("fetch", function (e) {
  if (e.request.mode === "navigate") e.respondWith(fetch(e.request));
});
