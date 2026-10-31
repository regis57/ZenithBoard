# SPDX-License-Identifier: GPL-3.0-or-later
"""Telegram messages (0.99.6): what is worth a message and when, the words, the sending, and what never goes out.

The network is not called: a fake sender records what would have gone out, and a fake urlopen answers like Telegram's
Bot API does (its error shape: ok false, error_code, description, parameters.retry_after or migrate_to_chat_id). The
wall is not asked: the tests hand the planes in.
"""
import io
import json
import os
import shutil
import signal
import sys
import tempfile
import time
import unittest
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "flightinfo"))
import telegram  # noqa: E402
import social  # noqa: E402
import server  # noqa: E402

TOKEN = "123456789:AAH0123456789abcdefghijklmnopqrstuv"
CFG = {"SOCIAL_RADIUS_KM": "15", "LAT": "49.2", "LON": "6.2", "UNITS": "metric", "TELEGRAM": "1", "TELEGRAM_CROSSINGS": "1",
       "TELEGRAM_SQUAWKS": "1", "TELEGRAM_RULES": "all", "TELEGRAM_LANG": "", "SOCIAL_LANG": "", "SOCIAL_AREA": ""}
EZY = {"hex": "4ca7b1", "flight": "EZY17QZ", "registration": "G-EZWA", "type": "A320", "type_name": "AIRBUS A-320", "shape": "narrow",
       "airline": "easyJet", "airline_icao": "EZY", "alt_ft": 36000, "gs_kt": 450, "track": 120, "military": False,
       "on_ground": False, "distance_km": 7.3, "bearing": 212, "pending": []}
RCH = dict(EZY, hex="ae0001", flight="RCH123", registration="", type="C17", type_name="BOEING C-17A Globemaster III", shape="quad",
           airline="MILITARY", airline_icao=None, military=True)


def ac(hex_code="4ca7b1", squawk="7700", flight="EZY17QZ", emergency=None, lat=50.04, lon=8.56, seen=1):
    a = {"hex": hex_code, "flight": flight, "squawk": squawk, "seen": seen, "alt_baro": 12000, "gs": 300}
    if emergency:
        a["emergency"] = emergency
    if lat is not None:
        a["lat"], a["lon"] = lat, lon
    return a


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.sent = []
        self._ask_wall, self._ask_one, self._sleep = social.ask_wall, social.ask_wall_one, telegram.time.sleep
        self.planes = []
        social.ask_wall = lambda c, r: list(self.planes)
        social.ask_wall_one = lambda c, h: None
        telegram.time.sleep = lambda s: None
        self._files = dict(telegram.TEMPLATE_FILES)
        for k in telegram.TEMPLATE_FILES:
            telegram.TEMPLATE_FILES[k] = os.path.join(self.tmp, "telegram-%s.txt" % k)

    def tearDown(self):
        social.ask_wall, social.ask_wall_one, telegram.time.sleep = self._ask_wall, self._ask_one, self._sleep
        telegram.TEMPLATE_FILES.update(self._files)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def look(self, c, state, aircraft, squawks, outbox, now, ask=True, pending=None):
        telegram.one_look(c, state, aircraft, squawks, pending if pending is not None else {}, outbox, now, ask)


class SquawkTest(Base):
    def test_one_read_is_not_enough(self):
        sq, box, st = telegram.Squawks(), telegram.Outbox(), {}
        self.look(CFG, st, [ac()], sq, box, 1000.0, ask=False)
        self.assertEqual(box.items, [], "one reply decoded once can be a bad decode")
        self.look(CFG, st, [ac()], sq, box, 1005.0, ask=False)
        self.assertEqual([m["kind"] for m in box.items], ["squawk"])

    def test_its_own_emergency_status_confirms_at_once(self):
        sq, box, st = telegram.Squawks(), telegram.Outbox(), {}
        self.look(CFG, st, [ac(squawk="7600", emergency="nordo")], sq, box, 1000.0, ask=False)
        self.assertEqual(len(box.items), 1)
        self.assertIn("7600", box.items[0]["text"])

    def test_once_per_flight_and_code(self):
        sq, box, st = telegram.Squawks(), telegram.Outbox(), {}
        for t in range(0, 600, 5):                       # ten minutes of 7700
            self.look(CFG, st, [ac()], sq, box, 1000.0 + t, ask=False)
        self.assertEqual(len(box.items), 1)
        self.look(CFG, st, [ac(squawk="7600", emergency="nordo")], sq, box, 1700.0, ask=False)
        self.assertEqual(len(box.items), 2, "another code is new: the radio failed after the emergency")
        self.look(CFG, st, [ac(flight="EZY18QZ", emergency="general")], sq, box, 1800.0, ask=False)
        self.assertEqual(len(box.items), 3, "the same airframe as another flight is another event")

    def test_an_hour_later_it_is_new(self):
        sq, box, st = telegram.Squawks(), telegram.Outbox(), {}
        self.look(CFG, st, [ac(emergency="general")], sq, box, 1000.0, ask=False)
        telegram.prune(st, 1000.0 + telegram.SQUAWK_GAP_S + 10)
        self.look(CFG, st, [ac(emergency="general")], sq, box, 1000.0 + telegram.SQUAWK_GAP_S + 10, ask=False)
        self.assertEqual(len(box.items), 2)

    def test_anywhere_in_range_not_only_the_radius(self):
        sq, box, st = telegram.Squawks(), telegram.Outbox(), {}
        far = ac(emergency="general", lat=50.04, lon=8.56)     # about 200 km from the antenna at 49.2, 6.2
        self.assertGreater(server.haversine_km(49.2, 6.2, 50.04, 8.56), 150)
        self.look(CFG, st, [far], sq, box, 1000.0, ask=False)
        self.assertEqual(len(box.items), 1)

    def test_ordinary_codes_and_old_aircraft_are_not(self):
        sq, box, st = telegram.Squawks(), telegram.Outbox(), {}
        for t in (1000.0, 1010.0):
            self.look(CFG, st, [ac(squawk="1000"), ac(hex_code="3c6444", squawk="7000"), ac(hex_code="3c6445", emergency="general", seen=300),
                                ac(hex_code="~3c6446", emergency="general")], sq, box, t, ask=False)
        self.assertEqual(box.items, [])

    def test_off_means_off(self):
        sq, box, st = telegram.Squawks(), telegram.Outbox(), {}
        self.look(dict(CFG, TELEGRAM_SQUAWKS="0"), st, [ac(emergency="general")], sq, box, 1000.0, ask=False)
        self.assertEqual(box.items, [])

    def test_no_position_still_said(self):
        sq, box, st = telegram.Squawks(), telegram.Outbox(), {}
        self.look(CFG, st, [ac(emergency="unlawful", squawk="7500", lat=None)], sq, box, 1000.0, ask=False)
        self.assertEqual(len(box.items), 1)
        self.assertIn("7500", box.items[0]["text"])
        self.assertIn("position not known", box.items[0]["text"])


class CrossingTest(Base):
    def test_once_per_crossing(self):
        sq, box, st = telegram.Squawks(), telegram.Outbox(), {}
        self.planes = [EZY]
        for t in range(0, 900, 15):
            self.look(CFG, st, [], sq, box, 1000.0 + t)
        self.assertEqual([m["what"] for m in box.items], ["EZY17QZ"])
        self.planes = []
        self.look(CFG, st, [], sq, box, 1000.0 + 900 + telegram.CROSSING_GAP_S + 5)
        telegram.prune(st, 1000.0 + 900 + telegram.CROSSING_GAP_S + 5)
        self.planes = [EZY]
        self.look(CFG, st, [], sq, box, 1000.0 + 900 + telegram.CROSSING_GAP_S + 10)
        self.assertEqual(len(box.items), 2, "an hour outside the radius ends the crossing")

    def test_rules(self):
        sq, box, st = telegram.Squawks(), telegram.Outbox(), {}
        self.planes = [EZY, RCH]
        self.look(dict(CFG, TELEGRAM_RULES="military"), st, [], sq, box, 1000.0)
        self.assertEqual([m["what"] for m in box.items], ["RCH123"])

    def test_waits_for_a_route_still_on_its_way(self):
        sq, box, st, pend = telegram.Squawks(), telegram.Outbox(), {}, {}
        self.planes = [dict(EZY, pending=["route"])]
        self.look(CFG, st, [], sq, box, 1000.0, pending=pend)
        self.assertEqual(box.items, [])
        self.look(CFG, st, [], sq, box, 1000.0 + telegram.SETTLE_S + 1, pending=pend)
        self.assertEqual(len(box.items), 1, "past the wait it goes with what is known")

    def test_off_and_on_the_ground(self):
        sq, box, st = telegram.Squawks(), telegram.Outbox(), {}
        self.planes = [dict(EZY, on_ground=True)]
        self.look(CFG, st, [], sq, box, 1000.0)
        self.planes = [EZY]
        self.look(dict(CFG, TELEGRAM_CROSSINGS="0"), st, [], sq, box, 1015.0)
        self.assertEqual(box.items, [])


class WordsTest(Base):
    def test_crossing_default(self):
        text = telegram.fill("crossing", EZY, CFG, now=time.mktime((2026, 10, 30, 14, 5, 0, 0, 0, -1)))
        self.assertTrue(text.startswith("✈ EZY17QZ · easyJet"), text)
        self.assertIn("Airbus A320", text)
        self.assertIn("14:05", text)
        self.assertIn("https://globe.adsbexchange.com/?icao=4ca7b1", text)

    def test_squawk_default_says_the_code_its_meaning_and_where(self):
        text = telegram.fill("squawk", EZY, CFG, ac=ac(), code="7700")
        self.assertIn("Squawk 7700: General emergency", text.splitlines()[0])
        self.assertIn("Kelsterbach", text, "the town nearest the aircraft, from its own position")

    def test_never_the_receiver(self):
        for kind, code in (("crossing", None), ("squawk", "7700")):
            text = telegram.fill(kind, EZY, dict(CFG, LAT="49.21234", LON="6.17654"), ac=ac(), code=code)
            for leak in ("49.21", "6.17", "7.3", "7,3", "212", "SW", "south-west"):
                self.assertNotIn(leak, text, (kind, leak, text))
        for name, _ in telegram.TAG_HELP:
            self.assertNotIn(name, ("distance", "bearing", "lat", "lon", "position"))

    def test_near_far_from_any_town(self):
        L = social.post_lang.get("en")
        self.assertEqual(telegram.near_words(None, None, L, "metric"), "position not known")
        words = telegram.near_words(47.0, -30.0, L, "metric")          # mid-Atlantic
        self.assertRegex(words, "^\\d[\\d\u00a0 ,]*\u00a0km from .+ \\(.+\\)$")
        self.assertIn("NM from", telegram.near_words(47.0, -30.0, L, "aviation"))

    def test_the_messages_language(self):
        self.assertEqual(telegram.lang_of({"SOCIAL_LANG": "fr"}), "fr")
        self.assertEqual(telegram.lang_of({"SOCIAL_LANG": "fr", "TELEGRAM_LANG": "de"}), "de")
        self.assertEqual(telegram.lang_of({"TELEGRAM_LANG": "xx"}), "en")
        fr = telegram.fill("squawk", EZY, dict(CFG, SOCIAL_LANG="fr"), ac=ac(), code="7700")
        L = social.post_lang.get("fr")
        self.assertIn(L.t(telegram.EMERGENCY["7700"]), fr)

    def test_owner_template(self):
        with open(telegram.TEMPLATE_FILES["squawk"], "w", encoding="utf-8") as fh:
            fh.write("SOS {squawk} {meaning}\n[{from} → {to}]\n{flight}")
        text = telegram.fill("squawk", EZY, CFG, ac=ac(), code="7600")
        self.assertEqual(text, "SOS 7600 Radio failure (lost communications)\nEZY17QZ")
        with open(telegram.TEMPLATE_FILES["squawk"], "w", encoding="utf-8") as fh:
            fh.write("broken {nope}")
        self.assertIn("Squawk 7600", telegram.fill("squawk", EZY, CFG, ac=ac(), code="7600"), "an unusable template: the default")

    def test_template_problems(self):
        self.assertIsNone(telegram.template_problem("{flight}\n[{near}]\n{meaning}"))
        self.assertIn("unknown tag", telegram.template_problem("{distance}"))
        self.assertIn("too long", telegram.template_problem("x" * (telegram.TEMPLATE_MAX + 1)))

    def test_within_telegram_length(self):
        text = telegram.fill("crossing", EZY, CFG, template="{flight} " * 1000)
        self.assertLessEqual(len(text), telegram.MAX_TEXT)


class OutboxTest(Base):
    def test_squawk_first_spaced_and_counted(self):
        box, st, got = telegram.Outbox(), {}, []
        box.add("crossing", "c1", "EZY1", 1000.0)
        box.add("squawk", "s1", "RCH1 (7700)", 1001.0)
        n = box.flush({"TELEGRAM_BOT_TOKEN": TOKEN, "TELEGRAM_CHAT_ID": "-100"}, st, 1002.0, sender=lambda sec, text: got.append(text))
        self.assertEqual(got, ["s1", "c1"])
        self.assertEqual(n, 2)
        self.assertEqual(st["days"][social.day_of(1002.0)], {"squawk": 1, "crossing": 1})
        self.assertGreaterEqual(box.next_at, 1002.0 + telegram.SEND_EVERY_S)

    def test_429_waits_as_told(self):
        box, st = telegram.Outbox(), {}
        box.add("crossing", "c1", "EZY1", 1000.0)

        def busy(sec, text):
            raise telegram.TgError(429, "Too Many Requests: retry after 17", {"retry_after": 17})
        box.flush({"TELEGRAM_BOT_TOKEN": TOKEN, "TELEGRAM_CHAT_ID": "1"}, st, 1000.0, sender=busy)
        self.assertEqual(box.pause_until, 1017.0)
        self.assertEqual(len(box.items), 1, "kept for later")

    def test_a_supergroup_moves(self):
        box, st, sec, got = telegram.Outbox(), {}, {"TELEGRAM_BOT_TOKEN": TOKEN, "TELEGRAM_CHAT_ID": "-4001"}, []
        box.add("squawk", "s1", "x", 1000.0)

        def once(sec_, text):
            if sec_["TELEGRAM_CHAT_ID"] == "-4001":
                raise telegram.TgError(400, "Bad Request: group chat was upgraded to a supergroup chat", {"migrate_to_chat_id": -1001234})
            got.append(sec_["TELEGRAM_CHAT_ID"])
        box.flush(sec, st, 1000.0, sender=once)
        box.flush(sec, st, 1001.0, sender=once)
        self.assertEqual(got, ["-1001234"])

    def test_dropped_when_too_old(self):
        box, st = telegram.Outbox(), {}
        box.add("crossing", "c1", "EZY1", 1000.0)
        box.add("squawk", "s1", "RCH1", 1000.0)
        box.pause_until = 99999
        box.flush({}, st, 1000.0 + telegram.KEEP_S["crossing"] + 1)
        self.assertEqual([m["kind"] for m in box.items], ["squawk"], "an emergency is kept an hour, a crossing ten minutes")


class FakeHTTP(object):
    def __init__(self, status, body):
        self.status, self.body = status, body

    def __call__(self, req, timeout=None):
        self.req = req
        if self.status != 200:
            raise urllib.error.HTTPError(req.full_url, self.status, "x", {}, io.BytesIO(json.dumps(self.body).encode()))
        return io.BytesIO(json.dumps(self.body).encode())


class ApiTest(Base):
    def setUp(self):
        Base.setUp(self)
        self._urlopen = telegram.urllib.request.urlopen

    def tearDown(self):
        telegram.urllib.request.urlopen = self._urlopen
        Base.tearDown(self)

    def test_send_says_chat_text_and_no_preview(self):
        fake = FakeHTTP(200, {"ok": True, "result": {"message_id": 5}})
        telegram.urllib.request.urlopen = fake
        telegram.send({"TELEGRAM_BOT_TOKEN": TOKEN, "TELEGRAM_CHAT_ID": "-100123"}, "hello")
        body = json.loads(fake.req.data.decode())
        self.assertEqual(body, {"chat_id": "-100123", "text": "hello", "link_preview_options": {"is_disabled": True}})
        self.assertTrue(fake.req.full_url.endswith("/sendMessage"))

    def test_errors_carry_telegrams_words_never_the_token(self):
        telegram.urllib.request.urlopen = FakeHTTP(429, {"ok": False, "error_code": 429, "description": "Too Many Requests: retry after 9",
                                                         "parameters": {"retry_after": 9}})
        with self.assertRaises(telegram.TgError) as cm:
            telegram.send({"TELEGRAM_BOT_TOKEN": TOKEN, "TELEGRAM_CHAT_ID": "1"}, "x")
        self.assertEqual((cm.exception.code, cm.exception.params.get("retry_after")), (429, 9))

        def down(req, timeout=None):
            raise urllib.error.URLError("cannot reach %s" % req.full_url)
        telegram.urllib.request.urlopen = down
        with self.assertRaises(telegram.TgError) as cm:
            telegram.send({"TELEGRAM_BOT_TOKEN": TOKEN, "TELEGRAM_CHAT_ID": "1"}, "x")
        self.assertNotIn(TOKEN, cm.exception.text)
        self.assertIn("<token>", cm.exception.text)

    def test_chats_lists_who_wrote(self):
        telegram.urllib.request.urlopen = FakeHTTP(200, {"ok": True, "result": [
            {"update_id": 1, "message": {"chat": {"id": 42, "type": "private", "first_name": "Régis", "last_name": "H"}, "text": "/start"}},
            {"update_id": 2, "my_chat_member": {"chat": {"id": -1009, "type": "supergroup", "title": "Avions\tde la famille"}}}]})
        sec_file = os.path.join(self.tmp, "telegram.env")
        with open(sec_file, "w") as fh:
            fh.write('TELEGRAM_BOT_TOKEN="%s"\n' % TOKEN)
        old, telegram.SECRETS_FILE = telegram.SECRETS_FILE, sec_file
        out = io.StringIO()
        try:
            sys.stdout, keep = out, sys.stdout
            telegram.cmd_chats()
        finally:
            sys.stdout, telegram.SECRETS_FILE = keep, old
        self.assertEqual(out.getvalue().splitlines(), ["-1009\tsupergroup\tAvions de la famille", "42\tprivate\tRégis H"])


class NothingFromTheTokenFileTest(Base):
    def test_status_and_hello_print_nothing_read_from_it(self):
        """CodeQL #85-87 (0.99.6): what telegram.env holds, the chat's name and id included, never reaches the journal."""
        sec_file = os.path.join(self.tmp, "telegram.env")
        with open(sec_file, "w") as fh:
            fh.write('TELEGRAM_BOT_TOKEN="%s"\nTELEGRAM_CHAT_ID="-100777"\nTELEGRAM_CHAT_TITLE="Avions secrets"\n' % TOKEN)
        old, telegram.SECRETS_FILE = telegram.SECRETS_FILE, sec_file
        old_send = telegram.send
        telegram.send = lambda sec, text: None
        out = io.StringIO()
        try:
            sys.stdout, keep = out, sys.stdout
            telegram.cmd_status()
            telegram.cmd_hello()
        finally:
            sys.stdout, telegram.SECRETS_FILE, telegram.send = keep, old, old_send
        for leak in (TOKEN, "-100777", "Avions secrets"):
            self.assertNotIn(leak, out.getvalue())
        self.assertIn("set up", out.getvalue())


class BlueskyNeverTest(unittest.TestCase):
    def test_squawks_go_to_telegram_only(self):
        with open(os.path.join(HERE, "..", "flightinfo", "social.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("telegram", src.lower(), "the Bluesky service knows nothing of the emergency messages")
        self.assertNotIn("EMERGENCY", src)


class Stop(Exception):
    pass


class Halt(BaseException):                                # not caught by the service's own `except Exception`
    pass


class RunTest(Base):
    """Review B8 (0.99.16): the service itself, a few loops of it, with the clock, the decoder, the wall and Telegram
    stood in for."""

    def setUp(self):
        Base.setUp(self)
        self.clock = [1800000000.0]
        self.reads = []                                   # what aircraft.json says at each loop
        self.loops = 0
        self.stop_after = 2
        self.ids = []
        self.sec = {"TELEGRAM_BOT_TOKEN": TOKEN, "TELEGRAM_CHAT_ID": "-100555"}
        keep = {n: getattr(telegram, n) for n in ("STATE_DIR", "cfg", "secrets", "send")}
        self.addCleanup(lambda: [setattr(telegram, n, v) for n, v in keep.items()])
        self.addCleanup(setattr, social, "read_aircraft", social.read_aircraft)
        self.addCleanup(setattr, telegram.time, "time", telegram.time.time)
        self.addCleanup(signal.signal, signal.SIGTERM, signal.getsignal(signal.SIGTERM))
        telegram.STATE_DIR = os.path.join(self.tmp, "state")
        telegram.cfg = lambda: dict(CFG)
        telegram.secrets = lambda: dict(self.sec)         # a fresh read of telegram.env each time, as on the Pi
        telegram.send = lambda sec, text: self.ids.append(sec["TELEGRAM_CHAT_ID"])
        social.read_aircraft = lambda c: self.reads[min(self.loops, len(self.reads) - 1)] if self.reads else []
        telegram.time.time = lambda: self.clock[0]

        def sleep(sec):
            if sec == telegram.READ_EVERY_S:
                self.loops += 1
                if self.loops >= self.stop_after:
                    raise Stop()
                self.clock[0] += telegram.ASK_EVERY_S     # every loop asks the wall
            else:
                self.clock[0] += sec
        telegram.time.sleep = sleep

    def run_service(self):
        import contextlib
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises((Stop, SystemExit)):
                telegram.cmd_run()
        return out.getvalue()

    def saved(self):
        with open(os.path.join(telegram.STATE_DIR, "state.json"), encoding="utf-8") as fh:
            return json.load(fh)

    def test_what_a_pass_sent_is_saved_at_once(self):
        # sent with the queue then empty, it waited up to a minute to be written down: a restart in that minute sent
        # the same crossing and the same squawk again
        self.reads = [[], [ac(hex_code="3c0001", emergency="general")]]
        self.planes_at = None
        orig = social.ask_wall
        social.ask_wall = lambda c, r: [EZY] if self.loops >= 1 else []
        self.addCleanup(setattr, social, "ask_wall", orig)
        self.run_service()
        self.assertEqual(len(self.ids), 2, "the squawk and the crossing went out in the second loop")
        st = self.saved()
        self.assertIn(EZY["hex"], st.get("posted", {}))
        self.assertIn("3c0001:7700", st.get("squawks", {}))

    def test_stopped_it_saves_first(self):
        # systemd stops the service with SIGTERM; what was already decided is written down before it exits
        self.reads = [[ac(hex_code="3c0001", emergency="general")]]

        def sent_then_stopped(sec, text):
            self.ids.append(sec["TELEGRAM_CHAT_ID"])
            handler = signal.getsignal(signal.SIGTERM)
            if not callable(handler):
                raise Halt("the service does not handle SIGTERM")     # what systemd's stop would do: no saving
            handler(signal.SIGTERM, None)
        telegram.send = sent_then_stopped
        self.stop_after = 99
        self.run_service()
        self.assertIn("3c0001:7700", self.saved().get("squawks", {}))

    def test_a_supergroup_stays_moved_after_each_read_of_the_secrets(self):
        # the new id was put in the dict the next read of telegram.env replaced, fifteen seconds later
        self.sec["TELEGRAM_CHAT_ID"] = "-4001"
        self.reads = [[ac(hex_code="3c0001", emergency="general")], [ac(hex_code="3c0002", emergency="general")],
                      [ac(hex_code="3c0003", emergency="general")]]
        refusals = []

        def sender(sec, text):
            if sec["TELEGRAM_CHAT_ID"] == "-4001":
                refusals.append(1)
                raise telegram.TgError(400, "Bad Request: group chat was upgraded to a supergroup chat", {"migrate_to_chat_id": -1001234})
            self.ids.append(sec["TELEGRAM_CHAT_ID"])
        telegram.send = sender
        self.stop_after = 4
        out = self.run_service()
        self.assertEqual(len(refusals), 1, "refused once, then the new id")
        self.assertEqual(self.ids, ["-1001234"] * 3)
        for leak in ("-4001", "1001234", TOKEN):
            self.assertNotIn(leak, out, "never in the journal")
        self.assertNotIn("1001234", json.dumps(self.saved()))

    def test_only_the_exact_old_id_is_followed(self):
        box = telegram.Outbox()
        box.moved = ("-4001", "-1001234")
        self.assertEqual(box.follow_move({"TELEGRAM_CHAT_ID": "-4001"})["TELEGRAM_CHAT_ID"], "-1001234")
        self.assertEqual(box.follow_move({"TELEGRAM_CHAT_ID": "-777"})["TELEGRAM_CHAT_ID"], "-777", "a chat set up since is kept")


class StatusWeekTest(Base):
    def test_last_seven_days_are_today_and_the_six_before(self):
        # review B8 (0.99.16): every stored day was added up, eight of them in the morning
        import contextlib
        import datetime
        now = 1800000000.0
        today = datetime.date.fromtimestamp(now)
        st = {"days": {(today - datetime.timedelta(days=i)).isoformat(): {"crossing": 1} for i in range(10)}}
        keep = (telegram.STATE_DIR, telegram.SECRETS_FILE, telegram.time.time)
        telegram.STATE_DIR, telegram.SECRETS_FILE = os.path.join(self.tmp, "state"), os.path.join(self.tmp, "none.env")
        telegram.time.time = lambda: now
        out = io.StringIO()
        try:
            telegram.save_state(st)
            with contextlib.redirect_stdout(out):
                telegram.cmd_status()
        finally:
            telegram.STATE_DIR, telegram.SECRETS_FILE, telegram.time.time = keep
        self.assertIn("Sent today: 1 crossing(s), 0 squawk(s); last 7 days: 7 and 0", out.getvalue())


if __name__ == "__main__":
    unittest.main()
