#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ZenithBoard logo library: turn ANY logo image into a colour dot-matrix bitmap and manage your collection.

  logo_tool.py add    ICAO image.png [--box 36x32] [--colors 12]    convert and store (adds or replaces)
  logo_tool.py fetch  ICAO                                         download from LOGO_URL_TEMPLATE, convert, store
  logo_tool.py remove ICAO
  logo_tool.py list
  logo_tool.py convert image.png out.json                          convert only (no library change)

Logos are stored as small JSON files in <USER_DATA_DIR>/logos/<ICAO>.json (default /var/lib/zenithboard/logos).
ZenithBoard ships NO real airline logos: they are trademarks. Use logos you are entitled to use.
Requires Pillow (apt install python3-pil).
"""
import argparse
import io
import json
import os
import re
import sys
import urllib.request

CONFIG_FILE = os.environ.get("ZENITHBOARD_CONFIG", "/etc/zenithboard/config.env")
DEFAULT_BOX = (36, 32)          # fits the 38 x 34 dot logo area of the wall
ICAO_RE = re.compile(r"^[A-Z0-9]{2,4}$")


def read_config():
    cfg = {"USER_DATA_DIR": "/var/lib/zenithboard", "LOGO_URL_TEMPLATE": ""}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    cfg[k.strip()] = v.strip().strip("\"'")
    except OSError:
        pass
    return cfg


def convert_image(img, box=DEFAULT_BOX, colors=12, dark=40, tolerance=48):
    """PIL image -> logo dict {"w","h","palette","rows"}.  '.' = unlit dot."""
    from PIL import Image
    img = img.convert("RGBA")
    px = img.load()
    w0, h0 = img.size
    has_alpha = any(px[x, y][3] < 250 for x in range(0, w0, max(1, w0 // 40)) for y in range(0, h0, max(1, h0 // 40)))
    if not has_alpha:   # opaque picture (JPG, logo on a white card): treat the corner colour as the background
        corners = [px[0, 0], px[w0 - 1, 0], px[0, h0 - 1], px[w0 - 1, h0 - 1]]
        bg = tuple(sum(c[i] for c in corners) // 4 for i in range(3))
        for y in range(h0):
            for x in range(w0):
                r, g, b, _ = px[x, y]
                if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) < tolerance:
                    px[x, y] = (0, 0, 0, 0)
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    scale = min(box[0] / img.width, box[1] / img.height)
    size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    img = img.resize(size, Image.LANCZOS)
    rgba = img.load()
    opaque = Image.new("RGB", size, (0, 0, 0))
    mask = [[False] * size[0] for _ in range(size[1])]
    for y in range(size[1]):
        for x in range(size[0]):
            r, g, b, a = rgba[x, y]
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            if a >= 128 and lum >= dark:        # a black LED can not be lit: very dark pixels stay off
                mask[y][x] = True
                opaque.putpixel((x, y), (r, g, b))
    quant = opaque.quantize(colors=max(2, min(colors, 36)), method=Image.Quantize.MEDIANCUT)
    pal = quant.getpalette()[:3 * colors]
    used, rows = {}, []
    for y in range(size[1]):
        row = ""
        for x in range(size[0]):
            if not mask[y][x]:
                row += "."
                continue
            idx = quant.getpixel((x, y))
            if idx not in used:
                used[idx] = len(used)
            row += format(used[idx], "x") if used[idx] < 16 else chr(ord("a") + used[idx] - 10)
        rows.append(row)
    palette = [None] * len(used)
    for idx, n in used.items():
        palette[n] = "#%02x%02x%02x" % tuple(pal[3 * idx:3 * idx + 3])
    return {"w": size[0], "h": size[1], "palette": palette, "rows": rows}


def logos_dir(cfg):
    d = os.path.join(cfg["USER_DATA_DIR"], "logos")
    os.makedirs(d, exist_ok=True)
    return d


def parse_box(text):
    m = re.match(r"^(\d+)x(\d+)$", text)
    if not m:
        raise SystemExit("--box must look like 36x32")
    return int(m.group(1)), int(m.group(2))


def load_image(src):
    from PIL import Image
    if re.match(r"^https?://", src):
        req = urllib.request.Request(src, headers={"User-Agent": "ZenithBoard-logo-tool"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return Image.open(io.BytesIO(resp.read(5_000_000)))
    return Image.open(src)


def airline_iata(icao, cfg):
    for path in (os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "flightinfo", "data", "airlines_builtin.json"),
                 os.path.join(cfg["USER_DATA_DIR"], "data", "airlines.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                info = json.load(fh).get(icao)
            if info and info.get("iata"):
                return info["iata"]
        except (OSError, ValueError):
            pass
    return ""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add"); a.add_argument("icao"); a.add_argument("image")
    f = sub.add_parser("fetch"); f.add_argument("icao")
    for p in (a, f):
        p.add_argument("--box", default="%dx%d" % DEFAULT_BOX); p.add_argument("--colors", type=int, default=12)
    r = sub.add_parser("remove"); r.add_argument("icao")
    sub.add_parser("list")
    c = sub.add_parser("convert"); c.add_argument("image"); c.add_argument("out"); c.add_argument("--box", default="%dx%d" % DEFAULT_BOX)
    c.add_argument("--colors", type=int, default=12)
    args = ap.parse_args(argv)
    cfg = read_config()

    if args.cmd == "list":
        d = logos_dir(cfg)
        names = sorted(n[:-5] for n in os.listdir(d) if n.endswith(".json"))
        print("Logos in %s: %s" % (d, ", ".join(names) if names else "(none yet)"))
        return 0
    if args.cmd == "convert":
        logo = convert_image(load_image(args.image), parse_box(args.box), args.colors)
        with open(args.out, "w") as fh:
            json.dump(logo, fh)
        print("wrote %s (%dx%d, %d colours)" % (args.out, logo["w"], logo["h"], len(logo["palette"])))
        return 0

    icao = args.icao.upper()
    if not ICAO_RE.match(icao):
        raise SystemExit("ICAO airline code must be 2-4 letters/digits, e.g. AFR")
    path = os.path.join(logos_dir(cfg), icao + ".json")
    if args.cmd == "remove":
        if os.path.exists(path):
            os.remove(path)
            print("removed", icao)
        else:
            print("no logo for", icao)
        return 0
    if args.cmd == "fetch":
        tpl = cfg.get("LOGO_URL_TEMPLATE", "")
        if not tpl:
            raise SystemExit("LOGO_URL_TEMPLATE is empty. Set a source, e.g.\n  sudo zenithboard config-set LOGO_URL_TEMPLATE 'https://your-source/{iata}.png'\n"
                             "(placeholders: {icao} {iata}). Check the source's terms of use first.")
        iata = airline_iata(icao, cfg)
        if "{iata}" in tpl and not iata:
            raise SystemExit("No IATA code known for %s (run: zenithboard data update)" % icao)
        src = tpl.replace("{icao}", icao).replace("{iata}", iata)
    else:
        src = args.image
    logo = convert_image(load_image(src), parse_box(args.box), args.colors)
    with open(path, "w") as fh:
        json.dump(logo, fh)
    os.chmod(path, 0o644)
    print("stored %s (%dx%d, %d colours) -> %s" % (icao, logo["w"], logo["h"], len(logo["palette"]), path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
