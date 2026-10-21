# Backup and restore

One file that carries a ZenithBoard to a new card (or keeps it safe from a dead one) and lets the new card carry
on where the old one stopped: the same stations on the networks, the same statistics, the same graphs, the same
logs, and the features that were on switched on again. Since 0.42.0.

```
sudo zenithboard backup make                 # on the old card: zenithboard-backup-HOST-DATE.tar.gz, in the current folder
zenithboard backup show FILE                 # what a backup holds, changing nothing
sudo zenithboard backup restore FILE         # on the new card: asks you to type RESTORE
```

Or the menu: *6 Maintenance → Back up everything*. The web console makes one too (*System → Backup*), without the
networks' identities: see [below](#from-the-web-console).

## What a backup holds

| Part | From | Back on the new card |
|---|---|---|
| Settings | `config.env`, without its secrets (as `settings export`) | Imported; the file from before kept as `config.env.bak-DATE` |
| What is on | Statistics, graphs1090, both watchdogs, logs kept after a restart, daily security fixes, Wi-Fi hardening, daily log clean-up, gain log, Bluesky posts, the web console, phone sign-in | Each switched on again by its own command (`stats on`, `watchdog on`…), so its timer or its file is really there, not only a line in `config.env` |
| Statistics | `/var/lib/zenithboard/stats`: the 30 days behind `/stats` and the summaries | Copied back; the samples of both cards are merged, once each, in time order |
| Posting history | `/var/lib/zenithboard/social/state.json`: what was posted, when the summaries went out | Copied back: nothing is posted twice, the next summary comes at its time |
| graphs1090's history | Dumped to XML by graphs1090's own `rrd-dump.sh` (collectd stopped first, so the day kept in memory is written) | Put back with its `rrd-restore.sh`, which reads XML made on another architecture (32-bit → 64-bit), [as graphs1090's README says](https://github.com/wiedehopf/graphs1090) |
| Logs kept after a restart | `/var/log/journal/MACHINE-ID` (50 MB at most) | Beside the new card's, in the old card's own folder: `journalctl -m` shows both, `journalctl -D /var/log/journal/OLD-ID` the old alone |
| The networks' identities | ADSB Exchange's UUID, FlightAware's feeder ID, Flightradar24's sharing key, Plane Finder's settings with its share code | Given back to each network: now if it is installed, else kept (root only) for its installation in menu 1 |

**Never in it:** the Bluesky app password, the console password, the domain name's token. A new Bluesky app
password takes a minute (bsky.app → *Settings* → *Privacy and security* → *App passwords*), then
`sudo zenithboard social setup`; the console: `sudo zenithboard console password && sudo zenithboard console on`.
The restore lists them at its end, under *Still to do*.

**The file is yours alone.** It holds Flightradar24's sharing key and the stations' identities: it is written for its
owner only (mode 600), and never goes into an issue or a chat. `backup show` names what is inside, never the values.

## Moving to a new card, step by step

1. **On the old card:** `sudo zenithboard backup make`, then copy the file to your computer:
   `scp USER@OLDPI.local:zenithboard-backup-*.tar.gz .` (the command prints the exact line).
2. **Switch the old card off** (`sudo shutdown now`). Two receivers with the same identities is one too many:
   FlightAware and Flightradar24 see one station feeding twice, and Plane Finder blocks a share code used on two
   receivers ([Plane Finder's forum](https://forum.planefinder.net/threads/pfclient-automatic-setup.1074/)).
3. **On the new card,** [Fresh install](Fresh-install) to step 12 (the installer and its first questions), then leave
   the menu and copy the file over: `scp zenithboard-backup-*.tar.gz USER@zenithboard.local:`
4. `sudo zenithboard backup restore zenithboard-backup-….tar.gz`, type `RESTORE`. It prints what it put back, part
   by part, and what is left to do.
5. **Menu 1 ADSB**, ticking the same networks: each installer finds its identity. ADSB Exchange's keeps the UUID it
   finds; FlightAware gets its feeder ID and needs no claim; Flightradar24's sign-up still runs (it is FR24's own): the
   terminal shows your key to paste at its *sharing key* question, and the key is set again afterwards whatever was
   answered; Plane Finder gets its share code and needs nothing on its page.
6. **Menu 2 FlightInfo**, then `sudo zenithboard graphs on` if graphs1090 was on (it needs the receiver map that
   menu 2 brings): its history comes back by itself.
7. Then Fresh install's steps 16 to 21. In the console, the first steps are then only a check.

The restore works at any other time too (everything installed already, or half of it): what can be applied is
applied at once, the rest waits in `/var/lib/zenithboard/restore-pending/` for its installer.

## Does the MAC address matter?

**On the same Raspberry Pi, no: the MAC address does not change with the card.** It belongs to the board's network
chip, not to the system on the card. Two places use it all the same:

* **Your router**, if it gives the Pi a fixed address by its MAC (a DHCP reservation): the same board gets the same
  address again. On a *new board*, change the reservation to the new MAC (`ip -br link` on the Pi prints it). If
  your router is set that way, compare `ip -br link` on both cards to be sure.
* **FlightAware** identified its older stations by MAC; since 2017 a new station gets a feeder ID
  ([FlightAware's own post](https://discussions.flightaware.com/t/how-piaware-feeders-are-identified-updated-2017-07-16/19811)).
  The backup carries the feeder ID; on the same board, a station still known by its MAC stays the same too. On a new
  board, the feeder ID is what keeps the station.

ADSB Exchange (its UUID), Flightradar24 (its sharing key) and Plane Finder (its share code) do not use the MAC.

## From the web console

*System → Backup → Make a backup*, then *Download it*. The console's backup holds everything above **except the
networks' identities**: keys never travel through the console, which runs as an unprivileged user over plain HTTP
on your home network. It keeps one backup at a time, readable by the wall's user only, in the console's own folder;
each download is written in the console's audit log.

**Restoring is done in the terminal**, never from the console: it replaces settings and data, runs the installers of
what was on, and asks for a typed word, like every step that cannot be taken back in one click.

## Taking a restore back

What the restore replaced is kept first in `/var/lib/zenithboard/before-restore-DATE/`: `config.env`, the statistics,
the posting history, the identities it overwrote. Settings: `sudo zenithboard settings import
/var/lib/zenithboard/before-restore-DATE/config.env`. A feature switched on: its own `off`. The old card's logs:
`sudo rm -r /var/log/journal/OLD-ID`.

## Without a backup

If the old card no longer starts, each identity can be found in your accounts:
[Fresh install, replacing a card](Fresh-install#replacing-a-card-that-already-feeds). The statistics and the graphs
live on the card only.
