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
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

VERSION = "0.2.2"
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
    "PORT": "8080",
    "AIRCRAFT_JSON": "",        # optional explicit path override
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
def build_planes(data, lat, lon, radius_km, airlines=None, photo_lookup=None, demo=False, types=None):
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
        kind = describe_type(ac, types)
        planes.append({
            "hex": ac.get("hex", ""),
            "flight": flight,
            "registration": ac.get("r"),
            "type": ac.get("t"),
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
        })
    planes.sort(key=lambda p: p["distance_km"])
    return planes, total


# --------------------------------------------------------------------------- photos (Planespotters, optional, proxied so the tablet needs no internet)
# Planespotters answers 403 when it is asked too quickly, so every lookup goes through ONE worker thread that
# makes at most one request every PHOTO_GAP_S. A lookup that failed (403, timeout, no internet) is retried
# later instead of being remembered as "this aircraft has no photo".
_photo_cache = {}     # hex -> {"meta": {...}|None, "retry_at": float|None}   retry_at None = settled
_photo_bytes = {}     # hex -> (content_type, bytes)
_photo_lock = threading.Lock()
_photo_queue = queue.Queue(maxsize=60)
_photo_worker = None
MAX_PHOTO_CACHE = 200
PHOTO_GAP_S = 2.0           # minimum delay between two Planespotters requests
PHOTO_RETRY_S = 600         # try again 10 min after a refused or failed lookup
PHOTO_NOPHOTO_RETRY_S = 86400   # an aircraft with no photo today may have one tomorrow


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


def _photo_loop():
    last = 0.0
    while True:
        hex_code = _photo_queue.get()
        wait = PHOTO_GAP_S - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)
        meta, ok = _photo_api(hex_code)
        last = time.monotonic()
        if ok:
            retry_at = None if meta else time.monotonic() + PHOTO_NOPHOTO_RETRY_S
        else:
            meta, retry_at = None, time.monotonic() + PHOTO_RETRY_S
        with _photo_lock:
            if len(_photo_cache) > MAX_PHOTO_CACHE * 5:
                _photo_cache.clear()
            _photo_cache[hex_code] = {"meta": meta, "retry_at": retry_at, "queued": False}


def lookup_photo(hex_code):
    """Non-blocking: the metadata we already have, and a queued request when it is missing or stale."""
    global _photo_worker
    if not hex_code:
        return None
    now = time.monotonic()
    with _photo_lock:
        e = _photo_cache.get(hex_code)
        if e and (e["retry_at"] is None or now < e["retry_at"] or e["queued"]):
            return e["meta"]
        meta = e["meta"] if e else None
        _photo_cache[hex_code] = {"meta": meta, "retry_at": now + PHOTO_RETRY_S, "queued": True}
        if _photo_worker is None:
            _photo_worker = threading.Thread(target=_photo_loop, daemon=True)
            _photo_worker.start()
    try:
        _photo_queue.put_nowait(hex_code)
    except queue.Full:      # a very busy sky: this aircraft is simply asked for again next time
        with _photo_lock:
            if hex_code in _photo_cache:
                _photo_cache[hex_code]["queued"] = False
    return meta


def fetch_photo_bytes(hex_code):
    with _photo_lock:
        if hex_code in _photo_bytes:
            return _photo_bytes[hex_code]
        e = _photo_cache.get(hex_code)
        meta = e["meta"] if e else None
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
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return self._send(200, {"error": "no_data", "path": path, "server_id": SERVER_ID,
                                    "planes": [], "total": 0})
        demo = cfg_bool(cfg, "DEMO")
        # DEMO_REAL_PHOTOS lets the demo ask Planespotters for its handful of real aircraft, so photos can be
        # checked on a Pi that has no antenna yet. The invented aircraft keep their mock pictures.
        real_photos = not demo or cfg_bool(cfg, "DEMO_REAL_PHOTOS")
        lookup = lookup_photo if cfg_bool(cfg, "SHOW_PHOTOS") and real_photos else None
        planes, total = build_planes(data, cfg_float(cfg, "LAT", 0), cfg_float(cfg, "LON", 0), radius_km,
                                     load_airlines(cfg), lookup, demo, load_types(cfg))
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
