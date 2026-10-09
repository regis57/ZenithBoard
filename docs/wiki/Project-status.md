# Project status

Last updated: **10 October 2026**, version **0.10.4**.

This page separates what has been proven on a real Raspberry Pi from what has only been written and unit-tested. The difference matters: every test in this project runs against stand-in programs, so a green suite proves the logic and says nothing about the hardware.

## Proven on hardware

One Raspberry Pi 3B, outdoors, on Wi-Fi, with an R820T dongle.

| Part | What is known |
|---|---|
| Install and the menus | Run end to end on a Pi 3B |
| readsb + the wall | Running continuously; the split-flap look is the one in daily use |
| Feeding ADSB Exchange | Feed received and confirmed |
| Gain tuning | `zenithboard gain check` reads real statistics; settled at **48.0 dB**, 4–5 % strong messages at rush hour |
| Route lookups | Working against adsbdb. The wrong answers it produced are what led to the plausibility filter and the hexdb second opinion in 0.9.2 |
| Reliability menu | All four options turned on and left on |
| Hardware watchdog | Installed and surviving reboots |
| Network watchdog | Did real work: three network restarts, each about three hours apart, no reboot loop |
| Persistent logs | Working, after one `sudo journalctl --flush` the first time |
| `zenithboard health` | Reports power, temperature, memory, card and the previous boot correctly |

## Written and unit-tested, not yet run for real

Treat these as likely-working rather than known-working, and please report what you find.

| Part | What is missing |
|---|---|
| Aircraft photos | The Planespotters request has only been exercised with stand-ins. Run `zenithboard photos test` on your Pi |
| 978 MHz UAT (United States) | No US hardware has run it |
| Fixed IP address and dynamic DNS | The `nmcli` calls and the provider answers are tested; a real address change and a real update were not run. Keep a keyboard and screen at hand |
| The Wi-Fi menu | Same: tested against a stand-in `nmcli`. Try it with the cable plugged in |
| FlightAware, Flightradar24, Plane Finder | The installers run; long-term feeding has not been watched |
| ACARS and Grafana | Built and tested; no long run on real traffic |

## Known rough edges

* Feeder download addresses are pinned in `lib/versions.sh` and were copied from each provider's page on 6 October 2026. Providers move files. A 404 during install usually means one line in that file needs updating.
* FlightAware and Flightradar24 keep your antenna position on their own websites. `zenithboard location` cannot change that for you; it tells you where to go.
* The airline name list covers about ninety airlines. Everything else shows the callsign.
* Routes are looked up by callsign, not by flight. A callsign can be reused for the other direction. The filter drops the impossible answers; it cannot invent the right one.
* ACARS legality differs by country. Check your local rules.

## Field log

Short notes from the Pi that is actually outside. Kept because the second time something happens, the first time is useful.

| When | What happened |
|---|---|
| 9 October 2026, 01:00 | Wi-Fi lost. The network watchdog restarted the network; the Pi recovered on its own without anyone touching it. Three restarts that night, three hours apart. Cause still open: the router's own schedule, a weak signal, or cold and damp on an outdoor install (about 6 °C). This is what added the Wi-Fi diagnostic lines in 0.10.2 |
| 8 October 2026 | Gain walked up and down the real R820T steps. 48.0 dB gives 4–5 % strong messages at rush hour, inside the 1–5 % guideline. Left there |
| October 2026 | A TV browser's top bar covered the settings gear. Moved to the bottom-right corner in 0.10.3 |
