// SPDX-License-Identifier: GPL-3.0-or-later
// Run: node tests/test_i18n.js   The pages' translation (flightinfo/static/i18n.js, 0.47.0): English is the key and
// the fallback, never a blank; placeholders filled in any order; plurals by the language's own rules (French says
// "1 changement" and "0 changement"; Russian has three forms); numbers in the language's way; the browser's language
// guessed for the first visit; the shipped French catalogue read as the pages read it.
const assert = require("assert"), fs = require("fs"), path = require("path");
global.window = {};
global.location = { search: "" };
Object.defineProperty(global, "navigator", { value: { languages: ["fr-FR", "fr"] }, writable: true, configurable: true });   // node has its own
require(path.join(__dirname, "..", "flightinfo", "static", "i18n.js"));
const I = window.ZBI18N;

// English: the key itself, its placeholders filled
I._load("en", {}, []);
assert.strictEqual(I.t("Make a backup"), "Make a backup");
assert.strictEqual(I.t("Sign in {name} at {ip}?", { name: "Firefox", ip: "192.168.1.20" }), "Sign in Firefox at 192.168.1.20?");
assert.strictEqual(I.t("{job}: done.", {}), "{job}: done.", "an unknown placeholder stays visible rather than becoming 'undefined'");
assert.strictEqual(I.tn(1, "Apply {n} change", "Apply {n} changes"), "Apply 1 change");
assert.strictEqual(I.tn(3, "Apply {n} change", "Apply {n} changes"), "Apply 3 changes");
assert.deepStrictEqual(I.langs(), ["en"], "a Pi with no catalogue offers English alone");

// French from the shipped catalogue
const fr = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "flightinfo", "static", "i18n", "fr", "console.json"), "utf8"));
I._load("fr", fr, ["fr"]);
assert.strictEqual(I.t("Make a backup"), "Faire une sauvegarde");
assert.strictEqual(I.t("Sign in {name} at {ip}?", { name: "Firefox", ip: "192.168.1.20" }), "Connecter Firefox à l'adresse 192.168.1.20 ?");
assert.strictEqual(I.t("A sentence nobody translated"), "A sentence nobody translated", "missing: the English, never a blank");
assert.strictEqual(I.tn(1, "Apply {n} change", "Apply {n} changes"), "Appliquer 1 changement");
assert.strictEqual(I.tn(0, "Apply {n} change", "Apply {n} changes"), "Appliquer 0 changement", "French: 0 takes the singular");
assert.strictEqual(I.tn(4, "Apply {n} change", "Apply {n} changes"), "Appliquer 4 changements");
assert.strictEqual(I.num(21.34, 1), "21,3", "a decimal comma in French");
assert.strictEqual(I.t("{time} ago", { time: "3 min" }), "il y a 3 min", "the word order is the translation's");
assert.deepStrictEqual(I.langs(), ["en", "fr"]);
assert.strictEqual(I.name("fr"), "Français");
assert.strictEqual(I.browserGuess(), "fr", "the first visit lights the browser's own language");

// Russian's three forms, from a catalogue entry made of them
I._load("ru", { "{n} aircraft": { one: "{n} самолёт", few: "{n} самолёта", many: "{n} самолётов", other: "{n} самолёта" } }, ["ru"]);
assert.strictEqual(I.tn(1, "{n} aircraft", "{n} aircraft"), "1 самолёт");
assert.strictEqual(I.tn(3, "{n} aircraft", "{n} aircraft"), "3 самолёта");
assert.strictEqual(I.tn(5, "{n} aircraft", "{n} aircraft"), "5 самолётов");
assert.strictEqual(I.tn(21, "{n} aircraft", "{n} aircraft"), "21 самолёт");

// Arabic (0.48.0): right to left; a value put in a sentence keeps its own order, its "@" with it; numbers in Western digits
const ar = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "flightinfo", "static", "i18n", "ar", "console.json"), "utf8"));
const arStats = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "flightinfo", "static", "i18n", "ar", "stats.json"), "utf8"));
I._load("ar", Object.assign({}, ar, arStats), ["ar"]);
assert.ok(I.rtl(), "Arabic reads right to left");
const acct = I.t("Account @{account}. The account itself is set up over SSH (it asks for an app password): sudo zenithboard social setup", { account: "zenithboard.bsky.social" });
assert.ok(acct.indexOf("\u2066@zenithboard.bsky.social\u2069") >= 0, "the handle isolated, its @ with it: " + acct);
assert.strictEqual(I.num(21.34, 1), "21.3", "Western digits, as the Pi writes its own numbers");
assert.strictEqual(I.tn(1, "{n} aircraft", "{n} aircraft"), "طائرة واحدة");
assert.strictEqual(I.tn(2, "{n} aircraft", "{n} aircraft"), "طائرتان");
assert.ok(/طائرات$/.test(I.tn(5, "{n} aircraft", "{n} aircraft")), "3 to 10: the plural");
I._load("fr", fr, ["fr"]);
assert.ok(!I.rtl());
assert.strictEqual(I.t("Account @{account}. Posting each crossing is switched in Sharing; the summaries here.", { account: "a.b" }).indexOf("\u2066"), -1, "no isolation left to right");

// the browser's language for the first visit: Traditional Chinese from Taiwan, Brazilian Portuguese from any pt
I._load("en", {}, ["zh-Hans", "zh-Hant", "pt-BR"]);
navigator.languages = ["zh-TW"]; assert.strictEqual(I.browserGuess(), "zh-Hant");
navigator.languages = ["zh-CN"]; assert.strictEqual(I.browserGuess(), "zh-Hans");
navigator.languages = ["pt-PT", "en"]; assert.strictEqual(I.browserGuess(), "pt-BR");
navigator.languages = ["sv-SE"]; assert.strictEqual(I.browserGuess(), "en", "a language with no catalogue: English");

// the count words take their singular in French (0.48.0: "1 avions" before)
const frStats = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "flightinfo", "static", "i18n", "fr", "stats.json"), "utf8"));
I._load("fr", Object.assign({}, fr, frStats), ["fr"]);
assert.strictEqual(I.tn(1, "{n} aircraft", "{n} aircraft"), "1 avion");
assert.strictEqual(I.tn(7, "{n} distinct aircraft", "{n} distinct aircraft"), "7 avions distincts");

// every key the console's script asks for is in the French catalogue (tools/i18n.py check says the same in detail)
const js = fs.readFileSync(path.join(__dirname, "..", "flightinfo", "static", "console.js"), "utf8");
const asked = [...js.matchAll(/(?<![\w.$])t\("((?:[^"\\]|\\.)*)"/g)].map(m => JSON.parse('"' + m[1] + '"'));
assert.ok(asked.length > 300, "console.js asks for its words through t()");
asked.forEach(k => assert.ok(fr[k], "not in fr/console.json: " + k));
console.log("i18n: ok");
