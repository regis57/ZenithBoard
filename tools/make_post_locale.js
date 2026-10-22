// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tools/make_post_locale.js   (0.51.0) Writes flightinfo/data/post-locale.json: what the posts need of each
// language that is not words to translate, taken from the Unicode CLDR data in Node's Intl, so the Pi needs no library
// for it: the decimal and group signs, the day-and-month pattern with its month names (Russian "12 октября", Japanese
// "10月12日"), the patterns of a span of days in one month and across two, the weekdays, and the country names; 0.52.1:
// the clock (13.50 in Indonesian and Finnish, 13:50 elsewhere) and the metric units (839 км/ч, 839 km/u, 10 670米). English
// keeps the posts' own style ("12 October", "12–18 October", a space that does not break between thousands) and is
// not written. Run it again when a language is added; tests/test_post_lang.py checks the Python side against it.
"use strict";
const fs = require("fs"), path = require("path");
const ROOT = path.join(__dirname, "..");
const LANGS = ["fr", "de", "nl", "it", "es", "pt-BR", "pl", "fi", "et", "lv", "lt", "id", "sw", "ru", "uk", "ar", "ja", "ko", "zh-Hans", "zh-Hant"];
const tag = (l) => l === "ar" ? "ar-u-nu-latn" : l;              // Arabic in Western digits, as the pages write it

const blocks = JSON.parse(fs.readFileSync(path.join(ROOT, "flightinfo/data/icao_countries.json"), "utf8")).blocks;
const codes = new Set(blocks.map((b) => b[2]).filter((c) => /^[A-Z]{2}$/.test(c)));
fs.readdirSync(path.join(ROOT, "flightinfo/data/flags")).forEach((f) => { const m = /^([A-Z]{2})\.png$/.exec(f); if (m) codes.add(m[1]); });

function dayMonth(l, d) {
  const parts = new Intl.DateTimeFormat(tag(l), { day: "numeric", month: "long", timeZone: "UTC" }).formatToParts(d);
  return { pattern: parts.map((p) => p.type === "day" ? "{d}" : p.type === "month" ? "{M}" : p.value).join(""),
           month: parts.filter((p) => p.type === "month").map((p) => p.value).join("") };
}
function rangePattern(l, a, b, months, dm) {
  const parts = new Intl.DateTimeFormat(tag(l), { day: "numeric", month: "long", timeZone: "UTC" }).formatRangeToParts(a, b);
  const words = (p, which) => p.type === "month" && p.value === months[(which === "1" ? a : b).getUTCMonth()];
  const figures = parts.some((p) => p.type === "literal" && p.value.includes("/")) && !dm.includes("/");
  if (!figures && parts.every((p) => p.type !== "month" || words(p, p.source === "startRange" ? "1" : "2"))) {
    return parts.map((p) => {
      const which = p.source === "startRange" ? "1" : "2";      // shared parts are the end's
      return p.type === "day" ? "{d" + which + "}" : p.type === "month" ? "{M" + which + "}" : p.value;
    }).join("");
  }
  // Japanese and Chinese spans fall back to figures in ICU (10/12～10/18), and Korean's across two months splits its
  // words: each end written as a day and month instead, with the span's own sign between them
  const shared = parts.filter((p) => p.source === "shared" && p.type === "literal").map((p) => p.value).join("");
  const sep = (shared.match(/\s*[~～〜至–—-]\s*/) || [" – "])[0];
  return dm.replace("{d}", "{d1}").replace("{M}", "{M1}") + sep + dm.replace("{d}", "{d2}").replace("{M}", "{M2}");
}

// 0.52.1: a time of day, 24-hour, as the language writes it: {h}:{m}, or {h}.{m} in Indonesian and Finnish (the owner
// read "pukul 13:50" on 22 October; Indonesian spelling, EYD, separates hours and minutes with a full stop)
function clockPattern(l) {
  const parts = new Intl.DateTimeFormat(tag(l), { hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: "UTC" })
    .formatToParts(new Date(Date.UTC(2026, 9, 22, 13, 5)));
  const p = parts.map((x) => x.type === "hour" ? "{h}" : x.type === "minute" ? "{m}" : x.value).join("");
  if (!/^\{h\}[^{}]{1,3}\{m\}$/.test(p)) throw new Error(l + ": an unexpected clock pattern: " + p);
  return p;
}
// a metric unit around its number, short: "{n} км/ч", "{n}km/h" (Korean), "km {n}/saa" (Swahili). A plain space becomes
// one that does not break, so "8 600 m" never splits across two lines (0.19.8). Arabic's metre changes with the count
// (10 600 متر, 10 610 أمتار, 10 670 مترًا): then one pattern per plural category, each from a number of that category
// (3 and up: Arabic's one and two are said without a figure, and an altitude is never 1 or 2 metres)
function unitPattern(l, unit) {
  const one = (n) => {
    let seen = false;
    const p = new Intl.NumberFormat(tag(l), { style: "unit", unit, unitDisplay: "short" }).formatToParts(n)
      .map((x) => x.type === "integer" || x.type === "group" ? (seen ? "" : (seen = true, "{n}")) : x.value).join("").replace(/ /g, "\u00a0");
    if (!seen) throw new Error(l + ": no number in the unit pattern of " + unit + " for " + n);
    return p;
  };
  const pr = new Intl.PluralRules(tag(l)), byCat = {};
  for (let n = 3; n < 1000; n++) { const c = pr.select(n); if (!(c in byCat)) byCat[c] = one(n); }
  const pats = new Set(Object.values(byCat));
  if (pats.size === 1) return [...pats][0];
  if (!byCat.other) throw new Error(l + ": no 'other' pattern for " + unit);
  return byCat;
}

const out = { _comment: "Made by tools/make_post_locale.js from Node " + process.version + " (ICU " + process.versions.icu + ", CLDR " + process.versions.cldr + "). Do not edit by hand." };
for (const l of LANGS) {
  const nf = new Intl.NumberFormat(tag(l));
  const parts = nf.formatToParts(12345.6);
  const group = (parts.find((p) => p.type === "group") || { value: "" }).value;
  const decimal = (parts.find((p) => p.type === "decimal") || { value: "." }).value;
  const minGroup = /\D/.test(nf.format(1000)) ? 1 : 2;           // Spanish and Polish write 1000, then 10 000
  const months = [], dm = [];
  for (let m = 0; m < 12; m++) { const x = dayMonth(l, new Date(Date.UTC(2026, m, 12))); months.push(x.month); dm.push(x.pattern); }
  if (new Set(dm).size !== 1) throw new Error(l + ": the day-and-month pattern changes with the month: " + dm.join(" | "));
  const wd = [];
  // the weekday as it is written inside a sentence (Latvian's alone has a capital): taken from a whole date
  for (let i = 0; i < 7; i++) wd.push(new Intl.DateTimeFormat(tag(l), { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" })
    .formatToParts(new Date(Date.UTC(2026, 9, 19 + i))).filter((p) => p.type === "weekday").map((p) => p.value).join(""));   // 19 October 2026 is a Monday
  const names = new Intl.DisplayNames([tag(l)], { type: "region", fallback: "none" });
  const countries = {};
  [...codes].sort().forEach((c) => { try { const n = names.of(c); if (n && n !== c) countries[c] = n; } catch (e) { /* not a region CLDR knows */ } });
  out[l] = {
    decimal, group, min_group: minGroup, day_month: dm[0], months, weekdays: wd,
    span_one_month: rangePattern(l, new Date(Date.UTC(2026, 9, 12)), new Date(Date.UTC(2026, 9, 18)), months, dm[0]),
    span_two_months: rangePattern(l, new Date(Date.UTC(2026, 8, 28)), new Date(Date.UTC(2026, 9, 4)), months, dm[0]),
    clock: clockPattern(l),
    units: { "meter": unitPattern(l, "meter"), "kilometer": unitPattern(l, "kilometer"), "kilometer-per-hour": unitPattern(l, "kilometer-per-hour") },
    countries
  };
}
fs.writeFileSync(path.join(ROOT, "flightinfo/data/post-locale.json"), JSON.stringify(out, null, 1) + "\n");

// the plural forms Intl gives, for tests/test_post_lang.py to hold the Python rules to
const plurals = {};
const ns = []; for (let n = 0; n <= 130; n++) ns.push(n); ns.push(200, 1000, 1001, 1000000, 2000000, 1234567);
for (const l of ["en"].concat(LANGS)) { const pr = new Intl.PluralRules(tag(l)); plurals[l] = ns.map((n) => [n, pr.select(n)]); }
fs.writeFileSync(path.join(ROOT, "tests/fixtures/plurals.json"), JSON.stringify(plurals) + "\n");
console.log("post-locale.json: " + LANGS.length + " languages, " + codes.size + " country codes");
