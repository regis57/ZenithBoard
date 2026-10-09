# Reliability and diagnostics

A wall on the garage wall is only as good as the Pi behind it, and a Pi outdoors on Wi-Fi fails in ways a desk machine does not: it freezes, it loses the network at 01:00, it browns out when the power supply is cold. These tools exist for that.

**Everything here is off until you turn it on**, in menu *4 Settings → 5 Reliability* or with the commands below. Nothing was added to the Pi silently.

## The health screen

```bash
zenithboard health
```

One screen, no digging: power (has the Pi been under-volted or throttled?), temperature, memory, SD card, which watchdogs are on, the network watchdog's last lines, whether the previous boot ended normally or abruptly, and any kernel problems in the logs.

Run it first whenever something odd happened. **"Previous boot ended abruptly"** is the single most useful line on it: it separates a crash or a power cut from a clean restart, and that decides where to look next.

## The hardware watchdog

```bash
sudo zenithboard watchdog on
zenithboard watchdog status
```

The Pi's own chip. The kernel pets it every few seconds; if the kernel stops answering for about **10 seconds**, the chip resets the board. This is the only thing that recovers a truly frozen Pi, because by then no software on it is running.

It cannot help with a Pi that is alive but useless — a decoder that died, a lost network — which is what the next one is for.

## The network watchdog

```bash
sudo zenithboard netwatch on
zenithboard netwatch status
sudo zenithboard netwatch run     # one check now, by hand
```

Every **2 minutes** it asks one question: can the Pi reach its own router? Not the internet — the router. An internet outage changes nothing here, because nothing is wrong with the Pi.

| Failures in a row | About | What happens |
|---|---|---|
| 1 | 2 min | Logged, with what the Wi-Fi can see |
| 3 | 6 min | Restart the network |
| 4 | 8 min | On Wi-Fi: switch the radio off and on, then ask for the saved connection again |
| 5 | 10 min | Logged again, in more detail |
| 6 | 12 min | Reboot the Pi |

Three guards keep this from becoming a reboot loop:

* **A three-hour gap.** Never more than one reboot every 3 hours. If your router is simply off for the evening, the Pi restarts once and then waits.
* **A ten-minute grace period** after any start. The router may still be booting too.
* **The counter lives in `/run`**, in memory. Nothing writes to the SD card every two minutes.

On a failed check it also records what the radio sees: whether your saved network is visible at all, at what signal, how many other networks are in range, and the state of the Wi-Fi device. That is what turns "the network went away" into an answer — a network that is not visible is the router's problem, a visible network at −85 dBm is yours.

## Logs that survive a restart

```bash
sudo zenithboard keeplogs on
```

By default Raspberry Pi OS keeps the system log in memory, so a reboot erases exactly the evidence you need. This moves it to disk and caps it at 50 MB.

If `/var/log/journal` looks empty right after turning it on, run `sudo journalctl --flush` once.

```bash
zenithboard logs usage        # how much space
zenithboard logs review       # size plus the recent warnings
sudo zenithboard logs limit 50
sudo zenithboard logs auto on # daily clean-up keeping 7 days
```

## Reading a bad night afterwards

In this order:

```bash
journalctl --list-boots                    # did it reboot, and when?
zenithboard health                         # did the previous boot end abruptly?
journalctl -t zenithboard-netwatch --since "yesterday 22:00" --until "today 08:00"
journalctl -k --since "yesterday 22:00" | grep -iE 'wlan|voltage|under|usb'
```

Read the netwatch lines as a story rather than a count. Three restarts spaced exactly three hours apart are the gap rule working, which is a success, not three separate faults. What tells you the cause is the diagnostic line next to the first failure of each episode.

Two patterns worth recognising:

* **Your network not visible, other networks visible** — the router's radio stopped, or it has a nightly schedule. Check the router before touching the Pi.
* **Your network visible but weak, or the device stuck in `disconnected`** — signal, interference, or the Pi's radio. On a Pi 3B, remember that Ethernet and the USB dongles share one internal hub.

## A note for the Pi 3B

It has less memory and a shared USB bus. Keeping the logs on disk is a sensible trade there; keeping a year of them is not. The 50 MB cap and the daily clean-up exist for that machine.
