# SPDX-License-Identifier: GPL-3.0-or-later
"""Social sharing (0.18.0): the words, the choice, the track, the picture, and the two networks' requests.

The networks are not called: a fake urlopen records what would have been sent and answers like the real
services do (shapes copied from the Bluesky and Mastodon API documentation). The renderer is real (node).
"""
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "flightinfo"))
import social  # noqa: E402

EZY = {"hex": "4071f1", "flight": "EZY1234 ", "registration": "G-UZHA", "type": "A20N", "type_name": "AIRBUS A-320neo",
       "shape": "narrow", "military": False, "airline_icao": "EZY", "airline": "easyJet", "alt_ft": 37000, "on_ground": False,
       "gs_kt": 320, "track": 110, "distance_km": 12.3, "bearing": 45,
       "route": {"from": {"iata": "EDI", "city": "Edinburgh", "name": "Edinburgh Airport"}, "to": {"iata": "BSL", "city": "Saint-Louis", "name": "EuroAirport"}}}
BELUGA = {"hex": "3c0001", "flight": "BGA113J", "registration": "F-GXLH", "type": "A337", "type_name": "AIRBUS A-330-743 Beluga XL",
          "shape": "wide", "military": False, "airline": None, "alt_ft": 32000, "on_ground": False, "track": 250, "distance_km": 32}
HELI = {"hex": "3d0001", "flight": "", "registration": "D-HABC", "type": "EC45", "type_name": "AIRBUS HELICOPTERS H145",
        "shape": "heli", "military": False, "airline": None, "alt_ft": 1500, "on_ground": False, "track": 10, "distance_km": 4}
KC135 = {"hex": "ae0001", "flight": "", "registration": None, "type": "K35R", "type_name": "BOEING KC-135R Stratotanker",
         "shape": "quad", "military": True, "airline": "MILITARY", "alt_ft": 25000, "on_ground": False, "track": 90, "distance_km": 40}
NOTHING = {"hex": "ffffff", "flight": "", "registration": None, "type": None, "type_name": None, "shape": "narrow",
           "military": False, "airline": None, "alt_ft": 30000, "on_ground": False, "track": 0, "distance_km": 20}
CFG = dict(social.DEFAULTS, UNITS="metric", THEME="amber", FLAGS="1", SOCIAL_AREA="over Luxembourg")


def trace(n=20, start=None):
    t0 = start or (time.time() - n * 5)
    return [[49.60 + i * 0.001, 6.13 + i * 0.0015, 37000 - i * 50, t0 + i * 5] for i in range(n)]


class WordsTest(unittest.TestCase):
    # 0.18.3: the post starts with the flight ("Flight Etihad #ETD11K") and ends with the place ("above Trémery");
    # no icon in front, the callsign a hashtag so the flight can be followed
    def test_airline_with_route(self):
        self.assertEqual(social.post_text(EZY, CFG).split("\n")[0],
                         "Flight easyJet #EZY1234 · Airbus A320neo · Edinburgh → Saint-Louis · 11 280 m over Luxembourg")

    def test_starts_with_the_flight_and_ends_above_the_place(self):
        t = social.post_text(EZY, dict(CFG, SOCIAL_AREA="Trémery")).split("\n")[0]
        self.assertTrue(t.startswith("Flight easyJet #EZY1234 · "), t)
        self.assertTrue(t.endswith(" above Trémery"), t)

    def test_unknown_airline_shows_callsign_and_model(self):
        self.assertEqual(social.post_text(BELUGA, CFG).split("\n")[0], "Flight #BGA113J · Airbus A330-743 Beluga XL · F-GXLH · 9 750 m over Luxembourg")

    def test_a_registration_used_as_callsign_is_an_aircraft_not_a_flight(self):
        p = dict(BELUGA, flight="FGXLH", type_name="CESSNA 172", type="C172")
        self.assertEqual(social.post_text(p, dict(CFG, SOCIAL_AREA="Trémery")).split("\n")[0], "Aircraft F-GXLH · Cessna 172 · 9 750 m above Trémery")

    def test_only_airline_callsigns_become_hashtags(self):
        self.assertEqual(social.hashtag_callsign("ETD11K"), "#ETD11K")
        self.assertEqual(social.hashtag_callsign("DEABC"), "DEABC")
        self.assertEqual(social.hashtag_callsign("SAMU57"), "SAMU57")
        self.assertEqual(social.hashtag_callsign(""), "")

    def test_helicopter(self):
        t = social.post_text(HELI, CFG)
        self.assertTrue(t.startswith("Helicopter D-HABC · Airbus Helicopters H145 · low over Luxembourg"), t)
        self.assertIn("#helicopter", t)

    def test_military_without_callsign(self):
        t = social.post_text(KC135, CFG)
        self.assertTrue(t.startswith("Military flight · Boeing KC-135R Stratotanker · 7 620 m over Luxembourg"), t)
        self.assertIn("#military", t)
        self.assertTrue(social.post_text(dict(KC135, flight="RCH123"), CFG).startswith("Military flight #RCH123 · "))

    def test_nothing_known_is_not_worth_a_post(self):
        self.assertFalse(social.known(NOTHING))
        self.assertTrue(social.known(EZY))

    def test_imperial_and_no_area(self):
        c = dict(CFG, UNITS="imperial", SOCIAL_AREA="")
        self.assertIn("37 000 ft", social.post_text(EZY, c))
        self.assertNotIn("over", social.post_text(EZY, c))

    def test_text_never_carries_distance_or_bearing(self):
        for p in (EZY, BELUGA, HELI, KC135):
            t = social.post_text(p, CFG)
            self.assertNotIn("km", t.replace("km/h", ""))
            self.assertNotIn("NE", t.split("\n")[0].replace("NEO", "").replace("Beluga", ""))

    def test_a_range_record_is_said_without_the_figure(self):
        # rounded DOWN to 50 km: enough to tell a record, not enough to draw a circle around the antenna
        t = social.post_text(dict(EZY, distance_km=332.4), CFG, why="farthest")
        self.assertTrue(t.startswith("Flight easyJet #EZY1234 · "), t)
        self.assertIn("· 11 280 m · range record for 30 days: over 300 km out", t)
        self.assertNotIn("332", t)
        # far from overhead: the place is where it was seen from, not what it flew above
        t = social.post_text(dict(EZY, distance_km=332.4), dict(CFG, SOCIAL_AREA="Trémery"), why="farthest").split("\n")[0]
        self.assertTrue(t.endswith("range record for 30 days: over 300 km out, seen from Trémery"), t)
        self.assertNotIn("above", t)
        self.assertEqual(social.range_words(51), "over 50 km out")
        self.assertEqual(social.range_words(149.9), "over 100 km out")

    def test_a_bare_place_name_reads_above(self):
        # reported from the real Pi: "1 750 m Trémery"; 0.18.3 asked for "above"
        self.assertEqual(social.area_words({"SOCIAL_AREA": "Trémery"}), "above Trémery")
        self.assertEqual(social.area_words({"SOCIAL_AREA": "near Metz"}), "near Metz")
        self.assertEqual(social.area_words({"SOCIAL_AREA": "over the Moselle"}), "over the Moselle")
        self.assertEqual(social.area_words({"SOCIAL_AREA": "  "}), "")
        self.assertIn("1 750 m above Trémery", social.post_text(dict(EZY, alt_ft=5740), dict(CFG, SOCIAL_AREA="Trémery")))

    def test_de_havilland(self):
        # reported from the real Pi: "DE Havilland DHC-8-400 Dash 8"
        self.assertEqual(social.nice_type({"type_name": "DE HAVILLAND DHC-8-400 Dash 8"}), "De Havilland DHC-8-400 Dash 8")

    def test_alt_text(self):
        a = social.alt_text(EZY, CFG, trace(20))
        self.assertIn("EZY1234", a); self.assertIn("easyJet", a); self.assertIn("from Edinburgh to Saint-Louis", a)
        self.assertIn("registration G-UZHA", a)
        self.assertTrue(a.endswith("north up."), a)


OLD = time.time() - 10 * 86400                     # a service that has watched for ten days


def warm(**kw):
    s = {"since": social.day_of(OLD), "types": {}, "far": {}, "posted": {}}
    s.update(kw)
    return s


class ChoiceTest(unittest.TestCase):
    def setUp(self):
        self.tracks = social.Tracks()
        now = time.time()
        for p in (EZY, BELUGA, HELI, KC135, NOTHING):
            for pt in trace(8, now - 40):
                self.tracks.feed([{"hex": p["hex"], "lat": pt[0], "lon": pt[1], "alt_baro": pt[2], "seen_pos": 0}], pt[3])

    def test_rules_rank_military_over_an_airliner(self):
        rules = {"military", "helicopter", "heavy", "rare"}
        st = warm(types={"A20N": {"a1": social.day_of(time.time()), "a2": social.day_of(time.time()), "a3": social.day_of(time.time())}})
        best = social.choose([EZY, KC135, HELI], self.tracks, rules, st, time.time())
        self.assertEqual(best[2]["hex"], KC135["hex"]); self.assertEqual(best[1], "military")

    def test_rare_counts_aircraft_not_looks(self):
        # 0.18.0 counted a type at every 15-second look, so an aircraft visible for thirty seconds had already been
        # counted three times when its track was long enough: "rare" never fired in the service. One aircraft, many looks:
        st, now = warm(), time.time()
        for i in range(12):
            social.note_types(st, [EZY], now + i * 15)
        self.assertEqual(social.others_of_type(st, EZY, now), 0)
        self.assertEqual(social.interest(EZY, {"rare"}, st, now)[1], "rare")

    def test_a_common_type_is_not_rare(self):
        st, now = warm(), time.time()
        for h in ("aa0001", "aa0002", "aa0003", "aa0004", "aa0005"):
            social.note_types(st, [dict(EZY, hex=h)], now)
        self.assertEqual(len(st["types"]["A20N"]), social.KEEP_PER_TYPE, "only the latest few are kept per type")
        self.assertEqual(social.interest(EZY, {"rare"}, st, now), (0, None))
        self.assertEqual(social.interest(dict(EZY, hex="aa0001"), {"rare"}, st, now), (0, None))

    def test_two_others_in_thirty_days_is_still_rare_three_is_not(self):
        st, now = warm(), time.time()
        social.note_types(st, [dict(EZY, hex="bb0001"), dict(EZY, hex="bb0002")], now - 5 * 86400)
        self.assertEqual(social.interest(EZY, {"rare"}, st, now)[1], "rare")
        social.note_types(st, [dict(EZY, hex="bb0003")], now - 86400)
        self.assertEqual(social.interest(EZY, {"rare"}, st, now), (0, None))

    def test_no_rare_and_no_record_before_three_days_of_history(self):
        now = time.time()
        fresh = {"since": social.day_of(now), "types": {}, "far": {}}
        self.assertFalse(social.warmed(fresh, now))
        self.assertEqual(social.interest(EZY, {"rare"}, fresh, now), (0, None))
        self.assertTrue(social.warmed(fresh, now + 3 * 86400 + 60))

    def test_the_0_18_0_history_is_dropped(self):
        st = social.prune_state({"types": {"A20N": {"2026-10-17": 40}, "DH8D": {"4d00c6": social.day_of(time.time())}},
                                 "farthest_day": "2026-10-17", "farthest_km": 12}, time.time())
        self.assertNotIn("A20N", st["types"]); self.assertIn("DH8D", st["types"])
        self.assertNotIn("farthest_km", st)

    def test_nothing_known_never_posts_even_under_any(self):
        self.assertIsNone(social.choose([NOTHING], self.tracks, {"any"}, warm(), time.time()))

    def test_already_posted_and_no_track_are_skipped(self):
        self.assertIsNone(social.choose([EZY], self.tracks, {"any"}, warm(posted={EZY["hex"]: time.time()}), time.time()))
        self.assertIsNone(social.choose([EZY], social.Tracks(), {"any"}, warm(), time.time()))

    def test_heavy_by_code_or_shape(self):
        self.assertEqual(social.interest(BELUGA, {"heavy"}, warm())[1], "heavy")
        self.assertEqual(social.interest(KC135, {"heavy"}, warm())[1], "heavy")     # quad shape
        self.assertEqual(social.interest(EZY, {"heavy"}, warm()), (0, None))


class RangeRecordTest(unittest.TestCase):
    """0.18.0: "farthest" compared an aircraft with a record it had just set itself, and only looked inside the
    sharing radius (15 km by default) for something over 50 km: it could never fire."""

    def setUp(self):
        self.c = dict(CFG, LAT="49.20", LON="6.20", SOCIAL_RULES="farthest", SOCIAL_RADIUS_KM="15")
        self.tracks = social.Tracks()
        self.far = {"hex": "4b1801", "flight": "SWR18", "type": "A21N", "type_name": "AIRBUS A-321neo", "airline": "Swiss",
                    "registration": "HB-JPA", "shape": "narrow", "alt_ft": 38000, "on_ground": False, "track": 90, "distance_km": 210}
        now = time.time()
        # its track: the collector saw it for a minute
        for pt in trace(12, now - 60):
            self.tracks.feed([{"hex": "4b1801", "lat": pt[0], "lon": pt[1], "alt_baro": 38000, "seen_pos": 0}], pt[3])
        self.old = (social.ask_wall, social.ask_wall_one)
        social.ask_wall = lambda c, r: []                       # nothing inside the sharing radius
        social.ask_wall_one = lambda c, h: dict(self.far) if h == "4b1801" else None
        self.addCleanup(setattr, social, "ask_wall", self.old[0]); self.addCleanup(setattr, social, "ask_wall_one", self.old[1])
        # 210 km from the receiver at 49.20 N 6.20 E: due east, ~2.86 degrees of longitude
        self.sky = [{"hex": "4b1801", "lat": 49.20, "lon": 6.20 + 210 / (111.32 * 0.6534), "seen_pos": 1}]

    def test_a_new_thirty_day_record_is_a_candidate_once(self):
        now = time.time()
        st = warm(far={social.day_of(now - 86400): 180.0})
        planes, best = social.one_poll(self.c, st, self.tracks, self.sky, now)
        self.assertIsNotNone(best, "a new record must be a candidate even outside the sharing radius")
        self.assertEqual(best[1], "farthest"); self.assertEqual(best[2]["hex"], "4b1801")
        self.assertAlmostEqual(st["far"][social.day_of(now)], 210, delta=1)
        # the next look: same aircraft, same distance: it set the record, it does not beat it
        planes, best = social.one_poll(self.c, st, self.tracks, self.sky, now + 15)
        self.assertIsNone(best)

    def test_not_a_record_when_the_month_had_farther(self):
        now = time.time()
        st = warm(far={social.day_of(now - 2 * 86400): 260.0})
        self.assertIsNone(social.one_poll(self.c, st, self.tracks, self.sky, now)[1])

    def test_no_record_before_three_days_of_history(self):
        now = time.time()
        st = {"since": social.day_of(now), "types": {}, "far": {}, "posted": {}}
        self.assertIsNone(social.one_poll(self.c, st, self.tracks, self.sky, now)[1])
        self.assertAlmostEqual(st["far"][social.day_of(now)], 210, delta=1, msg="the history is built even before")


class TracksTest(unittest.TestCase):
    def test_keeps_fifteen_minutes_and_drops_repeats_and_ground(self):
        t = social.Tracks(); now = time.time()
        t.feed([{"hex": "abc", "lat": 49.6, "lon": 6.1, "alt_baro": 1000, "seen_pos": 0}], now - 20 * 60)   # too old
        t.feed([{"hex": "abc", "lat": 49.6, "lon": 6.1, "alt_baro": 1000, "seen_pos": 0}], now - 100)
        t.feed([{"hex": "abc", "lat": 49.6, "lon": 6.1, "alt_baro": 1000, "seen_pos": 0}], now - 95)        # same spot: not a point
        t.feed([{"hex": "abc", "lat": 49.61, "lon": 6.1, "alt_baro": "ground", "seen_pos": 0}], now - 90)
        t.feed([{"hex": "~abc", "lat": 49.7, "lon": 6.1, "seen_pos": 0}, {"hex": "def", "lat": 1, "lon": 1, "seen_pos": 60}], now)
        self.assertEqual(len(t.of("abc")), 2)
        self.assertEqual(t.of("abc")[1][2], 0)
        self.assertEqual(t.of("~abc"), []); self.assertEqual(t.of("def"), [])


class PictureTest(unittest.TestCase):
    def test_the_renderer_draws_a_png_under_bluesky_s_limit(self):
        if shutil.which(social.NODE) is None:
            self.skipTest("node not installed here")
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        out = os.path.join(d, "p.png")
        info = social.render(EZY, trace(60), CFG, out)
        with open(out, "rb") as fh:
            head = fh.read(8)
        self.assertEqual(head, b"\x89PNG\r\n\x1a\n")
        self.assertLess(info["bytes"], 1000000)
        self.assertEqual((info["width"], info["height"]), (1310, 830))

    def node(self, js):
        if shutil.which(social.NODE) is None:
            self.skipTest("node not installed here")
        import subprocess
        r = subprocess.run([social.NODE, "-e", "const R = require(%s);" % json.dumps(social.RENDERER) + js],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_the_scale_keeps_the_track_inside_the_panel(self):
        # 0.18.2 let an A380's ten minutes (165 km) run past the frame; every extent up to 500 km per bar fits now
        out = self.node("const bad = []; for (let e = 0.1; e < 500 * R.HALF / R.BAR; e *= 1.07) {"
                        " const s = R.pickScaleKm(e); if (e * R.BAR / s > R.HALF) bad.push([e, s]); }"
                        " console.log(JSON.stringify({bad, a380: R.pickScaleKm(165)}));")
        self.assertEqual(out["bad"], [])
        self.assertEqual(out["a380"], 100)

    def test_callsign_small_and_registration_under_it(self):
        # 0.18.3: the callsign at the size of the other rows (7 dots high, not 14), the registration on the row under it
        out = self.node("const g = new Uint32Array(R.GW * R.GH);"
                        " R.drawWall(g, %s, 'metric', '11:39 GMT+2', true);"
                        " const lit = y => { let n = 0; for (let x = 0; x < 70; x++) n += g[y * R.GW + x] ? 1 : 0; return n; };"
                        " console.log(JSON.stringify({row: [...Array(16).keys()].map(lit), clock: lit(72)}));" % json.dumps(EZY))
        rows = out["row"]
        self.assertTrue(all(rows[y] for y in range(0, 7)), rows)          # the callsign
        self.assertEqual(rows[7], 0, rows)                                  # one dark row
        self.assertTrue(all(rows[y] for y in range(8, 15)), rows)          # G-UZHA
        self.assertGreater(out["clock"], 0)


class FakeResponse(object):
    def __init__(self, body, code=200):
        self.body, self.code = body, code
    def read(self):
        return json.dumps(self.body).encode()
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


class NetworksTest(unittest.TestCase):
    """What is sent to each network, checked against the shapes their documentation gives."""

    def setUp(self):
        self.sent = []
        self.old = urllib.request.urlopen
        test = self

        def fake(req, timeout=None):
            url = req.full_url
            test.sent.append((url, dict(req.header_items()), req.data))
            if url.endswith("createSession"):
                return FakeResponse({"accessJwt": "jwt-abc", "did": "did:plc:xyz", "handle": "zb.bsky.social"})
            if url.endswith("uploadBlob"):
                return FakeResponse({"blob": {"$type": "blob", "ref": {"$link": "bafy"}, "mimeType": "image/png", "size": 5}})
            if url.endswith("createRecord"):
                return FakeResponse({"uri": "at://did:plc:xyz/app.bsky.feed.post/3k", "cid": "bafy2"})
            if url.endswith("/api/v2/media"):
                return FakeResponse({"id": "110", "type": "image", "url": "https://files.example/x.png"})
            if "/api/v1/media/" in url:
                return FakeResponse({"id": "110", "url": "https://files.example/x.png"})
            if url.endswith("/api/v1/statuses"):
                return FakeResponse({"id": "1", "url": "https://mastodon.example/@zb/1"})
            if url.endswith("verify_credentials"):
                return FakeResponse({"acct": "zb"})
            raise AssertionError("unexpected url " + url)
        urllib.request.urlopen = fake
        self.addCleanup(setattr, urllib.request, "urlopen", self.old)
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        self.png = os.path.join(d, "p.png")
        with open(self.png, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\nfake")

    def test_bluesky_three_calls_with_hashtag_facets_and_alt(self):
        sec = {"BLUESKY_HANDLE": "zb.bsky.social", "BLUESKY_APP_PASSWORD": "aaaa-bbbb-cccc-dddd"}
        uri = social.post_bluesky(sec, "✈ easyJet · 11 280 m\n#ADSB #ZenithBoard", self.png, "alt here", 1310, 830)
        self.assertEqual(uri, "at://did:plc:xyz/app.bsky.feed.post/3k")
        urls = [s[0].split("/")[-1] for s in self.sent]
        self.assertEqual(urls, ["com.atproto.server.createSession", "com.atproto.repo.uploadBlob", "com.atproto.repo.createRecord"])
        self.assertEqual(self.sent[1][1]["Content-type"], "image/png")
        self.assertEqual(self.sent[1][1]["Authorization"], "Bearer jwt-abc")
        rec = json.loads(self.sent[2][2])["record"]
        self.assertEqual(rec["embed"]["images"][0]["alt"], "alt here")
        self.assertEqual(rec["embed"]["images"][0]["aspectRatio"], {"width": 1310, "height": 830})
        tags = [f["features"][0]["tag"] for f in rec["facets"]]
        self.assertEqual(tags, ["ADSB", "ZenithBoard"])
        # byte offsets, not character offsets: the ✈ is three bytes
        f0 = rec["facets"][0]["index"]
        self.assertEqual(rec["text"].encode("utf-8")[f0["byteStart"]:f0["byteEnd"]], b"#ADSB")

    def test_mastodon_media_then_status(self):
        sec = {"MASTODON_URL": "https://mastodon.example/", "MASTODON_TOKEN": "tok"}
        url = social.post_mastodon(sec, "✈ easyJet\n#ADSB", self.png, "alt here")
        self.assertEqual(url, "https://mastodon.example/@zb/1")
        self.assertTrue(self.sent[0][0].endswith("/api/v2/media"))
        self.assertTrue(self.sent[0][1]["Content-type"].startswith("multipart/form-data; boundary="))
        self.assertIn(b'name="description"\r\n\r\nalt here', self.sent[0][2])
        self.assertIn(b'filename="zenithboard.png"', self.sent[0][2])
        last = json.loads(self.sent[-1][2])
        self.assertEqual(last["media_ids"], ["110"]); self.assertEqual(last["visibility"], "public")
        self.assertIn("Idempotency-key", self.sent[-1][1])

    def test_check_accounts(self):
        sec = {"BLUESKY_HANDLE": "zb.bsky.social", "BLUESKY_APP_PASSWORD": "x", "MASTODON_URL": "https://mastodon.example", "MASTODON_TOKEN": "t"}
        r = social.check_accounts(sec, ["bluesky", "mastodon"])
        self.assertTrue(r["bluesky"].startswith("ok")); self.assertTrue(r["mastodon"].startswith("ok"))

    def test_secrets_are_never_in_the_text(self):
        sec = {"BLUESKY_HANDLE": "zb.bsky.social", "BLUESKY_APP_PASSWORD": "aaaa-bbbb-cccc-dddd"}
        social.post_bluesky(sec, "hello", self.png, "alt", 1, 1)
        for url, hdr, data in self.sent[1:]:
            self.assertNotIn(b"aaaa-bbbb", data or b"")


class ClockTest(unittest.TestCase):
    """The picture's last row: the time, with its offset from GMT as the Pi's zone has it that day."""

    def at(self, zone, when):
        old = os.environ.get("TZ")
        os.environ["TZ"] = zone; time.tzset()
        try:
            return social.clock_label(when)
        finally:
            if old is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = old
            time.tzset()

    def test_daylight_saving_follows_the_zone(self):
        summer, winter = 1784280000, 1768478400          # 2026-07-17 09:20 UTC, 2026-01-15 12:00 UTC
        self.assertEqual(self.at("Europe/Paris", summer), "11:20 GMT+2")
        self.assertEqual(self.at("Europe/Paris", winter), "13:00 GMT+1")
        self.assertEqual(self.at("UTC", winter), "12:00 GMT")
        self.assertEqual(self.at("Asia/Kolkata", winter), "17:30 GMT+5:30")
        self.assertEqual(self.at("America/New_York", winter), "07:00 GMT-5")


class PublishTest(unittest.TestCase):
    def test_an_unwritable_run_folder_does_not_stop_a_picture(self):
        # 0.18.1: `social test` from the command line crashed with PermissionError on /run/zenithboard/social,
        # which only exists while the service runs. A private temporary folder stands in, and is removed after.
        if shutil.which(social.NODE) is None:
            self.skipTest("node not installed here")
        old = social.RUN_DIR; social.RUN_DIR = "/proc/no-such-place/social"; self.addCleanup(setattr, social, "RUN_DIR", old)
        r = social.publish(EZY, trace(30), "any", CFG, {}, [], dry=True)
        self.assertIn("text", r)
        self.assertFalse([d for d in os.listdir(tempfile.gettempdir()) if d.startswith("zenithboard-social-")], "the stand-in folder must be removed")

    def test_the_picture_is_deleted_after_a_post_even_when_the_network_fails(self):
        if shutil.which(social.NODE) is None:
            self.skipTest("node not installed here")
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        old_run = social.RUN_DIR; social.RUN_DIR = d; self.addCleanup(setattr, social, "RUN_DIR", old_run)
        old = urllib.request.urlopen
        urllib.request.urlopen = lambda req, timeout=None: (_ for _ in ()).throw(OSError("no network"))
        self.addCleanup(setattr, urllib.request, "urlopen", old)
        keep = os.path.join(d, "keep", "preview.png")
        r = social.publish(EZY, trace(30), "any", CFG, {"BLUESKY_HANDLE": "h", "BLUESKY_APP_PASSWORD": "p"}, ["bluesky"], keep_png=keep)
        self.assertTrue(r["bluesky"].startswith("FAILED"))
        self.assertEqual([f for f in os.listdir(d) if f.startswith("post-")], [], "the picture must not stay on the Pi")
        self.assertTrue(os.path.exists(keep))


if __name__ == "__main__":
    unittest.main()
