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
                                      +--> AirNav Radar    (MLAT off, 0.99.6)
```

One chain. An ACARS chain (acarsdec, an ingester into SQLite, Grafana) was part of ZenithBoard until 0.29.0 and left it in 0.30.0.

## The processes

| Process | What it is | Started by |
|---|---|---|
| `readsb` or `dump1090-fa` | Decodes 1090 MHz into `aircraft.json` and a Beast stream | Its own package |
| **FlightInfo server** | `flightinfo/server.py`. Reads `aircraft.json`, works out what is in range, looks up names, routes and photos, serves the wall. With statistics on, a thread of it also looks at `aircraft.json` every five seconds for the day's farthest aircraft (0.22.0), kept in memory | `zenithboard-flightinfo.service` |
| Feeder clients | One process per sharing service, each reading the Beast stream | Their own packages |

Everything ZenithBoard installs lives in `/opt/zenithboard`. Nothing else is touched outside `/etc/zenithboard`, `/var/lib/zenithboard` and the systemd unit directory.

## Who reads and writes what

| Path | Written by | Read by |
|---|---|---|
| `/etc/zenithboard/config.env` | The menus and the `zenithboard` command | The server, every `lib/*.sh` module |
| `/run/readsb/aircraft.json` (or `/run/dump1090-fa/`) | The decoder, about once a second | The server, every refresh |
| `/run/readsb/stats.json` | The decoder | `zenithboard gain check`, the statistics sample |
| `/var/lib/zenithboard/stats/` | The statistics timer, every 15 min: `stats.csv`, `seen-DAY`, `gaps-DAY`, `farthest-DAY` | The server, for `/stats` |
| `/var/lib/zenithboard/data/types.json` | The monthly refresh timer | The server, for silhouette names |
| `/var/lib/zenithboard/gain-log.csv` | The gain log timer, every 15 min | You, in a spreadsheet. Holds 24 h, rolling |
| `/var/lib/zenithboard/netwatch-reboot` | The network watchdog | Itself, to honour the three-hour gap |
| `/run/zenithboard/zenithboard-netwatch.fails` | The network watchdog | Itself. In memory on purpose: nothing writes to the SD card every two minutes |
| `/etc/default/readsb` → `RECEIVER_OPTIONS` | `zenithboard gain set` | The decoder at start |

Since 0.99.11 `/var/lib/zenithboard` itself is root's (`root:zenithboard`, mode 3771: the services' group may add its own entries, the sticky bit keeps them from touching root's); `stats/`, `social/`, `telegram/`, the console's `state/` and `gain-log.csv` belong to the `zenithboard` user, `trust/`, `restore-pending/`, `data/`, `console/` and `console/out/` to root. Every install and update puts the owners right. The detail, and why: [Security](Security#root-never-trusts-a-path-the-service-user-owns-09911).

The server never writes to the config. It reads it again whenever the file changes (at the next request), so what the server decides by itself (who may read it, the radius `/api/planes` uses, whether a photo or a route is asked of the internet) follows a change without a restart. What a tablet reads once, when it opens the page (`/api/config`: units, colour, look, seconds per aircraft…), would not: so the commands that change it restart the wall service, and every tablet reloads itself when it sees the new `server_id` in its next answer. Those are `units`, `radius`, `color`, `mode` (the look), `cycle`, `photos on|off`, `routes on|off`, `data localdb on|off` and `config-set`, and in the menu the units, the radius, the look and colour, the seconds per aircraft and the offline database (`restart_flightinfo` in `lib/common.sh`; the menu's photos and routes switches do not restart it, the server takes them at its next request).

## Ports

| Address | What |
|---|---|
| `http://<pi>:8080/` | The wall. Change with `zenithboard config-set PORT 8090` |
| `http://<pi>:8081/` | The demo, only while `zenithboard-demo` runs |
| `http://<pi>/tar1090/` | Your receiver's own map, on port 80 |
| `http://<pi>:30053/` | Plane Finder's setup page |
| `127.0.0.1:30005` | The decoder's Beast stream. Local only; the feeders connect here |

## The two rules that are not obvious from the code

**One MLAT client.** Multilateration needs your receiver's timing, and several clients doing it at once on one receiver degrade all of them. ADSB Exchange owns the only MLAT client; the installer switches MLAT off in PiAware, Flightradar24 and AirNav Radar (`autostart_mlat=false` in `/etc/rbfeeder.ini`, 0.99.6). `zenithboard status` counts running MLAT processes so you can check it is exactly one, and `zenithboard mlat-guard` puts it back if a package update re-enables one.

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
