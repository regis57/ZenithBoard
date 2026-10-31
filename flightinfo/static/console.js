// SPDX-License-Identifier: GPL-3.0-or-later
// The web console (0.39.0): ZenithBoard's settings from a browser or a phone on the home network.
// One section on screen at a time (a side bar on a computer, tabs at the bottom of a phone), the wall's colour on
// black. Every change is one action from the Pi's fixed list (flightinfo/console_actions.py), run by the Pi's root
// helper as the same `zenithboard` command as over SSH; what it prints is shown in the Activity drawer as it comes.
// Reads /console/api/*; draws nothing it was not told by the Pi. 0.47.0: started once its language is known
// (flightinfo/static/i18n.js), so every word below is already in it.
window.ZBI18N.start({ part: "console" }, function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  // 0.47.0: every word shown goes through t() (the English text is the key; flightinfo/static/i18n.js)
  var I = window.ZBI18N, t = I.t, tn = I.tn, num = I.num;
  var S = {
    session: null, cfg: {}, facts: {}, factsAt: 0, catalog: {}, sections: [], section: "overview",
    jobs: {}, pending: {}, wanted: {}, inline: new Map(), drawerJob: null, activity: null, sessions: null, warnedQueue: {}
  };
  var SECTION_ICON = { overview: "overview", wall: "wall", receiver: "antenna", sharing: "share", reliability: "shield", system: "gear" };
  var THEME_HEX = { amber: "#ffb000", green: "#39ff6a", red: "#ff3b30", white: "#e8e8e8", turquoise: "#00d6d7" };

  // ---- small helpers
  var ICONS = {
    overview: '<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    wall: '<rect x="2.5" y="5" width="19" height="12" rx="1.5"/><path d="M8 21h8M12 17v4"/><circle cx="7" cy="9" r=".6"/><circle cx="10" cy="9" r=".6"/><circle cx="13" cy="9" r=".6"/><circle cx="7" cy="12.5" r=".6"/><circle cx="10" cy="12.5" r=".6"/>',
    antenna: '<path d="M12 12v9M8 21h8"/><circle cx="12" cy="10" r="2"/><path d="M7.8 5.8a6 6 0 0 0 0 8.4M16.2 5.8a6 6 0 0 1 0 8.4M5 3a10 10 0 0 0 0 14M19 3a10 10 0 0 1 0 14"/>',
    share: '<circle cx="18" cy="5" r="2.5"/><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="19" r="2.5"/><path d="M8.2 10.8l7.6-4.6M8.2 13.2l7.6 4.6"/>',
    shield: '<path d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9L7 7M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
    activity: '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    out: '<path d="M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4M10 8l-4 4 4 4M6 12h10"/>',
    chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    map: '<path d="M9 4L3 6.5v13.5l6-2.5 6 2.5 6-2.5V4l-6 2.5z"/><path d="M9 4v13.5M15 6.5V20"/>',
    graph: '<path d="M3 3v18h18"/><path d="M6 15l4-5 4 3 5-7"/>',
    link: '<path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/>',
    picture: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 16l-5-5-9 9"/>',
    phone: '<rect x="6" y="2.5" width="12" height="19" rx="2.5"/><path d="M11 18.5h2"/>',
    plane: '<path d="M10.5 3.5c0-.8.7-1.5 1.5-1.5s1.5.7 1.5 1.5V9l7 4v2l-7-2v4.5l2.5 2V21L12 20l-4 1v-1.5l2.5-2V13l-7 2v-2l7-4z"/>',
    terminal: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M13 15h4"/>',
    power: '<path d="M12 3v8"/><path d="M6.3 7a8 8 0 1 0 11.4 0"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.5 3.8 5.5 3.8 9s-1.3 6.5-3.8 9c-2.5-2.5-3.8-5.5-3.8-9s1.3-6.5 3.8-9z"/>'
  };
  function ico(name) {
    var s = document.createElement("span");
    s.className = "ico";
    s.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true">' + (ICONS[name] || "") + "</svg>";
    return s;
  }
  function h(tag, attrs) {
    var n = document.createElement(tag);
    attrs = attrs || {};
    Object.keys(attrs).forEach(function (k) {
      var v = attrs[k];
      if (v === undefined || v === null || v === false) return;
      if (k === "class") n.className = v;
      else if (k === "text") n.textContent = v;
      // 0.99.18 (review B10): a button waiting for the Pi says so with aria-disabled and keeps its keyboard focus, where
      // `disabled` threw the focus out to the page; the click guard below keeps it from doing anything meanwhile
      else if (k === "disabled" && tag === "button") n.setAttribute("aria-disabled", "true");
      else if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v === true ? "" : v);
    });
    for (var i = 2; i < arguments.length; i++) add(n, arguments[i]);
    return n;
  }
  function add(n, c) {
    if (c === null || c === undefined || c === false) return;
    if (Array.isArray(c)) { c.forEach(function (x) { add(n, x); }); return; }
    n.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c);
  }
  function on(v) { return String(v).toLowerCase() === "1" || String(v).toLowerCase() === "on"; }
  function host() { return location.hostname.indexOf(":") >= 0 ? "[" + location.hostname + "]" : location.hostname; }
  function dur(s) {
    s = Math.max(0, Math.round(s));
    if (s < 90) return t("{n} s", { n: s });
    if (s < 5400) return t("{n} min", { n: Math.round(s / 60) });
    if (s < 172800) return t("{n} h", { n: Math.round(s / 3600) });
    return t("{d} d {h} h", { d: Math.floor(s / 86400), h: Math.round((s % 86400) / 3600) });
  }
  function ago(at) { return at ? t("{time} ago", { time: dur(Date.now() / 1000 - at) }) : t("never"); }
  function size(mb) { mb = Number(mb); if (!(mb >= 0)) return "–"; return mb >= 2048 ? t("{n} GB", { n: num(mb / 1024, 1) }) : t("{n} MB", { n: num(mb, 0) }); }
  // words the Pi answers in English (states, colours, choices), shown in the page's language
  var WORD = { on: t("on"), off: t("off"), running: t("running"), queued: t("queued"), refused: t("refused"), done: t("done"),
    "not installed": t("not installed"), posting: t("posting"), amber: t("amber"), green: t("green"), red: t("red"), white: t("white"),
    turquoise: t("turquoise"), metric: t("metric"), imperial: t("imperial"), aviation: t("aviation"), dots: t("dot matrix"), flap: t("split-flap"), world: t("world"),
    us: t("United States"), daily: t("daily"), weekly: t("weekly"), monthly: t("monthly"),
    factual: t("factual"), story: t("story"), board: t("board"), spotter: t("spotter"), lookup: t("lookup"), custom: t("your own") };
  // graphs1090 answers on another port, so another origin: the language goes with the link
  function langQ() { return I.lang() !== "en" ? "?lang=" + encodeURIComponent(I.lang()) : ""; }
  // the summary's posts by what they show (0.48.0, the owner: "Post 2" alone said nothing)
  function postName(n) {
    return { "1": t("Post 1 · The period ↗"), "2": t("Post 2 · Cargo & business jets ↗"), "3": t("Post 3 · Military ↗"),
      "4": t("Post 4 · General aviation ↗") }[String(n)] || t("Post {n} ↗", { n: n });
  }
  function word(v) { return Object.prototype.hasOwnProperty.call(WORD, v) ? WORD[v] : (v === undefined || v === null || v === "" ? "?" : String(v)); }
  function dayName(d) {          // mon..sun in the page's language, from the browser's own calendar data
    var i = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"].indexOf(d);
    if (i < 0) return d;
    try { return new Date(Date.UTC(2024, 0, 1 + i)).toLocaleDateString(I.locale(), { weekday: "short", timeZone: "UTC" }); } catch (e) { return d; }
  }
  function clock(at) { var d = new Date(at * 1000); return ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2); }

  var toastTimer = null;
  function toast(msg, bad) {
    var el = $("toast");
    el.textContent = msg; el.className = "toast" + (bad ? " bad" : ""); el.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(function () { el.hidden = true; }, bad ? 7000 : 3500);
  }

  // ---- the brand: the name in the 5 x 7 dots of the wall, the unlit ones faint behind (as on /stats)
  function dots(mount, text, pitch) {
    var F = window.Font5x7, NS = "http://www.w3.org/2000/svg";
    if (!mount) return;
    if (!F) { mount.textContent = text; return; }
    var cols = text.length * 6 + 1, rows = 9, r = pitch * 0.38;
    var s = document.createElementNS(NS, "svg");
    s.setAttribute("viewBox", "0 0 " + cols * pitch + " " + rows * pitch); s.setAttribute("aria-hidden", "true");
    for (var i = 0; i < text.length; i++) {
      var g = F.GLYPHS[text[i]] || F.GLYPHS[" "] || [];
      for (var y = 0; y < 7; y++) for (var x = 0; x < 5; x++) {
        var lit = g[y] && g[y][x] === "#", c = document.createElementNS(NS, "circle");
        c.setAttribute("class", lit ? "d-on" : "d-off");
        c.setAttribute("cx", (1 + i * 6 + x + 0.5) * pitch); c.setAttribute("cy", (1 + y + 0.5) * pitch); c.setAttribute("r", lit ? r : r * 0.7);
        s.appendChild(c);
      }
    }
    mount.innerHTML = ""; mount.appendChild(s);
  }
  function theme(name) {
    var hex = THEME_HEX[name] || THEME_HEX.amber, st = document.documentElement.style;
    var n = parseInt(hex.slice(1), 16), c = [(n >> 16) & 255, (n >> 8) & 255, n & 255];
    st.setProperty("--on", hex);
    st.setProperty("--on-hot", "#" + c.map(function (v) { return ("0" + Math.round(v + (255 - v) * 0.4).toString(16)).slice(-2); }).join(""));
    st.setProperty("--on-dim", "rgba(" + c.join(",") + ",.14)");
  }

  // ---- talking to the Pi
  function api(path, opts) {
    opts = opts || {};
    var init = { method: opts.method || (opts.body !== undefined ? "POST" : "GET"), credentials: "same-origin", headers: {}, cache: "no-store" };
    if (opts.body !== undefined) {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(opts.body);
      if (S.session && S.session.csrf) init.headers["X-ZB-CSRF"] = S.session.csrf;
    }
    return fetch("/console/api/" + path, init).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (data) {
        if (r.status === 401 && S.session && path !== "login" && path !== "pair/redeem") signedOut();
        return { status: r.status, ok: r.ok, data: data || {} };
      });
    });
  }
  function signedOut() {
    S.session = null;
    $("app").hidden = true; closeDrawer(); closeModal();
    gate("login", t("You were signed out (the session ended, or someone signed everyone out)."));
  }

  // ---- before signing in
  function gate(which, msg) {
    $("gate").hidden = false; $("app").hidden = true;
    ["gate-off", "login", "gate-nopw", "gate-pairing", "gate-help", "gate-lang"].forEach(function (id) { $(id).hidden = true; });
    if (which === "lang") $("gate-lang").hidden = false;
    if (which === "off") $("gate-off").hidden = false;
    if (which === "pairing") $("gate-pairing").hidden = false;
    if (which === "nopw") { $("gate-nopw").hidden = false; $("gate-help").hidden = false; }
    if (which === "login") { $("login").hidden = false; $("gate-help").hidden = false; setTimeout(function () { $("pw").focus(); }, 50); }
    var err = $("gate-err");
    $("login-err").hidden = true;
    if (msg) { err.textContent = msg; err.hidden = false; } else err.hidden = true;
  }
  $("pw-eye").addEventListener("click", function () {
    var p = $("pw"); p.type = p.type === "password" ? "text" : "password";
    this.setAttribute("aria-label", p.type === "password" ? t("Show the password") : t("Hide the password"));
  });
  $("login").addEventListener("submit", function (e) {
    e.preventDefault();
    var b = $("login-go"); b.disabled = true;
    api("login", { body: { password: $("pw").value } }).then(function (r) {
      b.disabled = false;
      if (r.ok) { $("pw").value = ""; return boot(); }
      $("login-err").textContent = t(r.data.error || "Could not sign in."); $("login-err").hidden = false;
      $("pw").select();
    }).catch(function () { b.disabled = false; $("login-err").textContent = t("The Pi does not answer."); $("login-err").hidden = false; });
  });

  var WRITE_MSG = t("The wall cannot write its console folder yet: pairing and changes will fail. Over SSH: sudo systemctl restart zenithboard-flightinfo");
  // 0.40.1: the version running on this Pi, linked to its release notes on GitHub (the releases page when unknown)
  function showVersion(a, v) {
    if (!a) return;
    var ok = /^\d+\.\d+\.\d+$/.test(String(v || ""));
    a.textContent = "ZenithBoard " + (ok ? v : "");
    a.href = "https://github.com/regis57/ZenithBoard/releases" + (ok ? "/tag/v" + v : "");
    a.title = ok ? t("What changed in {version}", { version: v }) : t("ZenithBoard's releases");
  }
  function boot() {
    dots($("gate-logo"), "ZENITHBOARD", 10); dots($("gate-sub"), "CONSOLE", 10);
    var gl = $("gate-lang-pick"); if (gl && !gl.firstChild) gl.appendChild(I.picker());
    var m = /[#&]pair=([A-Za-z0-9_-]{16,64})/.exec(location.hash), pairTok = m && m[1];
    var ma = /[#&]approve=([A-Za-z0-9_-]{8,40})/.exec(location.hash);
    if (ma) S.approveId = ma[1];                                          // answered once signed in (0.40.0)
    if (pairTok || ma) history.replaceState(null, "", location.pathname);   // a used link is not kept in the history
    return api("session").then(function (r) {
      var s = r.data;
      showVersion($("gate-version"), s.version);
      if (s.enabled === false) return gate("off");
      S.unwritable = s.writable === false;
      if (pairTok) {
        gate("pairing");
        return api("pair/redeem", { body: { token: pairTok } }).then(function (p) {
          if (p.ok) return boot();
          gate(s.has_password ? "login" : "nopw", t(p.data.error || "This pairing code did not work."));
        });
      }
      S.phoneSignin = !!s.phone_signin;
      // 0.47.0: the very first visit, before anything else: the language, by its own name (the Pi has none yet and
      // this browser chose none); chosen, it is this browser's, and the Pi's default once signed in
      if (!s.signed_in && !I.saved() && !I.serverLang() && I.langs().length > 1) {
        var box = $("gate-lang-list"); box.innerHTML = ""; box.appendChild(I.chooser());
        return gate("lang");
      }
      if (!s.signed_in) {
        gate(s.has_password ? "login" : "nopw", S.unwritable ? WRITE_MSG : (S.approveId ? t("Sign this phone in first; then the computer's request is shown.") : null));
        if (S.phoneSignin && !S.approveId) phoneSignin();
        return;
      }
      stopPhoneSignin();
      S.session = s;
      startApp();
    }).catch(function () { gate("login", t("The Pi does not answer. Is the wall running?")); });
  }

  // ---- 0.40.0: a computer signed in by a phone. This page (on the computer) shows a QR code and a four-digit code;
  // a phone already signed in scans it, checks the code and says yes; this page, asking with its own secret, is then
  // signed in. The QR code carries the request's name only, never the secret.
  var PS = { timer: null, poll: null, renewals: 0 };
  function stopPhoneSignin() { clearInterval(PS.timer); clearInterval(PS.poll); PS.timer = PS.poll = null; var b = $("gate-phone"); if (b) b.hidden = true; }
  function phoneSignin() {
    stopPhoneSignin();
    var box = $("gate-phone"); if (!box) return;
    api("approve/request", { body: {} }).then(function (r) {
      if (!r.ok) { box.hidden = true; return; }
      var d = r.data, until = Date.now() + d.seconds * 1000;
      var url = location.protocol + "//" + location.host + "/console/#approve=" + d.id;
      var qr = $("gate-qr"), count = $("gate-count"), note = $("gate-phone-note");
      qr.innerHTML = ""; qr.appendChild(qrSvg(url)); qr.hidden = false;
      $("gate-code").textContent = d.code; note.textContent = t("Scan it with a phone already signed in to the console, check that it shows {code}, and say yes.", { code: d.code });
      box.hidden = false;
      PS.timer = setInterval(function () {
        var left = Math.max(0, Math.round((until - Date.now()) / 1000));
        count.textContent = Math.floor(left / 60) + ":" + ("0" + left % 60).slice(-2);
        if (!left) {
          stopPhoneSignin(); box.hidden = false;
          // a page left open renews its code a few times, then waits for a click (no endless requests)
          if (PS.renewals++ < 5 && document.visibilityState === "visible") phoneSignin();
          else {
            qr.hidden = true; count.textContent = ""; $("gate-code").textContent = ""; note.textContent = t("The code is out of date.") + " ";
            note.appendChild(h("button", { type: "button", "class": "btn", text: t("New code"), onclick: function () { PS.renewals = 0; phoneSignin(); } }));
          }
        }
      }, 1000);
      PS.poll = setInterval(function () {
        api("approve/poll", { body: { id: d.id, secret: d.secret } }).then(function (p) {
          var st = p.data.state;
          if (st === "approved") { stopPhoneSignin(); boot(); }
          else if (st === "refused") { stopPhoneSignin(); box.hidden = false; qr.hidden = true; note.textContent = t("Refused on the phone."); count.textContent = ""; }
        });
      }, 2000);
    });
  }
  function approveComputer(id) {
    api("approve?id=" + encodeURIComponent(id)).then(function (r) {
      if (!r.ok) return toast(t(r.data.error || "This sign-in code is out of date."), true);
      var d = r.data;
      if (d.state !== "waiting") return toast(t("This computer's request is {state}: it shows a new code.", { state: d.state }), true);
      function answer(yes) {
        closeModal();
        api("approve", { body: { id: id, yes: yes } }).then(function (a) {
          if (!a.ok) toast(t(a.data.error || "Too late: the computer shows a new code."), true);
          else toast(yes ? t("{name} is signed in.", { name: d.label }) : t("Refused."));
          if (yes) { S.sessions = null; }
        });
      }
      openModal(h("div", null,
        h("header", null, h("h2", { text: t("Sign a computer in") }), h("button", { type: "button", "class": "ghost", "aria-label": t("Close"), text: "×", onclick: function () { closeModal(); } })),
        h("div", { "class": "modal-body" },
          h("p", { text: t("Sign in {name} at {ip}?", { name: d.label, ip: d.ip }) }),
          h("div", { "class": "count", text: d.code }),
          h("p", { "class": "qr-note", text: t("Say yes only if the computer in front of you shows this same code. It is signed in for a week (a day unused); System → Signed in signs it out.") })),
        h("div", { "class": "modal-foot" },
          h("button", { type: "button", "class": "btn", text: t("Refuse"), onclick: function () { answer(false); } }),
          h("button", { type: "button", "class": "primary", text: t("Sign it in"), onclick: function () { answer(true); } }))));
    });
  }

  // ---- signed in
  function startApp() {
    $("gate").hidden = true; $("app").hidden = false;
    dots($("side-logo"), "ZB", 9); dots($("bar-logo"), "ZB", 6);
    var bl = $("bar-lang"); if (bl && !bl.firstChild) bl.appendChild(I.picker());
    document.querySelectorAll("[data-ico]").forEach(function (n) { if (!n.firstChild) n.appendChild(ico(n.getAttribute("data-ico")).firstChild); });
    showVersion($("side-version"), S.session.version);
    loadState().then(function () {
      route();
      if (S.unwritable) toast(WRITE_MSG, true);
      // the language chosen at the first visit becomes the Pi's default, for the browsers that choose none (0.47.0)
      if (!S.cfg.CONSOLE_LANG && I.saved() && S.catalog["console-lang"]) run("console-lang", { value: I.lang() }, { quiet: true, confirmed: true });
      if (S.approveId) { var aid = S.approveId; S.approveId = null; approveComputer(aid); }
      else if (!S.session.wizard_done) {
        // 0.54.2: on a card where the console was just switched on there is no reading of the Pi yet (the helper writes it
        // when it first runs): the steps opened on an empty one and said there was no decoder, no network, no watchdog.
        // Wait for the first reading (25 s at most, then open on what there is), and read it again.
        var first = !S.factsAt && S.refreshed ? Promise.race([S.refreshed, new Promise(function (res) { setTimeout(res, 25000); })]).then(loadState) : Promise.resolve();
        first.then(function () { if (!S.session.wizard_done && !S.wizardOpen) wizard(); });
      }
    });
  }
  function loadState() {
    return api("state").then(function (r) {
      if (!r.ok) return;
      S.cfg = r.data.cfg || {}; S.facts = r.data.facts || {}; S.factsAt = r.data.facts_at || 0; S.backup = r.data.backup || null;
      S.templates = typeof r.data.templates === "string" ? r.data.templates : "";
      S.templatesBefore = !!r.data.templates_before;
      S.tgTemplates = r.data.telegram_templates && typeof r.data.telegram_templates === "object" ? r.data.telegram_templates : {};   // 0.99.6
      S.catalog = r.data.catalog || {}; S.sections = r.data.sections || [];
      theme(S.cfg.THEME);
      // the overview's facts are read as root by the helper after each change; older than two minutes: again
      if (!S.factsAt || Date.now() / 1000 - S.factsAt > 120) {
        if (!S.refreshing) { S.refreshing = true; S.refreshed = run("refresh", {}, { quiet: true }).then(function () { S.refreshing = false; }); }
      }
      draw();
    }).catch(function () { /* the wall restarting: the next poll draws */ });
  }
  // 0.99.18 (review B10): the page read the Pi once, when it opened: left open, it showed settings changed since over
  // SSH and "Read on the Pi 3 h ago". It reads them again every two minutes and when its tab is shown again, only while
  // someone could be looking at it and nothing would be lost: the tab in view, signed in, no question or first steps
  // open, no field being typed in.
  var STALE_MS = 120000;
  function mayRead() {
    var a = document.activeElement;
    return document.visibilityState === "visible" && !!S.session && $("modal").hidden && !S.wizardOpen &&
      !(a && /^(INPUT|SELECT|TEXTAREA)$/.test(a.tagName));
  }
  function freshen() { if (mayRead()) loadState(); }
  setInterval(freshen, STALE_MS);
  document.addEventListener("visibilitychange", function () { if (document.visibilityState === "visible") freshen(); });
  window.addEventListener("hashchange", route);
  window.addEventListener("popstate", route);      // back and forward through the sections (0.99.1: pushState)
  function route() {
    var want = (location.hash || "#overview").slice(1);
    if (want === "first-steps") { history.replaceState(null, "", location.pathname + "#overview"); want = "overview"; setTimeout(S.openWizard, 0); }
    if (SECTION_IDS.indexOf(want) < 0) want = "overview";      // only a section's own name: never a property of the object
    if (want === "system") S.sessions = null;            // who is signed in, read again each time
    S.section = want;
    draw(true);
  }

  function nav() {
    var navEl = $("nav"), tabs = $("tabs");
    navEl.innerHTML = ""; tabs.innerHTML = "";
    S.sections.forEach(function (sec) {
      var id = sec[0], busy = Object.keys(S.pending).some(function (k) { return S.catalog[k] && S.catalog[k].section === id; });
      [navEl, tabs].forEach(function (where) {
        var short = where === tabs && id === "reliability" ? t("Reliable") : t(sec[1]);
        where.appendChild(h("a", { href: "#" + id, "class": id === S.section ? "on" : "", "aria-current": id === S.section ? "page" : null, onclick: showSection(id), "data-fk": (where === tabs ? "tab|" : "nav|") + id },
          ico(SECTION_ICON[id]), h("span", { text: short }), busy ? h("i", { "class": "dot" }) : null));
      });
    });
  }

  // 0.99.18 (review B10): drawing a section again rebuilds its controls, and the keyboard's place went with them (a
  // switch pressed with Space left the focus on the page). Each control carries a key (data-fk): the one written by
  // its maker (a switch, a button, a field's Apply), or its card, its kind, its words and its rank there; after a
  // redraw the focus goes back to the control with the same key.
  function fkOf(n) { return n && n.nodeType === 1 && n !== document.body ? n.getAttribute("data-fk") : null; }
  function keyAll(root) {
    var seen = {};
    root.querySelectorAll("button, a[href], input, select, textarea, summary").forEach(function (n) {
      if (n.hasAttribute("data-fk")) return;
      var c = n.closest(".card[data-title]"), words = (n.getAttribute("aria-label") || n.getAttribute("title") || n.textContent || "").trim().replace(/…$/, "");
      var k = (c ? c.getAttribute("data-title") : "") + "|" + n.tagName + "|" + words;
      seen[k] = (seen[k] || 0) + 1;
      n.setAttribute("data-fk", k + "#" + seen[k]);
    });
  }
  function refocus(root, key, was) {
    if (!key || (was && was.isConnected && root.contains(was))) return;
    var list = root.querySelectorAll("[data-fk]");
    for (var i = 0; i < list.length; i++) if (list[i].getAttribute("data-fk") === key) { list[i].focus({ preventScroll: true }); return; }
  }
  function draw(scrollTop) {
    if (!S.session) return;
    var view = $("view"), focused = document.activeElement, fk = $("app").contains(focused) ? fkOf(focused) : null;
    nav();
    if (!scrollTop && focused && view.contains(focused) && /INPUT|SELECT|TEXTAREA/.test(focused.tagName)) return;   // never under the typing finger
    var title = t((S.sections.filter(function (s) { return s[0] === S.section; })[0] || [0, "Overview"])[1]);
    $("title").textContent = title;
    document.title = t("{title} · ZenithBoard console", { title: title });
    var y = window.scrollY;
    view.innerHTML = "";
    add(view, sectionView(S.section));
    keyAll(view);
    if (scrollTop) { window.scrollTo(0, 0); view.focus({ preventScroll: true }); } else { window.scrollTo(0, y); refocus($("app"), fk, focused); }
    $("busy-badge").hidden = !Object.keys(S.jobs).some(function (k) { var j = S.jobs[k]; return j.state === "queued" || j.state === "running"; });
  }

  // ---- running an action, and following it
  function confirmBox(title, text, okLabel, danger) {
    return new Promise(function (resolve) {
      openModal(h("div", null,
        h("header", null, h("h2", { text: title })),
        h("div", { "class": "modal-body" }, (Array.isArray(text) ? text : [text]).map(function (p) { return p && p.nodeType ? p : h("p", { text: p }); })),
        h("div", { "class": "modal-foot" },
          h("button", { type: "button", "class": "btn", text: t("Cancel"), onclick: function () { closeModal(); resolve(false); } }),
          h("button", { type: "button", "class": danger ? "danger" : "primary", text: okLabel || t("Go on"), onclick: function () { closeModal(); resolve(true); } }))));
    });
  }
  var ASK = {
    location: [t("Change the antenna position?"), t("It is written everywhere it is stored on this Pi (the wall, and the feeders that can be set from here); the ones that cannot are named in the output. The position is never shown on the wall or in a post.")],
    graphs: ["graphs1090", t("Turning it on runs its author's installer: collectd and rrdtool from apt (signed), its files from GitHub, a few minutes. Turning it off puts back what was there before and keeps its history.")],
    "adsbx-stats": [t("ADSB Exchange stats"), t("Turning it on runs ADSB Exchange's own script, a minute or two. Every 5 seconds the Pi then sends them the aircraft it hears (the list their feed already gets) and its power warnings. In return: their map of only your aircraft, from anywhere, and Feed Details on their page. Turning it off removes it and the packages it added.")],
    "gain-step": [t("Move the gain one step?"), t("The decoder restarts with the new gain: a few seconds without aircraft. Go one step at a time, and check again after a day.")],
    social: [t("Social sharing"), t("Switching it on starts posting the aircraft worth it to Bluesky, as set in Sharing (place name, radius, rules, gap). Off stops the service; the account stays.")],
    watchdog: [t("Hardware watchdog"), t("If the Pi freezes completely, its own chip restarts it after about 10 seconds. Off takes the setting away again.")],
    "update-quick": [t("Update ZenithBoard and the wall?"), t("Seconds. The wall restarts, so this page reconnects by itself. The feeders are left as they are.")],
    update: [t("Update everything?"), t("ZenithBoard, the decoder and every feeder, one after the other: several minutes. The wall restarts during it; this page follows. A new GitHub signing key is never accepted from here: the update says so, and it is answered over SSH.")],
    "phone-signin": [t("Sign computers in with a phone"), t("When on, a computer's sign-in page shows a QR code. A phone already signed in scans it, sees the computer, its address and a four-digit code, and says yes: the computer is signed in, no password. Off again: computers use the password.")],
    "social-templates-delete": [t("Delete all your templates?"), t("The posts go on with the other words you ticked (factual when none is left). They are kept on the Pi: Put back brings them again.")],
    "telegram-test-send": [t("Send a test to the chat?"), t("The two messages, filled on an aircraft overhead now (or a sample), go to your Telegram chat, each marked as a test.")],
    "telegram-template-delete": [t("Back to the default message?"), t("Your own message is deleted and the default is used again. It is kept on the Pi: sudo zenithboard telegram template crossing undo (or squawk) brings it back.")],
    "social-templates-undo": [t("Put back your previous templates?"), t("The templates before the last change come back; today's are kept in their place, so it can be undone too.")],
    "backup-delete": [t("Delete the console's backup?"), t("Only the copy kept here for download: the files you already downloaded, and the Pi itself, are not touched.")],
    tailscale: [t("Tailscale"), t("Switching it on installs Tailscale the first time (from its own repository, a few minutes), then prints a sign-in link in this card: open it, sign in to YOUR Tailscale account, approve the Pi. The wall then answers your Tailscale devices too. Off disconnects the Pi from your Tailscale network; it stays installed. The wall restarts either way: this page reconnects by itself. Have your Tailscale account ready (tailscale.com, free) and its app on your phone: the switch waits up to an hour for the sign-in, and other changes wait behind it. To give up, switch it off.")],
    "tailscale-console": [t("The console over Tailscale"), t("On: the devices signed in to your Tailscale account can open this console too (encrypted by Tailscale; the password still applies). Off: your home network only. The wall restarts: this page reconnects by itself.")],
    "console-off": [t("Turn the console off?"), t("Its pages stop answering at once, this one included. Turn it on again over SSH: sudo zenithboard console on")]
  };
  function run(action, params, opts) {
    opts = opts || {};
    var spec = S.catalog[action] || { flags: [], label: action }, flags = spec.flags || [];
    // the card the click came from, read now: a confirmation box clicked next is not a card (0.40.3)
    var card = opts.card || S.lastCard;
    S.lastCard = null;
    var go = Promise.resolve(true);
    if (flags.indexOf("ask") >= 0 && !opts.confirmed) {
      var a = ASK[action] || [t(spec.label), t("Go on?")];
      var off = params && params.value === "off";
      go = confirmBox(a[0], off && action !== "graphs" ? t("Switch it off?") : a[1], off ? t("Switch off") : t("Go on"), action === "console-off");
    }
    return go.then(function (yes) {
      if (!yes) return null;
      var key = opts.key || action;
      if (!opts.quiet) { S.pending[key] = true; S.wanted[key] = params && params.value; draw(); }
      return api("run", { body: { action: action, params: params || {} } }).then(function (r) {
        if (!r.ok) {
          delete S.pending[key]; draw();
          toast(t(r.data.error || "Refused."), true); return null;
        }
        var id = r.data.job;
        S.jobs[id] = { id: id, action: action, label: opts.label || t(spec.label), params: params || {}, state: "queued", log: "", next: 0, key: key, quiet: opts.quiet };
        // 0.40.2: what a button shows appears in the card it was clicked in (the owner: "I click, but where do I look?");
        // 0.40.3: every action does, switches, choices and long ones included ("valable pour toute l'interface");
        // only one started outside a card (the wizard runs quietly) opens the Activity drawer
        if (!opts.quiet && !opts.noDrawer && card) { S.inline.set(S.section, { id: id, card: card }); draw(); }
        else if (!opts.quiet && !opts.noDrawer && (flags.indexOf("read") >= 0 || flags.indexOf("long") >= 0 || opts.show)) openDrawer(id);
        return follow(id);
      }).catch(function () {
        delete S.pending[key]; draw();
        toast(t("The Pi does not answer."), true); return null;
      });
    });
  }
  function follow(id) {
    var j = S.jobs[id], started = Date.now();
    return new Promise(function (resolve) {
      function tick() {
        api("job?id=" + id + "&from=" + j.next).then(function (r) {
          if (r.status === 404 && r.data.error === "off") { location.reload(); return; }   // the console was just turned off
          if (r.status === 404) { setTimeout(tick, 1500); return; }      // between the spool and the helper's first word
          var d = r.data;
          if (d.log) j.log += d.log;
          j.next = d.next || j.next; j.state = d.state; j.rc = d.rc; j.error = d.error; j.behind = d.behind; j.ahead = d.ahead;
          // 0.39.3: one job at a time. Waiting behind a long one (graphs1090, an update) is said as such, once; only a job
          // waiting with nothing running means the helper is not there (the owner's recording, 21 October)
          if (j.state === "queued" && !S.warnedQueue[id] && (d.behind ? Date.now() - started > 3000 : Date.now() - started > 20000)) {
            S.warnedQueue[id] = true;
            var now_ = Date.now();
            if (d.behind && now_ - (S.lastQueueNote || 0) > 15000) {
              S.lastQueueNote = now_;
              toast(t("Queued: {job} runs first, then this. The Pi does one change at a time.", { job: t((S.catalog[d.behind] || {}).label || d.behind) }));
            } else if (!d.behind && now_ - (S.lastQueueNote || 0) > 15000) {
              S.lastQueueNote = now_;
              toast(t("The console's helper has not taken the job. Over SSH: sudo zenithboard console on"), true);
            }
          }
          if (S.drawerJob === id) drawTerm();
          var it = document.getElementById("iterm-" + id);
          if (it) { var pre = it.querySelector("pre"), atEnd = pre.scrollHeight - pre.scrollTop - pre.clientHeight < 40;
            pre.textContent = termText(j); if (atEnd) pre.scrollTop = pre.scrollHeight;
            var pl = it.querySelector(".pill"), st = pillOf(j); pl.className = "pill " + st[0]; pl.textContent = st[1];
            // 0.45.1: Tailscale's sign-in link, as a button, as soon as it is printed (the job waits for that sign-in)
            if (j.action === "tailscale" && !it.querySelector(".ts-signin")) {
              var tsl = /https:\/\/login\.tailscale\.com\/a\/[A-Za-z0-9]+/.exec(j.log || "");
              if (tsl) it.appendChild(h("div", { "class": "actions ts-signin" }, h("a", { "class": "primary", href: tsl[0], target: "_blank", rel: "noopener noreferrer", text: t("Sign in to Tailscale ↗") })));
            } }
          if (j.state === "done" || j.state === "refused") return finish();
          setTimeout(tick, j.state === "running" ? 700 : 1000);
        }).catch(function () { setTimeout(tick, 1500); });            // the wall restarting after the change
      }
      function finish() {
        delete S.pending[j.key]; delete S.wanted[j.key];
        var spec = S.catalog[j.action] || { flags: [] }, ok = j.state === "done" && j.rc === 0;
        if (j.action === "refresh" && !j.quiet) toast(t("Read again."));
        if (!j.quiet && spec.flags.indexOf("read") < 0) {
          if (ok) toast(t("{job}: done.", { job: j.label }));
          else toast(j.error ? t("{job}: refused ({why})", { job: j.label, why: t(j.error) }) : t("{job}: it did not work. Read what it printed beside the button, or in Activity.", { job: j.label }), true);
        }
        // 0.54.7: after an update the page kept showing the old version everywhere and never said to reload; the wall
        // restarts, so it is asked once it answers again, and the page is reloaded when the version is not the one it has
        if (ok && j.action.indexOf("update") === 0 && S.session && S.session.version) {
          var was = S.session.version;
          setTimeout(function () { api("session").then(function (r) { if (r.ok && r.data && r.data.version && r.data.version !== was) location.reload(); }).catch(function () {}); }, 6000);
        }
        setTimeout(loadState, 1200); setTimeout(loadState, 5000);      // the helper reads the Pi's facts again after a job
        if (S.activityOpen) loadActivity();
        draw();
        resolve(j);
      }
      setTimeout(tick, 400);
    });
  }

  // ---- controls: a value is shown waiting (dashed) until the Pi has done it
  function waitingFor(key) { return S.pending[key] ? S.wanted[key] : undefined; }
  function seg(action, choices, current, labels, key) {
    key = key || action;
    var w = waitingFor(key);
    return h("div", { "class": "seg", role: "group" }, choices.map(function (c, i) {
      var cls = (w !== undefined ? (String(c) === String(w) ? "wait" : "") : (String(c) === String(current) ? "on" : ""));
      return h("button", { type: "button", "class": cls, "aria-pressed": String(c) === String(current) ? "true" : "false", disabled: S.pending[key] ? true : null,
        text: labels ? labels[i] : c, onclick: function () { if (String(c) !== String(current)) run(action, { value: String(c) }, { key: key }); } });
    }));
  }
  function sw(action, isOn, extra, key, label) {
    key = key || action;
    var waiting = S.pending[key];
    return h("button", { type: "button", role: "switch", "aria-checked": isOn ? "true" : "false", "aria-label": label || t((S.catalog[action] || {}).label || action),
      "class": "sw" + (isOn ? " on" : "") + (waiting ? " wait" : ""), disabled: waiting ? true : null, "data-fk": "sw|" + key,
      onclick: function () { var p = Object.assign({}, extra || {}, { value: isOn ? "off" : "on" }); run(action, p, { key: key }); } });
  }
  function btn(label, action, params, cls, opts) {
    var busy = S.pending[(opts && opts.key) || action];
    return h("button", { type: "button", "class": cls || "btn", disabled: busy ? true : null, text: busy ? label + "…" : label, "data-fk": "btn|" + ((opts && opts.key) || action) + "|" + label,
      onclick: function () { run(action, params || {}, Object.assign({ card: S.lastCard }, opts || {})); } });
  }
  function row(title, hint, ctl, end) {
    if (ctl && ctl.classList && ctl.classList.contains("sw")) end = true;   // a lone switch stays beside its words on a phone
    return h("div", { "class": "row" + (end ? " tight" : "") }, h("div", { "class": "what" }, h("b", { text: title }), hint ? h("span", { text: hint }) : null),
      h("div", { "class": "ctl" + (end ? " end" : "") }, ctl));
  }
  function card(title, icon, lead, body, width) {
    var shown = S.inline.get(S.section), j = shown && shown.card === title && S.jobs[shown.id];
    return h("section", { "class": "card" + (width ? " " + width : ""), "data-title": title }, h("h2", null, icon ? ico(icon) : null, title),
      lead ? h("p", { "class": "lead", text: lead }) : null, body, j ? inlineTerm(j) : null);
  }
  // the output of a button, under it in its own card, as it comes
  function inlineTerm(j) {
    var pre = h("pre", { text: termText(j) }), st = pillOf(j);
    var links = j.state === "done" && j.rc === 0 && (j.action === "social-test" || j.action === "summary-test") ? h("div", { "class": "actions" },
      h("a", { "class": "btn", href: j.action === "summary-test" ? "/social/preview1" : "/social/preview", target: "_blank", rel: "noopener", text: j.action === "summary-test" ? postName(1) : t("The picture ↗") }),
      j.action === "summary-test" ? ["2", "3", "4"].map(function (n) { return h("a", { "class": "btn", href: "/social/preview" + n, target: "_blank", rel: "noopener", text: postName(n) }); }) : null) : null;
    // 0.45.1: Tailscale's sign-in link, as a button, while it waits for it (only its own address is taken)
    var tsl = j.action === "tailscale" && j.state !== "done" && /https:\/\/login\.tailscale\.com\/a\/[A-Za-z0-9]+/.exec(j.log || "");
    if (tsl && !links) links = h("div", { "class": "actions ts-signin" }, h("a", { "class": "primary", href: tsl[0], target: "_blank", rel: "noopener noreferrer", text: t("Sign in to Tailscale ↗") }));
    var box = h("div", { "class": "term inline", id: "iterm-" + j.id },
      h("div", { "class": "th" }, ico("terminal"), h("b", { text: j.params && j.params.value ? t("{job}: {value}", { job: j.label, value: word(j.params.value) }) : j.label }), h("span", { "class": "pill " + st[0], text: st[1] }),
        h("button", { type: "button", "class": "ghost", title: t("Open in Activity"), text: "⤢", onclick: function () { openDrawer(j.id); } }),
        h("button", { type: "button", "class": "ghost", "aria-label": t("Close"), text: "×", onclick: function () { S.inline.delete(S.section); draw(); } })),
      pre, links);
    setTimeout(function () { pre.scrollTop = pre.scrollHeight; }, 0);
    return box;
  }
  function noteCard(e) {                                     // which card a control sits in, for the run() it calls
    var c = e.target && e.target.closest ? e.target.closest(".card[data-title]") : null;
    S.lastCard = c ? c.getAttribute("data-title") : null;
  }
  document.addEventListener("click", noteCard, true);
  // a waiting control (aria-disabled, 0.99.18) keeps its focus but does nothing: the click stops here, before its own
  function isOff(n) { return !!n && (n.disabled || n.getAttribute("aria-disabled") === "true"); }
  document.addEventListener("click", function (e) {
    var b = e.target && e.target.closest ? e.target.closest("[aria-disabled=true]") : null;
    if (b) { e.preventDefault(); e.stopPropagation(); }
  }, true);
  document.addEventListener("change", noteCard, true);     // a list chosen with the keyboard
  function stateWord(v) { return word(on(v) ? "on" : "off"); }

  // ---- the sections
  var SVC_NAMES = [
    ["readsb", t("Decoder (readsb)")], ["dump1090_fa", t("Decoder (dump1090-fa)")], ["dump978_fa", t("978 MHz UAT")],
    ["adsbexchange_feed", t("ADSB Exchange")], ["adsbexchange_stats", t("ADSB Exchange stats")], ["piaware", t("FlightAware")], ["fr24feed", t("Flightradar24")], ["pfclient", t("Plane Finder")], ["rbfeeder", t("AirNav Radar")],
    ["zenithboard_flightinfo", t("The wall")], ["zenithboard_social", t("Bluesky posts")], ["zenithboard_telegram", t("Telegram messages")], ["graphs1090", "graphs1090"], ["lighttpd", t("Receiver map's web server")]
  ];
  function go(section) { return showSection(section); }
  // 0.99.1 (the owner's recordings, 27 October 2026): on an iPhone, through Tailscale, every tap on a section reloaded
  // the whole page (Chrome's progress bar, a second of black), where a computer only changed the address's #. The
  // section is now shown by the page itself, the address updated without the browser navigating at all; the link
  // stays a link (a long press, a new tab).
  function showSection(section) {
    return function (e) {
      if (e && (e.metaKey || e.ctrlKey || e.shiftKey || e.button > 0)) return;     // a new tab or window: the browser's
      if (e) e.preventDefault();
      if (location.hash !== "#" + section) {
        try { history.pushState(null, "", location.pathname + "#" + section); } catch (err) { location.hash = "#" + section; return; }
      }
      route();
    };
  }

  // ---- 0.53.0: the console as an app (the owner, 22 October 2026). The manifest and icons let a browser install
  // it; Chrome's own Install button needs https, so over the Pi's plain http home address the card says which menu
  // does it. The service worker keeps nothing and registers only where the browser allows it (https).
  var INSTALL = { prompt: null, done: false };
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault(); INSTALL.prompt = e;
    if (S.section === "system" && !$("app").hidden) draw();
  });
  window.addEventListener("appinstalled", function () { INSTALL.prompt = null; INSTALL.done = true; if (S.section === "system" && !$("app").hidden) draw(); });
  if ("serviceWorker" in navigator && window.isSecureContext) {
    navigator.serviceWorker.register("/console-sw.js", { scope: "/console" }).catch(function () { /* the page works without it */ });
  }
  function installCard() {
    var nav = navigator, ua = nav.userAgent || "";
    var app = (window.matchMedia && matchMedia("(display-mode: standalone)").matches) || nav.standalone === true;
    var ios = /iPhone|iPad|iPod/.test(ua) || (nav.platform === "MacIntel" && nav.maxTouchPoints > 1), android = /Android/.test(ua);
    var body = [];
    if (app) body.push(h("p", { "class": "note", text: t("Installed: this window is the app.") }));
    else if (INSTALL.done) body.push(h("p", { "class": "note", text: t("Installed: open it from its icon.") }));
    else {
      if (INSTALL.prompt) body.push(h("div", { "class": "actions" }, h("button", { type: "button", "class": "primary", text: t("Install the app"), onclick: function () {
        var p = INSTALL.prompt; INSTALL.prompt = null;
        p.prompt(); p.userChoice.then(function (c) { if (c && c.outcome === "accepted") INSTALL.done = true; draw(); });
      } })));
      body.push(h("ul", { "class": "ticks" },
        h("li", { "class": ios ? "here" : null, text: t("iPhone or iPad, in Safari: Share → Add to Home Screen. It opens full screen, with its own icon. A QR code opens in Safari, not in the app: sign in inside it with the console password (choose one first if there is none: sudo zenithboard console password).") }),
        h("li", { "class": android ? "here" : null, text: t("Android, in Chrome: ⋮ → Add to Home screen.") }),
        h("li", { "class": !ios && !android ? "here" : null, text: t("A computer, in Chrome: ⋮ → Cast, save, and share → Install page as app. In Edge: ⋯ → Apps → Install this site as an app. In Safari on a Mac: File → Add to Dock.") })));
      if (!window.isSecureContext) body.push(h("p", { "class": "note", text: t("The Install button that browsers show by themselves needs an https address; this Pi answers in plain http on your home network, so their menu does it instead. Same console, same password.") }));
    }
    return card(t("The console as an app"), "phone", t("Its own icon and its own window, on the phone or the computer. Nothing is downloaded: it is this same page, from this Pi."), body, "w6");
  }
  // 0.99.6: AirNav Radar's station serial, as rbfeeder prints it (EXTRPI000000), only when it looks like one
  function rbStation() { var s = S.facts.radarbox_station || ""; return /^[A-Za-z0-9]{6,20}$/.test(s) ? s : null; }
  // 0.52.0: the link to ADSB Exchange's map of this antenna's aircraft, only when it is theirs
  function adsbxMap() { var u = S.facts.adsbx_map || ""; return /^https:\/\/www\.adsbexchange\.com\/api\/feeders\/\?feed=[0-9A-Fa-f-]{36}$/.test(u) ? u : null; }

  var SECTIONS = {
    overview: function () {
      var f = S.facts, c = S.cfg, out = [];
      var mem = f.mem_avail_mb ? size(f.mem_avail_mb) : "–", card_ = f.disk_free_mb ? size(f.disk_free_mb) : "–";
      var thr = f.throttled && f.throttled !== "0x0" ? t("power warnings: see Health") : (f.throttled ? t("power: no warning") : "");
      out.push(h("div", { "class": "tiles" },
        tile(t("Up for"), f.uptime_s ? dur(f.uptime_s) : "–", f.model || ""),
        tile(t("Temperature"), f.temp_c ? f.temp_c + " °C" : "–", thr || (f.load ? t("load {n}", { n: f.load }) : "")),
        tile(t("Memory free"), mem, f.mem_total_mb ? t("of {size}", { size: size(f.mem_total_mb) }) : ""),
        tile(t("Card free"), card_, f.disk_total_mb ? t("of {size}", { size: size(f.disk_total_mb) }) : "")));
      var svcs = SVC_NAMES.filter(function (s) { return f["svc_" + s[0]] !== undefined; }).map(function (s) {
        var st = f["svc_" + s[0]], quiet = (s[0] === "zenithboard_social" && !on(c.SOCIAL)) || (s[0] === "zenithboard_telegram" && !on(c.TELEGRAM));
        return h("div", { "class": "svc" }, h("i", { "class": st === "active" ? "ok" : (quiet ? "" : "bad") }), h("span", { text: s[1] }),
          h("em", { text: st === "active" ? word("running") : (quiet ? word("off") : st) }));
      });
      out.push(card(t("Services"), "antenna", S.factsAt ? t("Read on the Pi {time}.", { time: ago(S.factsAt) }) : t("Reading the Pi…"),
        [svcs.length ? svcs : h("p", { "class": "note", text: t("Nothing read yet.") }),
          h("div", { "class": "actions" }, btn(t("Read again"), "refresh", {}, "btn", { noDrawer: true }), btn(t("Status"), "status"), btn(t("Health"), "health"))], "w6"));
      out.push(card(t("At a glance"), "overview", null, h("div", { "class": "glance" },
        chip(t("Wall: {look}, {colour}, {radius}", { look: word(c.DISPLAY_MODE === "flap" ? "flap" : "dots"), colour: word(c.THEME || "amber"),
          radius: c.RADIUS + " " + distUnit(c.UNITS) }), "wall"),
        chip(t("Statistics {state}", { state: stateWord(c.STATS) }), "receiver", on(c.STATS)),
        chip(t("graphs1090 {state}", { state: word(f.graphs) }), "receiver", f.graphs === "on"),
        chip(t("Bluesky {state}", { state: word(on(c.SOCIAL) ? "posting" : "off") }), "sharing", on(c.SOCIAL)),
        chip(t("Summaries: {list}", { list: ["DAILY", "WEEKLY", "MONTHLY"].filter(function (p) { return on(c["SOCIAL_" + p]); }).map(function (p) { return word(p.toLowerCase()); }).join(", ") || word("off") }), "sharing"),
        chip(t("Telegram {state}", { state: stateWord(c.TELEGRAM) }), "sharing", on(c.TELEGRAM)),
        chip(t("Watchdog {state}", { state: word(f.watchdog) }), "reliability", f.watchdog === "on"),
        chip(t("Network watchdog {state}", { state: word(f.netwatch) }), "reliability", f.netwatch === "on"),
        f.tailscale && f.tailscale !== "not installed" ? chip(t("Tailscale {state}", { state: word(f.tailscale) }), "system", f.tailscale === "on") : null,
        chip(t("Security fixes {state}", { state: word(f.patches) }), "reliability", f.patches === "on"),
        f.wifi ? chip(t("Wi-Fi: {state}", { state: f.wifi }), "system") : null), "w6"));
      var gaps = setupGaps();
      if (gaps.length) out.push(card(t("Finish setting up"), "gear", null, [h("ul", { "class": "ticks no" }, gaps.map(function (g) { return h("li", { text: g }); })),
        h("div", { "class": "actions" }, h("button", { type: "button", "class": "primary", text: t("Open the first steps"), onclick: function () { S.openWizard(); } }))], "w12"));
      out.push(card(t("Pages"), "link", t("What this Pi shows, and what it can show once switched on."), h("div", { "class": "page-groups" }, pages()), "w12"));
      return out;
    },

    wall: function () {
      var c = S.cfg, unit = distUnit(c.UNITS);
      return [
        card(t("Look"), "wall", t("The default of every screen. A tablet that chose its own with its gear keeps it until Reset in its gear panel."), [
          row(t("Look"), t("Dot matrix, or the split-flap airport board"), seg("mode", ["dots", "flap"], c.DISPLAY_MODE || "dots", [t("Dot matrix"), t("Split-flap")])),
          row(t("Colour"), null, swatches()),
          row(t("Units"), t("Distances, speeds and heights"), seg("units", ["metric", "imperial", "aviation"], c.UNITS, [t("km · m"), t("mi · ft"), t("NM · kt · ft")])),
          row(t("Detection radius"), t("Aircraft inside it are on the wall, in {unit}", { unit: unit }), seg("radius", ["1", "2", "5", "10", "15", "30", "50"], String(Number(c.RADIUS)))),
          row(t("Seconds per aircraft"), t("2 to 60"), numberApply("cycle", c.CYCLE_SECONDS, 2, 60)),
          h("div", { "class": "actions" }, h("a", { "class": "btn", href: "/", target: "_blank", rel: "noopener", text: t("Open the wall ↗") }))
        ], "w6"),
        card(t("What it shows"), "plane", null, [
          row(t("Aircraft photos"), t("From Planespotters, with their credit; needs internet"), sw("photos", on(c.SHOW_PHOTOS))),
          row(t("Where flights come from and go to"), t("The callsign is looked up on adsbdb.com"), sw("routes", on(c.SHOW_ROUTES))),
          row(t("The receiver map's aircraft database"), t("Registrations and models read on the card (tar1090); nothing downloaded"), sw("localdb", on(c.LOCAL_DB))),
          row(t("Monthly refresh of the model names"), t("A free list from GitHub, once a month"), sw("data-auto", on(c.AUTO_DATA_REFRESH))),
          h("div", { "class": "actions" }, btn(t("Refresh the model names now"), "data-update"), btn(t("Aircraft data"), "data-status"), btn(t("Presets"), "presets"))
        ], "w6")
      ];
    },

    receiver: function () {
      var c = S.cfg, f = S.facts;
      var lat = h("input", { type: "text", inputmode: "decimal", value: c.LAT || "", "aria-label": t("Latitude"), size: 10 });
      var lon = h("input", { type: "text", inputmode: "decimal", value: c.LON || "", "aria-label": t("Longitude"), size: 10 });
      var alt = h("input", { type: "number", value: c.ALT_M || "0", "aria-label": t("Altitude in metres"), min: -500, max: 9000 });
      return [
        card(t("Antenna"), "antenna", null, [
          row(t("Region"), t("The United States adds the optional 978 MHz UAT step (menu 1)"), seg("region", ["world", "us"], c.REGION || "world", [t("World"), t("United States")])),
          h("div", { "class": "row" }, h("div", { "class": "what" }, h("b", { text: t("Position") }), h("span", { text: t("Decimal degrees, altitude in metres. Written everywhere it is stored; never shown on the wall or in a post.") })),
            h("div", { "class": "fields" }, field(t("Latitude"), lat), field(t("Longitude"), lon), field(t("Alt. m"), alt),
              [lat, lon].reduce(function (b, inp) { return onEnter(inp, b); }, onEnter(alt, h("button", { type: "button", "class": "btn", text: S.pending.location ? t("Applying…") : t("Apply"), disabled: S.pending.location ? true : null,
                onclick: function () { run("location", { lat: lat.value.trim(), lon: lon.value.trim(), alt: alt.value.trim() }); } })))))
        ], "w6"),
        card(t("Measure"), "chart", null, [
          row(t("Statistics"), t("A sample every 15 minutes, 30 days kept, about 30 KB a day"), [sw("stats", on(c.STATS)), on(c.STATS) ? h("a", { href: "/stats", target: "_blank", rel: "noopener", text: t("Open ↗") }) : null]),
          row("graphs1090", t("Years of the decoder's graphs on port 8542; installed by its author's script"), [sw("graphs", f.graphs === "on"), f.graphs === "on" ? h("a", { href: "http://" + host() + ":8542/" + langQ(), target: "_blank", rel: "noopener", text: t("Open ↗") }) : null]),
          f.graphs === "on" ? row(t("graphs1090 in ZenithBoard's look"), t("A black page in the wall's colour, its graphs drawn to match; off: graphs1090's own"), sw("graphs-look", S.cfg.GRAPHS_LOOK !== "original")) : null,
          f.svc_adsbexchange_feed !== undefined || f.adsbx_stats === "on" ? row(t("ADSB Exchange stats"), t("Their map of only your aircraft, from anywhere, and Feed Details on their page. The Pi sends them the aircraft it hears every 5 seconds."),
            [sw("adsbx-stats", f.adsbx_stats === "on"), adsbxMap() ? h("a", { href: adsbxMap(), target: "_blank", rel: "noopener noreferrer", text: t("Open ↗") }) : null]) : null,
          row(t("Gain"), t("Check it first; then one step at a time"), [btn(t("Check"), "gain-check"), btn(t("− Down"), "gain-step", { value: "down" }, "btn", { key: "gain-step" }), btn(t("Up +"), "gain-step", { value: "up" }, "btn", { key: "gain-step" })]),
          row(t("Gain log, 24 hours"), t("One measurement every 15 minutes, as a table"), [sw("gain-log", on(c.GAINLOG)), on(c.GAINLOG) ? btn(t("Read it"), "gain-log-show") : null])
        ], "w6"),
        card(t("Look at it"), "terminal", null, h("div", { "class": "actions" },
          btn(t("Status"), "status"), btn(t("Statistics in the terminal"), "stats-show"), btn(t("Unknown callsigns and types"), "stats-gaps"), btn(t("One MLAT client only"), "mlat-guard")), "w12")
      ];
    },

    sharing: function () {
      var c = S.cfg, f = S.facts, acct = f.bluesky;
      var col = c.SOCIAL_THEME || "wall", units = c.SOCIAL_UNITS || "wall";
      return [
        card(t("Bluesky"), "share", acct ? t("Account @{account}. The account itself is set up over SSH (it asks for an app password): sudo zenithboard social setup", { account: acct }) :
          t("No Bluesky account yet. Set it up over SSH, it asks for an app password: sudo zenithboard social setup"), [
          row(t("Post the aircraft overhead"), t("As set below. Never a distance or a direction."), acct ? sw("social", on(c.SOCIAL)) : h("span", { "class": "state", text: t("needs an account") })),
          // 0.50.0: the terminal wizard's answers, one by one (the owner: "no field for it")
          row(t("Place name"), t("Two or three words, as the posts say it: a town name alone gets the posts' word for above (above Trémery); empty: no place. Never the receiver's position."),
            textApply("social-area", c.SOCIAL_AREA, 40, t("none"), function (v) { return v.replace(/\s+/g, " ").trim() || "none"; }, "none")),
          row(t("Sharing radius"), t("Kilometres; an aircraft inside it is a candidate. Not the wall's radius."), numberApply("social-radius", c.SOCIAL_RADIUS_KM, 1, 200)),
          row(t("What is worth a post"), c.SOCIAL_RULES === "all" || c.SOCIAL_RULES === "any" ? t("Everything: every crossing, the special ones first") : t("Only the kinds lit; Everything posts every crossing"), rulesChips(c.SOCIAL_RULES)),
          row(t("Least time between posts"), t("Minutes; 0 = every crossing posted once"), numberApply("social-gap", c.SOCIAL_GAP_MIN, 0, 1440)),
          row(t("Town names on the maps"), t("From GeoNames, made on the Pi (a few minutes); off: the lists shipped with ZenithBoard"), sw("social-places", on(c.SOCIAL_PLACES))),
          h("div", { "class": "actions" }, btn(t("Try a post (posts nothing)"), "social-test"), h("a", { "class": "btn", href: "/social/preview", target: "_blank", rel: "noopener", text: t("Last picture ↗") }), btn(t("Status"), "social-status"))
        ], "w6"),
        card(t("The picture and the words"), "picture", null, [
          row(t("Picture"), null, seg("social-look", ["dotmap", "flap", "alternate"], c.SOCIAL_STYLE || "dotmap", [t("Dots + map"), t("Split-flap"), t("In turn")])),
          row(t("Colour"), t("The wall's own, one of the five, or in turn"), select("social-colour", ["wall", "amber", "green", "red", "white", "turquoise", "rotate"], col,
            [t("The wall's ({colour})", { colour: word(c.THEME || "amber") }), t("Amber"), t("Green"), t("Red"), t("White"), t("Turquoise"), t("In turn")])),
          row(t("Map"), null, select("social-map", ["normal", "night", "satellite", "terrain", "none", "rotate"], c.SOCIAL_MAP || "normal",
            [t("Normal"), t("Night"), t("Satellite"), t("Terrain"), t("None"), t("In turn")])),
          row(t("Units"), null, seg("social-units", ["wall", "metric", "imperial", "aviation"], units, [t("The wall's"), t("Metric"), t("Imperial"), t("Aviation")])),
          row(t("Link to the photo page"), t("Planespotters, at the end of each post"), sw("social-photolink", on(c.SOCIAL_PHOTOLINK))),
          row(t("Language of the posts"), t("The aircraft posts and the summaries' words; the pictures stay in English"),
            select("social-lang", I.langs().indexOf("en") < 0 ? ["en"].concat(I.langs()) : I.langs(), c.SOCIAL_LANG || "en",
              (I.langs().indexOf("en") < 0 ? ["en"].concat(I.langs()) : I.langs()).map(I.name))),
          row(t("Words of a post"), t("One or more; with several, one is drawn at each post"), sentenceChips(c.SOCIAL_SENTENCE || "factual")),
          row(t("Hashtags"), t("At the end of each post, separated by spaces (the # is optional); empty: none"),
            textApply("social-hashtags", c.SOCIAL_HASHTAGS, 340, t("none"), function (v) { return v.replace(/[,\s]+/g, " ").trim() || "none"; }, "none"))
        ], "w6"),
        acct ? templatesCard() : null,
        telegramCard(),
        f.telegram_chat ? telegramTemplatesCard() : null,
        card(t("Summaries"), "chart", t("From the statistics, at their time on the Pi's clock; the posts go in one queue, two minutes apart. Posts: 1 the period, 2 cargo and business jets, 3 military, 4 general aviation."),
          [summaryRow("daily", t("24 hours")), summaryRow("weekly", t("The week")), summaryRow("monthly", t("30 days")),
            on(c.STATS) ? null : h("p", { "class": "note", text: t("Statistics are off: no summary can be made until they are on (Receiver).") }),
            // the audit of 22-23 October 2026: they could be switched on with no account, or sharing off, and nothing said they would not go out
            summariesBlocked(acct, c),
            // 0.55.2 (the owner's screenshot): post 1, the period, was not among the links; "All summaries" is the terminal's
            h("div", { "class": "actions" }, btn(t("All summaries"), "summaries"),
              ["1", "2", "3", "4"].map(function (n) { return h("a", { "class": "btn", href: "/social/preview" + n, target: "_blank", rel: "noopener", text: postName(n) }); })),
            h("p", { "class": "note", text: t("Each summary goes once at its time: moved to later today, it goes today; set to a time already past, from the next one. Why one did not go out: sudo zenithboard social summary why") }),
            h("p", { "class": "note", text: t("Posting one now stays in the terminal, where you see it first: sudo zenithboard social summary weekly post") })], "w12")
      ];
    },

    reliability: function () {
      var f = S.facts, logsSel = h("select", { "aria-label": t("Which log") },
        [["flightinfo", t("The wall")], ["decoder", t("The decoder")], ["social", t("Bluesky posts")], ["telegram", t("Telegram messages")], ["radarbox", t("AirNav Radar")], ["uat", t("978 MHz UAT")]].map(function (o) { return h("option", { value: o[0], text: o[1] }); }));
      return [
        card(t("Keep it running"), "shield", t("All off by default; each one off again puts back what it found."), [
          row(t("Hardware watchdog"), t("The Pi's own chip restarts it after a complete freeze"), sw("watchdog", f.watchdog === "on")),
          row(t("Network watchdog"), t("No router for 6 minutes: the network restarts; 12 minutes: the Pi"), sw("netwatch", f.netwatch === "on")),
          row(t("Logs kept after a restart"), t("Up to 50 MB: what happened just before a freeze"), sw("keeplogs", f.keeplogs === "on")),
          row(t("Wi-Fi hardening"), t("Retry without end after a loss; no radio power saving"), sw("wifi-harden", f.wifi_harden === "on")),
          row(t("Daily security fixes"), t("Debian's security channel only; feeders untouched, no reboot"), sw("patches", f.patches === "on")),
          row(t("Daily log clean-up"), t("Keeps the last 7 days"), sw("logs-auto", f.logs_auto === "on"))
        ], "w6"),
        card(t("Look at it"), "terminal", null, [
          h("div", { "class": "actions" }, btn(t("Health"), "health"), btn(t("Memory"), "memory"), btn(t("Log size and warnings"), "logs-review")),
          row(t("The last 100 lines of"), null, [logsSel, h("button", { type: "button", "class": "btn", text: t("Show"), onclick: function () { run("logs", { value: logsSel.value }, { key: "logs", card: S.lastCard }); } })])
        ], "w6")
      ];
    },

    system: function () {
      var f = S.facts;
      return [
        card(t("Updates"), "power", t("From GitHub, checked against its signature before anything runs; your settings are never changed by an update."), [
          h("div", { "class": "actions" }, btn(t("Update ZenithBoard and the wall"), "update-quick", {}, "primary"), btn(t("Update everything"), "update"), btn(t("Installed components"), "update-list"),
            h("button", { type: "button", "class": "btn", text: t("First steps again"), onclick: function () { S.openWizard(); } })),
          h("p", { "class": "note", text: t("ZenithBoard {version} runs here. The release notes: ", { version: S.session.version || "" }) }, h("a", { href: "https://github.com/regis57/ZenithBoard/releases", target: "_blank", rel: "noopener noreferrer", text: t("GitHub ↗") }))
        ], "w6"),
        card(t("Backup"), "out", t("One file with the settings, the features that are on, the statistics, what was posted, graphs1090's history and the kept logs: to keep. It leaves the networks' identities out, so it is not the one to move to a new card."), [
          h("div", { "class": "actions" }, btn(t("Make a backup"), "backup", {}, "primary"),
            S.backup ? h("a", { "class": "btn", href: "/console/api/backup", download: "", text: t("Download it") }) : null,
            S.backup ? btn(t("Delete it"), "backup-delete", {}, "danger") : null),
          S.backup ? h("p", { "class": "note", text: t("Made {when} ({ago}), {size} on the card. One copy is kept here, replaced by the next; its name says the Pi and the date, so downloads sort in time order.", {
            when: new Date(S.backup.at * 1000).toLocaleString(I.locale(), { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }),
            ago: ago(S.backup.at), size: t("{n} MB", { n: num(S.backup.bytes / 1048576, 1) }) }) }) : null,
          h("p", { "class": "sub", text: t("Putting a backup back (the import)") }),
          h("ul", { "class": "ticks" },
            h("li", { text: t("In the terminal of the Pi that receives it: sudo zenithboard backup restore FILE (or the menu: 6 Backup → 2 Put a backup back). It shows what the file holds, asks you to type RESTORE, and keeps what it replaces.") }),
            h("li", { text: t("Not from this page, on purpose: a restore replaces data and runs installers as root, like the other steps that ask for a typed word.") }),
            h("li", { text: t("This copy leaves the networks' identities out (keys never travel through this page). To move to a new card, make the full one in the terminal: sudo zenithboard backup make.") })),
          h("p", { "class": "note" }, t("Step by step, and why the MAC address does not get in the way: "), h("a", { href: "https://github.com/regis57/ZenithBoard/wiki/Backup-and-restore", target: "_blank", rel: "noopener noreferrer", text: t("Backup and restore ↗") }))
        ], "w6"),
        card(t("Network"), "link", f.ip ? t("This Pi: {address}", { address: f.ip + (f.ddns ? " · " + f.ddns : "") }) : null, [
          h("div", { "class": "actions" }, btn(t("Network"), "net-status"), btn(t("Wi-Fi"), "wifi-status"), btn(t("Domain name"), "ddns-status"),
            S.cfg.DDNS_PROVIDER && S.cfg.DDNS_PROVIDER !== "none" ? btn(t("Refresh the domain name"), "ddns-update") : null),
          h("p", { "class": "note", text: t("Wi-Fi networks, fixed addresses and the domain name's key stay in the terminal (sudo zenithboard menu → 3 Connectivity): one mistake there cuts the Pi off the network this page comes through.") })
        ], "w6"),
        card(t("Tailscale"), "link", f.tailscale === "on" ? t("On: reachable from anywhere by the devices of your Tailscale account, no port opened.") :
            t("Off. The wall, the statistics and graphs1090 from anywhere, with no port opened: your phone or computer joins your own Tailscale network (a free account on tailscale.com, its app on the phone)."), [
          row(t("Connected"), f.tailscale === "on" ? t("Off: the Pi leaves your Tailscale network; it stays installed and signed in") :
            t("The first time it installs Tailscale (minutes), then its sign-in link appears below: open it, sign in to your account, approve the Pi"), sw("tailscale", f.tailscale === "on")),
          f.tailscale === "on" ? row(t("The console over Tailscale too"), t("Only your Tailscale devices; its password still applies. Off: home network only"), sw("tailscale-console", on(S.cfg.CONSOLE_TAILSCALE))) : null,
          f.tailscale === "on" && f.tailscale_ip ? h("div", { "class": "actions" },
            h("a", { "class": "btn", href: "http://" + f.tailscale_ip + ":" + (S.cfg.PORT || "8080") + "/", target: "_blank", rel: "noopener", text: t("The wall over Tailscale ↗") }),
            h("a", { "class": "btn", href: "http://" + f.tailscale_ip + ":" + (S.cfg.PORT || "8080") + "/stats", target: "_blank", rel: "noopener", text: t("Statistics ↗") })) : null,
          f.tailscale === "on" ? h("p", { "class": "note", text: t("Its address: {address}. Open these from a device with the Tailscale app on.", { address: (f.tailscale_ip || "?") + (f.tailscale_name ? " · " + f.tailscale_name : "") }) }) : null,
          h("div", { "class": "actions" }, btn(t("Status"), "tailscale-status")),
          h("p", { "class": "note" }, t("Removing it completely (sign-out, uninstall) asks for a typed word: in the terminal, sudo zenithboard tailscale remove. Step by step: "),
            h("a", { href: "https://github.com/regis57/ZenithBoard/wiki/The-menu#tailscale", target: "_blank", rel: "noopener noreferrer", text: t("Tailscale ↗") }))
        ], "w6"),
        card(t("Language"), "globe", t("The language of these pages, the statistics and graphs1090 for every browser that did not choose its own. The flag at the top chooses for this browser only. What the Pi prints (the terminal, the cards' output) stays in English."), [
          row(t("For every browser"), t("Its own name; a language with no translation yet is not listed"), select("console-lang", I.langs(), S.cfg.CONSOLE_LANG || "en", I.langs().map(I.name))),
          h("p", { "class": "note" }, t("A word that reads wrong? Every language has its review sheet, the English beside it: "),
            h("a", { href: "https://github.com/regis57/ZenithBoard/wiki/Translating", target: "_blank", rel: "noopener noreferrer", text: t("Translating ↗") }))
        ], "w6"),
        installCard(),
        card(t("Signed in"), "phone", t("Browsers and phones signed in to this console. Signed in with the password: a week (a day unused). A paired phone: as long as it opens the console once a month."), [
          sessionsList(),
          row(t("Sign computers in with a phone"), t("A computer's sign-in page shows a QR code; a phone signed in here scans it and says yes"), sw("phone-signin", on(S.cfg.CONSOLE_PHONE_SIGNIN))),
          h("div", { "class": "actions" }, h("button", { type: "button", "class": "primary", text: t("Pair a phone"), onclick: function () { pairPhone(); } }),
            h("button", { type: "button", "class": "btn", text: t("Sign out the others"), onclick: function () {
              api("sessions/revoke", { body: { id: "others" } }).then(function (r) { toast(tn(r.data.count || 0, "{n} signed out.", "{n} signed out.")); loadSessions(); });
            } }))
        ], "w6"),
        card(t("Security"), "shield", null, [
          h("div", { "class": "actions" }, btn(t("Security check"), "security")),
          h("p", { "class": "sub", text: t("Only in the terminal, on purpose") }),
          h("ul", { "class": "ticks no" },
            h("li", { text: t("Uninstalling, and anything that asks for a typed word") }),
            h("li", { text: t("Wi-Fi, fixed addresses (they can cut this page off)") }),
            h("li", { text: t("Passwords, tokens and keys: Bluesky, Telegram, the domain name, this console's own") }),
            h("li", { text: t("Posting to Bluesky, emptying statistics or logs, importing settings, restoring a backup") })),
          h("p", { "class": "note", text: t("This page travels unencrypted on your home network (plain HTTP), like the wall. It answers home addresses only.") }),
          h("div", { "class": "actions" }, btn(t("Turn the console off"), "console-off", {}, "danger"))
        ], "w6")
      ];
    }
  };

  var SECTION_IDS = ["overview", "wall", "receiver", "sharing", "reliability", "system"];
  function sectionView(id) {
    switch (id) {
      case "wall": return SECTIONS.wall();
      case "receiver": return SECTIONS.receiver();
      case "sharing": return SECTIONS.sharing();
      case "reliability": return SECTIONS.reliability();
      case "system": return SECTIONS.system();
      default: return SECTIONS.overview();
    }
  }
  // 0.99.19 (review B11): on a narrow phone a long figure ("14 дн. 7 ч.") can still be cut; its title gives it whole
  function tile(k, v, d) {
    return h("div", { "class": "tile" }, h("div", { "class": "k", text: k }), h("div", { "class": "v", text: v, title: v }),
      h("div", { "class": "d", text: d || "\u00a0", title: d || null }));
  }
  function chip(text, section, lit) {
    return h("button", { type: "button", "class": "chip" + (lit ? " on" : ""), text: text, onclick: go(section) });
  }
  function field(label, input) { return h("div", { "class": "field" }, h("label", { text: label }), input); }
  // Enter in a field does what its button does (the audit: only a click applied it)
  // 0.99.18 (review B10): the field is left first, so the card is drawn again at once with its button waiting ("…"):
  // the page skipped drawing under the typing finger, so the button stayed live and Enter then a click ran it twice
  function onEnter(inp, button) {
    if (!button.hasAttribute("data-fk")) button.setAttribute("data-fk", "enter|" + (inp.getAttribute("aria-label") || ""));
    inp.addEventListener("keydown", function (e) {
      if (e.key !== "Enter" || e.isComposing) return;
      e.preventDefault();
      if (isOff(button) || !button.isConnected) return;
      inp.blur(); button.focus(); button.click();
    });
    return button;
  }
  function numberApply(action, value, min, max) {
    var inp = h("input", { type: "number", value: value, min: min, max: max, "aria-label": (S.catalog[action] || {}).label });
    return [inp, onEnter(inp, h("button", { type: "button", "class": "btn", text: S.pending[action] ? "…" : t("Apply"), disabled: S.pending[action] ? true : null,
      onclick: function () { if (String(inp.value) !== String(value)) run(action, { value: String(inp.value) }); } }))];
  }
  // 0.50.0: a line of text and its Set; prep turns what was typed into the value sent (empty: the word for none)
  function textApply(action, value, max, placeholder, prep, none) {
    var cur = String(value || "");
    var inp = h("input", { type: "text", value: cur === none ? "" : cur, maxlength: max, placeholder: placeholder || null, "aria-label": t((S.catalog[action] || {}).label || action) });
    return [inp, onEnter(inp, h("button", { type: "button", "class": "btn", text: S.pending[action] ? "…" : t("Set"), disabled: S.pending[action] ? true : null,
      onclick: function () { var v = prep(inp.value); if (v !== (cur || none)) run(action, { value: v }); } }))];
  }
  function rulesChips(cur) {
    var five = ["military", "helicopter", "heavy", "rare", "farthest"], every = cur === "all" || cur === "any";   // "any": its name before 0.19.1
    var picked = every ? five.slice() : String(cur || "").split(",").filter(function (w) { return five.indexOf(w) >= 0; });   // the server gives the default when unset
    var names = { military: t("Military"), helicopter: t("Helicopters"), heavy: t("Heavies"), rare: t("Rare types"), farthest: t("Range records") };
    var waiting = S.pending["social-rules"];
    var chips = five.map(function (w) {
      var lit = picked.indexOf(w) >= 0;
      return h("button", { type: "button", "class": "chip" + (lit ? " on" : "") + (every ? " static" : ""), "aria-pressed": lit ? "true" : "false", text: names[w],
        disabled: (every || waiting) ? true : null, onclick: function () {
          var next = lit ? picked.filter(function (x) { return x !== w; }) : picked.concat([w]);
          if (!next.length) return toast(t("At least one."));
          run("social-rules", { value: five.filter(function (x) { return next.indexOf(x) >= 0; }).join(",") });
        } });
    });
    chips.push(h("button", { type: "button", "class": "chip" + (every ? " on" : ""), "aria-pressed": every ? "true" : "false", text: t("Everything"), disabled: waiting ? true : null,
      onclick: function () { run("social-rules", { value: every ? five.join(",") : "all" }); } }));
    return h("div", { "class": "chips" }, chips);
  }
  function select(action, values, current, labels) {
    var waiting = S.pending[action];
    var s = h("select", { "aria-label": (S.catalog[action] || {}).label, disabled: waiting ? true : null,
      onchange: function () { run(action, { value: s.value }); } },
      values.map(function (v, i) { return h("option", { value: v, text: labels[i], selected: String(v) === String(current) ? true : null }); }));
    return s;
  }
  function swatches() {
    var cur = S.cfg.THEME || "amber", w = waitingFor("color");
    return h("div", { "class": "swatches", role: "group", "aria-label": t("Colour") }, Object.keys(THEME_HEX).map(function (col) {
      var b = h("button", { type: "button", "class": "swatch" + (w !== undefined ? (col === w ? " wait" : "") : (col === cur ? " on" : "")),
        title: word(col), "aria-label": word(col), "aria-pressed": col === cur ? "true" : "false", disabled: S.pending.color ? true : null,
        onclick: function () { if (col !== cur) run("color", { value: col }); } });
      b.style.background = THEME_HEX[col];
      return b;
    }));
  }
  function sentenceChips(cur) {
    // 0.51.0: "your own", the owner's templates, while there is one
    var has = /\S/.test(S.templates || ""), all = ["factual", "story", "board", "spotter", "lookup"].concat(has ? ["custom"] : []);
    var picked = cur === "random" ? all.slice() : cur.split(",");
    var waiting = S.pending["social-sentence"];
    return h("div", { "class": "chips" }, all.map(function (w) {
      var lit = picked.indexOf(w) >= 0;
      return h("button", { type: "button", "class": "chip" + (lit ? " on" : ""), "aria-pressed": lit ? "true" : "false", text: word(w), disabled: waiting ? true : null,
        onclick: function () {
          var next = lit ? picked.filter(function (x) { return x !== w; }) : picked.concat([w]);
          if (!next.length) return toast(t("At least one."));
          next = all.filter(function (x) { return next.indexOf(x) >= 0; });
          run("social-sentence", { value: next.length === all.length ? "random" : next.join(",") });
        } });
    }));
  }
  // 0.51.0: the owner's own templates: one per line, the tags a click away, tried on an aircraft overhead before they
  // are saved. The draft outlives the page's redraws.
  var TAGS = [["flight", t("the flight number when known (FR4512), else the callsign")], ["callsign", t("the callsign as sent (RYR4512)")],
    ["airline", t("the airline")], ["airline_country", t("the country the airline is based in")], ["flag", t("that country's flag, as an emoji")],
    ["registration", t("the registration, as a hashtag: #EI-ENK")], ["reg_country", t("the country it is registered in")], ["type", t("make and model")],
    ["type_code", t("the ICAO type code (B738)")], ["category", t("airliner, cargo aircraft, business jet, helicopter…")],
    ["from", t("departure, city and code: Dublin (DUB)")], ["to", t("arrival, city and code")], ["from_code", t("the departure's code")],
    ["to_code", t("the arrival's code")], ["altitude", t("the altitude")], ["speed", t("the ground speed")], ["climb", t("climbing, descending or level")],
    ["heading", t("where it is heading: south-east")], ["squawk", t("its transponder code")], ["why", t("why it is posted: A rare visitor.")],
    ["area", t("your place name, as the posts say it")], ["time", t("the time")], ["date", t("the date")],
    ["photo", t("its Planespotters page, when photo links are on")], ["tracker", t("its page on ADSB Exchange's map")],
    ["hashtags", t("your hashtags (then not added again at the end)")]];
  function templatesCard() {
    var title = t("Your own templates");
    // the file changed on the Pi: read again what it holds now, and drop the draft that showed the old one
    function tplButton(label, action, cls) {
      var busy = S.pending[action];
      return h("button", { type: "button", "class": cls, disabled: busy ? true : null, text: busy ? label + "…" : label, onclick: function () {
        run(action, {}, { card: title }).then(function (j) { if (j && j.rc === 0) { S.tplDraft = null; loadState(); } });
      } });
    }
    var ta = h("textarea", { rows: 4, dir: "auto", spellcheck: "false", "aria-label": title,
      placeholder: "{flag} {airline} {flight}[, {from} → {to}] · {type} at {altitude}. {why}" });
    ta.value = S.tplDraft !== undefined && S.tplDraft !== null ? S.tplDraft : (S.templates || "").replace(/\s+$/, "");
    ta.addEventListener("input", function () { S.tplDraft = ta.value; });
    function insert(tag) {
      var a = ta.selectionStart || 0, b = ta.selectionEnd || 0, v = ta.value;
      ta.value = v.slice(0, a) + "{" + tag + "}" + v.slice(b); S.tplDraft = ta.value;
      ta.focus(); ta.selectionStart = ta.selectionEnd = a + tag.length + 2;
    }
    function text() { return ta.value.replace(/\r\n?/g, "\n").split("\n").map(function (l) { return l.trim(); }).filter(Boolean).join("\n"); }
    var help = h("details", { "class": "tags-help", open: S.tplHelp ? true : null, ontoggle: function () { S.tplHelp = help.open; } },
      h("summary", { text: t("The tags: click one to put it in") }),
      h("div", { "class": "chips" }, TAGS.map(function (x) {
        return h("button", { type: "button", "class": "chip", title: x[1], text: "{" + x[0] + "}", onclick: function () { insert(x[0]); } });
      })),
      h("ul", { "class": "tags-list" }, TAGS.map(function (x) { return h("li", null, h("code", { text: "{" + x[0] + "}" }), " " + x[1]); }),
        h("li", null, h("code", { text: "[ … ]" }), " " + t("a part left out when a tag inside it is empty: [{from} → {to}]")),
        h("li", null, h("code", { text: "{tag|cap}" }), " " + t("with a capital letter"))));
    return card(title, "picture", t("Posts in your words, in your language, one template per line; ZenithBoard fills in the tags. Used when “your own” is ticked in the words of a post; with several, one is drawn at each post. Nothing gives the receiver's position away."), [
      ta, help,
      h("div", { "class": "actions" },
        h("button", { type: "button", "class": "btn", text: S.pending["social-template-try"] ? t("Try (posts nothing)") + "…" : t("Try (posts nothing)"),
          disabled: S.pending["social-template-try"] ? true : null,
          onclick: function () { var v = text(); if (!v) return toast(t("Write a template first."), true); run("social-template-try", { text: v }, { card: title }); } }),
        h("button", { type: "button", "class": "primary", text: S.pending["social-templates"] ? t("Save") + "…" : t("Save"), disabled: S.pending["social-templates"] ? true : null,
          onclick: function () {
            var v = text();
            // an emptied field deletes them all: through the button that asks first, not a silent "none"
            if (!v) {
              if (!(S.templates || "").trim()) return toast(t("Write a template first."), true);
              return run("social-templates-delete", {}, { card: title }).then(function (j) { if (j && j.rc === 0) { S.tplDraft = null; loadState(); } });
            }
            run("social-templates", { text: v }, { card: title }).then(function (j) {
              if (!j || j.rc !== 0) return;
              S.templates = v;
              if (S.tplDraft === null || S.tplDraft === undefined || text() === v) {   // a draft typed meanwhile stays
                S.tplDraft = null;
                if (document.activeElement && document.activeElement.tagName === "TEXTAREA") document.activeElement.blur();
              }
              draw();
            });
          } }),
        // 0.53.3: delete them all with a real button (the owner), and put back the ones before the last change
        S.templates && S.templates.trim() ? tplButton(t("Delete them all"), "social-templates-delete", "danger") : null,
        S.templatesBefore ? tplButton(t("Put back the previous ones"), "social-templates-undo", "btn") : null)
    ], "w12");
  }
  // 0.99.6: Telegram, the messages to the owner's own chat. The bot's token and the chat are set up over SSH (a token is
  // never typed here); everything else is here.
  function tgRulesChips(cur) {
    var three = ["military", "helicopter", "heavy"], every = !cur || cur === "all";
    var picked = every ? three.slice() : String(cur).split(",").filter(function (w) { return three.indexOf(w) >= 0; });
    var names = { military: t("Military"), helicopter: t("Helicopters"), heavy: t("Heavies") };
    var waiting = S.pending["telegram-rules"];
    var chips = three.map(function (w) {
      var lit = picked.indexOf(w) >= 0;
      return h("button", { type: "button", "class": "chip" + (lit ? " on" : "") + (every ? " static" : ""), "aria-pressed": lit ? "true" : "false", text: names[w],
        disabled: (every || waiting) ? true : null, onclick: function () {
          var next = lit ? picked.filter(function (x) { return x !== w; }) : picked.concat([w]);
          if (!next.length) return toast(t("At least one."));
          run("telegram-rules", { value: three.filter(function (x) { return next.indexOf(x) >= 0; }).join(",") });
        } });
    });
    chips.push(h("button", { type: "button", "class": "chip" + (every ? " on" : ""), "aria-pressed": every ? "true" : "false", text: t("Everything"), disabled: waiting ? true : null,
      onclick: function () { run("telegram-rules", { value: every ? three.join(",") : "all" }); } }));
    return h("div", { "class": "chips" }, chips);
  }
  function telegramCard() {
    var c = S.cfg, chat = S.facts.telegram_chat, langs = ["posts"].concat(I.langs().indexOf("en") < 0 ? ["en"].concat(I.langs()) : I.langs());
    return card(t("Telegram"), "share", chat ? t("To the chat {chat}. The bot and the chat are set up over SSH (it asks for the bot's token): sudo zenithboard telegram setup", { chat: chat }) :
      t("No Telegram bot yet. Set it up over SSH, it asks for the bot's token from @BotFather and lets you choose the chat: sudo zenithboard telegram setup"), [
      row(t("Send the messages"), t("Text only, to your own chat or group; never public."), chat ? sw("telegram", on(c.TELEGRAM)) : h("span", { "class": "state", text: t("needs a bot") })),
      row(t("Aircraft crossing the sharing radius"), t("One message per crossing, as the Bluesky posts, inside the sharing radius ({n} km)", { n: c.SOCIAL_RADIUS_KM || "15" }), sw("telegram-crossings", on(c.TELEGRAM_CROSSINGS))),
      on(c.TELEGRAM_CROSSINGS) ? row(t("Which crossings"), c.TELEGRAM_RULES === "all" || !c.TELEGRAM_RULES ? t("Everything: every crossing") : t("Only the kinds lit; Everything writes every crossing"), tgRulesChips(c.TELEGRAM_RULES)) : null,
      row(t("Emergency squawks"), t("7500, 7600, 7700 anywhere the antenna hears them, not only in the radius; once per flight, with where the aircraft is. Never posted to Bluesky."), sw("telegram-squawks", on(c.TELEGRAM_SQUAWKS))),
      row(t("Language of the messages"), null, select("telegram-lang", langs, c.TELEGRAM_LANG || "posts", langs.map(function (l) { return l === "posts" ? t("The posts' ({lang})", { lang: I.name(c.SOCIAL_LANG || "en") }) : I.name(l); }))),
      row(t("Units"), null, seg("telegram-units", ["posts", "metric", "imperial", "aviation"], c.TELEGRAM_UNITS || "posts", [t("The posts'"), t("Metric"), t("Imperial"), t("Aviation")])),
      h("div", { "class": "actions" }, btn(t("Try the messages (sends nothing)"), "telegram-test"), chat ? btn(t("Send a test to the chat"), "telegram-test-send") : null, btn(t("Status"), "telegram-status"))
    ], "w6");
  }
  // the owner's own message for each kind: the whole message, lines kept, the tags a click away
  var TG_TAGS = TAGS.filter(function (x) { return x[0] !== "hashtags"; }).concat([["near", t("where the aircraft is: the town nearest it, or a city and how far (never from the antenna)")],
    ["meaning", t("what the emergency squawk means, in the messages' language")], ["hex", t("the aircraft's ICAO address (4ca7b1)")]]);
  function telegramTemplatesCard() {
    var title = t("Your own Telegram messages"), kind = S.tgKind || "crossing", saved = ((S.tgTemplates || {})[kind] || "").replace(/\s+$/, "");
    S.tgDraft = S.tgDraft || {};
    var ta = h("textarea", { rows: 7, dir: "auto", spellcheck: "false", "aria-label": title,
      placeholder: kind === "squawk" ? "🚨 Squawk {squawk}: {meaning}\n{flight}[ · {airline}][ · {type}]\n[{near}]\n{time}[ · {tracker}]" : "✈ {flight}[ · {airline}]\n[{from} → {to}]\n[{altitude}][ · {speed}]\n{time}[ · {area}]" });
    ta.value = S.tgDraft[kind] !== undefined && S.tgDraft[kind] !== null ? S.tgDraft[kind] : saved;
    ta.addEventListener("input", function () { S.tgDraft[kind] = ta.value; });
    function insert(tag) {
      var a = ta.selectionStart || 0, b = ta.selectionEnd || 0, v = ta.value;
      ta.value = v.slice(0, a) + "{" + tag + "}" + v.slice(b); S.tgDraft[kind] = ta.value;
      ta.focus(); ta.selectionStart = ta.selectionEnd = a + tag.length + 2;
    }
    function text() { return ta.value.replace(/\r\n?/g, "\n").split("\n").map(function (l) { return l.replace(/\s+$/, ""); }).join("\n").replace(/^\n+|\n+$/g, ""); }
    function after(j) { if (j && j.rc === 0) { S.tgDraft[kind] = null; loadState(); } }
    var help = h("details", { "class": "tags-help", open: S.tgHelp ? true : null, ontoggle: function () { S.tgHelp = help.open; } },
      h("summary", { text: t("The tags: click one to put it in") }),
      h("div", { "class": "chips" }, TG_TAGS.map(function (x) { return h("button", { type: "button", "class": "chip", title: x[1], text: "{" + x[0] + "}", onclick: function () { insert(x[0]); } }); })),
      h("ul", { "class": "tags-list" }, TG_TAGS.map(function (x) { return h("li", null, h("code", { text: "{" + x[0] + "}" }), " " + x[1]); }),
        h("li", null, h("code", { text: "[ … ]" }), " " + t("a part left out when a tag inside it is empty: [{from} → {to}]")),
        h("li", null, h("code", { text: "{tag|cap}" }), " " + t("with a capital letter"))));
    var kinds = h("div", { "class": "seg", role: "group" }, [["crossing", t("Crossing")], ["squawk", t("Emergency squawk")]].map(function (k) {
      return h("button", { type: "button", "class": k[0] === kind ? "on" : "", "aria-pressed": k[0] === kind ? "true" : "false", text: k[1], onclick: function () { S.tgKind = k[0]; draw(); } });
    }));
    return card(title, "picture", t("Each kind of message in your words, lines kept; ZenithBoard fills in the tags, in the messages' language. Empty: the default. Nothing gives the receiver's position away."), [
      row(t("The message"), (S.tgTemplates || {})[kind] && (S.tgTemplates || {})[kind].trim() ? t("Yours") : t("The default, until you save one"), kinds),
      ta, help,
      h("div", { "class": "actions" },
        h("button", { type: "button", "class": "btn", text: t("Show the default"), disabled: S.pending["telegram-template-default"] ? true : null,
          onclick: function () { run("telegram-template-default", { kind: kind }, { card: title }); } }),
        h("button", { type: "button", "class": "btn", text: S.pending["telegram-template-try"] ? t("Try (sends nothing)") + "…" : t("Try (sends nothing)"), disabled: S.pending["telegram-template-try"] ? true : null,
          onclick: function () { var v = text(); if (!v) return toast(t("Write a template first."), true); run("telegram-template-try", { kind: kind, text: v }, { card: title }); } }),
        h("button", { type: "button", "class": "primary", text: S.pending["telegram-template"] ? t("Save") + "…" : t("Save"), disabled: S.pending["telegram-template"] ? true : null,
          onclick: function () {
            var v = text();
            if (!v) {
              if (!saved.trim()) return toast(t("Write a template first."), true);
              return run("telegram-template-delete", { kind: kind }, { card: title }).then(after);
            }
            run("telegram-template", { kind: kind, text: v }, { card: title }).then(after);
          } }),
        saved.trim() ? h("button", { type: "button", "class": "danger", text: t("Back to the default"), disabled: S.pending["telegram-template-delete"] ? true : null,
          onclick: function () { run("telegram-template-delete", { kind: kind }, { card: title }).then(after); } }) : null)
    ], "w12");
  }
  function summariesBlocked(acct, c) {
    if (!acct) return h("p", { "class": "note", text: t("No Bluesky account yet: no summary goes out until one is set up (Sharing → Bluesky).") });
    if (!on(c.SOCIAL)) return h("p", { "class": "note", text: t("Posting is off: no summary goes out until “Post the aircraft overhead” is on (Sharing → Bluesky).") });
    return null;
  }
  function summaryRow(p, title) {
    var c = S.cfg, k = "SOCIAL_" + p.toUpperCase(), at = c[k + "_AT"] || "", parts = (c[k + "_PARTS"] || "1").split(","), lit = on(c[k]);
    var bits = at.split(" "), time = bits[bits.length - 1], day = bits.length > 1 ? bits[0] : "";
    var tIn = h("input", { type: "time", value: time, "aria-label": t("{what}: time", { what: title }) }), dIn = null;
    if (p === "weekly") dIn = h("select", { "aria-label": t("Day") }, ["mon", "tue", "wed", "thu", "fri", "sat", "sun"].map(function (d) {
      return h("option", { value: d, text: dayName(d), selected: d === day ? true : null }); }));
    if (p === "monthly") dIn = h("input", { type: "number", "class": "day", min: 1, max: 28, value: day || "1", "aria-label": t("Day of the month") });
    var keyAt = "at-" + p, keyParts = "parts-" + p;
    return h("div", { "class": "row" },
      h("div", { "class": "what" }, h("b", { text: title }), h("span", { text: lit ? t("On: {when}, posts {posts}", { when: day && p === "weekly" ? dayName(day) + " " + time : at, posts: parts.join(", ") }) : t("Off") }),
        lit ? h("span", { "class": "when", text: whenLine(p) }) : null),
      h("div", { "class": "ctl" },
        sw("summary", lit, { period: p }, "summary-" + p, title),
        dIn, tIn,
        onEnter(tIn, h("button", { type: "button", "class": "btn", text: S.pending[keyAt] ? "…" : t("Set"), disabled: S.pending[keyAt] ? true : null, onclick: function () {
          var when = (dIn ? String(dIn.value).trim() + " " : "") + tIn.value;
          if (when !== at) run("summary-at", { period: p, when: when }, { key: keyAt });
        } })),
        h("div", { "class": "chips" }, ["1", "2", "3", "4"].map(function (n) {
          var has = parts.indexOf(n) >= 0;
          return h("button", { type: "button", "class": "chip" + (has ? " on" : "") + (n === "1" ? " static" : ""), text: n, title: n === "1" ? t("The first always goes") : null,
            "aria-pressed": has ? "true" : "false", disabled: (n === "1" || S.pending[keyParts]) ? true : null, onclick: function () {
              var next = has ? parts.filter(function (x) { return x !== n; }) : parts.concat([n]);
              run("summary-parts", { period: p, value: next.sort().join(",") }, { key: keyParts });
            } });
        })),
        h("button", { type: "button", "class": "btn", text: t("Try (posts nothing)"), onclick: function () { run("summary-test", { period: p }, { key: "test-" + p, card: S.lastCard }); } })));
  }
  // 0.48.0: when that summary last went out and goes next, as the Pi computes it (one a day, a week, a month)
  function whenLine(p) {
    var f = S.facts, last = f["sum_" + p + "_last"], next = f["sum_" + p + "_next"];
    if (last === undefined && next === undefined) return "";
    var bits = [t("last: {when}", { when: last ? stamp(last) : t("never") })];
    if (next) bits.push(next === "now" ? t("next: now") : t("next: {when}", { when: stamp(next) }));
    return bits.join(" · ");
  }
  function stamp(v) {           // "2026-10-22 23:35" in the page's language; a day alone ("2026-10-21", a week "2026-W43") as it is
    var m = /^(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d)$/.exec(v || "");
    if (!m) return v;
    try { return new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]).toLocaleString(I.locale(), { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }); } catch (e) { return v; }
  }
  // 0.54.18 (the owner's screenshot, 24 October 2026): eleven tiles in one grid became three groups, each one folding to
  // its title alone: what this Pi shows, the networks it feeds, and Bluesky. Each group remembers, in this browser,
  // whether it was left folded.
  function pagesGroups() {
    var f = S.facts, c = S.cfg, hh = host(), list = [], groups = [];
    function group(id, title) { list = []; groups.push({ id: id, title: title, items: list }); }
    function page(icon, title, sub, href) { return h("a", { "class": "page", href: href, target: "_blank", rel: "noopener" }, ico(icon), h("div", null, h("b", { text: title }), h("span", { text: sub }))); }
    function later(icon, title, sub, section) { return h("button", { type: "button", "class": "page later", onclick: go(section) }, ico(icon), h("div", null, h("b", { text: title }), h("span", { text: sub }))); }
    group("pi", t("On this Pi"));
    list.push(page("wall", t("The wall"), (c.DISPLAY_MODE === "flap" ? t("Split-flap") : t("Dot matrix")) + ", " + word(c.THEME || "amber"), "/"));
    list.push(on(c.STATS) ? page("chart", t("Statistics"), t("24 h, 7 days, 30 days"), "/stats") : later("chart", t("Statistics"), t("Off · switch on in Receiver"), "receiver"));
    if (f.map) list.push(page("map", t("Receiver map"), t("tar1090, on port 80"), "http://" + hh + "/tar1090/"));
    if (f.skyaware) list.push(page("map", t("SkyAware"), t("FlightAware's map"), "http://" + hh + "/skyaware/"));
    list.push(f.graphs === "on" ? page("graph", "graphs1090", t("The decoder's graphs, port 8542"), "http://" + hh + ":8542/" + langQ()) : later("graph", "graphs1090", t("Off · switch on in Receiver"), "receiver"));
    group("feeds", t("The networks you feed"));
    if (f.svc_pfclient !== undefined) list.push(page("plane", t("Plane Finder"), t("Its own page, port 30053"), "http://" + hh + ":30053/"));
    if (f.svc_fr24feed !== undefined) list.push(page("plane", t("Flightradar24"), t("Its feeder's page, port 8754"), "http://" + hh + ":8754/"));
    // 0.99.6: AirNav Radar has no page on the Pi: its station's page on their site once rbfeeder said its serial, else where to claim it
    if (f.svc_rbfeeder !== undefined) list.push(h("a", { "class": "page", href: rbStation() ? "https://www.airnavradar.com/stations/" + rbStation() : "https://www.airnavradar.com/raspberry-pi/claim", target: "_blank", rel: "noopener noreferrer" },
      ico("link"), h("div", null, h("b", { text: t("AirNav Radar, formerly RadarBox") }), h("span", { text: rbStation() ? t("Station {serial}, on their site", { serial: rbStation() }) : t("Claim this station, on their site") }))));
    if (f.svc_adsbexchange_feed !== undefined) list.push(h("a", { "class": "page", href: "https://www.adsbexchange.com/myip/", target: "_blank", rel: "noopener noreferrer" }, ico("link"), h("div", null, h("b", { text: t("ADSB Exchange") }), h("span", { text: t("Your feed, on their site") }))));
    if (adsbxMap()) list.push(h("a", { "class": "page", href: adsbxMap(), target: "_blank", rel: "noopener noreferrer" }, ico("map"), h("div", null, h("b", { text: t("Your aircraft on ADSB Exchange") }), h("span", { text: t("Their map: only what your antenna hears") }))));
    // on, but the UUID unreadable here: their myip page carries the same link at its bottom
    else if (f.adsbx_stats === "on") list.push(h("a", { "class": "page", href: "https://www.adsbexchange.com/myip/", target: "_blank", rel: "noopener noreferrer" }, ico("map"), h("div", null, h("b", { text: t("Your aircraft on ADSB Exchange") }), h("span", { text: t("Your feed, on their site") }))));
    else if (f.svc_adsbexchange_feed !== undefined) list.push(later("map", t("Your aircraft on ADSB Exchange"), t("Off · switch on in Receiver"), "receiver"));
    group("bluesky", t("Bluesky"));
    if (f.bluesky) {
      list.push(page("picture", t("Last post's picture"), t("What 'Try a post' drew"), "/social/preview"));
      ["2", "3", "4"].forEach(function (n) { list.push(page("picture", t("Weekly post {n}", { n: n }), ["", "", t("Cargo and business jets"), t("Military"), t("General aviation")][Number(n)], "/social/preview" + n)); });
    } else list.push(later("share", t("Bluesky posts"), t("No account yet · see Sharing"), "sharing"));
    return groups.filter(function (g) { return g.items.length; });
  }
  function folded(key) { try { return window.localStorage.getItem("zb.fold." + key) === "1"; } catch (e) { return false; } }
  function shown(key) { try { return window.localStorage.getItem("zb.fold." + key) === "0"; } catch (e) { return false; } }   // left open
  function remember(key, isFolded) { try { window.localStorage.setItem("zb.fold." + key, isFolded ? "1" : "0"); } catch (e) { /* private window */ } }
  // 0.55.0: the radius's unit, by the wall's units (aviation: nautical miles, as pilots count)
  function distUnit(u) { return u === "imperial" ? "mi" : u === "aviation" ? "NM" : "km"; }
  function pages() {
    return pagesGroups().map(function (g) {
      var d = h("details", { "class": "fold", open: folded("pages." + g.id) ? null : true }, h("summary", null, h("bdi", { text: g.title }), h("span", { "class": "n-items", text: "· " + num(g.items.length) })),
        h("div", { "class": "pages" }, g.items));
      d.addEventListener("toggle", function () { remember("pages." + g.id, !d.open); });
      return d;
    });
  }

  // ---- signed-in browsers and phones
  function loadSessions() {
    return api("sessions").then(function (r) { if (r.ok) { S.sessions = r.data; if (S.section === "system") draw(); } });
  }
  function sessionsList() {
    if (!S.sessions) { loadSessions(); return h("p", { "class": "note", text: t("Reading…") }); }
    // 0.54.18 (the owner's screenshot): this browser first, the others under one line that unfolds, folded once
    // there are more than two of them
    var all = S.sessions.sessions, mine = all.filter(function (s) { return s.id === S.sessions.you; }),
      others = all.filter(function (s) { return s.id !== S.sessions.you; });
    if (others.length <= 2) return h("div", { "class": "list" }, mine.concat(others).map(sessionRow));
    var d = h("details", { "class": "fold", open: S.othersOpen || shown("sessions.others") ? true : null },
      h("summary", { text: tn(others.length, "{n} other browser or phone", "{n} other browsers and phones", { n: num(others.length) }) }),
      h("div", { "class": "list" }, others.map(sessionRow)));
    d.addEventListener("toggle", function () { S.othersOpen = d.open; remember("sessions.others", !d.open); });
    return h("div", null, h("div", { "class": "list" }, mine.map(sessionRow)), d);
  }
  function sessionRow(s) {
      var me = s.id === S.sessions.you;
      return h("div", { "class": "li" }, h("div", null, h("b", { text: s.label + (me ? " · " + t("this one") : "") }),
        h("small", { text: t("{how} · since {since} · seen {seen}", { how: s.kind === "paired" ? t("paired") : s.kind === "approved" ? t("by the phone") : t("password"), since: ago(s.created), seen: ago(s.seen) }) })),
        me ? h("span", { "class": "pill ok", text: t("you") }) : h("button", { type: "button", "class": "btn", text: t("Sign out"), onclick: function () {
          api("sessions/revoke", { body: { id: s.id } }).then(function () { loadSessions(); });
        } }));
  }

  // ---- pairing a phone: a QR code, dark on its own white square (a code on the black page would not scan)
  function qrSvg(text) {
    var q = window.qrcode(0, "M"); q.addData(text); q.make();
    var n = q.getModuleCount(), m = 4, sz = n + 2 * m, d = "";
    for (var r = 0; r < n; r++) for (var c = 0; c < n; c++) if (q.isDark(r, c)) d += "M" + (c + m) + " " + (r + m) + "h1v1h-1z";
    var NS = "http://www.w3.org/2000/svg", s = document.createElementNS(NS, "svg"), bg = document.createElementNS(NS, "rect"), p = document.createElementNS(NS, "path");
    s.setAttribute("viewBox", "0 0 " + sz + " " + sz); s.setAttribute("shape-rendering", "crispEdges"); s.setAttribute("role", "img"); s.setAttribute("aria-label", "QR code");
    bg.setAttribute("width", sz); bg.setAttribute("height", sz); bg.setAttribute("fill", "#ffffff");
    p.setAttribute("d", d); p.setAttribute("fill", "#000000");
    s.appendChild(bg); s.appendChild(p);
    return s;
  }
  function pairPhone(after) {
    var local = /^(localhost|127\.|\[?::1)/.test(location.hostname);
    api("pair", { body: {} }).then(function (r) {
      if (!r.ok) return toast(t(r.data.error || "Could not make a pairing code."), true);
      var url = location.protocol + "//" + location.host + "/console/#pair=" + r.data.token, until = Date.now() + r.data.seconds * 1000;
      var count = h("div", { "class": "count" }), status = h("p", { "class": "qr-note", text: t("Scan it with the phone's camera, then open the link.") });
      var box = h("div", { "class": "qr" }, qrSvg(url));
      openModal(h("div", null,
        h("header", null, h("h2", { text: t("Pair a phone") }), h("button", { type: "button", "class": "ghost", "aria-label": t("Close"), text: "×", onclick: stop })),
        h("div", { "class": "modal-body" }, local ? h("p", { "class": "err", text: t("This page was opened as {host}: a phone cannot reach that. Open the console at the Pi's address to pair one.", { host: location.hostname }) }) : null,
          box, count, status,
          h("p", { "class": "qr-note", text: t("The phone must be on your home Wi-Fi: not mobile data, not a guest network.") }),
          h("p", { "class": "qr-note", text: t("It works once, within five minutes. The phone then stays signed in as long as it opens the console once a month.") }))));
      var timer = setInterval(tickPair, 1000), poll = setInterval(checkPair, 2000);
      function tickPair() {
        var left = Math.max(0, Math.round((until - Date.now()) / 1000));
        count.textContent = Math.floor(left / 60) + ":" + ("0" + left % 60).slice(-2);
        if (!left) { box.hidden = true; status.textContent = t("Out of date. Close this and make a new one."); clearInterval(timer); clearInterval(poll); }
      }
      function checkPair() {
        api("pair?id=" + r.data.id).then(function (p) {
          if (p.ok && p.data.used_by) {
            clearInterval(timer); clearInterval(poll);
            box.hidden = true; count.hidden = true; status.className = "qr-ok"; status.textContent = "✓ " + t("{name} signed in.", { name: p.data.used_by });
            S.sessions = null; loadSessions();
          }
        });
      }
      function stop() { clearInterval(timer); clearInterval(poll); closeModal(); if (typeof after === "function") after(); }
      tickPair();
    });
  }

  // ---- the activity drawer
  // 0.99.18 (review B10): a panel opened over the page takes the keyboard with it and gives it back. What opened it is
  // remembered (by its key too: the page may have been drawn again meanwhile), the page behind is inert (Tab, a screen
  // reader and a click cannot reach it), Tab goes round inside the panel, and closing it puts the focus back where it was:
  // in the drawer when a question closes over it.
  var FOCUSABLE = "button, a[href], input, select, textarea, summary, [tabindex]:not([tabindex='-1'])";
  function opener() { var a = document.activeElement; return { el: a, fk: fkOf(a) }; }
  function giveBack(o, within, fallback) {
    if (o && o.el && o.el.isConnected && within.contains(o.el) && !o.el.closest("[inert]")) { o.el.focus({ preventScroll: true }); return; }
    if (o && o.fk) { refocus(within, o.fk, null); if (within.contains(document.activeElement) && document.activeElement !== document.body) return; }
    if (fallback) fallback.focus({ preventScroll: true });
  }
  function shield() {
    var modalOn = !$("modal").hidden, drawerOn = !$("drawer").hidden;
    $("app").inert = modalOn || drawerOn; $("gate").inert = modalOn;
    $("drawer").inert = modalOn;
  }
  function topPanel() { return !$("modal").hidden ? $("modal-panel") : !$("drawer").hidden ? $("drawer").querySelector(".drawer-panel") : null; }
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Tab") return;
    var p = topPanel(); if (!p) return;
    var list = Array.prototype.filter.call(p.querySelectorAll(FOCUSABLE), function (n) { return !n.disabled && n.getClientRects().length; });
    if (!list.length) { e.preventDefault(); return; }
    var first = list[0], last = list[list.length - 1], a = document.activeElement;
    if (!p.contains(a)) { e.preventDefault(); (e.shiftKey ? last : first).focus(); }
    else if (e.shiftKey && a === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && a === last) { e.preventDefault(); first.focus(); }
  });
  function openDrawer(jobId) {
    S.drawerJob = jobId || S.drawerJob; S.activityOpen = true;
    if ($("drawer").hidden) S.drawerOpener = opener();
    $("drawer").hidden = false; document.body.style.overflow = "hidden"; shield();
    drawDrawer(); loadActivity();
    $("drawer").querySelector(".drawer-panel header [data-close=drawer]").focus();
  }
  function closeDrawer() {
    var was = !$("drawer").hidden;
    $("drawer").hidden = true; S.activityOpen = false; document.body.style.overflow = ""; shield();
    if (was && S.session) giveBack(S.drawerOpener, $("app"), $("open-activity"));
    S.drawerOpener = null;
  }
  function loadActivity() { api("activity").then(function (r) { if (r.ok) { S.activity = r.data; drawDrawer(); } }); }
  function termText(j) {
    if (j.log || j.state !== "queued") return j.log || "";
    if (!j.behind) return t("Waiting for the Pi's helper…");
    var job = t((S.catalog[j.behind] || {}).label || j.behind);
    return j.ahead ? tn(j.ahead, "Waiting: {job} runs first ({n} before this one). The Pi does one change at a time.", "Waiting: {job} runs first ({n} before this one). The Pi does one change at a time.", { job: job })
      : t("Waiting: {job} runs first. The Pi does one change at a time.", { job: job });
  }
  function pillOf(j) {
    return j.state === "done" ? (j.rc === 0 ? ["ok", word("done")] : ["bad", t("exit {rc}", { rc: j.rc })]) : j.state === "refused" ? ["bad", word("refused")] : [j.state === "running" ? "run" : "queued", word(j.state || "queued")];
  }
  var termPre = null, termPill = null;
  function drawTerm() {
    var j = S.jobs[S.drawerJob];
    if (!j || !termPre) return;
    var atEnd = termPre.scrollHeight - termPre.scrollTop - termPre.clientHeight < 40;
    termPre.textContent = termText(j);
    if (atEnd) termPre.scrollTop = termPre.scrollHeight;
    var st = pillOf(j);
    termPill.className = "pill " + st[0]; termPill.textContent = st[1];
  }
  function drawDrawer() {
    var body = $("drawer-body"), focused = document.activeElement, fk = body.contains(focused) ? fkOf(focused) : null;
    body.innerHTML = ""; termPre = null;
    try { drawDrawerBody(body); } finally { keyAll(body); refocus(body, fk, focused); }
  }
  function drawDrawerBody(body) {
    var j = S.jobs[S.drawerJob];
    if (j) {
      termPre = h("pre"); termPill = h("span", { "class": "pill" });
      body.appendChild(h("div", { "class": "term" }, h("div", { "class": "th" }, ico("terminal"), h("b", { text: j.label }), termPill), termPre));
      drawTerm();
      if (j.state === "done" && j.rc === 0 && (j.action === "social-test" || j.action === "summary-test")) {
        body.appendChild(h("div", { "class": "actions" }, h("a", { "class": "btn", href: j.action === "summary-test" ? "/social/preview1" : "/social/preview", target: "_blank", rel: "noopener", text: j.action === "summary-test" ? postName(1) : t("The picture ↗") }),
          j.action === "summary-test" ? ["2", "3", "4"].map(function (n) { return h("a", { "class": "btn", href: "/social/preview" + n, target: "_blank", rel: "noopener", text: postName(n) }); }) : null));
      }
    }
    var a = S.activity;
    if (!a) { body.appendChild(h("p", { "class": "note", text: t("Reading…") })); return; }
    body.appendChild(h("div", null, h("p", { "class": "sub", text: t("The last jobs") }), h("div", { "class": "list" }, a.jobs.filter(function (x) { return x.action !== "refresh"; }).length ? a.jobs.filter(function (x) { return x.action !== "refresh"; }).slice(0, 12).map(function (x) {
      var spec = S.catalog[x.action] || { label: x.action }, ok = x.state === "done" && x.rc === 0, lbl = t(spec.label);
      var params = x.params && typeof x.params === "object" ? Object.keys(x.params).map(function (k) { return x.params[k]; }).filter(Boolean).join(" ") : "";
      return h("button", { type: "button", "class": "li" + (x.id === S.drawerJob ? " sel" : ""), "aria-current": x.id === S.drawerJob ? "true" : null, onclick: function () { showOld(x); } },
        h("div", null, h("b", { text: params ? t("{job}: {value}", { job: lbl, value: word(params) }) : lbl }), h("small", { text: clock(x.started || 0) + " · " + (x.by || "") })),
        h("span", { "class": "pill " + (x.state === "running" ? "run" : ok ? "ok" : x.state === "done" || x.state === "refused" ? "bad" : "queued"), text: x.state === "done" ? (ok ? t("ok") : t("exit {rc}", { rc: x.rc })) : word(x.state) }));
    }) : h("p", { "class": "note", text: t("Nothing run from the console yet.") }))));
    body.appendChild(h("div", null, h("p", { "class": "sub", text: t("Changes (the root helper's journal)") }), h("pre", { "class": "mono-list", text: a.journal.join("\n") || t("None yet.") })));
    body.appendChild(h("div", null, h("p", { "class": "sub", text: t("Sign-ins") }), h("pre", { "class": "mono-list", text: a.audit.join("\n") || t("None yet.") })));
  }
  function showOld(x) {
    if (!S.jobs[x.id]) S.jobs[x.id] = { id: x.id, action: x.action, label: t((S.catalog[x.action] || {}).label || x.action), params: x.params, state: x.state, log: "", next: 0, key: "old-" + x.id, quiet: true };
    var j = S.jobs[x.id];
    S.drawerJob = x.id; drawDrawer();
    $("drawer-body").scrollTop = 0;     // its output is at the top of the drawer: show it (0.39.3, it opened out of sight)
    if (!j.log) api("job?id=" + x.id + "&from=0").then(function (r) { if (r.ok) { j.log = r.data.log || ""; j.state = r.data.state; j.rc = r.data.rc; drawTerm(); } });
  }
  $("open-activity").addEventListener("click", function () { openDrawer(); });
  document.querySelectorAll("[data-close=drawer]").forEach(function (n) { n.addEventListener("click", closeDrawer); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") { if (!$("modal").hidden && !S.wizardOpen) closeModal(); else closeDrawer(); } });
  $("sign-out").addEventListener("click", function () { api("logout", { body: {} }).then(function () { S.session = null; location.replace("/console"); }); });

  // ---- modal
  function openModal(content, big) {
    var p = $("modal-panel"); p.innerHTML = ""; p.className = "modal-panel" + (big ? " big" : "");
    if ($("modal").hidden) S.modalOpener = opener();
    p.appendChild(content); $("modal").hidden = false; shield();
    var f = p.querySelector("button.primary") || p.querySelector("input, button"); if (f) setTimeout(function () { f.focus(); }, 30);
  }
  function closeModal() {
    var was = !$("modal").hidden;
    $("modal").hidden = true; $("modal-panel").innerHTML = ""; S.wizardOpen = false; shield();
    if (!was) return;
    var drawer = !$("drawer").hidden;
    giveBack(S.modalOpener, drawer ? $("drawer") : (S.session ? $("app") : $("gate")),
      drawer ? $("drawer").querySelector(".drawer-panel header [data-close=drawer]") : null);
    S.modalOpener = null;
  }

  // ---- the first steps (0.39.0; 0.41.0: the antenna, the feeders, sharing, the phone; open again at any time from
  // System or the overview). Only what differs from the Pi's settings is applied, in the review's order.
  var FEEDERS = [["adsbexchange_feed", t("ADSB Exchange"), "https://www.adsbexchange.com/myip/"], ["piaware", t("FlightAware"), "https://www.flightaware.com/adsb/piaware/claim"],
    ["fr24feed", t("Flightradar24"), ":8754"], ["pfclient", t("Plane Finder"), ":30053"], ["rbfeeder", t("AirNav Radar, formerly RadarBox"), "https://www.airnavradar.com/raspberry-pi/claim"]];
  function setupGaps() {
    var c = S.cfg, f = S.facts, out = [];
    if (!(Number(c.LAT) || Number(c.LON))) out.push(t("The antenna's position is not set"));
    if (!f.decoder) out.push(t("No decoder yet: sudo zenithboard menu → 1 ADS-B → 1 Decoder and networks"));
    // 0.54.15: statistics and the watchdogs are choices, shown on the overview, not missing steps (a Pi without
    // /dev/watchdog could never finish setting up)
    return out;
  }
  function wizard() {
    var c = S.cfg, f = S.facts;
    var W = {
      region: c.REGION || "world", units: c.UNITS || "metric", alt: c.ALT_M || "0",
      lat: (Number(c.LAT) || Number(c.LON)) ? c.LAT : "", lon: (Number(c.LAT) || Number(c.LON)) ? c.LON : "",   // 0, 0: not set
      mode: c.DISPLAY_MODE || "dots", color: c.THEME || "amber", radius: String(Number(c.RADIUS) || 10),
      stats: on(c.STATS) ? "on" : "off", graphs: f.graphs === "on" ? "on" : "off", localdb: on(c.LOCAL_DB) ? "on" : "off",
      watchdog: f.watchdog || "off", netwatch: f.netwatch || "off", keeplogs: f.keeplogs || "off", patches: f.patches || "off",
      "wifi-harden": f.wifi_harden || "off", sum_daily: on(c.SOCIAL_DAILY) ? "on" : "off", sum_weekly: on(c.SOCIAL_WEEKLY) ? "on" : "off",
      "phone-signin": on(c.CONSOLE_PHONE_SIGNIN) ? "on" : "off"
    };
    var start = JSON.parse(JSON.stringify(W)), step = 0, err = null;
    function svcWord(k) { var st = f["svc_" + k]; return st === undefined ? "not installed" : st === "active" ? "running" : st; }
    var STEPS = [
      function () {
        var feeders = FEEDERS.filter(function (x) { return f["svc_" + x[0]] !== undefined; }).map(function (x) { return x[1]; });
        return [h("h3", { text: t("Welcome to the console") }),
          h("p", { "class": "lead", text: t("ZenithBoard's settings from this browser. The menu and the zenithboard command stay as they are; each change here runs the same command, and you see what it prints.") }),
          h("ul", { "class": "ticks" },
            h("li", { text: t("This Pi: {model}, ZenithBoard {version}", { model: f.model || "Raspberry Pi", version: S.session.version || "" }) }),
            h("li", { text: t("Decoder: {name}", { name: f.decoder || t("none yet (sudo zenithboard menu → 1 ADS-B → 1 Decoder and networks)") }) }),
            h("li", { text: t("Feeding: {list}", { list: feeders.join(", ") || t("nobody yet") }) }),
            h("li", { text: t("Answers your home network only; uninstalling, Wi-Fi and passwords stay in the terminal") })),
          h("p", { "class": "note", text: t("{n} short steps, then a review: nothing changes before you apply it. Open them again at any time: System → First steps again.", { n: STEPS.length - 2 }) }),
          h("p", { "class": "note", text: t("Moving from an old card? Restore its backup first, in the terminal (sudo zenithboard backup restore FILE): the settings, what was on, the statistics and the networks' identities come back, and these steps are then only a check.") })];
      },
      function () {
        var lat = h("input", { type: "text", inputmode: "decimal", value: W.lat, "aria-label": t("Latitude"), oninput: function () { W.lat = lat.value.trim(); } });
        var lon = h("input", { type: "text", inputmode: "decimal", value: W.lon, "aria-label": t("Longitude"), oninput: function () { W.lon = lon.value.trim(); } });
        var alt = h("input", { type: "number", value: W.alt, "aria-label": t("Altitude in metres"), oninput: function () { W.alt = alt.value.trim(); } });
        return [h("h3", { text: t("Where the antenna is") }),
          h("p", { "class": "lead", text: t("The decoder, MLAT and the wall's distances need it; it is never shown on the wall or in a post. A right-click on your roof in a map gives the two numbers.") }),
          wrow(t("Region"), wseg("region", ["world", "us"], [t("World"), t("United States")])),
          wrow(t("Units"), wseg("units", ["metric", "imperial", "aviation"], [t("km · m"), t("mi · ft"), t("NM · kt · ft")])),
          h("div", { "class": "fields" }, field(t("Latitude"), lat), field(t("Longitude"), lon), field(t("Alt. m"), alt)),
          err ? h("p", { "class": "err", text: err }) : null];
      },
      function () {
        return [h("h3", { text: t("The wall") }), h("p", { "class": "lead", text: t("The default of every screen; a tablet can still pick its own with its gear.") }),
          wrow(t("Look"), wseg("mode", ["dots", "flap"], [t("Dot matrix"), t("Split-flap")])),
          wrow(t("Colour"), h("div", { "class": "swatches" }, Object.keys(THEME_HEX).map(function (col) {
            var b = h("button", { type: "button", "class": "swatch" + (W.color === col ? " on" : ""), "aria-label": word(col), onclick: function () { W.color = col; theme(col); redraw(); } });
            b.style.background = THEME_HEX[col]; return b;
          }))),
          wrow(t("Radius"), wseg("radius", ["1", "2", "5", "10", "15", "30", "50"]))];
      },
      function () {
        var hh = host();
        return [h("h3", { text: t("Feeding the networks") }),
          h("p", { "class": "lead", text: t("Each network is added in the terminal: sudo zenithboard menu → 1 ADS-B → 1 Decoder and networks. Their own installers ask questions as they go (a station name, an e-mail, a sharing key) and give a claim link or code to keep: the console runs commands that ask nothing, and keeps no key.") }),
          h("div", { "class": "list" }, [["readsb", t("Decoder (readsb)")], ["dump1090_fa", t("Decoder (dump1090-fa)")]].filter(function (x) { return f["svc_" + x[0]] !== undefined; }).concat(FEEDERS).map(function (x) {
            var st = svcWord(x[0]), url = x[2] ? (x[2][0] === ":" ? "http://" + hh + x[2] + "/" : x[2]) : null;
            return h("div", { "class": "li" }, h("div", null, h("b", { text: x[1] }), h("small", { text: word(st) })),
              st !== "not installed" && url ? h("a", { href: url, target: "_blank", rel: "noopener noreferrer", text: t("Its page ↗") }) : h("span", { "class": "pill " + (st === "running" ? "ok" : "queued"), text: st === "running" ? t("ok") : st === "not installed" ? t("terminal") : word(st) }));
          })),
          h("p", { "class": "note", text: t("ADSB Exchange comes first and is always on; FlightAware, Flightradar24, Plane Finder and AirNav Radar only if you want them. Their state is also on the overview.") })];
      },
      function () {
        return [h("h3", { text: t("What to collect") }), h("p", { "class": "lead", text: t("All of it stays on the card; nothing is sent anywhere.") }),
          wrow(t("Statistics"), wsw("stats"), t("A sample every 15 minutes, 30 days kept: the /stats page and the summaries' figures.")),
          wrow("graphs1090", wsw("graphs"), t("Years of the decoder's graphs on port 8542; its author's installer, a few minutes.")),
          wrow(t("The receiver map's aircraft database"), wsw("localdb"), f.map ? t("Registrations and models read on the card (tar1090).") : t("Needs the receiver map (tar1090), not seen on this Pi."))];
      },
      function () {
        return [h("h3", { text: t("What keeps it running") }), h("p", { "class": "lead", text: t("Recommended for a Pi left alone. Each one off again puts back what it found.") }),
          wrow(t("Hardware watchdog"), wsw("watchdog"), t("The chip restarts a frozen Pi after about 10 seconds.")),
          wrow(t("Network watchdog"), wsw("netwatch"), t("No router for 6 minutes: the network restarts; 12: the Pi.")),
          wrow(t("Logs kept after a restart"), wsw("keeplogs"), t("Up to 50 MB, to read what happened before a freeze.")),
          wrow(t("Daily security fixes"), wsw("patches"), t("Debian's security channel only; feeders untouched, no reboot.")),
          f.wifi ? wrow(t("Wi-Fi hardening"), wsw("wifi-harden"), t("Retry without end after a loss; no radio power saving.")) : null];
      },
      function () {
        var acct = f.bluesky;
        return [h("h3", { text: t("Sharing on Bluesky") }),
          h("p", { "class": "lead", text: acct ? t("Account @{account}. Posting each crossing is switched in Sharing; the summaries here.", { account: acct }) :
            t("No Bluesky account on this Pi: it is set up in the terminal (it asks for an app password): sudo zenithboard social setup. Skip this step until then.") }),
          // 0.54.18: without an account the two switches showed "on" for posts that could not be made (the owner's
          // fresh card): they wait for the account
          acct ? null : h("p", { "class": "note", text: t("The summaries come with the account: they are shown here once it is set up.") }),
          !acct ? null : wrow(t("Summary of the last 24 hours"), wsw("sum_daily"), t("Every day at its time (21:00 unless changed in Sharing), from the statistics.")),
          !acct ? null : wrow(t("Summary of the week"), wsw("sum_weekly"), t("Sunday 19:00 unless changed; four posts, two minutes apart.")),
          acct && W.stats !== "on" && (W.sum_daily === "on" || W.sum_weekly === "on") ? h("p", { "class": "note", text: t("They need the statistics: switch them on in step 5.") }) : null,
          acct && (W.sum_daily === "on" || W.sum_weekly === "on") ? summariesBlocked(acct, S.cfg) : null];
      },
      function () {
        return [h("h3", { text: t("Your phone, and this computer") }),
          h("p", { "class": "lead", text: t("Scan a QR code once and the phone stays signed in, no password typed, as long as it opens the console once a month. Face ID and passkeys need HTTPS under a domain name, which a Pi at a home address does not have.") }),
          h("div", { "class": "actions" }, h("button", { type: "button", "class": "btn", text: t("Pair a phone now"), onclick: function () { S.wizardOpen = false; pairPhone(reopen); } })),
          wrow(t("Sign computers in with the phone"), wsw("phone-signin"), t("A computer's sign-in page then shows a QR code; the phone says yes, no password."))];
      },
      function () {
        var plan = changes();
        return [h("h3", { text: plan.length ? t("Ready") : t("Nothing to change") }),
          h("p", { "class": "lead", text: plan.length ? t("Applied one after the other; each is the zenithboard command you can read in Activity.") : t("Everything is already as you chose.") }),
          h("ul", { "class": "ticks plan", id: "wiz-plan" }, plan.map(function (p) { return h("li", { "data-k": p.k, text: p.words }); })),
          setupGaps().length && !plan.length ? h("p", { "class": "note", text: t("Still to do: {list}.", { list: setupGaps().join("; ") }) }) : null];
      }
    ];
    var WORDS = { region: t("Region"), units: t("Units"), mode: t("Look"), color: t("Colour"), radius: t("Radius"), stats: t("Statistics"), graphs: "graphs1090", localdb: t("Receiver map's database"),
      watchdog: t("Hardware watchdog"), netwatch: t("Network watchdog"), keeplogs: t("Logs kept after a restart"), patches: t("Daily security fixes"), "wifi-harden": t("Wi-Fi hardening"),
      sum_daily: t("Summary of the last 24 hours"), sum_weekly: t("Summary of the week"), "phone-signin": t("Computers signed in by the phone") };
    var ORDER = ["region", "units", "mode", "color", "radius", "stats", "localdb", "watchdog", "netwatch", "keeplogs", "patches", "wifi-harden", "sum_daily", "sum_weekly", "phone-signin", "graphs"];
    function changes() {
      var out = [];
      if (W.lat !== start.lat || W.lon !== start.lon || W.alt !== start.alt) out.push({ k: "location", action: "location", params: { lat: W.lat, lon: W.lon, alt: W.alt }, words: t("Antenna position: {lat}, {lon}, {alt} m", { lat: W.lat, lon: W.lon, alt: W.alt }) });
      ORDER.forEach(function (k) {
        if (W[k] === start[k]) return;
        var action = k, params = { value: W[k] };
        if (k === "sum_daily" || k === "sum_weekly") { action = "summary"; params = { period: k === "sum_daily" ? "daily" : "weekly", value: W[k] }; }
        out.push({ k: k, action: action, params: params, words: WORDS[k] + ": " + word(W[k]) });
      });
      return out;
    }
    function wrow(title, ctl, hint) { var tight = ctl && ctl.classList && ctl.classList.contains("sw"); return h("div", { "class": "row" + (tight ? " tight" : "") }, h("div", { "class": "what" }, h("b", { text: title }), hint ? h("span", { text: hint }) : null), h("div", { "class": "ctl" + (tight ? " end" : "") }, ctl)); }
    function wseg(k, choices, labels) {
      return h("div", { "class": "seg" }, choices.map(function (c, i) {
        return h("button", { type: "button", "class": W[k] === c ? "on" : "", text: labels ? labels[i] : c, onclick: function () { W[k] = c; redraw(); } });
      }));
    }
    function wsw(k) { return h("button", { type: "button", role: "switch", "aria-checked": W[k] === "on" ? "true" : "false", "class": "sw" + (W[k] === "on" ? " on" : ""), onclick: function () { W[k] = W[k] === "on" ? "off" : "on"; redraw(); } }); }
    function valid() {          // the position, before leaving its step: the same ranges as the command
      if (step !== 1) return true;
      var la = Number(W.lat), lo = Number(W.lon), al = Number(W.alt);
      var changed = W.lat !== start.lat || W.lon !== start.lon || W.alt !== start.alt;
      if (!changed) return true;
      err = (W.lat === "" || isNaN(la) || la < -90 || la > 90) ? t("Latitude: a number between -90 and 90, e.g. 49.1193") :
        (W.lon === "" || isNaN(lo) || lo < -180 || lo > 180) ? t("Longitude: a number between -180 and 180, e.g. 6.1757") :
        (isNaN(al) || al < -500 || al > 9000) ? t("Altitude: metres above the sea, e.g. 180") : null;
      return !err;
    }
    function done() { api("wizard", { body: { done: true } }); S.session.wizard_done = true; theme(S.cfg.THEME); closeModal(); }
    function apply() {
      var plan = changes(), i = 0, ok = true;
      var foot = $("modal-panel").querySelector(".modal-foot"); if (foot) foot.innerHTML = "";
      function next() {
        if (i >= plan.length) {
          api("wizard", { body: { done: true } }); S.session.wizard_done = true;
          if (foot) foot.appendChild(h("button", { type: "button", "class": "primary", text: ok ? t("Done") : t("Close (see Activity)"), onclick: function () { closeModal(); loadState(); } }));
          return;
        }
        var p = plan[i], li = document.querySelector('#wiz-plan li[data-k="' + p.k + '"]');
        if (li) li.className = "run";
        run(p.action, p.params, { confirmed: true, quiet: true }).then(function (j) {
          var good = j && j.state === "done" && j.rc === 0; ok = ok && good;
          if (li) li.className = good ? "ok" : "bad";
          i++; next();
        });
      }
      next();
    }
    function reopen() { S.wizardOpen = true; redraw(); }
    function redraw() {
      if (!S.wizardOpen) return;
      var last = step === STEPS.length - 1;
      var body = h("div", { "class": "modal-body wiz" }, STEPS[step]());
      var dotsRow = h("div", { "class": "steps" }, STEPS.map(function (_, i) { return h("i", { "class": i === step ? "on" : i < step ? "done" : "" }); }));
      openModal(h("div", null,
        h("header", null, h("h2", { text: t("First steps · {n} of {total}", { n: step + 1, total: STEPS.length }) }), h("button", { type: "button", "class": "ghost", "aria-label": t("Close"), text: "×", onclick: done })),
        dotsRow, body,
        h("div", { "class": "modal-foot" },
          step === 0 ? h("button", { type: "button", "class": "ghost", text: t("Skip, I'll look around"), onclick: done }) : h("button", { type: "button", "class": "btn", text: t("Back"), onclick: function () { err = null; step--; redraw(); } }),
          last ? h("button", { type: "button", "class": "primary", text: changes().length ? tn(changes().length, "Apply {n} change", "Apply {n} changes") : t("Finish"), onclick: function () { if (changes().length) apply(); else done(); } })
            : h("button", { type: "button", "class": "primary", text: t("Next"), onclick: function () { if (!valid()) return redraw(); err = null; step++; redraw(); } }))), true);
      S.wizardOpen = true;
    }
    S.wizardOpen = true;
    redraw();
  }
  S.openWizard = function () { if (S.session) wizard(); };

  boot();
});
