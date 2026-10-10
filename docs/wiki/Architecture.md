# Architecture

## The whole picture

```
1090 MHz dongle
      |
      v
readsb (or dump1090-fa) --- aircraft.json ---> FlightInfo server ---> tablet / TV (the wall)
      |
      +-- Beast TCP 127.0.0.1:30005 --+--> ADSB Exchange   (owns the ONE mlat client)
                                      +--> FlightAware     (MLAT off)
                                      +--> Flightradar24   (MLAT off)
                                      +--> Plane Finder

131 MHz dongle --> acarsdec --> UDP JSON --> ingester --> SQLite --> Grafana
```

Two independent chains. The ADS-B chain is the project; the ACARS chain is optional and shares nothing with it but the Pi.

## The processes

| Process | What it is | Started by |
|---|---|---|
| `readsb` or `dump1090-fa` | Decodes 1090 MHz into `aircraft.json` and a Beast stream | Its own package |
| **FlightInfo server** | `flightinfo/server.py`. Reads `aircraft.json`, works out what is in range, looks up names, routes and photos, serves the wall | `zenithboard-flightinfo.service` |
| Feeder clients | One process per sharing service, each reading the Beast stream | Their own packages |
| `acarsdec` | Decodes ACARS on a second dongle, sends JSON over UDP | `zenithboard-acarsdec.service` |
| ACARS ingester | `acars/acars_ingest.py`. Filters, writes to SQLite, deletes old rows hourly | `zenithboard-acars-ingest.service` |
| Grafana | Shows the ACARS database | Its own package |

Everything ZenithBoard installs lives in `/opt/zenithboard`. Nothing else is touched outside `/etc/zenithboard`, `/var/lib/zenithboard` and the systemd unit directory.

## Who reads and writes what

| Path | Written by | Read by |
|---|---|---|
| `/etc/zenithboard/config.env` | The menus and the `zenithboard` command | The server, every `lib/*.sh` module |
| `/run/readsb/aircraft.json` (or `/run/dump1090-fa/`) | The decoder, about once a second | The server, every refresh |
| `/run/readsb/stats.json` | The decoder | `zenithboard gain check` |
| `/var/lib/zenithboard/data/types.json` | The monthly refresh timer | The server, for silhouette names |
| `/var/lib/zenithboard/gain-log.csv` | The gain log timer, every 15 min | You, in a spreadsheet. Holds 24 h, rolling |
| `/var/lib/zenithboard/netwatch-reboot` | The network watchdog | Itself, to honour the three-hour gap |
| `/run/zenithboard-netwatch.fails` | The network watchdog | Itself. In memory on purpose: nothing writes to the SD card every two minutes |
| `/etc/default/readsb` → `RECEIVER_OPTIONS` | `zenithboard gain set` | The decoder at start |

The server never writes to the config. It reads it at each request, so a setting change shows on the wall without restarting anything.

## Ports

| Address | What |
|---|---|
| `http://<pi>:8080/` | The wall. Change with `zenithboard config-set PORT 8090` |
| `http://<pi>:8081/` | The demo, only while `zenithboard-demo` runs |
| `http://<pi>/tar1090/` | Your receiver's own map, on port 80 |
| `http://<pi>:3000/` | Grafana, only with ACARS |
| `http://<pi>:30053/` | Plane Finder's setup page |
| `127.0.0.1:30005` | The decoder's Beast stream. Local only; the feeders connect here |

## The two rules that are not obvious from the code

**One MLAT client.** Multilateration needs your receiver's timing, and several clients doing it at once on one receiver degrade all of them. ADSB Exchange owns the only MLAT client; the installer switches MLAT off in PiAware and Flightradar24. `zenithboard status` counts running MLAT processes so you can check it is exactly one, and `zenithboard mlat-guard` puts it back if a package update re-enables one.

**ACARS retention is a rolling week.** The ingester drops acknowledgements, link tests and empty messages before storing anything, then deletes rows older than `ACARS_RETENTION_DAYS` (7 by default) every hour. The database does not grow without bound and the SD card is not asked to hold a year of chatter.

## Timers

The Pi runs nothing on a schedule that you have not turned on, except the monthly data refresh.

| Timer | Interval | Does |
|---|---|---|
| `zenithboard-data-refresh.timer` | Monthly | Refreshes the aircraft-type list |
| `zenithboard-ddns.timer` | 30 s after boot, then every 5 min | Tells your dynamic-DNS provider the current address |
| `zenithboard-netwatch.timer` | Every 2 min | The network watchdog. Off by default |
| `zenithboard-logs-clean.timer` | Daily | Deletes log messages older than 7 days. Off by default |
| `zenithboard-gain-log.timer` | Every 15 min, on the quarter hour | Appends one gain measurement. Off by default |

`zenithboard-wifi.service` is not a timer: it runs once at boot to re-apply the Wi-Fi country and the on/off choice.
