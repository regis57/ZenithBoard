# Roadmap

No dates. ZenithBoard is a spare-time project and a date would be a fiction. What this page promises is an order: the *Now* list is what is actually being worked on, and nothing from *Later* starts before *Now* is empty.

## Now — make 0.10.x trustworthy on real hardware

The code is complete enough. What it lacks is proof.

| Item | Why it is here | How it ends |
|---|---|---|
| Try Plane Finder | The fourth feeder is installed by the menu and has never been fed | It feeds, or the menu entry gets a caveat |
| Leave the gain alone | Settled at 48.0 dB, 4–5 % strong messages at rush hour | Nothing to do. Recorded so it is not re-opened |

## Next — once the above is proven

* **A decision on AirNav RadarBox.** A fifth feeder is only worth it if its MLAT does not fight the single-MLAT rule. Waiting on a few nights of data first.
* **Wi-Fi hardening**: `autoconnect-retries` and turning the radio's power saving off are two `nmcli` settings that cost nothing. No longer urgent — the night losses turned out to be an access point on a timer, not the Pi — but they would shorten the recovery when a network does come back.

## Later — good ideas, no urgency

* More airlines in the built-in name list. It knows about ninety; everything else shows the bare callsign.
* Wider silhouette coverage, so fewer aircraft fall back to the generic shape.
* The 978 MHz UAT path validated by someone in the United States. It is written and tested, and nobody has run it for real.
* Per-tablet presets, so a second screen can have its own look without a long link.
* A route source that does not need the internet, if a usable one exists. Callsign lookups are the weakest part of the wall.

## Not planned, and why

Saying no here saves answering the same question twice.

| Not planned | Why |
|---|---|
| **Airline logos** | They are trademarks. A free project cannot hand them out, and a wall of 90 logos is a licensing problem, not a feature. |
| **A cloud account, a hosted dashboard, telemetry** | The Pi is yours. Nothing should need to phone home for the wall to work. |
| **Turning off package signature checking** | It has been the quick fix for two different installer problems. It stays off the table: a signature that is not checked is not a signature. |
| **Supporting hardware other than a Raspberry Pi** | It probably works on other Debian machines; it will not be tested there, so it will not be claimed. |
| **A paid tier** | It is GPL and it stays free. There is a coffee link in the README and that is the whole business model. |

## Suggesting something

Open an issue. An item moves from *Later* to *Next* because someone wants it, not because it has waited long enough.
