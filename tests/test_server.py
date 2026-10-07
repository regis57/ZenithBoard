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
        data = json.load(open(os.path.join(os.path.dirname(__file__), "..", "flightinfo", "demo", "aircraft.json"), encoding="utf-8"))
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


if __name__ == "__main__":
    unittest.main()

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
