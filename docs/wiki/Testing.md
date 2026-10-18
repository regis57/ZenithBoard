# Testing

The suite answers one question: *does this behave the same after the change?* It cannot answer *does this work on a Raspberry Pi* — nothing here touches real hardware — so a green run and [Project status](Project-status) are two different promises.

No test framework is installed. Python uses `unittest` from the standard library; the shell and Node tests are plain scripts that exit non-zero on failure.

## Run everything

Exactly what CI runs:

```bash
shellcheck -x -S warning install.sh bin/zenithboard bin/run-acarsdec bin/zenithboard-demo lib/*.sh tests/*.sh
python3 -m unittest discover -s tests -v
for t in tests/test_*.sh; do bash "$t" || echo "FAIL $t"; done
for t in tests/test_*.js; do node "$t" || echo "FAIL $t"; done
```

Run the whole set before pushing. It takes well under a minute, and the shell tests are the ones that catch the expensive mistakes.

## What covers what

| Test | Covers |
|---|---|
| `test_server.py` | Route plausibility, the hexdb second opinion and its cache, what `build_planes` shows |
| `test_aircraft.py` | Reading `aircraft.json`, merging 1090 MHz with UAT |
| `test_acars.py` | The ingester: filtering, storing, retention |
| `test_update_types.py` | The monthly aircraft-type refresh |
| `test_gain.sh` | The real gain steps, editing `RECEIVER_OPTIONS`, reading `stats.json`, the advice, the 24-hour log and its pruning |
| `test_reliability.sh` | Both watchdogs, the netwatch decisions, the Wi-Fi diagnosis and reset, the health screen |
| `test_network.sh` | Fixed address and DHCP |
| `test_wifi.sh` | Radio, country, scan, connect, forget |
| `test_logs_uat.sh` | Log size, caps, clean-up; the UAT step |
| `test_hardware.sh` | Pi model detection and the warnings for the tighter models |
| `test_update_sync.sh`, `test_versions.sh` | That the updater knows every component, that every unit file is refreshed, that the wall is asked which version it is actually running and restarted when it is behind, and that the two version numbers agree |
| `test_fr24_key.sh` | The Flightradar24 signing key, by fingerprint |
| `test_menus.sh` | Every menu has exactly one `back` entry and no dead item |
| `test_install.sh` | `install.sh` run as a newcomer runs it, against a whiptail that answers from a script and records every screen: the flags, the first-run wizard from a blank settings file to the main menu, a bad latitude or altitude asked again, the hardware notice once, a clear stop when whiptail cannot be installed, no error on a machine that is not a Pi, the six colours and the six settings groups the README names |
| `test_format.js` | Formatting and unit conversion on the wall |
| `test_shapes.js`, `test_scene.js`, `test_flap.js` | Silhouettes, the animated scene, the split-flap board |
| `test_settings.sh` | Settings export never carries a secret, import takes only `KEY=VALUE` and keeps a way back; preset names, keys and what the wall serves; Wi-Fi hardening sets two things and `off` puts them back (against an `nmcli` stub); the `stats gaps` counters against a wall stub on the loopback; the typed word before each destructive menu step |
| `test_social.py`, `test_social.sh` | The posts' words for every case (the altitude never read as a distance), the choice under the rules, the track memory, both real renderers — Node's PNG with its labelled rows and the wall's colours, Pillow's split-flap JPEG with fake map tiles, the tile address, cache and fallbacks — the exact requests sent to Bluesky (against fakes shaped like the real answers), the secrets file's mode and contents, the 0.19.0 clean-up of a Mastodon token, the picture settings, on/off/remove, and the audit's line |
| `test_statsjs.js` | The statistics charts' axis: a handful of round lines whatever the size, from ten to billions of messages; the farthest aircraft's line, with each part left out when it is not known |
| `test_server.py` → `FarthestTest`, `test_stats.sh` | The farthest aircraft (0.22.0): what the watch keeps and ignores, the nearest city against GeoNames' real positions (Luxembourg-City's nearest of 100 000 is Trier), no district and no position in what is written, the route check, the timer waiting for a route on its way, never replacing a farther record, pruning |
| `test_layout.js` | The settings gear clears the photo and the silhouette on 15 screen sizes |
| `test_update_verify.sh` | The update's signature check: the whole decision table, real expired and current gpg keys, the one-time question for older installs, and that the private download folder outlives the sub-shell that asked for it |
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

Then add the file to `.github/workflows/ci.yml`. It is a list, not a glob, on purpose: a new test is visible in the diff.

## What else runs in CI

Beyond the suite: **CodeQL** (Python and JavaScript, on every pull request and weekly), and a **monthly check of the pinned download addresses** (`tools/check-links.sh`, which you can also run by hand) that opens an issue when a provider moves a file. The reasoning behind those, and the tools deliberately not used, is on the [Security](Security) page.

## A note on shellcheck

It runs at `-S warning` with `-x` so it follows `source`. Two codes come up often when a shell array and a plain variable share a name, SC2178 and SC2128. The fix is a different name, not a suppression comment.
