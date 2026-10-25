# Changelog

## 0.55.2
- **The summaries' post 1 has its link** (the owner's screenshot, 25 October 2026): *Sharing → Summaries* now shows *Post 1 · The period ↗* beside posts 2 to 4. *All summaries* draws the four in the terminal's way; the link opens the first one's picture. It has a copy of its own, `/social/preview1`, which a later *Try a post* of a crossing does not replace (before, post 1 shared `/social/preview` with it). `/social/preview` still shows the last picture drawn.

## 0.55.1
- **The registration is a hashtag in every aircraft post** (the owner, 25 October 2026), so Bluesky's search for *#EI-ENK* lists every time that aircraft crossed. Every shape and the owner's own templates:
  - where the words already show the registration after a space or at a line's start, that one becomes the hashtag (*Aircraft #D-EABC*, *✈ #RYR5ZK · #EI-ENK*, *#EI-ENK, a Ryanair…*);
  - otherwise it goes first among the hashtags (*#EI-ENK #ADSB #avgeek*), or first in a template's `{hashtags}`;
  - written as registered, hyphen included, which Bluesky keeps inside a hashtag (its own rule, checked in atproto's `TAG_REGEX`);
  - within the 300 characters: never dropped to fit (the other hashtags go first, then the text gives way); a long text cut where the registration stood gets it back among the hashtags; never twice; kept with `social hashtags none`.
  - The summaries carry none: they are about many aircraft.
- The console's tag list says so: *{registration}: the registration, as a hashtag: #EI-ENK*, in every language.

## 0.55.0
Two of the owner's requests of 25 October 2026.
- **Aviation units: nautical miles, knots and feet**, as pilots and air traffic control count, a third choice beside metric and imperial: `sudo zenithboard units aviation`, the installer's units screen, the wall menu, the console (*Wall → Units*, the first steps), a tablet's own (`?units=aviation`, its gear, a preset).
  - The wall: `ALT 35000 FT`, `SPD 450 KT`, `6.6NM NNE` on its last line; the radius in nautical miles (`WITHIN 10 NM`).
  - The posts (`sudo zenithboard social units aviation`, or the wall's own): feet and knots; a range record *over 175 NM*, rounded down to 25 NM, never the figure; the map's scale in NM. NM, kt and ft are the ICAO abbreviations, the same in every language.
  - `/stats` now follows the wall's units for its distances, in imperial and aviation too (the farthest box and line, the chart and the table, in mi or NM); before, they were in km whatever the units. Its altitudes were already in feet with imperial. The reviewed translations kept their words: only *km* became the unit's place.
- **Hindi (हिन्दी)**, with India's flag: the console, `/stats`, graphs1090's page and the Bluesky posts, 834 strings. Asked first whether Tamil, Hindi and Urdu could reach 90%, the answer was not without a native review, Hindi the easiest; the owner asked for Hindi, published like Swahili before its review. Its review sheet is `docs/translations/hi.csv`. Plurals: one for 0 and 1 (CLDR); large numbers in crore on `/stats` (*35.8 क॰*). Tamil and Urdu are not in.
- New console strings, in every language: *aviation*, *Aviation*, *NM · kt · ft*; on `/stats` the farthest distance's words now take the unit (`{n} {unit}`).

## 0.54.18
The owner's notes from a fresh card and a week of figures (25 October 2026).
- **A fresh card no longer asks about GitHub's signing key.** The first update listed GitHub's keys, the expired one first, and asked to compare with the *Verified* badge: it read as an error. That question came right after `install.sh` had run as root from the same clone, so it added no check. GitHub's current key (`968479A1…B5690EEEBB952194`, the key ID of `main`'s signature, and the key file as the owner's fresh card read it) now ships in `lib/versions.sh` and is trusted without a question. A key GitHub adds later is still shown and asked about. Expired keys are no longer listed.
- **ADSB Exchange's update no longer prints the station's UUID.** Their script says *Using existing valid UUID (…)*, and an update's output is pasted: hidden, as the stats installer's already was.
- **`/stats` counts the aircraft that crossed between two samples.** One look at `aircraft.json` every fifteen minutes missed about 11% of the day's aircraft (2 554 on 23 October against FlightAware's 2 878). The wall already looks every five seconds for the farthest aircraft; it now also notes every address of the day in memory, and the quarter-hour sample adds them to its files. Nothing more is written to the card. The list is answered on the loopback only (`/api/seen`). Without the wall, the quarter-hour look alone, as before.
- **The week's messages fit their box.** *386 530 3…* became *386,5 M*, written the language's way, from ten million on; the whole number is in the tooltip.
- **Bluesky in Start here, and no summaries' switches without an account.** Start here offers the account (optional) before the console. The console's first steps showed the two summaries switched on for an account that did not exist; without one, the step now says how to set it up and shows no switch.
- **The installer says where to find the position**: [mapcoordinates.net](https://www.mapcoordinates.net/en) gives the latitude, the longitude and the elevation of the spot you click; the altitude question adds the antenna's height above the ground.
- **"16 not upgraded", explained.** apt counts the system's own packages that have a newer version. Installing one never upgrades the others, and ZenithBoard never runs the system's upgrade: nothing is broken meanwhile. The end of an update now says how many, and the command (`sudo apt full-upgrade`, then a reboot for a new kernel).
- **An independent review of these changes** found what was fixed before release: ADSB Exchange's update runs unfiltered when its settings file lacks a value (it then opens its own setup screens, which a filter would hide); the aircraft added after midnight go into yesterday's fleet file too; `/api/seen` refuses a request that came through a reverse proxy; the system-updates count is apt's own.
- **The console:** the Pages in three groups that fold to their title (*On this Pi*, *The networks you feed*, *Bluesky*), remembered by the browser; more than two other browsers and phones folded under one line in *Signed in*; the disclosure triangle given room before its text. Four new strings, in every language.

## 0.54.17
The 22-23 October audit's optional findings on **robustness** (lot C, chosen by the owner on 25 October 2026). Nothing on the web pages changes, so no translation.
- **`console pair` draws its QR code the first time too**: without `qrencode` it printed a long link to type; it now fetches the small package once (the link stays below the code either way, and an offline Pi still gets the link).
- **A sign-in on a Pi whose clock is behind** (a boot before the network gave it the time) no longer dies at once: it was older than the last *sign everyone out* and refused at the next request.
- **The Bluesky service starts once the clock is set** (`time-sync.target`): the summaries are dated by it, and a Pi has no battery clock.
## 0.54.16
The 22-23 October audit's optional findings **in the terminal** (lot B, chosen by the owner on 25 October 2026). Nothing on the web pages changes, so no translation.
- **A new Bluesky app password does not replay the two wizards.** Changing only the password asked again every word and every picture setting; for an account already there it now says *saved and checked* and keeps them.
- **`stats on` offers the `/stats` page only when the wall that serves it is installed**; otherwise it says the page comes with the wall.
- **`zenithboard logs uat` and `logs social` say *not installed*** on a Pi without 978 MHz UAT or the Bluesky service, like the feeders' logs since 0.54.6, instead of journalctl's bare *-- No entries --*.
- **A Wi-Fi network joined from the menu with a wrong password offers to type it again**: it was saved as typed, and the menu went back with only a warning.
## 0.54.15
The 22-23 October audit's optional findings on **the web console** (lot A, chosen by the owner on 25 October 2026); three strings translated into the 20 languages.
- **Finish setting up asks only for what is missing**: the antenna's position and a decoder. Statistics and the watchdogs are choices, shown on the overview; a Pi without a hardware watchdog could never finish setting up.
- **Signing out a lost phone signs out what it signed in**: the computers it said yes to and the phones paired with a code it made (and so on). They stayed signed in.
- **The gain log switched on in the console is read there too** (*Read it*, beside its switch); it could be read only over SSH.
- **The statistics page, while they are off, names the console and the menu** beside the command.
- **The wall's gear panel points at the web console and the menu** for the defaults of every screen, not at `zenithboard config`, which only reads them.
## 0.54.14
The rest of the tests the 22-23 October audit found missing (batch 6), and one thing they found.
- **A console job that runs past its time is stopped with everything it started.** The helper stopped the command it ran, not what that command had started: a child left running kept the output open, and the job went on past its limit with the page showing it running. Each job now runs in its own process group, stopped whole. The line saying so comes from the stop itself, not from the clock.
- **Tested now**: the helper's time limit, its log's cap, the jobs it keeps and the journal's length (the limits can be lowered from the environment for a test; the Pi keeps 5 minutes, 1 hour for the long ones, 256 KB, 60 jobs, 400 lines); what `wifi apply` does at boot for Wi-Fi on, off or never chosen, and what a failed join says; what the Pi says of a Tailscale running, waiting for its sign-in, and where to reach the wall and the console over it; the static pages' translation, a link moved inside a sentence keeping its address; `summary-when --facts` and `template-tags`; a summary posted for real posts once and deletes its picture, after a refusal too; the update of the components, run whole on a Pi with nothing installed, reaches *Update finished* without apt. The ADS-B step itself, with its screens scripted: its plan names what goes and what comes and does it, then guards MLAT; 978 MHz UAT is offered in the United States only; No at the plan does nothing.
## 0.54.13
The tests the 22-23 October audit found missing (batch 6 of the list in *Project status*): a green suite proves the logic, never the hardware, and these make that proof wider. Two small things the new tests found are fixed with them.
- **The wall's own HTTP server is now tested end to end**: `/api/planes` asks the internet for photos and routes only when the settings say so (nothing with them off, nothing in the demo), keeps one aircraft when asked by its address and ignores anything else, and says *no_data* without a decoder; `/demo/` answers only in the demo. The console goes through the same server: the sign-in sets its cookie, a body over the limit gets 413, a POST elsewhere 405, and a backup downloads with its name, never without a sign-in.
- **Every console button names a command the command line knows**: a renamed case in `bin/zenithboard` would have left a button answering *Usage:* with every suite green.
- **The position written into the decoder's and feeders' files is tested** (dump1090-fa's options, ADSB Exchange's file with the altitude's unit glued, Plane Finder's JSON with its other keys kept). Found by it: dump1090-fa's options kept a double space after the position; gone.
- **The security check's own function is tested** on a folder of units, with the console's root helper set apart, the *no service yet* line, and a `console.env` readable by others. The units' folder is one setting for every service (`ZB_SYSTEMD_DIR`), so no test writes the real `/etc/systemd/system`, even run as root.
- **Tests that depended on the machine**: the Bluesky command-line checks could have used the real account on the Pi (they now read the test's own files); *node missing* failed wherever node is in `/usr/bin`, as on the Pi; the ACARS check failed on a leftover `__pycache__`; two test servers were waited for with a fixed sleep; the `qrencode` check was empty where it is installed; a temporary-folder check looked at the whole system's.
- **Also tested now**: *Post now* remembers a post that went out and not one that failed (it caused a double post in 0.19.2); every country of the address blocks has its flag; the newer preview is the one shown; `console signout` keeps the password and signs everyone out; every service shipped has the sandbox basics, a new one included; the command-reference check reads command names with digits; the gain check counts exactly one `--gain`; a language marked *draft* is not offered by the wall. The update's two unit paths follow the same setting.
- **The documentation's own findings** (batch 7): graphs1090 and the web console move to *proven on hardware* in *Project status* (installed and used from the console on the reference Pi on 21 October; an update from the page is still not seen); the position is checked when Next is pressed, not as you type; the phone is paired from *System → Signed in → Pair a phone*, and graphs1090 comes back ticked in step 4 of *Start here*; a paired phone stays a year (a month unused), not 30 days; behind a reverse proxy (`BIND_ADDRESS=127.0.0.1`) every visitor looks like the Pi itself, so the proxy must filter; a lost phone is signed out from the console first; *Testing* gives the full shellcheck line, the packages the split-flap tests need, and the real time the suite takes.
## 0.54.12
Low-severity findings of the 22-23 October audit on **robustness and the tools** (batch 5 of the list in *Project status*). Nothing on the web pages changes, so no translation.
- **`config.env` is written whole or not at all.** It was rewritten in place from a copy in `/tmp`, so a power cut at that moment could leave it cut short, and two writers at once (the console's helper and the menu) could lose one setting. The new file is now written beside it, put on the card, and renamed over it in one step, one writer at a time.
- **A failed copy of ZenithBoard's files says so.** The deploy removed the old folders, then copied without checking: an interrupted copy (a full card) left `/opt/zenithboard` without its files and nothing said. It now stops with the cause to look for and the command to repair.
- **`gpg` is installed with whiptail and curl** at the first run. Without it the update's signature check said *the commit is not signed*, which was not true; it now says gpg is missing and how to add it.
- **The monthly link check watches three more addresses**: graphs1090's installer, GitHub's signing key, and one of Tailscale's real files (the folder answers nothing). Not reachable from where this was written: the next monthly run is what checks them.
- **`acars remove` takes the old `ACARS_*` settings too.** On a Pi where only they were left it said *Nothing left* and kept them; they are now listed and removed.
- **`zenithboard health` says whether the clock is set from the network**: the statistics and the summaries are dated by it, and a Pi has no battery clock.
- **`i18n.py apply` refuses a sheet saved as plain CSV by Excel** (the computer's own encoding, which has already lost every letter outside it) with what to do, instead of a Python error. *Translating* says how to save it, and names the `posts` rows of the sheets.
- Comments that said the wrong thing: the statistics' and gain log's services run as `zenithboard`, not root; the Wi-Fi service's sandbox note was the network watchdog's; the Tailscale address sat under *Flightradar24* in `versions.sh`. The wiki's home page said twelve languages: 21.
## 0.54.11
Low-severity findings of the 22-23 October audit on **the wall** (batch 4 of the list in *Project status*).
- **The gear panel shows the radius in use.** A radius that is not one of the presets (12 km, set with `config-set` or `?radius=`) showed as the first preset, 1 km; it is now listed where it falls, and selected.
- **Seconds per aircraft in the gear panel are 2 to 60**, whole seconds, like the Pi's own setting: 0, -5 or 600 typed there stayed displayed while another value applied; the field now puts back what applies.
- **The photo's credit link goes to Planespotters and nowhere else.** The link in Planespotters' answer became the credit's address unchecked (a `javascript:` or another site would have been followed from the wall); it is kept only on planespotters.net over https. The photo and its link no longer send the wall's address as the referrer.
- **The CGNAT warning of `zenithboard ddns status`** is for 100.64.0.0/10 exactly: it also warned for ordinary public addresses such as 100.7.x or 100.10.x.
## 0.54.10
Low-severity findings of the 22-23 October audit: **Esc, numbers and the last menu details, in the terminal** (batch 3 of the list in *Project status*). Nothing on the web pages changes, so no translation.
- **Esc on a yes/no question no longer switches a feature off.** *Photos*, *Routes*, *Monthly refresh* and *Offline registrations* (and a Wi-Fi network's *Auto-connect*) took Esc for No; now only Yes and No change anything.
- **Seconds per aircraft are whole seconds, 2 to 60**, in the menu and `zenithboard cycle`, as the presets and the console already had it. 0, -3 and 600 were taken, and `10s` was dropped without a word; the menu now asks again with the reason.
- **The gain steps say only what happened.** *so 48.0 became 48.0* is gone when nothing was rounded, and a step past the maximum or the minimum says *Already at the maximum* instead of restarting the decoder for nothing.
- **Tailscale's sign-in says that Ctrl+C from the menu closes the menu too**, and how to start again.
- **A new look of the wall followed by Esc on the colour** keeps the look, restarts the wall and says *colour unchanged*; the look was written with no restart and no word.
- **Uninstall everything**: its first question no longer reads as two (*Yes* goes on to the typed word; *No* to make a backup first), and its last one names the Bluesky app password and the console's password among the settings, and says that the statistics and the posts' history in `/var/lib/zenithboard` stay, with the command to delete them.
- **The backup sub-menu *Show, list, delete older backups*** holds just that: *Make* and *Restore* were there twice; the entry that deletes is not the last one.
- **The web pages' language says *not chosen yet*** in the menu as in the command (it said *en*), and setting it says when a browser takes it.
## 0.54.9
Low-severity findings of the 22-23 October audit on **the Bluesky menu and its wizard, in the terminal** (batch 2 of the list in *Project status*). Nothing on the web pages changes, so no translation.
- **The Bluesky menu has seven entries and Return**, grouped like the console's Sharing page: switch sharing on or off, the account, words and rules, how a post looks, summaries, try it or post now, status. It had fourteen, and *Return* fell under the fold of a 24-line screen. A test holds it, and the new sub-menu, to seven.
- **Removing the account asks you to type `remove`**, and says what goes: the app password on the Pi, the service, and the history behind *rare* and *farthest*. It was a plain yes/no, one line above *Return*. The command asks too; `social remove --yes` does not.
- **The words wizard writes nothing until its last answer.** Each answer was saved as it came, so an Esc at the third question kept the first two.
- **The posts' language is chosen by name** in a list, not typed as a code; a refusal says *Nothing was changed.*
- **The picture wizard's last screen names the menu entries** (*6 Try it, or post now*, *1 Switch sharing ON*) beside the commands.
## 0.54.8
Low-severity findings of the 22-23 October audit on **the web console's words** (batch 1 of the list in *Project status*), seven strings translated into the 20 languages and three moved; the review sheets are regenerated.
- **The summaries say when they cannot go out.** They could be switched on with no Bluesky account, or with posting off, and nothing said so (the wizard applied them in silence too). The Summaries card and the wizard's step now say *no summary goes out until…*, and where to change it.
- ***Try a post* on an empty sky no longer offers a picture that is not there.** The *The picture* button comes only after a try that drew one, in the card and in Activity; the page itself, opened before any picture was drawn, says why instead of a bare *not found*; the try says to come back when the wall shows an aircraft nearby, and that nothing is wrong with the settings.
- **The line under *What is worth a post* follows the choice**: *Everything: every crossing* only when Everything is lit.
- **The first steps count themselves** (*7 short steps* came from a fixed word).
- **Phone sign-in**: an out-of-date code has a *New code* button (it waited for a reload the page did not mention); a computer signed in by the phone is listed *by the phone*, not *password*; a pairing code refused after the wall restarted names both ways to make a new one, the console's and the terminal's.
- **Emptying the templates field and saving goes through *Delete them all*** and its question, instead of deleting them without a word.
- **Enter in a field does what its button does** (the position, the radius, the place name, a summary's time…).
- **The decoder's menu is named as it is** in the console and the README: *1 ADS-B → 1 Decoder and networks*, not *1 ADSB* (also in `zenithboard region us`).
- **Switching sharing on, or the picture's look, may take minutes**: it may install Node or Pillow first, and the console now allows it the time (it stopped such a job after five minutes).
- Already fixed before this batch, crossed out: the pairing window naming Safari for every phone (0.53.8).
## 0.54.7
Low-severity findings of the 22-23 October audit on the web console's words, **translated once into the 20 languages** (five strings; the sheets are regenerated).
- **A forgotten password has a line on the sign-in page**: over SSH, `sudo zenithboard console password` (a new one; every browser and phone is signed out). It said *Wrong password.* and its only help was about phones.
- **The pairing window says the phone must be on the home Wi-Fi**, not mobile data, not a guest network: a scan from outside failed with no word from ZenithBoard.
- **A full card is not the helper's fault.** Starting a change on a full card said *Turn the console on again*; it now says the card is full and which commands show what takes the room.
- **A command that fails points at what it printed**: *Read what it printed beside the button, or in Activity*, not only *See Activity*.
- **The Tailscale switch says what it waits for**: your account and its app ready, up to an hour for the sign-in, other changes waiting behind it, and how to give up.
- **After an update the page of the old version reloads itself** once the wall answers with the new one. It kept showing the old version everywhere and never said to reload.
## 0.54.6
Low-severity findings of the 22-23 October audit that go together: **updating, and finding out why something is wrong**, in the terminal.
- **A key refused at the first question stops the update there.** It led straight into a second question (*Install it anyway?*) that a novice cannot judge, and the update then went on. Now: *Not trusted, so ZenithBoard was NOT updated*, with what to check on GitHub and the command to start again. A key that could not be fetched (no gpg, no internet) is not called a refusal.
- **`update quick` really is without apt.** It was documented as *no apt, in seconds* and ran `apt-get update` every time; only the components apt itself upgrades (dump1090, piaware, fr24) need it now.
- **A gone download folder says what to do**: the path, and the two commands to get it back, instead of *git clone it again*.
- **A failing feeder has a log to read**: `zenithboard logs adsbexchange|piaware|fr24|planefinder` (the status screen's own names); one that is not installed says so rather than printing journalctl's bare *-- No entries --*. The MLAT line in `status` points there.
- **Health explains itself**: *free some space* says where (the logs, the backups, graphs1090's history); with the logs not kept it says how to turn them on in each of the three ways, and *no earlier boot* says why. One name, *Logs kept after a restart (keeplogs)*, in the screen, the menu, the command and the README (it was also *Saved logs*).
- **`graphs1090` is in the list of names `update only` takes**, in the usage line and the Command reference.
## 0.54.5
Low-severity findings of the 22-23 October audit that go together: **the first hour, in *Start here***, where one wrong step threw the novice out or left them guessing.
- **After a restore, the networks the backup fed are ticked** in *ADS-B → Decoder and networks* (FlightAware, Flightradar24, Plane Finder, and ADSB Exchange's stats). Their identities were waiting for exactly that step, and the list started with everything unticked, as if the backup had said nothing. The screen says *Ticked already: the networks your backup fed.*
- **A backup step left no longer ends *Start here*.** A wrong path or Esc threw the novice back to the main menu, four screens before where they were; it now says it goes on without a backup and does.
- **A mistyped console password is asked again** (*Try again?*) instead of ending *Start here* at the main menu with the console off and no address shown.
- **Backing out of an ADS-B screen is not called a missing internet.** *Start here* now says you left the step and to choose it again; the *usually no internet* line stays for a decoder that failed to install. The step ends with *Press Enter to continue*, not *to return to the menu* when *Start here* goes on.
- **Esc at one of the first questions** (region, units, position) stops the installer with a line saying what is kept and how to start again, instead of nothing.
## 0.54.4
From the 22-23 October audit, the wall on the tablet (one *high* and one *medium* finding that the earlier batches had left).
- **The wall no longer blames the decoder when it is the tablet that lost the Pi.** Three failed polls in a row (the Wi-Fi, the Pi restarting) showed *NO DATA – RECEIVER NOT RESPONDING – CHECK THE DECODER*, which sent people to a decoder that was fine. It now says **NO ANSWER – THE TABLET LOST THE PI – CHECK THE WI-FI**. The decoder's own screen is unchanged in meaning.
- **That old screen was cut at both ends.** *RECEIVER NOT RESPONDING* is 137 dots wide and the wall has 128: it is now on two lines. A test now measures every centred text of the wall against its width.
- **The wall no longer reloads into the browser's error page.** After a minute without an answer it reloaded itself; with the network still down that left the browser's own error page on the tablet until someone touched it. It reloads now only once the Pi answers.
- Both screens were drawn in headless Chromium from the real server before this release (the one without data, the one with the poll refused).
## 0.54.3
Low-severity findings of the 22-23 October audit that go together: **screens that point to the wrong place or contradict each other**, in the terminal menu. Nothing on the web console changes, so no translation either.
- **Menu paths that do not exist any more.** Nine screens said *menu 1 ADSB* (the entry is *1 ADS-B → 1 Decoder and networks*), or *Settings > Network > Wi-Fi*, *Network > Fixed IP*, *4 Domain name*; the restore's two lines about graphs1090 sent the novice to two different menus. Each now names the entry that is there. `tests/test_menus.sh` fails if one comes back.
- **Port 80 said two ways.** One screen told how to forward the receiver map's port 80, the next said never to. It is *never* everywhere (port 22 too), in the domain-name help, its links and the README. The link line for the map now says it is for the home network.
- **Back to automatic (DHCP) warns like the fixed address does**: if you are connected through that connection the session drops, and the screen says where to find the Pi again (`zenithboard.local`, or the router's list of devices). The same sentence is in the Wi-Fi warning.
- **The domain-name success box scrolls** (its last lines were cut off), and its *Next* comes first and points at *From outside your home, safely*, not at port forwarding.
- **`tailscale console on` says when Tailscale is not connected** (it used to say the console now answers Tailscale's addresses, to nothing).
- **A restore on a card that has no Tailscale says so**: the settings come back with Tailscale on, the program and its sign-in do not; the command is in *Still to do*.
- **MLAT is explained in *Start here*, and zero is not *OK***: `zenithboard status` showed *0 (OK: max 1)* when ADSB Exchange's MLAT was not running.
- **The place name prompt says the posts are public**: a town or a region, not your village (it was in the wiki only).
- **Roadmap**: *an update from an old release* is no longer a condition of 1.0 (the owner, 23 October 2026: he is the only one who has installed it, so an update from a release nobody runs proves nothing).
## 0.54.2
The last two *medium* findings of the 22-23 October audit, both in the first hour of a new card.
- **The console's first steps no longer open on an empty reading.** Right after *Start here* the Pi had never been read by the console's helper, and the steps said *no decoder*, *nobody yet*, every network *not installed* and every watchdog off, sending the novice back to the terminal for something that was there. The page now waits for the first reading (25 seconds at most, then it opens on what it has) before the first screen.
- **ADSB Exchange's own boxes: a screen with what to type.** Their installer asks the position again (it takes no default) and refuses an altitude that is not whole metres or feet with the unit glued to the number: `180m`, not `180`, not `180 m`, without saying why. ZenithBoard's note before it printed `180 m` (the very form the box refuses) and their full-screen dialogs drew over it anyway. It is now a screen of its own, kept until OK, with the name rule, the latitude and longitude already set, and the altitude in the form their box takes (rounded to whole metres). Shown in a plain list when there is no screen.
## 0.54.1
From the 22-23 October audit: claims in the docs and in the tests that were not true, corrected, with no change on the Pi.
- **`tests/test_versions.sh` now checks what the docs said it checked.** *Testing* and *Release process* said it fails when the version numbers drift; it only checked that the number had the shape x.y.z. It now compares `lib/versions.sh` with the wall server's `VERSION`, `docs/wiki/Home.md` and `docs/wiki/Project-status.md`.
- **A menu-size check that was upside down.** *No menu has more than seven entries* had a stray `!`, so it passed only because the main menu broke the rule it states. Fixed: the main menu (Start here, seven subjects, Exit) is set apart, every other menu is held to seven entries and its way out.
- **Project-status** credited `tests/test_install.sh` with the deployed wall answering and the uninstall; it does neither (`curl` is a stand-in there, the uninstall is a source check). Said as it is.
- **Web console, troubleshooting**: Tailscale is *refused by design* said a line that 0.46.0 made false; it is refused until `sudo zenithboard tailscale console on`.
## 0.54.0
From the 22-23 October audit, the one finding that touches the rule *the receiver's position is never given away*:
- **The wall's data answers only to the Pi's own names.** The wall checked where a request came from, not the name it was addressed by. A page on another site that points its own name at the Pi (*DNS rebinding*) is read by a browser on your home network, comes from a private address, and could ask `/api/planes`: the aircraft's positions and distances, from which the antenna's position follows. `/api/*` and `/social/preview*` now answer to an address, a local name (`*.local`, `*.lan`, `*.home.arpa`…), the Pi's own name, your `DDNS_HOST`, or a name listed in `CONSOLE_HOSTS` (the console's rule), and give anything else a 403 that says how to add a name. The tablet by the Pi's address, `127.0.0.1` (the statistics timer), `localhost`, `zenithboard.local` and a request with no Host header (not a browser) are unchanged. **If you open the wall by a name your router gives the Pi (`pi.fritz.box`), add it once:** `sudo zenithboard config-set CONSOLE_HOSTS pi.fritz.box`. Not asked at all when `ALLOW_FROM=any`: then any name is meant to reach it.
- **"Uninstall everything" stops the Bluesky service too.** It left it running and enabled. Switched off, not removed: the account goes with the settings if you delete them at the end, and stays if you keep them.
## 0.53.8
From the 22-23 October audit: two promises the console made that its own file could not keep, and two lists that had fallen behind.
- **The console's Backup card no longer offers its file for a new card.** It said *to keep, or to start a new card where this one stopped*; the file it makes leaves the networks' identities out (keys never travel through a browser), so on a bare card ADSB Exchange, FlightAware, Flightradar24 and Plane Finder would each start as a new station. The card says so now. And `backup restore` says it too, before the typed word, when it is given a console copy on a card with no network yet; the *Start here* question names the full backup. A full backup is not told anything.
- **An iPhone's installed app cannot be signed in by a QR code**: a QR code opens in Safari, the app keeps its own cookies. The card told an iPhone to add the page from Safari and *sign in once more inside it*, and the pairing window said *add it to the home screen from Safari*, to a phone that was paired without a password and had no way to sign in the app. The card now says to use the console password (and to choose one first when there is none), and the pairing window no longer suggests it.
- **The menu's *Language of the web pages* offers all 21 languages.** It named 14: Polish, Finnish, Estonian, Latvian, Lithuanian, Swahili and Arabic were missing, though `console lang pl` took them. Arabic is named in Latin letters there: whiptail neither shapes nor reverses Arabic.
- **`update quick` keeps graphs1090's page in step.** The page holds its own copy of the catalogues and the list of languages; the quick update refreshed the wall and left that copy behind (the full update and `console lang` did not).
- Three console strings changed and are translated into every language; the review sheets are regenerated.
## 0.53.7
From the 22-23 October audit, three places where the menu or the update said *done* when it was not:
- **The words wizard no longer says *Saved.* after a refusal.** *Sharing radius* and *Minimum minutes between posts* took anything: a letter was dropped in silence, and 0, 500 or -5 were kept. They follow the commands' own rules now (`social radius`: whole kilometres, 1 to 200; `social gap`: whole minutes, 0 to 1440) and ask again with the reason.
- **`social on` tries the account first.** A refused app password used to give *Social sharing is ON* and only `zenithboard logs social` knew. Now Bluesky's refusal (400, 401 or 403) stops it, nothing is switched on, and it says what to do. Bluesky not reachable just now (the Pi offline for a while) is said and does not stop it: the posts wait for the network.
- **An update whose ZenithBoard code could not be pulled no longer ends *Update finished*.** The components were updated, but the first screen afterwards was the old version, with exit 0 and a *done* toast in the console. It now says *Update NOT complete*, names the version it is still on, and exits 1.
- The wiki's wizard table said the gap defaulted to 120 minutes with ten as a floor: it has been 0, no floor, since 0.20.0. Corrected.
## 0.53.6
- **CI now runs every test.** Its list of shell suites is written by hand on purpose, and five were never on it: the web console's, the backup's, Tailscale's, ADSB Exchange's stats and the translations' (`tests/test_i18n.sh`, the one that fails when a string is missing in a language). The five green checks on a pull request did not cover them. They are on the list now.
- **A test file left off the list fails `tests/test_docs.sh`**, for the shell and the JavaScript tests alike, so the list keeps its visible diff without being able to drift again. Found by the audit of 22-23 October 2026, which several independent reviewers reported.
## 0.53.5
- **The 41 translations *à trancher* settled** (the owner, 23 October 2026: the first proposal of each). They cover 18 languages. Examples:
  - *Großraumflugzeuge* for heavies in German, *Wide-body* in Italian;
  - *Exit-Code*, *kod wyjścia* and *код выхода* for an exit code;
  - *publication active* for Bluesky's state in French;
  - Polish's distinct aircraft as a plural on the statistics page.

  Each one keeps the English's placeholders and tags.
- **A test that failed depending on the time.** The check that a post never shows the distance looked for "6.2", which a Finnish or Indonesian post made at 06:2x contains ("klo 06.26"). It now looks for that number alone.

## 0.53.4
- **The reviewers' corrections in 20 languages** (sheets sent by the owner, 23 October 2026). 149 corrections were taken after a `--dry` check against the English. Among them:
  - French: "1,2 million de messages" (the singular below 2), "Un des deux watchdogs est désactivé", "Rien de capté", "Les 24 dernières heures" wherever the old order remained, and a space that does not break before `: ; ? !` throughout the console;
  - Polish and Ukrainian: counts in the right case after the number;
  - Japanese, Finnish and Indonesian: the busiest hour written the language's way;
  - Indonesian: one word for the callsign everywhere;
  - German, Spanish and Russian: the menu's own name;
  - Latvian, Dutch and Ukrainian: the track captions;
  - Swahili: its first corrections.
- **Left out:** one correction found inexact (Chinese, Simplified) and one that is an instruction about spacing (Chinese, Traditional). Three reviewers' notes were done by hand (Russian, Indonesian, French). The 41 rows marked *à trancher* are not applied: they wait for the owner. Details: wiki [Translating](https://github.com/regis57/ZenithBoard/wiki/Translating).
- **`tools/i18n.py apply` reads a sheet's doubled quotes right.** From the header line alone, Python's CSV sniffer also guessed `doublequote=False`, and a plural row's corrections came out ending in `""}`. Only the delimiter is guessed now. A test holds it.

## 0.53.3
- **A real button to delete your templates** (the owner, 22 October 2026). *Sharing → Your own templates → Delete them all* in the console, asked first; *4 Delete them all* in the menu; `sudo zenithboard social template set none`. The posts go on with the other words ticked, the factual ones when none is left. Before, emptying the field and saving did it, and nothing said so.
- **And one to put them back**: every change keeps the templates before it as `.bak`. *Put back the previous ones* (console, shown while there is something to put back), *5 Put back* (menu), or `sudo zenithboard social template undo`. Today's templates take the `.bak`'s place, so a put-back can be undone too.
- The console's new strings are translated into each language.

## 0.53.2
- **The project's site, zenithboard.app.** A static site in the console's languages that explains ADS-B, how to build a receiver, how to join ADSB Exchange, FlightAware, Flightradar24 and Plane Finder, and what ZenithBoard does. Linked from the README and from the console's side bar (*Learn more ↗*, translated into every language). Its source: [regis57/zenithboard-site](https://github.com/regis57/zenithboard-site).

## 0.53.1
- **Swahili is offered** (the owner, 22 October 2026): the console, the statistics page, graphs1090's page and the Bluesky posts, chosen like any other language, with the map of Africa as its picture. It was translated in 0.48.0 and held back for a native speaker's review, which has not come. Its review sheet stays open for corrections, applied like any other language's. 21 languages in all.
- Holding a language back with a `draft.txt` in its folder still works, for the next one that needs a review first.

## 0.53.0
- **The web console as an app** (the owner, 22 October 2026): its own icon and its own window on a phone or a computer. *System → The console as an app* says how for the browser in hand:
  - iPhone and iPad, in Safari: *Share → Add to Home Screen*;
  - Android, in Chrome: *⋮ → Add to Home screen*;
  - a computer, in Chrome: *⋮ → Cast, save, and share → Install page as app*; in Edge: *Apps → Install this site as an app*; in Safari on a Mac: *File → Add to Dock*.
- **Why the browser's menu.** Browsers show their own *Install* button only on an https address, and the Pi answers in plain http on the home network. On an https address (Tailscale or a domain that serves https), the card shows *Install the app* itself.
- **What it adds:**
  - a manifest;
  - icons drawn from the wall's own shapes and dot font (`tools/make_console_icons.js`): 192, 512, a maskable 512, and 180 px for iOS;
  - a service worker that keeps nothing (nothing stale is ever shown), registered only over https.

  The console's security headers are unchanged. Its new strings are translated into each language.

## 0.52.1
- **The time of day in the posts, as each language writes it**: *Di atas Trémery pukul 13.50* in Indonesian, *klo 13.50* in Finnish; 13:50 elsewhere. The owner read *pukul 13:50* on 22 October and asked whether *pukul* (also *to hit*) was right. It is the standard word before a clock time. The colon was the mistake: Indonesian spelling (EYD) separates hours and minutes with a full stop, and so does CLDR. This covers the board's line, your templates' `{time}`, and the summaries' busiest hour.
- **The metric units in the posts' language too**, from CLDR like the numbers and dates: *839 км/ч* and *10 670 м* in Russian, *км/год* in Ukrainian, *km/u* in Dutch, *km/godz.* in Polish, *km/j* in Indonesian, *10,670米* in Chinese, *839km/h* in Korean. In Arabic the word for metre follows the count (متر, أمتار, مترًا). French takes CLDR's narrow space before the unit (*10 670 m*). Feet and knots stay *ft* and *kt*, as in aviation. The pictures keep their English labels.
- English is unchanged: 5 610 posts, summaries and alt texts compared with 0.52.0, byte for byte.

## 0.52.0
- **ADSB Exchange's stats, optional, off by default.** The owner asked why ADSB Exchange's page shows *Feed UID Not Found / No Stats* under *Feed Details* while his feed and MLAT are fine (22 October 2026). That panel is filled by a second ADSB Exchange program, their stats package, which ZenithBoard did not install. Their script was read before it was added (`adsbexchange-stats`, commit 11647f2). Every 5 seconds it sends ADSB Exchange the aircraft list their feed already gets, the feed's UUID, three signal figures and the Pi's power warnings. In return you get *ADS-B Exchange Anywhere* (their map of only the aircraft your antenna hears, from anywhere), your receiver's statistics, and the claim of the receiver under an ADSB Exchange account if you want one. It can be switched on in three places:
  - the terminal: `sudo zenithboard adsbx-stats on`, then `off`, `status` or `url`;
  - the menu: a tick in *1 ADS-B*'s list of networks;
  - the console: *Receiver → Measure*, with a link to your map in *Pages*.
- **`off` puts back what `on` found**: their own uninstaller, then the packages their script added (jq, bind9-host, bash-builtins: whichever were not there before) unless something installed since needs one, and the video group it gave the `adsbexchange` user. The feed's UUID stays, so `on` again gives the same map. A copy installed by hand with their two lines is seen as on; `off` removes it and touches no package.
- **Removing ADSB Exchange removes its stats first.** Their feed's uninstaller leaves the stats service running, and it fails every two minutes without the feed. `zenithboard update` runs their stats script again when it is on, as their README says to update it.
- **The link to your map carries the station's UUID, so only `adsbx-stats url` and the console show it.** `on`, `status`, `zenithboard status` and the update's output say where to find it instead; they are often pasted or screenshotted. Their script prints the UUID and the link at its end, and both are hidden as `(id hidden)`. `zenithboard health` hides any station UUID in the last lines of a boot that ended abruptly; their service writes its UUID there at every start.
- **What `off` could not put back is kept for the next `off`**, for instance when apt is busy with the daily security fixes, or when the group is refused. Before, the notes went anyway, and a second `off` said *already off* with the packages still there. Packages that something installed since needs are left with the command to remove them later. Packages graphs1090 also uses (bash-builtins, git) stay while it is on, and the other way round.
- **One package installer at a time**: graphs1090's and the stats' installers wait for each other, so one never counts the other's packages as its own. That could happen when the console ran one while the terminal ran the other.
- *Uninstall everything* removes the stats even when ADSB Exchange's feed was removed by hand first. Unticking them in menu 1 finishes what a failed attempt left.
- The stats are part of a backup's *what was on*. On a new card they wait for ADSB Exchange's feed, and the restore says the command to run after menu 1. The monthly address check covers `https://adsbexchange.com/stats.sh`. The console's new strings are translated into each language. An independent review of this release found the points above before it shipped.

## 0.51.0
- **The posts in your language** (asked for by the owner on 22 October 2026): `sudo zenithboard social lang fr`, *Sharing → Language of the posts* in the console, or *Social sharing → 11* in the menu. It stays English until you set it. Every word of the aircraft posts follows it, in all five shapes, and so do the openings (*Visiteur rare :*), the place (*au-dessus d'Ennery*), the summaries' four texts and the alt texts. Each post declares its language to Bluesky. Numbers, dates, weekdays and country names come out as the language writes them, from Unicode's CLDR (`tools/make_post_locale.js` writes `flightinfo/data/post-locale.json` from Node's Intl): *11 280 m*, *12–18 octobre*, *Allemagne*. Plurals follow each language's rules, checked against Intl. English posts are unchanged, word for word. What stays English: the labels drawn in the pictures (they wait for the dot font's letters and a CJK font), the city names from the route database, the map credits, and your hashtags.
- **Your own templates, a sixth style** beside factual, story, board, spotter and lookup: `sudo zenithboard social template add '{airline} {flight}[, {from} → {to}] at {altitude}. {why}'`, then *your own* among the words of a post (`social sentence factual,custom`). You get 26 tags: the flight, the airline and its country and flag, the registration, the type, a category, the route, the altitude, speed, climb and heading, the squawk, why it is posted, your place, the time, the photo and tracker links, your hashtags. A `[part]` is left out when a tag inside it is empty. No tag gives a distance, a direction from the antenna or a place near it. A template is checked when it is saved: an unknown tag, a `[` left open, or more than 250 characters when filled with long names are refused. `social template test` fills each one on an aircraft overhead now (or a sample) and posts nothing. The templates are also in the console (*Sharing → Your own templates*, with the tags a click away, *Try* and *Save*) and in the menu (*Social sharing → 12*), kept in `/etc/zenithboard/social-templates.txt` with a `.bak` of the version before. A backup carries them to a new card.
- **The written post of 0.50.0 is taken out**, at the owner's word: it was not what he had asked for. `social say`, its menu entry and the console's *Write a post* are gone. Posting stays out of the console. The fields for the place name, radius, rules, town names and hashtags stay.
- Hashtags and links written in a post are found the way the Bluesky app finds them, accents kept (`#Trémery`), so a template's own hashtags are clickable. The wall's aircraft list now gives the squawk, for `{squawk}`.
- A post that is still too long once its hashtags are gone now shortens its words, ending in `…`; the map's credit and its links stay whole. Before, the last cut could take the credit's end. An independent review of this release found this, and three things now fixed in it: a template's `{hashtags}` judged on all templates rather than the one drawn, the map's fallback words left untranslated, and a templates file not in UTF-8 able to stop every post.
- `tools/i18n.py` has a fifth page, *posts*, found in `social.py`, `social_week.py` and `social_card.py`. Its templates are checked for balanced `[parts]`, and the review sheets list them. Every new console and post string is translated into each language.

## 0.50.0
- **A written post: your own words, posted to Bluesky as you typed them**, text only: no picture, no map, nothing read from the receiver (asked for by the owner on 22 October 2026). It can be sent from the terminal: `sudo zenithboard social say 'Le bilan part à 08:45 #avgeek'` (`--dry` shows it and posts nothing; quote the text, or the shell takes a `#` for a comment). From the menu, *Social sharing → 11 Write a post*: it is shown first and goes when you type `yes`. From the web console, *Sharing → Write a post*: a counter, *Preview (posts nothing)*, and *Post it*, which shows the words again in its confirmation. 300 characters at most, Bluesky's limit; counted in characters, which is never fewer than Bluesky's own count. Hashtags (accents kept, `#Trémery`) and `http(s)://` links become clickable the way the Bluesky app makes them; `@names` stay plain text. No language is declared, so you write in the language you like. Until now the console posted nothing, on purpose. This is the one exception, at the owner's word, behind its confirmation. Posting an aircraft or a summary at once still stays in the terminal.
- **The words of the automatic posts in the console**: *Sharing* gains the place name, the sharing radius, what is worth a post (military, helicopters, heavies, rare types, range records, or everything), the town names on the maps, and the hashtags. Until now the console only showed them as set in the terminal. Each answer of `social words` is now a command of its own: `social area WORDS|none`, `social radius KM` (1 to 200), and `social rules all|LIST`, with `social hashtags` as before. A place name is checked the same way everywhere, the wizard included: letters, digits, spaces and `' - . ,`, 40 characters at most.
- The console's helper writes a written post's lines on one line in its journal of changes. The page no longer redraws under a text box being typed in.
- Every new or changed string of the console is translated into each language.

## 0.49.1
- **`summary why` says when the service still runs the code from before the last update**, with the command to restart it (`sudo systemctl restart zenithboard-social`). Seen on the real Pi on 22 October 2026: the files were 0.49.0, the service still 0.47.0 since 00:11, so the summaries followed 0.47.0's rules. `social status` uses the same check, which now also compares the version the service gave when it started and looks at `social_week.py`.
- **`why` lists the service's starts apart**: the last twelve, one short line each. On 21 October, twenty-four starts (one per update) took thirty-two of the forty lines `why` showed and pushed out older lines. The summary lines and the errors now have their own thirty lines. The version it runs no longer ends with a stray full stop.
- **Correction of 0.49.0, from the owner's `summary why`.** The daily summary's post 1 went out on 21 October at 09:20, under 0.40.0; the journal has its Bluesky address. Posts 2 to 4 were skipped on purpose: the airline and type lists have only been counted since 20 October, and they join from the summary of 22 October. Under the one-a-day rule of 0.38.0 to 0.48.0, that post made the day done, so moving the time to 21:00 and then to 23:35 did nothing, and those versions wrote nothing about it. 0.48.0's guess (a summary gone out earlier that day) had the cause right and the hour wrong: 09:20, not 21:00. 0.49.0 withdrew that guess because of the feed. That post is no longer on Bluesky: its address opens nothing, while the posts of 22 October do. ZenithBoard has no way to delete a post.

## 0.49.0
- **Summaries: one per scheduled slot, no longer one per day** (the owner: the day lock is in the way; the schedule is enough to keep a summary from going twice). A summary goes once at its time. Moved to later the same day, it goes again at the new time. Set to a time that has already passed today, or switched on after its time, it does not go at once: from the next day, week or month, and the service says so in its journal. A Pi that was off at the time still posts it when it comes back the same day, the setting unchanged. A summary gone under 0.48.0 or before is not posted again after the update.
- **`sudo zenithboard social summary why`**: why a summary did not go out, in one place — each summary as set, when it last went and goes next, the queue, what it needs (statistics, sharing, an account), the service and the version it runs, and two days of its journal lines about summaries and errors. `zenithboard logs social` reads the last hundred lines only.
- **Correction of 0.48.0**: it said the daily summary had probably gone out at 21:00 on 21 October before its time was moved to 23:35. The owner's look at the Bluesky feed says no summary went out on 21 October at all. That cause was a guess and is withdrawn; `summary why` is what will tell.
- The console's note under the summaries says the new rule and the `why` command, in every language.

## 0.48.0
- **The web pages in 20 languages** (the owner: translate everything in all the languages covered): the console, the statistics page and graphs1090's page in German, Dutch, Italian, Spanish, Portuguese (Brazil), Polish, Finnish, Estonian, Latvian, Lithuanian, Indonesian, Russian, Ukrainian, Arabic, Japanese, Korean and Chinese (Simplified and Traditional), beside English and French. Each has its review sheet in `docs/translations/`. **Swahili is translated in full but not offered yet**: its translation could not be promised at 90% (the owner's bar), its technical words differing between Tanzania, Kenya and the software glossaries; it waits for a native speaker's review of `docs/translations/sw.csv` (a file `draft.txt` in its folder keeps it out of the list; deleting it once the review is in offers it). **Arabic reads right to left**: the side bar, the drawer and the switches mirror; what the Pi prints, commands, numbers and the charts stay left to right, numbers in Western digits as the Pi writes them. Letter spacing is taken off for Arabic, Chinese, Japanese and Korean. **Hausa and Yoruba were asked for unless 90% could not be reached, and are left out**: Yoruba's tone marks and the technical vocabulary of both are beyond a reliable machine translation; a native speaker's sheet can bring them later.
- **A picture for a language of many countries**: Arabic shows its letter ʿayn (ع), Swahili (once offered) the map of Africa; the others their country's flag (Taiwan's for Traditional Chinese, China's for Simplified).
- **Counts in each language's grammar**: *1 avion*, *2 avions*; Arabic's six forms; the languages whose counts would need case endings say them as *label: n*. A value put in an Arabic sentence (an address, `@handle`, a command) keeps its left-to-right order, and the overview's and the statistics' numbers keep their unit after them.
- **Translations corrected on review**: the post style *lookup* is the *Look up!* sentence, not a record: French *fiche* became *levez les yeux*, German *Steckbrief* *Schau nach oben*.
- **The console's first page is not crowded** with twenty flags: the browser's own language and English as two buttons, every other language in one list.
- **A reviewer's correction is checked before it goes in**: `tools/i18n.py apply FILE --dry` lists each proposal beside the English and today's translation; `--skip ID,ID` leaves out those found inexact. A correction now applies to the same English on the other pages too.
- **Summaries: when each went out, when each goes next, and why one did not.** On 21 October the daily summary was moved from 21:00 to 23:35 after the 21:00 one had gone out, and nothing went out at 23:35: one a day, by design, but nothing said so. Now `sudo zenithboard social summary` shows under each summary when it last went out and when it goes next (and the queue), says after a change that today's already went out and the new time applies from tomorrow, and points to `zenithboard logs social | grep -i summary`; the service writes a line when a summary falls due and is queued. The console shows *last* and *next* under each summary. Tested on a simulated evening: 21:00 posted, moved to 23:35, nothing until the next day's 23:35; moved before it went, it goes at the new time the same day; the next weekly and monthly dates.
- **The summary's posts by name in the console** (the owner): *Post 1 · The period*, *Post 2 · Cargo & business jets*, *Post 3 · Military*, *Post 4 · General aviation*; the summary's *Try* says *(posts nothing)*.

## 0.47.0
- **The web pages in French** (phase 1 of the [Translation plan](https://github.com/regis57/ZenithBoard/wiki/Translation-plan)): the web console, the statistics page and graphs1090's page (its title, links, period buttons and panel titles; its graphs are pictures graphs1090 draws, they stay in English). **The first visit to the console asks the language**, by its own name and flag, before the password; once signed in it becomes the Pi's default (`CONSOLE_LANG`) for every browser that has not chosen. **A flag at the top of every page** (console, statistics, graphs1090) changes it for that browser; *System → Language* and `sudo zenithboard console lang fr` (menu *7 Options → 4 Web console → 7*) change the Pi's default. Only the languages translated are offered: English and French now. What the Pi prints (the terminal, the output shown in the cards) stays in English, as the menu does.
- **How it works**: the English text is the key (`t("Make a backup")`), so a word not translated shows in English, never blank, and the English pages are what they were. Catalogues in `flightinfo/static/i18n/<lang>/`; plurals, decimals and dates by the browser's own rules (`Intl`), country names on the statistics page from the browser's own data. English's flag is the United Kingdom's and the United States' together, cut along the diagonal; Simplified Chinese will show China's, Traditional Chinese Taiwan's.
- **Every language has a review sheet** (the owner's choice, instead of an *unreviewed* mark): `docs/translations/<lang>.csv`, the English beside the translation and an empty *correction* column. A native speaker fills it in (a spreadsheet, or GitHub's editor), the owner puts it back, and `python3 tools/i18n.py apply fr.csv` takes the corrections (refusing one that loses a `{placeholder}`). Wiki: [Translating](https://github.com/regis57/ZenithBoard/wiki/Translating).
- The console's sign-in page said *Settings → 7 Web console*, a menu gone since 0.44.0: now *7 Options → 4 Web console*. Post styles in *Sharing* are shown by their translated names.
- Tests: `tests/test_i18n.sh` (every catalogue complete and in the English's shape, the fourteen language codes the same in the four places that list them, the review sheets current, a correction applied and a broken one refused, `console lang`, graphs1090's copy put and taken away exactly), `tests/test_i18n.js` (fallback, placeholders, French and Russian plurals, the browser's language).

## 0.46.0
- **Tailscale in the web console** (the owner): *System → Tailscale* — its switch connects (installing Tailscale the first time) and the sign-in link appears in the card as a *Sign in to Tailscale* button while it waits; once on, its addresses, links to the wall and the statistics over Tailscale, and the switch for *the console over Tailscale too*; disconnecting from the same switch. *At a glance* says *Tailscale on*. Removing it completely asks for a typed word: in the terminal (`sudo zenithboard tailscale remove`), like every such step.
- **The translation project, analysed first** as asked: wiki [Translation plan](https://github.com/regis57/ZenithBoard/wiki/Translation-plan) — what is to be translated (measured), the design (catalogues keyed by the English text, the language at first sign-in and from flags at the top, `SOCIAL_LANG` for the posts), the post templates and their tags (none of them gives a distance, a direction or a place near the antenna), what can break and how it is kept from breaking, the cost on the Pi, and the order proposed. Nothing translated yet.

## 0.45.0
- **Tailscale, from the menu** (the owner): *3 Connectivity → 4 Tailscale* — how it works step by step, install and connect, the web console over it, disconnect, remove it completely, status — and `sudo zenithboard tailscale on|off|status|remove|console on|off`. Off by default. `on` installs Tailscale as its own page says for this system (pkgs.tailscale.com, `debian` or `raspbian` and the Debian version; the package checked by apt; a repository list refused unless every line is Tailscale's, signed by its key), runs `tailscale up --qr` for the owner's own account (ZenithBoard never makes one), lets the wall answer Tailscale's range and prints the addresses to use from anywhere. `off` disconnects and puts back what the wall answered; `remove` (a typed word) signs out, stops it and uninstalls what ZenithBoard installed, then says to remove the Pi from the account's machines. The console over Tailscale only with `tailscale console on` (its `100.x` address or `*.ts.net` name).
- `ALLOW_FROM` may now name `private` in a list (`private,100.64.0.0/10`); `zenithboard security` says when Tailscale is on and whom the console answers. The console's *System → Network* card has a *Tailscale* status button.

## 0.44.0
- **The menu, by what you want to do** (the owner: too many menus, some of ten entries, and nothing said that the console needs ADS-B and the wall first). **Start here** does the first installation in its order — a backup from another card if any, ADS-B, the wall, what is worth switching on, the web console — skipping what is done; then **1 ADS-B**, **2 The wall**, **3 Connectivity**, **4 Troubleshoot**, **5 Updates**, **6 Backup**, **7 Options**, seven entries at most each, one way back. The top of the main menu says what the Pi already does. Every screen, captured from the menu itself: wiki [The menu](https://github.com/regis57/ZenithBoard/wiki/The-menu), with where each old entry went.
- **What is worth switching on**, at the end of the first installation: one list, everything ticked, untick at will — statistics, graphs1090, logs kept after a restart, the hardware and network watchdogs, Debian's daily security fixes, the daily log clean-up, Wi-Fi hardening when on Wi-Fi. Only what is off is listed.
- **From outside your home, safely** (*3 Connectivity → 3*): plain words on a VPN first (the router's own, or Tailscale with the allowed range to set), what an open port exposes (no password, no encryption, roughly where you live), port 22 and 80 never, CGNAT.
- **graphs1090 in ZenithBoard's look by default** (the owner): `sudo zenithboard graphs look original`, the menu or the console's switch opt out. An update puts it on a Pi that had never chosen.
- **A restore applies what it imports** (the owner: the position, altitude and units did not follow): the antenna position goes everywhere it is stored (decoder, networks, wall), the wall and Bluesky restart, graphs1090 takes the backup's look and colour.
- **Moving to a new card, for non-specialists**: a new wiki page, step by step, with WinSCP to copy the backup from Windows; *Start here* asks for the backup first and says where to put it. Fresh install's part C now follows *Start here*.
- Menus fit their text (the box grows with it, the terminal's height the limit); entries read by their words and numbers, without the tag column. Debian's security fixes moved to *5 Updates*.

## 0.43.0
- **The statistics page follows the period everywhere** (the owner): the sky by hour (one row of the 24 hours, or a row a day for 7 or 30), the fourth box (the busiest day, or for 24 hours the busiest hour, instead of the thirty days' best distance) and the farthest aircraft (one line, the period's, instead of today's and the thirty days'). **In the order of the summary's posts**: the four boxes, the farthest aircraft, then the aircraft (sky by hour, airlines, models), cargo and business jets, military, general aviation; then how high, the messages, and the rest. General aviation rows carry their country's flag as on the fourth card.
- **Every airline starts with its flag, passenger and cargo, on the page and on the summary's first and second cards**: the country the airline is based in, now written in ZenithBoard's airline and cargo lists (each checked against a source; OpenFlights' 2014 list was found wrong for a dozen reassigned cargo codes and not used for them), or adsbdb's when it names an airline the lists do not know; else where most of its aircraft are registered. `/api/stats` carries `fleet.airline_cc`, `window.heat`, `window.busiest` and `farthest.period`.
- **graphs1090 in ZenithBoard's look** (off by default): `sudo zenithboard graphs look zenithboard|original`, menu 3 → 2 Receiver → 7, or the console. The page in black and the wall's colour with the name in dots and links to the wall and `/stats`, one graph a row on a phone; the graphs drawn by graphs1090 in matching colours, through the variables it reads from `/etc/default/graphs1090` after its own schemes. Put back after graphs1090 updates and a new wall colour; `original` takes away exactly what was added.
- **Fix: the console on a new card** stopped on *chown: invalid user: zenithboard* when switched on before the wall (a new card on a Pi 4, the owner): the wall's user is now made where it is first needed (the console's folders, statistics, a restore), and `console on` says the wall comes first.

## 0.42.1
- **`backup show` checks a backup**: each part is read back the way a restore reads it, with the span it covers (statistics samples, the days of aircraft lists, the posting history, graphs1090's databases and their last point, the kept logs' boots); a damaged part is named and the command ends with an error. `backup restore` shows it before asking for `RESTORE`, and `backup make` reads its file back once written. The reference Pi's first backup (21 October, 12:51, from the console): every part ends within minutes of it.
- **Backups do not pile up unseen**: `backup list` shows them newest first (their names carry the date, `HOST-YYYYMMDD-HHMM`, so they sort the same way); `backup clean --keep N` deletes the older ones after the typed word `delete`; the menu has both. The console keeps one copy, replaced by the next; it can now be deleted (*Delete it*, or `backup delete --console`) and downloads as `zenithboard-backup-HOST-DATE-console.tar.gz`, like the terminal's. Asked by the owner.
- **The console's Backup card says where the import is**: in the terminal of the receiving Pi, `sudo zenithboard backup restore FILE` or the menu, and why not from the page; it links the wiki. Its *Download it* is no longer underlined.

## 0.42.0
- **Backup and restore: one file carries a ZenithBoard to a new card**, and the new card carries on where the old one stopped. `sudo zenithboard backup make` writes the settings, what is on, the statistics, what was posted (no double post after a move), graphs1090's history (by graphs1090's own `rrd-dump.sh`, readable on another architecture), the logs kept after a restart, and the networks' identities: ADSB Exchange's UUID, FlightAware's feeder ID, Flightradar24's sharing key, Plane Finder's share code. `backup show FILE` says what a file holds; `sudo zenithboard backup restore FILE` puts it back after the typed word `RESTORE`, keeping what it replaces in `/var/lib/zenithboard/before-restore-DATE/`. Asked for by the owner, 21 October, writing a new card.
- **What was on is switched on again by its own command**, so the timer or the file is really there: until now `settings import` brought back `STATS=1` or `NETWATCH=1` with nothing behind them, and the hardware watchdog and the kept logs, which live outside `config.env`, not at all. What needs a secret (Bluesky, the console's password) is listed at the end with its command.
- **The networks keep their stations**: an identity is given back at once when its network is installed, else kept (root only) and taken by that network's installation in menu 1: FlightAware needs no claim, Plane Finder nothing on its page, and FR24's own sign-up shows the key to paste and has it set again afterwards. The old card's logs go beside the new card's (`journalctl -m`).
- **In the menu** (*6 Maintenance → Back up everything*) and **in the web console** (*System → Backup*: make one and download it). The console's backup leaves the identities out, and restoring stays in the terminal.
- The MAC address: on the same Pi it does not change with the card; the wiki's new [Backup and restore](https://github.com/regis57/ZenithBoard/wiki/Backup-and-restore) says where it matters (a router's reservation, FlightAware's oldest stations). Fresh install restores the backup at step 12, before menu 1.

## 0.41.0
- **A fresh install, step by step, is a 1.0 proof** (the owner, 21 October): the new wiki page [Fresh install](https://github.com/regis57/ZenithBoard/wiki/Fresh-install) goes from a blank micro-SD card written with Raspberry Pi Imager to a ZenithBoard finished in the web console, in 21 steps, each with what you should see; how to keep the feeders' identities when a card is replaced (ADSB Exchange UUID, FlightAware feeder ID, Flightradar24 key, Plane Finder share code, the settings export); why the networks are added in the terminal; a checklist. Linked from the README, the wiki's home page and its sidebar; the Roadmap's 1.0 proof now names it.
- **The console's first steps: nine screens instead of five.** New: *Welcome* (the Pi's model, version, decoder and networks), *Where the antenna is* (region, units and position, checked as you type), *Feeding the networks* (each one running or not, with a link to its own page; read only), *Sharing on Bluesky* (the daily and weekly summaries). The review applies only what changed, the position first.
- **They open again**: *System → First steps again*, the address `…/console#first-steps`, and a *Finish setting up* card on the overview while something is missing (no position, no decoder, statistics off, a watchdog off).
- The console cannot add a network: its installers ask questions, keys and claims as they go and some run their own scripts as root, while the console runs fixed commands with no input. Said on the networks' screen and in the wiki.

## 0.40.5
- **The summaries' cards say their period in words**, top right: *LAST 24 HOURS*, *LAST 7 DAYS*, *LAST 30 DAYS*; *21 OCTOBER* there read as that day (the owner). The exact span goes to the foot (*20 October, 09:20 – 21 October, 09:20*), with *lists counted since* when it applies; the first card is titled *Aircraft above Trémery* like the others.
- **General aviation with flags**: each helicopter, light aircraft, glider, drone or balloon row starts with the flag of the country its aircraft are registered in (by their address), a row per model and country, all columns aligned as on the business jets' countries. Asked for by the owner.
- **Military aircraft of unknown type are asked by their address** when the summary is made, of adsbdb then hexdb, as the wall asks for every aircraft when routes are on (two seconds apart, a dozen at most): the reference Pi's *Germany: Unknown type (2)*. Off with `routes off`.
- *ZENITHBOARD* at the foot of the cards is raised clear of Bluesky's *ALT* badge, which covered it. The first summary to show the lists is now said under the half rule of 0.40.4.

## 0.40.4
- **Fix: the summaries left their lists out until the lists covered the whole period.** The reference Pi's first daily summary (21 October, 09:20) went out with no airline, no model and none of posts 2 to 4, *Counted since 20 October: shown from the summary of 22 October*, though the statistics page showed cargo, business jets, military and general aviation for those 24 hours: the lists had begun the day before. Now lists that cover **half the period at least** are shown, posts 2 to 4 with them, and every card says since when, bottom left (*Lists counted since 20 October, 19:15*, from the earliest time in the first list, or the day alone for a list older than 0.37.0). Under half, they stay out, as 0.34.1 decided (a week against two hours says something false). `summary test` prints the date too.

## 0.40.3
- **Console: every control shows what it did in its own card**, as 0.40.2 did for the buttons: switches, choices, colours, fields applied, the summaries' settings, and the long ones (an update, graphs1090), which opened the *Activity* drawer. The command, its answer, *done* or *exit N*; the last one per section, the earlier ones in *Activity*. Asked for by the owner. The card is noted at the click, before a confirmation box.

## 0.40.2
- **Console: what a button shows appears in its own card**, under the button, as it prints: Health, Memory, the logs, Status, a try of a post or a summary (with the links to its pictures). 0.39.0 put it in the *Activity* drawer, and the owner, clicking *Health*, did not know where to look. ⤢ opens it in *Activity*, × closes it; a change that takes minutes still opens *Activity*.

## 0.40.1
- **The console's sign-in page shows the version running on the Pi**, at the bottom, linked to that version's release notes on GitHub (the releases page when it is unknown); the side bar's version is a link too. Asked for by the owner.
- **CodeQL's ten open notes dealt with**: the eight *Empty except*, and two more found alongside, (the statistics, the flags, the cargo list, the memory report, the console's host check, the social service) now say why nothing is to be done; the wall's `do_GET` no longer mixes a bare `return` with returned values. The vendored QR code generator, kept unchanged, is no longer analysed (`paths-ignore`, reason in the workflow): its note was its own missing semicolon. Seen on the *Security* tab by the owner.

## 0.40.0
- **A computer signed in by your phone**, asked for by the owner. Off by default: `sudo zenithboard console phone-signin on` (also in the console, *System → Signed in*, and the menu, *Web console → 6*). The computer's sign-in page shows, under the password, a QR code and a four-digit code; a phone already signed in to the console scans it and shows *Sign in Windows at 192.168.1.237?* with the same code; *Sign it in*, and the computer is signed in for a week (a day unused), no password typed.
- How it is kept safe: only a signed-in phone can say yes, after seeing the computer's name, address and code; the QR code carries the request's name only, the computer collecting its sign-in with a secret of its own (a photo of the screen signs nobody in); a request lasts two minutes and is answered once, then turns into one session; twenty requests per address per ten minutes; each yes or no in *Activity → Sign-ins*. Previewed with a computer and a phone side by side.

## 0.39.3
- **Console: a change waiting behind a long one says so.** The Pi runs the console's commands one at a time; while graphs1090 installed, the changes made meanwhile were reported as *the console's helper has not taken the job … console on*, again and again (the owner's recording). Now: *Queued: graphs1090 runs first, then this*, once, and the drawer says how many are before it; the helper is blamed only when a change waits with nothing running.
- *Activity*: clicking one of the last jobs shows its output at the top of the drawer, scrolled into view (it opened out of sight), and marks the job; the background *Refresh* jobs are no longer listed among the last jobs.
- The sign-in page says why it never shows a QR code. The wiki gains *How it behaves, by design* (one change at a time; where QR codes are made; a code signs in the phone that scans it, once) and two break-glass rows. Signing a computer in with the phone is written down as a proposal.

## 0.39.2
- **Fix: the console refused every pairing code**, *used or out of date*, on the reference Pi; failed codes also count as failed sign-in tries, which can hold the password back for a while. The wall had been started (by the update) before `console on` made the console's folder, and its sandbox opens for writing only folders that exist when it starts (`ReadWritePaths=-…`): it could not note the code as used, and refused it rather than let it work twice. Now a used code is known in memory first, the card's note only carries it over a restart; `console on` restarts the wall; and the page says, with the command, when the wall cannot write its folder.
- **The terminal is for setting up, not for every visit**: a browser signed in with the password stays signed in for a week (a day unused; 12 hours before), a paired phone as long as it opens the console once a month, a year at most (30 days before). The QR code needs no password; the wiki says plainly which way needs what.
- *Activity*'s and the sign-in page's messages have their own place: a message before signing in no longer shows the password form on a Pi without a password.

## 0.39.1
- `zenithboard memory`: the WHAT column cut *name on the network (mDNS)* to *name on the network (mDN*, seen on the reference Pi; now *network name (mDNS)*, and a test keeps every name within the column. Named too: Debian security fixes (`unattended-upgrades`), devices, logins, clock (NTP), Bluetooth, the web console's helper.

## 0.39.0
- **A web console, `/console`, as a test** the owner may take out again: ZenithBoard's settings from a browser or a phone on the home network, in the wall's look. Off by default: `sudo zenithboard console password`, then `sudo zenithboard console on` (menu *Settings → 7 Web console*); `off` stops it and keeps the password, `forget` deletes it. Asked for by the owner.
- One section on screen at a time — a side bar on a computer, tabs at the bottom of a phone, no long scrolling: **Overview** (up time, temperature and power, memory, card, each service, links to every page the Pi serves and to those it can serve once switched on), **Wall**, **Receiver**, **Sharing** (Bluesky, the picture, the three summaries), **Reliability**, **System** (updates, network status, who is signed in, the security check). **Activity** shows the command running as it prints, the last jobs, the journal of changes and the sign-ins. A **first-run wizard** (the wall, statistics, the watchdogs, your phone, a review) applies only what differs.
- **Signing in**: a password chosen over SSH, kept as a scrypt hash in `/etc/zenithboard/console.env` (root:zenithboard 0640); or **a phone paired by a QR code** that works once within five minutes and keeps it signed in for 30 days, made on a signed-in computer or with `sudo zenithboard console pair` (drawn dark on its own white square, in the page and in the terminal, so it scans on black). Face ID and passkeys are not offered: WebAuthn needs HTTPS under a domain name, which a plain-HTTP page at a home address is not.
- **The wall still changes nothing itself.** It checks a request against a fixed list of actions (`flightinfo/console_actions.py`) and drops a job file in the one folder its sandbox may now write (`ReadWritePaths=/var/lib/zenithboard/console/state`); a root helper started by `zenithboard-console.path` (`tools/console_run.py`) checks it again, opens it without following links, and runs that one `zenithboard` command as arguments, never through a shell, input closed, with a time limit and a journal line. Left out on purpose: uninstalling, Wi-Fi and fixed addresses, passwords and keys, posting, emptying, importing, `config-set`.
- Home networks only whatever `ALLOW_FROM` says, and by an address or a local name only (DNS rebinding); cookie `HttpOnly`, `SameSite=Strict`, `Path=/console`, sessions kept as hashes and ended by a new password or `console signout`; a CSRF token and the page's own origin on every change; failed sign-ins slowed per address and overall; a strict Content-Security-Policy. `zenithboard security` says when the console is on and checks its file.
- QR codes are drawn by qrcode-generator 1.4.4 (Kazuhiko Arase, MIT), vendored unchanged in `flightinfo/static/vendor/`. Previewed at desktop and phone width; not yet run on the reference Pi.

## 0.38.0
- **Summaries of the last 24 hours, the week and the last 30 days**, each off by default, each at its own day and time on the Pi's clock, each with the posts picked among the four (the period; cargo and business jets; military; general aviation). `sudo zenithboard social summary [daily|weekly|monthly on|off|at TIME|parts LIST|test|post…]`, menu *Social sharing → 7 Summaries*. The weekly one keeps 0.33.0's Sunday 19:00 and all four posts by default; `social weekly …` still works. A day of the month is 1 to 28. Asked for by the owner.
- The daily card shows the 24 hours as a row of lit dots; the thirty-day card a column of dots a day. Their texts say *The last 24 hours above Trémery* and *The last 30 days above Trémery, 22 September – 21 October*.
- **One queue for all of them**: several due at once go the longer first, every post two minutes after the one before; a failure holds the queue ten minutes, a summary failing for four hours is dropped and the next goes on; a post with nothing to say gives its turn; scheduled is marked at once, so a restart posts nothing twice. The crossings carry on between them.
- Statistics page: the countries column lines up with the cargo and business jet columns, with how many countries, and is called *most registered in* (on the card too).
- The posts counted per day are kept thirty-one days (eight before), for the monthly summary.

## 0.37.0
- **The statistics page in ZenithBoard's look**: the name in the wall's dots, numbers and bars in the wall's colour on black, grey for the rest; the sky by hour as lit dots. Asked for by the owner, with ZenithBoard's banners as the model.
- **A period toggle, 24 h · 7 days · 30 days**, top right: the four numbers, the three charts (by hour for 24 hours, by day otherwise), the airlines, models and altitudes follow it. The sky by hour stays at thirty days (fourteen before). The choice stays in the address (`#7d`) and for the next visit. `/api/stats?range=`.
- **The weekly posts' lists on the page**, for the period: cargo airlines with their most seen model, business jets and the countries they are registered in, military aircraft by country, general aviation; real flags, served from the Pi at `/flags/XX.png`.
- The fleet files gain the time last seen, so the last 24 hours count yesterday's aircraft from the same time on. Model names as the posts write them on the page too (*Boeing 737-800*). An hour or a day with no sample is a gap in the farthest line, never a zero.
- What it costs: each period worked out on demand and kept until a statistics file changes; previewed at desk and phone width on made-up statistics.

## 0.36.1
- **Real flags on the weekly cards**, at scale: 48 × 32 pictures made once from country-flag-icons (MIT), the set tar1090 ships, in `flightinfo/data/flags`. 0.36.0 drew the wall's dot flags, crude at that size (the owner). `tools/flag-pixels.js` is gone.
- **Fix: the country of an address in a nested block.** The ICAO table nests (Bermuda and the Isle of Man inside the United Kingdom's blocks, listed before its catch-all); 0.36.0's faster search gave the UK's military block, among others, to no country. Flattened once into intervals that do not overlap; checked against the table's first-match reading on 200 000 addresses. Found redrawing the cards.
- `/social/preview2` (3, 4) says why there is no picture (the post had nothing to say at the last test, or no test was run) instead of a bare *not found*, seen on the reference Pi; `weekly test` removes an older picture of a post that has none this time.
- A cargo airline the airline list does not name gets its cargo list name on `/stats` (TAY was shown bare: *ASL Airlines Belgium*).

## 0.36.0
- **Four weekly posts**, two minutes apart on Sunday evening. The second card has three columns: each cargo airline with the model it flew most (*DHL · Boeing 767-300 (18) … 39*), the business jets by make and model, and the countries the business jets are registered in, with the wall's own flags, a bar and the count. **Third: the military aircraft**, by country with its flag, the most represented first, then makes and models with bars. **Fourth: general aviation**, helicopters, light aircraft, gliders, drones and balloons, makes and models with their counts. Sketched and asked for by the owner.
- The country is the state an aircraft's ICAO address is allocated to (Annex 10, tar1090's table, `flightinfo/data/icao_countries.json`). Military: the decoder's or tar1090's database mark, an address in tar1090-db's military blocks (`flightinfo/data/military_ranges.json`), or a combat class. General aviation by the wall's class or the category the aircraft sends (A7, A1, B1, B2, B4, B6).
- **The statistics' fleet files gain two columns**, the emitter category and the military mark (from the decoder's `dbFlags` or the first flag of tar1090's entry); lines of 0.31.0 are read as before. `server.local_info` gives a type and the mark for many addresses at once.
- A post with nothing to say gives its turn to the next; after four hours of failures the rest are dropped rather than posted late. `social weekly test` shows all four (`/social/preview` to `/social/preview4`), `post3` and `post4` post those now. Never a distance, a direction, a registration or a callsign.

## 0.35.0
- **The weekly card names the models too**: the week by hour is smaller, and under it the airlines and the models most seen side by side. The text gains *Models: Airbus A320 (…), Boeing 737-800 (…), …*; its lines are shorter (*Busiest: Friday (612 aircraft) and 17:00.*), and when the hashtags would not fit the lists go down to two names, then one, before a line is dropped.
- **A second weekly post, two minutes after the first: the cargo airlines and the business jets.** Cargo airlines by their own callsign prefix, from a list of 40 dedicated cargo operators each checked against a published source (`flightinfo/data/cargo_airlines.json`; DHL's airlines counted together). Turkish, Qatar, Emirates and others fly cargo under their passenger prefix and cannot be counted. Business jets as the wall classes them, by make and model, never with a registration. A failure waits ten minutes, and after four hours the post is dropped; no second post without the first, nor when the lists do not cover the week, nor when there is nothing to say.
- `social weekly test` shows both posts (`/social/preview` and `/social/preview2`); `social weekly post2` posts the second now.
- Asked for by the owner. Previewed with the real code on made-up statistics; not yet on a Pi.

## 0.34.1
- **The weekly summary names the airlines and the type only when their lists cover the whole week.** The first `social weekly test` on the reference Pi said *6 435 aircraft heard* and *Most seen: Ryanair (14), British Airways (8), easyJet (8)*: the week's aircraft came from the statistics' day files, the airlines from lists begun two hours earlier with 0.31.0. Seen by the owner. Until the lists cover the week, the text leaves both out, the picture says from which week they are shown (the week ending 1 November on the reference Pi), and `weekly test` says it as well.
- The type is written as the posts write it: *Boeing 737-800*, not *BOEING 737-800*.
- `social weekly test` says plainly that nothing was posted, and gives the command that posts it now.

## 0.34.0
- **`zenithboard health` gives the card's size**: `Card: 6% full: 1.7 GB used of 31.2 GB, 28.1 GB free (the card: 31.9 GB)`, the system's partition from `df` and the card under it from `lsblk`. The memory line says free of how much. Asked for by the owner.
- **`zenithboard memory`** (or `threads`; menu *3 Settings → 5 Reliability → Memory*): memory, peak, threads, open files and processes for each service, the largest first, then the whole Pi (memory, swap, threads, load), what runs outside the services, and the six largest processes. Read from `/proc` per service cgroup, since systemd has no memory figure on Raspberry Pi OS (the kernel's memory controller is off). With sudo, memory is PSS, which adds up, and open files are counted. Asked for by the owner once the Pi fed four networks.
- Plane Finder feeds from the reference Pi (20 October 2026): the README, Hardware and Project status say so, with the memory still available (575 MB).

## 0.33.0
- **A summary of the week on Bluesky.** `sudo zenithboard social weekly on` (menu *Social sharing → 7*, off by default): on Sundays from 19:00 the service posts the seven days ending that day, from the statistics: aircraft heard, messages decoded, the busiest day and hour, the three airlines and the type most seen, and the crossings the account posted. The Pi draws its picture (Pillow, 1200 × 675, in the posts' colour): the counts, the week by hour as dots, the airlines as bars, their names in plain text.
- Never a distance, a direction or a range: the farthest aircraft of the week is left out, since with the city nearest it two such posts would place the antenna.
- Once a week: nothing is posted late on Monday. A failure waits ten minutes like a post; a week with no statistics is skipped and said once in the journal. `social weekly test` shows this week's so far, posting nothing; `social weekly post` posts it now. `social status` says whether it is on.
- The last part of the owner's choice when Grafana left (0.30.0). Previewed with the real code on made-up statistics; not yet on a Pi.

## 0.32.0
- **graphs1090, as an option.** `sudo zenithboard graphs on` (menu *3 Settings → 2 Receiver → 6*, off by default) installs [graphs1090](https://github.com/wiedehopf/graphs1090) with its author's own installer: years of the decoder's graphs (messages, range, signal, aircraft, CPU, temperature) on port 8542 and at `/graphs1090` on the map's port. It needs the receiver map's lighttpd and 64 MB free in `/run`, where its graphs live; they are written to the card once a day at 23:42 and at shutdown.
- **`graphs off` puts back what `on` found**: graphs1090's uninstaller, then what it leaves behind (two lighttpd files, its unit, its settings, its cron line), then the packages that were not there before, removed and never purged (Debian's purge of collectd-core deletes the history). apt is asked first; if something installed since needs one of them, they stay and `off` says so. The history stays on the card; `off` gives the command to delete it.
- `zenithboard graphs status`, a line in `zenithboard status`, port 8542 named by `zenithboard security`, a `graphs1090` component for `update`, and *Uninstall everything* takes it.
- The second half of the owner's choice when Grafana left (0.30.0). The installer was read in full, not run here: not yet tried on a Pi.
- The statistics question in the menu said 6 KB a day; it is about 30 KB since 0.31.0.

## 0.31.0
- **The statistics page shows what Grafana would have.** Four new charts on `/stats`: **the sky by hour** (fourteen days by twenty-four hours, darker where more aircraft were overhead), **the airlines** and **the aircraft types most seen** (the ten with the most distinct aircraft over thirty days), and **how high** they fly (bands of 1 km or 5 000 ft, following the wall's units). Ground vehicles and the airport's own transmitters are not counted.
- For them each sample now writes the day's aircraft with their callsign, altitude and type to `fleet-YYYY-MM-DD` (no position): about 30 KB a day on the card instead of 6, kept thirty days, emptied by `stats clear`. The types come from the decoder when it has an aircraft database, otherwise from tar1090's with `sudo zenithboard data localdb on`, looked up by the sample once per aircraft and day, never by the page (thirty days of addresses at once would take a Pi 3B minutes). The lists start on the first quarter hour after the update.
- Previewed against the real server with thirty days of made-up samples, light and dark, desktop and phone width. The choice of the owner when ACARS and Grafana left (0.30.0).

## 0.30.1
- A Pi still running ACARS keeps the ingester and acarsdec's launcher through an update: 0.30.0's update replaced `/opt/zenithboard` without them, and their services would have failed while the update said it removed nothing. They go with `sudo zenithboard acars remove`. Found re-reading the update path for regressions; no Pi was concerned (the reference Pi never had ACARS).

## 0.30.0
- **ACARS and Grafana leave ZenithBoard.** The owner's decision: they were never run on the reference Pi, needed about 900 MB more than a 1 GB board has, and what Grafana could show is better done by the wall's own statistics page. Gone: menu 3, `acarsdec`'s build, the ingester, both services, the Grafana install and its password handling, the `ACARS_*` defaults, `zenithboard acars password`, `zenithboard logs acars`, the `acars` update component.
- **The main menu is renumbered**: 1 ADSB, 2 FlightInfo, 3 Settings, 4 Status, 5 Update, 6 Maintenance, 0 Exit.
- **A Pi that installed them keeps them until its owner says otherwise.** `zenithboard status`, `sudo zenithboard update` and `zenithboard security` say what is left and give the command; `sudo zenithboard acars remove` stops and removes acarsdec, the ingester and its database, Grafana (package, apt source and key, password file) and the `ACARS_*` settings, after the typed word `remove`. *Uninstall everything* takes them too. The build tools acarsdec needed are left: other software may use them.

## 0.29.0
- **The words of a post, in five shapes.** `sudo zenithboard social sentence factual|story|board|spotter|lookup` (menu *Social sharing → 6*, a checklist with an example of each): `factual` is the post as before; `story` ("A Ryanair Boeing 737-800 bound for Pisa from Brussels has just crossed the sky above Trémery, 10 570 m up."), `board` (four short lines: callsign and registration, route, type, altitude and speed, place and time), `spotter` (the registration first) and `lookup` ("Look up, Trémery! Ryanair #RYR5ZK is passing 10.6 km overhead…"). Several, comma-separated, or `random`: one is drawn at each post. Templates filled from the flight's own data, as the account's description says; none gives the distance or the direction from the receiver. A shape that lacks what it needs (no airline nor type), or would be too long, gives the factual text.
- **The reason first**: `Rare visitor:`, `Heavy overhead:`, `Military traffic:`, `Helicopter:` before the words (the factual text already says military, helicopter and a range record). A range record always keeps the factual words: it is nowhere near overhead.
- Asked for by the owner, who chose all five and the openings.

## 0.28.0
- **The town names follow the track.** A map names the places within 70 pixels of the aircraft's track first (towns, then villages in the gaps), and three of the largest cities elsewhere on it (50 000 or more, spread apart) so the reader knows where the map is; the rest of the map only when the track's surroundings give fewer than three names. RYR5ZK (Brussels → Pisa) named Lier, Geel, Hasselt, Maastricht and a dozen more in the north of its map, far from a track running from Namur to Luxembourg; the same map now names Namur, Ciney, Rochefort, Bastogne, Arlon, Luxembourg, Esch, Hayange and Metz along the line, and Leuven, Aachen and Trier around it. Previewed on four real posts (RYR5ZK, RYR6JR, SKV615, EJU86EN) with the real code, the region's list and EOX's tiles. Asked for by the owner.

## 0.27.3
- **The empty parts of a map get a village.** After the towns, a map names the heaviest village wherever no name is within 120 pixels of it, up to the 26 names it holds at most. SWR3AG (Swiss, Zurich → Luxembourg) went out over the Moselle plateau with seven towns, all on the edges, and nothing in the 30 km between them; previewed with the real code, the region's list and EOX's tiles, the same map now names Boulay-Moselle, Bouzonville, Rémilly, Verny, Morhange, Château-Salins and Dieuze in that space. Raising the three-names threshold was tried first and changed nothing there (the map had seven). Both kinds of list, shipped and the region's own.

## 0.27.2
- `social places on` downloads only the countries with a place of 500 or more within 400 km, measured place by place (GeoNames' cities500, rounded to a tenth of a degree, `flightinfo/data/country-cells.json.gz`, 300 KB). It went by one-degree cells with an 80 km margin, and the reference Pi downloaded the Czech and British files (5.2 MB) for no place within reach: the nearest British place of 500, Deal, is 408 km away. Around Metz: nine files, 24 MB.

## 0.27.1
- The region's list of places (`social places on`) is readable by its owner only, the service (0600, was 0644): its first lines give the centre of the area, the receiver's position. Found by CodeQL on 0.27.0.

## 0.27.0
- **Town names anywhere in the world: the region's own list.** `sudo zenithboard social places on` (menu *Social sharing → 5*, off by default) downloads GeoNames' files of the countries within 400 km once (about 30 MB around Metz), keeps every populated place within 400 km, weighted by its population or, where GeoNames knows none, by its rank (capital, province, district, subdistrict, village seat, village), and names the maps from it. GeoNames knows the population of 540 of Indonesia's 258 055 populated places, so the shipped lists left maps over Sumba, Borneo or Mongolia bare: on test maps, East Sumba 0 → 11 names, Pontianak 0 → 19, Ulaanbaatar 3 → 12, Lima 8 → 24, Trémery 8 → 9; Innsbruck's 2-minute map 11 → 4 (the shipped list counted its districts). `on` again remakes it; `off` deletes it. Asked for by the owner.
- **The maps go down the tiers by weight**, the same for both kinds of list: 5 000 and more, then 1 000, then any place, until three are named.
- A town's name goes left of its dot when the right is taken; a place is never named twice.

## 0.26.2
- **Villages on a map short of towns.** A map that names fewer than three towns of 5 000 inhabitants or more names the villages of 1 000 to 4 999 too, the largest first, under the same rules. From a real post: DAH1217, two minutes after leaving Metz-Nancy, went out on a strip east of the Moselle with no name at all; every town of 5 000 there is in the valley, just beyond the map's edge. The new list (`flightinfo/data/places1000.tsv.gz`, GeoNames, CC BY 4.0, made by `tools/make_places.py --small`, 68 000 places, 950 KB) is read only for such a map, never kept in memory. Asked for by the owner.

## 0.26.1
- **No town named twice on the posts' maps.** The light (`normal`) and dark (`night`) maps were EOX's OpenStreetMap layer, which writes its own town names: since 0.25.3 ZenithBoard's names went over them, a few pixels apart (EWG8QR over Nancy, on a real post). EOX has no OpenStreetMap layer without names, so these two maps are now built from two EOX layers that carry none: the light relief and the main roads (orange on the light map, white on the dark one), under ZenithBoard's names. The main roads only, not OpenStreetMap's small ones. Credits unchanged: OpenStreetMap, EOX, GeoNames. Approved by the owner on a preview.

## 0.26.0
- **Registrations and models from the receiver map's database, offline.** `sudo zenithboard data localdb on` (menu *Settings → Wall → 9*): the wall reads tar1090's aircraft database, which tar1090's installer keeps on the card and updates itself, before asking adsbdb and hexdb. From a real post: EWG8QR, 9H-EWG (4D2087), went out with no registration and no model; adsbdb and hexdb did not know it, tar1090's database did. Nothing is downloaded, nothing leaves the Pi; at most four of its files in memory (about 25 MB). Off by default; `zenithboard data status` and `zenithboard status` say whether it is on and which version tar1090 has.

## 0.25.4
- An airport's name that opens on the town next to it now gives that town alone: *Amsterdam Airport Schiphol* → *Amsterdam* (a real post read *Amsterdam Schiphol → Cape Town*). A name whose other words belong to the town's own name stays whole (*Palma de Mallorca*, *Paris Charles de Gaulle*), as does one whose first word is a city far from the airport (*London Stansted*, *Milan-Malpensa*).

## 0.25.3
From a recording of the posts made since 0.25.2.
- **The town names are drawn over the track**, not under it: the track cut letters out of the towns it crossed (*N ncy*). Each town's dot stays where the town is; nothing moves.
- **The OpenStreetMap maps (`normal`, `night`) name the towns too**, as the terrain and satellite maps do since 0.24.4: OSM's own labels, drawn for a screen, were an unreadable grey once the map was reduced to the post's size. The credit names GeoNames on those two maps as well. OSM's own labels stay under ours (EOX has no OpenStreetMap layer without them).
- **A town, not an airport's name, when the route comes from hexdb.** hexdb's second opinion gives each airport a name and no town, so a post read *Brussels South Charleroi Airport → Turin Airport (Caselle Airport)*. The town is now taken from the name: what is in brackets and the words *Airport*, *International* and the like go, and a name that opens on a city far from the airport (*Brussels*, 45 km) gives way to the town by it (*Charleroi*): *Charleroi → Turin*.
- The small words in a town's name are written as the town writes them: *Palma de Mallorca*, *Frankfurt am Main* (adsbdb wrote *Palma De Mallorca*).

## 0.25.2
- The town names on the posts' satellite and terrain maps are smaller (13 points, from 16) and more of them are shown (up to 26, from 16), still the largest first and never one over another. Asked for by the owner after the first post with them.

## 0.25.1
From a real post: TF-AKE, an Air Atlanta Icelandic cargo 747 (4CC54B), went out with blank registration and model rows.
- **hexdb.io's second opinion on the aircraft.** When adsbdb answers *unknown aircraft*, the wall asks hexdb, as it already does for a route adsbdb gets wrong: the registration and the model, once per airframe, remembered like adsbdb's answers. adsbdb answered *unknown aircraft* for TF-AKE; hexdb knew it.
- **No blank rows on the posts' pictures.** A row nobody could fill leaves no gap: the rows below move up, the flags with their row, the time stays at the foot (dot-matrix and split-flap). The wall itself is unchanged.

## 0.25.0
- **A link to the aircraft's photo in the posts, optional.** `sudo zenithboard social photolink on` (and menu *Social sharing → 4*): when the wall has a Planespotters photo of the aircraft, the post ends with *Photo: NAME / Planespotters*, a link to the photo's page with the photographer named. The link only: the picture is never posted and no link card is made, as Planespotters' photo API terms require. No line without a photo; left out rather than cutting the text when the post is full. JetPhotos is not used (no API; querying its site is not granted). Off by default. Asked for by the owner.

## 0.24.5
From Planespotters' photo API terms, read on 19 October 2026 at the owner's request.
- **The tablet loads the photos straight from Planespotters.** The terms ask that a picture be fetched from the address the API gives, by the screen that shows it, and never stored, proxied or passed on. Until now the Pi fetched each picture and served it to the tablet from a memory cache of 200 (`/api/photo/…`): that route and the cache are gone. The tablet needs internet to show photos; without it, the animated sky is shown as before.
- The API's answer is remembered 24 hours at most, as the terms allow; it was kept until the wall restarted.
- `zenithboard photos test` checks the API only and no longer downloads a picture to the Pi.
- The credit next to the photo and the photo as a link to its page were already as the terms ask. The photos are still never posted to Bluesky. JetPhotos is not used: it has no public photo API, and its terms grant personal, non-commercial use of the site only.

## 0.24.4
- **The towns are named on every map.** The satellite and terrain maps relied on EOX's label layer, which named one village in forty kilometres on a real post over Metz. They now carry the names ZenithBoard draws itself: the places of 5 000 inhabitants or more (GeoNames, CC BY 4.0, shipped with ZenithBoard, nothing looked up), the largest first, never over another name, the aircraft, north or the key. The credit names GeoNames; the satellite map's credit no longer names OpenStreetMap, whose labels it no longer carries. The OpenStreetMap maps already name their towns.
- Checked at the owner's question: the scale bar and the track agree with the real distances and speeds. A Transavia at 997 km/h over three minutes flies 50 km; its track measured 48 km against the 10 km bar on the post; Metz to Thionville (28 km) measures 27 km on a preview.

## 0.24.3
- **The posts can have their own units.** `sudo zenithboard social units imperial` (or `metric`, or `wall`, the default: the wall's own `UNITS`, as before), and a question in the picture wizard (menu *Social sharing → Picture*): the altitude, speed and scale on the picture and the altitude in the text, in ft, knots and miles, whatever the wall shows. Asked for by the owner.

## 0.24.2
- Code scanning (CodeQL) findings put right: `social status | head` no longer leaves a file handle open when the reader leaves; an unused distance function went from the dot renderer; an empty `except` says why; a test imported the map module twice.

## 0.24.1
- **A thinner track on the posts' maps** (dotmap and flap): 3 pixels with a 6-pixel dark edge, from 5 and 11, which the owner found far too thick on the real posts. The aircraft keeps its size.
- The README and the wiki show a real `dotmap` post from the reference Pi in place of the preview drawn without tiles.

## 0.24.0
From the owner's first afternoon on 0.23.0.
- **The posts always carry a map.** The dots-only look (the dot-matrix wall with the track drawn in dots, no map) is taken out of the choices, at the owner's word: `social look`, the picture wizard and the menu offer `dotmap`, `flap` and `alternate`. `dotmap` is the default. A Pi still set to `dots` is not changed: it posts `dotmap`, and `sudo zenithboard update` says so with the command. `social map none` with `dotmap` now draws the dot wall with the track on black, like `flap` does, instead of the dots-only picture. Pillow is installed for every look. A Pi without it (offline) still gets the dot picture rather than none.
- **The farthest aircraft of the day is named even when its callsign came late.** At the edge of range the decoder often has an aircraft's positions before its callsign, so the record was kept with no flight, airline or route (*18/10 13:09 · TF-ICE · BOEING 737 MAX 8 · 322 km*, on the real page). The wall now remembers the callsigns heard in the last hour and fills it in, before or after the farthest position; the route is then looked up at the next sample. The record already written for 18 October stays as it is: the aircraft is long gone.

## 0.23.0
From a Bluesky post (Eurowings EWG11S, D-AIDO).
- **A new look for the posts: the dot-matrix wall beside a real map.** `sudo zenithboard social look dotmap`: the wall's dots on the left, and in the right-hand column, instead of the track drawn in dots, the map the split-flap picture already carries (OpenStreetMap, darkened, satellite or terrain, from EOX, credited in the post and on the picture) with the track and the aircraft. The map turns like the split-flap one (`social map rotate`), and the colours too. Node draws the dots with that column left dark and says where it is; Pillow lays the map there and writes a JPEG under Bluesky's limit.
- **`alternate` is now the two looks with a map**, `dotmap` then `flap`, as asked; the track drawn in dots left the turn. It stays a look of its own, `social look dots`, which fetches no map. Alternating with the maps turning, each look meets each of the four maps over eight posts and each colour over ten.
- **The flags show whole in the dot-matrix picture.** Its right-hand panel started at dot 86, and its frame was drawn over the last column of an outlined flag (the German flag beside D-AIDO lost its right edge). It starts at 88 now, two dots clear: a dark column, then the panel. Its legend (`100KM`) and its "no track" words fit inside the narrower frame. The wall itself was never affected: its right-hand column starts at 90.
- **The dark blue is gone**, from the wall (dot matrix and split-flap), the tablet's gear, `zenithboard color`, the menu, the presets and the posts; turquoise stays. A setting the owner made is not changed by an update: a wall, a preset or a picture colour still set to blue shows the Pi's colour, or amber, and `sudo zenithboard update` names each one with the command to choose another. A tablet that remembered blue, or opens `?theme=blue`, falls back the same way rather than to unstyled dots.
- **The aircraft is never under the legend.** On the dotmap's narrow map a track flown north to south ended under the legend box; when the aircraft would land under it, the view is now chosen in the part of the map above the legend and the credit (on the split-flap map too, where that is rarer).
- The messages that name the wall's colour say the one the posts and the wall show: amber while the setting still says blue, not "blue". The update's notice for a preset set to blue gives the whole command, its other settings included (`preset add` replaces a preset).
- `sudo zenithboard social test` with `alternate` now says when the map tiles could not be fetched, like it does for one look. A Pi without Pillow, set to a map look, is told to run `social test` (which installs it and keeps the look) instead of a `social look` that would have replaced `alternate`.

## 0.22.0
- **The statistics page names the farthest aircraft.** Under the four numbers, two lines: the farthest aircraft of the day and of the thirty days, with the date and time, the airline and flight number, where it flew from and to, the model and registration, the altitude, the distance, and the city of 100 000 inhabitants or more nearest to it: `14/10 21:07 · easyJet U21234 (EZY1234) · Edinburgh (EDI) → Saint-Louis (BSL) · AIRBUS A-319 G-EZAB · 10 970 m · 329 km, 55 km from Lille, FR`. Asked for from the real page, where *355 km* stood alone.
- The decoder only says how far, never which aircraft. With statistics on, the wall server now looks at `aircraft.json` every five seconds (about a millisecond each time on a laptop, a few on a Pi) and keeps the farthest aircraft of today and yesterday in memory; the 15-minute sample asks for it on the loopback and writes it to `farthest-DAY`, kept thirty days. The route is the wall's own lookup with the wall's own check, so with routes off nothing more leaves the Pi; with routes on, the day's farthest callsign is looked up too (the README's privacy line says so).
- The cities come from a list shipped with ZenithBoard: GeoNames, Creative Commons Attribution 4.0, credited on the page, 4 578 cities, made by `tools/make_cities.py`. City districts are left out, and two British entries that carry a district's population (St Peter's in Kent, Mendip), found when the preview named a point over the Channel *near Saint Peters*. Nothing is asked of the internet for a city. Neither the aircraft's position nor the antenna's is written or shown.
- Days from before this version have their number in the box and no line; the page says so for the thirty-day best.
- The statistics unit may run 120 s instead of 60: the sample can wait a few seconds for a route on its way.

## 0.21.1
The fresh-install check from the roadmap, done as far as it can be without a Pi: `install.sh` walked end to end from the README, in a container, against a scripted whiptail and stand-ins for the system (every flag, the first-run wizard, every menu, the deployed wall answering on its port, the uninstall). What it found, fixed, and now held by `tests/test_install.sh`:
- **A missing whiptail no longer ends in silence.** When `apt` could not install whiptail and curl (no internet, say), every screen failed and the installer quietly exited with nothing said. It now stops with the command to run by hand.
- **The Wi-Fi line read `ON, ` on a Pi on Ethernet.** `nmcli` prints nothing at all when no network is active, so the text meant to say *not connected* never appeared, in the Settings menu, the Wi-Fi menu and `zenithboard status`. Fixed, with a test.
- **The wall's colour in the menu offers all six colours.** Menu *4 Settings → 3 Wall → Colour* still listed amber, green, red and white; turquoise and blue (0.13.1) could only be set from the command or the tablet's gear.
- **A typo in the altitude is asked again** instead of being written as 0 without a word, like a bad latitude already was.
- The welcome screen pointed at `sudo zenithboard config` to change the answers later; that command only shows them. It now names menu *4 Settings* and the commands.
- A decoder that fails to install says that the feeders were not installed either, and a failed download says what it usually means (no internet, or a moved address).
- On a machine that is not a Raspberry Pi the installer no longer prints `No such file or directory` twice for the model file.
- README: *4 Settings* has six groups, not four (Logs, Reliability and Social sharing were missing from the list), and step 6 says where the wall's address comes from (menu 2 prints it, `zenithboard status` repeats it).
- *Maintenance → Save my settings* proposes a folder that exists when there is no sudo user (root's), not `/home/pi`.
- For the test, `ZENITHBOARD_HOME` and `ZENITHBOARD_BIN_DIR` redirect `/opt/zenithboard` and the `zenithboard` link, like `ZENITHBOARD_ETC` does for the settings. Nothing changes on a Pi.

## 0.21.0
From a walk through every menu on the reference Pi, recorded.
- **The menu keeps the one irreversible step out of the way.** *7 Uninstall everything* is now inside *7 Maintenance*, after *Save my settings* and *Restore settings*, and it asks for the word `uninstall` to be typed, not a Yes: one Enter too many at the end of the list must not take a working receiver down. Removing the wall and deleting every log ask for a typed word too.
- **Settings as a file.** `zenithboard settings export` writes `config.env` without anything that looks like a secret (the Bluesky app password, feeder keys and passwords stay in their own root-only files); `sudo zenithboard settings import FILE` puts a file back, skipping anything that is not a setting, and keeps the file from before as `config.env.bak-DATE` so an import is one command from undone. Menu *7 Maintenance*.
- **A quick update.** `sudo zenithboard update quick`, and the first entry of menu *6 Update*: ZenithBoard and the wall only, in seconds; the feeders are left alone rather than asked of `apt` one by one, which took a minute or two for a change to the wall alone.
- **Per-tablet presets.** `sudo zenithboard preset add kitchen theme=green mode=flap radius=5`, then that tablet opens `http://PI:8080/?p=kitchen` and takes those choices at every load, instead of a long address of `?theme=…&mode=…`. Menu *4 Settings → 3 Wall → 8 Presets*. Kept in `config.env` as `PRESET_KITCHEN`, so they travel with an export.
- **Wi-Fi hardening, off by default.** `sudo zenithboard wifi harden on` sets two things on the saved Wi-Fi profile: keep trying to rejoin after a loss without end (NetworkManager gives up after four tries), and the radio's power saving off, a known cause of short losses on a Pi. `off` puts back exactly what was there. Menu *4 Settings → 1 Network → 1 Wi-Fi → Hardening*.
- **Counting what the wall cannot name or draw.** With statistics on, every sample also notes each aircraft shown with a callsign but no airline name (by its three-letter prefix) and each one drawn with the generic silhouette (by type code), once per aircraft, thirty days. `zenithboard stats gaps` prints the counts: the figures the roadmap's airline lookup and new silhouettes will be chosen on, rather than guesses. The statistics unit may now reach the wall on the loopback, and nothing else.
- The ACARS tag in the main menu no longer runs off the screen; `status` no longer calls a 1 GB Pi a board to skip ACARS on without saying why (it is the measured board: everything but ACARS and Grafana).
- Roadmap: an offline route source is *not planned* (no free, complete, current database of routes by callsign exists; a stale route shown with confidence is worse than none).

## 0.20.1
- **The hardware advice is measured now, not estimated.** The reference Pi 3B (1 GB) runs readsb, ADS-B Exchange with MLAT, FlightAware, Flightradar24, the wall and social sharing with 656 MB of its 1 GB still available, at 36 °C, without throttling. The README's table starts from those figures, *What you need* says a Pi 3B or newer (2 GB or more only for ACARS + Grafana), and a new wiki page, [Hardware](https://github.com/regis57/ZenithBoard/wiki/Hardware), says why a bigger Pi brings nothing you would see for ADS-B, and what moving the SD card to one would change (power supply, possibly the address, heat) and keep (the system, the settings, the feeders' identities), with the way back.
- The installer's notice on a 1 GB Pi 3 says what was measured on one, instead of advising at most one or two extra feeders; a board under 700 MB is told: ADS-B and the wall, no extra feeders.

## 0.20.0
- **Social sharing posts every crossing, once.** A crossing starts when an aircraft comes inside the sharing radius and ends when it has been outside it for an hour: whatever it does in between — circling, or leaving and coming back five minutes later — it is one post. The same airframe back after that is posted again (the return flight, the next day), and so is a new callsign sooner (turned round at a nearby airport). Until now an aircraft was remembered for a day after it was last seen anywhere by the receiver, so the evening's return flight was never posted, and the memory followed every aircraft the receiver heard, not the radius.
- **Nothing caps the posts.** The gap between two posts is now none by default (`SOCIAL_GAP_MIN=0`), and the ten-minute floor of 0.19.3 is gone: the feed is what crosses your radius. A gap can still be set, to any whole number of minutes, with the new `sudo zenithboard social gap MINUTES` (or in `social words`); a gap already in your `config.env` is kept, and the update says so. After a post the service looks again five seconds later rather than fifteen, in case another aircraft is waiting.
- **An aircraft that left the radius before its turn is still posted**, up to ten minutes after it left: its route still being looked up (the wait is up to two minutes, and a jet crosses 20 km in about one and a half), or another posted first. Among equals, the one that came in first goes first.
- **The Bluesky session is reused.** 0.19 signed in for every post; Bluesky allows an account 300 sign-ins a day and 30 in five minutes, which every crossing on a busy day could pass. The session is kept in memory (never written anywhere), renewed with its refresh token after an hour, and signed in afresh only when Bluesky refuses it — once, never in a loop. `social check` still signs in afresh.
- `social status` says how many posts went out in the last day (not how many aircraft were remembered) and how many crossings are remembered, so *why was that one not posted?* has an answer. State from 0.19 is read as it is.
- **The registration's flag sits beside the `REG` row**, on the wall and in the dot-matrix posts. Beside the airline row, where it was, it read as the airline's country. The airline row keeps its twelve letters: the flag's outline, when it has one, is on the dark row just above it.
- Without flags, the airline and model rows stop before the right-hand column and turn there; they ran on to the wall's edge, so a long airline name went under the silhouette.

## 0.19.10
- **The memory figure for Node is Node's own.** The service's hourly line read *104 MB at most, Node 104 MB at most*: Python starts Node with vfork, and the kernel then credits the child with the parent's peak, so both numbers were Python's. The renderer now reports its own peak (`process.resourceUsage().maxRSS`) and the service keeps the largest. Seen on the real Pi after four hours of posting.

## 0.19.9
- **A post waits for the second opinion on the route too.** RYR8526 and EWG6ZP went out with empty route rows. adsbdb had other flights under those callsigns (Berlin → Stansted, Salzburg → Aalborg), which the wall rightly refuses for an aircraft over Metz flying south-east or north; it then asks hexdb.io, which had the right ones (Charleroi → Reggio Calabria, Menorca → Cologne) — a few seconds after the post. `/api/planes` now reports that second lookup as pending as well, and social sharing waits for it like for the first (two minutes at most). Checked against both services' real answers for these two callsigns.

## 0.19.8
- **An altitude no longer breaks across two lines** in a post: *altitude 8* at the end of one line and *600 m* on the next, seen on a phone. The thousands and the unit are joined by no-break spaces (`8 600 m`, `37 000 ft`, `over 300 km out`).

## 0.19.7
- **The hashtags have a command:** `sudo zenithboard social hashtags ADSB avgeek Moselle`, and a question in `social words`. The `#` is optional — typed unquoted, the shell would take `#ADSB` for the start of a comment and pass nothing. `none` for no hashtags at all (not even `#helicopter`), `default` for the three; alone, it shows them. Eight at most, letters, digits and `_`, at least one letter. Until now the only way was to edit `config.env`.
- `zenithboard social status | head` no longer ends with a Python error when the reader leaves early.

## 0.19.6
- **The map credit in a post is one short line, at the end:** *Map © OpenStreetMap, EOX* (satellite: *Map: EOxCloudless by EOX, © OpenStreetMap*), each name a link — to OpenStreetMap's copyright page, to EOX. It was three lines of small print between the text and the hashtags. The whole required text is still drawn on the picture and read in the alt text; OpenStreetMap's attribution guideline accepts the name linked to its copyright page, and EOX asks an online publication for its name and a link. Asked for after the first satellite post.

## 0.19.5
- **A post waits for the aircraft's details.** KLM24V went out with empty registration, model and route rows: the wall asks adsbdb about an aircraft when it comes inside the radius it is asked about, and the service, whose track had followed it from far out, posted it the same second. `/api/planes` now says which lookups are still on their way (`pending`), and the service waits for them, up to two minutes from the first time it saw them pending, then posts with what is known. `social test` waits inside its half minute.
- **Optional: posts that vary.** `social look alternate` (dot-matrix and split-flap, one post each), `social colour rotate` (amber, green, red, white, turquoise in turn; the wall's dark blue is left out of the turn, it reads poorly on a phone), `social map rotate` (the four maps in turn, at each split-flap post). Over ten posts each look meets each colour. `social status` names the next picture; posts made by hand move the turn on. Off by default; the wizard offers each.

## 0.19.4
- **The social service reports its own memory**: in its hourly journal line and in `sudo zenithboard social status` (now, at most, and the largest drawing by Node). 0.19.3 said `systemctl status` would show it: it does not on Raspberry Pi OS, which boots with the kernel's memory controller off (`cgroup_disable=memory`), and for the same reason the unit's `MemoryMax=300M` only applies where that controller is on. Seen on the real Pi right after the 0.19.3 update; ZenithBoard does not change the boot command line for it.

## 0.19.3
From the real Pi's log.
- **An update restarts the social service.** It only made sure it was enabled, and a running service keeps the code it started with: the Pi ran 0.19.0 for hours after installing 0.19.2. The service's first journal line now says which version it runs, and `social status` says when it runs code older than what is installed.
- **`social status` tells the truth when it cannot read.** Run as `pi`, it said *no account* and *Last post: never* on a Pi that had just posted: `pi` cannot read the account file or the state folder. It now says it cannot, and how to see everything (`sudo zenithboard social status`, which reads them as the service's user).
- **Ten minutes at least between two posts**, whatever is set (removed in 0.20.0: the owner wants every crossing posted). The gap had been set to one minute for a test; with *ALL*, that is a post a minute, which is what gets a bot account reported. A smaller value is used as ten and the status says so; the wizard says it too.
- **The service's memory is counted and capped** (`MemoryMax=300M`): a split-flap picture with its map peaks near 140 MB; `systemctl status zenithboard-social` now shows the figure.
- **Route rows: the city when it fits**, the way a departure board reads — `→SAN JOSE`, not the airport's `→JUAN SANTAMAR` — then the airport's name, then the city cut at a word, never on a dangling word (`FRANKFURT`, not `FRANKFURT AM`). On the tablet and in the posts.
- The 0.19.2 entry said a post had broken the two-hour gap; it had not, the gap was one minute. The fault 0.19.2 fixed was real, found while looking.

## 0.19.2
- **A post made by hand now counts for the running service.** *Post now* (`social post`) writes its post to the state file, but the service kept its own copy in memory and wrote it back every fifteen seconds, so the manual post was forgotten at once: the gap restarted from the service's own last post, and the aircraft posted by hand could be posted a second time. Found by reading the code after a post that looked too early (it was not: the gap had been set to one minute for a test, see 0.19.3). The service now reads the file before each decision and keeps the latest post and every posted aircraft from both; `social post` merges in turn instead of overwriting.

## 0.19.1
- **The rules list: the special aircraft, then ALL.** *ALL* means everything that flies over, the special ones included — ticking it alone is ticking every line, and a military aircraft under ALL is posted as military, ahead of an airliner. It was *any*, the last of six lines that read like a sixth kind of aircraft, and under *any* alone a tanker counted as "anything". The old word still works in `config.env`. The list says which rules wait for three days of history.

## 0.19.0
Social sharing, after the first real posts were read on a phone.
- **Bluesky only.** Mastodon is taken out: the wizard, the menu, the commands and the service know one network. An update removes a Mastodon token left on the Pi and the list of networks from `config.env`, and keeps the Bluesky account; revoke the token on your instance too.
- **The altitude can no longer be read as a distance:** `… · Paris → Abu Dhabi · altitude 8 500 m · above Trémery` (it read *8 500 m above Trémery*, taken for 8.5 km from Trémery).
- **The wall's two top rows, on the tablet and in the posts alike:** the flight and the registration on one row each, labelled like the altitude and the speed (`FLT  ETD11K`, `REG  A6-APD`), where the callsign alone stood two rows high. On the dot-matrix wall, on the split-flap board (nine rows now) and on both pictures. The track's legend is a key — a piece of the trail then `10MIN`, the scale bar then `100KM` — instead of two words that had to be guessed. The trail takes the picture's colour, which was always amber.
- **The picture's colour is a setting:** `sudo zenithboard social colour green` (or `wall`, the default: the wall's own colour). The six colours are read from the wall's `style.css`, so the picture matches the tablet exactly; green and white were slightly off before.
- **A second look: the split-flap board beside a map.** `sudo zenithboard social look flap`. The board has the same rows as the dot-matrix picture, without the flags, fourteen letters wide; the map is centred on the track, with the aircraft, a key (`LAST 10 MIN`, a scale bar), north, and the credit. Five maps: `normal` (OpenStreetMap), `night` (the same, darkened), `satellite` (Sentinel-2 cloudless 2025, non-commercial use), `terrain`, `none` — `sudo zenithboard social map satellite`. Drawn by Pillow on the Pi in a second or two, a Pi 3B included; no browser, so the Pi 4 limit the roadmap planned is gone.
- **The map comes from EOX's tile service**, whose layers are free to use with attribution and a link back: both are on the picture and in the post (a clickable link). OpenStreetMap's own tile servers are not used: their policy rules out automated fetching nobody is looking at. Tiles are cached for a month under the service's state folder (60 MB at most), asked for with ZenithBoard's name, checked to be images, capped in size; when none come, the picture has no map and no credit, and `social test` says so.
- `social picture` asks the three picture questions; `social setup` asks for the account, the words and the picture. The menu has a *Picture* entry. `social test` keeps `preview.png` or `preview.jpg`, and `/social/preview` shows the newer one.
- The rule list in the wizard says what `farthest` has meant since 0.18.2: a 30-day range record.
- **One post per aircraft while it is in the sky.** An aircraft once posted is not posted again as long as the receiver still sees it, nor for a day after; it was a day from the post, which a slow aircraft or a restart could in theory outlast.
- **A failed post waits ten minutes before the next try.** It was tried again at the next look, fifteen seconds later, and every try signs in to Bluesky: a revoked app password or a Bluesky outage meant a sign-in every fifteen seconds, which Bluesky's limits do not allow for long.

## 0.18.3
Asked for after reading the first real post on a phone.
- **The post starts with the flight and ends with the place:** `Flight Etihad #ETD11K · Airbus A380-800 · Paris → Abu Dhabi · 8 500 m above Trémery`. No icon in front; an airline callsign is a hashtag, so the flight can be followed; a callsign that is only the registration reads `Aircraft D-EABC`, a helicopter `Helicopter …`, a military flight `Military flight …`. A town name reads *above Trémery* (it read *over* in 0.18.2); a phrase of your own (`near Metz`) is kept. A range record ends with *seen from Trémery*, since it was nowhere near overhead.
- **The picture:** the callsign at the size of the other rows, with the registration on the row under it; the last row has the time with its offset from GMT as the Pi's time zone has it that day — `11:39 GMT+2` in a French summer, `GMT+1` in winter, `GMT+5:30` where that applies. The alt text names the registration too.
- **The track always fits its frame.** A `10KM` legend pushed the scale bar out of the frame, and an A380's ten minutes (165 km) ran past the edge. The bar is shorter, sits against the right edge, and stands for 1 to 500 km, the smallest that keeps the whole track inside.
- The tablet's wall is unchanged: these are the posted picture's rows only.

## 0.18.2
Social sharing could hardly ever post: two of its five default rules could not fire in the service, though `social test` said they would.
- **`rare` counted looks, not aircraft.** The service asked the wall every fifteen seconds and counted the type each time; by the time an aircraft had thirty seconds of track it had been counted three times, so no type was ever "seen twice or less". It now keeps, per type, the last few distinct aircraft and the day; rare means at most two *other* aircraft of that type in thirty days. The 0.18.0 history is dropped, not converted.
- **`farthest` compared an aircraft with the record it had just set**, and only looked inside the sharing radius (15 km by default) for something over 50 km. It is now a thirty-day range record, looked for in the whole sky from `aircraft.json`, and the wall is asked about that one aircraft alone (`/api/planes?hex=`, so nothing in between sets off a lookup). The post says the distance rounded down to 50 km — *over 300 km out* — not the figure.
- `rare` and `farthest` wait for three days of history; `social status` says where it stands. The other rules work at once.
- **`social test` says whether the service would post** what it shows, and why not — it adds `any` for itself and so always shows something, which was the source of the confusion.
- The service writes one line an hour to its journal (looks, candidates, last post, next possible), and says at start what it will do.
- A bare place name reads *over Trémery*, not *1 750 m Trémery*; *De Havilland*, not *DE Havilland*. Both seen on the first real test.

## 0.18.1
- **`zenithboard social test` and `social post` no longer crash from the command line.** They draw the picture in `/run/zenithboard/social`, which systemd creates for the service only; run by hand as the `zenithboard` user, the folder did not exist and Python stopped with *Permission denied* (seen on the first real try). The folder is now made for the command line too, and when it still cannot be written, a private temporary folder stands in and is removed after the post. Tested as a user with no rights on a box without the folder.

## 0.18.0
- **Social sharing, off by default: the aircraft worth a post, on Bluesky and Mastodon, as a picture of the wall.** `sudo zenithboard social setup` asks for a Bluesky app password or a Mastodon access token (never a real password), tries the accounts, then asks for the words: the place named in the posts, the sharing radius, the minimum gap between posts, and what is worth a post — a rare type, military, a helicopter, a heavy, the farthest of the day, or anything. `social test` draws the picture and prints the text without posting; `social on` starts the service. Menu: *4 Settings → 6 Social sharing*.
- **The picture is the dot-matrix wall with the aircraft's track** over the last minutes in the right-hand column, drawn by the Pi itself from the wall's own code — no browser, no photo, under a second on a Pi 3B. Node is installed from Debian for it when sharing is switched on; nothing else is added.
- **Nothing that gives the receiver away leaves the Pi:** no distance, no bearing, the time where the tablet shows them, the track centred on the aircraft with no map. The Planespotters photo is not posted (their terms). Secrets live in `/etc/zenithboard/social.env`, root-owned, mode 0640, read by the service only; `zenithboard security` checks it. The picture is drawn in memory and deleted after each post.
- The service runs as the `zenithboard` user in the wall's sandbox (1.3), and `zenithboard update` carries it. Wiki: [Social sharing](https://github.com/regis57/ZenithBoard/wiki/Social-sharing).

## 0.17.4
- **The gear panel offers the statistics page, while there is one.** Beside the version, in the same grey: `ZenithBoard 0.17.4 · Statistics`. It appears only when `STATS=1` and goes as soon as statistics are switched off, because a link to a feature nobody turned on leads to a page that says "off" — a dead end dressed as a door. `/api/config` carries the setting; the wall reloads by itself within seconds of `zenithboard stats on` or `off`, so the link follows without touching the tablet.

## 0.17.3
- **An update now checks that the wall really came back on the new version**, instead of assuming it. The wall is a running Python process: new files on disk change nothing until it is restarted, and an update that did not pass through the FlightInfo step left it answering the old version — the menu said 0.17.2 while the gear panel still said 0.17.1 (seen on a real Pi after `update only zenithboard`). The end of every update now asks the wall, on the loopback, which version it is running, restarts it when that is not the version just installed, and says so. A wall that still will not come up is reported with the command to run, never hidden.

## 0.17.2
- **Both pages say which version they are running**, in one grey line: at the foot of the gear panel on the wall, and at the foot of the statistics page. The name is a link to that version's own release notes on GitHub (`releases/tag/v0.17.2`), so "what changed?" is one tap away from the tablet. Nothing is asked of GitHub to draw the line: it is a link, followed only if somebody taps it, so a wall with no way out to the internet still names its version. `/api/stats` carries the version the way `/api/config` already did, whether statistics are on or off.

## 0.17.1
Two things seen on the real wall.
- **The British flag was there and could not be seen.** Two thirds of the union flag is `#012169`, a navy that at eleven dots on an unlit wall reads as a hole — so a British Airways aircraft looked as though it had no flag at all. A flag that would be invisible against the black wall now gets the same one-dot white outline as a flag carrying black. Its colours are untouched: a navy brightened into another blue is no longer that flag. The United Kingdom is the only one the rule newly catches, and a test holds the list.
- **The model row keeps the maker only while the whole thing fits.** An Etihad A380 arrived as `AIRBUS A-380-800`, sixteen characters, and walked past the twelve the flags leave instead of standing still as `A-380-800`. Every neo, every MAX and every A380 scrolled for nothing. The maker is now dropped as soon as the full name is too long, and only what is still too long without it scrolls. `DE HAVILLAND CANADA` also stopped leaving a lonely `CANADA` behind.

## 0.17.0
- **Airline names beyond the built-in list.** The route answer adsbdb gives for a callsign also names the airline, and the wall now keeps that name for the callsign's three-letter prefix: a flight of an airline outside the ninety built in is shown with its name instead of a bare callsign, from the first route lookup on, for every later flight of that airline. No new request, no new service, nothing written to disk (the names live in memory, the server stays read-only); with routes off nothing changes. The built-in list keeps priority, its names being the short ones. Corporate suffixes (`Inc.`, `AG`, `Ltd`) are dropped. Tested against a real adsbdb answer.

## 0.16.3
- **The statistics page no longer smears its left edge once an hour passes a million messages.** The vertical axis of *Messages per hour* drew a line every 10 000, which is about three hundred labels written on top of each other with 3 million messages in an hour. The step now fits the size (1, 2 or 5 times a power of ten, four to six lines), and the axis reads `1 M`, `2 M`, `20 k`; the number above the busiest bar and the tooltips stay whole. A test takes the real `ticks()` out of `stats.js`.

## 0.16.2
- `zenithboard security` recognises ports 8504 and 8978: FlightAware's SkyAware map, which `dump1090-fa` also serves there. Found on a real Pi.

## 0.16.1
Three things the first real `zenithboard security` run on a Pi showed.
- **An update now refreshes every ZenithBoard unit file the Pi has**, whatever component is being updated. The audit found `zenithboard-data-refresh` at 9.6: the unit from before the sandboxes was still in place, because only a full FlightInfo update rewrote it. Now any update replaces every unit that differs from the repository's copy, and tells systemd once.
- **Open ports are listed once each.** A service listening on IPv4 and IPv6 appeared twice.
- **The feeders' ports are recognised**: readsb's inputs and the MLAT returns (30100–31999) and Flightradar24's page (8754) are no longer "something you installed?".

## 0.16.0
- **Statistics, off by default.** `sudo zenithboard stats on`, or menu 4 → Receiver → 5, starts a timer that takes one sample every fifteen minutes: messages decoded, the farthest aircraft, aircraft with a position, and the distinct aircraft seen that day. Thirty days are kept, about 6 KB a day. It runs as the `zenithboard` user inside the same sandbox as the wall (1.0 on systemd's scale).
- **`http://PI:8080/stats`**: four numbers for today and three charts — messages per hour over 24 hours, the farthest aircraft per day, aircraft per day — one colour each, a tooltip on every bar, the same numbers as a table, light or dark with the device. No fonts or scripts from the internet. `/api/stats` gives the JSON; both say so when statistics are off.
- **`zenithboard stats`** prints today, yesterday, the thirty-day average and best, and the day's hours as a sparkline; `stats csv` the raw lines; `stats status`, `stats clear`, `stats off` (keeps the files).
- The daily aircraft count is a floor, and both views say so: a sample every fifteen minutes misses an aircraft that crossed in less. Fifteen minutes is the same trade the gain log makes between knowing and writing to the SD card.
- Tested here against a fake decoder (what one sample writes, the day's count, pruning, the terminal view), against the real server on loopback (`/api/stats` off and on), and the page in a real browser in both themes and at phone width.

## 0.15.0
Security pass, five things. Each one can be undone on its own; the last line of each entry says how.

- **The wall answers your home network only.** It used to answer anyone who could reach port 8080, which with a forwarded port meant the internet, antenna position included. It now serves the private address ranges (10/8, 172.16/12, 192.168/16, the Pi itself, link-local and their IPv6 equivalents) and gives everyone else a 403. New settings `ALLOW_FROM` (`private`, `any`, or a list of networks) and `BIND_ADDRESS`. The dynamic-DNS menu says this at the moment a name is set up. A Pi that forwarded its port on purpose will see a 403 from outside after this update: `sudo zenithboard config-set ALLOW_FROM any` restores it.
- **Every service is sandboxed.** `ddns`, `logs-clean`, `gain-log`, `netwatch` and `wifi` ran as root with no protection (9.4 on systemd's scale). They now score 1.7, 1.4, 1.0, 4.2 and 3.9, each keeping exactly what its tools need: the watchdog keeps raw sockets for `ping` and has no system-call filter, because a filter that killed `ping` would leave the Pi unwatched in silence. The gain log timer runs as the `zenithboard` user, not root. `tests/test_units.sh` measures every unit and fails when a score climbs. The DDNS status and the watchdog counter moved to `/run/zenithboard/`. Undo: `git revert` of this version's commit and `zenithboard update`; the units are reinstalled by every update.
- **Grafana no longer keeps `admin` / `admin`.** At install, and at the next update of a Pi that still accepts it, ZenithBoard sets a generated password and keeps it root-only in `/etc/zenithboard/grafana.pass`. `sudo zenithboard acars password` shows it, `password new` draws another, `password set` takes yours. Not tested against a running Grafana here; the decision, the file and its mode are. Undo: `password set` to anything you like.
- **Debian security fixes, daily, optional.** `sudo zenithboard patches on` installs `unattended-upgrades` and a rule that takes the Debian security channel only: the feeders come from other repositories and are never touched, readsb is not a package, and the Pi is never rebooted by it. Also in the Reliability menu. `patches off` removes the rule, and the package too if `on` was what installed it; a Pi that had it before keeps it as it was.
- **One GitHub release per version.** When `ZB_VERSION` changes on main, a workflow tags it and publishes that version's changelog section as the release notes. The tag is a plain tag; what is signed is the commit it points at, which is what `zenithboard update` checks.
- **`zenithboard security`.** One screen of what the Pi does right now: who may read the wall, whether updates are verified, Grafana's password, SSH password logins, the ports listening on the network, the sandbox score of each installed service, the mode of the two secret files. Each WARN names the command that closes it; exit status 1 when there is one, so a script can notice.

## 0.14.4
- README: a Beluga XL on the split-flap board, in the section about the two looks. Documentation only; nothing on the Pi changes.

## 0.14.3
- **No more bright frame around a scrolling row.** A lit dot's glow is wider than the dot itself. Repainting only the scrolling row's own rectangle left that glow outside the cleared area, and every step added more of it, until a rectangle was drawn around whichever row was moving. The repaint is now clipped to a rectangle three dots larger and redraws the dots around it, so the glow is rebuilt rather than piled up. Checked in a real browser against the real page: the frame appears in 0.14.2 and is gone here.

## 0.14.2
- **A long name now turns continuously instead of jumping back.** 0.14.0 scrolled to the end of the name, paused, then snapped to the start, which read as a stutter. The row now holds the name, a three-space gap, then the name again, and the window walks one length before starting over: what leaves on the left is already arriving on the right. `tests/test_scroll.js` takes the real drawing code out of `app.js` and walks every step of a full turn, checking each one is the previous moved exactly one dot; the old jumping version fails it.

## 0.14.1
- **Fixes the flags of 0.14.0: black was being lit.** A black band came out in the wall's colour, so Germany appeared as three bright bands instead of black, red and gold. Black is now left unlit, which is what it is on the wall and on the flag. The white outline is what makes the edge visible, and it is drawn only around a flag that actually has black in it — Germany, Belgium, Estonia, Egypt, the United Arab Emirates, South Africa, Albania. Every other flag is drawn bare. 0.14.0 outlined by brightness instead, which was the wrong rule and the wrong fix.

## 0.14.0
- **Two flags on the dot-matrix wall.** Where the aircraft is registered, beside the airline, and where it was built, beside the model. The country is read from the registration the wall already has — `OE-LMP` is Austria, `CN-` is Morocco and not Canada, longest prefix first — so there is no lookup and nothing to fetch. Eleven dots by seven, drawn into the same grid as the text, so they scale with the wall.
- **No manufacturer's logo**, in dots or otherwise: those marks are protected and a dotted copy is still a copy. The second flag shows the country the airframe is built in instead, which is not protected.
- A flag with black at its edge (Germany, Belgium, Estonia, Egypt) gets a one-dot white outline, or the black band is indistinguishable from the unlit wall.
- **Long names scroll.** The flags cost the airline and model rows two characters, twelve instead of fourteen, so a row that no longer fits moves sideways one dot at a time with a pause at each end. Only those two rows are repainted, never the whole wall.
- **An aircraft now stays on screen for fourteen seconds** instead of six, which is time enough to read a long name as it goes by. A Pi that already has `CYCLE_SECONDS` in its configuration keeps its own value.
- Flags can be switched off per tablet from the gear, or for every screen with `FLAGS=0`. The split-flap board is unchanged: it is sixteen letter drums, and a flag is not a letter.

## 0.13.1
- **The hall sound of 0.13.0 is removed.** It did not sound good enough to keep. The note beside the gear, the `zenithboard sound` command and the `SOUND` / `SOUND_VOLUME` settings are gone with it; a Pi that had them keeps the two unused lines in `/etc/zenithboard/config.env`, where they do nothing. Nothing else in 0.13.0 existed, so the wall is exactly as it was in 0.12.5.

## 0.12.5
- **Two more wall colours: turquoise (`#00d6d7`) and blue (`#0404e2`).** Both work in either display, the dot-matrix one and the split-flap one, since a wall uses one colour throughout. `zenithboard color turquoise`, or the gear on the tablet. Blue is much deeper than the other five: it reads well up close and turns into a faint navigation light from across a room, so turquoise is the safer choice for a wall meant to be read from the sofa.
- A test now checks that every colour is declared in all four places that have to agree — the shell, the server, the stylesheet and the settings menu — because a colour missing from one of them falls back to amber without saying anything.

## 0.12.4
- **Aircraft photos are back.** 0.11.1 added a check on the photo address, because the Pi fetches that address itself and it comes from somebody else's answer. The check allowed only hosts inside `planespotters.net` — but Planespotters serves its pictures from `plnspttrs.net`, a different domain from the one its API answers on. Every photo was therefore refused in silence and the wall drew its generic plane instead. Both domains are allowed now, still over https only, and the test no longer invents an address: it uses the exact one Planespotters answered with, so a check written from a guess cannot pass again.
- Every request the wall makes to an outside service now sends the same descriptive identification, naming the project, its version and the repository. One of the five (the photo download itself) sent a short form; Planespotters has started refusing requests that do not say who is asking and how to reach them.
- Running `tests/test_server.py` directly ran only the first 30 of its 49 checks: a `unittest.main()` had ended up in the middle of the file. It is at the end now. CI was unaffected — it collects the tests another way and ran all of them.

## 0.12.3
- **The update check stops asking every time.** GitHub's key file holds two keys: its old one, which expired in 2024, and the one it signs with today. 0.12.0 and 0.12.1 recorded only the first — the old one — so every update was signed by a key "not recorded on this Pi" and asked again. Now every key in the file is shown, with expired or revoked ones marked and never trusted, and all the usable ones are recorded. A Pi that recorded only the old key is asked **once** about the current one (it was in the same file you already approved), then never again. A signature from an expired key no longer counts as good either.

## 0.12.2
- Every header the wall sends now comes from a fixed table inside the program: the file type is chosen by extension from a short list, the cache rule from two allowed values, and anything else gets a safe default. 0.12.1 already removed line breaks from those values; this goes one step further, so nothing that arrives with a request or with somebody else's answer can reach a header at all. It also closes the two CodeQL alerts that the 0.12.1 fix still raised, since CodeQL could not recognise a line-break filter as a protection. Nothing changes on screen.

## 0.12.1
- **Fixes an update broken by 0.12.0.** Downloads moved to a private folder in 0.12.0, but that folder was made inside a sub-shell that deleted it again before the download could be written: `zenithboard update` then failed for readsb and ADSB Exchange with `curl: (23)`. The folder is now made once, by the command itself. Everything else in 0.12.0 was unaffected.
- **A photo's type can no longer inject anything into the wall's answers.** The image type came straight from the photo service and went into one of our response headers; a value carrying a line break could have split the reply in two. Only known image types are passed on now, anything else becomes `image/jpeg`, and no header the wall sends can contain a line break. Found by CodeQL on its first run.
- Smaller cleanups CodeQL pointed at: three silent `except` blocks now say why they are silent, four wrappers that only called another function were removed, two computed-and-never-used values are gone, and a test file is closed properly.

## 0.12.0
- **The services can now only do their own job.** The wall server and the ACARS ingester run inside a full systemd sandbox: no devices, no kernel tuning or modules, no namespaces, an empty capability set and a system-call filter. The wall server can write nowhere — it only reads. Check it with `systemd-analyze security zenithboard-flightinfo`. `acarsdec` is deliberately less restricted because it drives a USB dongle.
- **The code is checked before an update installs it.** `zenithboard update` runs `install.sh` as root, so the commit it is about to run must carry a good signature from the key you trusted. The first time it shows you GitHub's signing key and asks; after that it is silent unless something changes. A **bad** signature stops the update outright. Unsigned, or a different key, is explained and you decide — and with nobody there to answer, nothing is installed. On a fork, set `UPDATE_VERIFY=0`.
- **Downloads that are about to be run as root** no longer land on a fixed name in `/tmp`, where another user on the Pi could have created the file first. They go to a private folder made for the run. Downloads are also https-only now, and a redirection cannot drop them to plain http.
- A `SECURITY.md` so a problem can be reported privately, through GitHub, rather than in a public issue.

## 0.11.2
- **Removing readsb now says it cannot be done, instead of appearing to work.** It fetched an uninstaller that has not existed for some time, so the download failed and nothing happened. readsb is built from source by somebody else's installer and there is no way back, so ZenithBoard refuses this one out loud and prints the commands to do it by hand, rather than deleting system files it did not put there. Everything else is still removed normally. Found by the new monthly check of the download addresses, on its first run.

## 0.11.1
- **The Pi no longer follows a photo address it was given without checking it.** Photos are found at Planespotters and then fetched by the Pi itself; that address must now be `https` and inside `planespotters.net`. Before, an answer that had been tampered with could have pointed the Pi at any address on your own network and handed the result to the tablet. Nothing changes for a normal photo.
- The project's security choices are now written down: what is exposed on your network, what is checked in the code, and what is trusted because it cannot be checked (the installers from readsb, ADSB Exchange and Flightradar24, run as root). See the wiki's Security page.
- CI additions: CodeQL on every pull request, the GitHub Actions pinned to a commit instead of a tag, and a **monthly check that the pinned download addresses still answer**, which opens an issue when a provider moves a file — the 404 that otherwise only shows up during somebody's install.

## 0.11.0
- **A 24-hour gain log** (menu *4 Settings → 2 Receiver → 4 Gain → 24-hour log*, or `zenithboard gain log on|off|status|show|clear`), off until you turn it on. One measurement every 15 minutes — gain, messages, share of very strong ones, farthest aircraft, signal levels — written to `/var/lib/zenithboard/gain-log.csv` as a table a spreadsheet can open. It keeps the **last 24 hours and nothing older** (96 lines, the oldest dropped as a new one arrives), so it cannot fill the card, and `gain log clear` empties it. A single check is one moment of one day; this is what lets a gain be chosen on a full day of evidence, quiet night and busy evening side by side.

## 0.10.4
- **A wiki**: the [roadmap](https://github.com/regis57/ZenithBoard/wiki/Roadmap), what is [proven on real hardware and what is not](https://github.com/regis57/ZenithBoard/wiki/Project-status), and thirteen pages documenting the software — architecture, every setting, every command, the wall's layout, the outside services, the watchdogs, gain, a code tour, the tests and the release process. The pages are kept in `docs/wiki/` so they are reviewed like any other change, and copied to the wiki with `tools/publish-wiki.sh`.
- The README now points at those pages instead of repeating them: *Known limits* and *Contributing & tests* are shorter, and the stale "not yet validated on a real Raspberry Pi" note is replaced by the status page.

## 0.10.3
- The settings gear is now in the **bottom-right corner** (it was top-right, where a TV browser's bar slides down and hides it). It sits below the plane photo and the aircraft drawing and never covers them; the settings panel opens upward from it and scrolls on short screens. A new layout test checks this on 15 screen sizes.

## 0.10.2
- Network watchdog, for a Pi on Wi-Fi: when a check fails it now writes what the Wi-Fi sees to the log (is your saved network visible and at what signal, how many other networks are in range, the state of the Wi-Fi), on the 1st, 3rd and 5th failed check and then every 30 minutes, so the next night tells whether the router's Wi-Fi was off, the signal too weak or the Pi at fault. After about 8 minutes it also switches the Wi-Fi radio off and on and asks for the saved connection again, before the Pi is restarted (an Ethernet-only Pi is not affected).
- `zenithboard health` shows the last lines of the network watchdog when it is on.

## 0.10.1
- Gain check: the first line now shows the date and time of the check (`Checked: 2026-10-08 20:18`), so a result copied somewhere can be placed in the day (the share of strong messages changes a lot between night and rush hour).

## 0.10.0
- **Reliability** (menu *4 Settings → 5 Reliability*, and `zenithboard health|watchdog|netwatch|keeplogs`), all off until turned on: a **health check** screen (power, temperature, memory, card, how the previous boot ended, problems in the logs); **saved logs** (the system log survives a restart, capped at 50 MB); the **hardware watchdog** (restarts a frozen Pi after about 10 s); a **network watchdog** (checks the router every 2 minutes, restarts the network after about 6 minutes of failure and the Pi after about 12, never more than once every 3 hours, never in the first 10 minutes after a start). It looks at the router only, so an internet outage alone changes nothing.

## 0.9.2
- **Wrong routes are no longer shown.** The route database knows *callsigns*, not flights, and a callsign can be reused for another route or the other direction. The wall now drops an answer that cannot be this flight: the same airport as origin and destination (seen: "East Midlands → East Midlands"), an aircraft far from the line between the two airports (more than 120 km, or 20 % of the route length), or one flying away from the destination. A blank route row is better than a wrong one. The airport positions used for this check are never displayed.
- **Second opinion from hexdb.io**, only when adsbdb's answer is dropped as impossible: the callsign is asked once on [hexdb.io](https://www.hexdb.io/) (answers kept 12 h, a few requests in total, never from the display loop) and the wall takes the first leg of that route the aircraft can really be on. Airport positions are asked once each and kept until restart. If hexdb is unreachable nothing wrong is shown or remembered.

## 0.9.1
- Gain check: an "under 1 % strong messages" reading no longer reads as an invitation to raise the gain. It now says the share depends on traffic (lower at night) and to check again at a busy hour first. README wording the same.

## 0.9.0
- **Gain** (menu *4 Settings → 2 Receiver → 4 Gain*, or `zenithboard gain ...`): *Check* reads the decoder's statistics of the last 15 minutes and says whether the gain is too high (over 5 % very strong messages), good (1-5 %) or can be raised one step; *maximum*, *one step lower/higher*, *type a value* (rounded to the dongle's real steps) and *back to the default* change only the `--gain` part of the decoder options and restart the decoder. Nothing is automatic. A `--gain -10` (the dongle's own automatic gain, not the maximum) is recognised and explained.
- README: new "Gain" section; chapter 4 is now "The receiver".

## 0.8.6
- Domain name: a DuckDNS token must now look like a DuckDNS token (36 characters, 8-4-4-4-12), so a typo is caught at once instead of as a "KO" later. When DuckDNS does refuse, the status shows the sub-domain that was sent and the token length (never the token).
- New **Test** (menu Network > Name, or `sudo zenithboard ddns test`): asks DuckDNS the same thing in four ways (as the timer does, without `ip=`, IPv4 only, with another user-agent) and explains the answers, to find out why a refusal happens. The token is never shown.

## 0.8.5
- **Domain name timer fixed**: it only had a "60 s after boot" start, so when the name was set up long after boot the 5-minute refresh never started until the next reboot. It now starts 30 s after being switched on and repeats every 5 minutes.
- Domain name status says plainly when the name points to your address ("it works"), whatever older line is shown.
- Domain name: the first update right after the setup is retried up to 3 times (5 s apart) before it is reported as failed, since the network or the service can still be settling; the status line now shows the service's own short answer (`OK`, `KO`, `badauth`...), which never contains the token.

## 0.8.4
- README: badges (licence, CI, Buy Me a Coffee) and a short "Support the project" section; `.github/FUNDING.yml` adds GitHub's *Sponsor* button to the repository page, pointing to https://buymeacoffee.com/regis57.

## 0.8.3
- Menu 6 Update: after an update (everything, or the components you ticked) the menu reopens by itself on the new version. Before, it stayed on the old code until you quit and came back.

## 0.8.2
- Menus: the *Back* entry no longer repeats the word in both columns (`back  Back`); it now reads `back  Return to the previous menu`.

## 0.8.1
- Menus: one way out instead of two. A menu with a *Back* entry in its list no longer also shows a Cancel button; a plain picker (no Back entry) keeps its button, now named *Back*. Esc works everywhere. Covered by `tests/test_menus.sh`.

## 0.8.0
- **Update menu** (menu 6): *Update everything*, or *Choose what to update* with a tick list of the installed components. Command line: `zenithboard update list` and `sudo zenithboard update only readsb flightinfo ...`.
- **Settings regrouped** into four entries: *1 Network*, *2 Receiver* (region, units, antenna position), *3 ZenithBoard wall* (radius, look, colour, seconds per aircraft, photos, routes, monthly data refresh) and *4 Logs*.
- **Logs**: new *automatic cleaning* (opt-in, `zenithboard logs auto on|off`): once a day a timer removes messages older than 7 days. The ambiguous *Clean: keep the last 7 days* choice is gone; `zenithboard logs clean` now means "delete everything".

## 0.7.0
- **Settings → Network** (new sub-menu, first entry of Settings): *1 Wi-Fi* (moved here), *2 Fixed IP* and *3 Domain name*.
- **Fixed IP** (`zenithboard net static|dhcp|status`): address, subnet mask (autocompleted, `255.255.255.0` or `24`), gateway (autocompleted, checked against the network) and DNS (Cloudflare, Google, the router or your own), for the Ethernet or Wi-Fi connection you pick. Only the IPv4 address settings are written: Ethernet stays the preferred connection, Wi-Fi the fallback. Kept after a reboot; *Back to automatic (DHCP)* undoes it.
- **Domain name** (`zenithboard ddns ...`): free dynamic DNS with **DuckDNS**, **No-IP** or **FreeDNS**, refreshed every 5 minutes by a systemd timer, with a guide to get a free name, how to forward a port in the router for the wall and/or the tar1090 map, and a privacy warning. The token / key is kept in a root-only file, never on a command line.
- Settings menu reordered as a first setup would go (network, place, look, data, logs); the README is reorganised the same way and shortened.

## 0.6.0
- **Model row fixed.** The line under the airline (aircraft type + registration) stayed empty whenever the receiver's database did not know the aircraft, and the model name was never used. The wall now asks adsbdb by the aircraft's 24-bit address (same "Flight routes" on/off setting, answers cached, requests spaced) and shows the model name when it fits, else the type code and registration.
- **Split-flap look** (opt-in): an old airport board where letters roll one by one, row after row, when the wall changes aircraft. Choose it with `?mode=flap`, gear > Style, `zenithboard mode flap|dots` or menu *4 Settings > Look*. Dot matrix stays the default.

## 0.5.0
- **Wi-Fi settings** (menu 4 Settings, first entry; `zenithboard wifi ...`): on/off, country, scan with signal strength, connect with a password, hidden networks, saved networks (connect, change password, auto-connect, forget), status. Built on NetworkManager. Networks are root-only profile files joined at boot; the on/off choice and the country are saved and re-applied at every boot (`zenithboard-wifi.service`), so everything survives a crash or reboot. Ethernet stays the preferred connection (Wi-Fi route metric 600 vs 100), the menu says so, and it warns before a change that could cut an SSH session over Wi-Fi. If NetworkManager is missing, the menu offers to install it (opt-in, refuses over a Wi-Fi SSH session; `zenithboard wifi install-nm`). Passwords never appear on a command line. Written without a Pi at hand: unit-tested on throw-away files (`tests/test_wifi.sh`), not yet tried on real hardware.

## 0.4.1
- README: links to the YouTube Short, the how-to and the playlist; the "See it" section is lighter (smaller previews, two real-flight photos instead of four).
- README: a "See it" section with an animated preview, the four colours, real flights and a short video; status line updated (the installer now runs on a real Pi).
- **Aircraft photos are shown complete**, never cropped: the corner now takes the photo's own proportions (wide, standard, square or tall), as large as the space allows, anchored bottom-right, with the credit on its own line underneath instead of over the picture. Before, a fixed frame cut off tails and noses.
- README: a table of tablet links with distinct examples (units, distance in km or miles, colour, seconds per aircraft).

## 0.4.0
- **Region** is now asked first (`world` or `us`; `zenithboard region world|us`, menu *4 Settings → Region*). With `us` the installer pre-selects imperial units and offers the new **978 MHz UAT** step in menu *1 ADSB* (second dongle, FlightAware `dump978-fa` + `skyaware978`); elsewhere nothing changes. The wall merges the 978 MHz aircraft with the 1090 MHz ones (an aircraft heard on both appears once). Written without a 978 MHz setup to test the radio part; the tests cover the dongle configuration, the region logic and the list merge.
- **Logs** (optional): `zenithboard logs usage|review|limit MB|default|clean [DAYS|all]` and menu *4 Settings → Logs* to see how much the journal uses, cap it (useful on a small SD card) and clean it.
- `zenithboard logs uat`, a 978 MHz line in `zenithboard status`, README sections "978 MHz UAT" and "Logs", hardware note for three dongles.

## 0.3.2
- README: a note on position and altitude for each feeder (what is automatic, what must be edited by hand on Flightradar24 / FlightAware / Plane Finder, altitude in metres vs feet).
- **Routes now retry after 1 minute** (was 10) when adsbdb could not be reached, so a flight no longer goes without its origin/destination for most of its pass over a single network hiccup; "unknown callsign" is re-checked every 2 h (was 6 h). Failed lookups are written to the log (`zenithboard logs flightinfo`).
- New `zenithboard routes test [CALLSIGN]`: checks from the Pi that adsbdb.com can be reached and shows the route it knows.
- **Flightradar24 install made friendlier**: FR24's own sign-up wizard is used (it already asks for an existing sharing key, so there is no second prompt of ours). Before it starts, the installer prints what to answer (sharing key if you have one, MLAT no, Beast / 127.0.0.1 / 30005); afterwards Beast, `127.0.0.1:30005`, MLAT = no and no BS/raw feed are enforced in `/etc/fr24feed.ini` even if a wizard answer was wrong. If the wizard did not finish, the installer says so and how to run it again.
- Fixed the **Flightradar24 install failing** with `The repository ... is not signed` / `SHA1 is not considered secure since 2026-02-01`: Debian 13 (trixie) refuses SHA1 signatures and FR24 re-signed its repository with a new key. The installer (and `zenithboard update`) now installs FR24's 2026 key where the FR24 apt source expects it, **only when its fingerprint is exactly `ED843290A602413685E57D436F7703F65FA1BDAF`** (the key apt reports as missing), then finishes the install and the FR24 sign-up. Signature checking is never disabled, and the test suite fails if a flag such as `trusted=yes` or `--allow-unauthenticated` ever appears in the code.
- New `tests/test_fr24_key.sh` (in CI): a throw-away GPG key and a fake apt folder check the one-line and deb822 source formats, `.asc` keyrings, the default path, replacement of an old keyring, refusal of a wrong fingerprint, and failed downloads.

## 0.3.1
- Fixed the **FlightAware (piaware) install failing with a 404**: FlightAware renamed its repository package from `piaware-repository_9.0.1` to `flightaware-apt-repository_1.3` and moved it. The installer now uses the new one (older installs that already have the old package keep working) and, if the download fails again, says which file to check. dump1090-fa uses the same repository, so it was affected too.
- Fixed the **Plane Finder** package address: the pinned 5.0.162 on the old server is replaced by 5.4.211 on `client-v2.planefinder.net` (https), as published on planefinder.net.

## 0.3.0
- **Where the flight comes from and goes to** is now on the wall: two rows with the origin and, after an arrow, the destination. The airport's name is shown when it fits the 14-character column, otherwise its city; accents are folded because the dot font has none. The route is looked up from the callsign on the free community database adsbdb.com (ADS-B itself never carries it), only for airline callsigns, spaced out (one request every 1.5 s) and kept for 12 hours. Only the callsign is sent, never your position.
- New setting `zenithboard routes on|off` (also in menu *4 Settings*), shown in `zenithboard status`.
- Wall layout: heading (`HDG`), vertical speed (`V/S`) and the radius were removed to make room. The last line now has the whole width and shows the position in the cycle, the distance and the direction.
- Demo: invented routes for some aircraft (others deliberately have none); `REAL_PHOTOS=1 ./bin/zenithboard-demo` also looks up the real route of its two real airliners.
- Photo and route lookups share one throttled lookup class (single worker, retry after a refusal, daily re-check of "not found", expiry of known routes).
- README: screenshots of the first installer screens (without version number), a "Flight routes" section.

## 0.2.2
- Fixed photos appearing for only one aircraft: Planespotters answers **403 Forbidden** when it is asked too quickly, and the wall used to fire one request per aircraft at once. Lookups now go through a single worker that makes at most one request every 2 seconds.
- A refused or failed lookup is no longer remembered as "this aircraft has no photo": it is retried 10 minutes later. An aircraft with no photo published is re-checked once a day.
- `zenithboard photos test` spaces its requests out too, and explains a 403 instead of reporting it as a failure.

## 0.2.1
- The animated sky is now one continuous day: the sun and the moon travel along an arc, the colours are interpolated from the clock (dawn, midday, dusk), clouds are lit from the sun's side, high cirrus drifts past, haze sits on the horizon, and the stars fade in and twinkle at night.
- `zenithboard photos on|off` now restarts the wall, so the setting takes effect immediately (before, it was written to the configuration and ignored until the next restart).
- New `zenithboard photos test [HEX]`: checks from the Pi that Planespotters can be reached and that an image downloads, without waiting for an aircraft.
- `REAL_PHOTOS=1 ./bin/zenithboard-demo` fetches the real photos of the demo's two real airliners, so photos can be seen before the antenna is connected.
- `zenithboard status` now shows whether photos are on, and prints the local map address that is actually installed (`/tar1090/` from readsb, or `/adsbx/`) instead of always `/adsbx/`.
- Fixed "Aircraft list: not downloaded" in `zenithboard status` when run without `sudo`: `/var/lib/zenithboard` was not traversable by other users. `zenithboard update` repairs existing installs.

## 0.2.0
- New wall layout (16:10): aircraft silhouette top-right, a real Planespotters photo (with credit and link) bottom-right, airline name line, distance/direction footer.
- Silhouettes now match the real aircraft model: 15 kinds (single-aisle, wide-body, 747 hump, A380 double deck, rear-engined jets, turboprops, bizjets, light/twin piston, helicopters incl. Chinook and tilt-rotor, fighters, delta-wings, transports, bombers, gliders, balloons), including military types. Type table checked against the ICAO type list.
- No photo? The corner shows an animated sky (drifting clouds, day/dusk/night, turning propellers and rotors) with a side view of the matching model and its name.
- Airline logos removed entirely (no logo library, no `logo` command, no `SHOW_LOGOS`).
- `zenithboard update` now resynchronises its download folder when the GitHub history was rewritten (e.g. commits re-signed) instead of failing with "Diverging branches"; it says clearly when the code could not be updated and which version you stay on.
- `zenithboard update` no longer leaves root-owned files in your download folder (which made your own `git fetch` fail with "Permission denied").
- Fixed the ADSB Exchange update URL (`feed-update.sh`).
- Optional monthly refresh of the aircraft model list (tar1090-db, downloaded to the Pi only): `zenithboard data update|auto on|off|status`, settings menu toggle, systemd timer.
- Colour setting: `zenithboard color amber|green|red|white` (amber default), menu entry, per-tablet override.
- Photos are fetched by the Pi (proxy) and enabled by default for new installs. Demo has mock photos for some aircraft only, so both states show.
- Demo runs on port 8081 so it cannot clash with the real wall; README documents the ports and the ADSB Exchange local map.
- Detects low-memory (< 1.5 GB) and older Pi boards: one-time notice, ACARS marked "not recommended", warning for many feeders, memory in `zenithboard status`.
- README: "Which Raspberry Pi?" table.

## 0.1.0
- Licence changed to GPL-3.0-or-later.
- New installer menu: 1 ADSB, 2 FlightInfo, 3 ACARS, plus Settings / Status / Uninstall.
- readsb (recommended) or dump1090-fa; ADSB Exchange mandatory; FlightAware, Flightradar24, Plane Finder optional; single MLAT enforced.
- First-run questions: metric/imperial, antenna position, radius. `zenithboard` command to change them later.
- FlightInfo rewritten: dependency-free Python server, canvas dot-matrix wall with built-in 5x7 font (works offline), radius presets, units, themes, auto-cycling, self-refresh.
- ACARS: acarsdec -> filtered SQLite with 7-day rolling retention -> Grafana dashboard.
- Tests and CI.
- `zenithboard update`: one command to upgrade ZenithBoard and every installed component.
- `zenithboard location`: sets the antenna position everywhere it is stored and lists what must be changed manually.

## 0.0.1
- Initial prototype.
