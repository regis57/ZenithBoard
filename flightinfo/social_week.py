# SPDX-License-Identifier: GPL-3.0-or-later
"""The week's summary post (0.33.0, off by default): `sudo zenithboard social weekly on`.

On Sunday from 19:00, the social service posts what the statistics counted over the seven days ending that day:
how many aircraft were heard, how many messages decoded, the busiest day and hour, the airlines and the type most
seen, and how many crossings the account posted. A picture drawn by the Pi goes with it: the week by hour, as on
the statistics page, and the airlines as bars.

What it never says: a distance, a direction, a range. The farthest aircraft of the week is left out on purpose:
with the city nearest it, two such posts would narrow down where the antenna is. Only the owner's own words for the
place (SOCIAL_AREA) say where.

It reads the files the statistics timer writes (lib/stats.sh): no statistics, no weekly post, and the service says
so in its journal once that week.
"""
import datetime
import os

import server

WEEK_DAY, WEEK_HOUR = 6, 19                  # Sunday (Monday is 0), from 19:00 on the Pi's clock
NBSP = " "
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
POST_MAX = 300                               # Bluesky's limit, as social.POST_MAX
TOP = 5                                      # airlines on the picture; three in the words
W, H = 1200, 675                             # 16:9, as Bluesky shows a single picture whole
THEME_HEX = {"amber": "#ffb000", "green": "#39ff6a", "red": "#ff3b30", "white": "#e8e8e8", "turquoise": "#00d6d7"}


# --------------------------------------------------------------------------- when
def week_key(now):
    """The ISO week of a time: one weekly post per key."""
    y, w, _ = datetime.date.fromtimestamp(now).isocalendar()
    return "%d-W%02d" % (y, w)


def due(c, state, now):
    """On, Sunday from 19:00, and not yet done this week. A Pi switched off on Sunday evening posts nothing on
    Monday: a summary of last week a day late is not what the account promises."""
    if not server.cfg_bool(c, "SOCIAL_WEEKLY", "0"):
        return False
    lt = datetime.datetime.fromtimestamp(now)
    return lt.weekday() == WEEK_DAY and lt.hour >= WEEK_HOUR and state.get("weekly") != week_key(now)


# --------------------------------------------------------------------------- what
def _lines(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return set(x.strip() for x in fh if x.strip())
    except OSError:
        return set()


def week_data(c, stats_dir=None, now=None, posts=None):
    """The seven days ending on now's day, from the statistics files; None when there are none.
    posts: {YYYY-MM-DD: number of posts} from the service's state."""
    stats_dir = stats_dir or server.STATS_DIR
    now_dt = datetime.datetime.fromtimestamp(now) if isinstance(now, (int, float)) else (now or datetime.datetime.now())
    st = server.read_stats(stats_dir, now_dt)
    if not st:
        return None
    dates = [(now_dt.date() - datetime.timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    by_day = {d["day"]: d for d in st.get("days") or []}
    heat = {r["day"]: r["hours"] for r in st.get("heat") or []}
    seen, per_day = set(), []
    for d in dates:
        s = _lines(os.path.join(stats_dir, "seen-" + d))
        seen |= s
        per_day.append((d, len(s) or (by_day.get(d) or {}).get("aircraft", 0)))
    messages = sum((by_day.get(d) or {}).get("messages", 0) for d in dates)
    if not seen and not messages:
        return None
    best_day = max(per_day, key=lambda x: (x[1], x[0]))
    rows = [heat.get(d) or [None] * 24 for d in dates]
    hours = []
    for h in range(24):
        v = [r[h] for r in rows if r[h] is not None]
        hours.append(sum(v) / len(v) if v else None)
    known = [(v, h) for h, v in enumerate(hours) if v is not None]
    busiest_hour = max(known)[1] if known else None
    # 0.34.1: the airlines and types only when their lists cover the whole week. On the reference Pi the first test,
    # the evening the lists began (0.31.0), said "6 435 aircraft heard" and "Ryanair (14)": a week against two hours
    fleet_from = fleet_start(stats_dir)
    covered = bool(fleet_from and fleet_from < dates[0])
    fleet = server.read_fleet(c, stats_dir, now_dt, since=dates[0]) if covered else {}
    posted = sum(int((posts or {}).get(d, 0)) for d in dates)
    return {"dates": dates, "aircraft": len(seen) or max(n for _, n in per_day), "messages": messages,
            "per_day": per_day, "best_day": best_day if best_day[1] else None, "busiest_hour": busiest_hour,
            "heat": rows, "airlines": (fleet.get("airlines") or [])[:TOP], "models": (fleet.get("types") or [])[:TOP],
            "cargo": (fleet.get("cargo") or [])[:TOP], "cargo_total": fleet.get("cargo_total", 0),
            "bizjets": (fleet.get("bizjets") or [])[:TOP], "bizjet_total": fleet.get("bizjet_total", 0),
            "cargo_models": fleet.get("cargo_models") or {}, "bizjet_countries": [(cc, k) for cc, k in fleet.get("bizjet_countries") or [] if cc][:TOP],
            "military": fleet.get("military") or [], "military_total": fleet.get("military_total", 0),
            "misc": fleet.get("misc") or {},
            "covered": covered, "posted": posted, "fleet_from": fleet_from, "fleet_week": first_full_week(fleet_from)}


def fleet_start(stats_dir):
    """The first day of the airline and type lists (fleet-DAY files, 0.31.0), or None."""
    try:
        days = sorted(n[6:] for n in os.listdir(stats_dir) if n.startswith("fleet-"))
    except OSError:
        return None
    return days[0] if days else None


def first_full_week(fleet_from):
    """The Sunday of the first week whose seven days the lists cover entirely: its first day after fleet_from."""
    if not fleet_from:
        return None
    # the week's first day must come after fleet_from (that day is counted from the update on, not whole): a Sunday
    # at least seven days after it
    d = datetime.date.fromisoformat(fleet_from) + datetime.timedelta(days=7)
    return (d + datetime.timedelta(days=(6 - d.weekday()) % 7)).isoformat()


# --------------------------------------------------------------------------- words
def number(n):
    """3 412, with a space that does not break, as the posts write altitudes."""
    return "{:,}".format(int(n)).replace(",", NBSP)


def messages_words(n):
    if n >= 1e6:
        return "%s million" % ("%.1f" % (n / 1e6)).rstrip("0").rstrip(".")
    return number(n)


def span_words(dates):
    a, b = (datetime.date.fromisoformat(x) for x in (dates[0], dates[-1]))
    if a.month == b.month:
        return "%d–%d %s" % (a.day, b.day, MONTHS[b.month - 1])
    return "%d %s – %d %s" % (a.day, MONTHS[a.month - 1], b.day, MONTHS[b.month - 1])


def short_date(d):
    d = datetime.date.fromisoformat(d)
    return "%d %s" % (d.day, MONTHS[d.month - 1])


def day_name(d):
    return DAYS[datetime.date.fromisoformat(d).weekday()]


def _ranked(label, pairs, n):
    return "%s: %s." % (label, ", ".join("%s (%s)" % (name, number(k)) for name, k in pairs[:n])) if pairs else None


def _fit_lines(head, parts, tags, fit):
    """head, then the parts: a part is a line, or (label, pairs) drawn as a ranked list. The lists go down from three
    names to one before any line is dropped, and lines are dropped from the end, so the hashtags stay whole."""
    def lines(n):
        return [x for x in ((p if isinstance(p, str) else _ranked(p[0], p[1], n)) for p in parts) if x]

    def size(ls):
        return len("\n".join([head] + ls + ([tags] if tags else [])))
    for n in (3, 2, 1):
        if size(lines(n)) <= POST_MAX:
            return fit("\n".join([head] + lines(n)), None, tags)
    ls = lines(1)
    while ls and size(ls) > POST_MAX:
        ls.pop()
    return fit("\n".join([head] + ls), None, tags)


def text(w, c, area, tags, fit):
    """The post: the head always; the busiest times, the airlines, the models and the posts while they fit beside the
    hashtags. No distance, ever."""
    head = "The week%s, %s: %s aircraft, %s messages." % (
        (" " + area) if area else "", span_words(w["dates"]), number(w["aircraft"]), messages_words(w["messages"]))
    parts = []
    bd, bh = w.get("best_day"), w.get("busiest_hour")
    if bd and bh is not None:
        parts.append("Busiest: %s (%s aircraft) and %02d:00." % (day_name(bd[0]), number(bd[1]), bh))
    elif bd:
        parts.append("Busiest: %s (%s aircraft)." % (day_name(bd[0]), number(bd[1])))
    parts.append(("Airlines", w.get("airlines") or []))
    parts.append(("Models", w.get("models") or []))          # 0.35.0
    if w.get("posted"):
        parts.append("Posted here: %s crossing%s." % (number(w["posted"]), "" if w["posted"] == 1 else "s"))
    return _fit_lines(head, parts, tags, fit)


def alt(w, area):
    bits = ["Weekly summary card for %s%s" % (span_words(w["dates"]), (" " + area) if area else ""),
            "%s aircraft heard and %s messages decoded" % (number(w["aircraft"]), messages_words(w["messages"]))]
    if w.get("best_day"):
        bits.append("busiest day %s with %s aircraft" % (day_name(w["best_day"][0]), number(w["best_day"][1])))
    if w.get("busiest_hour") is not None:
        bits.append("busiest hour %02d:00" % w["busiest_hour"])
    s = ", ".join(bits) + ". A grid of the seven days by hour, brighter where more aircraft were overhead."
    if w.get("airlines"):
        s += " The airlines most seen, as bars: " + ", ".join("%s %d" % (n, k) for n, k in w["airlines"]) + "."
    if w.get("models"):
        s += " Beside them, the models most seen: " + ", ".join("%s %d" % (n, k) for n, k in w["models"]) + "."
    return s


PARTS = (1, 2, 3, 4)          # 0.36.0: the week; cargo and business jets; military; helicopters, light aircraft, gliders
MISC_SHOWN = (("heli", "Helicopters", "HELICOPTERS"), ("light", "Light aircraft", "LIGHT AIRCRAFT"),
              ("glider", "Gliders", "GLIDERS"), ("other", "Drones and balloons", "DRONES AND BALLOONS"))


def misc_lists(w):
    """{group: {"total", "models"}} with the drones and the balloons together, as the picture shows them."""
    m = dict(w.get("misc") or {})
    other = {}
    for g in ("drone", "balloon"):
        for name, k in (m.get(g) or {}).get("models") or []:
            other[name] = other.get(name, 0) + k
    m["other"] = {"total": sum(other.values()), "models": sorted(other.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP]}
    return m


def has_part(w, part):
    """Something to say in that post, over the whole week. The first always has (when there are statistics)."""
    if part == 1:
        return bool(w)
    if not (w and w.get("covered")):
        return False
    if part == 2:
        return bool(w.get("cargo") or w.get("bizjets"))
    if part == 3:
        return bool(w.get("military_total"))
    return any(v.get("total") for v in misc_lists(w).values())


def has_second(w):
    return has_part(w, 2)


def _plural(n, one, many=None):
    return "%s %s" % (number(n), one if n == 1 else (many or one + "s"))


def text_second(w, area, tags, fit):
    """Cargo airlines and business jets: the head always, the lists while they fit."""
    head = "Cargo and business jets%s, %s: %s cargo aircraft, %s." % (
        (" " + area) if area else "", span_words(w["dates"]), number(w.get("cargo_total", 0)),
        _plural(w.get("bizjet_total", 0), "business jet"))
    return _fit_lines(head, [("Cargo", w.get("cargo") or []), ("Business jets", w.get("bizjets") or [])], tags, fit)


def text_military(w, area, tags, fit):
    """Military aircraft: by country, the most represented first, each with its models."""
    mil = w.get("military") or []
    head = "Military aircraft%s, %s: %s from %s." % ((" " + area) if area else "", span_words(w["dates"]),
                                                    _plural(w.get("military_total", 0), "aircraft", "aircraft"),
                                                    _plural(len(mil), "country", "countries"))
    return _fit_lines(head, [(e["country"], e["models"]) for e in mil], tags, fit)


def text_misc(w, area, tags, fit):
    m = misc_lists(w)
    counts = [_plural(m[g]["total"], one.lower().rstrip("s") if g != "other" else "drone or balloon",
                      one.lower() if g != "other" else "drones and balloons")
              for g, one, _ in MISC_SHOWN if (m.get(g) or {}).get("total")]
    head = "General aviation%s, %s: %s." % ((" " + area) if area else "", span_words(w["dates"]),
                                                                  ", ".join(counts))
    return _fit_lines(head, [(one, m[g]["models"]) for g, one, _ in MISC_SHOWN if (m.get(g) or {}).get("total")], tags, fit)


def alt_second(w, area):
    s = "Weekly card of the cargo airlines and business jets, %s%s: %s cargo aircraft and %s business jets." % (
        span_words(w["dates"]), (" " + area) if area else "", number(w.get("cargo_total", 0)), number(w.get("bizjet_total", 0)))
    if w.get("cargo"):
        cm = w.get("cargo_models") or {}
        s += " Cargo airlines, as bars, each with the model it flew most: " + ", ".join(
            "%s %d%s" % (n, k, (" (mostly %s, %d)" % tuple(cm[n])) if n in cm else "") for n, k in w["cargo"]) + "."
    if w.get("bizjets"):
        s += " Business jets by make and model, as bars: " + ", ".join("%s %d" % (n, k) for n, k in w["bizjets"]) + "."
    if w.get("bizjet_countries"):
        s += " The countries they are registered in, with their flags: " + ", ".join(
            "%s %d" % (server.country_name(c), k) for c, k in w["bizjet_countries"]) + "."
    return s


def alt_military(w, area):
    return "Weekly card of the military aircraft, %s%s: %s. By country, with its flag, the most represented first: %s." % (
        span_words(w["dates"]), (" " + area) if area else "", _plural(w.get("military_total", 0), "aircraft", "aircraft"),
        "; ".join("%s %d (%s)" % (e["country"], e["total"], ", ".join("%s %d" % (n, k) for n, k in e["models"][:3]))
                  for e in w.get("military") or []))


def alt_misc(w, area):
    m = misc_lists(w)
    groups = ["%s: %d (%s)." % (one, m[g]["total"], ", ".join("%s %d" % (n, k) for n, k in m[g]["models"]))
              for g, one, _ in MISC_SHOWN if (m.get(g) or {}).get("total")]
    return "Weekly card of the helicopters, light aircraft, gliders, drones and balloons, %s%s. %s" % (
        span_words(w["dates"]), (" " + area) if area else "", " ".join(groups))


def flag_pixels(codes, node=None):
    """{ISO code: [[x, y, rgb], ...]} from the wall's own flags (flags.js, through tools/flag-pixels.js); {} when
    Node cannot be run. A country without a drawing has no entry."""
    import json
    import subprocess
    codes = sorted({c for c in codes if c})
    if not codes:
        return {}
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools", "flag-pixels.js")
    try:
        out = subprocess.run([node or os.environ.get("ZENITHBOARD_NODE", "node"), script] + codes,
                             capture_output=True, timeout=20, check=True).stdout
        return json.loads(out.decode("utf-8") or "{}")
    except (OSError, ValueError, subprocess.SubprocessError):
        return {}


# --------------------------------------------------------------------------- the pictures
def _canvas(theme):
    from PIL import Image, ImageDraw
    import social_card as card
    col = card.rgb(THEME_HEX.get(theme, "#ffb000"))
    img = Image.new("RGB", (W, H), (0, 0, 0))
    fonts = {"head": card.font(30), "big": card.font(58), "lbl": card.font(18), "small": card.font(16, bold=False),
             "name": card.font(19, bold=False), "row": card.font(24, bold=False)}
    return img, ImageDraw.Draw(img), col, tuple(int(v * 0.55) for v in col), fonts


GREY, FAINT, OFF, INK = (150, 150, 150), (90, 90, 90), (28, 28, 28), (225, 225, 225)
M = 48


def _header(d, f, col, dim, title, dates):
    span = span_words(dates).upper()
    room = W - 2 * M - d.textlength(span, font=f["head"]) - 30       # a long place name never runs into the dates
    d.text((M, 34), _fit(d, title.upper(), f["head"], room), font=f["head"], fill=col)
    d.text((W - M, 34), span, font=f["head"], fill=dim, anchor="ra")
    d.line([(M, 86), (W - M, 86)], fill=OFF, width=2)
    d.text((W - M, H - 34), "ZENITHBOARD", font=f["lbl"], fill=FAINT, anchor="ra")


def _fit(d, text, fnt, width):
    """The text, cut with an ellipsis to fit width pixels."""
    if d.textlength(text, font=fnt) <= width:
        return text
    while text and d.textlength(text + "…", font=fnt) > width:
        text = text[:-1]
    return text.rstrip() + "…"


def _ranks(d, f, col, x, y, width, title, pairs, rows=TOP, step=44, fnt="name"):
    """A titled list: each name with its count on the right, a bar under it as long as its share of the first."""
    d.text((x, y), title, font=f["lbl"], fill=GREY)
    y += 32
    best = pairs[0][1] if pairs else 0
    for n, k in pairs[:rows]:
        num = number(k)
        nw = d.textlength(num, font=f[fnt])
        d.text((x, y), _fit(d, n, f[fnt], width - nw - 14), font=f[fnt], fill=INK)
        d.text((x + width, y), num, font=f[fnt], fill=GREY, anchor="ra")
        bar = y + (26 if fnt == "name" else 34)
        d.rounded_rectangle([x, bar, x + max(4, int(width * k / best)), bar + 5], radius=2, fill=col)
        y += step
    return y


def _not_yet(d, f, x, y, w):
    why = ("Counted since %s: shown from the week ending %s." % (short_date(w["fleet_from"]), short_date(w["fleet_week"]))
           if w.get("fleet_from") else "Not counted yet: statistics from ZenithBoard 0.31.0 on.")
    d.text((x, y), why, font=f["name"], fill=FAINT)


def draw(w, theme, area, out):
    """The week's card, as a PNG at `out`: the counts on the left; the week by hour, then the airlines and the
    models most seen side by side, on the right (0.35.0: the grid smaller to make room for the models).
    Needs Pillow (social_card). Returns {path, width, height, bytes, mime}."""
    img, d, col, dim, f = _canvas(theme)
    _header(d, f, col, dim, ("THE WEEK " + area) if area else "THE WEEK", w["dates"])
    rows = [(number(w["aircraft"]), "AIRCRAFT HEARD"),
            ((messages_words(w["messages"]).replace(" million", " M")), "MESSAGES DECODED")]
    if w.get("best_day"):
        rows.append((day_name(w["best_day"][0]).upper(), "BUSIEST DAY \u00b7 %s AIRCRAFT" % number(w["best_day"][1])))
    if w.get("busiest_hour") is not None:
        rows.append(("%02d:00" % w["busiest_hour"], "BUSIEST HOUR"))
    y = 112
    for big, lbl in rows:
        d.text((M, y), big, font=f["big"], fill=col)
        d.text((M + 2, y + 68), lbl, font=f["lbl"], fill=GREY)
        y += 128
    # the week by hour: a dot per hour, brighter where more aircraft had a position
    gx, gy, cw, ch = 520, 108, 26, 22
    vals = [v for r in w["heat"] for v in r if v is not None]
    top = max(vals) if vals else 0
    for i, r in enumerate(w["heat"]):
        d.text((gx - 14, gy + i * ch + ch / 2), day_name(w["dates"][i])[:3].upper(), font=f["small"], fill=GREY, anchor="rm")
        for h, v in enumerate(r):
            cx, cy = gx + h * cw + cw / 2, gy + i * ch + ch / 2
            k = None if v is None or not top else 0.12 + 0.88 * (v / top)
            fill = OFF if k is None else tuple(int(OFF[j] + (col[j] - OFF[j]) * k) for j in range(3))
            d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=fill)
    for h in (0, 6, 12, 18):
        d.text((gx + h * cw + cw / 2, gy + 7 * ch + 6), "%02dh" % h, font=f["small"], fill=FAINT, anchor="ma")
    # the airlines and the models, side by side
    x0, x1, colw, ly = 466, 820, 332, 300
    if w.get("airlines") or w.get("models"):
        _ranks(d, f, col, x0, ly, colw, "AIRLINES MOST SEEN", w.get("airlines") or [])
        _ranks(d, f, col, x1, ly, colw, "MODELS MOST SEEN", w.get("models") or [])
    else:
        d.text((x0, ly), "AIRLINES AND MODELS MOST SEEN", font=f["lbl"], fill=GREY)
        _not_yet(d, f, x0, ly + 32, w)
    img.save(out, "PNG", optimize=True)
    return {"path": out, "width": W, "height": H, "bytes": os.path.getsize(out), "mime": "image/png"}


def _flag(d, px, x, y, pitch=4):
    """A flag of the wall, dot by dot, its top left at x, y; 11 x 7 dots (13 x 9 with a dark flag's outline), 4 pixels a dot."""
    for fx, fy, v in px or []:
        if v:
            cx, cy = x + (fx + 1) * pitch, y + (fy + 1) * pitch
            d.rectangle([cx, cy, cx + pitch - 2, cy + pitch - 2], fill=((v >> 16) & 255, (v >> 8) & 255, v & 255))
    return 13 * pitch


def _flag_or_code(d, f, flags, cc, x, y):
    """The flag when the wall has one, otherwise the two letters in a box: the row keeps its place either way."""
    if cc in flags:
        _flag(d, flags[cc], x, y)
        return
    d.rectangle([x + 4, y + 4, x + 48, y + 32], outline=FAINT, width=1)
    d.text((x + 26, y + 18), cc or "?", font=f["small"], fill=GREY, anchor="mm")


def _total(d, f, col, x, y, n, label):
    d.text((x, y), number(n), font=f["big"], fill=col)
    d.text((x + 2, y + 68), label, font=f["lbl"], fill=GREY)


def draw_second(w, theme, area, out, flags=None):
    """The second card (0.35.0; three columns in 0.36.0): the cargo airlines, each with the model it flew most; the
    business jets by make and model; and the countries the business jets are registered in, with their flags."""
    img, d, col, dim, f = _canvas(theme)
    flags = flags or {}
    _header(d, f, col, dim, ("CARGO AND BUSINESS JETS " + area) if area else "CARGO AND BUSINESS JETS", w["dates"])
    # cargo: the airline, then in grey the model it flew most and how many of them, the airline's count on the right
    x, width = M, 420
    _total(d, f, col, x, 108, w.get("cargo_total", 0), "CARGO AIRCRAFT")
    d.text((x, 236), "CARGO AIRLINES \u00b7 MOST SEEN MODEL", font=f["lbl"], fill=GREY)
    y, cargo, cm = 268, w.get("cargo") or [], w.get("cargo_models") or {}
    best = cargo[0][1] if cargo else 0
    for name, k in cargo[:TOP]:
        num = number(k)
        room = width - d.textlength(num, font=f["name"]) - 14
        d.text((x, y), _fit(d, name, f["name"], room), font=f["name"], fill=INK)
        used = d.textlength(_fit(d, name, f["name"], room), font=f["name"])
        if name in cm and room - used > 60:
            model, mk = cm[name]
            d.text((x + used + 8, y + 2), _fit(d, "%s (%s)" % (model, number(mk)), f["small"], room - used - 8),
                   font=f["small"], fill=GREY)
        d.text((x + width, y), num, font=f["name"], fill=GREY, anchor="ra")
        d.rounded_rectangle([x, y + 26, x + max(4, int(width * k / best)), y + 31], radius=2, fill=col)
        y += 44
    if not cargo:
        d.text((x, 268), "None heard this week.", font=f["name"], fill=FAINT)
    # business jets: make and model
    x, width = 500, 300
    _total(d, f, col, x, 108, w.get("bizjet_total", 0), "BUSINESS JETS")
    if w.get("bizjets"):
        _ranks(d, f, col, x, 236, width, "MAKE AND MODEL", w["bizjets"])
    else:
        d.text((x, 236), "MAKE AND MODEL", font=f["lbl"], fill=GREY)
        d.text((x, 268), "None heard this week.", font=f["name"], fill=FAINT)
    # where they are registered: the flag, the country, a bar and the count
    x, width = 840, W - M - 840
    d.text((x, 236), "REGISTERED IN", font=f["lbl"], fill=GREY)
    y, ctry = 268, w.get("bizjet_countries") or []
    best = ctry[0][1] if ctry else 0
    for cc, k in ctry[:TOP]:
        _flag_or_code(d, f, flags, cc, x - 4, y - 6)
        num = number(k)
        d.text((x + 58, y), _fit(d, server.country_name(cc), f["name"], width - 58 - d.textlength(num, font=f["name"]) - 10),
               font=f["name"], fill=INK)
        d.text((x + width, y), num, font=f["name"], fill=GREY, anchor="ra")
        d.rounded_rectangle([x + 58, y + 26, x + 58 + max(4, int((width - 58) * k / best)), y + 31], radius=2, fill=col)
        y += 44
    img.save(out, "PNG", optimize=True)
    return {"path": out, "width": W, "height": H, "bytes": os.path.getsize(out), "mime": "image/png"}


def draw_military(w, theme, area, out, flags=None):
    """The third card (0.36.0): the military aircraft, a row per country and model, the most represented country
    first, each row with the country's flag, a bar and the count."""
    img, d, col, dim, f = _canvas(theme)
    flags = flags or {}
    _header(d, f, col, dim, ("MILITARY AIRCRAFT " + area) if area else "MILITARY AIRCRAFT", w["dates"])
    mil = w.get("military") or []
    _total(d, f, col, M, 108, w.get("military_total", 0), "MILITARY AIRCRAFT")
    _total(d, f, col, 420, 108, len(mil), "COUNTRIES" if len(mil) != 1 else "COUNTRY")
    rows = [(e["cc"], e["country"], n, k) for e in mil for n, k in e["models"][:2]][:10]   # two models a country, ten rows
    best = max((k for _, _, _, k in rows), default=0)
    x, y, width = M, 236, W - 2 * M
    d.text((x, y), "BY COUNTRY, THEN MAKE AND MODEL", font=f["lbl"], fill=GREY)
    y += 32
    last = None
    for cc, country, model, k in rows:
        if cc != last:                           # the flag and the country once, on the country's first row
            _flag_or_code(d, f, flags, cc, x - 4, y - 6)
            d.text((x + 62, y), _fit(d, country, f["name"], 290), font=f["name"], fill=INK)
            last = cc
        d.text((x + 370, y), _fit(d, model, f["name"], 400), font=f["name"], fill=INK)
        bx0, bx1 = x + 790, x + width - 60
        d.rounded_rectangle([bx0, y + 6, bx0 + max(4, int((bx1 - bx0) * k / best)), y + 20], radius=3, fill=col)
        d.text((x + width, y), number(k), font=f["name"], fill=GREY, anchor="ra")
        y += 34
    img.save(out, "PNG", optimize=True)
    return {"path": out, "width": W, "height": H, "bytes": os.path.getsize(out), "mime": "image/png"}


def draw_misc(w, theme, area, out):
    """The fourth card (0.36.0): helicopters, light aircraft, gliders, drones and balloons, a column each with its
    total and its makes and models."""
    img, d, col, dim, f = _canvas(theme)
    _header(d, f, col, dim, ("GENERAL AVIATION " + area) if area else "GENERAL AVIATION", w["dates"])
    m = misc_lists(w)
    shown = [(g, big) for g, _, big in MISC_SHOWN if (m.get(g) or {}).get("total")] or [(g, big) for g, _, big in MISC_SHOWN[:3]]
    gap = 24
    width = int((W - 2 * M - gap * (len(shown) - 1)) / len(shown))
    for i, (g, big) in enumerate(shown):
        x = M + i * (width + gap)
        e = m.get(g) or {"total": 0, "models": []}
        _total(d, f, col, x, 108, e["total"], big)
        if e["models"]:
            _ranks(d, f, col, x, 236, width, "MAKE AND MODEL", e["models"])
        else:
            d.text((x, 236), "None heard this week.", font=f["name"], fill=FAINT)
    img.save(out, "PNG", optimize=True)
    return {"path": out, "width": W, "height": H, "bytes": os.path.getsize(out), "mime": "image/png"}
