# ZenithBoard — working rules for an AI session

Read this first. It holds what the owner (Régis, regis57) has settled over the releases; the wiki
(`docs/wiki/`) holds the rest. Nothing here is advice: each line was learnt on the real Pi.

## What this is

A Raspberry Pi that listens to ADS-B and shows the aircraft overhead on a tablet as a dot-matrix wall or a
split-flap board, feeds ADSB Exchange / FlightAware / Flightradar24 / Plane Finder, and posts the aircraft crossing a radius to Bluesky. GPL-3.0-or-later. One reference Pi: a 3B (1 GB), outdoors,
on Wi-Fi, near Trémery (Moselle). The owner tests on it; a session never reaches it.

## Language

- Code, comments, README, wiki, CHANGELOG, commit messages: **English**.
- Replies to the owner: **French** (he writes a mix; answer in French).

## Hard rules (never relax them)

- **No airline logos and no manufacturer logos**, in dots or otherwise. Country flags stand in for them.
- **Never disable package signature checking** (apt, the signed-update check). Not as a quick fix either.
- **Features are off by default** and controllable both by command and by menu.
- **Every change is reversible**: an `off` puts back what `on` found; an import keeps a `.bak`; a destructive
  step asks for a typed word.
- **Nothing ships that nobody has seen**: a new picture, shape or screen is previewed (rendered to PNG, or the
  wall screenshotted in headless Chromium) before it is merged.
- **Verify against real answers, not guesses**: a lookup, a rate limit, a hardware figure is checked on the real
  service, the real documentation or the real Pi before it is written down.
- **Secrets never land in config.env, logs or chat**: the Bluesky app password lives in
  `/etc/zenithboard/social.env` (root:zenithboard 0640). A session never creates accounts, never types a
  password or token anywhere, never edits the owner's Bluesky profile.
- **Measure before building**: a feature that depends on what the sky looks like waits for the counters
  (`zenithboard stats gaps`, the field log) rather than an assumption.
- Mastodon is gone (0.19.0) and stays gone. No paid tier, no telemetry, no cloud account.

## Feature freeze (since 25 October 2026)

The owner froze the features for 1.0: **0.99.x is the release candidate, fixes only** (a crash, a wrong figure, something
not doing what the docs say, a security or privacy hole, a mistranslation, a doc a novice cannot follow, a provider that
moved a file). A request for anything new during the freeze is **not built**: say so to the owner, in French, and write
it under *Waiting for 1.1* in `docs/wiki/Roadmap.md`. Every release is a patch of 0.99 until the owner says 1.0. What
1.0 still needs, and the hands-off clock, are in Roadmap → What 1.0 takes.

## Workflow for a change

1. `git checkout main && git pull`, then a branch named for the change.
2. Make the change **with its tests and its docs in the same commit**: README where the feature is introduced,
   `docs/wiki/*.md` for the detail (Command-reference must list every command `bin/zenithboard` accepts —
   `tests/test_docs.sh` enforces it), CHANGELOG section at the top.
3. Version bump for any behaviour change: `lib/versions.sh` (ZB_VERSION), `flightinfo/server.py` (VERSION),
   `docs/wiki/Home.md` ("Current version"), `docs/wiki/Project-status.md` (the "version" line and a field-log
   row at the top of its table when something was learnt on the Pi). Patch for a fix, minor for a feature.
4. Full local CI, all four, before pushing:
   ```
   for t in tests/*.sh; do bash $t; done
   python3 -m unittest discover -s tests
   for j in format shapes scene flap layout flags scroll statsjs i18n; do node tests/test_$j.js; done
   shellcheck -x -S warning install.sh bin/zenithboard bin/zenithboard-demo lib/*.sh tests/*.sh tools/*.sh
   ```
5. Commit as the owner: `git -c user.name=regis57 -c user.email=regis.hennequin@gmail.com commit`.
   **No `Co-authored-by`, no "Generated with" lines** — the owner's standing rule.
6. Push, open the PR with `gh api repos/regis57/ZenithBoard/pulls` (body from a file), wait for the five checks
   (CodeQL, analyze python, analyze javascript, test ×2) **and check each one's conclusion is `success`** — 0.27.0
   was merged with CodeQL failing because only "completed" was checked — then squash-merge with
   `gh api -X PUT .../pulls/N/merge -f merge_method=squash -f sha=…`. Check `commits/main` is verified and
   `releases/latest` carries the new tag (the release workflow tags `v<version>` by itself).
7. Sync the wiki: GitHub's wiki is a separate repository; `docs/wiki/*.md` is the source. From the owner's
   Chrome (a new tab, never his Pi tab at `192.168.1.196:8080`), for each changed page: fetch the raw file from
   `raw.githubusercontent.com/regis57/ZenithBoard/main/docs/wiki/NAME.md`, fetch `/wiki/NAME/_edit`, POST the
   form with `wiki[body]`, `wiki[format]=markdown`, `wiki[commit]`, and verify the stored body equals the file.
   A new page goes through `/wiki/_new` first. Without his browser, say the wiki is not synced.
8. **Documentation after every change, without being asked** (the owner's standing rule, 20 October 2026):
   README, `docs/wiki/*.md`, CHANGELOG, the field log in Project-status (what the owner's paste or recording
   showed), and the pictures in `docs/images/` when what they show has changed, then the wiki sync of step 7.
   A doc-only change goes through the same PR and checks, with no version bump. Report the pages updated.
9. Tell the owner, in French, what changed and, when the Pi needs it, the command:
   `cd ~/ZenithBoard && sudo zenithboard update` (or `sudo zenithboard update quick` for ZenithBoard and the
   wall alone). A config value the owner set is never changed by an update: the update says so and gives the command.

## Layout

- `install.sh` — the menu; `bin/zenithboard` — the command; `lib/*.sh` — one file per subject (social, stats,
  settings, wifi, update…); `flightinfo/server.py` — the wall's server; `flightinfo/static/app.js` — the
  128×80 dot wall; `format.js` the row text; `flags.js`, `shapes.js`; `flightinfo/social.py` — the Bluesky
  service; `tools/social-render.js` — the dots picture; `flightinfo/social_card.py` — the split-flap picture.
- Tests run against stand-ins (stubs for systemctl, nmcli, apt, Bluesky, the wall): a green suite proves the
  logic, never the hardware. `docs/wiki/Project-status.md` says what has run on the real Pi.
- The owner shares his Pi by pasting `zenithboard health`, `sudo zenithboard social status`,
  `zenithboard logs social | tail`, screenshots and screen recordings. Read them fully before changing anything;
  a log line that contradicts a claim already made is corrected in CHANGELOG and told to him.

## Style

- Comments say why, in plain sentences, and name the release that introduced the line when it answers a
  finding ("seen on the real Pi, 0.19.2"). No decorative comments.
- Menus: every menu has exactly one way out (`tests/test_menus.sh`). Destructive steps are never the last
  entry before Exit.
- Posts and the wall never give the receiver's position away.
- The web pages are translated (0.47.0; 20 languages since 0.48.0, 21 with Swahili since 0.53.1, 22 with Hindi since 0.55.0): a word shown goes through `t("…")` (static HTML:
  `data-t`), the English is the key. **The owner's rule (22 October 2026): every new or changed English string on the
  console, `/stats` or graphs1090's page is translated into every language in the same commit** — `python3 tools/i18n.py
  sync LANG`, translate, `review LANG`, `check` (`tests/test_i18n.sh` fails otherwise). A reviewer's correction is
  checked against the English before it goes in (`apply FILE --dry`); an inexact one is left out (`--skip ID`) and a
  translation of ours found wrong is corrected in the catalogue and its sheet. The terminal, the menu and what the Pi
  prints stay English. Hausa and Yoruba were left out (90% not reachable); Swahili was held back
  (`i18n/<lang>/draft.txt`, the mechanism kept) and published by the owner on 22 October 2026 without a native review; Hindi was
  added at the owner's request on 25 October 2026, also without a native review (Tamil and Urdu wait for one);
  Arabic is right to left.
