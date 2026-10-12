# Security

ZenithBoard runs as root on a machine in your home, listens on your network, and installs software written by other people. This page says what that means, what is checked, and what is not.

**Found a hole?** Open an issue, or write to the address on the [repository](https://github.com/regis57/ZenithBoard) if you would rather not do it in public. It is a spare-time project with no security team and no deadline to promise — but a real report will be taken seriously and credited.

## What is actually exposed

| Surface | Reachable from | Notes |
|---|---|---|
| The wall, port 8080 | Anyone on your network | No login. It is meant to be opened by a tablet with no keyboard |
| `/api/planes`, `/api/config` | Same | Aircraft in range, and display settings. **The antenna's exact position is never sent** |
| tar1090, port 80 | Same | Installed by readsb, not by ZenithBoard |
| Grafana, port 3000 | Same | Only with ACARS. Default login `admin`/`admin` — change it |
| Plane Finder, port 30053 | Same | Its own setup page |

**Do not forward any of these from the internet.** Nothing here expects a hostile visitor: there is no login on the wall, no rate limit, and no audit trail. If you want to see your wall from outside, use a VPN to your home network. The dynamic-DNS feature exists so *you* can find your Pi, not so the world can.

## What is checked in the code

* **Files served from the wall.** Both file handlers resolve the real path and refuse anything that leaves the folder, so `../../etc/shadow` and its symlink cousins get a 404.
* **The photo address.** Photos are found at Planespotters and then fetched *by the Pi*. Since 0.11.1 that address must be `https` and inside `planespotters.net` before the Pi will follow it. Without the check, an answer that had been tampered with could have pointed the Pi at anything — your router's admin page, for instance — and handed the result to the tablet.
* **The dynamic-DNS token.** Never on a command line, never in `zenithboard config`, never in the logs. It lives in a root-only curl configuration file, which is why `zenithboard config` is safe to paste into an issue.
* **The Flightradar24 signing key** is installed only when its fingerprint matches the one recorded in `lib/versions.sh`. Package signature checking is never turned off, for any reason — see [Contributing](Contributing).

## What is trusted, and cannot be checked

The installer runs other people's installers, as root, straight from the network:

| Fetched and run as root | From |
|---|---|
| `readsb-install.sh` | wiedehopf/adsb-scripts on GitHub |
| `feed.sh`, `feed-update.sh` | adsbexchange.com |
| `install_fr24_rpi.sh` | repo-feed.flightradar24.com |
| `.deb` packages | FlightAware, Plane Finder, Grafana |

**This is a real trust decision and it is not hidden.** Installing ZenithBoard means trusting those four projects as much as you trust this one. Pinning a checksum for each would break on every release they make — their scripts change far more often than this project does — so what is pinned instead is the *address*, in `lib/versions.sh`, where you can read it before running anything.

If that trust is more than you want: install readsb yourself, by hand, and use only the wall. The wall needs nothing but `aircraft.json`.

## What is in the supply chain here

Deliberately very little. Python standard library only, no `pip install`; plain browser JavaScript, no build step, no npm; bash. There is no lockfile because there is nothing to lock. It is the main reason a dependency scanner finds nothing to report on this repository — the dependencies were never taken on.

What is left is the GitHub Actions used by CI, and those are **pinned to a commit rather than a tag**, since a tag can be moved to other code and these run with a token. Dependabot opens a pull request when one has a new release.

## What runs in CI

| Check | Does |
|---|---|
| shellcheck, at `-S warning`, following `source` | Quoting, unset variables, the usual shell traps |
| CodeQL, Python and JavaScript, weekly and on every pull request | Injection, unsafe handling, data flow into dangerous calls |
| The test suite | Including the path and address checks described above |
| The monthly download-link check | Opens an issue when a pinned address stops answering |

Three tools that are **not** used, and why, since the question comes up: **Trivy** reads lockfiles, and there are none. **OWASP ZAP** tests running web applications, and this one is five routes with no login, no forms and no database — it was read line by line instead, which is how the photo-address gap above was found. **Opengrep/Semgrep** would duplicate what CodeQL and shellcheck already cover.

## Running it more tightly, if you want to

* Put the Pi on a guest network or its own VLAN. It needs the internet and nothing else on your LAN.
* Change the Grafana password, or do not install ACARS.
* `sudo zenithboard update` regularly: it is what brings security fixes to the decoder and the feeders.
* Turn on `unattended-upgrades` for Debian security updates. Leave the feeders out of it — a feeder restarting itself at three in the morning can quietly break the single-MLAT rule.
