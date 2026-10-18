#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build flightinfo/data/cities100k.tsv: the cities of 100 000 inhabitants or more, for the statistics page.

The page names the large city nearest to the day's farthest aircraft (0.22.0). The list comes from GeoNames
(https://www.geonames.org/), whose data is under the Creative Commons Attribution 4.0 licence: the file says so in
its first lines and the page credits it. The population is the city's own, not its urban area.

    python3 tools/make_cities.py cities15000.txt > flightinfo/data/cities100k.tsv     # GeoNames' own dump
    python3 tools/make_cities.py cities15000.json "cities15000 as shipped by geonamescache 3.0.2 (PyPI)" > ...

cities15000.txt is GeoNames' tab-separated dump (download.geonames.org/export/dump/cities15000.zip): name in column
2, latitude 5, longitude 6, country code 9, population 15. The JSON form is the copy the geonamescache package ships
(a dict of {"name", "latitude", "longitude", "countrycode", "population"}), used when geonames.org cannot be reached.
"""
import json
import math
import sys

MIN_POPULATION = 100000
# GeoNames lists the districts of the largest cities as places of their own (the Paris arrondissements, Neukölln,
# "Lyon 03"). A place this close to a more populous one of the same country is taken for one of its districts and
# left out, so the page says "near Paris" rather than "near Paris 15 Vaugirard". Two real cities this close (Mannheim
# and Ludwigshafen) are named by the larger, which reads just as well.
DISTRICT_KM = 15
# GeoNames entries that carry the population of an administrative area rather than of a place. Each one was checked
# before it was listed here (0.22.0); an entry is not removed on a hunch. Found when the preview named a point over
# the Channel off Calais "near Saint Peters, GB".
NOT_CITIES = {
    ("GB", "Saint Peters"): "St Peter's, Kent: part of Broadstairs, about 7 000 people; 125 370 is the Thanet district",
    ("GB", "Mendip"): "a former district of Somerset (abolished 2023), about 110 000 people, not a town",
}


def rows_from_geonames_txt(fh):
    for line in fh:
        f = line.rstrip("\n").split("\t")
        if len(f) < 15:
            continue
        yield f[1], f[8], f[4], f[5], f[14]


def rows_from_geonamescache_json(fh):
    for c in json.load(fh).values():
        yield c["name"], c["countrycode"], c["latitude"], c["longitude"], c["population"]


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[2], a[3], b[2], b[3]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


def drop_districts(rows):
    """Largest first; a place within DISTRICT_KM of a larger one already kept, same country, is left out."""
    kept = []
    for r in sorted(rows, key=lambda r: -r[4]):
        if not any(k[1] == r[1] and abs(k[2] - r[2]) < 0.5 and km(k, r) < DISTRICT_KM for k in kept):
            kept.append(r)
    return kept


def build(rows, source):
    out = []
    for name, cc, lat, lon, pop in rows:
        try:
            pop, lat, lon = int(pop), float(lat), float(lon)
        except (TypeError, ValueError):
            continue
        name = " ".join(str(name).split())
        if pop < MIN_POPULATION or not name or "\t" in name or (str(cc).upper(), name) in NOT_CITIES:
            continue
        out.append((name, str(cc).upper()[:2], round(lat, 4), round(lon, 4), pop))
    out = drop_districts(out)
    out.sort(key=lambda r: (r[1], r[0]))
    lines = ["# Cities of %d inhabitants or more: name, country, latitude, longitude, population." % MIN_POPULATION,
             "# From GeoNames (https://www.geonames.org/), Creative Commons Attribution 4.0 licence. Source: %s" % source,
             "# Made by tools/make_cities.py; used by flightinfo/server.py to name the city nearest an aircraft."]
    lines += ["%s\t%s\t%s\t%s\t%d" % r for r in out]
    return "\n".join(lines) + "\n"


def main(argv):
    if len(argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        return 2
    path = argv[1]
    with open(path, encoding="utf-8") as fh:
        rows = list(rows_from_geonamescache_json(fh) if path.endswith(".json") else rows_from_geonames_txt(fh))
    sys.stdout.write(build(rows, argv[2] if len(argv) == 3 else path.rsplit("/", 1)[-1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
