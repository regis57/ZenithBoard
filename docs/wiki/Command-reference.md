# Command reference

Every `zenithboard` command, grouped by what you are trying to do. `zenithboard` on its own prints a short version of this page; `sudo zenithboard menu` opens the menus, which do the same things with questions instead of arguments.

**sudo**: commands that change something need it; commands that only look do not. The column says which.

*This page is checked by the test suite: every command the program accepts must appear here, so the table cannot quietly fall behind.*

## At a glance

| Command | sudo | What it is for |
|---|---|---|
| `zenithboard status` | | **The first thing to run when something looks wrong.** What is installed and running, the addresses that apply to your Pi, and the MLAT count (must be exactly 1) |
| `zenithboard health` | | One screen: power, temperature, memory, SD card, how the previous boot ended, problems in the logs |
| `zenithboard config` | | Every setting, as stored in `/etc/zenithboard/config.env`. Safe to paste into an issue: no secret is in it |
| `zenithboard version` | | The installed version |
| `sudo zenithboard menu` | yes | The installer menu: add or remove components, every setting |
| `zenithboard help` | | The short list |

## The wall

| Command | sudo | What it is for |
|---|---|---|
| `zenithboard units metric` · `imperial` | yes | km, km/h, m — or miles, knots, feet |
| `zenithboard radius N` | yes | How far around the antenna aircraft are shown: 1, 2, 5, 10, 15, 30 or 50, in your unit |
| `zenithboard location LAT LON [ALT_M]` | yes | Move the antenna. Writes the position **everywhere** it is stored (ZenithBoard, the decoder, the feeders) and tells you which websites to update by hand |
| `zenithboard color amber` · `green` · `red` · `white` · `turquoise` | yes | Dot colour of every wall (the dark blue was taken out in 0.23.0) |
| `zenithboard mode dots` · `flap` | yes | Dot matrix, or the airport split-flap board. Without an argument: shows the current one |
| `zenithboard cycle SECONDS` | yes | How long each aircraft stays on screen (14 by default) |
| `zenithboard stats` | | Today, yesterday, the 30-day average and best, and messages per hour as a sparkline. See [Statistics](Statistics) |
| `zenithboard stats on` · `off` · `status` | yes | Collect a sample every 15 minutes (off by default). `off` keeps the files |
| `zenithboard stats csv` · `clear` | yes for clear | The raw samples as CSV; empty them |
| `zenithboard stats gaps` | | Over thirty days: callsign prefixes shown without an airline name, and type codes drawn with the generic silhouette, each counted in distinct aircraft. Needs statistics on and the wall running. What to paste into an issue so the next airline lookup or silhouette is chosen on figures |
| `zenithboard settings export [FILE]` | | Your settings as one file, `zenithboard-settings-HOST-DATE.env` by default (`-` for the terminal). Never a secret: the Bluesky app password, feeder keys and passwords stay out |
| `zenithboard settings import FILE` | yes | Every setting in the file replaces the current one; lines that are not `KEY=VALUE`, or look like a secret, are skipped and counted. The file from before is kept as `config.env.bak-DATE`, importable the same way. The wall reads the new settings at once; the social service is restarted |
| `zenithboard preset list` · `add NAME key=value…` · `del NAME` | yes to change | A name for a tablet's own choices (`units radius cycle theme mode flags`), kept as `PRESET_NAME` in `config.env`. That tablet opens `http://PI:8080/?p=NAME`: the preset's keys are applied at every load, what it does not name the tablet keeps. Names: a letter then up to 15 letters or digits |
| `zenithboard social setup` | yes | The Bluesky account (an app password, never the real one), then the words and the picture. A wizard that tries the account before going on. See [Social sharing](Social-sharing) |
| `zenithboard social words` | yes | The place name the posts carry, the sharing radius, the gap between posts, the hashtags, and what is worth a post |
| `zenithboard social hashtags [WORD...]` | yes to change | The hashtags ending each post: `social hashtags ADSB avgeek Moselle` (the `#` is optional — unquoted, the shell would take it for a comment), `none`, or `default`. Alone: shows them |
| `zenithboard social gap [MINUTES]` | yes to change | The least time between two posts. `0`, the default since 0.20.0, is none: every crossing of the sharing radius is posted, once. Whole minutes up to 1440; taken by the running service at its next look. Alone: shows it |
| `zenithboard social picture` | yes | The picture: dot-matrix or split-flap, its colour, the map (a wizard) |
| `zenithboard social look dotmap` · `flap` · `alternate` | yes | The dot-matrix wall with a map, the split-flap board with a map, or the two in turn (one post each). `dots` was taken out in 0.24.0 |
| `zenithboard social colour NAME` · `wall` · `rotate` | yes | amber, green, red, white, turquoise, the wall's own colour, or the colours in turn |
| `zenithboard social places on` · `off` | yes (to change) | Name the towns on the maps from the region's own list: `on` downloads GeoNames' files of the countries with a place within 400 km once (24 MB around Metz) and keeps every populated place, ranked by population or by rank where the population is unknown; `on` again makes it again (after moving the antenna); `off` deletes it and goes back to the shipped lists. Off by default. 0.27.0 |
| `zenithboard social sentence LIST` | yes (to change) | The words of a post: `factual` (as before), `story`, `board`, `spotter`, `lookup`; several, comma-separated, or `random`, one drawn at each post. Without a value: the current choice. 0.29.0 |
| `zenithboard social photolink on` · `off` | yes (to change) | End each post with *Photo: NAME / Planespotters*, a link to the aircraft's photo page, when the wall has one. The link only, never the picture. Off by default. 0.25.0 |
| `zenithboard social units metric` · `imperial` · `wall` | yes | The posts' units, picture and text (m, km/h, km or ft, knots, mi), or the wall's own `UNITS` (the default). 0.24.3 |
| `zenithboard social map NAME` · `rotate` | yes | The map of the dotmap and flap looks: normal, night, satellite, terrain, none, or the four maps in turn |
| `zenithboard social test [HEX]` | | Draw the picture and print the text for the best candidate (or that aircraft); post nothing. The picture is at `/social/preview` |
| `zenithboard social on` · `off` · `status` | yes | Post the aircraft overhead as a picture of the wall (off by default). `off` keeps the account |
| `zenithboard social post [HEX]` | | Post now, once, whatever the gap. That aircraft then counts as posted for its crossing |
| `zenithboard social check` | yes | Try the account: open a session on Bluesky |
| `zenithboard social remove` | yes | Forget the account, stop the service, delete its state and its map tiles |
| `zenithboard photos on` · `off` | yes | Aircraft photos from Planespotters. Off: the animated sky scene instead |
| `zenithboard photos test [HEX]` | | Can this Pi reach Planespotters? One real request, and the answer |
| `zenithboard routes on` · `off` | yes | Origin and destination, looked up by callsign. Off: no callsign leaves the Pi |
| `zenithboard routes test [CALLSIGN]` | | Can this Pi reach adsbdb.com? One real route lookup, and the answer |
| `zenithboard config-set PORT 8090` | yes | Change the wall's port (or any other setting by name; prefer the dedicated commands, they check what you type) |

A tablet can override the colour, look, units, radius, cycle and flags for itself, with the gear or a link such as `?mode=flap&theme=green&flags=0`. See [The wall](The-wall).

## The receiver

| Command | sudo | What it is for |
|---|---|---|
| `zenithboard gain check` | | Is the gain right? Reads the decoder's last 15 minutes and gives advice |
| `zenithboard gain steps` | | The real gain steps the dongle has (29 of them, 0.0 to 49.6 dB) |
| `zenithboard gain set DB` · `max` · `default` | yes | Set the gain; snapped to the nearest real step |
| `zenithboard gain up` · `down` | yes | One step. **One at a time**, then wait 15–30 minutes |
| `zenithboard gain log on` · `off` | yes | Record one measurement every 15 minutes, keeping the last 24 hours, as a CSV table |
| `zenithboard gain log show` · `status` · `path` | | Print the table, how many measurements it holds, where the file is |
| `zenithboard gain log clear` | yes | Empty it and start again (before testing a new gain) |
| `zenithboard region world` · `us` | yes | `us` offers the optional 978 MHz UAT receiver in the menu |
| `zenithboard mlat-guard` | yes | Put the single-MLAT rule back, if a feeder update switched its own MLAT on |

How to read a day of the gain log, and why a quiet hour cannot judge the gain: [Gain tuning](Gain-tuning).

## Network

| Command | sudo | What it is for |
|---|---|---|
| `zenithboard net status` | | Saved connections, their addresses, the default route, DNS |
| `zenithboard net static IP MASK GATEWAY [DNS] [PROFILE]` | yes | A fixed address. MASK as `24` or `255.255.255.0`; DNS as `cloudflare`, `google`, `router` or `"1.1.1.1 9.9.9.9"` |
| `zenithboard net dhcp [PROFILE]` | yes | Back to an automatic address |
| `zenithboard wifi status` | | Radio, country, connection, and whether wired or Wi-Fi is preferred |
| `zenithboard wifi scan` | | Networks in range, with signal strength |
| `zenithboard wifi connect SSID [--hidden]` | yes | Save and join a network. Asks for the password; it never goes on the command line |
| `zenithboard wifi list` | | Saved networks |
| `zenithboard wifi forget SSID` | yes | Remove a saved network |
| `zenithboard wifi on` · `off` | yes | Radio on or off, kept after a reboot |
| `zenithboard wifi country XX` | yes | Regulatory country, e.g. `FR`, kept after a reboot |
| `zenithboard wifi install-nm` | yes | Install NetworkManager on a Pi that lacks it. Run with the cable plugged in |
| `zenithboard wifi harden on` · `off` · `status` | yes to change | Two settings of the saved Wi-Fi profile: `connection.autoconnect-retries 0` (keep trying to rejoin after a loss; NetworkManager stops after four tries by itself) and `802-11-wireless.powersave 2` (the radio's power saving off, a known cause of short losses on a Pi). Off by default; `on` notes the values it found, `off` puts them back. Taken at the next connection |
| `zenithboard ddns set duckdns` · `noip` · `freedns NAME` | yes | A name for your wall. Asks for the token; it never goes on the command line |
| `zenithboard ddns status` | | Provider, name, last result |
| `zenithboard ddns update` · `test` | yes | Refresh now / show exactly what the provider answers |
| `zenithboard ddns off` | yes | Stop updating the name |

## Keeping it running

| Command | sudo | What it is for |
|---|---|---|
| `zenithboard watchdog on` · `off` · `status` | on/off | The Pi's hardware watchdog: resets a frozen Pi after about 10 seconds |
| `zenithboard netwatch on` · `off` · `status` | on/off | Checks the router every 2 minutes; restarts the network, then the Pi, never more than once every 3 hours |
| `zenithboard netwatch run` | yes | One check now, by hand |
| `zenithboard keeplogs on` · `off` · `status` | on/off | Keep the system log across reboots (capped at 50 MB) |

All three are off until you turn them on. How they decide, and how to read a bad night afterwards: [Reliability and diagnostics](Reliability-and-diagnostics).

## Logs

| Command | sudo | What it is for |
|---|---|---|
| `zenithboard logs` | | The wall's own service, last 100 lines |
| `zenithboard logs decoder` · `acars` · `uat` · `social` | | The last 100 lines of that service |
| `zenithboard logs usage` | | How much space the system logs take |
| `zenithboard logs review` | | Size, plus the recent warnings |
| `zenithboard logs limit MB` · `default` | yes | Cap the system logs, 10–2000 MB |
| `zenithboard logs clean` | yes | Delete all logs now |
| `zenithboard logs auto on` · `off` · `status` | yes | Daily clean-up keeping the last 7 days |

## Updating

| Command | sudo | What it is for |
|---|---|---|
| `sudo zenithboard update` | yes | **The normal way to update.** ZenithBoard first — after checking the signature on the new code, see below — then the decoder, the feeders, ACARS and Grafana |
| `zenithboard update quick` | yes | ZenithBoard and the wall only, in seconds: the code is pulled, the wall restarted, the feeders left as they are (no `apt`). The menu's first Update entry since 0.21.0 |
| `zenithboard update list` | | What is installed, and the names `update only` accepts |
| `zenithboard update only NAME…` | yes | Just those, e.g. `readsb flightinfo`. Names: `zenithboard readsb dump1090 adsbx piaware fr24 planefinder flightinfo acars` |
| `zenithboard data update` | yes | Refresh the aircraft-model list now |
| `zenithboard data status` | | When it was last refreshed |
| `zenithboard data auto on` · `off` | yes | The monthly refresh (on by default) |
| `zenithboard data localdb on` · `off` | yes | Read registrations and models from tar1090's aircraft database on this Pi, before adsbdb and hexdb (0.26.0, off by default). Without `on`/`off`: whether it is on and tar1090's database version |

## Security and trust

The reasoning is on [Security](Security).

| Command | sudo | What it does |
|---|---|---|
| `zenithboard security` | | One screen of what this Pi does right now: who may read the wall, whether updates are verified, Grafana's password, SSH, open ports, the service sandboxes, the secret files. Each WARN says how to fix it. Exit status 1 when there is one |
| `zenithboard patches on` · `off` · `status` | yes | Debian's security fixes installed by themselves, once a day, from the Debian security channel only: the feeders are left to `zenithboard update` and the Pi is never rebooted. `off` puts things back as they were |
| `zenithboard acars password` · `new` · `set` | yes | The Grafana admin password ZenithBoard set (ACARS only): show it, draw a new one, or type your own. Kept root-only in `/etc/zenithboard/grafana.pass` |
| `zenithboard config-set ALLOW_FROM private` · `any` · `10.8.0.0/24,…` | yes | Who may read the wall: home networks only (the default), anyone, or the networks listed. See [Security](Security) |

And the things you may need to do by hand:

| What | How | What it is for |
|---|---|---|
| See what a sandbox allows | `systemd-analyze security zenithboard-flightinfo` | A score from 0 (locked down) to 10. The wall server scores about 1.3; every ZenithBoard service is under 4.5 |
| See which signing keys this Pi trusts | `sudo cat /var/lib/zenithboard/trust/signer.fpr` | One fingerprint per line |
| Trust GitHub's keys again from scratch | `sudo rm /var/lib/zenithboard/trust/signer.fpr` | The next update shows the keys and asks |
| Turn the update check off (fork, own branch) | `sudo zenithboard config-set UPDATE_VERIFY 0` | Your own commits are not signed by GitHub's key |
| Which commit is about to be installed | `git -C ~/ZenithBoard rev-parse --short origin/main` | Compare with the top commit on GitHub while the update waits for your answer |
| Are the pinned downloads still there? | `bash tools/check-links.sh` (in your clone) | The same check GitHub runs on the 1st of each month |

## Install, remove, try

| Command | sudo | What it is for |
|---|---|---|
| `sudo ./install.sh` | yes | First install, from the clone |
| `./install.sh --help` · `./install.sh --version` | no | The flags, and the version of the clone |
| `sudo /opt/zenithboard/install.sh --uninstall-all` | yes | Remove everything ZenithBoard installed. **readsb is the one exception**: it has no uninstaller, so the commands to remove it by hand are printed instead |
| `./bin/zenithboard-demo` | | A fake sky on port 8081: no dongle, no Pi needed |
| `REAL_PHOTOS=1 ./bin/zenithboard-demo` | | The same, with real photos and routes |
| `bash tools/publish-wiki.sh` | | Copy `docs/wiki/` to the GitHub wiki (maintainers) |

## Run by the system, not by you

Listed so that nothing in `ps` or the journal is a mystery. Running them by hand is harmless.

| Command | Run by | Every |
|---|---|---|
| `zenithboard gain log run` | `zenithboard-gain-log.timer` | 15 minutes, if the gain log is on |
| `zenithboard netwatch run` | `zenithboard-netwatch.timer` | 2 minutes, if the network watchdog is on |
| `zenithboard logs auto-run` | `zenithboard-logs-clean.timer` | day, if automatic cleaning is on |
| `zenithboard stats run` | `zenithboard-stats.timer` | 15 minutes, if statistics are on; runs as the `zenithboard` user |
| `flightinfo/social.py run` | `zenithboard-social.service` | A service, if social sharing is on: reads `aircraft.json` every 5 s, asks the wall every 15 s, posts under the rules; runs as the `zenithboard` user |
| `zenithboard ddns update` | `zenithboard-ddns.timer` | 5 minutes, if a name is set |
| `zenithboard wifi apply` | `zenithboard-wifi.service` | boot |
| `zenithboard update-components` | `zenithboard update` | update |
