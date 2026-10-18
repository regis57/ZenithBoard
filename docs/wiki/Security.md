# Security

ZenithBoard runs as root on a machine in your home, listens on your network, and installs software written by other people. This page says what that means, what is checked, what is trusted, and what was found and fixed along the way.

**Found a hole?** Use GitHub's private vulnerability reporting on the repository (*Security → Report a vulnerability*), or a normal issue if it is not sensitive. See [SECURITY.md](https://github.com/regis57/ZenithBoard/blob/main/SECURITY.md). It is a spare-time project with no security team and no deadline to promise — but a real report will be read, answered and credited.

## In one table

| Layer | What protects it | Since |
|---|---|---|
| Your network | The wall has no login **by design**. It answers home networks only (`ALLOW_FROM=private`): a forwarded port meets a 403 from the internet until you open it on purpose | 0.15.0 |
| The wall server | Runs as a `nologin` system user inside a full systemd sandbox; can write nowhere | 0.12.0 |
| The ACARS ingester | Same sandbox; listens on `127.0.0.1` only; parameterised SQL | 0.12.0 |
| Its HTTP answers | Every header value comes from a fixed table inside the program | 0.12.2 |
| Photos | The address must be `https` inside `planespotters.net` or `plnspttrs.net`; the type must be a known image type | 0.11.1, 0.12.4 |
| Files it serves | Real-path check: nothing outside its own folders, symlinks included | always |
| Updates of ZenithBoard | The commit is signature-checked before `install.sh` runs as root. One GitHub release per version, pointing at that signed commit | 0.12.0, fixed in 0.12.3; releases 0.15.0 |
| Downloads run as root | Private `mktemp` folder (mode 700), https only, no downgrade on redirect | 0.12.0, fixed in 0.12.1 |
| Third-party installers | **Trusted, not checked** — written down below | always |
| Package signatures | Never turned off. The Flightradar24 key is installed only if its fingerprint matches | always |
| Secrets | The dynamic-DNS token, the Grafana password and the Bluesky app password never go on a command line, into `config.env` or into a log; they live in root-owned files (the social one readable by the service's group) | always; Grafana 0.15.0; social 0.18.0 |
| Grafana | ZenithBoard sets the admin password itself at install and at update, so `admin`/`admin` is never left open | 0.15.0 |
| The operating system | Debian's security fixes can install themselves daily, from the security channel only; the feeders are left alone | 0.15.0 |
| Checking all of it | `zenithboard security` reads the running Pi and says what is open and how to close it | 0.15.0 |
| The repository | CodeQL, shellcheck, pinned actions, Dependabot, a monthly check of the download addresses | 0.11.1 |
| The `main` branch | A GitHub ruleset: pull request only, squash only, signed commits, the three checks must pass, no force push, no deletion. It refused a merge when the tests failed | October 2026 |
| Secrets in the repository | GitHub secret scanning and push protection are on | October 2026 |
| Statistics | Off by default. Its sample runs as the `zenithboard` user in the same kind of sandbox, and the `/stats` page answers the same networks as the wall | 0.16.0 |
| Social sharing | Off by default. Posts carry no distance, no bearing and no photo; a map, when chosen, is centred on the track with nothing marking the receiver, and its tiles come from a fixed address (EOX) over HTTPS, checked to be images and capped in size; the service runs as the `zenithboard` user in the wall's sandbox; the account's secret is root:zenithboard 0640, checked by the audit; the picture is drawn in memory and deleted after the post. Bluesky only since 0.19.0: an update removes a Mastodon token left on the Pi | 0.18.0, map 0.19.0 |

## What is exposed on your network

| Surface | Reachable from | Notes |
|---|---|---|
| The wall, port 8080 | Home networks (`ALLOW_FROM=private`) | No login: it is meant to be opened by a tablet with no keyboard. Anyone outside the private ranges gets a 403, forwarded port or not |
| `/api/planes`, `/api/config` | Same | Aircraft in range, and display settings. **The antenna's exact position is never sent** |
| tar1090, port 80 | Same | Installed by readsb, not by ZenithBoard |
| Grafana, port 3000 | Same | Only with ACARS. Login `admin` with the password ZenithBoard set: `sudo zenithboard acars password` |
| Plane Finder, port 30053 | Same | Its own setup page |
| SkyAware, port 8504 (or 8978) | Same | Served by FlightAware's lighttpd, not by ZenithBoard. `zenithboard security` names it |
| `/stats`, `/api/stats` | Same as the wall | Only when `STATS=1`. Counts and ranges per hour and per day; the antenna's position is not part of it. Since 0.22.0 also the farthest aircraft of the day and of the month, each with the large city nearest it and its distance from the antenna: two such lines narrow down where the antenna is, one more reason this page answers the home network only |
| `/api/farthest` | Same as the wall | Only when `STATS=1`. What the statistics sample asks on the loopback: the farthest aircraft of today and yesterday, named, never with a position |
| `/social/preview` | Same as the wall | The picture `zenithboard social test` drew, if any |

**Do not forward any of these from the internet.** Nothing here expects a hostile visitor: there is no login on the wall, no rate limit, and no audit trail. To see your wall from outside, use a VPN into your home network. The dynamic-DNS feature exists so *you* can find your Pi, not so the world can.

Since 0.15.0 the wall enforces that itself: it answers only the private ranges (10/8, 172.16/12, 192.168/16, the Pi, link-local, and their IPv6 equivalents) and gives everyone else a 403. A port forwarded by mistake therefore shows nothing. If you do want it public, or reachable through a VPN whose addresses are not private (Tailscale uses 100.64/10), say so: `sudo zenithboard config-set ALLOW_FROM any`, or the networks allowed, `sudo zenithboard config-set ALLOW_FROM 100.64.0.0/10`. The dynamic-DNS menu repeats this at the moment a name is set up. `BIND_ADDRESS` (default `0.0.0.0`) is the other knob: `127.0.0.1` keeps the wall to the Pi itself, for a reverse proxy in front of it.

## The services can only do their own job

The wall server and the ACARS ingester run as the `zenithboard` system user, which cannot log in, inside a full systemd sandbox: no devices, no kernel tuning, modules or logs, no namespaces, no new privileges, an empty capability set, a restricted list of network families and a system-call filter. The wall server can write **nowhere** — it only reads.

What that buys: a hole in the wall server stays a hole in a read-only program that can see `aircraft.json`, its own files and the internet. It cannot become a foothold on the Pi.

Measure it yourself:

```bash
systemd-analyze security zenithboard-flightinfo
```

On the author's Pi 3B it scores **1.3 (OK)**, on a scale where 0 is fully locked down and 10 is unprotected. What remains open is what the job needs: the internet (for photos and routes) and Python's memory model.

Every ZenithBoard service is sandboxed since 0.15.0, each keeping only what its job needs. Measured offline on the unit files, and enforced by `tests/test_units.sh` so a directive cannot quietly disappear:

| Unit | Score | What it keeps, and why |
|---|---|---|
| `zenithboard-flightinfo` | 1.3 | Nothing: it reads, and talks to the internet for photos and routes |
| `zenithboard-acars-ingest` | 1.3 | Writes `acars.db` |
| `zenithboard-gain-log` | 1.0 | Runs as the `zenithboard` user, not root, since 0.15.0: it reads `stats.json` and appends one CSV line |
| `zenithboard-social` | 1.3 | Reads `aircraft.json`, asks the wall on the loopback, writes its own state folder (and the map tiles' cache in it), posts over the internet. Node or Pillow runs inside the same box to draw the picture |
| `zenithboard-logs-clean` | 1.4 | May write the journal folder, nothing else |
| `zenithboard-ddns` | 1.7 | curl, no capability at all; its status line lives in `/run/zenithboard` |
| `zenithboard-data-refresh` | 4.2 | Writes the aircraft-type list |
| `zenithboard-netwatch` | 4.2 | Keeps raw sockets for `ping`, netlink and D-Bus for `nmcli` and `systemctl`, and **no system-call filter**: a filter that killed `ping` would leave the Pi unwatched without a sound |
| `zenithboard-wifi` | 3.9 | Keeps `CAP_NET_ADMIN` for `iw reg set` and `/dev/rfkill` |
| `zenithboard-acarsdec` | 6.0 | Drives a USB dongle, so devices cannot be taken away from it |

## The code is checked before it is run

`zenithboard update` pulls from GitHub and then runs `install.sh` as root. So before anything is merged or run, the new commit's signature is checked against keys you approved.

**The first time**, ZenithBoard fetches GitHub's signing-key file and lists every key in it. GitHub rotated its key in 2024 and still publishes the expired one, so there are two: expired or revoked keys are marked and never trusted, the rest are recorded in `/var/lib/zenithboard/trust/signer.fpr`. To check before you say yes: click the **Verified** badge beside a commit on GitHub — the *key ID* it shows must be the last 16 characters of one of the listed fingerprints.

**After that** the check is silent, and speaks only when something changes:

| What it finds | What it does |
|---|---|
| Good signature by a recorded key | Installs, says nothing |
| **Bad** signature | Refuses outright. It does not offer to continue |
| A signature by an expired key | Treated as unknown, not as good |
| Not signed, or signed by another key | Explains the possible honest reasons and asks. With nobody there to answer, nothing is installed |

**Why no fingerprint is written into the project's files:** a fingerprint recorded in the very files you are deciding whether to trust proves nothing. Trust starts with you looking once.

**While an update waits for your answer**, you can see exactly which commit it is about to install, from a second terminal, and compare it with the top commit on GitHub:

```bash
git -C ~/ZenithBoard rev-parse --short origin/main
```

Housekeeping:

| To | Do |
|---|---|
| See the trusted keys | `sudo cat /var/lib/zenithboard/trust/signer.fpr` |
| Start the trust over | `sudo rm /var/lib/zenithboard/trust/signer.fpr` — the next update shows the keys and asks |
| Run a fork or your own branch | `sudo zenithboard config-set UPDATE_VERIFY 0` |

## What is checked in the code

* **Files served by the wall.** Both file handlers resolve the real path and refuse anything outside their folder, so `../../etc/shadow` and its symlink cousins get a 404.
* **The photo address.** Photos are found at Planespotters and then fetched *by the Pi itself*. The address must be `https` and inside `planespotters.net` or `plnspttrs.net`, checked when the answer arrives and again just before the fetch. Without it, a tampered answer could have pointed the Pi at your router's admin page and handed the result to the tablet.
* **Every response header.** The content type is chosen by file extension from a short list written in the program, the cache rule from two allowed values, and anything else gets a safe default. Nothing that arrives with a request or with somebody else's answer can reach a header — which closes header injection (a line break that splits one reply into two) for good.
* **Downloads that are about to be run as root** land in a private folder made for the run (`mktemp -d`, mode 700), never on a fixed name in `/tmp` that somebody else could have created first.
* **Every download is https**, TLS 1.2 or later, and a redirection cannot drop it to plain http on the way.
* **The dynamic-DNS token** lives in a root-only file read by curl. It is never on a command line, never in `zenithboard config`, never in a log — which is why `zenithboard config` is safe to paste into an issue.
* **The Flightradar24 signing key** is installed only when its fingerprint matches the one recorded in `lib/versions.sh`. Package signature checking is never turned off, for any reason.

## What is trusted, and cannot be checked

The installer runs other people's installers, as root, straight from the network:

| Fetched and run as root | From |
|---|---|
| `readsb-install.sh` | wiedehopf/adsb-scripts on GitHub |
| `feed.sh`, `feed-update.sh` | adsbexchange.com |
| `install_fr24_rpi.sh` | repo-feed.flightradar24.com |
| `.deb` packages | FlightAware, Plane Finder, Grafana |

**This is a real trust decision, and it is not hidden.** Installing ZenithBoard means trusting those projects as much as you trust this one. Pinning a checksum for each would break on every one of their releases, so what is pinned instead is the *address*, in `lib/versions.sh`, where you can read it before running anything. A monthly check (below) says when one of those addresses stops answering, and [When a provider changes something](Providers) says what happens then.

**readsb cannot be uninstalled by ZenithBoard.** Its installer builds it from source and ships no way back, so removing readsb prints the commands to run by hand instead of guessing which system files to delete. Everything ZenithBoard itself installed is removed normally.

If that trust is more than you want: install readsb yourself, by hand, and use only the wall. The wall needs nothing but `aircraft.json`.

## The supply chain

Deliberately very little. Python standard library only, no `pip install`; plain browser JavaScript, no build step, no npm; bash. There is no lockfile because there is nothing to lock — the main reason a dependency scanner finds nothing to report here: the dependencies were never taken on.

What is left is the GitHub Actions used by CI. They are **pinned to a commit, not a tag**, since a tag can be moved to other code and these run with a token, and each job gets only the permissions it needs. Dependabot opens a pull request when a pinned action has a new release.

## What runs on every change

| Check | When | Does |
|---|---|---|
| shellcheck (`-S warning`, following `source`) | every push | Quoting, unset variables, the usual shell traps |
| CodeQL, Python and JavaScript | every pull request, and Mondays | Injection, unsafe data flows, dead code |
| The test suite | every push | Including the address, header, trust and temp-folder checks above, and that the [command reference](Command-reference) lists every command |
| The download-address check | the 1st of each month, or by hand | Opens one issue when a pinned address stops answering (`tools/check-links.sh`) |
| Dependabot | monthly | Pull requests for the pinned actions |

**How CodeQL findings are handled:** a real finding is fixed and gets a test. A finding that describes something deliberate is dismissed in the *Security* tab as *Won't fix*, **with the reason written in the dismissal** — the rule is never switched off, because it should still catch the next mistake. Two are dismissed this way today, and a third, an *Empty except* note raised on the statistics reader the same day, was fixed rather than dismissed:

| Alert | Why it stays |
|---|---|
| `acars.db` is mode 0640 | Grafana reads it through the `zenithboard` group; others get nothing |
| `types.json` is mode 0644 | A public list of aircraft model names, written by root and read by the wall server as another user; not world-writable |

**Tools that are not used, and why**, since the question comes up: **Trivy** reads lockfiles, and there are none. **OWASP ZAP** tests running web applications, and this one is five routes with no login, no forms and no database — it was read line by line instead, which is how the photo-address problem was found. **Opengrep/Semgrep** would duplicate what CodeQL and shellcheck already cover.

## What was found, and when

Kept as a record, because a security page that only lists what is fine is not believable.

| Version | Found by | What | Fix |
|---|---|---|---|
| 0.11.1 | Reading the code | The Pi followed a photo address from a third-party answer without checking it | https + host check, tested |
| 0.11.2 | The monthly link check, first run | Removing readsb fetched an uninstaller that no longer exists, so it silently did nothing | Says so, prints the manual commands |
| 0.12.0 | Review | Downloads run as root went to fixed names in `/tmp` | Private folder |
| 0.12.1 | A real Pi's update output | The private folder was made inside a sub-shell that deleted it again: updates of readsb and ADSB Exchange failed with `curl: (23)` | Folder made once by the command; a test holds it |
| 0.12.1 | CodeQL, first run | A photo's type went into a response header: a line break could have split the reply | Known image types only |
| 0.12.2 | CodeQL | The 0.12.1 line-break filter was not recognisable as a protection | Every header from a fixed table |
| 0.12.3 | A real Pi asking at every update | GitHub's key file has its expired key first; only that one was recorded | All usable keys recorded, expired ones never |
| 0.12.4 | The wall itself | The host check left out `plnspttrs.net`, where the pictures actually are, so every photo was refused in silence | Both domains allowed; the test uses the real answer |
| 0.15.0 | Reading the code again | The wall answered anyone, forwarded port included; Grafana kept `admin`/`admin`; five timers ran as root with no sandbox; the Pi installed no security fixes by itself | `ALLOW_FROM=private`; a generated Grafana password; every unit sandboxed; `zenithboard patches`; `zenithboard security` to check all of it |
| 0.16.1 | The first `zenithboard security` on a real Pi | An older install still had the unsandboxed `data-refresh` unit (score 9.6): updates installed new unit files only for features that were switched on, never refreshing the ones already there. The same port was listed twice; feeder ports were unrecognised | Every update now refreshes every ZenithBoard unit file the Pi has; ports listed once; decoder and feeder ports recognised |
| 0.16.2+ | CodeQL, on `main` | An `except OSError: pass` in the statistics reader: the deliberate fallback (keep the running count when a day file is gone) was indistinguishable from a forgotten error | The fallback is an explicit return value, same behaviour |
| 0.16.2 | The same audit, rerun | Ports 8504 and 8978 were reported as unknown: they are SkyAware, served by FlightAware's lighttpd | Recognised and named |

## What the author's own Pi says

`zenithboard security` was run on the Pi that is actually outside, on 15 October 2026 (version 0.16.2). Everything passes except two warnings, and both are decisions rather than oversights:

| Warning | Decision |
|---|---|
| Debian security patches are not switched on | Left to the owner: `sudo zenithboard patches on` when wanted. It is off by default because a machine that changes itself at night should be a choice |
| SSH still accepts passwords | **Kept on purpose.** The Pi is reached by SSH from the home network only, nothing forwards port 22, and the wall refuses everyone outside the private ranges. The warning stays visible in the audit so the decision stays a decision. Anyone who opens the Pi to the internet should turn passwords off first |

All five services are sandboxed, and every listening port is recognised: none is unexpected.

## Running it more tightly, if you want to

* Put the Pi on a guest network or its own VLAN. It needs the internet and nothing else on your LAN.
* Run `zenithboard security` and do what its WARN lines say.
* `sudo zenithboard update` regularly: it is what brings security fixes to the decoder and the feeders.
* `sudo zenithboard patches on`: Debian's security fixes, daily, from the security channel only. The feeders are left out on purpose — a feeder restarting itself at three in the morning can quietly break the single-MLAT rule — and the Pi is never rebooted by it. `patches off` removes exactly what `on` added.
* SSH with a key rather than a password, once your key is in place: `PasswordAuthentication no` in `/etc/ssh/sshd_config.d/zenithboard.conf`, then `sudo systemctl restart ssh`. `zenithboard security` reads this setting.
