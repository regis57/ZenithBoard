# Backup and restore

One file that carries a ZenithBoard to a new card (or keeps it safe from a dead one) and lets the new card carry
on where the old one stopped: the same stations on the networks, the same statistics, the same graphs, the same
logs, and the features that were on switched on again. Since 0.42.0.

```
sudo zenithboard backup make                 # on the old card: zenithboard-backup-HOST-DATE.tar.gz, in the current folder
zenithboard backup show FILE                 # what it holds, each part read back with the span it covers
sudo zenithboard backup restore FILE         # on the new card (the "import"): asks you to type RESTORE
zenithboard backup list                      # the backups, newest first
zenithboard backup clean --keep 3            # delete the older ones; asks you to type delete
```

Or the menu: *6 Backup → 1 Make a backup now*. The web console makes one too (*System → Backup*), without the
networks' identities: see [below](#from-the-web-console).

## What a backup holds

| Part | From | Back on the new card |
|---|---|---|
| Settings | `config.env`, without its secrets (as `settings export`) | Imported; the file from before kept as `config.env.bak-DATE` |
| What is on | Statistics, graphs1090, both watchdogs, logs kept after a restart, daily security fixes, Wi-Fi hardening, daily log clean-up, gain log, Bluesky posts, the web console, phone sign-in, ADSB Exchange's stats (0.52.0: after ADSB Exchange's feed, the restore says the command) | Each switched on again by its own command (`stats on`, `watchdog on`…), so its timer or its file is really there, not only a line in `config.env` |
| Statistics | `/var/lib/zenithboard/stats`: the 30 days behind `/stats` and the summaries | Copied back; the samples of both cards are merged, once each, in time order |
| Posting history | `/var/lib/zenithboard/social/state.json`: what was posted, when the summaries went out | Copied back: nothing is posted twice, the next summary comes at its time |
| Your own post templates (0.51.0) | `/etc/zenithboard/social-templates.txt` | Copied back; the ones it replaces are kept in `before-restore-DATE/` |
| graphs1090's history | Dumped to XML by graphs1090's own `rrd-dump.sh` (collectd stopped first, so the day kept in memory is written) | Put back with its `rrd-restore.sh`, which reads XML made on another architecture (32-bit → 64-bit), [as graphs1090's README says](https://github.com/wiedehopf/graphs1090) |
| Logs kept after a restart | `/var/log/journal/MACHINE-ID` (50 MB at most) | Beside the new card's, in the old card's own folder: `journalctl -m` shows both, `journalctl -D /var/log/journal/OLD-ID` the old alone |
| The networks' identities | ADSB Exchange's UUID, FlightAware's feeder ID, Flightradar24's sharing key, Plane Finder's settings with its share code, AirNav Radar's sharing key (0.99.6) | Given back to each network: now if it is installed, else kept (root only) for its installation in menu 1 |

**Never in it:** the Bluesky app password, the Telegram bot's token (0.99.6: the switch and your own messages are in it; `telegram setup` asks for the token again), the console password, the domain name's token. A new Bluesky app
password takes a minute (bsky.app → *Settings* → *Privacy and security* → *App passwords*), then
`sudo zenithboard social setup`; the console: `sudo zenithboard console password && sudo zenithboard console on`.
The restore lists them at its end, under *Still to do*.

**The file is yours alone.** It holds Flightradar24's sharing key and the stations' identities: it is written for its
owner only (mode 600), and never goes into an issue or a chat. `backup show` names what is inside, never the values.

## Checking a backup

`zenithboard backup show FILE` reads each part back the way a restore would, and says what it covers. On the reference
Pi's first backup, made from the console on 21 October 2026 at 12:51 (24 MB):

```
Checked:
  statistics: 572 samples, 2026-10-15 14:00 to 2026-10-21 12:45
  aircraft lists: 2026-10-15 to 2026-10-21
  posting history: readable, 6 aircraft posted
  graphs1090: 68 databases, last point 2026-10-21 12:50
  kept logs: 13 boot(s), 2026-10-08T09:06 to 2026-10-21T12:51
  Everything in it reads back; made 2026-10-21 12:51.
```

Every part ends within minutes of the backup: nothing was left in memory. A damaged part is named (*NOT COMPLETE:
graphs1090 would not come back*) and the command ends with an error; `backup restore` shows the same lines before it
asks for `RESTORE`. Each new backup is also read back once written (a full card shows up there).

## Where backups are kept, and clearing them

* **From the terminal or the menu**: where you said, by default the current folder (the menu: your home folder),
  named `zenithboard-backup-HOST-YYYYMMDD-HHMM.tar.gz`. The name sorts in time order; `backup list` shows them newest
  first with their size. Nothing deletes them by itself: `backup clean --keep 3` deletes all but the three newest
  (it lists them and asks you to type `delete`), or the menu, *6 Backup → 3 Show, list, delete older backups → 2*. They are
  your files: `rm` works too.
* **From the console**: one copy only, `/var/lib/zenithboard/console/out/backup.tar.gz`, replaced by the next one,
  so it never piles up; *Delete it* (or `sudo zenithboard backup delete --console`) frees its room on the card. Its
  download is named `zenithboard-backup-HOST-YYYYMMDD-HHMM-console.tar.gz`: the same order, marked as the one
  without the networks' identities.

A backup takes about the size of the logs kept (50 MB at most) plus graphs1090's history (30 MB on the reference Pi,
compressed): copy it off the Pi and keep a few, not dozens, on the card.

## Copying the file between your computer and the Pi

The file goes in **your home folder on the Pi** (`/home/YOUR_USER/`, written `~`): the restore takes it from there,
and the menu's *Restore* offers the newest one it finds there. PuTTY's own window is a terminal only and cannot carry
a file; three ways that can, on Windows:

* **The `scp` built into Windows 10 and 11** (its OpenSSH client), in PowerShell, from the folder holding the file
  (a console download is in *Downloads*):
  ```
  cd $env:USERPROFILE\Downloads
  scp .\zenithboard-backup-rp3-20261021-1252-console.tar.gz YOUR_USER@zenithboard.local:
  ```
  The `:` at the end, with nothing after it, means your home folder on the Pi. It asks for your Pi password. If
  `zenithboard.local` is not found, use the Pi's address (`YOUR_USER@192.168.1.x:`).
* **PuTTY's `pscp.exe`**, installed with PuTTY (its folder, usually `C:\Program Files\PuTTY`, is on the path), the
  same way ([PuTTY's manual, chapter 5](https://putty.cs.utah.edu/0.83/htmldoc/Chapter5.html)):
  ```
  pscp zenithboard-backup-rp3-20261021-1252-console.tar.gz YOUR_USER@192.168.1.x:/home/YOUR_USER/
  ```
* **WinSCP**, if you prefer windows to commands: connect with SFTP to the Pi, your user and password, and drag the
  file into the home folder it opens on.

From the Pi to your computer (a backup made in the terminal), the other way round, in PowerShell:
`scp YOUR_USER@zenithboard.local:zenithboard-backup-*.tar.gz .` (or `pscp YOUR_USER@192.168.1.x:/home/YOUR_USER/zenithboard-backup-rp3-….tar.gz .`).
On macOS and Linux, `scp` is there already, same lines.

Then, in PuTTY (or `ssh`) on the Pi: `ls ~/zenithboard-backup-*` shows it, and
`sudo zenithboard backup restore ~/zenithboard-backup-….tar.gz` puts it back (*Tab* completes the name).

## Moving to a new card, step by step

**The whole way, for someone who has never done it, with WinSCP from Windows: [Moving to a new card](Moving-to-a-new-card).**
In short: `sudo zenithboard backup make` on the old card, the file copied to your computer, the old card switched off
(two receivers with the same identities is one too many: Plane Finder blocks a share code used on two receivers,
[its forum](https://forum.planefinder.net/threads/pfclient-automatic-setup.1074/)); on the new card the installer, its
four questions, then **Start here**: *Yes* to the backup, `RESTORE`, and the rest of *Start here* (ADS-B with the same
networks, the wall, the list, the console). Each network's installer finds its identity: ADSB Exchange's keeps the UUID
it finds; FlightAware gets its feeder ID, no claim; Flightradar24's sign-up still runs (it is FR24's own), the terminal
shows the key to paste and it is set again afterwards whatever was answered; Plane Finder gets its share code.

**What a restore applies, not only imports** (0.44.0, the owner: the position, the altitude and the units had not
followed): the antenna's position goes everywhere it is stored (the decoder, the networks that take it, the wall), the
wall and the Bluesky service restart with the settings, and graphs1090 takes the look and colour of the backup.

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

ADSB Exchange (its UUID), Flightradar24 (its sharing key), Plane Finder (its share code) and AirNav Radar (its sharing key) do not use the MAC.

## From the web console

*System → Backup → Make a backup*, then *Download it* (and *Delete it* once downloaded, if you want the room back). The console's backup holds everything above **except the
networks' identities**: keys never travel through the console, which runs as an unprivileged user over plain HTTP
on your home network. It keeps one backup at a time, readable by the wall's user only, in the console's own folder;
each download is written in the console's audit log.

**The console's copy is for keeping, not for moving.** It leaves the networks' identities out, so on a card with no network yet every network would start as a new station. The console's card says so (0.53.8), and so does `backup restore` before it asks for the typed word, when it is given that file on such a card. To move to a new card, make the full backup in the terminal: `sudo zenithboard backup make`.

**Restoring (the import) is done in the terminal**, never from the console: the card says so, with the command.
A restore replaces settings and data, runs the installers of
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
