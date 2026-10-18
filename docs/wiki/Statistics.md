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

**What the wall could not name or draw (0.21.0).** Each sample also asks the wall, on the loopback, which aircraft are inside its radius, and notes once per aircraft the callsign prefixes shown without an airline name and the type codes drawn with the generic silhouette, in `gaps-YYYY-MM-DD` files kept thirty days. `zenithboard stats gaps` prints the counts; what they are for is on the [Roadmap](Roadmap#deciding-the-airline-lookup-and-the-new-silhouettes-on-figures).

**Which aircraft was the farthest (0.22.0).** The decoder's `stats.json` says how far the farthest aircraft was, never which one. So, while statistics are on, the wall server looks at `aircraft.json` every five seconds and keeps in memory, for today and yesterday, the aircraft whose position was the farthest from the antenna (a position under thirty seconds old, in the air, a real ICAO address, and under 600 km: readsb's own limit is 556 km, beyond is a decoding error). Each sample asks the wall for it on the loopback and writes it to `farthest-YYYY-MM-DD`, one JSON object, thirty days like the rest. A farther record already written (before the wall restarted, say) is never replaced by a nearer one. What is written: the date and time, the callsign and the flight number, the airline, the registration and model, the altitude, the distance, the route when the route lookup is on and can believe it (the same check as on the wall), and the city of 100 000 inhabitants or more nearest the aircraft with its distance. Neither the aircraft's position nor the antenna's is written or shown. When a route is still being looked up, the sample waits a few seconds for it.

The cities come from GeoNames (Creative Commons Attribution 4.0), shipped as `flightinfo/data/cities100k.tsv` and made by `tools/make_cities.py`: 4 578 cities, the population being the city's own. The districts GeoNames lists as places of their own (the Paris arrondissements, Neukölln) are left out, and so are two British entries that carry a district's population (checked: St Peter's in Kent, Mendip). Nothing is looked up over the internet for a city.

The figure in the box and the one in the line can differ by a few kilometres: the box is the decoder's own maximum over each fifteen minutes, the line the farthest position the wall saw, every five seconds. Days before 0.22.0 have a box and no line; the page says so for the thirty-day best.

**The daily aircraft count is a floor.** A sample every fifteen minutes misses an aircraft that crossed in less than that. Both the page and the command say so. Sampling more often would catch more of them and write to the SD card more often; fifteen minutes is the same trade the gain log makes.

## The page

Four numbers for today — aircraft, messages with the busiest hour, the farthest aircraft, the best distance of the thirty days — then two lines naming the farthest aircraft of today and of the thirty days, then three charts: messages per hour over the last twenty-four hours, the farthest aircraft per day, aircraft per day. One colour per chart, a tooltip on each bar or point, and the same numbers as a table underneath. It follows the device's light or dark setting and needs nothing from the internet.

![The statistics page with the two lines under the four numbers (a preview, made-up figures)](https://raw.githubusercontent.com/regis57/ZenithBoard/main/docs/images/stats-farthest.png)

The line leaves out what is not known rather than guess it: no airline, no route, no city each drop their part. A city within 50 km reads *near Lyon, FR (12 km)*; farther, over the sea or open country, *85 km from Brugge, BE*. Altitude follows the wall's units; distances are in km, like the rest of the page.

With statistics off, the page says so and how to turn them on. `/api/stats` answers the same numbers as JSON, `{"enabled": false}` when off. `/api/farthest` is what the sample asks: the records the wall holds in memory for today and yesterday.

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
