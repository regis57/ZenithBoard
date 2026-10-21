# The menu

`sudo zenithboard menu` (or `sudo ./install.sh` in the folder you downloaded). Since 0.44.0 it is ordered **by what
you want to do**: one entry to start with, then one menu per subject, seven entries at most, each with its way back
(the owner's review, 21 October 2026: too many menus, some of ten entries, and nothing said that the web console needs
ADS-B and the wall first). Every entry runs the same `zenithboard` command as the terminal and the web console: the
three stay one and the same. The screens below are the real ones, captured from the menu itself.

Move with the arrow keys, Enter to choose, Esc to go back. A step that cannot be undone asks you to type a word.

![The main menu](https://raw.githubusercontent.com/regis57/ZenithBoard/main/docs/images/menu-main.png)

The three lines at the top say what this Pi already does: the decoder and the networks it feeds, the wall's address,
the console's.

## Start here: the first installation

![Start here](https://raw.githubusercontent.com/regis57/ZenithBoard/main/docs/images/menu-start.png)

In its order, each step skipped when it is done already:

1. **A backup from another card?** Yes: it asks for the file in your home folder (copied there with WinSCP from
   Windows: [Moving to a new card](Moving-to-a-new-card)) and puts it back. The networks then find their identities
   by themselves at step 2.
2. **ADS-B**: the decoder (readsb), ADSB Exchange (always: it runs the one MLAT client), and the other networks you
   tick. Their installers are theirs, and ask in the terminal (a station name, an e-mail, a key); the screen says what
   to answer. Without a decoder the rest waits, and says so.
3. **The wall**, the page the tablet shows. The web console is one of its pages: without the wall, no console.
4. **What is worth switching on**, one list, everything ticked; untick what you do not want, each can be switched off
   again later:

   | Ticked | What it does |
   |---|---|
   | Statistics | The `/stats` page, and the Bluesky summaries (30 KB a day) |
   | graphs1090 | Years of graphs on port 8542, in ZenithBoard's look (only when the receiver map's web server is there) |
   | Logs kept after a restart | Why it stopped can be read afterwards (50 MB at most) |
   | Hardware watchdog | A frozen Pi restarts by itself (when the board has one) |
   | Network watchdog | The network, then the Pi, restarted when the router is lost |
   | Debian's security fixes | Daily, from Debian's security channel; the feeders are left alone, no reboot |
   | Daily log clean-up | The last 7 days kept |
   | Wi-Fi hardening | Reconnects without end, no power saving (only when on Wi-Fi) |

5. **The web console**: its password (10 characters at least, asked twice), then its address. You finish in your
   browser: its first steps check what is left, *System → Pair a phone*. Bluesky, if you post, is set up here in
   *7 Options* (it asks for an app password, which never goes through a web page).

Once everything is done, the entry says *all done: check it again*.

## 1 ADS-B

![1 ADS-B](https://raw.githubusercontent.com/regis57/ZenithBoard/main/docs/images/menu-adsb.png)

The decoder and the networks (install, add, remove: an unticked network is removed after a confirmation), the
antenna's position and region (applied everywhere it is stored: the decoder, the networks that take it, the wall), the
gain ([Gain tuning](Gain-tuning)), and what is running with the single-MLAT check.

## 2 The wall

![2 The wall](https://raw.githubusercontent.com/regis57/ZenithBoard/main/docs/images/menu-wall.png)

Install it (or reinstall its files), what it shows (radius, units, seconds per aircraft), its look (dot matrix or
split-flap, and its colour: graphs1090 and the web console take the same colour), photos, routes and aircraft names
([Routes, photos and data](Routes-photos-and-data)), presets for each tablet, and removing it (a typed word).

## 3 Connectivity

![3 Connectivity](https://raw.githubusercontent.com/regis57/ZenithBoard/main/docs/images/menu-connectivity.png)

Wi-Fi, a fixed address, a domain name, the status of all three. **Item 3, read before opening anything:**

![From outside your home, safely](https://raw.githubusercontent.com/regis57/ZenithBoard/main/docs/images/menu-outside.png)

* At home, everything works with no change.
* **The safe way from outside is a VPN**: your phone joins your home network; nothing is open to the internet.
  * Best: the VPN built into your router or box (WireGuard or OpenVPN; its menu often says *VPN server*). Through it
    you are "at home": the wall and the console answer, nothing to change on the Pi. A domain name (item 4) lets the
    VPN find your home when its address changes.
  * Or Tailscale or ZeroTier, installed on the Pi with their own installers. You then come from their addresses
    (Tailscale's: `100.64.0.0/10`): allow them for the wall with your home range, for example
    `sudo zenithboard config-set ALLOW_FROM 192.168.0.0/16,100.64.0.0/10`. The web console stays for home networks.
* **Opening a port makes the wall public**: no password, no encryption, and the aircraft around your antenna tell
  roughly where you live; robots scan every address all day. If you still want it: a fixed address, a domain name,
  forward **only** port 8080, then `sudo zenithboard config-set ALLOW_FROM any`. **Never** forward port 22 (SSH, the
  Pi's login) or port 80 (the receiver map has no guard). The console never answers from the internet anyway.
* Some providers share one public address between many homes (CGNAT): no port can be opened, a VPN like Tailscale
  still works.

`zenithboard security` (*4 Troubleshoot → 5*) says what is open at any time. More: [Security](Security).

## 4 Troubleshoot

![4 Troubleshoot](https://raw.githubusercontent.com/regis57/ZenithBoard/main/docs/images/menu-troubleshoot.png)

Health (power, temperature, memory, card, how the last start ended), what is running, memory service by service, the
last lines of a service's log, the security check, the watchdogs and logs kept after a restart, log housekeeping.
More: [Reliability and diagnostics](Reliability-and-diagnostics).

## 5 Updates

![5 Updates](https://raw.githubusercontent.com/regis57/ZenithBoard/main/docs/images/menu-updates.png)

ZenithBoard and the wall alone (seconds), everything (minutes), a choice of components, what is installed, and
Debian's daily security fixes. The menu opens again on the new version after an update.

## 6 Backup

![6 Backup](https://raw.githubusercontent.com/regis57/ZenithBoard/main/docs/images/menu-backup.png)

Make a backup (in your home folder), put one back (a typed word), show, list and delete the older ones, uninstall
everything (a typed word), and the settings file alone. [Moving to a new card](Moving-to-a-new-card) ·
[Backup and restore](Backup-and-restore).

## 7 Options

![7 Options](https://raw.githubusercontent.com/regis57/ZenithBoard/main/docs/images/menu-options.png)

Statistics ([Statistics](Statistics)), graphs1090 and its look, Bluesky ([Social sharing](Social-sharing)), the web
console ([Web console](Web-console)). Each is off until switched on, graphs1090's look excepted: ZenithBoard's by
default, graphs1090's own with `sudo zenithboard graphs look original`.

## Where did an entry go? (before 0.44.0)

| Before | Now |
|---|---|
| 1 ADSB | 1 ADS-B → 1 |
| 2 FlightInfo | 2 The wall |
| 3 Settings → 1 Network | 3 Connectivity |
| 3 Settings → 2 Receiver (region, position, gain) | 1 ADS-B → 2, 3 |
| 3 Settings → 2 Receiver (units) | 2 The wall → 2 |
| 3 Settings → 2 Receiver (statistics, graphs1090) | 7 Options → 1, 2 |
| 3 Settings → 3 Wall | 2 The wall |
| 3 Settings → 4 Logs | 4 Troubleshoot → 7 |
| 3 Settings → 5 Reliability (health, memory, watchdogs, saved logs) | 4 Troubleshoot |
| 3 Settings → 5 Reliability (Debian patches) | 5 Updates → 5 |
| 3 Settings → 6 Social sharing, 7 Web console | 7 Options → 3, 4 |
| 4 Status | 4 Troubleshoot → 2 (or 1 ADS-B → 4) |
| 5 Update | 5 Updates |
| 6 Maintenance | 6 Backup |
