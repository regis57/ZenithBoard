# Project status

Last updated: **17 October 2026**, version **0.19.10**.

This page separates what has been proven on a real Raspberry Pi from what has only been written and unit-tested. The difference matters: every test in this project runs against stand-in programs, so a green suite proves the logic and says nothing about the hardware.

## Proven on hardware

One Raspberry Pi 3B, outdoors, on Wi-Fi, with an R820T dongle.

| Part | What is known |
|---|---|
| Install and the menus | Run end to end on a Pi 3B |
| readsb + the wall | Running continuously; the split-flap look is the one in daily use |
| Feeding ADSB Exchange | Feed received and confirmed |
| Gain tuning | `zenithboard gain check` reads real statistics; settled at **48.0 dB** |
| The 24-hour gain log | A full day recorded, 96 measurements, nothing lost and nothing overrun. See [Gain tuning](Gain-tuning) |
| Aircraft photos | Real photos from Planespotters on the wall |
| The Wi-Fi menu | The Pi is on Wi-Fi, joined through the menu |
| Feeding FlightAware and Flightradar24 | Both feeding; FlightAware's coverage chart confirms it |
| Domain name (DuckDNS) | Set up and updating |
| Route lookups | Working against adsbdb. The wrong answers it produced are what led to the plausibility filter and the hexdb second opinion in 0.9.2 |
| Reliability menu | All four options turned on and left on |
| Hardware watchdog | Installed and surviving reboots |
| Network watchdog | Did real work on a real outage and diagnosed it: three network restarts three hours apart, no reboot loop, and its log named the cause |
| Persistent logs | Working, after one `sudo journalctl --flush` the first time |
| The systemd sandbox | The wall server runs inside it; `systemd-analyze security` gives 1.3 (OK) |
| Signed updates | Checked against GitHub's current key, silent once confirmed |
| `zenithboard health` | Reports power, temperature, memory, card and the previous boot correctly |

## Written and unit-tested, not yet run for real

Treat these as likely-working rather than known-working, and please report what you find.

| Part | What is missing |
|---|---|
| 978 MHz UAT (United States) | No US hardware has run it |
| Fixed IP address | The `nmcli` calls are tested; a real address change was not run. Keep a keyboard and screen at hand |
| Plane Finder | The installer runs; no feed has been watched |
| ACARS and Grafana | Built and tested; no long run on real traffic |

## Known rough edges

* Feeder download addresses are pinned in `lib/versions.sh` and were copied from each provider's page on 6 October 2026. Providers move files. A 404 during install usually means one line in that file needs updating. [When a provider changes something](Providers) says what happens and what to do.
* FlightAware and Flightradar24 keep your antenna position on their own websites. `zenithboard location` cannot change that for you; it tells you where to go.
* The airline name list covers about ninety airlines. Since 0.17.0 the rest are named from the route lookup once one of their flights has been looked up; with routes off they show the callsign.
* Routes are looked up by callsign, not by flight. A callsign can be reused for the other direction. The filter drops the impossible answers; it cannot invent the right one.
* ACARS legality differs by country. Check your local rules.

## Field log

Short notes from the Pi that is actually outside. Kept because the second time something happens, the first time is useful.

| When | What happened |
|---|---|
| 17 October 2026, evening | Four hours of the service on its own (still 0.19.7: the two updates after it not yet installed): 19 posts between 16:02 and 19:51 under *ALL* with the ten-minute floor, about five an hour; 35 to 36 of the 238 looks an hour found a candidate; 42 MB at rest, 104 MB at most. The hourly line said *Node 104 MB at most* too — Python's figure, which the kernel credits to a child started by vfork. Node now reports its own (0.19.10) |
| 17 October 2026, five o'clock | Two split-flap posts, RYR8526 and EWG6ZP, went out with empty route rows. Not the look: asked by hand, adsbdb gave other flights under those callsigns (Berlin → Stansted, Salzburg → Aalborg), which the wall rightly refuses for an aircraft over Metz heading south-east or north; hexdb.io, the second opinion, gave the right ones (Charleroi → Reggio Calabria, Menorca → Cologne), but a few seconds after the post. The wait for lookups now covers the second opinion too (0.19.9) |
| 17 October 2026, four o'clock | The first post with every 0.19 change in it, EWG9NU at 16:02, eighty seconds after the service started: all nine rows filled (the wait for adsbdb did its job), *→COLOGNE* by its city, the first step of the varied pictures (dots, amber), no credit line since there was no map. One flaw on a phone: *altitude 8* at the end of a line and *600 m* on the next. Numbers now hold together (0.19.8) |
| 17 October 2026, quarter to four | First satellite post, a Bellanca Decathlon (LX-FUN): the empty airline and route rows are right for a light aircraft, but the map credit took three lines of the post. It is now one short line at the end, the names as links; the full text stays on the picture and in the alt text (0.19.6) |
| 17 October 2026, twenty to four | Five minutes after the restart the service posted KLM24V with empty registration, model and route rows: its track, followed from far out, was long enough at once, while the wall had only just started asking adsbdb about it, which it does when an aircraft comes inside the radius it is asked about. The wall now says which lookups are on their way, and the service waits for them (up to two minutes). The owner also asked for posts that vary: the two looks in turn, the colours in turn, the maps in turn (0.19.5) |
| 17 October 2026, half past three | After the update the service ran 0.19.3 at once (restarted by the update, its first line said so), `sudo social status` showed the 14:21 post, four aircraft posted, 24 types noted and a 333 km range record, and as `pi` it said it could not read rather than *never*. One claim did not hold: `systemctl status` still had no *Memory* line. Raspberry Pi OS boots with the kernel's memory controller off, so systemd can neither show nor cap the service's memory. The service now measures it itself (0.19.4) |
| 17 October 2026, three o'clock | The Pi's own log, read line by line. The social service had run since 13:15: the updates that followed had installed new code without restarting it, so it still ran 0.19.0. `social status` run as `pi` said *no account* and *Last post: never* on a Pi that had posted twenty minutes before — `pi` cannot read the account file or the state folder, and the status did not say so. The gap had been set to one minute for a test, which explained the post that looked too early. Memory: 650 MB free on a Pi 3B, the service's own use not shown. All four fixed in 0.19.3, and the route rows now give the city (`→SAN JOSE`, not `→JUAN SANTAMAR`) |
| 17 October 2026, half past two | The service posted by itself for the first time — a Lufthansa A340 under `heavy`, split-flap with the night map, read on a phone. It came 48 minutes after the previous post, which looked like the two-hour gap failing; reading the code for that found a real fault — the service kept its memory in RAM and wrote it back every fifteen seconds over what *Post now* had written — fixed in 0.19.2. The post itself was not that fault: the gap had been set to one minute for a test, as the Pi's own log showed an hour later |
| 17 October 2026, two o'clock | Service on, radius 50 km, nothing posted in an hour while `test` always showed something: no military, helicopter or heavy had passed, and `rare`/`farthest` were still warming up — as designed, but the rules list made it hard to see, and its last line, *any*, read like a sixth kind of aircraft. It is now *ALL* at the end of the list, and ALL is every line at once: the special aircraft first, the ordinary traffic otherwise (0.19.1) |
| 17 October 2026, late afternoon | The first posts read on a phone: *10 670 m over Trémery* was taken for a distance from Trémery, and the track's legend (`10 MIN` over `10KM`) for a riddle. The text now says *altitude 10 670 m · above Trémery*, and the legend is a key. The owner sent a mock-up of the dot-matrix picture (flight and registration labelled), asked for the split-flap look with a map and a choice of map, and dropped Mastodon. The map could not come from OpenStreetMap's own servers — their policy rules out automated fetching — and EOX's tile service, free with attribution and a link back, took its place; the tiles were checked in a real browser, layer by layer, before the code used them. The split-flap picture is drawn with Pillow, not a browser, so it works on a Pi 3B (0.19.0) |
| 17 October 2026, afternoon | The first real post went out on Bluesky (an Etihad A380, from *Post now*). Read on a phone, it asked for changes: the text now starts with the flight (`Flight Etihad #ETD11K`) and ends with the place (`above Trémery`); the picture has a smaller callsign with the registration under it, and the time with its GMT offset, summer time included. The scale bar's `10KM` had pushed it out of the frame, and an A380's ten minutes ran past the edge: the scale now goes to 500 km per bar and always fits (0.18.3) |
| 17 October 2026, noon | No automatic post: reading the service again showed `rare` counting looks instead of aircraft and `farthest` comparing an aircraft with its own record — neither could fire, while `test`, which judges differently, said they would. Fixed in 0.18.2; the real service loop now posts a Dash 8 under `rare` in a test that feeds it a minute of a real-looking track |
| 17 October 2026, late morning | The first `social test` on the real Pi stopped with *Permission denied* on `/run/zenithboard/social`: the folder is systemd's, made for the service, and the command line ran outside it. Fixed in 0.18.1 the same hour |
| 17 October 2026 | Social sharing (0.18.0): Bluesky and Mastodon, a picture of the wall with the aircraft's track, drawn by the Pi without a browser. Decided against X (paid API since February 2026), Threads and Instagram (both fetch the picture from a public address). The Planespotters photo stays off the posts: their terms forbid re-hosting it. Mocked up in a browser and checked against the real renderer before being written; the networks are tested against fakes until the first real post |
| 15 October 2026, night (4) | The gear panel gained a link to the statistics page, shown only while statistics are on (0.17.4) |
| 15 October 2026, night (3) | A Pi showed the menu at 0.17.2 and the wall at 0.17.1 at the same time: updating only the ZenithBoard code deployed the new files without restarting the wall server, which runs the old ones until it is told otherwise. Every update now asks the wall what it is running and puts it right (0.17.3) |
| 15 October 2026, night (2) | The wall's gear panel and the statistics page now name the version they run, linked to its release notes (0.17.2) |
| 15 October 2026, night | Two faults the real wall showed that no test had: the union flag, being nearly all dark navy, was invisible on the black wall (British Airways looked flagless), and the model row scrolled `AIRBUS A-380-800` where `A-380-800` would have stood still. Both fixed in 0.17.1, both now held by a test. Neither was reproducible from the code alone — the first needed someone to look at the wall, the second needed a real Etihad A380 |
| 15 October 2026, late | Airline names learned from the route answer (0.17.0): the wall had been throwing away a name adsbdb sends with every route. Checked against the real answer for EZY1234, read in a browser the same day |
| 15 October 2026, evening (2) | The statistics page was smeared on its left edge once an hour passed a million messages: the axis drew about three hundred labels on top of each other. Seen on the real Pi's first busy afternoon, fixed in 0.16.3 and tested against the real axis function |
| 15 October 2026, evening | `zenithboard security` on the real Pi after 0.16.2: only two warnings, Debian patches not switched on and SSH passwords, the second kept on purpose (SSH is reached from home only). All five sandboxed services and every listening port recognised. The statistics portal is running |
| 15 October 2026, afternoon | Statistics (0.16.0): a 15-minute sample, the `/stats` page and `zenithboard stats`, off by default. The page was checked in a real browser against the real server with thirty days of made-up samples before being merged |
| 15 October 2026 | Second security pass (0.15.0): the wall answers home networks only, every service sandboxed, Grafana's default password closed, optional daily Debian security patches, a release per version, and `zenithboard security` to check the running Pi. Tested here with stubs and offline unit scoring; Grafana itself and the Pi's own `systemd-analyze` are the two things only the real machine can confirm |
| 14 October 2026, night | The wall gained the registration and maker flags (0.14.0). The manufacturer logo that was asked for alongside them was refused: a trademark redrawn in dots is still the trademark. The country where the airframe is built carries the same meaning and is free to draw |
| 14 October 2026, evening | A generated airport-hall ambience was added (0.13.0) and removed again an hour later (0.13.1): it did not sound good enough to keep. Turquoise and blue joined the wall colours the same evening and stayed |
| 13 October 2026, morning | No aircraft photos on the wall, only the drawn plane. The address check added in 0.11.1 allowed `planespotters.net`, but the pictures are served from `plnspttrs.net`: every photo had been refused in silence since. Fixed in 0.12.4. The test that should have caught it had been written from a guessed address instead of the real one |
| 13 October 2026, morning | `main` is now protected by a branch ruleset: no deletion, no force push, signed commits only, changes go through a pull request merged by squash, and the checks `test`, `analyze (python)` and `analyze (javascript)` must pass. The first attempt named the checks `analyse` with an *s*, which do not exist, so GitHub refused every merge until the spelling was fixed |
| 12 October 2026, evening | Security pass, all on the real Pi: the wall server's sandbox scores **1.3** in `systemd-analyze security` and the service runs normally inside it. The first signed-update checks found two bugs of their own — a download folder deleted before use (`curl: (23)`, fixed in 0.12.1) and only GitHub's expired key being recorded, so every update asked again (fixed in 0.12.3). After that, updates install silently. CodeQL's first run found a real header-injection path (fixed in 0.12.1/0.12.2); two deliberate file permissions were dismissed as *Won't fix* with the reason written down |
| 12 October 2026 | The new monthly link check found, on its first run, that `readsb-uninstall.sh` has not existed upstream for some time: removing readsb had been doing nothing at all. It now refuses out loud and prints the manual commands (0.11.2) |
| 11 October 2026 | First full day of the gain log: 96 measurements at 48.0 dB, median 2.83 % strong messages, range 271–336 km, 65 million messages. Four quarter hours went over 5 %, and the two before dawn turned out to be an artefact of low traffic rather than overload — the finding that a quiet hour cannot judge the gain in either direction |
| 10 October 2026 | **Cause found: the Wi-Fi extender had a schedule turning it off from 02:00 to 06:00.** Nothing wrong with the Pi, the signal or the weather. Schedule removed; the night of the 10th is clean from end to end |
| 9 October 2026, 01:00 | Wi-Fi lost. The network watchdog restarted the network and the Pi recovered on its own, nobody touching it. Three restarts that night, three hours apart — the gap rule working, not three faults. The diagnostic lines added in 0.10.2 are what identified it: the saved network invisible while other networks were still in range, which points at the access point rather than at the Pi |
| 8 October 2026 | Gain walked up and down the real R820T steps. 48.0 dB gives 4–5 % strong messages at rush hour, inside the 1–5 % guideline. Left there |
| October 2026 | A TV browser's top bar covered the settings gear. Moved to the bottom-right corner in 0.10.3 |
