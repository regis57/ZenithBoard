#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that the Pi can really fetch aircraft photos from Planespotters.

    zenithboard photos test            # try a few well-photographed airliners
    zenithboard photos test 3c6444     # try one aircraft by its ICAO hex

Useful before the antenna is connected: it tells you whether the Pi reaches the API, without waiting for an aircraft
to fly over. The picture itself is not downloaded: since 0.24.5 the tablet fetches it straight from Planespotters,
as their photo API terms require (the image fetched only by the screen that shows it), so the tablet needs internet.
"""
import json
import sys
import time
import urllib.request

API = "https://api.planespotters.net/pub/photos/hex/%s"
SAMPLES = ["3c6444", "4ca7b3", "406abc"]        # real, commonly photographed aircraft
TIMEOUT = 8
GAP_S = 2.5          # Planespotters refuses (403) requests that come too fast - the wall spaces them out too


def get(url, limit):
    req = urllib.request.Request(url, headers={"User-Agent": "ZenithBoard-photo-check (+https://github.com/regis57/ZenithBoard)"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:   # nosec - the fixed https API
        return resp.headers.get("Content-Type", ""), resp.read(limit)


def check(hex_code):
    hex_code = hex_code.lower().strip()
    try:
        _, raw = get(API % hex_code, 200_000)
        photos = json.loads(raw.decode("utf-8")).get("photos") or []
    except Exception as exc:
        if "403" in str(exc):
            print("  %s: refused (403) - asked too fast. The wall spaces its requests out, so this is harmless." % hex_code)
        else:
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
    print("  %s: OK - a photo by %s (the tablet loads it from %s)" % (hex_code, p.get("photographer") or "unknown",
                                                                  url.split("/")[2] if "//" in url else url))
    return True


def main(argv):
    codes = [argv[0]] if argv and argv[0] else SAMPLES
    print("Asking Planespotters for %d aircraft (one every %.1f s)..." % (len(codes), GAP_S))
    results = []
    for i, code in enumerate(codes):
        if i:
            time.sleep(GAP_S)
        results.append(check(code))
    if any(r is True for r in results):
        print("Photos work on this Pi. The tablet loads each picture from Planespotters itself, so it needs internet;"
              " aircraft without a published photo still show the animated sky scene.")
        return 0
    if all(r is None for r in results):
        print("Reached Planespotters, but none of these aircraft has a photo. Try another hex.")
        return 0
    print("Photos are not working. Check the Pi's internet connection, then try again.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
