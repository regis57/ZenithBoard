# The wall

The wall is one HTML page served by `flightinfo/server.py`, drawn on a single `<canvas>`. No framework, no build step: `flightinfo/static/` is what the browser gets.

## The dot grid

Everything is laid out on a fixed grid of **128 × 80 dots** (16:10), not in pixels. The browser window only decides how big a dot is:

```
pitch = min(width / (GW + 3), height / (GH + 3))
```

The `+ 3` leaves a margin, and the grid is then centred with an `ox` / `oy` offset. One consequence worth knowing: the wall never reflows. A phone and a 4K television show the same layout, just at different dot sizes. That is why it reads correctly from across a room.

## What sits where

| Area | Grid box | Holds |
|---|---|---|
| Text | left of column 86 | Callsign, airline, type, altitude, speed, distance, route — 14 characters per row |
| Silhouette | x 90, y 0, 38 × 34 | The aircraft seen from above, drawn in dots |
| Photo or scene | x 86, y 38, 42 × 30 | A real photo from Planespotters, or an animated side view when there is none |
| Free | below row 68, on the right | Deliberately empty. The settings gear lives here |

The photo box ends at row 68 of 80, which leaves the bottom-right corner clear. That is what makes the gear's new position safe.

## The settings gear

A faint circle in the **bottom-right corner** (it was top-right until 0.10.3). Tap it for units, radius, seconds per plane, colour, full screen and reset.

It moved because televisions put their browser bar at the top of the screen, sliding down over anything in that corner and making the gear unreachable. The bottom-right corner has no such furniture, and the box above it is free.

Two details follow from the corner it is in: the panel opens **upward** from the gear, and on a short screen it scrolls rather than running off the top. `tests/test_layout.js` checks on fifteen screen sizes that the gear never overlaps the photo box or the silhouette and stays on screen.

Choices made in the gear are stored in that browser only. They override the Pi's settings for that tablet and nothing else. **Reset** returns the tablet to the Pi's own settings.

## Two looks

| Mode | What it looks like |
|---|---|
| `dots` | The dot-matrix wall: text on the left, silhouette and photo on the right. The default |
| `flap` | An airport split-flap board: 16 letters × 8 rows on the left 84 dots, with the flaps rolling as the text changes. The photo column stays |

Set it for the whole Pi with `zenithboard mode dots|flap`, or per tablet with a link.

## Per-tablet links

Every display setting can ride in the address, which is how one Pi drives several screens that each look different:

```
http://<pi>:8080/?theme=green&mode=flap&units=imperial&radius=5&cycle=8
```

A link beats the gear when you are setting up a screen you will not touch again — a television with no keyboard, for instance. The link wins over the Pi's setting, and the gear wins over the link.

## Colours

Four themes: amber (the default), green, red, white. One dot colour at a time, because the point is a lit sign rather than a screenshot of a map.

## Staying up

The page refreshes itself. It polls `/api/planes` for the aircraft inside the radius, cycles through them at `CYCLE_SECONDS` each, keeps the screen awake, and reloads itself if the Pi restarts — so a power cut ends with the wall back on screen and nobody touching the tablet. If the decoder stops answering it says **NO DATA – RECEIVER NOT RESPONDING** instead of showing stale aircraft.

It also respects `prefers-reduced-motion`: with that set in the browser, the flap animation and the scene stop moving.

## Full screen

Either tap the gear → **Full screen**, or use the browser's *Add to Home Screen*, which gives a cleaner result because the browser's own bars disappear for good.
