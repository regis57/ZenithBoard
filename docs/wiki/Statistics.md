# Statistics

Off by default. Switched on, the Pi takes one sample every fifteen minutes and keeps thirty days of them, so that three questions have an answer: how many messages per hour, how far the antenna reaches, how many aircraft a day.

```bash
sudo zenithboard stats on      # or: sudo zenithboard menu -> 4 Settings -> Receiver -> 5 Statistics
zenithboard stats              # in the terminal
```

and in a browser, `http://PI-ADDRESS:8080/stats`. From a tablet, the gear panel on the wall carries a link to it, beside the version — but only while statistics are on.

## What a sample is

Every quarter hour, as the `zenithboard` user and inside the same sandbox as the wall, the timer reads the decoder's `stats.json` and `aircraft.json` and writes one line to `/var/lib/zenithboard/stats/stats.csv`:

| Column | What it is |
|---|---|
| `when` | `YYYY-MM-DD HH:MM` |
| `messages` | Messages decoded in the last fifteen minutes |
| `farthest_km` | The farthest aircraft in that window, in km |
| `aircraft_pos` | Aircraft with a position at that moment |
| `aircraft_seen` | Distinct aircraft seen so far that day |

It also notes every aircraft's address into a file for the day, `seen-YYYY-MM-DD`, one per line, so the day's count is the number of distinct aircraft. About 6 KB a day on the card. After thirty days a line, or a day file, is removed.

**The daily aircraft count is a floor.** A sample every fifteen minutes misses an aircraft that crossed in less than that. Both the page and the command say so. Sampling more often would catch more of them and write to the SD card more often; fifteen minutes is the same trade the gain log makes.

## The page

Four numbers for today — aircraft, messages with the busiest hour, the farthest aircraft, the best distance of the thirty days — then three charts: messages per hour over the last twenty-four hours, the farthest aircraft per day, aircraft per day. One colour per chart, a tooltip on each bar or point, and the same numbers as a table underneath. It follows the device's light or dark setting and needs nothing from the internet.

With statistics off, the page says so and how to turn them on. `/api/stats` answers the same numbers as JSON, `{"enabled": false}` when off.

## The terminal

```
$ zenithboard stats
Statistics: on, 2785 samples of 15 minutes, 30 days kept    File: /var/lib/zenithboard/stats/stats.csv

Today        201 aircraft seen     17558 messages   farthest 329 km
Yesterday    338 aircraft seen     37090 messages   farthest 334 km
30 days      326 aircraft/day on average   best 335 km on 2026-10-02

Messages per hour today, 00 to 23
 ▁▁▁▁▁▃▃█▇▇▆▆▆▆▂▁▁▁▁▁▁▁▁▁
```

`zenithboard stats csv` prints the raw samples; `zenithboard stats status` the state and the next run; `sudo zenithboard stats clear` empties the files; `sudo zenithboard stats off` stops the timer and keeps them.

## Turning it off

`sudo zenithboard stats off` disables the timer and removes its unit files. The CSV and the day files stay where they are until `stats clear`. Nothing else in ZenithBoard reads them.

## What the page says about itself

At the foot of the page, in grey, the version the server is running, linked to that version's release notes on GitHub. The line is drawn from `/api/stats`, which carries the version whether statistics are on or off; GitHub is asked for nothing unless somebody follows the link. It is there so a screenshot of the page says which code drew it.
