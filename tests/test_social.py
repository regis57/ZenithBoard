# SPDX-License-Identifier: GPL-3.0-or-later
"""Social sharing: the words, the choice, the track, the two pictures, and the requests sent to Bluesky.

The network is not called: a fake urlopen records what would have been sent and answers like Bluesky does (shapes
copied from its API documentation). The renderers are real: node for the dot-matrix picture, Pillow for the split-flap
one, which is given fake map tiles.
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
    # no icon in front, the callsign a hashtag so the flight can be followed. 0.19.0: "altitude 11 280 m" on its own,
    # because "8 500 m above Trémery" was read as a distance from Trémery
    def test_airline_with_route(self):
        self.assertEqual(social.post_text(EZY, CFG).split("\n")[0],
                         "Flight easyJet #EZY1234 · Airbus A320neo · Edinburgh → Saint-Louis · altitude 11 280 m · over Luxembourg")

    def test_starts_with_the_flight_and_ends_above_the_place(self):
        t = social.post_text(EZY, dict(CFG, SOCIAL_AREA="Trémery")).split("\n")[0]
        self.assertTrue(t.startswith("Flight easyJet #EZY1234 · "), t)
        self.assertTrue(t.endswith(" · altitude 11 280 m · above Trémery"), t)

    def test_unknown_airline_shows_callsign_and_model(self):
        self.assertEqual(social.post_text(BELUGA, CFG).split("\n")[0], "Flight #BGA113J · Airbus A330-743 Beluga XL · F-GXLH · altitude 9 750 m · over Luxembourg")

    def test_a_registration_used_as_callsign_is_an_aircraft_not_a_flight(self):
        p = dict(BELUGA, flight="FGXLH", type_name="CESSNA 172", type="C172")
        self.assertEqual(social.post_text(p, dict(CFG, SOCIAL_AREA="Trémery")).split("\n")[0], "Aircraft F-GXLH · Cessna 172 · altitude 9 750 m · above Trémery")

    def test_only_airline_callsigns_become_hashtags(self):
        self.assertEqual(social.hashtag_callsign("ETD11K"), "#ETD11K")
        self.assertEqual(social.hashtag_callsign("DEABC"), "DEABC")
        self.assertEqual(social.hashtag_callsign("SAMU57"), "SAMU57")
        self.assertEqual(social.hashtag_callsign(""), "")

    def test_helicopter(self):
        t = social.post_text(HELI, CFG)
        self.assertTrue(t.startswith("Helicopter D-HABC · Airbus Helicopters H145 · altitude 460 m · over Luxembourg"), t)
        self.assertIn("#helicopter", t)

    def test_military_without_callsign(self):
        t = social.post_text(KC135, CFG)
        self.assertTrue(t.startswith("Military flight · Boeing KC-135R Stratotanker · altitude 7 620 m · over Luxembourg"), t)
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
        self.assertIn("· altitude 11 280 m · range record for 30 days: over 300 km out", t)
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
        self.assertIn("altitude 1 750 m · above Trémery", social.post_text(dict(EZY, alt_ft=5740), dict(CFG, SOCIAL_AREA="Trémery")))

    def test_the_altitude_never_reads_as_a_distance(self):
        # reported from the first posts: "10 670 m over Trémery" read as 10 km from Trémery
        for p in (EZY, BELUGA, HELI, KC135):
            line = social.post_text(p, dict(CFG, SOCIAL_AREA="Trémery")).split("\n")[0]
            self.assertRegex(line, r"· altitude [0-9 ]+ m · above Trémery$")
        self.assertIn("altitude 37 000 ft", social.post_text(EZY, dict(CFG, UNITS="imperial")))

    def test_the_post_stays_inside_300_characters_without_cutting_a_hashtag(self):
        # found in review: a range record with the satellite credit was 300 characters exactly, and Bluesky's cut
        # at 300 turned #ZenithBoard into a clickable #ZenithBo
        body = "Flight Emirates #UAE225 · Boeing 777-300ER · Dubai → San Francisco · altitude 11 280 m · range record for 30 days: over 300 km out, seen from Trémery"
        credit, short = "Map: EOxCloudless 2025 by EOX, cloudless.eox.at, Copernicus Sentinel data; labels © OpenStreetMap contributors, maps.eox.at", "Map: EOxCloudless 2025 by EOX, cloudless.eox.at; labels © OSM, maps.eox.at"
        t = social.fit_post(body, credit, "#ADSB #military #ZenithBoard", short)
        self.assertLessEqual(len(t), 300)
        self.assertEqual(t.split("\n"), [body, short, "#ADSB #military #ZenithBoard"])
        t = social.fit_post(body + " · " + "x" * 120, credit, "#ADSB #military #ZenithBoard", short)
        self.assertLessEqual(len(t), 300)
        self.assertTrue(t.endswith("#ADSB") or t.endswith("#ZenithBoard") or t.endswith("#military") or "#" not in t.split("\n")[-1], t)
        for tag in ("#ZenithBo", "#milit", "#AD\n"):
            self.assertNotIn(tag, t)
        self.assertIn(short, t)
        self.assertEqual(social.fit_post("short", None, "#ADSB"), "short\n#ADSB")

    def test_the_map_credit_comes_before_the_hashtags(self):
        t = social.post_text(EZY, CFG, credit="Map \u00a9 OpenStreetMap contributors, EOX maps.eox.at").split("\n")
        self.assertEqual(t[1], "Map \u00a9 OpenStreetMap contributors, EOX maps.eox.at")
        self.assertTrue(t[2].startswith("#ADSB"))

    def test_de_havilland(self):
        # reported from the real Pi: "DE Havilland DHC-8-400 Dash 8"
        self.assertEqual(social.nice_type({"type_name": "DE HAVILLAND DHC-8-400 Dash 8"}), "De Havilland DHC-8-400 Dash 8")

    def test_alt_text(self):
        a = social.alt_text(EZY, CFG, trace(20))
        self.assertIn("EZY1234", a); self.assertIn("easyJet", a); self.assertIn("from Edinburgh to Saint-Louis", a)
        self.assertIn("registration G-UZHA", a)
        self.assertIn("altitude 11 280 m", a)
        f = social.alt_text(EZY, CFG, trace(20), "flap", {"map_words": "a satellite map", "credit_full": "EOxCloudless 2025"})
        self.assertTrue(f.startswith("Split-flap flight board"), f)
        self.assertIn("Beside it, a satellite map with the aircraft's track", f)
        self.assertTrue(f.endswith("Map: EOxCloudless 2025."), f)
        self.assertTrue(a.endswith("north up."), a)


OLD = time.time() - 10 * 86400                     # a service that has watched for ten days


def warm(**kw):
    s = {"since": social.day_of(OLD), "types": {}, "far": {}, "posted": {}}
    s.update(kw)
    return s


class ChoiceTest(unittest.TestCase):
    def test_all_means_every_rule_and_the_special_aircraft_first(self):
        # 0.19.1, from the owner: ticking ALL alone must still treat a military aircraft as military
        self.assertEqual(social.rules_of({"SOCIAL_RULES": "all"}), set(social.RULES_ALL))
        self.assertEqual(social.rules_of({"SOCIAL_RULES": "any"}), set(social.RULES_ALL), "the 0.18 word still works")
        self.assertEqual(social.rules_of({"SOCIAL_RULES": "military,heavy"}), {"military", "heavy"})
        score, why = social.interest(KC135, social.rules_of({"SOCIAL_RULES": "all"}), warm(), time.time())
        self.assertEqual(why, "military")
        self.assertEqual(social.interest(EZY, {"all"}, warm(), time.time())[1], "all")

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
        self.assertIsNone(social.choose([NOTHING], self.tracks, {"all"}, warm(), time.time()))

    def test_already_posted_and_no_track_are_skipped(self):
        self.assertIsNone(social.choose([EZY], self.tracks, {"all"}, warm(posted={EZY["hex"]: time.time()}), time.time()))
        self.assertIsNone(social.choose([EZY], social.Tracks(), {"all"}, warm(), time.time()))

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
        info = social.render(EZY, trace(60), CFG, os.path.join(d, "p"))
        with open(info["path"], "rb") as fh:
            head = fh.read(8)
        self.assertEqual(head, b"\x89PNG\r\n\x1a\n")
        self.assertEqual((info["mime"], info["path"][-4:]), ("image/png", ".png"))
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

    def test_flight_and_registration_rows_labelled_like_alt_and_spd(self):
        # 0.19.0, from the owner's mock-up: "FLT  EZY1234" and "REG  G-UZHA", one row each, lined up with "ALT  11280 M"
        out = self.node("console.log(JSON.stringify([R.rows(%s, {}), R.rows({hex: '3c0001'}, {})]));" % json.dumps(EZY))
        self.assertEqual(out[0], {"flight": "FLT  EZY1234", "reg": "REG  G-UZHA"})
        self.assertEqual(out[1], {"flight": "HEX  3C0001", "reg": ""})
        out = self.node("const g = new Uint32Array(R.GW * R.GH);"
                        " R.drawWall(g, %s, 'metric', '11:39 GMT+2', true);"
                        " const lit = y => { let n = 0; for (let x = 0; x < 84; x++) n += g[y * R.GW + x] ? 1 : 0; return n; };"
                        " console.log(JSON.stringify({row: [...Array(16).keys()].map(lit), clock: lit(72)}));" % json.dumps(EZY))
        rows = out["row"]
        self.assertTrue(all(rows[y] for y in range(0, 7)), rows)          # FLT  EZY1234
        self.assertEqual(rows[7], 0, rows)                                  # one dark row
        self.assertTrue(all(rows[y] for y in range(8, 15)), rows)          # REG  G-UZHA
        self.assertGreater(out["clock"], 0)

    def test_colours_are_the_wall_s_own(self):
        # read from style.css, so a theme added to the wall is a theme of the picture
        out = self.node("console.log(JSON.stringify(Object.keys(R.THEMES).sort().map(k => [k, R.THEMES[k].toString(16)])));")
        got = dict(out)
        self.assertEqual(sorted(got), sorted(social.server.THEMES))
        self.assertEqual(got["amber"], "ffb000")
        with open(os.path.join(HERE, "..", "flightinfo", "static", "style.css")) as fh:
            self.assertIn("#" + got["green"], fh.read())

    def test_the_flap_board_rows(self):
        if shutil.which(social.NODE) is None:
            self.skipTest("node not installed here")
        got = social._node({"plane": EZY, "units": "metric", "clock": "11:39 GMT+2", "theme": "green", "cols": 14}, None, "--lines")
        # the wall's own formatting (format.js), 14 letters a row: what the tablet's split-flap look would show
        self.assertEqual(got["lines"], ["FLT  EZY1234", "REG  G-UZHA", "EASYJET", "A-320NEO", "ALT  11280 M", "SPD  593 KMH",
                                        "EDINBURGH", "\u2192SAINT-LOUIS", "11:39 GMT+2"])
        self.assertEqual(got["color"], "#39ff6a")

    def test_the_picture_s_colour_setting(self):
        self.assertEqual(social.theme_of({"THEME": "red"}), "red")                          # the wall's, by default
        self.assertEqual(social.theme_of({"THEME": "red", "SOCIAL_THEME": "blue"}), "blue")
        self.assertEqual(social.theme_of({"THEME": "red", "SOCIAL_THEME": "pink"}), "red")  # not a colour: ignored
        self.assertEqual(social.style_of({"SOCIAL_STYLE": "FLAP"}), "flap")
        self.assertEqual(social.style_of({"SOCIAL_STYLE": "photo"}), "dots")
        self.assertEqual(social.map_of({"SOCIAL_MAP": "satellite"}), "satellite")
        self.assertEqual(social.map_of({"SOCIAL_MAP": "google"}), "normal")


try:
    import social_card
    from PIL import Image
except ImportError:                                  # Pillow is only needed for the split-flap look
    social_card = None


def fake_tile(layer, ext, z, x, y):
    import io
    im = Image.new("RGBA" if ext == "png" else "RGB", (256, 256), (0, 0, 0, 0) if ext == "png" else (220, 215, 200))
    buf = io.BytesIO()
    im.save(buf, "PNG" if ext == "png" else "JPEG")
    return buf.getvalue()


@unittest.skipIf(social_card is None, "Pillow not installed here")
class FlapPictureTest(unittest.TestCase):
    LINES = ["FLT  EZY1234", "REG  G-UZHA", "EASYJET", "AIRBUS A320NEO", "ALT  11280 M", "SPD  593 KMH", "EDINBURGH", "\u2192SAINT-LOUIS", "11:39 GMT+2"]

    def setUp(self):
        self.d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.d, True)

    def test_a_jpeg_under_bluesky_s_limit_with_the_map_credited(self):
        out = os.path.join(self.d, "p.jpg")
        asked = []
        info = social_card.render(self.LINES, trace(60), EZY, out, "#ffb000", map_mode="satellite",
                                  fetch=lambda *a: asked.append(a) or fake_tile(*a))
        with open(out, "rb") as fh:
            self.assertEqual(fh.read(3), b"\xff\xd8\xff")
        self.assertLess(info["bytes"], 1000000)
        self.assertEqual((info["width"], info["height"]), (1500, 900))
        self.assertEqual(info["map"], "satellite")
        self.assertIn("cloudless.eox.at", info["credit"])
        self.assertIn(("cloudless.eox.at", "https://cloudless.eox.at"), info["links"])
        self.assertEqual({a[0] for a in asked}, {"s2cloudless-%d_3857" % social_card.S2_YEAR, "overlay_bright_3857"})

    def test_no_tile_no_map_no_credit(self):
        info = social_card.render(self.LINES, trace(60), EZY, os.path.join(self.d, "p.jpg"), map_mode="normal", fetch=lambda *a: None)
        self.assertEqual(info["map"], "none")
        self.assertIsNone(info["credit"])
        info = social_card.render(self.LINES, trace(60), EZY, os.path.join(self.d, "q.jpg"), map_mode="none",
                                  fetch=lambda *a: self.fail("map none must fetch nothing"))
        self.assertEqual(info["map"], "none")

    def test_eox_tile_address(self):
        # as WMTSCapabilities.xml gives it: .../{layer}/default/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.jpg
        self.assertEqual(social_card.tile_url("osm_3857", "jpg", 11, 1059, 701),
                         "https://tiles.maps.eox.at/wmts/1.0.0/osm_3857/default/g/11/701/1059.jpg")

    def test_the_view_holds_the_whole_track_and_is_centred_on_it(self):
        t = trace(60)
        z, ox, oy = social_card.choose_view(t, social_card.MAP_W, social_card.MAP_H)
        xs = [social_card.world_px(p[0], p[1], z)[0] - ox for p in t]
        ys = [social_card.world_px(p[0], p[1], z)[1] - oy for p in t]
        self.assertTrue(0 < min(xs) and max(xs) < social_card.MAP_W and 0 < min(ys) and max(ys) < social_card.MAP_H)
        self.assertLessEqual(z, social_card.MAX_ZOOM)
        self.assertAlmostEqual((min(xs) + max(xs)) / 2, social_card.MAP_W / 2, delta=1)
        # a 160 km track still fits, farther out
        long = [[49.1, 4.2 + i * 0.0186, 28000, i * 5] for i in range(121)]
        z2, _, _ = social_card.choose_view(long, social_card.MAP_W, social_card.MAP_H)
        self.assertLess(z2, z)

    def test_tiles_are_cached_for_a_month(self):
        calls = []

        class Resp(object):
            def __init__(self, data): self.data = data
            def read(self, n=-1): return self.data
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def opener(req, timeout=None):
            calls.append((req.full_url, req.get_header("User-agent")))
            return Resp(fake_tile("osm_3857", "jpg", 11, 1, 2))
        cache = os.path.join(self.d, "tiles")
        a = social_card.fetch_tile("osm_3857", "jpg", 11, 1, 2, cache, "ZenithBoard/test", opener)
        b = social_card.fetch_tile("osm_3857", "jpg", 11, 1, 2, cache, "ZenithBoard/test", opener)
        self.assertEqual(a, b)
        self.assertEqual(len(calls), 1, "the second time comes from the cache")
        self.assertEqual(calls[0][1], "ZenithBoard/test")
        path = os.path.join(cache, "osm_3857", "11", "1", "2.jpg")
        old = time.time() - 40 * 86400
        os.utime(path, (old, old))
        social_card.fetch_tile("osm_3857", "jpg", 11, 1, 2, cache, "ZenithBoard/test", opener)
        self.assertEqual(len(calls), 2, "over a month old: fetched again")
        os.utime(path, (old - 40 * 86400, old - 40 * 86400))
        social_card.prune_cache(cache)
        self.assertFalse(os.path.exists(path), "a tile over two months old is dropped")

    def test_a_tile_that_is_not_256_square_or_came_over_http_is_refused(self):
        class Resp(object):
            def __init__(self, data, url="https://tiles.maps.eox.at/x"): self.data, self.url = data, url
            def read(self, n=-1): return self.data
            def geturl(self): return self.url
            def __enter__(self): return self
            def __exit__(self, *a): return False
        import io
        big = io.BytesIO(); Image.new("RGB", (4000, 4000)).save(big, "PNG")
        self.assertIsNone(social_card.fetch_tile("osm_3857", "jpg", 3, 1, 2, None, "UA", lambda r, timeout=None: Resp(big.getvalue())))
        self.assertIsNone(social_card.fetch_tile("osm_3857", "jpg", 3, 1, 2, None, "UA", lambda r, timeout=None: Resp(fake_tile("osm_3857", "jpg", 3, 1, 2), "http://elsewhere/x")))
        self.assertIsNotNone(social_card.fetch_tile("osm_3857", "jpg", 3, 1, 2, None, "UA", lambda r, timeout=None: Resp(fake_tile("osm_3857", "jpg", 3, 1, 2))))

    def test_a_stale_tile_is_still_a_map_when_eox_is_down(self):
        cache = os.path.join(self.d, "tiles")
        path = os.path.join(cache, "osm_3857", "11", "1", "2.jpg")
        os.makedirs(os.path.dirname(path))
        with open(path, "wb") as fh:
            fh.write(fake_tile("osm_3857", "jpg", 11, 1, 2))
        old = time.time() - 40 * 86400
        os.utime(path, (old, old))
        social_card.prune_cache(cache)                                      # between one and two months: kept
        self.assertTrue(os.path.exists(path))
        down = lambda r, timeout=None: (_ for _ in ()).throw(OSError("down"))
        self.assertIsNotNone(social_card.fetch_tile("osm_3857", "jpg", 11, 1, 2, cache, "UA", down))

    def test_the_legend_boxes_are_see_through(self):
        img, shown = social_card.draw_map(trace(60), EZY, "#ffb000", fetch=lambda *a: fake_tile("osm_3857", "jpg", 1, 1, 1))
        # the legend box sits bottom-left over a light tile: dark but not black
        px = img.getpixel((20, social_card.MAP_H - 60))
        self.assertGreater(sum(px), 60, px); self.assertLess(sum(px), 400, px)

    def test_an_error_page_is_not_a_tile(self):
        class Resp(object):
            def read(self, n=-1): return b"<html>rate limited</html>"
            def __enter__(self): return self
            def __exit__(self, *a): return False
        self.assertIsNone(social_card.fetch_tile("osm_3857", "jpg", 3, 1, 2, os.path.join(self.d, "t"), "UA", lambda r, timeout=None: Resp()))

    def test_night_is_dark(self):
        light = Image.new("RGB", (8, 8), (235, 230, 220))
        self.assertLess(sum(social_card.darken(light).getpixel((0, 0))), 120)

    def test_a_letter_a_flap_cannot_carry_is_a_blank_flap(self):
        a = social_card.draw_board(["\u00c9TOILE"], "#ffb000")
        b = social_card.draw_board([" TOILE"], "#ffb000")
        self.assertEqual(a.tobytes(), b.tobytes())

    def test_without_pillow_the_flap_look_falls_back_to_dots(self):
        if shutil.which(social.NODE) is None:
            self.skipTest("node not installed here")
        import builtins
        real = builtins.__import__
        def no_pil(name, *a, **k):
            if name == "social_card":
                raise ImportError("no PIL")
            return real(name, *a, **k)
        builtins.__import__ = no_pil; self.addCleanup(setattr, builtins, "__import__", real)
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()) as out:
            info = social.render(EZY, trace(30), dict(CFG, SOCIAL_STYLE="flap"), os.path.join(self.d, "p"))
        self.assertEqual((info["mime"], info["fallback"]), ("image/png", True))
        self.assertIn("Pillow", out.getvalue())

    def test_social_render_in_the_flap_look(self):
        if shutil.which(social.NODE) is None:
            self.skipTest("node not installed here")
        old = social_card.fetch_tile
        social_card.fetch_tile = lambda layer, ext, z, x, y, *a, **k: fake_tile(layer, ext, z, x, y)
        self.addCleanup(setattr, social_card, "fetch_tile", old)
        c = dict(CFG, SOCIAL_STYLE="flap", SOCIAL_MAP="night", SOCIAL_THEME="turquoise")
        old_dir = social.STATE_DIR; social.STATE_DIR = self.d; self.addCleanup(setattr, social, "STATE_DIR", old_dir)
        info = social.render(EZY, trace(60), c, os.path.join(self.d, "p"))
        self.assertEqual((info["mime"], info["path"][-4:], info["map"]), ("image/jpeg", ".jpg", "night"))
        self.assertIn("maps.eox.at", social.post_text(EZY, c, None, info["credit"]))


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
    """What is sent to Bluesky, checked against the shapes its documentation gives."""

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

    def test_a_jpeg_and_the_map_credit_as_a_link(self):
        sec = {"BLUESKY_HANDLE": "zb.bsky.social", "BLUESKY_APP_PASSWORD": "x"}
        text = "Flight easyJet #EZY1234 \u00b7 altitude 11 280 m\nMap \u00a9 OpenStreetMap contributors, EOX maps.eox.at\n#ADSB"
        social.post_bluesky(sec, text, self.png, "alt", 1500, 900, "image/jpeg", [("maps.eox.at", "https://maps.eox.at")])
        self.assertEqual(self.sent[1][1]["Content-type"], "image/jpeg")
        rec = json.loads(self.sent[2][2])["record"]
        links = [f for f in rec["facets"] if f["features"][0]["$type"].endswith("#link")]
        self.assertEqual(len(links), 1)
        i = links[0]["index"]
        self.assertEqual(rec["text"].encode("utf-8")[i["byteStart"]:i["byteEnd"]], b"maps.eox.at")
        self.assertEqual(links[0]["features"][0]["uri"], "https://maps.eox.at")
        starts = [f["index"]["byteStart"] for f in rec["facets"]]
        self.assertEqual(starts, sorted(starts))

    def test_check_the_account(self):
        self.assertTrue(social.check_bluesky({"BLUESKY_HANDLE": "zb.bsky.social", "BLUESKY_APP_PASSWORD": "x"}).startswith("ok"))
        self.assertFalse(social.bluesky_ready({"MASTODON_URL": "https://m.example", "MASTODON_TOKEN": "t"}),
                         "Mastodon is gone (0.19.0): its secrets alone are no account")

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


class OncePerAircraftTest(unittest.TestCase):
    def test_an_aircraft_is_posted_once_while_it_is_in_the_sky(self):
        # a slow aircraft that stays an hour in the zone, with a 20-minute gap: before 0.19.0 the "posted" memory
        # was a day from the post, which already held; now it is a day from the last time the aircraft was seen,
        # so a restart of the service or a long loiter can never make a second post of the same airframe
        st, t0 = warm(), time.time() - 3 * 86400
        st["posted"] = {EZY["hex"]: t0}
        for h in range(0, 50, 1):                               # seen every hour for two days
            social.note_seen(st, [{"hex": EZY["hex"].upper()}], t0 + h * 3600)
            social.prune_state(st, t0 + h * 3600)
        self.assertIn(EZY["hex"], st["posted"])
        tracks = social.Tracks()
        for pt in trace(8, t0 + 49 * 3600 - 40):
            tracks.feed([{"hex": EZY["hex"], "lat": pt[0], "lon": pt[1], "alt_baro": pt[2], "seen_pos": 0}], pt[3])
        self.assertIsNone(social.choose([EZY], tracks, {"all"}, st, t0 + 49 * 3600))
        social.prune_state(st, t0 + 49 * 3600 + 2 * 86400)   # a day after it was last seen: forgotten
        self.assertNotIn(EZY["hex"], st["posted"])


class ServiceLoopTest(unittest.TestCase):
    def test_a_failed_post_is_not_retried_at_every_look(self):
        # before 0.19.0 a failed post was tried again at the next look, fifteen seconds later, and each try signs in
        # to Bluesky: an app password revoked, or Bluesky down, meant a sign-in every fifteen seconds
        import contextlib
        import io
        start = 1800000000.0
        clock = [start]
        tries = []

        class Stop(Exception):
            pass

        def fake_sleep(sec):
            clock[0] += sec
            if clock[0] > start + 30 * 60:
                raise Stop()
        for name, fake in (("read_aircraft", lambda c: []), ("account", lambda: {"BLUESKY_HANDLE": "h", "BLUESKY_APP_PASSWORD": "p"}),
                           ("one_poll", lambda c, st, tr, ac, now: ([EZY], (5, "all", EZY))), ("load_state", warm),
                           ("save_state", lambda st: None), ("cfg", lambda: dict(CFG)),
                           ("publish", lambda *a, **k: tries.append(clock[0]) or {"bluesky": "FAILED: 503 down"})):
            self.addCleanup(setattr, social, name, getattr(social, name))
            setattr(social, name, fake)
        self.addCleanup(setattr, time, "time", time.time); time.time = lambda: clock[0]
        self.addCleanup(setattr, time, "sleep", time.sleep); time.sleep = fake_sleep
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(Stop):
                social.cmd_run()
        self.assertGreaterEqual(len(tries), 3)
        self.assertLessEqual(len(tries), 4, "half an hour: a try every ten minutes, not every fifteen seconds")
        self.assertTrue(all(b - a >= social.RETRY_AFTER_FAIL_S for a, b in zip(tries, tries[1:])))


class SharedStateTest(unittest.TestCase):
    def test_a_post_made_by_hand_counts_for_the_running_service(self):
        # seen on the real Pi (0.19.2): "Post now" at 13:34, then the service posted again at 14:22 with a two-hour
        # gap. The service kept its state in memory and wrote it back every fifteen seconds over what `social post`
        # had written: the manual post, and the aircraft it posted, were forgotten.
        import contextlib
        import io
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        self.addCleanup(setattr, social, "STATE_DIR", social.STATE_DIR); social.STATE_DIR = d
        start = 1800000000.0
        clock = [start]
        tries = []

        class Stop(Exception):
            pass

        def fake_sleep(sec):
            clock[0] += sec
            if abs(clock[0] - (start + 60)) < 3:            # one minute in, someone posts EZY by hand
                social.remember_post(EZY["hex"], clock[0])
            if clock[0] > start + 60 * 60:
                raise Stop()
        social.save_state(dict(warm(), last_post=start - 3 * 3600))   # the last post long ago: the gap is open
        for name, fake in (("read_aircraft", lambda c: []), ("account", lambda: {"BLUESKY_HANDLE": "h", "BLUESKY_APP_PASSWORD": "p"}),
                           # nothing worth a post for two minutes, then a Beluga: after a manual post a minute in
                           ("one_poll", lambda c, st, tr, ac, now: ([BELUGA], None if now < start + 120 else (5, "all", BELUGA))),
                           ("cfg", lambda: dict(CFG, SOCIAL_GAP_MIN="120")),
                           ("publish", lambda *a, **k: tries.append(clock[0]) or {"bluesky": "at://x"})):
            self.addCleanup(setattr, social, name, getattr(social, name))
            setattr(social, name, fake)
        self.addCleanup(setattr, time, "time", time.time); time.time = lambda: clock[0]
        self.addCleanup(setattr, time, "sleep", time.sleep); time.sleep = fake_sleep
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(Stop):
                social.cmd_run()
        self.assertEqual(tries, [], "the manual post opened a two-hour gap: the service waits")
        st = social.load_state()
        self.assertIn(EZY["hex"], st["posted"], "the aircraft posted by hand is still remembered after the service saved")
        self.assertGreaterEqual(st["last_post"], start + 57)


class LogFindingsTest(unittest.TestCase):
    """From the real Pi's log, 0.19.3."""

    def test_the_gap_has_a_floor_of_ten_minutes(self):
        # the gap had been set to 1 minute for a test: with ALL, that is a post a minute
        self.assertEqual(social.gap_min({"SOCIAL_GAP_MIN": "1"}), social.GAP_FLOOR_MIN)
        self.assertEqual(social.gap_min({"SOCIAL_GAP_MIN": "120"}), 120)
        self.assertIn("floor", social.gap_words({"SOCIAL_GAP_MIN": "1"}))
        self.assertEqual(social.gap_words({"SOCIAL_GAP_MIN": "30"}), "30 min")

    def test_status_says_when_it_cannot_read_rather_than_never(self):
        # `zenithboard social status` as pi printed "no account" and "Last post: never" on a Pi that had just posted:
        # pi cannot read the account file (root:zenithboard 0640) nor the service's state folder
        import contextlib
        import io
        self.addCleanup(setattr, social, "unreadable", social.unreadable)
        social.unreadable = lambda path: True
        with contextlib.redirect_stdout(io.StringIO()) as out:
            social.cmd_status()
        text = out.getvalue()
        self.assertIn("cannot read the account file", text)
        self.assertIn("cannot read the service's state folder", text)
        self.assertIn("sudo zenithboard social status", text)
        self.assertNotIn("no account", text)
        self.assertNotIn("Last post: never", text)

    def test_the_service_says_which_version_it_runs(self):
        # the log showed a service started before the update, still running the old code: its first line says now
        import contextlib
        import io

        class Stop(Exception):
            pass
        self.addCleanup(setattr, time, "sleep", time.sleep)
        time.sleep = lambda s: (_ for _ in ()).throw(Stop())
        for name, fake in (("read_aircraft", lambda c: []), ("account", lambda: {}), ("one_poll", lambda *a: ([], None)),
                           ("load_state", warm), ("save_state", lambda st: None), ("cfg", lambda: dict(CFG))):
            self.addCleanup(setattr, social, name, getattr(social, name))
            setattr(social, name, fake)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            with self.assertRaises(Stop):
                social.cmd_run()
        self.assertIn("running ZenithBoard %s" % social.server.VERSION, out.getvalue())


class PublishTest(unittest.TestCase):
    def test_an_unwritable_run_folder_does_not_stop_a_picture(self):
        # 0.18.1: `social test` from the command line crashed with PermissionError on /run/zenithboard/social,
        # which only exists while the service runs. A private temporary folder stands in, and is removed after.
        if shutil.which(social.NODE) is None:
            self.skipTest("node not installed here")
        old = social.RUN_DIR; social.RUN_DIR = "/proc/no-such-place/social"; self.addCleanup(setattr, social, "RUN_DIR", old)
        r = social.publish(EZY, trace(30), "all", CFG, {}, dry=True)
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
        keep = os.path.join(d, "keep", "preview")
        os.makedirs(os.path.dirname(keep), exist_ok=True)
        with open(keep + ".jpg", "wb") as fh:          # a flap preview from before
            fh.write(b"old")
        r = social.publish(EZY, trace(30), "all", CFG, {"BLUESKY_HANDLE": "h", "BLUESKY_APP_PASSWORD": "p"}, keep=keep)
        self.assertTrue(r["bluesky"].startswith("FAILED"))
        self.assertEqual([f for f in os.listdir(d) if f.startswith("post-")], [], "the picture must not stay on the Pi")
        self.assertTrue(os.path.exists(keep + ".png"))
        self.assertFalse(os.path.exists(keep + ".jpg"), "the preview is the last picture drawn, whatever the look")


if __name__ == "__main__":
    unittest.main()
