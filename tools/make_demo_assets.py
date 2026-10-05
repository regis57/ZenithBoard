#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generates the demo assets: ORIGINAL fictional airline logos (dot-matrix JSON), generic aircraft
illustrations (SVG) standing in for Planespotters photos, and the demo airline list.
No real airline artwork is used or reproduced. Run from the repo root:  python3 tools/make_demo_assets.py"""
import json
import math
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "flightinfo", "demo")
os.makedirs(os.path.join(OUT, "logos"), exist_ok=True)
os.makedirs(os.path.join(OUT, "photos"), exist_ok=True)

# ------------------------------------------------------------------ fictional airlines
AIRLINES = {"ZZA": {"name": "Zenith Air", "iata": "ZA"},
            "ZZB": {"name": "Nimbus Jet", "iata": "ZB"},
            "ZZC": {"name": "Aurora Air", "iata": "ZC"}}


def logo_json(w, h, palette, painter):
    rows = []
    for y in range(h):
        row = ""
        for x in range(w):
            idx = painter(x + 0.5, y + 0.5)
            row += "." if idx is None else format(idx, "x")
        rows.append(row)
    return {"w": w, "h": h, "palette": palette, "rows": rows}


def zenith(x, y):             # teal disc with a white caret
    if math.hypot(x - 16, y - 16) > 15:
        return None
    d = abs(x - 16)
    if 9 <= y <= 22 and (y - 9) * 0.9 - 3.2 <= d <= (y - 9) * 0.9 + 0.6:
        return 1
    return 0


def nimbus(x, y):             # light-blue cloud with an orange stripe
    cloud = (math.hypot(x - 10, y - 19) <= 6 or math.hypot(x - 17, y - 15) <= 8
             or math.hypot(x - 24, y - 19) <= 6 or (10 <= x <= 24 and 19 <= y <= 25))
    if not cloud:
        return None
    return 1 if 21.5 <= y <= 23.5 else 0


def aurora(x, y):             # three concentric arcs
    if y > 27:
        return None
    r = math.hypot(x - 16, y - 27)
    for radius, idx in ((15, 0), (11, 1), (7, 2)):
        if radius - 3 <= r <= radius:
            return idx
    return None


LOGOS = {"ZZA": (32, 32, ["#00b3b3", "#ffffff"], zenith),
         "ZZB": (32, 32, ["#6ec1ff", "#ff9f1c"], nimbus),
         "ZZC": (32, 28, ["#35e08c", "#35c9e0", "#c75bff"], aurora)}

# ------------------------------------------------------------------ generic aircraft illustrations (side view, nose right)
SKY = ('<defs><linearGradient id="s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4a98f0"/>'
       '<stop offset="1" stop-color="#d6ecff"/></linearGradient></defs><rect width="300" height="200" fill="url(#s)"/>'
       '<ellipse cx="60" cy="40" rx="34" ry="10" fill="#fff" opacity=".8"/><ellipse cx="230" cy="62" rx="40" ry="11" fill="#fff" opacity=".7"/>'
       '<rect y="176" width="300" height="24" fill="#4e6b4a"/>')


def windows(x0, x1, y, n):
    step = (x1 - x0) / n
    return "".join('<circle cx="%.1f" cy="%d" r="2.2" fill="#2a3641"/>' % (x0 + i * step, y) for i in range(n + 1))


def narrow(acc):
    return ('<path d="M38 106 L228 100 Q270 102 278 114 Q270 126 228 128 L60 130 Q40 124 38 106 Z" fill="#f4f6f8"/>'
            '<path d="M44 108 L30 54 L56 54 L96 104 Z" fill="%s"/><path d="M50 112 L26 122 L66 122 Z" fill="#cfd6dc"/>'
            '<path d="M138 124 L96 154 L122 156 L186 126 Z" fill="#aab4bd"/><ellipse cx="150" cy="140" rx="17" ry="8" fill="#8f9aa5"/>'
            '<rect x="50" y="116" width="200" height="4" fill="%s"/>' % (acc, acc)
            + windows(84, 230, 110, 14) + '<path d="M252 104 L268 108 L268 114 L254 112 Z" fill="#26323d"/>')


def wide(acc):
    return ('<path d="M30 104 L220 94 Q272 96 282 112 Q272 130 220 132 L58 134 Q32 126 30 104 Z" fill="#f4f6f8"/>'
            '<path d="M38 106 L22 44 L52 44 L102 100 Z" fill="%s"/><path d="M46 112 L18 124 L68 124 Z" fill="#cfd6dc"/>'
            '<path d="M140 128 L84 162 L116 164 L196 130 Z" fill="#aab4bd"/><ellipse cx="146" cy="146" rx="15" ry="8" fill="#8f9aa5"/>'
            '<ellipse cx="174" cy="140" rx="15" ry="8" fill="#7d8893"/><rect x="46" y="118" width="212" height="5" fill="%s"/>' % (acc, acc)
            + windows(80, 232, 108, 16) + '<path d="M254 100 L272 106 L274 112 L256 110 Z" fill="#26323d"/>')


def turboprop(acc):
    return ('<path d="M40 112 L210 106 Q246 108 252 118 Q246 128 210 130 L62 132 Q42 126 40 112 Z" fill="#f4f6f8"/>'
            '<path d="M46 112 L34 60 L58 60 L84 110 Z" fill="%s"/><path d="M30 62 L66 62 L66 68 L30 68 Z" fill="#cfd6dc"/>'
            '<path d="M104 104 L100 92 L192 92 L196 106 Z" fill="#aab4bd"/><ellipse cx="170" cy="100" rx="22" ry="9" fill="#8f9aa5"/>'
            '<ellipse cx="196" cy="98" rx="3.2" ry="30" fill="#3b4650" opacity=".55"/><rect x="52" y="120" width="180" height="4" fill="%s"/>' % (acc, acc)
            + windows(96, 206, 114, 10) + '<path d="M228 108 L244 112 L244 117 L230 116 Z" fill="#26323d"/>')


def bizjet(acc):
    return ('<path d="M60 112 L204 104 Q236 106 244 116 Q236 126 204 128 L78 130 Q60 124 60 112 Z" fill="#f4f6f8"/>'
            '<path d="M70 112 L60 62 L82 62 L104 108 Z" fill="%s"/><path d="M52 62 L92 62 L92 68 L52 68 Z" fill="#cfd6dc"/>'
            '<path d="M150 124 L118 150 L140 152 L184 126 Z" fill="#aab4bd"/><ellipse cx="96" cy="108" rx="22" ry="8" fill="#8f9aa5"/>'
            '<rect x="70" y="118" width="150" height="3" fill="%s"/>' % (acc, acc) + windows(130, 200, 112, 6)
            + '<path d="M214 107 L232 112 L232 117 L216 116 Z" fill="#26323d"/>')


def heli(acc):
    return ('<rect x="62" y="70" width="190" height="4" fill="#2f3a44"/><rect x="144" y="74" width="8" height="18" fill="#2f3a44"/>'
            '<ellipse cx="170" cy="116" rx="52" ry="28" fill="%s"/><path d="M130 108 L40 100 L36 112 L132 126 Z" fill="%s"/>'
            '<rect x="28" y="88" width="6" height="34" fill="#2f3a44"/><path d="M180 100 Q206 100 214 114 L184 116 Z" fill="#26323d"/>'
            '<rect x="120" y="150" width="108" height="5" fill="#2f3a44"/><rect x="138" y="140" width="5" height="12" fill="#2f3a44"/>'
            '<rect x="200" y="140" width="5" height="12" fill="#2f3a44"/>' % (acc, acc))


PHOTOS = {"narrow_teal": (narrow, "#00b3b3"), "bizjet_blue": (bizjet, "#2f7fd8"), "wide_violet": (wide, "#8a3fd1"),
          "turboprop_teal": (turboprop, "#00b3b3"), "narrow_neutral": (narrow, "#5b6b7a"), "heli_red": (heli, "#c8372d")}

with open(os.path.join(OUT, "airlines.json"), "w") as fh:
    json.dump(AIRLINES, fh, indent=1, sort_keys=True)
for icao, (w, h, pal, fn) in LOGOS.items():
    with open(os.path.join(OUT, "logos", icao + ".json"), "w") as fh:
        json.dump(logo_json(w, h, pal, fn), fh)
for name, (fn, acc) in PHOTOS.items():
    with open(os.path.join(OUT, "photos", name + ".svg"), "w") as fh:
        fh.write('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200">%s%s</svg>' % (SKY, fn(acc)))
print("demo assets written to", os.path.abspath(OUT))
