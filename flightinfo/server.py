#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ZenithBoard FlightInfo server.

Tiny, dependency-free (Python standard library only) web server that:
  * reads the decoder's aircraft.json (readsb or dump1090-fa),
  * keeps the aircraft that are inside the configured radius around the antenna,
  * adds airline name, model-matched silhouette class and (optionally) a Planespotters photo,
  * serves the dot-matrix wall (static/) and a small JSON API.

Configuration is read from /etc/zenithboard/config.env on every request (cached
by file modification time), so `zenithboard config ...` takes effect without a
restart.
"""
import json
import math
import mimetypes
import os
import queue
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

VERSION = "0.9.2"
CONFIG_FILE = os.environ.get("ZENITHBOARD_CONFIG", "/etc/zenithboard/config.env")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DEMO_DIR = os.path.join(BASE_DIR, "demo")
DATA_DIR = os.path.join(BASE_DIR, "data")
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
import aircraft  # noqa: E402  (silhouette class per aircraft type)

SERVER_ID = str(int(time.time()))  # changes on restart -> browsers reload themselves

KM_PER_MI = 1.609344
RADIUS_PRESETS = [1, 2, 5, 10, 15, 30, 50]
THEMES = ("amber", "green", "red", "white")
MAX_POSITION_AGE_S = 30  # ignore aircraft whose position is older than this

DEFAULTS = {
    "UNITS": "metric",          # metric | imperial
    "THEME": "amber",           # amber | green | red | white
    "LAT": "0",
    "LON": "0",
    "DECODER": "readsb",        # readsb | dump1090-fa
    "RADIUS": "10",             # in km (metric) or miles (imperial)
    "CYCLE_SECONDS": "6",
    "SHOW_PHOTOS": "1",
    "DISPLAY_MODE": "dots",     # dots (dot matrix) | flap (split-flap airport board)
    "SHOW_ROUTES": "1",         # where the flight comes from / goes to (looked up by callsign on adsbdb.com)
    "PORT": "8080",
    "AIRCRAFT_JSON": "",        # optional explicit path override
    "UAT978": "0",              # merge the 978 MHz UAT aircraft (United States, dump978-fa + skyaware978)
    "AIRCRAFT_JSON_978": "",    # optional explicit path override for the UAT list
    "DEMO": "0",                # 1 = fictional demo airlines and mock photos
    "USER_DATA_DIR": "/var/lib/zenithboard",   # data/types.json (monthly refresh) lives here
}

_cfg_cache = {"mtime": None, "data": dict(DEFAULTS)}


# --------------------------------------------------------------------------- config
def parse_env_text(text):
    """Parse KEY=VALUE lines (comments and blank lines ignored, quotes stripped)."""
    out = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[key.strip()] = value
    return out


def load_config():
    try:
        mtime = os.stat(CONFIG_FILE).st_mtime
    except OSError:
        return dict(DEFAULTS)
    if _cfg_cache["mtime"] != mtime:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as fh:
                data = dict(DEFAULTS)
                data.update(parse_env_text(fh.read()))
            _cfg_cache.update(mtime=mtime, data=data)
        except OSError:
            return dict(DEFAULTS)
    return _cfg_cache["data"]


def cfg_float(cfg, key, default):
    try:
        return float(cfg.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def cfg_bool(cfg, key):
    return str(cfg.get(key, "0")).lower() in ("1", "true", "yes", "on")


def radius_to_km(radius, units):
    return radius * KM_PER_MI if units == "imperial" else radius


def aircraft_json_path(cfg):
    if cfg.get("AIRCRAFT_JSON"):
        return cfg["AIRCRAFT_JSON"]
    preferred = "/run/%s/aircraft.json" % cfg.get("DECODER", "readsb")
    if os.path.exists(preferred):
        return preferred
    for alt in ("/run/readsb/aircraft.json", "/run/dump1090-fa/aircraft.json"):
        if os.path.exists(alt):
            return alt
    return preferred


def uat_json_path(cfg):
    """The 978 MHz UAT aircraft list, or None when UAT is not enabled."""
    if not cfg_bool(cfg, "UAT978"):
        return None
    return cfg.get("AIRCRAFT_JSON_978") or "/run/skyaware978/aircraft.json"


def merge_aircraft(primary, uat):
    """1090 MHz list + 978 MHz list -> one list. An aircraft heard on both keeps the more recent entry."""
    out = dict(primary) if isinstance(primary, dict) else {}
    merged, index = [], {}
    for source in (primary, uat):
        for ac in (source.get("aircraft") or []) if isinstance(source, dict) else []:
            if not isinstance(ac, dict):
                continue
            hx = str(ac.get("hex") or "").lower()
            if hx and hx in index:
                old = merged[index[hx]]
                if ac.get("seen_pos", ac.get("seen", 1e9)) < old.get("seen_pos", old.get("seen", 1e9)):
                    merged[index[hx]] = ac
                continue
            if hx:
                index[hx] = len(merged)
            merged.append(ac)
    out["aircraft"] = merged
    return out


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


# --------------------------------------------------------------------------- geometry
def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def bearing_deg(lat1, lon1, lat2, lon2):
    """Initial bearing from point 1 to point 2, 0..360 (0 = north)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


# --------------------------------------------------------------------------- airlines + silhouettes
_airlines = {"key": None, "data": {}}
_CALLSIGN_RE = re.compile(r"^([A-Z]{3})(\d[A-Z0-9]{0,3}|[A-Z0-9]{1,4})$")   # ICAO airline callsign: 3 letters + flight id


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def airline_sources(cfg):
    files = [os.path.join(DATA_DIR, "airlines_builtin.json")]
    if cfg_bool(cfg, "DEMO"):
        files.append(os.path.join(DEMO_DIR, "airlines.json"))
    return files


def load_airlines(cfg):
    """Merge curated built-in list < demo list. Cached by file mtimes."""
    files = airline_sources(cfg)
    key = tuple((f, os.path.getmtime(f) if os.path.exists(f) else 0) for f in files)
    if _airlines["key"] != key:
        merged = {}
        for f in files:
            merged.update(_read_json(f))
        _airlines.update(key=key, data=merged)
    return _airlines["data"]


def airline_for(callsign, airlines):
    """('AFR', {'name': 'Air France', 'iata': 'AF'}) for 'AFR1234', or (None, None)."""
    cs = (callsign or "").strip().upper()
    m = _CALLSIGN_RE.match(cs)
    if not m:
        return None, None
    icao = m.group(1)
    info = airlines.get(icao)
    return (icao, info) if info else (icao, None)


_types = {"key": None, "data": {}, "updated": None}


def types_file(cfg):
    return os.path.join(cfg.get("USER_DATA_DIR", DEFAULTS["USER_DATA_DIR"]), "data", "types.json")


def load_types(cfg):
    """Optional downloaded type list ({"types": {"A320": [long name, "L2J", "M"], ...}}), cached by mtime."""
    path = types_file(cfg)
    try:
        key = (path, os.path.getmtime(path))
    except OSError:
        key = (path, 0)
    if _types["key"] != key:
        raw = _read_json(path) if key[1] else {}
        data = raw.get("types") if isinstance(raw.get("types"), dict) else {}
        _types.update(key=key, data=data, updated=raw.get("updated"))
    return _types["data"]


def describe_type(ac, types=None):
    """Silhouette class + variant, military flag and a model name for one aircraft.json entry."""
    code = (ac.get("t") or "").upper()
    entry = (types or {}).get(code)
    long_name, desc, wtc = (entry + [None, None, None])[:3] if isinstance(entry, list) else (None, None, None)
    shape, variant = aircraft.classify(code, ac.get("category"), long_name, desc, wtc)
    return {
        "shape": shape,
        "variant": variant,
        "military": aircraft.is_military(shape, ac.get("dbFlags")),
        "type_name": aircraft.type_name(code, {code: long_name} if long_name else None),
    }


# --------------------------------------------------------------------------- planes
def build_planes(data, lat, lon, radius_km, airlines=None, photo_lookup=None, demo=False, types=None, route_lookup=None,
                 aircraft_lookup=None):
    """Return (planes_in_radius_sorted_by_distance, total_with_position)."""
    airlines = airlines or {}
    planes, total = [], 0
    for ac in data.get("aircraft", []):
        if "lat" not in ac or "lon" not in ac:
            continue
        if ac.get("seen_pos", 0) > MAX_POSITION_AGE_S:
            continue
        total += 1
        dist = haversine_km(lat, lon, ac["lat"], ac["lon"])
        if dist > radius_km:
            continue
        alt = ac.get("alt_baro", ac.get("alt_geom"))
        on_ground = alt == "ground"
        flight = (ac.get("flight") or "").strip()
        icao, info = airline_for(flight, airlines)
        photo, credit, link = None, None, None
        if demo and ac.get("demo_photo"):
            photo, credit = ac["demo_photo"], "DEMO ILLUSTRATION"
        elif photo_lookup is not None:
            found = photo_lookup(ac.get("hex"))
            if found:
                photo, credit, link = "/api/photo/%s" % ac.get("hex"), found.get("photographer"), found.get("link")
        if demo and ac.get("demo_route"):
            route = ac["demo_route"]
        else:
            route = route_lookup(flight) if route_lookup is not None else None
            route = route_plausible(route, ac["lat"], ac["lon"], ac.get("track"), ac.get("gs"))
        # The decoder only knows the type and the registration when its aircraft database has the airframe. When it
        # does not, ask adsbdb.com (by the aircraft's hex code) so the model is still shown and the silhouette fits.
        reg, code, found = ac.get("r"), ac.get("t"), None
        if aircraft_lookup is not None and not (reg and code) and not (demo and ac.get("t")):
            found = aircraft_lookup(ac.get("hex"))
            if found:
                reg = reg or found.get("registration")
                code = code or found.get("icao_type")
        kind = describe_type(dict(ac, t=code) if code != ac.get("t") else ac, types)
        if not kind["type_name"] and found and found.get("type"):
            kind["type_name"] = " ".join(x for x in (found.get("manufacturer"), found.get("type")) if x)
        planes.append({
            "hex": ac.get("hex", ""),
            "flight": flight,
            "registration": reg,
            "type": code,
            "type_name": kind["type_name"],
            "shape": kind["shape"],
            "variant": kind["variant"],
            "military": kind["military"],
            "airline_icao": icao if info else None,
            "airline": info.get("name") if info else ("MILITARY" if kind["military"] else None),
            "alt_ft": 0 if on_ground else alt,
            "on_ground": on_ground,
            "gs_kt": ac.get("gs"),
            "track": ac.get("track"),
            "vrate_fpm": ac.get("baro_rate", ac.get("geom_rate")),
            "distance_km": round(dist, 2),
            "bearing": round(bearing_deg(lat, lon, ac["lat"], ac["lon"])),
            "photo": photo,
            "photo_credit": credit,
            "photo_link": link,
            "route": route,
        })
    planes.sort(key=lambda p: p["distance_km"])
    return planes, total


# --------------------------------------------------------------------------- slow lookups (photos, routes)
class ThrottledLookup(object):
    """Non-blocking cache in front of a slow, rate-limited web service.

    get(key) answers at once from the cache and queues a request when the key is unknown or stale. One worker
    thread makes at most one request every `gap` seconds, which is what services such as Planespotters need
    (they answer 403 to bursts). fetch(key) returns (value, ok):
      ok True,  value       -> found:        kept for `found_ttl` seconds (None = until restart)
      ok True,  value None  -> not found:    asked again after `miss_retry`
      ok False              -> no answer (403, timeout, no internet): asked again after `retry`, and never
                               stored as "not found".
    """

    def __init__(self, fetch, gap, retry, miss_retry, found_ttl=None, max_queue=60, max_entries=1000):
        self.fetch, self.gap, self.retry, self.miss_retry, self.found_ttl = fetch, gap, retry, miss_retry, found_ttl
        self.max_entries = max_entries
        self.cache = {}                     # key -> {"value", "retry_at" (monotonic, None = settled), "queued"}
        self.lock = threading.Lock()
        self.queue = queue.Queue(maxsize=max_queue)
        self.worker = None

    def peek(self, key):
        with self.lock:
            e = self.cache.get(key)
            return e["value"] if e else None

    def get(self, key):
        if not key:
            return None
        now = time.monotonic()
        with self.lock:
            e = self.cache.get(key)
            if e and (e["queued"] or e["retry_at"] is None or now < e["retry_at"]):
                return e["value"]
            value = e["value"] if e else None
            self.cache[key] = {"value": value, "retry_at": now + self.retry, "queued": True}
            if self.worker is None:
                self.worker = threading.Thread(target=self._loop, daemon=True)
                self.worker.start()
        try:
            self.queue.put_nowait(key)
        except queue.Full:                  # a very busy sky: asked for again next time
            with self.lock:
                if key in self.cache:
                    self.cache[key]["queued"] = False
        return value

    def _loop(self):
        last = 0.0
        while True:
            key = self.queue.get()
            wait = self.gap - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
            try:
                value, ok = self.fetch(key)
            except Exception:               # never let a bad answer kill the worker
                value, ok = None, False
            last = time.monotonic()
            now = last
            if ok and value is not None:
                retry_at = None if self.found_ttl is None else now + self.found_ttl
            elif ok:
                retry_at = now + self.miss_retry
            else:
                value, retry_at = None, now + self.retry
            with self.lock:
                if len(self.cache) > self.max_entries:
                    self.cache.clear()
                self.cache[key] = {"value": value, "retry_at": retry_at, "queued": False}


# --------------------------------------------------------------------------- photos (Planespotters, optional, proxied so the tablet needs no internet)
_photo_bytes = {}     # hex -> (content_type, bytes)
_photo_lock = threading.Lock()
MAX_PHOTO_CACHE = 200
PHOTO_GAP_S = 2.0                   # Planespotters answers 403 to bursts: at most one request every 2 s
PHOTO_RETRY_S = 600                 # refused / failed: try again after 10 min
PHOTO_NOPHOTO_RETRY_S = 86400       # no photo published today: look again tomorrow


def _photo_api(hex_code):
    """-> (meta|None, ok). ok is False when we could not get an answer (403, timeout, no internet)."""
    url = "https://api.planespotters.net/pub/photos/hex/%s" % hex_code
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ZenithBoard/%s (+https://github.com/regis57/ZenithBoard)" % VERSION})
        with urllib.request.urlopen(req, timeout=6) as resp:
            photos = json.load(resp).get("photos") or []
    except Exception:       # network is optional: never break the wall because of photos
        return None, False
    if not photos:
        return None, True
    p = photos[0]
    url = (p.get("thumbnail_large") or {}).get("src")
    if not url:
        return None, True
    return {"url": url, "photographer": p.get("photographer"), "link": p.get("link")}, True


_photos = ThrottledLookup(lambda k: _photo_api(k), PHOTO_GAP_S, PHOTO_RETRY_S, PHOTO_NOPHOTO_RETRY_S)


def lookup_photo(hex_code):
    """Non-blocking: the photo metadata we already have; a request is queued when it is missing."""
    return _photos.get(hex_code)


def fetch_photo_bytes(hex_code):
    with _photo_lock:
        if hex_code in _photo_bytes:
            return _photo_bytes[hex_code]
    meta = _photos.peek(hex_code)
    if not meta:
        return None
    try:
        req = urllib.request.Request(meta["url"], headers={"User-Agent": "ZenithBoard/%s" % VERSION})
        with urllib.request.urlopen(req, timeout=6) as resp:
            body = resp.read(2_000_000)
            ctype = resp.headers.get("Content-Type", "image/jpeg")
    except Exception:
        return None
    with _photo_lock:
        if len(_photo_bytes) >= MAX_PHOTO_CACHE:
            _photo_bytes.clear()
        _photo_bytes[hex_code] = (ctype, body)
    return ctype, body


# --------------------------------------------------------------------------- routes (adsbdb.com, optional)
# ADS-B itself never carries the origin or destination, so the route is looked up from the callsign on the free
# community database adsbdb.com. It is only an indication: a callsign can be reused for another route, and
# some flights are missing.
ROUTE_GAP_S = 1.5                   # at most one request every 1.5 s
ROUTE_RETRY_S = 60                  # no answer (error, timeout, no internet): try again after 1 min (a flight lasts minutes)
ROUTE_MISS_RETRY_S = 2 * 3600       # callsign not in the database
ROUTE_TTL_S = 12 * 3600             # a known route is looked up again after 12 h (callsigns get reused)
CALLSIGN_RE = re.compile(r"^[A-Z]{3}[0-9][0-9A-Z]{0,3}$")      # airline callsigns like DLH4YK; skips registrations and GA


def _airport(a):
    if not isinstance(a, dict):
        return None
    out = {"iata": str(a.get("iata_code") or ""), "icao": str(a.get("icao_code") or ""),
           "name": str(a.get("name") or ""), "city": str(a.get("municipality") or ""),
           "country": str(a.get("country_iso_name") or "")}
    for key, src in (("lat", "latitude"), ("lon", "longitude")):     # kept only to check the route is plausible, never shown
        v = a.get(src)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out[key] = float(v)
    return out if (out["name"] or out["city"] or out["iata"] or out["icao"]) else None


def parse_route(data):
    """adsbdb answer -> {"from": {...}, "to": {...}} or None."""
    resp = data.get("response") if isinstance(data, dict) else None
    fr = resp.get("flightroute") if isinstance(resp, dict) else None
    if not isinstance(fr, dict):
        return None
    origin, dest = _airport(fr.get("origin")), _airport(fr.get("destination"))
    return {"from": origin, "to": dest} if (origin or dest) else None


def _same_airport(a, b):
    for k in ("icao", "iata"):
        if a.get(k) and a.get(k) == b.get(k):
            return True
    return bool(a.get("name")) and a.get("name") == b.get("name") and a.get("city") == b.get("city")


def _leg_distance_km(plat, plon, a, b):
    """Distance from the point to the great-circle segment a-b (both (lat, lon))."""
    r = 6371.0088
    length = haversine_km(a[0], a[1], b[0], b[1])
    d13 = haversine_km(a[0], a[1], plat, plon) / r
    diff = math.radians(bearing_deg(a[0], a[1], plat, plon) - bearing_deg(a[0], a[1], b[0], b[1]))
    xt = math.asin(max(-1.0, min(1.0, math.sin(d13) * math.sin(diff)))) * r
    along = r * math.atan2(math.sin(d13) * math.cos(diff), math.cos(d13))
    if along < 0:
        return haversine_km(plat, plon, a[0], a[1])
    if along > length:
        return haversine_km(plat, plon, b[0], b[1])
    return abs(xt)


ROUTE_CORRIDOR_MIN_KM = 120         # a real flight may leave the straight line by this much (weather, air traffic control)...
ROUTE_CORRIDOR_FRACTION = 0.2       # ...or by this share of the route length when that is more
ROUTE_HEADING_MAX_DEG = 100         # flying more than this away from the destination: probably the other direction of the callsign


def route_plausible(route, plat, plon, track=None, gs=None):
    """The database knows callsigns, not flights: a callsign can be reused for another route. Drop an answer that cannot
    be this flight: same airport twice, an aircraft far from the line between the two airports, or one flying away from
    the destination. When it cannot be checked (no airport position) the route is kept."""
    if not route:
        return route
    a, b = route.get("from"), route.get("to")
    if a and b and _same_airport(a, b):
        return None
    if not (a and b and "lat" in a and "lon" in a and "lat" in b and "lon" in b):
        return route
    pa, pb = (a["lat"], a["lon"]), (b["lat"], b["lon"])
    length = haversine_km(pa[0], pa[1], pb[0], pb[1])
    if length < 30:
        return None
    if _leg_distance_km(plat, plon, pa, pb) > max(ROUTE_CORRIDOR_MIN_KM, ROUTE_CORRIDOR_FRACTION * length):
        return None
    far = min(haversine_km(plat, plon, pa[0], pa[1]), haversine_km(plat, plon, pb[0], pb[1])) > 50
    if far and isinstance(track, (int, float)) and isinstance(gs, (int, float)) and gs >= 100:
        off = abs((track - bearing_deg(plat, plon, pb[0], pb[1]) + 180) % 360 - 180)
        if off > ROUTE_HEADING_MAX_DEG:
            return None
    return route


def _route_api(callsign):
    """-> (route|None, ok). ok is False when we could not get an answer."""
    url = "https://api.adsbdb.com/v0/callsign/%s" % callsign
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ZenithBoard/%s (+https://github.com/regis57/ZenithBoard)" % VERSION})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return parse_route(json.load(resp)), True
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            print("route lookup %s: HTTP %s, retrying in %d s" % (callsign, exc.code, ROUTE_RETRY_S), file=sys.stderr, flush=True)
        return None, exc.code == 404            # 404 = unknown callsign (a real answer); anything else = try later
    except Exception as exc:
        print("route lookup %s failed (%s), retrying in %d s" % (callsign, exc, ROUTE_RETRY_S), file=sys.stderr, flush=True)
        return None, False


_routes = ThrottledLookup(lambda k: _route_api(k), ROUTE_GAP_S, ROUTE_RETRY_S, ROUTE_MISS_RETRY_S, found_ttl=ROUTE_TTL_S)


def lookup_route(callsign):
    """Non-blocking: the route we already know for this callsign; a request is queued when it is missing."""
    cs = (callsign or "").strip().upper()
    return _routes.get(cs) if CALLSIGN_RE.match(cs) else None


# --------------------------------------------------------------------------- aircraft model (adsbdb.com, optional)
# Fallback for aircraft whose type / registration the decoder does not know: adsbdb.com is asked by hex code.
AIRCRAFT_GAP_S = 2.0
AIRCRAFT_RETRY_S = 60
AIRCRAFT_MISS_RETRY_S = 24 * 3600
AIRCRAFT_TTL_S = 7 * 24 * 3600
HEX_RE = re.compile(r"^[0-9A-F]{6}$")


def parse_aircraft(data):
    """adsbdb /aircraft answer -> {"icao_type", "type", "manufacturer", "registration"} or None."""
    resp = data.get("response") if isinstance(data, dict) else None
    ac = resp.get("aircraft") if isinstance(resp, dict) else None
    if not isinstance(ac, dict):
        return None
    out = {"icao_type": str(ac.get("icao_type") or "").upper(), "type": str(ac.get("type") or ""),
           "manufacturer": str(ac.get("manufacturer") or ""), "registration": str(ac.get("registration") or "")}
    return out if (out["icao_type"] or out["type"] or out["registration"]) else None


def _aircraft_api(hex_code):
    """-> (info|None, ok). ok is False when we could not get an answer."""
    url = "https://api.adsbdb.com/v0/aircraft/%s" % hex_code
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ZenithBoard/%s (+https://github.com/regis57/ZenithBoard)" % VERSION})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return parse_aircraft(json.load(resp)), True
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            print("aircraft lookup %s: HTTP %s, retrying in %d s" % (hex_code, exc.code, AIRCRAFT_RETRY_S), file=sys.stderr, flush=True)
        return None, exc.code == 404
    except Exception as exc:
        print("aircraft lookup %s failed (%s), retrying in %d s" % (hex_code, exc, AIRCRAFT_RETRY_S), file=sys.stderr, flush=True)
        return None, False


_aircraft = ThrottledLookup(lambda k: _aircraft_api(k), AIRCRAFT_GAP_S, AIRCRAFT_RETRY_S, AIRCRAFT_MISS_RETRY_S, found_ttl=AIRCRAFT_TTL_S)


def lookup_aircraft(hex_code):
    """Non-blocking: what we already know about this airframe; a request is queued when it is missing."""
    h = (hex_code or "").strip().upper()
    return _aircraft.get(h) if HEX_RE.match(h) else None


# --------------------------------------------------------------------------- HTTP
def public_config(cfg):
    units = cfg.get("UNITS", "metric")
    if units not in ("metric", "imperial"):
        units = "metric"
    theme = cfg.get("THEME", "amber")
    return {
        "version": VERSION,
        "server_id": SERVER_ID,
        "units": units,
        "theme": theme if theme in THEMES else "amber",
        "radius": cfg_float(cfg, "RADIUS", 10),
        "radius_presets": RADIUS_PRESETS,
        "cycle_seconds": max(2, cfg_float(cfg, "CYCLE_SECONDS", 6)),
        "show_photos": cfg_bool(cfg, "SHOW_PHOTOS"),
        "display_mode": "flap" if str(cfg.get("DISPLAY_MODE", "dots")).lower() == "flap" else "dots",
        "demo": cfg_bool(cfg, "DEMO"),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "ZenithBoard/" + VERSION

    def log_message(self, fmt, *args):  # keep journald quiet
        pass

    def _send(self, code, body, ctype="application/json", cache="no-store"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path
        cfg = load_config()
        if path == "/api/config":
            return self._send(200, public_config(cfg))
        if path == "/api/health":
            return self._send(200, {"ok": True, "version": VERSION})
        if path == "/api/planes":
            return self._planes(cfg, parse_qs(url.query))
        if path.startswith("/api/photo/"):
            got = fetch_photo_bytes(path[len("/api/photo/"):].lower()) if cfg_bool(cfg, "SHOW_PHOTOS") else None
            return self._send(200, got[1], got[0], cache="max-age=3600") if got else self._send(404, b"", "text/plain")
        if path.startswith("/demo/") and cfg_bool(cfg, "DEMO"):
            return self._file(DEMO_DIR, path[len("/demo/"):])
        return self._static(path)

    def _planes(self, cfg, query):
        units = cfg.get("UNITS", "metric")
        try:
            radius_km = float(query["radius_km"][0])
        except (KeyError, ValueError, IndexError):
            radius_km = radius_to_km(cfg_float(cfg, "RADIUS", 10), units)
        radius_km = min(max(radius_km, 0.1), 500.0)
        path = aircraft_json_path(cfg)
        data = read_json(path)
        upath = uat_json_path(cfg)
        if upath:                                   # 978 MHz UAT: optional, never a reason to show an error
            udata = read_json(upath)
            if udata is not None:
                data = merge_aircraft(data or {}, udata)
        if data is None:
            return self._send(200, {"error": "no_data", "path": path, "server_id": SERVER_ID,
                                    "planes": [], "total": 0})
        demo = cfg_bool(cfg, "DEMO")
        # DEMO_REAL_PHOTOS lets the demo ask Planespotters and adsbdb about its handful of real aircraft, so photos
        # and routes can be checked on a Pi that has no antenna yet. The invented aircraft keep their mock data.
        real_lookups = not demo or cfg_bool(cfg, "DEMO_REAL_PHOTOS")
        lookup = lookup_photo if cfg_bool(cfg, "SHOW_PHOTOS") and real_lookups else None
        route_lookup = lookup_route if cfg_bool(cfg, "SHOW_ROUTES") and real_lookups else None
        aircraft_lookup = lookup_aircraft if cfg_bool(cfg, "SHOW_ROUTES") and real_lookups else None
        planes, total = build_planes(data, cfg_float(cfg, "LAT", 0), cfg_float(cfg, "LON", 0), radius_km,
                                     load_airlines(cfg), lookup, demo, load_types(cfg), route_lookup, aircraft_lookup)
        return self._send(200, {"planes": planes, "total": total, "radius_km": radius_km,
                                "server_id": SERVER_ID, "updated": time.time()})

    def _static(self, path):
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        if rel.startswith("static/"):
            rel = rel[len("static/"):]
        return self._file(STATIC_DIR, rel)

    def _file(self, root, rel):
        full = os.path.realpath(os.path.join(root, rel))
        if not full.startswith(os.path.realpath(root) + os.sep) or not os.path.isfile(full):
            return self._send(404, b"not found", "text/plain")
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        with open(full, "rb") as fh:
            body = fh.read()
        text_like = ctype.startswith("text/") or ctype.endswith("javascript")
        return self._send(200, body, ctype + ("; charset=utf-8" if text_like else ""))


def main():
    cfg = load_config()
    port = int(os.environ.get("PORT") or cfg.get("PORT") or 8080)
    httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print("ZenithBoard FlightInfo %s listening on :%d (config: %s)" % (VERSION, port, CONFIG_FILE), flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
