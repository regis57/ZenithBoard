# SPDX-License-Identifier: GPL-3.0-or-later
"""Social sharing: the words, the choice, the track, the two pictures, and the requests sent to Bluesky.

The network is not called: a fake urlopen records what would have been sent and answers like Bluesky does (shapes
copied from its API documentation). The renderers are real: node for the dot-matrix picture, Pillow for the split-flap
one, which is given fake map tiles.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
import urllib.error
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


class SentenceTest(unittest.TestCase):
    """0.29.0, asked for by the owner: the post in five shapes, from templates, chosen one or several or at random."""
    RYR = {"hex": "4ca7b1", "flight": "RYR5ZK", "registration": "EI-ENK", "type": "B738", "type_name": "BOEING 737-800",
           "shape": "narrow", "airline": "Ryanair", "alt_ft": 34680, "gs_kt": 389, "distance_km": 6.2, "bearing": 300,
           "route": {"from": {"city": "Brussels"}, "to": {"city": "Pisa"}}}
    C = dict(CFG, SOCIAL_AREA="Trémery")

    def text(self, shape, why=None, p=None, **cfg):
        return social.post_text(p or self.RYR, dict(self.C, **cfg), why, shape=shape)

    def test_the_five_shapes(self):
        nb = "\u00a0"
        self.assertTrue(self.text("factual").startswith("Flight Ryanair #RYR5ZK · Boeing 737-800 · Brussels → Pisa"))
        self.assertTrue(self.text("story").startswith("A Ryanair Boeing 737-800 bound for Pisa from Brussels has just crossed the sky above Trémery, 10" + nb + "570" + nb + "m up. #RYR5ZK"), self.text("story"))
        board = self.text("board").split("\n")
        self.assertEqual(board[:3], ["\u2708 #RYR5ZK · EI-ENK", "Brussels \u2192 Pisa", "Boeing 737-800 · 10" + nb + "570" + nb + "m · 720" + nb + "km/h"])
        self.assertTrue(board[3].startswith("Above Trémery at "))
        self.assertTrue(self.text("spotter").startswith("EI-ENK, a Ryanair Boeing 737-800, flying Brussels \u2192 Pisa as #RYR5ZK: 10" + nb + "570" + nb + "m above Trémery at 720" + nb + "km/h."), self.text("spotter"))
        self.assertTrue(self.text("lookup").startswith("Look up, Trémery! Ryanair #RYR5ZK is passing 10.6" + nb + "km overhead on its way from Brussels to Pisa."), self.text("lookup"))

    def test_never_the_distance_nor_the_direction(self):
        for shape in social.SENTENCES:
            t = self.text(shape)
            self.assertNotIn("6.2", t, shape)
            self.assertNotRegex(t, r"\b(NNW|WNW|north|west)\b", shape)
            self.assertLessEqual(len(t), social.POST_MAX, shape)
            self.assertTrue(t.rstrip().endswith("#ZenithBoard"), shape)

    def test_the_reason_said_first(self):
        self.assertTrue(self.text("story", "rare").startswith("Rare visitor: A Ryanair"))
        self.assertTrue(self.text("factual", "heavy").startswith("Heavy overhead: Flight Ryanair"))
        mil = dict(self.RYR, airline="MILITARY", military=True, flight="RCH123", type_name="BOEING C-17A Globemaster III")
        self.assertTrue(self.text("lookup", "military", mil).startswith("Military traffic: Look up, Trémery! military #RCH123"), self.text("lookup", "military", mil))
        self.assertTrue(self.text("factual", "military", mil).startswith("Military flight #RCH123"), "factual already says it")
        rec = dict(self.RYR, distance_km=342)
        self.assertIn("range record for 30 days", self.text("story", "farthest", rec), "a record keeps the factual words")

    def test_what_a_shape_cannot_say_falls_back(self):
        bare = {"hex": "abc123", "flight": "", "registration": "D-EABC", "alt_ft": 3000}
        self.assertTrue(self.text("story", p=bare).startswith("Aircraft D-EABC"), "no airline, no type: factual")
        self.assertTrue(self.text("lookup", **{"SOCIAL_AREA": "near Metz"}).startswith("Look up! Ryanair #RYR5ZK"))

    def test_a_or_an(self):
        self.assertEqual([social._a(w) for w in ("Airbus", "easyJet A320", "Eurowings A320", "United 787", "Boeing")],
                         ["an Airbus", "an easyJet A320", "a Eurowings A320", "a United 787", "a Boeing"])

    def test_choosing(self):
        import random
        self.assertEqual(social.sentences_of({}), ["factual"])
        self.assertEqual(social.sentences_of({"SOCIAL_SENTENCE": "story, lookup,nonsense"}), ["story", "lookup"])
        self.assertEqual(social.sentences_of({"SOCIAL_SENTENCE": "random"}), list(social.SENTENCES))
        self.assertEqual(social.sentences_of({"SOCIAL_SENTENCE": "nonsense"}), ["factual"])
        rng = random.Random(1)
        got = {social.sentence_for({"SOCIAL_SENTENCE": "story,spotter"}, rng) for _ in range(40)}
        self.assertEqual(got, {"story", "spotter"})


class WordsTest(unittest.TestCase):
    # 0.18.3: the post starts with the flight ("Flight Etihad #ETD11K") and ends with the place ("above Trémery");
    # no icon in front, the callsign a hashtag so the flight can be followed. 0.19.0: "altitude 11\u00a0280\u00a0m" on its own,
    # because "8\u00a0500\u00a0m above Trémery" was read as a distance from Trémery
    def test_airline_with_route(self):
        self.assertEqual(social.post_text(EZY, CFG).split("\n")[0],
                         "Flight easyJet #EZY1234 · Airbus A320neo · Edinburgh → Saint-Louis · altitude 11\u00a0280\u00a0m · over Luxembourg")

    def test_starts_with_the_flight_and_ends_above_the_place(self):
        t = social.post_text(EZY, dict(CFG, SOCIAL_AREA="Trémery")).split("\n")[0]
        self.assertTrue(t.startswith("Flight easyJet #EZY1234 · "), t)
        self.assertTrue(t.endswith(" · altitude 11\u00a0280\u00a0m · above Trémery"), t)

    def test_unknown_airline_shows_callsign_and_model(self):
        self.assertEqual(social.post_text(BELUGA, CFG).split("\n")[0], "Flight #BGA113J · Airbus A330-743 Beluga XL · F-GXLH · altitude 9\u00a0750\u00a0m · over Luxembourg")

    def test_a_registration_used_as_callsign_is_an_aircraft_not_a_flight(self):
        p = dict(BELUGA, flight="FGXLH", type_name="CESSNA 172", type="C172")
        self.assertEqual(social.post_text(p, dict(CFG, SOCIAL_AREA="Trémery")).split("\n")[0], "Aircraft F-GXLH · Cessna 172 · altitude 9\u00a0750\u00a0m · above Trémery")

    def test_only_airline_callsigns_become_hashtags(self):
        self.assertEqual(social.hashtag_callsign("ETD11K"), "#ETD11K")
        self.assertEqual(social.hashtag_callsign("DEABC"), "DEABC")
        self.assertEqual(social.hashtag_callsign("SAMU57"), "SAMU57")
        self.assertEqual(social.hashtag_callsign(""), "")

    def test_helicopter(self):
        t = social.post_text(HELI, CFG)
        self.assertTrue(t.startswith("Helicopter D-HABC · Airbus Helicopters H145 · altitude 460\u00a0m · over Luxembourg"), t)
        self.assertIn("#helicopter", t)

    def test_military_without_callsign(self):
        t = social.post_text(KC135, CFG)
        self.assertTrue(t.startswith("Military flight · Boeing KC-135R Stratotanker · altitude 7\u00a0620\u00a0m · over Luxembourg"), t)
        self.assertIn("#military", t)
        self.assertTrue(social.post_text(dict(KC135, flight="RCH123"), CFG).startswith("Military flight #RCH123 · "))

    def test_nothing_known_is_not_worth_a_post(self):
        self.assertFalse(social.known(NOTHING))
        self.assertTrue(social.known(EZY))

    def test_imperial_and_no_area(self):
        c = dict(CFG, UNITS="imperial", SOCIAL_AREA="")
        self.assertIn("37\u00a0000\u00a0ft", social.post_text(EZY, c))
        self.assertNotIn("over", social.post_text(EZY, c))

    def test_text_never_carries_distance_or_bearing(self):
        for p in (EZY, BELUGA, HELI, KC135):
            t = social.post_text(p, CFG)
            self.assertNotIn("km", t.replace("km/h", ""))
            self.assertNotIn("NE", t.split("\n")[0].replace("NEO", "").replace("Beluga", ""))

    def test_a_range_record_is_said_without_the_figure(self):
        # rounded DOWN to 50\u00a0km: enough to tell a record, not enough to draw a circle around the antenna
        t = social.post_text(dict(EZY, distance_km=332.4), CFG, why="farthest")
        self.assertTrue(t.startswith("Flight easyJet #EZY1234 · "), t)
        self.assertIn("· altitude 11\u00a0280\u00a0m · range record for 30 days: over 300\u00a0km out", t)
        self.assertNotIn("332", t)
        # far from overhead: the place is where it was seen from, not what it flew above
        t = social.post_text(dict(EZY, distance_km=332.4), dict(CFG, SOCIAL_AREA="Trémery"), why="farthest").split("\n")[0]
        self.assertTrue(t.endswith("range record for 30 days: over 300\u00a0km out, seen from Trémery"), t)
        self.assertNotIn("above", t)
        self.assertEqual(social.range_words(51), "over 50\u00a0km out")
        self.assertEqual(social.range_words(149.9), "over 100\u00a0km out")

    def test_a_bare_place_name_reads_above(self):
        # reported from the real Pi: "1\u00a0750\u00a0m Trémery"; 0.18.3 asked for "above"
        self.assertEqual(social.area_words({"SOCIAL_AREA": "Trémery"}), "above Trémery")
        self.assertEqual(social.area_words({"SOCIAL_AREA": "near Metz"}), "near Metz")
        self.assertEqual(social.area_words({"SOCIAL_AREA": "over the Moselle"}), "over the Moselle")
        self.assertEqual(social.area_words({"SOCIAL_AREA": "  "}), "")
        self.assertIn("altitude 1\u00a0750\u00a0m · above Trémery", social.post_text(dict(EZY, alt_ft=5740), dict(CFG, SOCIAL_AREA="Trémery")))

    def test_the_altitude_never_reads_as_a_distance(self):
        # reported from the first posts: "10\u00a0670\u00a0m over Trémery" read as 10\u00a0km from Trémery
        for p in (EZY, BELUGA, HELI, KC135):
            line = social.post_text(p, dict(CFG, SOCIAL_AREA="Trémery")).split("\n")[0]
            self.assertRegex(line, r"· altitude [0-9\u00a0]+\u00a0m · above Trémery$")
        # and never split across two lines on a phone (0.19.8: "altitude 8" / "600 m")
        self.assertNotRegex(social.post_text(EZY, CFG), r"\d \d|\d m\b")
        self.assertIn("altitude 37\u00a0000\u00a0ft", social.post_text(EZY, dict(CFG, UNITS="imperial")))

    def test_the_post_stays_inside_300_characters_without_cutting_a_hashtag(self):
        # found in review: a range record with a long credit was 300 characters exactly, and Bluesky's cut at 300
        # turned #ZenithBoard into a clickable #ZenithBo
        body = "Flight Emirates #UAE225 · Boeing 777-300ER · Dubai → San Francisco · altitude 11\u00a0280\u00a0m · range record for 30 days: over 300\u00a0km out, seen from Trémery"
        credit = "Map: EOxCloudless by EOX, © OpenStreetMap"
        t = social.fit_post(body, credit, "#ADSB #military #ZenithBoard")
        self.assertLessEqual(len(t), 300)
        self.assertEqual(t.split("\n"), [body, "#ADSB #military #ZenithBoard", credit])
        t = social.fit_post(body + " · " + "x" * 120, credit, "#ADSB #military #ZenithBoard")
        self.assertLessEqual(len(t), 300)
        for tag in ("#ZenithBo\n", "#milit\n", "#AD\n"):
            self.assertNotIn(tag, t)
        self.assertTrue(t.endswith(credit), "the credit is never cut")
        self.assertEqual(social.fit_post("short", None, "#ADSB"), "short\n#ADSB")

    def test_hashtags_none_means_none_at_all(self):
        # 0.19.7: `social hashtags none` — not even #helicopter or #military added back
        for p in (EZY, HELI, KC135):
            t = social.post_text(p, dict(CFG, SOCIAL_HASHTAGS="none"))
            self.assertNotIn("#", t.replace("#EZY1234", ""), t)
        t = social.post_text(HELI, dict(CFG, SOCIAL_HASHTAGS="#ADSB #Moselle"))
        self.assertTrue(t.endswith("#ADSB #Moselle #helicopter"), t)

    def test_the_map_credit_is_one_short_line_at_the_end(self):
        # 0.19.6, from the owner after the first satellite post: the three lines of small print spoiled the post.
        # The whole text stays on the picture and in the alt text; the post has the names, as links
        if social_card is None:
            self.skipTest("Pillow not installed here")
        for mode, st in social_card.MAP_STYLES.items():
            if st["credit"]:
                self.assertLessEqual(len(st["credit"]), 45, mode)
                for label, uri in st["links"]:
                    self.assertIn(label, st["credit"], mode)
                    self.assertTrue(uri.startswith("https://"), uri)
                if "OpenStreetMap" in st["credit_full"]:                     # every map drawn from OSM's data says so
                    self.assertIn("OpenStreetMap", st["credit"], mode)
                    self.assertIn("OpenStreetMap contributors", st["credit_full"], mode)
                if st.get("names"):                                           # 0.24.4: the town names are GeoNames'
                    self.assertIn("GeoNames", st["credit"], mode)
                    self.assertIn("GeoNames (CC BY 4.0)", st["credit_full"], mode)
        self.assertIn("Copernicus Sentinel data", social_card.MAP_STYLES["satellite"]["credit_full"])
        t = social.post_text(EZY, CFG, credit="Map \u00a9 OpenStreetMap, EOX").split("\n")
        self.assertTrue(t[1].startswith("#ADSB"))
        self.assertEqual(t[2], "Map \u00a9 OpenStreetMap, EOX")


    def test_de_havilland(self):
        # reported from the real Pi: "DE Havilland DHC-8-400 Dash 8"
        self.assertEqual(social.nice_type({"type_name": "DE HAVILLAND DHC-8-400 Dash 8"}), "De Havilland DHC-8-400 Dash 8")

    def test_alt_text(self):
        a = social.alt_text(EZY, CFG, trace(20))
        self.assertIn("EZY1234", a); self.assertIn("easyJet", a); self.assertIn("from Edinburgh to Saint-Louis", a)
        self.assertIn("registration G-UZHA", a)
        self.assertIn("altitude 11\u00a0280\u00a0m", a)
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


class VarietyTest(unittest.TestCase):
    def test_alternate_and_rotate_meet_every_colour_and_every_map_in_both_looks(self):
        # 0.23.0: the turn is the two looks with a map, the dot-matrix wall and the split-flap board, both with the
        # four maps; the dots-only track left it. Five colours (the dark blue is gone) against two looks: ten posts
        c = dict(CFG, SOCIAL_STYLE="alternate", SOCIAL_THEME="rotate", SOCIAL_MAP="rotate")
        seen = [social.picture_for(c, n) for n in range(40)]
        looks = [s["SOCIAL_STYLE"] for s in seen]
        self.assertEqual(looks[:10], ["dotmap", "flap"] * 5)
        self.assertEqual(social.ROTATE_THEMES, ("amber", "green", "red", "white", "turquoise"))
        for look in ("dotmap", "flap"):
            self.assertEqual({s["SOCIAL_THEME"] for s in seen[:10] if s["SOCIAL_STYLE"] == look}, set(social.ROTATE_THEMES), look)
            self.assertEqual([s["SOCIAL_MAP"] for s in seen[:8] if s["SOCIAL_STYLE"] == look], list(social.ROTATE_MAPS), look)
        self.assertIn("next: flap", social.picture_words(c, {"pictures": 1}))
        self.assertIn("next: dotmap, red, night map", social.picture_words(c, {"pictures": 2}))

    def test_the_dotmap_look_alone_turns_its_maps_at_every_post(self):
        c = dict(CFG, SOCIAL_STYLE="dotmap", SOCIAL_THEME="white", SOCIAL_MAP="rotate")
        self.assertEqual([social.picture_for(c, n)["SOCIAL_MAP"] for n in range(4)], list(social.ROTATE_MAPS))
        self.assertEqual(social.picture_words(dict(c, SOCIAL_MAP="terrain")), "dotmap, white, terrain map")
        self.assertEqual(social.picture_words(dict(c, SOCIAL_MAP="none")), "dotmap, white, no map")   # the track on black (0.24.0)

    def test_fixed_settings_stay_fixed(self):
        c = dict(CFG, SOCIAL_STYLE="flap", SOCIAL_THEME="green", SOCIAL_MAP="night")
        self.assertEqual(social.picture_for(c, 7), c)
        self.assertEqual(social.picture_words(c, {"pictures": 3}), "flap, green, night map")

    def test_a_post_moves_the_picture_on_even_one_made_by_hand(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        self.addCleanup(setattr, social, "STATE_DIR", social.STATE_DIR); social.STATE_DIR = d
        social.remember_post({"hex": "aaaaaa"}, time.time())
        social.remember_post({"hex": "bbbbbb"}, time.time())
        self.assertEqual(social.load_state()["pictures"], 2)
        st = {"pictures": 1}
        self.assertEqual(social.merge_disk(st)["pictures"], 2)


class SettleTest(unittest.TestCase):
    def test_an_aircraft_the_wall_is_still_looking_up_waits(self):
        # seen on the real Pi (0.19.5): KLM24V posted with no registration, no model and no route. Its track was
        # five minutes long (followed from far out), but the wall had only just been asked about it
        tracks, now = social.Tracks(), time.time()
        for pt in trace(60, now - 300):
            tracks.feed([{"hex": EZY["hex"], "lat": pt[0], "lon": pt[1], "alt_baro": pt[2], "seen_pos": 0}], pt[3])
        bare = dict(EZY, registration=None, type=None, type_name=None, route=None, pending=["route", "model"])
        self.assertIsNone(social.choose([bare], tracks, {"all"}, warm(), now), "just asked: wait")
        self.assertIsNone(social.choose([bare], tracks, {"all"}, warm(), now + 60), "a minute on: still waiting")
        self.assertEqual(social.choose([dict(EZY, pending=[])], tracks, {"all"}, warm(), now + 75)[2]["hex"], EZY["hex"],
                         "the answers came: posted, complete")
        self.assertIsNotNone(social.choose([bare], tracks, {"all"}, warm(), now + social.SETTLE_S + 1), "past the wait: what is known")
        fresh = social.Tracks(); fresh.by_hex = dict(tracks.by_hex)
        self.assertIsNotNone(social.choose([bare], fresh, {"all"}, warm(), now, settle=False), "`social test` at the end of its half minute")

    def test_the_wall_says_what_is_still_on_its_way(self):
        srv = social.server
        lk = srv.ThrottledLookup(lambda key: (None, True), gap=0, retry=600, miss_retry=600)
        self.assertFalse(lk.pending("X"))
        with lk.lock:
            lk.cache["X"] = {"value": None, "retry_at": 0, "queued": True}
        self.assertTrue(lk.pending("X"), "asked, not answered")
        with lk.lock:
            lk.cache["X"] = {"value": None, "retry_at": 1e12, "queued": False}
        self.assertFalse(lk.pending("X"), "answered 'not found' (or failed): nothing to wait for")
        route = lambda cs: None
        route.pending = lambda cs: True
        planes, _ = srv.build_planes({"aircraft": [{"hex": "484b6c", "flight": "KLM24V", "lat": 49.25, "lon": 6.2, "alt_baro": 38000}]},
                                     49.25, 6.2, 10, route_lookup=route)
        self.assertEqual(planes[0]["pending"], ["route"])

    def test_a_second_opinion_on_its_way_is_waited_for_too(self):
        # 0.19.9, seen on the real Pi: RYR8526 over Metz heading south-east. adsbdb said Berlin -> Stansted (another
        # flight under that callsign: rightly refused); hexdb, asked next, said Charleroi -> Reggio Calabria, which
        # is this one, but the post had gone before its answer came
        srv = social.server
        ber = {"iata": "BER", "city": "Berlin", "name": "Berlin Brandenburg", "lat": 52.35139, "lon": 13.49389}
        stn = {"iata": "STN", "city": "London", "name": "London Stansted", "lat": 51.885, "lon": 0.235}
        crl = {"iata": "CRL", "city": "Charleroi", "name": "Brussels South Charleroi", "lat": 50.459, "lon": 4.4538}
        reg = {"iata": "REG", "city": "Reggio Calabria", "name": "Reggio Calabria", "lat": 38.0712, "lon": 15.6516}
        sky = {"aircraft": [{"hex": "4ca7b5", "flight": "RYR8526", "lat": 49.35, "lon": 6.15, "alt_baro": 34000, "track": 140, "gs": 465}]}
        first = lambda cs: {"from": ber, "to": stn}
        first.pending = lambda cs: False
        asked = lambda cs: None
        asked.pending = lambda cs: True
        planes, _ = srv.build_planes(sky, 49.25, 6.2, 20, route_lookup=first, route_fallback=asked)
        self.assertIsNone(planes[0]["route"], "Berlin -> Stansted cannot be an aircraft over Metz heading south-east")
        self.assertEqual(planes[0]["pending"], ["route"], "hexdb is on its way: wait")
        came = lambda cs: [{"from": crl, "to": reg}]
        came.pending = lambda cs: False
        planes, _ = srv.build_planes(sky, 49.25, 6.2, 20, route_lookup=first, route_fallback=came)
        self.assertEqual(planes[0]["route"]["to"]["city"], "Reggio Calabria")
        self.assertEqual(planes[0]["pending"], [])


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
    sharing radius (15\u00a0km by default) for something over 50\u00a0km: it could never fire."""

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
        # 210\u00a0km from the receiver at 49.20 N 6.20 E: due east, ~2.86 degrees of longitude
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
        # the dots alone: since 0.24.0 only what a Pi without Pillow posts rather than nothing (every look has a map)
        self.addCleanup(setattr, social, "flap_module", social.flap_module); social.flap_module = lambda: None
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
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
        # 0.18.2 let an A380's ten minutes (165\u00a0km) run past the frame; every extent up to 500\u00a0km per bar fits now
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
                        " const lit = (y, a, b) => { let n = 0; for (let x = a; x < b; x++) n += g[y * R.GW + x] ? 1 : 0; return n; };"
                        " console.log(JSON.stringify({row: [...Array(16).keys()].map(y => lit(y, 0, 72)), clock: lit(72, 0, 72),"
                        " flag: [...Array(17).keys()].map(y => lit(y, 74, 87))}));" % json.dumps(EZY))
        rows = out["row"]
        # 0.20.0: the registration's flag (G-UZHA: the United Kingdom) beside the REG row, nothing beside the FLT row
        self.assertTrue(all(out["flag"][y] for y in range(7, 16)), out["flag"])
        self.assertTrue(not any(out["flag"][y] for y in range(0, 7)), out["flag"])
        self.assertTrue(all(rows[y] for y in range(0, 7)), rows)          # FLT  EZY1234
        self.assertEqual(rows[7], 0, rows)                                  # one dark row
        self.assertTrue(all(rows[y] for y in range(8, 15)), rows)          # REG  G-UZHA
        self.assertGreater(out["clock"], 0)

    def test_a_long_airline_stays_clear_of_the_registration_flag_s_outline(self):
        # 0.20.0: G-UZHA's flag (the United Kingdom, outlined) beside the REG row; its outline's last row is just
        # above the airline row, so a fourteen-letter airline must still stop before the flag column
        out = self.node("const g = new Uint32Array(R.GW * R.GH);"
                        " R.drawWall(g, %s, 'metric', '11:39 GMT+2', true);"
                        " let last = -1; for (let y = 16; y < 23; y++) for (let x = 0; x < R.GW; x++) if (g[y * R.GW + x]) last = Math.max(last, x);"
                        " let outline = 0; for (let x = 74; x < 87; x++) outline += g[15 * R.GW + x] ? 1 : 0;"
                        " console.log(JSON.stringify({last: last, outline: outline}));" % json.dumps(dict(EZY, airline="Virgin Atlantic")))
        self.assertGreater(out["outline"], 0, "the outline is drawn on the row above the airline")
        self.assertLess(out["last"], 74, "the airline's letters stop before it")

    def test_the_flags_are_whole_beside_the_track_panel(self):
        # 0.23.0, from a post: Eurowings D-AIDO, an Airbus. The German flag's white outline ends at dot 86, where the
        # track panel's frame was drawn over it; the panel now starts at 88. The EU flag (no outline) at 75 to 85.
        dido = dict(EZY, flight="EWG11S", registration="D-AIDO", type="A321", type_name="AIRBUS A-321", airline="Eurowings")
        out = self.node("const g = new Uint32Array(R.GW * R.GH);"
                        " R.drawWall(g, %s, 'metric', '12:16 GMT+2', true); R.drawTrack(g, %s, 110, R.THEMES.red);"
                        " const at = (x, y) => g[y * R.GW + x];"
                        " console.log(JSON.stringify({edge: [...Array(9).keys()].map(i => at(86, 7 + i)), eu: [...Array(7).keys()].map(i => at(80, 25 + i)),"
                        " gap: [...Array(68).keys()].map(y => at(87, y)), frame: at(88, 30), panel: R.PANEL}));" % (json.dumps(dido), json.dumps(trace(60))))
        self.assertEqual(out["edge"], [0xffffff] * 9, "the outline's right-hand column, top to bottom")
        self.assertTrue(all(out["eu"]), out["eu"])
        self.assertEqual(out["gap"], [0] * 68, "a dark column between the flags and the panel")
        self.assertTrue(out["frame"])
        self.assertEqual(out["panel"]["x"], 88)

    def test_an_empty_row_leaves_no_gap(self):
        # 0.25.1, from a post (TF-AKE): no registration and no model known, two blank rows on the picture. The rows
        # below move up; the flap board's too, the time staying last
        bare = {"hex": "4cc54b", "flight": "ABD2614", "airline": "Air Atlanta", "alt_ft": 30650, "gs_kt": 478,
                "route": {"from": {"city": "Liege"}, "to": {"city": "Port Harcourt"}}}
        out = self.node("const g = new Uint32Array(R.GW * R.GH); R.drawWall(g, %s, 'metric', '18:42 GMT+2', true);"
                        " const lit = (y) => { let n = 0; for (let x = 0; x < 72; x++) n += g[y * R.GW + x] ? 1 : 0; return n; };"
                        " console.log(JSON.stringify({rows: [...Array(70).keys()].map(lit)}));" % json.dumps(bare))
        rows = out["rows"]
        self.assertTrue(all(rows[y] for y in range(8, 15)), "the airline on the second row, not a blank REG row")
        self.assertEqual(sum(rows[61:70]), 0, "nothing left for the last rows: they were moved up")
        got = social._node({"plane": bare, "units": "metric", "clock": "18:42 GMT+2", "theme": "green", "cols": 14}, None, "--lines")
        self.assertEqual(got["lines"][:5], ["FLT  ABD2614", "AIR ATLANTA", "ALT  9340 M", "SPD  885 KMH", "LIEGE"])
        self.assertEqual(got["lines"][-1], "18:42 GMT+2")
        self.assertEqual(len(got["lines"]), 9)

    def test_the_legend_and_no_track_stay_inside_the_frame(self):
        # "100KM" is 29 dots: with the panel at 88 it must still end before the frame (dot 127); "NO TRACK" is 47 dots,
        # the panel 40, so it is two lines
        far = [[49.0, 4.0 + i * 0.02, 30000, i * 5] for i in range(121)]      # about 150 km in ten minutes: 100 km a bar
        out = self.node("const box = (t) => { const g = new Uint32Array(R.GW * R.GH); R.drawTrack(g, t, 90, R.THEMES.amber);"
                        " let lo = 999, hi = -1; for (let y = 1; y < 67; y++) for (let x = 0; x < R.GW; x++) { const v = g[y * R.GW + x];"
                        " if (v && v !== 0x404040 && v !== 0x2a2a2a) { lo = Math.min(lo, x); hi = Math.max(hi, x); } } return [lo, hi]; };"
                        " console.log(JSON.stringify({far: box(%s), none: box([]), scale: R.pickScaleKm(150)}));" % json.dumps(far))
        self.assertEqual(out["scale"], 100)
        self.assertGreater(out["far"][0], 88); self.assertLess(out["far"][1], 127)
        self.assertGreater(out["none"][0], 88); self.assertLess(out["none"][1], 127)

    def test_with_a_map_the_column_is_left_dark_and_its_place_is_given(self):
        if shutil.which(social.NODE) is None or social_card is None:
            self.skipTest("node or Pillow not installed here")
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        got = social._node({"plane": EZY, "trace": trace(60), "units": "metric", "theme": "turquoise", "clock": "12:16 GMT+2",
                            "flags": True, "pitch": 10, "map": True}, os.path.join(d, "dots.png"))
        self.assertEqual(got["map_box"], [15 + 880, 15, 400, 800])    # dots 88 to 127, the whole height, at pitch 10
        self.assertEqual(got["color"], "#00d6d7")
        lit = lambda path: sum(1 for p in Image.open(path).convert("RGB").crop((895, 15, 1295, 815)).getdata()
                               if p[0] < 90 and p[1] > 150 and p[2] > 150)
        self.assertEqual(lit(os.path.join(d, "dots.png")), 0, "no track in dots where the map goes")
        social._node({"plane": EZY, "trace": trace(60), "units": "metric", "theme": "turquoise", "clock": "12:16 GMT+2",
                      "flags": True, "pitch": 10}, os.path.join(d, "track.png"))
        self.assertGreater(lit(os.path.join(d, "track.png")), 0, "without a map, the track is drawn there")
        out = self.node("const g = new Uint32Array(R.GW * R.GH); R.drawWall(g, %s, 'metric', '12:16 GMT+2', true);"
                        " let lit = 0; for (let y = 0; y < R.GH; y++) for (let x = R.MAP_BOX.x; x < R.GW; x++) lit += g[y * R.GW + x] ? 1 : 0;"
                        " console.log(JSON.stringify({lit: lit}));" % json.dumps(dict(EZY, airline="Virgin Atlantic Airways")))
        self.assertEqual(out["lit"], 0, "nothing of the wall reaches the map's column")

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

    def test_the_photo_link_is_a_link_only_and_off_by_default(self):
        # 0.25.0, asked for by the owner: the aircraft's Planespotters photo page as the last line, with the
        # photographer's name, clickable; never the picture (their API terms), and nothing when there is no photo
        p = dict(EZY, photo_credit="Jane  Doe", photo_link="https://www.planespotters.net/photo/1234567/g-uzha-easyjet")
        self.assertEqual(social.photo_line(p, CFG), (None, []))
        on = dict(CFG, SOCIAL_PHOTOLINK="1")
        line, links = social.photo_line(p, on)
        self.assertEqual(line, "Photo: Jane Doe / Planespotters")
        self.assertEqual(links, [(line, p["photo_link"])])
        t = social.post_text(p, on, None, "Map \u00a9 OpenStreetMap, EOX", line)
        self.assertTrue(t.endswith("\nMap \u00a9 OpenStreetMap, EOX\nPhoto: Jane Doe / Planespotters"), t)
        f = [x for x in social.bluesky_facets(t, links) if x["features"][0].get("uri") == p["photo_link"]]
        self.assertEqual(len(f), 1)
        for bad in ("https://evil.example/photo/1", "http://www.planespotters.net/photo/1", ""):
            self.assertEqual(social.photo_line(dict(p, photo_link=bad), on), (None, []), bad)
        self.assertEqual(social.photo_line(dict(p, photo_credit=""), on), (None, []))
        # a text too long for both: the photo line goes, the text stays whole
        long = dict(p, route={"from": {"city": "X" * 120}, "to": {"city": "Y" * 120}})
        t = social.post_text(long, on, None, None, line)
        self.assertNotIn("Planespotters", t)

    def test_the_posts_have_their_own_units(self):
        # 0.24.3, asked for by the owner: imperial posts whatever the wall shows, or the wall's own units by default
        self.assertEqual(social.units_of({"UNITS": "metric"}), "metric")
        self.assertEqual(social.units_of({"UNITS": "metric", "SOCIAL_UNITS": "imperial"}), "imperial")
        self.assertEqual(social.units_of({"UNITS": "imperial", "SOCIAL_UNITS": ""}), "imperial")
        self.assertEqual(social.units_of({"SOCIAL_UNITS": "feet"}), "metric")
        t = social.post_text(EZY, dict(CFG, UNITS="metric", SOCIAL_UNITS="imperial"))
        self.assertIn("altitude 37\u00a0000\u00a0ft", t)

    def test_the_picture_s_colour_setting(self):
        self.assertEqual(social.theme_of({"THEME": "red"}), "red")                          # the wall's, by default
        self.assertEqual(social.theme_of({"THEME": "red", "SOCIAL_THEME": "turquoise"}), "turquoise")
        self.assertEqual(social.theme_of({"THEME": "red", "SOCIAL_THEME": "blue"}), "red")   # gone in 0.23.0: the wall's
        self.assertEqual(social.theme_of({"THEME": "red", "SOCIAL_THEME": "pink"}), "red")  # not a colour: ignored
        self.assertEqual(social.style_of({"SOCIAL_STYLE": "FLAP"}), "flap")
        self.assertEqual(social.style_of({"SOCIAL_STYLE": "dotmap"}), "dotmap")
        self.assertEqual(social.style_of({"SOCIAL_STYLE": "photo"}), "dotmap")
        self.assertEqual(social.style_of({"SOCIAL_STYLE": "dots"}), "dotmap")   # taken out in 0.24.0, at the owner's word
        self.assertEqual(social.style_of({}), "dotmap")
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
        self.assertIn("EOxCloudless", info["credit"])
        self.assertIn(("EOxCloudless", "https://cloudless.eox.at"), info["links"])
        self.assertEqual({a[0] for a in asked}, {"s2cloudless-%d_3857" % social_card.S2_YEAR})    # names: ours (0.24.4)

    def test_the_towns_are_named_on_the_satellite_and_terrain_maps(self):
        # 0.24.4, from real posts over Metz: EOX's label layer named one village (Amnéville) in forty kilometres. The
        # towns of 5 000 or more from GeoNames are named instead, the largest first, never under another name
        names = []
        real = social_card.ImageDraw.ImageDraw.text
        def spy(d, xy, text, *a, **k):
            names.append(text)
            return real(d, xy, text, *a, **k)
        self.addCleanup(setattr, social_card.ImageDraw.ImageDraw, "text", real)
        social_card.ImageDraw.ImageDraw.text = spy
        metz = [[48.95 + i * 0.0125, 6.2, 30000, i * 5] for i in range(37)]
        img, shown = social_card.draw_map(metz, dict(EZY, track=2), "#ff0000", mode="terrain",
                                          fetch=lambda *a: fake_tile("terrain_3857", "jpg", 1, 1, 1))
        self.assertEqual(shown, "terrain")
        self.assertTrue({"Metz", "Thionville", "Talange", "Woippy"} <= set(names), names)
        self.assertNotIn("Hayange", names, "0.28.0: 10 km off a track along the Moselle, not named when the track's surroundings give enough")
        # 0.25.3: the two OpenStreetMap maps too, whose own labels were unreadable once reduced on the real posts
        for mode in ("normal", "night"):
            del names[:]
            img, shown = social_card.draw_map(metz, EZY, "#ff0000", mode=mode, fetch=lambda *a: fake_tile("osm_3857", "jpg", 1, 1, 1))
            self.assertEqual(shown, mode)
            self.assertIn("Metz", names, mode)
        del names[:]
        social_card.draw_map(metz, EZY, "#ff0000", mode="none", fetch=lambda *a: None)
        self.assertNotIn("Metz", names, "no map, no names")

    def test_villages_on_a_map_short_of_towns(self):
        # 0.26.2, a real post: DAH1217, two minutes after leaving Metz-Nancy, on a 20 km strip east of the Moselle:
        # no town of 5 000 in it, so no name at all. Villages of 1 000 to 4 999 fill in, only on such a map.
        names = []
        real = social_card.ImageDraw.ImageDraw.text
        def spy(d, xy, text, *a, **k):
            names.append(text)
            return real(d, xy, text, *a, **k)
        self.addCleanup(setattr, social_card.ImageDraw.ImageDraw, "text", real)
        social_card.ImageDraw.ImageDraw.text = spy
        east = [[49.12 + i * 0.0053, 6.37 - i * 0.0057, 3000, i * 5] for i in range(25)]     # Courcelles-Chaussy to Vigy
        social_card.draw_map(east, EZY, "#00e0e0", mode="normal", w=420, h=840,
                             fetch=lambda *a: fake_tile("terrain-light_3857", "jpg", 1, 1, 1))
        self.assertIn("Vigy", names)
        self.assertIn("Courcelles-Chaussy", names)
        del names[:]
        metz = [[48.95 + i * 0.0125, 6.2, 30000, i * 5] for i in range(37)]                   # Metz, Thionville, plenty
        social_card.draw_map(metz, EZY, "#ff0000", mode="terrain", fetch=lambda *a: fake_tile("terrain_3857", "jpg", 1, 1, 1))
        self.assertIn("Metz", names)
        self.assertNotIn("Vigy", names, "a map with towns enough takes no village")
        self.assertEqual(social_card._small_places(49.20, 49.21, 6.29, 6.31)[0][0], "Vigy")
        self.assertAlmostEqual(social_card._lat_of(social_card.world_px(49.2, 6.3, 10)[1], 10), 49.2, places=6)

    def test_no_town_is_named_twice(self):
        # 0.26.1, from the real posts (EWG8QR over Nancy): the names ZenithBoard draws went over EOX's OpenStreetMap
        # layer, which writes its own: every town twice, a few pixels apart. A map that names its towns draws on
        # layers that carry no name.
        unnamed = {"terrain-light_3857", "streets_3857", "terrain_3857", "s2cloudless-%d_3857" % social_card.S2_YEAR}
        for mode, st in social_card.MAP_STYLES.items():
            if st.get("names"):
                self.assertTrue({l for l, _ in st["layers"]} <= unnamed, mode)
                self.assertIn("GeoNames", st["credit_full"], mode)
        road = Image.new("RGBA", (4, 1), (255, 255, 255, 255)); road.putpixel((0, 0), (120, 120, 120, 255))
        t = social_card.tint(road, (214, 140, 60))
        self.assertEqual(t.getpixel((1, 0)), (214, 140, 60, 255), "a white road takes the colour")
        self.assertLess(t.getpixel((0, 0))[0], 214, "its grey edge stays darker")

    def test_the_names_are_drawn_over_the_track(self):
        # 0.25.3, from the real posts: the track cut letters out of the towns it crossed ("N ncy"). The names now come
        # after the track; each town's dot stays where the town is.
        order = []
        real_text, real_line = social_card.ImageDraw.ImageDraw.text, social_card.ImageDraw.ImageDraw.line
        def text(d, xy, t, *a, **k):
            order.append(("name", t)); return real_text(d, xy, t, *a, **k)
        def line(d, xy, *a, **k):
            order.append(("line", None)); return real_line(d, xy, *a, **k)
        self.addCleanup(setattr, social_card.ImageDraw.ImageDraw, "text", real_text)
        self.addCleanup(setattr, social_card.ImageDraw.ImageDraw, "line", real_line)
        social_card.ImageDraw.ImageDraw.text, social_card.ImageDraw.ImageDraw.line = text, line
        metz = [[48.95 + i * 0.0125, 6.2, 30000, i * 5] for i in range(37)]
        social_card.draw_map(metz, EZY, "#ff0000", mode="terrain", fetch=lambda *a: fake_tile("terrain_3857", "jpg", 1, 1, 1))
        first_name = order.index(("name", "Metz"))
        self.assertIn(("line", None), order[:first_name], "the track is drawn before the names")

    def _dots(self, **kw):
        if shutil.which(social.NODE) is None:
            self.skipTest("node not installed here")
        png = os.path.join(self.d, "dots.png")
        spec = dict({"plane": dict(EZY, registration="D-AIDO", type_name="AIRBUS A-321"), "trace": trace(60), "units": "metric",
                     "theme": "red", "clock": "12:16 GMT+2", "flags": True, "pitch": 10, "map": True}, **kw)
        return png, social._node(spec, png)

    def test_the_dot_matrix_wall_beside_a_map(self):
        # 0.23.0, asked for by the owner: the dots-only map mock-up gives way to the real map, beside the dot wall
        png, got = self._dots()
        out = os.path.join(self.d, "p.jpg")
        asked = []
        info = social_card.render_dotmap(png, got["map_box"], trace(60), EZY, out, got["color"], map_mode="night",
                                         fetch=lambda *a: asked.append(a) or fake_tile(*a))
        with open(out, "rb") as fh:
            self.assertEqual(fh.read(3), b"\xff\xd8\xff")
        self.assertEqual((info["width"], info["height"]), (1310, 830))
        self.assertLess(info["bytes"], 1000000)
        self.assertEqual(info["map"], "night"); self.assertEqual(info["credit"], "Map \u00a9 OpenStreetMap, EOX, GeoNames")
        self.assertEqual({a[0] for a in asked}, {"terrain-light_3857", "streets_3857"})   # 0.26.1: no layer with names of its own
        im = Image.open(out).convert("RGB")
        x, y, w, h = got["map_box"]
        self.assertGreater(sum(im.getpixel((x + w // 2, y + 40))), 60, "the map is there, not the dark column")
        self.assertGreater(min(im.getpixel((15 + 865, 15 + 105))), 190, "the German flag's outline, right edge, still white")

    def test_the_service_draws_it_and_posts_the_jpeg_alone(self):
        orig, social_card.fetch_tile = social_card.fetch_tile, (lambda layer, ext, z, x, y, *a, **k: fake_tile(layer, ext, z, x, y))
        self.addCleanup(setattr, social_card, "fetch_tile", orig)
        self.addCleanup(setattr, social, "STATE_DIR", social.STATE_DIR); social.STATE_DIR = self.d
        if shutil.which(social.NODE) is None:
            self.skipTest("node not installed here")
        base = os.path.join(self.d, "post")
        info = social.render(EZY, trace(60), dict(CFG, SOCIAL_STYLE="dotmap", SOCIAL_MAP="terrain"), base)
        self.assertEqual((info["mime"], info["path"]), ("image/jpeg", base + ".jpg"))
        self.assertFalse(os.path.exists(base + ".png"), "the dots alone are not left behind")
        self.assertEqual(info["map"], "terrain")
        a = social.alt_text(EZY, CFG, trace(60), "dotmap", info)
        self.assertTrue(a.startswith("Dot-matrix flight board"), a)
        self.assertIn("Beside it, a terrain map with the aircraft's track", a)
        # no map wanted: the dot-matrix wall with its track on black, nothing fetched (0.24.0: no longer the dots look)
        asked = []
        social_card.fetch_tile = lambda *a, **k: asked.append(a)
        info = social.render(EZY, trace(60), dict(CFG, SOCIAL_STYLE="dotmap", SOCIAL_MAP="none"), os.path.join(self.d, "q"))
        self.assertEqual((info["mime"], info["map"], info["credit"]), ("image/jpeg", "none", None))
        self.assertEqual(asked, [], "map none fetches nothing")

    def test_the_aircraft_is_never_under_the_legend(self):
        # 0.23.0: on the dotmap's narrow map (400 by 800) a southbound track ended under the legend box, the aircraft
        # hidden; the view is now chosen above the legend and credit band. The flap map is held to the same.
        south = [[49.9 - i * 0.008, 6.2, 36000, 1000 + i * 5] for i in range(120)]
        at = []
        icon = social_card._icon
        self.addCleanup(setattr, social_card, "_icon", icon)
        social_card._icon = lambda d, x, y, *a, **k: at.append(y / 3.0) or icon(d, x, y, *a, **k)   # drawn 3x, reduced
        light = lambda *a: fake_tile("osm_3857", "jpg", 1, 1, 1)
        for w, h in ((400, 800), (social_card.MAP_W, social_card.MAP_H)):
            del at[:]
            img, shown = social_card.draw_map(south, dict(EZY, track=180), "#ff0000", fetch=light, w=w, h=h)
            self.assertEqual(shown, "normal")
            top = next(y for y in range(4, h) if sum(img.getpixel((14, y))) < 300)     # the legend box's top edge
            self.assertLess(top, h - 74, (w, h))
            self.assertLess(at[0] + 22, top, "the aircraft (22 px across its centre) is above the legend, %dx%d" % (w, h))

    def test_no_tile_no_map_no_credit(self):
        info = social_card.render(self.LINES, trace(60), EZY, os.path.join(self.d, "p.jpg"), map_mode="normal", fetch=lambda *a: None)
        self.assertEqual(info["map"], "none")
        self.assertIsNone(info["credit"])
        asked = []
        info = social_card.render(self.LINES, trace(60), EZY, os.path.join(self.d, "q.jpg"), map_mode="none",
                                  fetch=lambda *a: asked.append(a))
        self.assertEqual(info["map"], "none")
        self.assertEqual(asked, [], "map none fetches nothing")       # a failure inside fetch would be swallowed

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
        # a 160\u00a0km track still fits, farther out
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
        self.assertIn("OpenStreetMap, EOX", social.post_text(EZY, c, None, info["credit"]))


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
        self.refuse = []                                # urls to answer once with an expired token
        self.old = urllib.request.urlopen
        social._SESSION.clear()
        self.addCleanup(social._SESSION.clear)
        test = self

        def fake(req, timeout=None):
            url = req.full_url
            test.sent.append((url, dict(req.header_items()), req.data))
            name = url.split("/")[-1]
            if name in test.refuse:
                test.refuse.remove(name)
                raise urllib.error.HTTPError(url, 400, "Bad Request", {}, io.BytesIO(b'{"error":"ExpiredToken","message":"Token has expired"}'))
            if url.endswith("createSession"):
                return FakeResponse({"accessJwt": "jwt-abc", "refreshJwt": "ref-1", "did": "did:plc:xyz", "handle": "zb.bsky.social"})
            if url.endswith("refreshSession"):
                return FakeResponse({"accessJwt": "jwt-new", "refreshJwt": "ref-2", "did": "did:plc:xyz", "handle": "zb.bsky.social"})
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
        uri = social.post_bluesky(sec, "✈ easyJet · 11\u00a0280\u00a0m\n#ADSB #ZenithBoard", self.png, "alt here", 1310, 830)
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
        text = "Flight easyJet #EZY1234 \u00b7 altitude 11\u00a0280\u00a0m\n#ADSB\nMap \u00a9 OpenStreetMap, EOX"
        social.post_bluesky(sec, text, self.png, "alt", 1500, 900, "image/jpeg", [("OpenStreetMap", "https://www.openstreetmap.org/copyright"), ("EOX", "https://maps.eox.at")])
        self.assertEqual(self.sent[1][1]["Content-type"], "image/jpeg")
        rec = json.loads(self.sent[2][2])["record"]
        links = [f for f in rec["facets"] if f["features"][0]["$type"].endswith("#link")]
        self.assertEqual(len(links), 2)
        got = {rec["text"].encode("utf-8")[f["index"]["byteStart"]:f["index"]["byteEnd"]]: f["features"][0]["uri"] for f in links}
        self.assertEqual(got, {b"OpenStreetMap": "https://www.openstreetmap.org/copyright", b"EOX": "https://maps.eox.at"})
        starts = [f["index"]["byteStart"] for f in rec["facets"]]
        self.assertEqual(starts, sorted(starts))

    def names(self):
        return [s[0].split("/")[-1].split(".")[-1] for s in self.sent]

    def test_one_sign_in_for_many_posts(self):
        # Bluesky allows 300 sign-ins a day: with every crossing posted, signing in for each post could pass it
        sec = {"BLUESKY_HANDLE": "zb.bsky.social", "BLUESKY_APP_PASSWORD": "x"}
        for _ in range(5):
            social.post_bluesky(sec, "a post", self.png, "alt", 1310, 830)
        self.assertEqual(self.names().count("createSession"), 1)
        self.assertEqual(self.names().count("createRecord"), 5)

    def test_after_an_hour_the_session_is_refreshed_not_signed_in_again(self):
        sec = {"BLUESKY_HANDLE": "zb.bsky.social", "BLUESKY_APP_PASSWORD": "x"}
        social.post_bluesky(sec, "a post", self.png, "alt", 1310, 830)
        social._SESSION["at"] -= social.SESSION_REUSE_S + 1
        social.post_bluesky(sec, "a post", self.png, "alt", 1310, 830)
        self.assertEqual(self.names().count("createSession"), 1)
        self.assertEqual(self.names().count("refreshSession"), 1)
        refresh = next(s for s in self.sent if s[0].endswith("refreshSession"))
        self.assertEqual(refresh[1]["Authorization"], "Bearer ref-1")
        self.assertEqual(self.sent[-1][1]["Authorization"], "Bearer jwt-new")

    def test_a_refused_token_signs_in_again_once(self):
        sec = {"BLUESKY_HANDLE": "zb.bsky.social", "BLUESKY_APP_PASSWORD": "x"}
        social.post_bluesky(sec, "a post", self.png, "alt", 1310, 830)
        self.refuse.append("com.atproto.repo.uploadBlob")
        self.assertTrue(social.post_bluesky(sec, "a post", self.png, "alt", 1310, 830).startswith("at://"))
        self.assertEqual(self.names().count("createSession"), 2)
        self.refuse.extend(["com.atproto.repo.uploadBlob", "com.atproto.repo.uploadBlob"])
        with self.assertRaises(urllib.error.HTTPError):
            social.post_bluesky(sec, "a post", self.png, "alt", 1310, 830)   # refused twice: not a loop of sign-ins
        self.assertEqual(self.names().count("createSession"), 3)

    def test_another_account_in_the_file_signs_in_again(self):
        social.post_bluesky({"BLUESKY_HANDLE": "zb.bsky.social", "BLUESKY_APP_PASSWORD": "x"}, "a", self.png, "alt", 1, 1)
        social.post_bluesky({"BLUESKY_HANDLE": "zb.bsky.social", "BLUESKY_APP_PASSWORD": "new-one"}, "a", self.png, "alt", 1, 1)
        self.assertEqual(self.names().count("createSession"), 2)

    def test_check_the_account(self):
        self.assertTrue(social.check_bluesky({"BLUESKY_HANDLE": "zb.bsky.social", "BLUESKY_APP_PASSWORD": "x"}).startswith("ok"))
        self.assertFalse(social.bluesky_ready({"MASTODON_URL": "https://m.example", "MASTODON_TOKEN": "t"}),
                         "Mastodon is gone (0.19.0): its secrets alone are no account")

    def test_secrets_are_never_in_the_text(self):
        sec = {"BLUESKY_HANDLE": "zb.bsky.social", "BLUESKY_APP_PASSWORD": "aaaa-bbbb-cccc-dddd"}
        social.post_bluesky(sec, "hello", self.png, "alt", 1, 1)
        for url, hdr, data in self.sent[1:]:
            self.assertNotIn(b"aaaa-bbbb", data or b"")


class FacetTest(unittest.TestCase):
    """0.50.0, for every post since 0.51.0: hashtags and links written in the text, found as the Bluesky app finds them
    (an owner's template can carry #Trémery or a link)."""

    def test_accents_kept_byte_offsets_and_the_sentence_left_out(self):
        text = "Le bilan part à 08:45 #Trémery #avgeek! Voir https://bsky.app/profile/zenithboard.bsky.social."
        facets, tags, links = social.text_facets(text)
        got = [text.encode("utf-8")[f["index"]["byteStart"]:f["index"]["byteEnd"]].decode("utf-8") for f in facets]
        self.assertEqual(got, ["#Trémery", "#avgeek", "https://bsky.app/profile/zenithboard.bsky.social"])
        self.assertEqual(facets[0]["features"][0], {"$type": "app.bsky.richtext.facet#tag", "tag": "Trémery"})

    def test_what_is_not_a_hashtag_or_a_link(self):
        _, tags, links = social.text_facets("Vol#1 ok #2026 #a_b (see https://example.org/a_(b)) http:// #" + "x" * 65)
        self.assertEqual(tags, ["#a_b"], "not inside a word, not digits alone, not longer than 64")
        self.assertEqual(links, ["https://example.org/a_(b)"], "a closing bracket of its own kept, the sentence's left out")
        # a uri Bluesky would refuse (the whole post with it), facets overlapping, a tag carrying an invisible
        # character the Bluesky app leaves out
        facets, tags, links = social.text_facets("https:///foo https://x #x(https://a.org) #avgeek\u200b #\ufe0f\u20e3 #soft\u00adhyphen u\ufeffhttps://b.org")
        self.assertEqual(links, ["https://a.org"])
        self.assertEqual(tags, ["#avgeek", "#soft"])
        ends = [(f["index"]["byteStart"], f["index"]["byteEnd"]) for f in facets]
        self.assertTrue(all(a[1] <= b[0] for a, b in zip(ends, ends[1:])), "in order, never overlapping: %s" % ends)

    def test_the_links_given_win_over_what_is_found(self):
        text = "Flight #EZY1234 \u00b7 #ADSB\nMap \u00a9 OpenStreetMap, EOX"
        f = social.bluesky_facets(text, [("EOX", "https://maps.eox.at")])
        kinds = [x["features"][0]["$type"].split("#")[1] for x in f]
        self.assertEqual(kinds, ["tag", "tag", "link"])


class CustomTemplateTest(unittest.TestCase):
    """0.51.0, the owner's word: posts in his own words, with tags, as one more style ("custom")."""
    RYR = SentenceTest.RYR
    C = dict(CFG, SOCIAL_AREA="Trémery", SOCIAL_HASHTAGS="#ADSB #avgeek", SOCIAL_SENTENCE="custom")

    def setUp(self):
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        self.path = os.path.join(d, "social-templates.txt")
        self.addCleanup(setattr, social, "TEMPLATES_FILE", social.TEMPLATES_FILE)
        social.TEMPLATES_FILE = self.path

    def write(self, *lines):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    def test_the_template_is_the_post_its_hashtags_after(self):
        self.write("{airline} {flight}[, {from} → {to}] at {altitude}. {why}")
        t = social.post_text(self.RYR, self.C, "rare")
        self.assertEqual(t.split("\n"), ["Ryanair RYR5ZK, Brussels → Pisa at 10\u00a0570\u00a0m. A rare visitor.", "#ADSB #avgeek"])

    def test_a_template_that_places_the_hashtags_gets_them_once(self):
        self.write("{airline} {flight} {hashtags}")
        self.assertEqual(social.post_text(self.RYR, self.C, None), "Ryanair RYR5ZK #ADSB #avgeek")

    def test_an_empty_tag_takes_its_part_away(self):
        self.write("{airline}[, {from} → {to}][, squawk {squawk}].")
        self.assertEqual(social.post_text(dict(self.RYR, route={}), self.C, None).split("\n")[0], "Ryanair.")

    def test_the_template_drawn_says_where_the_hashtags_go(self):
        # found in review (0.51.0): the check looked at every template, so one without {hashtags} lost them
        self.write("{airline} {flight} {hashtags}", "{airline} {flight}, no tags")
        import random as r
        self.addCleanup(setattr, social.random, "choice", r.choice)
        social.random.choice = lambda seq: seq[min(1, len(seq) - 1)]      # the style (one), then the second template
        self.assertEqual(social.post_text(self.RYR, self.C, None).split("\n"), ["Ryanair RYR5ZK, no tags", "#ADSB #avgeek"])
        social.random.choice = lambda seq: seq[0]
        heli = dict(self.RYR, shape="heli")
        self.assertEqual(social.post_text(heli, self.C, None), "Ryanair RYR5ZK #ADSB #helicopter", "the template's hashtags as the line's")

    def test_any_aircraft_takes_the_template(self):
        self.write("[{registration} ]{category}[ at {altitude}]")
        bare = {"hex": "abc123", "flight": "", "registration": "D-EABC", "alt_ft": 3000}
        self.assertEqual(social.post_text(bare, self.C, None).split("\n")[0], "D-EABC aircraft at 910\u00a0m")

    def test_the_maps_credit_is_never_cut(self):
        # found in review: a long template and the terrain map's credit (46 characters) went past 300, and the cut
        # took the credit's end, and its link
        credit = "Map \u00a9 OpenStreetMap and others, EOX, GeoNames"
        t = social.fit_post("x" * 280, credit, "#ADSB")
        self.assertLessEqual(len(t), 300)
        self.assertTrue(t.endswith("\n" + credit), t[-60:])
        self.assertIn("\u2026", t)
        self.assertLessEqual(social.TEMPLATE_MAX + 1 + len(credit), 300)

    def test_a_file_not_in_utf8_never_stops_a_post(self):
        with open(self.path, "wb") as fh:
            fh.write(b"{airline} caf\xe9\n")
        self.assertTrue(social.post_text(self.RYR, self.C, None).startswith("Ryanair caf"))
        self.assertTrue(social.post_text(self.RYR, dict(self.C, SOCIAL_SENTENCE="factual"), None).startswith("Flight Ryanair"))

    def test_no_usable_template_is_the_factual_words(self):
        self.write("{airline} {nope}", "{airline}[ {from}")
        self.assertEqual(social.custom_templates(self.C), [])
        self.assertEqual(social.sentences_of(self.C), ["factual"], "custom asked for, nothing usable")
        self.assertTrue(social.post_text(self.RYR, self.C, None).startswith("Flight Ryanair #RYR5ZK"))
        self.write("{airline} " + "x" * 300)
        self.assertTrue(social.post_text(self.RYR, self.C, None).startswith("Flight Ryanair"), "too long: factual")

    def test_chosen_with_the_others_and_by_random(self):
        self.assertNotIn("custom", social.sentences_of({"SOCIAL_SENTENCE": "random"}), "no template yet")
        self.write("{airline}")
        self.assertEqual(social.sentences_of({"SOCIAL_SENTENCE": "story,custom"}), ["story", "custom"])
        self.assertIn("custom", social.sentences_of({"SOCIAL_SENTENCE": "random"}))

    def test_no_tag_gives_the_receiver_away(self):
        v = social.template_values(dict(self.RYR, track=135, vrate_fpm=900, squawk="7700", lat=49.2077, lon=6.2183),
                                   dict(self.C, LAT="49.2401", LON="6.1985"), "rare", social.post_lang.get("en"))
        self.assertEqual(sorted(v), sorted(social.TEMPLATE_TAGS))
        self.assertEqual((v["heading"], v["climb"], v["squawk"], v["category"]), ("south-east", "climbing", "7700", "airliner"))
        for value in v.values():
            self.assertNotIn("6.2", value)
            self.assertNotIn("49.2", value, "neither the aircraft's position nor the receiver's")
            self.assertNotIn("300", value.replace("#", ""), "the bearing, 300, nowhere")
        self.assertFalse({"distance", "bearing", "lat", "lon", "position"} & set(social.TEMPLATE_TAGS))

    def test_a_template_too_long_with_long_names_is_refused_when_saved(self):
        ok = "{airline} {flight}[, {from} → {to}]"
        long = "{airline} {airline_country} {flag} {type} {category} {from} {to} {altitude} {speed} {why} {area} {photo} {tracker} " + "y" * 40
        bad = social.template_problems(ok + "\n" + long, self.C)
        self.assertEqual([b[0] for b in bad], [long])
        self.assertIn("with long names", bad[0][1])

    def test_the_posts_language_declared_to_bluesky(self):
        n = NetworksTest()
        n.setUp = NetworksTest.setUp.__get__(self)
        n.setUp()
        social.post_bluesky({"BLUESKY_HANDLE": "zb.bsky.social", "BLUESKY_APP_PASSWORD": "x"}, "Vol", self.png, "alt", 1, 1, lang="fr")
        self.assertEqual(json.loads(self.sent[-1][2])["record"]["langs"], ["fr"])


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


class CrossingTest(unittest.TestCase):
    """One post per crossing of the sharing radius (0.20.0): never twice for the same crossing, again for the next."""

    def setUp(self):
        self.t0 = time.time() - 3 * 86400
        self.st = warm()
        self.tracks = social.Tracks()
        for pt in trace(8, self.t0 - 40):
            self.tracks.feed([{"hex": EZY["hex"], "lat": pt[0], "lon": pt[1], "alt_baro": pt[2], "seen_pos": 0}], pt[3])

    def feed_at(self, t):
        for pt in trace(8, t - 40):
            self.tracks.feed([{"hex": EZY["hex"], "lat": pt[0] + (t - self.t0) * 1e-7, "lon": pt[1], "alt_baro": pt[2], "seen_pos": 0}], pt[3])

    def wanted(self, p, t):
        self.feed_at(t)
        return social.choose([p], self.tracks, {"all"}, self.st, t)

    def test_a_slow_aircraft_inside_for_an_hour_and_a_half_is_one_post(self):
        social.remember(self.st, EZY, self.t0)
        for m in range(0, 90):                                  # inside the radius, seen every minute
            t = self.t0 + m * 60
            social.note_seen(self.st, [{"hex": EZY["hex"].upper()}], t)
            social.prune_state(self.st, t)
        self.assertIsNone(self.wanted(EZY, self.t0 + 90 * 60))

    def test_out_of_the_radius_a_few_minutes_and_back_is_the_same_crossing(self):
        # the owner's words: the same aircraft must not be posted again five minutes after it left the radius
        social.remember(self.st, EZY, self.t0)
        social.note_seen(self.st, [EZY], self.t0 + 120)          # last seen inside two minutes after the post
        for t in (self.t0 + 120 + 5 * 60, self.t0 + 120 + 30 * 60, self.t0 + 120 + 59 * 60):
            social.prune_state(self.st, t)
            self.assertIsNone(self.wanted(EZY, t), "back %d min after it left: the same crossing" % ((t - self.t0 - 120) / 60))

    def test_the_next_day_or_after_an_hour_away_is_a_new_crossing(self):
        social.remember(self.st, EZY, self.t0)
        social.note_seen(self.st, [EZY], self.t0 + 120)
        later = self.t0 + 120 + social.CROSSING_GAP_S + 60
        social.prune_state(self.st, later)
        self.assertIsNotNone(self.wanted(EZY, later), "an hour out of the radius: this is another crossing")
        self.assertIsNotNone(self.wanted(EZY, self.t0 + 86400), "the next day")

    def test_the_return_flight_under_another_callsign_is_a_new_crossing(self):
        social.remember(self.st, EZY, self.t0)
        back = dict(EZY, flight="EZY1235")
        self.assertIsNotNone(self.wanted(back, self.t0 + 600), "a new callsign is another flight, even soon after")
        self.assertIsNone(self.wanted(dict(EZY, flight=""), self.t0 + 600), "the callsign lost for a while: the same flight")
        st2 = warm(); social.remember(st2, dict(EZY, flight=""), self.t0)
        self.assertTrue(social.already_posted(st2, EZY), "the callsign found later: the same flight")

    def test_the_memory_of_0_19_is_read(self):
        self.st["posted"] = {EZY["hex"]: self.t0}
        social.prune_state(self.st, self.t0 + 60)
        self.assertEqual(self.st["posted"][EZY["hex"]], {"t": self.t0, "flight": ""})
        self.assertIsNone(self.wanted(EZY, self.t0 + 60))

    def test_no_cap_every_crossing_is_posted(self):
        self.assertEqual(social.DEFAULTS["SOCIAL_GAP_MIN"], "0")
        self.assertEqual(social.gap_min(social.DEFAULTS), 0)
        self.assertEqual(social.gap_min({"SOCIAL_GAP_MIN": "1"}), 1, "no floor any more: what is set is what holds")
        self.assertEqual(social.gap_min({"SOCIAL_GAP_MIN": "-5"}), 0)
        self.assertIn("every crossing", social.gap_words({"SOCIAL_GAP_MIN": "0"}))
        self.assertEqual(social.gap_words({"SOCIAL_GAP_MIN": "30"}), "30 min")

    def test_a_busy_sky_is_posted_in_the_order_it_flew_over(self):
        other = dict(EZY, hex="4071f2", flight="EZY999")
        for pt in trace(8, self.t0 - 40):
            self.tracks.feed([{"hex": other["hex"], "lat": pt[0], "lon": pt[1], "alt_baro": pt[2], "seen_pos": 0}], pt[3])
        self.tracks.note_inside([other], self.t0 - 30)
        self.tracks.note_inside([EZY, other], self.t0)
        self.assertEqual(social.choose([EZY, other], self.tracks, {"all"}, self.st, self.t0)[2]["hex"], other["hex"],
                         "the same score: the one inside first goes first")


class LatePostTest(unittest.TestCase):
    """An aircraft that left the radius before its turn is still posted, once (0.20.0)."""

    def test_one_that_left_is_asked_about_and_posted(self):
        st, tracks, now = warm(), social.Tracks(), time.time()
        for pt in trace(8, now - 40):
            tracks.feed([{"hex": EZY["hex"], "lat": pt[0], "lon": pt[1], "alt_baro": pt[2], "seen_pos": 0}], pt[3])
        asked = []
        walls = [[dict(EZY, pending=["route"])], []]              # inside at the first look, its route on the way;
        for name, fake in (("ask_wall", lambda c, r: walls.pop(0)),  # gone at the second
                           ("ask_wall_one", lambda c, h: asked.append(h) or dict(EZY, distance_km=18))):
            self.addCleanup(setattr, social, name, getattr(social, name))
            setattr(social, name, fake)
        c = dict(CFG, SOCIAL_RULES="all", LAT="0", LON="0")
        planes, best = social.one_poll(c, st, tracks, [], now)
        self.assertIsNone(best, "its route is still being looked up: it waits")
        planes, best = social.one_poll(c, st, tracks, [], now + 15)
        self.assertEqual(asked, [EZY["hex"]])
        self.assertIsNotNone(best, "it left the radius: asked where it is, and posted")
        self.assertTrue(best[2].get("_late"))
        social.remember(st, best[2], now + 20)
        asked.clear()
        social.ask_wall = lambda c, r: []
        social.one_poll(c, st, tracks, [], now + 30)
        self.assertEqual(asked, [], "posted: not asked about again")

    def test_one_not_worth_a_post_is_not_followed(self):
        st, tracks, now = warm(), social.Tracks(), time.time()
        asked = []
        walls = [[dict(EZY)], []]
        for name, fake in (("ask_wall", lambda c, r: walls.pop(0)), ("ask_wall_one", lambda c, h: asked.append(h))):
            self.addCleanup(setattr, social, name, getattr(social, name))
            setattr(social, name, fake)
        c = dict(CFG, SOCIAL_RULES="military", LAT="0", LON="0")
        social.one_poll(c, st, tracks, [], now)
        social.one_poll(c, st, tracks, [], now + 15)
        self.assertEqual(asked, [], "an airliner under the military rule: nothing to follow once it has left")

    def test_forgotten_after_late_s(self):
        tracks = social.Tracks()
        tracks.note_inside([EZY], 1000.0)
        tracks.note_inside([], 1000.0 + social.LATE_S + 1)
        self.assertEqual(tracks.inside, {})


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


class NoCapTest(unittest.TestCase):
    def test_two_aircraft_one_after_the_other_are_both_posted_and_each_once(self):
        import contextlib
        import io
        start = 1800000000.0
        clock = [start]
        posted = []

        class Stop(Exception):
            pass

        def fake_sleep(sec):
            clock[0] += sec
            if clock[0] > start + 10 * 60:
                raise Stop()

        def poll(c, st, tr, ac, now):
            planes = [EZY, BELUGA] if now < start + 5 * 60 else [BELUGA]
            return planes, social.choose(planes, FakeTracks(), {"all"}, st, now)
        for name, fake in (("read_aircraft", lambda c: []), ("account", lambda: {"BLUESKY_HANDLE": "h", "BLUESKY_APP_PASSWORD": "p"}),
                           ("one_poll", poll), ("load_state", warm), ("save_state", lambda st: None), ("cfg", lambda: dict(CFG)),
                           ("publish", lambda p, *a, **k: posted.append((clock[0], p["hex"])) or {"bluesky": "at://x"})):
            self.addCleanup(setattr, social, name, getattr(social, name))
            setattr(social, name, fake)
        self.addCleanup(setattr, time, "time", time.time); time.time = lambda: clock[0]
        self.addCleanup(setattr, time, "sleep", time.sleep); time.sleep = fake_sleep
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(Stop):
                social.cmd_run()
        self.assertEqual(sorted(h for _, h in posted), sorted([EZY["hex"], BELUGA["hex"]]), "each crossing once, none skipped")
        self.assertLess(posted[1][0] - posted[0][0], 15, "no gap by default: the second straight after the first")


class FakeTracks(object):
    def of(self, h):
        return trace(8)

    def entered(self, h):
        return 0

    pending_since = {}


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
                social.remember_post(EZY, clock[0])
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

    def test_node_says_its_own_memory(self):
        # 0.19.10: the hourly line read "104 MB at most, Node 104 MB at most" on the Pi — the kernel credits a child
        # started by vfork with the parent's peak. Node now reports its own, and that is what is kept
        if shutil.which(social.NODE) is None:
            self.skipTest("node not installed here")
        self.addCleanup(setattr, social, "NODE_PEAK_KB", social.NODE_PEAK_KB)
        social.NODE_PEAK_KB = [0]
        got = social._node({"plane": EZY, "units": "metric", "clock": "", "theme": "amber", "cols": 14}, None, "--lines")
        self.assertGreater(got["maxrss_kb"], 10 * 1024)
        self.assertEqual(social.memory_mb()["node"], round(got["maxrss_kb"] / 1024.0))

    def test_the_service_measures_its_own_memory(self):
        # systemctl showed no Memory line on the Pi: the kernel's memory controller is off on Raspberry Pi OS
        m = social.memory_mb()
        self.assertGreater(m["now"], 0); self.assertGreaterEqual(m["peak"], m["now"])
        self.assertEqual(social.memory_words({"now": 38, "peak": 131, "node": 44}), "38 MB now, 131 MB at most, Node 44 MB at most")
        import contextlib
        import io
        for name, fake in (("load_state", lambda: dict(warm(), memory={"now": 38, "peak": 131, "node": 44, "since": time.time()})),
                           ("cfg", lambda: dict(CFG, SOCIAL="1")), ("unreadable", lambda p: False)):
            self.addCleanup(setattr, social, name, getattr(social, name))
            setattr(social, name, fake)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            social.cmd_status()
        self.assertIn("131 MB at most", out.getvalue())

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

    def test_the_test_says_the_map_failed_when_the_look_alternates(self):
        # 0.23.0: `social test` asked the setting ("alternate"), not this post's look, whether a map was due, and
        # said nothing when the tiles failed
        import contextlib
        import io
        c = dict(CFG, SOCIAL_STYLE="alternate", SOCIAL_MAP="rotate")
        for name, fake in (("_collect_once", lambda h=None: (c, {"pictures": 0}, EZY, trace(60), "all")),
                           ("publish", lambda *a, **k: {"map": "none", "text": "t", "alt": "a", "bytes": 1, "preview": "p"}),
                           ("local_ip", lambda: "192.0.2.1")):
            self.addCleanup(setattr, social, name, getattr(social, name))
            setattr(social, name, fake)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            social.cmd_test()
        self.assertIn("Picture: dotmap", out.getvalue())
        self.assertIn("Map: the tiles could not be fetched", out.getvalue())


class PublishTest(unittest.TestCase):
    def test_an_unwritable_run_folder_does_not_stop_a_picture(self):
        # 0.18.1: `social test` from the command line crashed with PermissionError on /run/zenithboard/social,
        # which only exists while the service runs. A private temporary folder stands in, and is removed after.
        if shutil.which(social.NODE) is None:
            self.skipTest("node not installed here")
        old = social.RUN_DIR; social.RUN_DIR = "/proc/no-such-place/social"; self.addCleanup(setattr, social, "RUN_DIR", old)
        r = social.publish(EZY, trace(30), "all", dict(CFG, SOCIAL_MAP="none"), {}, dry=True)
        self.assertIn("text", r)
        self.assertFalse([d for d in os.listdir(tempfile.gettempdir()) if d.startswith("zenithboard-social-")], "the stand-in folder must be removed")

    def test_the_picture_is_deleted_after_a_post_even_when_the_network_fails(self):
        if shutil.which(social.NODE) is None or social_card is None:
            self.skipTest("node or Pillow not installed here")
        d = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, d, True)
        old_run = social.RUN_DIR; social.RUN_DIR = d; self.addCleanup(setattr, social, "RUN_DIR", old_run)
        old = urllib.request.urlopen
        urllib.request.urlopen = lambda req, timeout=None: (_ for _ in ()).throw(OSError("no network"))
        self.addCleanup(setattr, urllib.request, "urlopen", old)
        keep = os.path.join(d, "keep", "preview")
        os.makedirs(os.path.dirname(keep), exist_ok=True)
        with open(keep + ".png", "wb") as fh:          # a dots preview from before 0.24.0 (the real Pi's
            fh.write(b"old")                            # /social/preview still showed one from an old version)
        r = social.publish(EZY, trace(30), "all", dict(CFG, SOCIAL_MAP="none"), {"BLUESKY_HANDLE": "h", "BLUESKY_APP_PASSWORD": "p"}, keep=keep)
        self.assertTrue(r["bluesky"].startswith("FAILED"))
        self.assertEqual([f for f in os.listdir(d) if f.startswith("post-")], [], "the picture must not stay on the Pi")
        self.assertTrue(os.path.exists(keep + ".jpg"))
        self.assertFalse(os.path.exists(keep + ".png"), "the preview is the last picture drawn, whatever the look")


class WeeklyTest(unittest.TestCase):
    """0.33.0: the week's summary. Sunday from 19:00, once a week, from the statistics' files; never a distance."""

    def setUp(self):
        import datetime
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)
        self.now = datetime.datetime(2026, 10, 18, 19, 5)            # a Sunday
        rows = ["when,messages,farthest_km,aircraft_pos,aircraft_seen"]
        for i in range(8):                                           # the Saturday before the week, then Monday to Sunday
            day = (self.now - datetime.timedelta(days=7 - i)).strftime("%Y-%m-%d")
            for h in range(24):
                if day == "2026-10-18" and h > 19:
                    break
                pos = 30 if h == 15 else 10
                rows.append("%s %02d:00,%d,250,%d,%d" % (day, h, 1000, pos + (5 if day == "2026-10-16" else 0), 50))
            with open(os.path.join(self.d, "seen-" + day), "w") as fh:
                n = 120 if day == "2026-10-16" else 80
                fh.write("".join("%06x\n" % (0x400000 + i * 1000 + k) for k in range(n)))
        with open(os.path.join(self.d, "stats.csv"), "w") as fh:
            fh.write("\n".join(rows) + "\n")
        with open(os.path.join(self.d, "fleet-2026-10-16"), "w") as fh:
            fh.write("4ca001\tRYR5ZK\t35000\tB738\n4ca002\tRYR12\t3000\tB738\n3c6444\tDLH4YK\t36000\tA320\n")
        with open(os.path.join(self.d, "fleet-2026-10-10"), "w") as fh:      # before the week: not counted
            fh.write("3c6445\tDLH9\t36000\tA320\n3c6446\tDLH8\t36000\tA320\n")
        self.c = dict(CFG, SOCIAL_AREA="Trémery", SOCIAL_WEEKLY="1")

    def week(self, **kw):
        import social_week
        return social_week.week_data(self.c, self.d, self.now, **kw)

    def test_when(self):
        import datetime
        import social_week
        at = lambda *a: time.mktime(datetime.datetime(*a).timetuple())
        sunday = at(2026, 10, 18, 19, 5)
        self.assertTrue(social_week.due(self.c, {}, sunday))
        self.assertFalse(social_week.due(dict(self.c, SOCIAL_WEEKLY="0"), {}, sunday), "off by default")
        self.assertFalse(social_week.due(CFG, {}, sunday), "off by default")
        self.assertFalse(social_week.due(self.c, {}, at(2026, 10, 18, 18, 59)))
        self.assertFalse(social_week.due(self.c, {}, at(2026, 10, 19, 19, 5)), "Monday: last week is not posted late")
        self.assertFalse(social_week.due(self.c, {"weekly": social_week.week_key(sunday)}, at(2026, 10, 18, 22, 0)))
        self.assertTrue(social_week.due(self.c, {"weekly": social_week.week_key(sunday)}, at(2026, 10, 25, 19, 0)))

    def test_the_week_counted(self):
        w = self.week(posts={"2026-10-16": 3, "2026-10-18": 2, "2026-10-10": 9})
        self.assertEqual(w["dates"][0], "2026-10-12")
        self.assertEqual(w["dates"][-1], "2026-10-18")
        self.assertEqual(w["aircraft"], 6 * 80 + 120, "distinct over the week, from the day files")
        self.assertEqual(w["messages"], 6 * 24 * 1000 + 20 * 1000)
        self.assertEqual(w["best_day"], ("2026-10-16", 120))
        self.assertEqual(w["busiest_hour"], 15)
        self.assertEqual([tuple(a) for a in w["airlines"]], [("Ryanair", 2), ("Lufthansa", 1)], "the week only")
        self.assertEqual(w["posted"], 5, "the week's posts only")
        self.assertEqual(len(w["heat"]), 7)
        self.assertIsNone(__import__("social_week").week_data(self.c, self.d + "/none", self.now))

    def test_airlines_only_when_their_lists_cover_the_week(self):
        # 0.34.1, seen on the reference Pi: "6 435 aircraft heard" beside "Ryanair (14)", the lists being two hours old
        import social_week
        os.unlink(os.path.join(self.d, "fleet-2026-10-10"))
        w = self.week()
        self.assertEqual((w["airlines"], w["models"], w["cargo"], w["bizjets"]), ([], [], [], []))
        self.assertEqual((w["fleet_from"], w["fleet_week"]), ("2026-10-16", "2026-10-25"))
        t = social_week.text(w, self.c, "above Trémery", "#ADSB", social.fit_post)
        self.assertNotIn("Airlines:", t)
        self.assertNotIn("Models:", t)
        self.assertFalse(social_week.has_second(w), "no second post before the lists cover the week")
        info = social_week.draw(w, "amber", "above Trémery", os.path.join(self.d, "w.png"))
        self.assertEqual(info["width"], 1200)
        self.assertEqual(social_week.first_full_week("2026-10-18"), "2026-10-25", "a Sunday start covers the next week")
        self.assertEqual(social_week.first_full_week("2026-10-19"), "2026-10-25", "a Monday start: six days of seven, shown (0.40.4)")
        self.assertEqual(social_week.first_full_week("2026-10-23"), "2026-11-01", "a Friday start: three days of seven, not yet")
        self.assertIsNone(social_week.fleet_start(self.d + "/none"))

    def add_cargo_and_bizjets(self):
        with open(os.path.join(self.d, "fleet-2026-10-17"), "w") as fh:
            fh.write("".join("a%05x\tFDX%d\t31000\tB77L\n" % (i, i) for i in range(3)))      # FedEx three times
            fh.write("b00001\tBCS12A\t29000\tB763\nb00002\tTHY6000\t33000\tB77L\n")       # DHL; Turkish: not cargo
            fh.write("c00001\t\t41000\tC56X\nc00002\tHBJFA\t43000\tC56X\nc00003\t\t39000\tFA7X\n")
            fh.write("c00004\t\t1500\tC172\n")                                            # a Cessna 172: no jet

    def test_cargo_and_business_jets(self):
        # 0.35.0: the second post. Cargo by the airline's own prefix (FedEx, DHL's EAT Leipzig), never by a
        # passenger airline's (Turkish flies cargo as THY too); business jets by the wall's own classes
        import social_week
        self.add_cargo_and_bizjets()
        w = self.week()
        self.assertEqual(w["cargo"][:2], [("FedEx", 3), ("DHL", 1)])
        self.assertEqual(w["cargo_total"], 4)
        self.assertEqual(w["bizjet_total"], 3)
        self.assertEqual(dict(w["bizjets"]).get("Cessna Citation Excel"), 2)
        self.assertNotIn("Cessna 172", str(w["bizjets"]))
        self.assertTrue(social_week.has_second(w))
        t = social_week.text_second(w, "above Trémery", "#ADSB #avgeek #ZenithBoard", social.fit_post)
        self.assertTrue(t.startswith("Cargo and business jets above Trémery, 12–18 October: 4 cargo aircraft, 3 business jets."), t)
        self.assertIn("Cargo: FedEx (3), DHL (1).", t)
        self.assertIn("Business jets: Cessna Citation Excel (2), Dassault Falcon 7X (1).", t)
        self.assertTrue(t.endswith("#ADSB #avgeek #ZenithBoard"))
        self.assertNotRegex(t + social_week.alt_second(w, "above Trémery"), r"\d\s?(km|mi|nm)\b|[A-Z]-[A-Z]{4}|HBJFA",
                            "no distance, and no registration of a private aircraft")
        info = social_week.draw_second(w, "white", "above Trémery", os.path.join(self.d, "w2.png"))
        self.assertEqual((info["width"], info["height"]), (1200, 675))
        info = social_week.draw(w, "white", "above a very long place name that would never fit beside the dates", os.path.join(self.d, "w1.png"))
        self.assertLess(info["bytes"], 1000000)

    def test_the_cargo_list(self):
        # 0.35.0: each entry an ICAO designator with its source; no passenger prefix (a callsign cannot tell its
        # cargo flights apart); DHL's airlines counted as one
        import json as _json
        import server
        with open(os.path.join(HERE, "..", "flightinfo", "data", "cargo_airlines.json"), encoding="utf-8") as fh:
            raw = _json.load(fh)
        codes = {k: v for k, v in raw.items() if not k.startswith("_")}
        self.assertGreaterEqual(len(codes), 30)
        for k, v in codes.items():
            self.assertRegex(k, r"^[A-Z]{3}$")
            self.assertTrue(v["name"] and v["source"].startswith("https://"), k)
        for passenger in ("THY", "QTR", "UAE", "AFR", "DLH", "KLM", "BAW", "RYR", "CPA", "ETH"):
            self.assertNotIn(passenger, codes)
        cargo = server.load_cargo()
        self.assertEqual({cargo[c] for c in ("BCS", "DHK", "DHX", "DAE", "DHA")}, {"DHL"})
        self.assertEqual((cargo["FDX"], cargo["CLX"], cargo["TAY"]), ("FedEx", "Cargolux", "ASL Airlines Belgium"))

    def add_military_and_general_aviation(self):
        # 0.36.0 columns: flight, altitude, type, category, military mark
        with open(os.path.join(self.d, "fleet-2026-10-15"), "w") as fh:
            fh.write("ae1001\tRCH123\t30000\tC17\tA5\t\n")          # a US military address: military by its range
            fh.write("ae1002\t\t25000\tK35R\tA5\t1\n")
            fh.write("3b7a01\tCTM1234\t28000\tA400\tA5\t1\n")       # French civil block, marked military by the database
            fh.write("3c0f01\t\t35000\tEUFI\t\t\n")                 # a fighter: military by its class
            fh.write("3c1a01\t\t1500\tEC45\tA7\t\n3c1a02\t\t1200\tEC45\tA7\t\n")
            fh.write("3c1a03\t\t2000\tC172\tA1\t\n3c1a04\t\t3000\tGLID\tB1\t\n3c1a05\t\t400\t\tB6\t\n")
            fh.write("4b1a01\t\t41000\tFA7X\tA2\t\n")                # a Swiss business jet

    def test_general_aviation_rows_carry_the_country_and_unknown_military_is_asked(self):
        # 0.40.5, the owner: the flags of the helicopters and light aircraft; and "Germany: Unknown type (2)"
        import social_week
        self.add_military_and_general_aviation()
        with open(os.path.join(self.d, "fleet-2026-10-15"), "a") as fh:
            fh.write("3f4401\t\t20000\t\t\t1\n3f4402\t\t21000\t\t\t1\n")     # German military, no type
            fh.write("4b1b01\t\t9000\tEC45\tA7\t\n")                       # a Swiss helicopter
        w = self.week()
        m = social_week.misc_lists(w)
        heli = {(n, cc): k for n, cc, k in m["heli"]["rows"]}
        self.assertEqual(sum(heli.values()), 3)
        self.assertEqual({cc for _, cc in heli}, {"DE", "CH"}, "one row per model and country")
        self.assertEqual(sorted(w["military_unknown"]["DE"]), ["3f4401", "3f4402"])
        asked = []
        social_week.name_unknown_military(w, lambda h: asked.append(h) or ({"manufacturer": "Airbus", "type": "A400M Atlas"} if h == "3f4401" else None))
        de = {e["cc"]: e for e in w["military"]}["DE"]
        self.assertEqual(sorted(asked), ["3f4401", "3f4402"])
        self.assertIn(("Airbus A400M Atlas", 1), de["models"])
        self.assertIn(("Unknown type", 1), de["models"])
        self.assertEqual(de["models"][-1][0], "Unknown type", "the unknown last")
        flags = social_week.load_flags(["DE", "CH", "US", "FR"])
        info = social_week.draw_misc(w, "amber", "above Trémery", os.path.join(self.d, "m.png"), flags)
        self.assertEqual((info["width"], info["height"]), (1200, 675))

    def test_the_cards_say_the_period_in_words(self):
        import social_week
        self.assertEqual(social_week.SPAN_TITLES, {"daily": "LAST 24 HOURS", "weekly": "LAST 7 DAYS", "monthly": "LAST 30 DAYS"})
        self.assertEqual(social_week.span_footer({"period": "daily", "dates": ["2026-10-20", "2026-10-21"], "until": "09:20"}),
                         "20 October, 09:20 – 21 October, 09:20")
        self.assertEqual(social_week.span_footer({"period": "weekly", "dates": ["2026-10-12", "2026-10-18"]}), "12–18 October")

    def test_military_and_general_aviation(self):
        import social_week
        import server
        self.add_military_and_general_aviation()
        w = self.week()
        mil = {e["cc"]: e for e in w["military"]}
        self.assertEqual(w["military_total"], 4)
        self.assertEqual(mil["US"]["total"], 2)
        self.assertEqual(w["military"][0]["cc"], "US", "the most represented country first")
        self.assertEqual(mil["FR"]["models"][0][1], 1)
        self.assertEqual(mil["DE"]["total"], 1, "the Typhoon, by its class")
        self.assertNotIn("EC45", str(w["military"]))
        m = social_week.misc_lists(w)
        self.assertEqual((m["heli"]["total"], m["light"]["total"], m["glider"]["total"], m["other"]["total"]), (2, 1, 1, 1))
        self.assertEqual(m["other"]["models"], [("Drone", 1)])
        self.assertIn(("CH", 1), w["bizjet_countries"])
        self.assertTrue(social_week.has_part(w, 3) and social_week.has_part(w, 4))
        t = social_week.text_military(w, "above Trémery", "#ADSB", social.fit_post)
        self.assertTrue(t.startswith("Military aircraft above Trémery, 12–18 October: 4 aircraft from 3 countries."), t)
        self.assertIn("United States: ", t)
        t = social_week.text_misc(w, "above Trémery", "#ADSB", social.fit_post)
        self.assertTrue(t.startswith("General aviation above Trémery, 12–18 October: 2 helicopters, 1 light aircraft, 1 glider, 1 drone or balloon."), t)
        for txt in (t, social_week.alt_military(w, "above Trémery"), social_week.alt_misc(w, "above Trémery")):
            self.assertNotRegex(txt, r"\d\s?(km|mi|nm)\b|RCH123|CTM1234|ae1001", "no distance, no callsign, no address")
        flags = social_week.load_flags(["US", "FR", "DE", "ZZ", "", "../x"])
        self.assertEqual(sorted(flags), ["DE", "FR", "US"], "the real flags (0.36.1); none for an unknown code")
        self.assertEqual(flags["FR"].size, (48, 32))
        self.assertEqual(flags["FR"].getpixel((4, 16))[2] > 100, True, "France starts blue")
        for draw, args in ((social_week.draw_military, (flags,)), (social_week.draw_misc, ()), (social_week.draw_second, (flags,))):
            info = draw(w, "red", "above Trémery", os.path.join(self.d, "c.png"), *args)
            self.assertEqual((info["width"], info["height"]), (1200, 675))
        self.assertEqual((server.icao_country("3c6444"), server.icao_country("ae1234"), server.icao_country("4b1a01")), ("DE", "US", "CH"))
        # nested blocks (0.36.1): Bermuda and the Isle of Man inside the United Kingdom's, listed before its catch-all;
        # the UK's military block (43c000) once fell to no country
        self.assertEqual([server.icao_country(h) for h in ("43c123", "4001a0", "43e800", "400a00", "zz")], ["GB", "BM", "IM", "GB", ""])
        self.assertTrue(server.in_military_range("ae1234"))
        self.assertFalse(server.in_military_range("3c6444"))
        self.assertEqual([server.misc_group(*a) for a in (("heli", ""), (None, "A7"), (None, "B6"), ("light", ""), ("narrow", "A3"))],
                         ["heli", "heli", "drone", "light", None])

    def test_publish_parts_three_and_four(self):
        self.addCleanup(setattr, social.server, "STATS_DIR", social.server.STATS_DIR)
        social.server.STATS_DIR = self.d
        now = time.mktime(self.now.timetuple())
        self.assertIn("no military aircraft", social.publish_week(self.c, {}, now, {}, dry=True, part=3)["skipped"])
        self.add_military_and_general_aviation()
        self.assertTrue(social.publish_week(self.c, {}, now, {}, dry=True, part=3)["text"].startswith("Military aircraft above Trémery"))
        self.assertTrue(social.publish_week(self.c, {}, now, {}, dry=True, part=4)["text"].startswith("General aviation above Trémery"))

    def test_summary_settings(self):
        # 0.38.0: three summaries, each at its own time, with the posts picked
        import social_week as sw
        self.assertEqual(sw.parse_at("weekly", "Sat 08:05"), (5, 8, 5))
        self.assertEqual(sw.parse_at("monthly", "28 23:59"), (28, 23, 59))
        self.assertEqual(sw.parse_at("daily", "7:30"), (None, 7, 30))
        for period, bad in (("daily", "25:00"), ("daily", "mon 21:00"), ("weekly", "21:00"), ("weekly", "xyz 10:00"),
                            ("monthly", "31 09:00"), ("monthly", "0 09:00"), ("monthly", "1 9h")):
            with self.assertRaises(ValueError, msg="%s %s" % (period, bad)):
                sw.parse_at(period, bad)
        c = dict(CFG, SOCIAL_MONTHLY_AT="31 09:00")
        self.assertEqual(sw.at_of(c, "monthly"), (1, 9, 0), "a hand-edited wrong value: the default, not a stop")
        self.assertEqual(sw.at_words(CFG, "weekly"), "every Sunday at 19:00")
        self.assertEqual(sw.at_words(dict(CFG, SOCIAL_MONTHLY_AT="2 07:00"), "monthly"), "on the 2nd of each month at 07:00")
        self.assertEqual(sw.parts_of(CFG, "daily"), [1])
        self.assertEqual(sw.parts_of(dict(CFG, SOCIAL_WEEKLY_PARTS="3,1"), "weekly"), [1, 3])
        self.assertEqual(sw.parts_of(dict(CFG, SOCIAL_WEEKLY_PARTS="all"), "weekly"), [1, 2, 3, 4])
        self.assertEqual(sw.parts_of(dict(CFG, SOCIAL_WEEKLY_PARTS="x,9"), "weekly"), [1])

    def test_when_each_summary_is_due(self):
        import datetime
        import social_week as sw
        at = lambda *a: time.mktime(datetime.datetime(*a).timetuple())
        c = dict(CFG, SOCIAL_DAILY="1", SOCIAL_DAILY_AT="07:30", SOCIAL_WEEKLY="1", SOCIAL_WEEKLY_AT="wed 12:00",
                 SOCIAL_MONTHLY="1", SOCIAL_MONTHLY_AT="21 06:00")
        wed = at(2026, 10, 21, 12, 0)                                     # Wednesday the 21st
        self.assertTrue(all(sw.due(c, {}, wed, p) for p in ("daily", "weekly", "monthly")))
        self.assertFalse(sw.due(c, {}, at(2026, 10, 21, 7, 29), "daily"))
        self.assertFalse(sw.due(c, {}, at(2026, 10, 22, 12, 0), "weekly"), "Thursday")
        self.assertFalse(sw.due(c, {}, at(2026, 11, 20, 12, 0), "monthly"), "the 20th")
        self.assertFalse(sw.due(c, {"summaries": {"daily": "2026-10-21"}}, wed, "daily"), "done today")
        self.assertTrue(sw.due(c, {"summaries": {"daily": "2026-10-20"}}, wed, "daily"))
        self.assertFalse(sw.due(c, {"weekly": "2026-W43"}, wed, "weekly"), "the key 0.33.0 kept still counts")
        self.assertFalse(sw.due(CFG, {}, wed, "monthly"), "off by default")
        self.assertEqual((sw.cycle_key("daily", wed), sw.cycle_key("weekly", wed), sw.cycle_key("monthly", wed)),
                         ("2026-10-21", "2026-W43", "2026-10"))

    def test_lists_begun_inside_the_period_are_shown_from_half_of_it(self):
        # the reference Pi, 21 October 2026: the first daily summary had no airline, no model and none of posts 2 to
        # 4, the lists having begun the day before; the statistics page showed them. 0.40.4: shown, saying since when
        import social_week as sw
        for n in ("fleet-2026-10-10", "fleet-2026-10-16"):
            os.unlink(os.path.join(self.d, n))
        with open(os.path.join(self.d, "fleet-2026-10-17"), "w") as fh:          # began on the 17th at 20:15
            fh.write("4ca001\tRYR5ZK\t35000\tB738\t\t\t2015\na00001\tFDX1\t31000\tB77L\t\t\t2130\n")
        day = sw.week_data(self.c, self.d, self.now, period="daily")             # the 24 hours from the 17th, 19:05
        self.assertFalse(day["covered"])
        self.assertTrue(day["shown"], "23 hours of 24")
        self.assertEqual(day["since"], "17 October, 20:15")
        self.assertEqual(sorted(n for n, _ in day["airlines"]), ["FedEx", "Ryanair"])
        self.assertTrue(sw.has_part(day, 2), "the cargo post goes out too")
        sw.draw(day, "amber", "above Trémery", os.path.join(self.d, "d.png"))
        week = sw.week_data(self.c, self.d, self.now)                           # two days of seven: still left out
        self.assertEqual((week["shown"], week["since"], week["airlines"]), (False, None, []))
        os.unlink(os.path.join(self.d, "fleet-2026-10-17"))
        with open(os.path.join(self.d, "fleet-2026-10-18"), "w") as fh:          # began this morning: 9 hours of 24
            fh.write("4ca001\tRYR5ZK\t35000\tB738\t\t\t1000\n")
        day = sw.week_data(self.c, self.d, self.now, period="daily")
        self.assertEqual((day["shown"], day["airlines"]), (False, []))
        self.assertFalse(sw.has_part(day, 2))
        with open(os.path.join(self.d, "fleet-2026-10-18"), "w") as fh:          # a file from before the time column
            fh.write("4ca001\tRYR5ZK\t35000\tB738\n")
        self.assertEqual(sw.fleet_since(self.d, "2026-10-18")[1], "18 October")

    def test_the_day_and_the_thirty_days(self):
        import datetime
        import social_week as sw
        with open(os.path.join(self.d, "fleet-2026-10-18"), "w") as fh:
            fh.write("4ca009\tRYR77\t35000\tB738\t\t\t1800\n")
        day = sw.week_data(self.c, self.d, self.now, period="daily")
        self.assertEqual(day["period"], "daily")
        self.assertEqual(day["busiest_hour"], 15)
        self.assertEqual(len(day["heat"][0]), 24)
        t = sw.text(day, self.c, "above Trémery", "#ADSB", social.fit_post)
        self.assertTrue(t.startswith("The last 24 hours above Trémery: "), t)
        self.assertIn("Busiest hour: 15:00.", t)
        self.assertEqual([n for n, _ in day["airlines"]], ["Ryanair"], "the lists of the last 24 hours")
        month = sw.week_data(self.c, self.d, self.now, period="monthly")
        self.assertEqual(len(month["dates"]), 30)
        self.assertEqual(month["best_day"], ("2026-10-16", 120))
        t = sw.text(month, self.c, "above Trémery", "#ADSB", social.fit_post)
        self.assertTrue(t.startswith("The last 30 days above Trémery, 19 September – 18 October: "), t)
        self.assertFalse(month["covered"], "the lists began on the 10th: they do not cover thirty days")
        for w, name in ((day, "d.png"), (month, "m.png")):
            info = sw.draw(w, "green", "above Trémery", os.path.join(self.d, name))
            self.assertEqual((info["width"], info["height"]), (1200, 675))
        self.assertIn("the last 24 hours", sw.text_military(dict(day, military=[], military_total=0), "above Trémery", "", social.fit_post))

    def test_summaries_share_one_queue(self):
        # 0.38.0: the week and the day both due on Sunday at 19:00: the longer first, every post two minutes after the
        # one before, only the posts picked; a restart does not post anything twice
        import datetime
        self.c.update(SOCIAL_DAILY="1", SOCIAL_DAILY_AT="19:00", SOCIAL_DAILY_PARTS="1,3", SOCIAL_WEEKLY_PARTS="1,2")
        ok = {"bluesky": "at://did/post/1"}
        sent, state = self.run_loop(self.sunday(), 2, {1: [ok], 2: [ok], 3: [ok]})
        self.assertEqual([p for _, p in sent], [1, 2, 1, 3], "the week's 1 and 2, then the day's 1 and 3")
        times = [t for t, _ in sent]
        self.assertTrue(all(social.SECOND_AFTER_S <= b - a < social.SECOND_AFTER_S + 30 for a, b in zip(times, times[1:])))
        self.assertEqual(state["summaries"], {"weekly": "2026-W42@sun 19:00", "daily": "2026-10-18@19:00"})
        self.assertEqual(state["summary_queue"], [])
        q = social.schedule_summaries(self.c, state, self.sunday() + 3 * 3600)
        self.assertEqual(q, [], "already done this cycle: nothing again")

    def test_the_lists_shrink_before_a_line_goes(self):
        import social_week
        w = self.week()
        w["airlines"] = [("Air %s" % x, 9) for x in "ABCDE"]
        w["models"] = [("Model with a long name %d" % i, 5) for i in range(5)]
        tags = "#ADSB #avgeek #ZenithBoard #planespotting #aviation"
        t = social_week.text(w, self.c, "above Trémery", tags, social.fit_post)
        self.assertLessEqual(len(t), social.POST_MAX)
        self.assertTrue(t.endswith(tags), "the hashtags whole")
        self.assertIn("Models: ", t, "the models stay, with fewer names, before any line is dropped")

    def test_publish_the_second_dry_and_skipped(self):
        self.addCleanup(setattr, social.server, "STATS_DIR", social.server.STATS_DIR)
        social.server.STATS_DIR = self.d
        now = time.mktime(self.now.timetuple())
        self.assertIn("no cargo airline nor business jet", social.publish_week(self.c, {}, now, {}, dry=True, second=True)["skipped"])
        self.add_cargo_and_bizjets()
        r = social.publish_week(self.c, {}, now, {}, dry=True, second=True)
        self.assertTrue(r["text"].startswith("Cargo and business jets above Trémery"))
        os.unlink(os.path.join(self.d, "fleet-2026-10-10"))
        self.assertIn("do not cover these seven days", social.publish_week(self.c, {}, now, {}, dry=True, second=True)["skipped"])

    def test_the_words_never_give_a_distance(self):
        import social_week
        w = self.week(posts={"2026-10-16": 3})
        t = social_week.text(w, self.c, social.area_words(self.c), "#ADSB #avgeek #ZenithBoard", social.fit_post)
        self.assertTrue(t.startswith("The week above Trémery, 12–18 October: "), t)
        self.assertIn("Busiest: Friday (120 aircraft) and 15:00.", t)
        self.assertIn("Airlines: Ryanair (2), Lufthansa (1).", t)
        self.assertIn("Models: ", t)
        self.assertIn("Posted here: 3 crossings.", t)
        self.assertTrue(t.endswith("#ADSB #avgeek #ZenithBoard"))
        self.assertNotRegex(t + social_week.alt(w, "above Trémery"), r"\d\s?(km|mi|nm)\b|farthest|range|north|south|east|west")
        long_tags = " ".join("#tag%02d" % i for i in range(30))
        t2 = social_week.text(w, self.c, "above Trémery", long_tags, social.fit_post)
        self.assertLessEqual(len(t2), social.POST_MAX)
        self.assertTrue(t2.startswith("The week above Trémery, 12–18 October: "), "the head always stays")
        self.assertEqual(social_week.messages_words(58_671_951), "58.7 million")
        self.assertEqual(social_week.messages_words(812_000), "812\u00a0000")
        self.assertEqual(social_week.span_words(["2026-09-28", "2026-10-04"]), "28 September – 4 October")

    def test_the_picture(self):
        import social_week
        from PIL import Image
        out = os.path.join(self.d, "week.png")
        info = social_week.draw(self.week(), "green", "above Trémery", out)
        self.assertEqual((info["width"], info["height"], info["mime"]), (1200, 675, "image/png"))
        self.assertLess(info["bytes"], 1000000)
        with Image.open(out) as im:
            self.assertEqual(im.size, (1200, 675))

    def test_publish_dry_and_skipped(self):
        self.addCleanup(setattr, social.server, "STATS_DIR", social.server.STATS_DIR)
        social.server.STATS_DIR = self.d
        now = time.mktime(self.now.timetuple())
        r = social.publish_week(self.c, {}, now, {"post_days": {}}, dry=True)
        self.assertTrue(r["text"].startswith("The week above Trémery"))
        self.assertIn("Weekly summary card", r["alt"])
        self.assertTrue(r["fleet_shown"])
        self.assertNotRegex(r["text"], r"Models: [A-Z]{4,} ", "the maker as the posts write it (0.34.1)")
        social.server.STATS_DIR = self.d + "/none"
        self.assertIn("skipped", social.publish_week(self.c, {}, now, {}, dry=True))

    def test_posts_counted_by_day_for_thirty_one_days(self):
        # 0.38.0: thirty-one days for the monthly summary (eight before)
        s = warm()
        now = time.time()
        social.remember(s, EZY, now - 32 * 86400)
        social.remember(s, EZY, now)
        social.remember(s, BELUGA, now)
        social.prune_state(s, now)
        self.assertEqual(s["post_days"], {social.day_of(now): 2})

    def test_the_service_posts_it_once_on_sunday(self):
        import contextlib
        import datetime
        start = time.mktime(datetime.datetime(2026, 10, 18, 18, 55).timetuple())
        clock = [start]
        sent, state = [], warm()

        class Stop(Exception):
            pass

        def fake_sleep(sec):
            clock[0] += sec
            if clock[0] > start + 3 * 3600:
                raise Stop()
        results = [{"bluesky": "FAILED: 503 down"}, {"bluesky": "at://did/post/1"}]
        for name, fake in (("read_aircraft", lambda c: []), ("account", lambda: {"BLUESKY_HANDLE": "h", "BLUESKY_APP_PASSWORD": "p"}),
                           ("one_poll", lambda c, st, tr, ac, now: ([], None)), ("load_state", lambda: state),
                           ("save_state", lambda st: None), ("cfg", lambda: dict(self.c)), ("merge_disk", lambda st: st),
                           ("publish_week", lambda c, sec, now, st, second=False, part=1, period="weekly": (sent.append(now) or results[min(len(sent), 2) - 1]) if part == 1 else {"skipped": "-"})):
            self.addCleanup(setattr, social, name, getattr(social, name))
            setattr(social, name, fake)
        self.addCleanup(setattr, time, "time", time.time); time.time = lambda: clock[0]
        self.addCleanup(setattr, time, "sleep", time.sleep); time.sleep = fake_sleep
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(Stop):
                social.cmd_run()
        self.assertEqual(len(sent), 2, "a failure, then one post ten minutes later, then nothing more that week")
        self.assertGreaterEqual(sent[0], start + 5 * 60, "not before 19:00")
        self.assertGreaterEqual(sent[1] - sent[0], social.RETRY_AFTER_FAIL_S)
        self.assertEqual(state["summaries"]["weekly"], "2026-W42@sun 19:00")

    def run_loop(self, start, hours, results, events=None, state=None):
        """The service loop on a Sunday evening. results: {part: [answers in turn]} (the last one repeats). events:
        [(time, function)], each called once when the clock passes it (a setting changed while it runs)."""
        self.periods = []
        events = sorted(events or [], key=lambda e: e[0])
        import contextlib
        clock = [start]
        sent, state = [], (state if state is not None else warm())

        class Stop(Exception):
            pass

        def fake_sleep(sec):
            clock[0] += sec
            while events and events[0][0] <= clock[0]:
                events.pop(0)[1]()
            if clock[0] > start + hours * 3600:
                raise Stop()

        def fake_publish(c, sec, now, st, second=False, part=None, period="weekly"):
            part = part or (2 if second else 1)
            sent.append((now, part))
            self.periods.append(period)
            seq = results.get(part) or [{"skipped": "-"}]
            return seq[min(len([x for x in sent if x[1] == part]), len(seq)) - 1]
        for name, fake in (("read_aircraft", lambda c: []), ("account", lambda: {"BLUESKY_HANDLE": "h", "BLUESKY_APP_PASSWORD": "p"}),
                           ("one_poll", lambda c, st, tr, ac, now: ([], None)), ("load_state", lambda: state),
                           ("save_state", lambda st: None), ("cfg", lambda: dict(self.c)), ("merge_disk", lambda st: st),
                           ("publish_week", fake_publish)):
            self.addCleanup(setattr, social, name, getattr(social, name))
            setattr(social, name, fake)
        self.addCleanup(setattr, time, "time", time.time); time.time = lambda: clock[0]
        self.addCleanup(setattr, time, "sleep", time.sleep); time.sleep = fake_sleep
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(Stop):
                social.cmd_run()
        self.journal = out.getvalue()
        return sent, state

    OK = {"bluesky": "at://did/post/1"}
    BAD = {"bluesky": "FAILED: 503"}

    def sunday(self):
        import datetime
        return time.mktime(datetime.datetime(2026, 10, 18, 18, 58).timetuple())

    def at(self, y, mo, d, h, mi):
        import datetime
        return time.mktime(datetime.datetime(y, mo, d, h, mi).timetuple())

    def test_a_daily_moved_later_after_it_went_out_goes_again_at_the_new_time(self):
        # 0.49.0, the owner on 22 October: one summary per scheduled slot, not per day. Moved to later the same day,
        # it goes at the new time; the slot already gone does not go again
        import social_week as sw
        self.c.update(SOCIAL_WEEKLY="0", SOCIAL_DAILY="1", SOCIAL_DAILY_AT="21:00", SOCIAL_DAILY_PARTS="1,2,3,4")
        ok = [self.OK]
        moved = lambda: self.c.update(SOCIAL_DAILY_AT="23:35")
        sent, state = self.run_loop(self.at(2026, 10, 21, 20, 58), 3, {1: ok, 2: ok, 3: ok, 4: ok}, events=[(self.at(2026, 10, 21, 23, 20), moved)])
        self.assertEqual([p for _, p in sent], [1, 2, 3, 4, 1, 2, 3, 4], "21:00, then 23:35")
        self.assertTrue(self.at(2026, 10, 21, 21, 0) <= sent[0][0] < self.at(2026, 10, 21, 21, 1))
        self.assertTrue(self.at(2026, 10, 21, 23, 35) <= sent[4][0] < self.at(2026, 10, 21, 23, 36))
        self.assertIn("daily summary due (every day at 21:00): posts 1,2,3,4 queued, 2 min apart, the first now", self.journal)
        self.assertIn("daily summary now every day at 23:35", self.journal)
        self.assertEqual(state["summaries"]["daily"], "2026-10-21@23:35")
        w = sw.when_words(self.c, state, self.at(2026, 10, 21, 23, 50), "daily")
        self.assertIn("next: Thu 2026-10-22 23:35", w)

    def test_a_time_set_after_it_has_passed_waits_for_the_next(self):
        # set at 22:00 to 21:00, or switched on at 22:00 when set for 21:00: nothing at once, the next day at 21:00
        import social_week as sw
        self.c.update(SOCIAL_WEEKLY="0", SOCIAL_DAILY="1", SOCIAL_DAILY_AT="23:00", SOCIAL_DAILY_PARTS="1")
        moved = lambda: self.c.update(SOCIAL_DAILY_AT="21:00")
        sent, state = self.run_loop(self.at(2026, 10, 21, 21, 30), 1, {1: [self.OK]}, events=[(self.at(2026, 10, 21, 22, 0), moved)])
        self.assertEqual(sent, [], "21:00 had passed when it was set")
        self.assertIn("daily summary set to every day at 21:00, already past today: from the next one, Thu 2026-10-22 21:00", self.journal)
        self.assertIn("next: Thu 2026-10-22 21:00", sw.when_words(self.c, state, self.at(2026, 10, 21, 22, 30), "daily"))
        sent2, _ = self.run_loop(self.at(2026, 10, 22, 20, 59), 0.2, {1: [self.OK]}, state=state)
        self.assertEqual([p for _, p in sent2], [1], "the next day at its time")
        # switched on after its time
        self.c.update(SOCIAL_DAILY="0", SOCIAL_DAILY_AT="21:00")
        on = lambda: self.c.update(SOCIAL_DAILY="1")
        sent3, _ = self.run_loop(self.at(2026, 10, 23, 20, 0), 2, {1: [self.OK]}, events=[(self.at(2026, 10, 23, 21, 30), on)], state={"summary_seen": {}})
        self.assertEqual(sent3, [], "switched on at 21:30 for 21:00: not at once")

    def test_a_pi_back_after_its_time_posts_it_the_same_day(self):
        # the setting unchanged, the service down at 21:00 and back at 21:40: it goes then (as before 0.49.0)
        self.c.update(SOCIAL_WEEKLY="0", SOCIAL_DAILY="1", SOCIAL_DAILY_AT="21:00", SOCIAL_DAILY_PARTS="1")
        state = {"summary_seen": {"daily": "on 21:00", "weekly": "off", "monthly": "off"}}
        sent, _ = self.run_loop(self.at(2026, 10, 21, 21, 40), 0.2, {1: [self.OK]}, state=state)
        self.assertEqual([p for _, p in sent], [1])

    def test_a_cycle_gone_before_0_49_is_not_posted_again(self):
        # 0.38.0 to 0.48.0 kept "2026-W43": the week's summary gone at 19:00, the service restarted at 20:00 on 0.49.0
        state = {"summaries": {"weekly": "2026-W43"}}
        sent, _ = self.run_loop(self.at(2026, 10, 25, 20, 0), 1, {1: [self.OK]}, state=state)
        self.assertEqual(sent, [])

    def test_a_daily_set_later_before_it_went_out_goes_at_the_new_time(self):
        self.c.update(SOCIAL_WEEKLY="0", SOCIAL_DAILY="1", SOCIAL_DAILY_AT="21:00", SOCIAL_DAILY_PARTS="1,3")
        moved = lambda: self.c.update(SOCIAL_DAILY_AT="23:35")
        sent, _ = self.run_loop(self.at(2026, 10, 21, 20, 30), 4, {1: [self.OK], 3: [self.OK]},
                                events=[(self.at(2026, 10, 21, 20, 40), moved)])
        self.assertEqual([p for _, p in sent], [1, 3], "only the posts picked, in order")
        self.assertTrue(self.at(2026, 10, 21, 23, 35) <= sent[0][0] < self.at(2026, 10, 21, 23, 36), "at 23:35, not 21:00")
        self.assertGreaterEqual(sent[1][0] - sent[0][0], social.SECOND_AFTER_S)

    def test_when_each_summary_goes_next(self):
        import social_week as sw
        c = dict(self.c, SOCIAL_DAILY="1", SOCIAL_DAILY_AT="21:00", SOCIAL_WEEKLY="1", SOCIAL_WEEKLY_AT="sun 19:00",
                 SOCIAL_MONTHLY="1", SOCIAL_MONTHLY_AT="1 09:00")
        wed = self.at(2026, 10, 21, 12, 0)                                   # a Wednesday
        self.assertEqual(sw.next_due(c, {}, wed, "daily").strftime("%Y-%m-%d %H:%M"), "2026-10-21 21:00")
        self.assertEqual(sw.next_due(c, {}, wed, "weekly").strftime("%Y-%m-%d %H:%M"), "2026-10-25 19:00")
        self.assertEqual(sw.next_due(c, {}, wed, "monthly").strftime("%Y-%m-%d %H:%M"), "2026-11-01 09:00")
        late = self.at(2026, 10, 21, 22, 0)                                  # past its time, not gone yet: now
        self.assertLess(abs(sw.next_due(c, {}, late, "daily").timestamp() - late), 1)
        done = {"summaries": {"daily": "2026-10-21", "weekly": "2026-W43", "monthly": "2026-10"}}
        self.assertEqual(sw.next_due(c, done, late, "daily").strftime("%Y-%m-%d %H:%M"), "2026-10-22 21:00")
        sun = self.at(2026, 10, 25, 20, 0)
        self.assertEqual(sw.next_due(c, {}, sun, "weekly").strftime("%Y-%m-%d"), "2026-10-25", "this week's not gone: now")
        self.assertEqual(sw.next_due(c, {"summaries": {"weekly": "2026-W43"}}, sun, "weekly").strftime("%Y-%m-%d %H:%M"), "2026-11-01 19:00")
        self.assertIsNone(sw.next_due(dict(c, SOCIAL_DAILY="0"), {}, wed, "daily"))
        self.assertIn("(off)", sw.when_words(dict(c, SOCIAL_DAILY="0"), {}, wed, "daily"))

    def test_four_posts_two_minutes_apart(self):
        # 0.35.0 the second, 0.36.0 the third (military) and the fourth (helicopters, light aircraft, gliders)
        sent, state = self.run_loop(self.sunday(), 2, {1: [self.OK], 2: [self.OK], 3: [self.OK], 4: [self.OK]})
        self.assertEqual([p for _, p in sent], [1, 2, 3, 4], "each once, in order")
        times = [t for t, _ in sent]
        for a, b in zip(times, times[1:]):
            self.assertGreaterEqual(b - a, social.SECOND_AFTER_S)
            self.assertLess(b - a, social.SECOND_AFTER_S + 30)
        self.assertNotIn("weekly2", state)

    def test_a_post_with_nothing_to_say_gives_its_turn(self):
        sent, state = self.run_loop(self.sunday(), 2, {1: [self.OK], 2: [{"skipped": "no cargo"}], 3: [self.OK], 4: [self.OK]})
        parts = dict((p, t) for t, p in sent)
        self.assertEqual(sorted(parts), [1, 2, 3, 4])
        self.assertLess(parts[3] - parts[1], social.SECOND_AFTER_S + 30, "the military post where the cargo one would have been")

    def test_a_failure_waits_and_never_without_the_first(self):
        sent, state = self.run_loop(self.sunday(), 2, {1: [self.OK], 2: [self.BAD, self.OK], 3: [self.OK], 4: [self.OK]})
        seconds = [t for t, p in sent if p == 2]
        self.assertEqual(len(seconds), 2)
        self.assertGreaterEqual(seconds[1] - seconds[0], social.RETRY_AFTER_FAIL_S)
        self.assertEqual([p for _, p in sent][-2:], [3, 4])
        sent, state = self.run_loop(self.sunday(), 2, {1: [{"skipped": "no statistics"}]})
        self.assertEqual([p for _, p in sent], [1], "the first skipped: no others")
        sent, state = self.run_loop(self.sunday(), 6, {1: [self.OK], 2: [self.BAD]})
        seconds = [t for t, p in sent if p == 2]
        self.assertLessEqual(seconds[-1] - seconds[0], social.SECOND_LATE_S, "dropped when hours late")
        self.assertNotIn(3, [p for _, p in sent], "and the rest with it: Bluesky is not answering")
        self.assertNotIn("weekly2", state)

if __name__ == "__main__":
    unittest.main()
