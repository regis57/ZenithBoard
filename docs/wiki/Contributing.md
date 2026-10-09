# Contributing

Bug reports and pull requests are both welcome, and a report that something did not work on a real Raspberry Pi is worth more than most code — see [Project status](Project-status) for how much of this is still unproven on hardware.

## Reporting something

Useful to include:

* `zenithboard status` and `zenithboard config` (the dynamic-DNS token is not in either — they are safe to paste)
* `zenithboard health`, if it is a freeze, a reboot or a network loss
* Which Pi model, and whether it is on Ethernet or Wi-Fi
* For a wrong route: the callsign and roughly when

## Proposing a change

1. A branch, one subject per branch.
2. Run the full test set — the commands are in [Testing](Testing). A new behaviour comes with a test; the suite is the only thing standing between a refactor and a Pi that stops decoding.
3. Open a pull request. CI runs shellcheck, the Python tests, the shell tests and the Node tests.

## House style

**The code.**

* Shell: `bash`, shellcheck clean at `-S warning`. Settings are read through `cfg_get`, never directly, so a missing key falls back to its default. Every system path has a `ZB_*` environment override, which is what makes it testable.
* Python: the standard library only. No `pip install` on a Pi.
* JavaScript: plain browser JavaScript, no build step, no framework.
* New versions and download URLs go in `lib/versions.sh` and nowhere else.

**The words.** The README and this wiki are written for somebody who has a Raspberry Pi and an interest in aeroplanes, not for a developer. Plain sentences, no jargon that is not explained in the same breath, and a reason given for anything that looks arbitrary. If a setting has a surprising default, say why.

**Two standing rules.**

* **No airline logos.** They are trademarks. See the [Roadmap](Roadmap).
* **Package signature checking is never turned off**, for any reason, not even temporarily in an installer. If a provider's key is wrong, the fix is to install the right key after checking its fingerprint — which is what `lib/versions.sh` and `test_fr24_key.sh` do for Flightradar24.

## Commits

Plain messages, present tense, saying what changed and why. No co-author or generated-by trailers.

## Licence

GPL-3.0-or-later. By contributing you agree your change ships under it. Source files carry an SPDX line:

```
# SPDX-License-Identifier: GPL-3.0-or-later
```

## This wiki

The pages are kept in the repository under `docs/wiki/` and copied to the wiki from there, so a change to them is reviewed like any other change. Edit the files, not the wiki pages, or the next copy will overwrite you.
