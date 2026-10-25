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

1.0 means *validated on real hardware, no caveats in [Project status](Project-status)* ([Release process](Release-process)). The state of it on **25 October 2026** (0.55.2), reviewed with the owner:

### Lifted

| Caveat | How it was lifted |
|---|---|
| ~~Plane Finder never fed~~ | Feeding from the reference Pi since 20 October 2026 |
| ~~graphs1090 never run on a Pi~~ | Running on the reference Pi: its 24-hour and 7-day graphs seen in the owner's exports, 24 October 2026. Only collectd's memory over weeks is still to be watched, which time does by itself |
| ~~The farthest aircraft named on `/stats`, never seen on the real sky~~ | Seen on the real page: *20/10 08:20 · easyJet EZY17QZ · Manchester → Verona · 335 km, near Cergy-Pontoise* |
| ~~The web console: an update run from the page, a computer signed in by the phone~~ | Done several times on 25 October 2026, on two Pis (the owner) |
| ~~978 MHz UAT (United States)~~ | **Marked experimental, outside 1.0** (the owner, 25 October 2026): no US receiver has run it. It stays in, documented as such; a US user's report can bring it in later |

### Still open

| Caveat | What lifts it |
|---|---|
| The summaries posted by the service | Daily (25 October, 08:45) and weekly (24 October, 08:00) **seen going out**. The **monthly** one is left: due 1 November, 09:00 |
| Posts 2 to 4 and the page's lists over a real month | The lists began on 20 October: a whole month of them around **20 November** |
| A fixed IP address never applied for real | `zenithboard net static …` on the reference Pi, then back to DHCP, with a keyboard and screen at hand |
| What 0.54.18 to 0.55.2 added | Seen once on the real Pi: the day's aircraft counted every 5 seconds (against FlightAware's count, a whole day after the update), aviation units, the registration's hashtag on a real post, Hindi, the summaries' post 1 link |

### The two proofs of stability

* **A fresh install** on a blank card, following the wiki's [Fresh install](Fresh-install) alone, step by step, **and finished from the web console** (the owner's criterion, 21 October 2026: its checklist ticked line by line; a line that needed anything not written there is a fix to the page and a new try). The owner's blank card of 25 October 2026 met three such lines (the signing-key question, Bluesky in the wizard, where to find the position), fixed in 0.54.18: **a new try on 0.55.x is what is left**. Since 0.21.1 the installer is also walked end to end against stand-ins at every change (`tests/test_install.sh`).
* **One month hands-off**, the release candidate's month (the owner, 25 October 2026: *l'application passe en RC pour un mois afin de valider un passage en v1.0*), social sharing on: no crash in `zenithboard logs`, no reboot forced by a watchdog. This one cannot start while the Pi is updated several times a day: it starts with the freeze.

### The freeze

**Frozen since 25 October 2026, 13:42** (the owner: *on gèle à partir de maintenant, on ne passe qu'en correction*): **0.99.0** is the release candidate, the same code as 0.55.2. From it only fixes are made (0.99.1, 0.99.2…): no new feature, no new setting, no new screen, no new language. The hands-off weeks are counted from there; a fix that has to be shipped during them restarts nothing unless it touches what the weeks are proving (the services, the posts, the watchdogs). What is asked during the freeze waits for 1.1, written down below in *Waiting for 1.1*.

**What counts as a fix:** something that does not do what the docs say, a crash, a wrong figure, a security or privacy hole, a mistranslation, a doc that a novice cannot follow (the fresh-card try will find some), a provider that moved a file. **What does not:** a new option, a new tag, a new screen or card, a new language, a new look, an improvement to something that works as documented.

**The hands-off clock started on 25 October 2026 at 13:51 CET** (the owner, the reference Pi on 0.99.0); written in the field log of [Project status](Project-status). The month ends on **25 November 2026**. An update that only carries fixes for something else does not reset it; a reboot forced by a watchdog, a crash in the logs, or a fix to the services, the posts or the watchdogs does.

Swahili and Hindi are published without a native review, said as such in [Translating](Translating): that is not a caveat for 1.0.

**Earliest date:** the monthly summary on 1 November, a month of lists around 20 November, the release candidate's month hands-off: **25 November 2026 at the earliest**, with the fresh card and the fixed address done meanwhile. A caveat still open then moves the date, not the bar.

## Waiting for 1.1

What is asked during the freeze, kept here so that nothing is lost, and done after 1.0:

* *(nothing yet)*

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
