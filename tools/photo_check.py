#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that the Pi can really fetch aircraft photos from Planespotters.

    zenithboard photos test            # try a few well-photographed airliners
    zenithboard photos test 3c6444     # try one aircraft by its ICAO hex

Useful before the antenna is connected: it tells you whether the network, the API and the image download work,
without waiting for an aircraft to fly over. Nothing is stored; the wall fetches photos the same way.
"""
import json
import sys
import urllib.request

API = "https://api.planespotters.net/pub/photos/hex/%s"
SAMPLES = ["3c6444", "4ca7b3", "406abc"]        # real, commonly photographed aircraft
TIMEOUT = 8


def get(url, limit):
    req = urllib.request.Request(url, headers={"User-Agent": "ZenithBoard-photo-check"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:   # nosec - fixed https API and the image it points to
        return resp.headers.get("Content-Type", ""), resp.read(limit)


def check(hex_code):
    hex_code = hex_code.lower().strip()
    try:
        _, raw = get(API % hex_code, 200_000)
        photos = json.loads(raw.decode("utf-8")).get("photos") or []
    except Exception as exc:
        print("  %s: cannot reach Planespotters (%s)" % (hex_code, exc))
        return False
    if not photos:
        print("  %s: no photo published for this aircraft (the wall shows the animated sky instead)" % hex_code)
        return None
    p = photos[0]
    url = (p.get("thumbnail_large") or {}).get("src")
    if not url:
        print("  %s: the entry has no usable image" % hex_code)
        return False
    try:
        ctype, data = get(url, 3_000_000)
    except Exception as exc:
        print("  %s: found a photo but could not download it (%s)" % (hex_code, exc))
        return False
    print("  %s: OK - %s, %d kB, by %s" % (hex_code, ctype or "image", len(data) // 1024, p.get("photographer") or "unknown"))
    return True


def main(argv):
    codes = [argv[0]] if argv and argv[0] else SAMPLES
    print("Asking Planespotters for %d aircraft..." % len(codes))
    results = [check(c) for c in codes]
    if any(r is True for r in results):
        print("Photos work on this Pi. Aircraft without a published photo still show the animated sky scene.")
        return 0
    if all(r is None for r in results):
        print("Reached Planespotters, but none of these aircraft has a photo. Try another hex.")
        return 0
    print("Photos are not working. Check the Pi's internet connection, then try again.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
