# Moving to a new card

Your ZenithBoard works on one micro-SD card and you want it on another one: a bigger card, a new Pi, or simply a fresh
start. This page does it **step by step, with no computer knowledge needed**. You keep everything: your settings, your
statistics, your graphs, your logs, and your stations on ADSB Exchange, FlightAware, Flightradar24 and Plane Finder.

About an hour, most of it waiting. **Your old card is never changed**: if anything goes wrong, put it back in the Pi
and you are where you started.

## What you need

* The Pi with its **old card**, still working.
* A **new micro-SD card** (16 GB or more) and a way to plug it into your computer.
* On your computer:
  * **PuTTY** to type commands on the Pi ([putty.org](https://www.putty.org/)), or the *Terminal* on a Mac.
  * **WinSCP** to copy a file between your computer and the Pi ([winscp.net](https://winscp.net/), free, for Windows).
    On a Mac or Linux, the `scp` command does the same (see the end of this page).

## Part 1 · On the old card: make the backup (10 minutes)

1. **Connect to the Pi** with PuTTY, as usual (its address, for example `192.168.1.196`, your user and password).
2. **Bring ZenithBoard up to date**, so that it knows how to make a backup. Type, then Enter:
   ```
   cd ~/ZenithBoard && sudo zenithboard update quick
   ```
3. **Make the backup:**
   ```
   sudo zenithboard backup make
   ```
   It ends with a line like `Backup written: /home/pi/zenithboard-backup-rp3-20261021-2130.tar.gz (24M)`. That file
   is your whole ZenithBoard. **It holds your Flightradar24 key: keep it for yourself**, never send it to anyone.
4. **Copy it to your computer with WinSCP:**
   1. Open WinSCP. In the *Login* window: *File protocol* **SFTP**, *Host name* the Pi's address, *User name* and
      *Password* your Pi's. Click **Login**.
   2. The first time, WinSCP asks whether you trust this computer's key: click **Yes** (or *Accept*).
   3. The window has two halves: your computer on the left, the Pi on the right (it opens in your home folder,
      `/home/pi`). **Drag the file `zenithboard-backup-…tar.gz` from the right to the left**, into a folder you will
      find again (your *Documents*).
5. **Switch the old Pi off properly:**
   ```
   sudo shutdown now
   ```
   Wait until its green light stops blinking (about 10 seconds), unplug it, and take the old card out. Put it somewhere
   safe. **Do not use the old card and the new one at the same time**: two receivers with the same identities confuse
   the networks, and Plane Finder blocks it.

## Part 2 · Prepare the new card (20 minutes)

Follow [Fresh install](Fresh-install), **steps 1 to 10** only: write Raspberry Pi OS with Raspberry Pi Imager, start the
Pi, connect with PuTTY, bring the system up to date. Two tips:

* Use **the same name** (`zenithboard`, or the one your old card had) and **the same user name** (`pi`, for example):
  your addresses and habits stay the same.
* On the **same Pi**, nothing changes for your router or the networks: the network address (the "MAC") belongs to the
  board, not to the card. On a **new Pi**, see [Backup and restore](Backup-and-restore#does-the-mac-address-matter).

## Part 3 · Put ZenithBoard and your backup on the new card (30 minutes)

1. **Copy the backup to the new Pi** with WinSCP, as in Part 1 but the other way round: log in to the Pi (the same
   address, usually; if WinSCP warns that the key has changed, that is normal for a new card: accept it), then **drag
   the file from the left (your computer) to the right (the Pi, `/home/pi`)**.
2. **Download ZenithBoard and start it**, in PuTTY, one line at a time:
   ```
   sudo apt install -y git
   git clone https://github.com/regis57/ZenithBoard.git
   cd ZenithBoard
   sudo ./install.sh
   ```
3. **Answer the four first questions** (region, units, position, radius). Your backup puts its own answers back a
   moment later, so what you type here does not matter much.
4. In the menu, choose **Start here**, then:
   1. *Are you moving from another card, with a ZenithBoard backup file?* → **Yes**.
   2. The next screen says where the file should be, and finds it: **OK**.
   3. It proposes the file: **OK**. It shows what the backup holds, then asks you to **type `RESTORE`** (in capitals)
      and Enter. It puts back your settings, your position everywhere it is used, what was switched on, your
      statistics, your logs, and the networks' identities.
   4. **ADS-B**: keep *readsb*, leave the dongle's serial number empty, and **tick the same networks as before**. Since 0.54.5 the ones your backup fed are already ticked (FlightAware, Flightradar24, Plane Finder, and ADSB Exchange's stats), and the screen says so; check the list rather than rebuild it. Each
      network's own installer runs and asks its questions:
      * *ADSB Exchange*: a station name and your position (as before). It keeps your old station by itself.
      * *FlightAware*: nothing to claim, your station comes back by itself.
      * *Flightradar24*: its sign-up asks for your e-mail, then your **sharing key**. Yours is shown in a line just
        before the sign-up starts (*Your sharing key, from your backup: …*): select it with the mouse, it is copied;
        a **right-click** in PuTTY pastes it. If you cannot find it, answer the questions anyway: ZenithBoard puts your
        own key back right after (Flightradar24 may then list a second, unused station on your account, which you can
        delete there).
      * *Plane Finder*: nothing to do on its page, your share code is back.
   5. **The wall**: Yes.
   6. **The list of what is worth switching on**: leave it as it is, Enter.
   7. **The web console**: Yes, then choose its password (10 characters at least, twice).
5. **Finish in your browser**: open `http://zenithboard.local:8080/console` (or the address the last screen shows),
   sign in, and look at the overview: every service should say *running*.

## Part 4 · What to check, and what to do again

* **Your stations**: within the hour, ADSB Exchange, FlightAware, Flightradar24 and Plane Finder show your station
  as before (the links are on the console's overview).
* **Your statistics** at `http://zenithboard.local:8080/stats`: the previous days are there.
* **Bluesky**, if you post: the backup never holds its password. Make a new *app password* on bsky.app
  (*Settings → Privacy and security → App passwords*), then in PuTTY: `sudo zenithboard social setup`.
* **graphs1090**, if you had it: it comes back with step 6 of *Start here* (or `sudo zenithboard graphs on`), with its
  history.
* **Your phone**: in the console, *System → Pair a phone*.

Once all is well for a few days, the old card can be reused.

## If something goes wrong

* **WinSCP cannot connect**: check the Pi's address (your router's list of devices), and that you typed the Pi's user
  and password, not your computer's.
* **`zenithboard backup make` says "command not found" or "Usage"**: the old card was not updated, do Part 1 step 2.
* **The restore says *Not a ZenithBoard backup***: the file was damaged during the copy. Copy it again.
* **You want to go back**: switch off, put the old card back, switch on. Nothing on it was changed.

## Without Windows

On a Mac or Linux, from the Terminal, in the folder where you want the file:

```
scp pi@zenithboard.local:zenithboard-backup-*.tar.gz .        # from the old Pi to your computer
scp zenithboard-backup-*.tar.gz pi@zenithboard.local:         # from your computer to the new Pi
```

What a backup holds, how to check it, the web console's own backup, and the details: [Backup and restore](Backup-and-restore).
