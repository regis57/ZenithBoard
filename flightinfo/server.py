#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ZenithBoard FlightInfo server.

Tiny, dependency-free (Python standard library only) web server that:
  * reads the decoder's aircraft.json (readsb or dump1090-fa),
  * keeps the aircraft that are inside the configured radius around the antenna,
  * serves the dot-matrix wall (static/) and a small JSON API.

Configuration is read from /etc/zenithboard/config.env on every request (cached
by file modification time), so `zenithboard config ...` takes effect without a
restart.
"""
import json
import math
import mimetypes
import os
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

VERSION = "0.1.0"
CONFIG_FILE = os.environ.get("ZENITHBOARD_CONFIG", "/etc/zenithboard/config.env")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
SERVER_ID = str(int(time.time()))  # changes on restart -> browsers reload themselves

KM_PER_MI = 1.609344
RADIUS_PRESETS = [1, 2, 5, 10, 15, 30, 50]
MAX_POSITION_AGE_S = 30  # ignore aircraft whose position is older than this

DEFAULTS = {
    "UNITS": "metric",          # metric | imperial
    "LAT": "0",
    "LON": "0",
    "DECODER": "readsb",        # readsb | dump1090-fa
    "RADIUS": "10",             # in km (metric) or miles (imperial)
    "CYCLE_SECONDS": "6",
    "SHOW_PHOTOS": "0",
    "PORT": "8080",
    "AIRCRAFT_JSON": "",        # optional explicit path override
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


# --------------------------------------------------------------------------- planes
def build_planes(data, lat, lon, radius_km):
    """Return (planes_in_radius_sorted_by_distance, total_with_position)."""
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
        planes.append({
            "hex": ac.get("hex", ""),
            "flight": (ac.get("flight") or "").strip(),
            "registration": ac.get("r"),
            "type": ac.get("t"),
            "alt_ft": 0 if on_ground else alt,
            "on_ground": on_ground,
            "gs_kt": ac.get("gs"),
            "track": ac.get("track"),
            "vrate_fpm": ac.get("baro_rate", ac.get("geom_rate")),
            "distance_km": round(dist, 2),
            "bearing": round(bearing_deg(lat, lon, ac["lat"], ac["lon"])),
            "photo": get_photo(ac.get("hex")) if _photos_enabled() else None,
        })
    planes.sort(key=lambda p: p["distance_km"])
    return planes, total


# --------------------------------------------------------------------------- photos (optional)
_photo_cache = {}
_photo_lock = threading.Lock()


def _photos_enabled():
    return load_config().get("SHOW_PHOTOS", "0") in ("1", "true", "yes", "on")


def _fetch_photo(hex_code):
    url = "https://api.planespotters.net/pub/photos/hex/%s" % hex_code
    src = None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ZenithBoard/%s" % VERSION})
        with urllib.request.urlopen(req, timeout=4) as resp:
            photos = json.load(resp).get("photos") or []
            if photos:
                src = photos[0].get("thumbnail_large", {}).get("src")
    except Exception:  # network is optional: never break the wall because of photos
        pass
    with _photo_lock:
        _photo_cache[hex_code] = src


def get_photo(hex_code):
    """Non-blocking: returns a cached URL, or None while a background fetch runs."""
    if not hex_code:
        return None
    with _photo_lock:
        if hex_code in _photo_cache:
            return _photo_cache[hex_code]
        _photo_cache[hex_code] = None  # mark as in-flight
    threading.Thread(target=_fetch_photo, args=(hex_code,), daemon=True).start()
    return None


# --------------------------------------------------------------------------- HTTP
def public_config(cfg):
    units = cfg.get("UNITS", "metric")
    if units not in ("metric", "imperial"):
        units = "metric"
    return {
        "version": VERSION,
        "server_id": SERVER_ID,
        "units": units,
        "radius": cfg_float(cfg, "RADIUS", 10),
        "radius_presets": RADIUS_PRESETS,
        "cycle_seconds": max(2, cfg_float(cfg, "CYCLE_SECONDS", 6)),
        "show_photos": _photos_enabled(),
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
        if url.path == "/api/config":
            return self._send(200, public_config(load_config()))
        if url.path == "/api/health":
            return self._send(200, {"ok": True, "version": VERSION})
        if url.path == "/api/planes":
            return self._planes(parse_qs(url.query))
        return self._static(url.path)

    def _planes(self, query):
        cfg = load_config()
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
        planes, total = build_planes(data, cfg_float(cfg, "LAT", 0), cfg_float(cfg, "LON", 0), radius_km)
        return self._send(200, {"planes": planes, "total": total, "radius_km": radius_km,
                                "server_id": SERVER_ID, "updated": time.time()})

    def _static(self, path):
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        if rel.startswith("static/"):
            rel = rel[len("static/"):]
        full = os.path.realpath(os.path.join(STATIC_DIR, rel))
        if not full.startswith(os.path.realpath(STATIC_DIR) + os.sep) or not os.path.isfile(full):
            return self._send(404, b"not found", "text/plain")
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        with open(full, "rb") as fh:
            body = fh.read()
        return self._send(200, body, ctype + ("; charset=utf-8" if ctype.startswith("text/") or ctype.endswith("javascript") else ""))


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
