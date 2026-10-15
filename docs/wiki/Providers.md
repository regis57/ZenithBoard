# When a provider changes something

ZenithBoard does not make FlightAware, ADSB Exchange, Flightradar24 or Plane Finder. It installs their software and keeps it fed with what the antenna hears. They are free to rename a file, move a download, publish a new version or change a signing key, and none of them asks ZenithBoard first. This page says what happens then, what you will see, and what to do.

The short version: **a provider's change can stop *that provider's* install or update, and nothing else.** The wall, the other feeders and your settings keep running, and package signatures are never switched off to get past it.

## Three kinds of change

| What the provider does | What happens | What you do |
|---|---|---|
| **Publishes a new version at the same address** | Nothing breaks. `sudo zenithboard update` brings it | Update once a month, or when you hear of a release |
| **Moves or renames a file** | The install or the update of *that provider only* stops with a warning (`404`, or "check lib/versions.sh"). What was installed before keeps running | Wait for the fix, or make it yourself: one line (below) |
| **Changes how it works** (a new signing key, an installer that behaves differently) | A new signing key is refused until its fingerprint is checked. An installer that behaves differently is **not detected**: see *What cannot be seen coming* | Read the issue or the changelog; report it if something broke |

## Provider by provider

| Provider | What ZenithBoard fetches | What is pinned | Who keeps it current after the first install | If it changes |
|---|---|---|---|---|
| **FlightAware** | The `flightaware-apt-repository` package, once, at install. After that `piaware` and `dump1090-fa` come from FlightAware's own APT repository | The address and version of that one repository package (`FA_REPO_*`) | APT: `zenithboard update` runs `apt-get update` and upgrades `piaware` and `dump1090-fa` | A moved repository package breaks only a **fresh** install. An installed Pi keeps updating through APT |
| **ADSB Exchange** | `feed.sh` to install and `feed-update.sh` to update, fetched **live** each time and run as root | The two addresses (`ADSBX_*`). Not the content | The script itself, which ZenithBoard runs again on every update | A moved script: a warning and no update. A **changed** script is run as it is: trusted, not checked. Afterwards `zenithboard mlat-guard` runs and puts the single-MLAT rule back |
| **Flightradar24** | An installer script, then `fr24feed` from FR24's APT repository | The installer address (`FR24_INSTALL_URL`) and the **fingerprint** of FR24's signing key (`FR24_KEY_FPR`) | APT | A moved installer: a warning. **A new signing key**: refused until the fingerprint in `lib/versions.sh` is updated, and `apt update` goes on reporting the repository as not signed until then. The key is never skipped. See [Security](Security) |
| **Plane Finder** | A `.deb` for your CPU, at a **pinned version** (`PF_VERSION_*`) | The version number and the address | Nobody: `zenithboard update` installs the pinned version again, it does not look for a newer one. A new release means a one-line bump in `lib/versions.sh` | A moved file: a warning ("the Plane Finder package URL may have changed"). Plane Finder is also the feeder that has **never been watched feeding** on a real Pi ([Project status](Project-status)) |
| **readsb** (decoder, not a feeder) | wiedehopf's installer script, run as root | The address (`READSB_INSTALL_URL`) | Its own installer, run again on every update | A moved script: a warning. It has no uninstaller, so removing it prints the commands instead |

Each of the four feeders fails separately. A 404 from Plane Finder does not stop FlightAware from updating, because `zenithboard update` carries on to the next component after a warning and ends with `Update finished`. The warning is in the output you just read, and `zenithboard status` tells you what is actually running.

## How you hear about it

1. **Before an install fails:** on the 1st of each month a GitHub check requests every pinned address (`tools/check-links.sh`). If one stops answering it opens **one** issue in the repository, *A pinned download address no longer answers*, listing which. The same check runs by hand with `bash tools/check-links.sh` in your clone.
2. **During an update:** a warning naming the provider, such as `Plane Finder update failed (check lib/versions.sh)`.
3. **From APT:** a repository that is "not signed" in `apt update`, which is how a changed Flightradar24 key shows itself.

## Fixing it

**The usual way: wait for the release, then update.** When the monthly check opens an issue, the fix is a one-line change in `lib/versions.sh`, made through a pull request and released like any other change. Then:

```bash
cd ~/ZenithBoard
sudo zenithboard update
```

`update` brings the new addresses first, then updates the components with them. To retry only the provider that failed: `sudo zenithboard update only planefinder` (the names are in the [Command reference](Command-reference)).

**To fix it yourself without waiting:** find the provider's current download on their own page, change the one line in `~/ZenithBoard/lib/versions.sh`, and run `sudo zenithboard update only planefinder` (or `adsbx`, `piaware`, `fr24`). A pull request with the same line is welcome. If a later update says *You changed files … so it was not updated*, run `git -C ~/ZenithBoard checkout lib/versions.sh` and update again: by then the fix is in the release.

**What not to do:** switch off signature checking to get past an APT error. A provider whose key changed has to be checked, not skipped: get the new fingerprint from the provider's own page, compare it, and put it in `FR24_KEY_FPR`. `zenithboard update` installs a key only when its fingerprint matches that line.

## What cannot be seen coming

The monthly check proves that an address **answers**. It does not prove that the file behind it is still the right one, that a newer version exists elsewhere, or that an installer still does what it did last month. Three honest consequences:

* **A script that changes behaviour is not detected.** ADSB Exchange's, Flightradar24's and readsb's installers run as root and are trusted on purpose ([Security](Security)). If one of them started doing something else, ZenithBoard would not notice. The remedy is the one the Security page gives: if that trust is more than you want, install the decoder yourself and use the wall alone.
* **Plane Finder does not move on its own.** Its version is a number in `lib/versions.sh`, so a new client version is picked up only once that number is changed.
* **Feeders can rewrite their own settings.** An update of FlightAware or Flightradar24 can switch their MLAT back on; ADSB Exchange owns the single MLAT client. `zenithboard update` ends with the MLAT guard, `zenithboard status` shows how many MLAT clients run (it should be 1 at most), and `sudo zenithboard mlat-guard` puts it right at any time.

## What the maintainer does

When the monthly issue appears: open the provider's own page, find the current file, change the line in `lib/versions.sh`, run the full test set, and merge through the usual pull request. Each version becomes a signed GitHub release, so the next `zenithboard update` carries the fix. The [Release process](Release-process) page has the steps. A fix that depends on a provider's page being checked by a human is not automated on purpose: guessing a new address and installing it as root is the thing being avoided.
