#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Social sharing: post the aircraft overhead to Bluesky and Mastodon, as a picture of the wall.

Off by default. Switched on, this runs as a small service under the wall's own user. Every few seconds it reads
the decoder's aircraft.json and keeps, in memory, the last positions of every aircraft (the track). Every
fifteen seconds it asks the wall itself (on the loopback) which aircraft are inside the sharing radius, with
everything the wall knows about them: airline, model, route, flags. When one of them is worth a post under the
rules the owner chose, and the last post is old enough, it draws the picture (tools/social-render.js: the wall
and the track, no browser, no photo) and posts it with a short text. The picture lives in /run while it is
being sent and is deleted right after, sent or not.

What never leaves the Pi: the receiver's position, the distance and the bearing to the aircraft, the Planespotters
photo, and the account secrets, which live in /etc/zenithboard/social.env (root:zenithboard, mode 0640) and
never in config.env, in a log or on a command line.

    social.py run            the service loop
    social.py test [HEX]     draw the picture and print the text for the best candidate (or HEX); posts nothing
    social.py post [HEX]     post now, once, whatever the gap
    social.py check          try the accounts: a session on Bluesky, verify_credentials on Mastodon
    social.py status         what it would do right now

Standard library only, like the rest of the wall: urllib and json talk to both networks.
"""
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server  # noqa: E402  (config, aircraft.json path, user agent)

SECRETS_FILE = os.environ.get("ZENITHBOARD_SOCIAL_SECRETS", "/etc/zenithboard/social.env")
STATE_DIR = os.environ.get("ZENITHBOARD_SOCIAL_DIR", "/var/lib/zenithboard/social")
RUN_DIR = os.environ.get("ZENITHBOARD_SOCIAL_RUN", "/run/zenithboard/social")
RENDERER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools", "social-render.js")
NODE = os.environ.get("ZENITHBOARD_NODE", "node")

TRACE_SECONDS = 15 * 60          # how much track is kept per aircraft
TRACE_MIN_POINTS = 6             # a post needs at least this much track (30 s at 5 s a sample)
READ_EVERY_S = 5
ASK_EVERY_S = 15
RULES_ALL = ("rare", "military", "helicopter", "heavy", "farthest", "any")
DEFAULTS = {
    "SOCIAL": "0",
    "SOCIAL_RADIUS_KM": "15",
    "SOCIAL_AREA": "",               # "over Luxembourg": the owner's words, never derived from the position
    "SOCIAL_GAP_MIN": "120",         # at least this long between two posts
    "SOCIAL_RULES": "rare,military,helicopter,heavy,farthest",
    "SOCIAL_HASHTAGS": "#ADSB #avgeek #ZenithBoard",
    "SOCIAL_NETWORKS": "",           # "bluesky,mastodon": set by the wizard once an account has passed `check`
}
HEAVY = {"A388", "A124", "A225", "B748", "B744", "A337", "A3ST", "BLCF", "C5M", "C17", "A400"}   # worth a post on sight


# --------------------------------------------------------------------------- settings and secrets
def cfg():
    c = dict(DEFAULTS)
    c.update(server.load_config())
    return c


def secrets():
    try:
        with open(SECRETS_FILE, "r", encoding="utf-8") as fh:
            return server.parse_env_text(fh.read())
    except OSError:
        return {}


def rules_of(c):
    want = {r.strip().lower() for r in str(c.get("SOCIAL_RULES", "")).split(",") if r.strip()}
    return {r for r in want if r in RULES_ALL}


def networks_of(c, sec):
    """The networks that are both chosen and have their secrets."""
    out = []
    chosen = {n.strip().lower() for n in str(c.get("SOCIAL_NETWORKS", "")).split(",")}
    if "bluesky" in chosen and sec.get("BLUESKY_HANDLE") and sec.get("BLUESKY_APP_PASSWORD"):
        out.append("bluesky")
    if "mastodon" in chosen and sec.get("MASTODON_URL") and sec.get("MASTODON_TOKEN"):
        out.append("mastodon")
    return out


# --------------------------------------------------------------------------- state (what was posted, what is rare)
def load_state():
    try:
        with open(os.path.join(STATE_DIR, "state.json"), "r", encoding="utf-8") as fh:
            s = json.load(fh)
            return s if isinstance(s, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(s):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        tmp = os.path.join(STATE_DIR, "state.json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(s, fh)
        os.replace(tmp, os.path.join(STATE_DIR, "state.json"))
    except OSError as exc:
        print("social: cannot save state: %s" % exc, file=sys.stderr, flush=True)


def prune_state(s, now):
    """Thirty days of type sightings (for "rare"), one day of posted aircraft, the farthest of today."""
    day = time.strftime("%Y-%m-%d", time.localtime(now))
    seen = s.setdefault("types", {})               # type code -> [day, count] per day, kept 30 days
    cut = time.strftime("%Y-%m-%d", time.localtime(now - 30 * 86400))
    for code in list(seen):
        seen[code] = {d: n for d, n in seen[code].items() if d >= cut}
        if not seen[code]:
            del seen[code]
    posted = s.setdefault("posted", {})            # hex -> time
    for h in list(posted):
        if now - posted[h] > 86400:
            del posted[h]
    if s.get("farthest_day") != day:
        s["farthest_day"] = day
        s["farthest_km"] = 0
    return s


# --------------------------------------------------------------------------- the track collector
class Tracks(object):
    def __init__(self):
        self.by_hex = {}                           # hex -> list of [lat, lon, alt_ft, t]

    def feed(self, aircraft, now):
        for ac in aircraft or []:
            h = str(ac.get("hex", "")).lower().strip()
            if not h or h.startswith("~") or "lat" not in ac or "lon" not in ac:
                continue
            if ac.get("seen_pos", 0) > 30:
                continue
            alt = ac.get("alt_baro", ac.get("alt_geom"))
            alt = 0 if alt == "ground" else (alt if isinstance(alt, (int, float)) else None)
            pts = self.by_hex.setdefault(h, [])
            if pts and abs(pts[-1][0] - ac["lat"]) < 1e-6 and abs(pts[-1][1] - ac["lon"]) < 1e-6:
                continue                           # the same position again: nothing moved
            pts.append([float(ac["lat"]), float(ac["lon"]), alt, now])
        cut = now - TRACE_SECONDS
        for h in list(self.by_hex):
            self.by_hex[h] = [p for p in self.by_hex[h] if p[3] >= cut]
            if not self.by_hex[h]:
                del self.by_hex[h]

    def of(self, hex_code):
        return list(self.by_hex.get(str(hex_code).lower(), []))


def read_aircraft(c):
    try:
        with open(server.aircraft_json_path(c), "r", encoding="utf-8") as fh:
            return json.load(fh).get("aircraft") or []
    except (OSError, ValueError):
        return []


def ask_wall(c, radius_km):
    """The wall's own answer: everything it knows about the aircraft inside the radius."""
    port = int(server.cfg_float(c, "PORT", 8080))
    url = "http://127.0.0.1:%d/api/planes?radius_km=%.3f" % (port, radius_km)
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.load(resp).get("planes") or []
    except (urllib.error.URLError, ValueError, OSError) as exc:
        print("social: the wall did not answer (%s)" % exc, file=sys.stderr, flush=True)
        return []


# --------------------------------------------------------------------------- what is worth a post
def known(p):
    """A post says what the wall knows. Nothing known, nothing to say."""
    return bool(p.get("type_name") or p.get("type") or p.get("registration") or p.get("airline"))


def interest(p, rules, state):
    """-> (score, reason) for one aircraft under the owner's rules; score 0 = not worth a post."""
    reasons = []
    code = str(p.get("type") or "").upper()
    if "military" in rules and p.get("military"):
        reasons.append(("military", 5))
    if "helicopter" in rules and p.get("shape") == "heli":
        reasons.append(("helicopter", 4))
    if "heavy" in rules and (code in HEAVY or p.get("shape") == "quad"):
        reasons.append(("heavy", 3))
    if "rare" in rules and code:
        days = state.get("types", {}).get(code, {})
        if sum(days.values()) <= 2:                # seen twice or less in thirty days, this one included
            reasons.append(("rare", 3))
    if "farthest" in rules and p.get("distance_km", 0) > max(50, state.get("farthest_km", 0)):
        reasons.append(("farthest", 2))
    if "any" in rules:
        reasons.append(("any", 1))
    if not reasons:
        return 0, None
    reasons.sort(key=lambda r: -r[1])
    return sum(r[1] for r in reasons), reasons[0][0]


def choose(planes, tracks, rules, state, now):
    """The best candidate right now, or None."""
    best = None
    for p in planes:
        if not known(p) or p.get("on_ground"):
            continue
        if p.get("hex") in state.get("posted", {}):
            continue
        if len(tracks.of(p.get("hex"))) < TRACE_MIN_POINTS:
            continue
        score, why = interest(p, rules, state)
        if score <= 0:
            continue
        # more is known about it = a better post: route, airline, model each count a little
        score += (1 if p.get("route") else 0) + (1 if p.get("airline") else 0) + (1 if p.get("type_name") else 0)
        if best is None or score > best[0]:
            best = (score, why, p)
    return best


# --------------------------------------------------------------------------- the words
def metres(alt_ft, units):
    if alt_ft is None:
        return None
    if units == "imperial":
        return "{:,} ft".format(int(round(alt_ft / 100.0) * 100)).replace(",", " ")
    return "{:,} m".format(int(round(alt_ft * 0.3048 / 10.0) * 10)).replace(",", " ")


def nice_type(p):
    name = p.get("type_name") or ""
    if name:
        # "AIRBUS A-320neo" -> "Airbus A320neo"; the list writes makers in capitals and models with a dash
        name = re.sub(r"\bA-(\d)", r"A\1", name)
        words = name.split()
        # makers are written in capitals (AIRBUS, BOEING, HELICOPTERS); model codes keep their letters (KC-135R, A320neo)
        return " ".join(w.capitalize() if w.isupper() and w.isalpha() and len(w) > 3 else w for w in words)
    return p.get("type") or ""


def post_text(p, c, why=None):
    """The post. English, short, nothing the wall does not know."""
    units = c.get("UNITS", "metric")
    area = str(c.get("SOCIAL_AREA", "")).strip()
    where = (" " + area) if area else ""
    alt = metres(p.get("alt_ft"), units)
    flight = (p.get("flight") or "").strip()
    reg = p.get("registration") or ""
    typ = nice_type(p)
    airline = p.get("airline") or ""
    heli = p.get("shape") == "heli"
    icon = "🚁" if heli else "✈"
    parts = []
    if p.get("military") and airline in ("", "MILITARY"):
        parts.append("Military")
        if typ:
            parts.append(typ)
        if flight:
            parts.append(flight)
    elif airline and airline != "MILITARY":
        parts.append((airline + " " + flight).strip())
        if typ:
            parts.append(typ)
        r = p.get("route") or {}
        a, b = (r.get("from") or {}), (r.get("to") or {})
        if a.get("city") or a.get("name"):
            parts.append("%s → %s" % (a.get("city") or a.get("name"), b.get("city") or b.get("name") or "?"))
    else:
        if typ:
            parts.append(typ)
        if reg:
            parts.append(reg)
        if flight and flight != reg:
            parts.append(flight)
    if heli:
        parts.append("low%s" % where if (p.get("alt_ft") or 0) < 3000 else "%s%s" % (alt or "", where))
    elif alt:
        parts.append("%s%s" % (alt, where))
    elif where:
        parts.append(where.strip())
    if why == "farthest" and p.get("distance_km"):
        parts.append("%d km out — farthest today" % round(p["distance_km"]))
    text = icon + " " + " · ".join(x for x in parts if x)
    tags = str(c.get("SOCIAL_HASHTAGS", "")).strip()
    if heli:
        tags = tags.replace("#avgeek", "#helicopter") if "#avgeek" in tags else tags + " #helicopter"
    if p.get("military"):
        tags = tags.replace("#avgeek", "#military") if "#avgeek" in tags else tags + " #military"
    return (text + "\n" + tags).strip() if tags else text


def alt_text(p, c, trace):
    """For the picture: what a screen reader should say."""
    units = c.get("UNITS", "metric")
    bits = ["Dot-matrix flight board"]
    if p.get("flight"):
        bits.append((p.get("flight") or "").strip())
    if p.get("airline") and p["airline"] != "MILITARY":
        bits.append(p["airline"])
    if p.get("military"):
        bits.append("military")
    if nice_type(p):
        bits.append(nice_type(p))
    r = p.get("route") or {}
    if r.get("from") and r.get("to"):
        bits.append("from %s to %s" % ((r["from"].get("city") or r["from"].get("name")), (r["to"].get("city") or r["to"].get("name"))))
    if metres(p.get("alt_ft"), units):
        bits.append(metres(p.get("alt_ft"), units))
    mins = max(1, int(round((trace[-1][3] - trace[0][3]) / 60))) if len(trace) > 1 else 0
    tail = (". Beside it, the aircraft's track over the last %d minute%s, north up." % (mins, "" if mins == 1 else "s")) if mins else "."
    return ", ".join(bits) + tail


# --------------------------------------------------------------------------- the picture
def render(p, trace, c, out_png):
    spec = {"plane": p, "trace": trace, "units": c.get("UNITS", "metric"), "theme": c.get("THEME", "amber"),
            "clock": time.strftime("%H:%M"), "flags": server.cfg_bool(c, "FLAGS", "1"), "pitch": 10}
    fd, spec_path = tempfile.mkstemp(prefix="social-", suffix=".json", dir=os.path.dirname(out_png) or None)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(spec, fh)
        r = subprocess.run([NODE, RENDERER, spec_path, out_png], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError("renderer failed: %s" % (r.stderr.strip() or r.stdout.strip()))
        return json.loads(r.stdout.strip() or "{}")
    finally:
        try:
            os.unlink(spec_path)
        except OSError:
            pass


# --------------------------------------------------------------------------- the networks
def _json_request(url, data=None, headers=None, method=None, timeout=30):
    body = None if data is None else (data if isinstance(data, bytes) else json.dumps(data).encode("utf-8"))
    hdr = {"User-Agent": server.USER_AGENT}
    if data is not None and not isinstance(data, bytes):
        hdr["Content-Type"] = "application/json"
    hdr.update(headers or {})
    req = urllib.request.Request(url, data=body, headers=hdr, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw.decode("utf-8")) if raw else {}


def _http_error_text(exc):
    try:
        return "%s %s" % (exc.code, exc.read().decode("utf-8", "replace")[:300])
    except Exception:
        return str(exc)


BLUESKY_PDS = "https://bsky.social"


def bluesky_session(sec):
    return _json_request(BLUESKY_PDS + "/xrpc/com.atproto.server.createSession",
                         {"identifier": sec["BLUESKY_HANDLE"], "password": sec["BLUESKY_APP_PASSWORD"]})


def bluesky_facets(text):
    """Hashtags as facets, which is how Bluesky makes them clickable. Byte offsets, UTF-8."""
    facets = []
    for m in re.finditer(r"(?<!\w)#([A-Za-z0-9_]+)", text):
        start = len(text[:m.start()].encode("utf-8"))
        end = start + len(m.group(0).encode("utf-8"))
        facets.append({"index": {"byteStart": start, "byteEnd": end},
                       "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": m.group(1)}]})
    return facets


def post_bluesky(sec, text, png_path, alt, width, height):
    ses = bluesky_session(sec)
    auth = {"Authorization": "Bearer " + ses["accessJwt"]}
    with open(png_path, "rb") as fh:
        data = fh.read()
    if len(data) > 1000000:
        raise RuntimeError("picture is %d bytes, Bluesky takes 1,000,000 at most" % len(data))
    blob = _json_request(BLUESKY_PDS + "/xrpc/com.atproto.repo.uploadBlob", data,
                         dict(auth, **{"Content-Type": "image/png"}))["blob"]
    record = {"$type": "app.bsky.feed.post", "text": text[:300], "createdAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
              "langs": ["en"], "facets": bluesky_facets(text[:300]),
              "embed": {"$type": "app.bsky.embed.images", "images": [{"alt": alt, "image": blob, "aspectRatio": {"width": width, "height": height}}]}}
    out = _json_request(BLUESKY_PDS + "/xrpc/com.atproto.repo.createRecord",
                        {"repo": ses["did"], "collection": "app.bsky.feed.post", "record": record}, auth)
    return out.get("uri", "")


def _multipart(fields, file_field, filename, content, content_type):
    boundary = "----zenithboard" + uuid.uuid4().hex
    body = b""
    for k, v in fields.items():
        body += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (boundary, k, v)).encode("utf-8")
    body += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n"
             % (boundary, file_field, filename, content_type)).encode("utf-8") + content + b"\r\n"
    body += ("--%s--\r\n" % boundary).encode("utf-8")
    return body, "multipart/form-data; boundary=" + boundary


def post_mastodon(sec, text, png_path, alt):
    base = sec["MASTODON_URL"].rstrip("/")
    auth = {"Authorization": "Bearer " + sec["MASTODON_TOKEN"]}
    with open(png_path, "rb") as fh:
        data = fh.read()
    body, ctype = _multipart({"description": alt[:1500]}, "file", "zenithboard.png", data, "image/png")
    media = _json_request(base + "/api/v2/media", body, dict(auth, **{"Content-Type": ctype}))
    media_id = media.get("id")
    if not media_id:
        raise RuntimeError("Mastodon did not return a media id")
    # 202 = still processing (videos mostly); an image is usually ready at once. Ask a few times to be sure.
    for _ in range(10):
        try:
            got = _json_request(base + "/api/v1/media/%s" % media_id, headers=auth)
            if got.get("url"):
                break
        except urllib.error.HTTPError as exc:
            if exc.code != 206:
                raise
        time.sleep(1)
    out = _json_request(base + "/api/v1/statuses", {"status": text[:500], "media_ids": [media_id], "visibility": "public", "language": "en"},
                        dict(auth, **{"Idempotency-Key": uuid.uuid4().hex}))
    return out.get("url", "")


def check_accounts(sec, networks):
    """-> {network: 'ok ...' | 'FAILED ...'}"""
    out = {}
    if "bluesky" in networks:
        try:
            ses = bluesky_session(sec)
            out["bluesky"] = "ok, signed in as %s" % ses.get("handle", sec["BLUESKY_HANDLE"])
        except urllib.error.HTTPError as exc:
            out["bluesky"] = "FAILED: " + _http_error_text(exc)
        except Exception as exc:
            out["bluesky"] = "FAILED: %s" % exc
    if "mastodon" in networks:
        try:
            me = _json_request(sec["MASTODON_URL"].rstrip("/") + "/api/v1/accounts/verify_credentials",
                               headers={"Authorization": "Bearer " + sec["MASTODON_TOKEN"]})
            out["mastodon"] = "ok, signed in as @%s" % me.get("acct", "?")
        except urllib.error.HTTPError as exc:
            out["mastodon"] = "FAILED: " + _http_error_text(exc)
        except Exception as exc:
            out["mastodon"] = "FAILED: %s" % exc
    return out


# --------------------------------------------------------------------------- one post, end to end
def publish(p, trace, why, c, sec, networks, dry=False, keep_png=None):
    """Draw, post everywhere chosen, delete the picture. Returns {network: url or error}."""
    os.makedirs(RUN_DIR, exist_ok=True)
    png = os.path.join(RUN_DIR, "post-%s.png" % uuid.uuid4().hex)
    results = {}
    try:
        info = render(p, trace, c, png)
        text, alt = post_text(p, c, why), alt_text(p, c, trace)
        if keep_png:
            try:
                os.makedirs(os.path.dirname(keep_png), exist_ok=True)
                with open(png, "rb") as src, open(keep_png, "wb") as dst:
                    dst.write(src.read())
            except OSError as exc:
                results["preview"] = "could not keep a copy: %s" % exc
        if dry:
            results["text"], results["alt"], results["bytes"] = text, alt, info.get("bytes")
            return results
        for net in networks:
            try:
                if net == "bluesky":
                    results[net] = post_bluesky(sec, text, png, alt, info.get("width", 0), info.get("height", 0))
                elif net == "mastodon":
                    results[net] = post_mastodon(sec, text, png, alt)
            except urllib.error.HTTPError as exc:
                results[net] = "FAILED: " + _http_error_text(exc)
            except Exception as exc:
                results[net] = "FAILED: %s" % exc
        return results
    finally:
        try:
            os.unlink(png)
        except OSError:
            pass


def note_types(state, planes, now):
    day = time.strftime("%Y-%m-%d", time.localtime(now))
    types = state.setdefault("types", {})
    for p in planes:
        code = str(p.get("type") or "").upper()
        if code:
            types.setdefault(code, {})
            types[code][day] = types[code].get(day, 0) + 1
        d = p.get("distance_km") or 0
        if d > state.get("farthest_km", 0):
            state["farthest_km"] = d


# --------------------------------------------------------------------------- commands
def local_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "PI-ADDRESS"


def cmd_run():
    tracks = Tracks()
    state = prune_state(load_state(), time.time())
    last_ask = 0
    print("social: running", flush=True)
    while True:
        now = time.time()
        c = cfg()
        tracks.feed(read_aircraft(c), now)
        if now - last_ask >= ASK_EVERY_S:
            last_ask = now
            radius = server.cfg_float(c, "SOCIAL_RADIUS_KM", 15)
            planes = ask_wall(c, radius)
            note_types(state, planes, now)
            prune_state(state, now)
            sec = secrets()
            networks = networks_of(c, sec)
            gap = server.cfg_float(c, "SOCIAL_GAP_MIN", 120) * 60
            if networks and now - state.get("last_post", 0) >= gap:
                best = choose(planes, tracks, rules_of(c), state, now)
                if best:
                    score, why, p = best
                    results = publish(p, tracks.of(p["hex"]), why, c, sec, networks)
                    ok = [n for n in networks if not str(results.get(n, "")).startswith("FAILED")]
                    print("social: posted %s (%s, %s): %s" % (p.get("flight") or p.get("hex"), why, ", ".join(ok) or "nowhere",
                                                               json.dumps(results)), flush=True)
                    if ok:
                        state["last_post"] = now
                        state.setdefault("posted", {})[p["hex"]] = now
            save_state(state)
        time.sleep(READ_EVERY_S)


def _collect_once(hex_code=None, seconds=35):
    """For test/post: gather a short track now, ask the wall, pick the aircraft."""
    c = cfg()
    tracks = Tracks()
    state = prune_state(load_state(), time.time())
    radius = server.cfg_float(c, "SOCIAL_RADIUS_KM", 15)
    deadline = time.time() + seconds
    planes = []
    while time.time() < deadline:
        now = time.time()
        tracks.feed(read_aircraft(c), now)
        planes = ask_wall(c, radius)
        if hex_code:
            if any(p.get("hex") == hex_code.lower() for p in planes) and len(tracks.of(hex_code)) >= TRACE_MIN_POINTS:
                break
        elif choose(planes, tracks, rules_of(c) | {"any"}, {"types": state.get("types", {})}, now):
            break
        time.sleep(READ_EVERY_S)
    if hex_code:
        for p in planes:
            if p.get("hex") == hex_code.lower():
                return c, state, p, tracks.of(hex_code), "chosen"
        return c, state, None, [], None
    best = choose(planes, tracks, rules_of(c) | {"any"}, {"types": state.get("types", {})}, time.time())
    if not best:
        return c, state, None, [], None
    return c, state, best[2], tracks.of(best[2]["hex"]), best[1]


def cmd_test(hex_code=None):
    c, state, p, trace, why = _collect_once(hex_code)
    if not p:
        print("Nothing to show: no aircraft with a track inside %s km right now (or the wall did not answer)." % c.get("SOCIAL_RADIUS_KM"))
        return 1
    preview = os.path.join(STATE_DIR, "preview.png")
    r = publish(p, trace, why, c, {}, [], dry=True, keep_png=preview)
    print("Aircraft: %s %s (%s)  rule: %s" % (p.get("flight") or "", p.get("hex"), p.get("type") or "?", why))
    print("Picture: %s (%s bytes)" % (preview, r.get("bytes")))
    port = int(server.cfg_float(c, "PORT", 8080))
    print("See it:  http://%s:%d/social/preview" % (local_ip(), port))
    print("Text:")
    print("  " + r["text"].replace("\n", "\n  "))
    print("Alt text: " + r["alt"])
    return 0


def cmd_post(hex_code=None):
    c, state, p, trace, why = _collect_once(hex_code)
    if not p:
        print("Nothing to post: no aircraft with a track inside %s km right now." % c.get("SOCIAL_RADIUS_KM"))
        return 1
    sec = secrets()
    networks = networks_of(c, sec)
    if not networks:
        print("No network is set up: run  sudo zenithboard social setup")
        return 1
    results = publish(p, trace, why, c, sec, networks)
    for net in networks:
        print("%s: %s" % (net, results.get(net, "?")))
    ok = [n for n in networks if not str(results.get(n, "")).startswith("FAILED")]
    if ok:
        state["last_post"] = time.time()
        state.setdefault("posted", {})[p["hex"]] = time.time()
        save_state(state)
    return 0 if ok else 1


def cmd_check():
    c, sec = cfg(), secrets()
    chosen = [n for n in ("bluesky", "mastodon") if n in str(c.get("SOCIAL_NETWORKS", "")).lower() or
              (n == "bluesky" and sec.get("BLUESKY_HANDLE")) or (n == "mastodon" and sec.get("MASTODON_URL"))]
    if not chosen:
        print("No account configured. Run:  sudo zenithboard social setup")
        return 1
    res = check_accounts(sec, chosen)
    for n in chosen:
        print("%s: %s" % (n, res.get(n, "not configured")))
    return 0 if all(not v.startswith("FAILED") for v in res.values()) else 1


def cmd_status():
    c, sec = cfg(), secrets()
    state = load_state()
    nets = networks_of(c, sec)
    print("Social sharing: %s" % ("on" if server.cfg_bool(c, "SOCIAL") else "off"))
    print("Networks ready: %s" % (", ".join(nets) or "none (run: sudo zenithboard social setup)"))
    print("Radius: %s km   Area: %s   Gap: %s min   Rules: %s" % (c.get("SOCIAL_RADIUS_KM"), c.get("SOCIAL_AREA") or "(none)",
                                                                   c.get("SOCIAL_GAP_MIN"), ", ".join(sorted(rules_of(c))) or "none"))
    print("Hashtags: %s" % c.get("SOCIAL_HASHTAGS"))
    lp = state.get("last_post")
    print("Last post: %s" % (time.strftime("%Y-%m-%d %H:%M", time.localtime(lp)) if lp else "never"))
    print("Posted today: %d aircraft   Types noted: %d" % (len(state.get("posted", {})), len(state.get("types", {}))))
    return 0


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "status"
    arg = argv[2] if len(argv) > 2 else None
    if cmd == "run":
        return cmd_run()
    if cmd == "test":
        return cmd_test(arg)
    if cmd == "post":
        return cmd_post(arg)
    if cmd == "check":
        return cmd_check()
    if cmd == "status":
        return cmd_status()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
