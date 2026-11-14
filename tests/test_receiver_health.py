"""1.2: is the receiver still hearing as it did? The three rules of flightinfo/receiver_health.py, their figures
measured on the owner's thirty days (16 October to 14 November 2026), and what the Telegram service says of them."""
import contextlib
import datetime
import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "flightinfo"))
import receiver_health as rh  # noqa: E402
import telegram  # noqa: E402

D = datetime.datetime
Q = datetime.timedelta(minutes=15)


def month(start=D(2026, 10, 16, 0, 15), days=30, messages=None, far=None):
    """Quarter-hour samples like the owner's: busy by day, quiet by night, a range near 290 km."""
    rows, t = [], start
    for i in range(days * 96):
        hour = (t - Q).hour
        m = 700000 if 7 <= hour < 22 else 150000
        f = 290.0
        if messages:
            m = messages(t, m)
        if far:
            f = far(t, f)
        rows.append((t, float(m), float(f)))
        t += Q
    return rows


class RulesTest(unittest.TestCase):
    def test_a_normal_month_says_nothing(self):
        rows = month()
        self.assertEqual(rh.replay(rows), [])
        self.assertEqual(rh.evaluate(rows, rows[-1][0]), {})

    def test_deaf_two_quarter_hours_in_a_row_at_any_hour(self):
        night = D(2026, 11, 8, 3, 0)
        quiet = {night + Q: 12, night + 2 * Q: 374}
        rows = month(messages=lambda t, m: quiet.get(t, m))
        rows = [r for r in rows if r[0] <= night + 2 * Q]
        self.assertEqual(rh.evaluate(rows[:-1], rows[-2][0]), {}, "one quiet quarter hour is not enough")
        self.assertEqual(rh.evaluate(rows, rows[-1][0]), {"deaf": {"messages": 374, "minutes": 30}})
        self.assertEqual(rh.evaluate(rows, rows[-1][0] + datetime.timedelta(hours=2)), {}, "old samples say nothing of now")

    def test_the_quietest_normal_night_is_not_deaf(self):
        rows = month(messages=lambda t, m: 4320 if (t - Q).hour == 3 else m)      # the least of the owner's other nights
        self.assertEqual(rh.replay(rows), [])

    def test_drop_by_day_two_hours_under_forty_percent_of_the_week_before(self):
        day = D(2026, 11, 10)
        cut = lambda share, hours: (lambda t, m: m * share if (t - Q).date() == day.date() and (t - Q).hour in hours else m)
        rows = month(messages=cut(0.35, (14, 15)))
        at = day.replace(hour=16)
        self.assertEqual(rh.evaluate([r for r in rows if r[0] <= at], at), {"drop": {"percent": 35}})
        one = month(messages=cut(0.35, (14,)))
        self.assertEqual(rh.evaluate([r for r in one if r[0] <= at], at), {}, "one hour is not enough")
        mild = month(messages=cut(0.55, (14, 15)))          # the lowest hour of the owner's month by day: 55 %
        self.assertEqual(rh.evaluate([r for r in mild if r[0] <= at], at), {})
        night = month(messages=cut(0.11, (2, 3)))           # by night the owner's ratio went down to 0.11 with nothing wrong
        at = day.replace(hour=4)
        self.assertEqual(rh.evaluate([r for r in night if r[0] <= at], at), {})

    def test_a_month_of_fewer_aircraft_is_not_an_alert(self):
        # the owner's month: the messages fell by 36 % with the same receiver, week after week
        first = D(2026, 10, 16)
        rows = month(messages=lambda t, m: m * (1 - 0.36 * min(1.0, (t - first).days / 29.0)))
        self.assertEqual(rh.replay(rows), [])

    def test_range_two_days_under_eighty_five_percent_of_the_fortnight(self):
        weak = D(2026, 11, 12).date()
        rows = month(far=lambda t, f: f * 0.8 if (t - Q).date() >= weak else f)
        at = D(2026, 11, 14, 0, 15)
        got = rh.evaluate([r for r in rows if r[0] <= at], at)
        self.assertEqual(got, {"range": {"percent": 80, "range_km": 232.0, "usual_km": 290.0}})
        at = D(2026, 11, 13, 0, 15)
        self.assertEqual(rh.evaluate([r for r in rows if r[0] <= at], at), {}, "one day is not enough")
        slight = month(far=lambda t, f: f * 0.94 if (t - Q).date() >= weak else f)     # the least of the owner's days: 94 %
        self.assertEqual(rh.replay(slight), [])

    def test_a_flicker_is_one_alert_and_the_end_is_said_once(self):
        # 8 November 2026 on the real Pi: 12, 374, a quarter hour over the limit, 878, 1 709, then normal
        base = D(2026, 11, 8, 3, 15)
        quiet = {base: 12, base + Q: 374, base + 3 * Q: 878, base + 4 * Q: 1709}
        events = rh.replay(month(messages=lambda t, m: quiet.get(t, m)))
        self.assertEqual([(str(w), r) for w, r, f in events], [("2026-11-08 03:30:00", "deaf"), ("2026-11-08 05:15:00", "ok")])

    def test_the_thresholds_are_settings_within_reason(self):
        self.assertEqual(rh.limits({}), {"deaf": 2000, "drop": 40, "range": 85})
        self.assertEqual(rh.limits({"HEALTH_DEAF_MESSAGES": "500", "HEALTH_DROP_PERCENT": "30", "HEALTH_RANGE_PERCENT": "70"}), {"deaf": 500, "drop": 30, "range": 70})
        self.assertEqual(rh.limits({"HEALTH_DEAF_MESSAGES": "0", "HEALTH_DROP_PERCENT": "100", "HEALTH_RANGE_PERCENT": "x"}), {"deaf": 2000, "drop": 40, "range": 85})

    def test_the_file_is_read_whatever_is_in_it(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        path = os.path.join(tmp, "stats.csv")
        with open(path, "w") as fh:
            fh.write("when,messages,farthest_km,aircraft_pos,aircraft_seen\n2026-11-14 23:15,278778,278,25,2211\nrubbish\n2026-11-14 23:00,nan,273,21,2206\n"
                     "2026-11-14 22:45,-5,277,26,2196\n2026-13-99 00:00,1,1\n2026-11-14 22:30,212864,277\n\x00\x00\n")
        self.assertEqual(rh.read_rows(path), [(D(2026, 11, 14, 22, 30), 212864.0, 277.0), (D(2026, 11, 14, 23, 15), 278778.0, 278.0)])
        self.assertEqual(rh.read_rows(os.path.join(tmp, "none.csv")), [])
        self.assertEqual(rh.evaluate([], D(2026, 11, 14)), {})
        self.assertEqual(rh.replay([]), [])


class ServiceTest(unittest.TestCase):
    """What the Telegram service does with the rules: off by default, one message when a rule starts, one at the end."""
    CFG = {"TELEGRAM": "1", "TELEGRAM_HEALTH": "1", "UNITS": "metric", "SOCIAL_LANG": "", "TELEGRAM_LANG": ""}

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.path = os.path.join(self.tmp, "stats.csv")

    def write(self, rows, stamp):
        with open(self.path, "w") as fh:
            fh.write("when,messages,farthest_km,aircraft_pos,aircraft_seen\n")
            for when, m, f in rows:
                fh.write("%s,%d,%d,20,2000\n" % (when.strftime("%Y-%m-%d %H:%M"), m, f))
        os.utime(self.path, (stamp, stamp))

    def look(self, c, state, box, when, stamp):
        with contextlib.redirect_stdout(io.StringIO()):
            telegram.health_look(c, state, box, when.timestamp(), self.path)

    def test_off_by_default_and_nothing_is_read(self):
        self.assertEqual(telegram.DEFAULTS["TELEGRAM_HEALTH"], "0")
        base = D(2026, 11, 8, 3, 15)
        rows = [r for r in month(messages=lambda t, m: 12 if t >= base else m) if r[0] <= base + Q]
        self.write(rows, 1000)
        box, st = telegram.Outbox(), {}
        self.look(dict(self.CFG, TELEGRAM_HEALTH="0"), st, box, base + Q, 1000)
        self.assertEqual((box.items, st), ([], {}))

    def test_one_message_when_it_starts_one_when_it_ends_none_in_between(self):
        base = D(2026, 11, 8, 3, 15)
        allrows = month(messages=lambda t, m: 12 if base <= t <= base + 4 * Q else m)
        box, st, stamp = telegram.Outbox(), {}, 1000
        for i in range(-2, 14):
            when = base + i * Q
            stamp += 900
            self.write([r for r in allrows if r[0] <= when], stamp)
            self.look(self.CFG, st, box, when, stamp)
            self.look(self.CFG, st, box, when, stamp)          # asked again before the next sample: the file has not changed
        self.assertEqual([m["kind"] for m in box.items], ["health", "health"])
        self.assertIn("Receiver alert: almost nothing heard for 30 minutes (12 messages", box.items[0]["text"])
        self.assertIn("The receiver hears normally again.", box.items[1]["text"])
        self.assertEqual(st["health"]["active"], {})

    def test_a_health_message_is_not_counted_as_a_crossing_and_goes_after_an_emergency(self):
        box, st, got = telegram.Outbox(), {}, []
        box.add("crossing", "c", "EZY1", 1000.0); box.add("health", "h", "the receiver (deaf)", 1001.0); box.add("squawk", "s", "RCH1 (7700)", 1002.0)
        self.addCleanup(setattr, telegram.time, "sleep", telegram.time.sleep); telegram.time.sleep = lambda s: None
        with contextlib.redirect_stdout(io.StringIO()):
            box.flush({"TELEGRAM_BOT_TOKEN": "1:x", "TELEGRAM_CHAT_ID": "1"}, st, 1003.0, sender=lambda sec, text: got.append(text))
        self.assertEqual(got, ["s", "h", "c"])
        self.assertEqual(st["days"][telegram.social.day_of(1003.0)], {"squawk": 1, "crossing": 1})

    def test_no_statistics_no_message_and_no_failure(self):
        box, st = telegram.Outbox(), {}
        self.look(self.CFG, st, box, D(2026, 11, 8), 0)
        self.assertEqual(box.items, [])

    def test_the_words_in_the_messages_language_and_units(self):
        fr = dict(self.CFG, TELEGRAM_LANG="fr")
        self.assertIn("Alerte récepteur : presque rien entendu depuis 30 minutes (374 messages", telegram.health_text("deaf", {"messages": 374, "minutes": 30}, fr))
        self.assertIn("31 % des messages", telegram.health_text("drop", {"percent": 31}, fr))
        nm = telegram.health_text("range", {"percent": 78, "range_km": 214.0, "usual_km": 276.0}, dict(self.CFG, TELEGRAM_UNITS="aviation"))
        self.assertIn("78 % of its usual (116 NM against 149 NM)", nm)
        for lang in telegram.post_lang.LANGS:
            for rule, f in (("deaf", {"messages": 374, "minutes": 30}), ("drop", {"percent": 31}), ("range", {"percent": 78, "range_km": 214.0, "usual_km": 276.0}), ("ok", {})):
                text = telegram.health_text(rule, f, dict(self.CFG, TELEGRAM_LANG=lang))
                self.assertNotIn("{", text, "%s %s" % (lang, rule))
                if lang != "en":
                    self.assertNotIn("Receiver alert", text, "%s %s is not translated" % (lang, rule))

    def test_the_check_replays_the_days_kept_and_sends_nothing(self):
        base = D(2026, 11, 8, 3, 15)
        quiet = {base: 12, base + Q: 374}
        self.write(month(messages=lambda t, m: quiet.get(t, m)), 1000)
        self.addCleanup(setattr, telegram, "STATS_FILE", telegram.STATS_FILE)
        self.addCleanup(setattr, telegram, "cfg", telegram.cfg)
        telegram.STATS_FILE, telegram.cfg = self.path, lambda: dict(self.CFG)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(telegram.cmd_health_check(), 0)
        text = out.getvalue()
        self.assertIn("2026-11-08 03:30", text)
        self.assertIn("under 2000 messages", text)
        self.assertIn("The receiver hears normally again.", text)
        telegram.STATS_FILE = os.path.join(self.tmp, "none.csv")
        with contextlib.redirect_stdout(io.StringIO()) as none:
            self.assertEqual(telegram.cmd_health_check(), 1)
        self.assertIn("sudo zenithboard stats on", none.getvalue())


if __name__ == "__main__":
    unittest.main()
