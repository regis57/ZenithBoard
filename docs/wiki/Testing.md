# Testing

The suite answers one question: *does this behave the same after the change?* It cannot answer *does this work on a Raspberry Pi* — nothing here touches real hardware — so a green run and [Project status](Project-status) are two different promises.

No test framework is installed. Python uses `unittest` from the standard library; the shell and Node tests are plain scripts that exit non-zero on failure.

## Run everything

Exactly what CI runs:

```bash
shellcheck -x -S warning install.sh bin/zenithboard bin/zenithboard-demo lib/*.sh tests/*.sh tools/*.sh
python3 -m unittest discover -s tests -v
for t in tests/test_*.sh; do bash "$t" || echo "FAIL $t"; done
for t in tests/test_*.js; do node "$t" || echo "FAIL $t"; done
for f in flightinfo/static/*.js tools/*.js tools/graphs1090-look/*.js; do node --check "$f" || echo "FAIL $f"; done
```

Run the whole set before pushing. It takes about a minute and a half on a laptop, and the shell tests are the ones that catch the
expensive mistakes. The split-flap pictures' tests need Pillow and its font, or they are skipped: `sudo apt install python3-pil
fonts-dejavu-core` (CI installs them).

## What covers what

| Test | Covers |
|---|---|
| `test_server.py` | Route plausibility, the hexdb second opinion and its cache, the lookup queue and cache when full, what `build_planes` shows, `/api/planes` with a radius or a setting that is not a finite number |
| `test_aircraft.py` | Reading `aircraft.json`, merging 1090 MHz with UAT |
| `test_legacy.sh` | 0.30.0: what an older ZenithBoard left of ACARS and Grafana is found, said by status and update (never removed by an update), removed by `acars remove` after the typed word; no menu or command offers ACARS any more |
| `test_update_types.py` | The monthly aircraft-type refresh |
| `test_gain.sh` | The real gain steps, editing `RECEIVER_OPTIONS`, reading `stats.json`, the advice, the 24-hour log and its pruning |
| `test_reliability.sh` | Both watchdogs, the netwatch decisions, the Wi-Fi diagnosis and reset, the health screen |
| `test_network.sh` | Fixed address and DHCP |
| `test_wifi.sh` | Radio, country, scan, connect, forget |
| `test_logs_uat.sh` | Log size, caps, clean-up; the UAT step |
| `test_hardware.sh` | Pi model detection and the warnings for the tighter models |
| `test_update_sync.sh`, `test_versions.sh` | That the updater knows every component, that every unit file is refreshed, that the wall is asked which version it is actually running and restarted when it is behind, and that the version numbers agree (`lib/versions.sh`, the server, `Home.md`, `Project-status.md`: 0.54.1; before, only the shape of the number was checked) |
| `test_fr24_key.sh` | The Flightradar24 signing key, by fingerprint |
| `test_radarbox.sh` | AirNav Radar (0.99.6): its key by fingerprint and a refused repository leaving nothing, `rbfeeder.ini` written section by section with MLAT off, the MLAT guard, the sharing key kept by a backup, a restore and a removal, the position |
| `test_telegram.py`, `test_telegram.sh` | Telegram (0.99.6): the squawk rule (two reads, the aircraft's own status, once per flight and code, anywhere in range), one message per crossing and the rules, the words in the messages' language and never the receiver, the pacing and Telegram's answers (429, a supergroup, a token never in an error) against a stand-in for its Bot API; the token's file, on and off, each setting, the templates and their .bak, the console's actions, the unit's sandbox |
| `test_menus.sh` | Every menu has exactly one `back` entry and no dead item |
| `test_i18n.sh` | The pages' languages (0.47.0): every shipped catalogue complete and in the English's shape, the language codes the same everywhere, the review sheets current, a reviewer's corrections applied (a broken one refused), `console lang`, graphs1090's copy put and taken away exactly |
| `test_install.sh` | `install.sh` run as a newcomer runs it, against a whiptail that answers from a script and records every screen: the flags, the first-run wizard from a blank settings file to the main menu, a bad latitude or altitude asked again, the hardware notice once, a clear stop when whiptail cannot be installed, no error on a machine that is not a Pi, the five colours and the six settings groups the README names |
| `test_format.js` | Formatting and unit conversion on the wall |
| `test_shapes.js`, `test_scene.js`, `test_flap.js` | Silhouettes, the animated scene, the split-flap board |
| `test_settings.sh` | Settings export never carries a secret, import takes only `KEY=VALUE` and keeps a way back; preset names, keys and what the wall serves; Wi-Fi hardening sets two things and `off` puts them back (against an `nmcli` stub); the `stats gaps` counters against a wall stub on the loopback; the typed word before each destructive menu step |
| `test_social.py`, `test_social.sh` | The posts' words for every case (the altitude never read as a distance), the choice under the rules, the track memory, both real renderers — Node's PNG with its labelled rows and the wall's colours, Pillow's split-flap JPEG with fake map tiles, the tile address, cache and fallbacks — the exact requests sent to Bluesky (against fakes shaped like the real answers), the secrets file's mode and contents, the 0.19.0 clean-up of a Mastodon token, the picture settings, on/off/remove, and the audit's line |
| `test_statsjs.js` | The statistics charts' axis: a handful of round lines whatever the size, from ten to billions of messages; the farthest aircraft's line, with each part left out when it is not known, in English and in French |
| `test_post_lang.py` | The posts' language (0.51.0): the plural rules against Node's Intl for every language, numbers, dates, countries, the clock and the metric units as CLDR writes them (0.52.1: pukul 13.50, 839 км/ч, Arabic's metre by the count; English unchanged), the templates' `[parts]`, filters and French elision, the owner's templates checked, and every shipped catalogue turned into real posts and summaries that fit and leave nothing unfilled |
| `test_i18n.js` | The pages' translation (0.47.0): English as key and fallback, placeholders, French and Russian plurals, decimals, the browser's language at the first visit, every word the console asks for in the French catalogue |
| `test_server.py` → `FarthestTest`, `test_stats.sh` | The farthest aircraft (0.22.0): what the watch keeps and ignores, the nearest city against GeoNames' real positions (Luxembourg-City's nearest of 100 000 is Trier), no district and no position in what is written, the route check, the timer waiting for a route on its way, never replacing a farther record, pruning |
| `test_layout.js` | The settings gear clears the photo and the silhouette on 15 screen sizes |
| `test_poll.js` | How the wall talks to the Pi (0.99.17): the whole of `app.js` run against a stand-in page, clock and `fetch`. A Pi that hangs: one request out at a time, each given up after five seconds, NO ANSWER after the third; a name the Pi refuses (403): WRONG NAME on the dots and the flaps, no reload, no failure counted; the ALLOW_FROM refusal still a failure; an error from `/api/config` leaves the defaults; every screen's words fit 128 dots and 16 flaps, in letters the font and the flaps have |
| `test_update_verify.sh` | The update's signature check: the whole decision table, real expired and current gpg keys, the one-time question for older installs, and that the private download folder outlives the sub-shell that asked for it |
| `test_console.py`, `test_console.sh` | The web console (0.39.0): the fixed list refuses anything else (shell characters, ranges, unknown actions); scrypt; home networks only and the Host check against DNS rebinding; the sign-in limits, also for a burst sent at once (0.99.10: five tries, two hashes at a time, *Busy* not counted); sessions kept as hashes, their lifetimes, a sign-out for everyone; a pairing code working once, and refused once its maker is signed out, revoked or older than a sign-out for everyone, like a yes to a computer (0.99.10); every request path (cookie flags, the CSRF header, the origin, JSON only); the root helper against a stand-in command, with forged, oversized and linked job files ignored; `console password`, `on`, `off`, `pair`, `forget` |
| `test_adsbx_stats.sh` | ADSB Exchange's stats (0.52.0): refused without the feed; their script from the pinned address; exactly the packages it added noted (one removed earlier with its settings left is not counted as there) and removed by `off`, unless something now needs one; the video group put back; the UUID kept; a copy installed by hand removed without touching a package; a link in `/tmp` never followed; only a real UUID makes a link; removing ADSB Exchange takes the stats first; `on`, `status` and the update never print the UUID (theirs hidden), health hides it; what `off` could not put back (apt busy, the group refused) kept for the next `off`; graphs1090's shared packages left; one package installer at a time |
| `test_console.py` → `AppTest` | The console as an app (0.53.0): the manifest meets Chrome's install criteria (name, standalone, start inside its scope, 192, 512 and maskable PNG icons of the sizes they say), the page links it, the service worker caches nothing and registers only over https, the files served with their types and the console's headers. Checked in Chromium too: no installability error on a secure address |
| `test_docs.sh` | Every command the program accepts, and every line of its help, appears on the [Command reference](Command-reference) page |

## The two patterns

Almost every shell test rests on one of these. Learn them and the suite stops being mysterious.

**1. Stub programs on `PATH`.** The code under test calls `systemctl`, `nmcli`, `ping`, `ip`, `logger`, `vcgencmd`, `journalctl`. The test writes a fake one of each into a temporary directory, puts that directory first on `PATH`, and has it print whatever the scenario needs. Nothing real is called, and the test can then assert which commands were attempted.

```bash
mk_stub nmcli 'echo "wifi connected MyNetwork"'
PATH="$STUB_DIR:$PATH"
```

**2. Environment overrides for every path.** No module hard-codes a system path. Each one reads an override first, so a test can point it at a temporary directory:

`ZB_SYSTEMD_CONF_DIR`, `ZB_JOURNALD_DIR`, `ZB_RUN_DIR`, `ZB_VAR_DIR`, `ZB_JOURNAL_DIR`, `ZB_WATCHDOG_DEV`, `ZB_UPTIME_FILE`, `ZB_NETWATCH_SLEEP`, `ZB_DEFAULT_DIR`, `ZB_STATS_DIR`, `ZB_PI_MODEL_FILE`, and for the installer as a whole `ZENITHBOARD_ETC`, `ZENITHBOARD_HOME` and `ZENITHBOARD_BIN_DIR` (the settings folder, `/opt/zenithboard` and where the `zenithboard` command is linked).

`ZB_NETWATCH_SLEEP=0` is the one that makes testing a watchdog bearable: a test for the 12-minute reboot decision runs instantly.

## Adding a test

Copy the nearest existing file; they all share a shape. A shell test sets up a temporary directory and its stubs, sources the module, runs a case, compares against an expected string, and counts failures. Keep each case's name on the same line as its command — a missing space there produces an unbound-variable error that looks like a bug in the module rather than in the test.

Then add the file to `.github/workflows/ci.yml`. It is a list, not a glob, on purpose: a new test is visible in the diff. `tests/test_docs.sh` fails for any `tests/test_*.sh` or `tests/test_*.js` that the list leaves out, so forgetting this step is caught (0.53.6; five suites had gone unrun in CI since 0.39.0).

## What else runs in CI

Beyond the suite: **CodeQL** (Python and JavaScript, on every pull request and weekly), and a **monthly check of the pinned download addresses** (`tools/check-links.sh`, which you can also run by hand) that opens an issue when a provider moves a file. The reasoning behind those, and the tools deliberately not used, is on the [Security](Security) page.

## A note on shellcheck

It runs at `-S warning` with `-x` so it follows `source`. Two codes come up often when a shell array and a plain variable share a name, SC2178 and SC2128. The fix is a different name, not a suppression comment.
