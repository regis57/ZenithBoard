# SPDX-License-Identifier: GPL-3.0-or-later
"""The split-flap picture for social sharing (0.19.0): the board, as the wall's split-flap look draws it, beside a
map with the aircraft's track. Pillow draws it on the Pi itself, in a second or two on a Pi 3B: no browser.

The same map also goes beside the dot-matrix wall (the "dotmap" look, 0.23.0): tools/social-render.js draws the
dots with the right-hand column left dark, and render_dotmap() lays the map in that column.

The board's rows come from the wall's own formatting (tools/social-render.js --lines), so they read exactly like
the tablet; this file only paints them. The map comes from EOX's tile service (maps.eox.at), whose layers are
"free to use" with a link back and the attribution, both of which every picture and every post carry:

    normal     EOX's light relief (OpenStreetMap and others) with EOX's roads, tinted here (0.26.1)
    night      the same, darkened here (inverted, hue turned back, dimmed), the roads left white
    satellite  Sentinel-2 cloudless (EOX, CC BY-NC-SA 4.0: non-commercial)
    terrain    EOX's terrain rendering (OpenStreetMap and elevation data)

All four name the towns themselves, from GeoNames (0.24.4; the light and dark ones since 0.25.3), over the track,
and none carries names of its own (0.26.1), so no town is named twice.
    none       no map: the track on black

OpenStreetMap's own tile servers are not used: their policy rules out automated fetching that no one is looking
at. Tiles are cached under the service's state folder for a month, so the few tiles over the owner's area are
fetched once, not at every post.

Privacy, as for the dot-matrix picture: the map is centred on the track, not on the receiver, and nothing marks
the receiver.
"""
import concurrent.futures
import gzip
import io
import math
import os
import time
import urllib.request

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

W, H, M = 1500, 900, 20                      # the picture, and its margin
COLS, ROWS = 14, 9                           # the board: 14 letters (the tablet's 16 less two, for a wider map) x 9 rows
CW, CH = 50, 95                              # one flap
BOARD_W, BOARD_H = COLS * CW, ROWS * CH
MAP_X = M + BOARD_W + M
MAP_W, MAP_H = W - MAP_X - M, H - 2 * M
BOARD_Y = M + (MAP_H - BOARD_H) // 2
CHARS = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,-/:+()→"   # what a flap carries: flap.js has the same set

TILE_HOST = "https://tiles.maps.eox.at/wmts/1.0.0/"
S2_YEAR = 2025                               # the newest Sentinel-2 cloudless layer EOX publishes (s2cloudless-2025_3857)
# Two credits for each map. credit_full is the whole required text: drawn on the picture and read in the alt text.
# credit is the line in the post: short, with its words as links (Bluesky shows a word and opens its address), so the
# post carries what the licences ask of an online publication — the name, and a way to the details — without three
# lines of small print under every aircraft (0.19.6, asked for after the first satellite post). OSMF's attribution
# guideline accepts "© OpenStreetMap" with the name linked to its copyright page; EOX asks for its name and a link.
OSM_LINK = ("OpenStreetMap", "https://www.openstreetmap.org/copyright")
EOX_LINK = ("EOX", "https://maps.eox.at")
GEONAMES_LINK = ("GeoNames", "https://www.geonames.org/")
PLACES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "places5000.tsv.gz")
# 0.26.2: the villages of 1 000 to 4 999, read only for a map that names fewer than MIN_NAMES towns from the list
# above. DAH1217, two minutes after leaving Metz-Nancy, went out on a 20 km strip east of the Moselle with no name at
# all: every town of 5 000 there is in the valley, a few kilometres beyond the map's edge.
SMALL_PLACES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "places1000.tsv.gz")
MIN_NAMES = 3
# 0.27.3: then the empty parts. SWR3AG over the Moselle plateau named seven towns, all on the edges, and nothing in
# the 30 km between them: a village is added where no name is within GAP_PX of its dot, the heaviest first.
GAP_PX = 120
# 0.27.0: the region's own list, made on the Pi from GeoNames' country files (tools/make_local_places.py, `social
# places on`): every populated place within 400 km, weighted by population or, where GeoNames knows none (almost every
# village in Indonesia), by its rank. social.py sets the path when the owner switched it on; None: the shipped lists.
LOCAL_PLACES_FILE = None
TIERS = (5000, 1000, 0)                      # weights a map goes down through until it names MIN_NAMES places
MAX_NAMES = 26                               # the towns named on a map, the largest first, none over another (0.25.2: 16 before)
MAP_STYLES = {
    # 0.26.1: the light and dark maps are built from two EOX layers that carry no names, the light relief and the
    # roads, under the names ZenithBoard draws. 0.25.3 drew those names over EOX's OpenStreetMap layer, whose own
    # labels stayed underneath: every town twice, a few pixels apart (seen on the real posts, EWG8QR over Nancy).
    # EOX has no OpenStreetMap layer without its labels. The roads layer is white; the light map tints it.
    "normal": {"layers": [("terrain-light_3857", "jpg"), ("streets_3857", "png")], "roads": (214, 140, 60),
               "names": "dark", "words": "a light relief map with the main roads",
               "credit": "Map \u00a9 OpenStreetMap, EOX, GeoNames", "links": [OSM_LINK, EOX_LINK, GEONAMES_LINK],
               "credit_full": "\u00a9 OpenStreetMap contributors and others, rendering \u00a9 EOX (maps.eox.at); place names: GeoNames (CC BY 4.0)"},
    "night": {"layers": [("terrain-light_3857", "jpg"), ("streets_3857", "png")], "night": True,
              "names": "light", "words": "a dark relief map with the main roads",
              "credit": "Map \u00a9 OpenStreetMap, EOX, GeoNames", "links": [OSM_LINK, EOX_LINK, GEONAMES_LINK],
              "credit_full": "\u00a9 OpenStreetMap contributors and others, rendering \u00a9 EOX (maps.eox.at); place names: GeoNames (CC BY 4.0)"},
    # 0.24.4: the terrain and satellite maps name the towns themselves (from GeoNames, "names"), in place of EOX's label
    # layer, which named one village in forty kilometres on a real post over Metz
    "terrain": {"layers": [("terrain_3857", "jpg")], "names": "dark", "words": "a terrain map",
                "credit": "Map \u00a9 OpenStreetMap and others, EOX, GeoNames", "links": [OSM_LINK, EOX_LINK, GEONAMES_LINK],
                "credit_full": "Terrain: data \u00a9 OpenStreetMap contributors and others, rendering \u00a9 EOX (maps.eox.at); "
                               "place names: GeoNames (CC BY 4.0)"},
    "satellite": {"layers": [("s2cloudless-%d_3857" % S2_YEAR, "jpg")], "names": "light", "words": "a satellite map",
                  "credit": "Map: EOxCloudless by EOX, GeoNames",
                  "links": [("EOxCloudless", "https://cloudless.eox.at"), ("EOX", "https://eox.at"), GEONAMES_LINK],
                  "credit_full": "EOxCloudless %d https://cloudless.eox.at by EOX IT Services GmbH (Contains modified Copernicus Sentinel data %d); "
                                 "place names: GeoNames (CC BY 4.0)" % (S2_YEAR, S2_YEAR)},
    "none": {"layers": [], "words": "", "credit": None, "links": [], "credit_full": None},
}
MAX_ZOOM, MIN_ZOOM = 12, 4                   # 12: about 18 km across the map at 49 degrees north
LEGEND_W = 340                               # the legend box's widest (a 100 km bar and its label): what the aircraft must clear
FIT = 0.7                                    # the track takes at most this share of the map, so the aircraft is never on the edge
CACHE_DAYS = 30
CACHE_MAX_BYTES = 60 * 1024 * 1024
TILE_MAX_BYTES = 2 * 1024 * 1024
FETCH_BUDGET_S = 25                          # all the tiles of one picture, whatever the network does
FONT_DIRS = ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/TTF", "/usr/share/fonts/dejavu")
LANCZOS = getattr(Image, "Resampling", Image).LANCZOS


# --------------------------------------------------------------------------- fonts and colours
def font(size, bold=True, condensed=False):
    names = (["DejaVuSansCondensed-Bold.ttf"] if condensed else []) + (["DejaVuSans-Bold.ttf"] if bold else ["DejaVuSans.ttf"])
    for d in FONT_DIRS:
        for n in names:
            p = os.path.join(d, n)
            if os.path.isfile(p):
                return ImageFont.truetype(p, size)
    try:
        return ImageFont.load_default(size=size)  # Pillow 10.1 and later
    except TypeError:
        return ImageFont.load_default()


def rgb(hex_color):
    h = str(hex_color).lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) if len(h) == 6 else (255, 176, 0)


# --------------------------------------------------------------------------- the board
def _flap_template():
    """One empty flap, as app.js paints it: two halves with a soft vertical gradient, a dark hinge between."""
    pad = max(1, int(round(CW * 0.06)))
    cell = Image.new("RGB", (CW, CH), (0, 0, 0))
    d = ImageDraw.Draw(cell)
    h = CH - 2 * pad
    for y in range(h):
        k = y / max(1, h - 1)
        if k < 0.5:
            v = int(0x20 + (0x15 - 0x20) * (k / 0.5))
        else:
            v = int(0x12 + (0x0b - 0x12) * ((k - 0.5) / 0.5))
        d.line([(pad, pad + y), (CW - pad - 1, pad + y)], fill=(v, v, v))
    return cell, pad


def _glyph(ch, color, pad, cache, fnt, squeeze):
    if ch in cache:
        return cache[ch]
    w, h = CW - 2 * pad, CH - 2 * pad
    wide = int(w / squeeze) + 2                  # drawn at full width, then squeezed like the wall squeezes wide fonts
    g = Image.new("RGBA", (wide, h), (0, 0, 0, 0))
    ImageDraw.Draw(g).text((wide / 2.0, h * 0.53), ch, font=fnt, fill=color + (255,), anchor="mm")
    if squeeze < 1:
        g = g.resize((max(1, int(round(wide * squeeze))), h), LANCZOS)
    cache[ch] = g
    return g


def draw_board(lines, color):
    """The rows on flaps, COLS x ROWS. A letter a flap cannot carry shows as a blank flap, as on the wall."""
    color = rgb(color)
    board = Image.new("RGB", (BOARD_W, BOARD_H), (0, 0, 0))
    tpl, pad = _flap_template()
    fnt = font(int(round(CH * 0.66)), condensed=True)
    wide = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), "W", font=fnt)
    squeeze = min(1.0, (CW - 2 * pad) * 0.9 / max(1, wide[2] - wide[0]))
    cache = {}
    for r in range(ROWS):
        line = str(lines[r]) if r < len(lines) and lines[r] is not None else ""
        for c in range(COLS):
            ch = line[c].upper() if c < len(line) else " "
            if ch not in CHARS:
                ch = " "
            cell = tpl.copy()
            if ch != " ":
                g = _glyph(ch, color, pad, cache, fnt, squeeze)
                cell.paste(g, (pad + (CW - 2 * pad - g.width) // 2, pad), g)
            ImageDraw.Draw(cell).rectangle([pad, CH // 2 - 1, CW - pad - 1, CH // 2], fill=(0, 0, 0))   # the hinge
            board.paste(cell, (c * CW, r * CH))
    return board


# --------------------------------------------------------------------------- the map
def world_px(lat, lon, z):
    """Web Mercator: a position in pixels of the whole world at zoom z (256-pixel tiles)."""
    n = 256.0 * (2 ** z)
    lat = max(-85.0511, min(85.0511, lat))
    s = math.sin(math.radians(lat))
    return (lon + 180.0) / 360.0 * n, (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n


def choose_view(trace, w, h):
    """The highest zoom at which the whole track fits in FIT of the map; the map centred on the track (never on the
    receiver). Returns (zoom, origin_x, origin_y) in world pixels."""
    pts = [(p[0], p[1]) for p in trace] or [(0.0, 0.0)]
    z = MAX_ZOOM
    while True:
        xy = [world_px(la, lo, z) for la, lo in pts]
        xs, ys = [p[0] for p in xy], [p[1] for p in xy]
        if z <= MIN_ZOOM or (max(xs) - min(xs) <= w * FIT and max(ys) - min(ys) <= h * FIT):
            break
        z -= 1
    cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    return z, int(round(cx - w / 2.0)), int(round(cy - h / 2.0))


def tile_url(layer, ext, z, x, y):
    """EOX's WMTS RESTful form, GoogleMapsCompatible set "g": .../{layer}/default/g/{z}/{row}/{col}.{ext}
    (the row, y, before the column, x: as WMTSCapabilities.xml writes it)."""
    return "%s%s/default/g/%d/%d/%d.%s" % (TILE_HOST, layer, z, y, x, ext)


def fetch_tile(layer, ext, z, x, y, cache_dir=None, user_agent="ZenithBoard", opener=None):
    """One tile's bytes, from the cache when it is under a month old, else from EOX (and then cached). None when it
    cannot be had; a stale cached copy is better than nothing when the network fails."""
    path = os.path.join(cache_dir, layer, str(z), str(x), "%d.%s" % (y, ext)) if cache_dir else None
    stale = None
    if path and os.path.isfile(path):
        try:
            with open(path, "rb") as fh:
                stale = fh.read()
            if time.time() - os.path.getmtime(path) < CACHE_DAYS * 86400:
                return stale
        except OSError:
            stale = None                         # unreadable cache entry: as if absent
    req = urllib.request.Request(tile_url(layer, ext, z, x, y), headers={"User-Agent": user_agent})
    try:
        with (opener or urllib.request.urlopen)(req, timeout=10) as resp:
            final = getattr(resp, "geturl", lambda: "https://")()
            if not str(final).startswith("https://"):           # a redirect off HTTPS is not followed
                return stale
            data = resp.read(TILE_MAX_BYTES + 1)
        if len(data) > TILE_MAX_BYTES:
            return stale
        im = Image.open(io.BytesIO(data))
        if im.size != (256, 256):                     # a tile, not an error page nor a decompression bomb
            return stale
        im.verify()
    except Exception:
        return stale
    if path:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "wb") as fh:
                fh.write(data)
            os.replace(tmp, path)
        except OSError:
            pass                                 # a cache that cannot be written is just no cache
    return data


def prune_cache(cache_dir, now=None):
    """Tiles over two months old go, then the oldest until the cache is under CACHE_MAX_BYTES. A tile between one
    and two months is stale — fetched again when EOX answers — but still a map when it does not."""
    if not cache_dir or not os.path.isdir(cache_dir):
        return
    now = now or time.time()
    files = []
    for root, _dirs, names in os.walk(cache_dir):
        for n in names:
            p = os.path.join(root, n)
            try:
                st = os.stat(p)
            except OSError:
                continue                         # removed meanwhile
            if now - st.st_mtime > 2 * CACHE_DAYS * 86400:
                try:
                    os.unlink(p)
                except OSError:
                    pass                         # removed meanwhile
            else:
                files.append((st.st_mtime, st.st_size, p))
    total = sum(f[1] for f in files)
    for _mt, size, p in sorted(files):
        if total <= CACHE_MAX_BYTES:
            break
        try:
            os.unlink(p)
            total -= size
        except OSError:
            pass                                 # removed meanwhile


def darken(tile):
    """The night map: the colours inverted, the hues turned back (so water stays blue-ish and roads warm), dimmed."""
    inv = ImageOps.invert(tile.convert("RGB"))
    h, s, v = inv.convert("HSV").split()
    h = h.point(lambda x: (x + 128) % 256)
    return ImageEnhance.Brightness(Image.merge("HSV", (h, s, v)).convert("RGB")).enhance(0.85)


def tint(tile, color):
    """EOX's roads layer, white roads with a grey edge, in a colour for the light map: each pixel keeps its share of
    light, so the edge stays darker than the road (0.26.1)."""
    a = tile.getchannel("A")
    lum = tile.convert("L")
    bands = [lum.point(lambda v, c=c: int(c * (0.55 + 0.45 * v / 255))) for c in color]
    return Image.merge("RGBA", bands + [a])


PLANE = [(0, -1.0), (0.09, -0.86), (0.10, -0.28), (0.96, 0.14), (0.96, 0.28), (0.10, 0.10), (0.08, 0.60),
         (0.38, 0.82), (0.38, 0.94), (0.0, 0.86), (-0.38, 0.94), (-0.38, 0.82), (-0.08, 0.60), (-0.10, 0.10),
         (-0.96, 0.28), (-0.96, 0.14), (-0.10, -0.28), (-0.09, -0.86)]   # a generic airliner from above, nose up


def _icon(d, x, y, track, size, color, heli=False):
    a = math.radians(track or 0)
    ca, sa = math.cos(a), math.sin(a)

    def at(px, py):
        return (x + (px * ca - py * sa) * size, y + (px * sa + py * ca) * size)
    if heli:
        r = size * 0.95
        d.ellipse([x - r, y - r, x + r, y + r], outline=(0, 0, 0, 255), width=max(2, int(size * 0.18)))
        d.ellipse([x - r, y - r, x + r, y + r], outline=color + (255,), width=max(1, int(size * 0.09)))
        body = [at(-0.25, -0.45), at(0.25, -0.45), at(0.25, 0.25), at(0.08, 0.95), at(-0.08, 0.95), at(-0.25, 0.25)]
        d.polygon(body, fill=color + (255,), outline=(0, 0, 0, 255))
        return
    pts = [at(px, py) for px, py in PLANE]
    halo = [at(px * 1.12, py * 1.12) for px, py in PLANE]
    d.polygon(halo, fill=(0, 0, 0, 255))
    d.polygon(pts, fill=color + (255,))


def _nice_scale(m_per_px, units, max_px=150):
    unit_m, label = (1609.344, "MI") if units == "imperial" else (1000.0, "KM")
    best = None
    for v in (0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500):
        px = v * unit_m / m_per_px
        if px <= max_px:
            best = (v, px)
    v, px = best or (0.1, 0.1 * unit_m / m_per_px)
    return ("%g %s" % (v, label)), px


def _wrap(d, text, fnt, width):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=fnt) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


_places = []


def places():
    """[(name, lat, lon, population)]: the GeoNames places of 5 000 or more, read once (tools/make_places.py)."""
    if not _places:
        try:
            with gzip.open(PLACES_FILE, "rt", encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("#"):
                        continue
                    n, la, lo, pop = line.rstrip("\n").split("\t")
                    _places.append((n, float(la), float(lo), int(pop)))
        except (OSError, ValueError):
            pass                                 # no list: the map without names, as before
    return _places


def _small_places(lat0, lat1, lon0, lon1):
    """[(name, lat, lon, population)] of the villages of 1 000 to 4 999 inside the box, read from the file each time
    (it is only read for a map that is short of names, so it is not kept in memory)."""
    out = []
    try:
        with gzip.open(SMALL_PLACES_FILE, "rt", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("#"):
                    continue
                n, la, lo, pop = line.rstrip("\n").split("\t")
                la, lo = float(la), float(lo)
                if lat0 <= la <= lat1 and lon0 <= lo <= lon1:
                    out.append((n, la, lo, int(pop)))
    except (OSError, ValueError):
        pass                                     # no file: the map keeps the towns it had
    return out


def _local_places(lat0, lat1, lon0, lon1):
    """[(name, lat, lon, weight)] of the region's list inside the box, or None when there is no such list or the box
    is not inside the area it covers (a farthest aircraft beyond it): the shipped lists are used then."""
    if not LOCAL_PLACES_FILE:
        return None
    out = []
    try:
        with gzip.open(LOCAL_PLACES_FILE, "rt", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("# centre "):
                    clat, clon, reach = (float(v) for v in line.split()[2:5])
                    for la, lo in ((lat0, lon0), (lat0, lon1), (lat1, lon0), (lat1, lon1)):
                        if _km(clat, clon, la, lo) > reach:
                            return None
                    continue
                if line.startswith("#"):
                    continue
                n, la, lo, wt = line.rstrip("\n").split("\t")
                la, lo = float(la), float(lo)
                if lat0 <= la <= lat1 and lon0 <= lo <= lon1:
                    out.append((n, la, lo, int(wt)))
    except (OSError, ValueError):
        return None                              # unreadable: the shipped lists, as before
    return out


def _km(la1, lo1, la2, lo2):
    la1, lo1, la2, lo2 = map(math.radians, (la1, lo1, la2, lo2))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0088 * math.asin(min(1.0, math.sqrt(h)))


def _lat_of(py, z):
    """The latitude of a row of pixels of the world at zoom z (the inverse of world_px)."""
    n = 256.0 * (2 ** z)
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * py / n))))


def _draw_names(img, z, ox, oy, w, h, band, tone, plane_at=None):
    """The towns inside the map, the largest first, each with a dot and its name on a halo; never over another name,
    the north box or the legend and credit band. A map with fewer than MIN_NAMES of them takes villages too (0.26.2).
    With the region's own list (0.27.0), the same, by weight: towns, then villages, then any populated place. Then
    the empty parts: a village where no name is within GAP_PX (0.27.3)."""
    d = ImageDraw.Draw(img)
    fnt = font(13)                                # 0.25.2, from the owner: smaller names, more of them (16 before)
    fill, halo = ((255, 255, 255), (0, 0, 0)) if tone == "light" else ((30, 30, 30), (255, 255, 255))
    taken = [(w - 52, 0, w, 70), (0, h - band, w, h)]
    if plane_at:                                  # the aircraft itself stays clear
        taken.append((plane_at[0] - 30, plane_at[1] - 30, plane_at[0] + 30, plane_at[1] + 30))
    fixed = list(taken)                           # north, the legend band, the aircraft: no dot under them either
    deg = 360.0 * w / (256.0 * 2 ** z) + 0.5      # a cheap box around the view before the projection
    lon0 = ox * 360.0 / (256.0 * 2 ** z) - 180.0
    shown = [0]
    done = set()                                  # a place named once, whatever tier offers it again

    dots = []

    def name_all(found, gap=0):
        for name, la, lo, pop in sorted(found, key=lambda p: -p[3]):
            if shown[0] >= MAX_NAMES:
                return
            if (name, la, lo) in done:
                continue
            x, y = world_px(la, lo, z)
            x, y = x - ox, y - oy
            if not (6 <= x <= w - 6 and 6 <= y <= h - 6):
                continue
            if gap and any((x - a) ** 2 + (y - b) ** 2 < gap * gap for a, b in dots):
                continue
            tw = d.textlength(name, font=fnt)
            # right of the dot, or left of it when the right is taken or off the map (0.27.0: Waingapu, under the
            # aircraft's clear square on a test over Sumba, had room on its left)
            for tx in (x + 7, x - 7 - tw):
                box = (tx - 3, y - 9, tx + tw + 3, y + 9)
                if box[0] >= 2 and box[2] <= w - 2 and \
                        not any(not (box[2] < t[0] or box[0] > t[2] or box[3] < t[1] or box[1] > t[3]) for t in taken):
                    break
            else:
                continue
            if any(not (x + 3 < t[0] or x - 3 > t[2] or y + 3 < t[1] or y - 3 > t[3]) for t in fixed):
                continue                          # the dot itself under the aircraft, north or the legend
            taken.append(box)
            done.add((name, la, lo))
            dots.append((x, y))
            d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=fill, outline=halo, width=1)
            d.text((tx, y), name, font=fnt, fill=fill, anchor="lm", stroke_width=2, stroke_fill=halo)
            shown[0] += 1

    lat0, lat1 = _lat_of(oy + h, z), _lat_of(oy, z)
    lon1 = lon0 + 360.0 * w / (256.0 * 2 ** z)
    local = _local_places(lat0, lat1, lon0, lon1)
    if local is not None:                         # 0.27.0: the region's list, the heaviest first, down the tiers
        for tier in TIERS:
            name_all([p for p in local if p[3] >= tier])
            if shown[0] >= MIN_NAMES:
                break
        name_all(local, GAP_PX)
        return shown[0]
    name_all([p for p in places() if lon0 - 0.5 <= p[2] <= lon0 + deg])
    small = _small_places(lat0, lat1, lon0, lon1)
    if shown[0] < MIN_NAMES:
        name_all(small)
    name_all(small, GAP_PX)
    return shown[0]


def draw_map(trace, plane, color, units="metric", mode="normal", cache_dir=None, fetch=None, user_agent="ZenithBoard",
             w=MAP_W, h=MAP_H):
    """The map with the track, the aircraft, the legend, north and the credit. Returns (image, shown_mode)."""
    style = MAP_STYLES.get(mode) or MAP_STYLES["normal"]
    color = rgb(color)
    f = font(20)
    fs = font(15, bold=False)
    # The legend and the credit take a band at the foot of the map. When the aircraft would land under the legend,
    # the track is centred in the area above that band instead: a north-south track on the narrow dotmap map put it
    # there (0.23.0). Only then, so that the wide split-flap map keeps its zoom for the tracks that were clear.
    planned = _wrap(ImageDraw.Draw(Image.new("RGB", (1, 1))), style["credit_full"], fs, w - 24) \
        if style["credit_full"] else []
    band = 19 * len(planned) + (10 if planned else 0) + 12 + 74 + 12
    z, ox, oy = choose_view(trace, w, h)
    if trace:
        ax, ay = world_px(trace[-1][0], trace[-1][1], z)
        if ay - oy + 30 > h - band and ax - ox - 30 < 12 + LEGEND_W:
            z, ox, oy = choose_view(trace, w, h - band)
    img = Image.new("RGB", (w, h), (16, 16, 16))
    n = 2 ** z
    tiles = [(tx, ty) for ty in range(oy // 256, (oy + h - 1) // 256 + 1) for tx in range(ox // 256, (ox + w - 1) // 256 + 1)
             if 0 <= ty < n]
    fetch = fetch or (lambda layer, ext, zz, x, y: fetch_tile(layer, ext, zz, x, y, cache_dir, user_agent))
    got_base = 0
    deadline = time.time() + FETCH_BUDGET_S
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
    try:
        for i, (layer, ext) in enumerate(style["layers"]):
            futs = {pool.submit(fetch, layer, ext, z, tx % n, ty): (tx, ty) for tx, ty in tiles}
            for fut, (tx, ty) in futs.items():
                try:
                    data = fut.result(timeout=max(0.1, deadline - time.time()))
                except Exception:
                    data = None
                if not data:
                    continue
                try:
                    tile = Image.open(io.BytesIO(data))
                    tile.load()
                except Exception:
                    continue
                at = (tx * 256 - ox, ty * 256 - oy)
                if ext == "png":
                    tile = tile.convert("RGBA")
                    if style.get("roads"):
                        tile = tint(tile, style["roads"])
                    img.paste(tile, at, tile)
                else:
                    tile = darken(tile) if style.get("night") else tile.convert("RGB")
                    img.paste(tile, at)
                if i == 0:
                    got_base += 1
    finally:
        pool.shutdown(wait=False, cancel_futures=True)   # a tile still on its way is not waited for
    shown = mode if got_base else "none"            # any of the map shown is credited; none of it, a plain black
    if not got_base:
        img = Image.new("RGB", (w, h), (16, 16, 16))

    S = 3                                             # drawn three times larger, then reduced: smooth lines
    ov = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    if shown == "none":                               # no map: a faint grid, so the track still has a scale
        for gx in range(0, w * S, 60 * S):
            d.line([(gx, 0), (gx, h * S)], fill=(255, 255, 255, 22), width=S)
        for gy in range(0, h * S, 60 * S):
            d.line([(0, gy), (w * S, gy)], fill=(255, 255, 255, 22), width=S)
    pts = []
    for p in trace:
        x, y = world_px(p[0], p[1], z)
        pts.append(((x - ox) * S, (y - oy) * S))
    if len(pts) >= 2:
        # a dark edge: the track reads on any map, roads of the same colour included. 0.24.1: 6 and 3 pixels, from
        # 11 and 5, which the owner found far too thick on the real posts
        d.line(pts, fill=(0, 0, 0, 220), width=6 * S, joint="curve")
        d.line(pts, fill=color + (255,), width=3 * S, joint="curve")
    if pts:
        _icon(d, pts[-1][0], pts[-1][1], plane.get("track"), 22 * S, color, heli=plane.get("shape") == "heli")
    ov = ov.resize((w, h), LANCZOS)
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    # 0.25.3: the names over the track, not under it: the track cut letters out of the towns it crossed ("N ncy" on
    # the real posts). Each town's dot stays where the town is; the aircraft keeps its clear square.
    if shown != "none" and style.get("names"):
        at = world_px(trace[-1][0], trace[-1][1], z) if trace else None
        _draw_names(img, z, ox, oy, w, h, band, style["names"], (at[0] - ox, at[1] - oy) if at else None)

    # legend, north, credit: drawn at their size, on see-through dark boxes so they read on any map
    d = ImageDraw.Draw(img, "RGBA")
    credit = style["credit_full"] if shown != "none" else None
    clines = _wrap(d, credit, fs, w - 24) if credit else []
    ch = 19 * len(clines) + (10 if clines else 0)
    if clines:
        d.rectangle([0, h - ch, w, h], fill=(0, 0, 0, 175))
        for i, line in enumerate(clines):
            d.text((w - 10, h - ch + 5 + i * 19), line, font=fs, fill=(235, 235, 235, 255), anchor="ra")
    minutes = max(1, int(round((trace[-1][3] - trace[0][3]) / 60.0))) if len(trace) > 1 else 0
    lat = trace[-1][0] if trace else 0.0
    m_per_px = 156543.03392 * math.cos(math.radians(lat)) / n
    label, bar = _nice_scale(m_per_px, units)
    lw = int(max(bar, 44) + 16 + d.textlength(max(label, "LAST %d MIN" % minutes, key=len), font=f) + 24)
    lx, ly = 12, h - ch - 12 - 74
    d.rounded_rectangle([lx, ly, lx + lw, ly + 74], radius=8, fill=(0, 0, 0, 185))
    tx = lx + 12 + int(max(bar, 44)) + 14
    if minutes:
        d.line([(lx + 12, ly + 22), (lx + 12 + 44, ly + 22)], fill=color + (255,), width=3)
        d.text((tx, ly + 22), "LAST %d MIN" % minutes, font=f, fill=(255, 255, 255, 255), anchor="lm")
    by = ly + 52
    d.line([(lx + 12, by), (lx + 12 + bar, by)], fill=(255, 255, 255, 255), width=3)
    d.line([(lx + 12, by - 7), (lx + 12, by + 7)], fill=(255, 255, 255, 255), width=3)
    d.line([(lx + 12 + bar, by - 7), (lx + 12 + bar, by + 7)], fill=(255, 255, 255, 255), width=3)
    d.text((tx, by), label, font=f, fill=(255, 255, 255, 255), anchor="lm")
    nx, ny = w - 46, 12                               # north up, said in a corner
    d.rounded_rectangle([nx, ny, nx + 34, ny + 52], radius=8, fill=(0, 0, 0, 185))
    d.polygon([(nx + 17, ny + 6), (nx + 26, ny + 22), (nx + 8, ny + 22)], fill=(255, 255, 255, 255))
    d.text((nx + 17, ny + 37), "N", font=f, fill=(255, 255, 255, 255), anchor="mm")
    d.rectangle([0, 0, w - 1, h - 1], outline=color + (255,), width=2)
    return img, shown


# --------------------------------------------------------------------------- the picture
def save_jpeg(img, out, limit=950000):
    """As a JPEG under Bluesky's 1,000,000 bytes: the quality goes down a step at a time if it has to."""
    buf = io.BytesIO()
    for q in (90, 84, 78, 72, 66, 60):
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, subsampling=0 if q >= 84 else 2, optimize=True)
        if buf.tell() <= limit:
            break
    with open(out, "wb") as fh:
        fh.write(buf.getvalue())
    return buf.tell()


def render(lines, trace, plane, out, color="#ffb000", units="metric", map_mode="normal", cache_dir=None, fetch=None,
           user_agent=None):
    """The whole picture, written to `out` as a JPEG. Returns {width, height, bytes, map, credit, links,
    credit_full, map_words}: what the post and the alt text say about the map actually shown."""
    user_agent = _user_agent(user_agent)
    prune_cache(cache_dir)
    img = Image.new("RGB", (W, H), (0, 0, 0))
    img.paste(draw_board(lines, color), (M, BOARD_Y))
    mp, shown = draw_map(trace, plane, color, units, map_mode, cache_dir, fetch, user_agent)
    img.paste(mp, (MAP_X, M))
    size = save_jpeg(img, out)
    return _info(W, H, size, shown)


def _info(w, h, size, shown):
    """What the post and the alt text say about the map actually shown: none of it shown, nothing credited."""
    st = MAP_STYLES.get(shown) or MAP_STYLES["none"]
    return {"width": w, "height": h, "bytes": size, "map": shown, "credit": st["credit"], "links": list(st["links"]),
            "credit_full": st["credit_full"], "map_words": st["words"] or "a plain dark background"}


def _user_agent(user_agent):
    if user_agent is not None:
        return user_agent
    try:
        import server
        return server.USER_AGENT
    except Exception:
        return "ZenithBoard (+https://github.com/regis57/ZenithBoard)"


def render_dotmap(dots_png, box, trace, plane, out, color="#ffb000", units="metric", map_mode="normal", cache_dir=None,
                  fetch=None, user_agent=None):
    """The dot-matrix picture with a map in its right-hand column (0.23.0). dots_png is what tools/social-render.js
    drew with "map": true, box its [x, y, w, h] for the map, in pixels. Written to `out` as a JPEG (a map in a PNG
    would pass Bluesky's 1,000,000 bytes). Returns what render() returns."""
    user_agent = _user_agent(user_agent)
    prune_cache(cache_dir)
    img = Image.open(dots_png).convert("RGB")
    x, y, w, h = (int(v) for v in box)
    mp, shown = draw_map(trace, plane, color, units, map_mode, cache_dir, fetch, user_agent, w=w, h=h)
    img.paste(mp, (x, y))
    size = save_jpeg(img, out)
    return _info(img.width, img.height, size, shown)
