# Roadmap

No dates except those the sky sets (a monthly summary, a month of lists). ZenithBoard is a spare-time project and any other date would be a fiction. What this page promises is an order.

**Where it stands (30 October 2026): 0.99.6, the release candidate for 1.0.** Features are frozen since 25 October 2026, 13:42 (the owner); only fixes ship until 1.0 (0.99.1 to 0.99.5), and they do not move the date. On 30 October the owner let two features in, AirNav Radar and Telegram messages (0.99.6), and started the month again: **30 days from the reference Pi's update to 0.99.6**, 29 November 2026 if it is updated on 30 October. So this page reads, in order: what 1.0 still takes; what is watched on the Pi meanwhile; what was asked during the freeze (*Waiting for 1.1*); what comes after 1.0; what is done; what will not be done.

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

**Frozen since 25 October 2026, 13:42** (the owner: *on gèle à partir de maintenant, on ne passe qu'en correction*): **0.99.0** is the release candidate, the same code as 0.55.2. From it only fixes are made (0.99.1, 0.99.2…): no new feature, no new setting, no new screen, no new language. The hands-off weeks are counted from there, and a fix shipped during them restarts nothing (the owner, 29 October 2026: *on fait des corrections, pas des nouvelles fonctions*). What is asked during the freeze waits for 1.1, written down below in *Waiting for 1.1*, unless the owner lets it in: **0.99.6** (30 October 2026) brought AirNav Radar and the Telegram messages, and the 30 days started again with it.

**What counts as a fix:** something that does not do what the docs say, a crash, a wrong figure, a security or privacy hole, a mistranslation, a doc that a novice cannot follow (the fresh-card try will find some), a provider that moved a file. **What does not:** a new option, a new tag, a new screen or card, a new language, a new look, an improvement to something that works as documented.

**The hands-off clock started on 25 October 2026, 13:51 CET, for 25 November 2026, and starts again with 0.99.6** (the owner, 30 October 2026: *repart pour 30 jours de RC à la suite*): 30 days from the reference Pi's update to 0.99.6, which ran on **30 October 2026 at 22:27 CET** (the wall's journal: *0.99.6 listening*, 22:27:08): the month ends on **29 November 2026, 22:27**. The fixes do not move it (the owner, 29 October 2026: *arrête de pousser la date de la RC, on fait des corrections ici, pas des nouvelles fonctions*). 0.99.1, 0.99.2 and 0.99.3 were fixes and the Pi took them in its stride; for two days the date had been pushed to 28 and then 29 November, which is withdrawn. What would stop the clock is what the month is there to catch: a crash in the logs, a reboot forced by a watchdog, a service that stops. Those are written in the field log of [Project status](Project-status), and one of them moves the date.

Swahili and Hindi are published without a native review, said as such in [Translating](Translating): that is not a caveat for 1.0.

**Earliest date:** the monthly summary on 1 November, a month of lists around 20 November, the release candidate's 30 days hands-off from the update to 0.99.6 (30 October, 22:27): **29 November 2026 at the earliest**, with the fresh card and the fixed address done meanwhile. A caveat still open then moves the date, not the bar.

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

**Undercounted before 0.99.13 for imperial and aviation units.** Until 0.99.12 the sampler sent `RADIUS` to the wall as kilometres, whatever the units: a wall set to 10 miles (16.1 km) or 10 nautical miles (18.5 km) was sampled over 10 km, a smaller circle, so `stats gaps` counted fewer aircraft than the wall shows (in area, about 39% of the circle for miles and 29% for nautical miles). A Pi set to kilometres was counted right. The gaps files of before are kept as they are (nothing can say which aircraft were missed), so on such a Pi read the figures as a floor, or read them again thirty days after the update. The 17 November reading needs 0.99.13 on the Pi; the units a Pi is set to: `zenithboard config | grep UNITS` (no line means kilometres).

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

* **Receiver health by trend** (asked by the owner, 26 October 2026). The statistics already keep thirty days of messages per hour. An alert when the rate falls well below the same hour one week earlier would catch a dongle losing strength, a degraded antenna or a cut cable, before a receiver goes quiet for days: the most useful alert for a Pi that runs without anyone watching it. It depends on what the sky looks like, so the threshold waits for the counters to show a normal week (`zenithboard stats gaps` and the field log), not a guess. Off by default, by command and by menu; the Telegram chat of 0.99.6 is where it would be said.

* **Emergency squawk banner on the wall** (asked by the owner, 26 October 2026). When 7500, 7600 or 7700 is heard anywhere in the antenna's range, not only inside the wall's radius, the wall shows a banner for 30 seconds, longer than its usual time for an aircraft, with the code and its meaning; a checkbox in the wall's settings (the gear), off by default, and a command. Nothing published: an emergency is not a fact to broadcast. The detection is 0.99.6's (`flightinfo/telegram.py`, heard on two reads in a row); to be previewed on the real wall before it ships.

* **From the review of 0.99.8** (30–31 October 2026), found while fixing and left for after 1.0 because each is a change of design, not a fix:
  * **A setting without a restart** (A2b). Today a wall setting restarts the wall service so that the tablets reload ([Architecture](Architecture)); a restart loses the aircraft seen since the last quarter-hour sample and sends a burst of lookups to adsbdb, hexdb and Planespotters. `/api/planes` would carry `config.env`'s modification time beside `server_id`, the wall would reload when it changes, and the wall's commands would only write the setting; a restart stays for a code update, `PORT` and `BIND_ADDRESS`. Until then, an option: the restart takes the statistics sample first when statistics are on.
  * **One validator** (A3b). Each value is checked two or three times (the command, the console, the presets, the import), and the copies already disagree: the console's hashtag rule is not `social_hashtags_clean`'s (100 characters, a letter in each word), `summary-at`'s format is not tied to the period. Either the console asks the command (`zenithboard <cmd> --check VALUE`) or both come from one table. With it, ADSB Exchange's, FlightAware's, Flightradar24's and Plane Finder's logs in the console's list (new labels, so the 22 languages).
  * **The towns near a point from an index** (A4). `_towns_near` reads the whole list of places at each call; it would be loaded once into one-degree squares, the loader shared by the wall's server, the Telegram service and the split-flap picture.
  * **Dead code** (A5): `net_default_mask` and `wifi_default_route_dev` in the shell, `local_types` in the server (unless 1.1 calls it), `social_set_weekly` once its test runs `zenithboard social weekly on`, the two pictures nothing shows (`docs/images/console-devices.png`, `docs/images/stats-fr.png`). The step that keeps an older install's ACARS units goes only once the owner confirms no Pi still has them.
  * **A page-error smoke test** (follow-up of T1): `/`, `/stats` and `/console` loaded in headless Chromium on the test server, failing on any page error. Playwright is in CI since 0.99.18.
  * **The wall's page refused by name too** (W2's other way, not taken in 0.99.17): `/` and `/static/*` answer 403 to a name that is not the Pi's, as the wall's data does, so the browser shows the refusal and its `CONSOLE_HOSTS` command at once instead of the wall's *WRONG NAME*.
  * **A day's figures counted in the quarter hour they measure** (S5, held for the owner's choice in 0.99.15): each day's messages and farthest aircraft include the day before's 23:45–24:00 and lose their own last quarter hour. Counting a row at its time less 15 minutes is right, but moves the figures already on screen by one quarter hour, which is the owner's call.
  * **The console's refusal with its reason**: the Pi already sends `{error, why}` for an action refused here; the console could show *Not allowed here: {why}* (a new string, so the 22 languages).
  * **Arabic's quick-glance chips**: *Bluesky* and its state read *:Bluesky إيقاف*, the colon on the wrong side, right to left.
* **A leaner architecture for 1.1**, by value, from the same review:
  1. One table of rules for every value (key, type, range, choices), read by the command, the console, the presets and the import, so that a check fixed in one place cannot be missed in another (A3b).
  2. Reload the setting instead of restarting the service (A2b).
  3. One unit-conversion module per language: one for Python (`social.py`, `telegram.py`, `social_card.py`, `server.py`), one for the pages (`format.js`, `stats.js`), against one table test. Five copies today, and each unit added so far missed one.
  4. One *saved on change* state helper for the two posting services, after each send and on SIGTERM, so that *once per crossing* holds through any restart, in one place.
  5. The boundary between root and the `zenithboard` user written in [Architecture](Architecture) as a rule (0.99.11 did most of it), with a test that walks every path root opens.
  6. One window helper for the statistics: one function decides a row's window and bucket (day, hour, quarter hour) for `/stats`' lines and boxes and the farthest aircraft, so they cannot drift apart again (S5).
  7. The places index of A4, loaded once and shared.
  8. The smoke test above, beside the docs' coverage check (every test file named on [Testing](Testing), 0.99.21).
  9. The dead code of A5 removed.

## After 1.0

What was planned before the freeze and is not a fix, in the order it would come. Nothing here starts before 1.0 is out; then *Waiting for 1.1* first.

* **Airline names for callsigns without a route**, and **more silhouettes**: decided on the figures of 17 November 2026 (procedure above). Since 0.17.0 every airline with a known route is already named from the route answer, so the lookup is worth it only if bare callsigns are still common on a real wall.
* **Coverage by direction on `/stats`** (which side of the sky the antenna hears best), once there are weeks of real data, on the page alone: the posts never give a direction.
* **The web console, further:** HTTPS, which passkeys and Face ID need; and the post pictures previewed inside the page rather than in a new tab. A Pi on a home network can have a certificate browsers trust in two ways (the owner's choice of 26 October 2026: both written down, Tailscale first):
  1. **Tailscale**, already in ZenithBoard (`zenithboard tailscale`): with MagicDNS and HTTPS switched on in Tailscale's admin console, `tailscale cert` (or `tailscale serve`) gives the Pi a real Let's Encrypt certificate for a name like `zenithboard.your-tailnet.ts.net`, nothing to install on the phones. *Limits:* only the devices on the tailnet reach it, each with the Tailscale app; the name shows the tailnet's.
  2. **Let's Encrypt by DNS, with the DuckDNS name**: the DNS-01 challenge proves the name with a TXT record instead of a connection from outside; DuckDNS sets it through its API, and `acme.sh` does it by itself (`dns_duckdns`). The name can point at the Pi's home address (192.168.x.x): nothing is opened to the internet. *Limits:* some home routers refuse a DNS answer that points at a private address (their DNS-rebinding protection) and need an exception for the name; the certificate lasts 90 days, so the Pi renews it on a timer.

  Not considered: a self-signed certificate or a local authority (`mkcert`), which every phone and computer would have to install by hand, and with which passkeys stay unreliable.
* **978 MHz UAT validated by someone in the United States:** experimental, outside 1.0, since 25 October 2026 (written and tested, never run for real).
* **More languages:** Tamil and Urdu (asked about on 24 October 2026) only with a native reviewer: 90% could not be promised without one; Hindi came without (0.55.0, the owner's request). Hausa and Yoruba likewise (left out in 0.48.0). Swahili and Hindi wait for their native review ([Translating](Translating)).

## Done

Kept so the question is not asked twice. Newest first.

* ~~Telegram alerts, from the Pi~~ — built in 0.99.6 (30 October 2026), let in during the release candidate by the owner: each crossing of the sharing radius and each emergency squawk (7500, 7600, 7700) anywhere in range, once per flight, to the owner's own chat or group; never to Bluesky. The token in the terminal only, the finer settings in the console, every language. See [Telegram](Telegram).
* ~~A decision on AirNav RadarBox~~ — built in 0.99.6 (30 October 2026) at the owner's word, with its MLAT off (`autostart_mlat=false`): ADSB Exchange keeps the only MLAT client, so it does not fight the rule. See [Providers](Providers#airnav-radar-radarbox).
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
| **Photos from AirTeamImages** (asked 30 October 2026) | A paid stock library (about 323 000 pictures). Its terms, read on 30 October 2026, allow low-resolution downloads for trial layouts only and forbid *all other reproduction* outside a paid usage agreement (personal prints, editorial licences); there is no public API. Showing its pictures on the wall or in the Bluesky posts would need a licence for each use. Planespotters stays the one source: a free API whose terms allow exactly what ZenithBoard does (the picture fetched from its own address, credited and linked) |
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
