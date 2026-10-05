#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Refresh the aircraft-type list used by the wall (model names + engine description).

The list comes from the free tar1090-db project (https://github.com/wiedehopf/tar1090-db, derived from the
Mictronics aircraft database). It is downloaded at run time and stored on the Pi only; it is never part of this
repository. Used by `zenithboard data update` and by the optional monthly timer.

The old file is only replaced when the download parses and looks sane, so a failed refresh changes nothing.
"""
import argparse
import datetime
import gzip
import json
import os
import re
import sys
import tempfile
import urllib.request

DEFAULT_URL = "https://raw.githubusercontent.com/wiedehopf/tar1090-db/master/db/icao_aircraft_types2.js"
DEFAULT_OUT = "/var/lib/zenithboard/data/types.json"
CODE_RE = re.compile(r"^[A-Z0-9]{2,4}$")
MIN_ENTRIES = 500          # the real list has ~2800: far fewer means a broken download


def parse_types(raw):
    """Bytes (optionally gzip-compressed) of {"A320": ["AIRBUS A-320", "L2J", "M"], ...} -> clean dict."""
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("unexpected format")
    out = {}
    for code, v in data.items():
        if not CODE_RE.match(str(code)) or not isinstance(v, list) or len(v) < 3:
            continue
        name, desc, wtc = (str(x or "").strip() for x in v[:3])
        out[code] = [name[:60], desc[:4], wtc[:1]]
    if len(out) < MIN_ENTRIES:
        raise ValueError("only %d entries - refusing to use this file" % len(out))
    return out


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "ZenithBoard-data-refresh"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:      # nosec - fixed https source (or file:// in tests)
        return resp.read(5_000_000)


def write_atomic(path, payload):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", prefix=".types-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, separators=(",", ":"), ensure_ascii=False)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--url", default=os.environ.get("ZB_TYPES_URL", DEFAULT_URL))
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    try:
        types = parse_types(fetch(args.url))
    except Exception as exc:                                         # network, parse, sanity - never touch the old file
        print("Aircraft data refresh failed (%s). Keeping the previous data." % exc, file=sys.stderr)
        return 1
    write_atomic(args.out, {"updated": datetime.date.today().isoformat(), "source": args.url, "count": len(types), "types": types})
    if not args.quiet:
        print("Aircraft data refreshed: %d types -> %s" % (len(types), args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
