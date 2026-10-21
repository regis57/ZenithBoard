# Roadmap

No dates. ZenithBoard is a spare-time project and a date would be a fiction. What this page promises is an order: the *Now* list is what is actually being worked on, and nothing from *Later* starts before *Now* is empty.

## Now — prove it on real hardware

The code is complete enough. What it lacks is proof.

| Item | Why it is here | How it ends |
|---|---|---|
| ~~Try Plane Finder~~ | Done 20 October 2026: the reference Pi feeds it beside ADSB Exchange, FlightAware and Flightradar24, 27 MB of memory ([Hardware](Hardware)) | Closed |
| **Watch the first real summaries** | 0.33.0 to 0.38.0 added the summaries: the day, the week (Sunday 19:00 by default) and the last 30 days, four posts each (the period; cargo and business jets; military; general aviation), in one queue two minutes apart. `social weekly test` ran on the Pi on 20 October; the first daily summary went out on 21 October at 09:20, post 1 only (0.40.4 fixed the lists; the four posts then went out by hand). With 0.40.4's half rule the airlines, models and posts 2 to 4 join the weekly summary from 25 October | The first weekly post on Sunday 25 October read on a phone; the first one with all four posts on 1 November; a field-log row for each, a fix for anything odd |
| **graphs1090 on the reference Pi** | Optional since 0.32.0; its installer was read in full, never run here | `sudo zenithboard graphs on`, then `zenithboard graphs status` (collectd's memory, the size in `/run`) pasted for the field log — or `graphs off` and a note |
| **The statistics page on a Pi 3B** | 0.37.0's look and period toggle were approved on the real page; its cost was measured on a desk machine only (0.14 s for thirty days), the last 24 hours' lists fill from 0.37.0's last-seen column | A toggle through 24 h, 7 days and 30 days on the Pi with `sudo zenithboard memory` before and after; a field-log row |
| Watch the Debian patches | Switched on 18 October 2026 from the menu | A few weeks without a feeder disturbed |
| **Count what the wall cannot name or draw** | Two *Later* items — airline names for bare callsigns, more silhouettes — wait on real figures, not guesses. Since 0.21.0 the statistics sampler notes, every quarter hour, each aircraft shown with a callsign but no airline (by its three-letter prefix) and each one drawn with the generic silhouette (by type code). `zenithboard stats on` must be on | After two weeks, `zenithboard stats gaps` pasted into an issue decides which prefixes get a lookup and which shapes get drawn |
| Watch the first weeks of the posts | Since 0.23.0 the Bluesky posts carry a real map with the track (`dotmap` and `flap`, alternating), town names on every map (satellite and terrain 0.24.4, smaller and more of them 0.25.2, over the track and on the OpenStreetMap maps 0.25.3), the photographer's name as a link to the aircraft's Planespotters page if `social photolink on` (0.25.0), and units of their own (0.24.3). Looked at so far on the real Pi: the normal and terrain maps, the satellite map once | A few posts on each map (normal, night, satellite, terrain) read on a phone: legible names, credits in place, nothing hidden by the legend. Anything else is a field-log row and a fix |
| Leave the gain alone | Settled at 48.0 dB, 4–5 % strong messages at rush hour | Nothing to do. Recorded so it is not re-opened |

## Deciding the airline lookup and the new silhouettes on figures

Two *Later* items are to be built from what the reference Pi measures, not from guesses. Statistics were switched on there on 18 October 2026; the figures are read on **17 November 2026** with `zenithboard stats gaps`, and this is the procedure, written down so it does not depend on anyone's memory.

**What is being counted.** With statistics on, every quarter hour the sampler asks the wall which aircraft are inside its radius and notes, once per aircraft over thirty days: the three-letter callsign prefix of each aircraft shown with a callsign but no airline name, and the type code of each aircraft drawn with the generic silhouette. `zenithboard stats gaps` prints both lists, most frequent first.

**2. Airline names for callsigns without a route**

1. Read the prefix list. A prefix seen on fewer than three aircraft in thirty days is noise. If no prefix passes that bar, the item is closed: the route lookup already names what matters.
2. Otherwise, one lookup per prefix, not per flight: the ICAO airline designator (`EZY`, `BGA`) asked once of adsbdb's airline endpoint if it answers by designator, or taken from an open designator list shipped with the wall if it does not; the answer cached for months in the wall's cache folder, like routes. Off by default, a line in the wall settings menu, `zenithboard config-set AIRLINE_LOOKUP 1`.
3. Checked against the real answers for the prefixes in the list before it ships, like the route filter was.

**3. More silhouettes**

1. Read the type-code list. The five to ten most frequent codes get a shape each; the rest keep the generic one.
2. Each shape is drawn in `flightinfo/static/shapes.js` with the primitives already there, previewed as a picture here, and shipped only once it has been seen — the rule for everything on the wall.
3. `aircraft.classify` maps the code to the new shape; `tests/test_shapes.js` holds the mapping so a code cannot quietly fall back to generic again.

**If the figures never come** (the Pi was off, statistics were switched off), the two items stay in *Later* as they are. Nothing is built on a guess.

## What 1.0 takes

1.0 means *validated on real hardware, no caveats in [Project status](Project-status)* ([Release process](Release-process)). Each open caveat ends one way or the other:

| Caveat today | What lifts it |
|---|---|
| ~~Plane Finder never fed~~ | Lifted 20 October 2026: feeding from the reference Pi |
| graphs1090 never run on a Pi (optional, 0.32.0) | Run on the reference Pi — or marked *optional, not verified*, so it stops being a caveat |
| The summaries never posted by the service | The first scheduled weekly and monthly posts seen on Bluesky |
| A fixed IP address never applied for real | `zenithboard net static …` on the reference Pi, then back to DHCP, with a keyboard and screen at hand |
| 978 MHz UAT (United States) | Run by a US user — or marked *experimental, outside 1.0*, so it stops being a caveat |

And three proofs of stability that no caveat names yet:

* **Two to four weeks hands-off**, social sharing on: no crash in `zenithboard logs`, no reboot forced by a watchdog.
* **A fresh install** on a blank card, following the wiki's [Fresh install](Fresh-install) alone, step by step, **and finished from the web console** (the owner's criterion, 21 October 2026: its checklist ticked line by line; a line that needed anything not written there is a fix to the page and a new try). Everything so far was proven on a Pi upgraded release after release; only a fresh install proves the README. Since 0.21.1 the installer is walked end to end against stand-ins at every change (`tests/test_install.sh`: flags, wizard, menus), which found a handful of small things, fixed in that release; the blank card itself is what remains.
* **An update from an old release** (0.19 to the latest, say) with nothing done by hand.

## Next — once the above is proven

* **Translations** (the owner, 21 October 2026): the web console, the statistics page, graphs1090's page and the posts in eleven languages, chosen at the first sign-in or from flags at the top, and the posts' own templates with ready-made tags. Analysed first, as asked: [Translation plan](Translation-plan) — feasible, light on the Pi, five steps (the framework and French; the Latin-script languages; the posts and their tags; Cyrillic; Chinese, Japanese, Korean). Waiting on the owner's answers to its four questions.

* **Posts, small things that may come:** the town names are drawn from a list of places of 5 000 inhabitants or more, and villages of 1 000 or more fill in on a map with fewer than three (0.26.2); a region sparser still may want a lower threshold (`tools/make_places.py`). The farthest aircraft of the month is named only from 0.22.0 on; earlier days have a figure and no line.
* ~~Enrich the statistics page~~ — done: the sky by hour, airlines, models and altitudes (0.31.0); cargo, business jets, military and general aviation with flags, ZenithBoard's own look and a 24 h / 7 days / 30 days toggle (0.37.0). What remains: **coverage by direction** (which side of the sky the antenna hears best), drawn only once there are weeks of real data, and kept on the page alone (the posts never give a direction).
* **A web console, `/console`** — **built as a test in 0.39.0** at the owner's request (21 October 2026), off by default and removable: all three steps at once, see [Web console](Web-console). What remains: the owner's verdict after trying it on the Pi; HTTPS under the DuckDNS name, which passkeys and Face ID would need; previews of the post pictures inside the page rather than in a new tab. The proposal as written on 21 October: The menu over SSH works but is rough for settings that need a preview (posts, cards, summaries). The idea, in three steps, each its own release: (1) read-only dashboards (status, health, memory, logs) and the settings that only need the wall or the social service restarted, with the post previews; (2) system actions — update, features on and off — through a small root helper that accepts only a fixed list of `zenithboard` commands, journaled, behind a password the owner chooses, with the typed word kept for anything destructive; (3) a first-boot wizard. It calls the same `zenithboard` commands, so the command and the menu stay the reference. Never through it: Wi-Fi and fixed-IP changes (they can cut the page off), the uninstall, and the Bluesky app password (SSH only). Waiting on: a decision by the owner, after the 1.0 proofs.
* ~~Signing a computer in with the phone~~ — done in 0.40.0 at the owner's go-ahead, off by default: `console phone-signin on`. See [Web console](Web-console).
* **A decision on AirNav RadarBox.** A fifth feeder is only worth it if its MLAT does not fight the single-MLAT rule. Waiting on a few nights of data first.
* ~~Wi-Fi hardening~~ — done in 0.21.0: `zenithboard wifi harden on`, off by default, reversible.

## Later — good ideas, no urgency

* Airline names for callsigns that have no route in adsbdb: a dedicated airline lookup, one request per prefix, off by default. Since 0.17.0 every airline with a known route is already named from the route answer, so this is worth doing only if bare callsigns are still common on a real wall — which is what `zenithboard stats gaps` (0.21.0) now measures; see *Now*.
* Wider silhouette coverage, so fewer aircraft fall back to the generic shape: the same counter says which type codes do, and the five to ten most frequent get a shape each, previewed before it ships.
* The 978 MHz UAT path validated by someone in the United States. It is written and tested, and nobody has run it for real.
* ~~Posts with a real map, flags whole, no dark blue~~ — done in 0.23.0 (`social look dotmap|flap|alternate`); the dots-only look left in 0.24.0.
* ~~Photos as Planespotters' terms ask~~ — done in 0.24.5: the tablet loads each picture itself, the Pi keeps none. JetPhotos is not used (no API; personal use only).
* ~~Per-tablet presets~~ — done in 0.21.0: `zenithboard preset add kitchen theme=green mode=flap`, then `?p=kitchen` on that tablet.

## Not planned, and why

Saying no here saves answering the same question twice.

| Not planned | Why |
|---|---|
| **Airline and aircraft-maker logos** | They are trademarks, and redrawing one in dots is still the trademark. A free project cannot hand them out, and a wall of 90 logos is a licensing problem, not a feature. Flags stand in for them: the registration country next to the registration (since 0.20.0), the maker's country next to the model |
| **Sound on the wall** | An airport-hall ambience was tried (0.13.0) and removed an hour later (0.13.1): it did not sound good enough to keep. Nothing nobody has heard is shipped |
| **A cloud account, a hosted dashboard, telemetry** | The Pi is yours. Nothing should need to phone home for the wall to work. |
| **Turning off package signature checking** | It has been the quick fix for two different installer problems. It stays off the table: a signature that is not checked is not a signature. |
| **Supporting hardware other than a Raspberry Pi** | It probably works on other Debian machines; it will not be tested there, so it will not be claimed. |
| **A route source that does not need the internet** | There is no free, complete and current database of routes by callsign: the public ones are partial, stale, or under licences a GPL project cannot carry, and a stale route shown with confidence is worse than none. Callsign lookups stay online (adsbdb, hexdb as a second opinion), cached, and off when the Pi is |
| **A photo in the Bluesky posts** | Planespotters' photo API terms forbid storing, re-hosting or passing on a picture, and a link card would upload its thumbnail. A link to the photo page with the photographer named is what is allowed (`social photolink on`, 0.25.0). JetPhotos has no API and grants personal, non-commercial use of the site only |
| **ACARS and Grafana** | Removed in 0.30.0: never run on the reference Pi, about 900 MB more than a 1 GB board has, and what Grafana would have shown is on the wall's own statistics page, with graphs1090 as the long-term option (0.32.0). A Pi that had them keeps them until `sudo zenithboard acars remove` |
| **A paid tier** | It is GPL and it stays free. There is a beer link in the README and that is the whole business model. |

## Suggesting something

Open an issue. An item moves from *Later* to *Next* because someone wants it, not because it has waited long enough.
