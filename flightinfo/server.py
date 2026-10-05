#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ZenithBoard FlightInfo server.

Tiny, dependency-free (Python standard library only) web server that:
  * reads the decoder's aircraft.json (readsb or dump1090-fa),
  * keeps the aircraft that are inside the configured radius around the antenna,
  * adds airline name, aircraft silhouette class, optional logo and photo,
  * serves the dot-matrix wall (static/) and a small JSON API.

Configuration is read from /etc/zenithboard/config.env on every request (cached
by file modification time), so `zenithboard config ...` takes effect without a
restart.
"""
import json
import math
import mimetypes
import os
import re
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

VERSION = "0.2.0"
CONFIG_FILE = os.environ.get("ZENITHBOARD_CONFIG", "/etc/zenithboard/config.env")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DEMO_DIR = os.path.join(BASE_DIR, "demo")
DATA_DIR = os.path.join(BASE_DIR, "data")
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
    "SHOW_LOGOS": "1",
    "PORT": "8080",
    "AIRCRAFT_JSON": "",        # optional explicit path override
    "DEMO": "0",                # 1 = fictional demo airlines, logos and photos
    "USER_DATA_DIR": "/var/lib/zenithboard",   # logos/ and data/ added by the user live here
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
    user = cfg.get("USER_DATA_DIR", DEFAULTS["USER_DATA_DIR"])
    files = [os.path.join(user, "data", "airlines.json"), os.path.join(DATA_DIR, "airlines_builtin.json")]   # later files win
    if cfg_bool(cfg, "DEMO"):
        files.append(os.path.join(DEMO_DIR, "airlines.json"))
    return files


def load_airlines(cfg):
    """Merge downloaded full list < curated built-in list < demo list. Cached by file mtimes."""
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


TURBOPROP_TYPES = {"AT43", "AT45", "AT72", "AT73", "AT75", "AT76", "DH8A", "DH8B", "DH8C", "DH8D", "SF34", "SB20",
                   "JS31", "JS32", "JS41", "B190", "BE20", "BE99", "C208", "PC12", "PC24x", "E120", "F50", "F27",
                   "D328", "SH36", "SW4", "C441", "TBM7", "TBM8", "TBM9", "P180", "AN24", "AN26", "L410", "DHC6"}
BIZJET_TYPES = {"C25A", "C25B", "C25C", "C25M", "C510", "C525", "C550", "C560", "C56X", "C680", "C68A", "C700", "C750",
                "CL30", "CL35", "CL60", "GL5T", "GL6T", "GLEX", "GLF2", "GLF3", "GLF4", "GLF5", "GLF6", "FA50",
                "FA7X", "FA8X", "F900", "F2TH", "LJ35", "LJ45", "LJ60", "E50P", "E55P", "H25B", "HDJT", "PRM1", "SF50"}
WIDEBODY_TYPES = {"A332", "A333", "A338", "A339", "A342", "A343", "A345", "A346", "A359", "A35K", "A388", "A306", "A310",
                  "B742", "B743", "B744", "B748", "B762", "B763", "B764", "B772", "B773", "B77L", "B77W", "B778", "B779",
                  "B788", "B789", "B78X", "MD11", "IL96", "A124", "A225"}


def shape_for(ac):
    """Silhouette class: heli | light | turboprop | bizjet | wide | narrow."""
    t = (ac.get("t") or "").upper()
    cat = (ac.get("category") or "").upper()
    if cat == "A7" or t in {"EC35", "EC45", "EC30", "EC20", "H135", "H145", "H160", "H125", "A109", "A139", "A169",
                            "AS50", "AS55", "AS65", "B06", "B407", "B412", "B429", "R22", "R44", "R66", "S76", "S92",
                            "H60", "NH90", "EC55", "EC75", "AS32", "AS3B", "MI8", "KA32"}:
        return "heli"
    if t in TURBOPROP_TYPES:
        return "turboprop"
    if t in BIZJET_TYPES:
        return "bizjet"
    if t in WIDEBODY_TYPES or cat == "A5":
        return "wide"
    if cat == "A1":
        return "light"
    if cat == "A2" and t not in {"A318", "A319", "A320", "A321", "B737", "B738", "B739", "B38M", "E190", "E170"}:
        return "bizjet"
    return "narrow"


# --------------------------------------------------------------------------- planes
def build_planes(data, lat, lon, radius_km, airlines=None, photo_lookup=None, demo=False):
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
        photo, credit = None, None
        if demo and ac.get("demo_photo"):
            photo, credit = ac["demo_photo"], "DEMO ILLUSTRATION"
        elif photo_lookup is not None:
            found = photo_lookup(ac.get("hex"))
            if found:
                photo, credit = "/api/photo/%s" % ac.get("hex"), found.get("photographer")
        planes.append({
            "hex": ac.get("hex", ""),
            "flight": flight,
            "registration": ac.get("r"),
            "type": ac.get("t"),
            "shape": shape_for(ac),
            "airline_icao": icao if info else None,
            "airline": info.get("name") if info else None,
            "alt_ft": 0 if on_ground else alt,
            "on_ground": on_ground,
            "gs_kt": ac.get("gs"),
            "track": ac.get("track"),
            "vrate_fpm": ac.get("baro_rate", ac.get("geom_rate")),
            "distance_km": round(dist, 2),
            "bearing": round(bearing_deg(lat, lon, ac["lat"], ac["lon"])),
            "photo": photo,
            "photo_credit": credit,
        })
    planes.sort(key=lambda p: p["distance_km"])
    return planes, total


# --------------------------------------------------------------------------- logos (dot-matrix bitmaps, never bundled for real airlines)
_ICAO_RE = re.compile(r"^[A-Z0-9]{2,4}$")


def logo_dirs(cfg):
    user = cfg.get("USER_DATA_DIR", DEFAULTS["USER_DATA_DIR"])
    dirs = [os.path.join(user, "logos")]
    if cfg_bool(cfg, "DEMO"):
        dirs.append(os.path.join(DEMO_DIR, "logos"))
    return dirs


def find_logo(icao, cfg):
    if not _ICAO_RE.match(icao or ""):
        return None
    for d in logo_dirs(cfg):
        path = os.path.join(d, icao + ".json")
        if os.path.isfile(path):
            data = _read_json(path)
            if {"w", "h", "palette", "rows"} <= set(data):
                return data
    return None


# --------------------------------------------------------------------------- photos (Planespotters, optional, proxied so the tablet needs no internet)
_photo_cache = {}     # hex -> {"url":..., "photographer":...} | None
_photo_bytes = {}     # hex -> (content_type, bytes)
_photo_lock = threading.Lock()
MAX_PHOTO_CACHE = 200


def _fetch_photo_meta(hex_code):
    url = "https://api.planespotters.net/pub/photos/hex/%s" % hex_code
    meta = None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ZenithBoard/%s" % VERSION})
        with urllib.request.urlopen(req, timeout=4) as resp:
            photos = json.load(resp).get("photos") or []
            if photos:
                p = photos[0]
                meta = {"url": p.get("thumbnail_large", {}).get("src"), "photographer": p.get("photographer")}
                if not meta["url"]:
                    meta = None
    except Exception:  # network is optional: never break the wall because of photos
        pass
    with _photo_lock:
        if len(_photo_cache) > MAX_PHOTO_CACHE * 5:
            _photo_cache.clear()
        _photo_cache[hex_code] = meta


def lookup_photo(hex_code):
    """Non-blocking: cached metadata, or None while a background fetch runs."""
    if not hex_code:
        return None
    with _photo_lock:
        if hex_code in _photo_cache:
            return _photo_cache[hex_code]
        _photo_cache[hex_code] = None  # mark as in-flight
    threading.Thread(target=_fetch_photo_meta, args=(hex_code,), daemon=True).start()
    return None


def fetch_photo_bytes(hex_code):
    with _photo_lock:
        if hex_code in _photo_bytes:
            return _photo_bytes[hex_code]
        meta = _photo_cache.get(hex_code)
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
        "show_logos": cfg_bool(cfg, "SHOW_LOGOS"),
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
        if path.startswith("/api/logo/"):
            logo = find_logo(path[len("/api/logo/"):].upper(), cfg) if cfg_bool(cfg, "SHOW_LOGOS") else None
            return self._send(200, logo or {}, cache="max-age=60")      # {} = no logo (not a 404: keeps browser consoles clean)
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
        lookup = lookup_photo if cfg_bool(cfg, "SHOW_PHOTOS") and not demo else None
        planes, total = build_planes(data, cfg_float(cfg, "LAT", 0), cfg_float(cfg, "LON", 0), radius_km,
                                     load_airlines(cfg), lookup, demo)
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
