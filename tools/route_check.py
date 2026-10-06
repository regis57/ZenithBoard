#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that the Pi can look up flight routes (origin / destination) on adsbdb.com.

    zenithboard routes test            # a few well-known airline callsigns
    zenithboard routes test TRA913C    # one callsign

Only the callsign is sent, never your position. Nothing is stored.
"""
import json
import sys
import time
import urllib.error
import urllib.request

API = "https://api.adsbdb.com/v0/callsign/%s"
SAMPLES = ["DLH4YK", "RYR8WL", "TRA913C"]
GAP_S = 1.5


def label(a):
    if not isinstance(a, dict):
        return "?"
    return "%s %s (%s)" % (a.get("iata_code") or a.get("icao_code") or "", a.get("name") or "", a.get("municipality") or "")


def check(cs):
    cs = cs.upper().strip()
    req = urllib.request.Request(API % cs, headers={"User-Agent": "ZenithBoard-route-check (+https://github.com/regis57/ZenithBoard)"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:   # nosec - fixed https API
            fr = (json.load(resp).get("response") or {}).get("flightroute") or {}
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print("  %s: reached adsbdb, this callsign is not in its database (the wall shows no route for it)" % cs)
            return None
        print("  %s: adsbdb answered HTTP %s (the wall retries after a minute)" % (cs, exc.code))
        return False
    except Exception as exc:
        print("  %s: cannot reach adsbdb.com (%s). Check the Pi's internet and DNS." % (cs, exc))
        return False
    print("  %s: OK  %s  ->  %s" % (cs, label(fr.get("origin")), label(fr.get("destination"))))
    return True


def main(argv):
    codes = [argv[0]] if argv and argv[0] else SAMPLES
    print("Asking adsbdb.com for %d callsign(s)..." % len(codes))
    results = []
    for i, cs in enumerate(codes):
        if i:
            time.sleep(GAP_S)
        results.append(check(cs))
    if any(r is True for r in results):
        print("Routes work on this Pi.")
        return 0
    if all(r is None for r in results):
        print("Reached adsbdb, but none of these callsigns is known. Try another one.")
        return 0
    print("Routes are not working. Check the Pi's internet connection, then try again (or: zenithboard logs flightinfo).")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
