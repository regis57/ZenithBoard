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
    fleet = server.read_fleet(c, stats_dir, now_dt, since=dates[0])
    posted = sum(int((posts or {}).get(d, 0)) for d in dates)
    return {"dates": dates, "aircraft": len(seen) or max(n for _, n in per_day), "messages": messages,
            "per_day": per_day, "best_day": best_day if best_day[1] else None, "busiest_hour": busiest_hour,
            "heat": rows, "airlines": fleet["airlines"][:TOP], "types": fleet["types"][:1], "posted": posted}


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


def day_name(d):
    return DAYS[datetime.date.fromisoformat(d).weekday()]


def text(w, c, area, tags, fit):
    """The post: the head and the counts always; the busiest times, the airlines, the type and the posts while they
    fit beside the hashtags, dropped from the end otherwise. No distance, ever."""
    head = "The week%s, %s: %s aircraft heard, %s messages decoded." % (
        (" " + area) if area else "", span_words(w["dates"]), number(w["aircraft"]), messages_words(w["messages"]))
    more = []
    busy = []
    if w.get("best_day"):
        busy.append("Busiest day: %s, %s aircraft." % (day_name(w["best_day"][0]), number(w["best_day"][1])))
    if w.get("busiest_hour") is not None:
        busy.append("Busiest hour: %02d:00." % w["busiest_hour"])
    if busy:
        more.append(" ".join(busy))
    if w.get("airlines"):
        more.append("Most seen: " + ", ".join("%s (%s)" % (n, number(k)) for n, k in w["airlines"][:3]) + ".")
    if w.get("types"):
        more.append("Top type: %s." % w["types"][0][0])
    if w.get("posted"):
        more.append("Posted here: %s crossing%s." % (number(w["posted"]), "" if w["posted"] == 1 else "s"))
    while True:
        body = "\n".join([head] + more)
        out = fit(body, None, tags)
        if out.startswith(body) or not more:
            return out
        more.pop()


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
    return s


# --------------------------------------------------------------------------- the picture
def draw(w, theme, area, out):
    """The card, as a PNG at `out`. Needs Pillow (social_card). Returns {path, width, height, bytes, mime}."""
    from PIL import Image, ImageDraw
    import social_card as card
    col = card.rgb(THEME_HEX.get(theme, "#ffb000"))
    dim = tuple(int(v * 0.55) for v in col)
    grey, faint, off = (150, 150, 150), (90, 90, 90), (28, 28, 28)
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    f_head, f_big, f_lbl, f_small, f_name = card.font(30), card.font(58), card.font(18), card.font(16, bold=False), card.font(20, bold=False)
    m = 48
    d.text((m, 34), ("THE WEEK " + area).upper() if area else "THE WEEK", font=f_head, fill=col)
    d.text((W - m, 34), span_words(w["dates"]).upper(), font=f_head, fill=dim, anchor="ra")
    d.line([(m, 86), (W - m, 86)], fill=off, width=2)
    # the counts, on the left
    rows = [(number(w["aircraft"]), "AIRCRAFT HEARD"),
            ((messages_words(w["messages"]).replace(" million", " M")), "MESSAGES DECODED")]
    if w.get("best_day"):
        rows.append((day_name(w["best_day"][0]).upper(), "BUSIEST DAY \u00b7 %s AIRCRAFT" % number(w["best_day"][1])))
    if w.get("busiest_hour") is not None:
        rows.append(("%02d:00" % w["busiest_hour"], "BUSIEST HOUR"))
    y = 112
    for big, lbl in rows:
        d.text((m, y), big, font=f_big, fill=col)
        d.text((m + 2, y + 68), lbl, font=f_lbl, fill=grey)
        y += 128
    # the week by hour, top right: a dot per hour, brighter where more aircraft had a position
    gx, gy, cw, ch = 520, 118, 26, 34
    vals = [v for r in w["heat"] for v in r if v is not None]
    top = max(vals) if vals else 0
    for i, r in enumerate(w["heat"]):
        d.text((gx - 14, gy + i * ch + ch / 2), day_name(w["dates"][i])[:3].upper(), font=f_small, fill=grey, anchor="rm")
        for h, v in enumerate(r):
            cx, cy = gx + h * cw + cw / 2, gy + i * ch + ch / 2
            if v is None or not top:
                fill = off
            else:
                k = 0.12 + 0.88 * (v / top)
                fill = tuple(int(off[j] + (col[j] - off[j]) * k) for j in range(3))
            rr = 10
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=fill)
    for h in (0, 6, 12, 18):
        d.text((gx + h * cw + cw / 2, gy + 7 * ch + 8), "%02dh" % h, font=f_small, fill=faint, anchor="ma")
    # the airlines, bottom right
    ay = 410
    d.text((gx - 54, ay), "MOST SEEN", font=f_lbl, fill=grey)
    ay += 34
    best = w["airlines"][0][1] if w.get("airlines") else 0
    bx0, bx1 = 760, W - m - 70
    for n, k in w.get("airlines") or []:
        d.text((gx - 54, ay + 2), n if len(n) <= 22 else n[:21] + "…", font=f_name, fill=(225, 225, 225))
        d.rounded_rectangle([bx0, ay + 4, bx0 + max(6, int((bx1 - bx0) * k / best)), ay + 24], radius=4, fill=col)
        d.text((W - m, ay + 2), number(k), font=f_name, fill=grey, anchor="ra")
        ay += 34
    if not w.get("airlines"):
        d.text((gx - 54, ay), "No airline counted yet (ZenithBoard 0.31.0 or later).", font=f_name, fill=faint)
    if w.get("types"):
        d.text((m, H - 34), "TOP TYPE  " + w["types"][0][0].upper(), font=f_lbl, fill=dim)
    d.text((W - m, H - 34), "ZENITHBOARD", font=f_lbl, fill=faint, anchor="ra")
    img.save(out, "PNG", optimize=True)
    return {"path": out, "width": W, "height": H, "bytes": os.path.getsize(out), "mime": "image/png"}
