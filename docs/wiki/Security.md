# Security

ZenithBoard runs as root on a machine in your home, listens on your network, and installs software written by other people. This page says what that means, what is checked, what is trusted, and what was found and fixed along the way.

**Found a hole?** Use GitHub's private vulnerability reporting on the repository (*Security → Report a vulnerability*), or a normal issue if it is not sensitive. See [SECURITY.md](https://github.com/regis57/ZenithBoard/blob/main/SECURITY.md). It is a spare-time project with no security team and no deadline to promise — but a real report will be read, answered and credited.

## In one table

| Layer | What protects it | Since |
|---|---|---|
| Your network | The wall has no login **by design**: never forward it from the internet | always |
| The wall server | Runs as a `nologin` system user inside a full systemd sandbox; can write nowhere | 0.12.0 |
| The ACARS ingester | Same sandbox; listens on `127.0.0.1` only; parameterised SQL | 0.12.0 |
| Its HTTP answers | Every header value comes from a fixed table inside the program | 0.12.2 |
| Photos | The address must be `https` inside `planespotters.net`; the type must be a known image type | 0.11.1 |
| Files it serves | Real-path check: nothing outside its own folders, symlinks included | always |
| Updates of ZenithBoard | The commit is signature-checked before `install.sh` runs as root | 0.12.0, fixed in 0.12.3 |
| Downloads run as root | Private `mktemp` folder (mode 700), https only, no downgrade on redirect | 0.12.0, fixed in 0.12.1 |
| Third-party installers | **Trusted, not checked** — written down below | always |
| Package signatures | Never turned off. The Flightradar24 key is installed only if its fingerprint matches | always |
| Secrets | The dynamic-DNS token never goes on a command line, into `config.env` or into a log | always |
| The repository | CodeQL, shellcheck, pinned actions, Dependabot, a monthly check of the download addresses | 0.11.1 |

## What is exposed on your network

| Surface | Reachable from | Notes |
|---|---|---|
| The wall, port 8080 | Anyone on your network | No login. It is meant to be opened by a tablet with no keyboard |
| `/api/planes`, `/api/config` | Same | Aircraft in range, and display settings. **The antenna's exact position is never sent** |
| tar1090, port 80 | Same | Installed by readsb, not by ZenithBoard |
| Grafana, port 3000 | Same | Only with ACARS. Default login `admin`/`admin` — change it |
| Plane Finder, port 30053 | Same | Its own setup page |

**Do not forward any of these from the internet.** Nothing here expects a hostile visitor: there is no login on the wall, no rate limit, and no audit trail. To see your wall from outside, use a VPN into your home network. The dynamic-DNS feature exists so *you* can find your Pi, not so the world can.

## The services can only do their own job

The wall server and the ACARS ingester run as the `zenithboard` system user, which cannot log in, inside a full systemd sandbox: no devices, no kernel tuning, modules or logs, no namespaces, no new privileges, an empty capability set, a restricted list of network families and a system-call filter. The wall server can write **nowhere** — it only reads.

What that buys: a hole in the wall server stays a hole in a read-only program that can see `aircraft.json`, its own files and the internet. It cannot become a foothold on the Pi.

Measure it yourself:

```bash
systemd-analyze security zenithboard-flightinfo
```

On the author's Pi 3B it scores **1.3 (OK)**, on a scale where 0 is fully locked down and 10 is unprotected. What remains open is what the job needs: the internet (for photos and routes) and Python's memory model.

Deliberately less restricted, and why:

| Unit | Why |
|---|---|
| `zenithboard-acarsdec` | It drives a USB dongle, so devices cannot be taken away from it |
| The watchdogs, Wi-Fi and DDNS timers | Short root tasks whose whole job is to restart the network, change the radio, or reboot the Pi |

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
* **The photo address.** Photos are found at Planespotters and then fetched *by the Pi itself*. The address must be `https` and inside `planespotters.net`, checked when the answer arrives and again just before the fetch. Without it, a tampered answer could have pointed the Pi at your router's admin page and handed the result to the tablet.
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

**This is a real trust decision, and it is not hidden.** Installing ZenithBoard means trusting those projects as much as you trust this one. Pinning a checksum for each would break on every one of their releases, so what is pinned instead is the *address*, in `lib/versions.sh`, where you can read it before running anything. A monthly check (below) says when one of those addresses stops answering.

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

**How CodeQL findings are handled:** a real finding is fixed and gets a test. A finding that describes something deliberate is dismissed in the *Security* tab as *Won't fix*, **with the reason written in the dismissal** — the rule is never switched off, because it should still catch the next mistake. Two are dismissed this way today:

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

## Running it more tightly, if you want to

* Put the Pi on a guest network or its own VLAN. It needs the internet and nothing else on your LAN.
* Change the Grafana password, or do not install ACARS.
* `sudo zenithboard update` regularly: it is what brings security fixes to the decoder and the feeders.
* Turn on `unattended-upgrades` for Debian **security** updates. Leave the feeders out of it — a feeder restarting itself at three in the morning can quietly break the single-MLAT rule.
