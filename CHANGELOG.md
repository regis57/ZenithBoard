# Changelog

## 0.17.0
- **Airline names beyond the built-in list.** The route answer adsbdb gives for a callsign also names the airline, and the wall now keeps that name for the callsign's three-letter prefix: a flight of an airline outside the ninety built in is shown with its name instead of a bare callsign, from the first route lookup on, for every later flight of that airline. No new request, no new service, nothing written to disk (the names live in memory, the server stays read-only); with routes off nothing changes. The built-in list keeps priority, its names being the short ones. Corporate suffixes (`Inc.`, `AG`, `Ltd`) are dropped. Tested against a real adsbdb answer.

## 0.16.3
- **The statistics page no longer smears its left edge once an hour passes a million messages.** The vertical axis of *Messages per hour* drew a line every 10 000, which is about three hundred labels written on top of each other with 3 million messages in an hour. The step now fits the size (1, 2 or 5 times a power of ten, four to six lines), and the axis reads `1 M`, `2 M`, `20 k`; the number above the busiest bar and the tooltips stay whole. A test takes the real `ticks()` out of `stats.js`.

## 0.16.2
- `zenithboard security` recognises ports 8504 and 8978: FlightAware's SkyAware map, which `dump1090-fa` also serves there. Found on a real Pi.

## 0.16.1
Three things the first real `zenithboard security` run on a Pi showed.
- **An update now refreshes every ZenithBoard unit file the Pi has**, whatever component is being updated. The audit found `zenithboard-data-refresh` at 9.6: the unit from before the sandboxes was still in place, because only a full FlightInfo update rewrote it. Now any update replaces every unit that differs from the repository's copy, and tells systemd once.
- **Open ports are listed once each.** A service listening on IPv4 and IPv6 appeared twice.
- **The feeders' ports are recognised**: readsb's inputs and the MLAT returns (30100–31999) and Flightradar24's page (8754) are no longer "something you installed?".

## 0.16.0
- **Statistics, off by default.** `sudo zenithboard stats on`, or menu 4 → Receiver → 5, starts a timer that takes one sample every fifteen minutes: messages decoded, the farthest aircraft, aircraft with a position, and the distinct aircraft seen that day. Thirty days are kept, about 6 KB a day. It runs as the `zenithboard` user inside the same sandbox as the wall (1.0 on systemd's scale).
- **`http://PI:8080/stats`**: four numbers for today and three charts — messages per hour over 24 hours, the farthest aircraft per day, aircraft per day — one colour each, a tooltip on every bar, the same numbers as a table, light or dark with the device. No fonts or scripts from the internet. `/api/stats` gives the JSON; both say so when statistics are off.
- **`zenithboard stats`** prints today, yesterday, the thirty-day average and best, and the day's hours as a sparkline; `stats csv` the raw lines; `stats status`, `stats clear`, `stats off` (keeps the files).
- The daily aircraft count is a floor, and both views say so: a sample every fifteen minutes misses an aircraft that crossed in less. Fifteen minutes is the same trade the gain log makes between knowing and writing to the SD card.
- Tested here against a fake decoder (what one sample writes, the day's count, pruning, the terminal view), against the real server on loopback (`/api/stats` off and on), and the page in a real browser in both themes and at phone width.

## 0.15.0
Security pass, five things. Each one can be undone on its own; the last line of each entry says how.

- **The wall answers your home network only.** It used to answer anyone who could reach port 8080, which with a forwarded port meant the internet, antenna position included. It now serves the private address ranges (10/8, 172.16/12, 192.168/16, the Pi itself, link-local and their IPv6 equivalents) and gives everyone else a 403. New settings `ALLOW_FROM` (`private`, `any`, or a list of networks) and `BIND_ADDRESS`. The dynamic-DNS menu says this at the moment a name is set up. A Pi that forwarded its port on purpose will see a 403 from outside after this update: `sudo zenithboard config-set ALLOW_FROM any` restores it.
- **Every service is sandboxed.** `ddns`, `logs-clean`, `gain-log`, `netwatch` and `wifi` ran as root with no protection (9.4 on systemd's scale). They now score 1.7, 1.4, 1.0, 4.2 and 3.9, each keeping exactly what its tools need: the watchdog keeps raw sockets for `ping` and has no system-call filter, because a filter that killed `ping` would leave the Pi unwatched in silence. The gain log timer runs as the `zenithboard` user, not root. `tests/test_units.sh` measures every unit and fails when a score climbs. The DDNS status and the watchdog counter moved to `/run/zenithboard/`. Undo: `git revert` of this version's commit and `zenithboard update`; the units are reinstalled by every update.
- **Grafana no longer keeps `admin` / `admin`.** At install, and at the next update of a Pi that still accepts it, ZenithBoard sets a generated password and keeps it root-only in `/etc/zenithboard/grafana.pass`. `sudo zenithboard acars password` shows it, `password new` draws another, `password set` takes yours. Not tested against a running Grafana here; the decision, the file and its mode are. Undo: `password set` to anything you like.
- **Debian security fixes, daily, optional.** `sudo zenithboard patches on` installs `unattended-upgrades` and a rule that takes the Debian security channel only: the feeders come from other repositories and are never touched, readsb is not a package, and the Pi is never rebooted by it. Also in the Reliability menu. `patches off` removes the rule, and the package too if `on` was what installed it; a Pi that had it before keeps it as it was.
- **One GitHub release per version.** When `ZB_VERSION` changes on main, a workflow tags it and publishes that version's changelog section as the release notes. The tag is a plain tag; what is signed is the commit it points at, which is what `zenithboard update` checks.
- **`zenithboard security`.** One screen of what the Pi does right now: who may read the wall, whether updates are verified, Grafana's password, SSH password logins, the ports listening on the network, the sandbox score of each installed service, the mode of the two secret files. Each WARN names the command that closes it; exit status 1 when there is one, so a script can notice.

## 0.14.4
- README: a Beluga XL on the split-flap board, in the section about the two looks. Documentation only; nothing on the Pi changes.

## 0.14.3
- **No more bright frame around a scrolling row.** A lit dot's glow is wider than the dot itself. Repainting only the scrolling row's own rectangle left that glow outside the cleared area, and every step added more of it, until a rectangle was drawn around whichever row was moving. The repaint is now clipped to a rectangle three dots larger and redraws the dots around it, so the glow is rebuilt rather than piled up. Checked in a real browser against the real page: the frame appears in 0.14.2 and is gone here.

## 0.14.2
- **A long name now turns continuously instead of jumping back.** 0.14.0 scrolled to the end of the name, paused, then snapped to the start, which read as a stutter. The row now holds the name, a three-space gap, then the name again, and the window walks one length before starting over: what leaves on the left is already arriving on the right. `tests/test_scroll.js` takes the real drawing code out of `app.js` and walks every step of a full turn, checking each one is the previous moved exactly one dot; the old jumping version fails it.

## 0.14.1
- **Fixes the flags of 0.14.0: black was being lit.** A black band came out in the wall's colour, so Germany appeared as three bright bands instead of black, red and gold. Black is now left unlit, which is what it is on the wall and on the flag. The white outline is what makes the edge visible, and it is drawn only around a flag that actually has black in it — Germany, Belgium, Estonia, Egypt, the United Arab Emirates, South Africa, Albania. Every other flag is drawn bare. 0.14.0 outlined by brightness instead, which was the wrong rule and the wrong fix.

## 0.14.0
- **Two flags on the dot-matrix wall.** Where the aircraft is registered, beside the airline, and where it was built, beside the model. The country is read from the registration the wall already has — `OE-LMP` is Austria, `CN-` is Morocco and not Canada, longest prefix first — so there is no lookup and nothing to fetch. Eleven dots by seven, drawn into the same grid as the text, so they scale with the wall.
- **No manufacturer's logo**, in dots or otherwise: those marks are protected and a dotted copy is still a copy. The second flag shows the country the airframe is built in instead, which is not protected.
- A flag with black at its edge (Germany, Belgium, Estonia, Egypt) gets a one-dot white outline, or the black band is indistinguishable from the unlit wall.
- **Long names scroll.** The flags cost the airline and model rows two characters, twelve instead of fourteen, so a row that no longer fits moves sideways one dot at a time with a pause at each end. Only those two rows are repainted, never the whole wall.
- **An aircraft now stays on screen for fourteen seconds** instead of six, which is time enough to read a long name as it goes by. A Pi that already has `CYCLE_SECONDS` in its configuration keeps its own value.
- Flags can be switched off per tablet from the gear, or for every screen with `FLAGS=0`. The split-flap board is unchanged: it is sixteen letter drums, and a flag is not a letter.

## 0.13.1
- **The hall sound of 0.13.0 is removed.** It did not sound good enough to keep. The note beside the gear, the `zenithboard sound` command and the `SOUND` / `SOUND_VOLUME` settings are gone with it; a Pi that had them keeps the two unused lines in `/etc/zenithboard/config.env`, where they do nothing. Nothing else in 0.13.0 existed, so the wall is exactly as it was in 0.12.5.

## 0.12.5
- **Two more wall colours: turquoise (`#00d6d7`) and blue (`#0404e2`).** Both work in either display, the dot-matrix one and the split-flap one, since a wall uses one colour throughout. `zenithboard color turquoise`, or the gear on the tablet. Blue is much deeper than the other five: it reads well up close and turns into a faint navigation light from across a room, so turquoise is the safer choice for a wall meant to be read from the sofa.
- A test now checks that every colour is declared in all four places that have to agree — the shell, the server, the stylesheet and the settings menu — because a colour missing from one of them falls back to amber without saying anything.

## 0.12.4
- **Aircraft photos are back.** 0.11.1 added a check on the photo address, because the Pi fetches that address itself and it comes from somebody else's answer. The check allowed only hosts inside `planespotters.net` — but Planespotters serves its pictures from `plnspttrs.net`, a different domain from the one its API answers on. Every photo was therefore refused in silence and the wall drew its generic plane instead. Both domains are allowed now, still over https only, and the test no longer invents an address: it uses the exact one Planespotters answered with, so a check written from a guess cannot pass again.
- Every request the wall makes to an outside service now sends the same descriptive identification, naming the project, its version and the repository. One of the five (the photo download itself) sent a short form; Planespotters has started refusing requests that do not say who is asking and how to reach them.
- Running `tests/test_server.py` directly ran only the first 30 of its 49 checks: a `unittest.main()` had ended up in the middle of the file. It is at the end now. CI was unaffected — it collects the tests another way and ran all of them.

## 0.12.3
- **The update check stops asking every time.** GitHub's key file holds two keys: its old one, which expired in 2024, and the one it signs with today. 0.12.0 and 0.12.1 recorded only the first — the old one — so every update was signed by a key "not recorded on this Pi" and asked again. Now every key in the file is shown, with expired or revoked ones marked and never trusted, and all the usable ones are recorded. A Pi that recorded only the old key is asked **once** about the current one (it was in the same file you already approved), then never again. A signature from an expired key no longer counts as good either.

## 0.12.2
- Every header the wall sends now comes from a fixed table inside the program: the file type is chosen by extension from a short list, the cache rule from two allowed values, and anything else gets a safe default. 0.12.1 already removed line breaks from those values; this goes one step further, so nothing that arrives with a request or with somebody else's answer can reach a header at all. It also closes the two CodeQL alerts that the 0.12.1 fix still raised, since CodeQL could not recognise a line-break filter as a protection. Nothing changes on screen.

## 0.12.1
- **Fixes an update broken by 0.12.0.** Downloads moved to a private folder in 0.12.0, but that folder was made inside a sub-shell that deleted it again before the download could be written: `zenithboard update` then failed for readsb and ADSB Exchange with `curl: (23)`. The folder is now made once, by the command itself. Everything else in 0.12.0 was unaffected.
- **A photo's type can no longer inject anything into the wall's answers.** The image type came straight from the photo service and went into one of our response headers; a value carrying a line break could have split the reply in two. Only known image types are passed on now, anything else becomes `image/jpeg`, and no header the wall sends can contain a line break. Found by CodeQL on its first run.
- Smaller cleanups CodeQL pointed at: three silent `except` blocks now say why they are silent, four wrappers that only called another function were removed, two computed-and-never-used values are gone, and a test file is closed properly.

## 0.12.0
- **The services can now only do their own job.** The wall server and the ACARS ingester run inside a full systemd sandbox: no devices, no kernel tuning or modules, no namespaces, an empty capability set and a system-call filter. The wall server can write nowhere — it only reads. Check it with `systemd-analyze security zenithboard-flightinfo`. `acarsdec` is deliberately less restricted because it drives a USB dongle.
- **The code is checked before an update installs it.** `zenithboard update` runs `install.sh` as root, so the commit it is about to run must carry a good signature from the key you trusted. The first time it shows you GitHub's signing key and asks; after that it is silent unless something changes. A **bad** signature stops the update outright. Unsigned, or a different key, is explained and you decide — and with nobody there to answer, nothing is installed. On a fork, set `UPDATE_VERIFY=0`.
- **Downloads that are about to be run as root** no longer land on a fixed name in `/tmp`, where another user on the Pi could have created the file first. They go to a private folder made for the run. Downloads are also https-only now, and a redirection cannot drop them to plain http.
- A `SECURITY.md` so a problem can be reported privately, through GitHub, rather than in a public issue.

## 0.11.2
- **Removing readsb now says it cannot be done, instead of appearing to work.** It fetched an uninstaller that has not existed for some time, so the download failed and nothing happened. readsb is built from source by somebody else's installer and there is no way back, so ZenithBoard refuses this one out loud and prints the commands to do it by hand, rather than deleting system files it did not put there. Everything else is still removed normally. Found by the new monthly check of the download addresses, on its first run.

## 0.11.1
- **The Pi no longer follows a photo address it was given without checking it.** Photos are found at Planespotters and then fetched by the Pi itself; that address must now be `https` and inside `planespotters.net`. Before, an answer that had been tampered with could have pointed the Pi at any address on your own network and handed the result to the tablet. Nothing changes for a normal photo.
- The project's security choices are now written down: what is exposed on your network, what is checked in the code, and what is trusted because it cannot be checked (the installers from readsb, ADSB Exchange and Flightradar24, run as root). See the wiki's Security page.
- CI additions: CodeQL on every pull request, the GitHub Actions pinned to a commit instead of a tag, and a **monthly check that the pinned download addresses still answer**, which opens an issue when a provider moves a file — the 404 that otherwise only shows up during somebody's install.

## 0.11.0
- **A 24-hour gain log** (menu *4 Settings → 2 Receiver → 4 Gain → 24-hour log*, or `zenithboard gain log on|off|status|show|clear`), off until you turn it on. One measurement every 15 minutes — gain, messages, share of very strong ones, farthest aircraft, signal levels — written to `/var/lib/zenithboard/gain-log.csv` as a table a spreadsheet can open. It keeps the **last 24 hours and nothing older** (96 lines, the oldest dropped as a new one arrives), so it cannot fill the card, and `gain log clear` empties it. A single check is one moment of one day; this is what lets a gain be chosen on a full day of evidence, quiet night and busy evening side by side.

## 0.10.4
- **A wiki**: the [roadmap](https://github.com/regis57/ZenithBoard/wiki/Roadmap), what is [proven on real hardware and what is not](https://github.com/regis57/ZenithBoard/wiki/Project-status), and thirteen pages documenting the software — architecture, every setting, every command, the wall's layout, the outside services, the watchdogs, gain, a code tour, the tests and the release process. The pages are kept in `docs/wiki/` so they are reviewed like any other change, and copied to the wiki with `tools/publish-wiki.sh`.
- The README now points at those pages instead of repeating them: *Known limits* and *Contributing & tests* are shorter, and the stale "not yet validated on a real Raspberry Pi" note is replaced by the status page.

## 0.10.3
- The settings gear is now in the **bottom-right corner** (it was top-right, where a TV browser's bar slides down and hides it). It sits below the plane photo and the aircraft drawing and never covers them; the settings panel opens upward from it and scrolls on short screens. A new layout test checks this on 15 screen sizes.

## 0.10.2
- Network watchdog, for a Pi on Wi-Fi: when a check fails it now writes what the Wi-Fi sees to the log (is your saved network visible and at what signal, how many other networks are in range, the state of the Wi-Fi), on the 1st, 3rd and 5th failed check and then every 30 minutes, so the next night tells whether the router's Wi-Fi was off, the signal too weak or the Pi at fault. After about 8 minutes it also switches the Wi-Fi radio off and on and asks for the saved connection again, before the Pi is restarted (an Ethernet-only Pi is not affected).
- `zenithboard health` shows the last lines of the network watchdog when it is on.

## 0.10.1
- Gain check: the first line now shows the date and time of the check (`Checked: 2026-10-08 20:18`), so a result copied somewhere can be placed in the day (the share of strong messages changes a lot between night and rush hour).

## 0.10.0
- **Reliability** (menu *4 Settings → 5 Reliability*, and `zenithboard health|watchdog|netwatch|keeplogs`), all off until turned on: a **health check** screen (power, temperature, memory, card, how the previous boot ended, problems in the logs); **saved logs** (the system log survives a restart, capped at 50 MB); the **hardware watchdog** (restarts a frozen Pi after about 10 s); a **network watchdog** (checks the router every 2 minutes, restarts the network after about 6 minutes of failure and the Pi after about 12, never more than once every 3 hours, never in the first 10 minutes after a start). It looks at the router only, so an internet outage alone changes nothing.

## 0.9.2
- **Wrong routes are no longer shown.** The route database knows *callsigns*, not flights, and a callsign can be reused for another route or the other direction. The wall now drops an answer that cannot be this flight: the same airport as origin and destination (seen: "East Midlands → East Midlands"), an aircraft far from the line between the two airports (more than 120 km, or 20 % of the route length), or one flying away from the destination. A blank route row is better than a wrong one. The airport positions used for this check are never displayed.
- **Second opinion from hexdb.io**, only when adsbdb's answer is dropped as impossible: the callsign is asked once on [hexdb.io](https://www.hexdb.io/) (answers kept 12 h, a few requests in total, never from the display loop) and the wall takes the first leg of that route the aircraft can really be on. Airport positions are asked once each and kept until restart. If hexdb is unreachable nothing wrong is shown or remembered.

## 0.9.1
- Gain check: an "under 1 % strong messages" reading no longer reads as an invitation to raise the gain. It now says the share depends on traffic (lower at night) and to check again at a busy hour first. README wording the same.

## 0.9.0
- **Gain** (menu *4 Settings → 2 Receiver → 4 Gain*, or `zenithboard gain ...`): *Check* reads the decoder's statistics of the last 15 minutes and says whether the gain is too high (over 5 % very strong messages), good (1-5 %) or can be raised one step; *maximum*, *one step lower/higher*, *type a value* (rounded to the dongle's real steps) and *back to the default* change only the `--gain` part of the decoder options and restart the decoder. Nothing is automatic. A `--gain -10` (the dongle's own automatic gain, not the maximum) is recognised and explained.
- README: new "Gain" section; chapter 4 is now "The receiver".

## 0.8.6
- Domain name: a DuckDNS token must now look like a DuckDNS token (36 characters, 8-4-4-4-12), so a typo is caught at once instead of as a "KO" later. When DuckDNS does refuse, the status shows the sub-domain that was sent and the token length (never the token).
- New **Test** (menu Network > Name, or `sudo zenithboard ddns test`): asks DuckDNS the same thing in four ways (as the timer does, without `ip=`, IPv4 only, with another user-agent) and explains the answers, to find out why a refusal happens. The token is never shown.

## 0.8.5
- **Domain name timer fixed**: it only had a "60 s after boot" start, so when the name was set up long after boot the 5-minute refresh never started until the next reboot. It now starts 30 s after being switched on and repeats every 5 minutes.
- Domain name status says plainly when the name points to your address ("it works"), whatever older line is shown.
- Domain name: the first update right after the setup is retried up to 3 times (5 s apart) before it is reported as failed, since the network or the service can still be settling; the status line now shows the service's own short answer (`OK`, `KO`, `badauth`...), which never contains the token.

## 0.8.4
- README: badges (licence, CI, Buy Me a Coffee) and a short "Support the project" section; `.github/FUNDING.yml` adds GitHub's *Sponsor* button to the repository page, pointing to https://buymeacoffee.com/regis57.

## 0.8.3
- Menu 6 Update: after an update (everything, or the components you ticked) the menu reopens by itself on the new version. Before, it stayed on the old code until you quit and came back.

## 0.8.2
- Menus: the *Back* entry no longer repeats the word in both columns (`back  Back`); it now reads `back  Return to the previous menu`.

## 0.8.1
- Menus: one way out instead of two. A menu with a *Back* entry in its list no longer also shows a Cancel button; a plain picker (no Back entry) keeps its button, now named *Back*. Esc works everywhere. Covered by `tests/test_menus.sh`.

## 0.8.0
- **Update menu** (menu 6): *Update everything*, or *Choose what to update* with a tick list of the installed components. Command line: `zenithboard update list` and `sudo zenithboard update only readsb flightinfo ...`.
- **Settings regrouped** into four entries: *1 Network*, *2 Receiver* (region, units, antenna position), *3 ZenithBoard wall* (radius, look, colour, seconds per aircraft, photos, routes, monthly data refresh) and *4 Logs*.
- **Logs**: new *automatic cleaning* (opt-in, `zenithboard logs auto on|off`): once a day a timer removes messages older than 7 days. The ambiguous *Clean: keep the last 7 days* choice is gone; `zenithboard logs clean` now means "delete everything".

## 0.7.0
- **Settings → Network** (new sub-menu, first entry of Settings): *1 Wi-Fi* (moved here), *2 Fixed IP* and *3 Domain name*.
- **Fixed IP** (`zenithboard net static|dhcp|status`): address, subnet mask (autocompleted, `255.255.255.0` or `24`), gateway (autocompleted, checked against the network) and DNS (Cloudflare, Google, the router or your own), for the Ethernet or Wi-Fi connection you pick. Only the IPv4 address settings are written: Ethernet stays the preferred connection, Wi-Fi the fallback. Kept after a reboot; *Back to automatic (DHCP)* undoes it.
- **Domain name** (`zenithboard ddns ...`): free dynamic DNS with **DuckDNS**, **No-IP** or **FreeDNS**, refreshed every 5 minutes by a systemd timer, with a guide to get a free name, how to forward a port in the router for the wall and/or the tar1090 map, and a privacy warning. The token / key is kept in a root-only file, never on a command line.
- Settings menu reordered as a first setup would go (network, place, look, data, logs); the README is reorganised the same way and shortened.

## 0.6.0
- **Model row fixed.** The line under the airline (aircraft type + registration) stayed empty whenever the receiver's database did not know the aircraft, and the model name was never used. The wall now asks adsbdb by the aircraft's 24-bit address (same "Flight routes" on/off setting, answers cached, requests spaced) and shows the model name when it fits, else the type code and registration.
- **Split-flap look** (opt-in): an old airport board where letters roll one by one, row after row, when the wall changes aircraft. Choose it with `?mode=flap`, gear > Style, `zenithboard mode flap|dots` or menu *4 Settings > Look*. Dot matrix stays the default.

## 0.5.0
- **Wi-Fi settings** (menu 4 Settings, first entry; `zenithboard wifi ...`): on/off, country, scan with signal strength, connect with a password, hidden networks, saved networks (connect, change password, auto-connect, forget), status. Built on NetworkManager. Networks are root-only profile files joined at boot; the on/off choice and the country are saved and re-applied at every boot (`zenithboard-wifi.service`), so everything survives a crash or reboot. Ethernet stays the preferred connection (Wi-Fi route metric 600 vs 100), the menu says so, and it warns before a change that could cut an SSH session over Wi-Fi. If NetworkManager is missing, the menu offers to install it (opt-in, refuses over a Wi-Fi SSH session; `zenithboard wifi install-nm`). Passwords never appear on a command line. Written without a Pi at hand: unit-tested on throw-away files (`tests/test_wifi.sh`), not yet tried on real hardware.

## 0.4.1
- README: links to the YouTube Short, the how-to and the playlist; the "See it" section is lighter (smaller previews, two real-flight photos instead of four).
- README: a "See it" section with an animated preview, the four colours, real flights and a short video; status line updated (the installer now runs on a real Pi).
- **Aircraft photos are shown complete**, never cropped: the corner now takes the photo's own proportions (wide, standard, square or tall), as large as the space allows, anchored bottom-right, with the credit on its own line underneath instead of over the picture. Before, a fixed frame cut off tails and noses.
- README: a table of tablet links with distinct examples (units, distance in km or miles, colour, seconds per aircraft).

## 0.4.0
- **Region** is now asked first (`world` or `us`; `zenithboard region world|us`, menu *4 Settings → Region*). With `us` the installer pre-selects imperial units and offers the new **978 MHz UAT** step in menu *1 ADSB* (second dongle, FlightAware `dump978-fa` + `skyaware978`); elsewhere nothing changes. The wall merges the 978 MHz aircraft with the 1090 MHz ones (an aircraft heard on both appears once). Written without a 978 MHz setup to test the radio part; the tests cover the dongle configuration, the region logic and the list merge.
- **Logs** (optional): `zenithboard logs usage|review|limit MB|default|clean [DAYS|all]` and menu *4 Settings → Logs* to see how much the journal uses, cap it (useful on a small SD card) and clean it.
- `zenithboard logs uat`, a 978 MHz line in `zenithboard status`, README sections "978 MHz UAT" and "Logs", hardware note for three dongles.

## 0.3.2
- README: a note on position and altitude for each feeder (what is automatic, what must be edited by hand on Flightradar24 / FlightAware / Plane Finder, altitude in metres vs feet).
- **Routes now retry after 1 minute** (was 10) when adsbdb could not be reached, so a flight no longer goes without its origin/destination for most of its pass over a single network hiccup; "unknown callsign" is re-checked every 2 h (was 6 h). Failed lookups are written to the log (`zenithboard logs flightinfo`).
- New `zenithboard routes test [CALLSIGN]`: checks from the Pi that adsbdb.com can be reached and shows the route it knows.
- **Flightradar24 install made friendlier**: FR24's own sign-up wizard is used (it already asks for an existing sharing key, so there is no second prompt of ours). Before it starts, the installer prints what to answer (sharing key if you have one, MLAT no, Beast / 127.0.0.1 / 30005); afterwards Beast, `127.0.0.1:30005`, MLAT = no and no BS/raw feed are enforced in `/etc/fr24feed.ini` even if a wizard answer was wrong. If the wizard did not finish, the installer says so and how to run it again.
- Fixed the **Flightradar24 install failing** with `The repository ... is not signed` / `SHA1 is not considered secure since 2026-02-01`: Debian 13 (trixie) refuses SHA1 signatures and FR24 re-signed its repository with a new key. The installer (and `zenithboard update`) now installs FR24's 2026 key where the FR24 apt source expects it, **only when its fingerprint is exactly `ED843290A602413685E57D436F7703F65FA1BDAF`** (the key apt reports as missing), then finishes the install and the FR24 sign-up. Signature checking is never disabled, and the test suite fails if a flag such as `trusted=yes` or `--allow-unauthenticated` ever appears in the code.
- New `tests/test_fr24_key.sh` (in CI): a throw-away GPG key and a fake apt folder check the one-line and deb822 source formats, `.asc` keyrings, the default path, replacement of an old keyring, refusal of a wrong fingerprint, and failed downloads.

## 0.3.1
- Fixed the **FlightAware (piaware) install failing with a 404**: FlightAware renamed its repository package from `piaware-repository_9.0.1` to `flightaware-apt-repository_1.3` and moved it. The installer now uses the new one (older installs that already have the old package keep working) and, if the download fails again, says which file to check. dump1090-fa uses the same repository, so it was affected too.
- Fixed the **Plane Finder** package address: the pinned 5.0.162 on the old server is replaced by 5.4.211 on `client-v2.planefinder.net` (https), as published on planefinder.net.

## 0.3.0
- **Where the flight comes from and goes to** is now on the wall: two rows with the origin and, after an arrow, the destination. The airport's name is shown when it fits the 14-character column, otherwise its city; accents are folded because the dot font has none. The route is looked up from the callsign on the free community database adsbdb.com (ADS-B itself never carries it), only for airline callsigns, spaced out (one request every 1.5 s) and kept for 12 hours. Only the callsign is sent, never your position.
- New setting `zenithboard routes on|off` (also in menu *4 Settings*), shown in `zenithboard status`.
- Wall layout: heading (`HDG`), vertical speed (`V/S`) and the radius were removed to make room. The last line now has the whole width and shows the position in the cycle, the distance and the direction.
- Demo: invented routes for some aircraft (others deliberately have none); `REAL_PHOTOS=1 ./bin/zenithboard-demo` also looks up the real route of its two real airliners.
- Photo and route lookups share one throttled lookup class (single worker, retry after a refusal, daily re-check of "not found", expiry of known routes).
- README: screenshots of the first installer screens (without version number), a "Flight routes" section.

## 0.2.2
- Fixed photos appearing for only one aircraft: Planespotters answers **403 Forbidden** when it is asked too quickly, and the wall used to fire one request per aircraft at once. Lookups now go through a single worker that makes at most one request every 2 seconds.
- A refused or failed lookup is no longer remembered as "this aircraft has no photo": it is retried 10 minutes later. An aircraft with no photo published is re-checked once a day.
- `zenithboard photos test` spaces its requests out too, and explains a 403 instead of reporting it as a failure.

## 0.2.1
- The animated sky is now one continuous day: the sun and the moon travel along an arc, the colours are interpolated from the clock (dawn, midday, dusk), clouds are lit from the sun's side, high cirrus drifts past, haze sits on the horizon, and the stars fade in and twinkle at night.
- `zenithboard photos on|off` now restarts the wall, so the setting takes effect immediately (before, it was written to the configuration and ignored until the next restart).
- New `zenithboard photos test [HEX]`: checks from the Pi that Planespotters can be reached and that an image downloads, without waiting for an aircraft.
- `REAL_PHOTOS=1 ./bin/zenithboard-demo` fetches the real photos of the demo's two real airliners, so photos can be seen before the antenna is connected.
- `zenithboard status` now shows whether photos are on, and prints the local map address that is actually installed (`/tar1090/` from readsb, or `/adsbx/`) instead of always `/adsbx/`.
- Fixed "Aircraft list: not downloaded" in `zenithboard status` when run without `sudo`: `/var/lib/zenithboard` was not traversable by other users. `zenithboard update` repairs existing installs.

## 0.2.0
- New wall layout (16:10): aircraft silhouette top-right, a real Planespotters photo (with credit and link) bottom-right, airline name line, distance/direction footer.
- Silhouettes now match the real aircraft model: 15 kinds (single-aisle, wide-body, 747 hump, A380 double deck, rear-engined jets, turboprops, bizjets, light/twin piston, helicopters incl. Chinook and tilt-rotor, fighters, delta-wings, transports, bombers, gliders, balloons), including military types. Type table checked against the ICAO type list.
- No photo? The corner shows an animated sky (drifting clouds, day/dusk/night, turning propellers and rotors) with a side view of the matching model and its name.
- Airline logos removed entirely (no logo library, no `logo` command, no `SHOW_LOGOS`).
- `zenithboard update` now resynchronises its download folder when the GitHub history was rewritten (e.g. commits re-signed) instead of failing with "Diverging branches"; it says clearly when the code could not be updated and which version you stay on.
- `zenithboard update` no longer leaves root-owned files in your download folder (which made your own `git fetch` fail with "Permission denied").
- Fixed the ADSB Exchange update URL (`feed-update.sh`).
- Optional monthly refresh of the aircraft model list (tar1090-db, downloaded to the Pi only): `zenithboard data update|auto on|off|status`, settings menu toggle, systemd timer.
- Colour setting: `zenithboard color amber|green|red|white` (amber default), menu entry, per-tablet override.
- Photos are fetched by the Pi (proxy) and enabled by default for new installs. Demo has mock photos for some aircraft only, so both states show.
- Demo runs on port 8081 so it cannot clash with the real wall; README documents the ports and the ADSB Exchange local map.
- Detects low-memory (< 1.5 GB) and older Pi boards: one-time notice, ACARS marked "not recommended", warning for many feeders, memory in `zenithboard status`.
- README: "Which Raspberry Pi?" table.

## 0.1.0
- Licence changed to GPL-3.0-or-later.
- New installer menu: 1 ADSB, 2 FlightInfo, 3 ACARS, plus Settings / Status / Uninstall.
- readsb (recommended) or dump1090-fa; ADSB Exchange mandatory; FlightAware, Flightradar24, Plane Finder optional; single MLAT enforced.
- First-run questions: metric/imperial, antenna position, radius. `zenithboard` command to change them later.
- FlightInfo rewritten: dependency-free Python server, canvas dot-matrix wall with built-in 5x7 font (works offline), radius presets, units, themes, auto-cycling, self-refresh.
- ACARS: acarsdec -> filtered SQLite with 7-day rolling retention -> Grafana dashboard.
- Tests and CI.
- `zenithboard update`: one command to upgrade ZenithBoard and every installed component.
- `zenithboard location`: sets the antenna position everywhere it is stored and lists what must be changed manually.

## 0.0.1
- Initial prototype.
