# Roadmap

No dates. ZenithBoard is a spare-time project and a date would be a fiction. What this page promises is an order: the *Now* list is what is actually being worked on, and nothing from *Later* starts before *Now* is empty.

## Now — prove it on real hardware

The code is complete enough. What it lacks is proof.

| Item | Why it is here | How it ends |
|---|---|---|
| Try Plane Finder | The fourth feeder is installed by the menu and has never been fed. It is also the only feeder whose version is pinned ([Providers](Providers)) | It feeds, or the menu entry gets a caveat |
| Switch the Debian patches on | `zenithboard security` on the author's Pi reports it as the one warning still open that is a plain to-do (the other, SSH passwords, is a decision) | `sudo zenithboard patches on`, and a few weeks without a feeder disturbed |
| Leave the gain alone | Settled at 48.0 dB, 4–5 % strong messages at rush hour | Nothing to do. Recorded so it is not re-opened |

## Next — once the above is proven

* **Enrich the statistics page**, later, once there are some weeks of real data to look at: coverage by direction (which side of the sky the antenna hears best) and the airlines seen most often. The page today shows messages per hour, the farthest aircraft and aircraft per day ([Statistics](Statistics)); nothing is added before the real figures show what is worth drawing.
* **A decision on AirNav RadarBox.** A fifth feeder is only worth it if its MLAT does not fight the single-MLAT rule. Waiting on a few nights of data first.
* **Wi-Fi hardening**: `autoconnect-retries` and turning the radio's power saving off are two `nmcli` settings that cost nothing. No longer urgent — the night losses turned out to be an access point on a timer, not the Pi — but they would shorten the recovery when a network does come back.
* **Grafana's generated password on a real Grafana.** It is tested against stand-ins only; it gets its proof when ACARS is installed on a real Pi.

## Later — good ideas, no urgency

* Airline names for callsigns that have no route in adsbdb: a dedicated airline lookup, one request per prefix, off by default. Since 0.17.0 every airline with a known route is already named from the route answer, so this is worth doing only if bare callsigns are still common on a real wall.
* Wider silhouette coverage, so fewer aircraft fall back to the generic shape.
* The 978 MHz UAT path validated by someone in the United States. It is written and tested, and nobody has run it for real.
* Per-tablet presets, so a second screen can have its own look without a long link.
* A route source that does not need the internet, if a usable one exists. Callsign lookups are the weakest part of the wall.

## Not planned, and why

Saying no here saves answering the same question twice.

| Not planned | Why |
|---|---|
| **Airline and aircraft-maker logos** | They are trademarks, and redrawing one in dots is still the trademark. A free project cannot hand them out, and a wall of 90 logos is a licensing problem, not a feature. Flags stand in for them: the registration country next to the airline, the maker's country next to the model |
| **Sound on the wall** | An airport-hall ambience was tried (0.13.0) and removed an hour later (0.13.1): it did not sound good enough to keep. Nothing nobody has heard is shipped |
| **A cloud account, a hosted dashboard, telemetry** | The Pi is yours. Nothing should need to phone home for the wall to work. |
| **Turning off package signature checking** | It has been the quick fix for two different installer problems. It stays off the table: a signature that is not checked is not a signature. |
| **Supporting hardware other than a Raspberry Pi** | It probably works on other Debian machines; it will not be tested there, so it will not be claimed. |
| **A paid tier** | It is GPL and it stays free. There is a beer link in the README and that is the whole business model. |

## Suggesting something

Open an issue. An item moves from *Later* to *Next* because someone wants it, not because it has waited long enough.
