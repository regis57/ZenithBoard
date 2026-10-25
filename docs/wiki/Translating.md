# Translating

Since **0.47.0** the web console, the statistics page and graphs1090's page speak more than English, and since
**0.51.0** the Bluesky posts do too, in the language chosen for them (`SOCIAL_LANG`). This page is for
the people who read a language and want it right: **every language has a review sheet**, the English beside the
translation, with a column for your correction. No account, no tool to install, no code.

![The first visit to the console asks the language](https://raw.githubusercontent.com/regis57/ZenithBoard/main/docs/images/console-lang-first.png)

## The languages

| Language | Flag or picture | Since | Review sheet |
|---|---|---|---|
| English | United Kingdom and United States, cut along the diagonal | the reference | — |
| Français | France | 0.47.0 | [fr.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/fr.csv) |
| Deutsch | Germany | 0.48.0 | [de.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/de.csv) |
| Nederlands | Netherlands | 0.48.0 | [nl.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/nl.csv) |
| Italiano | Italy | 0.48.0 | [it.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/it.csv) |
| Español | Spain | 0.48.0 | [es.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/es.csv) |
| Português (Brasil) | Brazil | 0.48.0 | [pt-BR.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/pt-BR.csv) |
| Polski | Poland | 0.48.0 | [pl.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/pl.csv) |
| Suomi | Finland | 0.48.0 | [fi.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/fi.csv) |
| Eesti | Estonia | 0.48.0 | [et.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/et.csv) |
| Latviešu | Latvia | 0.48.0 | [lv.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/lv.csv) |
| Lietuvių | Lithuania | 0.48.0 | [lt.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/lt.csv) |
| Bahasa Indonesia | Indonesia | 0.48.0 | [id.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/id.csv) |
| Kiswahili | the map of Africa (spoken in many countries) | 0.53.1, not yet reviewed by a native speaker | [sw.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/sw.csv) |
| Русский | Russia | 0.48.0 | [ru.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/ru.csv) |
| Українська | Ukraine | 0.48.0 | [uk.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/uk.csv) |
| العربية | its letter ʿayn, ع (spoken in many countries); right to left | 0.48.0 | [ar.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/ar.csv) |
| 日本語 | Japan | 0.48.0 | [ja.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/ja.csv) |
| 한국어 | South Korea | 0.48.0 | [ko.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/ko.csv) |
| 简体中文 | China | 0.48.0 | [zh-Hans.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/zh-Hans.csv) |
| 繁體中文 | Taiwan | 0.48.0 | [zh-Hant.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/zh-Hant.csv) |

**Swahili** was translated in 0.48.0 and held back: 90% (the owner's bar) could not be promised, its technical words
differing between Tanzania, Kenya and the software glossaries. **The owner published it on 22 October 2026 (0.53.1)**
without a native review. Its sheet, `sw.csv`, is the place for a Swahili speaker's corrections: they are checked
against the English and applied like any other language's (`tools/i18n.py apply sw.csv --dry`).

![The console in Arabic, right to left](https://raw.githubusercontent.com/regis57/ZenithBoard/main/docs/images/console-ar.png)

A language appears in the list at the top of the pages once it is translated; the first visit offers the browser's own
language and English as two buttons, the others in one list. **Hausa and Yoruba are not included** (the owner asked for
them unless their translation could not reach 90%): Yoruba's tone marks and the technical vocabulary of both are beyond
what a machine translation gets right reliably. A native speaker who wants either can start a sheet: the owner opens an
issue, and the language comes in once its sheet is filled.

The translations are first made by the session that builds each release, aviation words checked against each
language's own use; the review sheets are there so that someone who speaks it every day corrects them. **Every
correction is checked against the English before it goes in** (`apply --dry`, below); one that does not say what the
English says is not taken, and the reviewer is told why.

## Correcting a sheet

1. Open your language's sheet (the links above). On GitHub it shows as a table you can search; the **Download raw
   file** button gives the file.
2. Open it in LibreOffice Calc, Google Sheets or Excel (Excel: *Data → From Text/CSV*, file origin *UTF-8*, so the
   accents read right), and save it the same way: Excel's *CSV UTF-8*, LibreOffice's *Unicode (UTF-8)* character set.
   A plain *CSV* from Excel loses every letter outside the computer's own alphabet; `apply` refuses it and says so
   (0.54.12). The columns:

   | Column | What it is |
   |---|---|
   | `id` | The row's number, to talk about it |
   | `page` | `console`, `stats`, `graphs` or `posts` (the Bluesky posts' words: a `[part]` is left out when a tag inside it is empty, `{tag\|cap}` takes a capital letter); `[plural: one]` / `[plural: other]` / `[plural: many]` for the forms of a count |
   | `where` | The file it comes from |
   | `english` | The reference |
   | `translation` | What the page shows today |
   | `correction` | **Yours**: write the right text here, leave it empty when the translation is fine |
   | `comment` | Why, if it helps (a usage, a nuance) |

3. Keep what is between braces exactly as it is — `{name}`, `{n}`, `{time}`: the page puts a value there — and keep
   tags like `<a>…</a>` or `<b>…</b>` around the same words (they are the links and the bold). Move them in the
   sentence as your language needs. A correction that drops or renames one is refused, and said.
4. Commands (`sudo zenithboard …`), names (ZenithBoard, Bluesky, Tailscale, graphs1090) and menu entries of the
   terminal stay in English: the terminal and its menu are English.
5. Send the sheet back to the owner (an issue on GitHub with the file attached, or as you usually reach him). Saved
   as CSV, with commas or semicolons: both are read.

Editing it directly on GitHub (the pencil on the file) also works: it proposes the change for the owner to accept.

## Putting a corrected sheet back (the owner)

```
cp ~/Downloads/fr.csv /tmp/fr.csv                  # its name says the language: fr.csv, pt-BR.csv, zh-Hant.csv
python3 tools/i18n.py apply /tmp/fr.csv            # in a copy of the repository
python3 tools/i18n.py check fr                     # nothing missing, nothing broken
```

Before taking anything, `python3 tools/i18n.py apply /tmp/fr.csv --dry` lists each proposal beside the English and
today's translation: check each one says what the English says (a reviewer's local word for a term is welcome, a
changed meaning is not). Rows found inexact are left out with `--skip ID,ID` (their ids from the first column).

`apply` takes each row whose *correction* is filled in, applies it to the same English on the other pages too, keeps the old catalogue as `.bak`, refuses a correction that
loses a placeholder or a tag (and names the row), and writes the sheet again with the new translations. Then the usual
release: the change, its tests, a version, the PR. On the Pi: `cd ~/ZenithBoard && sudo zenithboard update quick`.

A plural row (*posts [plural: one]*) carries the whole entry in its translation column, `{"one": …}` with its quotes
doubled by the CSV. Since 0.53.4 `apply` reads those right. Before, the corrections of such rows came out ending in
`""}`, so a `--dry` that shows that is a reason to stop. A row whose *correction* is an instruction ("also fix the
sibling key…") is refused for its placeholders: it is done by hand, after reading it, or left out.

**The first review, 23 October 2026 (0.53.4).** Sheets for all 20 languages came back with 194 rows (153 with a correction):
* **149 corrections taken** after `--dry`. Most fix the case after a number (Polish, Ukrainian), the hour written
  the language's way (Japanese, Finnish, Indonesian), one term used everywhere ("callsign", "aircraft"), the menu's own
  names (Menü, menú, меню), and French's space that does not break before `: ; ? !`.
* **Left out:**
  * Chinese (Simplified) fix-1, inexact: the look-up post already reads "正在 10.7公里 高空", and the proposal lost
    "at that height".
  * Traditional Chinese fix-6, an instruction about spaces around `{what}`: waiting for a decision.
* **Done by hand, from their notes:**
  * Russian: "за последнюю {n} минуту" in both track captions;
  * Indonesian: "tanda panggil" for callsign everywhere;
  * French: "24 dernières heures" in the three places that still said "dernières 24".
* **41 rows marked *à trancher***, one reviewer out of two, with no correction filled in, were not applied at first.
  The owner chose their first proposal the same morning; it went into 0.53.5 after the same placeholder check.
  Two are plural entries (Polish's distinct aircraft on the statistics page, Swahili's posted crossings).

## For developers

* The English text is the key: in the pages' scripts every word shown goes through `t("…")` (`tn(n, "one", "other")`
  for a count), and a static page's text is marked `data-t`. A missing translation shows the English.
* Catalogues: `flightinfo/static/i18n/<lang>/console.json`, `stats.json`, `graphs.json`; the reading side is
  `flightinfo/static/i18n.js`. The posts (0.51.0): `posts.json`, read by `flightinfo/post_lang.py`. Its keys are found
  in `social.py`, `social_week.py` and `social_card.py` (`L.t("…")`, `L.tn(n, "one", "other")`, `N_("…")`). They are
  templates: `{tags}`, `{tag|cap}`, and `[parts]` left out when a tag inside is empty, kept balanced by `check`. The
  sheets list them under the page *posts*.
* What is not words comes from Unicode's CLDR through Node: `node tools/make_post_locale.js` writes
  `flightinfo/data/post-locale.json`. It holds the decimal and group signs, the day-and-month pattern, a span of days,
  the weekdays, the country names, the clock (0.52.1: `{h}.{m}` in Indonesian and Finnish) and the metric units
  (`{n} км/ч`; Arabic's metre by plural category). `tests/fixtures/plurals.json` holds the plural forms that
  `post_lang.py`'s rules are held to.
* `python3 tools/i18n.py keys` lists every key; `sync LANG` adds the new ones and drops the old; `check` says what is
  missing or broken; `review LANG` writes the sheet. A change to an English string means its translations and its
  sheet in the same commit: `tests/test_i18n.sh` fails otherwise.
* A language whose folder holds `draft.txt` is complete but not offered: the way to hold one back until it is reviewed. None is held back since 0.53.1 (Swahili was, from 0.48.0).
* The language codes are listed in five places that the tests hold together: `lib/common.sh`, `console_actions.py`,
  `i18n.js`, `tools/i18n.py`, `post_lang.py`.

More: [Translation plan](Translation-plan) · [Web console](Web-console#languages).
