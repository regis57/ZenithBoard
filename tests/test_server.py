# SPDX-License-Identifier: GPL-3.0-or-later
"""Run: python3 -m unittest discover -s tests -v"""
import json
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "flightinfo"))
import server  # noqa: E402

HERE = os.path.dirname(__file__)
LAT, LON = 49.246, 6.223


class ServerTests(unittest.TestCase):
    def test_env_parser(self):
        out = server.parse_env_text('# c\nUNITS=imperial\nLAT="49.2"\n\nBAD LINE\nX=\'y\'\n')
        self.assertEqual(out, {"UNITS": "imperial", "LAT": "49.2", "X": "y"})

    def test_haversine_and_bearing(self):
        self.assertAlmostEqual(server.haversine_km(0, 0, 0, 1), 111.195, delta=0.2)
        self.assertAlmostEqual(server.bearing_deg(0, 0, 1, 0), 0, delta=0.01)
        self.assertAlmostEqual(server.bearing_deg(0, 0, 0, 1), 90, delta=0.01)

    def test_radius_units(self):
        self.assertAlmostEqual(server.radius_to_km(10, "imperial"), 16.09344)
        self.assertEqual(server.radius_to_km(10, "metric"), 10)

    def test_build_planes(self):
        data = self._demo()
        planes, total = server.build_planes(data, LAT, LON, 10)
        self.assertEqual(total, 12)                     # no-position and stale aircraft ignored
        self.assertEqual(len(planes), 11)               # the EZY45RF at ~57 km is outside 10 km
        self.assertEqual(planes[0]["hex"], "dd0013")    # nearest first
        near, _ = server.build_planes(data, LAT, LON, 2)
        self.assertEqual([p["hex"] for p in near], ["dd0013", "3c6444", "dd0010", "3e1a2b"])
        ground = [p for p in near if p["hex"] == "3c6444"][0]
        self.assertTrue(ground["on_ground"])
        self.assertEqual(ground["alt_ft"], 0)
        far, _ = server.build_planes(data, LAT, LON, 100)
        self.assertEqual(len(far), 12)

    def _demo(self):
        with open(os.path.join(HERE, "..", "flightinfo", "demo", "aircraft.json")) as fh:
            return json.load(fh)

    def test_airline_lookup(self):
        air = {"AFR": {"name": "Air France", "iata": "AF"}}
        self.assertEqual(server.airline_for("AFR1234", air), ("AFR", {"name": "Air France", "iata": "AF"}))
        self.assertEqual(server.airline_for("afr12a ", air)[0], "AFR")
        self.assertEqual(server.airline_for("XYZ99", air), ("XYZ", None))      # unknown airline
        self.assertEqual(server.airline_for("N123AB", air), (None, None))      # registration used as callsign
        self.assertEqual(server.airline_for("", air), (None, None))

    def test_describe_type(self):
        k = server.describe_type({"t": "EC35", "category": "A7"})
        self.assertEqual((k["shape"], k["military"], k["type_name"]), ("heli", False, "Airbus H135"))
        self.assertEqual(server.describe_type({"category": "A7"})["shape"], "heli")
        self.assertEqual(server.describe_type({"t": "B748"})["variant"], "hump")
        self.assertTrue(server.describe_type({"t": "F16"})["military"])
        self.assertTrue(server.describe_type({"t": "A332", "dbFlags": 1})["military"])      # e.g. an A330 tanker
        self.assertFalse(server.describe_type({"t": "A332", "dbFlags": 0})["military"])
        self.assertEqual(server.describe_type({})["shape"], "narrow")

    def test_demo_planes(self):
        air = server.load_airlines(dict(server.DEFAULTS, DEMO="1", USER_DATA_DIR="/nonexistent"))
        planes, _ = server.build_planes(self._demo(), LAT, LON, 10, air, None, demo=True)
        by = {p["hex"]: p for p in planes}
        self.assertEqual(by["dd0001"]["airline"], "Zenith Air")
        self.assertTrue(by["dd0001"]["photo"].startswith("/demo/photos/"))
        self.assertEqual(by["dd0001"]["type_name"], "Airbus A320")
        self.assertEqual(by["3e1a2b"]["shape"], "heli")
        self.assertIsNone(by["3e1a2b"]["airline"])
        self.assertEqual((by["dd0003"]["shape"], by["dd0003"]["variant"]), ("quad", "deck"))
        self.assertEqual((by["dd0012"]["shape"], by["dd0012"]["variant"]), ("quad", "hump"))
        self.assertEqual(by["dd0010"]["shape"], "fighter")
        self.assertTrue(by["dd0010"]["military"])
        self.assertEqual(by["dd0010"]["airline"], "MILITARY")
        self.assertEqual(by["dd0011"]["shape"], "airlifter")
        self.assertIsNone(by["dd0010"]["photo"])                                  # no photo -> the wall shows its animated scene
        self.assertIsNone(by["4ca7b3"]["photo"])
        for p in planes:                                                          # every demo photo file exists
            if p["photo"]:
                self.assertTrue(os.path.isfile(os.path.join(HERE, "..", "flightinfo", p["photo"].replace("/demo/", "demo/"))), p["photo"])

    def test_photo_credit_and_link(self):
        lookup = lambda h: {"url": "u", "photographer": "Jane Doe", "link": "https://www.planespotters.net/photo/1"} if h == "dd0001" else None  # noqa: E731
        planes, _ = server.build_planes(self._demo(), LAT, LON, 10, {}, lookup, demo=False)
        by = {p["hex"]: p for p in planes}
        self.assertEqual(by["dd0001"]["photo"], "/api/photo/dd0001")
        self.assertEqual(by["dd0001"]["photo_credit"], "Jane Doe")
        self.assertEqual(by["dd0001"]["photo_link"], "https://www.planespotters.net/photo/1")
        self.assertIsNone(by["dd0002"]["photo"])

    def test_no_logo_api(self):
        self.assertFalse(hasattr(server, "find_logo"))
        self.assertNotIn("show_logos", server.public_config(dict(server.DEFAULTS)))
        self.assertNotIn("SHOW_LOGOS", server.DEFAULTS)

    def test_curated_airline_names(self):
        air = server.load_airlines(dict(server.DEFAULTS))
        self.assertEqual(air["SWR"]["name"], "Swiss")

    def test_public_config_defaults(self):
        cfg = dict(server.DEFAULTS, UNITS="bogus")
        self.assertEqual(server.public_config(cfg)["units"], "metric")
        self.assertEqual(server.public_config(dict(cfg, THEME="purple"))["theme"], "amber")   # amber is the default
        self.assertEqual(server.public_config(cfg)["radius_presets"], [1, 2, 5, 10, 15, 30, 50])


class ThrottledLookupTests(unittest.TestCase):
    """Planespotters refuses bursts with 403, so slow lookups are spaced out and failures are retried."""

    def make(self, found_ttl=None):
        self.calls = []

        def fake(key):
            self.calls.append((key, time.monotonic()))
            if key == "ref403":
                return None, False                      # refused / no answer
            if key == "nopic":
                return None, True                       # reached, but nothing published
            return {"url": "http://x/p.jpg", "photographer": "P", "link": "l"}, True

        return server.ThrottledLookup(fake, gap=0.2, retry=0.4, miss_retry=1000, found_ttl=found_ttl)

    def test_requests_are_spaced_and_failures_retried(self):
        lk = self.make()
        for h in ("a1", "a2", "a3", "ref403", "nopic"):
            lk.get(h)
        time.sleep(1.8)
        self.assertEqual(len(self.calls), 5, "every key must be asked for exactly once")
        gaps = [self.calls[i + 1][1] - self.calls[i][1] for i in range(len(self.calls) - 1)]
        self.assertTrue(all(g >= 0.18 for g in gaps), "requests were sent too fast: %s" % gaps)

        self.assertIsNotNone(lk.get("a1"))
        self.assertIsNone(lk.cache["ref403"]["value"], "a refused lookup must not become a value")
        self.assertIsNotNone(lk.cache["ref403"]["retry_at"], "a refused lookup must stay retryable")
        self.assertIsNone(lk.cache["nopic"]["value"])

        n = len(self.calls)
        for _ in range(5):
            lk.get("a1")
            lk.get("nopic")
        time.sleep(0.5)
        self.assertEqual(len(self.calls), n, "a settled key must not be asked for again")

        lk.get("ref403")                                 # past `retry` by now
        time.sleep(0.6)
        self.assertGreater(len(self.calls), n, "a refused lookup must be retried later")

    def test_found_values_expire_when_a_ttl_is_set(self):
        lk = self.make(found_ttl=0.3)
        lk.get("x1")
        time.sleep(0.4)
        self.assertIsNotNone(lk.get("x1"), "the old value is still served while it is refreshed")
        time.sleep(0.5)
        self.assertEqual(len([c for c in self.calls if c[0] == "x1"]), 2, "a stale value must be looked up again")

    def test_a_crashing_fetch_does_not_kill_the_worker(self):
        seen = []

        def fetch(key):
            seen.append(key)
            if key == "boom":
                raise RuntimeError("bad answer")
            return "ok", True

        lk = server.ThrottledLookup(fetch, gap=0.0, retry=5, miss_retry=5)
        lk.get("boom")
        lk.get("fine")
        time.sleep(0.4)
        self.assertEqual(seen, ["boom", "fine"])
        self.assertEqual(lk.peek("fine"), "ok")


ADSBDB_SAMPLE = {"response": {"flightroute": {
    "callsign": "DLH4YK",
    "origin": {"country_iso_name": "DE", "iata_code": "MUC", "icao_code": "EDDM", "municipality": "Munich", "name": "Munich Airport"},
    "destination": {"country_iso_name": "BG", "iata_code": "SOF", "icao_code": "LBSF", "municipality": "Sofia", "name": "Sofia Airport"}}}}


# A real adsbdb answer, read on 15 October 2026: the route comes with the airline behind the callsign.
ADSBDB_EASYJET = {"response": {"flightroute": {
    "callsign": "EZY1234", "callsign_icao": "EZY1234", "callsign_iata": "U21234",
    "airline": {"name": "easyJet", "icao": "EZY", "iata": "U2", "country": "United Kingdom", "country_iso": "GB", "callsign": "EASY"},
    "origin": {"country_iso_name": "GB", "country_name": "United Kingdom", "elevation": 135, "iata_code": "EDI", "icao_code": "EGPH",
               "latitude": 55.95015, "longitude": -3.37229, "municipality": "Edinburgh", "name": "Edinburgh Airport"},
    "destination": {"country_iso_name": "FR", "country_name": "France", "elevation": 885, "iata_code": "BSL", "icao_code": "LFSB",
                    "latitude": 47.60068, "longitude": 7.52112, "municipality": "Saint-Louis", "name": "EuroAirport Basel-Mulhouse-Freiburg"}}}}


class LearnedAirlineTests(unittest.TestCase):
    """0.17.0: a callsign outside the built-in list gets its airline name from the route answer the wall already asks for."""

    def setUp(self):
        with server._learned["lock"]:
            server._learned["data"].clear()

    def test_the_real_answer_names_the_airline(self):
        self.assertEqual(server.parse_airline(ADSBDB_EASYJET), {"icao": "EZY", "name": "easyJet", "iata": "U2"})
        self.assertEqual(server.parse_route(ADSBDB_EASYJET)["to"]["iata"], "BSL")     # the route still comes out of the same answer

    def test_learned_name_shows_for_every_callsign_of_that_prefix(self):
        self.assertEqual(server.airline_for("EZY52AB", {}), ("EZY", None))            # not in the built-in list: bare
        server.learn_airline(ADSBDB_EASYJET)
        self.assertEqual(server.airline_for("EZY52AB", {}), ("EZY", {"name": "easyJet", "iata": "U2", "learned": True}))
        self.assertEqual(server.airline_for("EZY1", {}), ("EZY", {"name": "easyJet", "iata": "U2", "learned": True}))
        self.assertEqual(server.airline_for("RYR1", {}), ("RYR", None))              # another prefix learns nothing from it

    def test_builtin_list_wins_over_what_was_learned(self):
        server.learn_airline(ADSBDB_EASYJET)
        self.assertEqual(server.airline_for("EZY1", {"EZY": {"name": "EASYJET SHORT", "iata": "U2"}})[1]["name"], "EASYJET SHORT")

    def test_corporate_suffixes_are_dropped_and_broken_answers_teach_nothing(self):
        self.assertEqual(server.clean_airline_name("American Airlines Inc."), "American Airlines")
        self.assertEqual(server.clean_airline_name("Lufthansa Cargo AG"), "Lufthansa Cargo")
        self.assertEqual(server.clean_airline_name("  Air  France "), "Air France")
        for bad in ({"response": "unknown callsign"}, {"response": {"flightroute": {"airline": {"name": "X", "icao": "TOOLONG"}}}},
                    {"response": {"flightroute": {"airline": {"icao": "ABC", "name": ""}}}}, None, "garbage"):
            self.assertIsNone(server.learn_airline(bad))
        self.assertEqual(server._learned["data"], {})

    def test_the_wall_shows_the_learned_name(self):
        server.learn_airline(ADSBDB_EASYJET)
        ac = {"hex": "4071f1", "flight": "EZY52AB ", "lat": 49.7, "lon": 6.2, "seen_pos": 1, "alt_baro": 35000, "gs": 440, "track": 90}
        planes, _ = server.build_planes({"aircraft": [ac]}, 49.6, 6.1, 100, airlines={})
        self.assertEqual(planes[0]["airline"], "easyJet")
        self.assertEqual(planes[0]["airline_icao"], "EZY")


class OnlyHexTest(unittest.TestCase):
    """0.18.2: social sharing asks the wall about one far aircraft (a range record) without setting off lookups
    for everything in between."""

    def test_only_that_aircraft_and_no_lookup_for_the_others(self):
        asked = []
        data = {"aircraft": [{"hex": "aaaaaa", "lat": 49.61, "lon": 6.13, "seen_pos": 1, "flight": "AAA1"},
                             {"hex": "bbbbbb", "lat": 49.62, "lon": 6.14, "seen_pos": 1, "flight": "BBB2"}]}
        planes, total = server.build_planes(data, 49.6, 6.13, 500, route_lookup=lambda cs: asked.append(cs), only_hex="bbbbbb")
        self.assertEqual([p["hex"] for p in planes], ["bbbbbb"])
        self.assertEqual(asked, ["BBB2"])
        self.assertEqual(total, 2)


class RouteTests(unittest.TestCase):
    def test_parse_real_adsbdb_answer(self):
        r = server.parse_route(ADSBDB_SAMPLE)
        self.assertEqual(r["from"], {"iata": "MUC", "icao": "EDDM", "name": "Munich Airport", "city": "Munich", "country": "DE"})
        self.assertEqual(r["to"]["iata"], "SOF")

    def test_parse_unknown_or_broken_answers(self):
        self.assertIsNone(server.parse_route({"response": "unknown callsign"}))
        self.assertIsNone(server.parse_route({"response": {"flightroute": {}}}))
        self.assertIsNone(server.parse_route("garbage"))
        self.assertIsNone(server.parse_route(None))
        half = server.parse_route({"response": {"flightroute": {"origin": {"municipality": "Metz"}}}})
        self.assertEqual(half["from"]["city"], "Metz")
        self.assertIsNone(half["to"])

    def test_implausible_routes_are_dropped(self):
        def ap(code, lat, lon, city=""):
            return {"iata": code, "icao": "", "name": code + " Airport", "city": city or code, "country": "", "lat": lat, "lon": lon}
        ema, lux = ap("EMA", 52.83, -1.33), ap("LUX", 49.63, 6.20)
        mad, mxp = ap("MAD", 40.49, -3.57), ap("MXP", 45.63, 8.72)
        ok = server.route_plausible
        # the same airport twice (a real case: East Midlands to East Midlands)
        self.assertIsNone(ok({"from": ema, "to": dict(ema)}, 49.3, 6.3, 60, 250))
        # LUX-EMA seen near the line, heading to EMA (west-north-west): kept
        r = {"from": lux, "to": ema}
        self.assertIs(ok(r, 50.5, 4.0, 300, 250), r)
        # Madrid-Milan, but the aircraft is far north of that line over Lorraine: dropped
        self.assertIsNone(ok({"from": mad, "to": mxp}, 49.0, 6.5, 120, 450))
        # on the Madrid-Milan line: kept
        r = {"from": mad, "to": mxp}
        self.assertIs(ok(r, 43.0, 3.0, 65, 450), r)
        # on the line but flying the other way (callsign reused for the return leg): dropped
        self.assertIsNone(ok(r, 43.0, 3.0, 245, 450))
        # no airport position (older cache / odd answer): cannot check, kept
        r2 = {"from": {"city": "A"}, "to": {"city": "B"}}
        self.assertIs(ok(r2, 49.0, 6.0, 0, 400), r2)
        self.assertIsNone(ok(None, 49.0, 6.0))
        # just after take-off the heading may point anywhere: not judged near the airports
        r = {"from": lux, "to": ema}
        self.assertIs(ok(r, 49.7, 6.3, 150, 180), r)
        # only one end known: kept
        r3 = {"from": lux, "to": None}
        self.assertIs(ok(r3, 40.0, 0.0, 0, 400), r3)

    def test_parse_keeps_airport_position_only_when_given(self):
        a = dict(ADSBDB_SAMPLE["response"]["flightroute"]["origin"], latitude=48.35, longitude=11.78)
        r = server.parse_route({"response": {"flightroute": {"origin": a, "destination": ADSBDB_SAMPLE["response"]["flightroute"]["destination"]}}})
        self.assertEqual((r["from"]["lat"], r["from"]["lon"]), (48.35, 11.78))
        self.assertNotIn("lat", r["to"])

    def test_build_planes_drops_a_route_that_cannot_be_this_flight(self):
        ema = {"iata": "EMA", "icao": "EGNX", "name": "East Midlands", "city": "East Midlands", "country": "GB", "lat": 52.83, "lon": -1.33}
        data = {"aircraft": [{"hex": "4b0001", "flight": "LGL12", "lat": 49.25, "lon": 6.22, "seen_pos": 0, "track": 60, "gs": 250}]}
        planes, _ = server.build_planes(data, 49.246, 6.223, 10, {}, None, False, None, lambda cs: {"from": ema, "to": dict(ema)})
        self.assertIsNone(planes[0]["route"])

    def test_hexdb_route_parsing(self):
        self.assertEqual(server.parse_hexdb_route("EGNX-ELLX-EGNX"), [("EGNX", "ELLX"), ("ELLX", "EGNX")])
        self.assertEqual(server.parse_hexdb_route("EIDW-EGLL"), [("EIDW", "EGLL")])
        for bad in ("", None, "EIDW", "EIDW-", "EIDW-EGLL-<script>", "EIDWX-EGLL", "EGNX-EGNX", "A-B-C-D-E-F-G-H"):
            self.assertEqual(server.parse_hexdb_route(bad), [], bad)

    def test_second_opinion_from_hexdb_is_cached_and_lean(self):
        calls = []
        airports = {"EGNX": (52.83, -1.33), "ELLX": (49.63, 6.20), "EGLL": (51.47, -0.46)}

        def fake(path):
            calls.append(path)
            if path.startswith("/route/icao/"):
                return {"flight": "LGL12", "route": "EGNX-ELLX-EGNX"}
            code = path.rsplit("/", 1)[1]
            lat, lon = airports[code]
            return {"icao": code, "airport": code + " Airport", "location": code + " City", "country_code": "XX", "latitude": lat, "longitude": lon}
        real, server._hexdb_json = server._hexdb_json, fake
        server._airport_cache.clear()
        try:
            value, ok = server._route2_api("LGL12")
            self.assertTrue(ok)
            self.assertEqual([(r["from"]["icao"], r["to"]["icao"]) for r in value], [("EGNX", "ELLX"), ("ELLX", "EGNX")])
            n = len(calls)
            self.assertEqual(n, 1 + 2, "one route request and one per DISTINCT airport (2), not per leg end: %s" % calls)
            server._route2_api("LGL12")
            self.assertEqual(len(calls), n + 1, "the airports are remembered: only the route is asked again")
            # an unreachable service is "no answer", never "not found"
            def down(path):
                raise OSError("no internet")
            server._hexdb_json = down
            server._airport_cache.clear()
            self.assertEqual(server._route2_api("LGL12"), (None, False))
        finally:
            server._hexdb_json = real
            server._airport_cache.clear()

    def test_wall_takes_the_second_opinion_only_when_the_first_is_wrong(self):
        ema = {"iata": "EMA", "icao": "EGNX", "name": "East Midlands", "city": "East Midlands", "country": "GB", "lat": 52.83, "lon": -1.33}
        lux = {"iata": "LUX", "icao": "ELLX", "name": "Luxembourg", "city": "Luxembourg", "country": "LU", "lat": 49.63, "lon": 6.20}
        data = {"aircraft": [{"hex": "4b0001", "flight": "LGL12", "lat": 50.6, "lon": 3.9, "seen_pos": 0, "track": 300, "gs": 250}]}
        asked = []
        def second(cs):
            asked.append(cs)
            return [{"from": ema, "to": lux}, {"from": lux, "to": ema}]
        planes, _ = server.build_planes(data, 50.6, 3.9, 10, {}, None, False, None, lambda cs: {"from": ema, "to": dict(ema)}, None, second)
        self.assertEqual(planes[0]["route"]["to"]["icao"], "EGNX", "the leg the aircraft is really on (LUX to EMA, heading west-north-west)")
        self.assertEqual(planes[0]["route"]["from"]["icao"], "ELLX")
        # the first answer is fine: the second service is not even asked
        asked.clear()
        good = {"from": lux, "to": ema}
        planes, _ = server.build_planes(data, 50.6, 3.9, 10, {}, None, False, None, lambda cs: good, None, second)
        self.assertEqual(asked, [])
        self.assertIs(planes[0]["route"], good)
        # nothing plausible from either: empty
        planes, _ = server.build_planes(data, 50.6, 3.9, 10, {}, None, False, None, lambda cs: {"from": ema, "to": dict(ema)}, None, lambda cs: None)
        self.assertIsNone(planes[0]["route"])
        # a second opinion that cannot be checked (no airport positions) is not believed
        unchecked = [{"from": {"city": "A"}, "to": {"city": "B"}}]
        planes, _ = server.build_planes(data, 50.6, 3.9, 10, {}, None, False, None, lambda cs: {"from": ema, "to": dict(ema)}, None, lambda cs: unchecked)
        self.assertIsNone(planes[0]["route"])

    def test_only_airline_callsigns_are_looked_up(self):
        asked = []
        real = server._routes
        server._routes = type("Fake", (), {"get": staticmethod(lambda k: asked.append(k) or {"from": None, "to": None})})()
        try:
            for cs in ("DLH4YK", "RYR8WL", "EZY45RF", "ZZA210", "dlh4yk ", "DEZPA", "N123AB", "D-EZPA", "", None, "SAMU34"):
                server.lookup_route(cs)
        finally:
            server._routes = real
        self.assertEqual(asked, ["DLH4YK", "RYR8WL", "EZY45RF", "ZZA210", "DLH4YK"])   # SAMU34: four letters, not an airline callsign

    def test_build_planes_uses_demo_route_then_lookup(self):
        data = {"aircraft": [
            {"hex": "dd0001", "flight": "ZZA210", "lat": 49.25, "lon": 6.22, "seen_pos": 0, "demo_route": {"from": {"city": "A"}, "to": {"city": "B"}}},
            {"hex": "3c6444", "flight": "DLH4YK", "lat": 49.26, "lon": 6.22, "seen_pos": 0},
            {"hex": "aaaaaa", "flight": "", "lat": 49.27, "lon": 6.22, "seen_pos": 0}]}
        asked = []
        planes, _ = server.build_planes(data, 49.246, 6.223, 10, {}, None, True, None, lambda cs: asked.append(cs) or {"from": {"city": "MUNICH"}, "to": None})
        by = {p["hex"]: p for p in planes}
        self.assertEqual(by["dd0001"]["route"]["to"]["city"], "B", "a demo route wins")
        self.assertEqual(by["3c6444"]["route"]["from"]["city"], "MUNICH")
        self.assertEqual(asked, ["DLH4YK", ""])
        planes, _ = server.build_planes(data, 49.246, 6.223, 10, {}, None, True, None, None)
        self.assertIsNone({p["hex"]: p for p in planes}["3c6444"]["route"], "no lookup configured -> no route")

    def test_demo_has_routes_for_some_aircraft_only(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "flightinfo", "demo", "aircraft.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        planes, _ = server.build_planes(data, 49.246, 6.223, 10, {}, None, True, None, None)
        with_route = [p["hex"] for p in planes if p["route"]]
        self.assertGreaterEqual(len(with_route), 5)
        self.assertLess(len(with_route), len(planes), "some demo aircraft must show the no-route state")




class UatMergeTests(unittest.TestCase):
    def test_path_only_when_enabled(self):
        self.assertIsNone(server.uat_json_path({"UAT978": "0"}))
        self.assertIsNone(server.uat_json_path({}))
        self.assertEqual(server.uat_json_path({"UAT978": "1"}), "/run/skyaware978/aircraft.json")
        self.assertEqual(server.uat_json_path({"UAT978": "1", "AIRCRAFT_JSON_978": "/x.json"}), "/x.json")

    def test_lists_are_joined(self):
        a = {"now": 5, "aircraft": [{"hex": "aaaaaa", "lat": 1, "lon": 1}]}
        u = {"aircraft": [{"hex": "~123456", "lat": 2, "lon": 2}]}
        out = server.merge_aircraft(a, u)
        self.assertEqual([x["hex"] for x in out["aircraft"]], ["aaaaaa", "~123456"])
        self.assertEqual(out["now"], 5)

    def test_same_aircraft_keeps_the_fresher_entry(self):
        a = {"aircraft": [{"hex": "ABCDEF", "seen_pos": 9, "tag": "1090"}]}
        u = {"aircraft": [{"hex": "abcdef", "seen_pos": 1, "tag": "978"}]}
        out = server.merge_aircraft(a, u)
        self.assertEqual(len(out["aircraft"]), 1)
        self.assertEqual(out["aircraft"][0]["tag"], "978")
        out = server.merge_aircraft(u, a)
        self.assertEqual(out["aircraft"][0]["tag"], "978")

    def test_missing_or_broken_sides_are_harmless(self):
        self.assertEqual(server.merge_aircraft({}, {"aircraft": [{"hex": "a"}]})["aircraft"], [{"hex": "a"}])
        self.assertEqual(server.merge_aircraft({"aircraft": [{"hex": "a"}]}, {})["aircraft"], [{"hex": "a"}])
        self.assertEqual(server.merge_aircraft({"aircraft": [3, None, {"hex": "b"}]}, {"aircraft": "x"})["aircraft"], [{"hex": "b"}])

    def test_read_json(self):
        self.assertIsNone(server.read_json("/nonexistent/file.json"))



class AircraftLookupTests(unittest.TestCase):
    SAMPLE = {"response": {"aircraft": {"type": "C Series 300", "icao_type": "BCS3", "manufacturer": "Bombardier",
                                        "mode_s": "4B1805", "registration": "HB-JCN"}}}

    def test_parse(self):
        info = server.parse_aircraft(self.SAMPLE)
        self.assertEqual((info["icao_type"], info["registration"], info["manufacturer"]), ("BCS3", "HB-JCN", "Bombardier"))
        for bad in ({"response": "unknown aircraft"}, {"response": {"aircraft": {}}}, "x", None):
            self.assertIsNone(server.parse_aircraft(bad))

    def test_only_hex_codes_are_looked_up(self):
        asked = []
        real = server._aircraft
        server._aircraft = type("Fake", (), {"get": staticmethod(lambda k: asked.append(k) or None)})()
        try:
            for h in ("4b1805", "4B1805 ", "zzzzzz", "12345", "", None):
                server.lookup_aircraft(h)
        finally:
            server._aircraft = real
        self.assertEqual(asked, ["4B1805", "4B1805"])

    def test_model_comes_from_lookup_when_the_decoder_has_none(self):
        data = {"aircraft": [
            {"hex": "4b1805", "flight": "SWR123", "lat": 49.25, "lon": 6.22, "seen_pos": 0},            # decoder knows nothing
            {"hex": "3c6444", "flight": "DLH4YK", "lat": 49.26, "lon": 6.22, "seen_pos": 0, "t": "A320", "r": "D-AIUA"}]}
        asked = []
        def lk(h):
            asked.append(h)
            return server.parse_aircraft(self.SAMPLE)
        planes, _ = server.build_planes(data, 49.246, 6.223, 20, {}, None, False, {}, None, lk)
        by = {p["hex"]: p for p in planes}
        self.assertEqual((by["4b1805"]["type"], by["4b1805"]["registration"], by["4b1805"]["type_name"]), ("BCS3", "HB-JCN", "Airbus A220-300"))
        self.assertEqual(by["3c6444"]["type"], "A320")
        self.assertEqual(asked, ["4b1805"])                      # the decoder already knew the other one: no request

    def test_unknown_type_falls_back_on_maker_and_name(self):
        info = {"icao_type": "ZZ99", "type": "Skyfoo 9", "manufacturer": "Acme", "registration": "X-1"}
        data = {"aircraft": [{"hex": "aaaaaa", "lat": 49.25, "lon": 6.22, "seen_pos": 0}]}
        planes, _ = server.build_planes(data, 49.246, 6.223, 20, {}, None, False, {}, None, lambda h: info)
        self.assertEqual(planes[0]["type_name"], "Acme Skyfoo 9")

    def test_no_lookup_when_turned_off(self):
        data = {"aircraft": [{"hex": "aaaaaa", "lat": 49.25, "lon": 6.22, "seen_pos": 0}]}
        planes, _ = server.build_planes(data, 49.246, 6.223, 20, {}, None, False, {}, None, None)
        self.assertIsNone(planes[0]["type"])


class DisplayModeTests(unittest.TestCase):
    def test_display_mode_is_dots_unless_flap_is_chosen(self):
        self.assertEqual(server.public_config({})["display_mode"], "dots")
        self.assertEqual(server.public_config({"DISPLAY_MODE": "flap"})["display_mode"], "flap")
        self.assertEqual(server.public_config({"DISPLAY_MODE": "FLAP"})["display_mode"], "flap")
        self.assertEqual(server.public_config({"DISPLAY_MODE": "weird"})["display_mode"], "dots")


class ThemeTest(unittest.TestCase):
    """A colour lives in four places at once. When they drift, a theme silently falls back to amber."""

    def _read(self, *parts):
        with open(os.path.join(os.path.dirname(__file__), "..", *parts)) as fh:
            return fh.read()

    def test_every_theme_is_known_everywhere(self):
        css, html, shell = self._read("flightinfo", "static", "style.css"), \
            self._read("flightinfo", "static", "index.html"), self._read("lib", "common.sh")
        for name in server.THEMES:
            if name != "amber":                        # amber is the default, it has no rule of its own
                self.assertIn('body[data-theme="%s"]' % name, css, name)
            self.assertIn('<option value="%s">' % name, html, name)
            self.assertIn(name, shell.split("valid_theme()")[1].split("\n")[0], name)

    def test_the_two_new_colours_are_the_ones_asked_for(self):
        css = self._read("flightinfo", "static", "style.css")
        self.assertIn("--dot: #00d6d7", css)           # turquoise
        self.assertIn("--dot: #0404e2", css)           # blue

    def test_an_unknown_colour_falls_back_on_amber(self):
        self.assertEqual(server.public_config({"THEME": "mauve"})["theme"], "amber")
        self.assertEqual(server.public_config({"THEME": "turquoise"})["theme"], "turquoise")


class FlagsAndCycleTest(unittest.TestCase):
    """The flags are on unless a Pi says otherwise, and an aircraft stays on screen for 14 seconds."""

    def test_flags_are_on_even_on_a_pi_installed_before_they_existed(self):
        self.assertTrue(server.public_config({})["flags"])            # no FLAGS line in an older config.env
        self.assertTrue(server.public_config({"FLAGS": "1"})["flags"])
        self.assertFalse(server.public_config({"FLAGS": "0"})["flags"])

    def test_the_wall_is_told_whether_there_is_a_statistics_page_to_offer(self):
        # 0.17.4: the gear panel shows a way to /stats, but only while statistics are on — a link to a feature
        # nobody switched on leads to a page that says "off", which is a dead end dressed as a door.
        self.assertFalse(server.public_config({})["stats"])            # off by default, and on an older config.env
        self.assertFalse(server.public_config({"STATS": "0"})["stats"])
        self.assertTrue(server.public_config({"STATS": "1"})["stats"])

    def test_an_aircraft_stays_fourteen_seconds(self):
        self.assertEqual(server.public_config({})["cycle_seconds"], 14)
        self.assertEqual(server.DEFAULTS["CYCLE_SECONDS"], "14")
        self.assertEqual(server.public_config({"CYCLE_SECONDS": "6"})["cycle_seconds"], 6)

    def test_a_setting_that_starts_off_still_starts_off(self):
        self.assertFalse(server.public_config({})["demo"])            # cfg_bool's own default is unchanged


class WhoMayReadTest(unittest.TestCase):
    """The wall has no login, so who may read it is decided by where they come from."""

    def test_home_networks_are_allowed_and_the_internet_is_not(self):
        for addr in ("192.168.1.20", "10.0.0.3", "172.16.4.4", "127.0.0.1", "::1", "fe80::1%wlan0", "::ffff:192.168.1.5"):
            self.assertTrue(server.client_allowed(addr, "private"), addr)
        for addr in ("8.8.8.8", "2a01:e0a:1::1", "100.64.0.1", "203.0.113.9"):
            self.assertFalse(server.client_allowed(addr, "private"), addr)

    def test_any_opens_it_and_a_list_narrows_it(self):
        self.assertTrue(server.client_allowed("8.8.8.8", "any"))
        self.assertTrue(server.client_allowed("10.8.0.5", "10.8.0.0/24, 192.168.1.0/24"))
        self.assertFalse(server.client_allowed("10.9.0.5", "10.8.0.0/24, 192.168.1.0/24"))
        self.assertTrue(server.client_allowed("192.168.1.77", "10.8.0.0/24, 192.168.1.0/24"))

    def test_a_broken_setting_falls_back_to_private_never_to_open(self):
        for policy in ("", None, "garbage", "10.8.0.0/99", "10.8.0.0/24,notanet"):
            self.assertTrue(server.client_allowed("192.168.1.5", policy), repr(policy))
            self.assertFalse(server.client_allowed("8.8.8.8", policy), repr(policy))
        self.assertFalse(server.client_allowed("notanip", "private"))

    def test_the_default_setting_is_private(self):
        self.assertEqual(server.DEFAULTS["ALLOW_FROM"], "private")
        self.assertEqual(server.DEFAULTS["BIND_ADDRESS"], "0.0.0.0")

    def test_the_running_server_refuses_with_403(self):
        # The real server, on the loopback address. 127.0.0.1 is private, so the default lets it in; a list that
        # leaves the loopback out must turn the same request away with a 403 and not with a crash.
        import http.client, socket, tempfile, threading
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as fh:
            fh.write("ALLOW_FROM=private\n")
            cfgpath = fh.name
        old_cfg = server.CONFIG_FILE
        server.CONFIG_FILE = cfgpath
        server._cfg_cache.update(mtime=None)                      # forget whatever config an earlier test loaded
        httpd = server.WallServer(("127.0.0.1", 0), server.Handler)
        port = httpd.server_address[1]
        t = threading.Thread(target=httpd.serve_forever, daemon=True); t.start()
        try:
            def get(path):
                c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                c.request("GET", path); r = c.getresponse(); body = r.read(); c.close()
                return r.status, body
            self.assertEqual(get("/api/health")[0], 200)
            with open(cfgpath, "w") as fh:
                fh.write("ALLOW_FROM=10.8.0.0/24\n")
            os.utime(cfgpath, (time.time() + 5, time.time() + 5))     # make the change visible to the mtime cache
            status, body = get("/api/health")
            self.assertEqual(status, 403)
            self.assertIn(b"ALLOW_FROM", body)
            with open(cfgpath, "w") as fh:
                fh.write("ALLOW_FROM=any\n")
            os.utime(cfgpath, (time.time() + 10, time.time() + 10))
            self.assertEqual(get("/api/health")[0], 200)
        finally:
            httpd.shutdown(); httpd.server_close()
            server.CONFIG_FILE = old_cfg
            server._cfg_cache.update(mtime=None)
            os.unlink(cfgpath)


class StatsTest(unittest.TestCase):
    """What the stats timer wrote, turned into what the page shows. Written against a folder made here."""

    def _dir(self):
        import tempfile
        d = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        return d

    def test_no_folder_means_none(self):
        self.assertIsNone(server.read_stats(self._dir() + "/missing"))

    def test_rows_become_hours_days_and_today(self):
        import datetime
        d = self._dir()
        now = datetime.datetime(2026, 10, 15, 14, 7)
        lines = ["when,messages,farthest_km,aircraft_pos,aircraft_seen"]
        # yesterday: two samples; today: 13:00, 13:15, 13:30 and one at 02:00 (inside the 24 h window) and one 30 h ago (outside)
        lines += ["2026-10-14 09:00,1000,290,20,120", "2026-10-14 09:15,1100,301,22,130",
                  "2026-10-15 02:00,200,150,3,40", "2026-10-15 13:00,800,312,18,200", "2026-10-15 13:15,900,300,19,230",
                  "2026-10-15 13:30,700,280,17,260", "2026-10-14 07:30,50,100,1,10", "garbage,line", "2026-10-13 25:99,1,1,1,1"]
        with open(os.path.join(d, "stats.csv"), "w") as fh:
            fh.write("\n".join(lines) + "\n")
        with open(os.path.join(d, "seen-2026-10-15"), "w") as fh:
            fh.write("3c6444\n4ca123\na1b2c3\n\nff0001\n")       # four aircraft, one blank line
        r = server.read_stats(d, now)
        self.assertTrue(r["enabled"])
        self.assertEqual(r["samples"], 7)                         # the two broken lines are skipped
        self.assertEqual(r["since"], "2026-10-14 07:30")
        self.assertEqual(r["hours"][13]["messages"], 2400)        # 800 + 900 + 700
        self.assertEqual(r["hours"][13]["samples"], 3)
        self.assertEqual(r["hours"][2]["messages"], 200)
        self.assertEqual(r["hours"][9]["messages"], 0)            # yesterday 09:00 is more than 24 h before 14:07? no: 29 h ago -> outside
        self.assertEqual(r["hours"][7]["messages"], 0)            # 30 h ago: outside the window
        t = r["today"]
        self.assertEqual(t["day"], "2026-10-15")
        self.assertEqual(t["aircraft"], 4)                        # from the day file, not the CSV's running 260
        self.assertEqual(t["messages"], 2600)
        self.assertEqual(t["farthest_km"], 312)
        self.assertEqual(t["busiest_hour"], 13)
        self.assertEqual(t["busiest_messages"], 2400)
        days = {x["day"]: x for x in r["days"]}
        self.assertEqual(sorted(days), ["2026-10-14", "2026-10-15"])
        self.assertEqual(days["2026-10-14"]["farthest_km"], 301)
        self.assertEqual(days["2026-10-14"]["aircraft"], 130)     # no day file: the CSV's running count
        self.assertEqual(days["2026-10-14"]["messages"], 2150)
        self.assertEqual(r["best"], {"day": "2026-10-15", "farthest_km": 312})

    def test_empty_file_is_on_but_empty(self):
        d = self._dir()
        with open(os.path.join(d, "stats.csv"), "w") as fh:
            fh.write("when,messages,farthest_km,aircraft_pos,aircraft_seen\n")
        r = server.read_stats(d)
        self.assertEqual(r["samples"], 0)
        self.assertIsNone(r["best"])
        self.assertEqual(r["today"]["aircraft"], 0)

    def test_the_api_says_off_when_the_setting_is_off(self):
        import http.client, tempfile, threading
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as fh:
            fh.write("STATS=0\n"); cfgpath = fh.name
        old_cfg, old_dir = server.CONFIG_FILE, server.STATS_DIR
        server.CONFIG_FILE = cfgpath; server._cfg_cache.update(mtime=None)
        httpd = server.WallServer(("127.0.0.1", 0), server.Handler); port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            def get(path):
                c = http.client.HTTPConnection("127.0.0.1", port, timeout=5); c.request("GET", path); r = c.getresponse(); b = r.read(); c.close(); return r.status, b
            st, body = get("/api/stats")
            self.assertEqual(st, 200)
            # 0.17.2: the page names the version it runs, so a screenshot says which code drew it. It travels
            # with the answer whether statistics are on or off, because the page shows the line in both states.
            self.assertEqual(json.loads(body), {"enabled": False, "version": server.VERSION})
            st, body = get("/stats")
            self.assertEqual(st, 200); self.assertIn(b"ZenithBoard statistics", body)
            d = self._dir()
            with open(os.path.join(d, "stats.csv"), "w") as fh:
                fh.write("when,messages,farthest_km,aircraft_pos,aircraft_seen\n2026-10-15 13:00,800,312,18,200\n")
            server.STATS_DIR = d
            with open(cfgpath, "w") as fh:
                fh.write("STATS=1\n")
            os.utime(cfgpath, (time.time() + 5, time.time() + 5))
            st, body = get("/api/stats")
            j = json.loads(body)
            self.assertTrue(j["enabled"]); self.assertEqual(j["samples"], 1); self.assertEqual(j["days"][0]["farthest_km"], 312)
            self.assertEqual(j["version"], server.VERSION)
        finally:
            httpd.shutdown(); httpd.server_close()
            server.CONFIG_FILE, server.STATS_DIR = old_cfg, old_dir
            server._cfg_cache.update(mtime=None); os.unlink(cfgpath)


class PhotoUrlTest(unittest.TestCase):
    """The photo address is somebody else's answer, and the Pi fetches it itself: it has to be checked first."""

    # The exact address Planespotters answered with on 13 October 2026. The pictures are on plnspttrs.net, not on
    # the planespotters.net the API itself answers on. 0.11.1 allowed only the latter, so every photo was refused
    # in silence and the wall drew its generic plane instead. The real address is pinned here so that a check
    # written from a guess cannot pass again.
    REAL_ANSWER = {"photos": [{"id": "1982059",
                               "thumbnail_large": {"src": "https://t.plnspttrs.net/36434/1982059_2d5d48e9d8_280.jpg"},
                               "link": "https://www.planespotters.net/photo/1982059/hb-jcn-swiss",
                               "photographer": "Mehrad Watson"}]}

    def test_the_address_planespotters_really_answers_is_allowed(self):
        self.assertTrue(server.photo_url_allowed(self.REAL_ANSWER["photos"][0]["thumbnail_large"]["src"]))

    def test_planespotters_addresses_are_allowed(self):
        for url in ("https://t.plnspttrs.net/36434/1982059_2d5d48e9d8_280.jpg",
                    "https://plnspttrs.net/x.jpg",
                    "https://cdn.planespotters.net/x.jpg",
                    "https://planespotters.net/photo.jpg",
                    "https://api.planespotters.net/pub/photos/hex/abc"):
            self.assertTrue(server.photo_url_allowed(url), url)

    def test_anything_else_is_refused(self):
        for url in ("http://cdn.planespotters.net/x.jpg",          # not https
                    "https://192.168.1.1/admin",                   # the home network
                    "https://127.0.0.1:8080/api/config",
                    "http://169.254.169.254/latest/meta-data/",
                    "file:///etc/zenithboard/config.env",
                    "https://evil.example/x.jpg",
                    "https://planespotters.net.evil.example/x.jpg",  # suffix that only looks right
                    "https://notplanespotters.net/x.jpg",
                    "https://plnspttrs.net.evil.example/x.jpg",     # the picture domain, as a prefix only
                    "https://notplnspttrs.net/x.jpg",
                    "http://t.plnspttrs.net/x.jpg",                 # the right host, but not https
                    "", None):
            self.assertFalse(server.photo_url_allowed(url), url)

    def test_an_answer_with_a_foreign_address_is_dropped(self):
        meta, ok = server.parse_photo_answer({"photos": [{"thumbnail_large": {"src": "https://evil.example/x.jpg"},
                                                          "photographer": "x", "link": "y"}]})
        self.assertIsNone(meta)
        self.assertTrue(ok)        # a complete answer, just not one to follow: do not keep asking

    def test_the_real_answer_is_kept_whole(self):
        meta, ok = server.parse_photo_answer(self.REAL_ANSWER)
        self.assertEqual(meta["url"], "https://t.plnspttrs.net/36434/1982059_2d5d48e9d8_280.jpg")
        self.assertEqual(meta["photographer"], "Mehrad Watson")
        self.assertTrue(ok)

    def test_a_normal_answer_is_kept(self):
        meta, ok = server.parse_photo_answer({"photos": [{"thumbnail_large": {"src": "https://cdn.planespotters.net/x.jpg"},
                                                          "photographer": "Jane Doe", "link": "https://www.planespotters.net/photo/1"}]})
        self.assertEqual(meta["url"], "https://cdn.planespotters.net/x.jpg")
        self.assertEqual(meta["photographer"], "Jane Doe")
        self.assertTrue(ok)


class UserAgentTest(unittest.TestCase):
    """Planespotters refuses a request that does not say who is asking and how to reach them."""

    def test_it_names_the_project_the_version_and_a_contact_address(self):
        self.assertTrue(server.USER_AGENT.startswith("ZenithBoard/" + server.VERSION))
        self.assertIn("https://github.com/regis57/ZenithBoard", server.USER_AGENT)

    def test_every_outside_request_uses_it(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "flightinfo", "server.py")) as fh:
            source = fh.read()
        self.assertNotIn('"User-Agent": "ZenithBoard/%s"', source)   # the short form Planespotters refuses
        self.assertEqual(source.count('"User-Agent": USER_AGENT'), source.count('"User-Agent"'))


class ResponseHeaderTest(unittest.TestCase):
    """A photo's type is somebody else's answer and ends up in one of our headers."""

    def test_only_known_image_types_are_passed_on(self):
        self.assertEqual(server.photo_type_allowed("image/png"), "image/png")
        self.assertEqual(server.photo_type_allowed("image/jpeg; charset=binary"), "image/jpeg")
        self.assertEqual(server.photo_type_allowed("IMAGE/WEBP"), "image/webp")

    def test_anything_else_becomes_jpeg(self):
        for ctype in ("text/html", "application/javascript", "", None,
                      "image/jpeg\r\nSet-Cookie: a=b",          # a reply split in two
                      "image/jpeg\nLocation: https://evil.example"):
            self.assertEqual(server.photo_type_allowed(ctype), "image/jpeg")

    def test_header_values_only_ever_come_from_our_tables(self):
        hv = server.Handler._header_values
        self.assertEqual(hv("application/json", "no-store"), ("application/json", "no-store"))
        self.assertEqual(hv("image/png", "max-age=3600"), ("image/png", "max-age=3600"))
        # anything we did not write ourselves gets the safe default, line break or not
        self.assertEqual(hv("text/plain\r\nX-Evil: 1", "no-store\r\nSet-Cookie: a=b"),
                         ("application/octet-stream", "no-store"))
        self.assertEqual(hv("text/html; x=y", "public"), ("application/octet-stream", "no-store"))

    def test_files_are_typed_by_their_extension(self):
        for ext, want in ((".html", "text/html; charset=utf-8"), (".js", "text/javascript; charset=utf-8"),
                          (".css", "text/css; charset=utf-8"), (".svg", "image/svg+xml"), (".json", "application/json")):
            self.assertEqual(server.FILE_TYPES[ext], want)
            self.assertIn(want, server.HEADER_TYPES)       # and every one of them is allowed through _send

    def test_every_file_the_wall_serves_has_a_known_type(self):
        for folder in ("static", "demo"):
            root = os.path.join(os.path.dirname(__file__), "..", "flightinfo", folder)
            for dirpath, _, files in os.walk(root):
                for f in files:
                    self.assertIn(os.path.splitext(f)[1].lower(), server.FILE_TYPES, os.path.join(dirpath, f))


if __name__ == "__main__":
    unittest.main()
