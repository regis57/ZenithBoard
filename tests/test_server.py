# SPDX-License-Identifier: GPL-3.0-or-later
"""Run: python3 -m unittest discover -s tests -v"""
import json
import os
import sys
import tempfile
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
        self.assertEqual(total, 8)                      # no-position and stale aircraft ignored
        self.assertEqual(len(planes), 7)                # the EZY45RF at ~57 km is outside 10 km
        self.assertEqual(planes[0]["hex"], "3c6444")    # nearest first (aircraft on the ground)
        self.assertTrue(planes[0]["on_ground"])
        self.assertEqual(planes[0]["alt_ft"], 0)
        near, _ = server.build_planes(data, LAT, LON, 2)
        self.assertEqual([p["hex"] for p in near], ["3c6444", "3e1a2b"])
        far, _ = server.build_planes(data, LAT, LON, 100)
        self.assertEqual(len(far), 8)

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

    def test_shapes(self):
        self.assertEqual(server.shape_for({"t": "EC35", "category": "A7"}), "heli")
        self.assertEqual(server.shape_for({"category": "A7"}), "heli")
        self.assertEqual(server.shape_for({"t": "AT72", "category": "A3"}), "turboprop")
        self.assertEqual(server.shape_for({"t": "A388", "category": "A5"}), "wide")
        self.assertEqual(server.shape_for({"t": "C25C", "category": "A2"}), "bizjet")
        self.assertEqual(server.shape_for({"t": "C172", "category": "A1"}), "light")
        self.assertEqual(server.shape_for({"t": "A320", "category": "A3"}), "narrow")
        self.assertEqual(server.shape_for({}), "narrow")

    def test_demo_planes_have_airline_photo_and_shape(self):
        air = server.load_airlines(dict(server.DEFAULTS, DEMO="1", USER_DATA_DIR="/nonexistent"))
        planes, _ = server.build_planes(self._demo(), LAT, LON, 10, air, None, demo=True)
        by = {p["hex"]: p for p in planes}
        self.assertEqual(by["dd0001"]["airline"], "Zenith Air")
        self.assertEqual(by["dd0001"]["airline_icao"], "ZZA")
        self.assertTrue(by["dd0001"]["photo"].startswith("/demo/photos/"))
        self.assertEqual(by["3e1a2b"]["shape"], "heli")
        self.assertIsNone(by["3e1a2b"]["airline"])

    def test_logo_lookup_and_curated_names_win(self):
        cfg = dict(server.DEFAULTS, DEMO="1", USER_DATA_DIR="/nonexistent")
        logo = server.find_logo("ZZA", cfg)
        self.assertTrue(logo and {"w", "h", "palette", "rows"} <= set(logo))
        self.assertIsNone(server.find_logo("RYR", cfg))
        self.assertIsNone(server.find_logo("../x", cfg))                         # no path tricks
        self.assertIsNone(server.find_logo("ZZA", dict(cfg, DEMO="0")))          # demo logos only in demo mode
        with tempfile.TemporaryDirectory() as d:                                  # downloaded list must not override curated names
            os.makedirs(os.path.join(d, "data"))
            with open(os.path.join(d, "data", "airlines.json"), "w") as fh:
                json.dump({"SWR": {"name": "Swissair", "iata": "SR"}, "QQQ": {"name": "Test Air", "iata": "QQ"}}, fh)
            air = server.load_airlines(dict(server.DEFAULTS, USER_DATA_DIR=d))
            self.assertEqual(air["SWR"]["name"], "Swiss")
            self.assertEqual(air["QQQ"]["name"], "Test Air")

    def test_public_config_defaults(self):
        cfg = dict(server.DEFAULTS, UNITS="bogus")
        self.assertEqual(server.public_config(cfg)["units"], "metric")
        self.assertEqual(server.public_config(dict(cfg, THEME="purple"))["theme"], "amber")   # amber is the default
        self.assertEqual(server.public_config(cfg)["radius_presets"], [1, 2, 5, 10, 15, 30, 50])


if __name__ == "__main__":
    unittest.main()
