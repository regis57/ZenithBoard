// SPDX-License-Identifier: GPL-3.0-or-later
// The web console (0.39.0): ZenithBoard's settings from a browser or a phone on the home network.
// One section on screen at a time (a side bar on a computer, tabs at the bottom of a phone), the wall's colour on
// black. Every change is one action from the Pi's fixed list (flightinfo/console_actions.py), run by the Pi's root
// helper as the same `zenithboard` command as over SSH; what it prints is shown in the Activity drawer as it comes.
// Reads /console/api/*; draws nothing it was not told by the Pi.
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var S = {
    session: null, cfg: {}, facts: {}, factsAt: 0, catalog: {}, sections: [], section: "overview",
    jobs: {}, pending: {}, wanted: {}, drawerJob: null, activity: null, sessions: null, warnedQueue: {}
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
    power: '<path d="M12 3v8"/><path d="M6.3 7a8 8 0 1 0 11.4 0"/>'
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
    if (s < 90) return s + " s";
    if (s < 5400) return Math.round(s / 60) + " min";
    if (s < 172800) return Math.round(s / 3600) + " h";
    return Math.floor(s / 86400) + " d " + Math.round((s % 86400) / 3600) + " h";
  }
  function ago(t) { return t ? dur(Date.now() / 1000 - t) + " ago" : "never"; }
  function size(mb) { mb = Number(mb); if (!(mb >= 0)) return "–"; return mb >= 2048 ? (mb / 1024).toFixed(1) + " GB" : Math.round(mb) + " MB"; }
  function clock(t) { var d = new Date(t * 1000); return ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2); }

  var toastTimer = null;
  function toast(msg, bad) {
    var t = $("toast");
    t.textContent = msg; t.className = "toast" + (bad ? " bad" : ""); t.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(function () { t.hidden = true; }, bad ? 7000 : 3500);
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
    gate("login", "You were signed out (the session ended, or someone signed everyone out).");
  }

  // ---- before signing in
  function gate(which, msg) {
    $("gate").hidden = false; $("app").hidden = true;
    ["gate-off", "login", "gate-nopw", "gate-pairing", "gate-help"].forEach(function (id) { $(id).hidden = true; });
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
    this.setAttribute("aria-label", p.type === "password" ? "Show the password" : "Hide the password");
  });
  $("login").addEventListener("submit", function (e) {
    e.preventDefault();
    var b = $("login-go"); b.disabled = true;
    api("login", { body: { password: $("pw").value } }).then(function (r) {
      b.disabled = false;
      if (r.ok) { $("pw").value = ""; return boot(); }
      $("login-err").textContent = r.data.error || "Could not sign in."; $("login-err").hidden = false;
      $("pw").select();
    }).catch(function () { b.disabled = false; $("login-err").textContent = "The Pi does not answer."; $("login-err").hidden = false; });
  });

  var WRITE_MSG = "The wall cannot write its console folder yet: pairing and changes will fail. Over SSH: sudo systemctl restart zenithboard-flightinfo";
  // 0.40.1: the version running on this Pi, linked to its release notes on GitHub (the releases page when unknown)
  function showVersion(a, v) {
    if (!a) return;
    var ok = /^\d+\.\d+\.\d+$/.test(String(v || ""));
    a.textContent = "ZenithBoard " + (ok ? v : "");
    a.href = "https://github.com/regis57/ZenithBoard/releases" + (ok ? "/tag/v" + v : "");
    a.title = ok ? "What changed in " + v : "ZenithBoard's releases";
  }
  function boot() {
    dots($("gate-logo"), "ZENITHBOARD", 10); dots($("gate-sub"), "CONSOLE", 10);
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
          gate(s.has_password ? "login" : "nopw", p.data.error || "This pairing code did not work.");
        });
      }
      S.phoneSignin = !!s.phone_signin;
      if (!s.signed_in) {
        gate(s.has_password ? "login" : "nopw", S.unwritable ? WRITE_MSG : (S.approveId ? "Sign this phone in first; then the computer's request is shown." : null));
        if (S.phoneSignin && !S.approveId) phoneSignin();
        return;
      }
      stopPhoneSignin();
      S.session = s;
      startApp();
    }).catch(function () { gate("login", "The Pi does not answer. Is the wall running?"); });
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
      $("gate-code").textContent = d.code; note.textContent = "Scan it with a phone already signed in to the console, check that it shows " + d.code + ", and say yes.";
      box.hidden = false;
      PS.timer = setInterval(function () {
        var left = Math.max(0, Math.round((until - Date.now()) / 1000));
        count.textContent = Math.floor(left / 60) + ":" + ("0" + left % 60).slice(-2);
        if (!left) {
          stopPhoneSignin(); box.hidden = false;
          // a page left open renews its code a few times, then waits for a click (no endless requests)
          if (PS.renewals++ < 5 && document.visibilityState === "visible") phoneSignin();
          else { qr.hidden = true; note.textContent = "The code is out of date."; count.textContent = ""; $("gate-code").textContent = ""; }
        }
      }, 1000);
      PS.poll = setInterval(function () {
        api("approve/poll", { body: { id: d.id, secret: d.secret } }).then(function (p) {
          var st = p.data.state;
          if (st === "approved") { stopPhoneSignin(); boot(); }
          else if (st === "refused") { stopPhoneSignin(); box.hidden = false; qr.hidden = true; note.textContent = "Refused on the phone."; count.textContent = ""; }
        });
      }, 2000);
    });
  }
  function approveComputer(id) {
    api("approve?id=" + encodeURIComponent(id)).then(function (r) {
      if (!r.ok) return toast(r.data.error || "This sign-in code is out of date.", true);
      var d = r.data;
      if (d.state !== "waiting") return toast("This computer's request is " + d.state + ": it shows a new code.", true);
      function answer(yes) {
        closeModal();
        api("approve", { body: { id: id, yes: yes } }).then(function (a) {
          if (!a.ok) toast(a.data.error || "Too late: the computer shows a new code.", true);
          else toast(yes ? d.label + " is signed in." : "Refused.");
          if (yes) { S.sessions = null; }
        });
      }
      openModal(h("div", null,
        h("header", null, h("h2", { text: "Sign a computer in" }), h("button", { type: "button", "class": "ghost", "aria-label": "Close", text: "×", onclick: function () { closeModal(); } })),
        h("div", { "class": "modal-body" },
          h("p", { text: "Sign in " + d.label + " at " + d.ip + "?" }),
          h("div", { "class": "count", text: d.code }),
          h("p", { "class": "qr-note", text: "Say yes only if the computer in front of you shows this same code. It is signed in for a week (a day unused); System → Signed in signs it out." })),
        h("div", { "class": "modal-foot" },
          h("button", { type: "button", "class": "btn", text: "Refuse", onclick: function () { answer(false); } }),
          h("button", { type: "button", "class": "primary", text: "Sign it in", onclick: function () { answer(true); } }))));
    });
  }

  // ---- signed in
  function startApp() {
    $("gate").hidden = true; $("app").hidden = false;
    dots($("side-logo"), "ZB", 9); dots($("bar-logo"), "ZB", 6);
    document.querySelectorAll("[data-ico]").forEach(function (n) { if (!n.firstChild) n.appendChild(ico(n.getAttribute("data-ico")).firstChild); });
    showVersion($("side-version"), S.session.version);
    loadState().then(function () {
      route();
      if (S.unwritable) toast(WRITE_MSG, true);
      if (S.approveId) { var aid = S.approveId; S.approveId = null; approveComputer(aid); }
      else if (!S.session.wizard_done) wizard();
    });
  }
  function loadState() {
    return api("state").then(function (r) {
      if (!r.ok) return;
      S.cfg = r.data.cfg || {}; S.facts = r.data.facts || {}; S.factsAt = r.data.facts_at || 0;
      S.catalog = r.data.catalog || {}; S.sections = r.data.sections || [];
      theme(S.cfg.THEME);
      // the overview's facts are read as root by the helper after each change; older than two minutes: again
      if (!S.factsAt || Date.now() / 1000 - S.factsAt > 120) {
        if (!S.refreshing) { S.refreshing = true; run("refresh", {}, { quiet: true }).then(function () { S.refreshing = false; }); }
      }
      draw();
    }).catch(function () { /* the wall restarting: the next poll draws */ });
  }
  window.addEventListener("hashchange", route);
  function route() {
    var want = (location.hash || "#overview").slice(1);
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
        var short = where === tabs ? (sec[1] === "Reliability" ? "Reliable" : sec[1]) : sec[1];
        where.appendChild(h("a", { href: "#" + id, "class": id === S.section ? "on" : "", "aria-current": id === S.section ? "page" : null },
          ico(SECTION_ICON[id]), h("span", { text: short }), busy ? h("i", { "class": "dot" }) : null));
      });
    });
  }

  function draw(scrollTop) {
    if (!S.session) return;
    nav();
    var view = $("view"), focused = document.activeElement;
    if (!scrollTop && focused && view.contains(focused) && /INPUT|SELECT/.test(focused.tagName)) return;   // never under the typing finger
    var title = (S.sections.filter(function (s) { return s[0] === S.section; })[0] || [0, "Overview"])[1];
    $("title").textContent = title;
    document.title = title + " · ZenithBoard console";
    var y = window.scrollY;
    view.innerHTML = "";
    add(view, sectionView(S.section));
    if (scrollTop) { window.scrollTo(0, 0); view.focus({ preventScroll: true }); } else window.scrollTo(0, y);
    $("busy-badge").hidden = !Object.keys(S.jobs).some(function (k) { var j = S.jobs[k]; return j.state === "queued" || j.state === "running"; });
  }

  // ---- running an action, and following it
  function confirmBox(title, text, okLabel, danger) {
    return new Promise(function (resolve) {
      openModal(h("div", null,
        h("header", null, h("h2", { text: title })),
        h("div", { "class": "modal-body" }, (Array.isArray(text) ? text : [text]).map(function (p) { return h("p", { text: p }); })),
        h("div", { "class": "modal-foot" },
          h("button", { type: "button", "class": "btn", text: "Cancel", onclick: function () { closeModal(); resolve(false); } }),
          h("button", { type: "button", "class": danger ? "danger" : "primary", text: okLabel || "Go on", onclick: function () { closeModal(); resolve(true); } }))));
    });
  }
  var ASK = {
    location: ["Change the antenna position?", "It is written everywhere it is stored on this Pi (the wall, and the feeders that can be set from here); the ones that cannot are named in the output. The position is never shown on the wall or in a post."],
    graphs: ["graphs1090", "Turning it on runs its author's installer: collectd and rrdtool from apt (signed), its files from GitHub, a few minutes. Turning it off puts back what was there before and keeps its history."],
    "gain-step": ["Move the gain one step?", "The decoder restarts with the new gain: a few seconds without aircraft. Go one step at a time, and check again after a day."],
    social: ["Social sharing", "Switching it on starts posting the aircraft worth it to Bluesky, as set in the terminal (radius, rules, gap). Off stops the service; the account stays."],
    watchdog: ["Hardware watchdog", "If the Pi freezes completely, its own chip restarts it after about 10 seconds. Off takes the setting away again."],
    "update-quick": ["Update ZenithBoard and the wall?", "Seconds. The wall restarts, so this page reconnects by itself. The feeders are left as they are."],
    update: ["Update everything?", "ZenithBoard, the decoder and every feeder, one after the other: several minutes. The wall restarts during it; this page follows. A new GitHub signing key is never accepted from here: the update says so, and it is answered over SSH."],
    "phone-signin": ["Sign computers in with a phone", "When on, a computer's sign-in page shows a QR code. A phone already signed in scans it, sees the computer, its address and a four-digit code, and says yes: the computer is signed in, no password. Off again: computers use the password."],
    "console-off": ["Turn the console off?", "Its pages stop answering at once, this one included. Turn it on again over SSH: sudo zenithboard console on"]
  };
  function run(action, params, opts) {
    opts = opts || {};
    var spec = S.catalog[action] || { flags: [], label: action }, flags = spec.flags || [];
    var go = Promise.resolve(true);
    if (flags.indexOf("ask") >= 0 && !opts.confirmed) {
      var a = ASK[action] || [spec.label, "Go on?"];
      var off = params && params.value === "off";
      go = confirmBox(a[0], off && action !== "graphs" ? "Switch it off?" : a[1], off ? "Switch off" : "Go on", action === "console-off");
    }
    return go.then(function (yes) {
      if (!yes) return null;
      var key = opts.key || action;
      if (!opts.quiet) { S.pending[key] = true; S.wanted[key] = params && params.value; draw(); }
      return api("run", { body: { action: action, params: params || {} } }).then(function (r) {
        if (!r.ok) {
          delete S.pending[key]; draw();
          toast(r.data.error || "Refused.", true); return null;
        }
        var id = r.data.job;
        S.jobs[id] = { id: id, action: action, label: opts.label || spec.label, params: params || {}, state: "queued", log: "", next: 0, key: key, quiet: opts.quiet };
        if (!opts.quiet && !opts.noDrawer && (flags.indexOf("read") >= 0 || flags.indexOf("long") >= 0 || opts.show)) openDrawer(id);
        return follow(id);
      }).catch(function () {
        delete S.pending[key]; draw();
        toast("The Pi does not answer.", true); return null;
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
              toast("Queued: " + ((S.catalog[d.behind] || {}).label || d.behind) + " runs first, then this. The Pi does one change at a time.");
            } else if (!d.behind && now_ - (S.lastQueueNote || 0) > 15000) {
              S.lastQueueNote = now_;
              toast("The console's helper has not taken the job. Over SSH: sudo zenithboard console on", true);
            }
          }
          if (S.drawerJob === id) drawTerm();
          if (j.state === "done" || j.state === "refused") return finish();
          setTimeout(tick, j.state === "running" ? 700 : 1000);
        }).catch(function () { setTimeout(tick, 1500); });            // the wall restarting after the change
      }
      function finish() {
        delete S.pending[j.key]; delete S.wanted[j.key];
        var spec = S.catalog[j.action] || { flags: [] }, ok = j.state === "done" && j.rc === 0;
        if (j.action === "refresh" && !j.quiet) toast("Read again.");
        if (!j.quiet && spec.flags.indexOf("read") < 0) {
          if (ok) toast(j.label + ": done.");
          else toast(j.label + (j.error ? ": refused (" + j.error + ")" : ": it did not work. See Activity."), true);
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
    return h("button", { type: "button", role: "switch", "aria-checked": isOn ? "true" : "false", "aria-label": label || (S.catalog[action] || {}).label,
      "class": "sw" + (isOn ? " on" : "") + (waiting ? " wait" : ""), disabled: waiting ? true : null,
      onclick: function () { var p = Object.assign({}, extra || {}, { value: isOn ? "off" : "on" }); run(action, p, { key: key }); } });
  }
  function btn(label, action, params, cls, opts) {
    var busy = S.pending[(opts && opts.key) || action];
    return h("button", { type: "button", "class": cls || "btn", disabled: busy ? true : null, text: busy ? label + "…" : label,
      onclick: function () { run(action, params || {}, opts); } });
  }
  function row(title, hint, ctl, end) {
    if (ctl && ctl.classList && ctl.classList.contains("sw")) end = true;   // a lone switch stays beside its words on a phone
    return h("div", { "class": "row" + (end ? " tight" : "") }, h("div", { "class": "what" }, h("b", { text: title }), hint ? h("span", { text: hint }) : null),
      h("div", { "class": "ctl" + (end ? " end" : "") }, ctl));
  }
  function card(title, icon, lead, body, width) {
    return h("section", { "class": "card" + (width ? " " + width : "") }, h("h2", null, icon ? ico(icon) : null, title),
      lead ? h("p", { "class": "lead", text: lead }) : null, body);
  }
  function stateWord(v) { return on(v) ? "on" : "off"; }

  // ---- the sections
  var SVC_NAMES = [
    ["readsb", "Decoder (readsb)"], ["dump1090_fa", "Decoder (dump1090-fa)"], ["dump978_fa", "978 MHz UAT"],
    ["adsbexchange_feed", "ADSB Exchange"], ["piaware", "FlightAware"], ["fr24feed", "Flightradar24"], ["pfclient", "Plane Finder"],
    ["zenithboard_flightinfo", "The wall"], ["zenithboard_social", "Bluesky posts"], ["graphs1090", "graphs1090"], ["lighttpd", "Receiver map's web server"]
  ];
  function go(section) { return function () { location.hash = "#" + section; }; }

  var SECTIONS = {
    overview: function () {
      var f = S.facts, c = S.cfg, out = [];
      var mem = f.mem_avail_mb ? size(f.mem_avail_mb) : "–", card_ = f.disk_free_mb ? size(f.disk_free_mb) : "–";
      var thr = f.throttled && f.throttled !== "0x0" ? "power warnings: see Health" : (f.throttled ? "power: no warning" : "");
      out.push(h("div", { "class": "tiles" },
        tile("Up for", f.uptime_s ? dur(f.uptime_s) : "–", f.model || ""),
        tile("Temperature", f.temp_c ? f.temp_c + " °C" : "–", thr || (f.load ? "load " + f.load : "")),
        tile("Memory free", mem, f.mem_total_mb ? "of " + size(f.mem_total_mb) : ""),
        tile("Card free", card_, f.disk_total_mb ? "of " + size(f.disk_total_mb) : "")));
      var svcs = SVC_NAMES.filter(function (s) { return f["svc_" + s[0]] !== undefined; }).map(function (s) {
        var st = f["svc_" + s[0]], quiet = (s[0] === "zenithboard_social" && !on(c.SOCIAL));
        return h("div", { "class": "svc" }, h("i", { "class": st === "active" ? "ok" : (quiet ? "" : "bad") }), h("span", { text: s[1] }),
          h("em", { text: st === "active" ? "running" : (quiet ? "off" : st) }));
      });
      out.push(card("Services", "antenna", S.factsAt ? "Read on the Pi " + ago(S.factsAt) + "." : "Reading the Pi…",
        [svcs.length ? svcs : h("p", { "class": "note", text: "Nothing read yet." }),
          h("div", { "class": "actions" }, btn("Read again", "refresh", {}, "btn", { noDrawer: true }), btn("Status", "status"), btn("Health", "health"))], "w6"));
      out.push(card("At a glance", "overview", null, h("div", { "class": "glance" },
        chip("Wall: " + (c.DISPLAY_MODE === "flap" ? "split-flap" : "dots") + ", " + (c.THEME || "amber") + ", " + c.RADIUS + (c.UNITS === "imperial" ? " mi" : " km"), "wall"),
        chip("Statistics " + stateWord(c.STATS), "receiver", on(c.STATS)),
        chip("graphs1090 " + (f.graphs || "?"), "receiver", f.graphs === "on"),
        chip("Bluesky " + (on(c.SOCIAL) ? "posting" : "off"), "sharing", on(c.SOCIAL)),
        chip("Summaries: " + (["DAILY", "WEEKLY", "MONTHLY"].filter(function (p) { return on(c["SOCIAL_" + p]); }).map(function (p) { return p.toLowerCase(); }).join(", ") || "off"), "sharing"),
        chip("Watchdog " + (f.watchdog || "?"), "reliability", f.watchdog === "on"),
        chip("Network watchdog " + (f.netwatch || "?"), "reliability", f.netwatch === "on"),
        chip("Security fixes " + (f.patches || "?"), "reliability", f.patches === "on"),
        f.wifi ? chip("Wi-Fi: " + f.wifi, "system") : null), "w6"));
      out.push(card("Pages", "link", "What this Pi shows, and what it can show once switched on.", h("div", { "class": "pages" }, pages()), "w12"));
      return out;
    },

    wall: function () {
      var c = S.cfg, unit = c.UNITS === "imperial" ? "mi" : "km";
      return [
        card("Look", "wall", "The default of every screen. A tablet that chose its own with its gear keeps it until Reset in its gear panel.", [
          row("Look", "Dot matrix, or the split-flap airport board", seg("mode", ["dots", "flap"], c.DISPLAY_MODE || "dots", ["Dot matrix", "Split-flap"])),
          row("Colour", null, swatches()),
          row("Units", "Distances, speeds and heights", seg("units", ["metric", "imperial"], c.UNITS, ["km · m", "mi · ft"])),
          row("Detection radius", "Aircraft inside it are on the wall, in " + unit, seg("radius", ["1", "2", "5", "10", "15", "30", "50"], String(Number(c.RADIUS)))),
          row("Seconds per aircraft", "2 to 60", numberApply("cycle", c.CYCLE_SECONDS, 2, 60)),
          h("div", { "class": "actions" }, h("a", { "class": "btn", href: "/", target: "_blank", rel: "noopener", text: "Open the wall ↗" }))
        ], "w6"),
        card("What it shows", "plane", null, [
          row("Aircraft photos", "From Planespotters, with their credit; needs internet", sw("photos", on(c.SHOW_PHOTOS))),
          row("Where flights come from and go to", "The callsign is looked up on adsbdb.com", sw("routes", on(c.SHOW_ROUTES))),
          row("The receiver map's aircraft database", "Registrations and models read on the card (tar1090); nothing downloaded", sw("localdb", on(c.LOCAL_DB))),
          row("Monthly refresh of the model names", "A free list from GitHub, once a month", sw("data-auto", on(c.AUTO_DATA_REFRESH))),
          h("div", { "class": "actions" }, btn("Refresh the model names now", "data-update"), btn("Aircraft data", "data-status"), btn("Presets", "presets"))
        ], "w6")
      ];
    },

    receiver: function () {
      var c = S.cfg, f = S.facts;
      var lat = h("input", { type: "text", inputmode: "decimal", value: c.LAT || "", "aria-label": "Latitude", size: 10 });
      var lon = h("input", { type: "text", inputmode: "decimal", value: c.LON || "", "aria-label": "Longitude", size: 10 });
      var alt = h("input", { type: "number", value: c.ALT_M || "0", "aria-label": "Altitude in metres", min: -500, max: 9000 });
      return [
        card("Antenna", "antenna", null, [
          row("Region", "The United States adds the optional 978 MHz UAT step (menu 1)", seg("region", ["world", "us"], c.REGION || "world", ["World", "United States"])),
          h("div", { "class": "row" }, h("div", { "class": "what" }, h("b", { text: "Position" }), h("span", { text: "Decimal degrees, altitude in metres. Written everywhere it is stored; never shown on the wall or in a post." })),
            h("div", { "class": "fields" }, field("Latitude", lat), field("Longitude", lon), field("Alt. m", alt),
              h("button", { type: "button", "class": "btn", text: S.pending.location ? "Applying…" : "Apply", disabled: S.pending.location ? true : null,
                onclick: function () { run("location", { lat: lat.value.trim(), lon: lon.value.trim(), alt: alt.value.trim() }); } })))
        ], "w6"),
        card("Measure", "chart", null, [
          row("Statistics", "A sample every 15 minutes, 30 days kept, about 30 KB a day", [sw("stats", on(c.STATS)), on(c.STATS) ? h("a", { href: "/stats", target: "_blank", rel: "noopener", text: "Open ↗" }) : null]),
          row("graphs1090", "Years of the decoder's graphs on port 8542; installed by its author's script", [sw("graphs", f.graphs === "on"), f.graphs === "on" ? h("a", { href: "http://" + host() + ":8542/", target: "_blank", rel: "noopener", text: "Open ↗" }) : null]),
          row("Gain", "Check it first; then one step at a time", [btn("Check", "gain-check"), btn("− Down", "gain-step", { value: "down" }, "btn", { key: "gain-step" }), btn("Up +", "gain-step", { value: "up" }, "btn", { key: "gain-step" })]),
          row("Gain log, 24 hours", "One measurement every 15 minutes, as a table", sw("gain-log", on(c.GAINLOG)))
        ], "w6"),
        card("Look at it", "terminal", null, h("div", { "class": "actions" },
          btn("Status", "status"), btn("Statistics in the terminal", "stats-show"), btn("Unknown callsigns and types", "stats-gaps"), btn("One MLAT client only", "mlat-guard")), "w12")
      ];
    },

    sharing: function () {
      var c = S.cfg, f = S.facts, acct = f.bluesky;
      var col = c.SOCIAL_THEME || "wall", units = c.SOCIAL_UNITS || "wall";
      return [
        card("Bluesky", "share", acct ? "Account @" + acct + ". The account itself is set up over SSH (it asks for an app password): sudo zenithboard social setup" :
          "No Bluesky account yet. Set it up over SSH, it asks for an app password: sudo zenithboard social setup", [
          row("Post the aircraft overhead", "As set in the terminal: radius, rules, gap. Never a distance or a direction.", acct ? sw("social", on(c.SOCIAL)) : h("span", { "class": "state", text: "needs an account" })),
          row("Least time between posts", "Minutes; 0 = every crossing posted once", numberApply("social-gap", c.SOCIAL_GAP_MIN, 0, 1440)),
          h("div", { "class": "actions" }, btn("Try a post (posts nothing)", "social-test"), h("a", { "class": "btn", href: "/social/preview", target: "_blank", rel: "noopener", text: "Last picture ↗" }), btn("Status", "social-status"))
        ], "w6"),
        card("The picture and the words", "picture", null, [
          row("Picture", null, seg("social-look", ["dotmap", "flap", "alternate"], c.SOCIAL_STYLE || "dotmap", ["Dots + map", "Split-flap", "In turn"])),
          row("Colour", "The wall's own, one of the five, or in turn", select("social-colour", ["wall", "amber", "green", "red", "white", "turquoise", "rotate"], col,
            ["The wall's (" + (c.THEME || "amber") + ")", "Amber", "Green", "Red", "White", "Turquoise", "In turn"])),
          row("Map", null, select("social-map", ["normal", "night", "satellite", "terrain", "none", "rotate"], c.SOCIAL_MAP || "normal",
            ["Normal", "Night", "Satellite", "Terrain", "None", "In turn"])),
          row("Units", null, seg("social-units", ["wall", "metric", "imperial"], units, ["The wall's", "Metric", "Imperial"])),
          row("Link to the photo page", "Planespotters, at the end of each post", sw("social-photolink", on(c.SOCIAL_PHOTOLINK))),
          row("Words of a post", "One or more; with several, one is drawn at each post", sentenceChips(c.SOCIAL_SENTENCE || "factual"))
        ], "w6"),
        card("Summaries", "chart", "From the statistics, at their time on the Pi's clock; the posts go in one queue, two minutes apart. Posts: 1 the period, 2 cargo and business jets, 3 military, 4 general aviation.",
          [summaryRow("daily", "24 hours"), summaryRow("weekly", "The week"), summaryRow("monthly", "30 days"),
            on(c.STATS) ? null : h("p", { "class": "note", text: "Statistics are off: no summary can be made until they are on (Receiver)." }),
            h("div", { "class": "actions" }, btn("All summaries", "summaries"),
              ["2", "3", "4"].map(function (n) { return h("a", { "class": "btn", href: "/social/preview" + n, target: "_blank", rel: "noopener", text: "Post " + n + " ↗" }); })),
            h("p", { "class": "note", text: "Posting one now stays in the terminal, where you see it first: sudo zenithboard social summary weekly post" })], "w12")
      ];
    },

    reliability: function () {
      var f = S.facts, logsSel = h("select", { "aria-label": "Which log" },
        [["flightinfo", "The wall"], ["decoder", "The decoder"], ["social", "Bluesky posts"], ["uat", "978 MHz UAT"]].map(function (o) { return h("option", { value: o[0], text: o[1] }); }));
      return [
        card("Keep it running", "shield", "All off by default; each one off again puts back what it found.", [
          row("Hardware watchdog", "The Pi's own chip restarts it after a complete freeze", sw("watchdog", f.watchdog === "on")),
          row("Network watchdog", "No router for 6 minutes: the network restarts; 12 minutes: the Pi", sw("netwatch", f.netwatch === "on")),
          row("Logs kept after a restart", "Up to 50 MB: what happened just before a freeze", sw("keeplogs", f.keeplogs === "on")),
          row("Wi-Fi hardening", "Retry without end after a loss; no radio power saving", sw("wifi-harden", f.wifi_harden === "on")),
          row("Daily security fixes", "Debian's security channel only; feeders untouched, no reboot", sw("patches", f.patches === "on")),
          row("Daily log clean-up", "Keeps the last 7 days", sw("logs-auto", f.logs_auto === "on"))
        ], "w6"),
        card("Look at it", "terminal", null, [
          h("div", { "class": "actions" }, btn("Health", "health"), btn("Memory", "memory"), btn("Log size and warnings", "logs-review")),
          row("The last 100 lines of", null, [logsSel, h("button", { type: "button", "class": "btn", text: "Show", onclick: function () { run("logs", { value: logsSel.value }, { key: "logs" }); } })])
        ], "w6")
      ];
    },

    system: function () {
      var f = S.facts;
      return [
        card("Updates", "power", "From GitHub, checked against its signature before anything runs; your settings are never changed by an update.", [
          h("div", { "class": "actions" }, btn("Update ZenithBoard and the wall", "update-quick", {}, "primary"), btn("Update everything", "update"), btn("Installed components", "update-list")),
          h("p", { "class": "note", text: "ZenithBoard " + (S.session.version || "") + " runs here. The release notes: " }, h("a", { href: "https://github.com/regis57/ZenithBoard/releases", target: "_blank", rel: "noopener noreferrer", text: "GitHub ↗" }))
        ], "w6"),
        card("Network", "link", f.ip ? "This Pi: " + f.ip + (f.ddns ? " · " + f.ddns : "") : null, [
          h("div", { "class": "actions" }, btn("Network", "net-status"), btn("Wi-Fi", "wifi-status"), btn("Domain name", "ddns-status"),
            S.cfg.DDNS_PROVIDER && S.cfg.DDNS_PROVIDER !== "none" ? btn("Refresh the domain name", "ddns-update") : null),
          h("p", { "class": "note", text: "Wi-Fi networks, fixed addresses and the domain name's key stay in the terminal (sudo zenithboard menu → Settings → Network): one mistake there cuts the Pi off the network this page comes through." })
        ], "w6"),
        card("Signed in", "phone", "Browsers and phones signed in to this console. Signed in with the password: a week (a day unused). A paired phone: as long as it opens the console once a month.", [
          sessionsList(),
          row("Sign computers in with a phone", "A computer's sign-in page shows a QR code; a phone signed in here scans it and says yes", sw("phone-signin", on(S.cfg.CONSOLE_PHONE_SIGNIN))),
          h("div", { "class": "actions" }, h("button", { type: "button", "class": "primary", text: "Pair a phone", onclick: function () { pairPhone(); } }),
            h("button", { type: "button", "class": "btn", text: "Sign out the others", onclick: function () {
              api("sessions/revoke", { body: { id: "others" } }).then(function (r) { toast((r.data.count || 0) + " signed out."); loadSessions(); });
            } }))
        ], "w6"),
        card("Security", "shield", null, [
          h("div", { "class": "actions" }, btn("Security check", "security")),
          h("p", { "class": "sub", text: "Only in the terminal, on purpose" }),
          h("ul", { "class": "ticks no" },
            h("li", { text: "Uninstalling, and anything that asks for a typed word" }),
            h("li", { text: "Wi-Fi, fixed addresses (they can cut this page off)" }),
            h("li", { text: "Passwords, tokens and keys: Bluesky, the domain name, this console's own" }),
            h("li", { text: "Posting to Bluesky, emptying statistics or logs, importing settings" })),
          h("p", { "class": "note", text: "This page travels unencrypted on your home network (plain HTTP), like the wall. It answers home addresses only." }),
          h("div", { "class": "actions" }, btn("Turn the console off", "console-off", {}, "danger"))
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
  function tile(k, v, d) {
    return h("div", { "class": "tile" }, h("div", { "class": "k", text: k }), h("div", { "class": "v", text: v }), h("div", { "class": "d", text: d || "\u00a0" }));
  }
  function chip(text, section, lit) {
    return h("button", { type: "button", "class": "chip" + (lit ? " on" : ""), text: text, onclick: go(section) });
  }
  function field(label, input) { return h("div", { "class": "field" }, h("label", { text: label }), input); }
  function numberApply(action, value, min, max) {
    var inp = h("input", { type: "number", value: value, min: min, max: max, "aria-label": (S.catalog[action] || {}).label });
    return [inp, h("button", { type: "button", "class": "btn", text: S.pending[action] ? "…" : "Apply", disabled: S.pending[action] ? true : null,
      onclick: function () { if (String(inp.value) !== String(value)) run(action, { value: String(inp.value) }); } })];
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
    return h("div", { "class": "swatches", role: "group", "aria-label": "Colour" }, Object.keys(THEME_HEX).map(function (t) {
      var b = h("button", { type: "button", "class": "swatch" + (w !== undefined ? (t === w ? " wait" : "") : (t === cur ? " on" : "")),
        title: t, "aria-label": t, "aria-pressed": t === cur ? "true" : "false", disabled: S.pending.color ? true : null,
        onclick: function () { if (t !== cur) run("color", { value: t }); } });
      b.style.background = THEME_HEX[t];
      return b;
    }));
  }
  function sentenceChips(cur) {
    var all = ["factual", "story", "board", "spotter", "lookup"], picked = cur === "random" ? all.slice() : cur.split(",");
    var waiting = S.pending["social-sentence"];
    return h("div", { "class": "chips" }, all.map(function (w) {
      var lit = picked.indexOf(w) >= 0;
      return h("button", { type: "button", "class": "chip" + (lit ? " on" : ""), "aria-pressed": lit ? "true" : "false", text: w, disabled: waiting ? true : null,
        onclick: function () {
          var next = lit ? picked.filter(function (x) { return x !== w; }) : picked.concat([w]);
          if (!next.length) return toast("At least one.");
          next = all.filter(function (x) { return next.indexOf(x) >= 0; });
          run("social-sentence", { value: next.length === all.length ? "random" : next.join(",") });
        } });
    }));
  }
  function summaryRow(p, title) {
    var c = S.cfg, k = "SOCIAL_" + p.toUpperCase(), at = c[k + "_AT"] || "", parts = (c[k + "_PARTS"] || "1").split(","), lit = on(c[k]);
    var bits = at.split(" "), time = bits[bits.length - 1], day = bits.length > 1 ? bits[0] : "";
    var tIn = h("input", { type: "time", value: time, "aria-label": title + ": time" }), dIn = null;
    if (p === "weekly") dIn = h("select", { "aria-label": "Day" }, ["mon", "tue", "wed", "thu", "fri", "sat", "sun"].map(function (d) {
      return h("option", { value: d, text: d, selected: d === day ? true : null }); }));
    if (p === "monthly") dIn = h("input", { type: "number", "class": "day", min: 1, max: 28, value: day || "1", "aria-label": "Day of the month" });
    var keyAt = "at-" + p, keyParts = "parts-" + p;
    return h("div", { "class": "row" },
      h("div", { "class": "what" }, h("b", { text: title }), h("span", { text: lit ? "On: " + at + ", posts " + parts.join(", ") : "Off" })),
      h("div", { "class": "ctl" },
        sw("summary", lit, { period: p }, "summary-" + p, title),
        dIn, tIn,
        h("button", { type: "button", "class": "btn", text: S.pending[keyAt] ? "…" : "Set", disabled: S.pending[keyAt] ? true : null, onclick: function () {
          var when = (dIn ? String(dIn.value).trim() + " " : "") + tIn.value;
          if (when !== at) run("summary-at", { period: p, when: when }, { key: keyAt });
        } }),
        h("div", { "class": "chips" }, ["1", "2", "3", "4"].map(function (n) {
          var has = parts.indexOf(n) >= 0;
          return h("button", { type: "button", "class": "chip" + (has ? " on" : "") + (n === "1" ? " static" : ""), text: n, title: n === "1" ? "The first always goes" : null,
            "aria-pressed": has ? "true" : "false", disabled: (n === "1" || S.pending[keyParts]) ? true : null, onclick: function () {
              var next = has ? parts.filter(function (x) { return x !== n; }) : parts.concat([n]);
              run("summary-parts", { period: p, value: next.sort().join(",") }, { key: keyParts });
            } });
        })),
        h("button", { type: "button", "class": "btn", text: "Try", onclick: function () { run("summary-test", { period: p }, { key: "test-" + p }); } })));
  }
  function pages() {
    var f = S.facts, c = S.cfg, hh = host(), list = [];
    function page(icon, title, sub, href) { return h("a", { "class": "page", href: href, target: "_blank", rel: "noopener" }, ico(icon), h("div", null, h("b", { text: title }), h("span", { text: sub }))); }
    function later(icon, title, sub, section) { return h("button", { type: "button", "class": "page later", onclick: go(section) }, ico(icon), h("div", null, h("b", { text: title }), h("span", { text: sub }))); }
    list.push(page("wall", "The wall", (c.DISPLAY_MODE === "flap" ? "Split-flap" : "Dot matrix") + ", " + (c.THEME || "amber"), "/"));
    list.push(on(c.STATS) ? page("chart", "Statistics", "24 h, 7 days, 30 days", "/stats") : later("chart", "Statistics", "Off · switch on in Receiver", "receiver"));
    if (f.map) list.push(page("map", "Receiver map", "tar1090, on port 80", "http://" + hh + "/tar1090/"));
    if (f.skyaware) list.push(page("map", "SkyAware", "FlightAware's map", "http://" + hh + "/skyaware/"));
    list.push(f.graphs === "on" ? page("graph", "graphs1090", "The decoder's graphs, port 8542", "http://" + hh + ":8542/") : later("graph", "graphs1090", "Off · switch on in Receiver", "receiver"));
    if (f.svc_pfclient !== undefined) list.push(page("plane", "Plane Finder", "Its own page, port 30053", "http://" + hh + ":30053/"));
    if (f.svc_fr24feed !== undefined) list.push(page("plane", "Flightradar24", "Its feeder's page, port 8754", "http://" + hh + ":8754/"));
    if (f.svc_adsbexchange_feed !== undefined) list.push(h("a", { "class": "page", href: "https://www.adsbexchange.com/myip/", target: "_blank", rel: "noopener noreferrer" }, ico("link"), h("div", null, h("b", { text: "ADSB Exchange" }), h("span", { text: "Your feed, on their site" }))));
    if (f.bluesky) {
      list.push(page("picture", "Last post's picture", "What 'Try a post' drew", "/social/preview"));
      ["2", "3", "4"].forEach(function (n) { list.push(page("picture", "Weekly post " + n, ["", "", "Cargo and business jets", "Military", "General aviation"][Number(n)], "/social/preview" + n)); });
    } else list.push(later("share", "Bluesky posts", "No account yet · see Sharing", "sharing"));
    return list;
  }

  // ---- signed-in browsers and phones
  function loadSessions() {
    return api("sessions").then(function (r) { if (r.ok) { S.sessions = r.data; if (S.section === "system") draw(); } });
  }
  function sessionsList() {
    if (!S.sessions) { loadSessions(); return h("p", { "class": "note", text: "Reading…" }); }
    return h("div", { "class": "list" }, S.sessions.sessions.map(function (s) {
      var me = s.id === S.sessions.you;
      return h("div", { "class": "li" }, h("div", null, h("b", { text: s.label + (me ? " · this one" : "") }),
        h("small", { text: (s.kind === "paired" ? "paired" : "password") + " · since " + ago(s.created) + " · seen " + ago(s.seen) })),
        me ? h("span", { "class": "pill ok", text: "you" }) : h("button", { type: "button", "class": "btn", text: "Sign out", onclick: function () {
          api("sessions/revoke", { body: { id: s.id } }).then(function () { loadSessions(); });
        } }));
    }));
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
      if (!r.ok) return toast(r.data.error || "Could not make a pairing code.", true);
      var url = location.protocol + "//" + location.host + "/console/#pair=" + r.data.token, until = Date.now() + r.data.seconds * 1000;
      var count = h("div", { "class": "count" }), status = h("p", { "class": "qr-note", text: "Scan it with the phone's camera, then open the link." });
      var box = h("div", { "class": "qr" }, qrSvg(url));
      openModal(h("div", null,
        h("header", null, h("h2", { text: "Pair a phone" }), h("button", { type: "button", "class": "ghost", "aria-label": "Close", text: "×", onclick: stop })),
        h("div", { "class": "modal-body" }, local ? h("p", { "class": "err", text: "This page was opened as " + location.hostname + ": a phone cannot reach that. Open the console at the Pi's address to pair one." }) : null,
          box, count, status,
          h("p", { "class": "qr-note", text: "It works once, within five minutes. The phone then stays signed in as long as it opens the console once a month. Add it to the home screen from Safari's Share menu to open it in one tap." }))));
      var timer = setInterval(tickPair, 1000), poll = setInterval(checkPair, 2000);
      function tickPair() {
        var left = Math.max(0, Math.round((until - Date.now()) / 1000));
        count.textContent = Math.floor(left / 60) + ":" + ("0" + left % 60).slice(-2);
        if (!left) { box.hidden = true; status.textContent = "Out of date. Close this and make a new one."; clearInterval(timer); clearInterval(poll); }
      }
      function checkPair() {
        api("pair?id=" + r.data.id).then(function (p) {
          if (p.ok && p.data.used_by) {
            clearInterval(timer); clearInterval(poll);
            box.hidden = true; count.hidden = true; status.className = "qr-ok"; status.textContent = "✓ " + p.data.used_by + " signed in.";
            S.sessions = null; loadSessions();
          }
        });
      }
      function stop() { clearInterval(timer); clearInterval(poll); closeModal(); if (typeof after === "function") after(); }
      tickPair();
    });
  }

  // ---- the activity drawer
  function openDrawer(jobId) {
    S.drawerJob = jobId || S.drawerJob; S.activityOpen = true;
    $("drawer").hidden = false; document.body.style.overflow = "hidden";
    drawDrawer(); loadActivity();
  }
  function closeDrawer() { $("drawer").hidden = true; S.activityOpen = false; document.body.style.overflow = ""; }
  function loadActivity() { api("activity").then(function (r) { if (r.ok) { S.activity = r.data; drawDrawer(); } }); }
  var termPre = null, termPill = null;
  function drawTerm() {
    var j = S.jobs[S.drawerJob];
    if (!j || !termPre) return;
    var atEnd = termPre.scrollHeight - termPre.scrollTop - termPre.clientHeight < 40;
    termPre.textContent = j.log || (j.state === "queued" ? (j.behind ? "Waiting: " + ((S.catalog[j.behind] || {}).label || j.behind) + " runs first" + (j.ahead ? " (" + j.ahead + " before this one)" : "") + ". The Pi does one change at a time." : "Waiting for the Pi's helper…") : "");
    if (atEnd) termPre.scrollTop = termPre.scrollHeight;
    var st = j.state === "done" ? (j.rc === 0 ? ["ok", "done"] : ["bad", "exit " + j.rc]) : j.state === "refused" ? ["bad", "refused"] : [j.state === "running" ? "run" : "queued", j.state];
    termPill.className = "pill " + st[0]; termPill.textContent = st[1];
  }
  function drawDrawer() {
    var body = $("drawer-body"); body.innerHTML = ""; termPre = null;
    var j = S.jobs[S.drawerJob];
    if (j) {
      termPre = h("pre"); termPill = h("span", { "class": "pill" });
      body.appendChild(h("div", { "class": "term" }, h("div", { "class": "th" }, ico("terminal"), h("b", { text: j.label }), termPill), termPre));
      drawTerm();
      if (j.state === "done" && (j.action === "social-test" || j.action === "summary-test")) {
        body.appendChild(h("div", { "class": "actions" }, h("a", { "class": "btn", href: "/social/preview", target: "_blank", rel: "noopener", text: "The picture ↗" }),
          j.action === "summary-test" ? ["2", "3", "4"].map(function (n) { return h("a", { "class": "btn", href: "/social/preview" + n, target: "_blank", rel: "noopener", text: "Post " + n + " ↗" }); }) : null));
      }
    }
    var a = S.activity;
    if (!a) { body.appendChild(h("p", { "class": "note", text: "Reading…" })); return; }
    body.appendChild(h("div", null, h("p", { "class": "sub", text: "The last jobs" }), h("div", { "class": "list" }, a.jobs.filter(function (x) { return x.action !== "refresh"; }).length ? a.jobs.filter(function (x) { return x.action !== "refresh"; }).slice(0, 12).map(function (x) {
      var spec = S.catalog[x.action] || { label: x.action }, ok = x.state === "done" && x.rc === 0;
      var params = x.params && typeof x.params === "object" ? Object.keys(x.params).map(function (k) { return x.params[k]; }).filter(Boolean).join(" ") : "";
      return h("button", { type: "button", "class": "li" + (x.id === S.drawerJob ? " sel" : ""), "aria-current": x.id === S.drawerJob ? "true" : null, onclick: function () { showOld(x); } },
        h("div", null, h("b", { text: spec.label + (params ? ": " + params : "") }), h("small", { text: clock(x.started || 0) + " · " + (x.by || "") })),
        h("span", { "class": "pill " + (x.state === "running" ? "run" : ok ? "ok" : x.state === "done" || x.state === "refused" ? "bad" : "queued"), text: x.state === "done" ? (ok ? "ok" : "exit " + x.rc) : x.state }));
    }) : h("p", { "class": "note", text: "Nothing run from the console yet." }))));
    body.appendChild(h("div", null, h("p", { "class": "sub", text: "Changes (the root helper's journal)" }), h("pre", { "class": "mono-list", text: a.journal.join("\n") || "None yet." })));
    body.appendChild(h("div", null, h("p", { "class": "sub", text: "Sign-ins" }), h("pre", { "class": "mono-list", text: a.audit.join("\n") || "None yet." })));
  }
  function showOld(x) {
    if (!S.jobs[x.id]) S.jobs[x.id] = { id: x.id, action: x.action, label: (S.catalog[x.action] || {}).label || x.action, params: x.params, state: x.state, log: "", next: 0, key: "old-" + x.id, quiet: true };
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
    p.appendChild(content); $("modal").hidden = false;
    var f = p.querySelector("button.primary") || p.querySelector("input, button"); if (f) setTimeout(function () { f.focus(); }, 30);
  }
  function closeModal() { $("modal").hidden = true; $("modal-panel").innerHTML = ""; S.wizardOpen = false; }

  // ---- the wizard: the first time, five short steps; only what differs from the Pi's settings is applied
  function wizard() {
    var c = S.cfg, f = S.facts;
    var W = {
      mode: c.DISPLAY_MODE || "dots", color: c.THEME || "amber", units: c.UNITS || "metric", radius: String(Number(c.RADIUS) || 10),
      stats: on(c.STATS) ? "on" : "off", localdb: on(c.LOCAL_DB) ? "on" : "off",
      watchdog: f.watchdog || "off", netwatch: f.netwatch || "off", patches: f.patches || "off", keeplogs: f.keeplogs || "off"
    };
    var start = JSON.parse(JSON.stringify(W)), step = 0;
    var STEPS = [
      function () {
        return [h("h3", { text: "Welcome to the console" }),
          h("p", { "class": "lead", text: "ZenithBoard's settings from this browser, next to the wall, the menu and the zenithboard command, which all stay as they are. Each change here runs the same command as over SSH, and you see what it prints." }),
          h("ul", { "class": "ticks" }, h("li", { text: "Answers your home network only" }), h("li", { text: "Signed in by password, or a phone paired with a QR code" }),
            h("li", { text: "A fixed list of actions; uninstalling, Wi-Fi and passwords stay in the terminal" }), h("li", { text: "Off again at any time: sudo zenithboard console off" })),
          h("p", { "class": "note", text: "Four short steps (the wall, what to collect, what keeps it running, your phone), then a review. Nothing is changed before you apply it there." })];
      },
      function () {
        return [h("h3", { text: "The wall" }), h("p", { "class": "lead", text: "The default of every screen; a tablet can still pick its own with its gear." }),
          wrow("Look", wseg("mode", ["dots", "flap"], ["Dot matrix", "Split-flap"])),
          wrow("Colour", h("div", { "class": "swatches" }, Object.keys(THEME_HEX).map(function (t) {
            var b = h("button", { type: "button", "class": "swatch" + (W.color === t ? " on" : ""), "aria-label": t, onclick: function () { W.color = t; theme(t); redraw(); } });
            b.style.background = THEME_HEX[t]; return b;
          }))),
          wrow("Units", wseg("units", ["metric", "imperial"], ["km · m", "mi · ft"])),
          wrow("Radius", wseg("radius", ["1", "2", "5", "10", "15", "30", "50"]))];
      },
      function () {
        return [h("h3", { text: "What to collect" }), h("p", { "class": "lead", text: "Both stay on the card; nothing is sent anywhere." }),
          wrow("Statistics", wsw("stats"), "A sample every 15 minutes, 30 days kept (about 30 KB a day): the /stats page, and the summaries' figures."),
          wrow("The receiver map's aircraft database", wsw("localdb"), f.map ? "Registrations and models read on the card (tar1090)." : "Needs the receiver map (tar1090), not seen on this Pi.")];
      },
      function () {
        return [h("h3", { text: "What keeps it running" }), h("p", { "class": "lead", text: "Recommended for a Pi left outdoors on Wi-Fi. Each one off again puts back what it found." }),
          wrow("Hardware watchdog", wsw("watchdog"), "The chip restarts a frozen Pi after about 10 seconds."),
          wrow("Network watchdog", wsw("netwatch"), "No router for 6 minutes: the network restarts; 12: the Pi."),
          wrow("Logs kept after a restart", wsw("keeplogs"), "Up to 50 MB, to read what happened before a freeze."),
          wrow("Daily security fixes", wsw("patches"), "Debian's security channel only; feeders untouched, no reboot.")];
      },
      function () {
        return [h("h3", { text: "Your phone" }),
          h("p", { "class": "lead", text: "Scan a QR code once and the phone stays signed in, no password typed, as long as it opens the console once a month. Face ID and passkeys need HTTPS under a domain name, which a Pi at a home address does not have: the QR code is how a phone signs in here." }),
          h("div", { "class": "actions" }, h("button", { type: "button", "class": "btn", text: "Pair a phone now", onclick: function () { S.wizardOpen = false; pairPhone(reopen); } })),
          h("p", { "class": "note", text: "Or later: System → Signed in → Pair a phone; or over SSH: sudo zenithboard console pair." })];
      },
      function () {
        var plan = changes();
        return [h("h3", { text: plan.length ? "Ready" : "Nothing to change" }),
          h("p", { "class": "lead", text: plan.length ? "These are applied one after the other; each is the zenithboard command shown in Activity." : "Everything is already as you chose." }),
          h("ul", { "class": "ticks plan", id: "wiz-plan" }, plan.map(function (p) { return h("li", { "data-k": p[0], text: p[2] }); }))];
      }
    ];
    var ACTION_OF = { mode: "mode", color: "color", units: "units", radius: "radius", stats: "stats", localdb: "localdb", watchdog: "watchdog", netwatch: "netwatch", patches: "patches", keeplogs: "keeplogs" };
    var WORDS = { mode: "Look", color: "Colour", units: "Units", radius: "Radius", stats: "Statistics", localdb: "Receiver map's database", watchdog: "Hardware watchdog", netwatch: "Network watchdog", patches: "Daily security fixes", keeplogs: "Logs kept after a restart" };
    function changes() {
      return Object.keys(W).filter(function (k) { return W[k] !== start[k]; }).map(function (k) { return [k, ACTION_OF[k], WORDS[k] + ": " + W[k]]; });
    }
    function wrow(title, ctl, hint) { var t = ctl && ctl.classList && ctl.classList.contains("sw"); return h("div", { "class": "row" + (t ? " tight" : "") }, h("div", { "class": "what" }, h("b", { text: title }), hint ? h("span", { text: hint }) : null), h("div", { "class": "ctl" + (t ? " end" : "") }, ctl)); }
    function wseg(k, choices, labels) {
      return h("div", { "class": "seg" }, choices.map(function (c, i) {
        return h("button", { type: "button", "class": W[k] === c ? "on" : "", text: labels ? labels[i] : c, onclick: function () { W[k] = c; redraw(); } });
      }));
    }
    function wsw(k) { return h("button", { type: "button", role: "switch", "aria-checked": W[k] === "on" ? "true" : "false", "class": "sw" + (W[k] === "on" ? " on" : ""), onclick: function () { W[k] = W[k] === "on" ? "off" : "on"; redraw(); } }); }
    function done() { api("wizard", { body: { done: true } }); S.session.wizard_done = true; theme(S.cfg.THEME); closeModal(); }
    function apply() {
      var plan = changes(), i = 0, ok = true;
      var foot = $("modal-panel").querySelector(".modal-foot"); if (foot) foot.innerHTML = "";
      function next() {
        if (i >= plan.length) {
          api("wizard", { body: { done: true } }); S.session.wizard_done = true;
          if (foot) foot.appendChild(h("button", { type: "button", "class": "primary", text: ok ? "Done" : "Close", onclick: function () { closeModal(); loadState(); } }));
          return;
        }
        var p = plan[i], li = document.querySelector('#wiz-plan li[data-k="' + p[0] + '"]');
        if (li) li.className = "run";
        run(p[1], { value: W[p[0]] }, { confirmed: true, quiet: true }).then(function (j) {
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
        h("header", null, h("h2", { text: "First steps · " + (step + 1) + " of " + STEPS.length }), h("button", { type: "button", "class": "ghost", "aria-label": "Close", text: "×", onclick: done })),
        dotsRow, body,
        h("div", { "class": "modal-foot" },
          step === 0 ? h("button", { type: "button", "class": "ghost", text: "Skip, I'll look around", onclick: done }) : h("button", { type: "button", "class": "btn", text: "Back", onclick: function () { step--; redraw(); } }),
          last ? h("button", { type: "button", "class": "primary", text: changes().length ? "Apply " + changes().length + " change" + (changes().length > 1 ? "s" : "") : "Finish", onclick: function () { if (changes().length) apply(); else done(); } })
            : h("button", { type: "button", "class": "primary", text: "Next", onclick: function () { step++; redraw(); } }))), true);
      S.wizardOpen = true;
    }
    S.wizardOpen = true;
    redraw();
  }

  boot();
})();
