# Configuration reference

Every setting lives in one file: **`/etc/zenithboard/config.env`**. It is a plain `KEY=value` file, one per line, no quotes needed.

You rarely need to edit it by hand. Each setting has a menu entry or a command, and those validate what you give them. If you do edit it, `sudo systemctl restart zenithboard-flightinfo` is not needed for display settings — the server reads the file on every request — but it is needed for `PORT`.

Read the whole file with `zenithboard config`.

## The wall

| Key | Default | Set with | What it does |
|---|---|---|---|
| `UNITS` | `metric` | `zenithboard units metric\|imperial` | km, km/h, m — or miles, knots, feet |
| `THEME` | `amber` | `zenithboard color amber\|green\|red\|white\|turquoise` | Dot colour of every wall. A tablet can override it with a link. `blue` (taken out in 0.23.0) shows amber |
| `DISPLAY_MODE` | `dots` | `zenithboard mode dots\|flap` | Dot matrix, or the airport split-flap board |
| `RADIUS` | `10` | `zenithboard radius N` | Detection radius in your unit. Allowed: 1, 2, 5, 10, 15, 30, 50 |
| `CYCLE_SECONDS` | `14` | `zenithboard cycle N` | How long each aircraft stays on screen. A row too long for its width scrolls once in that time |
| `SHOW_PHOTOS` | `1` | `zenithboard photos on\|off` | Aircraft photos from Planespotters. Needs internet on the Pi |
| `FLAGS` | `1` | the gear on the tablet, or this line | The two flags on the dot-matrix wall: where the aircraft is registered, and where it was built. With them on, the airline and model rows hold twelve characters instead of fourteen |
| `SHOW_ROUTES` | `1` | `zenithboard routes on\|off` | Where the flight comes from and goes to. Needs internet |
| `LOCAL_DB` | `0` | `zenithboard data localdb on\|off` | Registrations and models from tar1090's aircraft database on this Pi, before adsbdb and hexdb (0.26.0). Offline |
| `LOCAL_DB_DIR` | `/usr/local/share/tar1090/git-db/db` | `zenithboard config-set LOCAL_DB_DIR PATH` | Where that database is |
| `PORT` | `8080` | `zenithboard config-set PORT 8090` | The wall's port. Needs a restart of the service |
| `BIND_ADDRESS` | `0.0.0.0` | `zenithboard config-set BIND_ADDRESS 127.0.0.1` | The interface the wall listens on. `127.0.0.1` keeps it to this Pi (behind a reverse proxy, say). Needs a restart of the service |
| `ALLOW_FROM` | `private` | `zenithboard config-set ALLOW_FROM any` | Who may read the wall: `private` (home networks: 10/8, 172.16/12, 192.168/16, the Pi itself, link-local and their IPv6 equivalents), `all`, or a list of networks such as `10.8.0.0/24,100.64.0.0/10`; since 0.45.0 the list may name `private` too (`private,100.64.0.0/10` is what `tailscale on` makes). Anyone else gets a 403. An unreadable value means `private` |

## Position and region

| Key | Default | Set with | What it does |
|---|---|---|---|
| `LAT` | asked at install | `zenithboard location LAT LON [ALT_M]` | Antenna latitude. The command also updates the decoder and the feeders |
| `LON` | asked at install | same | Antenna longitude |
| `ALT_M` | `0` | same | Antenna height above sea level, in metres. Matters for MLAT |
| `REGION` | `world` | `zenithboard region world\|us` | `us` adds the optional 978 MHz UAT step to the menu |

Changing the position in `config.env` by hand is the one case where hand-editing is a bad idea: four other places store it too, and only the command updates them all.

## Receiver

| Key | Default | Set with | What it does |
|---|---|---|---|
| `DECODER` | `readsb` | The ADSB menu | `readsb` or `dump1090-fa`. Decides which `/run/...` and `/etc/default/...` files are used |
| `ADSB_SDR` | empty | The ADSB menu | Serial number of the 1090 MHz dongle. Only needed with more than one dongle |
| `UAT978` | `0` | The UAT menu | Whether the 978 MHz receiver is installed |
| `UAT_SDR` | empty | The UAT menu | Serial number of the 978 MHz dongle. Must differ from the others |

The dongle gain is **not** here. It lives in `RECEIVER_OPTIONS` in `/etc/default/readsb` (or `/etc/default/dump1090-fa`), because that is where the decoder reads it. See [Gain tuning](Gain-tuning).

## Network

| Key | Default | Set with | What it does |
|---|---|---|---|
| `WIFI` | empty | `zenithboard wifi on\|off` | Whether the Wi-Fi radio should be on. Re-applied at every boot |
| `WIFI_COUNTRY` | empty | `zenithboard wifi country XX` | Regulatory country code, e.g. `FR`. Re-applied at every boot |
| `DDNS_PROVIDER` | `none` | `zenithboard ddns set PROVIDER NAME` | `duckdns`, `noip` or `freedns` |
| `DDNS_HOST` | empty | same | Your host name at that provider |

The dynamic-DNS **token is not stored here.** It is asked for interactively and kept in a root-only file, so that `zenithboard config` can be pasted into an issue without leaking it.

## Upkeep

| Key | Default | Set with | What it does |
|---|---|---|---|
| `AUTO_DATA_REFRESH` | `1` | `zenithboard data auto on\|off` | Monthly refresh of the aircraft-type list |
| `LOG_AUTOCLEAN` | `0` | `zenithboard logs auto on\|off` | Daily clean-up keeping the last 7 days |
| `NETWATCH` | `0` | `zenithboard netwatch on\|off` | The network watchdog. See [Reliability](Reliability-and-diagnostics) |
| `GAINLOG` | `0` | `zenithboard gain log on\|off` | The 24-hour gain log. See [Gain tuning](Gain-tuning) |
| `WIFI_HARDEN` | `0` | `zenithboard wifi harden on\|off` | The two Wi-Fi profile settings above are applied. `WIFI_HARDEN_PREV` keeps what they were, for `off` |
| `PRESET_NAME` | — | `zenithboard preset add\|del` | A tablet preset, e.g. `PRESET_KITCHEN="theme=green mode=flap"`; `?p=kitchen` applies it. Comes along in `settings export` |
| `STATS` | `0` | `zenithboard stats on\|off` | A sample every 15 minutes for the `/stats` page and `zenithboard stats`. See [Statistics](Statistics) |
| `TAILSCALE` | `0` | `zenithboard tailscale on\|off` | Whether Tailscale was switched on from ZenithBoard (0.45.0). What it installed: `/etc/zenithboard/tailscale.state` (`BY_ZB=1`) |
| `CONSOLE_TAILSCALE` | `0` | `zenithboard tailscale console on\|off` | The web console answers Tailscale's addresses (`100.64.0.0/10`) and `*.ts.net` names too |
| `GRAPHS_LOOK` | `zenithboard` (0.44.0; `original` before) | `zenithboard graphs look zenithboard\|original` | graphs1090 in ZenithBoard's look (0.43.0). The look itself is a marked block at the end of `/etc/default/graphs1090` and three files beside graphs1090's page; this keeps the choice for after an update or a new `graphs on` |
| `GRAPHS1090` | `0` | `zenithboard graphs on\|off` | Whether graphs1090 was turned on (0.32.0). What `on` found, to put it back, is in `/etc/zenithboard/graphs1090.state`. See [Statistics](Statistics#graphs1090-years-of-the-decoders-graphs-optional) |
| `CONSOLE` | `0` | `zenithboard console on\|off` | The web console at `/console` (0.39.0). Its password's hash is in `console.env`, never here. See [Web console](Web-console) |
| `CONSOLE_LANG` | *(empty)* | `zenithboard console lang CODE` | The web pages' language (console, `/stats`, graphs1090's page) for the browsers that did not choose their own with the flag at the top: `en`, `fr` (0.47.0; only the languages translated on this Pi). Empty: the console asks at its first visit, then sets it |
| `CONSOLE_PHONE_SIGNIN` | `0` | `zenithboard console phone-signin on\|off` | A computer's console sign-in page shows a QR code that a phone already signed in approves (0.40.0) |
| `CONSOLE_HOSTS` | — | `zenithboard config-set CONSOLE_HOSTS name1,name2` | Names, besides an address, `*.local`, `*.lan`, `*.home.arpa` and the Pi's own name, that the console may be opened by (a guard against DNS rebinding) |
| `SOCIAL` | `0` | `zenithboard social on\|off` | Post the aircraft overhead to Bluesky. See [Social sharing](Social-sharing). The account's secret is in `social.env`, not here |
| `SOCIAL_RADIUS_KM` | `15` | `zenithboard social words` | An aircraft is a candidate while inside it. Separate from `RADIUS` |
| `SOCIAL_AREA` | empty | same | The place named in the posts, in your words: a town name (`Trémery`) reads *above Trémery*, a phrase (`near Metz`) is kept. Never derived from the position |
| `SOCIAL_GAP_MIN` | `0` | same | At least this many minutes between two posts; `0`, the default since 0.20.0, is none: every crossing of the sharing radius is posted, once. (0.19.x defaulted to 120 and never went under 10.) A config file that still says `120` keeps it: set `0` with `social words` for every crossing |
| `SOCIAL_RULES` | `rare,military,helicopter,heavy,farthest` | same | What is worth a post; `all` is every rule at once: everything that flies over, the special aircraft first |
| `SOCIAL_HASHTAGS` | `#ADSB #avgeek #ZenithBoard` | `zenithboard social hashtags WORD...` or `social words` | Ending every post; `none` for none at all. Eight at most, letters, digits and `_`. `#avgeek` becomes `#helicopter` or `#military` when one of those is posted |
| `SOCIAL_STYLE` | `dotmap` | `zenithboard social look dotmap\|flap\|alternate` | The picture: the dot-matrix wall with a map, the split-flap board with a map, or the two in turn. `dots` (the track in dots, no map) was taken out in 0.24.0 and is read as `dotmap` |
| `SOCIAL_PLACES` | `0` | `zenithboard social places on\|off` | `1`: the town names of the maps from the region's own list, `/var/lib/zenithboard/social/places-local.tsv.gz` (0.27.0) |
| `SOCIAL_PLACES_KM` | `400` | `zenithboard config-set SOCIAL_PLACES_KM 300`, then `social places on` | How far around the receiver that list reaches (50 to 1 000 km) |
| `SOCIAL_WEEKLY` | `0` | `zenithboard social summary weekly on\|off` | `1`: a summary of the week, from the statistics (0.33.0) |
| `SOCIAL_WEEKLY_AT` · `SOCIAL_WEEKLY_PARTS` | `sun 19:00` · `1,2,3,4` | `zenithboard social summary weekly at …` · `parts …` | Its day and time on the Pi's clock, and its posts (0.38.0) |
| `SOCIAL_DAILY` · `SOCIAL_DAILY_AT` · `SOCIAL_DAILY_PARTS` | `0` · `21:00` · `1` | `zenithboard social summary daily …` | The summary of the last 24 hours (0.38.0) |
| `SOCIAL_MONTHLY` · `SOCIAL_MONTHLY_AT` · `SOCIAL_MONTHLY_PARTS` | `0` · `1 09:00` · `1,2,3,4` | `zenithboard social summary monthly …` | The summary of the last 30 days, on a day of the month 1 to 28 (0.38.0) |
| `SOCIAL_SENTENCE` | `factual` | `zenithboard social sentence LIST` | The words of a post: `factual`, `story`, `board`, `spotter`, `lookup`, `custom` (your own templates, 0.51.0), several (`story,lookup`) or `random` (0.29.0) |
| `SOCIAL_LANG` | `en` | `zenithboard social lang CODE` | The posts' language (0.51.0): every word of the aircraft posts and the summaries, numbers and dates as that language writes them; the pictures keep English |
| `SOCIAL_PHOTOLINK` | `0` | `zenithboard social photolink on\|off` | `1`: a last line linking to the aircraft's Planespotters photo page, with the photographer's name (0.25.0) |
| `SOCIAL_UNITS` | empty | `zenithboard social units metric\|imperial\|wall` | The posts' units, picture and text; empty = the wall's `UNITS` (0.24.3) |
| `SOCIAL_THEME` | empty | `zenithboard social colour NAME\|wall\|rotate` | The picture's colour: `amber`, `green`, `red`, `white`, `turquoise`; empty = the wall's `THEME`; `rotate` = the colours in turn. `blue` (taken out in 0.23.0) gives the wall's colour |
| `SOCIAL_MAP` | `normal` | `zenithboard social map NAME` | The map of the `dotmap` and `flap` pictures: `normal`, `night`, `satellite`, `terrain`, `none` (no map, nothing fetched), `rotate` (the four maps in turn) |
| `PATCHES` | `0` | `zenithboard patches on\|off` | Debian security fixes installed daily by themselves. See [Security](Security) |
| `PATCHES_PKG_BY_ZB` | `0` | set by `patches on` | Whether `patches on` installed unattended-upgrades itself, so that `patches off` knows to remove it again |
| `UPDATE_VERIFY` | `1` | by hand | Check the signature on the code before `zenithboard update` installs it. Set to `0` on a fork or your own branch. See [Security](Security) |
| `HW_NOTICE_SEEN` | unset | set by the installer | Remembers that the "this Pi model is tight for this" notice has been shown once |

The hardware watchdog and the persistent logs are **not** keys: they are system files, and `zenithboard watchdog status` / `keeplogs status` read the real state rather than a remembered one.

## ACARS (until 0.29.0)

The `ACARS_*` settings belonged to the ACARS chain that left ZenithBoard in 0.30.0. They do nothing now; `sudo zenithboard acars remove` deletes them with the rest.

## Defaults in the code

The default for every key is in one place, `lib/common.sh`, in a single block. A key missing from `config.env` falls back to that default rather than to an empty value, so an older config keeps working after an update.
