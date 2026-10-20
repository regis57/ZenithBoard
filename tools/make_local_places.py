#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The town names of the posts' maps, made on the Pi for its own region (0.27.0).

The lists shipped with ZenithBoard name the places whose population GeoNames knows: 2 074 places of 5 000 or more in
France, 479 in Indonesia, a country four times as populous, where GeoNames knows the population of almost no village
(257 515 of its 258 055 populated places have none). A map over Java or Sumba was left with one name or none.

GeoNames publishes one file per country with every populated place, population known or not, and its rank: national
capital (PPLC), seat of a first-level division (PPLA, a province), second (PPLA2, a regency or a French prefecture),
third (PPLA3), fourth (PPLA4), or a plain place (PPL). This tool downloads the files of the countries within reach
of the receiver, keeps the populated places within KM of it, and gives each a weight: its population when GeoNames
knows it, otherwise a figure from its rank. social_card.py names the heaviest first, as with the shipped lists.

    python3 tools/make_local_places.py LAT LON OUT [KM]          the region's list (run by: zenithboard social places on)
    python3 tools/make_local_places.py --grid cities500.json      flightinfo/data/country-cells.json.gz, at build time

The files come from https://download.geonames.org/export/dump/ (Creative Commons Attribution 4.0): about 20 MB for a
receiver in Lorraine (France, Germany, Belgium, Luxembourg, the Netherlands, Switzerland...), downloaded once, read a
line at a time and deleted; the list kept is a few hundred kilobytes. Nothing about the receiver is sent: the
country files are the same for everyone.
"""
import gzip
import io
import json
import math
import os
import sys
import tempfile
import time
import urllib.request
import zipfile

DUMP = "https://download.geonames.org/export/dump/%s.zip"
HERE = os.path.dirname(os.path.abspath(__file__))
GRID_FILE = os.path.join(HERE, "..", "flightinfo", "data", "country-cells.json.gz")
KM_DEFAULT = 400
# The weight of a place whose population GeoNames does not know, from its rank. A known population always wins: a
# Luxembourg commune seat of 126 inhabitants stays a village.
RANK_WEIGHT = {"PPLC": 1000000, "PPLA": 200000, "PPLG": 200000, "PPLA2": 50000, "PPLA3": 10000, "PPLA4": 2000,
               "PPLA5": 1000, "PPL": 100, "PPLF": 50, "PPLL": 50, "PPLS": 50, "PPLR": 50}
# Not places to name: a part of a city (PPLX), historical (PPLH, PPLCH), abandoned (PPLQ), destroyed (PPLW).
SKIP = {"PPLX", "PPLH", "PPLCH", "PPLQ", "PPLW"}
SAME_PLACE_KM = 1.5          # a lighter place this close to a heavier one is taken for a part of it
USER_AGENT = "ZenithBoard (+https://github.com/regis57/ZenithBoard)"


def km(la1, lo1, la2, lo2):
    la1, lo1, la2, lo2 = map(math.radians, (la1, lo1, la2, lo2))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0088 * math.asin(min(1.0, math.sqrt(h)))


def weight(fcode, population):
    return population if population > 0 else RANK_WEIGHT.get(fcode, 0)


# ---------------------------------------------------------------------------------------------- which countries
def countries_near(lat, lon, reach_km, grid=None):
    """The countries with a populated place in a one-degree cell whose centre is within reach (plus half a cell)."""
    if grid is None:
        with gzip.open(GRID_FILE, "rt", encoding="utf-8") as fh:
            grid = json.load(fh)["cells"]
    out = set()
    for key, codes in grid.items():
        la, lo = (int(v) for v in key.split(","))
        if km(lat, lon, la + 0.5, lo + 0.5) <= reach_km + 80:
            out.update(codes)
    return sorted(out)


def build_grid(cities):
    cells = {}
    for c in cities:
        key = "%d,%d" % (math.floor(float(c["latitude"])), math.floor(float(c["longitude"])))
        cells.setdefault(key, set()).add(c["countrycode"])
    return {"cells": {k: sorted(v) for k, v in sorted(cells.items())}}


# ---------------------------------------------------------------------------------------------- one country file
def places_in(lines, lat, lon, reach_km):
    """[(name, lat, lon, weight)] of the populated places within reach, from the lines of a GeoNames country file."""
    out = []
    dlat = reach_km / 111.0 + 0.1
    for line in lines:
        f = line.rstrip("\n").split("\t")
        if len(f) < 15 or f[6] != "P" or f[7] in SKIP:
            continue
        try:
            la, lo, pop = float(f[4]), float(f[5]), int(f[14] or 0)
        except ValueError:
            continue
        if abs(la - lat) > dlat or km(lat, lon, la, lo) > reach_km:
            continue
        name = " ".join(f[1].split())
        w = weight(f[7], pop)
        if name and "\t" not in name and w > 0:
            out.append((name, round(la, 4), round(lo, 4), w))
    return out


def fetch(code, folder, opener=urllib.request.urlopen):
    """Download one country's file to folder; returns its path. Raises on any failure."""
    path = os.path.join(folder, "%s.zip" % code)
    req = urllib.request.Request(DUMP % code, headers={"User-Agent": USER_AGENT})
    with opener(req, timeout=60) as resp, open(path, "wb") as fh:
        while True:
            block = resp.read(1 << 16)
            if not block:
                break
            fh.write(block)
    return path


def read_zip(path, code):
    with zipfile.ZipFile(path) as z, z.open("%s.txt" % code) as fh:
        yield from io.TextIOWrapper(fh, encoding="utf-8")


def thin(rows):
    """The heaviest first; a lighter place within SAME_PLACE_KM of a heavier one is left out."""
    rows = sorted(rows, key=lambda r: -r[3])
    grid, kept = {}, []
    for r in rows:
        cell = (int(r[1] * 50), int(r[2] * 50))
        near = [k for dx in (-1, 0, 1) for dy in (-1, 0, 1) for k in grid.get((cell[0] + dx, cell[1] + dy), [])]
        if any(km(k[1], k[2], r[1], r[2]) < SAME_PLACE_KM for k in near):
            continue
        grid.setdefault(cell, []).append(r)
        kept.append(r)
    return kept


def write(rows, out, lat, lon, reach_km, codes):
    lines = ["# Populated places within %d km, weighted by population or rank: name, latitude, longitude, weight." % reach_km,
             "# From GeoNames (https://www.geonames.org/), Creative Commons Attribution 4.0 licence: the country files %s, %s."
             % (" ".join(codes), time.strftime("%Y-%m-%d")),
             "# centre %.2f %.2f %d" % (lat, lon, reach_km),
             "# Made by tools/make_local_places.py (zenithboard social places on); used by flightinfo/social_card.py."]
    lines += ["%s\t%s\t%s\t%d" % r for r in sorted(rows, key=lambda r: (r[1], r[2]))]
    tmp = out + ".tmp"
    with gzip.GzipFile(tmp, "wb", mtime=0) as fh:
        fh.write(("\n".join(lines) + "\n").encode("utf-8"))
    os.chmod(tmp, 0o644)
    os.replace(tmp, out)


def make(lat, lon, out, reach_km=KM_DEFAULT, opener=urllib.request.urlopen, grid=None, log=print):
    codes = countries_near(lat, lon, reach_km, grid)
    if not codes:
        raise RuntimeError("no country found near %.2f %.2f" % (lat, lon))
    log("Countries within %d km: %s" % (reach_km, " ".join(codes)))
    rows = []
    with tempfile.TemporaryDirectory(prefix="zb-places-") as folder:
        for code in codes:
            path = fetch(code, folder, opener)
            log("  %s: %.1f MB downloaded" % (code, os.path.getsize(path) / 1e6))
            got = places_in(read_zip(path, code), lat, lon, reach_km)
            os.unlink(path)
            log("  %s: %d populated places within reach" % (code, len(got)))
            rows += got
    rows = thin(rows)
    write(rows, out, lat, lon, reach_km, codes)
    log("Kept %d places in %s (%d KB)." % (len(rows), out, os.path.getsize(out) // 1024))
    return len(rows)


def main(argv):
    if len(argv) == 3 and argv[1] == "--grid":
        with open(argv[2], encoding="utf-8") as fh:
            grid = build_grid(json.load(fh).values())
        with gzip.GzipFile(GRID_FILE, "wb", mtime=0) as out:
            out.write(json.dumps(grid, separators=(",", ":")).encode("utf-8"))
        print("%d cells written to %s" % (len(grid["cells"]), GRID_FILE))
        return 0
    if len(argv) not in (4, 5):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        lat, lon = float(argv[1]), float(argv[2])
        reach = int(argv[4]) if len(argv) == 5 else KM_DEFAULT
        if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0) or not 50 <= reach <= 1000:
            raise ValueError
    except ValueError:
        print("Usage: make_local_places.py LAT LON OUT [KM 50-1000]; the receiver's position must be set.", file=sys.stderr)
        return 2
    try:
        make(lat, lon, argv[3], reach)
    except Exception as exc:                      # the list from before, if any, is kept as it was
        print("Could not make the list: %s. Nothing was changed." % exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
