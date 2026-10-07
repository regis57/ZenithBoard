# Changelog

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
