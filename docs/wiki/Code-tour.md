# Code tour

About 5,000 lines in three languages, each chosen for where it has to run: shell for anything that configures a Debian machine, Python with nothing but the standard library for the server, and plain browser JavaScript with no build step for the wall.

**No dependencies to install** beyond what Raspberry Pi OS already has. That is a deliberate constraint: an installer that needs `pip install` on a Pi has one more way to fail two years from now.

## Layout

```
install.sh              the menu-driven installer (also the uninstaller)
bin/zenithboard         the whole command line
bin/zenithboard-demo    a fake sky, for working without hardware
lib/*.sh                one module per subject, sourced by both install.sh and bin/zenithboard
flightinfo/server.py    the wall's web server and all its lookups
flightinfo/static/      the wall itself: app.js, flap.js, scene.js, shapes, CSS
flightinfo/aircraft.py  reading aircraft.json
flightinfo/social.py    social sharing: the service that picks an aircraft and posts it to Bluesky
flightinfo/social_card.py  the split-flap picture with its map (Pillow)
systemd/                the unit files
tools/                  maintenance scripts (type-list refresh, demo photos, checkers), social-render.js (the dot-matrix picture)
tests/                  the whole suite
docs/wiki/              the source of this wiki
```

## The shell modules

| Module | Holds |
|---|---|
| `common.sh` | `cfg_get` / `cfg_set`, the default for every setting, the whiptail helpers (`wt_menu`, `wt_input`, `wt_msg`), validation, service checks |
| `versions.sh` | **Every pinned version and download URL**, plus `ZB_VERSION`. The one file to edit when a provider moves a file |
| `adsb.sh` | The decoder and the sharing services, the single-MLAT rule |
| `flightinfo.sh` | Installing and configuring the wall |
| `gain.sh` | The gain steps, reading `stats.json`, the advice, the 24-hour log, the menu |
| `reliability.sh` | Both watchdogs, persistent logs, the health screen |
| `patches.sh` | Debian security fixes by themselves: the one apt rule it writes, and taking it back |
| `security.sh` | `zenithboard security`: reads the running Pi, one line per fact, each WARN with its fix |
| `stats.sh` | The 15-minute statistics sample, the day files of aircraft seen, the farthest aircraft asked of the wall (`stats_farthest_sample`), pruning, and the terminal view with its sparkline |
| `network.sh` | Fixed address, DHCP, `net status` |
| `wifi.sh` | Radio, country, scan, connect, forget, the boot-time re-apply |
| `ddns.sh` | DuckDNS, No-IP, FreeDNS |
| `logs.sh` | Size, review, cap, clean, the daily clean-up |
| `uat.sh` | The optional 978 MHz receiver (United States) |
| `update.sh` | Updating everything, or one component |

Two conventions throughout: a menu's back entry is always the single word `back`, and no module reads a setting directly — it goes through `cfg_get`, so a missing key falls back to the default in `common.sh`.

## `flightinfo/server.py`

One file, read top to bottom in five parts:

1. **Config and geometry** — `load_config`, `radius_to_km`, `haversine_km`, `bearing_deg`.
2. **Building the picture** — `merge_aircraft` joins 1090 MHz and UAT, `build_planes` turns raw aircraft into what the wall shows: distance, airline from the callsign, type name, route, photo.
3. **The lookups** — `ThrottledLookup` and the route, photo and aircraft functions. See [Routes, photos and data](Routes-photos-and-data).
4. **The farthest aircraft** (0.22.0) — `FarthestTracker` keeps the day's farthest position, `farthest_watch` feeds it every five seconds while statistics are on, `nearest_city` reads `data/cities100k.tsv`, `describe_farthest` names the record with the same route check as the wall (`checked_route`), and `read_farthest` reads back what the statistics timer wrote.
5. **The server** — `Handler` serves `/`, the static files, `/api/planes` and `/api/config`. `public_config` decides what the browser is allowed to know, which is where the antenna's exact position is held back.

`VERSION` near the top must match `ZB_VERSION` in `lib/versions.sh`; a test enforces it.

## The wall's JavaScript

| File | Does |
|---|---|
| `app.js` | The grid geometry, the layout, polling, cycling, the settings panel |
| `flap.js` | The split-flap board: the letter drum and the rolling animation |
| `scene.js` | The animated sky scene and the side views, used when there is no photo |
| `shapes.js` | Aircraft seen from above, drawn as dots |
| `flags.js` | Registration prefix to country, maker to country, and the flags themselves at 11 x 7 dots. No manufacturer mark is ever drawn |
| `stats.html`, `stats.css`, `stats.js` | The `/stats` page: four headline numbers, the two farthest aircraft in words (`farthestLine`), and three charts from `/api/stats`, one series each, following the device's light or dark setting |
| `font5x7.js`, `format.js` | The dot font, and formatting numbers in metric or imperial units |

The constants at the top of `app.js` — `GW`, `GH`, `SIL_BOX`, `PHOTO_BOX` — are the layout. Change one and `tests/test_layout.js` will tell you whether the settings gear still fits. See [The wall](The-wall).

## The systemd units

| Unit | Does | When |
|---|---|---|
| `zenithboard-flightinfo.service` | The wall's server | Always |
| `zenithboard-wifi.service` | Re-applies the Wi-Fi country and on/off choice | At boot |
| `zenithboard-data-refresh.service` + `.timer` | Refreshes the aircraft-type list | Monthly |
| `zenithboard-ddns.service` + `.timer` | Updates your dynamic-DNS host | 30 s after boot, then every 5 min |
| `zenithboard-netwatch.service` + `.timer` | The network watchdog | Every 2 min, if on |
| `zenithboard-logs-clean.service` + `.timer` | Deletes log messages older than 7 days | Daily, if on |
| `zenithboard-gain-log.service` + `.timer` | One gain measurement into the 24-hour CSV | Every 15 min, if on |

The watchdog timers are `oneshot` services fired by a timer rather than long-running daemons: a crashed check cannot take the watchdog down with it, since the next tick starts a fresh one.
