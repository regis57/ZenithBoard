# Roadmap

No dates. ZenithBoard is a spare-time project and a date would be a fiction. What this page promises is an order: the *Now* list is what is actually being worked on, and nothing from *Later* starts before *Now* is empty.

## Now — prove it on real hardware

The code is complete enough. What it lacks is proof.

| Item | Why it is here | How it ends |
|---|---|---|
| Try Plane Finder | The fourth feeder is installed by the menu and has never been fed. It is also the only feeder whose version is pinned ([Providers](Providers)) | It feeds, or the menu entry gets a caveat |
| Watch the Debian patches | Switched on 18 October 2026 from the menu | A few weeks without a feeder disturbed |
| **Count what the wall cannot name or draw** | Two *Later* items — airline names for bare callsigns, more silhouettes — wait on real figures, not guesses. Since 0.21.0 the statistics sampler notes, every quarter hour, each aircraft shown with a callsign but no airline (by its three-letter prefix) and each one drawn with the generic silhouette (by type code). `zenithboard stats on` must be on | After two weeks, `zenithboard stats gaps` pasted into an issue decides which prefixes get a lookup and which shapes get drawn |
| Leave the gain alone | Settled at 48.0 dB, 4–5 % strong messages at rush hour | Nothing to do. Recorded so it is not re-opened |

## What 1.0 takes

1.0 means *validated on real hardware, no caveats in [Project status](Project-status)* ([Release process](Release-process)). Each open caveat ends one way or the other:

| Caveat today | What lifts it |
|---|---|
| Plane Finder never fed | A night of feed confirmed on Plane Finder's own site — or a "not verified" caveat in the menu |
| A fixed IP address never applied for real | `zenithboard net static …` on the reference Pi, then back to DHCP, with a keyboard and screen at hand |
| ACARS + Grafana never run for long | A second dongle, a 131 MHz antenna and a week of messages — on a 2 GB board ([Hardware](Hardware)) |
| 978 MHz UAT (United States) | Run by a US user — or marked *experimental, outside 1.0*, so it stops being a caveat |

And three proofs of stability that no caveat names yet:

* **Two to four weeks hands-off**, social sharing on: no crash in `zenithboard logs`, no reboot forced by a watchdog.
* **A fresh install** on a blank card, following the README alone. Everything so far was proven on a Pi upgraded release after release; only a fresh install proves the README.
* **An update from an old release** (0.19 to the latest, say) with nothing done by hand.

## Next — once the above is proven

* **Enrich the statistics page**, later, once there are some weeks of real data to look at: coverage by direction (which side of the sky the antenna hears best) and the airlines seen most often. The page today shows messages per hour, the farthest aircraft and aircraft per day ([Statistics](Statistics)); nothing is added before the real figures show what is worth drawing.
* **A decision on AirNav RadarBox.** A fifth feeder is only worth it if its MLAT does not fight the single-MLAT rule. Waiting on a few nights of data first.
* ~~Wi-Fi hardening~~ — done in 0.21.0: `zenithboard wifi harden on`, off by default, reversible.
* **Grafana's generated password on a real Grafana.** It is tested against stand-ins only; it gets its proof when ACARS is installed on a real Pi.

## Later — good ideas, no urgency

* Airline names for callsigns that have no route in adsbdb: a dedicated airline lookup, one request per prefix, off by default. Since 0.17.0 every airline with a known route is already named from the route answer, so this is worth doing only if bare callsigns are still common on a real wall — which is what `zenithboard stats gaps` (0.21.0) now measures; see *Now*.
* Wider silhouette coverage, so fewer aircraft fall back to the generic shape: the same counter says which type codes do, and the five to ten most frequent get a shape each, previewed before it ships.
* The 978 MHz UAT path validated by someone in the United States. It is written and tested, and nobody has run it for real.
* ~~Per-tablet presets~~ — done in 0.21.0: `zenithboard preset add kitchen theme=green mode=flap`, then `?p=kitchen` on that tablet.

## Not planned, and why

Saying no here saves answering the same question twice.

| Not planned | Why |
|---|---|
| **Airline and aircraft-maker logos** | They are trademarks, and redrawing one in dots is still the trademark. A free project cannot hand them out, and a wall of 90 logos is a licensing problem, not a feature. Flags stand in for them: the registration country next to the registration (since 0.20.0), the maker's country next to the model |
| **Sound on the wall** | An airport-hall ambience was tried (0.13.0) and removed an hour later (0.13.1): it did not sound good enough to keep. Nothing nobody has heard is shipped |
| **A cloud account, a hosted dashboard, telemetry** | The Pi is yours. Nothing should need to phone home for the wall to work. |
| **Turning off package signature checking** | It has been the quick fix for two different installer problems. It stays off the table: a signature that is not checked is not a signature. |
| **Supporting hardware other than a Raspberry Pi** | It probably works on other Debian machines; it will not be tested there, so it will not be claimed. |
| **A route source that does not need the internet** | There is no free, complete and current database of routes by callsign: the public ones are partial, stale, or under licences a GPL project cannot carry, and a stale route shown with confidence is worse than none. Callsign lookups stay online (adsbdb, hexdb as a second opinion), cached, and off when the Pi is |
| **A paid tier** | It is GPL and it stays free. There is a beer link in the README and that is the whole business model. |

## Suggesting something

Open an issue. An item moves from *Later* to *Next* because someone wants it, not because it has waited long enough.
