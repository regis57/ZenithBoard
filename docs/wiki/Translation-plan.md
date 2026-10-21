# Translation plan (analysis)

The owner's next project (21 October 2026): the web console, the statistics page, graphs1090's page, and the Bluesky
posts and their pictures in **French, German, Dutch, Indonesian, Spanish, Portuguese (Brazil), Russian, Chinese,
Korean, Japanese and Ukrainian**, chosen at the console's first sign-in or from flags at the top; the Linux menu stays
in English. And, in the posts, **your own message** assembled with ready-made ADS-B tags. This page is the analysis
asked for first: is it feasible, what can break, what it costs the Pi. **Nothing here is built yet.**

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
* **Translations are machine-made** (by the session that builds them) and **marked unreviewed** in the language menu
  until a native speaker has read them. Aviation words (callsign, squawk, MLAT) are checked against each language's
  usage, not guessed.

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
   and in the top bar. French first: the owner reads it, so the framework is judged on a real translation.
2. **German, Spanish, Dutch, Portuguese (Brazil), Indonesian** — Latin script, nothing new to draw.
3. **The posts**: `SOCIAL_LANG`, the five post styles, the summaries and their cards, in the languages done so far;
   **your own templates and their tags**.
4. **Russian and Ukrainian** — Cyrillic in the dot font for the pictures.
5. **Japanese, Korean, Chinese** — Noto CJK for the cards on demand; the dot pictures' labels in English.

Each step its own release, previewed, its translations marked unreviewed until read by a native speaker.

## Questions for the owner

* Chinese: simplified (mainland) or traditional (Taiwan, Hong Kong), or both?
* English's flag: the United Kingdom's or the United States'?
* May the language list carry a small *unreviewed* mark until someone reads each language?
* The console's terminal output stays in English (it is the Linux side): agreed?
