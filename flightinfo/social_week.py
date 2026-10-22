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
import re

import post_lang
import server
from post_lang import N_

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
# 0.38.0: three summaries, each on or off, at its own time on the Pi's clock, with the posts the owner picks.
#   daily    every day at HH:MM, the last 24 hours
#   weekly   one weekday at HH:MM, the seven days ending that day (Sunday 19:00 since 0.33.0)
#   monthly  one day of the month (1 to 28, so that every month has it) at HH:MM, the thirty days ending that day
PERIODS = {
    "daily": {"days": 1, "key": "SOCIAL_DAILY", "at": "21:00", "parts": "1", "word": N_("The last 24 hours")},
    "weekly": {"days": 7, "key": "SOCIAL_WEEKLY", "at": "sun 19:00", "parts": "1,2,3,4", "word": N_("The week")},
    "monthly": {"days": 30, "key": "SOCIAL_MONTHLY", "at": "1 09:00", "parts": "1,2,3,4", "word": N_("The last 30 days")},
}
ORDER = ("monthly", "weekly", "daily")      # when two fall at the same time, the longer goes first
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def parse_at(period, value):
    """(day, hour, minute) from the setting: day is None (daily), 0-6 (weekly, Monday 0) or 1-28 (monthly).
    Raises ValueError on anything else."""
    value = " ".join(str(value or "").strip().lower().split())
    parts = value.split(" ")
    clock = parts[-1]
    if not clock or ":" not in clock:
        raise ValueError("a time, HH:MM")
    hh, mm = clock.split(":", 1)
    hour, minute = int(hh), int(mm)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("a time, HH:MM")
    if period == "daily":
        if len(parts) != 1:
            raise ValueError("a time only, HH:MM")
        return None, hour, minute
    if len(parts) != 2:
        raise ValueError("a day and a time")
    if period == "weekly":
        day = parts[0][:3]
        if day not in WEEKDAYS:
            raise ValueError("a weekday: mon tue wed thu fri sat sun")
        return WEEKDAYS.index(day), hour, minute
    day = int(parts[0])
    if not 1 <= day <= 28:
        raise ValueError("a day of the month, 1 to 28")
    return day, hour, minute


def at_of(c, period):
    """The period's time as set, or its default when the setting is missing or wrong (the setter refuses a wrong one;
    a hand-edited config.env falls back rather than stops the service)."""
    try:
        return parse_at(period, c.get(PERIODS[period]["key"] + "_AT") or PERIODS[period]["at"])
    except (ValueError, KeyError):
        return parse_at(period, PERIODS[period]["at"])


def at_words(c, period):
    day, hour, minute = at_of(c, period)
    clock = "%02d:%02d" % (hour, minute)
    if period == "daily":
        return "every day at " + clock
    if period == "weekly":
        return "every %s at %s" % (DAYS[day], clock)
    return "on the %d%s of each month at %s" % (day, {1: "st", 2: "nd", 3: "rd", 21: "st", 22: "nd", 23: "rd"}.get(day, "th"), clock)


def parts_of(c, period):
    """The posts picked for that summary, 1 to 4 in order; the first is always among them (the others follow it)."""
    raw = str(c.get(PERIODS[period]["key"] + "_PARTS") or PERIODS[period]["parts"]).replace(" ", "")
    if raw.lower() == "all":
        return [1, 2, 3, 4]
    got = sorted({int(x) for x in raw.split(",") if x.isdigit() and 1 <= int(x) <= 4})
    return got or [1]


def is_on(c, period):
    return server.cfg_bool(c, PERIODS[period]["key"], "0")


def cycle_key(period, now):
    """One summary per key: the day, the ISO week or the month of a time."""
    d = datetime.date.fromtimestamp(now)
    if period == "daily":
        return d.isoformat()
    if period == "weekly":
        y, w, _ = d.isocalendar()
        return "%d-W%02d" % (y, w)
    return d.strftime("%Y-%m")


def week_key(now):
    """The ISO week of a time (0.33.0)."""
    return cycle_key("weekly", now)


def at_norm(c, period):
    """The time as set, in one spelling: "21:00", "sun 19:00", "1 09:00"."""
    day, hour, minute = at_of(c, period)
    clock = "%02d:%02d" % (hour, minute)
    return clock if period == "daily" else ("%s %s" % (WEEKDAYS[day], clock) if period == "weekly" else "%d %s" % (day, clock))


def slot_key(c, period, now):
    """0.49.0: one summary per scheduled slot, the cycle and the time it is set for ("2026-10-22@23:35"), no longer
    one per cycle: the owner (22 October) moved the daily one to a later time and wanted it to go at that time; the
    schedule itself keeps a summary from going twice (a slot goes once)."""
    return "%s@%s" % (cycle_key(period, now), at_norm(c, period))


def setting_of(c, period):
    return ("on " + at_norm(c, period)) if is_on(c, period) else "off"


def changed(c, state, period):
    """The time or the switch was changed since the service last looked (None: never looked, 0.49.0's first start)."""
    seen = (state.get("summary_seen") or {}).get(period)
    return seen is not None and seen != setting_of(c, period)


def slot_passed(c, period, now):
    """Its day in this cycle, and its time reached: the moment it is due from, until the end of that day."""
    day, hour, minute = at_of(c, period)
    lt = datetime.datetime.fromtimestamp(now)
    if period == "weekly" and lt.weekday() != day:
        return False
    if period == "monthly" and lt.day != day:
        return False
    return (lt.hour, lt.minute) >= (hour, minute)


def slot_done(c, state, period, now):
    done = done_for(state, period)
    if not done:
        return False
    if "@" not in done:                          # 0.38.0 to 0.48.0 kept the cycle alone: done for the time as set now
        return done == cycle_key(period, now)
    return done == slot_key(c, period, now)


def due(c, state, now, period="weekly"):
    """On, its slot reached (its day, from its time to the end of that day), and that slot not gone yet. A Pi switched
    off at that time posts it when it comes back the same day, never the next day. 0.49.0: a time moved later the same
    day is a new slot, which goes at its time; a time set (or a summary switched on) after its time has passed today
    does not go at once: the service marks that slot as gone when it sees the change."""
    if not is_on(c, period) or not slot_passed(c, period, now):
        return False
    if changed(c, state, period):
        return False
    return not slot_done(c, state, period, now)


def next_due(c, state, now, period):
    """0.48.0: when that summary goes out next, as a datetime; now when it is due now; None when it is off. 0.49.0: a
    time moved to later today goes today; a time set after it has passed today goes from the next cycle."""
    if not is_on(c, period):
        return None
    if due(c, state, now, period):
        return datetime.datetime.fromtimestamp(now)
    day, hour, minute = at_of(c, period)
    base = datetime.datetime.fromtimestamp(now)
    for i in range(0, 62):
        d = (base + datetime.timedelta(days=i)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        if period == "weekly" and d.weekday() != day:
            continue
        if period == "monthly" and d.day != day:
            continue
        if d.timestamp() < now:                  # passed today: set after it, or gone already
            continue
        if slot_done(c, state, period, d.timestamp()):
            continue
        return d
    return None


def done_for(state, period):
    """The cycle (day, ISO week, month) whose summary was already put in the queue, or None."""
    done = (state.get("summaries") or {}).get(period)
    if period == "weekly" and not done:
        done = state.get("weekly")
    return done


def when_words(c, state, now, period):
    """One line for `social summary`: when it last went out, when it goes out next (0.48.0)."""
    last_at = (state.get("summaries_at") or {}).get(period)
    done = done_for(state, period)
    if isinstance(last_at, (int, float)):
        last = "last: %s" % datetime.datetime.fromtimestamp(last_at).strftime("%Y-%m-%d %H:%M")
    else:
        last = "last: %s" % (done or "never")
    nxt = next_due(c, state, now, period)
    if nxt is None:
        return last + ("" if is_on(c, period) else "   (off)")
    if abs(nxt.timestamp() - now) < 61:
        return last + "   next: now (due: in the queue at the service's next look)"
    return last + "   next: " + nxt.strftime("%a %Y-%m-%d %H:%M")


# --------------------------------------------------------------------------- what
def _lines(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return set(x.strip() for x in fh if x.strip())
    except OSError:
        return set()


def week_data(c, stats_dir=None, now=None, posts=None, period="weekly"):
    """The period ending now, from the statistics files; None when there are none. weekly and monthly: the 7 or 30
    days ending on now's day; daily (0.38.0): the last 24 hours, to the quarter hour. posts: {YYYY-MM-DD: number of
    posts} from the service's state."""
    stats_dir = stats_dir or server.STATS_DIR
    now_dt = datetime.datetime.fromtimestamp(now) if isinstance(now, (int, float)) else (now or datetime.datetime.now())
    n = PERIODS[period]["days"]
    st = server.read_stats(stats_dir, now_dt, "24h" if n == 1 else ("7d" if n == 7 else "30d"))
    if not st:
        return None
    dates = [(now_dt.date() - datetime.timedelta(days=i)).isoformat() for i in range(max(n, 2) - 1, -1, -1)]
    fleet_from = fleet_start(stats_dir)
    # 0.34.1: the airlines and types only when their lists cover the whole period. On the reference Pi the first
    # test, the evening the lists began (0.31.0), said "6 435 aircraft heard" and "Ryanair (14)": a week against two
    # hours. The last 24 hours start yesterday: the lists must have begun before it
    covered = bool(fleet_from and fleet_from < dates[0])
    # 0.40.4: lists that began inside the period are shown all the same when they cover half of it at least, saying
    # since when (the owner, 21 October: the first daily summary went out with no airline, no model and none of
    # posts 2 to 4, the lists having begun the day before; the statistics page showed them). Under half, they stay
    # out, as 0.34.1 decided: "6 435 aircraft heard" beside "Ryanair (14)" says something false.
    shown, since = covered, None
    if fleet_from and not covered and fleet_from <= dates[-1]:
        began, since = fleet_since(stats_dir, fleet_from)
        start = now_dt - datetime.timedelta(hours=24) if n == 1 else \
            datetime.datetime.combine(datetime.date.fromisoformat(dates[-n]), datetime.time())
        whole = (now_dt - start).total_seconds()
        shown = whole > 0 and (now_dt - max(began, start)).total_seconds() >= whole / 2
        since = since if shown else None
    posted = sum(int((posts or {}).get(d, 0)) for d in dates[-n:] if n > 1) if n > 1 else \
        int((posts or {}).get(dates[-1], 0))
    w = st["window"]
    if n == 1:
        if not w["totals"]["messages"] and not w["totals"]["aircraft"]:
            return None
        fleet = server.read_fleet(c, stats_dir, now_dt, rng="24h") if shown else {}
        row = [v if c_ else None for v, c_ in zip(w["aircraft"], w["messages"])]
        known = [(v, i) for i, v in enumerate(row) if v is not None]
        # the busiest hour as the weekly one counts it: the most aircraft with a position, not the most messages
        busiest = int(w["labels"][max(known)[1]][:2]) if known else None
        out = {"dates": dates, "aircraft": w["totals"]["aircraft"], "messages": w["totals"]["messages"], "per_day": [],
               "best_day": None, "busiest_hour": busiest, "heat": [row], "heat_labels": w["labels"]}
    else:
        by_day = {d["day"]: d for d in st.get("days") or []}
        heat = {r["day"]: r["hours"] for r in st.get("heat") or []}
        seen, per_day = set(), []
        for d in dates:
            s_ = _lines(os.path.join(stats_dir, "seen-" + d))
            seen |= s_
            per_day.append((d, len(s_) or (by_day.get(d) or {}).get("aircraft", 0)))
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
        fleet = server.read_fleet(c, stats_dir, now_dt, since=dates[0]) if shown else {}
        out = {"dates": dates, "aircraft": len(seen) or max(k for _, k in per_day), "messages": messages,
               "per_day": per_day, "best_day": best_day if best_day[1] else None,
               "busiest_hour": max(known)[1] if known else None, "heat": rows}
    out.update({"period": period, "airlines": (fleet.get("airlines") or [])[:TOP], "models": (fleet.get("types") or [])[:TOP],
                "cargo": (fleet.get("cargo") or [])[:TOP], "cargo_total": fleet.get("cargo_total", 0),
                "bizjets": (fleet.get("bizjets") or [])[:TOP], "bizjet_total": fleet.get("bizjet_total", 0),
                "cargo_models": fleet.get("cargo_models") or {},
                "bizjet_countries": [(cc, k) for cc, k in fleet.get("bizjet_countries") or [] if cc][:TOP],
                "military": fleet.get("military") or [], "military_total": fleet.get("military_total", 0),
                "military_unknown": fleet.get("military_unknown") or {}, "until": now_dt.strftime("%H:%M"),
                "misc": fleet.get("misc") or {}, "airline_cc": fleet.get("airline_cc") or {}, "covered": covered, "shown": shown, "since": since, "posted": posted,
                "fleet_from": fleet_from,
                "fleet_week": first_full_week(fleet_from) if period == "weekly" else first_full(fleet_from, n)})
    return out


def fleet_since(stats_dir, day):
    """When the lists began -> (datetime, words): "20 October, 19:15" from the earliest time an aircraft was last seen
    in that day's file (its seventh column, 0.37.0 on), or the day's start and "20 October" when the file is older than
    that column."""
    times = []
    try:
        with open(os.path.join(stats_dir, "fleet-" + day), encoding="utf-8") as fh:
            for line in fh:
                cols = line.rstrip("\n").split("\t")
                if len(cols) >= 7 and re.match(r"^([01]\d|2[0-3])[0-5]\d$", cols[6]):
                    times.append(cols[6])
                elif line.strip():
                    times = []                   # a line from before 0.37.0: the start of the day is not known
                    break
    except OSError:
        pass                                     # no file: the day alone
    d = datetime.date.fromisoformat(day)
    if times:
        t = min(times)
        return datetime.datetime.combine(d, datetime.time(int(t[:2]), int(t[2:]))), "%s, %s:%s" % (short_date(day), t[:2], t[2:])
    return datetime.datetime.combine(d, datetime.time()), short_date(day)


def first_full(fleet_from, days):
    """The first day a summary of `days` days ending that day shows the lists: covered half at least (0.40.4; whole
    in 0.38.0). The day after they began for the 24 hours, half the period after it otherwise."""
    if not fleet_from:
        return None
    return (datetime.date.fromisoformat(fleet_from) + datetime.timedelta(days=max(1, (days + 1) // 2))).isoformat()


def fleet_start(stats_dir):
    """The first day of the airline and type lists (fleet-DAY files, 0.31.0), or None."""
    try:
        days = sorted(n[6:] for n in os.listdir(stats_dir) if n.startswith("fleet-"))
    except OSError:
        return None
    return days[0] if days else None


def first_full_week(fleet_from):
    """The Sunday of the first week whose lists are shown: covered half at least (0.40.4; whole before)."""
    if not fleet_from:
        return None
    # half a week: the lists must have begun three and a half days before the Sunday evening at least
    d = datetime.date.fromisoformat(fleet_from) + datetime.timedelta(days=3)
    return (d + datetime.timedelta(days=(6 - d.weekday()) % 7)).isoformat()


# --------------------------------------------------------------------------- words
# 0.51.0: the summaries' words in the posts' language (SOCIAL_LANG, post_lang.py); each function takes it as L,
# English when it is not given. The pictures keep English this release: they call these without L.
EN = post_lang.get("en")
UNKNOWN_NAMES = (N_("Unknown type"), N_("Helicopter, type unknown"), N_("Light aircraft, type unknown"),
                 N_("Glider, type unknown"), N_("Balloon or airship"), N_("Drone"))       # server.MISC_UNKNOWN's, and the lists' own


def number(n, L=None):
    """3 412, with a space that does not break, as the posts write altitudes (0.51.0: 3.412 in German)."""
    return (L or EN).num(int(n))


def millions(n, L=None):
    """58.7 for 58 700 000 (58,7 in French); 58 for 58 000 000."""
    s = ("%.1f" % (n / 1e6)).rstrip("0").rstrip(".")
    return s if (L or EN).code == "en" else s.replace(".", (L.loc.get("decimal") or "."))


def messages_words(n, L=None):
    """"58.7 million" (the pictures, English), as before 0.51.0."""
    if n >= 1e6:
        return "%s million" % millions(n)
    return number(n)


def messages_phrase(n, L=None):
    """"58.7 million messages", "3 412 messages": the words of the posts. Japanese, Korean and Chinese count in tens of
    thousands: 5870万件 rather than 58.7 million (post_lang.Lang.myriad)."""
    L = L or EN
    if L.myriad(n):
        return L.tn(int(n), "{n} messages", "{n} messages", n=L.myriad(n))
    if n >= 1e6:
        return L.tn(int(n // 1e6), "{n} million messages", "{n} million messages", n=millions(n, L))   # "1,2 million de messages"
    return L.tn(n, "{n} messages", "{n} messages")


def aircraft_phrase(n, L=None):
    return (L or EN).tn(n, "{n} aircraft", "{n} aircraft")


def span_words(dates, L=None):
    return (L or EN).span(dates[0], dates[-1])


def period_words(w, L=None):
    """"14–20 October", or for the daily summary "the last 24 hours" (0.38.0)."""
    return (L or EN).t("the last 24 hours") if w.get("period") == "daily" else span_words(w["dates"], L)


def short_date(d, L=None):
    return (L or EN).day_month(d)


def day_name(d, L=None):
    return (L or EN).weekday(d)


def model_name(name, L=None):
    """A model as the lists say it: "Unknown type" and the like in the posts' language, a real name as it is."""
    return (L or EN).t(name) if name in UNKNOWN_NAMES else name


def _ranked(label, pairs, n, L=None):
    L = L or EN
    return L.t("{label}: {list}.", label=label, list=L.join(["%s (%s)" % (model_name(name, L), number(k, L)) for name, k in pairs[:n]])) if pairs else None


def _fit_lines(head, parts, tags, fit, L=None):
    """head, then the parts: a part is a line, or (label, pairs) drawn as a ranked list. The lists go down from three
    names to one before any line is dropped, and lines are dropped from the end, so the hashtags stay whole."""
    def lines(n):
        return [x for x in ((p if isinstance(p, str) else _ranked(p[0], p[1], n, L)) for p in parts) if x]

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
    hashtags. No distance, ever. In the posts' language (SOCIAL_LANG, 0.51.0); area as the posts say it."""
    L = post_lang.of(c)
    word = L.t(PERIODS[w.get("period") or "weekly"]["word"])
    if w.get("period") == "daily":
        head = L.t("{period}[ {area}]: {aircraft}, {messages}.", period=word, area=area,
                   aircraft=aircraft_phrase(w["aircraft"], L), messages=messages_phrase(w["messages"], L))
    else:
        head = L.t("{period}[ {area}], {span}: {aircraft}, {messages}.", period=word, area=area, span=span_words(w["dates"], L),
                   aircraft=aircraft_phrase(w["aircraft"], L), messages=messages_phrase(w["messages"], L))
    parts = []
    bd, bh = w.get("best_day"), w.get("busiest_hour")
    if bd and bh is not None:
        parts.append(L.t("Busiest: {day} ({aircraft}) and {hour}.", day=day_name(bd[0], L), aircraft=aircraft_phrase(bd[1], L),
                         hour=L.clock(bh)))
    elif bd:
        parts.append(L.t("Busiest: {day} ({aircraft}).", day=day_name(bd[0], L), aircraft=aircraft_phrase(bd[1], L)))
    elif bh is not None:
        parts.append(L.t("Busiest hour: {hour}.", hour=L.clock(bh)))
    parts.append((L.t("Airlines"), w.get("airlines") or []))
    parts.append((L.t("Models"), w.get("models") or []))          # 0.35.0
    if w.get("posted"):
        parts.append(L.tn(w["posted"], "Posted here: {n} crossing.", "Posted here: {n} crossings."))
    return _fit_lines(head, parts, tags, fit, L)


ALT_KIND = {"daily": N_("Daily summary card for {period}[ {area}]"), "weekly": N_("Weekly summary card for {period}[ {area}]"),
            "monthly": N_("Thirty-day summary card for {period}[ {area}]")}
ALT_PICTURE = {"daily": N_("A row of the 24 hours, brighter where more aircraft were overhead."),
               "weekly": N_("A grid of the seven days by hour, brighter where more aircraft were overhead."),
               "monthly": N_("A column of dots for each of the thirty days, taller where more aircraft were heard.")}


def alt(w, area, L=None):
    L = L or EN
    period = w.get("period") or "weekly"
    bits = [L.t(ALT_KIND[period], period=period_words(w, L), area=area),
            L.t("{aircraft} heard and {messages} decoded", aircraft=aircraft_phrase(w["aircraft"], L), messages=messages_phrase(w["messages"], L))]
    if w.get("best_day"):
        bits.append(L.t("busiest day {day} with {aircraft}", day=day_name(w["best_day"][0], L), aircraft=aircraft_phrase(w["best_day"][1], L)))
    if w.get("busiest_hour") is not None:
        bits.append(L.t("busiest hour {hour}", hour=L.clock(w["busiest_hour"])))
    s = L.t("{sentence}.", sentence=L.join(bits)) + " " + L.t(ALT_PICTURE[period])
    if w.get("airlines"):
        s += " " + L.t("The airlines most seen, as bars: {list}.", list=L.join(["%s %d" % (n, k) for n, k in w["airlines"]]))
    if w.get("models"):
        s += " " + L.t("Beside them, the models most seen: {list}.", list=L.join(["%s %d" % (model_name(n, L), k) for n, k in w["models"]]))
    return s


PARTS = (1, 2, 3, 4)          # 0.36.0: the week; cargo and business jets; military; helicopters, light aircraft, gliders
MISC_SHOWN = (("heli", N_("Helicopters"), "HELICOPTERS"), ("light", N_("Light aircraft"), "LIGHT AIRCRAFT"),
              ("glider", N_("Gliders"), "GLIDERS"), ("other", N_("Drones and balloons"), "DRONES AND BALLOONS"))
MISC_COUNT = {"heli": (N_("{n} helicopter"), N_("{n} helicopters")), "light": (N_("{n} light aircraft"), N_("{n} light aircraft")),
              "glider": (N_("{n} glider"), N_("{n} gliders")), "other": (N_("{n} drone or balloon"), N_("{n} drones and balloons"))}


def misc_lists(w):
    """{group: {"total", "models"}} with the drones and the balloons together, as the picture shows them."""
    m = dict(w.get("misc") or {})
    other = {}
    for g in ("drone", "balloon"):
        for name, k in (m.get(g) or {}).get("models") or []:
            other[name] = other.get(name, 0) + k
    rows = {}
    for g in ("drone", "balloon"):
        for name, cc, k in (m.get(g) or {}).get("rows") or []:
            rows[(name, cc)] = rows.get((name, cc), 0) + k
    m["other"] = {"total": sum(other.values()), "models": sorted(other.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP],
                  "rows": [(n, c, k) for (n, c), k in sorted(rows.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1] or ""))[:TOP]]}
    return m


def name_unknown_military(w, lookup, limit=12):
    """0.40.5: military aircraft whose type neither the decoder nor tar1090's database gave (the reference Pi's first
    daily summary: "Germany: Unknown type (2)"), asked of adsbdb, then hexdb, by their address: what the wall asks
    for any aircraft when routes are on. A dozen at most, the answers renamed in place; the rest stay unknown.
    lookup(hex) -> {"icao_type", "type", "manufacturer"} or None."""
    asked = 0
    for e in w.get("military") or []:
        hexes = (w.get("military_unknown") or {}).get(e.get("cc")) or []
        named = {}
        for h in hexes:
            if asked >= limit:
                break
            asked += 1
            try:
                got = lookup(h)
            except Exception:
                got = None                       # unreachable: it stays unknown
            if not got:
                continue
            name = " ".join(x for x in (got.get("manufacturer"), got.get("type")) if x) or got.get("icao_type")
            if name:
                named[name] = named.get(name, 0) + 1
        if not named:
            continue
        models = dict(e["models"])
        left = models.pop("Unknown type", 0) - sum(named.values())
        for n, k in named.items():
            models[n] = models.get(n, 0) + k
        if left > 0:
            models["Unknown type"] = left
        e["models"] = sorted(models.items(), key=lambda kv: (kv[0] == "Unknown type", -kv[1], kv[0]))
    return w


def has_part(w, part):
    """Something to say in that post, over the whole week. The first always has (when there are statistics)."""
    if part == 1:
        return bool(w)
    if not (w and (w.get("shown") or w.get("covered"))):
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


def text_second(w, area, tags, fit, L=None):
    """Cargo airlines and business jets: the head always, the lists while they fit."""
    L = L or EN
    head = L.t("Cargo and business jets[ {area}], {period}: {cargo}, {bizjets}.", area=area, period=period_words(w, L),
               cargo=L.tn(w.get("cargo_total", 0), "{n} cargo aircraft", "{n} cargo aircraft"),
               bizjets=L.tn(w.get("bizjet_total", 0), "{n} business jet", "{n} business jets"))
    return _fit_lines(head, [(L.t("Cargo"), w.get("cargo") or []), (L.t("Business jets"), w.get("bizjets") or [])], tags, fit, L)


def text_military(w, area, tags, fit, L=None):
    """Military aircraft: by country, the most represented first, each with its models."""
    L = L or EN
    mil = w.get("military") or []
    head = L.t("Military aircraft[ {area}], {period}: {aircraft} from {countries}.", area=area, period=period_words(w, L),
               aircraft=aircraft_phrase(w.get("military_total", 0), L), countries=L.tn(len(mil), "{n} country", "{n} countries"))
    return _fit_lines(head, [(L.country(e.get("cc"), e["country"]), e["models"]) for e in mil], tags, fit, L)


def text_misc(w, area, tags, fit, L=None):
    L = L or EN
    m = misc_lists(w)
    shown = [g for g, _, _ in MISC_SHOWN if (m.get(g) or {}).get("total")]
    counts = [L.tn(m[g]["total"], MISC_COUNT[g][0], MISC_COUNT[g][1]) for g in shown]
    head = L.t("General aviation[ {area}], {period}: {counts}.", area=area, period=period_words(w, L), counts=L.join(counts))
    return _fit_lines(head, [(L.t(label), m[g]["models"]) for g, label, _ in MISC_SHOWN if g in shown], tags, fit, L)


def alt_second(w, area, L=None):
    L = L or EN
    s = L.t("Weekly card of the cargo airlines and business jets, {period}[ {area}]: {cargo} and {bizjets}.", period=period_words(w, L),
            area=area, cargo=L.tn(w.get("cargo_total", 0), "{n} cargo aircraft", "{n} cargo aircraft"),
            bizjets=L.tn(w.get("bizjet_total", 0), "{n} business jets", "{n} business jets"))
    if w.get("cargo"):
        cm = w.get("cargo_models") or {}
        s += " " + L.t("Cargo airlines, as bars, each with the model it flew most: {list}.", list=L.join([
            "%s %d%s" % (n, k, (" " + L.t("(mostly {model}, {n})", model=model_name(cm[n][0], L), n=cm[n][1])) if n in cm else "")
            for n, k in w["cargo"]]))
    if w.get("bizjets"):
        s += " " + L.t("Business jets by make and model, as bars: {list}.", list=L.join(["%s %d" % (n, k) for n, k in w["bizjets"]]))
    if w.get("bizjet_countries"):
        s += " " + L.t("The countries they are registered in, with their flags: {list}.", list=L.join([
            "%s %d" % (L.country(c, server.country_name(c)), k) for c, k in w["bizjet_countries"]]))
    return s


def alt_military(w, area, L=None):
    L = L or EN
    return L.t("Weekly card of the military aircraft, {period}[ {area}]: {aircraft}. By country, with its flag, the most represented first: {list}.",
               period=period_words(w, L), area=area, aircraft=aircraft_phrase(w.get("military_total", 0), L),
               list=L.join(["%s %d (%s)" % (L.country(e.get("cc"), e["country"]), e["total"],
                                            L.join(["%s %d" % (model_name(n, L), k) for n, k in e["models"][:3]]))
                            for e in w.get("military") or []], "{a}; {b}"))


def alt_misc(w, area, L=None):
    L = L or EN
    m = misc_lists(w)
    groups = [L.t("{label}: {n} ({list}).", label=L.t(label), n=m[g]["total"], list=L.join(["%s %d" % (model_name(n, L), k) for n, k in m[g]["models"]]))
              for g, label, _ in MISC_SHOWN if (m.get(g) or {}).get("total")]
    return L.t("Weekly card of the helicopters, light aircraft, gliders, drones and balloons, {period}[ {area}]. {groups}",
               period=period_words(w, L), area=area, groups=" ".join(groups))


FLAG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "flags")


def load_flags(codes):
    """{ISO code: picture} of the real flags, 48 x 32 (0.36.1: flightinfo/data/flags, country-flag-icons, MIT). A
    country without one has no entry. The wall's dot flags looked crude at this size (the owner, 0.36.0)."""
    from PIL import Image
    out = {}
    for cc in sorted({c for c in codes if c}):
        p = os.path.join(FLAG_DIR, "%s.png" % cc)
        if len(cc) == 2 and cc.isalpha() and os.path.isfile(p):
            try:
                with Image.open(p) as im:
                    out[cc] = im.convert("RGB")
            except OSError:
                pass                             # an unreadable file: the two letters instead
    return out


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


SPAN_TITLES = {"daily": "LAST 24 HOURS", "weekly": "LAST 7 DAYS", "monthly": "LAST 30 DAYS"}
FOOT_Y = H - 56                     # 0.40.5: above Bluesky's ALT badge, which covered the name in the corner


def span_footer(w):
    """The period exactly, for the foot of a card: "20 October, 10:15 – 21 October, 10:15" for the 24 hours."""
    if w.get("period") == "daily" and w.get("until"):
        return "%s, %s – %s, %s" % (short_date(w["dates"][0]), w["until"], short_date(w["dates"][-1]), w["until"])
    return span_words(w["dates"])


def _header(d, f, col, dim, title, w):
    # 0.40.5: the period in words at the top right (the owner: "21 OCTOBER" read as that day, not the 24 hours
    # before it), and its exact span at the foot
    span = SPAN_TITLES.get(w.get("period") or "weekly", "LAST 7 DAYS")
    room = W - 2 * M - d.textlength(span, font=f["head"]) - 30       # a long place name never runs into the period
    d.text((M, 34), _fit(d, title.upper(), f["head"], room), font=f["head"], fill=col)
    d.text((W - M, 34), span, font=f["head"], fill=dim, anchor="ra")
    d.line([(M, 86), (W - M, 86)], fill=OFF, width=2)
    d.text((W - M, FOOT_Y), "ZENITHBOARD", font=f["lbl"], fill=FAINT, anchor="ra")
    foot = span_footer(w)
    if w.get("since"):                           # 0.40.4: lists shown though they began inside the period
        foot += "  \u00b7  lists counted since " + w["since"]
    d.text((M, FOOT_Y), foot, font=f["small"], fill=FAINT)


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
    if w.get("covered") or w.get("shown"):
        why = "Nothing in the lists for this period."
    elif w.get("fleet_from"):
        why = "Counted since %s: shown from the summary of %s." % (short_date(w["fleet_from"]), short_date(w["fleet_week"]))
    else:
        why = "Not counted yet: statistics from ZenithBoard 0.31.0 on."
    d.text((x, y), why, font=f["name"], fill=FAINT)


def _dot_fill(col, v, top):
    k = None if v is None or not top else 0.12 + 0.88 * (v / top)
    return OFF if k is None else tuple(int(OFF[j] + (col[j] - OFF[j]) * k) for j in range(3))


def _period_graph(d, f, col, w):
    """The card's graph, in dots: the week by hour (7 rows of 24); the last 24 hours (one row, larger dots, 0.38.0);
    the thirty days (a column of dots a day, as tall as that day had aircraft, 0.38.0)."""
    period = w.get("period") or "weekly"
    gx, gy = 520, 108
    if period == "monthly":
        per = w.get("per_day") or []
        top = max([k for _, k in per] or [0])
        cw, levels, step = (W - M - gx) / max(1, len(per)), 8, 20
        for i, (day, k) in enumerate(per):
            lit = round(levels * k / top) if top else 0
            cx = gx + i * cw + cw / 2
            for lv in range(levels):
                cy = gy + (levels - 1 - lv) * step + 10
                d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=col if lv < lit else OFF)
            if i % 7 == 0 and len(per) - i > 3:  # one date a week, none crowding the last
                dd = datetime.date.fromisoformat(day)
                d.text((cx, gy + levels * step + 6), "%02d/%02d" % (dd.day, dd.month), font=f["small"], fill=FAINT, anchor="ma")
            if i == len(per) - 1:
                dd = datetime.date.fromisoformat(day)
                d.text((cx, gy + levels * step + 6), "%02d/%02d" % (dd.day, dd.month), font=f["small"], fill=GREY, anchor="ma")
        return
    if period == "daily":
        row, labels = (w.get("heat") or [[None] * 24])[0], w.get("heat_labels") or ["%02dh" % h for h in range(24)]
        vals = [v for v in row if v is not None]
        top, cw = max(vals) if vals else 0, (W - M - gx) / 24
        for h, v in enumerate(row):
            cx, cy = gx + h * cw + cw / 2, gy + 50
            d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=_dot_fill(col, v, top))
            if h % 3 == 0:
                d.text((cx, cy + 22), labels[h], font=f["small"], fill=FAINT, anchor="ma")
        d.text((gx, gy), "AIRCRAFT WITH A POSITION, HOUR BY HOUR", font=f["small"], fill=GREY)
        return
    cw, ch = 26, 22
    vals = [v for r in w["heat"] for v in r if v is not None]
    top = max(vals) if vals else 0
    for i, r in enumerate(w["heat"]):
        d.text((gx - 14, gy + i * ch + ch / 2), day_name(w["dates"][i])[:3].upper(), font=f["small"], fill=GREY, anchor="rm")
        for h, v in enumerate(r):
            cx, cy = gx + h * cw + cw / 2, gy + i * ch + ch / 2
            d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=_dot_fill(col, v, top))
    for h in (0, 6, 12, 18):
        d.text((gx + h * cw + cw / 2, gy + 7 * ch + 6), "%02dh" % h, font=f["small"], fill=FAINT, anchor="ma")


def draw(w, theme, area, out, flags=None):
    """The week's card, as a PNG at `out`: the counts on the left; the week by hour, then the airlines and the
    models most seen side by side, on the right (0.35.0: the grid smaller to make room for the models).
    Needs Pillow (social_card). Returns {path, width, height, bytes, mime}."""
    img, d, col, dim, f = _canvas(theme)
    # 0.40.5: the period is said at the top right of every card now, so the first one is titled like the others
    _header(d, f, col, dim, ("AIRCRAFT " + area) if area else "AIRCRAFT", w)
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
    _period_graph(d, f, col, w)
    # the airlines and the models, side by side
    x0, x1, colw, ly = 466, 820, 332, 300
    if w.get("airlines") or w.get("models"):
        # 0.43.0: each airline with the flag of the country it is based in, first, as on the statistics page (the owner)
        acc = w.get("airline_cc") or {}
        _flag_ranks(img, d, f, col, flags or {}, x0, ly, colw, "AIRLINES MOST SEEN",
                    [(n, acc.get(n), k) for n, k in w.get("airlines") or []])
        _ranks(d, f, col, x1, ly, colw, "MODELS MOST SEEN", w.get("models") or [])
    else:
        d.text((x0, ly), "AIRLINES AND MODELS MOST SEEN", font=f["lbl"], fill=GREY)
        _not_yet(d, f, x0, ly + 32, w)
    img.save(out, "PNG", optimize=True)
    return {"path": out, "width": W, "height": H, "bytes": os.path.getsize(out), "mime": "image/png"}


def _flag_or_code(img, d, f, flags, cc, x, y):
    """The country's flag, 48 x 32 with a thin grey edge (a white flag shows on black), or its two letters in a box:
    the row keeps its place either way."""
    if cc in flags:
        img.paste(flags[cc], (int(x) + 1, int(y) + 1))
        d.rectangle([x, y, x + 49, y + 33], outline=(70, 70, 70), width=1)
        return
    d.rectangle([x, y, x + 49, y + 33], outline=FAINT, width=1)
    d.text((x + 25, y + 17), cc or "?", font=f["small"], fill=GREY, anchor="mm")


def _total(d, f, col, x, y, n, label):
    d.text((x, y), number(n), font=f["big"], fill=col)
    d.text((x + 2, y + 68), label, font=f["lbl"], fill=GREY)


def draw_second(w, theme, area, out, flags=None):
    """The second card (0.35.0; three columns in 0.36.0): the cargo airlines, each with the model it flew most; the
    business jets by make and model; and the countries the business jets are registered in, with their flags."""
    img, d, col, dim, f = _canvas(theme)
    flags = flags or {}
    _header(d, f, col, dim, ("CARGO AND BUSINESS JETS " + area) if area else "CARGO AND BUSINESS JETS", w)
    # cargo: the airline, then in grey the model it flew most and how many of them, the airline's count on the right
    x0, width0 = M, 420
    _total(d, f, col, x0, 108, w.get("cargo_total", 0), "CARGO AIRCRAFT")
    d.text((x0, 236), "CARGO AIRLINES \u00b7 MOST SEEN MODEL", font=f["lbl"], fill=GREY)
    y, cargo, cm, acc = 268, w.get("cargo") or [], w.get("cargo_models") or {}, w.get("airline_cc") or {}
    best = cargo[0][1] if cargo else 0
    x, width = x0 + 58, width0 - 58            # 0.43.0: the airline's flag first, the rest after it
    for name, k in cargo[:TOP]:
        _flag_or_code(img, d, f, flags, acc.get(name), x0, y - 6)
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
        d.text((x0, 268), "None heard this week.", font=f["name"], fill=FAINT)
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
    d.text((x, 236), "MOST REGISTERED IN", font=f["lbl"], fill=GREY)
    y, ctry = 268, w.get("bizjet_countries") or []
    best = ctry[0][1] if ctry else 0
    for cc, k in ctry[:TOP]:
        _flag_or_code(img, d, f, flags, cc, x, y - 6)
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
    _header(d, f, col, dim, ("MILITARY AIRCRAFT " + area) if area else "MILITARY AIRCRAFT", w)
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
            _flag_or_code(img, d, f, flags, cc, x, y - 6)
            d.text((x + 62, y), _fit(d, country, f["name"], 290), font=f["name"], fill=INK)
            last = cc
        d.text((x + 370, y), _fit(d, model, f["name"], 400), font=f["name"], fill=INK)
        bx0, bx1 = x + 790, x + width - 60
        d.rounded_rectangle([bx0, y + 6, bx0 + max(4, int((bx1 - bx0) * k / best)), y + 20], radius=3, fill=col)
        d.text((x + width, y), number(k), font=f["name"], fill=GREY, anchor="ra")
        y += 34
    img.save(out, "PNG", optimize=True)
    return {"path": out, "width": W, "height": H, "bytes": os.path.getsize(out), "mime": "image/png"}


def _flag_ranks(img, d, f, col, flags, x, y, width, title, rows, top=TOP, step=44):
    """0.40.5: a titled list whose rows each start with the flag of the country the aircraft are registered in (by
    their address), then the name, the count on the right and a bar: every column of the card lines up the same."""
    d.text((x, y), title, font=f["lbl"], fill=GREY)
    y += 32
    best = rows[0][2] if rows else 0
    for name, cc, k in rows[:top]:
        _flag_or_code(img, d, f, flags, cc, x, y - 6)
        num = number(k)
        nx = x + 58
        d.text((nx, y), _fit(d, name, f["name"], width - 58 - d.textlength(num, font=f["name"]) - 12), font=f["name"], fill=INK)
        d.text((x + width, y), num, font=f["name"], fill=GREY, anchor="ra")
        d.rounded_rectangle([nx, y + 26, nx + max(4, int((width - 58) * k / best)), y + 31], radius=2, fill=col)
        y += step
    return y


def draw_misc(w, theme, area, out, flags=None):
    """The fourth card (0.36.0): helicopters, light aircraft, gliders, drones and balloons, a column each with its
    total and its makes and models; since 0.40.5 each row with its country's flag (the owner)."""
    flags = flags or {}
    img, d, col, dim, f = _canvas(theme)
    _header(d, f, col, dim, ("GENERAL AVIATION " + area) if area else "GENERAL AVIATION", w)
    m = misc_lists(w)
    shown = [(g, big) for g, _, big in MISC_SHOWN if (m.get(g) or {}).get("total")] or [(g, big) for g, _, big in MISC_SHOWN[:3]]
    gap = 24
    width = int((W - 2 * M - gap * (len(shown) - 1)) / len(shown))
    for i, (g, big) in enumerate(shown):
        x = M + i * (width + gap)
        e = m.get(g) or {"total": 0, "models": []}
        _total(d, f, col, x, 108, e["total"], big)
        if e.get("rows"):
            _flag_ranks(img, d, f, col, flags, x, 236, width, "MAKE AND MODEL", e["rows"])
        elif e["models"]:
            _ranks(d, f, col, x, 236, width, "MAKE AND MODEL", e["models"])
        else:
            d.text((x, 236), "None heard this week.", font=f["name"], fill=FAINT)
    img.save(out, "PNG", optimize=True)
    return {"path": out, "width": W, "height": H, "bytes": os.path.getsize(out), "mime": "image/png"}
