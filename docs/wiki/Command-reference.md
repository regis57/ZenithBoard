# Command reference

Every `zenithboard` command, grouped by what you are trying to do. `zenithboard` on its own prints a short version of this page; `sudo zenithboard menu` opens the menus, which do the same things with questions instead of arguments.

**sudo**: commands that change something need it; commands that only look do not. The column says which.

*This page is checked by the test suite: every command the program accepts must appear here, so the table cannot quietly fall behind.*

## At a glance

| Command | sudo | What it is for |
|---|---|---|
| `zenithboard status` | | **The first thing to run when something looks wrong.** What is installed and running, the addresses that apply to your Pi, and the MLAT count (must be exactly 1) |
| `zenithboard health` | | One screen: power, temperature, memory (free of the total), SD card (how full, its size, what is free), how the previous boot ended, problems in the logs |
| `zenithboard memory` (or `threads`) | for exact figures | Memory, threads and open files, service by service, then the largest processes. Read from `/proc`; nothing changed. With sudo, memory is PSS (adds up) and open files are counted; without, RSS for other users' processes. 0.34.0 |
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
| `zenithboard graphs look zenithboard` · `original` · `status` | yes to change | 0.43.0, the default since 0.44.0 (`original` opts out): graphs1090's page and graphs in ZenithBoard's look (a black page in the wall's colour, the name in dots, links to the wall and `/stats`; the graphs drawn in matching colours), or graphs1090's own. Kept after graphs1090 updates and a new wall colour. See [Statistics](Statistics#graphs1090-in-zenithboards-look-0430-optional) |
| `zenithboard graphs on` · `off` · `status` | yes for on and off | graphs1090, off by default (0.32.0): wiedehopf's graphs of the decoder, kept for years, on port 8542. `on` runs its author's installer; `off` its uninstaller, then removes what it leaves and the packages it added (never purged: the history stays). See [Statistics](Statistics#graphs1090-years-of-the-decoders-graphs-optional) |
| `zenithboard stats gaps` | | Over thirty days: callsign prefixes shown without an airline name, and type codes drawn with the generic silhouette, each counted in distinct aircraft. Needs statistics on and the wall running. What to paste into an issue so the next airline lookup or silhouette is chosen on figures |
| `zenithboard backup make [FILE]` | yes | Everything to move to a new card, `zenithboard-backup-HOST-DATE.tar.gz` by default, mode 600: settings, what is on, statistics, posting history, graphs1090's history, kept logs, the networks' identities. Never the Bluesky app password or the console password. `--console` (what the console runs) leaves the identities out. [Backup and restore](Backup-and-restore) |
| `zenithboard backup show FILE` | | What a backup holds, from where and when, changing nothing; names the identities, never their values. Each part is read back as a restore would and its span said (samples, days, last graphs point, logs' boots); a damaged part is named and the command ends with an error |
| `zenithboard backup list [DIR]` | | The backups in DIR (by default the home folder and the current folder), newest first, with their size; the console's copy apart |
| `zenithboard backup clean [--keep N] [DIR]` | | Deletes all but the N newest backups in DIR (3, the home folder): lists them, asks you to type `delete` (`--yes` skips the question) |
| `zenithboard backup delete --console` | yes | Deletes the copy the web console keeps for download (one at a time, replaced by each new one) |
| `zenithboard backup restore FILE` | yes | Asks you to type `RESTORE`, keeps what it replaces in `/var/lib/zenithboard/before-restore-DATE/`, puts every part back, switches on again what was on, gives each network its identity now or at its installation, and lists what is left to do |
| `zenithboard settings export [FILE]` | | Your settings as one file, `zenithboard-settings-HOST-DATE.env` by default (`-` for the terminal). Never a secret: the Bluesky app password, feeder keys and passwords stay out |
| `zenithboard settings import FILE` | yes | Every setting in the file replaces the current one; lines that are not `KEY=VALUE`, or look like a secret, are skipped and counted. The file from before is kept as `config.env.bak-DATE`, importable the same way. The wall reads the new settings at once; the social service is restarted |
| `zenithboard preset list` · `add NAME key=value…` · `del NAME` | yes to change | A name for a tablet's own choices (`units radius cycle theme mode flags`), kept as `PRESET_NAME` in `config.env`. That tablet opens `http://PI:8080/?p=NAME`: the preset's keys are applied at every load, what it does not name the tablet keeps. Names: a letter then up to 15 letters or digits |
| `zenithboard social setup` | yes | The Bluesky account (an app password, never the real one), then the words and the picture. A wizard that tries the account before going on. See [Social sharing](Social-sharing) |
| `zenithboard social words` | yes | The place name the posts carry, the sharing radius, the gap between posts, the hashtags, and what is worth a post |
| `zenithboard social area [WORDS]` · `none` | yes to change | The place name the posts say, in your words: a name alone reads *above Trémery*, words with their own (*near Metz*) are kept. Letters, digits, spaces and `' - . ,`, 40 characters at most. Never the receiver's position. 0.50.0 |
| `zenithboard social radius [KM]` | yes to change | The sharing radius, whole kilometres from 1 to 200: an aircraft inside it is a candidate. Not the wall's radius. Taken by the service at its next look. 0.50.0 |
| `zenithboard social lang [CODE]` | yes to change | The posts' language: `en` (the default), or one of the web pages' languages with a catalogue (`fr`, `de`, `pt-BR`, `zh-Hant`…). Every word of the aircraft posts, your templates' and the summaries'; numbers, dates and countries as that language writes them. The pictures keep English. 0.51.0 |
| `zenithboard social template` · `tags` · `add 'TEXT'` · `del N` · `set 'TEXT'` · `set none` · `undo` · `test ['TEXT']` | yes to change | Your own post templates, one per line in `/etc/zenithboard/social-templates.txt`: `{tags}` filled for each aircraft, `[parts]` left out when a tag inside is empty. Checked when saved (an unknown tag, a `[` left open, 250 characters filled with long names); `test` fills each on an aircraft overhead now, or a sample, and posts nothing. Used when `custom` is among the words of a post. 0.51.0. `set none` deletes them all; every change keeps the file before as `.bak`, and `undo` (0.53.3) puts it back, today's becoming the `.bak` |
| `zenithboard social rules [all\|LIST]` | yes to change | What is worth a post: `all` (every crossing, the special ones first), or some of `military,helicopter,heavy,rare,farthest`. 0.50.0 |
| `zenithboard social hashtags [WORD...]` | yes to change | The hashtags ending each post: `social hashtags ADSB avgeek Moselle` (the `#` is optional — unquoted, the shell would take it for a comment), `none`, or `default`. Alone: shows them |
| `zenithboard social gap [MINUTES]` | yes to change | The least time between two posts. `0`, the default since 0.20.0, is none: every crossing of the sharing radius is posted, once. Whole minutes up to 1440; taken by the running service at its next look. Alone: shows it |
| `zenithboard social picture` | yes | The picture: dot-matrix or split-flap, its colour, the map (a wizard) |
| `zenithboard social look dotmap` · `flap` · `alternate` | yes | The dot-matrix wall with a map, the split-flap board with a map, or the two in turn (one post each). `dots` was taken out in 0.24.0 |
| `zenithboard social colour NAME` · `wall` · `rotate` | yes | amber, green, red, white, turquoise, the wall's own colour, or the colours in turn |
| `zenithboard social places on` · `off` | yes (to change) | Name the towns on the maps from the region's own list: `on` downloads GeoNames' files of the countries with a place within 400 km once (24 MB around Metz) and keeps every populated place, ranked by population or by rank where the population is unknown; `on` again makes it again (after moving the antenna); `off` deletes it and goes back to the shipped lists. Off by default. 0.27.0 |
| `zenithboard social summary` · `summary daily\|weekly\|monthly on` · `off` · `at TIME` · `parts LIST` · `test` · `post` … `post4` | yes (to change) | Summaries of the last 24 hours, the week and the last 30 days (0.38.0), each off by default, at its own time on the Pi's clock (`21:00`, `sun 19:00`, `1 09:00`; a day of the month 1 to 28) with the posts picked (`1,3` or `all`; the first always). Alone: the three, on or off, and (with sudo, 0.48.0) when each last went out and goes next, and the queue. 0.49.0: one per scheduled slot, so a time moved to later today goes today, and a time set when it has already passed (or a summary switched on after its time) goes from the next one. Several due at once share one queue, two minutes apart, the longer period first. See [Social sharing](Social-sharing#the-weeks-summary-0330-optional) |
| `zenithboard social summary why` | yes (for the state and the whole journal) | Why a summary did not go out (0.49.0): each as set, when it last went and goes next, the queue, what it needs (statistics, sharing, an account), the service and the version it runs (and whether it still runs the code from before the last update, with the restart command, 0.49.1), its journal lines about the summaries and any error over the last two days, and its starts |
| `zenithboard social weekly on` · `off` · `test` · `post` · `post2` · `post3` · `post4` | yes (on, off) | The same as `social summary weekly …` since 0.38.0. | Four posts on Sundays from 19:00, two minutes apart: the week (aircraft, messages, the busiest day and hour, the airlines and models most seen, the crossings posted, a picture of the week by hour); the cargo airlines and business jets (0.35.0); the military aircraft by country; general aviation (0.36.0). Needs statistics on; never a distance, a direction or a registration. `test` draws all four and prints the texts, posting nothing; `post` … `post4` posts that one now. Off by default. 0.33.0 |
| `zenithboard social sentence LIST` | yes (to change) | The words of a post: `factual` (as before), `story`, `board`, `spotter`, `lookup`, `custom` (your own templates, 0.51.0); several, comma-separated, or `random`, one drawn at each post. Without a value: the current choice. 0.29.0 |
| `zenithboard social photolink on` · `off` | yes (to change) | End each post with *Photo: NAME / Planespotters*, a link to the aircraft's photo page, when the wall has one. The link only, never the picture. Off by default. 0.25.0 |
| `zenithboard social units metric` · `imperial` · `wall` | yes | The posts' units, picture and text (m, km/h, km or ft, knots, mi), or the wall's own `UNITS` (the default). 0.24.3 |
| `zenithboard social map NAME` · `rotate` | yes | The map of the dotmap and flap looks: normal, night, satellite, terrain, none, or the four maps in turn |
| `zenithboard social test [HEX]` | | Draw the picture and print the text for the best candidate (or that aircraft); post nothing. The picture is at `/social/preview` |
| `zenithboard social on` · `off` · `status` | yes | Post the aircraft overhead as a picture of the wall (off by default). `on` tries the account first (0.53.7): a refused app password stops it, with what to do; Bluesky not reachable just now is said and sharing goes on, the posts waiting for the network. `off` keeps the account |
| `zenithboard social post [HEX]` | | Post now, once, whatever the gap. That aircraft then counts as posted for its crossing |
| `zenithboard social check` | yes | Try the account: open a session on Bluesky |
| `zenithboard social remove` | yes | Forget the account, stop the service, delete its state (the 30 days of history behind `rare` and `farthest`) and its map tiles. Asks you to type `remove` (0.54.9); `remove --yes` does not ask |
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
| `zenithboard adsbx-stats on` · `off` · `status` · `url` | yes for on and off | ADSB Exchange's stats package, off by default (0.52.0). It fills *Feed Details* on their [myip](https://www.adsbexchange.com/myip/) page, with their map of only the aircraft your antenna hears, viewable from anywhere, and your receiver's statistics. `on` needs ADSB Exchange's feed and runs their own script. Every 5 seconds the Pi then sends them the aircraft list their feed already gets, with its power warnings. `off` runs their uninstaller and removes the packages it added. `url` prints the link to your map, the feed's UUID in it: keep it to yourself. See [ADSB Exchange's stats](Providers#adsb-exchanges-stats-0520-optional) |

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
| `zenithboard tailscale on` | yes | 0.45.0, off by default: installs Tailscale from its own repository (pkgs.tailscale.com, checked by apt) if needed, prints a sign-in link and its QR code (your own Tailscale account; ZenithBoard never makes one), then lets the wall answer Tailscale's addresses (`ALLOW_FROM` gets `100.64.0.0/10` added) and prints the addresses to use from anywhere. No port opened. See [The menu](The-menu#tailscale) |
| `zenithboard tailscale off` | yes | Disconnects (`tailscale down`); the wall answers what it answered before. Stays installed and signed in: `on` again needs no new sign-in |
| `zenithboard tailscale status` | | Installed or not, connected or not, the Pi's Tailscale address and name, what the wall and the console answer |
| `zenithboard tailscale remove` | yes | Asks you to type `remove`: signs the Pi out (its key expires), stops Tailscale, uninstalls the package, its repository, its key and its state, when ZenithBoard installed them (one installed by hand is only signed out and stopped). Then remove the Pi from your account's machine list |
| `zenithboard tailscale console on` · `off` | yes | The web console answers Tailscale's addresses and its `*.ts.net` name too (off by default: home networks only) |
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
| `zenithboard logs decoder` · `uat` · `social` | | The last 100 lines of that service |
| `zenithboard logs adsbexchange` · `piaware` · `fr24` · `planefinder` | | The last 100 lines of that feeder's service (0.54.6: a failing feeder had no log to read); one that is not installed says so |
| `zenithboard logs usage` | | How much space the system logs take |
| `zenithboard logs review` | | Size, plus the recent warnings |
| `zenithboard logs limit MB` · `default` | yes | Cap the system logs, 10–2000 MB |
| `zenithboard logs clean` | yes | Delete all logs now |
| `zenithboard logs auto on` · `off` · `status` | yes | Daily clean-up keeping the last 7 days |

## Updating

| Command | sudo | What it is for |
|---|---|---|
| `sudo zenithboard update` | yes | **The normal way to update.** ZenithBoard first — after checking the signature on the new code, see below — then the decoder and the feeders |
| `zenithboard update quick` | yes | ZenithBoard and the wall only, in seconds: the code is pulled, the wall restarted, the feeders left as they are (no `apt`). The menu's first Update entry since 0.21.0 |
| `zenithboard update list` | | What is installed, and the names `update only` accepts |
| `zenithboard update only NAME…` | yes | Just those, e.g. `readsb flightinfo`. Names: `zenithboard readsb dump1090 adsbx piaware fr24 planefinder flightinfo graphs1090` |
| `zenithboard data update` | yes | Refresh the aircraft-model list now |
| `zenithboard data status` | | When it was last refreshed |
| `zenithboard data auto on` · `off` | yes | The monthly refresh (on by default) |
| `zenithboard data localdb on` · `off` | yes | Read registrations and models from tar1090's aircraft database on this Pi, before adsbdb and hexdb (0.26.0, off by default). Without `on`/`off`: whether it is on and tar1090's database version |

## Security and trust

The reasoning is on [Security](Security).

| Command | sudo | What it does |
|---|---|---|
| `zenithboard security` | | One screen of what this Pi does right now: who may read the wall, whether updates are verified, anything left from ACARS / Grafana, SSH, open ports, the service sandboxes, the secret files. Each WARN says how to fix it. Exit status 1 when there is one |
| `zenithboard patches on` · `off` · `status` | yes | Debian's security fixes installed by themselves, once a day, from the Debian security channel only: the feeders are left to `zenithboard update` and the Pi is never rebooted. `off` puts things back as they were |
| `zenithboard acars remove` | yes | ACARS and Grafana left ZenithBoard in 0.30.0. On a Pi where an older version installed them: stops and removes acarsdec, its ingester and database, Grafana (package, apt source, password file) and the `ACARS_*` settings, after you type the word `remove`. An update never does this by itself; `zenithboard status` and `zenithboard security` say when something is left |
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

## The web console

A test since 0.39.0, off by default: the settings from a browser or a phone on your home network, at `http://PI:8080/console`. The reasoning and the limits are on [Web console](Web-console).

| Command | sudo | What it does |
|---|---|---|
| `zenithboard console on` · `off` · `status` | yes for on and off | `on` makes its folders, installs its root helper (`zenithboard-console.path` and `.service`) and prints the address; `off` removes the helper and the pages stop answering at once, the password is kept. Menu: *7 Options → 4 Web console* |
| `zenithboard console password` | yes | Choose the console's password (asked twice, 10 characters at least, never on the command line). Kept as a scrypt hash in `/etc/zenithboard/console.env` (root:zenithboard 0640). Signs every browser and phone out |
| `zenithboard console pair` | yes | A QR code (drawn by `qrencode` when installed, dark on a white square) and its link: a phone that opens it within five minutes is signed in for 30 days. Works once |
| `zenithboard console phone-signin on` · `off` | yes for on and off | Off by default (0.40.0). On: a computer's sign-in page shows a QR code and a four-digit code; a phone already signed in to the console scans it, checks the code and says yes, and the computer is signed in without the password. Also in the console (*System → Signed in*) and the menu |
| `zenithboard console lang [CODE]` | yes to change it | The web pages' language for every browser that has not chosen its own with the flag at the top (0.47.0): `en`, `fr`; a language not translated on this Pi is refused. Without a code: the current one and those available. Also *System → Language* in the console and *7 Options → 4 Web console → 7* in the menu |
| `zenithboard console signout` | yes | Sign every browser and phone out now |
| `zenithboard console forget` | yes | `off`, then delete the password, the sessions and the record of what the console ran |

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
| `zenithboard console state` | `zenithboard-console.service` (the console's helper, as root) | after each change made from the console: the facts its overview shows |
| `zenithboard stats run` | `zenithboard-stats.timer` | 15 minutes, if statistics are on; runs as the `zenithboard` user |
| `flightinfo/social.py run` | `zenithboard-social.service` | A service, if social sharing is on: reads `aircraft.json` every 5 s, asks the wall every 15 s, posts under the rules; runs as the `zenithboard` user |
| `zenithboard ddns update` | `zenithboard-ddns.timer` | 5 minutes, if a name is set |
| `zenithboard wifi apply` | `zenithboard-wifi.service` | boot |
| `zenithboard update-components` | `zenithboard update` | update |
