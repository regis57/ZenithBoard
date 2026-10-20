#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build flightinfo/data/places5000.tsv.gz: the places of 5 000 inhabitants or more, named on the posts' satellite and
terrain maps (0.24.4). Those maps' own label layer named one village in forty kilometres (Amnéville, on a real post
over Metz); the owner asked for the towns to be named every time, as the OpenStreetMap map does.

The list comes from GeoNames (https://www.geonames.org/), Creative Commons Attribution 4.0: the file says so in its
first lines and the picture's credit names it.

    python3 tools/make_places.py cities5000.json "cities5000 as shipped by geonamescache 3.0.2 (PyPI)"
    python3 tools/make_places.py --small cities1000.json "cities1000 as shipped by geonamescache 3.0.2 (PyPI)"

--small (0.26.2) builds flightinfo/data/places1000.tsv.gz instead: the villages of 1 000 to 4 999, for the maps that
name fewer than three towns from the first list.

cities5000.json is the copy the geonamescache package ships (geonames.org itself could not be reached from the build).
"""
import gzip
import json
import math
import re
import sys

MIN_POPULATION = 5000
DISTRICT_KM = 2.5            # a place this close to a larger one of the same country is taken for one of its districts


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[1], a[2], b[1], b[2]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


def build(cities, source, low=MIN_POPULATION, high=None):
    rows = []
    for c in cities:
        name = " ".join(str(c["name"]).split())
        pop = int(c["population"] or 0)
        if pop < low or (high is not None and pop >= high) or not name or "\t" in name or re.search(r"\d", name):   # "Lyon 03", "Paris 15"
            continue
        rows.append((name, round(float(c["latitude"]), 3), round(float(c["longitude"]), 3), pop, c["countrycode"]))
    rows.sort(key=lambda r: -r[3])
    grid, kept = {}, []
    for r in rows:
        cell = (int(r[1] * 20), int(r[2] * 20))
        near = [k for dx in (-1, 0, 1) for dy in (-1, 0, 1) for k in grid.get((cell[0] + dx, cell[1] + dy), [])]
        if any(k[4] == r[4] and km(k, r) < DISTRICT_KM for k in near):
            continue
        grid.setdefault(cell, []).append(r)
        kept.append(r)
    kept.sort(key=lambda r: (r[1], r[2]))
    lines = [("# Places of %d inhabitants or more: name, latitude, longitude, population." % low) if high is None else
             ("# Places of %d to %d inhabitants: name, latitude, longitude, population." % (low, high - 1)),
             "# From GeoNames (https://www.geonames.org/), Creative Commons Attribution 4.0 licence. Source: %s" % source,
             "# Made by tools/make_places.py; used by flightinfo/social_card.py to name the towns on the posts' maps."]
    lines += ["%s\t%s\t%s\t%d" % r[:4] for r in kept]
    return "\n".join(lines) + "\n"


def main(argv):
    small = len(argv) > 1 and argv[1] == "--small"
    if small:
        argv = argv[:1] + argv[2:]
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        cities = json.load(fh).values()
    text = build(cities, argv[2], 1000, MIN_POPULATION) if small else build(cities, argv[2])
    target = "flightinfo/data/places1000.tsv.gz" if small else "flightinfo/data/places5000.tsv.gz"
    with gzip.GzipFile(target, "wb", mtime=0) as out:
        out.write(text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
