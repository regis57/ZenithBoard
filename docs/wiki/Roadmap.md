# Roadmap

No dates except those the sky sets (a monthly summary, a month of lists). ZenithBoard is a spare-time project and any other date would be a fiction. What this page promises is an order.

**Where it stands (26 October 2026): 0.99.0, the release candidate for 1.0.** Features are frozen since 25 October 2026, 13:42 (the owner); only fixes ship until 1.0 (0.99.1, 0.99.2…). The reference Pi runs 0.99.0 hands-off since 25 October, 13:51 CET, for a month. So this page reads, in order: what 1.0 still takes; what is watched on the Pi meanwhile; what was asked during the freeze (*Waiting for 1.1*); what comes after 1.0; what is done; what will not be done.

## What 1.0 takes

1.0 means *validated on real hardware, no caveats in [Project status](Project-status)* ([Release process](Release-process)). The state of it on **26 October 2026**, the release candidate **0.99.0** running on the reference Pi since 25 October, 13:51 CET:

### Lifted

| Caveat | How it was lifted |
|---|---|
| ~~Plane Finder never fed~~ | Feeding from the reference Pi since 20 October 2026 |
| ~~graphs1090 never run on a Pi~~ (optional since 0.32.0, 20 October 2026) | Running on the reference Pi: its 24-hour and 7-day graphs seen in the owner's exports, 24 October 2026. Only collectd's memory over weeks is still to be watched, which time does by itself |
| ~~The farthest aircraft named on `/stats`, never seen on the real sky~~ | Seen on the real page: *20/10 08:20 · easyJet EZY17QZ · Manchester → Verona · 335 km, near Cergy-Pontoise* |
| ~~The web console: an update run from the page, a computer signed in by the phone~~ | Done several times on 25 October 2026, on two Pis (the owner) |
| ~~978 MHz UAT (United States)~~ | **Marked experimental, outside 1.0** (the owner, 25 October 2026): no US receiver has run it. It stays in, documented as such; a US user's report can bring it in later |

### Still open

| Caveat | What lifts it |
|---|---|
| The summaries posted by the service (0.33.0 to 0.38.0, 20–21 October 2026) | Daily (25 October, 08:45) and weekly (Saturday 24 October, 08:00, the day the owner chose) **seen going out**, the four posts each. The **monthly** one is left: due Sunday 1 November, 09:00 |
| Posts 2 to 4 and the page's lists over a real month | The lists began on 20 October 2026 (0.31.0): a whole month of them around **20 November** |
| A fixed IP address never applied for real | `zenithboard net static …` on the reference Pi, then back to DHCP, with a keyboard and screen at hand |
| What 0.54.18 to 0.55.2 added | Seen once on the real Pi: the day's aircraft counted every 5 seconds (against FlightAware's count, a whole day after the update), aviation units, the registration's hashtag on a real post, Hindi, the summaries' post 1 link |

### The two proofs of stability

* **A fresh install** on a blank card, following the wiki's [Fresh install](Fresh-install) alone, step by step, **and finished from the web console** (the owner's criterion, 21 October 2026: its checklist ticked line by line; a line that needed anything not written there is a fix to the page and a new try). The owner's blank card of 25 October 2026 met three such lines (the signing-key question, Bluesky in the wizard, where to find the position), fixed in 0.54.18: **a new try on 0.99.0 is what is left**. Since 0.21.1 the installer is also walked end to end against stand-ins at every change (`tests/test_install.sh`).
* **One month hands-off**, the release candidate's month (the owner, 25 October 2026: *l'application passe en RC pour un mois afin de valider un passage en v1.0*), social sharing on: no crash in `zenithboard logs`, no reboot forced by a watchdog. This one cannot start while the Pi is updated several times a day: it starts with the freeze.

### The freeze

**Frozen since 25 October 2026, 13:42** (the owner: *on gèle à partir de maintenant, on ne passe qu'en correction*): **0.99.0** is the release candidate, the same code as 0.55.2. From it only fixes are made (0.99.1, 0.99.2…): no new feature, no new setting, no new screen, no new language. The hands-off weeks are counted from there; a fix that has to be shipped during them restarts nothing unless it touches what the weeks are proving (the services, the posts, the watchdogs). What is asked during the freeze waits for 1.1, written down below in *Waiting for 1.1*.

**What counts as a fix:** something that does not do what the docs say, a crash, a wrong figure, a security or privacy hole, a mistranslation, a doc that a novice cannot follow (the fresh-card try will find some), a provider that moved a file. **What does not:** a new option, a new tag, a new screen or card, a new language, a new look, an improvement to something that works as documented.

**The hands-off clock started on 25 October 2026 at 13:51 CET** (the owner, the reference Pi on 0.99.0); written in the field log of [Project status](Project-status). The month ends on **25 November 2026**. An update that only carries fixes for something else does not reset it; a reboot forced by a watchdog, a crash in the logs, or a fix to the services, the posts or the watchdogs does.

Swahili and Hindi are published without a native review, said as such in [Translating](Translating): that is not a caveat for 1.0.

**Earliest date:** the monthly summary on 1 November, a month of lists around 20 November, the release candidate's month hands-off: **25 November 2026 at the earliest**, with the fresh card and the fixed address done meanwhile. A caveat still open then moves the date, not the bar.

## Watched during the release candidate

Not caveats for 1.0, but things the month on the Pi answers by itself. Each ends with a field-log row in [Project status](Project-status), and a fix (0.99.x) only if something is wrong.

| Item | Since | How it ends |
|---|---|---|
| **The statistics page's cost on a Pi 3B** | 0.37.0's look and period toggle (21 October 2026) approved on the real page; its cost measured on a desk machine only (0.14 s for thirty days) | A toggle through 24 h, 7 days and 30 days on the Pi with `sudo zenithboard memory` before and after |
| **The day's aircraft counted every 5 seconds** | 0.54.18 (25 October 2026): `/stats` was 11% under FlightAware | A whole day after the update compared with FlightAware's *Aircraft reported*: a few percent apart is right |
| **Debian's daily security fixes** | Switched on 18 October 2026 from the menu | A few weeks without a feeder disturbed (8 November) |
| **What the wall cannot name or draw** | Counted since 18 October 2026 (`zenithboard stats gaps`, 0.21.0) | Read on **17 November 2026**, procedure below; what it decides is built after 1.0 |
| **The posts' maps** | Since 0.23.0 (18 October 2026): a real map with the track, town names (0.24.4 to 0.27.0), the photographer's link (0.25.0, if on), units of their own (0.24.3; aviation 0.55.0), the registration as a hashtag (0.55.1). Read so far on the real Pi: the normal and terrain maps, the satellite map once | A few posts on each map (normal, night, satellite, terrain) read on a phone: legible names, credits in place, nothing hidden by the legend |
| **The gain** | Settled at 48.0 dB, 4–5 % strong messages at rush hour | Nothing to do. Recorded so it is not re-opened |

## Deciding the airline lookup and the new silhouettes on figures

Two items of *After 1.0* are to be built from what the reference Pi measures, not from guesses. The figures are read during the release candidate; what they decide is built after 1.0 (a new lookup and new shapes are features, not fixes). Statistics were switched on there on 18 October 2026; the figures are read on **17 November 2026** with `zenithboard stats gaps`, and this is the procedure, written down so it does not depend on anyone's memory.

**What is being counted.** With statistics on, every quarter hour the sampler asks the wall which aircraft are inside its radius and notes, once per aircraft over thirty days: the three-letter callsign prefix of each aircraft shown with a callsign but no airline name, and the type code of each aircraft drawn with the generic silhouette. `zenithboard stats gaps` prints both lists, most frequent first.

**2. Airline names for callsigns without a route**

1. Read the prefix list. A prefix seen on fewer than three aircraft in thirty days is noise. If no prefix passes that bar, the item is closed: the route lookup already names what matters.
2. Otherwise, one lookup per prefix, not per flight: the ICAO airline designator (`EZY`, `BGA`) asked once of adsbdb's airline endpoint if it answers by designator, or taken from an open designator list shipped with the wall if it does not; the answer cached for months in the wall's cache folder, like routes. Off by default, a line in the wall settings menu, `zenithboard config-set AIRLINE_LOOKUP 1`.
3. Checked against the real answers for the prefixes in the list before it ships, like the route filter was.

**3. More silhouettes**

1. Read the type-code list. The five to ten most frequent codes get a shape each; the rest keep the generic one.
2. Each shape is drawn in `flightinfo/static/shapes.js` with the primitives already there, previewed as a picture here, and shipped only once it has been seen — the rule for everything on the wall.
3. `aircraft.classify` maps the code to the new shape; `tests/test_shapes.js` holds the mapping so a code cannot quietly fall back to generic again.

**If the figures never come** (the Pi was off, statistics were switched off), the two items stay in *After 1.0* as they are. Nothing is built on a guess.

## Waiting for 1.1

What is asked during the freeze, kept here so that nothing is lost, and done after 1.0:

* **Telegram alerts, from the Pi** (asked by the owner, 25 October 2026). A message in a private Telegram chat or group when:
  * an aircraft inside the social sharing radius is seen, the same rule as the Bluesky crossings;
  * an aircraft, anywhere the antenna receives, broadcasts the emergency squawk codes 7500, 7600 or 7700.

  At most one message per flight, the repeat rule Bluesky applies. The squawk alerts go to the owner's chat only and are never published: an emergency is not a fact to broadcast, and the crew and the rescue services are not an audience. The Pi reads `aircraft.json` itself; the bot token lives in a file readable by the service's user alone and is set up from the terminal (`zenithboard telegram setup`, to be written), then tuned in the web console. The proof of concept is in French and English; every other console language follows with a native review, as the translation rule asks. Nothing is built before 1.0 is out: a service change restarts the hands-off clock.

## After 1.0

What was planned before the freeze and is not a fix, in the order it would come. Nothing here starts before 1.0 is out; then *Waiting for 1.1* first.

* **Airline names for callsigns without a route**, and **more silhouettes**: decided on the figures of 17 November 2026 (procedure above). Since 0.17.0 every airline with a known route is already named from the route answer, so the lookup is worth it only if bare callsigns are still common on a real wall.
* **Coverage by direction on `/stats`** (which side of the sky the antenna hears best), once there are weeks of real data, on the page alone: the posts never give a direction.
* **The web console, further:** HTTPS under the DuckDNS name (passkeys and Face ID need it); the post pictures previewed inside the page rather than in a new tab.
* **A decision on AirNav RadarBox:** a fifth feeder is only worth it if its MLAT does not fight the single-MLAT rule. Waiting on a few nights of data first.
* **978 MHz UAT validated by someone in the United States:** experimental, outside 1.0, since 25 October 2026 (written and tested, never run for real).
* **More languages:** Tamil and Urdu (asked about on 24 October 2026) only with a native reviewer: 90% could not be promised without one; Hindi came without (0.55.0, the owner's request). Hausa and Yoruba likewise (left out in 0.48.0). Swahili and Hindi wait for their native review ([Translating](Translating)).

## Done

Kept so the question is not asked twice. Newest first.

* ~~Posts, small things: a lower threshold of town names for a sparse region; the farthest aircraft named for the whole month~~ — settled 26 October 2026: the region's own list (`sudo zenithboard social places on`, 0.27.0, 20 October) names towns anywhere, ranked by GeoNames' place type rather than a population threshold; the farthest aircraft is named every day since 0.22.0 (19 October), so the unnamed days leave the thirty-day page around 18 November.
* ~~The web console, `/console`~~ — built in 0.39.0 (21 October 2026) at the owner's request, off by default and removable; computers signed in by the phone in 0.40.0 (21 October); an update from the page and a phone sign-in done on two Pis (25 October). See [Web console](Web-console). Never through it, by design: Wi-Fi and fixed-address changes, the uninstall, the Bluesky app password.
* ~~Translations~~ — the web console, `/stats`, graphs1090's page and the posts: French in 0.47.0 (21 October 2026), twenty languages in 0.48.0 (22 October), Swahili in 0.53.1 (22 October), Hindi in 0.55.0 (25 October); twenty-two in all, each with its review sheet ([Translating](Translating), [Translation plan](Translation-plan)).
* ~~Enrich the statistics page~~ — the sky by hour, airlines, models and altitudes (0.31.0, 20 October 2026); cargo, business jets, military and general aviation with flags, ZenithBoard's own look and a 24 h / 7 days / 30 days toggle (0.37.0, 21 October).
* ~~graphs1090~~ — optional since 0.32.0 (20 October 2026), running on the reference Pi (seen 24 October).
* ~~Try Plane Finder~~ — feeding from the reference Pi since 20 October 2026 ([Hardware](Hardware)).
* ~~Photos as Planespotters' terms ask~~ — 0.24.5 (19 October 2026): the tablet loads each picture itself, the Pi keeps none. JetPhotos is not used (no API; personal use only).
* ~~Posts with a real map, flags whole, no dark blue~~ — 0.23.0 (18 October 2026), `social look dotmap|flap|alternate`; the dots-only look left in 0.24.0.
* ~~Wi-Fi hardening~~ — 0.21.0 (18 October 2026): `zenithboard wifi harden on`, off by default, reversible.
* ~~Per-tablet presets~~ — 0.21.0 (18 October 2026): `zenithboard preset add kitchen theme=green mode=flap`, then `?p=kitchen` on that tablet.

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

Open an issue. During the freeze a new idea goes to *Waiting for 1.1*; after 1.0, an item moves up because someone wants it, not because it has waited long enough.
