# ZenithBoard — ADSB Flight Info

**See the planes flying right above your house, on an old tablet, in glowing dot-matrix lights — and share the same antenna with the big flight-tracking networks.**

ZenithBoard turns a Raspberry Pi (4 or newer recommended) and a cheap USB radio dongle into:

1. **An ADS-B receiver** that feeds **ADSB Exchange** (mandatory base layer) and, if you want, **FlightAware**, **Flightradar24** and **Plane Finder** — with **one single MLAT client**, because several at once overload a Raspberry Pi.
2. **FlightInfo**, a responsive **dot-matrix wall** for any tablet or screen with a browser. It automatically cycles through every aircraft inside the radius you choose (1, 2, 5, 10, 15, 30 or 50 km / miles) — callsign, type, altitude, speed, heading, climb/descent, distance and direction — and refreshes itself.
3. **ACARS** *(optional)*: aircraft text messages collected with a second dongle and shown in **Grafana**, filtered, and automatically rolled and cleaned every 7 days.

Everything is installed from one menu, and you can come back at any time to add or remove parts.

> **Status: v0.1 (early).** The wall, the configuration tools and the tests work and are verified on a PC. The installer scripts have **not yet been run on real Raspberry Pi hardware** — please try it and open an issue with anything that breaks. See [Known limits](#known-limits).

Inspired by [jprochazka/adsb-receiver](https://github.com/jprochazka/adsb-receiver). ZenithBoard is an independent project with a smaller scope, not a fork.

---

## What you need

| Item | Notes |
|---|---|
| Raspberry Pi **4 or newer** | 2 GB+ recommended (1 GB is enough without ACARS). Raspberry Pi OS **Lite** (Bookworm or newer). See [Which Raspberry Pi?](#which-raspberry-pi) |
| Micro-SD card 16 GB+ | |
| **RTL-SDR dongle** + **1090 MHz antenna** | A dongle with a built-in 1090 filter (e.g. "ADS-B" or "FlightAware Pro Stick") gives the best range. |
| *(optional)* a **second** RTL-SDR dongle + 131 MHz antenna | Only for ACARS. The ADS-B dongle cannot do both. See [docs/HARDWARE.md](docs/HARDWARE.md). |
| An old tablet or any screen | Anything with a modern browser on your home Wi-Fi. |
| Accounts | A free [ADSB Exchange](https://www.adsbexchange.com/myip/) key is asked during setup. FlightAware / Flightradar24 / Plane Finder accounts only if you choose them. |

### Which Raspberry Pi?

Estimates, not yet measured on real boards.

| Board | ADS-B + feeders + wall | + ACARS & Grafana |
|---|---|---|
| **Pi 5 / Pi 4, 2 GB or more** | Comfortable | Comfortable (Pi 4 with 2 GB: fine) |
| **Pi 4, 1 GB** | Good (about 400–550 MB used). Keep to one or two extra feeders. | Not recommended: about 900 MB more needed |
| **Pi 3B / 3B+ (1 GB)** | Works. Prefer Ethernet and a good power supply. | Not recommended (Grafana is slow, `acarsdec` takes long to build) |
| Pi Zero 2 W / Pi 2 | ADS-B and the wall only, no extra feeders | No |

The installer detects the board and its memory, warns you once, and marks ACARS as *not recommended* in the menu on low-memory or older boards (you can still continue). `zenithboard status` shows the free memory.

---

## Install — step by step

### 1. Prepare the SD card
1. Install **Raspberry Pi Imager** from <https://www.raspberrypi.com/software/>.
2. Choose *Raspberry Pi 4*, then **Raspberry Pi OS Lite (64-bit)** (under "Raspberry Pi OS (other)"), then your SD card.
3. Click **Edit settings** and fill in: hostname (e.g. `zenithboard`), your username + password, your Wi-Fi (skip if you use Ethernet), time zone, and **enable SSH**.
4. Write the card, put it in the Pi, plug in the dongle (a USB 2.0 port is best) and power on. Wait 2–3 minutes.

### 2. Connect to the Pi
From your computer's terminal (Windows 10/11, macOS and Linux all have one):

```bash
ssh YOUR_USERNAME@zenithboard.local
```

If the name is not found, use the Pi's IP address from your router instead.

### 3. Download and run ZenithBoard
```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/regis57/ZenithBoard.git
cd ZenithBoard
sudo ./install.sh
```

### 4. Answer the first questions
The first run asks, once:

* **Units** — *metric* (km, km/h, metres, m/s) or *imperial* (miles, knots, feet, ft/min).
* **Antenna position** — latitude, longitude, altitude (needed by the decoder, MLAT and the wall's distance calculation). Tip: right-click your house in Google Maps to copy the coordinates.
* **Default radius** — how close a plane must be to appear on the wall.

### 5. Use the menu
```
 1  ADSB        decoder + share to ADSB Exchange, FlightAware, FR24 ...
 2  FlightInfo  dot-matrix wall for an old tablet
 3  ACARS       optional ACARS messages in Grafana (2nd dongle)
 4  Settings    units, radius, antenna position
 5  Status      what is running
 6  Update      upgrade ZenithBoard, decoder, feeders, ACARS
 7  Uninstall everything
```

**1 · ADSB** — pick the decoder (**readsb** is recommended; **dump1090-fa** is supported as an alternative; both feed the same local port so every feeder works with either). Then tick where to share. *ADSB Exchange is always on.* The ADSB Exchange script will ask for a station name and your position, and prints a link to see your feed. FlightAware prints a claim link; Plane Finder finishes setup on a small web page. Unticking an installed feeder removes it after a confirmation.

**2 · FlightInfo** — installs the wall. At the end it prints the address, e.g. `http://192.168.1.50:8080/`.

**3 · ACARS** *(optional)* — asks for the second dongle's serial number and your frequencies, builds `acarsdec`, installs Grafana and a ready-made dashboard at `http://<pi-address>:3000/` (first login `admin` / `admin`, you are asked to change it).

### 6. Put the wall on the tablet
Open the address from step 2 in the tablet's browser. Tap the browser's *Add to Home Screen* for a full-screen app look, or tap the faint gear in the top-right corner → **Full screen**. The screen stays awake and the page reloads itself if the Pi restarts.

Check that everything is healthy at any time:

```bash
zenithboard status
```

---

## Changing units, radius and position later

Three ways, pick the one that suits you.

| Where | How |
|---|---|
| **Command line** (affects every screen) | `sudo zenithboard units imperial` · `sudo zenithboard units metric` · `sudo zenithboard radius 5` · `sudo zenithboard cycle 8` |
| **Menu** | `sudo zenithboard menu` → *4 Settings* |
| **On the tablet** (that tablet only) | Tap the faint gear in the top-right corner: units, radius, seconds per plane, colour (amber / green / red / white). Or use a link: `http://<pi>:8080/?units=imperial&radius=5&theme=green` |

Radius presets are **1, 2, 5, 10, 15, 30, 50** — read as kilometres in metric mode and miles in imperial mode. Changes apply immediately, no restart or reinstall.

### Moving the antenna (position)

```bash
sudo zenithboard location 49.246 6.223 210      # latitude, longitude, altitude in metres
```

(or menu *4 Settings → Antenna position*). The position is updated **everywhere ZenithBoard can reach**: the wall, readsb / dump1090-fa, ADSB Exchange (including its MLAT) and Plane Finder. A summary then lists anything only the provider's website can change (FlightAware and Flightradar24 hold your position in your online account) with the page to open.

All settings live in one readable file: `/etc/zenithboard/config.env`.

---

## What the wall shows

```
+--------------------------------------+---------------+
| ZZA210                               |   AIRLINE     |
| ZENITH AIR                           |   LOGO  or    |
| A320 F-ZZAA                          |   aircraft    |
| ALT  35000 FT                        |   silhouette  |
| SPD  450 KT                          |               |
| HDG  270° W                          +---------------+
| V/S  ↑1200 FPM                       |  photo of the |
|                                      |  plane (LED   |
| 6/7 3.6MI NNE            R 10 MI     |  look)        |
+--------------------------------------+---------------+
```

* **Left:** callsign, airline name, aircraft type and registration, altitude, speed, heading, climb/descent, then *position in the cycle*, distance and the direction **from you** (`NNE`), and your radius. `HDG` is where the plane is heading.
* **Top right:** the airline's **logo** in colour dots when you have one in your library, otherwise a **silhouette of the right kind of aircraft** (airliner, widebody, turboprop, business jet, light plane, helicopter). See [Airline logos](#airline-logos-and-photos).
* **Bottom right:** a **photo of the aircraft** (from [Planespotters](https://www.planespotters.net/), credited at the bottom of the screen) shown through an LED-style mask, when one exists. The photos are fetched by the Pi, so the tablet does not need internet.
* Aircraft are shown nearest first, one at a time, for a few seconds each, with a wipe transition. With nothing in range the wall shows a clock and how many aircraft your antenna sees.

## Colours

The dots are **amber by default**. Pick amber, green, red or white:

| Where | How |
|---|---|
| **Every screen** | `sudo zenithboard color green` (back to the default: `sudo zenithboard color amber`) |
| **Menu** | `sudo zenithboard menu` → *4 Settings → Colour* |
| **One tablet only** | Tap the faint gear in the top-right corner → *Colour*. Or open `http://<pi>:8080/?theme=red`. The gear's **Reset** returns that tablet to the Pi's colour. |

## Airline logos and photos

**No real airline logos are bundled with ZenithBoard** — they are trademarks, and the right to display them is yours to judge. Instead you get a small logo library you control:

```bash
sudo zenithboard logo add AFR ~/Downloads/airline-logo.png    # convert YOUR image to dot-matrix and store it
sudo zenithboard logo list
sudo zenithboard logo remove AFR
sudo zenithboard data update                                  # download the full airline-name list (OpenFlights data)
```

Every logo image (PNG with transparency is best; JPG on a plain background works too) is converted to at most 12 colours on a 36×32 dot grid and stored in `/var/lib/zenithboard/logos/`. They survive updates. Add, replace or remove one at any time; the wall picks it up within a minute. Airlines without a logo get the aircraft silhouette. More in [docs/LOGOS.md](docs/LOGOS.md), including how to fetch logos automatically from a source of your choice (e.g. a logo service such as [Airhex](https://airhex.com/airline-logos/), which needs its own account and terms).

How an aircraft is matched to an airline: the first three letters of the callsign (`AFR1234` → `AFR` → Air France). The built-in list covers about 90 major airlines; `zenithboard data update` loads the full list.

Photos can be switched off with `sudo zenithboard photos off`, and logos with `sudo zenithboard config-set SHOW_LOGOS 0`.

### Try it without any hardware
The demo uses invented airlines (with original logos), a helicopter, a turboprop, a business jet and mock illustrations instead of photos. Run it from the ZenithBoard folder on any computer or Pi with Python 3:

```bash
./bin/zenithboard-demo                  # metric, amber
./bin/zenithboard-demo imperial green   # units, then colour
```

Then open **`http://<the-pi-address>:8081/`** (or `http://localhost:8081/` on the same computer).

> **Do not run the demo on port 8080.** The real wall already uses 8080 once FlightInfo is installed, and a second program on the same port fails with `Address already in use`. The demo therefore defaults to **8081**. If 8081 is also taken: `PORT=8082 ./bin/zenithboard-demo`.

---

## Network ports (what answers where)

| Address | What | Notes |
|---|---|---|
| `http://<pi>:8080/` | **ZenithBoard wall** | Change with `sudo zenithboard config-set PORT 8090` |
| `http://<pi>:8081/` | ZenithBoard **demo** | Only while `zenithboard-demo` runs |
| `http://<pi>/adsbx/` | **ADSB Exchange map of your own receiver** | Served on **port 80**, so it never clashes with 8080. Some installs use `http://<pi>/tar1090/`. |
| <https://www.adsbexchange.com/myip/> | ADSB Exchange feed status | Open it from the same network as the Pi: it tells you whether your feed is received |
| `http://<pi>:3000/` | Grafana (ACARS) | Only if ACARS is installed |
| `http://<pi>:30053/` | Plane Finder setup page | Only if Plane Finder is installed |

`zenithboard status` prints the ones that apply to your Pi.

---

## How it fits together

```
1090 MHz dongle
      |
      v
readsb (or dump1090-fa) --- aircraft.json ---> FlightInfo server ---> tablet (dot-matrix wall)
      |
      +-- Beast TCP 127.0.0.1:30005 --+--> ADSB Exchange   (+ the ONE mlat client)
                                      +--> FlightAware     (MLAT off)
                                      +--> Flightradar24   (MLAT off)
                                      +--> Plane Finder

131 MHz dongle --> acarsdec --> UDP JSON --> ingester (filter, 7-day rolling) --> SQLite --> Grafana
```

**Single MLAT:** ADSB Exchange owns the only MLAT client. The installer switches MLAT off in PiAware and Flightradar24, and `zenithboard status` counts running MLAT processes so you can verify it is exactly one.

**ACARS retention:** the ingester drops acknowledgements, link tests and empty messages (configurable in `config.env`) and deletes everything older than `ACARS_RETENTION_DAYS` (default 7) every hour.

---

## Updating and uninstalling

**One command updates everything** (ZenithBoard itself from GitHub, readsb / dump1090-fa, ADSB Exchange, FlightAware, Flightradar24, Plane Finder, acarsdec, Grafana). Your settings are kept:

```bash
sudo zenithboard update
```

The same is available in the menu (*6 Update*). Run it whenever a provider releases a new version, or once a month. If a provider changes a download link, edit it in [`lib/versions.sh`](lib/versions.sh) and run the update again.

```bash
sudo zenithboard menu                                 # add or remove any component at any time
sudo /opt/zenithboard/install.sh --uninstall-all      # remove everything
```

---

## Troubleshooting

| Symptom | Try |
|---|---|
| Wall says **NO DATA – RECEIVER NOT RESPONDING** | `zenithboard status` — is the decoder running? `zenithboard logs decoder`. Dongle plugged in and not shared with ACARS? |
| Wall says NO FLIGHTS for a long time | Raise the radius (`sudo zenithboard radius 30`). Check `zenithboard status` for the aircraft count. |
| Wall opens but looks cropped | Use the gear → **Full screen**, or *Add to Home Screen*. |
| Two MLAT clients in `status` | `sudo zenithboard mlat-guard` |
| ACARS panels empty | `zenithboard logs acars`; confirm the ACARS dongle serial in `zenithboard config` and that frequencies are correct for your region. |
| Grafana asks for a login | Default `admin` / `admin`. Menu 3 can allow anonymous *viewing* on your LAN only. |

---

## Known limits

* **Not yet validated on a real Raspberry Pi** — third-party installers (readsb, ADSB Exchange, Flightradar24, Plane Finder, `acarsdec`) change over time. Version pins and URLs are all in [`lib/versions.sh`](lib/versions.sh).
* The Plane Finder package URL for 64-bit systems must be checked against their site.
* FlightAware and Flightradar24 store your antenna position on their websites: after `zenithboard location`, update it there too (the command tells you where).
* ACARS legality differs per country — check your local rules before collecting ACARS messages.
* Photos come from Planespotters and need internet on the Pi. Logos and the airline list are optional extras you add yourself.

## Contributing & tests

```bash
python3 -m unittest discover -s tests -v     # server + ACARS
node tests/test_format.js                    # wall formatting / units
shellcheck -x install.sh bin/* lib/*.sh      # installer
```

## License

ZenithBoard is free software under the **GNU General Public License v3.0 or later** — see [LICENSE](LICENSE).
