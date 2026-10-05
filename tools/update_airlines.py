#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Downloads the OpenFlights airline list (ODbL licence, https://openflights.org/data.html) and converts it to
<USER_DATA_DIR>/data/airlines.json: {"AFR": {"name": "Air France", "iata": "AF"}, ...}.
The file stays on your machine; it is not part of the ZenithBoard repository.
  update_airlines.py [--file airlines.dat] [--out airlines.json]"""
import argparse
import csv
import io
import json
import os
import sys
import urllib.request

URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat"


def parse(text):
    out = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 8:
            continue
        _, name, _, iata, icao, _, _, active = row[:8]
        if active != "Y" or len(icao) != 3 or not icao.isalnum() or icao.upper() == "N/A":
            continue
        out[icao.upper()] = {"name": name.strip(), "iata": iata if iata not in ("\\N", "-", "") else ""}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file")
    ap.add_argument("--out", default="/var/lib/zenithboard/data/airlines.json")
    args = ap.parse_args()
    if args.file:
        text = open(args.file, encoding="utf-8").read()
    else:
        with urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "ZenithBoard"}), timeout=30) as resp:
            text = resp.read().decode("utf-8", "replace")
    data = parse(text)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, sort_keys=True)
    os.chmod(args.out, 0o644)
    print("%d airlines written to %s" % (len(data), args.out))


if __name__ == "__main__":
    sys.exit(main())
