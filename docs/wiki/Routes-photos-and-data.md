# Routes, photos and data

The wall knows four things the radio does not tell it: which airline a callsign belongs to, what the aircraft model is, where the flight is going, and what the aircraft looks like. Three of those come from the internet, which raises a question the design has to answer: **what happens to a wall whose Pi cannot reach the internet?** The answer throughout is *it shows less, it never stalls and it never shows something wrong*.

## The sources

| What | Source | Needs internet |
|---|---|---|
| Airline name | Built-in list, about 90 major airlines | No |
| Aircraft model name | `types.json`, refreshed monthly | Only for the refresh |
| Route (from → to) | [adsbdb.com](https://www.adsbdb.com/) by callsign, with [hexdb.io](https://www.hexdb.io/) as a second opinion | Yes |
| Photo | [Planespotters](https://www.planespotters.net/) by ICAO hex | Yes |
| Silhouette | Drawn in code from the aircraft type | No |

## Nothing blocks the display

Every outside lookup goes through `ThrottledLookup`, and the rule is absolute: **the display loop never waits for the network.** A lookup that is not answered yet returns nothing, the wall draws the row without it, and the answer appears on a later pass. At most one request leaves every 1.5 seconds, however many aircraft are overhead.

Answers are cached, and so are the failures — a missing answer that was not cached would be asked again every few seconds for as long as that aircraft is in range:

| Case | Asked again after |
|---|---|
| A route was found | 12 hours |
| The callsign is not in the database | 2 hours |
| No answer at all (error, timeout, no internet) | 1 minute |

Twelve hours is not about load. A callsign is reused: today's AF1234 and tomorrow's AF1234 need not be the same route.

## Why routes are the weakest part

The route databases know **callsigns, not flights**. A callsign is reused for the return leg, and reassigned over time. Ask about one and you may get yesterday's route, or the same route backwards.

So the answer is checked against the aircraft in front of you before it is shown. An answer is dropped when:

* origin and destination are the same airport — *East Midlands → East Midlands* was a real sighting;
* the aircraft is more than **120 km** from the straight line between the two airports, or more than **20 %** of the route length when that is further;
* the aircraft is heading more than **100°** away from the destination, which usually means the callsign's other direction.

A blank route row is better than a wrong one.

When adsbdb's answer is dropped, **hexdb.io is asked once** as a second opinion, and the wall takes the first leg of that route the aircraft can actually be on. If hexdb is unreachable, nothing is shown and nothing wrong is remembered.

The airport positions used for these checks are never displayed. They exist only to judge plausibility, and are fetched once per airport and kept until the next restart.

## Photos

Looked up by the aircraft's ICAO hex, which is a far better key than a callsign: it identifies the airframe. Photos are cached, credited to the photographer on screen, and optional — `zenithboard photos off`.

With no photo available, the corner shows an animated sky scene with a side view of the matching model, rather than an empty box. Most aircraft have no photo on a quiet night, so this is the normal case rather than the fallback.

`zenithboard photos test` makes one real request and tells you whether this Pi can reach the service at all. It is the right command when the corner is always a drawing.

## The aircraft type list

`types.json` turns an ICAO type code into a readable name and picks the silhouette. It is refreshed monthly by a timer; `zenithboard data update` does it now, `zenithboard data status` says when it last happened, and `zenithboard data auto off` stops it. An out-of-date list costs you nothing but the newest models' names.

## If you see a wrong route

Worth reporting, with the callsign and the time. The plausibility rules are deliberately loose — a real flight can be diverted 100 km off its line — so an answer that is wrong but geometrically possible will get through. Those are the cases that improve the filter.
