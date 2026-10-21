# SPDX-License-Identifier: GPL-3.0-or-later
"""The web console (0.39.0): ZenithBoard's settings from a browser or a phone on the home network, at /console.

A test the owner may take out again; off by default (`sudo zenithboard console on`). This module is the wall
server's side: who may come in, how they sign in, and how a change is handed to the root helper. It changes nothing
on the Pi itself: the server runs as the `zenithboard` user inside its sandbox, and may write one folder, its own
(state/: the sessions and the job spool). See lib/console.sh for the whole picture and the wiki's Web-console page.

Signing in, as one can on a home network over plain HTTP:
  * a password, chosen over SSH, kept as a scrypt hash in /etc/zenithboard/console.env (root:zenithboard 0640);
  * or a phone paired by a QR code: a random link that works once within five minutes, made either by a browser
    already signed in or by `sudo zenithboard console pair` in a terminal.
Passkeys (Face ID) are not offered: browsers allow WebAuthn only on HTTPS (or localhost) under a domain name, and
never on a plain-HTTP address like http://192.168.1.196:8080 (web.dev/articles/webauthn-rp-id).

What protects it: home networks only (whatever ALLOW_FROM says); a Host header that is an address or a local name
(against DNS rebinding); a session cookie that is HttpOnly, SameSite=Strict and limited to /console; a second token
in a header on every change (against cross-site requests); failed sign-ins slowed down per address and overall;
sessions that end (12 h for a password, 30 days for a paired phone, sooner when unused) and that `console password`
or `console signout` end at once; strict security headers on every page.
"""
import base64
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import socket
import threading
import time

import console_actions as actions

ENV_FILE = os.environ.get("ZENITHBOARD_CONSOLE_ENV", "/etc/zenithboard/console.env")
CONSOLE_DIR = os.environ.get("ZB_CONSOLE_DIR", "/var/lib/zenithboard/console")
STATE_DIR = os.path.join(CONSOLE_DIR, "state")
SPOOL_DIR = os.path.join(STATE_DIR, "spool")
OUT_DIR = os.path.join(CONSOLE_DIR, "out")

COOKIE = "zbc"
# 0.39.2: kept while used, so the terminal is for setting up, not for every visit: a browser signed in with the
# password stays a week (a day unused), a paired phone a year as long as it opens the console once a month
PASSWORD_LIFE_S, PASSWORD_IDLE_S = 7 * 86400, 86400
PAIRED_LIFE_S, PAIRED_IDLE_S = 365 * 86400, 30 * 86400
PAIR_S = 300
MAX_BODY = 8192
FAIL_FREE = 5                       # failed sign-ins from one address before it waits
FAIL_WAIT_S, FAIL_WAIT_MAX_S = 30, 3600
GLOBAL_FAILS, GLOBAL_WINDOW_S, GLOBAL_WAIT_S = 30, 900, 300

LOCAL_NETS = tuple(ipaddress.ip_network(n) for n in (
    "127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16",
    "::1/128", "fc00::/7", "fe80::/10"))
LOCAL_SUFFIXES = (".local", ".lan", ".home", ".home.arpa", ".internal")

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
                               "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

# what the page may read of config.env: the settings it shows, never a secret (there are none in config.env)
SHOWN_KEYS = {
    "UNITS": "metric", "RADIUS": "10", "THEME": "amber", "DISPLAY_MODE": "dots", "CYCLE_SECONDS": "14",
    "SHOW_PHOTOS": "1", "SHOW_ROUTES": "1", "LOCAL_DB": "0", "AUTO_DATA_REFRESH": "1", "STATS": "0", "GAINLOG": "0",
    "REGION": "world", "LAT": "", "LON": "", "ALT_M": "0", "PORT": "8080", "DDNS_PROVIDER": "none",
    "SOCIAL": "0", "SOCIAL_STYLE": "dotmap", "SOCIAL_THEME": "", "SOCIAL_UNITS": "", "SOCIAL_MAP": "normal",
    "SOCIAL_PHOTOLINK": "0", "SOCIAL_SENTENCE": "factual", "SOCIAL_GAP_MIN": "0", "SOCIAL_AREA": "",
    "SOCIAL_DAILY": "0", "SOCIAL_DAILY_AT": "21:00", "SOCIAL_DAILY_PARTS": "1",
    "SOCIAL_WEEKLY": "0", "SOCIAL_WEEKLY_AT": "sun 19:00", "SOCIAL_WEEKLY_PARTS": "1,2,3,4",
    "SOCIAL_MONTHLY": "0", "SOCIAL_MONTHLY_AT": "1 09:00", "SOCIAL_MONTHLY_PARTS": "1,2,3,4",
    "NETWATCH": "0", "WIFI_HARDEN": "0", "LOG_AUTOCLEAN": "0", "CONSOLE_PHONE_SIGNIN": "0",
}


def log(msg):
    print("console: " + msg, flush=True)       # the wall's journal: zenithboard logs flightinfo


def now():
    return time.time()


# --------------------------------------------------------------------------- who may come in
def client_ok(addr):
    try:
        ip = ipaddress.ip_address(str(addr).split("%")[0])
    except ValueError:
        return False
    ip = getattr(ip, "ipv4_mapped", None) or ip
    return any(ip in n for n in LOCAL_NETS)


def host_ok(host, extra=""):
    """The name the browser used: an address, a local name or this Pi's own name. A site elsewhere that points its own
    name at the Pi (DNS rebinding) sends its own name, and gets nothing."""
    host = str(host or "").strip().lower()
    if host.startswith("["):
        host = host[1:host.find("]")] if "]" in host else ""
    elif host.count(":") == 1:
        host = host.split(":")[0]
    if not host:
        return False
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass
    if host == "localhost" or host.endswith(LOCAL_SUFFIXES):
        return True
    names = {socket.gethostname().lower()} | {h.strip().lower() for h in str(extra or "").split(",") if h.strip()}
    return host in names


# --------------------------------------------------------------------------- the password and the sign-out epoch
_env_cache = {"mtime": None, "data": {}}


def secrets_env():
    try:
        mtime = os.stat(ENV_FILE).st_mtime
    except OSError:
        return {}
    if _env_cache["mtime"] != mtime:
        data = {}
        try:
            with open(ENV_FILE, encoding="utf-8") as fh:
                for line in fh:
                    k, sep, v = line.strip().partition("=")
                    if sep and re.match(r"^[A-Z_]+$", k):
                        data[k] = v.strip().strip('"')
        except OSError:
            return {}
        _env_cache.update(mtime=mtime, data=data)
    return _env_cache["data"]


def has_password():
    return bool(secrets_env().get("CONSOLE_PASSWORD_HASH"))


def epoch():
    try:
        return int(secrets_env().get("CONSOLE_EPOCH") or 0)
    except ValueError:
        return 0


def hash_password(pw, salt=None, n=16384, r=8, p=1):
    salt = salt or os.urandom(16)
    h = hashlib.scrypt(pw.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=32, maxmem=64 * 1024 * 1024)
    b = lambda x: base64.b64encode(x).decode()  # noqa: E731
    return "scrypt$%d$%d$%d$%s$%s" % (n, r, p, b(salt), b(h))


def check_password(pw, stored):
    try:
        kind, n, r, p, salt, want = str(stored).split("$")
        if kind != "scrypt" or not (1024 <= int(n) <= 1 << 20) or not (1 <= int(r) <= 32) or not (1 <= int(p) <= 4):
            return False
        got = hashlib.scrypt(str(pw).encode("utf-8"), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p),
                             dklen=32, maxmem=64 * 1024 * 1024)
        return hmac.compare_digest(got, base64.b64decode(want))
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------- failed sign-ins
class Limiter(object):
    """Five tries from an address, then a wait that doubles with each miss (30 s up to an hour); more than thirty
    misses in a quarter of an hour from anywhere, and everyone waits five minutes."""

    def __init__(self):
        self.lock = threading.Lock()
        self.per = {}               # ip -> [misses, locked until]
        self.recent = []

    def wait(self, ip, t=None):
        t = now() if t is None else t
        with self.lock:
            self.recent = [x for x in self.recent if t - x < GLOBAL_WINDOW_S]
            if len(self.recent) >= GLOBAL_FAILS and t - self.recent[-1] < GLOBAL_WAIT_S:
                return int(GLOBAL_WAIT_S - (t - self.recent[-1])) + 1
            misses, until = self.per.get(ip, [0, 0])
            return int(until - t) + 1 if until > t else 0

    def miss(self, ip, t=None):
        t = now() if t is None else t
        with self.lock:
            self.recent.append(t)
            misses, _ = self.per.get(ip, [0, 0])
            misses += 1
            until = t + min(FAIL_WAIT_MAX_S, FAIL_WAIT_S * 2 ** (misses - FAIL_FREE)) if misses >= FAIL_FREE else 0
            self.per[ip] = [misses, until]

    def ok(self, ip):
        with self.lock:
            self.per.pop(ip, None)


# --------------------------------------------------------------------------- sessions
def _sha(text):
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def device_label(ua):
    ua = str(ua or "")
    for key, name in (("iPhone", "iPhone"), ("iPad", "iPad"), ("Android", "Android"), ("Macintosh", "Mac"),
                      ("Windows", "Windows"), ("CrOS", "Chromebook"), ("Linux", "Linux")):
        if key in ua:
            return name
    return "Browser"


class Sessions(object):
    """Kept as their SHA-256 only, in state/sessions.json (the wall's own folder), so a restart of the wall, which
    most changes cause, does not sign anyone out; the file never holds what the browser holds."""

    def __init__(self, path=None):
        self.path = path or os.path.join(STATE_DIR, "sessions.json")
        self.lock = threading.Lock()
        self.data = None
        self.saved = 0

    def _load(self):
        if self.data is None:
            try:
                with open(self.path, encoding="utf-8") as fh:
                    got = json.load(fh)
                self.data = got if isinstance(got, dict) else {}
            except (OSError, ValueError):
                self.data = {}

    def _save(self):
        try:
            tmp = self.path + ".tmp"
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh)
            os.replace(tmp, self.path)
            self.saved = now()
        except OSError as e:
            log("could not keep the sessions (%s): a restart of the wall will sign everyone out" % e.strerror)

    def _alive(self, rec, t):
        life, idle = (PAIRED_LIFE_S, PAIRED_IDLE_S) if rec.get("kind") == "paired" else (PASSWORD_LIFE_S, PASSWORD_IDLE_S)
        return t - rec.get("created", 0) < life and t - rec.get("seen", 0) < idle and rec.get("created", 0) >= epoch()

    def create(self, kind, label):
        token = secrets.token_urlsafe(32)
        t = now()
        rec = {"id": secrets.token_hex(4), "kind": kind, "label": label, "created": t, "seen": t,
               "csrf": secrets.token_urlsafe(24)}
        with self.lock:
            self._load()
            self.data = {k: v for k, v in self.data.items() if self._alive(v, t)}
            self.data[_sha(token)] = rec
            self._save()
        return token, rec

    def get(self, token):
        if not token or len(token) > 100:
            return None
        t = now()
        with self.lock:
            self._load()
            rec = self.data.get(_sha(token))
            if rec is None:
                return None
            if not self._alive(rec, t):
                self.data.pop(_sha(token), None)
                self._save()
                return None
            rec["seen"] = t
            if t - self.saved > 300:            # the last-seen time is written down every five minutes, not each request
                self._save()
            return rec

    def drop(self, token):
        with self.lock:
            self._load()
            if self.data.pop(_sha(token), None) is not None:
                self._save()

    def listing(self):
        t = now()
        with self.lock:
            self._load()
            return [dict((k, v) for k, v in r.items() if k != "csrf") for r in self.data.values() if self._alive(r, t)]

    def revoke(self, sid=None, keep=None):
        """sid: that one; sid None: every one but keep."""
        with self.lock:
            self._load()
            before = len(self.data)
            self.data = {k: v for k, v in self.data.items()
                         if not ((sid is not None and v.get("id") == sid) or (sid is None and v.get("id") != keep))}
            if len(self.data) != before:
                self._save()
            return before - len(self.data)


# --------------------------------------------------------------------------- pairing a phone
class Pairs(object):
    """One-time links. Made here by a signed-in browser, or by `console pair` as root, which writes the token's
    SHA-256 and its end into out/pair (the wall can read it, not write it); a used one is noted in state/."""

    def __init__(self):
        self.lock = threading.Lock()
        self.links = {}             # sha -> {"pid", "until", "by", "used_by"}
        self.used = set()           # the terminal's codes used since the wall started

    def make(self, by):
        token, t = secrets.token_urlsafe(24), now()
        pid = secrets.token_hex(4)
        with self.lock:
            self.links = {k: v for k, v in self.links.items() if v["until"] > t - 600}
            self.links[_sha(token)] = {"pid": pid, "until": t + PAIR_S, "by": by, "used_by": None}
        return token, pid

    def status(self, pid):
        with self.lock:
            for v in self.links.values():
                if v["pid"] == pid:
                    return {"used_by": v["used_by"], "expired": v["until"] < now() and not v["used_by"]}
        return None

    def redeem(self, token, label):
        """-> True once for a live link, then never again."""
        if not isinstance(token, str) or not (16 <= len(token) <= 64):
            return False
        h, t = _sha(token), now()
        with self.lock:
            v = self.links.get(h)
            if v is not None:
                if v["used_by"] or v["until"] < t:
                    return False
                v["used_by"] = label
                return True
            return self._redeem_from_terminal(h, t)

    def _redeem_from_terminal(self, h, t):
        # 0.39.2: the code is refused only when it is unknown, out of date or already used. 0.39.0 also refused it when
        # it could not note it as used on the card, which is what happened on the reference Pi: the wall had been
        # started before `console on` made its folder, so its sandbox kept the folder read-only. Used is now known in
        # memory first; the card's note only carries it over a restart.
        try:
            with open(os.path.join(OUT_DIR, "pair"), encoding="utf-8") as fh:
                want, until = fh.read().split()[:2]
        except (OSError, ValueError):
            return False
        if not hmac.compare_digest(want, h) or float(until) < t or h in self.used:
            return False
        used = os.path.join(STATE_DIR, "pair-used")
        try:
            with open(used, encoding="utf-8") as fh:
                if h in fh.read().split():
                    return False
        except OSError:
            pass                                 # no code used yet
        self.used.add(h)
        try:
            with open(used, "a", encoding="utf-8") as fh:
                fh.write(h + "\n")
        except OSError:
            log("cannot write %s: restart the wall (sudo systemctl restart zenithboard-flightinfo)" % STATE_DIR)
        return True


# --------------------------------------------------------------------------- a computer signed in by a phone
class Approvals(object):
    """0.40.0, asked for by the owner: pairing the other way round. The sign-in page of a computer shows a QR code; a
    phone already signed in scans it, sees the computer, its address and a four-digit code also shown on the computer,
    and says yes; the computer is then signed in, no password typed. Off unless CONSOLE_PHONE_SIGNIN=1.

    The QR code carries the request's name only. The computer keeps a secret of its own and asks with it: a photo of
    its screen signs nobody in. A request is answered once, within two minutes, and turns into a session once."""

    LIFE_S = 120
    PER_ADDRESS = 20                # requests per address per ten minutes; an open page asks one every two minutes

    def __init__(self):
        self.lock = threading.Lock()
        self.reqs = {}              # id -> {"secret": sha256, "code", "label", "ip", "until", "state", "by"}
        self.made = {}              # address -> [times]

    def request(self, label, ip):
        t = now()
        with self.lock:
            self.reqs = {k: v for k, v in self.reqs.items() if v["until"] > t - 600}
            times = [x for x in self.made.get(ip, []) if t - x < 600]
            if len(times) >= self.PER_ADDRESS:
                return None
            self.made[ip] = times + [t]
            rid, secret = secrets.token_urlsafe(12), secrets.token_urlsafe(24)
            code = "%04d" % secrets.randbelow(10000)
            self.reqs[rid] = {"secret": _sha(secret), "code": code, "label": label, "ip": ip, "until": t + self.LIFE_S,
                              "state": "waiting", "by": None}
            return {"id": rid, "secret": secret, "code": code, "seconds": self.LIFE_S}

    def info(self, rid):
        with self.lock:
            v = self.reqs.get(str(rid))
            if v is None:
                return None
            expired = v["state"] == "waiting" and v["until"] < now()
            return {"label": v["label"], "ip": v["ip"], "code": v["code"], "state": "expired" if expired else v["state"],
                    "seconds": max(0, int(v["until"] - now()))}

    def answer(self, rid, yes, by):
        with self.lock:
            v = self.reqs.get(str(rid))
            if v is None or v["state"] != "waiting" or v["until"] < now():
                return False
            v["state"], v["by"] = ("approved" if yes else "refused"), by
            return True

    def poll(self, rid, secret):
        """-> (state, request) for the computer that made it; "approved" is answered once, then "used"."""
        with self.lock:
            v = self.reqs.get(str(rid))
            if v is None or not isinstance(secret, str) or not hmac.compare_digest(v["secret"], _sha(secret)):
                return "unknown", None
            if v["state"] == "waiting" and v["until"] < now():
                return "expired", v
            if v["state"] == "approved":
                v["state"] = "used"
                return "approved", v
            return v["state"], v


def phone_signin(cfg):
    return str(cfg.get("CONSOLE_PHONE_SIGNIN", "0")).lower() in ("1", "on", "yes", "true")


# --------------------------------------------------------------------------- jobs for the root helper
def submit(name, params, by):
    actions.build(name, params)                  # raises Refused; the helper checks it again as root
    job_id = secrets.token_hex(8)
    body = json.dumps({"action": name, "params": params or {}, "by": by, "at": int(now())})
    tmp = os.path.join(SPOOL_DIR, "." + job_id + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)   # root reads it; nobody else need
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(body)
    os.replace(tmp, os.path.join(SPOOL_DIR, job_id + ".job"))   # the .path unit sees it only once it is whole
    return job_id


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def safe_job_id(job_id):
    """16 hexadecimal digits, rebuilt from the number they spell: nothing else from a request reaches a path."""
    if not actions.JOB_ID_RE.match(str(job_id or "")):
        return None
    return "%016x" % int(job_id, 16)


def job_status(job_id, offset=0):
    job_id = safe_job_id(job_id)
    if job_id is None:
        return None
    meta = _read_json(os.path.join(OUT_DIR, job_id + ".json"))
    if meta is None:
        spooled = os.path.join(SPOOL_DIR, job_id + ".job")
        if not os.path.exists(spooled):
            return None
        mine = os.path.getmtime(spooled)
        # 0.39.3: the helper runs one job at a time; one queued behind a long one (graphs1090, an update) is waiting,
        # not lost: say which one runs and how many are before it, so the page does not blame the helper (the owner's
        # recording, 21 October: "has not taken the job" while graphs1090 was installing)
        ahead = 0
        try:
            for n in os.listdir(SPOOL_DIR):
                if n.endswith(".job") and n != job_id + ".job" and os.path.getmtime(os.path.join(SPOOL_DIR, n)) < mine:
                    ahead += 1
        except OSError:
            pass                                 # the spool changed while it was read: the count is a hint only
        running = [j for j in recent_jobs(10) if j.get("state") == "running" and now() - (j.get("started") or 0) < 7200]
        return {"id": job_id, "state": "queued", "age": int(now() - mine), "log": "", "next": 0, "ahead": ahead,
                "behind": running[0].get("action") if running else None}
    text, nxt = "", offset
    try:
        with open(os.path.join(OUT_DIR, job_id + ".log"), "rb") as fh:
            fh.seek(max(0, int(offset)))
            chunk = fh.read(65536)
            nxt = max(0, int(offset)) + len(chunk)
            text = chunk.decode("utf-8", "replace")
    except (OSError, ValueError):
        pass                                     # no output yet: the helper has not started it
    meta = dict(meta, log=text, next=nxt)
    return meta


def recent_jobs(n=25):
    try:
        names = [x for x in os.listdir(OUT_DIR) if x.endswith(".json") and actions.JOB_ID_RE.match(x[:-5])]
    except OSError:
        return []
    got = [_read_json(os.path.join(OUT_DIR, x)) for x in names]
    got = [g for g in got if isinstance(g, dict)]
    got.sort(key=lambda g: g.get("started") or 0, reverse=True)
    return got[:n]


def tail(path, n):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()[-n:]
    except OSError:
        return []


AUDIT_KEEP = 300


def audit(line):
    log(line)
    path = os.path.join(STATE_DIR, "audit.log")
    lines = tail(path, AUDIT_KEEP - 1) + [time.strftime("%Y-%m-%d %H:%M  ") + line]
    try:
        tmp = path + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        os.replace(tmp, path)
    except OSError:
        pass                                     # the journal line above is the record that matters


def state_writable():
    """Whether the wall's sandbox lets it write its console folder. systemd opens ReadWritePaths only for a folder that
    exists when the service starts (the \"-\" makes a missing one skipped, not an error): a wall started before
    `console on` cannot write it until restarted (seen on the reference Pi, 0.39.0)."""
    return os.access(SPOOL_DIR, os.W_OK) and os.access(STATE_DIR, os.W_OK)


def wizard_done():
    return os.path.exists(os.path.join(STATE_DIR, "wizard-done"))


# --------------------------------------------------------------------------- requests
class Request(object):
    """What handle() needs of an HTTP request; built by the server, or by a test."""

    def __init__(self, method, path, query=None, headers=None, client="127.0.0.1", body=b"", cfg=None):
        self.method, self.path, self.query = method, path, query or {}
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.client, self.body, self.cfg = client, body or b"", cfg or {}

    def cookie(self, name):
        for part in str(self.headers.get("cookie", "")).split(";"):
            k, sep, v = part.strip().partition("=")
            if sep and k == name:
                return v
        return None

    def json(self):
        if "application/json" not in str(self.headers.get("content-type", "")) or len(self.body) > MAX_BODY:
            return None
        try:
            got = json.loads(self.body.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            return None
        return got if isinstance(got, dict) else None

    def q(self, name, default=""):
        v = self.query.get(name)
        return v[0] if isinstance(v, list) and v else (v if isinstance(v, str) else default)


class Reply(object):
    def __init__(self, code, body, ctype="application/json", cookie=None, file=None):
        self.code, self.body, self.ctype, self.file = code, body, ctype, file
        self.headers = dict(SECURITY_HEADERS)
        if cookie is not None:
            self.headers["Set-Cookie"] = cookie


def _cookie(token, max_age):
    return "%s=%s; Path=/console; HttpOnly; SameSite=Strict; Max-Age=%d" % (COOKIE, token, max_age)


def _same_origin(req):
    """A change must come from the console's own page: the browser says where a request comes from."""
    site = req.headers.get("sec-fetch-site")
    if site and site not in ("same-origin", "none"):
        return False
    origin = req.headers.get("origin")
    if origin and origin.split("://", 1)[-1].lower() != str(req.headers.get("host", "")).lower():
        return False
    return True


class Console(object):
    def __init__(self):
        self.sessions = Sessions()
        self.limiter = Limiter()
        self.pairs = Pairs()
        self.approvals = Approvals()

    def enabled(self, cfg):
        return str(cfg.get("CONSOLE", "0")).lower() in ("1", "on", "yes", "true")

    def handle(self, req):
        """-> a Reply for /console..., or None for any other path."""
        if req.path != "/console" and not req.path.startswith("/console/"):
            return None
        if not client_ok(req.client):
            return Reply(403, b"The console answers your home network only.", "text/plain")
        if not host_ok(req.headers.get("host"), req.cfg.get("CONSOLE_HOSTS", "")):
            return Reply(403, b"Open the console by the Pi's address (http://192.168.x.x:8080/console) or its local name.", "text/plain")
        if req.method == "GET" and req.path in ("/console", "/console/"):
            return Reply(200, None, file="console.html")
        if not req.path.startswith("/console/api/"):
            return Reply(404, b"not found", "text/plain")
        api = req.path[len("/console/api/"):]
        on = self.enabled(req.cfg)
        token = req.cookie(COOKIE)
        sess = self.sessions.get(token) if on and token else None
        if api == "session" and req.method == "GET":
            return Reply(200, {"enabled": on, "signed_in": bool(sess), "has_password": has_password(),
                               "kind": sess and sess["kind"], "label": sess and sess["label"], "id": sess and sess["id"],
                               "csrf": sess and sess["csrf"], "wizard_done": wizard_done(), "version": req.cfg.get("_VERSION"),
                               "writable": state_writable() if on else None, "phone_signin": on and phone_signin(req.cfg)})
        if not on:
            return Reply(404, {"error": "off"})
        if req.method == "POST":
            if not _same_origin(req):
                return Reply(403, {"error": "This change did not come from the console's own page."})
            body = req.json()
            if body is None:
                return Reply(400, {"error": "bad request"})
            if api == "login":
                return self._login(req, body)
            if api == "pair/redeem":
                return self._redeem(req, body)
            if api in ("approve/request", "approve/poll"):
                if not phone_signin(req.cfg):
                    return Reply(404, {"error": "Signing in with a phone is off: sudo zenithboard console phone-signin on"})
                if api == "approve/request":
                    got = self.approvals.request(device_label(req.headers.get("user-agent")), req.client)
                    return Reply(200, got) if got else Reply(429, {"error": "Too many sign-in codes from this address. Wait a few minutes."})
                state, v = self.approvals.poll(body.get("id"), body.get("secret"))
                if state != "approved":
                    return Reply(200, {"state": state})
                token, rec = self.sessions.create("approved", v["label"])
                audit("signed in by a phone (%s): %s %s from %s" % (v["by"], v["label"], rec["id"], req.client))
                return Reply(200, {"state": "approved"}, cookie=_cookie(token, PASSWORD_LIFE_S))
            if sess is None:
                return Reply(401, {"error": "signed out"})
            if not hmac.compare_digest(str(req.headers.get("x-zb-csrf", "")), sess["csrf"]):
                return Reply(403, {"error": "This change did not come from the console's own page."})
            return self._post(req, api, body, sess, token)
        if sess is None:
            return Reply(401, {"error": "signed out"})
        return self._get(req, api, sess)

    # -- signing in
    def _login(self, req, body):
        ip = req.client
        wait = self.limiter.wait(ip)
        if wait:
            return Reply(429, {"error": "Too many tries. Wait %d seconds." % wait, "wait": wait})
        stored = secrets_env().get("CONSOLE_PASSWORD_HASH")
        if not stored:
            return Reply(400, {"error": "No console password yet: sudo zenithboard console password (or pair a phone: sudo zenithboard console pair)"})
        if not check_password(str(body.get("password", ""))[:256], stored):
            self.limiter.miss(ip)
            audit("sign-in refused from %s" % ip)
            time.sleep(0.4)
            return Reply(401, {"error": "Wrong password."})
        self.limiter.ok(ip)
        label = device_label(req.headers.get("user-agent"))
        token, rec = self.sessions.create("password", label)
        audit("signed in with the password: %s %s from %s" % (label, rec["id"], ip))
        return Reply(200, {"ok": True}, cookie=_cookie(token, PASSWORD_LIFE_S))

    def _redeem(self, req, body):
        ip = req.client
        wait = self.limiter.wait(ip)
        if wait:
            return Reply(429, {"error": "Too many tries. Wait %d seconds." % wait, "wait": wait})
        label = device_label(req.headers.get("user-agent"))
        if not self.pairs.redeem(body.get("token"), label):
            self.limiter.miss(ip)
            audit("pairing link refused from %s" % ip)
            return Reply(401, {"error": "This pairing code is used or out of date: make a new one (sudo zenithboard console pair). "
                                        "It is valid five minutes, once."})
        token, rec = self.sessions.create("paired", label)
        audit("paired: %s %s from %s" % (label, rec["id"], ip))
        return Reply(200, {"ok": True}, cookie=_cookie(token, PAIRED_LIFE_S))

    # -- signed in
    def _get(self, req, api, sess):
        if api == "state":
            snap = _read_json(os.path.join(OUT_DIR, "state.json")) or {}
            shown = {k: str(req.cfg.get(k, d)) for k, d in SHOWN_KEYS.items()}
            return Reply(200, {"cfg": shown, "facts": snap.get("facts") or {}, "facts_at": snap.get("at"),
                               "catalog": actions.catalog(), "sections": actions.SECTIONS, "now": int(now())})
        if api == "job":
            st = job_status(req.q("id"), int(req.q("from", "0") or 0) if req.q("from", "0").isdigit() else 0)
            return Reply(200, st) if st else Reply(404, {"error": "no such job"})
        if api == "activity":
            return Reply(200, {"jobs": [dict((k, v) for k, v in j.items()) for j in recent_jobs()],
                               "journal": tail(os.path.join(OUT_DIR, "journal.log"), 40)[::-1],
                               "audit": tail(os.path.join(STATE_DIR, "audit.log"), 40)[::-1]})
        if api == "sessions":
            return Reply(200, {"sessions": sorted(self.sessions.listing(), key=lambda r: -r["seen"]), "you": sess["id"]})
        if api == "approve":
            st = self.approvals.info(req.q("id")) if phone_signin(req.cfg) else None
            return Reply(200, st) if st else Reply(404, {"error": "This sign-in code is out of date: the computer shows a new one."})
        if api == "pair":
            st = self.pairs.status(req.q("id"))
            return Reply(200, st) if st else Reply(404, {"error": "no such pairing"})
        return Reply(404, {"error": "not found"})

    def _post(self, req, api, body, sess, token):
        who = "%s %s" % (sess["label"], sess["id"])
        if api == "logout":
            self.sessions.drop(token)
            audit("signed out: %s" % who)
            return Reply(200, {"ok": True}, cookie=_cookie("", 0))
        if api == "run":
            try:
                job = submit(body.get("action"), body.get("params") or {}, who)
            except actions.Refused as e:
                return Reply(400, {"error": "Not allowed here: %s" % e})
            except OSError as e:
                return Reply(503, {"error": "Could not hand the job over (%s). Turn the console on again: sudo zenithboard console on" % e.strerror})
            return Reply(200, {"job": job})
        if api == "pair":
            ptoken, pid = self.pairs.make(who)
            audit("pairing code made by %s" % who)
            return Reply(200, {"token": ptoken, "id": pid, "seconds": PAIR_S})
        if api == "approve":
            yes = body.get("yes") is True
            if not phone_signin(req.cfg) or not self.approvals.answer(body.get("id"), yes, who):
                return Reply(410, {"error": "This sign-in code is out of date or already answered: the computer shows a new one."})
            audit("%s a computer's sign-in: %s" % ("approved" if yes else "refused", who))
            return Reply(200, {"ok": True})
        if api == "sessions/revoke":
            sid = body.get("id")
            n = self.sessions.revoke(keep=sess["id"]) if sid == "others" else self.sessions.revoke(sid=str(sid))
            audit("%d session(s) signed out by %s" % (n, who))
            return Reply(200, {"ok": True, "count": n})
        if api == "wizard":
            try:
                open(os.path.join(STATE_DIR, "wizard-done"), "a").close()
            except OSError:
                pass                             # the wizard comes back next time: harmless
            return Reply(200, {"ok": True})
        return Reply(404, {"error": "not found"})
