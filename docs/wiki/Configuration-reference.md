# Configuration reference

Every setting lives in one file: **`/etc/zenithboard/config.env`**. It is a plain `KEY=value` file, one per line, no quotes needed.

You rarely need to edit it by hand. Each setting has a menu entry or a command, and those validate what you give them. If you do edit it, `sudo systemctl restart zenithboard-flightinfo` is not needed for display settings — the server reads the file on every request — but it is needed for `PORT`.

Read the whole file with `zenithboard config`.

## The wall

| Key | Default | Set with | What it does |
|---|---|---|---|
| `UNITS` | `metric` | `zenithboard units metric\|imperial` | km, km/h, m — or miles, knots, feet |
| `THEME` | `amber` | `zenithboard color amber\|green\|red\|white` | Dot colour of every wall. A tablet can override it with a link |
| `DISPLAY_MODE` | `dots` | `zenithboard mode dots\|flap` | Dot matrix, or the airport split-flap board |
| `RADIUS` | `10` | `zenithboard radius N` | Detection radius in your unit. Allowed: 1, 2, 5, 10, 15, 30, 50 |
| `CYCLE_SECONDS` | `6` | `zenithboard cycle N` | How long each aircraft stays on screen |
| `SHOW_PHOTOS` | `1` | `zenithboard photos on\|off` | Aircraft photos from Planespotters. Needs internet on the Pi |
| `SHOW_ROUTES` | `1` | `zenithboard routes on\|off` | Where the flight comes from and goes to. Needs internet |
| `PORT` | `8080` | `zenithboard config-set PORT 8090` | The wall's port. Needs a restart of the service |

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
