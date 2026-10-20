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
import os
import queue
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

VERSION = "0.36.0"
CONFIG_FILE = os.environ.get("ZENITHBOARD_CONFIG", "/etc/zenithboard/config.env")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
STATS_DIR = os.environ.get("ZENITHBOARD_STATS_DIR", "/var/lib/zenithboard/stats")   # written by the stats timer
SOCIAL_DIR = os.environ.get("ZENITHBOARD_SOCIAL_DIR", "/var/lib/zenithboard/social")   # `zenithboard social test` leaves preview.png or preview.jpg here


def social_preview_name():
    """preview.png (the dot-matrix look) or preview.jpg (split-flap with a map): the newer, if both are there."""
    got = []
    for n in ("preview.png", "preview.jpg"):
        try:
            got.append((os.path.getmtime(os.path.join(SOCIAL_DIR, n)), n))
        except OSError:
            pass                                 # that look was never drawn
    return max(got)[1] if got else "preview.png"
DEMO_DIR = os.path.join(BASE_DIR, "demo")
DATA_DIR = os.path.join(BASE_DIR, "data")
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
import aircraft  # noqa: E402  (silhouette class per aircraft type)

SERVER_ID = str(int(time.time()))  # changes on restart -> browsers reload themselves

KM_PER_MI = 1.609344
RADIUS_PRESETS = [1, 2, 5, 10, 15, 30, 50]
THEMES = ("amber", "green", "red", "white", "turquoise")      # 0.23.0: the dark blue (#0404e2) is gone, turquoise stays
MAX_POSITION_AGE_S = 30  # ignore aircraft whose position is older than this

DEFAULTS = {
    "UNITS": "metric",          # metric | imperial
    "THEME": "amber",           # amber | green | red | white | turquoise
    "LAT": "0",
    "LON": "0",
    "DECODER": "readsb",        # readsb | dump1090-fa
    "RADIUS": "10",             # in km (metric) or miles (imperial)
    "CYCLE_SECONDS": "14",
    "SHOW_PHOTOS": "1",
    "FLAGS": "1",               # the registration and maker flags on the dot-matrix wall
    "STATS": "0",               # the 15-minute statistics timer; /stats and /api/stats say so when it is off
    "DISPLAY_MODE": "dots",     # dots (dot matrix) | flap (split-flap airport board)
    "SHOW_ROUTES": "1",         # where the flight comes from / goes to (looked up by callsign on adsbdb.com)
    "LOCAL_DB": "0",            # 0.26.0: read registrations and models from tar1090's aircraft database on this Pi
    "LOCAL_DB_DIR": "/usr/local/share/tar1090/git-db/db",
    "PORT": "8080",
    "BIND_ADDRESS": "0.0.0.0",  # the interface the wall listens on; 127.0.0.1 keeps it to this Pi (a reverse proxy, say)
    "ALLOW_FROM": "private",    # who may read the wall: private (home networks only), any, or networks like 10.8.0.0/24,192.168.1.0/24
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


PRESET_KEYS = ("units", "radius", "cycle", "theme", "mode", "flags")


def presets_of(cfg):
    """The per-tablet presets (0.21.0): PRESET_KITCHEN="theme=green mode=flap" -> {"kitchen": {"theme": "green", ...}}.
    Only the tablet's own keys, so a preset can never set anything of the server's."""
    out = {}
    for k, v in cfg.items():
        if not k.startswith("PRESET_") or not re.match(r"^PRESET_[A-Z][A-Z0-9]{0,15}$", k):
            continue
        pairs = {}
        for pair in str(v).split():
            name, _, val = pair.partition("=")
            if name in PRESET_KEYS and val:
                pairs[name] = val[:32]
        if pairs:
            out[k[7:].lower()] = pairs
    return out


def cfg_float(cfg, key, default):
    try:
        return float(cfg.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def cfg_bool(cfg, key, default="0"):
    # A Pi installed before a setting existed has no line for it, so a setting that should start life switched
    # on passes its own default here rather than inheriting "off" from an older config file.
    return str(cfg.get(key, default)).lower() in ("1", "true", "yes", "on")


# --------------------------------------------------------------------------- statistics
# The stats timer (lib/stats.sh) writes one CSV line every fifteen minutes and one file of aircraft seen per day.
# This turns them into what the /stats page and the terminal show: the last 24 hours by hour, thirty days by day,
# and today's headline numbers. It reads; it never writes.
import csv
import datetime


def _count_lines(path, default):
    """Non-empty lines of a file, or `default` when it cannot be read."""
    try:
        with open(path, encoding="utf-8") as fh:
            return sum(1 for line in fh if line.strip())
    except OSError:
        return default


def read_stats(stats_dir=None, now=None):
    stats_dir = stats_dir or STATS_DIR
    now = now or datetime.datetime.now()
    path = os.path.join(stats_dir, "stats.csv")
    rows = []
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                try:
                    when = datetime.datetime.strptime(r["when"], "%Y-%m-%d %H:%M")
                    rows.append((when, int(float(r["messages"] or 0)), int(float(r["farthest_km"] or 0)),
                                 int(float(r["aircraft_pos"] or 0)), int(float(r["aircraft_seen"] or 0))))
                except (KeyError, ValueError, TypeError):
                    continue
    except OSError:
        return None
    rows.sort()
    # the last 24 hours, by hour of the day (the hour a sample was taken in)
    since = now - datetime.timedelta(hours=24)
    hours = [{"hour": h, "messages": 0, "samples": 0} for h in range(24)]
    for when, msgs, far, pos, seen in rows:
        if since < when <= now:
            hours[when.hour]["messages"] += msgs
            hours[when.hour]["samples"] += 1
    # thirty days, by day
    days = {}
    for when, msgs, far, pos, seen in rows:
        d = when.strftime("%Y-%m-%d")
        e = days.setdefault(d, {"day": d, "messages": 0, "farthest_km": 0, "aircraft": 0, "samples": 0})
        e["messages"] += msgs
        e["farthest_km"] = max(e["farthest_km"], far)
        e["aircraft"] = max(e["aircraft"], seen)
        e["samples"] += 1
    # the day's aircraft count is the day file's length, which is exact for that day; the CSV only carries the running
    # count, which stands when the day file is missing (removed after thirty days, or the sampler was off that day)
    for d, e in days.items():
        e["aircraft"] = _count_lines(os.path.join(stats_dir, "seen-" + d), e["aircraft"])
    day_list = [days[d] for d in sorted(days)][-30:]
    today = now.strftime("%Y-%m-%d")
    t = days.get(today) or {"day": today, "messages": 0, "farthest_km": 0, "aircraft": 0, "samples": 0}
    busiest = max(hours, key=lambda h: h["messages"]) if rows else None
    best = max(day_list, key=lambda d: d["farthest_km"]) if day_list else None
    # 0.31.0: the sky by hour, the last HEAT_DAYS days: the aircraft with a position, on average over the hour's samples
    heat_days = [(now - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(HEAT_DAYS - 1, -1, -1)]
    cells = {}
    for when, msgs, far_, pos, seen in rows:
        d = when.strftime("%Y-%m-%d")
        if d in heat_days:
            c = cells.setdefault((d, when.hour), [0, 0])
            c[0] += pos
            c[1] += 1
    heat = [{"day": d, "hours": [round(cells[(d, h)][0] / float(cells[(d, h)][1]), 1) if (d, h) in cells else None
                                 for h in range(24)]} for d in heat_days]
    far = read_farthest(stats_dir, now)
    if best:                              # the box's best day: were its details written down? (not before 0.22.0)
        far["best_box_detailed"] = os.path.exists(os.path.join(stats_dir, "farthest-" + best["day"]))
    return {
        "enabled": True,
        "samples": len(rows),
        "since": rows[0][0].strftime("%Y-%m-%d %H:%M") if rows else None,
        "today": {"day": today, "aircraft": t["aircraft"], "messages": t["messages"], "farthest_km": t["farthest_km"],
                  "busiest_hour": busiest["hour"] if busiest and busiest["messages"] else None,
                  "busiest_messages": busiest["messages"] if busiest else 0},
        "best": {"day": best["day"], "farthest_km": best["farthest_km"]} if best else None,
        "hours": hours,
        "days": day_list,
        "farthest": far,
        "heat": heat,
    }


HEAT_DAYS = 14
FLEET_TOP = 10
NOT_AIRCRAFT = {"GND", "TWR", "GRND", "SERV", "EMER"}
CALLSIGN_PREFIX = re.compile(r"^([A-Z]{3})\d")
# 0.36.0, the weekly posts: what is neither an airliner, a business jet nor military, by group
MISC_GROUPS = ("heli", "light", "glider", "balloon", "drone")
MISC_UNKNOWN = {"heli": "Helicopter, type unknown", "light": "Light aircraft, type unknown", "glider": "Glider, type unknown",
                "balloon": "Balloon or airship", "drone": "Drone"}
_icao_blocks, _icao_starts, _mil_ranges = [], [], []


def _top(counts, n=FLEET_TOP):
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def misc_group(shape, category):
    """The group of an aircraft that is not an airliner: by the wall's class, else by the emitter category it sends
    (DO-260: A7 rotorcraft, A1 light, B1 glider, B2 lighter than air, B4 ultralight, B6 unmanned)."""
    cat = (category or "").upper()
    if shape == "heli" or cat == "A7":
        return "heli"
    if shape == "glider" or cat == "B1":
        return "glider"
    if shape == "balloon" or cat == "B2":
        return "balloon"
    if cat == "B6":
        return "drone"
    if shape in ("light", "twinprop") or cat in ("A1", "B4"):
        return "light"
    return None


def _load_blocks():
    if not _icao_blocks:
        try:
            with open(os.path.join(DATA_DIR, "icao_countries.json"), encoding="utf-8") as fh:
                rows = json.load(fh)["blocks"]
            _icao_blocks.extend(sorted((int(a, 16), int(b, 16), cc, name) for a, b, cc, name in rows))
            _icao_starts.extend(b[0] for b in _icao_blocks)
        except (OSError, ValueError, KeyError, TypeError):
            pass
        try:
            with open(os.path.join(DATA_DIR, "military_ranges.json"), encoding="utf-8") as fh:
                _mil_ranges.extend((int(a, 16), int(b, 16)) for a, b in json.load(fh)["military"])
        except (OSError, ValueError, KeyError, TypeError):
            pass


def icao_country(hex_code):
    """The ISO code of the state an ICAO address is allocated to ("" when unknown): the country of registration."""
    _load_blocks()
    try:
        n = int(str(hex_code), 16)
    except ValueError:
        return ""
    import bisect                                 # thirty days of aircraft at each page load: a search, not a scan
    i = bisect.bisect_right(_icao_starts, n) - 1
    if i >= 0 and _icao_blocks[i][0] <= n <= _icao_blocks[i][1]:
        return _icao_blocks[i][2]
    return ""


def country_name(cc):
    _load_blocks()
    for _, _, c, name in _icao_blocks:
        if c == cc and cc:
            return name
    return "Unknown country"


def in_military_range(hex_code):
    """An address in a block allocated to military aircraft (tar1090-db's ranges, as tar1090 marks them)."""
    _load_blocks()
    try:
        n = int(str(hex_code), 16)
    except ValueError:
        return False
    return any(a <= n <= b for a, b in _mil_ranges)
_cargo = {}


def load_cargo():
    """{ICAO prefix: name} of the dedicated cargo airlines (0.35.0, flightinfo/data/cargo_airlines.json, each code
    checked against a published source). Airlines that fly cargo under their passenger prefix (Turkish, Qatar,
    Emirates) cannot be told apart by callsign and are not in it."""
    if not _cargo:
        try:
            with open(os.path.join(DATA_DIR, "cargo_airlines.json"), encoding="utf-8") as fh:
                _cargo.update({k: v["name"] for k, v in json.load(fh).items() if not k.startswith("_")})
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            pass
    return _cargo
_fleet_cache = {"key": None, "data": None}


def local_types(hexes, d):
    """0.31.0: {hex: type code} for many addresses at once (see local_info)."""
    return {h: v["t"] for h, v in local_info(hexes, d).items() if v.get("t")}


def local_info(hexes, d):
    """{hex: {"t": type code, "mil": military}} for many addresses at once, from tar1090's database in folder d, for
    the statistics' fleet files (lib/stats.sh). The addresses are walked in order and only the files on the current
    path are kept, so each file is read once, and the wall's own caches (local_aircraft) are neither used nor emptied.
    0.36.0: the military mark, the first character of the entry's flags ("10": military; "0010": the address is
    private), as tar1090 reads it (planeObject.js: data[2][0] == '1')."""
    out, path = {}, {}
    if not d:
        return out
    for h in sorted({str(x or "").strip().upper() for x in hexes}):
        if not HEX_RE.match(h):
            continue
        n = 1
        while n <= len(h):
            p = h[:n]
            if p not in path:
                for k in [k for k in path if not p.startswith(k)]:
                    del path[k]
                path[p] = _read_shard(d, p)
            shard = path[p]
            if not shard:
                break
            entry = shard.get(h[n:])
            if isinstance(entry, list) and entry:
                code = str(entry[1] or "").strip().upper() if len(entry) > 1 else ""
                flags = str(entry[2] or "") if len(entry) > 2 else ""
                if code or flags.startswith("1"):
                    out[h.lower()] = {"t": code, "mil": flags.startswith("1")}
                break
            if h[:n + 1] not in (shard.get("children") or []):
                break
            n += 1
    return out


def read_fleet(cfg, stats_dir=None, now=None, since=None):
    """0.31.0: who flew over in thirty days, from the fleet-DAY files the timer writes: the airlines and the types
    most seen (distinct aircraft each), and how high they were. An airline is named from its callsign's prefix, as the
    wall does; the type is the one the sample wrote: the decoder's, or tar1090's when `data localdb on` (looked up by
    the sample, never here: thirty days of addresses would take the wall's Pi 3B minutes). Cached until a fleet
    file changes."""
    stats_dir = stats_dir or STATS_DIR
    now = now or datetime.datetime.now()
    # since: the first day counted, YYYY-MM-DD (0.33.0, the weekly post); thirty days otherwise
    cut = since or (now - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    try:
        names = sorted(n for n in os.listdir(stats_dir) if n.startswith("fleet-") and n[6:] >= cut)
    except OSError:
        names = []
    key = (tuple((n, os.path.getmtime(os.path.join(stats_dir, n))) for n in names), cfg.get("UNITS"), stats_dir)
    if _fleet_cache["key"] == key:
        return _fleet_cache["data"]
    fleet = {}
    for n in names:                               # oldest first: a later day's values replace an earlier one's
        try:
            with open(os.path.join(stats_dir, n), encoding="utf-8") as fh:
                for line in fh:
                    f = line.rstrip("\n").split("\t")
                    if len(f) < 4 or not HEX_RE.match(f[0].upper()):
                        continue
                    # flight, altitude, type; since 0.36.0 the category and the military mark (older lines: blank)
                    v = (f[1:] + [""] * 5)[:5]
                    old = fleet.get(f[0], [""] * 5)
                    fleet[f[0]] = [v[k] or old[k] for k in range(5)]
        except OSError:
            continue
    airlines, types, cargo = load_airlines(cfg), load_types(cfg), load_cargo()
    by_airline, by_type, by_cargo, by_biz, alts, typed = {}, {}, {}, {}, [], 0
    cargo_models, biz_countries, mil, misc = {}, {}, {}, {g: {} for g in MISC_GROUPS}
    for h in sorted(fleet):
        flight, alt, code, cat, milmark = fleet[h]
        icao, info = airline_for(flight, airlines)
        if icao:
            name = (info or {}).get("name") or icao
            by_airline[name] = by_airline.get(name, 0) + 1
        if code in NOT_AIRCRAFT:                  # tar1090's database lists airport vehicles and towers too: not counted
            continue
        d = describe_type({"t": code, "category": cat}, types) if (code or cat) else {}
        label = (d.get("type_name") or code) if code else ""
        shape = d.get("shape")
        m = CALLSIGN_PREFIX.match(flight.upper())
        if m and m.group(1) in cargo:             # 0.35.0: the cargo airlines, by their own callsign prefix
            name = cargo[m.group(1)]
            by_cargo[name] = by_cargo.get(name, 0) + 1
            if label:                             # 0.36.0: and the model each flies most
                cm = cargo_models.setdefault(name, {})
                cm[label] = cm.get(label, 0) + 1
        if code:
            typed += 1
            by_type[label] = by_type.get(label, 0) + 1
        military = milmark == "1" or in_military_range(h) or aircraft.is_military(shape)
        cc = icao_country(h)
        if military:                              # 0.36.0: by the country its address belongs to, then the model
            e = mil.setdefault(cc, {})
            k = label or "Unknown type"
            e[k] = e.get(k, 0) + 1
        elif shape == "bizjet" and code:          # 0.35.0: the business jets, by make and model (the wall's own classes)
            by_biz[label] = by_biz.get(label, 0) + 1
            biz_countries[cc] = biz_countries.get(cc, 0) + 1          # 0.36.0: and the country they are registered in
        else:
            g = misc_group(shape, cat)
            if g:                                 # 0.36.0: helicopters, light aircraft, gliders, balloons, drones
                k = label or MISC_UNKNOWN[g]
                misc[g][k] = misc[g].get(k, 0) + 1
        try:
            if int(alt) > 0:
                alts.append(int(alt))
        except ValueError:
            pass
    imperial = public_config(cfg)["units"] == "imperial"
    step = 5000 if imperial else 1000 / 0.3048                   # bands of 5 000 ft, or of 1 km
    top_band = 9 if imperial else 13
    bands = [0] * (top_band + 1)
    for a in alts:
        bands[min(int(a // step), top_band)] += 1
    labels = [("%d–%d" % (i * 5, i * 5 + 5)) if imperial else ("%d–%d" % (i, i + 1)) for i in range(top_band)]
    labels.append("%d+" % (top_band * 5 if imperial else top_band))
    data = {"alt_unit": "thousand ft" if imperial else "km", "aircraft": len(fleet), "days": len(names), "typed": typed,
            "airlines": sorted(by_airline.items(), key=lambda kv: (-kv[1], kv[0]))[:FLEET_TOP],
            "types": sorted(by_type.items(), key=lambda kv: (-kv[1], kv[0]))[:FLEET_TOP],
            "cargo": sorted(by_cargo.items(), key=lambda kv: (-kv[1], kv[0]))[:FLEET_TOP], "cargo_total": sum(by_cargo.values()),
            "bizjets": sorted(by_biz.items(), key=lambda kv: (-kv[1], kv[0]))[:FLEET_TOP], "bizjet_total": sum(by_biz.values()),
            "cargo_models": {n: max(v.items(), key=lambda kv: (kv[1], kv[0])) for n, v in cargo_models.items()},
            "bizjet_countries": _top(biz_countries),
            "military": sorted(({"cc": c, "country": country_name(c), "total": sum(v.values()), "models": _top(v)}
                                for c, v in mil.items()), key=lambda e: (-e["total"], e["country"]))[:FLEET_TOP],
            "military_total": sum(sum(v.values()) for v in mil.values()),
            "misc": {g: {"total": sum(v.values()), "models": _top(v)} for g, v in misc.items()},
            "altitudes": {"labels": labels, "counts": bands}}
    _fleet_cache.update(key=key, data=data)
    return data


FARTHEST_SHOWN = ("day", "time", "hex", "flight", "flight_iata", "airline", "registration", "type", "type_name",
                  "alt_ft", "km", "route", "near")


def read_farthest(stats_dir, now):
    """{"today": record or None, "best": the farthest record of the thirty days or None}, from the farthest-DAY files
    the timer writes (0.22.0). Only the fields the page shows are passed on, whatever else a file holds."""
    cut = (now - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    recs = []
    try:
        names = os.listdir(stats_dir)
    except OSError:
        names = []
    for name in names:
        day = name[len("farthest-"):]
        if not name.startswith("farthest-") or not re.match(r"^\d{4}-\d{2}-\d{2}$", day) or day < cut:
            continue
        rec = _read_json(os.path.join(stats_dir, name))
        try:
            rec["km"] = float(rec.get("km"))
        except (TypeError, ValueError):
            continue
        rec["day"] = day
        recs.append({k: rec.get(k) for k in FARTHEST_SHOWN})
    today = now.strftime("%Y-%m-%d")
    return {"today": next((r for r in recs if r["day"] == today), None),
            "best": max(recs, key=lambda r: (r["km"], r["day"])) if recs else None}


# --------------------------------------------------------------------------- who may read the wall
# The wall has no login: it is a sign on a wall. So the question of who may read it is answered by where they
# come from. "private" means the ranges home networks use (10/8, 172.16/12, 192.168/16, the Pi itself, link-local
# and their IPv6 equivalents) — which is every tablet and television in the house, and nobody on the internet,
# even when a router forwards the port by mistake or on purpose. "any" opens it, and a list of networks in CIDR
# form allows exactly those (a VPN's range, say). Anything unreadable in the setting falls back to "private".
import ipaddress


def _as_ip(addr):
    try:
        ip = ipaddress.ip_address(str(addr).split("%")[0])        # drop a scope id like %eth0
    except ValueError:
        return None
    mapped = getattr(ip, "ipv4_mapped", None)                     # ::ffff:192.168.1.5 is 192.168.1.5
    return mapped or ip


def allowed_networks(policy):
    """-> list of networks, or None for "any". Unreadable input means private only, never open."""
    policy = str(policy or "private").strip().lower()
    if policy == "any":
        return None
    if policy == "private":
        return list(PRIVATE_NETWORKS)
    nets = []
    for part in policy.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            nets.append(ipaddress.ip_network(part, strict=False))
        except ValueError:
            return list(PRIVATE_NETWORKS)
    return nets or list(PRIVATE_NETWORKS)


PRIVATE_NETWORKS = tuple(ipaddress.ip_network(n) for n in (
    "127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16",
    "::1/128", "fc00::/7", "fe80::/10"))


def client_allowed(addr, policy):
    nets = allowed_networks(policy)
    if nets is None:
        return True
    ip = _as_ip(addr)
    if ip is None:
        return False
    return any(ip in n for n in nets)


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


def read_aircraft(cfg):
    """-> (the decoder's aircraft.json with the 978 MHz UAT aircraft merged in, or None; the path read)."""
    path = aircraft_json_path(cfg)
    data = read_json(path)
    upath = uat_json_path(cfg)
    if upath:                                   # 978 MHz UAT: optional, never a reason to show an error
        udata = read_json(upath)
        if udata is not None:
            data = merge_aircraft(data or {}, udata)
    return data, path


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
    info = airlines.get(icao) or learned_airline(icao)
    return (icao, info) if info else (icao, None)


# Airlines learned from the route answers. adsbdb's answer for a callsign names the airline, so the wall keeps that
# name for the callsign's three-letter prefix: a callsign of an airline outside the built-in list is then shown with
# its name instead of bare. Kept in memory only (the server writes nowhere), for the life of the process; a route
# lookup repeats every 12 hours anyway. The built-in list wins when it knows the prefix (its names are the short ones).
_learned = {"data": {}, "lock": threading.Lock()}
_CORP_RE = re.compile(r"[\s,]+(INC\.?|LTD\.?|LIMITED|LLC|PLC|S\.?A\.?|GMBH|AG|CO\.?|CORP\.?|CORPORATION|COMPANY)$", re.I)


def clean_airline_name(name):
    """'American Airlines Inc.' -> 'American Airlines'. The dot font has no accents (format.js drops them)."""
    name = re.sub(r"\s+", " ", str(name or "")).strip()
    while True:
        short = _CORP_RE.sub("", name).strip()
        if short == name or not short:
            break
        name = short
    return name


def parse_airline(data):
    """adsbdb answer -> {'icao': 'EZY', 'name': 'easyJet', 'iata': 'U2'} or None."""
    resp = data.get("response") if isinstance(data, dict) else None
    fr = resp.get("flightroute") if isinstance(resp, dict) else None
    al = fr.get("airline") if isinstance(fr, dict) else None
    if not isinstance(al, dict):
        return None
    icao, name = str(al.get("icao") or "").strip().upper(), clean_airline_name(al.get("name"))
    if not re.match(r"^[A-Z]{3}$", icao) or not name:
        return None
    return {"icao": icao, "name": name, "iata": str(al.get("iata") or "").strip().upper() or None}


def learn_airline(data):
    """Remember the airline an adsbdb answer names. Returns what was learned, or None."""
    info = parse_airline(data)
    if info:
        with _learned["lock"]:
            if len(_learned["data"]) > 2000:
                _learned["data"].clear()
            _learned["data"][info["icao"]] = {"name": info["name"], "iata": info["iata"], "learned": True}
    return info


def learned_airline(icao):
    with _learned["lock"]:
        return _learned["data"].get(icao)


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
def checked_route(flight, lat, lon, track, gs, route_lookup, route_fallback):
    """-> (route the aircraft can really be on, or None; True while an answer is still on its way).
    adsbdb first; hexdb's second opinion only when adsbdb's answer cannot be this flight."""
    route = route_lookup(flight) if route_lookup is not None else None
    waiting = bool(route is None and route_lookup is not None and getattr(route_lookup, "pending", None) and route_lookup.pending(flight))
    checked = route_plausible(route, lat, lon, track, gs)
    if route and not checked and route_fallback is not None:      # a second opinion, only when the first answer is wrong
        for leg in route_fallback(flight) or ():
            checked = route_plausible(leg, lat, lon, track, gs, strict=True)
            if checked:
                break
        if not checked and getattr(route_fallback, "pending", None) and route_fallback.pending(flight):
            waiting = True
    return checked, waiting


def build_planes(data, lat, lon, radius_km, airlines=None, photo_lookup=None, demo=False, types=None, route_lookup=None,
                 aircraft_lookup=None, route_fallback=None, only_hex=None, local_db=None):
    """Return (planes_in_radius_sorted_by_distance, total_with_position). only_hex: that aircraft alone, so asking
    about one far aircraft (social sharing's range record) does not set off lookups for everything in between."""
    airlines = airlines or {}
    planes, total = [], 0
    for ac in data.get("aircraft", []):
        if "lat" not in ac or "lon" not in ac:
            continue
        if ac.get("seen_pos", 0) > MAX_POSITION_AGE_S:
            continue
        total += 1
        if only_hex and str(ac.get("hex", "")).lower() != only_hex:
            continue
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
                # the address Planespotters gave, unchanged: the tablet fetches the picture itself (0.24.5)
                photo, credit, link = found.get("url"), found.get("photographer"), found.get("link")
        # What is still on its way for this aircraft: the wall ignores it (it shows the rows when they come); social
        # sharing waits for it rather than post a board with empty rows. 0.19.5: adsbdb's first answer, after KLM24V
        # went out with no registration, model or route. 0.19.9: hexdb's second opinion too, after RYR8526 and EWG6ZP
        # went out with no route — adsbdb had another flight under those callsigns (Berlin-Stansted, Salzburg-
        # Aalborg), rightly refused, while hexdb had the right one (Charleroi-Reggio Calabria, Menorca-Cologne) on its
        # way a few seconds later
        pending = []
        if demo and ac.get("demo_route"):
            route = ac["demo_route"]
        else:
            route, waiting = checked_route(flight, ac["lat"], ac["lon"], ac.get("track"), ac.get("gs"), route_lookup, route_fallback)
            if waiting:
                pending.append("route")
        # The decoder only knows the type and the registration when its aircraft database has the airframe. When it
        # does not, ask adsbdb.com (by the aircraft's hex code) so the model is still shown and the silhouette fits.
        reg, code, found = ac.get("r"), ac.get("t"), None
        if local_db and not (reg and code) and not demo:
            found = local_aircraft(ac.get("hex"), local_db)
            if found:
                reg = reg or found.get("registration")
                code = code or found.get("icao_type")
        if aircraft_lookup is not None and not (reg and code) and not (demo and ac.get("t")):
            found = aircraft_lookup(ac.get("hex"))
            if found:
                reg = reg or found.get("registration")
                code = code or found.get("icao_type")
            elif getattr(aircraft_lookup, "pending", None) and aircraft_lookup.pending(ac.get("hex")):
                pending.append("model")
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
            "pending": pending,
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

    def pending(self, key):
        """True while the first answer for this key is on its way (asked, not yet answered). A key answered once,
        found or not, or whose request failed, is not pending: there is nothing to wait for."""
        with self.lock:
            e = self.cache.get(key)
            return bool(e and e["queued"] and e["value"] is None)

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


# --------------------------------------------------------------------------- photos (Planespotters, optional)
# 0.24.5, from Planespotters' photo API terms (read 19 October 2026): the picture must be fetched straight from the
# address the API gives, by the screen that shows it, and never stored, proxied or passed on; the API's answer may
# be kept 24 hours at most. Until then the Pi fetched each picture and served it to the tablet from a cache of 200.
# Now the wall hands the tablet Planespotters' own address, with the credit and the link back the terms ask for.
# Every request this server makes to somebody else carries this. Planespotters refuses a plain library or
# product name and asks for one that names the application and a contact address, so all five requests send the
# same descriptive line rather than each inventing its own.
USER_AGENT = "ZenithBoard/%s (+https://github.com/regis57/ZenithBoard)" % VERSION

PHOTO_TTL_S = 24 * 3600             # an answer is asked again after a day, as the terms require
PHOTO_GAP_S = 2.0                   # Planespotters answers 403 to bursts: at most one request every 2 s
PHOTO_RETRY_S = 600                 # refused / failed: try again after 10 min
PHOTO_NOPHOTO_RETRY_S = 86400       # no photo published today: look again tomorrow


# The photo address comes from somebody else's answer, and the tablet then fetches it. So it is checked before it
# is passed on: https only, and a host inside one of the domains below. Without this, an answer that was tampered
# with could send the tablet to any address, your own router included. Planespotters serves its pictures from
# plnspttrs.net, a different domain from the one its API answers on: leaving it out silently refused every photo,
# which is what 0.12.4 fixes.
PHOTO_HOSTS = ("planespotters.net", "plnspttrs.net")
# Every header value the wall sends comes out of these tables, never from a request or from somebody else's
# answer: the lookup returns OUR string, so whatever arrives cannot end up in a header (no line break, no
# second header smuggled in). Files are typed by their extension here too, rather than by the system's MIME list.
FILE_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
}
HEADER_TYPES = {t: t for t in set(FILE_TYPES.values()) | {"text/plain", "application/octet-stream"}}
CACHE_RULES = {"no-store": "no-store", "max-age=3600": "max-age=3600"}

def photo_url_allowed(url):
    try:
        u = urlparse(url or "")
    except Exception:
        return False
    host = (u.hostname or "").lower()
    if u.scheme != "https":
        return False
    return any(host == d or host.endswith("." + d) for d in PHOTO_HOSTS)


def parse_photo_answer(data):
    """-> (meta|None, ok). Split out of the request so the checks can be tested without the network."""
    photos = (data or {}).get("photos") or []
    if not photos:
        return None, True
    p = photos[0]
    url = (p.get("thumbnail_large") or {}).get("src")
    if not url or not photo_url_allowed(url):
        return None, True
    return {"url": url, "photographer": p.get("photographer"), "link": p.get("link")}, True


def _photo_api(hex_code):
    """-> (meta|None, ok). ok is False when we could not get an answer (403, timeout, no internet)."""
    url = "https://api.planespotters.net/pub/photos/hex/%s" % hex_code
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.load(resp)
    except Exception:       # network is optional: never break the wall because of photos
        return None, False
    return parse_photo_answer(data)


_photos = ThrottledLookup(_photo_api, PHOTO_GAP_S, PHOTO_RETRY_S, PHOTO_NOPHOTO_RETRY_S, found_ttl=PHOTO_TTL_S)


def lookup_photo(hex_code):
    """Non-blocking: the photo metadata we already have; a request is queued when it is missing."""
    return _photos.get(hex_code)


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
           "name": str(a.get("name") or ""), "city": tidy_place(a.get("municipality") or ""),
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
    if not (origin or dest):
        return None
    out = {"from": origin, "to": dest}
    iata = str(fr.get("callsign_iata") or "").strip().upper()     # FR8526 for RYR8526: the number on the ticket (0.22.0)
    if re.match(r"^[A-Z0-9]{2}[0-9]{1,4}[A-Z]?$", iata):
        out["flight_iata"] = iata
    return out


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


def route_plausible(route, plat, plon, track=None, gs=None, strict=False):
    """The database knows callsigns, not flights: a callsign can be reused for another route. Drop an answer that cannot
    be this flight: same airport twice, an aircraft far from the line between the two airports, or one flying away from
    the destination. When it cannot be checked (no airport position) the route is kept, unless strict."""
    if not route:
        return route
    a, b = route.get("from"), route.get("to")
    if a and b and _same_airport(a, b):
        return None
    if not (a and b and "lat" in a and "lon" in a and "lat" in b and "lon" in b):
        return None if strict else route          # strict (a second opinion): only a route that could be checked is believed
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
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
        learn_airline(data)                 # the answer names the airline too: keep it for callsigns of that prefix
        return parse_route(data), True
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            print("route lookup %s: HTTP %s, retrying in %d s" % (callsign, exc.code, ROUTE_RETRY_S), file=sys.stderr, flush=True)
        return None, exc.code == 404            # 404 = unknown callsign (a real answer); anything else = try later
    except Exception as exc:
        print("route lookup %s failed (%s), retrying in %d s" % (callsign, exc, ROUTE_RETRY_S), file=sys.stderr, flush=True)
        return None, False


_routes = ThrottledLookup(_route_api, ROUTE_GAP_S, ROUTE_RETRY_S, ROUTE_MISS_RETRY_S, found_ttl=ROUTE_TTL_S)


def lookup_route(callsign):
    """Non-blocking: the route we already know for this callsign; a request is queued when it is missing."""
    cs = (callsign or "").strip().upper()
    return _routes.get(cs) if CALLSIGN_RE.match(cs) else None


lookup_route.pending = lambda callsign: _routes.pending((callsign or "").strip().upper())


# --------------------------------------------------------------------------- routes, second opinion (hexdb.io, optional)
# Asked ONLY when adsbdb gave a route that cannot be this flight, once per callsign (answers kept for hours). hexdb gives
# airport codes only, so the position of each airport is asked once and kept for good. Several legs ("EGNX-ELLX-EGNX")
# are all offered; the wall takes the first one the aircraft can really be on.
HEXDB_URL = "https://hexdb.io/api/v1"
ICAO_AIRPORT_RE = re.compile(r"^[A-Z0-9]{4}$")
_airport_cache = {}                 # ICAO code -> airport dict (with lat/lon) or None; small and kept until restart
_airport_lock = threading.Lock()


def _hexdb_json(path):
    req = urllib.request.Request(HEXDB_URL + path, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)


def _hexdb_airport(code):
    """-> airport dict with lat/lon, or None. Raises when hexdb cannot be reached (so nothing wrong is remembered)."""
    with _airport_lock:
        if code in _airport_cache:
            return _airport_cache[code]
    try:
        d = _hexdb_json("/airport/icao/%s" % code)
        lat, lon = d.get("latitude"), d.get("longitude")
        ok = isinstance(lat, (int, float)) and isinstance(lon, (int, float))
        a = {"iata": str(d.get("iata") or ""), "icao": code, "name": str(d.get("airport") or ""),
             "city": tidy_place(str(d.get("location") or "")), "country": str(d.get("country_code") or ""),
             "lat": float(lat), "lon": float(lon)} if ok else None
        if a and not a["city"]:          # hexdb gives no town (seen on the real posts, 0.25.3): taken from the name
            a["city"] = city_of_airport(a["name"], a["lat"], a["lon"])
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        a = None
    with _airport_lock:
        if len(_airport_cache) > 2000:
            _airport_cache.clear()
        _airport_cache[code] = a
    return a


# 0.25.3: the posts said "Brussels South Charleroi Airport -> Turin Airport (Caselle Airport)" where adsbdb's routes
# say "Milan" or "Weeze": hexdb's airports carry a name and no town. The town is made from the name: what is in
# brackets and the words that only say "airport" go; and when the name opens on a city that is not by the airport
# ("Brussels" South Charleroi, 45 km away) while a later word is a town by it ("Charleroi", 5 km), that town is kept.
PLACES_FILE = os.path.join(DATA_DIR, "places5000.tsv.gz")
AIRPORT_TOWN_KM = 30
AIRPORT_WORDS_RE = re.compile(r"\b(International|Intl|Regional|Airport|Airfield|Aerodrome|Air Base|Airbase)\b", re.I)
PLACE_PARTICLES = {"de", "del", "della", "di", "da", "do", "dos", "das", "du", "des", "la", "las", "le", "les", "los",
                   "am", "an", "im", "sur", "en", "y", "on"}


def tidy_place(name):
    """'Palma De Mallorca' -> 'Palma de Mallorca', 'Frankfurt Am Main' -> 'Frankfurt am Main': the small words inside a
    town's name in lower case, as the town writes it (adsbdb capitalises every word). The first word is left as it is."""
    words = str(name or "").split(" ")
    return " ".join(w.lower() if i and w.lower() in PLACE_PARTICLES else w for i, w in enumerate(words)).strip()


def _towns_near(lat, lon, km=AIRPORT_TOWN_KM):
    """{name: distance_km} of the GeoNames places of 5 000 or more within km of the point; {} without the list."""
    out, dlat = {}, km / 111.0
    dlon = km / (111.0 * max(0.1, math.cos(math.radians(lat))))
    try:
        import gzip
        with gzip.open(PLACES_FILE, "rt", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("#"):
                    continue
                n, la, lo, _pop = line.rstrip("\n").split("\t")
                la, lo = float(la), float(lo)
                if abs(la - lat) <= dlat and abs(lo - lon) <= dlon:
                    d = haversine_km(lat, lon, la, lo)
                    if d <= km and d < out.get(n, 1e9):
                        out[n] = d
    except (OSError, ValueError):
        return {}
    return out


def city_of_airport(name, lat=None, lon=None):
    """The town an airport's name stands for: 'Turin Airport (Caselle Airport)' -> 'Turin',
    'Brussels South Charleroi Airport' -> 'Charleroi' (with its position), 'Amsterdam Airport Schiphol' -> 'Amsterdam',
    'Frankfurt-Hahn Airport' -> 'Frankfurt-Hahn'."""
    n = re.sub(r"\s*\([^)]*\)", "", str(name or ""))
    n = re.sub(r"\s{2,}", " ", AIRPORT_WORDS_RE.sub("", n)).strip(" -,")
    if not n:
        return str(name or "")
    words = [w for w in re.split(r"[ -]", n) if w]
    if len(words) > 1 and isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        near = _towns_near(lat, lon)
        if near and words[0] not in near:
            for w in words[1:]:
                if w in near:
                    return w
        # 0.25.4: "Amsterdam Airport Schiphol" gave "Amsterdam Schiphol" on a real post. A name that opens on the town
        # by the airport is that town, unless the rest is part of the town's own name ("Palma de Mallorca")
        if near and words[0] in near and not any(w.lower() in PLACE_PARTICLES for w in words[1:]):
            return words[0]
    return tidy_place(n)


def parse_hexdb_route(text):
    """'EGNX-ELLX-EGNX' -> [('EGNX','ELLX'), ('ELLX','EGNX')]; anything odd -> []."""
    codes = [c.strip().upper() for c in str(text or "").split("-")]
    if not 2 <= len(codes) <= 6 or not all(ICAO_AIRPORT_RE.match(c) for c in codes):
        return []
    return [(codes[i], codes[i + 1]) for i in range(len(codes) - 1) if codes[i] != codes[i + 1]]


def _route2_api(callsign):
    """-> (list of routes|None, ok)."""
    try:
        legs = parse_hexdb_route(_hexdb_json("/route/icao/%s" % callsign).get("route"))
        out = []
        for a, b in legs[:4]:
            pa, pb = _hexdb_airport(a), _hexdb_airport(b)
            if pa and pb:
                out.append({"from": pa, "to": pb})
            time.sleep(0.3)
        return (out or None), True
    except urllib.error.HTTPError as exc:
        return None, exc.code == 404
    except Exception as exc:
        print("route (hexdb) %s failed (%s), retrying in %d s" % (callsign, exc, ROUTE_RETRY_S), file=sys.stderr, flush=True)
        return None, False


_routes2 = ThrottledLookup(_route2_api, ROUTE_GAP_S, ROUTE_RETRY_S, ROUTE_MISS_RETRY_S, found_ttl=ROUTE_TTL_S, max_queue=20)


def lookup_route_fallback(callsign):
    """Non-blocking: the routes hexdb knows for this callsign (a list), or None while unknown / not asked yet."""
    cs = (callsign or "").strip().upper()
    return _routes2.get(cs) if CALLSIGN_RE.match(cs) else None


lookup_route_fallback.pending = lambda callsign: _routes2.pending((callsign or "").strip().upper())


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


def parse_hexdb_aircraft(data):
    """hexdb /aircraft answer -> the same dict as parse_aircraft, or None. Its keys: Registration, ICAOTypeCode,
    Manufacturer, Type (and owner and flag fields, not used)."""
    if not isinstance(data, dict):
        return None
    out = {"icao_type": str(data.get("ICAOTypeCode") or "").upper(), "type": str(data.get("Type") or ""),
           "manufacturer": str(data.get("Manufacturer") or ""), "registration": str(data.get("Registration") or "")}
    return out if (out["icao_type"] or out["type"] or out["registration"]) else None


def _hexdb_aircraft(hex_code):
    """hexdb's second opinion on an airframe adsbdb does not know. 0.25.1: TF-AKE, an Air Atlanta cargo 747, went out
    with blank registration and model rows; adsbdb answered "unknown aircraft", hexdb knew it."""
    try:
        return parse_hexdb_aircraft(_hexdb_json("/aircraft/%s" % hex_code))
    except Exception:
        return None                              # not known there either, or unreachable: the rows stay as they were


def _aircraft_api(hex_code):
    """-> (info|None, ok). ok is False when we could not get an answer. adsbdb first; hexdb only when adsbdb does
    not know the airframe."""
    url = "https://api.adsbdb.com/v0/aircraft/%s" % hex_code
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            found = parse_aircraft(json.load(resp))
        return (found or _hexdb_aircraft(hex_code)), True
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            print("aircraft lookup %s: HTTP %s, retrying in %d s" % (hex_code, exc.code, AIRCRAFT_RETRY_S), file=sys.stderr, flush=True)
            return None, False
        return _hexdb_aircraft(hex_code), True
    except Exception as exc:
        print("aircraft lookup %s failed (%s), retrying in %d s" % (hex_code, exc, AIRCRAFT_RETRY_S), file=sys.stderr, flush=True)
        return None, False


_aircraft = ThrottledLookup(_aircraft_api, AIRCRAFT_GAP_S, AIRCRAFT_RETRY_S, AIRCRAFT_MISS_RETRY_S, found_ttl=AIRCRAFT_TTL_S)


def lookup_aircraft(hex_code):
    """Non-blocking: what we already know about this airframe; a request is queued when it is missing."""
    h = (hex_code or "").strip().upper()
    return _aircraft.get(h) if HEX_RE.match(h) else None


lookup_aircraft.pending = lambda hex_code: _aircraft.pending((hex_code or "").strip().upper())


# --------------------------------------------------------------------------- aircraft, offline (tar1090's database)
# 0.26.0, from a real post: EWG8QR (4D2087, 9H-EWG) went out with no registration and no model. adsbdb answered
# "unknown aircraft", hexdb "n/a"; tar1090's database, which the receiver map's installer keeps on the Pi and updates
# itself, knew it. Read from the card, nothing asked of the internet. Its layout (wiedehopf/tar1090-db, db/*.js):
# gzip'd JSON files named by the first characters of the hex code; in each, the rest of the code -> [registration,
# ICAO type, flags, description], and "children": the longer prefixes that have a file of their own.
LOCAL_DB_SHARDS = 4                 # parsed files kept in memory (one is about a megabyte of JSON)
LOCAL_DB_HEXES = 4000               # answers kept, found or not
_localdb_shards = {}                # (dir, prefix) -> dict, in the order they were read
_localdb_hexes = {}                 # (dir, hex) -> answer or None
_localdb_lock = threading.Lock()


def _read_shard(d, prefix):
    """One file of tar1090's database, parsed: a dict, or None when it is missing or unreadable."""
    try:
        import gzip
        with open(os.path.join(d, prefix + ".js"), "rb") as fh:
            raw = fh.read()
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass                                 # a plain JSON file is read as it is
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return None


def _localdb_shard(d, prefix):
    key = (d, prefix)
    with _localdb_lock:
        if key in _localdb_shards:
            return _localdb_shards[key]
    data = _read_shard(d, prefix)
    with _localdb_lock:
        while len(_localdb_shards) >= LOCAL_DB_SHARDS:
            _localdb_shards.pop(next(iter(_localdb_shards)))
        _localdb_shards[key] = data
    return data


def local_db_dir(cfg):
    """The folder of tar1090's database when LOCAL_DB is on and the folder is there; None otherwise."""
    if not cfg_bool(cfg, "LOCAL_DB"):
        return None
    d = str(cfg.get("LOCAL_DB_DIR") or DEFAULTS["LOCAL_DB_DIR"]).strip()
    return d if os.path.isdir(d) else None


def local_aircraft(hex_code, d):
    """-> {"registration", "icao_type", "type", "manufacturer"} from tar1090's database in folder d, or None."""
    h = (hex_code or "").strip().upper()
    if not d or not HEX_RE.match(h):
        return None
    with _localdb_lock:
        if (d, h) in _localdb_hexes:
            return _localdb_hexes[(d, h)]
    found, n = None, 1
    while n <= len(h):
        shard = _localdb_shard(d, h[:n])
        if not shard:
            break
        entry = shard.get(h[n:])
        if isinstance(entry, list) and entry:
            reg = str(entry[0] or "").strip()
            code = str(entry[1] or "").strip().upper() if len(entry) > 1 else ""
            desc = str(entry[3] or "").strip() if len(entry) > 3 else ""
            if reg or code:
                found = {"registration": reg, "icao_type": code, "type": desc, "manufacturer": ""}
            break
        children = shard.get("children") or []
        if h[:n + 1] not in children:
            break
        n += 1
    with _localdb_lock:
        if len(_localdb_hexes) >= LOCAL_DB_HEXES:
            _localdb_hexes.clear()
        _localdb_hexes[(d, h)] = found
    return found


# --------------------------------------------------------------------------- the farthest aircraft of the day (0.22.0)
# The decoder's stats.json says how far the farthest aircraft was, never which one. So, with statistics on, the server
# looks at aircraft.json every few seconds and keeps, for today and yesterday, the aircraft whose position was the
# farthest from the antenna: its callsign, registration, type, altitude, and when. It keeps them in memory only (the
# server writes nowhere); the statistics timer asks for them on the loopback every quarter hour and writes them down
# (lib/stats.sh), with the airline, the route and the large city nearest the aircraft, which the /stats page shows.
FARTHEST_EVERY_S = 5                # aircraft.json is rewritten every second; a position stays in it for a minute
FARTHEST_MAX_KM = 600               # readsb's own range limit is 300 NM (556 km): a position beyond is a decoding error
CALLSIGN_KEEP_S = 3600              # a callsign is remembered an hour after it was last heard: one pass across the range
CITIES_FILE = os.path.join(DATA_DIR, "cities100k.tsv")


class FarthestTracker(object):
    """The farthest aircraft position seen, per day (local time), for the last two days."""

    def __init__(self):
        self.lock = threading.Lock()
        self.days = {}                      # "YYYY-MM-DD" -> record
        # hex -> (callsign, when last seen). At the edge of range the decoder often has an aircraft's positions before
        # its callsign: the day's farthest was then written with no flight, airline or route (TF-ICE at 322 km, seen
        # on the real Pi, 0.23.0). The callsign heard before or after fills it in.
        self.calls = {}

    def observe(self, data, lat, lon, now=None):
        now = time.time() if now is None else now
        for ac in (data or {}).get("aircraft") or []:
            if not isinstance(ac, dict) or not isinstance(ac.get("lat"), (int, float)) or not isinstance(ac.get("lon"), (int, float)):
                continue
            age = ac.get("seen_pos", 0)
            if not isinstance(age, (int, float)) or age > MAX_POSITION_AGE_S:
                continue
            hx = str(ac.get("hex") or "").lower()
            alt = ac.get("alt_baro", ac.get("alt_geom"))
            if not re.match(r"^[0-9a-f]{6}$", hx) or alt == "ground":      # ~ marks a made-up address: nothing to name
                continue
            call = str(ac.get("flight") or "").strip()
            if call:
                with self.lock:
                    self.calls[hx] = (call, now)
                    for rec in self.days.values():
                        if rec["hex"] == hx and not rec["flight"]:
                            rec["flight"] = call
            km = haversine_km(lat, lon, ac["lat"], ac["lon"])
            if km > FARTHEST_MAX_KM:
                continue
            when = datetime.datetime.fromtimestamp(now - age)
            day = when.strftime("%Y-%m-%d")
            with self.lock:
                cur = self.days.get(day)
                if cur and cur["km"] >= round(km, 1):
                    continue
                self.days[day] = {
                    "day": day, "time": when.strftime("%H:%M"), "hex": hx, "flight": call or self.calls.get(hx, ("", 0))[0],
                    "registration": ac.get("r"), "type": ac.get("t"), "category": ac.get("category"), "dbFlags": ac.get("dbFlags"),
                    "alt_ft": alt if isinstance(alt, (int, float)) else None, "km": round(km, 1),
                    "lat": ac["lat"], "lon": ac["lon"], "track": ac.get("track"), "gs": ac.get("gs")}
        with self.lock:
            for d in sorted(self.days)[:-2]:
                del self.days[d]
            for hx in [h for h, (_, t) in self.calls.items() if now - t > CALLSIGN_KEEP_S]:
                del self.calls[hx]

    def snapshot(self):
        with self.lock:
            return [dict(self.days[d]) for d in sorted(self.days)]


_farthest = FarthestTracker()


def farthest_watch():
    """The tracker's loop, a thread of its own. Does nothing while statistics are off or the position is not set."""
    while True:
        try:
            cfg = load_config()
            lat, lon = cfg_float(cfg, "LAT", 0), cfg_float(cfg, "LON", 0)
            if cfg_bool(cfg, "STATS") and (lat or lon):
                data, _ = read_aircraft(cfg)
                if data is not None:
                    _farthest.observe(data, lat, lon)
        except Exception as exc:            # a bad file now and then must not end the watch for good
            print("farthest aircraft: %s" % exc, file=sys.stderr, flush=True)
        time.sleep(FARTHEST_EVERY_S)


_cities = {"rows": None, "lock": threading.Lock()}


def load_cities(path=None):
    """[(name, country, lat, lon, population)] from the GeoNames list shipped in data/ (read once)."""
    with _cities["lock"]:
        if _cities["rows"] is None or path:
            rows = []
            try:
                with open(path or CITIES_FILE, encoding="utf-8") as fh:
                    for line in fh:
                        if line.startswith("#"):
                            continue
                        f = line.rstrip("\n").split("\t")
                        try:
                            rows.append((f[0], f[1], float(f[2]), float(f[3]), int(f[4])))
                        except (IndexError, ValueError):
                            continue
            except OSError:
                rows = []
            if path:
                return rows
            _cities["rows"] = rows
        return _cities["rows"]


def nearest_city(lat, lon, cities=None):
    """{"name", "country", "km"} of the city of 100 000 inhabitants or more nearest the point, or None."""
    best, best_km = None, None
    cos = max(0.1, math.cos(math.radians(lat)))
    for c in (cities if cities is not None else load_cities()):
        if best_km is not None and (abs(c[2] - lat) * 111.2 > best_km or abs(c[3] - lon) * 111.2 * cos > best_km):
            continue                        # cheaper than the great circle, and enough to rule a city out
        km = haversine_km(lat, lon, c[2], c[3])
        if best_km is None or km < best_km:
            best, best_km = c, km
    return {"name": best[0], "country": best[1], "km": round(best_km)} if best else None


def _shown_airport(a):
    """An airport as the page shows it: what it is called, without the position that served only to check the route."""
    return {k: a.get(k) for k in ("city", "name", "iata", "icao", "country")} if isinstance(a, dict) else None


def describe_farthest(rec, cfg, route_lookup=None, route_fallback=None, aircraft_lookup=None, airlines=None, types=None):
    """One of the tracker's records, as the statistics timer writes it down: the airline, the route and the model when
    they are known, the nearest large city; neither the aircraft's position nor the antenna's. "pending" lists what is
    still being looked up, so the timer can wait a few seconds for it."""
    flight, pending = rec.get("flight") or "", []
    route, waiting = checked_route(flight, rec["lat"], rec["lon"], rec.get("track"), rec.get("gs"), route_lookup, route_fallback)
    if waiting:
        pending.append("route")
    reg, code, found = rec.get("registration"), rec.get("type"), None
    local_db = local_db_dir(cfg)
    if local_db and not (reg and code):
        found = local_aircraft(rec.get("hex"), local_db)
        if found:
            reg, code = reg or found.get("registration"), code or found.get("icao_type")
    if aircraft_lookup is not None and not (reg and code):
        found = aircraft_lookup(rec.get("hex"))
        if found:
            reg, code = reg or found.get("registration"), code or found.get("icao_type")
        elif getattr(aircraft_lookup, "pending", None) and aircraft_lookup.pending(rec.get("hex")):
            pending.append("model")
    icao, info = airline_for(flight, airlines if airlines is not None else load_airlines(cfg))   # after the route: it teaches airline names
    kind = describe_type({"t": code, "category": rec.get("category"), "dbFlags": rec.get("dbFlags")},
                         types if types is not None else load_types(cfg))
    if not kind["type_name"] and found and found.get("type"):
        kind["type_name"] = " ".join(x for x in (found.get("manufacturer"), found.get("type")) if x)
    return {
        "day": rec["day"], "time": rec["time"], "hex": rec["hex"], "flight": flight,
        "flight_iata": (route or {}).get("flight_iata"),
        "airline": info.get("name") if info else ("MILITARY" if kind["military"] else None),
        "registration": reg or None, "type": code or None, "type_name": kind["type_name"] or None,
        "alt_ft": rec.get("alt_ft"), "km": rec["km"],
        "route": {"from": _shown_airport(route.get("from")), "to": _shown_airport(route.get("to"))} if route else None,
        "near": nearest_city(rec["lat"], rec["lon"]),
        "pending": pending,
    }


def farthest_answer(cfg):
    """What /api/farthest says: the records of today and yesterday, described. Lookups only with routes on."""
    if not cfg_bool(cfg, "STATS"):
        return {"enabled": False}
    real = not cfg_bool(cfg, "DEMO")
    routes = cfg_bool(cfg, "SHOW_ROUTES") and real
    rl = lookup_route if routes else None
    return {"enabled": True, "days": [describe_farthest(r, cfg, rl, lookup_route_fallback if rl else None,
                                                        lookup_aircraft if routes else None) for r in _farthest.snapshot()]}


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
        "cycle_seconds": max(2, cfg_float(cfg, "CYCLE_SECONDS", 14)),
        "show_photos": cfg_bool(cfg, "SHOW_PHOTOS"),
        "flags": cfg_bool(cfg, "FLAGS", "1"),
        "stats": cfg_bool(cfg, "STATS"),           # the gear panel offers the /stats page only when there is one
        "display_mode": "flap" if str(cfg.get("DISPLAY_MODE", "dots")).lower() == "flap" else "dots",
        "demo": cfg_bool(cfg, "DEMO"),
        "presets": presets_of(cfg),                # ?p=NAME on a tablet applies one (0.21.0)
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "ZenithBoard/" + VERSION

    def log_message(self, fmt, *args):  # keep journald quiet
        pass

    @staticmethod
    def _header_values(ctype, cache):
        """-> (content type, cache rule), both taken from our own tables; anything unknown gets the safe default."""
        return HEADER_TYPES.get(ctype, "application/octet-stream"), CACHE_RULES.get(cache, "no-store")

    def _send(self, code, body, ctype="application/json", cache="no-store"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode("utf-8")
        ctype, cache = self._header_values(ctype, cache)
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
        if not client_allowed(self.client_address[0], cfg.get("ALLOW_FROM", "private")):
            return self._send(403, b"This wall answers its own network only (ALLOW_FROM).", "text/plain")
        if path == "/api/config":
            return self._send(200, public_config(cfg))
        if path == "/api/health":
            return self._send(200, {"ok": True, "version": VERSION})
        if path == "/api/planes":
            return self._planes(cfg, parse_qs(url.query))
        if path == "/api/stats":
            if not cfg_bool(cfg, "STATS"):
                return self._send(200, {"enabled": False, "version": VERSION})
            got = read_stats() or {"enabled": True, "samples": 0, "hours": [], "days": [], "today": None, "best": None}
            return self._send(200, dict(got, version=VERSION, units=public_config(cfg)["units"], fleet=read_fleet(cfg)))
        if path == "/api/farthest":                    # asked by the statistics timer every quarter hour (lib/stats.sh)
            return self._send(200, farthest_answer(cfg))
        if path == "/stats":
            return self._file(STATIC_DIR, "stats.html")
        if path == "/social/preview":                 # the picture `zenithboard social test` drew, to look at before posting anything
            return self._file(SOCIAL_DIR, social_preview_name())
        if path in ("/social/preview2", "/social/preview3", "/social/preview4"):   # the weekly posts' pictures (0.35.0, 0.36.0)
            return self._file(SOCIAL_DIR, "preview%s.png" % path[-1])
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
        data, path = read_aircraft(cfg)
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
        route_fallback = lookup_route_fallback if route_lookup is not None else None
        only = (query.get("hex") or [""])[0].strip().lower()
        only = only if re.match(r"^[0-9a-f]{6}$", only) else None     # an ICAO address or nothing: no other input reaches the loop
        planes, total = build_planes(data, cfg_float(cfg, "LAT", 0), cfg_float(cfg, "LON", 0), radius_km,
                                     load_airlines(cfg), lookup, demo, load_types(cfg), route_lookup, aircraft_lookup, route_fallback,
                                     only_hex=only, local_db=local_db_dir(cfg))
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
        ctype = FILE_TYPES.get(os.path.splitext(full)[1].lower(), "application/octet-stream")
        with open(full, "rb") as fh:
            body = fh.read()
        return self._send(200, body, ctype)


class WallServer(ThreadingHTTPServer):
    """ThreadingHTTPServer that can also sit on an IPv6 address."""
    def __init__(self, bind, handler):
        if ":" in bind[0]:
            self.address_family = socket.AF_INET6
        super().__init__(bind, handler)


def main():
    cfg = load_config()
    port = int(os.environ.get("PORT") or cfg.get("PORT") or 8080)
    bind = str(cfg.get("BIND_ADDRESS") or "0.0.0.0").strip() or "0.0.0.0"
    httpd = WallServer((bind, port), Handler)
    threading.Thread(target=farthest_watch, daemon=True).start()
    print("ZenithBoard FlightInfo %s listening on %s:%d, answering %s (config: %s)"
          % (VERSION, bind, port, cfg.get("ALLOW_FROM", "private"), CONFIG_FILE), flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
