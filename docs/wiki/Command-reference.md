# Command reference

`zenithboard` is the whole interface outside the menus. `zenithboard` with no arguments prints a short version of this page; `zenithboard menu` opens the installer menu.

Commands that change something need `sudo`. Commands that only report do not.

## Looking around

```bash
zenithboard status          # what is installed, what is running, and the MLAT count
zenithboard config          # every setting, as stored
zenithboard health          # power, temperature, memory, card, how the last boot ended
```

`status` is the first thing to run when the wall misbehaves. It prints the decoder, the services, the feeders, the addresses that apply to your Pi, and how many MLAT clients are running — which must be exactly one.

## The wall

```bash
sudo zenithboard units imperial        # mi, knots, ft
sudo zenithboard radius 30             # 1 2 5 10 15 30 50, in your unit
sudo zenithboard color green           # amber green red white
sudo zenithboard mode flap             # dots | flap
sudo zenithboard cycle 8               # seconds per aircraft
sudo zenithboard photos on|off
sudo zenithboard photos test [HEX]     # can this Pi reach Planespotters?
sudo zenithboard routes on|off
sudo zenithboard location 49.28 6.14 180   # lat, lon, altitude in metres
sudo zenithboard config-set PORT 8090
```

`location` is the important one: it writes the position to ZenithBoard, the decoder and every feeder that stores it locally, then tells you which websites you must still update by hand.

## The receiver

```bash
zenithboard gain check                 # is the gain right? reads the decoder statistics
zenithboard gain steps                 # the real steps this dongle has
sudo zenithboard gain set 44.5         # or: max | default | up | down
sudo zenithboard gain log on           # record a measurement every 15 min for 24 h
zenithboard gain log show              # the CSV table
zenithboard gain log status
sudo zenithboard gain log clear        # empty it
sudo zenithboard gain log off
sudo zenithboard mlat-guard            # put the single-MLAT rule back
sudo zenithboard region us             # offer the 978 MHz UAT step in the menu
```

One step at a time, then wait a few minutes before checking again. See [Gain tuning](Gain-tuning).

## Network

```bash
zenithboard net status                 # connections, addresses, default route, DNS
sudo zenithboard net static 192.168.1.50 24 192.168.1.1 router
sudo zenithboard net dhcp              # back to an automatic address

zenithboard wifi status                # radio, country, connection, wired-vs-Wi-Fi priority
zenithboard wifi scan                  # what is in range, with signal strength
sudo zenithboard wifi connect "My network"     # asks for the password; add --hidden if hidden
sudo zenithboard wifi country FR
sudo zenithboard wifi on|off
zenithboard wifi list
sudo zenithboard wifi forget "Old network"
sudo zenithboard wifi install-nm       # run with the cable plugged in

zenithboard ddns status
sudo zenithboard ddns set duckdns myboard      # asks for the token, never on the command line
sudo zenithboard ddns update|test|off
```

The mask in `net static` takes either form: `24` or `255.255.255.0`. The last argument picks the DNS: `cloudflare`, `google`, `router`, or two addresses in quotes.

## Keeping it alive

```bash
zenithboard watchdog status            # the hardware watchdog: restarts a frozen Pi
sudo zenithboard watchdog on|off
zenithboard netwatch status            # the network watchdog
sudo zenithboard netwatch on|off
sudo zenithboard netwatch run          # run one check now, by hand
zenithboard keeplogs status            # do logs survive a reboot?
sudo zenithboard keeplogs on|off
```

All three are off until you turn them on. See [Reliability and diagnostics](Reliability-and-diagnostics).

## Logs

```bash
zenithboard logs                       # the wall's own service
zenithboard logs decoder|acars|uat     # the last 100 lines of one service
zenithboard logs usage                 # how much space the system logs take
zenithboard logs review                # size, plus the recent warnings
sudo zenithboard logs limit 50         # cap the system logs, 10-2000 MB
sudo zenithboard logs clean            # delete all logs now
sudo zenithboard logs auto on|off|status       # daily clean keeping 7 days
```

## Updating

```bash
sudo zenithboard update                # ZenithBoard, decoder, feeders, ACARS, Grafana
zenithboard update list                # what is installed and what can be updated
sudo zenithboard update only readsb flightinfo
sudo zenithboard data update           # refresh the aircraft-type list now
zenithboard data status
sudo zenithboard data auto on|off
```

`update` is the normal way to pick up a new release: `cd ~/ZenithBoard && sudo zenithboard update`.

## Trying it without hardware

```bash
./bin/zenithboard-demo                 # a fake sky on port 8081
REAL_PHOTOS=1 ./bin/zenithboard-demo   # the same, but real photos and routes
```

Useful for working on the display on a laptop. No dongle, no Pi.
