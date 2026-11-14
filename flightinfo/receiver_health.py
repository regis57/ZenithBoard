"""Is the receiver still hearing as it did? (1.2, asked by the owner on 26 October 2026.)

Three rules, read from the statistics' quarter-hour samples (stats.csv: when, messages, farthest_km, ...). They come
from the owner's own thirty days (16 October to 14 November 2026, 2 877 samples), not from a guess:

  deaf    two quarter hours in a row under 2 000 messages, at any hour. The quietest quarter hour of every other
          night was 4 320; on 8 November, 02:45 to 04:00, the receiver gave 12, 374, 878 and 1 709.
  drop    between 07:00 and 22:00, two hours in a row under 40 % of the same hours one week earlier. The lowest hour
          by day in those thirty days was 55 %, once.
  range   the day's median of the farthest aircraft under 85 % of the median of the fourteen days before it, two days
          in a row. Those days went from 94 % to 102 %.

What was NOT taken, and why: the Roadmap's first idea, the message rate against the same hour a week earlier at any
hour. In that month the messages fell by 36 % (65 million a day to 41) while the messages per aircraft in view stayed
where they were: fewer aircraft, the same receiver. At night the ratio of one hour to the same hour a week before
went down to 0.11 with nothing wrong. Such an alert would have cried wolf for a month.

A row stamped HH:MM measures the quarter hour that ends then (lib/stats.sh). No rule can prove a dongle is weakening
before it has happened once: the thresholds are settings.
"""
import datetime
import statistics

DEAF_MESSAGES = 2000         # under this in a quarter hour, twice running: the receiver hears almost nothing
DROP_PERCENT = 40            # by day, an hour under this share of the same hour a week before, twice running
RANGE_PERCENT = 85           # a day's median range under this share of the fourteen days before, twice running
DAY_FROM, DAY_TO = 7, 22     # the hours whose traffic is steady enough to compare week to week
RANGE_DAYS, RANGE_DAYS_MIN = 14, 7
DAY_ROWS_MIN = 90            # of the 96 quarter hours: a day cut short says nothing of its median
RULES = ("deaf", "drop", "range")
QUARTER = datetime.timedelta(minutes=15)


def read_rows(path):
    """[(when, messages, farthest_km)] from stats.csv, oldest first; a line that cannot be read is left out."""
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parts = line.strip().split(",")
                if len(parts) < 3:
                    continue
                try:
                    when = datetime.datetime.strptime(parts[0].strip(), "%Y-%m-%d %H:%M")
                    msgs, far = float(parts[1]), float(parts[2])
                except ValueError:
                    continue
                if msgs != msgs or far != far or msgs < 0 or msgs in (float("inf"),) or far in (float("inf"),):
                    continue
                out.append((when, msgs, far))
    except OSError:
        return []
    out.sort(key=lambda r: r[0])
    return out


def limits(cfg=None):
    """The three thresholds, the owner's when they are sane, else the measured ones."""
    cfg = cfg or {}

    def num(key, default, low, high):
        try:
            v = int(str(cfg.get(key, "")).strip())
        except ValueError:
            return default
        return v if low <= v <= high else default
    return {"deaf": num("HEALTH_DEAF_MESSAGES", DEAF_MESSAGES, 1, 999999),
            "drop": num("HEALTH_DROP_PERCENT", DROP_PERCENT, 1, 99),
            "range": num("HEALTH_RANGE_PERCENT", RANGE_PERCENT, 1, 99)}


def _hours(rows):
    """{hour start: messages} for the hours with their four quarter hours."""
    got = {}
    for when, msgs, _far in rows:
        got.setdefault((when - QUARTER).replace(minute=0, second=0, microsecond=0), []).append(msgs)
    return {k: sum(v) for k, v in got.items() if len(v) == 4}


def _day_ranges(rows):
    """{date: median farthest} for the days with nearly all their quarter hours."""
    got = {}
    for when, _msgs, far in rows:
        got.setdefault((when - QUARTER).date(), []).append(far)
    return {d: statistics.median(v) for d, v in got.items() if len(v) >= DAY_ROWS_MIN}


def evaluate(rows, now, cfg=None):
    """{rule: finding} for the rules that hold at `now` (a datetime). A finding carries the figures the message says."""
    lim, out = limits(cfg), {}
    rows = [r for r in rows if r[0] <= now]
    if not rows:
        return out
    # deaf: the last two samples, fresh, one quarter hour apart
    if len(rows) >= 2:
        a, b = rows[-2], rows[-1]
        if now - b[0] <= datetime.timedelta(minutes=40) and datetime.timedelta(minutes=10) <= b[0] - a[0] <= datetime.timedelta(minutes=20) \
                and a[1] < lim["deaf"] and b[1] < lim["deaf"]:
            out["deaf"] = {"messages": int(b[1]), "minutes": 30}
    # drop: the last two whole hours, by day, each against the same hour a week before
    hours = _hours(rows)
    last = (rows[-1][0] - QUARTER).replace(minute=0, second=0, microsecond=0)
    if rows[-1][0].minute != 0:                    # the hour of the last sample is not over yet
        last -= datetime.timedelta(hours=1)
    pair, ratios = (last - datetime.timedelta(hours=1), last), []
    for h in pair:
        before = hours.get(h - datetime.timedelta(days=7))
        if h in hours and before and DAY_FROM <= h.hour < DAY_TO and now - h <= datetime.timedelta(hours=4):
            ratios.append(100.0 * hours[h] / before)
    if len(ratios) == 2 and all(r < lim["drop"] for r in ratios):
        out["drop"] = {"percent": int(round(max(ratios)))}
    # range: yesterday and the day before, each against the fourteen days before it
    days = _day_ranges(rows)
    today, shares, figures = now.date(), [], None
    for back in (2, 1):
        d = today - datetime.timedelta(days=back)
        before = [days[d - datetime.timedelta(days=i)] for i in range(1, RANGE_DAYS + 1) if d - datetime.timedelta(days=i) in days]
        if d in days and len(before) >= RANGE_DAYS_MIN:
            usual = statistics.median(before)
            if usual > 0:
                shares.append(100.0 * days[d] / usual)
                figures = (days[d], usual)
    if len(shares) == 2 and all(s < lim["range"] for s in shares):
        out["range"] = {"percent": int(round(max(shares))), "range_km": figures[0], "usual_km": figures[1]}
    return out


CLEAR_AFTER = 4              # a rule is over once four samples in a row (an hour) no longer show it


def step(active, found):
    """One sample later: `active` is {rule: quiet samples so far}, changed in place. Returns (started, ended): the
    rules that begin now, and True when the last of them has just ended. A rule that flickers (8 November 2026: under
    the limit, over it for one quarter hour, under it again) is one alert, not two."""
    started = [rule for rule in RULES if rule in found and rule not in active]
    for rule in found:
        active[rule] = 0
    had = bool(active)
    for rule in [k for k in active if k not in found]:
        active[rule] = int(active[rule]) + 1
        if active[rule] >= CLEAR_AFTER:
            del active[rule]
    return started, had and not active


def replay(rows, cfg=None):
    """Every time a rule would have started or all would have ended, over the whole file: [(when, rule, finding)], the
    rule "ok" for an end. For `telegram health check`: what the alert would have said of the days already kept."""
    out, active = [], {}
    for i, row in enumerate(rows):
        found = evaluate(rows[max(0, i - 24 * 96):i + 1], row[0], cfg)      # twenty-four days back is all a rule reads
        started, ended = step(active, found)
        for rule in started:
            out.append((row[0], rule, found[rule]))
        if ended:
            out.append((row[0], "ok", {}))
    return out
