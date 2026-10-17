# Release process

## Version numbers

`MAJOR.MINOR.PATCH`, and the rule in practice is:

| Bump | For |
|---|---|
| **Patch** (0.10.2 → 0.10.3) | A fix, a wording change, a small improvement to something that exists |
| **Minor** (0.10.x → 0.11.0) | A new feature, a new menu, a new command |
| **Major** | Reserved for 1.0, which means "validated on real hardware, no caveats in [Project status](Project-status)": the caveats lifted one by one, two to four weeks hands-off, a fresh install from the README alone, and an update from an old release untouched. The list, kept up to date, is in [Roadmap → What 1.0 takes](Roadmap#what-10-takes) |

Most releases are patches. When in doubt it is a patch.

## The version lives in two files

```
lib/versions.sh        ZB_VERSION="0.12.3"
flightinfo/server.py   VERSION = "0.12.3"
```

Both, always, identical. `tests/test_versions.sh` fails if they drift — the server prints its own version to the wall, and a wall claiming a version it is not makes every bug report misleading.

## The changelog

`CHANGELOG.md`, newest at the top, **written for the person running the Pi**, not for whoever reads the commits. A good entry says what changed on their screen and why they might care:

> The settings gear is now in the bottom-right corner (it was top-right, where a TV browser's bar slides down and hides it).

Not:

> Moved `#gear` to `position: fixed; bottom: 6px`.

Bold the part someone scanning for their own problem would recognise. Put the reason in the same sentence as the change.

## How a change reaches a Pi

1. A branch off `main`.
2. The full test set locally — see [Testing](Testing). CI runs the same commands, and a failure there costs a round trip.
3. A pull request.
4. **Squash and merge** on GitHub. One release, one commit on `main`. The squashed message must carry no co-author or generated-by lines, and the merge commit comes out signed and `Verified`.
5. On the Pi:

```bash
cd ~/ZenithBoard
sudo zenithboard update
```

`update` pulls, re-installs what changed, re-registers any systemd unit whose file moved, and restarts the services. It also re-installs the netwatch units when the network watchdog is on, which is why a release that changes those units does not need anything done by hand.

A display-only change needs one more thing: **reload the page on the tablet or television**. The browser is holding the old JavaScript, and nothing on the Pi can reach in and refresh it.

## The wall is a process, not a file

Deploying new files changes nothing for the wall until `zenithboard-flightinfo` is restarted: the server is a running Python process holding the old code. Since 0.17.3 the end of every update asks the wall on `127.0.0.1` which version it answers, restarts it when that is not the version just installed, and prints what it found. It is a check against the running machine rather than a trust in the flow, which is how the gap was found in the first place: a Pi whose menu said 0.17.2 while the wall's gear panel said 0.17.1.

## Checklist for a release

* [ ] Both version numbers bumped and equal
* [ ] `CHANGELOG.md` entry, in user language
* [ ] README updated if a menu or a setting changed
* [ ] A new or changed command is in the [Command reference](Command-reference) — `test_docs.sh` fails otherwise
* [ ] The wiki updated if behaviour or internals changed — [Project status](Project-status) especially, since it is the page that goes stale first
* [ ] New tests added to `.github/workflows/ci.yml`
* [ ] The whole suite green locally
