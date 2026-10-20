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


def has_second(w):
    """The second post (0.35.0): something to say about cargo airlines or business jets, over the whole week."""
    return bool(w and w.get("covered") and (w.get("cargo") or w.get("bizjets")))


def text_second(w, area, tags, fit):
    """Cargo airlines and business jets: the head always, the lists while they fit."""
    head = "Cargo and business jets%s, %s: %s cargo aircraft, %s business jet%s." % (
        (" " + area) if area else "", span_words(w["dates"]), number(w.get("cargo_total", 0)),
        number(w.get("bizjet_total", 0)), "" if w.get("bizjet_total") == 1 else "s")
    return _fit_lines(head, [("Cargo", w.get("cargo") or []), ("Business jets", w.get("bizjets") or [])], tags, fit)


def alt_second(w, area):
    s = "Weekly card of the cargo airlines and business jets, %s%s: %s cargo aircraft and %s business jets." % (
        span_words(w["dates"]), (" " + area) if area else "", number(w.get("cargo_total", 0)), number(w.get("bizjet_total", 0)))
    if w.get("cargo"):
        s += " Cargo airlines, as bars: " + ", ".join("%s %d" % (n, k) for n, k in w["cargo"]) + "."
    if w.get("bizjets"):
        s += " Business jets by make and model, as bars: " + ", ".join("%s %d" % (n, k) for n, k in w["bizjets"]) + "."
    return s


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


def draw_second(w, theme, area, out):
    """The second card (0.35.0): the cargo airlines and the business jets of the week, two lists with their totals."""
    img, d, col, dim, f = _canvas(theme)
    _header(d, f, col, dim, ("CARGO AND BUSINESS JETS " + area) if area else "CARGO AND BUSINESS JETS", w["dates"])
    for x, total, label, title, pairs in ((M, w.get("cargo_total", 0), "CARGO AIRCRAFT", "CARGO AIRLINES", w.get("cargo") or []),
                                          (620, w.get("bizjet_total", 0), "BUSINESS JETS", "MAKE AND MODEL", w.get("bizjets") or [])):
        d.text((x, 108), number(total), font=f["big"], fill=col)
        d.text((x + 2, 176), label, font=f["lbl"], fill=GREY)
        if pairs:
            _ranks(d, f, col, x, 240, 532, title, pairs, step=64, fnt="row")
        else:
            d.text((x, 236), title, font=f["lbl"], fill=GREY)
            d.text((x, 268), "None heard this week.", font=f["name"], fill=FAINT)
    img.save(out, "PNG", optimize=True)
    return {"path": out, "width": W, "height": H, "bytes": os.path.getsize(out), "mime": "image/png"}
