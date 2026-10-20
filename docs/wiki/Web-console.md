# Web console

A test since **0.39.0**, off by default, that can be taken out again: ZenithBoard's settings from a browser or a
phone on your home network, at `http://PI:8080/console`, in the wall's own look. The menu (`sudo zenithboard menu`)
and the `zenithboard` command stay as they are and stay the reference: every change the console makes runs the same
command, and you read what it prints.

![The console's overview on a computer](https://raw.githubusercontent.com/regis57/ZenithBoard/main/docs/images/console-overview.png)

![The wall's settings on a phone](https://raw.githubusercontent.com/regis57/ZenithBoard/main/docs/images/console-phone.png)

## Turning it on

```
sudo zenithboard console password     # choose its password (asked twice, never on the command line)
sudo zenithboard console on           # prints the address: http://192.168.x.x:8080/console
```

Or the menu: *Settings → 7 Web console*. The first time you sign in, five short steps (the wall's look, statistics,
what keeps the Pi running, your phone, then a review) apply what you chose; *Skip* leaves everything as it is.

Off again: `sudo zenithboard console off` (the password is kept). Gone for good: `sudo zenithboard console forget`
(the password, the signed-in phones and the record of what it ran are deleted). Nothing else on the Pi depends on it.

## Signing in

* **A password**, chosen over SSH. Kept as a scrypt hash in `/etc/zenithboard/console.env` (root:zenithboard, 0640),
  never in `config.env`, never in a log. The password field is a normal one, so the phone's or the browser's password
  manager can keep it. A password session lasts 12 hours (2 hours unused).
* **A phone, by QR code.** On a computer already signed in: *System → Signed in → Pair a phone*; or over SSH:
  `sudo zenithboard console pair`. Scan the code with the phone's camera within five minutes: the link works once and
  keeps the phone signed in for 30 days (7 days unused). The code is drawn dark on its own white square with its
  margin, on the page and in the terminal (`qrencode`, when installed, is told both colours), so it scans on a black
  background. Add the page to the home screen from Safari's *Share* menu to open it in one tap.
* **Signing out**: *Sign out* on the page; *System → Signed in* lists every browser and phone and signs any of them
  out; `sudo zenithboard console signout` signs everyone out, and so does choosing a new password.

**Face ID and passkeys are not offered, on purpose.** A passkey (WebAuthn) is tied to a domain name and browsers allow
it only in a *secure context*: HTTPS, or `localhost` on the machine itself. A plain-HTTP page at an address like
`http://192.168.1.196:8080` is neither, so Safari refuses to create one there
([web.dev: the relying party ID](https://web.dev/articles/webauthn-rp-id),
[Corbado: passkeys need HTTPS](https://www.corbado.com/blog/test-passkeys-localhost-ngrok)). It would take HTTPS under a
domain name the phone trusts — the DuckDNS name with a real certificate, say — which is a project of its own; the QR
code is what signs a phone in meanwhile.

## What it does

One section on screen at a time: a side bar on a computer, tabs at the bottom of a phone.

| Section | What is in it |
|---|---|
| Overview | Up time, temperature and power warnings, memory, card; each service running or not; links to every page this Pi serves (the wall, `/stats`, the receiver map, graphs1090, Plane Finder, Flightradar24, the post pictures) and to the ones it can serve once switched on |
| Wall | Look, colour, units, radius, seconds per aircraft; photos, routes, the receiver map's database, the monthly data refresh |
| Receiver | Region, antenna position, statistics, graphs1090, the gain (check, one step down or up), the gain log, status |
| Sharing | Bluesky on or off, the gap, the picture (look, colour, map, units, photo link, the words), the three summaries (on or off, day and time, which posts, a try); *Try a post* and the pictures |
| Reliability | Hardware and network watchdogs, logs kept after a restart, Wi-Fi hardening, daily security fixes, daily log clean-up; health, memory, logs |
| System | Update ZenithBoard and the wall, update everything; network, Wi-Fi and domain name status; who is signed in, pairing a phone; the security check; turning the console off |

**Activity** (top right) shows the job running as it prints, the last jobs, the journal of changes and the sign-ins.

**Only in the terminal, on purpose:** uninstalling and anything that asks for a typed word; Wi-Fi on, off, networks,
country, and fixed addresses (one mistake cuts the Pi off the network the page comes through); passwords, tokens and
keys (the Bluesky account, the domain name, the console's own); posting to Bluesky; emptying statistics or logs;
importing settings; `config-set`. An update never accepts a new GitHub signing key from the console: it says so, and
the key is answered over SSH.

## How it is kept safe

The wall's server runs as the unprivileged `zenithboard` user inside its sandbox. It cannot change the Pi, and the
console does not give it that right:

1. **Home networks only**: 10/8, 172.16/12, 192.168/16, link-local and the Pi itself, whatever `ALLOW_FROM` says (a
   narrower `ALLOW_FROM` still applies). The page must be opened by an address or a local name (`*.local`, `*.lan`,
   `*.home.arpa`, the Pi's own name, or one listed in `CONSOLE_HOSTS`): a site elsewhere that points its own name at
   the Pi (*DNS rebinding*) gets nothing.
2. **The session**: a random cookie, `HttpOnly`, `SameSite=Strict`, limited to `/console`, kept on the Pi only as its
   SHA-256 (`/var/lib/zenithboard/console/state/sessions.json`, 0600). Every change also carries a second token in a
   header and must come from the page's own origin, so another site cannot make the browser change anything.
3. **Failed sign-ins**: five from an address, then a wait that doubles (30 s up to an hour); thirty in a quarter of an
   hour from anywhere, and everyone waits five minutes. Each is noted in *Activity* and in the wall's journal.
4. **A fixed list of actions** (`flightinfo/console_actions.py`): each is one `zenithboard` command whose values must
   be one of those listed, a number in its range or text matching its pattern. The server checks the request against
   it and writes a small job file into the one folder it may write
   (`ReadWritePaths=/var/lib/zenithboard/console/state`).
5. **A root helper** (`tools/console_run.py`), started by `zenithboard-console.path` when a job appears: it opens the
   file without following links, requires a plain file of the wall's user under 4 KB, checks it against the same list
   (root's own copy in `/opt`), and runs the one command as an argument list — never through a shell — with its input
   closed and a time limit. What it prints goes to `/var/lib/zenithboard/console/out/` (root's, read by the wall), with
   a journal line per change.
6. **The page**: strict security headers (`Content-Security-Policy` with no inline code, `frame-ancestors 'none'`,
   `nosniff`, no referrer), no file from the internet: the fonts, the dots and the QR code generator (MIT,
   `flightinfo/static/vendor/`) are on the Pi.

**What it does not protect against:** the page travels unencrypted on your home network (plain HTTP, like the wall),
so someone able to read your Wi-Fi traffic could read a session cookie. Use it on a network you trust; turn it off
when you do not need it. `zenithboard security` says it is on and checks the password file's mode.

## Files

| File | What |
|---|---|
| `/etc/zenithboard/console.env` | The password's scrypt hash and when everyone was last signed out. root:zenithboard 0640 |
| `/var/lib/zenithboard/console/state/` | The wall's: sessions (hashes), the job spool, the sign-in record. 0700 |
| `/var/lib/zenithboard/console/out/` | Root's: each job's output and end, the journal, the overview's facts, a terminal pairing code's hash |
| `/etc/systemd/system/zenithboard-console.path` · `.service` | The helper, installed by `console on` only |
| `CONSOLE=1` in `config.env` | On; `CONSOLE_HOSTS=name1,name2` adds names the page may be opened by |

## Status

Built and previewed on 21 October 2026 against a stand-in for the `zenithboard` command (desktop and phone width,
headless Chromium): the wizard, every section, Activity, the QR code. The request checks, the sessions, the pairing
and the helper are covered by `tests/test_console.py` and `tests/test_console.sh`. **Not yet run on the reference Pi**:
the systemd path unit, the helper as root, a real update from the page. See [Project status](Project-status).
