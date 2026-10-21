# Translation plan (analysis)

The owner's next project (21 October 2026): the web console, the statistics page, graphs1090's page, and the Bluesky
posts and their pictures in **French, German, Dutch, Indonesian, Spanish, Portuguese (Brazil), Russian, Chinese,
Korean, Japanese and Ukrainian** (and Italian, added with the owner's answers), chosen at the console's first sign-in or from flags at the top; the Linux menu stays
in English. And, in the posts, **your own message** assembled with ready-made ADS-B tags. This page is the analysis
asked for first: is it feasible, what can break, what it costs the Pi.

**Where it stands**: the **web pages are translated** — the console, the statistics page and graphs1090's page:
French in **0.47.0**, eighteen more in **0.48.0** (Swahili translated, waiting for a native review). The language is asked at the console's first visit and
chosen from a flag at the top of every page. The **posts** (phase 3 below) are next. How to correct a language:
[Translating](Translating).

## The owner's answers (22 October 2026, 00:01)

* **Translate everything into all the languages covered**, on the console, the statistics and graphs1090, from now on:
  every new or changed English string goes into every language in the same release.
* **The translation reference is corrected when a suggestion from abroad proves inexact**: a reviewer's correction is
  checked against the English before it is taken (`tools/i18n.py apply --dry`), and one found inexact is not
  (`--skip`); a translation of ours found wrong is corrected in the catalogue and its sheet.
* **The console's first page not crowded with countries**: the browser's language and English as two buttons, every
  other language in one list.
* **More languages**: Finnish, Estonian, Latvian, Lithuanian and Polish (Latin script: with German and the others), and
  **Swahili, Arabic, Hausa and Yoruba**, except those whose translation could not reach 90%. **Hausa and Yoruba are not
  included**: Yoruba is written with tone marks on most vowels, which a machine translation gets wrong too often for a
  reader to trust, and neither has the settled technical vocabulary (settings, feeders, receiver, decoder) that the
  pages need; both can come later from a native speaker's sheet. Arabic is in. **Swahili is translated but held
  back**: its translator could not promise 90% (estimated 85 to 92%), the technical words differing between Tanzania,
  Kenya and the software glossaries; it is offered once a native speaker has reviewed its sheet.
* **A picture for a language of many countries**: Swahili shows the map of **Africa**; Arabic, spoken from Morocco to
  Iraq, shows its letter **ʿayn (ع)** rather than one country's flag. Finnish, Estonian, Latvian, Lithuanian and Polish
  their countries' flags. **Arabic is right to left**: the console's side bar, drawer and switches mirror; what the Pi
  prints, commands, numbers and the charts stay left to right; numbers in Western digits, as the Pi writes them.

## The owner's answers (21 October 2026, 23:06)

* **Chinese: both**, Simplified (`zh-Hans`, China's flag) and Traditional (`zh-Hant`, Taiwan's flag).
* **English: the two flags merged**, the United Kingdom's and the United States', cut along the diagonal.
* **No *unreviewed* mark**: instead, per language, a document with the English as the reference where people write
  their local corrections, which the owner puts back: the review sheets `docs/translations/<lang>.csv` and
  `tools/i18n.py apply` ([Translating](Translating)).
* **The terminal output stays in English**: yes.
* **Italian too.**

## In short

* **Feasible**, with three limits that are physical, not choices: graphs1090's **graph images** stay English (they are
  drawn by graphs1090's own script); the **dot-matrix and split-flap pictures** can carry accents and Cyrillic once
  their 5 × 7 font learns them, but **no Chinese, Japanese or Korean** (a 5 × 7 cell cannot draw them: their labels
  stay in English, the post's text and the summary cards are translated); the **terminal output** shown in the
  console's cards (what `zenithboard` prints) stays English, as the Linux side does.
* **Load on the Pi: negligible**, except one optional package: Chinese, Japanese and Korean summary cards need the
  Noto CJK font (61 MB to download, 91 MB on the card, +4.4 MB of memory while a card is drawn, measured), installed
  only when one of those three is chosen for the posts.
* **Regressions**: kept in check by the English text staying the key (gettext style), a test of every catalogue, and
  previews in three scripts (French, Russian, Japanese) at desk and phone width before each merge.
* **Translations are machine-made** (by the session that builds them), and **each language has a review sheet** where a
  native speaker corrects them (the owner's choice over an *unreviewed* mark). Aviation words (callsign, squawk, MLAT)
  are checked against each language's usage, not guessed.

## What is to be translated (measured, 0.45.0)

| Part | Where | Strings | Words (English) |
|---|---|---|---|
| Web console | `console.js`, `console.html`, labels in `console_actions.py`, server answers in `console.py` | about 600 | about 4 500 |
| Statistics page | `stats.js`, `stats.html` | about 80 | about 300 |
| graphs1090's page | `zenithboard.js` (its buttons and panel titles, set by script) | about 30 | about 60 |
| Posts, summaries, their pictures | `social.py`, `social_week.py`, `social_card.py` | about 300 | about 3 000 |
| **Total, per language** | | **about 1 000** | **about 8 000** |

Eleven languages: about 88 000 words to write, and to review. Country names (about 250, in the lists, the flags'
captions, the posts) come from the Unicode CLDR data the browsers carry (`Intl.DisplayNames`) on the pages, and from a
table generated once from the same data for the posts (about 60 KB for twelve languages; CLDR's licence is
permissive). Airline, model and city names are proper names and stay as they are.

## How (the design proposed)

**One catalogue per language and part**, `flightinfo/i18n/<lang>/console.json`, `stats.json`, `social.json`; the
**English text is the key**: `t("Make a backup")`. A missing translation shows the English, never a blank; the tests
grepping English strings keep working; the English page is byte for byte what it is today.

**Plurals and numbers**: the browser's `Intl.PluralRules`, `Intl.NumberFormat`, `Intl.DateTimeFormat` on the pages
(Russian and Ukrainian have three plural forms, Chinese, Japanese and Korean none); a small table of the same rules in
Python for the posts.

**Choosing the language**

* **The console's first sign-in**: a first screen before the nine first steps, the languages by their own names with
  their flag; written to the Pi as `CONSOLE_LANG` (the default for every browser) and to the browser.
* **At the top of every page** (console, statistics, graphs1090): a flag with the language's own name (*Français*,
  *Deutsch*, *日本語*), a list to change it. Flags are pictures (the flags ZenithBoard already carries), not emoji:
  Windows draws no flag emoji. A flag names a country, not a language: English shows the UK's, Portuguese Brazil's
  (as asked), Spanish Spain's, Chinese China's (simplified characters, unless the owner prefers traditional).
* **The posts**: `SOCIAL_LANG`, asked in the terminal's Bluesky set-up (`social setup`) and in the console's *Sharing*.

**Your own message, with tags** (in the posts' rotation as one more style, `custom`, beside *factual*, *story*,
*board*, *spotter*, *lookup*): one or more templates written in your words, in your language, with tags that
ZenithBoard fills in. A part between `[` and `]` is left out when one of its tags is empty. Example:

```
{flag} {airline} {flight}[, {from} → {to}] · {type}[ {registration}] at {altitude}. {why} {hashtags}
```

| Tag | Means | Example |
|---|---|---|
| `{flight}` | The flight number when known (IATA), else the callsign | `FR4512` |
| `{callsign}` | The callsign as transmitted | `RYR4512` |
| `{airline}` | The airline's name | `Ryanair` |
| `{airline_country}` | The country the airline is based in | `Ireland` / `Irlande` |
| `{flag}` | That country's flag, as an emoji (Bluesky shows it) | 🇮🇪 |
| `{registration}` | The aircraft's registration | `EI-DCL` |
| `{reg_country}` | The country it is registered in (by its address) | `Ireland` |
| `{type}` | Make and model | `Boeing 737-800` |
| `{type_code}` | ICAO type designator | `B738` |
| `{category}` | What it is: airliner, cargo, business jet, helicopter, military, light aircraft… | `airliner` |
| `{from}` · `{to}` | Departure and arrival, city and code | `Dublin (DUB)` |
| `{from_code}` · `{to_code}` | Their codes only | `DUB` |
| `{altitude}` | Altitude, in the posts' units | `11 280 m` |
| `{speed}` | Ground speed, in the posts' units | `820 km/h` |
| `{climb}` | Climbing, descending or level | `descending` |
| `{heading}` | Where it is heading, in words | `south-east` |
| `{squawk}` | Its transponder code | `7700` |
| `{why}` | Why it was posted: rare, military, heavy, the farthest… | `A rare visitor.` |
| `{area}` | The area you wrote yourself (`SOCIAL_AREA`) | `above Metz` |
| `{time}` · `{date}` | When, on the Pi's clock | `21:42` |
| `{photo}` | The Planespotters page of the aircraft (when photo links are on) | a link |
| `{tracker}` | Its page on ADSB Exchange's map | a link |
| `{hashtags}` | Your hashtags | `#avgeek` |

**No tag gives a distance, a direction from the antenna or a place near it**: the posts never give the receiver's
position away, and the templates cannot either. An unknown tag is refused when the template is saved; `sudo zenithboard
social template test` shows what the last aircraft would have given; a template longer than Bluesky's 300 characters
with plausible values is refused. Several templates rotate, in order or at random, like the styles today. Kept in
`/etc/zenithboard/social-templates.txt` (one per line, no secret in it), editable from the console's *Sharing*.

## What can break, and how it is kept from breaking

| Risk | Kept in check by |
|---|---|
| A string left in English, a translation lost when the English changes | A test lists, per catalogue, what is missing or orphaned; English is always the fallback |
| A `{placeholder}` dropped or misspelt in a translation | A test compares the placeholders of every entry with the English |
| German and Dutch about a third longer: buttons wrap, cards overflow | Previews at desk and phone width in French, Russian and Japanese before each merge; long words may break (CSS `hyphens`) |
| A post over 300 characters in a longer language | The posts' fitting (lists shortened, lines dropped) runs per language in the tests, at the longest plausible values |
| Accents and Cyrillic on the dot pictures | The 5 × 7 font gains É È À Ü Ö Ä Ñ Ç Ã Õ … and the 33 + 4 Cyrillic letters, each drawn and previewed; until then they are written without accents (as the wall does today) |
| Chinese, Japanese, Korean on the summary cards | Noto CJK, installed on demand; the card refuses to draw rather than drawing empty boxes, and says why |
| The English page changing by accident | English pages and posts compared with today's, byte for byte |
| Tests that read English strings in the code | Unchanged: the English stays in the code as the key |

## What it costs the Pi (Raspberry Pi 3B, 1 GB)

| | Cost |
|---|---|
| Disk | About 40 KB of catalogues per language, under 0.6 MB for the twelve; +91 MB only with a Chinese, Japanese or Korean post language (Noto CJK) |
| Memory, the wall's server | Nothing held: the catalogues are files the browser fetches once per page |
| Memory, the Bluesky service | One language's catalogue (about 40 KB); +4.4 MB while a CJK card is drawn (measured on a desk machine, Pillow 12) |
| CPU | Nothing measurable on the pages (the translation happens in the browser); a CJK card took 0.5 s to set its text on a desk machine, so a few seconds on the Pi 3B, once per summary |
| Network | One catalogue (about 40 KB) per page load on the home network |

## The order proposed

1. **The framework and French** — the console, the statistics page, graphs1090's page; the language at first sign-in
   and in the top bar. French first: the owner reads it, so the framework is judged on a real translation. *Done,
   0.47.0.*
2. **The pages in every other language** — German, Dutch, Italian, Spanish, Portuguese (Brazil), Polish, Finnish,
   Estonian, Latvian, Lithuanian, Indonesian, Russian, Ukrainian, Arabic (right to left), Japanese, Korean,
   Chinese (Simplified and Traditional). *Done, 0.48.0.* Swahili translated, offered after a native review.
3. **The posts**: `SOCIAL_LANG`, the five post styles, the summaries and their cards, in the languages done so far;
   **your own templates and their tags**.
4. **The dot font's letters for the pictures**: the accents of the Latin-script languages (Polish ą ę ł ś ż, the Baltic
   ā č ē ģ ī ķ ļ ņ š ū ž ė į ų, Finnish and Estonian ä ö õ…), then Cyrillic for Russian and Ukrainian. Arabic's
   pictures keep their labels in English (a 5 × 7 cell cannot join Arabic letters), like Chinese, Japanese and Korean.
5. **Japanese, Korean, Chinese (Simplified and Traditional)** — Noto CJK for the cards on demand; the dot pictures'
   labels in English.

Each step its own release, previewed, with its review sheets. Step 1 is done (0.47.0).

## What 0.47.0 measured

* **About 600 keys** for French across the three pages (console 490, statistics 90, graphs1090 25): 60 KB of catalogues,
  one fetched per page load; nothing held by the wall's server, which only lists which languages it has.
* The pages stay one script each: the console waits for its catalogue (a few KB, on the home network) before drawing;
  a missing or broken catalogue shows the page in English.
