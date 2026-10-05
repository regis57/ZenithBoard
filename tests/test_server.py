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


if __name__ == "__main__":
    unittest.main()
