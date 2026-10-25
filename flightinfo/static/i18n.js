// SPDX-License-Identifier: GPL-3.0-or-later
// The web pages' languages (0.47.0): the console, the statistics page and graphs1090's page in the visitor's language.
// The English text is the key (gettext's way): t("Make a backup") gives the catalogue's translation, or the English
// itself when there is none, never a blank. A catalogue is a JSON object per language and page,
// /static/i18n/<lang>/<page>.json, fetched once per page load; English needs none. A plural is an object of the
// language's plural forms ({"one": ..., "other": ...}), chosen with the browser's Intl.PluralRules.
// The language: ?lang= in the address, else the one chosen in this browser (localStorage "zb-lang"), else the Pi's
// (CONSOLE_LANG, given by /api/config), else English. Only the languages the Pi has catalogues for are offered.
// Flags are the PNG flags the wall already carries (Windows draws no flag emoji); English shows the United Kingdom's
// and the United States' together, cut along the diagonal (the owner's choice, 21 October 2026).
(function () {
  "use strict";
  // code, its own name, flag(s); the order of the list shown. A language spoken across many countries has a picture of
  // its own rather than one country's flag (0.48.0, the owner's choice): Swahili the map of Africa, Arabic its letter
  // ʿayn. Flags are the wall's PNGs (/flags/CC.png); "@name" is a picture in /static/i18n/flags/name.svg.
  var LANGS = [
    ["en", "English", ["GB", "US"]],
    ["fr", "Français", ["FR"]],
    ["de", "Deutsch", ["DE"]],
    ["nl", "Nederlands", ["NL"]],
    ["it", "Italiano", ["IT"]],
    ["es", "Español", ["ES"]],
    ["pt-BR", "Português (Brasil)", ["BR"]],
    ["pl", "Polski", ["PL"]],
    ["fi", "Suomi", ["FI"]],
    ["et", "Eesti", ["EE"]],
    ["lv", "Latviešu", ["LV"]],
    ["lt", "Lietuvių", ["LT"]],
    ["id", "Bahasa Indonesia", ["ID"]],
    ["sw", "Kiswahili", ["@africa"]],
    ["hi", "हिन्दी", ["IN"]],
    ["ru", "Русский", ["RU"]],
    ["uk", "Українська", ["UA"]],
    ["ar", "العربية", ["@arabic"]],
    ["ja", "日本語", ["JP"]],
    ["ko", "한국어", ["KR"]],
    ["zh-Hans", "简体中文", ["CN"]],
    ["zh-Hant", "繁體中文", ["TW"]]
  ];
  var RTL = ["ar"];
  var KEY = "zb-lang";
  var cur = "en", cat = {}, avail = ["en"], conf = {};

  function known(code) { return LANGS.some(function (l) { return l[0] === code; }); }
  function info(code) { return LANGS.filter(function (l) { return l[0] === code; })[0] || LANGS[0]; }
  function saved() { try { return localStorage.getItem(KEY) || ""; } catch (e) { return ""; } }
  function save(code) { try { localStorage.setItem(KEY, code); } catch (e) { /* a private window: this page only */ } }
  function param() { var m = /[?&]lang=([A-Za-z-]{2,8})/.exec(location.search); return m ? m[1] : ""; }

  // a value put in a right-to-left sentence (an address, a name, a command, "@handle") keeps its own left-to-right
  // order: it is isolated (U+2066 … U+2069), its "@" with it (0.48.0, Arabic)
  function fill(s, v) {
    if (!v) return s;
    var rtl = RTL.indexOf(cur) >= 0;
    return String(s).replace(/(@?)\{(\w+)\}/g, function (m, at, k) {
      if (!Object.prototype.hasOwnProperty.call(v, k)) return m;
      return rtl ? "\u2066" + at + String(v[k]) + "\u2069" : at + String(v[k]);
    });
  }
  function t(key, v) {
    if (typeof key !== "string") return key;
    var tr = cat[key];
    return fill(typeof tr === "string" && tr !== "" ? tr : key, v);
  }
  // tn(5, "{n} aircraft seen", "{n} aircraft seen"): the English singular and plural; the catalogue's entry, keyed by
  // the plural, holds the language's own forms
  function tn(n, one, other, v) {
    v = Object.assign({ n: num(n) }, v || {});
    var tr = cat[other];
    if (tr && typeof tr === "object") {
      var form = "other";
      try { form = new Intl.PluralRules(locale()).select(Number(n)); } catch (e) { /* old browser: "other" */ }
      var s = tr[form] || tr.other;
      if (s) return fill(s, v);
    } else if (typeof tr === "string" && tr !== "") return fill(tr, v);
    return fill(Number(n) === 1 ? one : other, v);
  }
  // Arabic in Western digits: the Pi's own numbers (addresses, times, the output) are written so, and mixing both
  // digit sets on one page reads worse than either
  function locale() { return cur === "ar" ? "ar-u-nu-latn" : cur; }
  function num(x, digits) {
    if (typeof x !== "number" && !(typeof x === "string" && x !== "" && !isNaN(Number(x)))) return x;
    var d = digits === undefined ? undefined : digits;
    try {
      return new Intl.NumberFormat(locale(), d === undefined ? { maximumFractionDigits: 20, useGrouping: false } :
        { minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: false }).format(Number(x));
    } catch (e) { return d === undefined ? String(x) : Number(x).toFixed(d); }
  }

  // ---- static pages: an element marked data-t is translated whole; its key is its text with the inner tags kept
  // bare (<a>, <b>, <code>…, without their attributes), so a translation may move a link inside its sentence and the
  // link keeps its address. aria-label, title and placeholder are translated when the catalogue knows them.
  function keyOf(el) {
    var out = "";
    el.childNodes.forEach(function (n) {
      if (n.nodeType === 3) out += n.nodeValue;
      else if (n.nodeType === 1) { var tag = n.tagName.toLowerCase(); out += "<" + tag + ">" + keyOf(n) + "</" + tag + ">"; }
    });
    return out;
  }
  function norm(s) { return s.replace(/[ \t\r\n]+/g, " ").replace(/^ | $/g, ""); }
  function rebuild(el, tr) {
    var kids = Array.prototype.filter.call(el.childNodes, function (n) { return n.nodeType === 1; });
    var used = {}, re = /<(\w+)>([\s\S]*?)<\/\1>/g, last = 0, m, frag = document.createDocumentFragment();
    while ((m = re.exec(tr))) {
      if (m.index > last) frag.appendChild(document.createTextNode(tr.slice(last, m.index)));
      var tag = m[1].toLowerCase(), n = used[tag] || 0, src = kids.filter(function (k) { return k.tagName.toLowerCase() === tag; })[n];
      used[tag] = n + 1;
      if (src) {
        var c = src.cloneNode(false);
        if (src.children.length) rebuild(c, m[2]); else c.textContent = m[2];
        frag.appendChild(c);
      } else frag.appendChild(document.createTextNode(m[2]));
      last = re.lastIndex;
    }
    if (last < tr.length) frag.appendChild(document.createTextNode(tr.slice(last)));
    el.textContent = ""; el.appendChild(frag);
  }
  function translateDom(root) {
    root = root || document;
    if (cur === "en") return;
    root.querySelectorAll("[data-t]").forEach(function (el) {
      var key = norm(keyOf(el)), tr = cat[key];
      if (typeof tr === "string" && tr !== "") rebuild(el, tr);
    });
    ["aria-label", "title", "placeholder"].forEach(function (a) {
      root.querySelectorAll("[" + a + "]").forEach(function (el) {
        var tr = cat[el.getAttribute(a)];
        if (typeof tr === "string" && tr !== "") el.setAttribute(a, tr);
      });
    });
    var ti = document.querySelector("title");
    if (ti && cat[ti.textContent]) ti.textContent = cat[ti.textContent];
  }

  // ---- choosing: a flag and the language's own name, a list of the others
  function flag(code, base) {
    var f = info(code)[2], box = document.createElement("span");
    box.className = "zb-flag" + (f.length > 1 ? " two" : "");
    f.forEach(function (cc) {
      var img = document.createElement("img");
      img.src = cc.charAt(0) === "@" ? (conf.staticBase || "/static/") + "i18n/flags/" + cc.slice(1) + ".svg"
        : (base || conf.flagBase || "/flags/") + cc + ".png";
      img.alt = ""; img.width = 24; img.height = 16;
      box.appendChild(img);
    });
    return box;
  }
  function listButton(code, onPick, isOn) {
    var b = document.createElement("button");
    b.type = "button"; b.className = "zb-lang-item" + (isOn ? " on" : ""); b.setAttribute("lang", code);
    if (isOn) b.setAttribute("aria-current", "true");
    b.appendChild(flag(code));
    var nm = document.createElement("span"); nm.textContent = info(code)[1]; b.appendChild(nm);
    b.addEventListener("click", function () { onPick(code); });
    return b;
  }
  function picker(opts) {
    opts = opts || {};
    var wrap = document.createElement("div"); wrap.className = "zb-lang";
    var btn = document.createElement("button");
    btn.type = "button"; btn.className = "zb-lang-btn"; btn.setAttribute("aria-haspopup", "true"); btn.setAttribute("aria-expanded", "false");
    btn.setAttribute("aria-label", t("Language") + ": " + info(cur)[1]); btn.title = t("Language");
    btn.appendChild(flag(cur));
    var nm = document.createElement("span"); nm.className = "zb-lang-name"; nm.textContent = info(cur)[1]; btn.appendChild(nm);
    var menu = document.createElement("div"); menu.className = "zb-lang-menu"; menu.hidden = true;
    list().forEach(function (code) { menu.appendChild(listButton(code, function (c) { menu.hidden = true; choose(c, opts.onChange); }, code === cur)); });
    btn.addEventListener("click", function (e) {
      e.stopPropagation(); menu.hidden = !menu.hidden; btn.setAttribute("aria-expanded", menu.hidden ? "false" : "true");
    });
    document.addEventListener("click", function (e) { if (!wrap.contains(e.target)) { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); } });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); } });
    wrap.appendChild(btn); wrap.appendChild(menu);
    if (list().length < 2) wrap.hidden = true;            // English alone on this Pi: nothing to choose
    return wrap;
  }
  // the first visit: the browser's own language and English as two large buttons, every other one in a single list
  // (0.48.0, the owner: twenty flags on the first page would be too many)
  function chooser(onPick) {
    var wrap = document.createElement("div"), box = document.createElement("div");
    var pick = onPick || function (c) { choose(c); };
    box.className = "zb-lang-first";
    var guess = browserGuess(), first = [guess].concat(guess === "en" ? [] : ["en"]);
    if (first.length < 2) first.push(list().filter(function (c) { return c !== "en"; })[0]);
    first = first.filter(Boolean);
    first.forEach(function (code) { box.appendChild(listButton(code, pick, code === guess)); });
    wrap.appendChild(box);
    var rest = list().filter(function (c) { return first.indexOf(c) < 0; });
    if (rest.length) {
      var more = document.createElement("label"); more.className = "zb-lang-more";
      var sel = document.createElement("select");
      var o0 = document.createElement("option"); o0.value = ""; o0.textContent = t("Other languages ({n})", { n: rest.length }); sel.appendChild(o0);
      rest.forEach(function (code) {
        var o = document.createElement("option"); o.value = code; o.textContent = info(code)[1]; o.lang = code; sel.appendChild(o);
      });
      sel.setAttribute("aria-label", t("Other languages"));
      sel.addEventListener("change", function () { if (sel.value) pick(sel.value); });
      more.appendChild(sel); wrap.appendChild(more);
    }
    return wrap;
  }
  function browserGuess() {
    var want = (navigator.languages || [navigator.language || "en"]), l = list();
    for (var i = 0; i < want.length; i++) {
      var w = String(want[i]), base = w.split("-")[0].toLowerCase();
      if (l.indexOf(w) >= 0) return w;
      if (base === "zh") { var hant = /-(TW|HK|MO|Hant)/i.test(w) ? "zh-Hant" : "zh-Hans"; if (l.indexOf(hant) >= 0) return hant; }
      if (base === "pt" && l.indexOf("pt-BR") >= 0) return "pt-BR";
      if (l.indexOf(base) >= 0) return base;
    }
    return "en";
  }
  function list() { return LANGS.map(function (l) { return l[0]; }).filter(function (c) { return avail.indexOf(c) >= 0; }); }
  function choose(code, then) {
    save(code);
    if (typeof then === "function") return then(code);
    // a ?lang= in the address would win again: the address loses it (these pages carry nothing else after "?")
    if (location.search && window.history && history.replaceState) history.replaceState(null, "", location.pathname + location.hash);
    location.reload();
  }

  // ---- start a page: its language, its catalogue, then the page itself
  // opts: part (console, stats, graphs), base (where the catalogues are), config (an object, or the address of
  // /api/config), flagBase
  function start(opts, run) {
    opts = opts || {};
    conf = opts;
    var cfgP = typeof opts.config === "object" && opts.config ? Promise.resolve(opts.config) :
      fetch(opts.config || "/api/config", { cache: "no-store", credentials: "same-origin" }).then(function (r) { return r.json(); });
    var done = false;
    function go() {
      if (done) return;
      done = true;
      document.documentElement.lang = cur;
      if (opts.dir !== false) document.documentElement.dir = RTL.indexOf(cur) >= 0 ? "rtl" : "ltr";   // graphs1090's page: its own
      translateDom(document); run();
    }
    cfgP.catch(function () { return {}; }).then(function (c) {
      c = c || {};
      conf.server = c.lang || "";
      avail = ["en"].concat((c.langs || []).filter(function (x) { return known(x) && x !== "en"; }));
      var p = param();
      if (p && avail.indexOf(p) >= 0) save(p);
      var want = [p, saved(), c.lang].filter(function (x) { return x && avail.indexOf(x) >= 0; })[0] || "en";
      cur = want;
      if (cur === "en") return go();
      return fetch((opts.base || "/static/i18n/") + cur + "/" + (opts.part || "console") + ".json", { cache: "no-cache" })
        .then(function (r) { if (!r.ok) throw new Error("no catalogue"); return r.json(); })
        .then(function (j) { cat = j || {}; go(); })
        .catch(function () { cur = "en"; cat = {}; go(); });   // a missing catalogue: the page in English, never broken
    });
    setTimeout(function () { if (!done) { cur = "en"; cat = {}; go(); } }, 8000);   // never a page stuck on a slow answer
  }

  window.ZBI18N = {
    t: t, tn: tn, num: num, locale: locale, lang: function () { return cur; }, langs: list, name: function (c) { return info(c)[1]; },
    saved: saved, serverLang: function () { return conf.server || ""; }, start: start, translateDom: translateDom,
    picker: picker, chooser: chooser, choose: choose, flag: flag, browserGuess: browserGuess, LANGS: LANGS,
    rtl: function () { return RTL.indexOf(cur) >= 0; },
    _load: function (lang, catalogue, langs) { cur = lang; cat = catalogue || {}; avail = ["en"].concat(langs || []); }   // the tests
  };
})();
