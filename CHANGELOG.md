# Changelog

## 0.24.5
From Planespotters' photo API terms, read on 19 October 2026 at the owner's request.
- **The tablet loads the photos straight from Planespotters.** The terms ask that a picture be fetched from the address the API gives, by the screen that shows it, and never stored, proxied or passed on. Until now the Pi fetched each picture and served it to the tablet from a memory cache of 200 (`/api/photo/…`): that route and the cache are gone. The tablet needs internet to show photos; without it, the animated sky is shown as before.
- The API's answer is remembered 24 hours at most, as the terms allow; it was kept until the wall restarted.
- `zenithboard photos test` checks the API only and no longer downloads a picture to the Pi.
- The credit next to the photo and the photo as a link to its page were already as the terms ask. The photos are still never posted to Bluesky. JetPhotos is not used: it has no public photo API, and its terms grant personal, non-commercial use of the site only.

## 0.24.4
- **The towns are named on every map.** The satellite and terrain maps relied on EOX's label layer, which named one village in forty kilometres on a real post over Metz. They now carry the names ZenithBoard draws itself: the places of 5 000 inhabitants or more (GeoNames, CC BY 4.0, shipped with ZenithBoard, nothing looked up), the largest first, never over another name, the aircraft, north or the key. The credit names GeoNames; the satellite map's credit no longer names OpenStreetMap, whose labels it no longer carries. The OpenStreetMap maps already name their towns.
- Checked at the owner's question: the scale bar and the track agree with the real distances and speeds. A Transavia at 997 km/h over three minutes flies 50 km; its track measured 48 km against the 10 km bar on the post; Metz to Thionville (28 km) measures 27 km on a preview.

## 0.24.3
- **The posts can have their own units.** `sudo zenithboard social units imperial` (or `metric`, or `wall`, the default: the wall's own `UNITS`, as before), and a question in the picture wizard (menu *Social sharing → Picture*): the altitude, speed and scale on the picture and the altitude in the text, in ft, knots and miles, whatever the wall shows. Asked for by the owner.

## 0.24.2
- Code scanning (CodeQL) findings put right: `social status | head` no longer leaves a file handle open when the reader leaves; an unused distance function went from the dot renderer; an empty `except` says why; a test imported the map module twice.

## 0.24.1
- **A thinner track on the posts' maps** (dotmap and flap): 3 pixels with a 6-pixel dark edge, from 5 and 11, which the owner found far too thick on the real posts. The aircraft keeps its size.
- The README and the wiki show a real `dotmap` post from the reference Pi in place of the preview drawn without tiles.

## 0.24.0
From the owner's first afternoon on 0.23.0.
- **The posts always carry a map.** The dots-only look (the dot-matrix wall with the track drawn in dots, no map) is taken out of the choices, at the owner's word: `social look`, the picture wizard and the menu offer `dotmap`, `flap` and `alternate`. `dotmap` is the default. A Pi still set to `dots` is not changed: it posts `dotmap`, and `sudo zenithboard update` says so with the command. `social map none` with `dotmap` now draws the dot wall with the track on black, like `flap` does, instead of the dots-only picture. Pillow is installed for every look. A Pi without it (offline) still gets the dot picture rather than none.
- **The farthest aircraft of the day is named even when its callsign came late.** At the edge of range the decoder often has an aircraft's positions before its callsign, so the record was kept with no flight, airline or route (*18/10 13:09 · TF-ICE · BOEING 737 MAX 8 · 322 km*, on the real page). The wall now remembers the callsigns heard in the last hour and fills it in, before or after the farthest position; the route is then looked up at the next sample. The record already written for 18 October stays as it is: the aircraft is long gone.

## 0.23.0
From a Bluesky post (Eurowings EWG11S, D-AIDO).
- **A new look for the posts: the dot-matrix wall beside a real map.** `sudo zenithboard social look dotmap`: the wall's dots on the left, and in the right-hand column, instead of the track drawn in dots, the map the split-flap picture already carries (OpenStreetMap, darkened, satellite or terrain, from EOX, credited in the post and on the picture) with the track and the aircraft. The map turns like the split-flap one (`social map rotate`), and the colours too. Node draws the dots with that column left dark and says where it is; Pillow lays the map there and writes a JPEG under Bluesky's limit.
- **`alternate` is now the two looks with a map**, `dotmap` then `flap`, as asked; the track drawn in dots left the turn. It stays a look of its own, `social look dots`, which fetches no map. Alternating with the maps turning, each look meets each of the four maps over eight posts and each colour over ten.
- **The flags show whole in the dot-matrix picture.** Its right-hand panel started at dot 86, and its frame was drawn over the last column of an outlined flag (the German flag beside D-AIDO lost its right edge). It starts at 88 now, two dots clear: a dark column, then the panel. Its legend (`100KM`) and its "no track" words fit inside the narrower frame. The wall itself was never affected: its right-hand column starts at 90.
- **The dark blue is gone**, from the wall (dot matrix and split-flap), the tablet's gear, `zenithboard color`, the menu, the presets and the posts; turquoise stays. A setting the owner made is not changed by an update: a wall, a preset or a picture colour still set to blue shows the Pi's colour, or amber, and `sudo zenithboard update` names each one with the command to choose another. A tablet that remembered blue, or opens `?theme=blue`, falls back the same way rather than to unstyled dots.
- **The aircraft is never under the legend.** On the dotmap's narrow map a track flown north to south ended under the legend box; when the aircraft would land under it, the view is now chosen in the part of the map above the legend and the credit (on the split-flap map too, where that is rarer).
- The messages that name the wall's colour say the one the posts and the wall show: amber while the setting still says blue, not "blue". The update's notice for a preset set to blue gives the whole command, its other settings included (`preset add` replaces a preset).
- `sudo zenithboard social test` with `alternate` now says when the map tiles could not be fetched, like it does for one look. A Pi without Pillow, set to a map look, is told to run `social test` (which installs it and keeps the look) instead of a `social look` that would have replaced `alternate`.

## 0.22.0
- **The statistics page names the farthest aircraft.** Under the four numbers, two lines: the farthest aircraft of the day and of the thirty days, with the date and time, the airline and flight number, where it flew from and to, the model and registration, the altitude, the distance, and the city of 100 000 inhabitants or more nearest to it: `14/10 21:07 · easyJet U21234 (EZY1234) · Edinburgh (EDI) → Saint-Louis (BSL) · AIRBUS A-319 G-EZAB · 10 970 m · 329 km, 55 km from Lille, FR`. Asked for from the real page, where *355 km* stood alone.
- The decoder only says how far, never which aircraft. With statistics on, the wall server now looks at `aircraft.json` every five seconds (about a millisecond each time on a laptop, a few on a Pi) and keeps the farthest aircraft of today and yesterday in memory; the 15-minute sample asks for it on the loopback and writes it to `farthest-DAY`, kept thirty days. The route is the wall's own lookup with the wall's own check, so with routes off nothing more leaves the Pi; with routes on, the day's farthest callsign is looked up too (the README's privacy line says so).
- The cities come from a list shipped with ZenithBoard: GeoNames, Creative Commons Attribution 4.0, credited on the page, 4 578 cities, made by `tools/make_cities.py`. City districts are left out, and two British entries that carry a district's population (St Peter's in Kent, Mendip), found when the preview named a point over the Channel *near Saint Peters*. Nothing is asked of the internet for a city. Neither the aircraft's position nor the antenna's is written or shown.
- Days from before this version have their number in the box and no line; the page says so for the thirty-day best.
- The statistics unit may run 120 s instead of 60: the sample can wait a few seconds for a route on its way.

## 0.21.1
The fresh-install check from the roadmap, done as far as it can be without a Pi: `install.sh` walked end to end from the README, in a container, against a scripted whiptail and stand-ins for the system (every flag, the first-run wizard, every menu, the deployed wall answering on its port, the uninstall). What it found, fixed, and now held by `tests/test_install.sh`:
- **A missing whiptail no longer ends in silence.** When `apt` could not install whiptail and curl (no internet, say), every screen failed and the installer quietly exited with nothing said. It now stops with the command to run by hand.
- **The Wi-Fi line read `ON, ` on a Pi on Ethernet.** `nmcli` prints nothing at all when no network is active, so the text meant to say *not connected* never appeared, in the Settings menu, the Wi-Fi menu and `zenithboard status`. Fixed, with a test.
- **The wall's colour in the menu offers all six colours.** Menu *4 Settings → 3 Wall → Colour* still listed amber, green, red and white; turquoise and blue (0.13.1) could only be set from the command or the tablet's gear.
- **A typo in the altitude is asked again** instead of being written as 0 without a word, like a bad latitude already was.
- The welcome screen pointed at `sudo zenithboard config` to change the answers later; that command only shows them. It now names menu *4 Settings* and the commands.
- A decoder that fails to install says that the feeders were not installed either, and a failed download says what it usually means (no internet, or a moved address).
- On a machine that is not a Raspberry Pi the installer no longer prints `No such file or directory` twice for the model file.
- README: *4 Settings* has six groups, not four (Logs, Reliability and Social sharing were missing from the list), and step 6 says where the wall's address comes from (menu 2 prints it, `zenithboard status` repeats it).
- *Maintenance → Save my settings* proposes a folder that exists when there is no sudo user (root's), not `/home/pi`.
- For the test, `ZENITHBOARD_HOME` and `ZENITHBOARD_BIN_DIR` redirect `/opt/zenithboard` and the `zenithboard` link, like `ZENITHBOARD_ETC` does for the settings. Nothing changes on a Pi.

## 0.21.0
From a walk through every menu on the reference Pi, recorded.
- **The menu keeps the one irreversible step out of the way.** *7 Uninstall everything* is now inside *7 Maintenance*, after *Save my settings* and *Restore settings*, and it asks for the word `uninstall` to be typed, not a Yes: one Enter too many at the end of the list must not take a working receiver down. Removing the wall and deleting every log ask for a typed word too.
- **Settings as a file.** `zenithboard settings export` writes `config.env` without anything that looks like a secret (the Bluesky app password, feeder keys and passwords stay in their own root-only files); `sudo zenithboard settings import FILE` puts a file back, skipping anything that is not a setting, and keeps the file from before as `config.env.bak-DATE` so an import is one command from undone. Menu *7 Maintenance*.
- **A quick update.** `sudo zenithboard update quick`, and the first entry of menu *6 Update*: ZenithBoard and the wall only, in seconds; the feeders are left alone rather than asked of `apt` one by one, which took a minute or two for a change to the wall alone.
- **Per-tablet presets.** `sudo zenithboard preset add kitchen theme=green mode=flap radius=5`, then that tablet opens `http://PI:8080/?p=kitchen` and takes those choices at every load, instead of a long address of `?theme=…&mode=…`. Menu *4 Settings → 3 Wall → 8 Presets*. Kept in `config.env` as `PRESET_KITCHEN`, so they travel with an export.
- **Wi-Fi hardening, off by default.** `sudo zenithboard wifi harden on` sets two things on the saved Wi-Fi profile: keep trying to rejoin after a loss without end (NetworkManager gives up after four tries), and the radio's power saving off, a known cause of short losses on a Pi. `off` puts back exactly what was there. Menu *4 Settings → 1 Network → 1 Wi-Fi → Hardening*.
- **Counting what the wall cannot name or draw.** With statistics on, every sample also notes each aircraft shown with a callsign but no airline name (by its three-letter prefix) and each one drawn with the generic silhouette (by type code), once per aircraft, thirty days. `zenithboard stats gaps` prints the counts: the figures the roadmap's airline lookup and new silhouettes will be chosen on, rather than guesses. The statistics unit may now reach the wall on the loopback, and nothing else.
- The ACARS tag in the main menu no longer runs off the screen; `status` no longer calls a 1 GB Pi a board to skip ACARS on without saying why (it is the measured board: everything but ACARS and Grafana).
- Roadmap: an offline route source is *not planned* (no free, complete, current database of routes by callsign exists; a stale route shown with confidence is worse than none).

## 0.20.1
- **The hardware advice is measured now, not estimated.** The reference Pi 3B (1 GB) runs readsb, ADS-B Exchange with MLAT, FlightAware, Flightradar24, the wall and social sharing with 656 MB of its 1 GB still available, at 36 °C, without throttling. The README's table starts from those figures, *What you need* says a Pi 3B or newer (2 GB or more only for ACARS + Grafana), and a new wiki page, [Hardware](https://github.com/regis57/ZenithBoard/wiki/Hardware), says why a bigger Pi brings nothing you would see for ADS-B, and what moving the SD card to one would change (power supply, possibly the address, heat) and keep (the system, the settings, the feeders' identities), with the way back.
- The installer's notice on a 1 GB Pi 3 says what was measured on one, instead of advising at most one or two extra feeders; a board under 700 MB is told: ADS-B and the wall, no extra feeders.

## 0.20.0
- **Social sharing posts every crossing, once.** A crossing starts when an aircraft comes inside the sharing radius and ends when it has been outside it for an hour: whatever it does in between — circling, or leaving and coming back five minutes later — it is one post. The same airframe back after that is posted again (the return flight, the next day), and so is a new callsign sooner (turned round at a nearby airport). Until now an aircraft was remembered for a day after it was last seen anywhere by the receiver, so the evening's return flight was never posted, and the memory followed every aircraft the receiver heard, not the radius.
- **Nothing caps the posts.** The gap between two posts is now none by default (`SOCIAL_GAP_MIN=0`), and the ten-minute floor of 0.19.3 is gone: the feed is what crosses your radius. A gap can still be set, to any whole number of minutes, with the new `sudo zenithboard social gap MINUTES` (or in `social words`); a gap already in your `config.env` is kept, and the update says so. After a post the service looks again five seconds later rather than fifteen, in case another aircraft is waiting.
- **An aircraft that left the radius before its turn is still posted**, up to ten minutes after it left: its route still being looked up (the wait is up to two minutes, and a jet crosses 20 km in about one and a half), or another posted first. Among equals, the one that came in first goes first.
- **The Bluesky session is reused.** 0.19 signed in for every post; Bluesky allows an account 300 sign-ins a day and 30 in five minutes, which every crossing on a busy day could pass. The session is kept in memory (never written anywhere), renewed with its refresh token after an hour, and signed in afresh only when Bluesky refuses it — once, never in a loop. `social check` still signs in afresh.
- `social status` says how many posts went out in the last day (not how many aircraft were remembered) and how many crossings are remembered, so *why was that one not posted?* has an answer. State from 0.19 is read as it is.
- **The registration's flag sits beside the `REG` row**, on the wall and in the dot-matrix posts. Beside the airline row, where it was, it read as the airline's country. The airline row keeps its twelve letters: the flag's outline, when it has one, is on the dark row just above it.
- Without flags, the airline and model rows stop before the right-hand column and turn there; they ran on to the wall's edge, so a long airline name went under the silhouette.

## 0.19.10
- **The memory figure for Node is Node's own.** The service's hourly line read *104 MB at most, Node 104 MB at most*: Python starts Node with vfork, and the kernel then credits the child with the parent's peak, so both numbers were Python's. The renderer now reports its own peak (`process.resourceUsage().maxRSS`) and the service keeps the largest. Seen on the real Pi after four hours of posting.

## 0.19.9
- **A post waits for the second opinion on the route too.** RYR8526 and EWG6ZP went out with empty route rows. adsbdb had other flights under those callsigns (Berlin → Stansted, Salzburg → Aalborg), which the wall rightly refuses for an aircraft over Metz flying south-east or north; it then asks hexdb.io, which had the right ones (Charleroi → Reggio Calabria, Menorca → Cologne) — a few seconds after the post. `/api/planes` now reports that second lookup as pending as well, and social sharing waits for it like for the first (two minutes at most). Checked against both services' real answers for these two callsigns.

## 0.19.8
- **An altitude no longer breaks across two lines** in a post: *altitude 8* at the end of one line and *600 m* on the next, seen on a phone. The thousands and the unit are joined by no-break spaces (`8 600 m`, `37 000 ft`, `over 300 km out`).

## 0.19.7
- **The hashtags have a command:** `sudo zenithboard social hashtags ADSB avgeek Moselle`, and a question in `social words`. The `#` is optional — typed unquoted, the shell would take `#ADSB` for the start of a comment and pass nothing. `none` for no hashtags at all (not even `#helicopter`), `default` for the three; alone, it shows them. Eight at most, letters, digits and `_`, at least one letter. Until now the only way was to edit `config.env`.
- `zenithboard social status | head` no longer ends with a Python error when the reader leaves early.

## 0.19.6
- **The map credit in a post is one short line, at the end:** *Map © OpenStreetMap, EOX* (satellite: *Map: EOxCloudless by EOX, © OpenStreetMap*), each name a link — to OpenStreetMap's copyright page, to EOX. It was three lines of small print between the text and the hashtags. The whole required text is still drawn on the picture and read in the alt text; OpenStreetMap's attribution guideline accepts the name linked to its copyright page, and EOX asks an online publication for its name and a link. Asked for after the first satellite post.

## 0.19.5
- **A post waits for the aircraft's details.** KLM24V went out with empty registration, model and route rows: the wall asks adsbdb about an aircraft when it comes inside the radius it is asked about, and the service, whose track had followed it from far out, posted it the same second. `/api/planes` now says which lookups are still on their way (`pending`), and the service waits for them, up to two minutes from the first time it saw them pending, then posts with what is known. `social test` waits inside its half minute.
- **Optional: posts that vary.** `social look alternate` (dot-matrix and split-flap, one post each), `social colour rotate` (amber, green, red, white, turquoise in turn; the wall's dark blue is left out of the turn, it reads poorly on a phone), `social map rotate` (the four maps in turn, at each split-flap post). Over ten posts each look meets each colour. `social status` names the next picture; posts made by hand move the turn on. Off by default; the wizard offers each.

## 0.19.4
- **The social service reports its own memory**: in its hourly journal line and in `sudo zenithboard social status` (now, at most, and the largest drawing by Node). 0.19.3 said `systemctl status` would show it: it does not on Raspberry Pi OS, which boots with the kernel's memory controller off (`cgroup_disable=memory`), and for the same reason the unit's `MemoryMax=300M` only applies where that controller is on. Seen on the real Pi right after the 0.19.3 update; ZenithBoard does not change the boot command line for it.

## 0.19.3
From the real Pi's log.
- **An update restarts the social service.** It only made sure it was enabled, and a running service keeps the code it started with: the Pi ran 0.19.0 for hours after installing 0.19.2. The service's first journal line now says which version it runs, and `social status` says when it runs code older than what is installed.
- **`social status` tells the truth when it cannot read.** Run as `pi`, it said *no account* and *Last post: never* on a Pi that had just posted: `pi` cannot read the account file or the state folder. It now says it cannot, and how to see everything (`sudo zenithboard social status`, which reads them as the service's user).
- **Ten minutes at least between two posts**, whatever is set (removed in 0.20.0: the owner wants every crossing posted). The gap had been set to one minute for a test; with *ALL*, that is a post a minute, which is what gets a bot account reported. A smaller value is used as ten and the status says so; the wizard says it too.
- **The service's memory is counted and capped** (`MemoryMax=300M`): a split-flap picture with its map peaks near 140 MB; `systemctl status zenithboard-social` now shows the figure.
- **Route rows: the city when it fits**, the way a departure board reads — `→SAN JOSE`, not the airport's `→JUAN SANTAMAR` — then the airport's name, then the city cut at a word, never on a dangling word (`FRANKFURT`, not `FRANKFURT AM`). On the tablet and in the posts.
- The 0.19.2 entry said a post had broken the two-hour gap; it had not, the gap was one minute. The fault 0.19.2 fixed was real, found while looking.

## 0.19.2
- **A post made by hand now counts for the running service.** *Post now* (`social post`) writes its post to the state file, but the service kept its own copy in memory and wrote it back every fifteen seconds, so the manual post was forgotten at once: the gap restarted from the service's own last post, and the aircraft posted by hand could be posted a second time. Found by reading the code after a post that looked too early (it was not: the gap had been set to one minute for a test, see 0.19.3). The service now reads the file before each decision and keeps the latest post and every posted aircraft from both; `social post` merges in turn instead of overwriting.

## 0.19.1
- **The rules list: the special aircraft, then ALL.** *ALL* means everything that flies over, the special ones included — ticking it alone is ticking every line, and a military aircraft under ALL is posted as military, ahead of an airliner. It was *any*, the last of six lines that read like a sixth kind of aircraft, and under *any* alone a tanker counted as "anything". The old word still works in `config.env`. The list says which rules wait for three days of history.

## 0.19.0
Social sharing, after the first real posts were read on a phone.
- **Bluesky only.** Mastodon is taken out: the wizard, the menu, the commands and the service know one network. An update removes a Mastodon token left on the Pi and the list of networks from `config.env`, and keeps the Bluesky account; revoke the token on your instance too.
- **The altitude can no longer be read as a distance:** `… · Paris → Abu Dhabi · altitude 8 500 m · above Trémery` (it read *8 500 m above Trémery*, taken for 8.5 km from Trémery).
- **The wall's two top rows, on the tablet and in the posts alike:** the flight and the registration on one row each, labelled like the altitude and the speed (`FLT  ETD11K`, `REG  A6-APD`), where the callsign alone stood two rows high. On the dot-matrix wall, on the split-flap board (nine rows now) and on both pictures. The track's legend is a key — a piece of the trail then `10MIN`, the scale bar then `100KM` — instead of two words that had to be guessed. The trail takes the picture's colour, which was always amber.
- **The picture's colour is a setting:** `sudo zenithboard social colour green` (or `wall`, the default: the wall's own colour). The six colours are read from the wall's `style.css`, so the picture matches the tablet exactly; green and white were slightly off before.
- **A second look: the split-flap board beside a map.** `sudo zenithboard social look flap`. The board has the same rows as the dot-matrix picture, without the flags, fourteen letters wide; the map is centred on the track, with the aircraft, a key (`LAST 10 MIN`, a scale bar), north, and the credit. Five maps: `normal` (OpenStreetMap), `night` (the same, darkened), `satellite` (Sentinel-2 cloudless 2025, non-commercial use), `terrain`, `none` — `sudo zenithboard social map satellite`. Drawn by Pillow on the Pi in a second or two, a Pi 3B included; no browser, so the Pi 4 limit the roadmap planned is gone.
- **The map comes from EOX's tile service**, whose layers are free to use with attribution and a link back: both are on the picture and in the post (a clickable link). OpenStreetMap's own tile servers are not used: their policy rules out automated fetching nobody is looking at. Tiles are cached for a month under the service's state folder (60 MB at most), asked for with ZenithBoard's name, checked to be images, capped in size; when none come, the picture has no map and no credit, and `social test` says so.
- `social picture` asks the three picture questions; `social setup` asks for the account, the words and the picture. The menu has a *Picture* entry. `social test` keeps `preview.png` or `preview.jpg`, and `/social/preview` shows the newer one.
- The rule list in the wizard says what `farthest` has meant since 0.18.2: a 30-day range record.
- **One post per aircraft while it is in the sky.** An aircraft once posted is not posted again as long as the receiver still sees it, nor for a day after; it was a day from the post, which a slow aircraft or a restart could in theory outlast.
- **A failed post waits ten minutes before the next try.** It was tried again at the next look, fifteen seconds later, and every try signs in to Bluesky: a revoked app password or a Bluesky outage meant a sign-in every fifteen seconds, which Bluesky's limits do not allow for long.

## 0.18.3
Asked for after reading the first real post on a phone.
- **The post starts with the flight and ends with the place:** `Flight Etihad #ETD11K · Airbus A380-800 · Paris → Abu Dhabi · 8 500 m above Trémery`. No icon in front; an airline callsign is a hashtag, so the flight can be followed; a callsign that is only the registration reads `Aircraft D-EABC`, a helicopter `Helicopter …`, a military flight `Military flight …`. A town name reads *above Trémery* (it read *over* in 0.18.2); a phrase of your own (`near Metz`) is kept. A range record ends with *seen from Trémery*, since it was nowhere near overhead.
- **The picture:** the callsign at the size of the other rows, with the registration on the row under it; the last row has the time with its offset from GMT as the Pi's time zone has it that day — `11:39 GMT+2` in a French summer, `GMT+1` in winter, `GMT+5:30` where that applies. The alt text names the registration too.
- **The track always fits its frame.** A `10KM` legend pushed the scale bar out of the frame, and an A380's ten minutes (165 km) ran past the edge. The bar is shorter, sits against the right edge, and stands for 1 to 500 km, the smallest that keeps the whole track inside.
- The tablet's wall is unchanged: these are the posted picture's rows only.

## 0.18.2
Social sharing could hardly ever post: two of its five default rules could not fire in the service, though `social test` said they would.
- **`rare` counted looks, not aircraft.** The service asked the wall every fifteen seconds and counted the type each time; by the time an aircraft had thirty seconds of track it had been counted three times, so no type was ever "seen twice or less". It now keeps, per type, the last few distinct aircraft and the day; rare means at most two *other* aircraft of that type in thirty days. The 0.18.0 history is dropped, not converted.
- **`farthest` compared an aircraft with the record it had just set**, and only looked inside the sharing radius (15 km by default) for something over 50 km. It is now a thirty-day range record, looked for in the whole sky from `aircraft.json`, and the wall is asked about that one aircraft alone (`/api/planes?hex=`, so nothing in between sets off a lookup). The post says the distance rounded down to 50 km — *over 300 km out* — not the figure.
- `rare` and `farthest` wait for three days of history; `social status` says where it stands. The other rules work at once.
- **`social test` says whether the service would post** what it shows, and why not — it adds `any` for itself and so always shows something, which was the source of the confusion.
- The service writes one line an hour to its journal (looks, candidates, last post, next possible), and says at start what it will do.
- A bare place name reads *over Trémery*, not *1 750 m Trémery*; *De Havilland*, not *DE Havilland*. Both seen on the first real test.

## 0.18.1
- **`zenithboard social test` and `social post` no longer crash from the command line.** They draw the picture in `/run/zenithboard/social`, which systemd creates for the service only; run by hand as the `zenithboard` user, the folder did not exist and Python stopped with *Permission denied* (seen on the first real try). The folder is now made for the command line too, and when it still cannot be written, a private temporary folder stands in and is removed after the post. Tested as a user with no rights on a box without the folder.

## 0.18.0
- **Social sharing, off by default: the aircraft worth a post, on Bluesky and Mastodon, as a picture of the wall.** `sudo zenithboard social setup` asks for a Bluesky app password or a Mastodon access token (never a real password), tries the accounts, then asks for the words: the place named in the posts, the sharing radius, the minimum gap between posts, and what is worth a post — a rare type, military, a helicopter, a heavy, the farthest of the day, or anything. `social test` draws the picture and prints the text without posting; `social on` starts the service. Menu: *4 Settings → 6 Social sharing*.
- **The picture is the dot-matrix wall with the aircraft's track** over the last minutes in the right-hand column, drawn by the Pi itself from the wall's own code — no browser, no photo, under a second on a Pi 3B. Node is installed from Debian for it when sharing is switched on; nothing else is added.
- **Nothing that gives the receiver away leaves the Pi:** no distance, no bearing, the time where the tablet shows them, the track centred on the aircraft with no map. The Planespotters photo is not posted (their terms). Secrets live in `/etc/zenithboard/social.env`, root-owned, mode 0640, read by the service only; `zenithboard security` checks it. The picture is drawn in memory and deleted after each post.
- The service runs as the `zenithboard` user in the wall's sandbox (1.3), and `zenithboard update` carries it. Wiki: [Social sharing](https://github.com/regis57/ZenithBoard/wiki/Social-sharing).

## 0.17.4
- **The gear panel offers the statistics page, while there is one.** Beside the version, in the same grey: `ZenithBoard 0.17.4 · Statistics`. It appears only when `STATS=1` and goes as soon as statistics are switched off, because a link to a feature nobody turned on leads to a page that says "off" — a dead end dressed as a door. `/api/config` carries the setting; the wall reloads by itself within seconds of `zenithboard stats on` or `off`, so the link follows without touching the tablet.

## 0.17.3
- **An update now checks that the wall really came back on the new version**, instead of assuming it. The wall is a running Python process: new files on disk change nothing until it is restarted, and an update that did not pass through the FlightInfo step left it answering the old version — the menu said 0.17.2 while the gear panel still said 0.17.1 (seen on a real Pi after `update only zenithboard`). The end of every update now asks the wall, on the loopback, which version it is running, restarts it when that is not the version just installed, and says so. A wall that still will not come up is reported with the command to run, never hidden.

## 0.17.2
- **Both pages say which version they are running**, in one grey line: at the foot of the gear panel on the wall, and at the foot of the statistics page. The name is a link to that version's own release notes on GitHub (`releases/tag/v0.17.2`), so "what changed?" is one tap away from the tablet. Nothing is asked of GitHub to draw the line: it is a link, followed only if somebody taps it, so a wall with no way out to the internet still names its version. `/api/stats` carries the version the way `/api/config` already did, whether statistics are on or off.

## 0.17.1
Two things seen on the real wall.
- **The British flag was there and could not be seen.** Two thirds of the union flag is `#012169`, a navy that at eleven dots on an unlit wall reads as a hole — so a British Airways aircraft looked as though it had no flag at all. A flag that would be invisible against the black wall now gets the same one-dot white outline as a flag carrying black. Its colours are untouched: a navy brightened into another blue is no longer that flag. The United Kingdom is the only one the rule newly catches, and a test holds the list.
- **The model row keeps the maker only while the whole thing fits.** An Etihad A380 arrived as `AIRBUS A-380-800`, sixteen characters, and walked past the twelve the flags leave instead of standing still as `A-380-800`. Every neo, every MAX and every A380 scrolled for nothing. The maker is now dropped as soon as the full name is too long, and only what is still too long without it scrolls. `DE HAVILLAND CANADA` also stopped leaving a lonely `CANADA` behind.

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
