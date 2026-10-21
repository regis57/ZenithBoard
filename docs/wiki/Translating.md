# Translating

Since **0.47.0** the web console, the statistics page and graphs1090's page speak more than English. This page is for
the people who read a language and want it right: **every language has a review sheet**, the English beside the
translation, with a column for your correction. No account, no tool to install, no code.

![The first visit to the console asks the language](https://raw.githubusercontent.com/regis57/ZenithBoard/main/docs/images/console-lang-first.png)

## The languages

| Language | Flag | State | Review sheet |
|---|---|---|---|
| English | United Kingdom and United States, cut along the diagonal | the reference | — |
| Français | France | translated (0.47.0) | [fr.csv](https://github.com/regis57/ZenithBoard/blob/main/docs/translations/fr.csv) |
| Deutsch, Nederlands, Italiano, Español, Português (Brasil), Bahasa Indonesia | Germany, Netherlands, Italy, Spain, Brazil, Indonesia | next | — |
| Русский, Українська | Russia, Ukraine | later (the dot pictures need Cyrillic first) | — |
| 日本語, 한국어, 简体中文, 繁體中文 | Japan, South Korea, China, Taiwan | later (the post pictures need a CJK font) | — |

A language appears in the list at the top of the pages only once it is translated. The translations are first made
by the session that builds each release, aviation words checked against each language's own use; the review sheets are
there so that someone who speaks it every day corrects them.

## Correcting a sheet

1. Open your language's sheet (the links above). On GitHub it shows as a table you can search; the **Download raw
   file** button gives the file.
2. Open it in LibreOffice Calc, Google Sheets or Excel (Excel: *Data → From Text/CSV*, file origin *UTF-8*, so the
   accents read right). The columns:

   | Column | What it is |
   |---|---|
   | `id` | The row's number, to talk about it |
   | `page` | `console`, `stats` or `graphs`; `[plural: one]` / `[plural: other]` for the forms of a count |
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

`apply` takes each row whose *correction* is filled in, keeps the old catalogue as `.bak`, refuses a correction that
loses a placeholder or a tag (and names the row), and writes the sheet again with the new translations. Then the usual
release: the change, its tests, a version, the PR. On the Pi: `cd ~/ZenithBoard && sudo zenithboard update quick`.

## For developers

* The English text is the key: in the pages' scripts every word shown goes through `t("…")` (`tn(n, "one", "other")`
  for a count), and a static page's text is marked `data-t`. A missing translation shows the English.
* Catalogues: `flightinfo/static/i18n/<lang>/console.json`, `stats.json`, `graphs.json`; the reading side is
  `flightinfo/static/i18n.js`.
* `python3 tools/i18n.py keys` lists every key; `sync LANG` adds the new ones and drops the old; `check` says what is
  missing or broken; `review LANG` writes the sheet. A change to an English string means its translations and its
  sheet in the same commit: `tests/test_i18n.sh` fails otherwise.
* The language codes are listed in four places that the tests hold together: `lib/common.sh`, `console_actions.py`,
  `i18n.js`, `tools/i18n.py`.

More: [Translation plan](Translation-plan) · [Web console](Web-console#languages).
