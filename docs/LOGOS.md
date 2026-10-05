# Airline logos, silhouettes and photos

## What you see
| Situation | Top-right of the wall |
|---|---|
| The aircraft's airline is in your logo library | the logo, in colour dots |
| No logo for that airline, or callsign without an airline (private jets, helicopters, registrations) | a **silhouette** of the matching aircraft class: airliner, widebody, turboprop, business jet, light plane, helicopter |

The class comes from the aircraft's ADS-B category and its ICAO type code (e.g. `EC35` → helicopter, `AT72` → turboprop, `A388` → widebody). The silhouettes are original drawings that ship with ZenithBoard.

## Why no ready-made logo pack?
Airline logos are trademarks. ZenithBoard does not redistribute them; you decide which ones you may display. The tool makes it a one-minute job per airline.

## Add a logo
1. Get a logo image you may use. Transparent PNG is best; a JPG or PNG on a plain background also works (the background colour of the corners is removed automatically).
2. Find the airline's **ICAO code** — the three letters at the start of its callsigns (Air France `AFR`, Lufthansa `DLH`). `zenithboard status` shows planes' callsigns, and the wall shows them live.
3. Convert and store it:
   ```bash
   sudo zenithboard logo add AFR ~/Downloads/af-logo.png
   ```
   Options for the underlying tool: `python3 /opt/zenithboard/tools/logo_tool.py add AFR logo.png --box 36x32 --colors 12`.
4. The wall picks it up within a minute. Check with `sudo zenithboard logo list`.

Tips: simple, bold logos look best at 36×32 dots. Very dark pixels are left unlit (a black LED cannot show black), so a logo with black text may need a light version.

Replace a logo by running `logo add` again; remove it with `sudo zenithboard logo remove AFR`. Files live in `/var/lib/zenithboard/logos/` and survive updates.

## Fetch logos automatically from a source
`zenithboard logo fetch AFR` downloads from a URL template you configure, converts and stores it:

```bash
sudo zenithboard config-set LOGO_URL_TEMPLATE 'https://YOUR-LOGO-SOURCE/{iata}.png'
sudo zenithboard logo fetch AFR
```

`{icao}` and `{iata}` are replaced for you (the IATA code comes from the airline list: run `sudo zenithboard data update` first for the full list). Services such as [Airhex](https://airhex.com/airline-logos/) offer airline logos through an API with an account; read the terms of whichever source you choose.

## Airline names
The first three letters of a callsign pick the airline (`AFR1234` → `AFR`). About 90 major airlines are built in. `sudo zenithboard data update` downloads the full [OpenFlights](https://openflights.org/data.html) list (ODbL licence) to `/var/lib/zenithboard/data/airlines.json`; the built-in names win when both have an entry.

## Photos
Photos come from the Planespotters API, looked up by the aircraft's ICAO hex code, fetched by the Pi and shown with an LED-style mask in the bottom-right corner, with the photographer credited at the bottom of the screen. `sudo zenithboard photos off` disables them. Many aircraft have no photo yet; the area then stays dark.

## Demo
`./bin/zenithboard-demo` uses invented airlines (Zenith Air, Nimbus Jet, Aurora Air) with original logos and generated illustrations instead of photos. `python3 tools/make_demo_assets.py` regenerates them.
