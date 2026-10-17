# Configuration reference

Every setting lives in one file: **`/etc/zenithboard/config.env`**. It is a plain `KEY=value` file, one per line, no quotes needed.

You rarely need to edit it by hand. Each setting has a menu entry or a command, and those validate what you give them. If you do edit it, `sudo systemctl restart zenithboard-flightinfo` is not needed for display settings — the server reads the file on every request — but it is needed for `PORT`.

Read the whole file with `zenithboard config`.

## The wall

| Key | Default | Set with | What it does |
|---|---|---|---|
| `UNITS` | `metric` | `zenithboard units metric\|imperial` | km, km/h, m — or miles, knots, feet |
| `THEME` | `amber` | `zenithboard color amber\|green\|red\|white\|turquoise\|blue` | Dot colour of every wall. A tablet can override it with a link |
| `DISPLAY_MODE` | `dots` | `zenithboard mode dots\|flap` | Dot matrix, or the airport split-flap board |
| `RADIUS` | `10` | `zenithboard radius N` | Detection radius in your unit. Allowed: 1, 2, 5, 10, 15, 30, 50 |
| `CYCLE_SECONDS` | `14` | `zenithboard cycle N` | How long each aircraft stays on screen. A row too long for its width scrolls once in that time |
| `SHOW_PHOTOS` | `1` | `zenithboard photos on\|off` | Aircraft photos from Planespotters. Needs internet on the Pi |
| `FLAGS` | `1` | the gear on the tablet, or this line | The two flags on the dot-matrix wall: where the aircraft is registered, and where it was built. With them on, the airline and model rows hold twelve characters instead of fourteen |
| `SHOW_ROUTES` | `1` | `zenithboard routes on\|off` | Where the flight comes from and goes to. Needs internet |
| `PORT` | `8080` | `zenithboard config-set PORT 8090` | The wall's port. Needs a restart of the service |
| `BIND_ADDRESS` | `0.0.0.0` | `zenithboard config-set BIND_ADDRESS 127.0.0.1` | The interface the wall listens on. `127.0.0.1` keeps it to this Pi (behind a reverse proxy, say). Needs a restart of the service |
| `ALLOW_FROM` | `private` | `zenithboard config-set ALLOW_FROM any` | Who may read the wall: `private` (home networks: 10/8, 172.16/12, 192.168/16, the Pi itself, link-local and their IPv6 equivalents), `all`, or a list of networks such as `10.8.0.0/24,100.64.0.0/10`. Anyone else gets a 403. An unreadable value means `private` |

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
| `STATS` | `0` | `zenithboard stats on\|off` | A sample every 15 minutes for the `/stats` page and `zenithboard stats`. See [Statistics](Statistics) |
| `SOCIAL` | `0` | `zenithboard social on\|off` | Post the aircraft overhead to Bluesky. See [Social sharing](Social-sharing). The account's secret is in `social.env`, not here |
| `SOCIAL_RADIUS_KM` | `15` | `zenithboard social words` | An aircraft is a candidate while inside it. Separate from `RADIUS` |
| `SOCIAL_AREA` | empty | same | The place named in the posts, in your words: a town name (`Trémery`) reads *above Trémery*, a phrase (`near Metz`) is kept. Never derived from the position |
| `SOCIAL_GAP_MIN` | `120` | same | At least this many minutes between two posts; never under 10, whatever is set (a value under it is used as 10 and `social status` says so) |
| `SOCIAL_RULES` | `rare,military,helicopter,heavy,farthest` | same | What is worth a post; `all` is every rule at once: everything that flies over, the special aircraft first |
| `SOCIAL_HASHTAGS` | `#ADSB #avgeek #ZenithBoard` | this line | Appended to every post |
| `SOCIAL_STYLE` | `dots` | `zenithboard social look dots\|flap\|alternate` | The picture: the dot-matrix wall with the track in dots, the split-flap board with a map, or the two in turn |
| `SOCIAL_THEME` | empty | `zenithboard social colour NAME\|wall\|rotate` | The picture's colour: `amber`, `green`, `red`, `white`, `turquoise`, `blue`; empty = the wall's `THEME`; `rotate` = the colours in turn, all but blue |
| `SOCIAL_MAP` | `normal` | `zenithboard social map NAME` | The split-flap picture's map: `normal`, `night`, `satellite`, `terrain`, `none` (no map, nothing fetched), `rotate` (the four maps in turn) |
| `PATCHES` | `0` | `zenithboard patches on\|off` | Debian security fixes installed daily by themselves. See [Security](Security) |
| `PATCHES_PKG_BY_ZB` | `0` | set by `patches on` | Whether `patches on` installed unattended-upgrades itself, so that `patches off` knows to remove it again |
| `UPDATE_VERIFY` | `1` | by hand | Check the signature on the code before `zenithboard update` installs it. Set to `0` on a fork or your own branch. See [Security](Security) |
| `HW_NOTICE_SEEN` | unset | set by the installer | Remembers that the "this Pi model is tight for this" notice has been shown once |

The hardware watchdog and the persistent logs are **not** keys: they are system files, and `zenithboard watchdog status` / `keeplogs status` read the real state rather than a remembered one.

## ACARS

| Key | Default | What it does |
|---|---|---|
| `ACARS_SDR` | empty | Serial of the ACARS dongle. Must differ from `ADSB_SDR` |
| `ACARS_FREQS` | `131.525 131.725 131.825` | Frequencies in MHz, up to 8. The US set is `131.550 130.025 129.125` |
| `ACARS_RETENTION_DAYS` | `7` | Rows older than this are deleted hourly |
| `ACARS_IGNORE_EMPTY` | `1` | Drop messages with no text |
| `ACARS_IGNORE_LABELS` | `_d,Q0,SQ` | Labels dropped before storing: acknowledgements and link tests |
| `ACARS_UDP_PORT` | `5555` | Where `acarsdec` sends and the ingester listens. Local only |
| `ACARS_DB` | `/var/lib/zenithboard/acars.db` | The SQLite file Grafana reads |

## Defaults in the code

The default for every key is in one place, `lib/common.sh`, in a single block. A key missing from `config.env` falls back to that default rather than to an empty value, so an older config keeps working after an update.
