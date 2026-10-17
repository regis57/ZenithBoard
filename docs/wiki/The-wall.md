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
| Text | left of column 86 | Nine rows of 14 characters: `FLT  BAW123`, `REG  G-XLEA` (the flight and the registration, labelled like the rows under them, since 0.19.0; before, the callsign alone stood two rows high), airline, type, altitude, speed, route, and the last row with the distance and bearing |
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
| `flap` | An airport split-flap board: 16 letters × 9 rows on the left 84 dots, with the flaps rolling as the text changes. The photo column stays |

Set it for the whole Pi with `zenithboard mode dots|flap`, or per tablet with a link.

## Per-tablet links

Every display setting can ride in the address, which is how one Pi drives several screens that each look different:

```
http://<pi>:8080/?theme=green&mode=flap&units=imperial&radius=5&cycle=8
```

A link beats the gear when you are setting up a screen you will not touch again — a television with no keyboard, for instance. The link wins over the Pi's setting, and the gear wins over the link.

## Colours

Six themes: amber (the default), green, red, white, turquoise (`#00d6d7`) and blue (`#0404e2`). One dot colour at a time, because the point is a lit sign rather than a screenshot of a map. Blue is the deepest of the six: on a dark wall at a distance it reads as a quiet navigation light rather than as text, so try turquoise first if the board is meant to be read from the sofa.

## The two flags

On the dot-matrix wall, a small flag sits at the right of the airline row and another at the right of the model row. The first is where the aircraft is registered, the second is where it was built. Both are drawn into the same dot grid as everything else, eleven dots by seven, so they scale with the wall rather than needing a size of their own.

The country comes from the registration the wall already receives: `OE-LMP` is Austria, `HB-` Switzerland, `N` the United States, `CN-` Morocco and not Canada, because the longest prefix wins. It is a published allocation table held in `flags.js`, so there is no lookup and nothing to reach over the network. A registration whose prefix is not in the table shows no flag rather than a wrong one.

The second flag is the country the airframe comes from: European for Airbus and ATR, American for Boeing, Brazilian for Embraer, Canadian for De Havilland. **No manufacturer's logo is drawn, in dots or otherwise.** Those marks are protected, and redrawing one in dots is still redrawing it. A country is not protected, which is why the badge shows one.

At eleven dots a flag is its bands of colour. Flags carrying an emblem keep the colours and lose the emblem: Portugal has no armillary sphere, the United Kingdom's crosses do not have their true widths, Morocco's star is five dots. They are made to be recognised across a room.

A flag's colours are never changed to make it show: the black of a flag stays black, a navy stays that navy. What a flag that would be invisible against the black wall gets instead is a one-dot white outline, so its edge is there to see. Two kinds qualify. The first carries black — Germany, Belgium, Estonia, Egypt, the United Arab Emirates. The second is simply too dark: the union flag is two thirds `#012169`, and at eleven dots on an unlit wall it read as a hole rather than a flag, which is how a British Airways aircraft came to look as though it had no flag at all (found on the real wall, 0.17.1). The United Kingdom is the only flag the second rule catches today; `tests/test_flags.js` holds the list, so a flag cannot quietly join or leave it. Every other flag is drawn bare, with nothing around it.

The two flags cost the airline and model rows two characters each, twelve instead of fourteen. The model row answers that by dropping the maker's name as soon as the whole does not fit: `AIRBUS A-380-800` becomes `A-380-800` and stands still, because a short name read at a glance beats a long one walking past. Only what is still too long without its maker scrolls. A name that no longer fits turns continuously: the row holds the name, three spaces, then the name again, and the window walks one length before starting over, so what leaves on the left is already arriving on the right. One dot every 110 milliseconds, and only those two rows are repainted rather than the whole wall. An aircraft stays on screen for fourteen seconds by default, which is time enough for a long name to come round.

Flags are a dot-matrix matter. The split-flap board is sixteen letter drums and a flag is not a letter, so it shows none.

| | |
|---|---|
| For every screen | `FLAGS` in `/etc/zenithboard/config.env`, then `zenithboard config` |
| For this tablet only | the gear, **Flags**, or `?flags=0` in the address |

At the foot of the gear panel sits one grey line: the version the wall is running, and behind it the release notes for that version on GitHub. When statistics are on, the way to the [statistics page](Statistics) sits beside it in the same grey; switch them off and the link goes, because the page would only say it is off. It is a link and nothing more — the page asks GitHub for nothing, so a wall with no way out to the internet still names its version. The statistics page carries the same line at its foot.

## Staying up

The page refreshes itself. It polls `/api/planes` for the aircraft inside the radius, cycles through them at `CYCLE_SECONDS` each, keeps the screen awake, and reloads itself if the Pi restarts — so a power cut ends with the wall back on screen and nobody touching the tablet. If the decoder stops answering it says **NO DATA – RECEIVER NOT RESPONDING** instead of showing stale aircraft.

It also respects `prefers-reduced-motion`: with that set in the browser, the flap animation and the scene stop moving.

## Full screen

Either tap the gear → **Full screen**, or use the browser's *Add to Home Screen*, which gives a cleaner result because the browser's own bars disappear for good.
