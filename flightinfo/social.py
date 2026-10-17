#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Social sharing: post the aircraft overhead to Bluesky, as a picture of the wall.

Off by default. Switched on, this runs as a small service under the wall's own user. Every few seconds it reads
the decoder's aircraft.json and keeps, in memory, the last positions of every aircraft (the track). Every
fifteen seconds it asks the wall itself (on the loopback) which aircraft are inside the sharing radius, with
everything the wall knows about them: airline, model, route, flags. When one of them is worth a post under the
rules the owner chose, and the last post is old enough, it draws the picture and posts it with a short text.
Two looks: the dot-matrix wall with the track drawn in dots (tools/social-render.js, Node), or the split-flap
board beside a map with the track (social_card.py, Pillow; the map from EOX's tile service). No browser, no photo.
The picture lives in /run while it is being sent and is deleted right after, sent or not.

What never leaves the Pi: the receiver's position, the distance and the bearing to the aircraft, the Planespotters
photo, and the account secret (a Bluesky app password), which lives in /etc/zenithboard/social.env
(root:zenithboard, mode 0640) and never in config.env, in a log or on a command line.

    social.py run            the service loop
    social.py test [HEX]     draw the picture and print the text for the best candidate (or HEX); posts nothing
    social.py post [HEX]     post now, once, whatever the gap
    social.py check          try the account: open a session on Bluesky
    social.py status         what it would do right now

Standard library only for the service and the network, like the rest of the wall; Pillow only for the split-flap
look, imported when that look is chosen.
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
    "SOCIAL_AREA": "",               # "Trémery" (read "above Trémery") or "near Metz": the owner's words, never the position
    "SOCIAL_GAP_MIN": "120",         # at least this long between two posts
    "SOCIAL_RULES": "rare,military,helicopter,heavy,farthest",
    "SOCIAL_HASHTAGS": "#ADSB #avgeek #ZenithBoard",
    "SOCIAL_STYLE": "dots",          # the picture: dots (the dot-matrix wall + track) | flap (split-flap board + map)
    "SOCIAL_THEME": "",              # its colour: amber | green | red | white | turquoise | blue; empty = the wall's THEME
    "SOCIAL_MAP": "normal",          # the flap look's map: normal | night | satellite | terrain | none
}
STYLES = ("dots", "flap")
MAPS = ("normal", "night", "satellite", "terrain", "none")
HEAVY = {"A388", "A124", "A225", "B748", "B744", "A337", "A3ST", "BLCF", "C5M", "C17", "A400"}   # worth a post on sight
WARMUP_DAYS = 3                  # "rare" and "farthest" judge against history: none before this much of it
KEEP_PER_TYPE = 4                # the latest distinct aircraft kept per type: enough to tell rare (<= 2 others) from not
RECORD_MIN_KM = 50               # a range record under this is not one
RECORD_RADIUS_KM = 500           # the wall answers out to this; farther than that is a position glitch anyway
RETRY_AFTER_FAIL_S = 600         # a post that failed is not tried again for ten minutes: Bluesky limits sign-ins


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


def bluesky_ready(sec):
    """The account is set up: a handle and its app password. Bluesky is the only network since 0.19.0."""
    return bool(sec.get("BLUESKY_HANDLE") and sec.get("BLUESKY_APP_PASSWORD"))


def style_of(c):
    s = str(c.get("SOCIAL_STYLE", "dots")).strip().lower()
    return s if s in STYLES else "dots"


def map_of(c):
    m = str(c.get("SOCIAL_MAP", "normal")).strip().lower()
    return m if m in MAPS else "normal"


def theme_of(c):
    """The picture's colour: its own setting, else the wall's, else amber."""
    for k in ("SOCIAL_THEME", "THEME"):
        t = str(c.get(k, "") or "").strip().lower()
        if t in server.THEMES:
            return t
    return "amber"


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


def day_of(t):
    return time.strftime("%Y-%m-%d", time.localtime(t))


def prune_state(s, now):
    """What the rules need, and no more:
      types    type code -> {hex: last day seen}, the latest KEEP_PER_TYPE distinct aircraft, thirty days ("rare")
      far      day -> farthest km that day, thirty days ("farthest")
      posted   hex -> time, one day (an aircraft is posted once)
      since    the first day the service watched the sky (no history, no "rare", no "farthest")
    0.18.0 counted a type once per poll instead of once per aircraft; that history is dropped, not converted."""
    cut = day_of(now - 30 * 86400)
    s.setdefault("since", day_of(now))
    types = s.setdefault("types", {})
    for code in list(types):
        seen = types[code]
        if not isinstance(seen, dict) or any(re.match(r"^\d{4}-\d{2}-\d{2}$", str(k)) for k in seen):
            del types[code]                        # the 0.18.0 format: per-day counts of polls, meaningless
            continue
        types[code] = {h: d for h, d in seen.items() if d >= cut}
        if not types[code]:
            del types[code]
    far = s.setdefault("far", {})
    for d in list(far):
        if d < cut:
            del far[d]
    posted = s.setdefault("posted", {})
    for h in list(posted):
        if now - posted[h] > 86400:
            del posted[h]
    s.pop("farthest_day", None); s.pop("farthest_km", None)
    return s


def warmed(state, now):
    """True once the service has watched for WARMUP_DAYS: before that, "rare" and "farthest" mean nothing."""
    try:
        start = time.mktime(time.strptime(state.get("since", day_of(now)), "%Y-%m-%d"))
    except (TypeError, ValueError):
        return False
    return now - start >= WARMUP_DAYS * 86400


def note_types(state, planes, now):
    """Each aircraft once per type: the same aircraft seen at every poll is still one aircraft."""
    day = day_of(now)
    types = state.setdefault("types", {})
    for p in planes:
        code, h = str(p.get("type") or "").upper(), str(p.get("hex") or "").lower()
        if not code or not h:
            continue
        seen = types.setdefault(code, {})
        seen[h] = day
        while len(seen) > KEEP_PER_TYPE:
            del seen[min(seen, key=lambda k: seen[k])]


def others_of_type(state, p, now):
    """How many OTHER aircraft of this type were seen in the last thirty days (at most KEEP_PER_TYPE)."""
    cut = day_of(now - 30 * 86400)
    seen = state.get("types", {}).get(str(p.get("type") or "").upper(), {})
    me = str(p.get("hex") or "").lower()
    return sum(1 for h, d in seen.items() if h != me and d >= cut)


def range_best(state):
    """The farthest of the last thirty days so far, today included."""
    return max([0] + list(state.get("far", {}).values()))


def note_range(state, km, now):
    day = day_of(now)
    far = state.setdefault("far", {})
    if km > far.get(day, 0):
        far[day] = round(km, 1)


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


def ask_wall_one(c, hex_code):
    """Everything the wall knows about one aircraft, wherever it is (out to RECORD_RADIUS_KM)."""
    port = int(server.cfg_float(c, "PORT", 8080))
    url = "http://127.0.0.1:%d/api/planes?radius_km=%d&hex=%s" % (port, RECORD_RADIUS_KM, urllib.parse.quote(str(hex_code).lower()))
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            got = json.load(resp).get("planes") or []
        return got[0] if got else None
    except (urllib.error.URLError, ValueError, OSError):
        return None


def farthest_now(c, aircraft):
    """(hex, km) of the farthest aircraft with a fresh position right now, from the receiver; (None, 0) if none."""
    lat, lon = server.cfg_float(c, "LAT", 0), server.cfg_float(c, "LON", 0)
    if not lat and not lon:
        return None, 0
    best = (None, 0)
    for ac in aircraft or []:
        if "lat" not in ac or "lon" not in ac or ac.get("seen_pos", 0) > 30:
            continue
        h = str(ac.get("hex", "")).lower()
        if not h or h.startswith("~"):
            continue
        d = server.haversine_km(lat, lon, ac["lat"], ac["lon"])
        if RECORD_MIN_KM < d <= RECORD_RADIUS_KM and d > best[1]:
            best = (h, d)
    return best


# --------------------------------------------------------------------------- what is worth a post
def known(p):
    """A post says what the wall knows. Nothing known, nothing to say."""
    return bool(p.get("type_name") or p.get("type") or p.get("registration") or p.get("airline"))


def interest(p, rules, state, now=None):
    """-> (score, reason) for one aircraft under the owner's rules; score 0 = not worth a post."""
    reasons = []
    code = str(p.get("type") or "").upper()
    if "military" in rules and p.get("military"):
        reasons.append(("military", 5))
    if "helicopter" in rules and p.get("shape") == "heli":
        reasons.append(("helicopter", 4))
    if "heavy" in rules and (code in HEAVY or p.get("shape") == "quad"):
        reasons.append(("heavy", 3))
    now = time.time() if now is None else now
    if "rare" in rules and code and warmed(state, now) and others_of_type(state, p, now) <= 2:
        reasons.append(("rare", 3))                # two other aircraft of this type in thirty days, at most
    if "farthest" in rules and p.get("_record"):
        reasons.append(("farthest", 2))            # set by the service: a new thirty-day range record
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
        score, why = interest(p, rules, state, now)
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
        out = []
        for w in words:
            if w == "DE":                           # "DE HAVILLAND" is De Havilland, not DE Havilland
                out.append("De")
            elif w.isupper() and w.isalpha() and len(w) > 3:
                out.append(w.capitalize())
            else:
                out.append(w)
        return " ".join(out)
    return p.get("type") or ""


def place_name(c):
    """The place the owner named, as typed."""
    return re.sub(r"\s+", " ", str(c.get("SOCIAL_AREA", ""))).strip()


def area_words(c):
    """How the post ends. A place name ("Trémery") reads "above Trémery"; words that bring their own preposition
    ("near Metz", "over the Moselle") are kept as typed."""
    area = place_name(c)
    if area and area[0].isupper() and not re.match(r"^(Over|Near|Above|Around|By)\b", area):
        area = "above " + area
    return area


def seen_from(c):
    """For a range record, which is nowhere near overhead: "seen from Trémery". A phrase is left out."""
    area = place_name(c)
    return ("seen from " + area) if area and area[0].isupper() and not re.match(r"^(Over|Near|Above|Around|By)\b", area) else ""


def clock_label(t=None):
    """The time on the picture, with its offset from GMT as the Pi's time zone has it that day: 11:28 GMT+2 in a
    French summer, 10:28 GMT+1 in winter, 05:58 GMT+5:30 in India. Daylight saving is whatever the zone says."""
    lt = time.localtime(t)
    off = int(getattr(lt, "tm_gmtoff", 0) or 0) // 60
    h, m = divmod(abs(off), 60)
    tz = "GMT" if off == 0 else "GMT%s%d%s" % ("+" if off > 0 else "-", h, (":%02d" % m) if m else "")
    return time.strftime("%H:%M", lt) + " " + tz


def hashtag_callsign(flight):
    """An airline callsign (ETD11K) becomes a hashtag, so a flight can be followed; a registration used as a
    callsign (DEABC) stays plain text."""
    return ("#" + flight) if server.CALLSIGN_RE.match(flight or "") else flight


def range_words(km):
    """A range record, said without placing the antenna: rounded DOWN to 50 km ("over 300 km"), never the figure."""
    step = int(km // 50) * 50
    return "over %d km out" % max(step, 50)


def post_text(p, c, why=None, credit=None):
    """The post. English, short, nothing the wall does not know. Starts with the flight ("Flight Etihad #ETD11K"),
    ends with the place ("above Trémery"); a range record ends with where it was seen from instead, since it was
    nowhere near overhead. credit: the map's credit line, when the picture has a map."""
    units = c.get("UNITS", "metric")
    alt = metres(p.get("alt_ft"), units)
    flight = (p.get("flight") or "").strip()
    reg = p.get("registration") or ""
    typ = nice_type(p)
    airline = p.get("airline") or ""
    heli = p.get("shape") == "heli"
    military = bool(p.get("military")) and airline in ("", "MILITARY")
    record = why == "farthest" and p.get("distance_km")
    cs = hashtag_callsign(flight)
    # the head: what this is
    if military:
        head = "Military flight" + (" " + cs if cs else "")
    elif airline and airline != "MILITARY":
        head = "Flight %s %s" % (airline, cs) if cs else "Flight " + airline
    elif heli:
        head = "Helicopter " + (cs or reg) if (cs or reg) else "Helicopter"
    elif cs and cs.replace("-", "") != reg.replace("-", ""):     # a callsign that is not just the registration
        head = "Flight " + cs
    else:
        head = "Aircraft " + reg if reg else "Aircraft"
    parts = [head.strip()]
    # then what it is and where it goes
    if typ:
        parts.append(typ)
    if reg and reg not in head and not (airline and airline != "MILITARY"):
        parts.append(reg)
    r = p.get("route") or {}
    a, b = (r.get("from") or {}), (r.get("to") or {})
    if a.get("city") or a.get("name"):
        parts.append("%s → %s" % (a.get("city") or a.get("name"), b.get("city") or b.get("name") or "?"))
    # and last, where it is. The altitude is said as one ("altitude 8 500 m"): "8 500 m above Trémery" was read as
    # a distance from the place (0.19.0)
    height = ("altitude " + alt) if alt else ""
    if record:
        parts.append(height)
        parts.append(", ".join(x for x in ("range record for 30 days: " + range_words(p["distance_km"]), seen_from(c)) if x))
    else:
        parts.append(height)
        parts.append(area_words(c))
    text = " · ".join(x for x in parts if x)          # starts with the flight itself: no icon in front of it
    tags = str(c.get("SOCIAL_HASHTAGS", "")).strip()
    if heli:
        tags = tags.replace("#avgeek", "#helicopter") if "#avgeek" in tags else tags + " #helicopter"
    if p.get("military"):
        tags = tags.replace("#avgeek", "#military") if "#avgeek" in tags else tags + " #military"
    return "\n".join(x for x in (text, credit or "", tags.strip()) if x)


def alt_text(p, c, trace, look="dots", info=None):
    """For the picture: what a screen reader should say."""
    units = c.get("UNITS", "metric")
    info = info or {}
    bits = ["Split-flap flight board" if look == "flap" else "Dot-matrix flight board"]
    if p.get("flight"):
        bits.append((p.get("flight") or "").strip())
    if p.get("registration") and p["registration"].replace("-", "") != (p.get("flight") or "").strip():
        bits.append("registration " + p["registration"])            # the picture's second row (0.18.3)
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
        bits.append("altitude " + metres(p.get("alt_ft"), units))
    mins = max(1, int(round((trace[-1][3] - trace[0][3]) / 60))) if len(trace) > 1 else 0
    s = "" if mins == 1 else "s"
    if not mins:
        tail = "."
    elif look == "flap" and info.get("map_words"):
        tail = ". Beside it, %s with the aircraft's track over the last %d minute%s, north up." % (info["map_words"], mins, s)
    else:
        tail = ". Beside it, the aircraft's track over the last %d minute%s, north up." % (mins, s)
    if info.get("credit_full"):
        tail += " Map: " + info["credit_full"] + "."
    return ", ".join(bits) + tail


# --------------------------------------------------------------------------- the picture
def _node(spec, out, *extra):
    """Run the dot-matrix renderer (or ask it for the board's rows, --lines). Returns its JSON answer."""
    where = os.path.dirname(out) if out else work_dir()
    fd, spec_path = tempfile.mkstemp(prefix="social-", suffix=".json", dir=where or None)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(spec, fh)
        args = [NODE, RENDERER, spec_path] + ([out] if out else []) + list(extra)
        r = subprocess.run(args, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError("renderer failed: %s" % (r.stderr.strip() or r.stdout.strip()))
        return json.loads(r.stdout.strip() or "{}")
    finally:
        try:
            os.unlink(spec_path)
        except OSError:
            pass


def render(p, trace, c, out_base):
    """Draw the picture in the chosen look. out_base has no extension: .png for dots, .jpg for flap (a map in PNG
    would pass Bluesky's 1,000,000 bytes). Returns {path, mime, width, height, bytes, and for a map: credit, links,
    credit_full, map_words}."""
    look = style_of(c)
    spec = {"plane": p, "trace": trace, "units": c.get("UNITS", "metric"), "theme": theme_of(c),
            "clock": clock_label(), "flags": server.cfg_bool(c, "FLAGS", "1"), "pitch": 10}
    if look == "flap":
        import social_card                       # Pillow: only this look needs it
        got = _node(dict(spec, flags=False, cols=social_card.COLS), None, "--lines")
        out = out_base + ".jpg"
        info = social_card.render(got["lines"], trace, p, out, color=got.get("color", "#ffb000"),
                                  units=spec["units"], map_mode=map_of(c), cache_dir=os.path.join(STATE_DIR, "tiles"))
        info.update(path=out, mime="image/jpeg")
        return info
    out = out_base + ".png"
    info = _node(spec, out)
    info.update(path=out, mime="image/png")
    return info


# --------------------------------------------------------------------------- the network
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


def _byte_span(text, start, end):
    return len(text[:start].encode("utf-8")), len(text[:end].encode("utf-8"))


def bluesky_facets(text, links=None):
    """Hashtags and links as facets, which is how Bluesky makes them clickable. Byte offsets, UTF-8.
    links: [(label, uri)], each label found in the text (the map credit's "maps.eox.at")."""
    facets = []
    for m in re.finditer(r"(?<!\w)#([A-Za-z0-9_]+)", text):
        a, b = _byte_span(text, m.start(), m.end())
        facets.append({"index": {"byteStart": a, "byteEnd": b},
                       "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": m.group(1)}]})
    for label, uri in links or ():
        at = text.find(label)
        if at >= 0 and uri.startswith("https://"):
            a, b = _byte_span(text, at, at + len(label))
            facets.append({"index": {"byteStart": a, "byteEnd": b},
                           "features": [{"$type": "app.bsky.richtext.facet#link", "uri": uri}]})
    return sorted(facets, key=lambda f: f["index"]["byteStart"])


def post_bluesky(sec, text, path, alt, width, height, mime="image/png", links=None):
    ses = bluesky_session(sec)
    auth = {"Authorization": "Bearer " + ses["accessJwt"]}
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) > 1000000:
        raise RuntimeError("picture is %d bytes, Bluesky takes 1,000,000 at most" % len(data))
    blob = _json_request(BLUESKY_PDS + "/xrpc/com.atproto.repo.uploadBlob", data,
                         dict(auth, **{"Content-Type": mime}))["blob"]
    text = text[:300]
    record = {"$type": "app.bsky.feed.post", "text": text, "createdAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
              "langs": ["en"], "facets": bluesky_facets(text, links),
              "embed": {"$type": "app.bsky.embed.images", "images": [{"alt": alt, "image": blob, "aspectRatio": {"width": width, "height": height}}]}}
    out = _json_request(BLUESKY_PDS + "/xrpc/com.atproto.repo.createRecord",
                        {"repo": ses["did"], "collection": "app.bsky.feed.post", "record": record}, auth)
    return out.get("uri", "")


def check_bluesky(sec):
    """'ok, signed in as ...' or 'FAILED: ...'"""
    try:
        ses = bluesky_session(sec)
        return "ok, signed in as %s" % ses.get("handle", sec["BLUESKY_HANDLE"])
    except urllib.error.HTTPError as exc:
        return "FAILED: " + _http_error_text(exc)
    except Exception as exc:
        return "FAILED: %s" % exc


# --------------------------------------------------------------------------- one post, end to end
def work_dir():
    """Where the picture is drawn: /run/zenithboard/social under the service (systemd makes it, in memory); from
    the command line that folder may not exist or not be ours, so a private temporary folder then (0.18.1)."""
    try:
        os.makedirs(RUN_DIR, exist_ok=True)
        if os.access(RUN_DIR, os.W_OK):
            return RUN_DIR
    except OSError:
        pass
    d = tempfile.mkdtemp(prefix="zenithboard-social-")
    return d


def keep_copy(src, keep_base):
    """`social test` keeps the picture as preview.png or preview.jpg, and drops the other one, so /social/preview
    shows the last picture drawn whatever the look."""
    ext = os.path.splitext(src)[1]
    os.makedirs(os.path.dirname(keep_base), exist_ok=True)
    for other in (".png", ".jpg"):
        if other != ext:
            try:
                os.unlink(keep_base + other)
            except OSError:
                pass
    with open(src, "rb") as a, open(keep_base + ext, "wb") as b:
        b.write(a.read())
    return keep_base + ext


def publish(p, trace, why, c, sec, dry=False, keep=None):
    """Draw, post to Bluesky, delete the picture. Returns {"bluesky": uri or 'FAILED ...'} (dry: the text instead)."""
    base = os.path.join(work_dir(), "post-%s" % uuid.uuid4().hex)
    results = {}
    try:
        info = render(p, trace, c, base)
        text = post_text(p, c, why, info.get("credit"))
        alt = alt_text(p, c, trace, style_of(c), info)
        if keep:
            try:
                results["preview"] = keep_copy(info["path"], keep)
            except OSError as exc:
                results["preview_error"] = "could not keep a copy: %s" % exc
        if dry:
            results.update(text=text, alt=alt, bytes=info.get("bytes"), look=style_of(c), map=info.get("map"))
            return results
        try:
            results["bluesky"] = post_bluesky(sec, text, info["path"], alt, info.get("width", 0), info.get("height", 0),
                                              info.get("mime", "image/png"), info.get("links"))
        except urllib.error.HTTPError as exc:
            results["bluesky"] = "FAILED: " + _http_error_text(exc)
        except Exception as exc:
            results["bluesky"] = "FAILED: %s" % exc
        return results
    finally:
        for ext in (".png", ".jpg"):
            try:
                os.unlink(base + ext)
            except OSError:
                pass
        d = os.path.dirname(base)
        if d != RUN_DIR:
            try:
                os.rmdir(d)
            except OSError:
                pass


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


def one_poll(c, state, tracks, aircraft, now):
    """One look at the sky: the candidates under the rules, with the range record among them.
    Returns (planes, best). Notes the types and the day's range AFTER choosing, so an aircraft is never compared
    with a record it set itself (0.18.0 did, and "farthest" could never fire)."""
    radius = server.cfg_float(c, "SOCIAL_RADIUS_KM", 15)
    rules = rules_of(c)
    planes = ask_wall(c, radius)
    far_hex, far_km = farthest_now(c, aircraft)
    if "farthest" in rules and far_hex and warmed(state, now) and far_km > max(RECORD_MIN_KM, range_best(state)):
        rec = next((p for p in planes if p.get("hex") == far_hex), None) or ask_wall_one(c, far_hex)
        if rec:
            rec = dict(rec, _record=True)
            planes = [p for p in planes if p.get("hex") != far_hex] + [rec]
    best = choose(planes, tracks, rules, state, now)
    note_types(state, planes, now)
    if far_km:
        note_range(state, far_km, now)
    return planes, best


def cmd_run():
    tracks = Tracks()
    state = prune_state(load_state(), time.time())
    last_ask, last_summary, last_fail = 0, time.time(), 0
    polls = candidates = 0
    c = cfg()
    sec = secrets()
    print("social: running. Bluesky: %s. Picture: %s. Radius %s km, gap %s min, rules: %s. History since %s%s." % (
        sec.get("BLUESKY_HANDLE") if bluesky_ready(sec) else "NO ACCOUNT (run: sudo zenithboard social setup)", picture_words(c),
        c.get("SOCIAL_RADIUS_KM"), c.get("SOCIAL_GAP_MIN"), ", ".join(sorted(rules_of(c))) or "none",
        state.get("since"), "" if warmed(state, time.time()) else
        " (rare and farthest wait for %d days of it)" % WARMUP_DAYS), flush=True)
    while True:
        now = time.time()
        c = cfg()
        aircraft = read_aircraft(c)
        tracks.feed(aircraft, now)
        if now - last_ask >= ASK_EVERY_S:
            last_ask = now
            prune_state(state, now)
            planes, best = one_poll(c, state, tracks, aircraft, now)
            polls += 1
            candidates += 1 if best else 0
            sec = secrets()
            gap = server.cfg_float(c, "SOCIAL_GAP_MIN", 120) * 60
            # A failed post (Bluesky down, the app password revoked, no picture) waits ten minutes before the next
            # try: before 0.19.0 it was tried again at every look, every fifteen seconds, and each try signs in
            if best and bluesky_ready(sec) and now - state.get("last_post", 0) >= gap and now - last_fail >= RETRY_AFTER_FAIL_S:
                score, why, p = best
                try:
                    results = publish(p, tracks.of(p["hex"]), why, c, sec)
                except Exception as exc:                 # a picture that cannot be drawn must not stop the service
                    results = {"bluesky": "FAILED: %s" % exc}
                ok = not str(results.get("bluesky", "FAILED")).startswith("FAILED")
                print("social: %s %s (%s): %s" % ("posted" if ok else "could not post", p.get("flight") or p.get("hex"), why,
                                                  json.dumps(results)), flush=True)
                if ok:
                    state["last_post"] = now
                    state.setdefault("posted", {})[p["hex"]] = now
                else:
                    last_fail = now
            save_state(state)
        if now - last_summary >= 3600:
            # once an hour, so the journal answers "why no post?" without a line every fifteen seconds
            lp = state.get("last_post")
            wait = max(0, int((lp + server.cfg_float(c, "SOCIAL_GAP_MIN", 120) * 60 - now) / 60)) if lp else 0
            print("social: last hour: %d looks, %d with a candidate under the rules. Last post: %s.%s%s" % (
                polls, candidates, time.strftime("%H:%M", time.localtime(lp)) if lp else "never",
                (" Next possible in %d min." % wait) if wait else "",
                "" if bluesky_ready(secrets()) else " No Bluesky account set up: nothing can be posted."), flush=True)
            last_summary, polls, candidates = now, 0, 0
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
        elif choose(planes, tracks, rules_of(c) | {"any"}, state, now):
            break
        time.sleep(READ_EVERY_S)
    if hex_code:
        for p in planes:
            if p.get("hex") == hex_code.lower():
                return c, state, p, tracks.of(hex_code), "chosen"
        return c, state, None, [], None
    best = choose(planes, tracks, rules_of(c) | {"any"}, state, time.time())
    if not best:
        return c, state, None, [], None
    return c, state, best[2], tracks.of(best[2]["hex"]), best[1]


def cmd_test(hex_code=None):
    c, state, p, trace, why = _collect_once(hex_code)
    if not p:
        print("Nothing to show: no aircraft with a track inside %s km right now (or the wall did not answer)." % c.get("SOCIAL_RADIUS_KM"))
        return 1
    r = publish(p, trace, why, c, {}, dry=True, keep=os.path.join(STATE_DIR, "preview"))
    print("Aircraft: %s %s (%s)" % (p.get("flight") or "", p.get("hex"), p.get("type") or "?"))
    # The test always finds something to show (it adds "any"); say plainly whether the service would post it.
    score, real = interest(p, rules_of(c), state, time.time())
    if real:
        print("Would the service post it? Yes, under the rule '%s'." % real)
    else:
        why_not = "your rules (%s) do not pick it" % (", ".join(sorted(rules_of(c))) or "none")
        if not warmed(state, time.time()) and rules_of(c) & {"rare", "farthest"}:
            why_not += "; 'rare' and 'farthest' wait for %d days of history (since %s)" % (WARMUP_DAYS, state.get("since", "today"))
        print("Would the service post it? No: %s. The test shows it anyway." % why_not)
    print("Picture: %s, %s (%s bytes)" % (picture_words(c), r.get("preview") or r.get("preview_error"), r.get("bytes")))
    if style_of(c) == "flap" and map_of(c) != "none" and r.get("map") == "none":
        print("Map: the tiles could not be fetched (no internet, or the tile service is busy); the track is drawn on black.")
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
    if not bluesky_ready(sec):
        print("No Bluesky account is set up: run  sudo zenithboard social setup")
        return 1
    results = publish(p, trace, why, c, sec)
    print("bluesky: %s" % results.get("bluesky", "?"))
    ok = not str(results.get("bluesky", "FAILED")).startswith("FAILED")
    if ok:
        state["last_post"] = time.time()
        state.setdefault("posted", {})[p["hex"]] = time.time()
        save_state(state)
    return 0 if ok else 1


def cmd_check():
    sec = secrets()
    if not bluesky_ready(sec):
        print("No account configured. Run:  sudo zenithboard social setup")
        return 1
    res = check_bluesky(sec)
    print("bluesky: %s" % res)
    return 1 if res.startswith("FAILED") else 0


def picture_words(c):
    """"dots, amber" or "flap, green, satellite map": what the picture will look like."""
    if style_of(c) == "flap":
        return "flap, %s, %s" % (theme_of(c), "no map" if map_of(c) == "none" else map_of(c) + " map")
    return "dots, %s" % theme_of(c)


def cmd_status():
    c, sec = cfg(), secrets()
    state = load_state()
    print("Social sharing: %s" % ("on" if server.cfg_bool(c, "SOCIAL") else "off"))
    print("Bluesky: %s" % (("@" + sec["BLUESKY_HANDLE"]) if bluesky_ready(sec) else "no account (run: sudo zenithboard social setup)"))
    print("Picture: %s" % picture_words(c))
    print("Radius: %s km   Area: %s   Gap: %s min   Rules: %s" % (c.get("SOCIAL_RADIUS_KM"), c.get("SOCIAL_AREA") or "(none)",
                                                                   c.get("SOCIAL_GAP_MIN"), ", ".join(sorted(rules_of(c))) or "none"))
    print("Hashtags: %s" % c.get("SOCIAL_HASHTAGS"))
    lp = state.get("last_post")
    print("Last post: %s" % (time.strftime("%Y-%m-%d %H:%M", time.localtime(lp)) if lp else "never"))
    now = time.time()
    print("Posted in the last day: %d aircraft   Types noted: %d   Range record (30 days): %s" % (
        len(state.get("posted", {})), len(state.get("types", {})),
        ("%d km" % range_best(state)) if range_best(state) else "none yet"))
    if state.get("since"):
        print("History since %s: %s" % (state["since"], "rare and farthest are active" if warmed(state, now)
                                          else "rare and farthest start after %d days" % WARMUP_DAYS))
    gap = server.cfg_float(c, "SOCIAL_GAP_MIN", 120) * 60
    if lp and now - lp < gap:
        print("Next post possible in %d min (the gap)." % int((lp + gap - now) / 60))
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
