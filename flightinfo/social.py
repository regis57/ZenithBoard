#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Social sharing: post the aircraft overhead to Bluesky, as a picture of the wall.

Off by default. Switched on, this runs as a small service under the wall's own user. Every few seconds it reads
the decoder's aircraft.json and keeps, in memory, the last positions of every aircraft (the track). Every
fifteen seconds it asks the wall itself (on the loopback) which aircraft are inside the sharing radius, with
everything the wall knows about them: airline, model, route, flags. When one of them is worth a post under the
rules the owner chose, and the last post is old enough, it draws the picture and posts it with a short text.
Two looks, each with a map of the track: the dot-matrix wall (tools/social-render.js, Node, draws the dots;
social_card.py, Pillow, lays the map beside them) or the split-flap board (social_card.py), the map from EOX's tile
service; or the two in turn. No browser, no photo.
The picture lives in /run while it is being sent and is deleted right after, sent or not.

What never leaves the Pi: the receiver's position, the distance and the bearing to the aircraft, the Planespotters
photo, and the account secret (a Bluesky app password), which lives in /etc/zenithboard/social.env
(root:zenithboard, mode 0640) and never in config.env, in a log or on a command line.

    social.py run            the service loop
    social.py test [HEX]     draw the picture and print the text for the best candidate (or HEX); posts nothing
    social.py post [HEX]     post now, once, whatever the gap
    social.py check          try the account: open a session on Bluesky
    social.py week-test      draw the week's summary and print its text; posts nothing (0.33.0)
    social.py week-post      post the week's summary now
    social.py week-post2     post the week's second post now: cargo airlines and business jets (0.35.0)
    social.py week-post3     the third: military aircraft (0.36.0)
    social.py week-post4     the fourth: helicopters, light aircraft, gliders, drones and balloons (0.36.0)
    social.py summary-test PERIOD          the four posts of the daily, weekly or monthly summary; posts nothing (0.38.0)
    social.py summary-when                 each summary: when it last went out, when it goes next; the queue (0.48.0)
    social.py summary-post PERIOD [N]      post N (1 to 4) of that summary now
    social.py status         what it would do right now

Standard library only for the service and the network, like the rest of the wall; Pillow only for the looks with a
map (dotmap, flap), imported when one of them is chosen.
"""
import datetime
import gzip
import json
import os
import random
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
SETTLE_S = 120                   # an aircraft whose route or model the wall is still looking up waits up to this long
READ_EVERY_S = 5
ASK_EVERY_S = 15
RULES_ALL = ("rare", "military", "helicopter", "heavy", "farthest", "all")   # "all" was "any" until 0.19.1
DEFAULTS = {
    "SOCIAL": "0",
    "SOCIAL_RADIUS_KM": "15",
    "SOCIAL_AREA": "",               # "Trémery" (read "above Trémery") or "near Metz": the owner's words, never the position
    "SOCIAL_GAP_MIN": "0",           # at least this long between two posts; 0 = none: every crossing is posted (0.20.0)
    "SOCIAL_RULES": "rare,military,helicopter,heavy,farthest",
    "SOCIAL_HASHTAGS": "#ADSB #avgeek #ZenithBoard",
    "SOCIAL_SENTENCE": "factual",     # 0.29.0: factual | story | board | spotter | lookup, several (a,b) or random
    "SOCIAL_STYLE": "dotmap",        # the picture: dotmap (dot-matrix wall + map) | flap (split-flap + map) | alternate
    "SOCIAL_THEME": "",              # its colour: amber | green | red | white | turquoise; empty = the wall's THEME
    "SOCIAL_UNITS": "",              # metric | imperial; empty = the wall's UNITS (0.24.3)
    "SOCIAL_MAP": "normal",
    "SOCIAL_PLACES": "0",            # 1: the town names from the region's own list (0.27.0, social places on)
    "SOCIAL_WEEKLY": "0",            # 1: a summary of the week on Sundays from 19:00 (0.33.0, social weekly on)
    "SOCIAL_WEEKLY_AT": "sun 19:00",  # 0.38.0: its day and time, and the posts it makes (1 the week, 2 cargo and
    "SOCIAL_WEEKLY_PARTS": "1,2,3,4",  # business jets, 3 military, 4 general aviation)
    "SOCIAL_DAILY": "0", "SOCIAL_DAILY_AT": "21:00", "SOCIAL_DAILY_PARTS": "1",               # the last 24 hours
    "SOCIAL_MONTHLY": "0", "SOCIAL_MONTHLY_AT": "1 09:00", "SOCIAL_MONTHLY_PARTS": "1,2,3,4",  # the last 30 days
    "SOCIAL_PHOTOLINK": "0",         # 1: a last line linking to the aircraft's Planespotters photo page (0.25.0)          # the map of the dotmap and flap looks: normal | night | satellite | terrain | none
}
STYLES = ("dotmap", "flap")
MAP_LOOKS = STYLES               # every look carries a map (0.24.0)
MAPS = ("normal", "night", "satellite", "terrain", "none")
# 0.19.5, optional: vary the posts. "alternate" takes the looks in turn, "rotate" the wall's colours, and the four
# maps (not "none"), one step per post. Off by default; a fixed look, colour and map stay as they are.
# 0.23.0: "alternate" is the two looks with a map, the dot-matrix wall and the split-flap board, asked for by the
# owner: the dots-only track, a map drawn in dots, left the turn. 0.24.0: it left the choices too, at the owner's
# word; a setting still on "dots" is read as dotmap, and the update says so. Node still draws it when Pillow is
# missing, rather than no picture.
# The wall's dark blue went the same day, from the wall and from the posts: it read poorly on a phone, and a blue
# track on the satellite map nearly disappeared. Turquoise stays.
STYLE_CHOICES = STYLES + ("alternate",)
ALTERNATE = ("dotmap", "flap")
MAP_CHOICES = MAPS + ("rotate",)
ROTATE_MAPS = ("normal", "night", "satellite", "terrain")
ROTATE_THEMES = tuple(server.THEMES)
HEAVY = {"A388", "A124", "A225", "B748", "B744", "A337", "A3ST", "BLCF", "C5M", "C17", "A400"}   # worth a post on sight
WARMUP_DAYS = 3                  # "rare" and "farthest" judge against history: none before this much of it
KEEP_PER_TYPE = 4                # the latest distinct aircraft kept per type: enough to tell rare (<= 2 others) from not
RECORD_MIN_KM = 50               # a range record under this is not one
RECORD_RADIUS_KM = 500           # the wall answers out to this; farther than that is a position glitch anyway
LATE_S = 600                     # an aircraft that left the radius before it could be posted (its route still being looked
                                 # up, another one posted first) is still posted this long after: every crossing counts
LATE_ASKS = 6                    # at most this many of those asked about per look, to keep the Pi light
CROSSING_GAP_S = 3600            # one crossing ends when the aircraft has been outside the sharing radius this long:
                                 # back inside sooner, it is the same crossing and is not posted again (0.20.0)
SECOND_AFTER_S = 120              # 0.35.0: the week's second post (cargo, business jets) follows the first this long after
SECOND_LATE_S = 4 * 3600          # and is dropped when it could not go out within this long
RETRY_AFTER_FAIL_S = 600         # a post that failed is not tried again for ten minutes: Bluesky limits sign-ins


# --------------------------------------------------------------------------- settings and secrets
def cfg():
    c = dict(DEFAULTS)
    c.update(server.load_config())
    return c


def account():
    """The Bluesky account from social.env: the handle (public, the account's name) and its app password."""
    try:
        with open(SECRETS_FILE, "r", encoding="utf-8") as fh:
            return server.parse_env_text(fh.read())
    except OSError:
        return {}


def rules_of(c):
    """The rules chosen. "all" (or "any", its name before 0.19.1) means everything that flies over, the special
    aircraft included: so it brings every other rule with it, and a military aircraft under "all" is posted as
    military, ahead of an airliner, not as "anything"."""
    want = {r.strip().lower() for r in str(c.get("SOCIAL_RULES", "")).split(",") if r.strip()}
    if want & {"all", "any"}:
        return set(RULES_ALL)
    return {r for r in want if r in RULES_ALL}


def bluesky_ready(sec):
    """The account is set up: a handle and its app password. Bluesky is the only network since 0.19.0."""
    return bool(sec.get("BLUESKY_HANDLE") and sec.get("BLUESKY_APP_PASSWORD"))


def gap_min(c):
    """The minutes between two posts: the setting, 0 for none. 0.19.3 to 0.19.10 never went under ten minutes; the
    owner wants the feed to be every crossing, uncapped, so there is no floor any more (0.20.0)."""
    return max(0.0, server.cfg_float(c, "SOCIAL_GAP_MIN", 0))


def gap_words(c):
    return "none (every crossing is posted)" if gap_min(c) <= 0 else "%g min" % gap_min(c)


def picture_for(c, n):
    """The settings with "alternate" and "rotate" turned into this post's look, colour and map. n = posts made so
    far. Five colours against two looks: over ten posts each look meets each colour; alternating, the map moves on
    every second post, so over eight posts each look meets each of the four maps."""
    out = dict(c)
    style = str(c.get("SOCIAL_STYLE", "dotmap")).strip().lower()
    alternate = style == "alternate"
    if alternate:
        out["SOCIAL_STYLE"] = ALTERNATE[n % len(ALTERNATE)]
    if str(c.get("SOCIAL_THEME", "")).strip().lower() == "rotate":
        out["SOCIAL_THEME"] = ROTATE_THEMES[n % len(ROTATE_THEMES)]
    if str(c.get("SOCIAL_MAP", "")).strip().lower() == "rotate":
        k = n // 2 if alternate else n                  # alternating: the map moves on after each pair of looks
        out["SOCIAL_MAP"] = ROTATE_MAPS[k % len(ROTATE_MAPS)]
    return out


def varies(c):
    return (str(c.get("SOCIAL_STYLE", "")).lower() == "alternate" or str(c.get("SOCIAL_THEME", "")).lower() == "rotate"
            or str(c.get("SOCIAL_MAP", "")).lower() == "rotate")


def style_of(c):
    s = str(c.get("SOCIAL_STYLE", "dotmap")).strip().lower()
    return s if s in STYLES else "dotmap"          # "dots", taken out in 0.24.0, included


def map_of(c):
    m = str(c.get("SOCIAL_MAP", "normal")).strip().lower()
    return m if m in MAPS else "normal"


def units_of(c):
    """The posts' units: their own setting (0.24.3), else the wall's UNITS, else metric."""
    for k in ("SOCIAL_UNITS", "UNITS"):
        u = str(c.get(k, "") or "").strip().lower()
        if u in ("metric", "imperial"):
            return u
    return "metric"


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


def memory_mb():
    """The service's own memory, in MB: {now, peak, node, since}. Measured by the process itself, because
    `systemctl status` cannot: Raspberry Pi OS boots with the kernel's memory controller off (cgroup_disable=memory),
    so systemd shows no Memory line and does not enforce MemoryMax either (seen on the real Pi, 0.19.4).
    peak is Python's (Pillow draws in it), node the largest drawing by Node, as Node itself reports it: from outside,
    the kernel credits a child started by vfork with the parent's peak, so RUSAGE_CHILDREN said "Node 104 MB" when
    104 MB was Python's (0.19.10, seen on the real Pi)."""
    import resource
    now = 0.0
    try:
        with open("/proc/self/status", "r") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    now = int(line.split()[1]) / 1024.0
                    break
    except (OSError, ValueError, IndexError):
        now = 0.0                                # not Linux: the peak alone
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0      # kilobytes on Linux
    return {"now": round(now), "peak": round(max(peak, now)), "node": round(NODE_PEAK_KB[0] / 1024.0)}


NODE_PEAK_KB = [0]                               # the largest maxrss_kb Node has reported since the service started


def memory_words(m):
    if not m:
        return ""
    return "%d MB now, %d MB at most%s" % (m.get("now", 0), m.get("peak", 0),
                                          (", Node %d MB at most" % m["node"]) if m.get("node") else "")


def merge_disk(state):
    """What another process wrote since: `social post` (Post now) records its post in state.json while the service
    runs. The service held its state in memory and wrote it back every fifteen seconds, so a post made by hand was
    forgotten at once: the gap restarted from the service's own last post, and the aircraft posted by hand could be
    posted again (seen on the real Pi, 0.19.2). Now the latest post and every posted aircraft are taken from both."""
    disk = load_state()
    lp = disk.get("last_post")
    if isinstance(lp, (int, float)) and lp > state.get("last_post", 0):
        state["last_post"] = lp
    if isinstance(disk.get("pictures"), int) and disk["pictures"] > int(state.get("pictures", 0)):
        state["pictures"] = disk["pictures"]
    mine = state.setdefault("posted", {})
    for h, v in (disk.get("posted") or {}).items():
        theirs = posted_entry(v)
        if h not in mine or theirs["t"] > posted_entry(mine[h])["t"]:
            mine[h] = theirs
    times = set(state.get("posts", [])) | {t for t in disk.get("posts", []) if isinstance(t, (int, float))}
    state["posts"] = sorted(times)
    return state


def remember_post(p, when):
    """A post made from the command line, written so that the running service sees it (it merges the file)."""
    state = prune_state(load_state(), when)
    state["last_post"] = max(state.get("last_post", 0), when)
    remember(state, p, when)
    state["pictures"] = int(state.get("pictures", 0)) + 1
    save_state(state)


def day_of(t):
    return time.strftime("%Y-%m-%d", time.localtime(t))


def prune_state(s, now):
    """What the rules need, and no more:
      types    type code -> {hex: last day seen}, the latest KEEP_PER_TYPE distinct aircraft, thirty days ("rare")
      far      day -> farthest km that day, thirty days ("farthest")
      posted   hex -> {t: last time it was inside the sharing radius, flight: its callsign when posted}. One post per
               crossing (0.20.0): kept while the aircraft is inside, and an hour after it last was; the same airframe
               back later (the return flight, the next day) is a new crossing, and so is a new callsign
      posts    the times of the posts of the last day, for `social status`
      post_days  day -> number of posts, thirty-one days, for the summaries (0.33.0; eight days before 0.38.0)
      weekly   the ISO week of the last weekly summary, posted or skipped (0.33.0)
      summaries  period -> the cycle (day, ISO week, month) last scheduled (0.38.0)
      summary_queue  the summary posts still to make: [{period, part, key, at}], two minutes apart (0.38.0)
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
        e = posted_entry(posted[h])
        if now - e["t"] > CROSSING_GAP_S:
            del posted[h]
        else:
            posted[h] = e
    s["posts"] = [t for t in s.get("posts", []) if isinstance(t, (int, float)) and now - t <= 86400]
    week_cut = day_of(now - 31 * 86400)             # 0.38.0: thirty days, for the monthly summary (eight before)
    s["post_days"] = {d: n for d, n in (s.get("post_days") or {}).items() if isinstance(d, str) and d >= week_cut}
    s.pop("farthest_day", None); s.pop("farthest_km", None)
    return s


def warmed(state, now):
    """True once the service has watched for WARMUP_DAYS: before that, "rare" and "farthest" mean nothing."""
    try:
        start = time.mktime(time.strptime(state.get("since", day_of(now)), "%Y-%m-%d"))
    except (TypeError, ValueError):
        return False
    return now - start >= WARMUP_DAYS * 86400


def posted_entry(v):
    """A posted record in the 0.20.0 form, from that form or from the bare time 0.19 kept."""
    if isinstance(v, dict):
        return {"t": float(v.get("t", 0) or 0), "flight": str(v.get("flight", "") or "")}
    return {"t": float(v or 0), "flight": ""}


def note_seen(state, planes, now):
    """An aircraft already posted, still inside the sharing radius: its crossing goes on (0.20.0). Called with the
    aircraft the wall answered for that radius, so leaving the radius is what starts the hour that ends it."""
    posted = state.get("posted", {})
    for p in planes or ():
        h = str(p.get("hex", "")).lower()
        if h in posted:
            e = posted_entry(posted[h])
            e["t"] = now
            posted[h] = e


def already_posted(state, p):
    """Posted during this crossing. A different callsign on the same airframe is another flight (a return leg
    straight after a turnaround nearby): not this crossing. A callsign that appears or disappears is the same one."""
    e = state.get("posted", {}).get(str(p.get("hex", "")).lower())
    if e is None:
        return False
    e = posted_entry(e)
    now_cs, then_cs = (p.get("flight") or "").strip().upper(), e["flight"].strip().upper()
    return not (now_cs and then_cs and now_cs != then_cs)


def remember(state, p, when):
    """This aircraft is posted: its crossing starts being remembered, and the post is counted."""
    state.setdefault("posted", {})[str(p.get("hex", "")).lower()] = {"t": when, "flight": (p.get("flight") or "").strip()}
    state.setdefault("posts", []).append(when)
    days = state.setdefault("post_days", {})            # 0.33.0: posts per day, for the weekly summary
    days[day_of(when)] = int(days.get(day_of(when), 0)) + 1


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
        self.pending_since = {}                    # hex -> when the wall was first seen still looking it up
        self.inside = {}                           # hex -> [first, last] time seen inside the sharing radius, worth a post

    def note_inside(self, planes, now):
        """Inside the radius at this look; forgets what left it longer ago than LATE_S."""
        for p in planes or ():
            h = str(p.get("hex", "")).lower()
            if h:
                self.inside.setdefault(h, [now, now])[1] = now
        for h in [k for k, v in self.inside.items() if now - v[1] > LATE_S]:
            del self.inside[h]

    def entered(self, hex_code):
        v = self.inside.get(str(hex_code).lower())
        return v[0] if v else 0

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


def inside_now(c, aircraft, radius_km):
    """The receiver's own aircraft inside the sharing radius right now, from their positions: a crossing goes on
    while the aircraft is there, even at a look where the wall did not answer (restarting, busy)."""
    lat, lon = server.cfg_float(c, "LAT", 0), server.cfg_float(c, "LON", 0)
    if not lat and not lon:
        return []
    out = []
    for ac in aircraft or []:
        h = str(ac.get("hex", "")).lower()
        if not h or h.startswith("~") or "lat" not in ac or "lon" not in ac or ac.get("seen_pos", 0) > 30:
            continue
        if server.haversine_km(lat, lon, ac["lat"], ac["lon"]) <= radius_km:
            out.append({"hex": h, "flight": str(ac.get("flight") or "").strip()})
    return out


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
    if "all" in rules:
        reasons.append(("all", 1))                 # everything that flies over: the best-known aircraft, once per gap
    if not reasons:
        return 0, None
    reasons.sort(key=lambda r: -r[1])
    return sum(r[1] for r in reasons), reasons[0][0]


def choose(planes, tracks, rules, state, now, settle=True):
    """The best candidate right now, or None. settle=False: do not wait for lookups still on their way."""
    best, best_first = None, 0
    for p in planes:
        if not known(p) or p.get("on_ground"):
            continue
        if already_posted(state, p):
            continue
        trace = tracks.of(p.get("hex"))
        if len(trace) < TRACE_MIN_POINTS:
            continue
        # the wall is still asking adsbdb for its route or model: wait (up to SETTLE_S from the first time it was
        # seen asking) rather than post a board with empty rows (0.19.5); past that, it goes with what is known.
        # Counted from that moment, not from the track: the track starts far out, the lookups only when the aircraft
        # comes inside the sharing radius, which is when it becomes a candidate
        if settle and p.get("pending"):
            if len(tracks.pending_since) > 2000:
                tracks.pending_since.clear()
            since = tracks.pending_since.setdefault(p.get("hex"), now)
            if now - since < SETTLE_S:
                continue
        score, why = interest(p, rules, state, now)
        if score <= 0:
            continue
        # more is known about it = a better post: route, airline, model each count a little
        score += (1 if p.get("route") else 0) + (1 if p.get("airline") else 0) + (1 if p.get("type_name") else 0)
        # equal scores: the one that came into the radius first, so a busy sky is posted in the order it flew over
        first = tracks.entered(p.get("hex")) if hasattr(tracks, "entered") else 0
        if best is None or score > best[0] or (score == best[0] and first and (not best_first or first < best_first)):
            best, best_first = (score, why, p), first
    return best


# --------------------------------------------------------------------------- the words
NBSP = "\u00a0"                  # between the thousands and before the unit: "8 600 m" never breaks across two lines
                                 # (seen on a phone, 0.19.8: "altitude 8" at the end of one line, "600 m" on the next)


def metres(alt_ft, units):
    if alt_ft is None:
        return None
    if units == "imperial":
        return "{:,}".format(int(round(alt_ft / 100.0) * 100)).replace(",", NBSP) + NBSP + "ft"
    return "{:,}".format(int(round(alt_ft * 0.3048 / 10.0) * 10)).replace(",", NBSP) + NBSP + "m"


def nice_type(p):
    """"AIRBUS A-320neo" -> "Airbus A320neo" (server.nice_name since 0.37.0, shared with the statistics page)."""
    name = p.get("type_name") or ""
    return server.nice_name(name) if name else (p.get("type") or "")


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
    return "over %d%skm out" % (max(step, 50), NBSP)


POST_MAX = 300                   # Bluesky's limit, in characters


def fit_post(body, credit, tags):
    """The post's lines inside Bluesky's 300 characters: the text, the hashtags, the map's credit last, as a
    footnote (0.19.6: it sat between the text and the hashtags). When it is too long: hashtags dropped from the end,
    then the body cut at a separator. Never a hashtag cut in the middle (a wrong, clickable tag) and never the credit."""
    def join(b, cr, t):
        return "\n".join(x for x in (b, t, cr or "") if x)
    words = tags.split()
    while len(join(body, credit, " ".join(words))) > POST_MAX and words:
        words.pop()
    tags = " ".join(words)
    while len(join(body, credit, tags)) > POST_MAX and " \u00b7 " in body:
        body = body.rsplit(" \u00b7 ", 1)[0]
    return join(body, credit, tags)[:POST_MAX]


PHOTO_PAGE = re.compile(r"^https://(www\.)?planespotters\.net/photo/[0-9]+")


def photo_line(p, c):
    """(line, [(label, uri)]) or (None, []). 0.25.0, asked for by the owner: a link to the aircraft's photo page on
    Planespotters, with the photographer's name, as the post's last line. Only the link: the picture is never posted
    (their photo API terms forbid storing or passing it on), and no card is made, which would upload the thumbnail."""
    link, who = str(p.get("photo_link") or ""), " ".join(str(p.get("photo_credit") or "").split())[:40]
    if not server.cfg_bool(c, "SOCIAL_PHOTOLINK", "0") or not PHOTO_PAGE.match(link) or not who:
        return None, []
    line = "Photo: %s / Planespotters" % who
    return line, [(line, link)]


# 0.29.0, asked for by the owner: the post's words in one of five shapes, filled from the flight's own data (templates,
# never generated text: the account says so). None of them gives the distance or the direction from the receiver.
SENTENCES = ("factual", "story", "board", "spotter", "lookup")
OPENINGS = {"rare": "Rare visitor: ", "military": "Military traffic: ", "heavy": "Heavy overhead: ",
            "helicopter": "Helicopter: ", "farthest": "New 30-day range record: "}
STYLED_MAX = 220                 # a shaped text longer than this goes back to the factual one, which can be cut cleanly


def sentences_of(c):
    """The shapes the owner chose, in order; unknown words are left out, nothing valid gives factual."""
    words = [w.strip().lower() for w in str(c.get("SOCIAL_SENTENCE", "factual") or "factual").split(",")]
    if "random" in words:
        return list(SENTENCES)
    return [w for w in words if w in SENTENCES] or ["factual"]


def sentence_for(c, rng=random):
    return rng.choice(sentences_of(c))


def _a(word):
    """"an Airbus", "an easyJet", but "a Eurowings", "a United": a vowel said as "you" takes "a"."""
    w = word.lower()
    vowel = w[:1] in "aeiou" and not w.startswith(("eu", "uni", "us", "one"))
    return ("an " if vowel else "a ") + word


def speed_words(gs_kt, units):
    if not gs_kt:
        return ""
    if units == "imperial":
        return "%d%skt" % (int(round(gs_kt)), NBSP)
    return "%d%skm/h" % (int(round(gs_kt * 1.852)), NBSP)


def height_words(alt_ft, units):
    """"10.6 km" or "34,700 ft": the look-up shape says how high in round words."""
    if not alt_ft:
        return ""
    if units == "imperial":
        return "{:,}".format(int(round(alt_ft / 100.0) * 100)) + NBSP + "ft"
    return ("%.1f" % (alt_ft * 0.3048 / 1000.0)) + NBSP + "km"


def styled_text(shape, p, c, why=None, now=None):
    """The post's text in one of the shapes other than factual, or None when the flight lacks what the shape needs
    (an airline or a type) or the result is too long: the factual text is used then."""
    units = units_of(c)
    flight = (p.get("flight") or "").strip()
    cs = hashtag_callsign(flight)
    reg = p.get("registration") or ""
    typ = nice_type(p)
    airline = p.get("airline") or ""
    military = bool(p.get("military")) and airline in ("", "MILITARY")
    heli = p.get("shape") == "heli"
    if airline == "MILITARY":
        airline = ""
    what = " ".join(x for x in ("military" if military else airline, typ or ("helicopter" if heli else "")) if x)
    if not what or why == "farthest":           # a range record is nowhere near overhead: the factual words say so
        return None
    alt = metres(p.get("alt_ft"), units) or ""
    speed = speed_words(p.get("gs_kt"), units)
    r = p.get("route") or {}
    a = (r.get("from") or {}).get("city") or (r.get("from") or {}).get("name") or ""
    b = (r.get("to") or {}).get("city") or (r.get("to") or {}).get("name") or ""
    area = area_words(c)                          # "above Trémery", or the owner's own phrase ("near Metz")
    place = place_name(c) if area.startswith("above ") else ""
    clock = time.strftime("%H:%M", time.localtime(now))
    if shape == "story":
        text = _a(what)
        text = text[0].upper() + text[1:]
        if a and b:
            text += " bound for %s from %s" % (b, a)
        text += " has just crossed the sky" + (" " + area if area else "") + (", %s up." % alt if alt else ".")
        text += (" " + cs) if cs else ""
    elif shape == "board":
        lines = ["\u2708 " + " · ".join(x for x in (cs, reg) if x), "%s \u2192 %s" % (a, b) if a and b else "",
                 " · ".join(x for x in (typ, alt, speed) if x),
                 ((area[0].upper() + area[1:] + " at " + clock) if area else "")]
        text = "\n".join(x for x in lines if x.strip())
    elif shape == "spotter":
        text = (reg + ", " if reg else "") + _a(what)
        if a and b:
            text += ", flying %s \u2192 %s" % (a, b)
        if cs and cs.replace("#", "") != reg.replace("-", ""):
            text += " as " + cs
        rest = " ".join(x for x in (alt, area, ("at " + speed) if speed else "") if x)
        text += (": " + rest + ".") if rest else "."
    elif shape == "lookup":
        who = " ".join(x for x in ((airline or ("military" if military else "")), cs or reg or typ) if x)
        text = ("Look up, %s! " % place) if place else "Look up! "
        text += "%s is passing %s overhead" % (who or _a(what), height_words(p.get("alt_ft"), units) or "")
        text = text.replace("passing  overhead", "passing overhead")
        text += (" on its way from %s to %s." % (a, b)) if a and b else "."
    else:
        return None
    text = OPENINGS.get(why, "") + text
    return text if len(text) <= STYLED_MAX else None


def post_text(p, c, why=None, credit=None, photo=None, shape=None):
    """The post. English, short, nothing the wall does not know. Starts with the flight ("Flight Etihad #ETD11K"),
    ends with the place ("above Trémery"); a range record ends with where it was seen from instead, since it was
    nowhere near overhead. credit: the map's credit line, when the picture has a map."""
    units = units_of(c)
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
    if why in ("rare", "heavy"):                 # 0.29.0: the reason, said first (the others already say theirs)
        text = OPENINGS[why] + text
    shape = shape or sentence_for(c)
    if shape != "factual":
        text = styled_text(shape, p, c, why) or text
    tags = str(c.get("SOCIAL_HASHTAGS", "")).strip()
    if tags.lower() == "none":                   # set so: no hashtags at all, not even #helicopter
        tags = ""
    if heli and tags:
        tags = tags.replace("#avgeek", "#helicopter") if "#avgeek" in tags else tags + " #helicopter"
    if p.get("military") and tags:
        tags = tags.replace("#avgeek", "#military") if "#avgeek" in tags else tags + " #military"
    if photo:                                    # the photo line only when the text fits whole beside it
        with_photo = fit_post(text, "\n".join(x for x in (credit, photo) if x), tags.strip())
        if with_photo.startswith(text + "\n") or with_photo == text:
            return with_photo
    return fit_post(text, credit, tags.strip())


def alt_text(p, c, trace, look="dotmap", info=None):
    """For the picture: what a screen reader should say."""
    units = units_of(c)
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
    elif look in MAP_LOOKS and info.get("map_words"):
        tail = ". Beside it, %s with the aircraft's track over the last %d minute%s, north up." % (info["map_words"], mins, s)
    else:
        tail = ". Beside it, the aircraft's track over the last %d minute%s, north up." % (mins, s)
    if info.get("credit_full"):
        tail += " Map: " + info["credit_full"] + "."
    return ", ".join(bits) + tail


# --------------------------------------------------------------------------- the picture
def _node(spec, out, *extra):
    """Run the dot-matrix renderer (or ask it for the board's rows, --lines). Returns its JSON answer."""
    where = os.path.dirname(out) if out else None     # --lines: the system's temporary folder, nothing left behind
    fd, spec_path = tempfile.mkstemp(prefix="social-", suffix=".json", dir=where or None)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(spec, fh)
        args = [NODE, RENDERER, spec_path] + ([out] if out else []) + list(extra)
        r = subprocess.run(args, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise RuntimeError("renderer failed: %s" % (r.stderr.strip() or r.stdout.strip()))
        got = json.loads(r.stdout.strip() or "{}")
        kb = got.get("maxrss_kb")
        if isinstance(kb, (int, float)) and kb > NODE_PEAK_KB[0]:
            NODE_PEAK_KB[0] = kb
        return got
    finally:
        try:
            os.unlink(spec_path)
        except OSError:
            pass                                 # already gone: nothing to clean


PLACES_LOCAL = "places-local.tsv.gz"         # in STATE_DIR, made by tools/make_local_places.py (0.27.0)


def places_words(c):
    """The status line on the town names of the maps."""
    path = os.path.join(STATE_DIR, PLACES_LOCAL)
    if not server.cfg_bool(c, "SOCIAL_PLACES", "0"):
        return "the lists shipped with ZenithBoard (towns of 5 000+, villages when short)   (region's own list: sudo zenithboard social places on)"
    try:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            head = [next(fh) for _ in range(3)]
        n = sum(1 for _ in gzip.open(path, "rt", encoding="utf-8")) - 4
        made = head[1].rstrip().split("the country files ", 1)[1].rstrip(".")
        return "the region's own list, %d places within %s km (GeoNames: %s)" % (n, head[2].split()[4], made)
    except (OSError, IndexError, StopIteration, ValueError):
        return "ON, but the region's list is missing or unreadable (make it again: sudo zenithboard social places on)"


def flap_module():
    """social_card (Pillow), or None when Pillow is not installed. Only the looks with a map (dotmap, flap) need it."""
    try:
        import social_card
        return social_card
    except ImportError:
        return None


def render(p, trace, c, out_base):
    """Draw the picture in the chosen look. out_base has no extension: .jpg (a map in PNG would pass Bluesky's
    1,000,000 bytes), or .png for the dots alone when Pillow is missing. Returns {path, mime, width, height, bytes, and for a map: credit, links,
    credit_full, map_words}."""
    look = style_of(c)
    spec = {"plane": p, "trace": trace, "units": units_of(c), "theme": theme_of(c),
            "clock": clock_label(), "flags": server.cfg_bool(c, "FLAGS", "1"), "pitch": 10}
    card = flap_module()
    if card is not None:                         # 0.27.0: the region's list, when made and switched on
        local = os.path.join(STATE_DIR, PLACES_LOCAL)
        card.LOCAL_PLACES_FILE = local if server.cfg_bool(c, "SOCIAL_PLACES", "0") and os.path.isfile(local) else None
    if card is None:                             # Pillow not installed (an offline `social look flap`): the dots, and a word
        # `social test` installs what the chosen look needs and keeps the setting; `social look` would replace an
        # `alternate` with the one look named here
        print("social: the %s picture needs Pillow: drawing the dot-matrix picture instead. Install it with:  sudo zenithboard social test"
              % ("split-flap" if look == "flap" else "dotmap"), flush=True)
        look = "flap-fallback"
    if card is not None and look == "dotmap":    # 0.23.0: Node draws the dots, the right-hand column dark; Pillow lays the map
        got = _node(dict(spec, map=True), out_base + ".png")
        out = out_base + ".jpg"
        info = card.render_dotmap(out_base + ".png", got["map_box"], trace, p, out, color=got.get("color", "#ffb000"),
                                  units=spec["units"], map_mode=map_of(c), cache_dir=os.path.join(STATE_DIR, "tiles"))
        try:
            os.unlink(out_base + ".png")         # the dots alone: only the JPEG with its map is posted
        except OSError:
            pass                                 # publish() removes it anyway
        info.update(path=out, mime="image/jpeg")         # Node's memory is counted by _node()
        return info
    if card is not None:
        got = _node(dict(spec, flags=False, cols=card.COLS), None, "--lines")
        out = out_base + ".jpg"
        info = card.render(got["lines"], trace, p, out, color=got.get("color", "#ffb000"),
                           units=spec["units"], map_mode=map_of(c), cache_dir=os.path.join(STATE_DIR, "tiles"))
        info.update(path=out, mime="image/jpeg")
        return info
    out = out_base + ".png"
    info = _node(spec, out)
    info.update(path=out, mime="image/png", fallback=(look == "flap-fallback"))
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


def _error_body(exc):
    """The body of an HTTP error, read once and kept: it can only be read once."""
    if not hasattr(exc, "zb_body"):
        try:
            exc.zb_body = exc.read().decode("utf-8", "replace")
        except Exception:
            exc.zb_body = ""
    return exc.zb_body


def _http_error_text(exc):
    try:
        return "%s %s" % (exc.code, _error_body(exc)[:300])
    except Exception:
        return str(exc)


BLUESKY_PDS = "https://bsky.social"
SESSION_REUSE_S = 3600           # an access token is used this long, then refreshed (Bluesky's last about two hours)
_SESSION = {}                    # the service's session, in memory only: never written anywhere


def bluesky_session(sec, fresh=False):
    """Signed in to Bluesky, reusing the session (0.20.0). Bluesky allows an account 300 sign-ins a day, 30 in five
    minutes; signing in for every post, as 0.19 did, was fine with a gap between posts and is not with every
    crossing posted. The access token is reused for an hour, then renewed with the refresh token; a new sign-in
    only when that is refused, when the account in the file changed, or when asked (fresh: `social check`)."""
    key = (sec.get("BLUESKY_HANDLE"), sec.get("BLUESKY_APP_PASSWORD"))
    ses, now = _SESSION.get("ses"), time.time()
    if not fresh and ses and _SESSION.get("key") == key:
        if now - _SESSION.get("at", 0) < SESSION_REUSE_S:
            return ses
        if ses.get("refreshJwt"):
            try:
                new = _json_request(BLUESKY_PDS + "/xrpc/com.atproto.server.refreshSession", b"",
                                    {"Authorization": "Bearer " + ses["refreshJwt"]}, method="POST")
                if new.get("accessJwt"):
                    new.setdefault("did", ses.get("did"))
                    _SESSION.update(ses=new, at=now)
                    return new
            except urllib.error.HTTPError:
                pass                             # refused (expired, revoked): sign in again below
    _SESSION.clear()
    ses = _json_request(BLUESKY_PDS + "/xrpc/com.atproto.server.createSession",
                        {"identifier": sec["BLUESKY_HANDLE"], "password": sec["BLUESKY_APP_PASSWORD"]})
    _SESSION.update(key=key, ses=ses, at=now)
    return ses


def token_refused(exc):
    """Bluesky no longer takes the session's token (expired early, revoked): worth one new sign-in."""
    if not isinstance(exc, urllib.error.HTTPError) or exc.code not in (400, 401):
        return False
    body = _error_body(exc)
    return exc.code == 401 or "ExpiredToken" in body or "InvalidToken" in body


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
        at = text.rfind(label)                   # the credit is the last line: its words, not the same word higher up
        if at >= 0 and uri.startswith("https://"):
            a, b = _byte_span(text, at, at + len(label))
            facets.append({"index": {"byteStart": a, "byteEnd": b},
                           "features": [{"$type": "app.bsky.richtext.facet#link", "uri": uri}]})
    return sorted(facets, key=lambda f: f["index"]["byteStart"])


def post_bluesky(sec, text, path, alt, width, height, mime="image/png", links=None):
    """The post, with the session kept from the last one; a token refused on the way: one new sign-in, once."""
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) > 1000000:
        raise RuntimeError("picture is %d bytes, Bluesky takes 1,000,000 at most" % len(data))
    try:
        return _post_once(bluesky_session(sec), text, data, alt, width, height, mime, links)
    except urllib.error.HTTPError as exc:
        if not token_refused(exc):
            raise
    return _post_once(bluesky_session(sec, fresh=True), text, data, alt, width, height, mime, links)


def _post_once(ses, text, data, alt, width, height, mime, links):
    auth = {"Authorization": "Bearer " + ses["accessJwt"]}
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
        ses = bluesky_session(sec, fresh=True)
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
        pass                                     # not ours to make: the private temporary folder below
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
                pass                             # no preview of the other look to drop
    with open(src, "rb") as a, open(keep_base + ext, "wb") as b:
        b.write(a.read())
    return keep_base + ext


def publish(p, trace, why, c, sec, dry=False, keep=None):
    """Draw, post to Bluesky, delete the picture. Returns {"bluesky": uri or 'FAILED ...'} (dry: the text instead)."""
    base = os.path.join(work_dir(), "post-%s" % uuid.uuid4().hex)
    results = {}
    try:
        info = render(p, trace, c, base)
        pline, plinks = photo_line(p, c)
        text = post_text(p, c, why, info.get("credit"), pline)
        links = list(info.get("links") or []) + (plinks if pline and pline in text else [])
        alt = alt_text(p, c, trace, "dotmap" if info.get("fallback") else style_of(c), info)   # no Pillow: the dots
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
                                              info.get("mime", "image/png"), links)
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
                pass                             # the other look's file was never drawn
        d = os.path.dirname(base)
        if d != RUN_DIR:
            try:
                os.rmdir(d)
            except OSError:
                pass                             # not empty, or gone already: left as it is


def publish_week(c, sec, now, state=None, dry=False, keep=None, second=False, part=None, period="weekly"):
    """The week's posts (social_week.py): draw, post, delete the picture. part 1 the week (0.33.0), 2 the cargo
    airlines and business jets (0.35.0; second=True says the same), 3 the military aircraft, 4 the helicopters, light
    aircraft and gliders (0.36.0). Returns {"bluesky": uri or 'FAILED ...'}, or {"skipped": why} when there is
    nothing to say (dry: the text instead)."""
    part = part or (2 if second else 1)
    import social_week as week
    w = week.week_data(c, now=now, posts=(state or {}).get("post_days"), period=period)
    span = {"daily": "the last 24 hours", "weekly": "these seven days", "monthly": "these thirty days"}[period]
    if not w:
        return {"skipped": "no statistics for %s (turn them on: sudo zenithboard stats on)" % span}
    for k in ("models", "bizjets"):              # "BOEING 737-800" as the posts write it: "Boeing 737-800" (0.34.1)
        w[k] = [(nice_type({"type_name": n}), v) for n, v in w.get(k) or []]
    w["cargo_models"] = {a: (nice_type({"type_name": m}), v) for a, (m, v) in (w.get("cargo_models") or {}).items()}
    if part == 3 and str(c.get("SHOW_ROUTES", "1")).lower() in ("1", "on", "yes", "true") and w.get("military_unknown"):
        # 0.40.5: a military aircraft of unknown type is asked of adsbdb, then hexdb, by its address, as the wall asks
        # for every aircraft when routes are on; two seconds apart, a dozen at most
        last = {"t": 0.0}

        def ask(hex_code):
            time.sleep(max(0.0, week.server.AIRCRAFT_GAP_S - (time.time() - last["t"])))
            last["t"] = time.time()
            return week.server._aircraft_api(hex_code.upper())[0]
        week.name_unknown_military(w, ask)
    for e in w.get("military") or []:
        e["models"] = [(nice_type({"type_name": n}), v) for n, v in e["models"]]
    if part > 1 and not week.has_part(w, part):
        return {"skipped": ({2: "no cargo airline nor business jet in the lists", 3: "no military aircraft in the lists",
                             4: "no helicopter, light aircraft, glider, drone or balloon in the lists"}[part] + " for " + span
                            if (w.get("covered") or w.get("shown")) else
                            "the airline and type lists do not cover %s yet (counted since %s, shown from the summary of %s)"
                            % (span, w.get("fleet_from") or "-", w.get("fleet_week") or "-"))}
    if flap_module() is None:
        return {"skipped": "the weekly picture needs Pillow (install it: sudo zenithboard social test)"}
    tags = str(c.get("SOCIAL_HASHTAGS", "")).strip()
    tags = "" if tags.lower() == "none" else tags
    area = area_words(c)
    out = os.path.join(work_dir(), "week-%s.png" % uuid.uuid4().hex)
    results = {}
    try:
        if part == 2:
            flags = week.load_flags([cc for cc, _ in w.get("bizjet_countries") or []] + list((w.get("airline_cc") or {}).values()))
            info = week.draw_second(w, theme_of(c), area, out, flags)
            text, alt = week.text_second(w, area, tags, fit_post), week.alt_second(w, area)
        elif part == 3:
            flags = week.load_flags([e["cc"] for e in w.get("military") or []])
            info = week.draw_military(w, theme_of(c), area, out, flags)
            text, alt = week.text_military(w, area, tags, fit_post), week.alt_military(w, area)
        elif part == 4:
            codes = []
            for g in ("heli", "light", "glider", "drone", "balloon"):
                e = (w.get("misc") or {}).get(g)
                if e:
                    e["models"] = [(nice_type({"type_name": n}), v) for n, v in e["models"]]
                    e["rows"] = [(nice_type({"type_name": n}), cc, v) for n, cc, v in e.get("rows") or []]
                    codes += [cc for _, cc, _ in e["rows"]]
            info = week.draw_misc(w, theme_of(c), area, out, week.load_flags(codes))
            text, alt = week.text_misc(w, area, tags, fit_post), week.alt_misc(w, area)
        else:
            info = week.draw(w, theme_of(c), area, out, week.load_flags(list((w.get("airline_cc") or {}).values())))
            text, alt = week.text(w, c, area, tags, fit_post), week.alt(w, area)
        if keep:
            try:
                results["preview"] = keep_copy(out, keep)
            except OSError as exc:
                results["preview_error"] = "could not keep a copy: %s" % exc
        if dry:
            results.update(text=text, alt=alt, bytes=info["bytes"], fleet_from=w.get("fleet_from"),
                           fleet_week=w.get("fleet_week"), fleet_shown=bool(w.get("covered") or w.get("shown")),
                           fleet_since=w.get("since"))
            return results
        try:
            results["bluesky"] = post_bluesky(sec, text, out, alt, info["width"], info["height"], info["mime"])
        except urllib.error.HTTPError as exc:
            results["bluesky"] = "FAILED: " + _http_error_text(exc)
        except Exception as exc:
            results["bluesky"] = "FAILED: %s" % exc
        return results
    finally:
        try:
            os.unlink(out)
        except OSError:
            pass                                 # never drawn


def schedule_summaries(c, state, now):
    """Put the posts of every summary that is due into the queue, the longer period first, each SECOND_AFTER_S after
    the last one already there. Marked as scheduled at once: a restart does not post it twice."""
    import social_week
    queue = state.setdefault("summary_queue", [])
    done = state.setdefault("summaries", {})
    seen = state.setdefault("summary_seen", {})
    for period in social_week.ORDER:
        # 0.49.0: a time or a switch changed since the last look. Set (or switched on) after its time has passed
        # today: that slot is marked as gone, so it does not go at once; it goes from the next cycle. Moved to later
        # today: nothing to mark, it goes at its new time (the owner, 22 October)
        now_set = social_week.setting_of(c, period)
        if social_week.changed(c, state, period):
            if social_week.is_on(c, period) and social_week.slot_passed(c, period, now) \
                    and not social_week.slot_done(c, state, period, now):
                done[period] = social_week.slot_key(c, period, now)
                nxt = social_week.next_due(c, dict(state, summary_seen=dict(seen, **{period: now_set})), now, period)
                print("social: %s summary set to %s, already past today: from the next one%s" % (
                    period, social_week.at_words(c, period), (", " + nxt.strftime("%a %Y-%m-%d %H:%M")) if nxt else ""), flush=True)
            else:
                print("social: %s summary now %s" % (period, social_week.at_words(c, period) if social_week.is_on(c, period) else "off"), flush=True)
        seen[period] = now_set
        if not social_week.due(c, state, now, period):
            continue
        key = social_week.slot_key(c, period, now)
        at = max([now] + [q["at"] + SECOND_AFTER_S for q in queue])
        parts = social_week.parts_of(c, period)
        for i, part in enumerate(parts):
            queue.append({"period": period, "part": part, "key": key, "at": at + i * SECOND_AFTER_S})
        done[period] = key
        state.setdefault("summaries_at", {})[period] = now       # 0.48.0: `social summary` says when it last went
        # 0.48.0: said in the journal, so "why no summary?" has an answer (the owner, 21 October)
        print("social: %s summary due (%s): posts %s queued, %d min apart, the first %s" % (
            period, social_week.at_words(c, period), ",".join(str(p) for p in parts), SECOND_AFTER_S // 60,
            "now" if at <= now else "at " + time.strftime("%H:%M", time.localtime(at))), flush=True)
    state.pop("weekly2", None)                     # the chain of 0.35.0 to 0.37.0, replaced by the queue
    return queue


def run_summaries(c, sec, state, now, last_fail):
    """One step of the queue: the first post whose time has come. Returns the time of the last failure."""
    queue = schedule_summaries(c, state, now)
    if not queue or now < queue[0]["at"] or not bluesky_ready(sec) or now - last_fail < RETRY_AFTER_FAIL_S:
        return last_fail
    q = queue[0]
    if now - q["at"] > SECOND_LATE_S:              # failing for hours: that summary is dropped, not posted late
        print("social: %s summary dropped: could not be posted for %d hours" % (q["period"], SECOND_LATE_S // 3600), flush=True)
        state["summary_queue"] = [x for x in queue if not (x["period"] == q["period"] and x["key"] == q["key"])]
        return last_fail
    try:
        results = publish_week(c, sec, now, state, part=q["part"], period=q["period"])
    except Exception as exc:                       # a summary that cannot be made must not stop the service
        results = {"bluesky": "FAILED: %s" % exc}
    name = "%s summary, post %d" % (q["period"], q["part"])
    if "skipped" in results:
        print("social: no %s: %s" % (name, results["skipped"]), flush=True)
        queue.pop(0)
        if q["part"] == 1:                         # nothing to sum up: none of that summary's other posts either
            state["summary_queue"] = [x for x in queue if not (x["period"] == q["period"] and x["key"] == q["key"])]
        elif queue:
            queue[0]["at"] = min(queue[0]["at"], now)  # nothing to say: the next one keeps its turn
        return last_fail
    if str(results.get("bluesky", "FAILED")).startswith("FAILED"):
        print("social: could not post the %s: %s" % (name, json.dumps(results)), flush=True)
        return now
    print("social: posted the %s: %s" % (name, json.dumps(results)), flush=True)
    queue.pop(0)
    if queue:
        queue[0]["at"] = max(queue[0]["at"], now + SECOND_AFTER_S)
    return last_fail


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
    note_seen(state, planes + inside_now(c, aircraft, radius), now)   # inside: a crossing already posted goes on
    # every crossing is posted (0.20.0): one worth a post that left the radius before its turn is asked about
    # where it is now. Only those worth it are followed, so the wall is not asked about every aircraft that leaves
    tracks.note_inside([p for p in planes if known(p) and not p.get("on_ground") and interest(p, rules, state, now)[0] > 0], now)
    here = {str(p.get("hex", "")).lower() for p in planes}
    calls = {str(a.get("hex", "")).lower(): str(a.get("flight") or "").strip() for a in aircraft or []}
    late = sorted((v[0], h) for h, v in tracks.inside.items()
                  if h not in here and not already_posted(state, {"hex": h, "flight": calls.get(h, "")}))
    for _, h in late[:LATE_ASKS]:
        p = ask_wall_one(c, h)
        if p:
            planes = planes + [dict(p, _late=True)]
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
    started = time.time()
    polls = candidates = 0
    c = cfg()
    sec = account()
    print("social: running ZenithBoard %s. Bluesky: %s. Picture: %s. Radius %s km, gap %s, rules: %s. History since %s%s." % (
        server.VERSION,
        sec.get("BLUESKY_HANDLE") if bluesky_ready(sec) else "NO ACCOUNT (run: sudo zenithboard social setup)", picture_words(c, state),
        c.get("SOCIAL_RADIUS_KM"), gap_words(c), ", ".join(sorted(rules_of(c))) or "none",
        state.get("since"), "" if warmed(state, time.time()) else
        " (rare and farthest wait for %d days of it)" % WARMUP_DAYS), flush=True)
    while True:
        now = time.time()
        c = cfg()
        aircraft = read_aircraft(c)
        tracks.feed(aircraft, now)
        if now - last_ask >= ASK_EVERY_S:
            last_ask = now
            prune_state(merge_disk(state), now)        # a post made by hand counts for the gap and the aircraft
            planes, best = one_poll(c, state, tracks, aircraft, now)
            polls += 1
            candidates += 1 if best else 0
            sec = account()
            gap = gap_min(c) * 60
            # A failed post (Bluesky down, the app password revoked, no picture) waits ten minutes before the next
            # try: before 0.19.0 it was tried again at every look, every fifteen seconds, and each try signs in
            if best and bluesky_ready(sec) and now - state.get("last_post", 0) >= gap and now - last_fail >= RETRY_AFTER_FAIL_S:
                score, why, p = best
                try:
                    results = publish(p, tracks.of(p["hex"]), why, picture_for(c, int(state.get("pictures", 0))), sec)
                except Exception as exc:                 # a picture that cannot be drawn must not stop the service
                    results = {"bluesky": "FAILED: %s" % exc}
                ok = not str(results.get("bluesky", "FAILED")).startswith("FAILED")
                print("social: %s %s (%s): %s" % ("posted" if ok else "could not post", p.get("flight") or p.get("hex"), why,
                                                  json.dumps(results)), flush=True)
                if ok:
                    state["last_post"] = now
                    remember(state, p, now)
                    state["pictures"] = int(state.get("pictures", 0)) + 1     # the next one varies, when asked to
                    last_ask = 0                         # another one may be waiting its turn: look again at the next read
                else:
                    last_fail = now
            # the summaries (0.33.0 the week; 0.38.0 the day and thirty days too), each at its own time, with the posts
            # picked for it, two minutes apart in one queue. A failure waits like a post's does
            last_fail = run_summaries(c, sec, state, now, last_fail)
            state["memory"] = dict(memory_mb(), since=started)  # for `social status`: since this start
            save_state(state)
        if now - last_summary >= 3600:
            # once an hour, so the journal answers "why no post?" without a line every fifteen seconds
            lp = state.get("last_post")
            wait = max(0, int((lp + gap_min(c) * 60 - now) / 60)) if lp else 0
            print("social: last hour: %d looks, %d with a candidate under the rules. Last post: %s.%s Memory: %s.%s" % (
                polls, candidates, time.strftime("%H:%M", time.localtime(lp)) if lp else "never",
                (" Next possible in %d min." % wait) if wait else "", memory_words(memory_mb()),
                "" if bluesky_ready(account()) else " No Bluesky account set up: nothing can be posted."), flush=True)
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
        elif choose(planes, tracks, rules_of(c) | {"all"}, state, now):
            break
        time.sleep(READ_EVERY_S)
    if hex_code:
        for p in planes:
            if p.get("hex") == hex_code.lower():
                return c, state, p, tracks.of(hex_code), "chosen"
        return c, state, None, [], None
    best = choose(planes, tracks, rules_of(c) | {"all"}, state, time.time())
    if not best:                                   # the half minute is over: what is known will do
        best = choose(planes, tracks, rules_of(c) | {"all"}, state, time.time(), settle=False)
    if not best:
        return c, state, None, [], None
    return c, state, best[2], tracks.of(best[2]["hex"]), best[1]


def cmd_test(hex_code=None):
    c, state, p, trace, why = _collect_once(hex_code)
    if not p:
        print("Nothing to show: no aircraft with a track inside %s km right now (or the wall did not answer)." % c.get("SOCIAL_RADIUS_KM"))
        return 1
    pc = picture_for(c, int(state.get("pictures", 0)))     # this post's look and map, "alternate" and "rotate" resolved
    r = publish(p, trace, why, pc, {}, dry=True, keep=os.path.join(STATE_DIR, "preview"))
    print("Aircraft: %s %s (%s)" % (p.get("flight") or "", p.get("hex"), p.get("type") or "?"))
    # The test always finds something to show (it adds "all"); say plainly whether the service would post it.
    score, real = interest(p, rules_of(c), state, time.time())
    if real:
        print("Would the service post it? Yes, under the rule '%s'." % real)
    else:
        why_not = "your rules (%s) do not pick it" % (", ".join(sorted(rules_of(c))) or "none")
        if not warmed(state, time.time()) and rules_of(c) & {"rare", "farthest"}:
            why_not += "; 'rare' and 'farthest' wait for %d days of history (since %s)" % (WARMUP_DAYS, state.get("since", "today"))
        print("Would the service post it? No: %s. The test shows it anyway." % why_not)
    print("Picture: %s, %s (%s bytes)" % (picture_words(pc), r.get("preview") or r.get("preview_error"), r.get("bytes")))
    if style_of(pc) in MAP_LOOKS and map_of(pc) != "none" and r.get("map") == "none":
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
    sec = account()
    if not bluesky_ready(sec):
        print("No Bluesky account is set up: run  sudo zenithboard social setup")
        return 1
    results = publish(p, trace, why, picture_for(c, int(merge_disk(state).get("pictures", 0))), sec)
    print("bluesky: %s" % results.get("bluesky", "?"))
    ok = not str(results.get("bluesky", "FAILED")).startswith("FAILED")
    if ok:
        remember_post(p, time.time())
    return 0 if ok else 1


WEEK_TITLES = {1: "the period: aircraft, messages, busiest times, airlines and models", 2: "cargo airlines and business jets", 3: "military aircraft",
               4: "general aviation: helicopters, light aircraft, gliders, drones and balloons"}


def cmd_week(post=False, second=False, part=None, period="weekly"):
    """`social summary weekly test` (`social weekly test`): the four posts of that summary, drawn and shown, nothing
    posted; `... post` (post2, post3, post4): that one posted now. The scheduled ones still go out."""
    import social_week
    part = part or (2 if second else 1)
    c = cfg()
    state = prune_state(load_state(), time.time())
    sec = account()
    if post and not bluesky_ready(sec):
        print("No Bluesky account is set up: run  sudo zenithboard social setup")
        return 1
    if post:
        r = publish_week(c, sec, time.time(), state, part=part, period=period)
        if "skipped" in r:
            print("Nothing to post: %s." % r["skipped"])
            return 1
        print("bluesky: %s" % r.get("bluesky", "?"))
        return 0 if not str(r.get("bluesky", "FAILED")).startswith("FAILED") else 1
    port = int(server.cfg_float(c, "PORT", 8080))
    for n in (1, 2, 3, 4):
        r = publish_week(c, sec, time.time(), state, dry=True, part=n, period=period,
                         keep=os.path.join(STATE_DIR, "preview" if n == 1 else "preview%d" % n))
        if n == 1 and "skipped" in r:
            print("Nothing to sum up: %s." % r["skipped"])
            return 1
        picked = n in social_week.parts_of(c, period)
        print("Post %d%s: %s%s" % (n, (", " + social_week.at_words(c, period)) if n == 1 else
                                   ", %d minutes after the one before" % (SECOND_AFTER_S // 60), WEEK_TITLES[n],
                                   "" if picked else "   (not picked: sudo zenithboard social summary %s parts ...)" % period))
        if "skipped" in r:
            print("  Not posted this time: %s." % r["skipped"])
            try:                                 # no picture of an older test shown for a post that has none (0.36.1)
                os.unlink(os.path.join(STATE_DIR, "preview%d.png" % n))
            except OSError:
                pass                             # there was none to remove
        else:
            print("  Picture: %s (%s bytes)   See it:  http://%s:%d/social/preview%s" % (
                r.get("preview") or r.get("preview_error"), r.get("bytes"), local_ip(), port, "" if n == 1 else n))
            print("  " + r["text"].replace("\n", "\n  "))
            print("  Alt text: " + r["alt"])
        if n == 1 and r.get("fleet_since"):
            print("  Airlines and models: counted since %s (the lists began inside this period; said on the cards)." % r["fleet_since"])
        if n == 1 and not r.get("fleet_shown"):
            print("  Airlines and models: %s" % (("counted since %s, they join the summary from the one of %s, the first "
                                                   "they cover whole." % (r["fleet_from"], r["fleet_week"])) if r.get("fleet_from")
                                                  else "not counted yet (the statistics' lists, ZenithBoard 0.31.0 on)."))
        print()
    print("Nothing was posted: this was the test. To post one now:  sudo zenithboard social summary %s post  (post2, post3, post4)" % period)
    print("The service posts posts %s %s." % (",".join(str(x) for x in social_week.parts_of(c, period)),
                                              social_week.at_words(c, period) if social_week.is_on(c, period)
                                              else "only once it is on: sudo zenithboard social summary %s on" % period))
    return 0


def cmd_check():
    sec = account()
    if not bluesky_ready(sec):
        print("No account configured. Run:  sudo zenithboard social setup")
        return 1
    res = check_bluesky(sec)
    print("bluesky: %s" % res)
    return 1 if res.startswith("FAILED") else 0


def picture_words(c, state=None):
    """"dotmap, amber, normal map" or "flap, green, satellite map": what the picture will look like. With the varying settings,
    what varies, and the next post's picture when the count of posts is known."""
    def one(r):
        return "%s, %s, %s" % (style_of(r), theme_of(r), "no map" if map_of(r) == "none" else map_of(r) + " map")
    if not varies(c):
        return one(c)
    what = [x for x, on in (("dotmap and flap in turn", str(c.get("SOCIAL_STYLE", "")).lower() == "alternate"),
                            ("the colours in turn", str(c.get("SOCIAL_THEME", "")).lower() == "rotate"),
                            ("the maps in turn", str(c.get("SOCIAL_MAP", "")).lower() == "rotate")) if on]
    nxt = (" (next: %s)" % one(picture_for(c, int(state.get("pictures", 0))))) if state is not None else ""
    return ", ".join(what) + nxt


def unreadable(path):
    """True when the path is there but this user cannot read it (`social status` run as pi, not as root)."""
    return os.path.exists(path) and not os.access(path, os.R_OK | (os.X_OK if os.path.isdir(path) else 0))


def cmd_status():
    """What the service would do. Run as a user who cannot read the account file or the state folder (pi), it says
    so: in 0.19.2 it printed "no account" and "Last post: never" on a Pi that had just posted (seen on the real Pi)."""
    c, sec = cfg(), account()
    who = getpass_user()
    blind = []
    print("Social sharing: %s" % ("on" if server.cfg_bool(c, "SOCIAL") else "off"))
    if unreadable(SECRETS_FILE):
        blind.append(SECRETS_FILE)
        print("Bluesky: set up, but %s cannot read the account file" % who)
    else:
        print("Bluesky: %s" % (("@" + sec["BLUESKY_HANDLE"]) if bluesky_ready(sec) else "no account (run: sudo zenithboard social setup)"))
    state_blind = unreadable(STATE_DIR) or unreadable(os.path.join(STATE_DIR, "state.json"))
    print("Picture: %s" % picture_words(c, None if state_blind else load_state()))
    print("Radius: %s km   Area: %s   Gap: %s   Rules: %s" % (c.get("SOCIAL_RADIUS_KM"), c.get("SOCIAL_AREA") or "(none)",
                                                               gap_words(c), ", ".join(sorted(rules_of(c))) or "none"))
    print("Hashtags: %s   (change: sudo zenithboard social hashtags ...)" % c.get("SOCIAL_HASHTAGS"))
    print("Town names on the maps: %s" % places_words(c))
    print("Post sentence: %s%s   (change: sudo zenithboard social sentence ...)" % (",".join(sentences_of(c)),
          "  (one drawn at each post)" if len(sentences_of(c)) > 1 else ""))
    import social_week
    for period in ("daily", "weekly", "monthly"):          # 0.38.0
        print("Summary, %s: %s" % (period, ("on, %s, posts %s" % (social_week.at_words(c, period),
                                                                  ",".join(str(x) for x in social_week.parts_of(c, period))))
                                   if social_week.is_on(c, period) else "off   (sudo zenithboard social summary %s on)" % period))
    if unreadable(STATE_DIR) or unreadable(os.path.join(STATE_DIR, "state.json")):
        blind.append(STATE_DIR)
        print("History: %s cannot read the service's state folder" % who)
    else:
        state = load_state()
        lp = state.get("last_post")
        print("Last post: %s" % (time.strftime("%Y-%m-%d %H:%M", time.localtime(lp)) if lp else "never"))
        now = time.time()
        posts = [t for t in state.get("posts", []) if isinstance(t, (int, float)) and now - t <= 86400]
        crossing = [h for h, v in (state.get("posted") or {}).items() if now - posted_entry(v)["t"] <= CROSSING_GAP_S]
        print("Posts in the last day: %d   Types noted: %d   Range record (30 days): %s" % (
            len(posts), len(state.get("types", {})), ("%d km" % range_best(state)) if range_best(state) else "none yet"))
        print("Crossings remembered: %d (posted, still inside the radius or left it less than %d min ago:"
              " not posted again until then)" % (len(crossing), CROSSING_GAP_S // 60))
        if state.get("since"):
            print("History since %s: %s" % (state["since"], "rare and farthest are active" if warmed(state, now)
                                              else "rare and farthest start after %d days" % WARMUP_DAYS))
        gap = gap_min(c) * 60
        if lp and now - lp < gap:
            print("Next post possible in %d min (the gap)." % int((lp + gap - now) / 60))
        m = state.get("memory")
        if m and server.cfg_bool(c, "SOCIAL"):
            print("Memory (the service, since %s): %s" % (time.strftime("%H:%M", time.localtime(m.get("since", now))), memory_words(m)))
    if blind:
        print("For the whole picture:  sudo zenithboard social status")
    return 0


def getpass_user():
    try:
        import pwd
        return pwd.getpwuid(os.getuid()).pw_name
    except Exception:
        return "this user"


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
    if cmd == "week-test":
        return cmd_week()
    if cmd in ("week-post", "week-post2", "week-post3", "week-post4"):
        return cmd_week(post=True, part=int(cmd[9:] or 1))
    if cmd in ("summary-test", "summary-post") and arg in ("daily", "weekly", "monthly"):     # 0.38.0
        n = argv[3] if len(argv) > 3 else "1"
        if cmd == "summary-test":
            return cmd_week(period=arg)
        return cmd_week(post=True, part=int(n) if n in ("1", "2", "3", "4") else 1, period=arg)
    if cmd == "status":
        return cmd_status()
    if cmd == "summary-when":                     # 0.48.0: for `zenithboard social summary`
        import social_week
        c, now = cfg(), time.time()
        state = {} if unreadable(STATE_DIR) or unreadable(os.path.join(STATE_DIR, "state.json")) else load_state()
        raw = arg == "--facts"                   # for the web console's facts: sum_daily_last=..., sum_daily_next=...
        for period in ("daily", "weekly", "monthly"):
            if raw:
                last_at = (state.get("summaries_at") or {}).get(period)
                last = time.strftime("%Y-%m-%d %H:%M", time.localtime(last_at)) if isinstance(last_at, (int, float)) \
                    else (social_week.done_for(state, period) or "")
                nxt = social_week.next_due(c, state, now, period)
                print("sum_%s_last=%s\nsum_%s_next=%s" % (period, last, period,
                                                         "now" if nxt and abs(nxt.timestamp() - now) < 61 else (nxt.strftime("%Y-%m-%d %H:%M") if nxt else "")))
                continue
            print("%s %s" % (period, social_week.when_words(c, state, now, period)))
        if raw:
            return 0
        q = state.get("summary_queue") or []
        if q:
            print("queue " + ", ".join("%s post %d at %s" % (x["period"], x["part"], time.strftime("%H:%M", time.localtime(x["at"])))
                                       for x in q[:8]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except BrokenPipeError:                      # `social status | head`: the reader left, nothing went wrong
        with open(os.devnull, "w") as null:      # Python's own flush at exit then writes nowhere, without a second error
            os.dup2(null.fileno(), sys.stdout.fileno())
        sys.exit(0)
