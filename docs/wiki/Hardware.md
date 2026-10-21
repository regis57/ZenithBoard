# Hardware

Which Raspberry Pi ZenithBoard needs, from what was measured rather than guessed, and what happens if you move it to another one. The short version: **a Pi 3B with 1 GB is enough for everything ZenithBoard does**, and a bigger board brings nothing you would see for ADS-B.

## What the reference Pi runs, measured

The project's reference Pi is a Raspberry Pi 3 Model B (1 GB), outdoors, on Wi-Fi, with an R820T dongle. Measured on 17 October 2026 with `zenithboard health` and `sudo zenithboard social status`, after more than seven hours up:

| | |
|---|---|
| Running | readsb; ADS-B Exchange with its MLAT client, FlightAware, Flightradar24; the wall; DuckDNS; the hardware and network watchdogs; persistent logs; social sharing posting every crossing of a 10 km radius |
| Memory | **656 MB of 1 GB still available**, no swap used |
| Social sharing | the heaviest of the optional parts: about 30–40 MB at rest; while it draws a picture, about 105 MB at most (Python with Pillow, for the split-flap look), plus Node up to 65 MB for a second or two |
| Temperature | 36 °C |
| Power | no under-voltage and no throttling since the start |
| SD card | 6 % of it used |

**With Plane Finder as a fourth feed** (20 October 2026, 22:40, about four hours up): ADS-B Exchange, FlightAware, Flightradar24 and Plane Finder, the wall, statistics and social sharing — **575 MB of 1 GB still available**, no swap used, 34 °C, no under-voltage, card 6 % full. Then, with 0.34.0's `sudo zenithboard memory` (23:40, about five hours up; PSS, so the services add up): **212 MB for all the services**, 600 MB available, 193 threads. The largest: social sharing 39 MB (73 MB at its peak, while drawing), the wall 36 MB, **Plane Finder 27 MB**, Flightradar24 17 MB, FlightAware 13 MB (two processes), ADS-B Exchange 15 MB (feed 7 and MLAT 8), readsb 5 MB, tar1090 and lighttpd 1 MB each. Debian's own `unattended-upgrades` 13 MB. The card is a 64 GB one (62.5 GB), 3.5 GB used.

**The next morning** (21 October 2026, 07:56, after the 0.39.0 update): **180 MB for all the services**, 619 MB available, 190 threads, load 1.1 on four cores, 28 MB of swap used. The wall 21 MB (30 at its peak), social sharing 24 MB, Flightradar24 17 MB, FlightAware 13 MB. **Plane Finder 43 MB**, up from 27 MB the evening before: it was the one service not restarted by the update (it has run since the evening), so it grows while it runs; a figure to watch over the next days rather than a problem at 43 MB.

`zenithboard health` gives the same lines on any Pi; [Reliability and diagnostics](Reliability-and-diagnostics) says how to read them.

## Which board for what

| Board | ADS-B + feeders + wall + social sharing |
|---|---|
| **Pi 3B / 3B+ (1 GB)** | **Measured: comfortable**, with ADS-B Exchange and three more feeders (FlightAware, Flightradar24, Plane Finder): 575 MB still available. Ethernet or a strong Wi-Fi signal, and the official power supply |
| **Pi 4, 1 GB** | Comfortable (estimate: the same software, a faster processor) |
| **Pi 4, 2 GB or more / Pi 5** | Comfortable, and nothing more to gain over a Pi 3B (estimate) |
| Pi Zero 2 W (512 MB) / Pi 2 | ADS-B and the wall only, no extra feeders (estimate) |

Only the Pi 3B row is measured. The others are reasoned from it, and say so; a report from another board is welcome (see [Contributing](Contributing)).

## Before buying a bigger Pi

What decides how many aircraft you see is the antenna — where it is, how high, how clear — then the dongle and its gain ([Gain tuning](Gain-tuning)). Decoding 1090 MHz and feeding three networks is light work: the reference 3B does it with most of its memory unused.

What a Pi 4 would change, against a Pi 3B, for ADS-B, the feeders, the wall and social sharing:

| | |
|---|---|
| Reception, MLAT, the feeds | Nothing |
| The wall | Nothing: the tablet draws it, the Pi only answers |
| Social sharing | The picture is drawn in less time — a few seconds sooner on a post that already waits for the aircraft's details |
| Memory | More of it, unused |
| Power | More: Raspberry Pi gives a typical bare-board draw of 600 mA for a Pi 4 against 400 mA for a Pi 3B, and recommends a 3 A supply against 2.5 A ([its power table](https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/power-supplies.adoc)) |
| Heat | It runs warmer: give it a heatsink or a ventilated case, outdoors especially |

Until 0.29.0 the one reason to move was **ACARS with Grafana**, which needed about 900 MB more and a second dongle. ACARS left ZenithBoard in 0.30.0: there is no reason left in ZenithBoard itself.

## Moving the SD card to another Pi

Asked about on the reference Pi in October 2026, with a Pi 4 (2 GB) to hand; after looking at the figures above, the 3B stayed. **Not tried on hardware yet**: this is what should happen, and why.

**What comes across as it is**

* **The system.** Raspberry Pi OS is one image for the Pi 3, 4 and 5; a card written for one starts on the others.
* **ZenithBoard.** It stores nothing about the board. It reads the model and the memory when it needs them — `zenithboard health` will name the new board. It does not touch the boot files (`config.txt`, `cmdline.txt`).
* **The feeders' identities**, which live on the card: Flightradar24's sharing key in `/etc/fr24feed.ini`; PiAware's feeder ID in `/var/cache/piaware/feeder_id`, which is how FlightAware recognises a site set up since 2017, rather than by the board's network address ([FlightAware's explanation](https://discussions.flightaware.com/t/how-piaware-feeders-are-identified-updated-2017-07-16/19811?page=2)); ADS-B Exchange's client keeps its own ID on the card too. Write down the PiAware one before you move: `cat /var/cache/piaware/feeder_id`.
* **MLAT**, since the antenna, and so the position, does not move.
* **Your settings, history and statistics**: all on the card.

**What changes**

* **The power supply.** A Pi 4 takes USB-C, 5.1 V 3 A; the Pi 3B's micro-USB supply does not fit.
* **Possibly the address.** The new board has another network address (MAC). If your router hands out addresses by MAC, the Pi may get a new IP, and the tablet showing the wall must be pointed at it. Reserve an address for the new board on the router, or use a fixed address (`sudo zenithboard net static …`, see [Command reference](Command-reference)), which is kept with the card.
* **Heat**: above.
* **An overclock** written by hand into `/boot/firmware/config.txt` for the 3B (`arm_freq`, `over_voltage`) is not meant for a Pi 4: take it out first.

**How to go back**

1. Make a copy of the card first (Raspberry Pi Imager, or any disk-imaging tool). That copy is the real way back.
2. `sudo poweroff`, wait for the green light to stop, then move the card and the dongle.
3. On the new board: `zenithboard health` and `zenithboard status`, then each feeder's own page.
4. If anything is wrong, power off and put the card back in the 3B. Starting it on a Pi 4 does not change it in a way the 3B would mind: the Pi 4's own firmware updates go to a chip on the Pi 4, not to the card.
