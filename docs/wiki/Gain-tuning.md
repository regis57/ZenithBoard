# Gain tuning

The dongle's gain decides how many aircraft you hear. Too low and distant aircraft never arrive; too high and the receiver overloads, so strong nearby signals turn to mush. The sweet spot is a step or two below overload, and the only way to find it is to measure.

```bash
zenithboard gain check
```

It reads the decoder's own statistics and tells you where you are, with the time of the check on the first line — which matters, because the answer at 3 a.m. and the answer at 18:00 are different.

## What it measures

The decoder counts, over the last 15 minutes, how many messages it accepted and how many of those were **strong signals** — messages loud enough to be near the overload point. What matters is the share:

| Share of strong messages | Reading |
|---|---|
| Under 1 % | Probably room to go up a step — but judge it at a busy hour, not at night |
| 1 % to 5 % | Where you want to be |
| Over 5 % | Go down one step |

At a quiet hour almost nothing is strong, so a low figure then means little. Check at rush hour.

## Changing it

```bash
zenithboard gain steps          # the real steps this dongle has
sudo zenithboard gain up        # one step up
sudo zenithboard gain down      # one step down
sudo zenithboard gain set 44.5  # a specific value, snapped to the nearest real step
sudo zenithboard gain set max
sudo zenithboard gain set default
```

**One step at a time**, then wait a few minutes before checking again: the statistics cover the last 15 minutes, so an immediate re-check still describes the old setting.

## The R820T's real steps

The tuner has 29 fixed steps and nothing in between. Ask for 45 and you get 44.5. They are:

```
0.0  0.9  1.4  2.7  3.7  7.7  8.7 12.5 14.4 15.7 16.6 19.7 20.7 22.9 25.4
28.0 29.7 32.8 33.8 36.4 37.2 38.6 40.2 42.1 43.4 43.9 44.5 48.0 49.6
```

The top step is **49.6 dB**, and the one below 48.0 is 44.5 — the gap near the top is wide, which is why going up one step from 44.5 can change things noticeably.

## `-10` is not the maximum

A value of `-10` in the decoder's options means **the dongle's own automatic gain control**, not full gain. It is a common misreading, and it matters: AGC on an ADS-B receiver tends to chase strong local signals and lose the distant ones, which is the opposite of what you want. Set a real number instead. readsb also has an experimental `--gain=auto` which is a different thing and does its own measuring.

## Where the setting actually lives

Not in `config.env`. The gain is part of `RECEIVER_OPTIONS` in:

* `/etc/default/readsb`, or
* `/etc/default/dump1090-fa`

depending on your decoder, because that is the file the decoder reads at start. `zenithboard gain set` edits only the `--gain` part of that line and leaves your other options alone, then restarts the decoder.

## The 24-hour log

One check is one moment. The share of strong messages changes with the traffic, so a decision taken at 03:00 and a decision taken at 18:00 will not agree. The log settles that by measuring all day, by itself:

```bash
sudo zenithboard gain log on      # a measurement every 15 minutes
zenithboard gain log status       # how many so far
zenithboard gain log show         # the table
sudo zenithboard gain log clear   # empty it and start again
sudo zenithboard gain log off     # stop (the file is kept)
```

It keeps **24 hours and nothing older**: 96 lines, the oldest dropped as a new one arrives. Nothing to prune by hand, and nothing that quietly fills the SD card. It is off until you turn it on.

The file is `/var/lib/zenithboard/gain-log.csv`:

```
when,gain_db,decoder,accepted,strong,strong_pct,farthest_km,avg_dbfs,peak_dbfs
2026-10-10 07:45,48.0,readsb,810956,18386,2.27,318,-10.8,-1.6
2026-10-10 08:00,48.0,readsb,845112,19902,2.36,322,-10.6,-1.5
```

Every 15 minutes on the quarter hour, which matches the window the decoder itself reports, so two consecutive lines do not describe the same messages twice.

**How to read a day of it.** Sort or chart `strong_pct` against `when`. What you are looking for is not an average but the **peak**: the busiest hour is the one that decides whether the gain is too high, because that is when the receiver is closest to overloading. A day that stays under 5 % at its worst hour is a gain you can leave alone. Then look at `farthest_km` and `accepted` at the *same* hours across two different gains — comparing a quiet night at one setting with a busy evening at another proves nothing.

**Tuning with it.** Record a day at your current gain. Change one step. Record another day. Compare the two at matching hours. It is slower than guessing and it is the only way to know, because the difference between two neighbouring steps is smaller than the difference between Tuesday and Sunday.

*Opening it in a French Excel: use Données → À partir d'un fichier texte/CSV and pick the comma as separator; double-clicking puts everything in one column, because a French Excel expects semicolons.*

## A worked example

From the Pi this project is developed against: 48.0 dB gives 4–5 % strong messages at rush hour. That is inside the guideline, near the top of it, and one step down would be 44.5 — a big drop for little gain. Left at 48.0. Settled is better than optimal.
